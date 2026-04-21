import uuid

from django.db import models


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey('shops.Shop', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events')
    actor_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events')
    action = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=120)
    resource_id = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    payload_signature = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['shop', 'created_at'], name='auditevent_shop_created_idx'),
            models.Index(fields=['action', 'created_at'], name='auditevent_action_created_idx'),
        ]
