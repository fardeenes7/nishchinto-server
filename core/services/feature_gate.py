import json
from django.core.cache import cache
from shops.models import Shop

# In a real scenario, this matrix would be manageable from the internal admin.
# Hardcoding as per business_rules_and_limits.md
PLAN_MATRIX = {
    'Free': {
        'max_stores': 1,
        'max_products': 5,
        'custom_domains': 0,
        'staff_accounts': 1,
        'remove_branding': False,
        'marketing_pixels': False,
        'custom_smtp': False,
        'pos_system': False,
        'b2b_credit': False,
        'developer_api': False,
        'ai_credits_monthly': 10 # Technically one-time for Free, but used as limit
    },
    'Basic': {
        'max_stores': 3,
        'max_products': 50,
        'custom_domains': 1,
        'staff_accounts': 3,
        'remove_branding': True,
        'marketing_pixels': True,
        'custom_smtp': False,
        'pos_system': False,
        'b2b_credit': False,
        'developer_api': False,
        'ai_credits_monthly': 100
    },
    'Pro': {
        'max_stores': 999999,
        'max_products': 999999,
        'custom_domains': 3,
        'staff_accounts': 10,
        'remove_branding': True,
        'marketing_pixels': True,
        'custom_smtp': True,
        'pos_system': True,
        'b2b_credit': False,
        'developer_api': False,
        'ai_credits_monthly': 250
    },
    'Business': {
        'max_stores': 999999,
        'max_products': 999999,
        'custom_domains': 999999,
        'staff_accounts': 999999,
        'remove_branding': True,
        'marketing_pixels': True,
        'custom_smtp': True,
        'pos_system': True,
        'b2b_credit': True,
        'developer_api': True,
        'ai_credits_monthly': 1000
    }
}

class FeatureGate:
    """
    Utility service to determine if a specific shop has access to a feature.
    Evaluates tier matrix + overrides.
    """
    
    @staticmethod
    def get_shop_plan(shop: Shop) -> str:
        # Placeholder: Assume shop has an active Subscription relationship
        # For now, returning default 'Free'
        return getattr(shop, 'active_plan_name', 'Free')

    @classmethod
    def get_effective_limit(cls, shop: Shop, limit_key: str):
        # Override formula: Effective Limit = Shop.override_max_products ?? Shop.SubscriptionPlan.max_products
        override_attr = f'override_{limit_key}'
        if hasattr(shop, override_attr) and getattr(shop, override_attr) is not None:
            return getattr(shop, override_attr)
            
        plan_name = cls.get_shop_plan(shop)
        matrix = PLAN_MATRIX.get(plan_name, PLAN_MATRIX['Free'])
        return matrix.get(limit_key, 0)
        
    @classmethod
    def can_access_feature(cls, shop: Shop, feature_key: str) -> bool:
        # Check permissions matrix
        plan_name = cls.get_shop_plan(shop)
        matrix = PLAN_MATRIX.get(plan_name, PLAN_MATRIX['Free'])
        return bool(matrix.get(feature_key, False))

    @classmethod
    def enforce_product_limit(cls, shop: Shop, current_product_count: int) -> bool:
        limit = cls.get_effective_limit(shop, 'max_products')
        return current_product_count < limit
