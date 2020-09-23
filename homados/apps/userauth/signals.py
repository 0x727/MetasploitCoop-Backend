from django.db.models import signals
from django.dispatch import receiver
import channels
import json
from asgiref.sync import async_to_sync
from duplex.consumers import CustomerGroup
from .models import Log
from .serializers import LogSerializer


channel_layer = channels.layers.get_channel_layer()


@receiver(signals.post_save, sender=Log)
def migrate_notify_post(instance, created, **kwargs):
    if created:
        message = {
            'type': 'homados',
            'action': 'log',
            'data': LogSerializer(instance).data
        }
        async_to_sync(channel_layer.group_send)(
            CustomerGroup.Notify,
            {
                'type': 'send_message',
                'message': json.dumps(message)
            }
        )
