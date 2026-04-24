from celery import shared_task
from billing.services.subscription import sweep_expired_grace_periods

@shared_task(name='billing.tasks.subscription.sweep_grace_periods')
def sweep_grace_periods_task():
    """
    Periodic task to sweep shops that have exceeded their grace period.
    """
    count = sweep_expired_grace_periods()
    return f"Suspended {count} shops with expired grace periods."
