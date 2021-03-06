import base64
import functools
import io
import threading
import uuid
import ipaddress
from pathlib import Path
from asgiref.sync import AsyncToSync
import channels

import html2text
import magic
from dbmsf.models import ModuleResult
from dbmsf.serializers import Session, SessionEvent, SessionEventSerializer
from dbmsf.utils import get_session_events, get_module_results, sort_history_key
from django.conf import settings
from django.contrib.postgres.aggregates.general import StringAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Min, Q
from django.http import FileResponse, request
from django_filters import rest_framework as rich_filters
from homados.contrib.cache import LootDownloadLinkCache
from homados.contrib.exceptions import (MissParamError, MSFJSONRPCError,
                                        UnknownError)
from homados.contrib.mymixins import PackResponseMixin
from homados.contrib.viewsets import (ListDestroyViewSet,
                                      NoUpdateRetrieveViewSet, NoUpdateViewSet)
from kb.models import ResourceScript
from kb.serializers import ResourceScriptMiniSerializer, ResourceScriptSerializer
from libs.disable_command_handler import disable_command_handler
from libs.pymetasploit.jsonrpc import MsfJsonRpc, MsfRpcError
from libs.utils import get_user_ident, memview_to_str, report_msfjob_event
from qqwry import QQwry
from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from msfjsonrpc.permissions import CanUpdateModConfig

from .filters import ModuleFilter
from .models import ModAutoConfig, Modules
from .serializers import ModAutoConfigMiniSerializer, ModAutoConfigSerializer, ModuleSerializer
from . import background
from duplex.consumers import CustomerGroup

logger = settings.LOGGER

msfjsonrpc = background.msfjsonrpc

refresh_mod_mutex = threading.Lock()

iploc = QQwry()
iploc.load_file(str(settings.QQWRY_PATH))

def inner_try(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MsfRpcError as e:
            raise MSFJSONRPCError
    return inner


class ModuleViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Modules.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["ref_name"]
    filterset_class = ModuleFilter

    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)
        # double check
        if Modules.objects.count() == 0:
            with refresh_mod_mutex:
                if Modules.objects.count() == 0:
                    self.refresh_module_cache(request)
        return request

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(methods=["POST"], detail=False, url_path='refreshModuleCache')
    def refresh_module_cache(self, request, *args, **kwargs):
        """??????????????????"""
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
            return Response(diff_names)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    @action(detail=False, url_path='types')
    def types(self, request, *args, **kwargs):
        """????????????????????????"""
        data = list(Modules.objects.values('type').annotate(count=Count('id')))
        return Response(data=data)

    @action(detail=False, url_path='ref_names')
    def get_ref_names(self, request, *args, **kwargs):
        """??????????????????"""
        try:
            platform = request.query_params.get('platform')
            mtype = request.query_params.get('type')
            queryset = self.get_queryset()
            if mtype:
                queryset = queryset.filter(type=mtype)
            if platform:
                queryset = queryset.filter(Q(ref_name__startswith='multi') | Q(ref_name__startswith=platform))
            data = list(queryset.values('id', 'ref_name'))
            return Response(data=data)
        except Exception as e:
            raise UnknownError

    @action(detail=False, url_path='usable/fullnames')
    def usable_mod_fullnames(self, request, *args, **kwargs):
        """?????????????????????payload???????????????"""
        condition = (~Q(type='payload')) & (~Q(fullname='exploit/multi/handler'))
        data = list(self.get_queryset().filter(condition).values('id', 'fullname'))
        return Response(data=data)
    
    @action(detail=True, url_path='info_html')
    def get_info_html(self, request, *args, **kwargs):
        """????????????id????????????html"""
        instance = self.get_object()
        if instance.info_html is not None:
            return Response(data=instance.info_html)
        try:
            module_type = instance.type
            module_name = instance.fullname
            module_info_html = msfjsonrpc.modules.use(module_type, module_name).info_html
            # html???markdown????????????????????????
            handler_html2text = html2text.HTML2Text()
            handler_html2text.body_width = 0
            instance.info_html = handler_html2text.handle(module_info_html)
            instance.save()
            return Response(data=instance.info_html)
        except MsfRpcError as e:
            raise MSFJSONRPCError

    @action(detail=False, url_path='info')
    def get_info(self, request, *args, **kwargs):
        """????????????id??????????????????"""
        fullname = request.query_params.get('fullname')
        try:
            module_type = fullname.split('/')[0]
            module_info = msfjsonrpc.modules.use(module_type, fullname).info
            return Response(data=module_info)
        except MsfRpcError as e:
            raise MSFJSONRPCError

    @action(detail=False, url_path='compatible-payloads')
    def get_compatible_payloads(self, request, *args, **kwargs):
        """??????????????? exploit ???????????? payload ??????,?????????target??????"""
        try:
            exploit_fullname = request.query_params.get('ref_name') or 'multi/handler'
            exploit_fullname = exploit_fullname[8:] if exploit_fullname.startswith('exploit/') else exploit_fullname
            exploit_module = Modules.objects.filter(type='exploit', ref_name=exploit_fullname).first()
            # if exploit_module.compatible_payloads is not None:
            #     return Response(data=exploit_module.compatible_payloads)
            module_exp = msfjsonrpc.modules.use('exploit', exploit_fullname)
            if(request.query_params.get('target')):
                module_exp._target = request.query_params.get('target')
            exploit_module.compatible_payloads = module_exp.payloads
            exploit_module.save()
            return Response(data=exploit_module.compatible_payloads)
        except (KeyError, ) as e:
            raise UnknownError
        except (AttributeError, ) as e:
            msg = '????????????exploit'
            logger.exception(msg)
            raise exceptions.APIException(detail=msg)
    
    @action(detail=False, url_path='options')
    def get_options(self, request, *args, **kwargs):
        """??????????????????"""
        try:
            module_ref_name = request.query_params['ref_name']
            module = Modules.objects.get(Q(ref_name=module_ref_name) | Q(fullname=module_ref_name))
            if module.options is not None:
                return Response(data=module.options)
            module.options = msfjsonrpc.modules.use(module.type, module.ref_name)._moptions
            module.save()
            return Response(data=module.options)
        except ObjectDoesNotExist as e:
            raise APIException(detail='???????????????????????????????????????????????????', code=404)
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

    @action(methods=['GET'], detail=False, url_path='usableModList')
    def usable_mod_list(self, request, *args, **kwargs):
        """?????????????????????"""
        condition = (~Q(type='payload')) & (~Q(fullname='exploit/multi/handler'))
        self.queryset = self.get_queryset().filter(condition)
        return self.list(request, *args, **kwargs)


