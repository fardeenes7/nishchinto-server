"""
Tests for the messenger app (v0.6).

Covers:
  - Greeting pre-filter logic
  - ConversationBotState Redis operations (human takeover, order draft, ctx cache)
  - MessengerMessage + FAQEntry model creation
  - Comment auto-reply deduplication logic
  - Webhook view: verification handshake + HMAC guard
  - Human takeover API endpoint
  - FAQ CRUD API endpoints
"""
from __future__ import annotations

import json
import hashlib
import hmac
import time
import unittest
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model

from messenger.services.greeting import is_greeting, greeting_reply_text

User = get_user_model()


# ---------------------------------------------------------------------------
# Greeting Pre-filter
# ---------------------------------------------------------------------------

class GreetingFilterTests(TestCase):
    def test_exact_match_hi(self):
        self.assertTrue(is_greeting(message_text="hi"))

    def test_exact_match_bangla(self):
        self.assertTrue(is_greeting(message_text="হ্যালো"))

    def test_case_insensitive(self):
        self.assertTrue(is_greeting(message_text="Hello"))
        self.assertTrue(is_greeting(message_text="HELLO"))

    def test_punctuation_stripped(self):
        self.assertTrue(is_greeting(message_text="hi!"))
        self.assertTrue(is_greeting(message_text="hey,"))

    def test_partial_match_not_greeting(self):
        """'hi I want to buy' must NOT match — full-message only."""
        self.assertFalse(is_greeting(message_text="hi I want to buy a shirt"))

    def test_custom_keyword_list(self):
        self.assertTrue(is_greeting(message_text="yo", keywords=["yo", "sup"]))
        self.assertFalse(is_greeting(message_text="hi", keywords=["yo", "sup"]))

    def test_empty_message(self):
        self.assertFalse(is_greeting(message_text=""))

    def test_greeting_reply_text_not_empty(self):
        reply = greeting_reply_text()
        self.assertIsInstance(reply, str)
        self.assertTrue(len(reply) > 0)


# ---------------------------------------------------------------------------
# ConversationBotState (Redis) — mocked
# ---------------------------------------------------------------------------

