from rest_framework import serializers

from orders.models import Order, OrderItem, PaymentInvoice


class PaymentInvoiceOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    variant_summary = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_name",
            "variant_summary",
            "quantity",
            "unit_price",
            "line_discount_amount",
            "line_total_amount",
        ]

    def get_variant_summary(self, obj: OrderItem) -> str:
        if not obj.variant:
            return ""
        attrs = [obj.variant.attribute_value_1, obj.variant.attribute_value_2]
        return " / ".join([value for value in attrs if value])


class PaymentInvoiceOrderSummarySerializer(serializers.ModelSerializer):
    items = PaymentInvoiceOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "subtotal_amount",
            "shipping_amount",
            "discount_amount",
            "total_amount",
            "currency",
            "items",
        ]


class PaymentInvoicePublicSerializer(serializers.ModelSerializer):
    order = PaymentInvoiceOrderSummarySerializer(read_only=True)

    class Meta:
        model = PaymentInvoice
        fields = [
            "token",
            "expires_at",
            "is_used",
            "order",
        ]


class PaymentInvoiceCodConfirmResponseSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    order_status = serializers.CharField()
    invoice_token = serializers.UUIDField()
