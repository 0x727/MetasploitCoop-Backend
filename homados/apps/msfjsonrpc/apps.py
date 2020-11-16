from django.apps import AppConfig
import os


class MsfjsonrpcConfig(AppConfig):
    name = 'msfjsonrpc'

    def ready(self):
        # 判断 RUN_MAIN 主要原因是因为测试环境保证只运行一次，参见
        # https://stackoverflow.com/questions/33814615/how-to-avoid-appconfig-ready-method-running-twice-in-django/40602348
        if os.environ.get('RUN_MAIN', None) != 'true':
            try:
                self._restore_listen()
            except Exception as e:
                print('msf jsonrpc service not started')

    def _restore_listen(self):
        """恢复msf监听器"""
        from . import background
        listeners = background.msfjsonrpc.jobs.list
        if len(listeners) > 0:
            return
        background.ListenerCacheRecoverThread().start()
