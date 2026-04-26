from django.urls import path, include
from rest_framework.routers import DefaultRouter

from accounting.api.views import (
    AdminSettlementApproveView,
    AdminSettlementListView,
    AdminSettlementRejectView,
    MerchantBalanceView,
    MerchantPayoutListView,
    MerchantLedgerListView,
    MerchantPayoutRequestView,
    PurchaseOrderViewSet,
)

router = DefaultRouter()
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')

urlpatterns = [
    # Merchant Endpoints
    path('balance/', MerchantBalanceView.as_view(), name='merchant_balance'),
    path('payouts/', MerchantPayoutListView.as_view(), name='merchant_payout_list'),
    path('payouts/request/', MerchantPayoutRequestView.as_view(), name='merchant_payout_request'),
    path('ledger/', MerchantLedgerListView.as_view(), name='merchant_ledger_list'),
    path('', include(router.urls)),

    # Admin Endpoints
    path('admin/settlements/', AdminSettlementListView.as_view(), name='admin_settlement_list'),
    path('admin/settlements/<uuid:pk>/approve/', AdminSettlementApproveView.as_view(), name='admin_settlement_approve'),
    path('admin/settlements/<uuid:pk>/reject/', AdminSettlementRejectView.as_view(), name='admin_settlement_reject'),
]
