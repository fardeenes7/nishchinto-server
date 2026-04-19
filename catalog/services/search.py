"""
Meilisearch service helpers for catalog indexing.

Fix 6.8 (post_v03_debrief.md): Meilisearch is the primary catalog search engine.
Supports Bengali phonetic (Banglish) typo-tolerance and faceted filtering that
Postgres FTS cannot provide at scale.

Usage:
  from catalog.services.search import get_meili_client, PRODUCTS_INDEX

Architecture:
  - One index per shop is an anti-pattern at scale; we use a single shared
    'products' index with 'shop_id' as a filterable attribute.
  - All queries against Meilisearch MUST include a `filter: "shop_id = X"` clause
    to enforce tenant isolation at the search layer.
"""

import logging

import meilisearch
from django.conf import settings

logger = logging.getLogger(__name__)

PRODUCTS_INDEX = "products"

# Attributes that Meilisearch should make filterable/sortable
FILTERABLE_ATTRIBUTES = ["shop_id", "status", "category_id", "is_digital"]
SORTABLE_ATTRIBUTES = ["sort_order", "created_at", "base_price"]
SEARCHABLE_ATTRIBUTES = ["name", "description", "sku", "category_name"]

# Typo tolerance: allow 1 typo for words ≥4 chars, 2 typos for words ≥8 chars
TYPO_TOLERANCE = {
    "enabled": True,
    "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8},
}


def get_meili_client() -> meilisearch.Client:
    """Returns a configured Meilisearch client. No connection is made until a request."""
    return meilisearch.Client(
        settings.MEILISEARCH_HOST,
        settings.MEILISEARCH_API_KEY,
    )


def get_or_create_index() -> meilisearch.index.Index:
    """
    Returns the products index, creating and configuring it if it doesn't exist.
    Safe to call multiple times — settings updates are idempotent.
    """
    client = get_meili_client()
    try:
        index = client.get_index(PRODUCTS_INDEX)
    except meilisearch.errors.MeilisearchApiError:
        # Index does not exist — create it with 'id' as the primary key
        task = client.create_index(PRODUCTS_INDEX, {"primaryKey": "id"})
        client.wait_for_task(task.task_uid)
        index = client.get_index(PRODUCTS_INDEX)

    # Apply settings (idempotent)
    index.update_filterable_attributes(FILTERABLE_ATTRIBUTES)
    index.update_sortable_attributes(SORTABLE_ATTRIBUTES)
    index.update_searchable_attributes(SEARCHABLE_ATTRIBUTES)
    index.update_typo_tolerance(TYPO_TOLERANCE)

    return index


def build_product_document(product) -> dict:
    """
    Serialises a Product ORM instance into a Meilisearch document dict.
    Must be called with the product's related category pre-fetched.
    """
    thumbnail = None
    for pm in getattr(product, "_prefetched_objects_cache", {}).get("product_media", []):
        if pm.is_thumbnail and pm.media:
            thumbnail = pm.media.cdn_url
            break

    return {
        "id": str(product.id),
        "shop_id": str(product.shop_id),
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku or "",
        "description": product.description or "",
        "status": product.status,
        "base_price": float(product.base_price),
        "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
        "category_id": str(product.category_id) if product.category_id else None,
        "category_name": product.category.name if product.category else None,
        "is_digital": product.is_digital,
        "sort_order": product.sort_order,
        "thumbnail": thumbnail,
        "total_stock": product.total_stock if hasattr(product, "total_stock") else 0,
        "created_at": product.created_at.isoformat(),
    }


def index_product(product) -> None:
    """
    Adds or updates a single product in the Meilisearch index.
    Soft-deleted products are automatically removed by the signal handler.
    """
    try:
        index = get_or_create_index()
        doc = build_product_document(product)
        index.add_documents([doc])
    except Exception as exc:
        # Never let a Meilisearch failure break a product save
        logger.error(
            "Meilisearch index_product failed for product=%s: %s",
            getattr(product, "id", "?"),
            exc,
            exc_info=True,
        )


def delete_product_from_index(product_id: str) -> None:
    """Removes a product document from the Meilisearch index."""
    try:
        index = get_or_create_index()
        index.delete_document(product_id)
    except Exception as exc:
        logger.error(
            "Meilisearch delete_product failed for product_id=%s: %s",
            product_id,
            exc,
            exc_info=True,
        )
