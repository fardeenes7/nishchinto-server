"""
accounting/services/settlement.py

Service for platform balance management, deductions, and payouts.
Implements the T+7 holding period rule.
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from accounting.models import PlatformBalance, LedgerEntry, Payout
from shops.models import Shop

logger = logging.getLogger(__name__)

class SettlementService:
    """
    Handles merchant funds and platform markups.
    """

    def __init__(self, shop_id):
        self.shop_id = shop_id
        self.balance, _ = PlatformBalance.objects.get_or_create(
            shop_id=shop_id,
            defaults={'tenant_id': shop_id}
        )

    def record_order_income(self, order, amount: Decimal):
        """
        Records income from a completed order.
        Amount is placed in 'pending_balance' for T+7 days.
        """
        with transaction.atomic():
            # Update balance
            self.balance.pending_balance = F('pending_balance') + amount
            self.balance.total_earned = F('total_earned') + amount
            self.balance.save()

            # Create LedgerEntry
            LedgerEntry.objects.create(
                shop_id=self.shop_id,
                tenant_id=self.shop_id,
                entry_type=LedgerEntry.ENTRY_TYPE_INCOME,
                amount=amount,
                description=f"Order income: {order.id}",
                order=order
            )

    def deduct_platform_fees(self, amount: Decimal, description: str, order=None):
        """
        Deducts platform fees (shipping, markups, etc.) from current balance.
        If current balance is insufficient, it can go negative or we block.
        For COD, we often deduct shipping from the merchant's balance.
        """
        with transaction.atomic():
            self.balance.current_balance = F('current_balance') - amount
            self.balance.save()

            LedgerEntry.objects.create(
                shop_id=self.shop_id,
                tenant_id=self.shop_id,
                entry_type=LedgerEntry.ENTRY_TYPE_EXPENSE,
                amount=amount,
                description=description,
                order=order
            )

    def process_payout_request(self, amount: Decimal, bank_info: dict):
        """
        Merchant requests a payout from their current_balance.
        """
        self.balance.refresh_from_db()
        if amount > self.balance.current_balance:
            raise ValueError("Insufficient balance for payout.")

        with transaction.atomic():
            # Create Payout record
            payout = Payout.objects.create(
                shop_id=self.shop_id,
                tenant_id=self.shop_id,
                amount=amount,
                status=Payout.STATUS_PENDING,
                bank_info=bank_info
            )

            # Deduct from balance
            self.balance.current_balance = F('current_balance') - amount
            self.balance.total_withdrawn = F('total_withdrawn') + amount
            self.balance.save()

            # Record in ledger
            LedgerEntry.objects.create(
                shop_id=self.shop_id,
                tenant_id=self.shop_id,
                entry_type=LedgerEntry.ENTRY_TYPE_PAYOUT,
                amount=amount,
                description=f"Payout request: {payout.id}",
                payout=payout
            )
            
            return payout

    @staticmethod
    def sweep_matured_funds():
        """
        Celery task: Moves funds from pending to current after 7 days.
        """
        from datetime import timedelta
        threshold = timezone.now() - timedelta(days=7)
        
        matured_entries = LedgerEntry.objects.filter(
            entry_type=LedgerEntry.ENTRY_TYPE_INCOME,
            is_cleared=False,
            created_at__lte=threshold
        )
        
        count = 0
        for entry in matured_entries:
            with transaction.atomic():
                balance = PlatformBalance.objects.get(shop=entry.shop)
                balance.pending_balance = F('pending_balance') - entry.amount
                balance.current_balance = F('current_balance') + entry.amount
                balance.save()
                
                entry.is_cleared = True
                entry.cleared_at = timezone.now()
                entry.save()
                count += 1
        
        return count
