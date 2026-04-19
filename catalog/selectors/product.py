"""
Catalog selectors — read-only query layer.

No business logic here. Pure ORM queries optimised with select_related/
prefetch_related to avoid N+1 problems.

Search architecture (Fix 6.8 — post_v03_debrief.md):
  - Dashboard product list: Postgres FTS (status/category/shop filters; no typo tolerance needed)
  - Storefront search: Meilisearch (typo tolerance, Banglish phonetic matching)
  - Fallback: if Meilisearch is unavailable, storefront search falls back to Postgres FTS
    with a logged warning.
"""
import logging

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def product_count_active(*, shop_id: str) -> int:
    """Returns the count of non-deleted, non-archived products for a shop."""
    from catalog.models import Product

    return Product.objects.filter(
        shop_id=shop_id,
        deleted_at__isnull=True,
    ).exclude(status="ARCHIVED").count()


def product_list_for_dashboard(
    *,
    shop_id: str,
    status: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> QuerySet:
    """
    Returns a queryset of Products for the seller dashboard.
    Supports status filter, category filter, and full-text search via Postgres FTS.

    Note: Dashboard search uses Postgres FTS — typo tolerance is not required here
    since sellers know their own product names. Meilisearch is used for storefront
    (customer-facing) search only.
    """
    from catalog.models import Product

    qs = (
        Product.objects.filter(shop_id=shop_id, deleted_at__isnull=True)
        .select_related("category")
        .prefetch_related("product_media__media", "variants")
        .order_by("sort_order", "-created_at")
    )

    if status:
        qs = qs.filter(status=status)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if search:
        query = SearchQuery(search, config="english")
        qs = (
            qs.annotate(rank=SearchRank("search_vector", query))
            .filter(search_vector=query)
            .order_by("-rank")
        )

    return qs


def product_get_by_id(*, product_id: str, shop_id: str) -> "Product":  # noqa: F821
    from catalog.models import Product

    return (
        Product.objects.select_related("category", "shop__tracking_config")
        .prefetch_related("product_media__media", "variants__image")
        .get(id=product_id, shop_id=shop_id, deleted_at__isnull=True)
    )


def product_list_for_storefront(
    *,
    shop_id: str,
    category_slug: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> QuerySet:
    """
    Returns only PUBLISHED products for the public storefront.
    Orders by manual sort_order (drag-drop configured by merchant).

    Fix 6.8: When `search` is provided, queries Meilisearch for typo-tolerant
    (Banglish-aware) results, then fetches matching IDs from Postgres to preserve
    the full ORM queryset interface (with prefetch_related etc.). Falls back to
    Postgres FTS if Meilisearch is unavailable.
    """
    from catalog.models import Product

    base_qs = (
        Product.objects.filter(
            shop_id=shop_id,
            status__in=["PUBLISHED", "OUT_OF_STOCK"],
            deleted_at__isnull=True,
        )
        .select_related("category")
        .prefetch_related(
            "product_media__media",
            "variants",
        )
        .order_by("sort_order", "-created_at")
    )

    if category_slug:
        base_qs = base_qs.filter(category__slug=category_slug)

    if search:
        meili_ids = _search_via_meilisearch(shop_id=shop_id, query=search)
        if meili_ids is not None:
            # Preserve Meilisearch relevance ordering via a CASE WHEN expression
            from django.db.models import Case, IntegerField, Value, When
            order_cases = [
                When(id=product_id, then=Value(rank))
                for rank, product_id in enumerate(meili_ids)
            ]
            if order_cases:
                base_qs = base_qs.filter(id__in=meili_ids).annotate(
                    meili_rank=Case(*order_cases, default=Value(9999), output_field=IntegerField())
                ).order_by("meili_rank")
            else:
                # No results from Meilisearch
                return base_qs.none()
        else:
            # Meilisearch unavailable — fall back to Postgres FTS
            fts_query = SearchQuery(search, config="english")
            base_qs = (
                base_qs.annotate(rank=SearchRank("search_vector", fts_query))
                .filter(search_vector=fts_query)
                .order_by("-rank")
            )

    return base_qs


def _search_via_meilisearch(*, shop_id: str, query: str) -> list[str] | None:
    """
    Executes a Meilisearch query scoped to a single shop.
    Returns a list of product ID strings in relevance order, or None if Meilisearch
    is unavailable (so the caller can fall back to Postgres FTS).

    Tenant isolation is enforced by the `filter: "shop_id = {shop_id}"` clause.
    """
    try:
        from catalog.services.search import get_or_create_index

        index = get_or_create_index()
        result = index.search(
            query,
            {
                "filter": f"shop_id = {shop_id}",
                "attributesToRetrieve": ["id"],
                "limit": 200,  # More than a typical page; Postgres handles pagination
            },
        )
        return [hit["id"] for hit in result.get("hits", [])]
    except Exception as exc:
        logger.warning(
            "_search_via_meilisearch: Meilisearch unavailable, falling back to Postgres FTS. Error: %s",
            exc,
        )
        return None


def product_get_for_storefront(*, shop_id: str, slug: str) -> "Product":  # noqa: F821
    """
    Returns a single PUBLISHED product for the storefront by slug.
    Raises Product.DoesNotExist if not found or not published.
    """
    from catalog.models import Product

    return (
        Product.objects.select_related("category")
        .prefetch_related(
            "product_media__media",
            "variants__image",
        )
        .get(
            shop_id=shop_id,
            slug=slug,
            status__in=["PUBLISHED", "OUT_OF_STOCK"],
            deleted_at__isnull=True,
        )
    )


def category_list_for_shop(*, shop_id: str) -> QuerySet:
    from catalog.models import Category

    return Category.objects.filter(
        shop_id=shop_id, deleted_at__isnull=True, is_active=True
    ).select_related("parent").order_by("sort_order", "name")


def variant_list_for_product(*, product_id: str, shop_id: str) -> QuerySet:
    from catalog.models import ProductVariant

    return ProductVariant.objects.filter(
        product_id=product_id,
        shop_id=shop_id,
        deleted_at__isnull=True,
    ).select_related("image").order_by("attribute_value_1", "attribute_value_2")

