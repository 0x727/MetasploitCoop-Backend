import json
import threading
import chardet
from django.conf import settings
from rest_framework.exceptions import ValidationError
from userauth.serializers import LogSerializer
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
from ratelimit import limits, sleep_and_retry

logger = settings.LOGGER


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


def get_user_ident(user):
    """获取用户身份"""
    return getattr(user, 'username', '') or getattr(user, 'email', '')


def report_event(msg, data=None, ltype='default', level='info', callback=None):
    """事件报告写入日志"""
    try:
        data = {
            'ltype': ltype,
            'info': {
                'msg': msg,
                'data': data,
            },
            'level': level,
        }
        serializer = LogSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if callback and callable(callback):
            callable(data)
    except ValidationError as e:
        logger.error(f'写入日志错误: {e}')

def report_auth_event(msg, callback=None):
    report_event(msg, ltype='auth', callback=callback)

def report_msfjob_event(msg, callback=None):
    report_event(msg, ltype='msfjob', callback=callback)

def memview_to_str(data):
    data_bytes = data.tobytes()
    result = chardet.detect(data_bytes)
    encoding = result['encoding'] if result.get('encoding') else 'utf-8'
    return data_bytes.decode(encoding)


@sleep_and_retry
@limits(calls=5, period=60)
def get_translation_from_qq(text):
    """从腾讯翻译君翻译字符"""
    # 腾讯接口每秒5次频率限制
    try: 
        cred = credential.Credential(settings.TENCENT_TRANSLATE_TOKEN['SecretId'], settings.TENCENT_TRANSLATE_TOKEN['SecretKey']) 
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tmt.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = tmt_client.TmtClient(cred, "ap-shanghai", clientProfile) 

        req = models.TextTranslateRequest()
        params = {
            "SourceText": text,
            "Source": "en",
            "Target": "zh",
            "ProjectId": 0
        }
        req.from_json_string(json.dumps(params))

        resp = client.TextTranslate(req)
        result = resp.to_json_string()
        data = json.loads(result)
        return data.get('TargetText', '')

    except TencentCloudSDKException as e: 
        logger.exception(e)
