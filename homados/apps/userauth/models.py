from django.db import models

# Create your models here.


class Log(models.Model):
    """系统操作日志表"""
    SUCCESS = 'success'
    INFO = 'info'
    WARNING = 'warning'
    DANGER = 'danger'
    LEVEL_CHOICES = [
        (SUCCESS, 'success'),
        (INFO, 'info'),
        (WARNING, 'warning'),
        (DANGER, 'danger'),
    ]
    ltype = models.CharField(max_length=20, verbose_name='日志类型')
    info = models.TextField(verbose_name='信息')
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=INFO, verbose_name='日志等级')
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
