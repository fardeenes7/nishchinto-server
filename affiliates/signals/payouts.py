from django.db.models.signals import post_save
from django.dispatch import receiver
from billing.models import PaymentTransaction
from affiliates.models import Referral
from django.db import transaction
from decimal import Decimal

@receiver(post_save, sender=PaymentTransaction)
def handle_referral_payout(sender, instance, created, **kwargs):
    """
    When a payment is completed, check if the shop was referred.
    If so, verify the referral and apply rewards.
    """
    # Only process completed transactions for subscription or topups
    if instance.status == PaymentTransaction.STATUS_COMPLETED:
        # Check if this shop was referred
        try:
            referral = Referral.objects.select_related('referrer_shop', 'referred_shop').get(
                referred_shop=instance.shop,
                status='PENDING'
            )
            
            with transaction.atomic():
                # 1. Verify referral
                referral.status = 'VERIFIED'
                
                # Reward logic: 500 BDT in AI credits as a thank you
                reward = Decimal('500.00')
                referral.reward_amount = reward
                
                # 2. Inject credits into referrer shop's balance
                from shops.models import ShopSettings
                shop_settings, _ = ShopSettings.objects.get_or_create(shop=referral.referrer_shop)
                
                # Use Decimal for financial fields
                shop_settings.ai_credit_balance += reward
                shop_settings.save()
                
                referral.reward_applied = True
                referral.save()
                
        except Referral.DoesNotExist:
            pass