class BotStateTests(TestCase):
    """
    Redis calls are mocked; we test the logic of the wrapper functions.
    """

    def _make_redis_mock(self, hgetall_data: dict | None = None):
        mock_r = MagicMock()
        mock_r.hgetall.return_value = hgetall_data or {}
        mock_r.exists.return_value = 0
        mock_r.lrange.return_value = []
        return mock_r

    @patch("messenger.services.bot_state.get_redis_connection")
    def test_human_active_flag_set(self, mock_conn):
        mock_r = self._make_redis_mock()
        mock_conn.return_value = mock_r

        from messenger.services.bot_state import bot_state_set_human_active
        bot_state_set_human_active(page_id="P1", psid="U1", ttl_minutes=30)

        mock_r.hset.assert_called_once()
        call_kwargs = mock_r.hset.call_args[1]
        self.assertEqual(call_kwargs["mapping"]["human_active"], "1")

    @patch("messenger.services.bot_state.get_redis_connection")
    def test_human_active_returns_false_when_expired(self, mock_conn):
        expired_ts = str(int(time.time()) - 10)  # 10 seconds in the past
        mock_r = self._make_redis_mock({
            b"human_active": b"1",
            b"human_active_expires_at": expired_ts.encode(),
        })
        mock_conn.return_value = mock_r

        from messenger.services.bot_state import bot_state_is_human_active
        result = bot_state_is_human_active(page_id="P1", psid="U1")
        self.assertFalse(result)

    @patch("messenger.services.bot_state.get_redis_connection")
    def test_human_active_returns_true_when_valid(self, mock_conn):
        future_ts = str(int(time.time()) + 1800)  # 30 min in the future
        mock_r = self._make_redis_mock({
            b"human_active": b"1",
            b"human_active_expires_at": future_ts.encode(),
        })
        mock_conn.return_value = mock_r

        from messenger.services.bot_state import bot_state_is_human_active
        result = bot_state_is_human_active(page_id="P1", psid="U1")
        self.assertTrue(result)

    @patch("messenger.services.bot_state.get_redis_connection")
    def test_order_draft_round_trip(self, mock_conn):
        stored = {}

        def fake_hset(key, mapping=None, **kwargs):
            if mapping:
                stored.update({k.encode() if isinstance(k, str) else k: v.encode() if isinstance(v, str) else v for k, v in mapping.items()})

        def fake_hget(key, field):
            f = field.encode() if isinstance(field, str) else field
            return stored.get(f)

        mock_r = MagicMock()
        mock_r.hset.side_effect = fake_hset
        mock_r.hget.side_effect = fake_hget
        mock_conn.return_value = mock_r

        from messenger.services.bot_state import bot_state_set_order_draft, bot_state_get_order_draft
        draft = {"product_id": "abc", "quantity": 2}
        bot_state_set_order_draft(page_id="P1", psid="U1", draft=draft)
        result = bot_state_get_order_draft(page_id="P1", psid="U1")
        self.assertEqual(result, draft)

    @patch("messenger.services.bot_state.get_redis_connection")
    def test_ctx_cache_miss_returns_none(self, mock_conn):
        mock_r = self._make_redis_mock()
        mock_r.exists.return_value = 0
        mock_conn.return_value = mock_r

        from messenger.services.bot_state import ctx_cache_get
        result = ctx_cache_get(page_id="P1", psid="U1")
        self.assertIsNone(result)

    @patch("messenger.services.bot_state.get_redis_connection")
    def test_ctx_cache_returns_chronological_order(self, mock_conn):
        """LPUSH stores newest at index 0; ctx_cache_get must reverse to chronological."""
        # Simulate 2 messages stored via LPUSH (newest first at index 0)
        msg1 = json.dumps({"role": "user", "content": "hello", "timestamp": 100}).encode()
        msg2 = json.dumps({"role": "assistant", "content": "hi", "timestamp": 200}).encode()
        mock_r = self._make_redis_mock()
        mock_r.exists.return_value = 1
        mock_r.lrange.return_value = [msg2, msg1]  # newest first (LPUSH order)
        mock_conn.return_value = mock_r

        from messenger.services.bot_state import ctx_cache_get
        result = ctx_cache_get(page_id="P1", psid="U1")
        self.assertEqual(result[0]["timestamp"], 100)  # oldest first
        self.assertEqual(result[1]["timestamp"], 200)


# ---------------------------------------------------------------------------
# MessengerMessage model
# ---------------------------------------------------------------------------

class MessengerMessageModelTests(TestCase):
    def setUp(self):
        from shops.models import Shop, SubscriptionPlan
        plan, _ = SubscriptionPlan.objects.get_or_create(name="FREE")
        self.shop = Shop.objects.create(name="Test Shop", subdomain="testshop", plan=plan)

    def test_create_inbound_message(self):
        from messenger.models import MessengerMessage, MessageDirection
        msg = MessengerMessage.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            psid="12345",
            page_id="PAGE1",
            direction=MessageDirection.INBOUND,
            message_text="What is the price?",
            mid="m_test_001",
            timestamp=1000000,
        )
        self.assertEqual(msg.direction, MessageDirection.INBOUND)
        self.assertEqual(str(msg.psid), "12345")

    def test_mid_uniqueness(self):
        from messenger.models import MessengerMessage, MessageDirection
        from django.db import IntegrityError
        MessengerMessage.objects.create(
            shop=self.shop, tenant_id=self.shop.id,
            psid="A", page_id="P", direction=MessageDirection.INBOUND,
            message_text="hi", mid="uniq_mid_1", timestamp=1,
        )
        with self.assertRaises(IntegrityError):
            MessengerMessage.objects.create(
                shop=self.shop, tenant_id=self.shop.id,
                psid="B", page_id="P", direction=MessageDirection.INBOUND,
                message_text="hi2", mid="uniq_mid_1", timestamp=2,
            )


