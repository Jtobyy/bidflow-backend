from django.db import models
from bids.models import Bid

class ComplianceCheck(models.Model):
    bid = models.OneToOneField(Bid, on_delete=models.CASCADE, related_name='compliance')
    is_compliant = models.BooleanField(default=False)
    missing_documents = models.JSONField(default=list, blank=True, null=True)
    failed_documents = models.JSONField(default=list, blank=True, null=True)
    document_scores = models.JSONField(default=dict, blank=True, null=True)
    evaluation = models.JSONField(default=dict, blank=True, null=True) 
    proposal_score = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Compliance Check for Bid #{self.bid.id}"
