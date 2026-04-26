from django.db import migrations
from pgvector.django import VectorExtension as BaseVectorExtension

class VectorExtension(BaseVectorExtension):
    @property
    def hints(self):
        return getattr(self, '_hints', {})
    @hints.setter
    def hints(self, value):
        self._hints = value

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        VectorExtension(),
    ]
