from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from catalog.models import InventoryLog
from catalog.models import Product, ProductVariant
from compliance.models import AuditEvent
from orders.models import OrderRefundEvent, OrderStatus
from orders.services.checkout import checkout_create_order
from orders.services.invoices import (
    PaymentInvoiceGoneError,
    payment_invoice_consume,
    payment_invoice_create,
)
from orders.services.partial_fulfillment import (
    OptimisticLockError,
    PartialFulfillmentError,
    partial_inventory_reversal_apply,
    partial_fulfillment_cancel_items,
    partial_fulfillment_split_order,
    partial_refund_create,
)
from orders.services.transitions import order_transition
from shops.models import Shop


class OrderCheckoutServiceTests(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Demo Shop", subdomain="demo-shop")
        self.product = Product.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            name="T-Shirt",
            slug="t-shirt",
            description="",
            status="PUBLISHED",
            base_price=Decimal("250.00"),
            compare_at_price=None,
            tax_rate=Decimal("0.0000"),
            sku="",
            is_digital=False,
            specifications={},
            seo_title="",
            seo_description="",
            sort_order=1,
        )
        self.variant = ProductVariant.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            product=self.product,
            sku="TSHIRT-RED-M",
            attribute_name_1="Color",
            attribute_value_1="Red",
            attribute_name_2="Size",
            attribute_value_2="M",
            stock_quantity=5,
            is_active=True,
        )

    def test_checkout_create_order_locks_price_and_records_items(self):
        order = checkout_create_order(
            shop_id=str(self.shop.id),
            items=[
                {
                    "product_id": str(self.product.id),
                    "variant_id": str(self.variant.id),
                    "quantity": 2,
                }
            ],
        )

        self.assertEqual(order.status, OrderStatus.AWAITING_PAYMENT)
        self.assertEqual(order.subtotal_amount, Decimal("500.00"))
        self.assertEqual(order.total_amount, Decimal("500.00"))
        self.assertIsNotNone(order.lock_expires_at)
        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.unit_price, Decimal("250.00"))
        self.assertEqual(item.line_total_amount, Decimal("500.00"))

    def test_checkout_create_order_rejects_insufficient_stock(self):
        with self.assertRaises(ValueError):
            checkout_create_order(
                shop_id=str(self.shop.id),
                items=[
                    {
                        "product_id": str(self.product.id),
                        "variant_id": str(self.variant.id),
                        "quantity": 6,
                    }
                ],
            )


class PaymentInvoiceServiceTests(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Demo Shop", subdomain="demo-shop")
        self.product = Product.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            name="Mug",
            slug="mug",
            description="",
            status="PUBLISHED",
            base_price=Decimal("120.00"),
            compare_at_price=None,
            tax_rate=Decimal("0.0000"),
            sku="",
            is_digital=False,
            specifications={},
            seo_title="",
            seo_description="",
            sort_order=1,
        )
        self.variant = ProductVariant.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            product=self.product,
            sku="MUG-WHT",
            attribute_name_1="Color",
            attribute_value_1="White",
            attribute_name_2="",
            attribute_value_2="",
            stock_quantity=3,
            is_active=True,
        )
        self.order = checkout_create_order(
            shop_id=str(self.shop.id),
            items=[
                {
                    "product_id": str(self.product.id),
                    "variant_id": str(self.variant.id),
                    "quantity": 1,
                }
            ],
        )

    def test_payment_invoice_create_and_consume(self):
        invoice = payment_invoice_create(order=self.order)

        self.assertFalse(invoice.is_used)
        self.assertGreater(invoice.expires_at, timezone.now())

        consumed = payment_invoice_consume(token=str(invoice.token), shop_id=str(self.shop.id))
        self.assertTrue(consumed.is_used)
        self.assertIsNotNone(consumed.used_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="PAYMENT_INVOICE_CONSUMED",
                resource_type="orders.PaymentInvoice",
                resource_id=str(invoice.id),
            ).exists()
        )

    def test_payment_invoice_consume_cannot_reuse(self):
        invoice = payment_invoice_create(order=self.order)
        payment_invoice_consume(token=str(invoice.token), shop_id=str(self.shop.id))

        with self.assertRaises(PaymentInvoiceGoneError):
            payment_invoice_consume(token=str(invoice.token), shop_id=str(self.shop.id))


