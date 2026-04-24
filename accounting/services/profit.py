"""
accounting/services/profit.py

Service for calculating order profitability and investor splits.
"""

import logging
from decimal import Decimal
from django.db import transaction

from accounting.models import LedgerEntry, Investor
from orders.models import Order

logger = logging.getLogger(__name__)

class ProfitService:
    """
    Calculates profit per order and handles equity splits.
    """

    def __init__(self, shop_id):
        self.shop_id = shop_id

    def calculate_order_profit(self, order: Order) -> Decimal:
        """
        Profit = Total Amount - Total COGS (Cost of Goods Sold) - Platform Fees.
        COGS is derived from the variant's purchase_price at the time of order.
        """
        total_revenue = order.total_amount
        total_cogs = Decimal('0.00')
        
        for item in order.items.all():
            purchase_price = item.variant.effective_purchase_price if item.variant else Decimal('0.00')
            total_cogs += purchase_price * item.quantity
            
        # Simplified: fees are usually recorded separately in LedgerEntry
        # But we can subtract them here if we have them linked to the order.
        fees = LedgerEntry.objects.filter(
            shop_id=self.shop_id,
            order=order,
            entry_type=LedgerEntry.ENTRY_TYPE_EXPENSE
        ).values_list('amount', flat=True)
        
        total_fees = sum(fees)
        
        profit = total_revenue - total_cogs - total_fees
        return profit

    def distribute_investor_shares(self, order: Order, profit: Decimal):
        """
        Splits the profit among investors based on their equity percentage.
        Records these as separate LedgerEntry items for transparency.
        """
        if profit <= 0:
            return

        investors = Investor.objects.filter(shop_id=self.shop_id)
        
        with transaction.atomic():
            for investor in investors:
                share_amount = (profit * investor.equity_percentage) / Decimal('100.00')
                
                LedgerEntry.objects.create(
                    shop_id=self.shop_id,
                    tenant_id=self.shop_id,
                    entry_type=LedgerEntry.ENTRY_TYPE_ADJUSTMENT,
                    amount=share_amount,
                    description=f"Profit share for {investor.name} from Order {order.id}",
                    order=order
                )
                
                logger.info(f"Distributed {share_amount} to investor {investor.name}")
