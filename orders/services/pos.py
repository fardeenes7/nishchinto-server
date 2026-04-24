"""
orders/services/pos.py

Service for handling POS sales and synchronization.
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderItem, OrderStatus
from catalog.models import ProductVariant
from accounting.services.settlement import SettlementService

logger = logging.getLogger(__name__)

class POSService:
    """
    Handles retail transactions from the POS interface.
    """

    def __init__(self, shop_id):
        from shops.models import Shop
        self.shop = Shop.objects.get(id=shop_id)

    def process_pos_sale(self, items: list, payments: list, customer_id=None):
        """
        items: [{variant_id, quantity, unit_price}]
        payments: [{method, amount}]
        """
        total_amount = sum(Decimal(str(i['quantity'])) * Decimal(str(i['unit_price'])) for i in items)
        
        with transaction.atomic():
            # 1. Create Order
            order = Order.objects.create(
                shop=self.shop,
                tenant_id=self.shop.id,
                status=OrderStatus.DELIVERED, # POS sales are immediate
                total_amount=total_amount,
                subtotal_amount=total_amount, # Simplified
                customer_profile_id=customer_id
            )

            # 2. Create OrderItems & Update Inventory
            for item in items:
                variant = ProductVariant.objects.select_for_update().get(id=item['variant_id'], shop_id=self.shop.id)
                
                OrderItem.objects.create(
                    order=order,
                    tenant_id=self.shop.id,
                    product=variant.product,
                    variant=variant,
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    line_total_amount=Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))
                )
                
                # Inventory deduction
                if variant.stock_quantity < item['quantity']:
                    # In POS, we might allow overselling if configured, 
                    # but default to strict check.
                    raise ValueError(f"Insufficient stock for {variant.sku}")
                
                variant.stock_quantity -= item['quantity']
                variant.save()

            # 3. Handle Payments & Platform Settlement
            settlement = SettlementService(self.shop.id)
            for pay in payments:
                if pay['method'] != 'CASH':
                    # Non-cash payments (e.g. Card/MFS) are handled via platform settlement
                    # logic if the merchant is using the platform's unified terminal.
                    # For MVP, we record it as income.
                    settlement.record_order_income(order, Decimal(str(pay['amount'])))
                else:
                    # Cash payments go directly to merchant's pocket, 
                    # we just record them in ledger for P&L.
                    from accounting.models import LedgerEntry
                    LedgerEntry.objects.create(
                        shop=self.shop,
                        tenant_id=self.shop.id,
                        entry_type=LedgerEntry.ENTRY_TYPE_INCOME,
                        amount=Decimal(str(pay['amount'])),
                        description=f"POS Cash Sale: {order.id}",
                        order=order,
                        is_cleared=True, # Cash is already 'cleared'
                        cleared_at=timezone.now()
                    )

            return order
