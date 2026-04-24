from django.urls import path

from orders.api.views import (
    StorefrontPaymentInvoiceCodConfirmView,
    StorefrontPaymentInvoiceDetailView,
    POSCheckoutView
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

dashboard_urlpatterns = [
    path(
        "pos/checkout/",
        POSCheckoutView.as_view(),
        name="pos-checkout",
    ),
]
