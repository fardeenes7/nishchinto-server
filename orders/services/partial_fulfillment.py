from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from catalog.models import InventoryLog, ProductVariant
from compliance.audit import audit_event_create
from orders.models import (
    Order,
    OrderItem,
    OrderRefundEvent,
    OrderRefundStatus,
    OrderSplitLink,
    OrderSplitMode,
    OrderStatus,
)
from orders.services.transitions import order_transition


class OptimisticLockError(Exception):
    pass


class PartialFulfillmentError(Exception):
    pass


@dataclass
class PartialFulfillmentResult:
    order_id: str
    child_order_id: str | None
    refund_amount: Decimal
    remaining_items: int


@dataclass
class PartialRefundResult:
    order_id: str
    refund_event_id: str
    refund_amount: Decimal
    refunded_items: int


@dataclass
class PartialInventoryReversalResult:
    refund_event_id: str
    reversed_quantity: int
    remaining_quantity: int


def _normalize_last_updated(value) -> timezone.datetime:
    if hasattr(value, "tzinfo"):
        dt_value = value
    elif isinstance(value, str):
        dt_value = parse_datetime(value)
        if dt_value is None:
            raise OptimisticLockError("Invalid last_updated_at format.")
    else:
        raise OptimisticLockError("last_updated_at is required.")

    if timezone.is_naive(dt_value):
        dt_value = timezone.make_aware(dt_value, timezone.get_current_timezone())
    return dt_value


def _assert_optimistic_lock(*, order: Order, last_updated_at) -> None:
    expected = _normalize_last_updated(last_updated_at)
    current = order.updated_at
    delta_seconds = abs((current - expected).total_seconds())
    if delta_seconds > 0.001:
        raise OptimisticLockError("Order was modified by another actor. Reload and retry.")


def _assert_order_partial_fulfillment_status(order: Order) -> None:
    if order.status not in {OrderStatus.CONFIRMED, OrderStatus.PROCESSING}:
        raise PartialFulfillmentError("Partial fulfillment is allowed only for CONFIRMED or PROCESSING orders.")


def _assert_refund_role_allowed(actor_role: str | None) -> None:
    if actor_role in {"CASHIER"}:
        raise PermissionDenied("Role CASHIER cannot execute partial refund or inventory reversal.")


def _recalculate_order_totals(order: Order) -> tuple[Decimal, int]:
    active_items = list(order.items.filter(deleted_at__isnull=True).only("line_total_amount", "quantity"))
    subtotal = sum((item.line_total_amount for item in active_items), Decimal("0.00"))
    order.subtotal_amount = subtotal
    order.total_amount = subtotal + order.shipping_amount - order.discount_amount
    order.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
    return subtotal, len(active_items)


def partial_fulfillment_split_order(
    *,
    order_id: str,
    unavailable_item_ids: Sequence[str],
    last_updated_at,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
) -> PartialFulfillmentResult:
    if not unavailable_item_ids:
        raise PartialFulfillmentError("unavailable_item_ids cannot be empty.")

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id, deleted_at__isnull=True)
        _assert_optimistic_lock(order=order, last_updated_at=last_updated_at)
        _assert_order_partial_fulfillment_status(order)

        unavailable_items = list(
            OrderItem.objects.select_for_update()
            .filter(order=order, id__in=unavailable_item_ids, deleted_at__isnull=True)
        )
        if len(unavailable_items) != len(set(unavailable_item_ids)):
            raise PartialFulfillmentError("One or more unavailable items are invalid for this order.")

        child_order = Order.objects.create(
            shop=order.shop,
            tenant_id=order.tenant_id,
            customer_profile=order.customer_profile,
            status=OrderStatus.ON_HOLD,
            subtotal_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            currency=order.currency,
        )

        moved_item_ids: list[str] = []
        for item in unavailable_items:
            OrderItem.objects.create(
                order=child_order,
                tenant_id=child_order.tenant_id,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_discount_amount=item.line_discount_amount,
                line_total_amount=item.line_total_amount,
            )
            item.delete()
            moved_item_ids.append(str(item.id))

        _, remaining_items = _recalculate_order_totals(order)
        _recalculate_order_totals(child_order)

        if remaining_items > 0 and order.status == OrderStatus.CONFIRMED:
            order_transition(
                order=order,
                to_status=OrderStatus.PROCESSING,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason="Partial fulfillment split: processing available items",
            )
        elif remaining_items == 0 and order.status != OrderStatus.ON_HOLD:
            order_transition(
                order=order,
                to_status=OrderStatus.ON_HOLD,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason="Partial fulfillment split: all items moved to child order",
            )

        OrderSplitLink.objects.create(
            parent_order=order,
            child_order=child_order,
            split_mode=OrderSplitMode.BACKORDER_SPLIT,
            metadata={"moved_item_ids": moved_item_ids},
        )

        audit_event_create(
            shop_id=str(order.shop_id),
            actor_user_id=actor_user_id,
            action="ORDER_PARTIAL_FULFILLMENT_SPLIT",
            resource_type="orders.Order",
            resource_id=str(order.id),
            metadata={
                "child_order_id": str(child_order.id),
                "moved_item_ids": moved_item_ids,
            },
        )

        return PartialFulfillmentResult(
            order_id=str(order.id),
            child_order_id=str(child_order.id),
            refund_amount=Decimal("0.00"),
            remaining_items=remaining_items,
        )


