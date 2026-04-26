from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_courierconsignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                blank=True,
                choices=[('COD', 'Cash on Delivery'), ('PREPAID', 'Prepaid / Online')],
                max_length=20,
                null=True,
            ),
        ),
    ]
