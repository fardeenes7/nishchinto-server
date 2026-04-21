import uuid

from django.db import models

from core.models import TenantModel


class OrderStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    AWAITING_PAYMENT = 'AWAITING_PAYMENT', 'Awaiting Payment'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    PROCESSING = 'PROCESSING', 'Processing'
    SHIPPED = 'SHIPPED', 'Shipped'
    IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
    DELIVERED = 'DELIVERED', 'Delivered'
    CANCELLED = 'CANCELLED', 'Cancelled'
    REFUNDED = 'REFUNDED', 'Refunded'
    RTO_RETURNED = 'RTO_RETURNED', 'RTO Returned'
    ON_HOLD = 'ON_HOLD', 'On Hold'


class Order(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='orders')
    customer_profile = models.ForeignKey(
        'shops.CustomerProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    status = models.CharField(max_length=30, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='BDT')
    lock_expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            self.tenant_id = self.shop_id
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['shop', 'status', 'created_at'], name='order_shop_status_created_idx'),
        ]


class OrderItem(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='order_items')
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.PROTECT,
        related_name='order_items',
        null=True,
        blank=True,
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            self.tenant_id = self.order.tenant_id
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['order', 'created_at'], name='orderitem_order_created_idx'),
        ]


class PaymentInvoice(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payment_invoices')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            self.tenant_id = self.order.tenant_id
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['shop', 'expires_at', 'is_used'], name='invoice_shop_expiry_used_idx'),
        ]


class OrderTransitionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='transitions')
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    actor_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['order', 'created_at'], name='ordertransition_order_created_idx'),
        ]
