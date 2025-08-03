from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Tender
from .serializers import TenderSerializer
from bids.models import Bid
from ai.compliance.engine import run_compliance_check, rank_bids_for_tender
from bids.serializers import BidSerializer

class TenderViewSet(viewsets.ModelViewSet):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="process_bids")
    def process_bids(self, request, pk=None):
        tender = self.get_object()
        bids = Bid.objects.filter(tender=tender)

        if not bids.exists():
            return Response({"detail": "No bids submitted yet."}, status=400)

        for bid in bids:
            run_compliance_check(bid)

        rank_bids_for_tender(tender.id)

        return Response({"detail": "Bids processed and ranked successfully."})
    
    @action(detail=True, methods=['get'])
    def bids(self, request, pk=None):
        tender = self.get_object()
        bids = Bid.objects.filter(tender=tender)
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)
