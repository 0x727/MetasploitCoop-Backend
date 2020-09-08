import functools
import io

import html2text
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.http import FileResponse
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from homados.contrib.exceptions import (MissParamError, MSFJSONRPCError,
                                        UnknownError)
from homados.contrib.mymixins import PackResponseMixin
from homados.contrib.viewsets import (ListDestroyViewSet,
                                      NoUpdateRetrieveViewSet, NoUpdateViewSet)
from libs.pymetasploit.jsonrpc import MsfJsonRpc, MsfRpcError

from .models import Modules
from .serializers import ModuleSerializer


logger = settings.LOGGER

msfjsonrpc = MsfJsonRpc(server=settings.MSFCONFIG['HOST'], port=settings.MSFCONFIG['JSONRPC']['PORT'], token=settings.MSFCONFIG['JSONRPC']['TOKEN'])


class ModuleViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Modules.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
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
            raise MSFJSONRPCError
        except Exception as e:
            raise UnknownError

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
            raise MissParamError(query_params=['type'])
    
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
            raise MSFJSONRPCError
    
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


class SessionViewSet(PackResponseMixin, ListDestroyViewSet):
    """msf 会话视图集"""
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        data = []
        for k, v in msfjsonrpc.sessions.list.items():
            data.append({ 'id': k, **v })
        return Response(data=data)

    def destroy(self, request, *args, **kwargs):
        try:
            result = msfjsonrpc.sessions.session(kwargs[self.lookup_field]).stop()
            return Response(data=result, status=status.HTTP_204_NO_CONTENT)
        except MsfRpcError as e:
            raise MSFJSONRPCError
        except Exception as e:
            raise UnknownError
    
    @action(methods=["POST"], detail=True, url_path='executeCmd')
    def execute_cmd(self, request, *args, **kwargs):
        try:
            command = request.query_params['command']
            if not command:
                return Response(data='')
            shell = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            result = shell.execute_cmd(command)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['command'])
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='cmdAutocomplete')
    def cmd_autocomplete(self, request, *args, **kwargs):
        try:
            command = request.query_params.get['command']
            if not command:
                return Response(data='')
            shell = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            result = shell.tabs(command)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['command'])
        except Exception as e:
            raise UnknownError

    @action(methods=['GET'], detail=True, url_path='procList')
    def proc_list(self, request, *args, **kwargs):
        try:
            session = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            result = session.proc_list()
            return Response(data=result)
        except Exception as e:
            raise UnknownError

    @action(methods=['GET'], detail=True, url_path='dirList')
    def dir_list(self, request, *args, **kwargs):
        try:
            command = request.query_params.get('command', 'pwd')
            dirpath = request.query_params.get('dirpath', '')
            session = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            result = session.dir_list(dirpath, command)
            return Response(data=result)
        except Exception as e:
            raise UnknownError

    @action(methods=['PATCH'], detail=True, url_path='editFile')
    def edit_file(self, request, *args, **kwargs):
        try:
            filepath = request.data['filepath']
            filetext = request.data['filetext']
            session = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            result = session.edit_file(filepath, filetext)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(body_params=['filepath', 'filetext'])
        except Exception as e:
            raise UnknownError
    
    @action(methods=['POST'], detail=True, url_path='uploadFile')
    def upload_file(self, request, sid):
        try:
            src = request.data['src']
            dest = request.data['dest']
            session = msfjsonrpc.sessions.session(sid)
            result = session.upload_file(src, dest)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(body_params=['src', 'dest'])
        except Exception as e:
            raise UnknownError


class LootViewSet(PackResponseMixin, NoUpdateViewSet):
    """msf loot 文件中转区视图集"""
    lookup_field = 'filename'
    lookup_value_regex = '[^/]+'
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            result = msfjsonrpc.core.loots
            return Response(data=result)
        except MsfRpcError as e:
            raise MSFJSONRPCError
        except Exception as e:
            raise UnknownError
    
    def retrieve(self, request, *args, **kwargs):
        try:
            filename = kwargs[self.lookup_field]
            data = msfjsonrpc.core.loot_download(filename)
            data = io.BytesIO(data)
            data.seek(0)
            return FileResponse(data, as_attachment=True, filename=filename)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['filename'])
        except MsfRpcError as e:
            raise MSFJSONRPCError
        except Exception as e:
            raise UnknownError
    
    def destroy(self, request, *args, **kwargs):
        try:
            filename = kwargs[self.lookup_field]
            result = msfjsonrpc.core.loot_destroy(filename)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['filename'])
        except MsfRpcError as e:
            raise MSFJSONRPCError
        except Exception as e:
            raise UnknownError
    
    def create(self, request, *args, **kwargs):
        try:
            file = request.data['file']
            filename = file.name
            data = file.read()
            result = msfjsonrpc.core.loot_upload(filename, data)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(body_params=['file'])
        except MsfRpcError as e:
            raise MSFJSONRPCError
        except Exception as e:
            raise UnknownError


