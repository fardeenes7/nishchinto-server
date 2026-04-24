from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from catalog.models import InventoryLog
from catalog.models import Product
from catalog.models import ProductVariant
from compliance.models import AuditEvent
from compliance.services import hard_delete_account
from media.models import Media
from notifications.models import NotificationChannel, NotificationDeliveryLog, NotificationDeliveryStatus
from orders.models import Order
from orders.services.transitions import order_transition
from shops.models import CustomerProfile, Shop, ShopMember
from rest_framework.test import APIClient
from users.models import User


class HardDeleteAccountServiceTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="secret123",
            is_staff=True,
        )
        self.target_user = User.objects.create_user(
            email="owner@example.com",
            password="secret123",
            first_name="Owner",
            last_name="User",
        )
        self.shop = Shop.objects.create(name="Owner Shop", subdomain="owner-shop")
        ShopMember.objects.create(user=self.target_user, shop=self.shop, role="OWNER")

        self.customer = CustomerProfile.objects.create(
            tenant_id=self.shop.id,
            name="Customer Name",
            phone_number="01700111222",
        )
        self.order = Order.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            customer_profile=self.customer,
            status="CONFIRMED",
            subtotal_amount=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            currency="BDT",
        )
        self.product = Product.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            name="Sample",
            slug="sample",
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
        self.media = Media.objects.create(
            shop=self.shop,
            uploaded_by=self.target_user,
            original_filename="photo.jpg",
            s3_key="media/test/photo.jpg",
            cdn_url="",
            md5_hash="",
            mime_type="image/jpeg",
        )

    def test_hard_delete_account_anonymizes_and_audits(self):
        hard_delete_account(user_id=str(self.target_user.id), actor_admin_id=str(self.admin_user.id))

        self.target_user.refresh_from_db()
        self.customer.refresh_from_db()
        self.order.refresh_from_db()
        self.media.refresh_from_db()

        self.assertTrue(self.target_user.email.endswith("@deleted.local"))
        self.assertEqual(self.target_user.first_name, "")
        self.assertEqual(self.target_user.last_name, "")
        self.assertFalse(self.target_user.is_active)
        self.assertIsNotNone(self.target_user.deleted_at)

        self.assertEqual(self.customer.name, "")
        self.assertTrue(self.customer.phone_number.startswith("anon-"))
        self.assertIsNone(self.order.customer_profile)
        self.assertIsNotNone(self.media.deleted_at)

        self.assertTrue(
            AuditEvent.objects.filter(
                actor_user=self.admin_user,
                action="HARD_DELETE_ACCOUNT",
                resource_type="users.User",
                resource_id=str(self.target_user.id),
            ).exists()
        )

    def test_hard_delete_requires_internal_admin(self):
        non_admin = User.objects.create_user(email="user@example.com", password="secret123")

        with self.assertRaises(PermissionDenied):
            hard_delete_account(user_id=str(self.target_user.id), actor_admin_id=str(non_admin.id))


class ComplianceLogsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="owner-logs@example.com", password="secret123")
        self.cashier = User.objects.create_user(email="cashier-logs@example.com", password="secret123")

        self.shop = Shop.objects.create(name="Logs Shop", subdomain="logs-shop")
        ShopMember.objects.create(user=self.owner, shop=self.shop, role="OWNER")
        ShopMember.objects.create(user=self.cashier, shop=self.shop, role="CASHIER")

        self.customer = CustomerProfile.objects.create(
            tenant_id=self.shop.id,
            name="Buyer",
            phone_number="01710000000",
        )
        self.order = Order.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            customer_profile=self.customer,
            status="CONFIRMED",
            subtotal_amount=Decimal("120.00"),
            total_amount=Decimal("120.00"),
            currency="BDT",
        )
        order_transition(order=self.order, to_status="PROCESSING", actor_user_id=str(self.owner.id), actor_role="OWNER")

        self.product = Product.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            name="Cap",
            slug="cap",
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
            sku="CAP-RED",
            attribute_name_1="Color",
            attribute_value_1="Red",
            attribute_name_2="",
            attribute_value_2="",
            stock_quantity=5,
            is_active=True,
        )

        InventoryLog.objects.create(
            shop=self.shop,
            variant=self.variant,
            delta=-1,
            reason=InventoryLog.Reason.SALE,
            reference_id=str(self.order.id),
            created_by=self.owner,
        )
        NotificationDeliveryLog.objects.create(
            shop=self.shop,
            channel=NotificationChannel.EMAIL,
            event_key="order.confirmed",
            recipient="buyer@example.com",
            status=NotificationDeliveryStatus.SENT,
            payload={"order_id": str(self.order.id)},
        )
        AuditEvent.objects.create(
            shop=self.shop,
            actor_user=self.owner,
            action="ORDER_STATUS_CHANGE",
            resource_type="orders.Order",
            resource_id=str(self.order.id),
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_owner_can_fetch_all_log_endpoints(self):
        self._auth(self.owner)
        headers = {"HTTP_X_TENANT_ID": str(self.shop.id)}

        order_resp = self.client.get("/api/v1/compliance/logs/orders/", **headers)
        message_resp = self.client.get("/api/v1/compliance/logs/messages/", **headers)
        inventory_resp = self.client.get("/api/v1/compliance/logs/inventory/", **headers)
        audit_resp = self.client.get("/api/v1/compliance/logs/audit/", **headers)

        self.assertEqual(order_resp.status_code, 200)
        self.assertEqual(message_resp.status_code, 200)
        self.assertEqual(inventory_resp.status_code, 200)
        self.assertEqual(audit_resp.status_code, 200)

        self.assertGreaterEqual(order_resp.json()["count"], 1)
        self.assertGreaterEqual(message_resp.json()["count"], 1)
        self.assertGreaterEqual(inventory_resp.json()["count"], 1)
        self.assertGreaterEqual(audit_resp.json()["count"], 1)

    def test_cashier_is_forbidden_from_logs(self):
        self._auth(self.cashier)
        response = self.client.get("/api/v1/compliance/logs/orders/", HTTP_X_TENANT_ID=str(self.shop.id))
        self.assertEqual(response.status_code, 403)

    def test_missing_tenant_header_is_forbidden(self):
        self._auth(self.owner)
        response = self.client.get("/api/v1/compliance/logs/orders/")
        self.assertEqual(response.status_code, 403)
