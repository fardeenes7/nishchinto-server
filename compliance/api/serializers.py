from rest_framework import serializers

from catalog.models import InventoryLog
from compliance.models import AuditEvent
from notifications.models import NotificationDeliveryLog
from orders.models import OrderTransitionLog


class OrderTransitionLogSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(source="order.id", read_only=True)
    actor_user_id = serializers.UUIDField(source="actor_user.id", read_only=True, allow_null=True)

    class Meta:
        model = OrderTransitionLog
        fields = [
            "id",
            "order_id",
            "from_status",
            "to_status",
            "reason",
            "metadata",
            "actor_user_id",
            "created_at",
        ]


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDeliveryLog
        fields = [
            "id",
            "channel",
            "event_key",
            "recipient",
            "status",
            "error_message",
            "created_at",
        ]


class InventoryLogSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True, allow_null=True)

    class Meta:
        model = InventoryLog
        fields = [
            "id",
            "variant_id",
            "delta",
            "reason",
            "reference_id",
            "created_by_id",
            "created_at",
        ]


class AuditEventSerializer(serializers.ModelSerializer):
    actor_user_id = serializers.UUIDField(source="actor_user.id", read_only=True, allow_null=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "action",
            "resource_type",
            "resource_id",
            "metadata",
            "ip_address",
            "payload_signature",
            "actor_user_id",
            "created_at",
        ]
