from rest_framework import viewsets, permissions, serializers, status, filters
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
from tenders.models import Tender
from django.utils import timezone
from django.db.models import Q
from ai.compliance.engine import run_compliance_check



class BidViewSet(viewsets.ModelViewSet):
    """
    Handles creation and retrieval of bids.

    Users can:
    - Create bids (including uploading multiple documents inline)
    - View their own bids
    - Superusers can view all bids
    """

    queryset = Bid.objects.all().select_related('tender', 'submitted_by', 'submitted_by__company')
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = [
        'tender__title',
        'tender__id',
        'submitted_by__username',
        'submitted_by__email',
        'submitted_by__company__name',   # if User → company FK exists
        # '^price'   # numbers aren’t great with SearchFilter; leave out or handle separately
    ]
    ordering_fields = ['submitted_at', 'price', 'score', 'rank']
    ordering = ['-submitted_at']

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

        tender_id = request.data.get('tender')
        price = request.data.get('price')
        print("Tender is", tender_id)

        try:
            tender = Tender.objects.get(pk=tender_id)
        except Tender.DoesNotExist:
            return Response({"detail": "Invalid tender."}, status=status.HTTP_400_BAD_REQUEST)

        if tender.status == "closed" or tender.deadline <= timezone.now():
            return Response(
                {"detail": "This tender is closed. You cannot submit a bid."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data={
            'tender': tender_id,
            'price': price,
            'documents': documents
        })

        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except IntegrityError:
            raise ValidationError({"detail": "You have already submitted a bid for this tender."})

        bid = serializer.instance 
        procurer = tender.created_by

        notify_user(
            recipient=procurer,
            message=f"A new bid was submitted to your tender '{tender.title}'",
            data={"type": "bid_submitted", "tender_id": tender.id, "bid_id": bid.id}
        )


        return Response(serializer.data, status=201)

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # Vendors: only their bids
        if not user.is_superuser:
            # If this endpoint is used by both vendors & procurers, allow procurers to see
            # bids submitted to their tenders as well.
            qs = qs.filter(
                Q(submitted_by=user) |
                Q(tender__created_by=user)
            ).distinct()

        return qs

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

        # Flatten all single-valued fields in request.data
        data = flatten_dict(dict(request.data))
        data['documents'] = documents

        serializer = self.get_serializer(
            instance,
            data=data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Notify...
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
    Allows vendors to manage their own documents and procurers (tender owners)
    to verify/fail documents submitted to their tenders.
    """
    queryset = BidDocument.objects.all()
    serializer_class = BidDocumentReadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        if u.is_superuser:
            return BidDocument.objects.all()
        # vendor (submitted_by) OR procurer (tender.created_by)
        return BidDocument.objects.filter(
            Q(bid__submitted_by=u) | Q(bid__tender__created_by=u)
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        # Only procurer (tender owner) or superuser may change verification
        if not (user.is_superuser or user == instance.bid.tender.created_by):
            return Response(
                {"detail": "Only the procurer may update verification status."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Whitelist fields you allow to change via PATCH
        allowed = {"verification_status", "extracted_data"}
        data = {k: v for k, v in request.data.items() if k in allowed}

        if "verification_status" in data:
            val = str(data["verification_status"]).lower()
            if val not in {"pending", "verified", "failed"}:
                return Response(
                    {"verification_status": "Invalid value (use pending|verified/failed)."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            data["verification_status"] = val

        if not data:
            return Response(
                {"detail": "No updatable fields provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        instance = self.get_object()
        if not (request.user.is_superuser or request.user == instance.bid.tender.created_by):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        instance.verification_status = "verified"
        instance.save(update_fields=["verification_status"])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        instance = self.get_object()
        if not (request.user.is_superuser or request.user == instance.bid.tender.created_by):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        instance.verification_status = "failed"
        instance.save(update_fields=["verification_status"])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def reverify(self, request, pk=None):
        instance = self.get_object()
        u = request.user
        # allow superuser, tender owner (procurer), or the submitting vendor to re-run
        if not (u.is_superuser or u == instance.bid.tender.created_by or u == instance.bid.submitted_by):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        updated = reverify_document(instance)
        return Response(self.get_serializer(updated).data)

def flatten_dict(data):
    """
    Convert any single-valued list to its scalar value.
    Example: {'foo': ['bar']} => {'foo': 'bar'}
    """
    result = {}
    for k, v in data.items():
        # v could be a list or scalar
        if isinstance(v, list) and len(v) == 1:
            result[k] = v[0]
        else:
            result[k] = v
    return result