class SessionViewSet(PackResponseMixin, viewsets.ModelViewSet):
    """msf ???????????????"""
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        data = []
        sessions = msfjsonrpc.sessions.list
        # update_thread ????????????????????????????????????
        update_thread = background.UpdateHostsInfoThread(sessions)
        update_thread.start()
        for k, v in sessions.items():
            tunnel_peer = v.get('tunnel_peer')
            db_session = self._get_db_session_from_sid(k)
            v['desc'] = db_session.desc
            v['db_id'] = db_session.id
            if tunnel_peer:
                rip = tunnel_peer.split(':')[0].strip()
                location = iploc.lookup(rip)
                v['location'] = location if location else []
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
            sid = kwargs[self.lookup_field]
            command = request.data['command'].strip()
            self._send_input2front(sid, command)
            if not command:
                return Response(data='')
            # ??????????????????????????????????????????
            for k, v in disable_command_handler.items():
                if not k.search(command):
                    continue
                result = v(command, sid=sid)
                # ???????????????????????????????????????
                if not result.can_exec:
                    self._send_output2front(sid, result.tips)
                return Response(data=result.tips)
            else:
                shell = msfjsonrpc.sessions.session(sid)
                result = shell.write(command)
                return Response(data=f'> {command}')
        except (KeyError, ) as e:
            raise MissParamError(body_params=['command'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    def _send_input2front(self, sid, input_data):
        """????????????????????????????????????

        Args:
            sid: msf??????id
            input_data: ????????????
        """
        message = {
            'type': 'notify',
            'action': 'on_session_command',
            'data': {
                'sid': sid,
                'command': input_data
            }
        }
        receiver_name = CustomerGroup.Notify
        self.channel_layer = channels.layers.get_channel_layer()
        AsyncToSync(self.channel_layer.group_send)(
            receiver_name,
            {
                'type': 'send_message',
                'message': message
            }
        )
    
    def _send_output2front(self, sid: int, output: str):
        """????????????????????????????????????????????????????????????????????????????????????????????????msf??????ws??????????????????
        
        Args:
            sid: msf??????id
            output: ????????????
        """
        message = {
            'type': 'notify',
            'action': 'on_session_output',
            'data': {
                'sid': int(sid),
                'output': base64.b64encode(output.encode()).decode()
            }
        }
        receiver_name = CustomerGroup.Notify
        self.channel_layer = channels.layers.get_channel_layer()
        AsyncToSync(self.channel_layer.group_send)(
            receiver_name,
            {
                'type': 'send_message',
                'message': message
            }
        )

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
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
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
        """session??????????????????"""
        try:
            sid = kwargs[self.lookup_field]
            db_session = self._get_db_session_from_sid(sid)
            return Response(get_session_events(db_session))
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='moduleResults')
    def module_results(self, request, *args, **kwargs):
        """session ?????????????????????"""
        try:
            sid = kwargs[self.lookup_field]
            db_session = self._get_db_session_from_sid(sid)
            return Response(get_module_results(db_session))
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError
    
    @action(methods=['GET'], detail=True, url_path='history')
    def history(self, request, *args, **kwargs):
        """????????????????????????????????????"""
        try:
            sid = kwargs[self.lookup_field]
            db_session = self._get_db_session_from_sid(sid)
            data = get_session_events(db_session)
            data.extend(get_module_results(db_session))
            data.sort(key=sort_history_key)
            return Response(data)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    def _get_db_session_from_sid(self, sid):
        db_session = Session.objects.filter(local_id=sid).order_by('-id').first()
        if not db_session:
            raise exceptions.NotFound
        return db_session
    
    @action(methods=['GET'], detail=True, url_path='screenshot')
    def screenshot(self, request, *args, **kwargs):
        """??????"""
        try:
            quality = int(request.query_params.get('quality', 50))
            sid = kwargs[self.lookup_field]
            session = msfjsonrpc.sessions.session(sid)
            report_msfjob_event(f'{get_user_ident(request.user)} ??????????????? {sid} ??????????????????')
            result = session.screenshot(quality=quality)
            return Response(data=result)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError

    @action(methods=['GET'], detail=True, url_path='downloadFile')
    def download_file(self, request, *args, **kwargs):
        try:
            sid = kwargs[self.lookup_field]
            src = str(request.query_params.get('src'))
            session = msfjsonrpc.sessions.session(sid)
            report_msfjob_event(f'{get_user_ident(request.user)} ??????????????? {sid} ????????????????????????')
            result = session.download_file(src)
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(query_params=['src'])
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except Exception as e:
            raise UnknownError


class LootViewSet(PackResponseMixin, NoUpdateViewSet):
    """msf loot ????????????????????????"""
    permission_classes = [IsAuthenticated]
    loot_download_link_cache = LootDownloadLinkCache()

    def get_permissions(self):
        """
        ???????????????action????????????????????????????????????
        """
        if self.action == 'retrieve':
            permission_classes = []
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

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
            report_msfjob_event(f'{get_user_ident(request.user)} ???????????? {path} ????????????')
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
            ftype = None
            if content:
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
    
    @action(methods=['POST'], detail=False, url_path='createDownloadLink')
    def create_download_link(self, request, *args, **kwargs):
        """??????????????????????????????"""
        try:
            path = request.data['path'].strip().replace('../', '')
            expire = int(request.data['expire'])
            assert path and expire
            link_uuid = str(uuid.uuid4())
            self.loot_download_link_cache.set(link_uuid, path, expire)
            return Response(data={'link_uuid': link_uuid})
        except (KeyError, AssertionError) as e:
            raise MissParamError(query_params=['path', 'expire'])
        except Exception as e:
            raise UnknownError

    def retrieve(self, request, *args, **kwargs):
        """????????????????????????????????????"""
        try:
            link_uuid = kwargs[self.lookup_field]
            path = self.loot_download_link_cache.get(link_uuid)
            if not path:
                raise exceptions.NotFound
            filename = Path(path).name
            data = msfjsonrpc.core.loot_download(path)
            if not data:
                raise exceptions.NotFound
            data = io.BytesIO(data)
            data.seek(0)
            return FileResponse(data, as_attachment=True, filename=filename)
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))


