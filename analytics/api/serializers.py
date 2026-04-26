from rest_framework import serializers
from analytics.models import ShopSalesMetrics, CustomerLTV, CohortData

class ShopSalesMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSalesMetrics
        fields = ['date', 'total_orders', 'total_revenue', 'avg_order_value']

class CustomerLTVSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer_profile.name', read_only=True)
    customer_phone = serializers.CharField(source='customer_profile.phone_number', read_only=True)

    class Meta:
        model = CustomerLTV
        fields = ['customer_name', 'customer_phone', 'total_orders', 'lifetime_value', 'last_purchase_date']

class CohortDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CohortData
        fields = ['cohort_month', 'signup_count']
