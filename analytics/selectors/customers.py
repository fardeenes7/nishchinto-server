from analytics.models import CustomerLTV

def get_top_customers_by_ltv(*, tenant_id: str, limit=10):
    """
    Fetches top customers by lifetime value from the materialized view.
    """
    return CustomerLTV.objects.filter(tenant_id=tenant_id).order_by('-lifetime_value')[:limit]

def get_customer_ltv_stats(*, tenant_id: str, customer_profile_id: str):
    """
    Fetches LTV stats for a specific customer.
    """
    return CustomerLTV.objects.filter(
        tenant_id=tenant_id, 
        customer_profile_id=customer_profile_id
    ).first()
