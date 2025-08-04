# notifications/serializers.py

from rest_framework import serializers
from .models import Notification
from users.serializers import UserSerializer  # Import your existing UserSerializer

class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(read_only=True)  # Use nested serializer

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'message', 'data', 'read', 'created_at']
