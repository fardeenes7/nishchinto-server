import uuid
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.services.request_context import clear_request_context, set_request_context

class TenantMiddleware:
    """
    Middleware that captures the tenant context and enforces it at the database layer.
    Extracts the tenant dynamically via 'X-Tenant-ID' request header.
    To support PgBouncer, the SET LOCAL command only lasts for the current transaction block.
    If ATOMIC gets committed, we need a signal implementation, but here we inject it 
    as part of standard workflow queries.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = request.headers.get("X-Tenant-ID")

        if tenant_id:
            try:
                # Basic validation to prevent SQLi
                uuid.UUID(tenant_id)
            except ValueError:
                tenant_id = None

        request.tenant_id = tenant_id

        impersonated_user_id = request.headers.get("X-Impersonate-User-ID")
        expires_at_raw = request.headers.get("X-Impersonation-Expires-At")
        is_impersonation = bool(impersonated_user_id)
        request.impersonation = {
            "active": False,
            "target_user_id": None,
            "expires_at": None,
            "actor_user_id": str(request.user.id) if getattr(request, "user", None) and request.user.is_authenticated else None,
        }

        if is_impersonation:
            if not getattr(request, "user", None) or not request.user.is_authenticated:
                return JsonResponse({"detail": "Authentication required for impersonation."}, status=401)
            if not request.user.is_staff:
                return JsonResponse({"detail": "Only internal staff can impersonate."}, status=403)
            if not expires_at_raw:
                return JsonResponse({"detail": "X-Impersonation-Expires-At is required."}, status=400)

            expires_at = parse_datetime(expires_at_raw)
            if not expires_at:
                return JsonResponse({"detail": "Invalid X-Impersonation-Expires-At format."}, status=400)
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
            if expires_at <= timezone.now():
                return JsonResponse({"detail": "Impersonation context expired."}, status=403)

            request.impersonation = {
                "active": True,
                "target_user_id": impersonated_user_id,
                "expires_at": expires_at.isoformat(),
                "actor_user_id": str(request.user.id),
            }

        set_request_context(
            {
                "tenant_id": tenant_id,
                "impersonation": request.impersonation,
                "ip_address": request.META.get("REMOTE_ADDR"),
            }
        )

        # Since Django opens a fresh transaction or just executes within the connection thread:
        with connection.cursor() as cursor:
            if tenant_id:
                # `app.current_shop_id` will be used in PostgreSQL RLS policies
                cursor.execute("SET app.current_shop_id = %s", [tenant_id])
            else:
                cursor.execute("SET app.current_shop_id = ''")

        response = self.get_response(request)

        # Clear it structurally ensuring no connection pooling leak if transaction mode is weird
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_shop_id = ''")

        clear_request_context()

        return response
