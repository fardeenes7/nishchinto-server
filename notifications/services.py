from notifications.models import DeadLetterEvent, NotificationDeliveryLog


def notification_delivery_log_create(*, shop_id: str, channel: str, event_key: str, recipient: str, payload: dict):
    return NotificationDeliveryLog.objects.create(
        shop_id=shop_id,
        channel=channel,
        event_key=event_key,
        recipient=recipient,
        payload=payload,
    )


def dead_letter_event_create(*, source: str, event_key: str, payload: dict, error_message: str, shop_id: str | None = None):
    return DeadLetterEvent.objects.create(
        shop_id=shop_id,
        source=source,
        event_key=event_key,
        payload=payload,
        error_message=error_message,
    )
