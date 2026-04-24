"""
billing/services/developer.py

Business logic for Developer API access and Outbound Webhooks.
Supports EPIC G: Advanced Developer Integrations.
"""

from typing import List
from django.utils import timezone
from shops.models import Shop
from billing.models import MerchantAPIToken, OutboundWebhook

def create_api_token(shop: Shop, user, name: str, scopes: List[str], expires_in_days: int = None):
    """
    Creates a new scoped API token.
    """
    expires_at = None
    if expires_in_days:
        expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
        
    instance, raw_token = MerchantAPIToken.generate(
        shop=shop,
        created_by=user,
        name=name,
        scopes=scopes,
        expires_at=expires_at
    )
    return instance, raw_token

def revoke_api_token(shop: Shop, token_id: str):
    """
    Soft-deletes an API token.
    """
    return MerchantAPIToken.objects.filter(shop=shop, id=token_id).delete()

def register_webhook(shop: Shop, url: str, subscribed_events: List[str]):
    """
    Registers a new outbound webhook endpoint.
    """
    webhook = OutboundWebhook.objects.create(
        shop=shop,
        tenant_id=shop.id,
        url=url,
        subscribed_events=subscribed_events
    )
    return webhook

def update_webhook(shop: Shop, webhook_id: str, **kwargs):
    """
    Updates webhook settings.
    """
    webhook = OutboundWebhook.objects.get(shop=shop, id=webhook_id)
    for key, value in kwargs.items():
        setattr(webhook, key, value)
    webhook.save()
    return webhook

def get_active_webhooks_for_event(shop: Shop, event_type: str):
    """
    Returns all active webhooks subscribed to a specific event.
    """
    return OutboundWebhook.objects.filter(
        shop=shop,
        status=OutboundWebhook.STATUS_ACTIVE,
        subscribed_events__contains=event_type
    )
