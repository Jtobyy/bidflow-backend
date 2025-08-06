from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from datetime import timedelta


User = get_user_model()

class Tender(models.Model):
    """
    Represents a procurement opportunity published by a procuring entity.

    A tender defines the *requirements* for a project or service that vendors can bid for.
    It includes the project title, description, submission deadline, current status, and
    the user (usually an admin or procurement officer) who created it.

    In BidFlow:
    - A **tender** is what the government/agency is offering (e.g. "Supply of Laptops").
    - A **bid** is what a vendor submits in response to a tender.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),         # Not visible to vendors yet
        ('published', 'Published'), # Visible, accepting bids
        ('closed', 'Closed'),       # Deadline passed
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tenders')
    created_at = models.DateTimeField(auto_now_add=True)
    required_documents = ArrayField(
        models.CharField(max_length=50),
        default=list,
        help_text="List of required document types (e.g., CAC, TIN, TAX_CERT, TCC, ISO_PECB)"
    )
    
    tender_document = models.FileField(upload_to='tender_docs/', null=True, blank=True)
    extra_documents = models.FileField(upload_to='tender_extras/', null=True, blank=True)

    @property
    def is_open(self):
        return self.status == 'published' and self.deadline > timezone.now()
    
    @property
    def is_closed(self):
        return self.status == 'closed' or (self.status == 'published' and self.deadline <= timezone.now())

    def __str__(self):
        return self.title
