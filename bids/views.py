from rest_framework import viewsets, permissions
from .models import Bid
from .serializers import BidSerializer
from django.db import IntegrityError
from rest_framework import serializers


class BidViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for bids.

    Only authenticated users (bidders) can create bids.
    Read operations are allowed for all authenticated users.
    """

    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        try:
            serializer.save(submitted_by=self.request.user)
        except IntegrityError:
            # Return a clear JSON error response
            raise serializers.ValidationError({
                "detail": "You have already submitted a bid for this tender. Multiple submissions are not allowed."
            })
            
    def get_queryset(self):
        """
        Optionally filter bids by the current user.
        """
        if self.request.user.is_superuser:
            return Bid.objects.all()
        return Bid.objects.filter(submitted_by=self.request.user)