class InfoViewSet(PackResponseMixin, viewsets.GenericViewSet):
    """msf ?????????????????????"""
    permission_classes = [IsAuthenticated]

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
    """msf ???????????????"""
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
            report_msfjob_event(f'{get_user_ident(request.user)} ??????????????? {payload_type}')
            
            # ???????????????????????????
            background.ListenerCacheAddThread(result.get('job_id')).start()
            return Response(data=result)
        except (KeyError, ) as e:
            raise MissParamError(body_params=['PAYLOAD'])

    def list(self, request, *args, **kwargs):
        jobs = msfjsonrpc.jobs.list_info
        return Response(data=jobs)

    def destroy(self, request, *args, **kwargs):
        job_id = kwargs[self.lookup_field]
        result = msfjsonrpc.jobs.stop(job_id)

        # ??????????????????????????????
        background.ListenerCacheDelThread(job_id).start()
        report_msfjob_event(f'{get_user_ident(request.user)} ??????????????? job_id: {job_id}')
        return Response(data=result)
    
    @action(methods=["POST"], detail=True, url_path='genStagers')
    def gen_stagers(self, request, *args, **kwargs):
        try:
            # ??????module
            job = msfjsonrpc.jobs.info(kwargs[self.lookup_field])
            options = job['datastore']
            payload_ref_name = options.pop('PAYLOAD')
            module = Modules.objects.get(ref_name=payload_ref_name)
            # ??????module??????
            options['Format'] = 'c'
            options.update(request.data)
            payload = msfjsonrpc.modules.use('payload', module.ref_name)
            for k, v in options.items():
                payload[k] = v
            if payload.missing_required:
                raise exceptions.ValidationError(detail={'????????????': payload.missing_required})
            data = payload.payload_generate()
            data = base64.b64decode(data)
            return Response(data=data.decode())
        except MsfRpcError as e:
            raise MSFJSONRPCError(str(e))
        except ObjectDoesNotExist as e:
            raise exceptions.NotFound
        except KeyError as e:
            raise MSFJSONRPCError(detail='session??????????????????datastore')
        except (UnicodeDecodeError, ) as e:
            data = io.BytesIO(data)
            data.seek(0)
            return FileResponse(data, as_attachment=True, filename=f"test.{payload['Format']}")


