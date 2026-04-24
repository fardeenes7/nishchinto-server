from django.core.paginator import Paginator
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import InventoryLog
from compliance.api.serializers import (
    AuditEventSerializer,
    InventoryLogSerializer,
    NotificationLogSerializer,
    OrderTransitionLogSerializer,
)
from compliance.models import AuditEvent
from notifications.models import NotificationDeliveryLog
from orders.models import OrderTransitionLog
from shops.models import ShopMember


ALLOWED_LOG_ROLES = {"OWNER", "MANAGER", "INVENTORY_MANAGER"}


def _require_tenant_id(request) -> str:
    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        raise PermissionError("No shop context. Provide X-Tenant-ID header.")
    return str(tenant_id)


def _assert_logs_access(*, user_id: str, shop_id: str) -> None:
    membership = (
        ShopMember.objects.filter(
            user_id=user_id,
            shop_id=shop_id,
            deleted_at__isnull=True,
            shop__deleted_at__isnull=True,
        )
        .only("role")
        .first()
    )
    if not membership:
        raise PermissionError("No active membership for this shop.")
    if membership.role not in ALLOWED_LOG_ROLES:
        raise PermissionError("Insufficient role to access logs.")


def _paginated_response(*, queryset, serializer_class, request):
    page_num = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    paginator = Paginator(queryset, page_size)
    page = paginator.get_page(page_num)
    return {
        "count": paginator.count,
        "num_pages": paginator.num_pages,
        "results": serializer_class(page.object_list, many=True).data,
    }


class BaseLogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_shop_id(self, request) -> str:
        shop_id = _require_tenant_id(request)
        _assert_logs_access(user_id=str(request.user.id), shop_id=shop_id)
        return shop_id


class OrderLogsView(BaseLogsView):
    @extend_schema(
        tags=["compliance", "logs"],
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: OrderTransitionLogSerializer(many=True)},
        summary="List order transition logs for active tenant",
    )
    def get(self, request):
        try:
            shop_id = self.get_shop_id(request)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        queryset = (
            OrderTransitionLog.objects.select_related("order", "actor_user")
            .filter(order__shop_id=shop_id)
            .order_by("-created_at")
        )
        return Response(_paginated_response(queryset=queryset, serializer_class=OrderTransitionLogSerializer, request=request))


class MessageLogsView(BaseLogsView):
    @extend_schema(
        tags=["compliance", "logs"],
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: NotificationLogSerializer(many=True)},
        summary="List message/notification delivery logs for active tenant",
    )
    def get(self, request):
        try:
            shop_id = self.get_shop_id(request)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        queryset = NotificationDeliveryLog.objects.filter(shop_id=shop_id).order_by("-created_at")
        return Response(_paginated_response(queryset=queryset, serializer_class=NotificationLogSerializer, request=request))


class InventoryLogsView(BaseLogsView):
    @extend_schema(
        tags=["compliance", "logs"],
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: InventoryLogSerializer(many=True)},
        summary="List inventory movement logs for active tenant",
    )
    def get(self, request):
        try:
            shop_id = self.get_shop_id(request)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        queryset = InventoryLog.objects.filter(shop_id=shop_id).order_by("-created_at")
        return Response(_paginated_response(queryset=queryset, serializer_class=InventoryLogSerializer, request=request))


class AuditLogsView(BaseLogsView):
    @extend_schema(
        tags=["compliance", "logs"],
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: AuditEventSerializer(many=True)},
        summary="List audit events for active tenant",
    )
    def get(self, request):
        try:
            shop_id = self.get_shop_id(request)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        queryset = AuditEvent.objects.filter(shop_id=shop_id).order_by("-created_at")
        return Response(_paginated_response(queryset=queryset, serializer_class=AuditEventSerializer, request=request))
