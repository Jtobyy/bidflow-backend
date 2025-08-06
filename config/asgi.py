import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import notifications.routing

def get_websocket_app():
    from notifications.channels_jwt_auth import JWTAuthMiddleware
    return JWTAuthMiddleware(
        URLRouter(notifications.routing.websocket_urlpatterns)
    )

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": get_websocket_app(),
})
