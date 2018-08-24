# coding: utf-8

import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.conf import settings


class TwitchChatConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
            settings.WEBSOCKET_CHANNEL,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            settings.WEBSOCKET_CHANNEL,
            self.channel_name
        )
    #
    # def receive(self, text_data=None, bytes_data=None):
    #     text_data_json = json.loads(text_data)
    #     message = text_data_json['message']
    #
    #     async_to_sync(self.channel_layer.group_send)(
    #         WEBSOCKET_CHANNEL,
    #         {
    #             'type': 'chat_message',
    #             'message': message
    #         }
    #     )
    #
    # Receive message from room group
    def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))
