from django.urls import path
from .claim_views import ShopCreateView
from .views import ShopDetailView, ActiveShopContextView, ShopSettingsView, ShopTrackingConfigView, StoreThemeView

urlpatterns = [
    path('create/', ShopCreateView.as_view(), name='shop_create'),
    path('claim/', ShopCreateView.as_view(), name='shop_claim'),
    path('me/', ShopDetailView.as_view(), name='shop_detail'),
    path('active/', ActiveShopContextView.as_view(), name='shop_active_context'),
    path('settings/', ShopSettingsView.as_view(), name='shop_settings'),
    path('tracking/', ShopTrackingConfigView.as_view(), name='shop_tracking'),
    path('theme/', StoreThemeView.as_view(), name='shop_theme'),
]