class OrderTransitionServiceTests(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Transition Shop", subdomain="transition-shop")
        self.product = Product.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            name="Bottle",
            slug="bottle",
            description="",
            status="PUBLISHED",
            base_price=Decimal("80.00"),
            compare_at_price=None,
            tax_rate=Decimal("0.0000"),
            sku="",
            is_digital=False,
            specifications={},
            seo_title="",
            seo_description="",
            sort_order=1,
        )
        self.variant = ProductVariant.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            product=self.product,
            sku="BOT-1",
            attribute_name_1="Size",
            attribute_value_1="M",
            attribute_name_2="",
            attribute_value_2="",
            stock_quantity=10,
            is_active=True,
        )
        self.order = checkout_create_order(
            shop_id=str(self.shop.id),
            items=[
                {
                    "product_id": str(self.product.id),
                    "variant_id": str(self.variant.id),
                    "quantity": 1,
                }
            ],
        )

    def test_transition_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            order_transition(order=self.order, to_status="INVALID_STATUS")

    def test_transition_restricts_cashier_refund(self):
        self.order.status = OrderStatus.DELIVERED
        self.order.save(update_fields=["status", "updated_at"])

        with self.assertRaises(PermissionDenied):
            order_transition(order=self.order, to_status=OrderStatus.REFUNDED, actor_role="CASHIER")

    def test_transition_allows_manager_refund(self):
        self.order.status = OrderStatus.DELIVERED
        self.order.save(update_fields=["status", "updated_at"])

        updated = order_transition(order=self.order, to_status=OrderStatus.REFUNDED, actor_role="MANAGER")
        self.assertEqual(updated.status, OrderStatus.REFUNDED)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="ORDER_STATUS_TRANSITION",
                resource_type="orders.Order",
                resource_id=str(self.order.id),
            ).exists()
        )