def partial_fulfillment_cancel_items(
    *,
    order_id: str,
    cancelled_item_ids: Sequence[str],
    last_updated_at,
    actor_user_id: str | None = None,
    actor_role: str | None = None,
) -> PartialFulfillmentResult:
    if not cancelled_item_ids:
        raise PartialFulfillmentError("cancelled_item_ids cannot be empty.")

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id, deleted_at__isnull=True)
        _assert_optimistic_lock(order=order, last_updated_at=last_updated_at)
        _assert_order_partial_fulfillment_status(order)

        cancelled_items = list(
            OrderItem.objects.select_for_update()
            .filter(order=order, id__in=cancelled_item_ids, deleted_at__isnull=True)
        )
        if len(cancelled_items) != len(set(cancelled_item_ids)):
            raise PartialFulfillmentError("One or more cancelled items are invalid for this order.")

        refund_amount = sum((item.line_total_amount for item in cancelled_items), Decimal("0.00"))
        removed_item_ids: list[str] = []
        for item in cancelled_items:
            removed_item_ids.append(str(item.id))
            item.delete()

        _, remaining_items = _recalculate_order_totals(order)

        if remaining_items == 0:
            order_transition(
                order=order,
                to_status=OrderStatus.CANCELLED,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason="Partial fulfillment cancel: all items removed",
            )
        elif order.status == OrderStatus.CONFIRMED:
            order_transition(
                order=order,
                to_status=OrderStatus.PROCESSING,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason="Partial fulfillment cancel: continue with remaining items",
            )

        audit_event_create(
            shop_id=str(order.shop_id),
            actor_user_id=actor_user_id,
            action="ORDER_PARTIAL_FULFILLMENT_CANCEL",
            resource_type="orders.Order",
            resource_id=str(order.id),
            metadata={
                "cancelled_item_ids": removed_item_ids,
                "refund_amount": str(refund_amount),
                "remaining_items": remaining_items,
            },
        )

        return PartialFulfillmentResult(
            order_id=str(order.id),
            child_order_id=None,
            refund_amount=refund_amount,
            remaining_items=remaining_items,
        )


def partial_refund_create(
    *,
    order_id: str,
    refund_items: Sequence[dict],
    actor_user_id: str | None = None,
    actor_role: str | None = None,
    reason: str = "",
) -> PartialRefundResult:
    if not refund_items:
        raise PartialFulfillmentError("refund_items cannot be empty.")

    _assert_refund_role_allowed(actor_role)

    requested_by_item: dict[str, int] = {}
    for entry in refund_items:
        item_id = str(entry.get("order_item_id", ""))
        quantity = int(entry.get("quantity", 0))
        if not item_id or quantity <= 0:
            raise PartialFulfillmentError("Each refund item must include order_item_id and positive quantity.")
        requested_by_item[item_id] = requested_by_item.get(item_id, 0) + quantity

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id, deleted_at__isnull=True)
        items = list(
            OrderItem.objects.select_for_update().filter(
                order=order,
                id__in=list(requested_by_item.keys()),
                deleted_at__isnull=True,
            )
        )
        if len(items) != len(requested_by_item):
            raise PartialFulfillmentError("One or more refund items are invalid for this order.")

        line_items: list[dict] = []
        total_refund = Decimal("0.00")
        for item in items:
            quantity = requested_by_item[str(item.id)]
            if quantity > item.quantity:
                raise PartialFulfillmentError("Refund quantity exceeds purchased quantity.")

            line_total_refund = (item.line_total_amount * Decimal(quantity) / Decimal(item.quantity)).quantize(Decimal("0.01"))
            total_refund += line_total_refund
            line_items.append(
                {
                    "order_item_id": str(item.id),
                    "variant_id": str(item.variant_id) if item.variant_id else None,
                    "quantity": quantity,
                    "line_refund_amount": str(line_total_refund),
                }
            )

        refund_event = OrderRefundEvent.objects.create(
            order=order,
            shop=order.shop,
            amount=total_refund,
            currency=order.currency,
            status=OrderRefundStatus.REQUESTED,
            reason=reason,
            metadata={"items": line_items, "inventory_reversed": {}},
            actor_user_id=actor_user_id,
        )

        audit_event_create(
            shop_id=str(order.shop_id),
            actor_user_id=actor_user_id,
            action="ORDER_PARTIAL_REFUND_CREATED",
            resource_type="orders.OrderRefundEvent",
            resource_id=str(refund_event.id),
            metadata={
                "order_id": str(order.id),
                "refund_amount": str(total_refund),
                "reason": reason,
                "line_items": line_items,
            },
        )

        return PartialRefundResult(
            order_id=str(order.id),
            refund_event_id=str(refund_event.id),
            refund_amount=total_refund,
            refunded_items=len(line_items),
        )


