"""
Catalog signals.

1. Auto-create ShopTrackingConfig when a new Shop is created.
2. Update Product.search_vector when name/description changes (Postgres FTS fallback).
3. Enqueue CatalogIndexingTask to sync Product to Meilisearch on create/update/delete.
   Fix 6.8 (post_v03_debrief.md).
"""
from django.contrib.postgres.search import SearchVector
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="shops.Shop")
def create_shop_tracking_config(sender, instance, created, **kwargs):
    """Auto-create a ShopTrackingConfig record when a new Shop is saved."""
    if created:
        from catalog.models.tracking import ShopTrackingConfig
        ShopTrackingConfig.objects.get_or_create(shop=instance)


@receiver(post_save, sender="catalog.Product")
def update_product_search_vector(sender, instance, **kwargs):
    """
    Rebuild the product's Postgres full-text search vector after each save.
    Uses update() to avoid recursive signal emission.

    NOTE: This is kept as a legacy signal for dashboard keyword search fallback
    (product_list_for_dashboard still queries Postgres directly for status/category
    filters). Meilisearch handles storefront typo-tolerant search via the separate
    meilisearch_index_product signal below.
    """
    from catalog.models.product import Product

    Product.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector("name", weight="A")
            + SearchVector("description", weight="B")
            + SearchVector("sku", weight="C")
        )
    )


@receiver(post_save, sender="catalog.Product")
def meilisearch_index_product(sender, instance, **kwargs):
    """
    Fix 6.8: Enqueue an async Celery task to sync this Product to Meilisearch.

    Uses transaction.on_commit so the task is dispatched only after the Postgres
    row is fully committed — prevents Celery from reading stale data.
    Soft-deleted products (deleted_at set) are removed from the Meilisearch index
    by the task itself.
    """
    from catalog.tasks import catalog_index_product

    product_id = str(instance.pk)

    def _enqueue():
        catalog_index_product.delay(product_id)

    transaction.on_commit(_enqueue)
