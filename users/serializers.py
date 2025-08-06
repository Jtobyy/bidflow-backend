# users/serializers.py
from rest_framework import serializers
from .models import User
from company.serializers import CompanySerializer


class UserSerializer(serializers.ModelSerializer):
    # If company is a FK, show the company name (or a nested serializer)
    company = CompanySerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar', 'company']
        # If company is required on create/update, remove read_only on 'company'
