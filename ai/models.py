from django.db import models


# ai/models.py
class DocumentSuggestion(models.Model):
    name = models.CharField(max_length=120, unique=True)  # e.g., "Work Plan"
    count = models.PositiveIntegerField(default=0)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected')],
        default='pending'
    )
    last_tender = models.ForeignKey('tenders.Tender', null=True, blank=True, on_delete=models.SET_NULL)

class DocumentCatalog(models.Model):
    """
    Global list of known document types your UI/API can serve as options.
    """
    key = models.SlugField(unique=True)         # "CAC", "TECHNICAL_PROPOSAL"
    label = models.CharField(max_length=120)    # "CAC", "Technical Proposal"
    envelope = models.CharField(
        max_length=15,
        choices=[('TECHNICAL','TECHNICAL'),('FINANCIAL','FINANCIAL'),('ADMIN','ADMIN'),('NONE','NONE')],
        default='ADMIN'
    )
    verifiable = models.BooleanField(default=False)  # you have a parser for it
    parser_code = models.CharField(max_length=100, blank=True)  # tie to your verifier
    is_system = models.BooleanField(default=False)   # lock core items from delete

