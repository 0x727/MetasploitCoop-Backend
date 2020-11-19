from threading import Thread
from django.apps import AppConfig
import os
import time


class MsfjsonrpcConfig(AppConfig):
    name = 'msfjsonrpc'

    def ready(self):
        # 判断 RUN_MAIN 主要原因是因为测试环境保证只运行一次，参见
        # https://stackoverflow.com/questions/33814615/how-to-avoid-appconfig-ready-method-running-twice-in-django/40602348
        if os.environ.get('RUN_MAIN', None) != 'true':
            t = Thread(target=self._retry_restore_listen, daemon=True)
            t.start()

    def _retry_restore_listen(self):
        """重试恢复msf监听器"""
        from . import background
        while True:
            try:
                listeners = background.msfjsonrpc.jobs.list
                if len(listeners) > 0:
                    return
                background.ListenerCacheRecoverThread().start()
                break
            except Exception as e:
                print('msf jsonrpc service not started')
                time.sleep(5)
