from django.urls import path
from .claim_views import ShopClaimView

urlpatterns = [
    path('claim/', ShopClaimView.as_view(), name='shop_claim'),
]
