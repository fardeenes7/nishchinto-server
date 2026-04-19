"""
Migration: Add base_currency to Shop model.

Decision B (post_v03_debrief.md, Fix 6.9):
  Shop.base_currency is the single source of truth for a shop's currency.
  All price fields (base_price, price_override) inherit from Shop.base_currency —
  they do NOT carry their own currency metadata.
  Default is BDT. Live exchange rate sync is out of scope for v1.0.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shops", "0004_subscriptionplan_shop_override_max_staff_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="shop",
            name="base_currency",
            field=models.CharField(
                max_length=3,
                default="BDT",
                help_text=(
                    "ISO 4217 currency code for this shop. All price fields inherit "
                    "from this value — individual prices do not carry their own currency. "
                    "Example: BDT, USD, EUR."
                ),
            ),
        ),
    ]
