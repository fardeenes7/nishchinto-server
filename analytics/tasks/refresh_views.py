from celery import shared_task
from django.db import connection

@shared_task(queue='default')
def refresh_analytics_materialized_views():
    """
    Refreshes materialized views concurrently to avoid locking readers.
    Requires a unique index on the materialized view (which we have).
    """
    with connection.cursor() as cursor:
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_shop_sales_metrics;")
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_customer_ltv;")
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_cohort_data;")
