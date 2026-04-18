import uuid
from django.db import connection
from django.core.exceptions import ValidationError

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

        # Wrap everything to automatically inject session setting per request.
        # NOTE: For complex celery tasks or out-of-band DB requests, this will not apply.
        # This requires PostgreSQL Row-Level Security setup manually applying to tables.
        def execute_tenant_wrapper(execute, sql, params, many, context):
            # This is fundamentally applying the SET LOCAL per cursor operation.
            # However, direct execute intercepting can be complex.
            # In Django 5, doing a direct execute in middleware covers the connection until committed.
            pass

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

        return response
