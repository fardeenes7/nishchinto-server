import hmac
from hashlib import sha256

from django.conf import settings

from webhooks.models import WebhookLog


def webhook_signature_valid(*, signature: str, body: bytes, app_secret: str | None = None) -> bool:
    if not signature:
        return False

    secret_value = app_secret or settings.META_APP_SECRET
    if not secret_value:
        return False

    secret = secret_value.encode('utf-8')
    expected = hmac.new(secret, msg=body, digestmod=sha256).hexdigest()
    normalized = signature.replace('sha256=', '')
    return hmac.compare_digest(expected, normalized)


def webhook_event_already_processed(*, provider: str, external_event_id: str) -> bool:
    return WebhookLog.objects.filter(provider=provider, external_event_id=external_event_id).exists()
