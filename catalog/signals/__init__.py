"""
Catalog signals.

1. Auto-create ShopTrackingConfig when a new Shop is created.
2. Update Product.search_vector when name/description changes.
"""
from django.contrib.postgres.search import SearchVector
from django.db import models
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
    """
    from catalog.models.product import Product

    Product.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector("name", weight="A")
            + SearchVector("description", weight="B")
            + SearchVector("sku", weight="C")
        )
    )
