from django.db import models
from core.models import TenantModel

class ShopSalesMetrics(models.Model):
    # This model represents a materialized view
    tenant_id = models.UUIDField()
    shop = models.ForeignKey('shops.Shop', on_delete=models.DO_NOTHING, related_name='+')
    date = models.DateField()
    total_orders = models.IntegerField()
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    avg_order_value = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'analytics_shop_sales_metrics'
        indexes = [
            models.Index(fields=['shop', 'date']),
        ]

class CustomerLTV(models.Model):
    # This model represents a materialized view
    tenant_id = models.UUIDField()
    customer_profile = models.ForeignKey('shops.CustomerProfile', on_delete=models.DO_NOTHING, related_name='+')
    total_orders = models.IntegerField()
    lifetime_value = models.DecimalField(max_digits=12, decimal_places=2)
    last_purchase_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'analytics_customer_ltv'
        indexes = [
            models.Index(fields=['tenant_id', 'customer_profile']),
        ]

class CohortData(models.Model):
    # This model represents a materialized view
    tenant_id = models.UUIDField()
    cohort_month = models.DateField()
    signup_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'analytics_cohort_data'
        indexes = [
            models.Index(fields=['tenant_id', 'cohort_month']),
        ]
