import hmac
from hashlib import sha256

from django.conf import settings
from django.db import IntegrityError

from webhooks.models import WebhookLog, WebhookProcessingStatus


def _normalize_signature(signature: str) -> str:
    return signature.strip().replace('sha256=', '')


def _payload_fingerprint(body: bytes) -> str:
    return sha256(body).hexdigest()


def webhook_signature_valid(*, signature: str, body: bytes, app_secret: str | None = None) -> bool:
    if not signature:
        return False

    secret_value = app_secret or settings.META_APP_SECRET
    if not secret_value:
        return False

    secret = secret_value.encode('utf-8')
    expected = hmac.new(secret, msg=body, digestmod=sha256).hexdigest()
    normalized = _normalize_signature(signature)
    return hmac.compare_digest(expected, normalized)


def webhook_event_already_processed(*, provider: str, external_event_id: str) -> bool:
    return WebhookLog.objects.filter(provider=provider, external_event_id=external_event_id).exists()


def webhook_log_event(
    *,
    provider: str,
    external_event_id: str,
    event_type: str = '',
    body: bytes = b'',
    shop_id: str | None = None,
    status: str = WebhookProcessingStatus.PROCESSED,
    error_message: str = '',
) -> tuple[WebhookLog, bool]:
    defaults = {
        'event_type': event_type,
        'shop_id': shop_id,
        'payload_fingerprint': _payload_fingerprint(body),
        'dedupe_hash': f"{provider}:{external_event_id}",
        'status': status,
        'error_message': error_message,
    }

    try:
        log, created = WebhookLog.objects.get_or_create(
            provider=provider,
            external_event_id=external_event_id,
            defaults=defaults,
        )
    except IntegrityError:
        log = WebhookLog.objects.get(provider=provider, external_event_id=external_event_id)
        created = False

    if not created and log.status != WebhookProcessingStatus.DUPLICATE:
        log.status = WebhookProcessingStatus.DUPLICATE
        log.error_message = error_message
        log.save(update_fields=['status', 'error_message'])

    return log, created
