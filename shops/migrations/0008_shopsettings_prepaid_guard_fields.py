from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0007_v0_6_messenger_faq_greeting_keywords'),
    ]

    operations = [
        migrations.AddField(
            model_name='shopsettings',
            name='prepaid_misuse_consecutive_limit',
            field=models.PositiveSmallIntegerField(default=5),
        ),
        migrations.AddField(
            model_name='shopsettings',
            name='uses_platform_courier_credentials',
            field=models.BooleanField(default=False),
        ),
    ]
