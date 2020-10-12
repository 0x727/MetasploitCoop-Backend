import base64
import functools
import io
from pathlib import Path

import html2text
import magic
from dbmsf.models import ModuleResult
from dbmsf.serializers import Session, SessionEvent, SessionEventSerializer
from django.conf import settings
from django.contrib.postgres.aggregates.general import StringAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Min, Q
from django.http import FileResponse, request
from django_filters import rest_framework as rich_filters
from homados.contrib.exceptions import (MissParamError, MSFJSONRPCError,
                                        UnknownError)
from homados.contrib.mymixins import PackResponseMixin
from homados.contrib.viewsets import (ListDestroyViewSet,
                                      NoUpdateRetrieveViewSet, NoUpdateViewSet)
from libs.disable_command_handler import disable_command_handler
from libs.pymetasploit.jsonrpc import MsfJsonRpc, MsfRpcError
from libs.utils import get_user_ident, memview_to_str, report_msfjob_event
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import ModuleFilter
from .models import Modules
from .serializers import ModuleSerializer

logger = settings.LOGGER

msfjsonrpc = MsfJsonRpc(
    server=settings.MSFCONFIG['HOST'],
    port=settings.MSFCONFIG['JSONRPC']['PORT'],
    token=settings.MSFCONFIG['JSONRPC']['TOKEN'],
)


class ModuleViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Modules.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["ref_name"]
    filterset_class = ModuleFilter

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
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    @action(detail=False, url_path='types')
    def types(self, request, *args, **kwargs):
        """列模块类型与数量"""
        data = list(Modules.objects.values('type').annotate(count=Count('id')))
        return Response(data=data)

    @action(detail=False, url_path='ref_names', filter_backends=(rich_filters.DjangoFilterBackend,))
    def get_ref_names(self, request, *args, **kwargs):
        """过滤模块标识"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            data = list(queryset.values('id', 'ref_name'))
            return Response(data=data)
        except Exception as e:
            raise UnknownError
    
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
            raise UnknownError
        except (AttributeError, ) as e:
            msg = '没有这个exploit'
            logger.exception(msg)
            raise exceptions.APIException(detail=msg)
    
    @action(detail=False, url_path='options')
    def get_options(self, request, *args, **kwargs):
        """获取模块选项"""
        try:
            module_ref_name = request.query_params['ref_name']
            module = Modules.objects.get(Q(ref_name=module_ref_name) | Q(fullname=module_ref_name))
            if module.options is not None:
                return Response(data=module.options)
            module.options = msfjsonrpc.modules.use(module.type, module.ref_name)._moptions
            module.save()
            return Response(data=module.options)
        except ObjectDoesNotExist as e:
            raise APIException(detail='模块未找到，可能你需要刷新模块缓存', code=404)
        except KeyError as e:
            raise MissParamError(query_params=['ref_name'])
        except MsfRpcError as e:
            raise MSFJSONRPCError
        except Exception as e:
            raise UnknownError
    
    @action(detail=True, methods=['POST'], url_path='execute')
    def execute(self, request, *args, **kwargs):
        try:
            module = self.get_object()
            mod = msfjsonrpc.modules.use(module.type, module.ref_name)
            for k, v in request.data.items():
                mod[k.upper()] = v
            data = mod.execute()
            return Response(data=data)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError


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
            command = request.data['command'].strip()
            if not command:
                return Response(data='')
            for k, v in disable_command_handler.items():
                if not k.search(command):
                    continue
                result = v(command, sid=kwargs[self.lookup_field])
                return Response(data=result.tips)
            else:
                shell = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
                result = shell.write(command)
                return Response(data=f'> {command}')
        except (KeyError, ) as e:
            raise MissParamError(body_params=['command'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='cmdAutocomplete')
    def cmd_autocomplete(self, request, *args, **kwargs):
        try:
            command = request.query_params['command']
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
            dirpath = request.query_params.get('dirpath')
            dirpath = dirpath if dirpath and dirpath.strip() else None
            session = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            data = session.dir_list(dirpath)
            return Response(data=data)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='catFile')
    def cat_file(self, request, *args, **kwargs):
        try:
            filepath = request.query_params['filepath'].strip()
            assert filepath and isinstance(filepath, str)
            session = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            data = session.cat_file(filepath)
            return Response(data=data)
        except (KeyError, AssertionError) as e:
            raise MissParamError(query_params=['filepath'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    @action(methods=['DELETE'], detail=True, url_path='delFile')
    def delete_file(self, request, *args, **kwargs):
        try:
            paths = request.data['paths'] or []
            dirs_for_del = []
            files_for_del = []
            for pathinfo in paths:
                if pathinfo['isDir']:
                    dirs_for_del.append(pathinfo['filepath'])
                else:
                    files_for_del.append(pathinfo['filepath'])
            session = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            paths = {
                'dirs': dirs_for_del,
                'files': files_for_del,
            }
            result = session.rm_paths(paths)
            return Response(data=result)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except (KeyError, AssertionError) as e:
            raise MissParamError(body_params=['paths'])
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
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except (KeyError, ) as e:
            raise MissParamError(body_params=['filepath', 'filetext'])
        except Exception as e:
            raise UnknownError
    
    @action(methods=['POST'], detail=True, url_path='uploadFile')
    def upload_file(self, request, *args, **kwargs):
        try:
            src = request.data['src']
            dest = request.data['dest']
            session = msfjsonrpc.sessions.session(kwargs[self.lookup_field])
            result = session.upload_file(src, dest)
            return Response(data=result)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except (KeyError, ) as e:
            raise MissParamError(body_params=['src', 'dest'])
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='events')
    def events(self, request, *args, **kwargs):
        """session执行过的事件"""
        try:
            sid = kwargs[self.lookup_field]
            db_session = Session.objects.filter(local_id=sid).order_by('-id').first()
            if not db_session:
                raise exceptions.NotFound
            session_events = db_session.session_events
            serializer = SessionEventSerializer(session_events, many=True)
            return Response(data=serializer.data)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='moduleResults')
    def module_results(self, request, *args, **kwargs):
        """session 的模块执行结果"""
        try:
            sid = kwargs[self.lookup_field]
            db_session = Session.objects.filter(local_id=sid).order_by('-id').first()
            if not db_session:
                raise exceptions.NotFound
            data = list(ModuleResult.objects.filter(session=db_session).values('track_uuid').annotate(
                output=StringAgg('output', delimiter=''),
                created_at=Min('created_at'),
                fullname=Min('fullname')
            ))
            for i in data:
                i['output'] = memview_to_str(i['output'])
            return Response(data=data)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='screenshot')
    def screenshot(self, request, *args, **kwargs):
        """截屏"""
        try:
            quality = int(request.query_params.get('quality', 50))
            sid = kwargs[self.lookup_field]
            session = msfjsonrpc.sessions.session(sid)
            report_msfjob_event(f'{get_user_ident(request.user)} 正在对会话 {sid} 进行截屏操作')
            result = session.screenshot(quality=quality)
            return Response(data=result)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError


class LootViewSet(PackResponseMixin, NoUpdateViewSet):
    """msf loot 文件中转区视图集"""
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            path = request.query_params.get('path', '')
            result = msfjsonrpc.core.loots(path)
            return Response(data=result)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    @action(methods=['POST'], detail=False, url_path='download')
    def download_file(self, request, *args, **kwargs):
        try:
            path = request.data['path']
            filename = Path(path).name
            data = msfjsonrpc.core.loot_download(path)
            data = io.BytesIO(data)
            data.seek(0)
            return FileResponse(data, as_attachment=True, filename=filename)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['path'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    @action(methods=['POST'], detail=False, url_path='delete')
    def delete_file(self, request, *args, **kwargs):
        try:
            path = request.data['path']
            result = msfjsonrpc.core.loot_destroy(path)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['path'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    def create(self, request, *args, **kwargs):
        try:
            file = request.data['file']
            dir = request.data['dir']
            path = dir.rstrip('/') + '/' + file.name
            data = file.read()
            result = msfjsonrpc.core.loot_upload(path, data)
            report_msfjob_event(f'{get_user_ident(request.user)} 上传文件 {path} 到中转区')
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(body_params=['file', 'dir'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    @action(methods=['POST'], detail=False, url_path='preview')
    def preview_file(slef, request, *args, **kwargs):
        try:
            path = request.data['path']
            content = msfjsonrpc.core.loot_download(path)
            ftype = magic.from_buffer(content, mime=True)
            data = {
                'content': base64.b64encode(content).decode(),
                'ftype': ftype
            }
            return Response(data)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['path'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
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
            payload_type = request.data['PAYLOAD']
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
            report_msfjob_event(f'{get_user_ident(request.user)} 创建监听器 {payload_type}')
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(body_params=['PAYLOAD'])

    def list(self, request, *args, **kwargs):
        jobs = msfjsonrpc.jobs.list_info
        return Response(data=jobs)

    def destroy(self, request, *args, **kwargs):
        job_id = kwargs[self.lookup_field]
        result = msfjsonrpc.jobs.stop(job_id)
        report_msfjob_event(f'{get_user_ident(request.user)} 删除监听器 job_id: {job_id}')
        return Response(data=result)
    
    @action(methods=["POST"], detail=True, url_path='genStagers')
    def gen_stagers(self, request, *args, **kwargs):
        try:
            # 获取module
            job = msfjsonrpc.jobs.info(kwargs[self.lookup_field])
            options = job['datastore']
            payload_ref_name = options.pop('PAYLOAD')
            module = Modules.objects.get(ref_name=payload_ref_name)
            # 设置module参数
            options['Format'] = 'c'
            options.update(request.data)
            payload = msfjsonrpc.modules.use('payload', module.ref_name)
            for k, v in options.items():
                payload[k] = v
            if payload.missing_required:
                raise exceptions.ValidationError(detail={'参数缺失': payload.missing_required})
            data = payload.payload_generate()
            data = base64.b64decode(data)
            return Response(data=data.decode())
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except ObjectDoesNotExist as e:
            raise exceptions.NotFound
        except KeyError as e:
            raise MSFJSONRPCError(detail='session信息中不存在datastore')
        except (UnicodeDecodeError, ) as e:
            data = io.BytesIO(data)
            data.seek(0)
            return FileResponse(data, as_attachment=True, filename=f"test.{payload['Format']}")
