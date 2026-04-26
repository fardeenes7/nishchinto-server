from django.urls import path

from accounting.api.views import (
    AdminSettlementApproveView,
    AdminSettlementListView,
    AdminSettlementRejectView,
)

urlpatterns = [
    path('admin/settlements/', AdminSettlementListView.as_view(), name='admin_settlement_list'),
    path('admin/settlements/<uuid:pk>/approve/', AdminSettlementApproveView.as_view(), name='admin_settlement_approve'),
    path('admin/settlements/<uuid:pk>/reject/', AdminSettlementRejectView.as_view(), name='admin_settlement_reject'),
]
