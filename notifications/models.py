import uuid

from django.db import models

from core.models import TenantModel


class NotificationChannel(models.TextChoices):
    EMAIL = 'EMAIL', 'Email'
    WEBSOCKET = 'WEBSOCKET', 'Websocket'


class NotificationDeliveryStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    FAILED = 'FAILED', 'Failed'


class NotificationPreference(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='notification_preferences')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notification_preferences')
    event_key = models.CharField(max_length=120)
    email_enabled = models.BooleanField(default=True)
    websocket_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['shop', 'user', 'event_key'],
                condition=models.Q(deleted_at__isnull=True),
                name='uq_notif_pref_shop_user_event_active',
            )
        ]


class NotificationDeliveryLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='notification_delivery_logs')
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    event_key = models.CharField(max_length=120)
    recipient = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=NotificationDeliveryStatus.choices, default=NotificationDeliveryStatus.PENDING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['shop', 'status', 'created_at'], name='notiflog_shop_status_created_idx'),
        ]


class DeadLetterEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey('shops.Shop', on_delete=models.SET_NULL, null=True, blank=True, related_name='dead_letter_events')
    source = models.CharField(max_length=120)
    event_key = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
