from rest_framework import serializers

from accounting.models import Payout


class AdminPayoutSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source='shop.name', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id',
            'shop',
            'shop_name',
            'amount',
            'status',
            'bank_info',
            'admin_note',
            'paid_at',
            'created_at',
            'updated_at',
        ]


class AdminPayoutActionSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True, default='')
