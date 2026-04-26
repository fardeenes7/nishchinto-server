from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from marketing.services.meta_ads import MetaAdsService
from marketing.serializers import MetaAdAccountSerializer

class MetaAdsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def _require_shop_id(self, request):
        shop_id = getattr(request, "tenant_id", None)
        if not shop_id:
            raise PermissionError("No shop context. Provide X-Tenant-ID header.")
        return str(shop_id)

    @extend_schema(responses={200: {"type": "array", "items": {"type": "object"}}}, tags=["marketing"])
    @action(detail=False, methods=["get"], url_path="available-accounts")
    def available_accounts(self, request):
        """
        List all Meta Ad Accounts the connected user has access to.
        """
        try:
            shop_id = self._require_shop_id(request)
            service = MetaAdsService(shop_id)
            accounts = service.get_available_ad_accounts()
            return Response(accounts)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(request=MetaAdAccountSerializer, responses={201: MetaAdAccountSerializer}, tags=["marketing"])
    @action(detail=False, methods=["post"], url_path="link-account")
    def link_account(self, request):
        """
        Link a selected Ad Account to the shop.
        """
        try:
            shop_id = self._require_shop_id(request)
            serializer = MetaAdAccountSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = MetaAdsService(shop_id)
            account = service.link_ad_account(
                account_id=serializer.validated_data["account_id"],
                name=serializer.validated_data["name"],
                currency=serializer.validated_data.get("currency", "BDT")
            )
            return Response(MetaAdAccountSerializer(account).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={201: {"type": "object"}}, tags=["marketing"])
    @action(detail=False, methods=["post"], url_path="create-campaign")
    def create_campaign(self, request):
        """
        EPIC D-02: Create an automated Traffic campaign on Meta.
        """
        try:
            shop_id = self._require_shop_id(request)
            ad_account_id = request.data.get("ad_account_id")
            name = request.data.get("name")
            budget = request.data.get("daily_budget_bdt")
            gender = request.data.get("gender", "ALL")
            
            if not all([ad_account_id, name, budget]):
                return Response({"detail": "ad_account_id, name, and daily_budget_bdt are required."}, status=status.HTTP_400_BAD_REQUEST)
                
            service = MetaAdsService(shop_id)
            result = service.create_automated_campaign(
                ad_account_id=ad_account_id,
                campaign_name=name,
                daily_budget_bdt=float(budget),
                gender=gender
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
