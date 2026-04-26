from analytics.models import CohortData

def get_cohort_retention_data(*, tenant_id: str):
    """
    Fetches cohort data from the materialized view.
    Note: Real cohort analysis usually involves joining with order data 
    to see how many users from a signup month bought in subsequent months.
    This view currently only tracks signups per month.
    """
    return CohortData.objects.filter(tenant_id=tenant_id).order_by('cohort_month')
