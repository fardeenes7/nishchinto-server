from notifications.models import DeadLetterEvent


def dead_letter_events_unresolved(*, limit: int = 100):
    return DeadLetterEvent.objects.filter(resolved_at__isnull=True).order_by('-created_at')[:limit]
