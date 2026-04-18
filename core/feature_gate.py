from django.core.cache import cache
from shops.models import Shop

class FeatureGate:
    """
    Enforces business limits and features based on the shop's subscription tier.
    Implements caching to reduce DB hits on high-frequency requests.
    """
    
    @staticmethod
    def get_effective_limit(shop: Shop, limit_name: str):
        """
        Calculates the effective limit by checking shop overrides first, 
        then falling back to the SubscriptionPlan default.
        """
        cache_key = f"feature_gate:{shop.id}:{limit_name}"
        cached_val = cache.get(cache_key)
        
        if cached_val is not None:
            return cached_val

        # 1. Check if there's an override on the Shop model
        override_field = f"override_{limit_name}"
        if hasattr(shop, override_field):
            val = getattr(shop, override_field)
            if val is not None:
                cache.set(cache_key, val, timeout=3600) # cache for 1 hour
                return val
        
        # 2. Fallback to SubscriptionPlan
        if shop.plan:
            val = getattr(shop.plan, limit_name, None)
            if val is not None:
                cache.set(cache_key, val, timeout=3600)
                return val
        
        return None

    @staticmethod
    def can_use_feature(shop: Shop, feature_name: str) -> bool:
        """
        Boolean check for feature availability.
        """
        cache_key = f"feature_gate:{shop.id}:{feature_name}"
        cached_val = cache.get(cache_key)

        if cached_val is not None:
            return cached_val

        if shop.plan:
            val = getattr(shop.plan, feature_name, False)
            cache.set(cache_key, val, timeout=3600)
            return val
            
        return False

    @staticmethod
    def check_limit(shop: Shop, limit_name: str, current_count: int) -> bool:
        """
        Convenience method to check if a limit has been reached.
        """
        limit = FeatureGate.get_effective_limit(shop, limit_name)
        if limit is None: # Unlimited
            return True
        return current_count < limit
