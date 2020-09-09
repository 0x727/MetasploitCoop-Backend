from ._base import *
import os


DEBUG = True


ALLOWED_HOSTS = ['*']


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'homados',
        'USER': os.getenv('HOMADOS_PG_USER') or 'postgres',
        'PASSWORD': os.getenv('HOMADOS_PG_PASS') or '19971030',
        'HOST': os.getenv('HOMADOS_PG_SERVER') or '192.168.174.136',
        'PORT': os.getenv('HOMADOS_PG_PORT') or '5433',
    },
    'msf': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'msf',
        'USER': 'msf',
        'PASSWORD': 'qzteRjxSmkJaXZKo4E5xaIXVxr1POUy8JyheinJmgrk=',
        'HOST': '192.168.174.136',
        'PORT': '5433',
    }
}


DATABASE_ROUTERS = ['homados.contrib.dbrouters.MsfRouter']


# msf 服务端相关配置

MSFCONFIG = {
    'HOST': os.getenv('MSF_HOST') or '192.168.174.136',
    'JSONRPC': {
        'PORT': os.getenv('MSF_JSONRPC_PORT') or '55553',
        'TOKEN': os.getenv('MSF_WS_JSON_RPC_API_TOKEN') or 'homados',
    },
}