def partial_inventory_reversal_apply(
    *,
    refund_event_id: str,
    reversal_items: Sequence[dict],
    actor_user_id: str | None = None,
    actor_role: str | None = None,
) -> PartialInventoryReversalResult:
    if not reversal_items:
        raise PartialFulfillmentError("reversal_items cannot be empty.")

    _assert_refund_role_allowed(actor_role)

    requested_by_item: dict[str, int] = {}
    for entry in reversal_items:
        item_id = str(entry.get("order_item_id", ""))
        quantity = int(entry.get("quantity", 0))
        if not item_id or quantity <= 0:
            raise PartialFulfillmentError("Each reversal item must include order_item_id and positive quantity.")
        requested_by_item[item_id] = requested_by_item.get(item_id, 0) + quantity

    with transaction.atomic():
        refund_event = OrderRefundEvent.objects.select_for_update().select_related("order", "shop").get(id=refund_event_id)

        metadata = dict(refund_event.metadata or {})
        lines = metadata.get("items", [])
        if not lines:
            raise PartialFulfillmentError("Refund event has no refundable items.")

        line_map = {line["order_item_id"]: line for line in lines}
        if any(item_id not in line_map for item_id in requested_by_item):
            raise PartialFulfillmentError("One or more reversal items are not part of the refund event.")

        inventory_reversed = dict(metadata.get("inventory_reversed", {}))
        variant_ids = {
            line_map[item_id]["variant_id"]
            for item_id in requested_by_item
            if line_map[item_id].get("variant_id")
        }
        variants = {
            str(variant.id): variant
            for variant in ProductVariant.objects.select_for_update().filter(id__in=list(variant_ids), deleted_at__isnull=True)
        }

        total_reversed = 0
        for item_id, quantity in requested_by_item.items():
            line = line_map[item_id]
            max_qty = int(line["quantity"])
            already_reversed = int(inventory_reversed.get(item_id, 0))
            if already_reversed + quantity > max_qty:
                raise PartialFulfillmentError("Reversal quantity exceeds refunded quantity.")

            variant_id = line.get("variant_id")
            if not variant_id:
                inventory_reversed[item_id] = already_reversed + quantity
                total_reversed += quantity
                continue

            variant = variants.get(variant_id)
            if not variant:
                raise PartialFulfillmentError("Variant not found for reversal item.")

            variant.stock_quantity += quantity
            variant.save(update_fields=["stock_quantity", "updated_at"])
            InventoryLog.objects.create(
                shop=refund_event.shop,
                variant=variant,
                delta=quantity,
                reason=InventoryLog.Reason.RETURN,
                reference_id=str(refund_event.id),
                created_by_id=actor_user_id,
            )

            inventory_reversed[item_id] = already_reversed + quantity
            total_reversed += quantity

        metadata["inventory_reversed"] = inventory_reversed
        all_reversed = all(int(inventory_reversed.get(line["order_item_id"], 0)) >= int(line["quantity"]) for line in lines)
        if all_reversed:
            refund_event.status = OrderRefundStatus.COMPLETED
            refund_event.inventory_reversed_at = timezone.now()

        refund_event.metadata = metadata
        update_fields = ["metadata"]
        if all_reversed:
            update_fields.extend(["status", "inventory_reversed_at"])
        refund_event.save(update_fields=update_fields)

        remaining_quantity = sum(
            int(line["quantity"]) - int(inventory_reversed.get(line["order_item_id"], 0))
            for line in lines
        )

        audit_event_create(
            shop_id=str(refund_event.shop_id),
            actor_user_id=actor_user_id,
            action="ORDER_PARTIAL_INVENTORY_REVERSED",
            resource_type="orders.OrderRefundEvent",
            resource_id=str(refund_event.id),
            metadata={
                "order_id": str(refund_event.order_id),
                "reversal_items": requested_by_item,
                "remaining_quantity": remaining_quantity,
            },
        )

        return PartialInventoryReversalResult(
            refund_event_id=str(refund_event.id),
            reversed_quantity=total_reversed,
            remaining_quantity=remaining_quantity,
        )
