from django.db import models
from core.models import SoftDeleteModel
import uuid

class Referral(SoftDeleteModel):
    """
    Tracks a successful shop signup driven by another shop.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer_shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='referrals_sent')
    referred_shop = models.OneToOneField('shops.Shop', on_delete=models.CASCADE, related_name='referral_info')
    
    # Status of the referral (e.g., PENDING, VERIFIED, REJECTED)
    status = models.CharField(max_length=20, default='PENDING')
    
    # Credits or amount earned by the referrer
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reward_applied = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer_shop.name} -> {self.referred_shop.name}"
