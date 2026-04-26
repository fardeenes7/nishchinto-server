from rest_framework import serializers

from accounting.models import Payout, PlatformBalance, LedgerEntry, PurchaseOrder




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


class MerchantBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformBalance
        fields = [
            'current_balance',
            'total_withdrawn',
            'pending_payouts',
            'updated_at',
        ]


class MerchantPayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            'id',
            'amount',
            'status',
            'bank_info',
            'admin_note',
            'paid_at',
            'created_at',
        ]


class MerchantLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = [
            'id',
            'entry_type',
            'amount',
            'description',
            'created_at',
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = [
            'id',
            'supplier_name',
            'total_amount',
            'auxiliary_costs',
            'status',
            'items_json',
            'received_at',
            'created_at',
        ]


class PayoutRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    bank_info = serializers.JSONField()


