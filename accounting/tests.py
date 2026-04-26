from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounting.models import LedgerEntry, Payout, PlatformBalance
from shops.models import Shop


class AdminSettlementApiTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.admin_user = user_model.objects.create_user(
			email='admin@example.com',
			password='password123',
			is_staff=True,
		)
		self.staffless_user = user_model.objects.create_user(
			email='user@example.com',
			password='password123',
			is_staff=False,
		)
		self.shop = Shop.objects.create(name='Settlement Shop', subdomain='settlement-shop')
		self.balance = PlatformBalance.objects.create(
			shop=self.shop,
			tenant_id=self.shop.id,
			current_balance=Decimal('0.00'),
			total_withdrawn=Decimal('100.00'),
		)
		self.payout = Payout.objects.create(
			shop=self.shop,
			tenant_id=self.shop.id,
			amount=Decimal('100.00'),
			status=Payout.STATUS_PENDING,
			bank_info={'channel': 'bkash'},
		)

		self.client = APIClient()

	def test_admin_can_list_settlements(self):
		self.client.force_authenticate(user=self.admin_user)
		response = self.client.get('/api/v1/accounting/admin/settlements/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]['status'], Payout.STATUS_PENDING)

	def test_non_admin_cannot_list_settlements(self):
		self.client.force_authenticate(user=self.staffless_user)
		response = self.client.get('/api/v1/accounting/admin/settlements/')
		self.assertEqual(response.status_code, 403)

	def test_admin_can_approve_pending_payout(self):
		self.client.force_authenticate(user=self.admin_user)
		response = self.client.post(
			f'/api/v1/accounting/admin/settlements/{self.payout.id}/approve/',
			{'admin_note': 'Approved for transfer.'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.payout.refresh_from_db()
		self.assertEqual(self.payout.status, Payout.STATUS_PROCESSING)
		self.assertEqual(self.payout.admin_note, 'Approved for transfer.')

	def test_admin_can_reject_pending_payout_and_restore_balance(self):
		self.client.force_authenticate(user=self.admin_user)
		response = self.client.post(
			f'/api/v1/accounting/admin/settlements/{self.payout.id}/reject/',
			{'admin_note': 'Bank details mismatch.'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)

		self.payout.refresh_from_db()
		self.balance.refresh_from_db()

		self.assertEqual(self.payout.status, Payout.STATUS_FAILED)
		self.assertEqual(self.payout.admin_note, 'Bank details mismatch.')
		self.assertEqual(self.balance.current_balance, Decimal('100.00'))
		self.assertEqual(self.balance.total_withdrawn, Decimal('0.00'))
		self.assertTrue(
			LedgerEntry.objects.filter(
				shop=self.shop,
				payout=self.payout,
				entry_type=LedgerEntry.ENTRY_TYPE_ADJUSTMENT,
			).exists()
		)
