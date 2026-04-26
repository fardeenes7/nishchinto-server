from django.db import models
from core.models import TenantModel
import uuid

class FraudConfig(TenantModel):
    """
    Per-shop configuration for fraud detection and risk thresholds.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.OneToOneField('shops.Shop', on_delete=models.CASCADE, related_name='fraud_config')
    
    opt_in_pooling = models.BooleanField(default=True, help_text="Contribute to and benefit from the global fraud pool.")
    block_high_risk = models.BooleanField(default=False, help_text="Automatically block orders from high-risk numbers.")
    warn_on_rto = models.BooleanField(default=True, help_text="Show warning in dashboard for customers with RTO history.")
    
    rto_threshold = models.PositiveIntegerField(default=2, help_text="Number of RTOs before a customer is flagged as high-risk.")

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            self.tenant_id = self.shop_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Fraud Config for {self.shop_id}"
