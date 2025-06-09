from rest_framework import viewsets, permissions
from .models import Bid
from .serializers import BidSerializer

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
        serializer.save(submitted_by=self.request.user)

    def get_queryset(self):
        """
        Optionally filter bids by the current user.
        """
        if self.request.user.is_superuser:
            return Bid.objects.all()
        return Bid.objects.filter(submitted_by=self.request.user)
