from compliance.models import AuditEvent
from core.services.request_context import get_request_context


def audit_event_create(
    *,
    action: str,
    resource_type: str,
    resource_id: str = "",
    shop_id: str | None = None,
    actor_user_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    payload_signature: str = "",
) -> AuditEvent:
    context = get_request_context()
    context_impersonation = context.get("impersonation") or {}
    context_ip = context.get("ip_address")

    merged_metadata = dict(metadata or {})
    if context_impersonation.get("active"):
        merged_metadata.setdefault("impersonation", context_impersonation)

    return AuditEvent.objects.create(
        shop_id=shop_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=merged_metadata,
        ip_address=ip_address or context_ip,
        payload_signature=payload_signature,
    )
