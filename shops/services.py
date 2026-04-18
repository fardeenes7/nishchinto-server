# shops/services.py
from .models import Shop, ShopMember
from django.db import transaction
from django.conf import settings

def shop_create(*, name: str, subdomain: str, owner_user) -> Shop:
    """
    Creates a new shop tenant and immediately assigns the creator as OWNER.
    """
    with transaction.atomic():
        shop = Shop.objects.create(name=name, subdomain=subdomain)
        ShopMember.objects.create(
            user=owner_user,
            shop=shop,
            role='OWNER'
        )
    return shop
