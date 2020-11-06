# 一些后台任务
import threading
from dbmsf.models import Host
from homados.contrib.cache import MsfCache
from libs.pymetasploit.jsonrpc import MsfJsonRpc
from django.conf import settings


msfcache = MsfCache()

msfjsonrpc = MsfJsonRpc(
    server=settings.MSFCONFIG['HOST'],
    port=settings.MSFCONFIG['JSONRPC']['PORT'],
    token=settings.MSFCONFIG['JSONRPC']['TOKEN'],
)

logger = settings.LOGGER


class UpdateHostsInfoThread(threading.Thread):
    """根据现有存活会话更新主机列表存活状态"""
    def __init__(self, sessions):
        super().__init__()
        self.sessions = sessions
    
    def run(self):
        sess_hosts = []
        for sid, session in self.sessions.items():
            sess_hosts.append(session['session_host'])
        Host.objects.exclude(address__in=sess_hosts).filter(state='alive').update(state='down')


class ListenerCacheAddThread(threading.Thread):
    """增加监听器缓存配置
    
    Attributes:
        listener_config: 监听器配置
    """
    def __init__(self, jid):
        super().__init__()
        self.jid = jid
    
    def run(self):
        listener_config = msfjsonrpc.jobs.info(self.jid)
        msfcache.add_listener(listener_config)


class ListenerCacheDelThread(threading.Thread):
    """删除监听器缓存配置
    
    Attributes:
        jid: 监听器job id
    """
    def __init__(self, jid):
        super().__init__()
        self.jid = int(jid)
    
    def run(self):
        msfcache.del_listener_with_jid(self.jid)


class ListenerCacheRecoverThread(threading.Thread):
    """监听器恢复"""
    def run(self):
        # 依次创建监听器
        listeners = msfcache.get_listeners()
        for addr, listener_config in listeners.items():
            module_exploit = msfjsonrpc.modules.use('exploit', 'exploit/multi/handler')
            module_payload = ''
            datastore = listener_config['datastore']
            for k, v in datastore.items():
                if k == 'PAYLOAD':
                    module_payload = msfjsonrpc.modules.use('payload', v)
                module_exploit[k] = v
            result = module_exploit.execute(payload=module_payload)
            logger.info(f'初始化创建监听器返回: {result}')
            listeners[addr]['jid'] = int(result['job_id'])
        # 更新监听器缓存
        msfcache.bulk_update_listeners(listeners)
