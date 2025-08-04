# notifications/models.py

from django.db import models
from django.conf import settings
from company.models import Company  # or import from wherever

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)  # e.g. {type: "bid_status", bid_id: 5}
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optionally: action_type, related_object (GenericForeignKey), etc

    def __str__(self):
        return f"To: {self.recipient} | {self.message[:50]}"
