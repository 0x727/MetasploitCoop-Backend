from django.db import models
from rubymarshal import reader
import base64


class RubyHashField(models.TextField):
    """读取数据库中存入的ruby"""
    def to_python(self, value):
        byte_text = base64.b64decode(value.encode())
        data = reader.loads(byte_text)
        return self.convert_to_dict(data)

    def convert_to_dict(self, value: dict):
        result = {}
        for k, v in value.items():
            # str(v) 主要是为了防止有些RubyString捣鬼
            # str(k)[1:] 主要是因为 k 为 Symbol，例如 Symbol("WORKSPACE") str 后为 ":WORKSPACE"
            k, v = str(k)[1:], str(v)
            if v in ('true', 'false'):
                result[k] = True if v.lower() == 'true' else False
            elif v.isdigit():
                result[k] = int(v)
            elif v == '':
                result[k] = None
            else:
                result[k] = v
        return result

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)


class UnlimitedCharField(models.CharField):
    """没有max_length校验的CharField"""
    def __init__(self, *args, **kwargs):
        # not a typo: we want to skip CharField.__init__ because that adds the max_length validator
        super(models.CharField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        # likewise, want to skip CharField.__check__
        return super(models.CharField, self).check(**kwargs)
