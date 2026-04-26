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
    PAYMENT_METHOD_COD = 'COD'
    PAYMENT_METHOD_PREPAID = 'PREPAID'
    PAYMENT_METHOD_CHOICES = (
        (PAYMENT_METHOD_COD, 'Cash on Delivery'),
        (PAYMENT_METHOD_PREPAID, 'Prepaid / Online'),
    )

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
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
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
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='payment_invoices')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            self.tenant_id = self.order.tenant_id
        if not self.shop_id:
            self.shop_id = self.order.shop_id
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
            models.Index(fields=['order', 'created_at'], name='ordtrans_order_created_idx'),
        ]


class OrderSplitMode(models.TextChoices):
    BACKORDER_SPLIT = 'BACKORDER_SPLIT', 'Backorder Split'
    ITEM_CANCEL = 'ITEM_CANCEL', 'Item Cancel'


class OrderSplitLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='split_links_as_parent')
    child_order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='split_links_as_child')
    split_mode = models.CharField(max_length=20, choices=OrderSplitMode.choices, default=OrderSplitMode.BACKORDER_SPLIT)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['parent_order', 'created_at'], name='ordsplit_parent_created_ix'),
            models.Index(fields=['child_order', 'created_at'], name='ordsplit_child_created_ix'),
        ]


class OrderRefundStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    COMPLETED = 'COMPLETED', 'Completed'


class OrderRefundEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='refund_events')
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='order_refund_events')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='BDT')
    status = models.CharField(max_length=20, choices=OrderRefundStatus.choices, default=OrderRefundStatus.REQUESTED)
    reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    actor_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_refund_events')
    inventory_reversed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['shop', 'order', 'created_at'], name='ordrefund_shop_ord_cr_idx'),
            models.Index(fields=['shop', 'status', 'created_at'], name='ordrefund_shop_st_cr_idx'),
        ]


class CourierProvider(models.TextChoices):
    PATHAO = 'PATHAO', 'Pathao'
    PAPERFLY = 'PAPERFLY', 'Paperfly'
    STEADFAST = 'STEADFAST', 'Steadfast'
    OTHER = 'OTHER', 'Other'


class CourierConsignmentStatus(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    DISPATCHED = 'DISPATCHED', 'Dispatched'
    IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
    DELIVERED = 'DELIVERED', 'Delivered'
    FAILED = 'FAILED', 'Failed'
    RTO = 'RTO', 'Return To Origin'


class CourierConsignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='consignments')
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='courier_consignments')
    provider = models.CharField(max_length=20, choices=CourierProvider.choices, default=CourierProvider.OTHER)
    external_consignment_id = models.CharField(max_length=120)
    tracking_code = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=CourierConsignmentStatus.choices, default=CourierConsignmentStatus.CREATED)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['shop', 'status', 'created_at'], name='courier_shop_stat_cr_ix'),
            models.Index(fields=['provider', 'external_consignment_id'], name='courier_prov_ext_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['provider', 'external_consignment_id'], name='uq_courier_provider_extid'),
        ]
