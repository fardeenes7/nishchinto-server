from typing import Sequence

from orders.models import Order


def checkout_create_order(*, shop_id: str, items: Sequence[dict], customer_profile_id: str | None = None) -> Order:
    raise NotImplementedError('Phase 1 scaffold: implement checkout_create_order service.')
