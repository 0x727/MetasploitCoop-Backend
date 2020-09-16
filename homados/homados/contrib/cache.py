from django.core.cache import caches
from functools import partial


class DistinctCacheProxy:
    """根据不同的前缀进行区分开来的缓存"""
    def __init__(self, ident_name='', cache_name='default'):
        self.cache = caches[cache_name]
        self.ident_name = ident_name

    def __getattr__(self, name):
        if hasattr(self.cache, name):
            return partial(self.method_missing, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def method_missing(self, name: str, *args, **kwargs):
        # 如果以下划线开头不代理
        if name.startswith('_'):
            return getattr(self, name)
        # 带有_many后缀的特殊处理，详见 django.core.cache.backends.db.DatabaseCache 的成员方法
        if name.endswith('_many'):
            if 'keys' in kwargs:
                key = kwargs.pop('keys')
            else:
                key = args.pop(0)
            if not isinstance(key, list):
                raise TypeError('keys arguments error')
            for idx, val in enumerate(key):
                key[idx] = self.get_key(val)
        else:
            if 'key' in kwargs:
                key = kwargs.pop('key')
            else:
                key = args.pop(0)
            if not isinstance(key, str):
                raise TypeError('key arguments error')
            key = self.get_key(key)
        method = getattr(self.cache, name)
        return method(key, *args, **kwargs)

    def get_key(self, key):
        if not self.ident_name or not isinstance(self.ident_name, str):
            return key
        return ':'.join([self.ident_name, key])

    def msfconsole_history_add(self, key, value):
        if not value:
            return
        key = self.get_key(key)
        history = self.cache.get(key) or []
        history.insert(0, value)
        self.cache.set(key, history)
