from rest_framework import serializers
from .models import ComplianceCheck

class ComplianceCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceCheck
        fields = '__all__'
        read_only_fields = ['verified_at']
