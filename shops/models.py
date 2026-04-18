from django.db import models
import uuid
from core.models import SoftDeleteModel, TenantModel
from django.conf import settings

class Shop(SoftDeleteModel):
    """
    Core Application Tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    subdomain = models.CharField(max_length=100, unique=True, db_index=True)
    grace_period_until = models.DateTimeField(null=True, blank=True)
    
    # Custom Overrides (from Business Rules limits)
    override_max_products = models.IntegerField(null=True, blank=True)
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
