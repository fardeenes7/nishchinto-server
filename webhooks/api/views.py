import json
from hashlib import sha256

from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.services import dead_letter_event_create
from webhooks.models import WebhookProcessingStatus, WebhookProvider
from webhooks.services import webhook_log_event, webhook_signature_valid


class MetaWebhookIngestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["webhooks"],
        summary="Meta webhook verification",
        request=None,
        responses={200: dict},
    )
    def get(self, request):
        mode = request.query_params.get("hub.mode")
        verify_token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        expected = getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "")

        if mode == "subscribe" and verify_token and verify_token == expected:
            return HttpResponse(challenge or "", status=status.HTTP_200_OK, content_type="text/plain")
        return Response({"detail": "Verification failed."}, status=status.HTTP_403_FORBIDDEN)

    @extend_schema(
        tags=["webhooks"],
        summary="Meta webhook ingest",
        request=None,
        responses={200: dict, 400: dict, 401: dict},
    )
    def post(self, request):
        signature = request.headers.get("X-Hub-Signature-256", "")
        raw_body = request.body or b""
        if not webhook_signature_valid(signature=signature, body=raw_body):
            return Response({"detail": "Invalid signature."}, status=status.HTTP_401_UNAUTHORIZED)

        payload = {}
        if raw_body:
            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError:
                return Response({"detail": "Malformed JSON payload."}, status=status.HTTP_400_BAD_REQUEST)

        external_event_id = (
            str(payload.get("id") or "")
            or str(payload.get("entry", [{}])[0].get("id") or "")
            or sha256(raw_body).hexdigest()
        )
        shop_id = payload.get("shop_id")

        webhook_log, created = webhook_log_event(
            provider=WebhookProvider.META,
            external_event_id=external_event_id,
            event_type="meta.webhook",
            body=raw_body,
            shop_id=shop_id,
            status=WebhookProcessingStatus.PROCESSED,
        )
        if not created:
            return Response({"status": "duplicate", "webhook_log_id": str(webhook_log.id)})

        try:
            return Response({"status": "accepted", "webhook_log_id": str(webhook_log.id)})
        except Exception as exc:
            dead_letter_event_create(
                source="webhooks.meta",
                event_key=external_event_id,
                payload=payload,
                error_message=str(exc),
                shop_id=shop_id,
            )
            webhook_log_event(
                provider=WebhookProvider.META,
                external_event_id=external_event_id,
                event_type="meta.webhook",
                body=raw_body,
                shop_id=shop_id,
                status=WebhookProcessingStatus.FAILED,
                error_message=str(exc),
            )
            return Response({"detail": "Webhook processing failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
