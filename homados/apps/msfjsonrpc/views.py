import html2text
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from homados.contrib.mymixins import PackResponseMixin
from libs.pymetasploit.jsonrpc import MsfJsonRpc, MsfRpcError

from .models import Modules
from .serializers import ModuleSerializer


logger = settings.LOGGER

msfjsonrpc = MsfJsonRpc(server=settings.MSFCONFIG['HOST'], port=settings.MSFCONFIG['JSONRPC']['PORT'], token=settings.MSFCONFIG['JSONRPC']['TOKEN'])


class ModuleViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Modules.objects.all()
    serializer_class = ModuleSerializer
    permission_class = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["ref_name"]

    def list(self, request, *args, **kwargs):
        if Modules.objects.count() == 0:
            self.refresh_module_cache(request)
        return super().list(request, *args, **kwargs)
    
    @action(methods=["POST"], detail=False, url_path='refreshModuleCache')
    def refresh_module_cache(self, request, *args, **kwargs):
        """刷新模块缓存"""
        try:
            module_infos = {v['ref_name']: v for v in msfjsonrpc.modules.allinfo}
            module_names = module_infos.keys()
            ref_names = Modules.objects.filter(ref_name__in=module_names).values_list('ref_name', flat=True)
            diff_names = set()
            if len(ref_names) <= len(module_names):
                diff_names = set(module_names) - set(ref_names)
            modules = []
            for name in diff_names:
                module_info = {field.name: module_infos[name].get(field.name) for field in Modules._meta.get_fields()}
                modules.append(Modules(**module_info))
            Modules.objects.bulk_create(modules)
            return Response()
        except MsfRpcError as e:
            msg = 'msfjsonrpc出错'
            logger.exception(msg)
            raise exceptions.APIException(detail=msg)
        except Exception as e:
            logger.exception('未知错误')
        
    
    @action(detail=False, url_path='types')
    def types(self, request, *args, **kwargs):
        """列模块类型与数量"""
        data = list(Modules.objects.values('type').annotate(count=Count('id')))
        return Response(data=data)

    @action(detail=False, url_path='ref_names')
    def get_ref_names(self, request, *args, **kwargs):
        """根据指定类型列所有模块标识"""
        try:
            mtype = request.query_params['type']
            data = list(Modules.objects.filter(type=mtype).values('id', 'ref_name'))
            return Response(data=data)
        except KeyError as e:
            raise exceptions.ValidationError(detail={'type': '缺少参数'})
    
    @action(detail=True, url_path='info_html')
    def get_info_html(self, request, *args, **kwargs):
        """根据指定id获取模块html"""
        instance = self.get_object()
        if instance.info_html is not None:
            return Response(data=instance.info_html)
        try:
            module_type = instance.type
            module_name = instance.fullname
            module_info_html = msfjsonrpc.modules.use(module_type, module_name).info_html
            # html转markdown时一行过长不换行
            handler_html2text = html2text.HTML2Text()
            handler_html2text.body_width = 0
            instance.info_html = handler_html2text.handle(module_info_html)
            instance.save()
            return Response(data=instance.info_html)
        except MsfRpcError as e:
            msg = 'msfjsonrpc出错'
            logger.exception(msg)
            raise exceptions.APIException(detail=msg)
    
    @action(detail=False, url_path='compatible-payloads')
    def get_compatible_payloads(self, request, *args, **kwargs):
        """获取与某个 exploit 相兼容的 payload 列表"""
        try:
            exploit_fullname = request.query_params.get('ref_name') or 'multi/handler'
            exploit_fullname = exploit_fullname[8:] if exploit_fullname.startswith('exploit/') else exploit_fullname
            exploit_module = Modules.objects.filter(type='exploit', ref_name=exploit_fullname).first()
            if exploit_module.compatible_payloads is not None:
                return Response(data=exploit_module.compatible_payloads)
            module_exp = msfjsonrpc.modules.use('exploit', exploit_fullname)
            exploit_module.compatible_payloads = module_exp.payloads
            exploit_module.save()
            return Response(data=exploit_module.compatible_payloads)
        except (KeyError, ) as e:
            logger.exception()
            raise exceptions.APIException(detail=e)
        except (AttributeError, ) as e:
            msg = '没有这个exploit'
            logger.exception(msg)
            raise exceptions.APIException(detail=msg)
    
    @action(detail=False, url_path='options')
    def get_options(self, request, *args, **kwargs):
        """获取模块选项"""
        try:
            module_type = request.query_params['type']
            module_ref_name = request.query_params['ref_name']
            module_ref_name = module_ref_name[len(module_type):] if module_ref_name.startswith(module_type+'/') else module_ref_name
            module_obj = Modules.objects.filter(type=module_type, ref_name=module_ref_name).first()
            if module_obj.options is not None:
                return Response(data=module_obj.options)
            module_obj.options = msfjsonrpc.modules.use(module_type, module_ref_name)._moptions
            module_obj.save()
            return Response(data=module_obj.options)
        except (KeyError, MsfRpcError, ) as e:
            logger.exception()
            raise exceptions.APIException(detail=e)
        except (AttributeError, ) as e:
            msg = '没有这个模块'
            logger.exception(msg)
            raise exceptions.APIException(detail=msg)
