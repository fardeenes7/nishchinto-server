from django.db.models import QuerySet

from orders.models import Order


def order_get_by_id(*, order_id: str, shop_id: str) -> Order:
    return Order.objects.get(id=order_id, shop_id=shop_id, deleted_at__isnull=True)


def order_list_for_shop(*, shop_id: str) -> QuerySet[Order]:
    return Order.objects.filter(shop_id=shop_id, deleted_at__isnull=True).order_by('-created_at')
