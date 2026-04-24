from django.urls import path, include
from rest_framework.routers import DefaultRouter
from billing.api.views import (
    BillingContextViewSet, PaymentGatewayViewSet, PaymentMethodViewSet,
    APITokenViewSet, OutboundWebhookViewSet
)

router = DefaultRouter()
router.register(r'context', BillingContextViewSet, basename='billing-context')
router.register(r'gateways', PaymentGatewayViewSet, basename='payment-gateways')
router.register(r'methods', PaymentMethodViewSet, basename='payment-methods')
router.register(r'tokens', APITokenViewSet, basename='api-tokens')
router.register(r'webhooks', OutboundWebhookViewSet, basename='outbound-webhooks')

urlpatterns = [
    path('', include(router.urls)),
]
