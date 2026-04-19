from django.urls import path, include
from rest_framework.routers import DefaultRouter

from catalog.api.views import (
    CategoryViewSet,
    ProductViewSet,
    VariantViewSet,
    TrackingConfigView,
)
from catalog.api.views.storefront import (
    StorefrontProductListView,
    StorefrontProductDetailView,
    StorefrontTrackingConfigView,
    StorefrontShopView,
)

# Dashboard router
router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")

# Nested variant routes (manual, since DefaultRouter doesn't support nested by default)
variant_list = VariantViewSet.as_view({"get": "list", "post": "create"})
variant_detail = VariantViewSet.as_view({"patch": "partial_update"})
variant_adjust_stock = VariantViewSet.as_view({"post": "adjust_stock"})

urlpatterns = [
    # ── Dashboard (authenticated) ──────────────────────────────────────────
    path("", include(router.urls)),

    # Nested variant endpoints
    path(
        "products/<uuid:product_pk>/variants/",
        variant_list,
        name="product-variant-list",
    ),
    path(
        "products/<uuid:product_pk>/variants/<uuid:pk>/",
        variant_detail,
        name="product-variant-detail",
    ),
    path(
        "products/<uuid:product_pk>/variants/<uuid:pk>/adjust-stock/",
        variant_adjust_stock,
        name="product-variant-adjust-stock",
    ),

    # Tracking config
    path("tracking-config/", TrackingConfigView.as_view(), name="tracking-config"),

    # ── Storefront (public) ────────────────────────────────────────────────
    # Note: mounted under /api/v1/storefront/ in the root urls.py
]

storefront_urlpatterns = [
    path(
        "<slug:shop_slug>/products/",
        StorefrontProductListView.as_view(),
        name="storefront-product-list",
    ),
    path(
        "<slug:shop_slug>/products/<slug:slug>/",
        StorefrontProductDetailView.as_view(),
        name="storefront-product-detail",
    ),
    path(
        "<slug:shop_slug>/tracking/",
        StorefrontTrackingConfigView.as_view(),
        name="storefront-tracking-config",
    ),
    path(
        "<slug:shop_slug>/config/",
        StorefrontShopView.as_view(),
        name="storefront-shop-config",
    ),
]
