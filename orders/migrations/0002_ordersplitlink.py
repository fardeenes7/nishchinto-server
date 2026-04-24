import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderSplitLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('split_mode', models.CharField(choices=[('BACKORDER_SPLIT', 'Backorder Split'), ('ITEM_CANCEL', 'Item Cancel')], default='BACKORDER_SPLIT', max_length=20)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('child_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='split_links_as_child', to='orders.order')),
                ('parent_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='split_links_as_parent', to='orders.order')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['parent_order', 'created_at'], name='ordsplit_parent_created_ix'),
                    models.Index(fields=['child_order', 'created_at'], name='ordsplit_child_created_ix'),
                ],
            },
        ),
    ]
