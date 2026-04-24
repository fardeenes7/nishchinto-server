from datetime import timedelta

from django.utils import timezone

from compliance.audit import audit_event_create
from orders.models import Order, PaymentInvoice
from shops.models import ShopSettings


class PaymentInvoiceNotFoundError(Exception):
    pass


class PaymentInvoiceGoneError(Exception):
    pass


def payment_invoice_create(*, order: Order) -> PaymentInvoice:
    reservation_minutes = 30
    try:
        settings_obj = order.shop.settings
    except ShopSettings.DoesNotExist:
        settings_obj = None
    if settings_obj and settings_obj.stock_reservation_minutes > 0:
        reservation_minutes = settings_obj.stock_reservation_minutes

    return PaymentInvoice.objects.create(
        order=order,
        shop_id=order.shop_id,
        tenant_id=order.tenant_id,
        expires_at=timezone.now() + timedelta(minutes=reservation_minutes),
        is_used=False,
    )


def payment_invoice_get_for_shop(*, token: str, shop_id: str) -> PaymentInvoice:
    invoice = (
        PaymentInvoice.objects
        .select_related("order", "order__shop")
        .filter(token=token, deleted_at__isnull=True)
        .first()
    )
    if not invoice or str(invoice.shop_id) != str(shop_id):
        raise PaymentInvoiceNotFoundError()
    return invoice


def payment_invoice_assert_active(*, invoice: PaymentInvoice) -> None:
    if invoice.is_used:
        raise PaymentInvoiceGoneError("used")
    if invoice.expires_at <= timezone.now():
        raise PaymentInvoiceGoneError("expired")


def payment_invoice_consume(*, token: str, shop_id: str) -> PaymentInvoice:
    invoice = payment_invoice_get_for_shop(token=token, shop_id=shop_id)
    payment_invoice_assert_active(invoice=invoice)
    invoice.is_used = True
    invoice.used_at = timezone.now()
    invoice.save(update_fields=["is_used", "used_at", "updated_at"])

    audit_event_create(
        shop_id=str(invoice.shop_id),
        action="PAYMENT_INVOICE_CONSUMED",
        resource_type="orders.PaymentInvoice",
        resource_id=str(invoice.id),
        metadata={
            "order_id": str(invoice.order_id),
            "token": str(invoice.token),
        },
    )
    return invoice
