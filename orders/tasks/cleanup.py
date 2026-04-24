from django.db import transaction
from django.utils import timezone
from celery import shared_task

from orders.models import Order
from orders.services.reservations import reservation_clear
from orders.services.transitions import order_transition


@shared_task(bind=True, max_retries=2)
def cancel_expired_payment_reservations(self):
    now = timezone.now()
    expired_orders = Order.objects.filter(
        status="AWAITING_PAYMENT",
        lock_expires_at__isnull=False,
        lock_expires_at__lte=now,
        deleted_at__isnull=True,
    ).only("id", "status", "lock_expires_at", "shop_id")

    cancelled_ids = []
    for order in expired_orders:
        with transaction.atomic():
            order_transition(
                order=order,
                to_status="CANCELLED",
                reason="Payment reservation expired",
            )
            reservation_clear(order_id=str(order.id))
            cancelled_ids.append(str(order.id))

    return {"cancelled_order_ids": cancelled_ids, "count": len(cancelled_ids)}
