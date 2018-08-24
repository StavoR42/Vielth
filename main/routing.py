# coding: utf-8
# from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from chat_app.routing import websocket_urlpatterns


application = ProtocolTypeRouter({
    'websocket': URLRouter(websocket_urlpatterns),
})
