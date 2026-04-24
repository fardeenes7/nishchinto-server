import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_ordersplitlink"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderRefundEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="BDT", max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[("REQUESTED", "Requested"), ("COMPLETED", "Completed")],
                        default="REQUESTED",
                        max_length=20,
                    ),
                ),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("inventory_reversed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="order_refund_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_events",
                        to="orders.order",
                    ),
                ),
                (
                    "shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="order_refund_events",
                        to="shops.shop",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["shop", "order", "created_at"], name="ordrefund_shop_ord_cr_idx"),
                    models.Index(fields=["shop", "status", "created_at"], name="ordrefund_shop_st_cr_idx"),
                ]
            },
        )
    ]
