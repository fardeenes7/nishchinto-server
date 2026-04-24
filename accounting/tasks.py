from celery import shared_task
from accounting.services.settlement import SettlementService

@shared_task(name='accounting.tasks.sweep_matured_funds')
def sweep_matured_funds_task():
    """
    Moves pending funds to current balance after the 7-day hold period.
    """
    count = SettlementService.sweep_matured_funds()
    return f"Settled {count} matured income entries."
