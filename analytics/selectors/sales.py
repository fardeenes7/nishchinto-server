from analytics.models import ShopSalesMetrics

def get_shop_sales_metrics(*, shop_id: str, start_date=None, end_date=None):
    """
    Fetches aggregated sales metrics for a shop from the materialized view.
    """
    queryset = ShopSalesMetrics.objects.filter(shop_id=shop_id)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    
    return queryset.order_by('date')
