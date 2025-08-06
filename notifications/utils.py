from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def notify_user(recipient, message, data=None):
    from .models import Notification
    notif = Notification.objects.create(
        recipient=recipient,
        message=message,
        data=data or {}
    )

    # Send via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{recipient.id}",
        {
            "type": "send_notification",
            "notification": {
                "id": notif.id,
                "message": notif.message,
                "data": notif.data,
                "read": notif.read,
                "created_at": notif.created_at.isoformat()
            }
        }
    )
