from ._base import *
import os


DEBUG = True


LOGGER = logging.getLogger("dev")


ALLOWED_HOSTS = ['*']


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

_pg_user = os.getenv('HOMADOS_PG_USER') or 'postgres'
_pg_pass = os.getenv('HOMADOS_PG_PASS') or 'homados@123'
_pg_host = os.getenv('HOMADOS_PG_SERVER') or '127.0.0.1'
_pg_port = os.getenv('HOMADOS_PG_PORT') or '5432'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'homados',
        'USER': _pg_user,
        'PASSWORD': _pg_pass,
        'HOST': _pg_host,
        'PORT': _pg_port,
    },
    'msf': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'msf',
        'USER': _pg_user,
        'PASSWORD': _pg_pass,
        'HOST': _pg_host,
        'PORT': _pg_port,
    },
    'kbase': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
}


# msf 服务端相关配置

MSFCONFIG = {
    'HOST': os.getenv('MSF_HOST') or '127.0.0.1',
    'JSONRPC': {
        'PORT': os.getenv('MSF_JSONRPC_PORT') or '55553',
        'TOKEN': os.getenv('MSF_WS_JSON_RPC_API_TOKEN') or 'homados',
    },
}

# 通道层
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}


# 腾讯翻译君 api token
TENCENT_TRANSLATE_TOKEN = {
    'SecretId': os.getenv('TENCENT_TRANSLATE_TOKEN_ID') or '',
    'SecretKey': os.getenv('TENCENT_TRANSLATE_TOKEN_KEY') or ''
}

from libs.pymetasploit.jsonrpc import MsfJsonRpc
MSFJSONRPC = MsfJsonRpc(server=MSFCONFIG['HOST'], port=MSFCONFIG['JSONRPC']['PORT'], token=MSFCONFIG['JSONRPC']['TOKEN'])
