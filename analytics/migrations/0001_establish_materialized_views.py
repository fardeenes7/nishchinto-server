from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_order_payment_method'),
        ('shops', '0011_merge_0008_prepaid_and_0010_domain'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE MATERIALIZED VIEW analytics_shop_sales_metrics AS
                SELECT
                    shop_id as tenant_id,
                    shop_id,
                    DATE(created_at) as date,
                    COUNT(id) as total_orders,
                    SUM(total_amount) as total_revenue,
                    AVG(total_amount) as avg_order_value
                FROM orders_order
                WHERE status = 'DELIVERED'
                GROUP BY shop_id, DATE(created_at);

                CREATE UNIQUE INDEX analytics_shop_sales_metrics_uidx ON analytics_shop_sales_metrics (shop_id, date);

                CREATE MATERIALIZED VIEW analytics_customer_ltv AS
                SELECT
                    tenant_id,
                    customer_profile_id,
                    COUNT(id) as total_orders,
                    SUM(total_amount) as lifetime_value,
                    MAX(created_at) as last_purchase_date
                FROM orders_order
                WHERE status = 'DELIVERED'
                GROUP BY tenant_id, customer_profile_id;

                CREATE UNIQUE INDEX analytics_customer_ltv_uidx ON analytics_customer_ltv (tenant_id, customer_profile_id);

                CREATE MATERIALIZED VIEW analytics_cohort_data AS
                SELECT
                    tenant_id,
                    DATE_TRUNC('month', created_at) as cohort_month,
                    COUNT(id) as signup_count
                FROM shops_customerprofile
                GROUP BY tenant_id, DATE_TRUNC('month', created_at);

                CREATE UNIQUE INDEX analytics_cohort_data_uidx ON analytics_cohort_data (tenant_id, cohort_month);
            """,
            reverse_sql="""
                DROP MATERIALIZED VIEW IF EXISTS analytics_shop_sales_metrics;
                DROP MATERIALIZED VIEW IF EXISTS analytics_customer_ltv;
                DROP MATERIALIZED VIEW IF EXISTS analytics_cohort_data;
            """
        )
    ]
