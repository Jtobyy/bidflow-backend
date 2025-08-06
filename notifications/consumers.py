from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Set a group for this user, e.g., by user ID or username
        user = self.scope['user']
        if user.is_anonymous:
            await self.close(code=403)
            return
        self.group_name = f"user_{user.id}"  # or whatever scheme you want
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Only call group_discard if group_name is set
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Optional: handle messages from the client
        data = json.loads(text_data)
        # do something, or just pass

    async def send_notification(self, event):
        # This is the handler for group sends
        print('event ', event)
        await self.send(text_data=json.dumps(event["notification"]))
