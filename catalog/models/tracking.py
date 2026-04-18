"""
ShopTrackingConfig — marketing pixel/analytics configuration per shop.

Gated by FeatureGate: only Basic+ plans can configure tracking pixels.
This model is auto-created alongside the Shop via a post_save signal.
"""
import uuid

from django.db import models


class ShopTrackingConfig(models.Model):
    """
    Stores merchant-provided analytics/tracking IDs.
    Referenced by the Storefront's TrackingProvider component to conditionally
    inject <Script> tags for FB Pixel, GA4, and GTM.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.OneToOneField(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="tracking_config",
    )

    # Facebook Pixel
    fb_pixel_id = models.CharField(max_length=50, blank=True)

    # Google Analytics 4
    ga4_measurement_id = models.CharField(
        max_length=50, blank=True,
        help_text="Format: G-XXXXXXXXXX"
    )

    # Google Tag Manager
    gtm_id = models.CharField(
        max_length=50, blank=True,
        help_text="Format: GTM-XXXXXXX"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop Tracking Config"
        verbose_name_plural = "Shop Tracking Configs"

    def __str__(self):
        return f"Tracking config for {self.shop}"
