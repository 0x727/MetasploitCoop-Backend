from logging import info
from django.db import models
from requests.sessions import session
from homados.contrib.fields import RubyHashField, UnlimitedCharField


class Workspace(models.Model):
    """工作区表"""
    id = models.AutoField(primary_key=True)
    name = UnlimitedCharField(verbose_name='名称')
    created_at = models.DateTimeField(verbose_name='创建时间')
    updated_at = models.DateTimeField(verbose_name='更新时间')
    boundary = models.CharField(max_length=4096)
    description = models.CharField(max_length=4096, verbose_name='描述')
    owner_id = models.IntegerField(verbose_name='创建者')
    limit_to_network = models.BooleanField()
    import_fingerprint = models.BooleanField()

    class Meta:
        db_table = 'workspaces'


class Event(models.Model):
    """时间表"""
    id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(to='dbmsf.Workspace', db_constraint=False, on_delete=models.DO_NOTHING, 
                            db_column='workspace_id', related_name='events', verbose_name='工作区id')
    host = models.ForeignKey(to='dbmsf.Host', db_constraint=False, on_delete=models.DO_NOTHING, 
                            db_column='host_id', related_name='events', verbose_name='主机id')
    created_at = models.DateTimeField(verbose_name='创建时间')
    updated_at = models.DateTimeField(verbose_name='更新时间')
    name = UnlimitedCharField(verbose_name='事件名')
    critical = models.BooleanField(verbose_name='是否重要')
    seen = models.BooleanField()
    username = UnlimitedCharField()
    info = RubyHashField(verbose_name='事件信息')

    class Meta:
        db_table = 'events'


class Host(models.Model):
    """主机表"""
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField()
    address = models.GenericIPAddressField()
    mac = UnlimitedCharField()
    comm = UnlimitedCharField()
    name = UnlimitedCharField()
    state = UnlimitedCharField()
    os_name = UnlimitedCharField()
    os_flavor = UnlimitedCharField()
    os_sp = UnlimitedCharField()
    os_lang = UnlimitedCharField()
    arch = UnlimitedCharField()
    workspace_id = models.IntegerField(verbose_name='工作区id')
    updated_at = models.DateTimeField()
    purpose = models.TextField()
    info = models.CharField(max_length=65535)
    comments = models.TextField()
    scope = models.TextField()
    virtual_host = models.TextField()
    note_count = models.IntegerField()
    vuln_count = models.IntegerField()
    service_count = models.IntegerField()
    host_detail_count = models.IntegerField()
    exploit_attempt_count = models.IntegerField()
    cred_count = models.IntegerField()
    detected_arch = UnlimitedCharField()
    os_family = UnlimitedCharField()

    class Meta:
        db_table = 'hosts'


class Session(models.Model):
    """会话表"""
    id = models.AutoField(primary_key=True)
    host = models.ForeignKey(to='dbmsf.Host', db_constraint=False, on_delete=models.DO_NOTHING, 
                            db_column='host_id', related_name='sessions', verbose_name='主机id')
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


class ModuleResult(models.Model):
    """模块结果表"""
    id = models.AutoField(primary_key=True)
    session = models.ForeignKey(to='dbmsf.Session', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='session_id', related_name='module_results', verbose_name='会话id')
    track_uuid = models.CharField(max_length=20, verbose_name='执行模块任务uuid')
    fullname = models.CharField(max_length=200, verbose_name='模块名')
    output = models.BinaryField(verbose_name='输出')
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'module_results'


class Service(models.Model):
    """服务表"""
    id = models.AutoField(primary_key=True)
    host = models.ForeignKey(to='dbmsf.Host', db_constraint=False, on_delete=models.DO_NOTHING, 
                            db_column='host_id', related_name='services', verbose_name='主机id')
    created_at = models.DateTimeField()
    port = models.IntegerField(verbose_name='端口')
    proto = models.CharField(max_length=16, verbose_name='传输层协议')
    state = UnlimitedCharField(verbose_name='协议')
    name = UnlimitedCharField(verbose_name='应用层协议名')
    updated_at = models.DateTimeField()
    info = models.TextField()

    class Meta:
        db_table = 'services'


class MetasploitCredentialLogin(models.Model):
    """cred login"""
    id = models.AutoField(primary_key=True)
    core = models.ForeignKey(to='dbmsf.MetasploitCredentialCore', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='core_id', related_name='cred_logins', verbose_name='核心表关联')
    service = models.ForeignKey(to='dbmsf.Service', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='service_id', related_name='cred_logins', verbose_name='核心表关联')
    access_level = UnlimitedCharField()
    status = UnlimitedCharField()
    last_attempted_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'metasploit_credential_logins'


class MetasploitCredentialPrivate(models.Model):
    """cred private"""
    id = models.AutoField(primary_key=True)
    type = UnlimitedCharField()
    data = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    jtr_format = UnlimitedCharField()

    class Meta:
        db_table = 'metasploit_credential_privates'


class MetasploitCredentialPublic(models.Model):
    """cred public"""
    id = models.AutoField(primary_key=True)
    username = UnlimitedCharField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    type = UnlimitedCharField()

    class Meta:
        db_table = 'metasploit_credential_publics'


class MetasploitCredentialRealm(models.Model):
    """cred realm"""
    id = models.AutoField(primary_key=True)
    key = UnlimitedCharField()
    value = UnlimitedCharField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'metasploit_credential_realms'


class MetasploitCredentialOriginSession(models.Model):
    """cred origin session"""
    id = models.AutoField(primary_key=True)
    post_reference_name = models.TextField(verbose_name='post模块名')
    session = models.ForeignKey(to='dbmsf.Session', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='session_id', related_name='cred_origins', verbose_name='会话id')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'metasploit_credential_origin_sessions'


class MetasploitCredentialCore(models.Model):
    id = models.AutoField(primary_key=True)
    origin_type = UnlimitedCharField()
    origin = models.ForeignKey(to='dbmsf.MetasploitCredentialOriginSession', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='origin_id', related_name='cred_core')
    private = models.ForeignKey(to='dbmsf.MetasploitCredentialPrivate', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='private_id', related_name='cred_core')
    public = models.ForeignKey(to='dbmsf.MetasploitCredentialPublic', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='public_id', related_name='cred_core')
    realm = models.ForeignKey(to='dbmsf.MetasploitCredentialRealm', db_constraint=False, on_delete=models.DO_NOTHING, 
                                db_column='realm_id', related_name='cred_core')
    workspace_id = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    logins_count = models.IntegerField()

    """cred核心表"""
    class Meta:
        db_table = 'metasploit_credential_cores'
