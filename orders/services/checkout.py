from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from django.db import transaction

from catalog.models import Product, ProductVariant
from orders.models import Order, OrderItem, OrderStatus
from orders.services.reservations import reservation_expires_at, reservation_store, reserve_stock_atomic
from shops.models import Shop, ShopSettings


def _resolve_line_price(*, product: Product, variant: ProductVariant | None) -> Decimal:
    if variant and variant.price_override is not None:
        return Decimal(str(variant.price_override))
    return Decimal(str(product.base_price))


def _resolve_available_stock(*, product: Product, variant: ProductVariant | None) -> int:
    if variant is not None:
        return int(variant.stock_quantity)
    return int(product.total_stock)


def checkout_create_order(*, shop_id: str, items: Sequence[dict], customer_profile_id: str | None = None) -> Order:
    shop = Shop.objects.get(id=shop_id, deleted_at__isnull=True)
    try:
        settings_obj = shop.settings
    except ShopSettings.DoesNotExist:
        settings_obj = None
    reservation_minutes = getattr(settings_obj, "stock_reservation_minutes", 30)
    expiry_at = reservation_expires_at(minutes=reservation_minutes)
    subtotal = Decimal("0.00")

    with transaction.atomic():
        order = Order.objects.create(
            shop=shop,
            tenant_id=shop.id,
            customer_profile_id=customer_profile_id,
            status=OrderStatus.AWAITING_PAYMENT,
            subtotal_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            currency=shop.base_currency,
            lock_expires_at=expiry_at,
        )

        for raw_item in items:
            product_id = raw_item.get("product_id")
            variant_id = raw_item.get("variant_id")
            quantity = int(raw_item.get("quantity", 1))
            if quantity <= 0:
                raise ValueError("Quantity must be positive.")

            product = Product.objects.select_related("shop").get(id=product_id, shop_id=shop.id, deleted_at__isnull=True)
            variant = None
            if variant_id:
                variant = ProductVariant.objects.select_related("product", "shop").get(
                    id=variant_id,
                    shop_id=shop.id,
                    product_id=product.id,
                    deleted_at__isnull=True,
                )

            available_stock = _resolve_available_stock(product=product, variant=variant)
            if quantity > available_stock:
                raise ValueError(
                    f"Insufficient stock for product {product.id}; requested {quantity}, available {available_stock}."
                )

            if not reserve_stock_atomic(str(product.id), str(variant.id) if variant else None, quantity):
                raise ValueError(
                    f"Failed to reserve stock for product {product.id}; requested {quantity}."
                )

            unit_price = _resolve_line_price(product=product, variant=variant)
            line_total = unit_price * Decimal(quantity)
            subtotal += line_total

            OrderItem.objects.create(
                order=order,
                tenant_id=order.tenant_id,
                product=product,
                variant=variant,
                quantity=quantity,
                unit_price=unit_price,
                line_discount_amount=Decimal("0.00"),
                line_total_amount=line_total,
            )

        order.subtotal_amount = subtotal
        order.total_amount = subtotal
        order.save(update_fields=["subtotal_amount", "total_amount", "lock_expires_at", "updated_at"])

        reservation_store(order=order, minutes=reservation_minutes)

    return order
