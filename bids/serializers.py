# bids/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Bid, BidDocument
from company.serializers import CompanySerializer
from tenders.serializers import TenderSerializer
from tenders.models import Tender
from compliance.serializers import ComplianceCheckSerializer
from ai.utils.humanize import humanize_doc_result  # <- your humanizer

User = get_user_model()


class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class BidDocumentInlineSerializer(serializers.Serializer):
    """
    Write-only serializer used when creating/updating a bid with documents inline.
    No humanized fields here.
    """
    document_type = serializers.ChoiceField(choices=[c[0] for c in BidDocument.DOCUMENT_TYPE_CHOICES])
    custom_document_name = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField()

    def validate(self, data):
        if data['document_type'] == 'OTHER' and not data.get('custom_document_name'):
            raise serializers.ValidationError({
                'custom_document_name': 'This field is required when document_type is OTHER.'
            })
        return data


class BidMiniSerializer(serializers.ModelSerializer):
    tender = serializers.SerializerMethodField()
    submitted_by = UserLiteSerializer(read_only=True)
    company = CompanySerializer(source="submitted_by.company", read_only=True)

    class Meta:
        model = Bid
        fields = ["id", "price", "submitted_at", "status", "score", "rank", "tender", "submitted_by", "company"]

    def get_tender(self, obj):
        return {"id": obj.tender.id, "title": obj.tender.title}

class BidDocumentReadSerializer(serializers.ModelSerializer):
    report_text = serializers.SerializerMethodField()
    bid = BidMiniSerializer(read_only=True)  # <- embed mini bid

    class Meta:
        model = BidDocument
        fields = [
            "id", "bid", "document_type", "custom_document_name", "file",
            "uploaded_at", "extracted_data", "verification_status",
            "report_text",
        ]

    def get_report_text(self, obj):
        try:
            return humanize_doc_result(obj)
        except Exception:
            return None

class BidSerializer(serializers.ModelSerializer):
    # Write-only docs for create/update
    documents = BidDocumentInlineSerializer(many=True, write_only=True, required=False)

    # Read-only uploaded docs (with report_text)
    uploaded_documents = BidDocumentReadSerializer(source='documents', many=True, read_only=True)

    # Company (from the submitting user)
    company = CompanySerializer(source='submitted_by.company', read_only=True)

    # Tender can be written as PK; we expand it on output
    tender = serializers.PrimaryKeyRelatedField(queryset=Tender.objects.all(), write_only=False)

    # Small user payload
    submitted_by = UserLiteSerializer(read_only=True)

    # Include saved compliance check (make sure your ComplianceCheckSerializer adds `report_text`)
    compliance = ComplianceCheckSerializer(read_only=True)

    class Meta:
        model = Bid
        fields = [
            'id', 'tender', 'submitted_by', 'company',
            'price', 'submitted_at', 'status',
            'documents',              # write-only input
            'uploaded_documents',     # read-only output (with report_text)
            'score', 'rank',
            'compliance',             # read-only
        ]
        read_only_fields = [
            'id', 'submitted_by', 'company', 'submitted_at', 'status',
            'uploaded_documents', 'score', 'rank', 'compliance',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Expand tender object for reads
        data['tender'] = TenderSerializer(instance.tender, context=self.context).data
        return data

    def create(self, validated_data):
        documents_data = validated_data.pop('documents', [])
        validated_data['submitted_by'] = self.context['request'].user
        bid = Bid.objects.create(**validated_data)
        for doc in documents_data:
            BidDocument.objects.create(bid=bid, **doc)
        return bid

    def update(self, instance, validated_data):
        documents_data = validated_data.pop('documents', [])
        instance.price = validated_data.get('price', instance.price)
        instance.save(update_fields=['price'])

        # Upsert documents by type
        for doc in documents_data:
            doc_type = doc['document_type']
            existing = instance.documents.filter(document_type=doc_type).first()
            if existing:
                existing.file = doc['file']
                if doc_type == 'OTHER':
                    existing.custom_document_name = doc.get('custom_document_name', '')
                existing.save()
            else:
                BidDocument.objects.create(bid=instance, **doc)

        return instance
