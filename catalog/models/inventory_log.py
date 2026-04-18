"""
InventoryLog model — append-only audit trail for every stock movement.

Heavy log tables must eventually be partitioned by month (noted in plan).
This model is intentionally NOT soft-deleted — it's a ledger.
"""
from django.conf import settings
from django.db import models


class InventoryLog(models.Model):
    """
    Every stock change writes one row here.
    delta > 0 = restock / return
    delta < 0 = sale / manual deduction
    """

    class Reason(models.TextChoices):
        SALE = "SALE", "Sale"
        RESTOCK = "RESTOCK", "Restock"
        ADJUSTMENT = "ADJUSTMENT", "Manual Adjustment"
        RETURN = "RETURN", "Return"
        IMPORT = "IMPORT", "Import"

    # BigAutoField to support massive log volume
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="inventory_logs",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="inventory_logs",
    )
    delta = models.IntegerField(help_text="Positive = restock, negative = deduction")
    reason = models.CharField(max_length=15, choices=Reason.choices)
    # Flexible reference: order ID, import batch UUID, etc.
    reference_id = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_actions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inventory Log"
        verbose_name_plural = "Inventory Logs"
        indexes = [
            models.Index(
                fields=["shop", "variant", "created_at"],
                name="invlog_shop_variant_created_idx",
            ),
            models.Index(
                fields=["shop", "created_at"],
                name="invlog_shop_created_idx",
            ),
        ]
        # NOTE: This table should eventually be partitioned by created_at month.
        # See system_audit_report.md §2 "Data Duplication in Event Logs".

    def __str__(self):
        sign = "+" if self.delta >= 0 else ""
        return f"[{self.reason}] {sign}{self.delta} on {self.variant_id}"
