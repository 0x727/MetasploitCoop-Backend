from django.db import models
from homados.contrib.fields import RubyHashField, UnlimitedCharField


class Session(models.Model):
    """会话表"""
    id = models.AutoField(primary_key=True)
    host_id = models.IntegerField(verbose_name='主机id')
    stype = UnlimitedCharField(verbose_name='会话类型')
    via_exploit = UnlimitedCharField(verbose_name='使用的exp')
    via_payload = UnlimitedCharField(verbose_name='使用的payload')
    desc = UnlimitedCharField(null=True, verbose_name='描述')
    port = models.IntegerField(verbose_name='端口')
    platform = UnlimitedCharField(verbose_name='描述')
    datastore = RubyHashField(verbose_name='基本信息')
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField()
    close_reason = UnlimitedCharField(blank=True, verbose_name='关闭原因')
    local_id = models.IntegerField(verbose_name='本地会话id')
    last_seen = models.DateTimeField()
    module_run_id = models.IntegerField(null=True)

    class Meta:
        db_table = 'sessions'


class SessionEvent(models.Model):
    """会话事件表"""
    id = models.AutoField(primary_key=True)
    session = models.ForeignKey(to='dbmsf.Session', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='session_id', related_name='session_events', verbose_name='会话id')
    etype = UnlimitedCharField(verbose_name='事件类型')
    command = models.BinaryField(verbose_name='命令')
    output = models.BinaryField(verbose_name='输出')
    remote_path = UnlimitedCharField()
    local_path = UnlimitedCharField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'session_events'
