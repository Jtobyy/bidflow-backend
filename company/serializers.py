# companies/serializers.py
from rest_framework import serializers
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'address', 'phone', 'website',
            'rc_number', 'logo', 'description', 'type'
        ]
