from rest_framework import serializers
from shops.models import Shop
from shops.models import ShopMember


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
