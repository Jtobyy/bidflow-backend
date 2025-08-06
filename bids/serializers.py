from rest_framework import serializers
from .models import Bid, BidDocument
from company.serializers import CompanySerializer
from tenders.serializers import TenderSerializer
from tenders.models import Tender


class BidDocumentInlineSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=[c[0] for c in BidDocument.DOCUMENT_TYPE_CHOICES])
    custom_document_name = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField()

    def validate(self, data):
        if data['document_type'] == 'OTHER' and not data.get('custom_document_name'):
            raise serializers.ValidationError({
                'custom_document_name': 'This field is required when document_type is OTHER.'
            })
        return data

class BidDocumentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = BidDocument
        fields = '__all__'

class BidSerializer(serializers.ModelSerializer):
    documents = BidDocumentInlineSerializer(many=True, write_only=True, required=False)
    uploaded_documents = BidDocumentReadSerializer(source='documents', many=True, read_only=True)
    company = CompanySerializer(source='submitted_by.company', read_only=True)
    tender = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(),
        write_only=False  # it can be used for both
    )


    class Meta:
        model = Bid
        fields = [
            'id', 'tender', 'submitted_by', 'company', 'price', 'submitted_at', 'status',
            'documents', 'uploaded_documents', 'score', 'rank'
        ]
        read_only_fields = [
            'id', 'submitted_by', 'company', 'submitted_at', 'status',
            'uploaded_documents', 'score', 'rank'
        ]

    def to_representation(self, instance):
        # Start with the default representation (IDs etc)
        ret = super().to_representation(instance)
        # Now override 'tender' to serialize as object
        ret['tender'] = TenderSerializer(instance.tender, context=self.context).data
        return ret

    def create(self, validated_data):
        documents_data = validated_data.pop('documents', [])
        validated_data['submitted_by'] = self.context['request'].user
        bid = Bid.objects.create(**validated_data)
        for doc_data in documents_data:
            BidDocument.objects.create(bid=bid, **doc_data)
        return bid

    def update(self, instance, validated_data):
        documents_data = validated_data.pop('documents', [])
        instance.price = validated_data.get('price', instance.price)
        instance.save()

        for doc_data in documents_data:
            doc_type = doc_data['document_type']
            existing_doc = instance.documents.filter(document_type=doc_type).first()

            if existing_doc:
                # Update the existing file
                existing_doc.file = doc_data['file']
                if doc_type == 'OTHER':
                    existing_doc.custom_document_name = doc_data.get('custom_document_name', '')
                existing_doc.save()
            else:
                BidDocument.objects.create(bid=instance, **doc_data)

        return instance
    
    def get_company(self, obj):
        # Handle missing user or missing company
        if obj.submitted_by and hasattr(obj.submitted_by, "company") and obj.submitted_by.company:
            return {
                "id": obj.submitted_by.company.id,
                "name": obj.submitted_by.company.name
            }
        return None