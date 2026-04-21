from orders.models import Order, OrderTransitionLog


def order_transition(*, order: Order, to_status: str, actor_user_id: str | None = None, reason: str = '') -> Order:
    allowed_transitions = {
        "PENDING": {"AWAITING_PAYMENT", "CANCELLED", "ON_HOLD"},
        "AWAITING_PAYMENT": {"CONFIRMED", "CANCELLED", "ON_HOLD"},
        "CONFIRMED": {"PROCESSING", "CANCELLED", "ON_HOLD"},
        "PROCESSING": {"SHIPPED", "CANCELLED", "ON_HOLD"},
        "SHIPPED": {"IN_TRANSIT", "CANCELLED", "ON_HOLD"},
        "IN_TRANSIT": {"DELIVERED", "RTO_RETURNED", "CANCELLED", "ON_HOLD"},
        "DELIVERED": {"REFUNDED", "ON_HOLD"},
        "RTO_RETURNED": {"CONFIRMED", "REFUNDED", "ON_HOLD"},
        "ON_HOLD": {"PENDING", "AWAITING_PAYMENT", "CONFIRMED", "PROCESSING", "SHIPPED", "IN_TRANSIT", "DELIVERED", "CANCELLED", "REFUNDED", "RTO_RETURNED"},
    }

    current_status = str(order.status)
    if current_status == to_status:
        return order

    next_allowed = allowed_transitions.get(current_status, set())
    if to_status not in next_allowed:
        raise ValueError(f"Illegal order transition: {current_status} -> {to_status}")

    order.status = to_status
    order.save(update_fields=["status", "updated_at"])
    OrderTransitionLog.objects.create(
        order=order,
        from_status=current_status,
        to_status=to_status,
        actor_user_id=actor_user_id,
        reason=reason,
    )
    return order
