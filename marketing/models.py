from django.db import models
import uuid

from core.models import TenantModel

class WaitlistEntry(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CLAIMED', 'Claimed'),
    )

    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20)
    survey_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    invite_token = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} ({self.status})"


class SocialProvider(models.TextChoices):
    META = "META", "Meta (Facebook)"


class SocialConnectionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    DISCONNECTED = "DISCONNECTED", "Disconnected"


class SocialPostStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class SocialConnection(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="social_connections")
    provider = models.CharField(max_length=20, choices=SocialProvider.choices, default=SocialProvider.META)
    page_id = models.CharField(max_length=100)
    page_name = models.CharField(max_length=255)
    access_token = models.TextField()
    token_expires_at = models.DateTimeField(null=True, blank=True)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SocialConnectionStatus.choices, default=SocialConnectionStatus.ACTIVE)
    last_error = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["shop", "provider", "status"], name="social_conn_shop_provider_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "provider", "page_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_social_connection_shop_provider_page_active",
            )
        ]

    def __str__(self):
        return f"{self.shop_id}::{self.provider}::{self.page_name}"


class ProductSocialPostLog(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="social_post_logs")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="social_post_logs")
    connection = models.ForeignKey("marketing.SocialConnection", on_delete=models.PROTECT, related_name="post_logs")
    idempotency_key = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=SocialPostStatus.choices, default=SocialPostStatus.QUEUED)
    retry_count = models.PositiveSmallIntegerField(default=0)
    external_post_id = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["shop", "product", "status"], name="social_post_shop_product_status_idx"),
            models.Index(fields=["connection", "created_at"], name="social_post_conn_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "idempotency_key"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_social_post_shop_idempotency_active",
            )
        ]

    def __str__(self):
        return f"{self.product_id}::{self.connection_id}::{self.status}"
