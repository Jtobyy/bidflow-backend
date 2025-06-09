from django.db import models
from django.conf import settings
from tenders.models import Tender

class Bid(models.Model):
    """
    Represents a bid submitted by a user (vendor) for a specific tender.

    Each bid is linked to:
    - A `Tender` published by a procuring entity.
    - A `User` (typically a bidder/vendor) who submitted the bid.

    The model stores essential bid submission details, such as:
    - attached documents
    - proposed price
    - timestamp of submission
    - current status (e.g., pending, reviewed, disqualified, accepted)

    This model forms the foundation for further evaluation and compliance checks.
    """
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bids')
    documents = models.FileField(upload_to='bids/documents/', blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('reviewed', 'Reviewed'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('disqualified', 'Disqualified'),
        ],
        default='pending'
    )

    class Meta:
        unique_together = ('tender', 'submitted_by')  # Prevent duplicate bids

    def __str__(self):
        return f"Bid by {self.submitted_by.username} for {self.tender.title}"
