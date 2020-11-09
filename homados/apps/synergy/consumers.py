import json

from asgiref.sync import async_to_sync
from django.conf import settings
from homados.contrib import mychannels
from rest_framework.exceptions import ValidationError
from synergy import serializers


logger = settings.LOGGER


class ChatConsumer(mychannels.AuthCustomer):
    # 推送消息的行为定义
    _actions = ['join', 'chat', 'exit']

    def connect(self):
        super().connect()
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self._send_message('join')

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

        self._send_message('exit')

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # save message to chat records database
        self._save_chat_record(message)
        
        # Send message to room group
        self._send_message('chat', message)

    # Receive message from room group
    def chat_message(self, event):
        data = event['data']

        assert isinstance(data, dict), '发送消息必须是字典形式'

        # Send message to WebSocket
        self.send(text_data=json.dumps(data))
    
    def _save_chat_record(self, message):
        """保存聊天记录到数据库"""
        try:
            data = {
                'user': self.scope['user'].pk,
                'username': self.scope['user'].username,
                'message': message,
                'room': self.room_name,
            }
            serializer = serializers.ChatRecordSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except ValidationError as e:
            logger.error(f'保存聊天记录出错: {e}')
    
    def _send_message(self, action, message=None):
        assert action in self._actions, 'action must be one of %s' % repr(list(self._actions))

        data = {
            'message': message,
            'user_id': self.scope['user'].pk,
            'username': self.scope['user'].username,
            'action': action,
        }

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'data': data,
            }
        )
