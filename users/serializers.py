# users/serializers.py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    # If company is a FK, show the company name (or a nested serializer)
    company_name = serializers.CharField(source='company.name', read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar', 'role', 'company', 'company_name']
        # If company is required on create/update, remove read_only on 'company'
