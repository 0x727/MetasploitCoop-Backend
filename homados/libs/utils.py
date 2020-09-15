import threading

class Singleton(type):
    """单例模式基类"""
    _lock = threading.Lock()
    def __init__(self, *args, **kwargs):
        self.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        if self.__instance is None:
            with Singleton._lock:
                if self.__instance is None:
                    self.__instance = super().__call__(*args, **kwargs)
        return self.__instance

    def __new__(cls, *args, **kwargs):
        instance = type.__new__(cls, *args, **kwargs)
        return instance
