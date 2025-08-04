# notifications/utils.py

from .models import Notification

def notify_user(recipient, message, data=None):
    Notification.objects.create(
        recipient=recipient,
        message=message,
        data=data or {}
    )
