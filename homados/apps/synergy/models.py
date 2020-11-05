from django.db import models
from django.conf import settings


class ChatRecord(models.Model):
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, db_constraint=False, verbose_name='用户')
    message = models.TextField(default='', verbose_name='信息')
    room = models.CharField(max_length=200, verbose_name='聊天室名')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'chat_records'
