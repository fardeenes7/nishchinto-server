from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AIModelRegistry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "usage",
                    models.CharField(
                        choices=[
                            ("CHAT_COMPLETION", "Chat Completion"),
                            ("EMBEDDING", "Embedding"),
                            ("IMAGE_GENERATION", "Image Generation"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("OPENAI", "OpenAI"),
                            ("ANTHROPIC", "Anthropic"),
                            ("STABILITY", "Stability AI"),
                            ("CUSTOM", "Custom"),
                        ],
                        default="OPENAI",
                        max_length=20,
                    ),
                ),
                ("model_name", models.CharField(max_length=100)),
                ("display_name", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False)),
                ("priority", models.PositiveIntegerField(default=100)),
                ("input_price_per_1m_tokens", models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True)),
                ("output_price_per_1m_tokens", models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True)),
                ("image_price_per_call", models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "ordering": ["usage", "priority", "model_name"],
            },
        ),
        migrations.AddIndex(
            model_name="aimodelregistry",
            index=models.Index(fields=["usage", "is_active", "priority"], name="ai_model_usage_active_pri_idx"),
        ),
        migrations.AddIndex(
            model_name="aimodelregistry",
            index=models.Index(fields=["provider", "usage"], name="ai_model_provider_usage_idx"),
        ),
        migrations.AddConstraint(
            model_name="aimodelregistry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("usage", "provider", "model_name"),
                name="uq_ai_model_usage_provider_model_active",
            ),
        ),
        migrations.AddConstraint(
            model_name="aimodelregistry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default", True), ("deleted_at__isnull", True)),
                fields=("usage",),
                name="uq_ai_model_single_default_per_usage",
            ),
        ),
    ]
