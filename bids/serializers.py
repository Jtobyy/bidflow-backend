from rest_framework import serializers
from .models import Bid

class BidSerializer(serializers.ModelSerializer):
    """
    Serializes Bid objects for API operations.

    Includes key bid attributes: tender reference, bidder, price, document, status.
    The `submitted_by` field is read-only and auto-filled from the request user.
    """

    class Meta:
        model = Bid
        fields = ['id', 'tender', 'submitted_by', 'price', 'document', 'submitted_at', 'status']
        read_only_fields = ['id', 'submitted_by', 'submitted_at', 'status']

    def create(self, validated_data):
        validated_data['submitted_by'] = self.context['request'].user
        return super().create(validated_data)
