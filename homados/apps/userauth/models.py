from django.db import models

# Create your models here.


class Log(models.Model):
    """系统操作日志表"""
    ltype = models.CharField(max_length=20, verbose_name='日志类型')
    info = models.TextField(verbose_name='信息')
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
