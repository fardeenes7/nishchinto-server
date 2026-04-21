import uuid

from django.db import models


class WebhookProvider(models.TextChoices):
    META = 'META', 'Meta'
    BKASH = 'BKASH', 'bKash'
    COURIER = 'COURIER', 'Courier'


class WebhookProcessingStatus(models.TextChoices):
    PROCESSED = 'PROCESSED', 'Processed'
    DUPLICATE = 'DUPLICATE', 'Duplicate'
    FAILED = 'FAILED', 'Failed'
    REJECTED = 'REJECTED', 'Rejected'


class WebhookLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=WebhookProvider.choices)
    event_type = models.CharField(max_length=120, blank=True)
    external_event_id = models.CharField(max_length=255)
    dedupe_hash = models.CharField(max_length=255, blank=True)
    shop = models.ForeignKey('shops.Shop', on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    payload_fingerprint = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=WebhookProcessingStatus.choices, default=WebhookProcessingStatus.PROCESSED)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['provider', 'external_event_id'], name='webhook_provider_event_idx'),
            models.Index(fields=['shop', 'created_at'], name='webhook_shop_created_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['provider', 'external_event_id'], name='uq_webhook_provider_external_id'),
        ]