class PartialFulfillmentServiceTests(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Split Shop", subdomain="split-shop")
        self.product = Product.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            name="Shoes",
            slug="shoes",
            description="",
            status="PUBLISHED",
            base_price=Decimal("100.00"),
            compare_at_price=None,
            tax_rate=Decimal("0.0000"),
            sku="",
            is_digital=False,
            specifications={},
            seo_title="",
            seo_description="",
            sort_order=1,
        )
        self.variant = ProductVariant.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            product=self.product,
            sku="SHOE-1",
            attribute_name_1="Size",
            attribute_value_1="42",
            attribute_name_2="",
            attribute_value_2="",
            stock_quantity=20,
            is_active=True,
        )
        self.order = checkout_create_order(
            shop_id=str(self.shop.id),
            items=[
                {"product_id": str(self.product.id), "variant_id": str(self.variant.id), "quantity": 1},
                {"product_id": str(self.product.id), "variant_id": str(self.variant.id), "quantity": 1},
            ],
        )
        order_transition(order=self.order, to_status=OrderStatus.CONFIRMED)

    def test_partial_fulfillment_split_creates_child_order(self):
        first_item = self.order.items.order_by("created_at").first()
        result = partial_fulfillment_split_order(
            order_id=str(self.order.id),
            unavailable_item_ids=[str(first_item.id)],
            last_updated_at=self.order.updated_at,
            actor_role="MANAGER",
        )

        self.order.refresh_from_db()
        self.assertIsNotNone(result.child_order_id)
        self.assertEqual(result.remaining_items, 1)
        self.assertEqual(self.order.items.count(), 1)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="ORDER_PARTIAL_FULFILLMENT_SPLIT",
                resource_id=str(self.order.id),
            ).exists()
        )

    def test_partial_fulfillment_cancel_returns_refund_amount(self):
        first_item = self.order.items.order_by("created_at").first()
        result = partial_fulfillment_cancel_items(
            order_id=str(self.order.id),
            cancelled_item_ids=[str(first_item.id)],
            last_updated_at=self.order.updated_at,
            actor_role="MANAGER",
        )

        self.order.refresh_from_db()
        self.assertEqual(result.refund_amount, Decimal("100.00"))
        self.assertEqual(self.order.items.count(), 1)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="ORDER_PARTIAL_FULFILLMENT_CANCEL",
                resource_id=str(self.order.id),
            ).exists()
        )

    def test_partial_fulfillment_optimistic_lock_conflict(self):
        first_item = self.order.items.order_by("created_at").first()
        stale_time = self.order.updated_at - timedelta(seconds=2)

        with self.assertRaises(OptimisticLockError):
            partial_fulfillment_split_order(
                order_id=str(self.order.id),
                unavailable_item_ids=[str(first_item.id)],
                last_updated_at=stale_time,
                actor_role="MANAGER",
            )

    def test_partial_refund_create_records_event_and_audit(self):
        first_item = self.order.items.order_by("created_at").first()

        result = partial_refund_create(
            order_id=str(self.order.id),
            refund_items=[{"order_item_id": str(first_item.id), "quantity": 1}],
            actor_role="MANAGER",
            reason="Customer requested return",
        )

        event = OrderRefundEvent.objects.get(id=result.refund_event_id)
        self.assertEqual(result.refund_amount, Decimal("100.00"))
        self.assertEqual(event.amount, Decimal("100.00"))
        self.assertEqual(event.status, "REQUESTED")
        self.assertTrue(
            AuditEvent.objects.filter(
                action="ORDER_PARTIAL_REFUND_CREATED",
                resource_type="orders.OrderRefundEvent",
                resource_id=str(event.id),
            ).exists()
        )

    def test_partial_inventory_reversal_updates_stock_and_logs(self):
        first_item = self.order.items.order_by("created_at").first()
        refund = partial_refund_create(
            order_id=str(self.order.id),
            refund_items=[{"order_item_id": str(first_item.id), "quantity": 1}],
            actor_role="MANAGER",
        )

        self.variant.refresh_from_db()
        before_stock = self.variant.stock_quantity
        result = partial_inventory_reversal_apply(
            refund_event_id=refund.refund_event_id,
            reversal_items=[{"order_item_id": str(first_item.id), "quantity": 1}],
            actor_role="MANAGER",
        )

        self.variant.refresh_from_db()
        event = OrderRefundEvent.objects.get(id=refund.refund_event_id)
        self.assertEqual(result.reversed_quantity, 1)
        self.assertEqual(result.remaining_quantity, 0)
        self.assertEqual(self.variant.stock_quantity, before_stock + 1)
        self.assertEqual(event.status, "COMPLETED")
        self.assertEqual(
            InventoryLog.objects.filter(reference_id=str(event.id), reason=InventoryLog.Reason.RETURN).count(),
            1,
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="ORDER_PARTIAL_INVENTORY_REVERSED",
                resource_type="orders.OrderRefundEvent",
                resource_id=str(event.id),
            ).exists()
        )

    def test_partial_inventory_reversal_rejects_over_reversal(self):
        first_item = self.order.items.order_by("created_at").first()
        refund = partial_refund_create(
            order_id=str(self.order.id),
            refund_items=[{"order_item_id": str(first_item.id), "quantity": 1}],
            actor_role="MANAGER",
        )
        partial_inventory_reversal_apply(
            refund_event_id=refund.refund_event_id,
            reversal_items=[{"order_item_id": str(first_item.id), "quantity": 1}],
            actor_role="MANAGER",
        )

        with self.assertRaises(PartialFulfillmentError):
            partial_inventory_reversal_apply(
                refund_event_id=refund.refund_event_id,
                reversal_items=[{"order_item_id": str(first_item.id), "quantity": 1}],
                actor_role="MANAGER",
            )

    def test_partial_refund_rejects_cashier_role(self):
        first_item = self.order.items.order_by("created_at").first()

        with self.assertRaises(PermissionDenied):
            partial_refund_create(
                order_id=str(self.order.id),
                refund_items=[{"order_item_id": str(first_item.id), "quantity": 1}],
                actor_role="CASHIER",
            )
