from django.core.cache import cache
from shops.models import Shop

class FeatureGate:
    """
    Enforces business limits and features based on the shop's subscription tier.
    Interacts with the billing service to retrieve effective limits.
    """
    
    @staticmethod
    def get_context(shop: Shop):
        """
        Retrieves the full subscription context for a shop.
        """
        from billing.services.subscription import get_subscription_context
        return get_subscription_context(shop)

    @staticmethod
    def get_effective_limit(shop: Shop, limit_name: str):
        """
        Retrieves a specific numeric limit.
        """
        context = FeatureGate.get_context(shop)
        if context.get('is_billing_exempt'):
            return 999999999 # Effectively unlimited
            
        return context.get('limits', {}).get(limit_name)

    @staticmethod
    def can_use_feature(shop: Shop, feature_name: str) -> bool:
        """
        Boolean check for feature availability.
        """
        context = FeatureGate.get_context(shop)
        if context.get('is_billing_exempt'):
            return True
            
        return bool(context.get('limits', {}).get(feature_name, False))

    @staticmethod
    def check_limit(shop: Shop, limit_name: str, current_count: int) -> bool:
        """
        Checks if the current count is within the effective limit.
        """
        limit = FeatureGate.get_effective_limit(shop, limit_name)
        if limit is None:
            return True # Unlimited
        return current_count < limit