class InfoViewSet(PackResponseMixin, viewsets.GenericViewSet):
    """msf 基础信息视图集"""
    permission_classes = [IsAuthenticated]

    def inner_try(func):
        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except MsfRpcError as e:
                raise MSFJSONRPCError
        return inner

    @inner_try
    @action(methods=['GET'], detail=False, url_path='version')
    def version(self, request, *args, **kwargs):
        """Get meatapsloit version"""
        version_info = msfjsonrpc.core.version
        return Response(data=version_info)

    @inner_try
    @action(methods=['GET'], detail=False, url_path='encodeformats')
    def encodeformats(self, request, *args, **kwargs):
        """Get meatapsloit payload encodeformats"""
        modules = msfjsonrpc.modules.encodeformats
        return Response(data=modules)

    @inner_try
    @action(methods=['GET'], detail=False, url_path='platforms')
    def platforms(self, request, *args, **kwargs):
        """Get meatapsloit payload platforms"""
        modules = msfjsonrpc.modules.platforms
        return Response(data=modules)

    @inner_try
    @action(methods=['GET'], detail=False, url_path='encoders')
    def encoders(self, request, *args, **kwargs):
        """Get meatapsloit payload encoders"""
        encoders = msfjsonrpc.modules.encoders
        return Response(data=encoders)

    # ToDelete
    @inner_try
    @action(methods=['GET'], detail=False, url_path='moduleStats')
    def module_stats(self, request, *args, **kwargs):
        """Get the number of modules loaded, broken down by type."""
        stats = msfjsonrpc.core.stats
        data = []
        for k, v in stats.items():
            data.append({'name': k, 'count': v})
        return Response(data=data)

    @inner_try
    @action(methods=['GET'], detail=False, url_path='threadList')
    def thread_list(self, request, *args, **kwargs):
        """Get a list the status of all background threads 
        along with an ID number that can be used to shut down the thread.
        """
        threads_bg = msfjsonrpc.core.threads
        data = []
        for k, v in threads_bg.items():
            v['id'] = k
            data.append(v)
        return Response(data=data)


class JobViewSet(PackResponseMixin, NoUpdateRetrieveViewSet):
    """msf 任务视图集"""
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            payload_type = request.data['payload']
            module_exploit = msfjsonrpc.modules.use('exploit', 'exploit/multi/handler')
            # don't exit from the exploit after a session has been created
            module_exploit['ExitOnSession'] = False
            module_payload = msfjsonrpc.modules.use('payload', payload_type)

            # set option to payload, for example: LHOST
            for k ,v in request.data.items():
                if k == 'payload':
                    continue
                module_payload[k] = v
            result = module_exploit.execute(payload=module_payload)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(body_params=['payload'])

    def list(self, request, *args, **kwargs):
        data = []
        jobs = msfjsonrpc.jobs.list
        for jobid in jobs.keys():
            job_info = msfjsonrpc.jobs.info(jobid)
            data.append(job_info)
        return Response(data=data)

    def destroy(self, request, *args, **kwargs):
        result = msfjsonrpc.jobs.stop(kwargs[self.lookup_field])
        return Response(data=result)
    
    # ToDelete
    @action(methods=['GET'], detail=False, url_path='compatiblePayloads')
    def get_target_compatible_payloads(self, request, *args, **kwargs):
        """获取与特定的exp模块兼容的 payload 列表"""
        exploit = request.query_params.get('exploit')
        exploit = exploit or 'exploit/multi/handler'
        target = request.query_params.get('target')
        target = target if target else 0
        module_exp = msfjsonrpc.modules.use('exploit', exploit)
        payloads = module_exp.targetpayloads(t=target)
        return Response(data=payloads)
