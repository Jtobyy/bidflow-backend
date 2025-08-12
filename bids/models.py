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
    price = models.DecimalField(max_digits=12, decimal_places=2)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rank = models.PositiveIntegerField(null=True, blank=True)
    
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

class BidDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('TECHNICAL_PROPOSAL', 'Technical Proposal'),
        ('FINANCIAL_PROPOSAL', 'Financial Proposal'),
        ('CAC', 'CAC'),
        ('TIN', 'TIN'),
        ('TCC', 'TCC'),
        ('ISO_PECB', 'ISO PECB'),
        ('OTHER', 'Other'),
    ]

    bid = models.ForeignKey('Bid', on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        help_text="Type of document (e.g., CAC, TIN, etc. Use 'Other' if not listed)"
    )
    custom_document_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Only required if document_type is 'OTHER'"
    )
    file = models.FileField(upload_to='bids/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_data = models.JSONField(null=True, blank=True)  # parsed fields
    verification_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('verified', 'Verified'), ('failed', 'Failed')],
        default='pending'
    )

    class Meta:
        unique_together = ('bid', 'document_type')

    def __str__(self):
        return f"{self.document_type or 'Other'} - {self.custom_document_name or ''}"
