from rest_framework import serializers
from .models import WaitlistEntry

class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = ('id', 'email', 'phone_number', 'survey_data', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')
