from django.db import models
import uuid
from core.models import SoftDeleteModel, TenantModel
from django.conf import settings

class SubscriptionPlan(models.Model):
    """
    Defines the available tiers and their default limits.
    """
    TIER_CHOICES = (
        ('FREE', 'Free'),
        ('BASIC', 'Basic'),
        ('PRO', 'Pro'),
        ('BUSINESS', 'Business'),
    )
    name = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    max_products = models.IntegerField(default=5)
    max_staff = models.IntegerField(default=1)
    can_use_pos = models.BooleanField(default=False)
    can_use_api = models.BooleanField(default=False)
    
    def __str__(self):
        return self.get_name_display()

class Shop(SoftDeleteModel):
    """
    Core Application Tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    subdomain = models.CharField(max_length=100, unique=True, db_index=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='shops', null=True)
    grace_period_until = models.DateTimeField(null=True, blank=True)
    
    # Custom Overrides (from Business Rules limits)
    override_max_products = models.IntegerField(null=True, blank=True)
    override_max_staff = models.IntegerField(null=True, blank=True)
    is_billing_exempt = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class ShopMember(SoftDeleteModel):
    """
    Maps Users to Shops with Roles. Note: Does not inherit from TenantModel
    since it's a structural bridge, but it relates directly to the Tenant.
    """
    ROLE_CHOICES = (
        ('OWNER', 'Owner'),
        ('MANAGER', 'Manager'),
        ('CASHIER', 'Cashier'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shop_memberships')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CASHIER')
    
    class Meta:
        unique_together = ('user', 'shop')

    def __str__(self):
        return f"{self.user.email} - {self.shop.name} ({self.role})"

class CustomerProfile(TenantModel):
    """
    End-Buyer identity mapped per Shop.
    Inherits from TenantModel to enforce RLS visibility per shop.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    loyalty_points = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
