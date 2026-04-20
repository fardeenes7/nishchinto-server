from django.urls import path
from .claim_views import ShopClaimView
from .views import ShopDetailView, ActiveShopContextView

urlpatterns = [
    path('claim/', ShopClaimView.as_view(), name='shop_claim'),
    path('me/', ShopDetailView.as_view(), name='shop_detail'),
    path('active/', ActiveShopContextView.as_view(), name='shop_active_context'),
]
