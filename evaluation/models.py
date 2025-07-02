from django.db import models
from bids.models import Bid
from users.models import User

EVALUATION_METHOD_CHOICES = [
    ('QCBS', 'Quality and Cost Based Selection'),
    ('QBS', 'Quality Based Selection'),
]

class Evaluation(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='evaluations')
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    method = models.CharField(max_length=10, choices=EVALUATION_METHOD_CHOICES, default='QCBS')
    
    # Scores
    technical_score = models.DecimalField(max_digits=5, decimal_places=2)
    financial_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    compliance_status = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('bid', 'evaluator')  # One evaluation per bid per evaluator

    def __str__(self):
        return f"Evaluation for Bid #{self.bid.id} by {self.evaluator.username}"
