# coding: utf-8

from django.conf.urls import url

from chat_app.consumers import TwitchChatConsumer


websocket_urlpatterns = [
    url(r'^ws/twitch-chat/$', TwitchChatConsumer),
]
