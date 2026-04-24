import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_orderrefundevent"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourierConsignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("PATHAO", "Pathao"),
                            ("PAPERFLY", "Paperfly"),
                            ("STEADFAST", "Steadfast"),
                            ("OTHER", "Other"),
                        ],
                        default="OTHER",
                        max_length=20,
                    ),
                ),
                ("external_consignment_id", models.CharField(max_length=120)),
                ("tracking_code", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("CREATED", "Created"),
                            ("DISPATCHED", "Dispatched"),
                            ("IN_TRANSIT", "In Transit"),
                            ("DELIVERED", "Delivered"),
                            ("FAILED", "Failed"),
                            ("RTO", "Return To Origin"),
                        ],
                        default="CREATED",
                        max_length=20,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consignments",
                        to="orders.order",
                    ),
                ),
                (
                    "shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="courier_consignments",
                        to="shops.shop",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["shop", "status", "created_at"], name="courier_shop_stat_cr_ix"),
                    models.Index(fields=["provider", "external_consignment_id"], name="courier_prov_ext_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=["provider", "external_consignment_id"], name="uq_courier_provider_extid")
                ],
            },
        ),
    ]
