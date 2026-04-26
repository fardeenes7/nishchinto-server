import requests
import logging
from django.conf import settings
from marketing.models import MetaUserAccount, MetaAdAccount

logger = logging.getLogger(__name__)

_GRAPH_API_VERSION = "v21.0"

class MetaAdsService:
    def __init__(self, shop_id: str):
        self.shop_id = shop_id
        try:
            self.user_account = MetaUserAccount.objects.get(shop_id=shop_id)
        except MetaUserAccount.DoesNotExist:
            self.user_account = None

    def get_available_ad_accounts(self) -> list[dict]:
        """
        Fetches all ad accounts the user has access to.
        """
        if not self.user_account:
            raise ValueError("Meta user account not connected.")

        url = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/me/adaccounts"
        params = {
            "access_token": self.user_account.access_token,
            "fields": "id,name,currency,account_status",
        }
        
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except requests.RequestException as e:
            logger.error("Failed to fetch ad accounts from Meta: %s", e)
            raise e

    def link_ad_account(self, account_id: str, name: str, currency: str) -> MetaAdAccount:
        """
        Links a specific ad account to the shop.
        """
        account, created = MetaAdAccount.objects.update_or_create(
            shop_id=self.shop_id,
            account_id=account_id,
            defaults={
                "tenant_id": self.shop_id,
                "name": name,
                "currency": currency,
                "is_active": True,
            }
        )
        return account

    def create_automated_campaign(self, *, ad_account_id: str, campaign_name: str, daily_budget_bdt: float, gender: str = "ALL") -> dict:
        """
        EPIC D-02: Create a simplified traffic campaign on Meta.
        """
        if not self.user_account:
            raise ValueError("Meta user account not connected.")

        # 1. Create Campaign
        campaign_url = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{ad_account_id}/campaigns"
        campaign_payload = {
            "name": campaign_name,
            "objective": "OUTCOME_TRAFFIC",
            "status": "PAUSED", # Start paused for safety
            "special_ad_categories": "NONE",
            "access_token": self.user_account.access_token,
        }
        
        resp = requests.post(campaign_url, json=campaign_payload, timeout=20)
        resp.raise_for_status()
        campaign_id = resp.json().get("id")

        # 2. Create AdSet
        adset_url = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{ad_account_id}/adsets"
        
        # Gender mapping: 1=Male, 2=Female, [1,2]=All
        genders = [1, 2]
        if gender == "MALE": genders = [1]
        elif gender == "FEMALE": genders = [2]

        adset_payload = {
            "name": f"AdSet for {campaign_name}",
            "campaign_id": campaign_id,
            "daily_budget": int(daily_budget_bdt * 100), # Meta uses cents/subunits
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "LINK_CLICKS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {
                "geo_locations": {"countries": ["BD"]},
                "genders": genders,
                "publisher_platforms": ["facebook", "instagram"],
            },
            "status": "PAUSED",
            "access_token": self.user_account.access_token,
        }

        resp = requests.post(adset_url, json=adset_payload, timeout=20)
        resp.raise_for_status()
        adset_id = resp.json().get("id")

        # 3. Save to DB
        from marketing.models import MetaAdCampaign, MetaAdAccount
        ad_account = MetaAdAccount.objects.get(account_id=ad_account_id, shop_id=self.shop_id)
        
        campaign = MetaAdCampaign.objects.create(
            shop_id=self.shop_id,
            tenant_id=self.shop_id,
            ad_account=ad_account,
            external_campaign_id=campaign_id,
            name=campaign_name,
            daily_budget_bdt=daily_budget_bdt,
            targeting_data={"gender": gender, "adset_id": adset_id}
        )

        return {
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "local_id": str(campaign.id)
        }
