from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from shops.models import Shop
from shops.models import ShopMember
from .serializers import ShopSerializer, ActiveShopContextSerializer, ShopSettingsSerializer, ShopTrackingConfigSerializer
from shops.models import ShopSettings
from catalog.models import ShopTrackingConfig


class ShopDetailView(APIView):
    """
    GET /api/v1/shops/me/ — Get current shop details.
    PATCH /api/v1/shops/me/ — Update shop details (e.g., base_currency).
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, shop_id):
        return get_object_or_404(Shop, id=shop_id, deleted_at__isnull=True)

    def _resolve_shop_id(self, request):
        tenant_shop_id = getattr(request, "tenant_id", None)
        if tenant_shop_id:
            membership_exists = ShopMember.objects.filter(
                user=request.user,
                shop_id=tenant_shop_id,
                deleted_at__isnull=True,
                shop__deleted_at__isnull=True,
            ).exists()
            if membership_exists:
                return str(tenant_shop_id)

        membership = (
            ShopMember.objects.select_related("shop")
            .filter(
                user=request.user,
                deleted_at__isnull=True,
                shop__deleted_at__isnull=True,
            )
            .order_by("created_at")
            .first()
        )
        if membership:
            return str(membership.shop_id)
        return None

    def get(self, request):
        shop_id = self._resolve_shop_id(request)
        if not shop_id:
            return Response({"detail": "No accessible shop found."}, status=status.HTTP_404_NOT_FOUND)
        
        shop = self.get_object(shop_id)
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def patch(self, request):
        shop_id = self._resolve_shop_id(request)
        if not shop_id:
            return Response({"detail": "No accessible shop found."}, status=status.HTTP_404_NOT_FOUND)
        
        shop = self.get_object(shop_id)
        serializer = ShopSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ActiveShopContextView(APIView):
    """
    GET /api/v1/shops/active/ — Resolve authenticated user's active shop context.
    Prefers X-Tenant-ID when provided and user has membership.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant_shop_id = getattr(request, "tenant_id", None)

        if tenant_shop_id:
            tenant_membership = (
                ShopMember.objects.select_related("shop")
                .filter(
                    user=request.user,
                    shop_id=tenant_shop_id,
                    deleted_at__isnull=True,
                    shop__deleted_at__isnull=True,
                )
                .first()
            )
            if tenant_membership:
                payload = {
                    "shop": tenant_membership.shop,
                    "role": tenant_membership.role,
                }
                return Response(ActiveShopContextSerializer(payload).data)

        membership = (
            ShopMember.objects.select_related("shop")
            .filter(
                user=request.user,
                deleted_at__isnull=True,
                shop__deleted_at__isnull=True,
            )
            .order_by("created_at")
            .first()
        )

        if not membership:
            return Response({"detail": "No accessible shop found."}, status=status.HTTP_404_NOT_FOUND)

        payload = {
            "shop": membership.shop,
            "role": membership.role,
        }
        return Response(ActiveShopContextSerializer(payload).data)


class ShopSettingsView(APIView):
    """
    GET /api/v1/shops/settings/
    PATCH /api/v1/shops/settings/
    """
    permission_classes = [IsAuthenticated]

    def _get_shop_id(self, request):
        # We can reuse the ActiveShopContextView logic or use _resolve_shop_id
        # Let's instantiate ShopDetailView for simplicity to reuse _resolve_shop_id
        shop_id = ShopDetailView()._resolve_shop_id(request)
        return shop_id

    def get(self, request):
        shop_id = self._get_shop_id(request)
        if not shop_id:
            return Response({"detail": "No accessible shop found."}, status=status.HTTP_404_NOT_FOUND)
        
        settings, _ = ShopSettings.objects.get_or_create(shop_id=shop_id)
        serializer = ShopSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        shop_id = self._get_shop_id(request)
        if not shop_id:
            return Response({"detail": "No accessible shop found."}, status=status.HTTP_404_NOT_FOUND)
        
        settings, _ = ShopSettings.objects.get_or_create(shop_id=shop_id)
        serializer = ShopSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ShopTrackingConfigView(APIView):
    """
    GET /api/v1/shops/tracking/
    PATCH /api/v1/shops/tracking/
    """
    permission_classes = [IsAuthenticated]

    def _get_shop_id(self, request):
        return ShopDetailView()._resolve_shop_id(request)

    def get(self, request):
        shop_id = self._get_shop_id(request)
        if not shop_id:
            return Response({"detail": "No accessible shop found."}, status=status.HTTP_404_NOT_FOUND)
        
        config, _ = ShopTrackingConfig.objects.get_or_create(shop_id=shop_id)
        serializer = ShopTrackingConfigSerializer(config)
        return Response(serializer.data)

    def patch(self, request):
        shop_id = self._get_shop_id(request)
        if not shop_id:
            return Response({"detail": "No accessible shop found."}, status=status.HTTP_404_NOT_FOUND)
        
        config, _ = ShopTrackingConfig.objects.get_or_create(shop_id=shop_id)
        serializer = ShopTrackingConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
