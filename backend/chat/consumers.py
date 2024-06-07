# support/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        self.agent_group_name = f'chat_{self.agent_id}'

        # Join agent group
        await self.channel_layer.group_add(
            self.agent_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave agent group
        await self.channel_layer.group_discard(
            self.agent_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to agent group
        await self.channel_layer.group_send(
            self.agent_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def chat_message(self, event):
        message = event['message']
        print(message)

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
