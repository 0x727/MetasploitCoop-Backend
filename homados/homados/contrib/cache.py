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


class MsfConsoleCache(DistinctCacheProxy):
    CACHE_MSFCONSOLE_INPUT_CACHE = 'msfconsole:input:cache'
    CACHE_MSFCONSOLE_HISTORY_CACHE = 'msfconsole:history:cache'
    CACHE_MSFCONSOLE_HISTORY_CURSOR = 'msfconsole:history:cursor'

    def msfconsole_history_add(self, value):
        if not value:
            return
        key = self.get_key(self.CACHE_MSFCONSOLE_HISTORY_CACHE)
        history = self.cache.get(key) or []
        self.cache.set(self.get_key(self.CACHE_MSFCONSOLE_HISTORY_CURSOR), 0, None)  # 重置光标
        history.insert(0, value)
        self.cache.set(key, history, None)

    @property
    def msfconsole_history(self):
        key = self.get_key(self.CACHE_MSFCONSOLE_HISTORY_CACHE)
        return self.cache.get(key) or []

    @property
    def msfconsole_input_cache(self):
        key = self.get_key(self.CACHE_MSFCONSOLE_INPUT_CACHE)
        return self.cache.get(key) or ''

    @property
    def msfconsole_history_cursor(self):
        key = self.get_key(self.CACHE_MSFCONSOLE_HISTORY_CURSOR)
        return self.cache.get(key) or 0
    
    def msfconsole_input_cache_clear(self):
        key = self.get_key(self.CACHE_MSFCONSOLE_INPUT_CACHE)
        self.cache.delete(key)

    def msfconsole_input_cache_backspace(self):
        key = self.get_key(self.CACHE_MSFCONSOLE_INPUT_CACHE)
        input_cache = self.cache.get(key)
        if not input_cache:
            return "\u0007"
        else:
            self.cache.set(key, input_cache[0:-1], None)
            return "\b\u001b[K"

    def msfconsole_input_cache_append(self, data):
        input_cache = self.msfconsole_input_cache
        if not input_cache:
            self.cache.set(self.get_key(self.CACHE_MSFCONSOLE_INPUT_CACHE), data, None)
            return data
        else:
            self.cache.set(self.get_key(self.CACHE_MSFCONSOLE_INPUT_CACHE), input_cache + data, None)
            return input_cache + data

    def msfconsole_input_cache_clear_online(self):
        input_cache = self.msfconsole_input_cache
        if not input_cache:
            return "\u0007"
        else:
            self.cache.set(self.get_key(self.CACHE_MSFCONSOLE_INPUT_CACHE), "", None)
            return "\b\u001b[K" * len(input_cache)

    def msfconsole_history_cache_last(self):
        history = self.msfconsole_history
        if not history:
            return ''
        cursor = self.msfconsole_history_cursor
        self.cache.set(self.get_key(self.CACHE_MSFCONSOLE_HISTORY_CURSOR), cursor + 1, None)  # 重置光标
        cursor = cursor % len(history)
        return history[cursor]

    def msfconsole_history_cache_next(self):
        history = self.msfconsole_history
        if not history:
            return ''
        cursor = self.msfconsole_history_cursor
        if not cursor:
            self.cache.set(self.get_key(self.CACHE_MSFCONSOLE_HISTORY_CURSOR), 0, None)
            return ''
        else:
            self.cache.set(self.get_key(self.CACHE_MSFCONSOLE_HISTORY_CURSOR), cursor - 1, None)  # 重置光标
        cursor = cursor % len(history)
        return history[cursor]

