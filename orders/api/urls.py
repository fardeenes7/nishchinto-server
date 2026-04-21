from django.urls import path

from orders.api.views import (
    StorefrontPaymentInvoiceCodConfirmView,
    StorefrontPaymentInvoiceDetailView,
)

storefront_urlpatterns = [
    path(
        "<slug:shop_slug>/pay/<uuid:token>/",
        StorefrontPaymentInvoiceDetailView.as_view(),
        name="storefront-payment-invoice-detail",
    ),
    path(
        "<slug:shop_slug>/pay/<uuid:token>/cod-confirm/",
        StorefrontPaymentInvoiceCodConfirmView.as_view(),
        name="storefront-payment-invoice-cod-confirm",
    ),
]
