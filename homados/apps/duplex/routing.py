from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
    path(r'ws/msf/console/', consumers.MsfConsoleCustomer),
    path(r'ws/msf/notify/', consumers.MsfNotifyCustomer),
]