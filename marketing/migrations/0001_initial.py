# Generated manually for v0.4 social foundations

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
        ("shops", "0005_shop_base_currency"),
    ]

    operations = [
        migrations.CreateModel(
            name="WaitlistEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True)),
                ("phone_number", models.CharField(max_length=20)),
                ("survey_data", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("CLAIMED", "Claimed"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("invite_token", models.UUIDField(blank=True, null=True, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="SocialConnection",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("tenant_id", models.UUIDField(db_index=True, help_text="Tenant that owns this record")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "provider",
                    models.CharField(
                        choices=[("META", "Meta (Facebook)")],
                        default="META",
                        max_length=20,
                    ),
                ),
                ("page_id", models.CharField(max_length=100)),
                ("page_name", models.CharField(max_length=255)),
                ("access_token", models.TextField()),
                ("token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_refreshed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("EXPIRED", "Expired"),
                            ("DISCONNECTED", "Disconnected"),
                        ],
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("last_error", models.TextField(blank=True)),
                (
                    "shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_connections",
                        to="shops.shop",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["shop", "provider", "status"],
                        name="socconn_shop_prov_status_ix",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProductSocialPostLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("tenant_id", models.UUIDField(db_index=True, help_text="Tenant that owns this record")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("idempotency_key", models.CharField(max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[("QUEUED", "Queued"), ("SUCCESS", "Success"), ("FAILED", "Failed")],
                        default="QUEUED",
                        max_length=20,
                    ),
                ),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                ("external_post_id", models.CharField(blank=True, max_length=120)),
                ("error_message", models.TextField(blank=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                (
                    "connection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="post_logs",
                        to="marketing.socialconnection",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_post_logs",
                        to="catalog.product",
                    ),
                ),
                (
                    "shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_post_logs",
                        to="shops.shop",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["shop", "product", "status"],
                        name="socpost_shop_prod_status_ix",
                    ),
                    models.Index(fields=["connection", "created_at"], name="social_post_conn_created_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="socialconnection",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("shop", "provider", "page_id"),
                name="uq_social_connection_shop_provider_page_active",
            ),
        ),
        migrations.AddConstraint(
            model_name="productsocialpostlog",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("shop", "idempotency_key"),
                name="uq_social_post_shop_idempotency_active",
            ),
        ),
    ]
