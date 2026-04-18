from django.contrib import admin
from catalog.models import (
    Category,
    Product,
    ProductVariant,
    ProductMedia,
    ShopTrackingConfig,
    InventoryLog,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "shop", "status", "base_price", "created_at"]
    list_filter = ["status", "is_digital"]
    search_fields = ["name", "sku", "shop__name"]
    raw_id_fields = ["shop", "category"]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["__str__", "sku", "stock_quantity", "is_active"]
    search_fields = ["sku", "product__name"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "shop", "parent", "sort_order", "is_active"]
    search_fields = ["name", "shop__name"]


@admin.register(ShopTrackingConfig)
class ShopTrackingConfigAdmin(admin.ModelAdmin):
    list_display = ["shop", "fb_pixel_id", "ga4_measurement_id", "gtm_id"]


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ["variant", "delta", "reason", "reference_id", "created_at"]
    list_filter = ["reason"]
    readonly_fields = ["shop", "variant", "delta", "reason", "reference_id", "created_by", "created_at"]
