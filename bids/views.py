from rest_framework import viewsets, permissions, serializers
from .models import Bid, BidDocument
from .serializers import BidSerializer, BidDocumentReadSerializer, BidDocumentInlineSerializer
from django.db import IntegrityError
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from compliance.models import ComplianceCheck
from compliance.serializers import ComplianceCheckSerializer
from notifications.utils import notify_user
from decimal import Decimal, InvalidOperation
from rest_framework.exceptions import ValidationError




class BidViewSet(viewsets.ModelViewSet):
    """
    Handles creation and retrieval of bids.

    Users can:
    - Create bids (including uploading multiple documents inline)
    - View their own bids
    - Superusers can view all bids
    """

    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def create(self, request, *args, **kwargs):
        documents = []
        i = 0
        while f'documents[{i}][file]' in request.FILES:
            documents.append({
                'file': request.FILES.get(f'documents[{i}][file]'),
                'document_type': request.data.get(f'documents[{i}][document_type]'),
                'custom_document_name': request.data.get(f'documents[{i}][custom_document_name]'),
            })
            i += 1

        tender = request.data.get('tender')
        price = request.data.get('price')

        serializer = self.get_serializer(data={
            'tender': tender,
            'price': price,
            'documents': documents
        })

        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except IntegrityError:
            raise ValidationError({"detail": "You have already submitted a bid for this tender."})

        tender = Tender.objects.get(pk=tender)

        bid_user = request.user
        notify_user(
            recipient=procurer,
            message=f"A new bid was submitted to your tender '{tender.title}'",
            data={"type": "bid_submitted", "tender_id": tender.id, "bid_id": bid.id}
        )

        return Response(serializer.data, status=201)



    def get_queryset(self):
        if self.request.user.is_superuser:
            return Bid.objects.all()
        return Bid.objects.filter(submitted_by=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        documents = []
        i = 0
        while f'documents[{i}][file]' in request.FILES or f'documents[{i}][document_type]' in request.data:
            documents.append({
                'file': request.FILES.get(f'documents[{i}][file]'),
                'document_type': request.data.get(f'documents[{i}][document_type]'),
                'custom_document_name': request.data.get(f'documents[{i}][custom_document_name]'),
            })
            i += 1

        partial = kwargs.pop('partial', True)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data={**request.data, 'documents': documents},
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Notify the procurer
        procurer = instance.tender.created_by
        notify_user(
            recipient=procurer,
            message=f"A bid was updated for your tender '{instance.tender.title}'",
            data={"type": "bid_updated", "tender_id": instance.tender.id, "bid_id": instance.id}
        )

        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def generate_report(self, request, pk=None):
        bid = self.get_object()
        compliance = run_compliance_check(bid)
        serializer = ComplianceCheckSerializer(compliance)

        notify_user(
            recipient=bid.submitted_by,
            message=f"Your bid for '{bid.tender.title}' was processed — result: {'✅ Compliant' if compliance.is_compliant else '❌ Not Compliant'}",
            data={"type": "bid_compliance", "bid_id": bid.id}
        )
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        bid = self.get_object()
        tender = bid.tender
        bid_id = bid.id
        self.perform_destroy(bid)

        # Notify the procurer
        procurer = tender.created_by
        notify_user(
            recipient=procurer,
            message=f"A bid was deleted from your tender '{tender.title}'",
            data={"type": "bid_deleted", "tender_id": tender.id, "bid_id": bid_id}
        )

        return Response(status=status.HTTP_204_NO_CONTENT)




class BidDocumentViewSet(viewsets.ModelViewSet):
    """
    Handles standalone operations for bid documents (optional if you're using inline upload).
    
    Allows vendors to:
    - List their own documents
    - Upload new documents separately (if not using inline)
    """

    queryset = BidDocument.objects.all()
    serializer_class = BidDocumentReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return BidDocument.objects.all()
        return BidDocument.objects.filter(bid__submitted_by=self.request.user)
