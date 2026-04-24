import hmac
import json
from hashlib import sha256

from django.test import override_settings
from django.test import TestCase
from rest_framework.test import APIClient

from shops.models import Shop
from webhooks.models import WebhookProcessingStatus, WebhookProvider
from webhooks.services import webhook_log_event, webhook_signature_valid


class WebhookServicesTests(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Demo", subdomain="demo-webhooks")

    def test_webhook_signature_valid_supports_sha256_prefix(self):
        body = b'{"hello": "world"}'
        secret = "test-secret"
        digest = hmac.new(secret.encode("utf-8"), msg=body, digestmod=sha256).hexdigest()

        self.assertTrue(webhook_signature_valid(signature=f"sha256={digest}", body=body, app_secret=secret))
        self.assertFalse(webhook_signature_valid(signature="sha256=bad", body=body, app_secret=secret))

    def test_webhook_log_event_marks_duplicates(self):
        log, created = webhook_log_event(
            provider=WebhookProvider.META,
            external_event_id="evt-123",
            event_type="message",
            body=b'{"id":"evt-123"}',
            shop_id=str(self.shop.id),
        )

        self.assertTrue(created)
        self.assertEqual(log.status, WebhookProcessingStatus.PROCESSED)

        duplicate, duplicate_created = webhook_log_event(
            provider=WebhookProvider.META,
            external_event_id="evt-123",
            event_type="message",
            body=b'{"id":"evt-123"}',
            shop_id=str(self.shop.id),
            error_message="duplicate webhook",
        )

        self.assertFalse(duplicate_created)
        self.assertEqual(duplicate.id, log.id)
        self.assertEqual(duplicate.status, WebhookProcessingStatus.DUPLICATE)


@override_settings(META_APP_SECRET="meta-secret", META_WEBHOOK_VERIFY_TOKEN="verify-token")
class MetaWebhookIngestApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _signed_body(self, payload: dict) -> tuple[str, str]:
        raw = json.dumps(payload).encode("utf-8")
        digest = hmac.new(b"meta-secret", msg=raw, digestmod=sha256).hexdigest()
        return raw.decode("utf-8"), f"sha256={digest}"

    def test_verification_requires_valid_token(self):
        ok = self.client.get("/api/v1/webhooks/meta/?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=abc")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.content.decode("utf-8"), "abc")

        denied = self.client.get("/api/v1/webhooks/meta/?hub.mode=subscribe&hub.verify_token=bad&hub.challenge=abc")
        self.assertEqual(denied.status_code, 403)

    def test_post_rejects_invalid_signature(self):
        response = self.client.post(
            "/api/v1/webhooks/meta/",
            data=json.dumps({"id": "evt-1"}),
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid",
        )
        self.assertEqual(response.status_code, 401)

    def test_post_accepts_and_deduplicates(self):
        payload = {"id": "evt-accepted", "entry": [{"id": "entry-1"}]}
        body, signature = self._signed_body(payload)

        first = self.client.post(
            "/api/v1/webhooks/meta/",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "accepted")

        second = self.client.post(
            "/api/v1/webhooks/meta/",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "duplicate")
