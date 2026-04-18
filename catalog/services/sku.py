"""
SKU generation service.

Auto-generates unique, human-readable SKUs scoped per shop.
Format: {SHOPPREFIX}-{PID6}-{VID4}
  e.g. "MYSH-A3F9E1-B2C4"

Safe Mode (used during import conflicts) appends numeric suffixes:
  "MYSH-A3F9E1-B2C4" → "MYSH-A3F9E1-B2C4-1" → "MYSH-A3F9E1-B2C4-2"
"""
import uuid


def _shop_prefix(shop_id: str) -> str:
    """Derives a 4-char uppercase prefix from the shop subdomain or UUID."""
    # Imported here to prevent cross-app model imports at module level
    from shops.models import Shop
    try:
        shop = Shop.objects.get(id=shop_id)
        prefix = shop.subdomain.upper()[:4].ljust(4, "X")
    except Shop.DoesNotExist:
        prefix = str(shop_id).upper()[:4]
    return prefix


def generate_sku(
    *, shop_id: str, product_id: str, variant_id: str | None = None
) -> str:
    """
    Generates a candidate SKU. Does NOT guarantee uniqueness — call ensure_unique_sku.
    Format: SHOPPREFIX-PID6-VID4 (all uppercase, no dashes in UUIDs)
    """
    prefix = _shop_prefix(shop_id)
    pid_short = str(product_id).replace("-", "").upper()[:6]
    vid_short = (
        str(variant_id).replace("-", "").upper()[:4]
        if variant_id
        else "BASE"
    )
    return f"{prefix}-{pid_short}-{vid_short}"


def ensure_unique_sku(*, shop_id: str, candidate_sku: str, exclude_id: str | None = None) -> str:
    """
    Checks if the SKU is unique within the shop (active records only).
    If not, appends -1, -2, ... suffix (Safe Mode behaviour from spec).
    """
    from catalog.models.product import Product
    from catalog.models.variant import ProductVariant

    def sku_exists(sku: str) -> bool:
        product_qs = Product.objects.filter(
            shop_id=shop_id, sku=sku, deleted_at__isnull=True
        )
        variant_qs = ProductVariant.objects.filter(
            shop_id=shop_id, sku=sku, deleted_at__isnull=True
        )
        if exclude_id:
            product_qs = product_qs.exclude(id=exclude_id)
            variant_qs = variant_qs.exclude(id=exclude_id)
        return product_qs.exists() or variant_qs.exists()

    if not sku_exists(candidate_sku):
        return candidate_sku

    counter = 1
    while True:
        suffixed = f"{candidate_sku}-{counter}"
        if not sku_exists(suffixed):
            return suffixed
        counter += 1
        if counter > 999:
            # Extreme edge case guard
            return f"{candidate_sku}-{uuid.uuid4().hex[:4].upper()}"
