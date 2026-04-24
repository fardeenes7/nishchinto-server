from rest_framework import serializers
from shops.models import Shop
from shops.models import ShopMember, ShopSettings
from catalog.api.serializers import ShopTrackingConfigSerializer


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = [
            "id", "name", "subdomain", "base_currency",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "subdomain", "created_at", "updated_at"]


class ActiveShopContextSerializer(serializers.Serializer):
    shop = ShopSerializer()
    role = serializers.ChoiceField(choices=ShopMember.ROLE_CHOICES)


class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        fields = [
            "id", "stock_reservation_minutes", "allow_guest_checkout",
            "mandatory_advance_fee_bdt", "maintenance_mode",
            "show_stock_count", "enable_product_reviews",
            "tax_calculation_base", "discount_application",
            "messenger_greeting_keywords", "notification_targets",
        ]
        read_only_fields = ["id"]
