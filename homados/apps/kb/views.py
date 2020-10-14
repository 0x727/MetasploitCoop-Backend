from django.conf import settings
from django.db.models import Count
from django_filters import rest_framework as rich_filters
from homados.contrib.exceptions import MissParamError, MSFJSONRPCError
from homados.contrib.mymixins import PackResponseMixin
from libs.pymetasploit.jsonrpc import MsfJsonRpc, MsfRpcError
from libs.utils import get_translation_from_qq
from msfjsonrpc.models import Modules
from rest_framework import exceptions, filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from kb.filters import FocusKeywordFilter, MsfModuleManualFilter
from kb.models import FocusKeyword, MsfModuleManual, TranslationBase
from kb.serializers import (FocusKeywordSerializer, MsfModuleManualSerializer,
                            TranslationBaseSerializer)

msfjsonrpc = MsfJsonRpc(
    server=settings.MSFCONFIG['HOST'],
    port=settings.MSFCONFIG['JSONRPC']['PORT'],
    token=settings.MSFCONFIG['JSONRPC']['TOKEN'],
)


class MsfModuleManualViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = MsfModuleManual.objects.all()
    serializer_class = MsfModuleManualSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [rich_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MsfModuleManualFilter

    def list(self, request, *args, **kwargs):
        # 如果模块翻译不存在则进行自动翻译
        if request.query_params.get('fullname', ''):
            count = self.filter_queryset(self.get_queryset()).count()
            if count == 0:
                self.auto_translate(request)
        return super().list(request, *args, **kwargs)

    @action(methods=['GET'], detail=False, url_path='autoTranslate')
    def auto_translate(self, request, *args, **kwargs):
        try:
            fullname = request.query_params['fullname']
            # 判断模块是否已有翻译
            manual = Modules.objects.filter(fullname=fullname).first()
            if manual:
                serializer = self.get_serializer(manual)
                return Response(data=serializer.data)
            # 没有翻译则进行机器翻译
            msfmodule = self._get_msfmodule(fullname)
            if msfmodule is None:
                raise exceptions.NotFound
            data = {
                'fullname': fullname
            }
            options = msfmodule.options
            data['title'] = self._get_translate(msfmodule.name)
            data['intro'] = self._get_translate(msfmodule.description)
            options_trans = {}
            for k, v in options.items():
                options_trans[k] = self._get_translate(v)
            data['options'] = options_trans
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=200, headers=headers)
        except (KeyError) as e:
            raise MissParamError(query_params=['fullname'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
    
    def _get_msfmodule(self, fullname):
        module = Modules.objects.filter(fullname=fullname).first()
        if not module:
            return None
        if module.options is None:
            module.options = msfjsonrpc.modules.use(module.type, module.ref_name)._moptions
            module.save()
        return module
    
    def _get_translate(self, text):
        text = text.replace('\r\n', ' ').replace('\n', ' ').strip()
        if not text:
            return ''
        # 从数据库获取数据
        result = self._get_translate_from_db(text)
        if result != None:
            return result
        # 从腾讯翻译君翻译
        result = get_translation_from_qq(text)
        if result:
            # 增加翻译到数据库
            self._add_translation_to_db(text, result)
            return result
        return None
    
    def _get_translate_from_db(self, text):
        translation_base = TranslationBase.objects.filter(en_source=text).first()
        if not translation_base:
            return None
        return translation_base.zh_target
    
    def _add_translation_to_db(self, en_source, zh_target):
        trans_base = TranslationBase(
            en_source=en_source,
            zh_target=zh_target
        )
        trans_base.save()

class TranslationBaseViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = TranslationBase.objects.all()
    serializer_class = TranslationBaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['en_source', 'zh_target']

    @action(methods=['POST'], detail=False, url_path='getOne')
    def get_translation(self, request, *args, **kwargs):
        """从数据中获取某个句子的翻译"""
        try:
            en_source = request.data['en_source'].strip()
            translation_base = self.get_queryset().filter(en_source=en_source).first()
            if not translation_base:
                raise exceptions.NotFound
            return Response(data=translation_base.zh_target)
        except KeyError as e:
            raise MissParamError(query_params=['en_source'])


class FocusKeywordViewSet(PackResponseMixin, viewsets.ModelViewSet):
    queryset = FocusKeyword.objects.all()
    serializer_class = FocusKeywordSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated]
    filter_backends = [rich_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = FocusKeywordFilter

    @action(methods=['GET'], detail=False, url_path='categories')
    def categories(self, request, *args, **kwargs):
        data = list(self.get_queryset().values('category').annotate(count=Count('id')))
        return Response(data=data)

