from rest_framework import serializers
from .models import Tender
from bids.models import Bid
from compliance.models import ComplianceCheck
from users.serializers import UserSerializer

class TenderSerializer(serializers.ModelSerializer):
    total_bids = serializers.SerializerMethodField()
    compliant_bids = serializers.SerializerMethodField()
    bid_scores = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Tender
        fields = '__all__'
        read_only_fields = ['total_bids', 'compliant_bids', 'bid_scores', 'created_by']

    def get_total_bids(self, obj):
        return obj.bids.count()

    def get_compliant_bids(self, obj):
        return ComplianceCheck.objects.filter(bid__tender=obj, is_compliant=True).count()

    def get_bid_scores(self, obj):
        bids = obj.bids.all().select_related("compliance").order_by("-score")
        return [
            {
                "bid_id": bid.id,
                "vendor": bid.submitted_by.username,
                "score": bid.score,
                "rank": bid.rank,
                "status": bid.status,
            }
            for bid in bids
        ]
