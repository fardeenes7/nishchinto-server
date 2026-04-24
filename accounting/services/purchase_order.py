"""
accounting/services/purchase_order.py

Service for managing Purchase Orders (PO) and updating inventory costs.
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from accounting.models import PurchaseOrder, LedgerEntry
from catalog.models import ProductVariant

logger = logging.getLogger(__name__)

class POService:
    """
    Handles Purchase Order lifecycle and stock ingestion.
    """

    def __init__(self, shop_id):
        self.shop_id = shop_id

    def create_po(self, supplier_name: str, items: list) -> PurchaseOrder:
        """
        items: list of dicts {variant_id, quantity, unit_cost}
        """
        total_amount = sum(Decimal(str(i['quantity'])) * Decimal(str(i['unit_cost'])) for i in items)
        
        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                shop_id=self.shop_id,
                tenant_id=self.shop_id,
                supplier_name=supplier_name,
                total_amount=total_amount,
                status=PurchaseOrder.STATUS_DRAFT,
                items_json=items # We'll store it as JSON for simplicity in MVP
            )
            return po

    def mark_as_received(self, po_id: str):
        """
        Finalizes a PO, updates variant stock, and updates purchase_price (COGS).
        """
        with transaction.atomic():
            po = PurchaseOrder.objects.get(id=po_id, shop_id=self.shop_id)
            if po.status == PurchaseOrder.STATUS_RECEIVED:
                return po

            for item in po.items_json:
                variant = ProductVariant.objects.get(id=item['variant_id'], shop_id=self.shop_id)
                
                # Update stock
                variant.stock_quantity += int(item['quantity'])
                
                # Update purchase price (Weighted average or Last cost)
                # Here we use Last Cost for simplicity per §3 rules.
                variant.purchase_price_override = Decimal(str(item['unit_cost']))
                variant.save()

            po.status = PurchaseOrder.STATUS_RECEIVED
            po.received_at = timezone.now()
            po.save()

            # Record in Ledger as an expense (Inventory investment)
            LedgerEntry.objects.create(
                shop_id=self.shop_id,
                tenant_id=self.shop_id,
                entry_type=LedgerEntry.ENTRY_TYPE_EXPENSE,
                amount=po.total_amount,
                description=f"Purchase Order Received: {po.id} from {po.supplier_name}",
            )

            return po
