from django.urls import path

from compliance.api.views import AuditLogsView, InventoryLogsView, MessageLogsView, OrderLogsView

urlpatterns = [
    path("logs/orders/", OrderLogsView.as_view(), name="logs-orders"),
    path("logs/messages/", MessageLogsView.as_view(), name="logs-messages"),
    path("logs/inventory/", InventoryLogsView.as_view(), name="logs-inventory"),
    path("logs/audit/", AuditLogsView.as_view(), name="logs-audit"),
]