# ---------------------------------------------------------------------------
# FAQEntry model
# ---------------------------------------------------------------------------

class FAQEntryModelTests(TestCase):
    def setUp(self):
        from shops.models import Shop, SubscriptionPlan
        plan, _ = SubscriptionPlan.objects.get_or_create(name="FREE")
        self.shop = Shop.objects.create(name="FAQ Shop", subdomain="faqshop", plan=plan)

    def test_create_faq_entry(self):
        from messenger.models import FAQEntry, FAQCategory
        entry = FAQEntry.objects.create(
            shop=self.shop,
            tenant_id=self.shop.id,
            category=FAQCategory.RETURN_POLICY,
            question="What is your return policy?",
            answer="You can return within 7 days.",
            is_active=True,
        )
        self.assertEqual(entry.category, FAQCategory.RETURN_POLICY)
        self.assertIsNone(entry.embedding)  # not yet embedded

    def test_ordering_by_sort_order(self):
        from messenger.models import FAQEntry
        FAQEntry.objects.create(shop=self.shop, tenant_id=self.shop.id, question="Q2", answer="A2", sort_order=2)
        FAQEntry.objects.create(shop=self.shop, tenant_id=self.shop.id, question="Q1", answer="A1", sort_order=1)
        entries = list(FAQEntry.objects.filter(shop=self.shop).order_by("sort_order"))
        self.assertEqual(entries[0].question, "Q1")
        self.assertEqual(entries[1].question, "Q2")


# ---------------------------------------------------------------------------
# Webhook View — HMAC guard + verification handshake
# ---------------------------------------------------------------------------

class MessengerWebhookViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_signature(self, body: bytes, secret: str = "test_secret") -> str:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    @override_settings(META_APP_SECRET="test_secret", META_WEBHOOK_VERIFY_TOKEN="test_verify_token")
    def test_webhook_verification_handshake(self):
        from messenger.api.views import MetaWebhookView
        request = self.factory.get(
            "/api/v1/messenger/webhook/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "CHALLENGE_CODE_12345",
            },
        )
        view = MetaWebhookView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CHALLENGE_CODE_12345", response.content)

    @override_settings(META_APP_SECRET="test_secret", META_WEBHOOK_VERIFY_TOKEN="test_verify_token")
    def test_webhook_verification_wrong_token(self):
        from messenger.api.views import MetaWebhookView
        request = self.factory.get(
            "/api/v1/messenger/webhook/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "WRONG_TOKEN",
                "hub.challenge": "CHALLENGE_CODE_12345",
            },
        )
        view = MetaWebhookView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)

    @override_settings(META_APP_SECRET="test_secret")
    def test_webhook_post_invalid_hmac_rejected(self):
        from messenger.api.views import MetaWebhookView
        body = b'{"object":"page","entry":[]}'
        request = self.factory.post(
            "/api/v1/messenger/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalidsignature",
        )
        view = MetaWebhookView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)

    @override_settings(META_APP_SECRET="test_secret")
    @patch("messenger.api.views.process_inbound_message")
    def test_webhook_post_valid_hmac_returns_200(self, mock_task):
        from messenger.api.views import MetaWebhookView
        body = json.dumps({"object": "page", "entry": []}).encode()
        sig = self._make_signature(body)
        request = self.factory.post(
            "/api/v1/messenger/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sig,
        )
        view = MetaWebhookView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Comment Auto-Reply deduplication
# ---------------------------------------------------------------------------

