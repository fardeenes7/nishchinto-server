from __future__ import annotations

from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone
from django_redis import get_redis_connection
from orders.models import Order

RESERVATION_CACHE_PREFIX = "orders:reservation"

LUA_RESERVE_STOCK = """
local key = KEYS[1]
local amount = tonumber(ARGV[1])
local current = tonumber(redis.call('get', key) or "0")
if current >= amount then
    redis.call('decrby', key, amount)
    return 1
else
    return 0
end
"""

def reservation_cache_key(*, order_id: str) -> str:
    return f"{RESERVATION_CACHE_PREFIX}:{order_id}"

def reservation_expires_at(*, minutes: int) -> timezone.datetime:
    return timezone.now() + timedelta(minutes=minutes)

def reservation_store(*, order: Order, minutes: int) -> None:
    cache.set(
        reservation_cache_key(order_id=str(order.id)),
        {
            "order_id": str(order.id),
            "shop_id": str(order.shop_id),
            "expires_at": order.lock_expires_at.isoformat() if order.lock_expires_at else None,
            "total_amount": str(order.total_amount),
        },
        timeout=max(minutes * 60, 60),
    )

def reservation_clear(*, order_id: str) -> None:
    cache.delete(reservation_cache_key(order_id=order_id))

def reserve_stock_atomic(product_id: str, variant_id: str | None, quantity: int) -> bool:
    key = f"stock:{product_id}"
    if variant_id:
        key += f":{variant_id}"
    r = get_redis_connection("default")
    result = r.eval(LUA_RESERVE_STOCK, 1, key, quantity)
    return bool(result)
