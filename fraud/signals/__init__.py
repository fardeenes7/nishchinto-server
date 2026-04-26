from django.db.models.signals import post_save
from django.dispatch import receiver
from fraud.models import FraudReport, GlobalFraudPool, FraudConfig
from django.db import transaction

@receiver(post_save, sender=FraudReport)
def sync_fraud_to_global_pool(sender, instance, created, **kwargs):
    """
    Update the global (non-tenant) fraud pool when a merchant reports fraud.
    Only syncs if the shop has opted-in to pooling.
    """
    if created:
        config, _ = FraudConfig.objects.get_or_create(shop=instance.shop)
        if not config.opt_in_pooling:
            return

        with transaction.atomic():
            pool, _ = GlobalFraudPool.objects.get_or_create(phone_hash=instance.phone_hash)
            
            if instance.reason == 'RTO':
                pool.rto_count += 1
            elif instance.reason == 'FAKE_ORDER':
                pool.fake_order_count += 1
            elif instance.reason == 'HARASSMENT':
                pool.harassment_count += 1
            elif instance.reason == 'UNPAID':
                pool.unpaid_count += 1
                
            pool.save()
