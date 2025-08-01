from rest_framework import viewsets, permissions, serializers
from .models import Bid, BidDocument
from .serializers import BidSerializer, BidDocumentReadSerializer, BidDocumentInlineSerializer
from django.db import IntegrityError
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response


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
                'custom_document_name': request.data.get(f'documents[{i}][custom_document_name]'),  # <-- add this
            })
            i += 1

        # Explicitly extract flat values
        tender = request.data.get('tender')
        price = request.data.get('price')

        # Assemble clean data for serializer
        serializer = self.get_serializer(data={
            'tender': tender,
            'price': price,
            'documents': documents
        })

        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Bid.objects.all()
        return Bid.objects.filter(submitted_by=self.request.user)


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
