from __future__ import annotations

from hashlib import sha256

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from compliance.audit import audit_event_create
from media.models import Media
from orders.models import Order
from shops.models import CustomerProfile, ShopMember


def _tombstone_token(*, user_id: str) -> str:
    digest = sha256(f"hard-delete:{user_id}:{timezone.now().isoformat()}".encode("utf-8")).hexdigest()
    return f"anon-{digest[:12]}"


def hard_delete_account(*, user_id: str, actor_admin_id: str) -> None:
    user_model = get_user_model()
    actor = user_model.objects.filter(id=actor_admin_id, deleted_at__isnull=True).first()
    if not actor or not actor.is_staff:
        raise PermissionDenied("Only internal admins can execute hard account deletion.")

    target = user_model.objects.filter(id=user_id, deleted_at__isnull=True).first()
    if not target:
        return

    now = timezone.now()
    tombstone = _tombstone_token(user_id=str(target.id))

    with transaction.atomic():
        owned_shop_ids = list(
            ShopMember.objects.filter(
                user_id=target.id,
                role="OWNER",
                deleted_at__isnull=True,
            ).values_list("shop_id", flat=True)
        )

        if owned_shop_ids:
            profiles = CustomerProfile.objects.filter(tenant_id__in=owned_shop_ids, deleted_at__isnull=True)
            profile_ids = list(profiles.values_list("id", flat=True))
            if profile_ids:
                profiles.update(name="", phone_number=tombstone)
                Order.objects.filter(customer_profile_id__in=profile_ids).update(customer_profile=None)

            media_assets = Media.objects.filter(shop_id__in=owned_shop_ids, deleted_at__isnull=True)
            for media in media_assets:
                if media.s3_key:
                    default_storage.delete(media.s3_key)
                media.soft_delete()

        target.email = f"{tombstone}@deleted.local"
        target.first_name = ""
        target.last_name = ""
        target.is_active = False
        target.deleted_at = now
        target.set_unusable_password()
        target.save(
            update_fields=[
                "email",
                "first_name",
                "last_name",
                "is_active",
                "password",
                "deleted_at",
                "updated_at",
            ]
        )

        audit_event_create(
            action="HARD_DELETE_ACCOUNT",
            resource_type="users.User",
            resource_id=str(target.id),
            actor_user_id=str(actor.id),
            metadata={
                "tombstone_token": tombstone,
                "owned_shop_ids": [str(shop_id) for shop_id in owned_shop_ids],
            },
        )