class CommentAutoReplyDedupTests(TestCase):
    def setUp(self):
        from shops.models import Shop, SubscriptionPlan
        plan, _ = SubscriptionPlan.objects.get_or_create(name="FREE")
        self.shop = Shop.objects.create(name="Shop", subdomain="dedupshop", plan=plan)

    @patch("messenger.services.comment_autoreply.reply_to_comment")
    @patch("messenger.services.comment_autoreply.send_generic_template")
    def test_duplicate_comment_skipped(self, mock_send, mock_reply):
        """A second comment from the same PSID on the same post must be skipped."""
        from messenger.services.comment_autoreply import handle_comment_auto_reply
        from catalog.models import Product, ProductStatus
        from catalog.models import Category

        cat, _ = Category.objects.get_or_create(
            shop=self.shop, name="Cat", defaults={"tenant_id": self.shop.id}
        )
        product = Product.objects.create(
            shop=self.shop, tenant_id=self.shop.id, name="T-shirt",
            base_price="500.00", slug="tshirt", category=cat,
            status=ProductStatus.PUBLISHED,
        )
        from catalog.models import ProductVariant
        ProductVariant.objects.create(
            shop=self.shop, tenant_id=self.shop.id, product=product,
            stock_quantity=10, is_active=True,
        )

        kwargs = dict(
            shop_id=str(self.shop.id),
            page_id="PAGE1",
            psid="USER1",
            post_id="POST1",
            comment_id="CMT1",
            page_access_token="TOKEN",
            product_ids=[str(product.id)],
        )

        result1 = handle_comment_auto_reply(**kwargs)
        result2 = handle_comment_auto_reply(**kwargs)

        self.assertTrue(result1)   # first call sends DM
        self.assertFalse(result2)  # second call is deduplicated
        self.assertEqual(mock_send.call_count, 1)

    @patch("messenger.services.comment_autoreply.reply_to_comment")
    @patch("messenger.services.comment_autoreply.send_generic_template")
    def test_stock_zero_freezes_dm(self, mock_send, mock_reply):
        """If product is out of stock, DM must NOT be sent."""
        from messenger.services.comment_autoreply import handle_comment_auto_reply
        from catalog.models import Product, ProductStatus
        from catalog.models import Category

        cat, _ = Category.objects.get_or_create(
            shop=self.shop, name="Cat2", defaults={"tenant_id": self.shop.id}
        )
        product = Product.objects.create(
            shop=self.shop, tenant_id=self.shop.id, name="OOS Product",
            base_price="200.00", slug="oos-product", category=cat,
            status=ProductStatus.PUBLISHED,
        )

        result = handle_comment_auto_reply(
            shop_id=str(self.shop.id),
            page_id="PAGE1",
            psid="USER2",
            post_id="POST2",
            comment_id="CMT2",
            page_access_token="TOKEN",
            product_ids=[str(product.id)],
        )

        self.assertFalse(result)
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Human Takeover API
# ---------------------------------------------------------------------------

class HumanTakeoverAPITests(TestCase):
    def setUp(self):
        from shops.models import Shop, SubscriptionPlan, ShopMember
        plan, _ = SubscriptionPlan.objects.get_or_create(name="FREE")
        self.shop = Shop.objects.create(name="TakeoverShop", subdomain="takeovershop", plan=plan)
        self.user = User.objects.create_user(email="agent@test.com", password="pass")
        ShopMember.objects.create(user=self.user, shop=self.shop, role="MANAGER")
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("messenger.api.views.bot_state_set_human_active")
    def test_takeover_sets_human_active(self, mock_set):
        self.client.credentials(HTTP_X_TENANT_ID=str(self.shop.id))
        resp = self.client.post(
            "/api/v1/messenger/takeover/",
            {"page_id": "P1", "psid": "U1", "action": "takeover"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_set.assert_called_once_with(page_id="P1", psid="U1", ttl_minutes=30)

    @patch("messenger.api.views.bot_state_clear_human_active")
    def test_handback_clears_human_active(self, mock_clear):
        self.client.credentials(HTTP_X_TENANT_ID=str(self.shop.id))
        resp = self.client.post(
            "/api/v1/messenger/takeover/",
            {"page_id": "P1", "psid": "U1", "action": "handback"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_clear.assert_called_once_with(page_id="P1", psid="U1")
