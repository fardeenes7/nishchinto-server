from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from shops.models import Shop
from .serializers import ShopSerializer


class ShopDetailView(APIView):
    """
    GET /api/v1/shops/me/ — Get current shop details.
    PATCH /api/v1/shops/me/ — Update shop details (e.g., base_currency).
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, shop_id):
        return get_object_or_404(Shop, id=shop_id, deleted_at__isnull=True)

    def get(self, request):
        shop_id = getattr(request, "tenant_id", None)
        if not shop_id:
            return Response({"detail": "No shop context."}, status=400)
        
        shop = self.get_object(shop_id)
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def patch(self, request):
        shop_id = getattr(request, "tenant_id", None)
        if not shop_id:
            return Response({"detail": "No shop context."}, status=400)
        
        shop = self.get_object(shop_id)
        serializer = ShopSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
