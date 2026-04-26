from rest_framework import serializers
from .models import WaitlistEntry, SocialConnection, ProductSocialPostLog, MetaAdAccount

class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = ('id', 'email', 'phone_number', 'survey_data', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')


class MetaAdAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaAdAccount
        fields = ["id", "account_id", "name", "currency", "is_active"]


class SocialConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialConnection
        fields = (
            "id",
            "provider",
            "page_id",
            "page_name",
            "status",
            "token_expires_at",
            "last_refreshed_at",
            "last_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SocialConnectionCreateSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["META"], default="META")
    page_id = serializers.CharField(max_length=100)
    page_name = serializers.CharField(max_length=255)
    access_token = serializers.CharField()
    expires_in = serializers.IntegerField(required=False, min_value=0)


class SocialOAuthCallbackSerializer(serializers.Serializer):
    code = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    oauth_state = serializers.CharField(required=False, allow_blank=True)
    selected_page_id = serializers.CharField(required=False, allow_blank=True)


class SocialOAuthPageSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class SocialPublishRequestSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    connection_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(max_length=120, required=False, allow_blank=True)


class SocialBulkPublishRequestSerializer(serializers.Serializer):
    product_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    connection_id = serializers.UUIDField()


class ProductSocialPostLogSerializer(serializers.ModelSerializer):
    connection_page_name = serializers.CharField(source="connection.page_name", read_only=True)

    class Meta:
        model = ProductSocialPostLog
        fields = (
            "id",
            "product",
            "connection",
            "connection_page_name",
            "idempotency_key",
            "status",
            "retry_count",
            "external_post_id",
            "error_message",
            "published_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
