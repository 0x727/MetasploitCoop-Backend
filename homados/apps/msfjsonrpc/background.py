# 一些后台任务
import threading
from dbmsf.models import Host

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
