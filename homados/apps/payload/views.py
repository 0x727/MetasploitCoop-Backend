from django.http.response import FileResponse
from rest_framework import exceptions, viewsets
from rest_framework.decorators import action
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from homados.contrib.mymixins import PackResponseMixin
from pluginbase import PluginBase
from rest_framework.response import Response
from libs import options
import io
from . import utils

logger = settings.LOGGER

plugin_base = PluginBase(package='plugins.payload')
plugin_source = plugin_base.make_plugin_source(searchpath=[str(settings.BASE_DIR.joinpath('plugins/payload'))])

logger.info('执行模块检查')
for plugin_name in plugin_source.list_plugins():
    plugin = plugin_source.load_plugin(plugin_name)
    utils.check_valid_plugin(plugin)
logger.info('模块检查结束')


class PayloadViewSet(PackResponseMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        plugins = []
        for plugin_name in plugin_source.list_plugins():
            plugin = plugin_source.load_plugin(plugin_name)
            plugin_info = {
                'identifier': plugin_name,
                'name': getattr(plugin, 'NAME', None),
                'desc': getattr(plugin, 'DESC', None),
                'options': options.options_to_dict(getattr(plugin, 'OPTIONS', None)),
                'references': getattr(plugin, 'REFERENCES', None),
                'attck': getattr(plugin, 'ATTCK', None),
                'author': getattr(plugin, 'AUTHOR', None),
            }
            plugins.append(plugin_info)
        return Response(data=plugins)

    @action(methods=['POST'], detail=True, url_path='generate')
    def generate(self, request, *args, **kwargs):
        try:
            plugin_name = kwargs[self.lookup_field]
            plugin = plugin_source.load_plugin(plugin_name)
            data = dict(request.data)
            # 检查选项
            errs = []
            for option in plugin.OPTIONS:
                value = data.get(option._name)
                if value is None:
                    if option._required:
                        errs.append(f'{option._name} 参数必须存在')
                    else:
                        data[option._name] = option._default
                else:
                    if not option.is_valid(value):
                        errs.append(f'{option._name} 参数必须是 {option._type} 类型')
            if errs:
                raise exceptions.ValidationError(detail=errs)
            res = plugin.run(data, data.get('info'))
            bin_data = io.BytesIO(res)
            bin_data.seek(0)
            return FileResponse(bin_data, as_attachment=True, filename=f"test.exe")
        except ImportError as e:
            raise exceptions.ValidationError(detail='没有这个paylaod生成插件')
