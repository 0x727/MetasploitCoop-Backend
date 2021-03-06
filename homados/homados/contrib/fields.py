import base64
import json
import chardet
import traceback

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from rest_framework.fields import Field, JSONField
from rubymarshal import reader
from rubymarshal.classes import Symbol, RubyObject
logger = settings.LOGGER


class UnlimitedCharField(models.CharField):
    """没有max_length校验的CharField"""

    def __init__(self, *args, **kwargs):
        # not a typo: we want to skip CharField.__init__ because that adds the max_length validator
        super(models.CharField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        # likewise, want to skip CharField.__check__
        return super(models.CharField, self).check(**kwargs)


class MyJSONField(Field):
    default_error_messages = {
        'invalid': _('Value must be valid JSON.')
    }

    def __init__(self, *args, **kwargs):
        self.ensure_ascii = kwargs.pop('ensure_ascii', True)
        self.encoder = kwargs.pop('encoder', None)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        try:
            return json.dumps(data, cls=self.encoder, ensure_ascii=self.ensure_ascii)
        except (TypeError, ValueError):
            self.fail('invalid')
        return data

    def to_representation(self, value):
        value = json.loads(value, cls=self.encoder)
        return value


class RubyJSONField(JSONField):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _to_python(self, value):
        # super().to_python(value)
        if not isinstance(value, str):
            return value
        try:
            byte_text = base64.b64decode(value.encode())
            data = reader.loads(byte_text)
            if isinstance(data, dict):
                return self._convert_to_dict(data)
            elif isinstance(data, bytes):
                res = chardet.detect(data)
                return data.decode(res['encoding'] or 'utf-8')
            elif isinstance(data, RubyObject):
                return str(data)
            return data
        except Exception as e:
            logger.exception(f'RubyHashField出现解析问题 {str(e)}')
            return ''

    def _convert_to_dict(self, value: dict):
        result = {}
        for k, v in value.items():
            # 处理key
            new_k = ''
            if isinstance(k, Symbol):
                new_k = str(k)[1:]
            elif isinstance(k, bytes):
                new_k = k.decode()
            else:
                new_k = str(k)
            # 处理value
            new_v = ''
            if isinstance(v, str):
                if v in ('true', 'false'):
                    new_v = True if v.lower() == 'true' else False
                elif v.isdigit():
                    new_v = int(v)
                elif v == '':
                    new_v = None
                else:
                    new_v = str(v)
            elif isinstance(v, bytes):
                new_v = v.decode()
            elif isinstance(v, dict):
                new_v = self._convert_to_dict(v)
            else:
                new_v = str(v)
            result[new_k] = new_v
        return result

    def to_representation(self, value):
        if self.binary:
            value = json.dumps(value, cls=self.encoder)
            value = value.encode()
        value = self._to_python(value)
        return value