class ModAutoConfigViewSet(PackResponseMixin, viewsets.ModelViewSet):
    """???????????????????????????"""
    queryset = ModAutoConfig.objects.all()
    serializer_class = ModAutoConfigSerializer
    permission_classes = [IsAuthenticated & CanUpdateModConfig]
    pagination_class = None

    def create(self, request, *args, **kwargs):
        """?????????????????????????????????????????????????????????"""
        request.data['user'] = request.user.pk
        return super().create(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        self.serializer_class = ModAutoConfigMiniSerializer
        self.queryset = self.get_queryset().filter(Q(user=request.user) | Q(is_public=True))
        return super().list(request, *args, **kwargs)


class ResourceScriptViewSet(PackResponseMixin, viewsets.ModelViewSet):
    """?????????????????????"""
    queryset = ResourceScript.objects.all()
    serializer_class = ResourceScriptSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated]

    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)
        if self.get_queryset().count() == 0:
            self.refresh_rc_cache(request, *args, **kwargs)
        return request

    def refresh_rc_cache(self, request, *args, **kwargs):
        """????????????????????????"""
        rc_list = msfjsonrpc.core.rc_list()
        rc_map = {i['rc_name']:i['rc_content'] for i in rc_list}
        rc_names = rc_map.keys()
        db_rc_names = self.get_queryset().filter(filename__in=rc_names).values_list('filename', flat=True)
        diff_names = set()
        if len(db_rc_names) <= len(rc_names):
            diff_names = set(rc_names) - set(db_rc_names)
        rc_scripts = []
        for name in diff_names:
            rc_scripts.append(self.get_queryset().model(
                filename=name,
                content=rc_map[name]
            ))
        self.get_queryset().bulk_create(rc_scripts)
        return Response()

    def list(self, request, *args, **kwargs):
        self.serializer_class = ResourceScriptMiniSerializer
        return super().list(request, *args, **kwargs)

    # TODO ??????????????????
    @action(methods=['POST'], detail=True, url_path='load')
    def load(self, request, *args, **kwargs):
        """??????????????????"""
        pass


class RouteViewSet(PackResponseMixin, viewsets.ModelViewSet):
    """????????????????????????"""
    permission_classes = [IsAuthenticated]

    @inner_try
    def list(self, request, *args, **kwargs):
        data = msfjsonrpc.sessions.route_list()
        return Response(data=data)
    
    @inner_try
    def create(self, request, *args, **kwargs):
        try:
            address = request.data['address']
            sid = request.data['sid']
            return self._route_operation(sid, address, 'route_add')
        except KeyError as e:
            raise MissParamError(body_params=['address', 'sid'])

    @inner_try
    def destroy(self, request, *args, **kwargs):
        try:
            subnet = request.data['subnet']
            netmask = request.data['netmask']
            sid = kwargs[self.lookup_field]
            session = msfjsonrpc.sessions.session(sid)
            res = session.route_del(subnet, netmask)
            return Response(data=res)
        except KeyError as e:
            raise MissParamError(body_params=['subnet', 'netmask'])

    def _route_operation(self, sid, address, operation):
        """??????????????????"""
        avail = ['route_add', 'route_del']
        assert operation in avail, f"????????????????????? {avail} ????????????"

        try:
            assert '/' in address, "address ????????? 192.168.1.1/24 ???????????????"
            session = msfjsonrpc.sessions.session(sid)

            ipnet = ipaddress.ip_network(address, strict=False)
            subnet, netmask = str(ipnet.network_address), str(ipnet.netmask)

            res = getattr(session, operation)(subnet, netmask)
            return Response(data=res)
        except AssertionError as e:
            raise MissParamError(query_params=['address', 'sid'], msg=str(e))
