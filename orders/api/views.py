from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.api.serializers import (
    PaymentInvoiceCodConfirmResponseSerializer,
    PaymentInvoicePublicSerializer,
)
from orders.services import (
    PaymentInvoiceGoneError,
    PaymentInvoiceNotFoundError,
    payment_invoice_assert_active,
    payment_invoice_consume,
    payment_invoice_get_for_shop,
    order_transition,
)
from shops.models import Shop


class StorefrontPaymentInvoiceBaseView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_shop(self, shop_slug: str) -> Shop:
        return Shop.objects.get(subdomain=shop_slug, deleted_at__isnull=True)


class StorefrontPaymentInvoiceDetailView(StorefrontPaymentInvoiceBaseView):
    @extend_schema(
        tags=["storefront", "orders"],
        responses={200: PaymentInvoicePublicSerializer},
        summary="Validate and fetch public payment invoice by token",
    )
    def get(self, request, shop_slug: str, token: str):
        try:
            shop = self.get_shop(shop_slug=shop_slug)
        except Shop.DoesNotExist:
            return Response({"detail": "Shop not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            invoice = payment_invoice_get_for_shop(token=token, shop_id=str(shop.id))
            payment_invoice_assert_active(invoice=invoice)
        except PaymentInvoiceNotFoundError:
            return Response({"detail": "Payment invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        except PaymentInvoiceGoneError as exc:
            return Response({"detail": f"Payment invoice is {exc.args[0]}."}, status=status.HTTP_410_GONE)

        serializer = PaymentInvoicePublicSerializer(invoice)
        payload = serializer.data
        payload["payment_methods"] = [
            {"code": "COD", "label": "Cash on Delivery", "enabled": True},
            {"code": "ONLINE", "label": "Pay Online", "enabled": False},
        ]
        return Response(payload)


class StorefrontPaymentInvoiceCodConfirmView(StorefrontPaymentInvoiceBaseView):
    @extend_schema(
        tags=["storefront", "orders"],
        request=None,
        responses={200: PaymentInvoiceCodConfirmResponseSerializer},
        summary="Confirm order via COD by consuming payment invoice token",
    )
    def post(self, request, shop_slug: str, token: str):
        try:
            shop = self.get_shop(shop_slug=shop_slug)
        except Shop.DoesNotExist:
            return Response({"detail": "Shop not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            invoice = payment_invoice_consume(token=token, shop_id=str(shop.id))
        except PaymentInvoiceNotFoundError:
            return Response({"detail": "Payment invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        except PaymentInvoiceGoneError as exc:
            return Response({"detail": f"Payment invoice is {exc.args[0]}."}, status=status.HTTP_410_GONE)

        if invoice.order.status in {"PENDING", "AWAITING_PAYMENT"}:
            order_transition(
                order=invoice.order,
                to_status="CONFIRMED",
                reason="COD confirmation via payment invoice page",
            )

        return Response(
            {
                "order_id": invoice.order_id,
                "order_status": invoice.order.status,
                "invoice_token": invoice.token,
            }
        )
