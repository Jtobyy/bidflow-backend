from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from channels.db import database_sync_to_async

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        token = None

        # Authorization header
        auth_header = headers.get(b'authorization', b'').decode()
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token = params.get("token", [None])[0]

        print(f'token: {token}')
        user = AnonymousUser()
        if token:
            try:
                validated_token = JWTAuthentication().get_validated_token(token)
                # This is the critical line: wrap ORM in sync_to_async
                user = await database_sync_to_async(JWTAuthentication().get_user)(validated_token)
            except Exception as e:
                print('JWT ERROR:', e)
                pass

        scope["user"] = user
        return await self.inner(scope, receive, send)
