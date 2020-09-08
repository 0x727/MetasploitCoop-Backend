import requests
import re
import time
from retry import retry
from libs.requestsauth import BearerTokenAuth
import base64


requests.packages.urllib3.disable_warnings()


class MsfError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class MsfRpcError(Exception):
    pass


class MsfAuthError(MsfError):
    def __init__(self, msg):
        self.msg = msg


class MsfRpcMethod:
    AuthLogin = 'auth.login'
    AuthLogout = 'auth.logout'
    AuthTokenList = 'auth.token_list'
    AuthTokenAdd = 'auth.token_add'
    AuthTokenGenerate = 'auth.token_generate'
    AuthTokenRemove = 'auth.token_remove'
    ConsoleCreate = 'console.create'
    ConsoleList = 'console.list'
    ConsoleDestroy = 'console.destroy'
    ConsoleRead = 'console.read'
    ConsoleWrite = 'console.write'
    ConsoleTabs = 'console.tabs'
    ConsoleSessionKill = 'console.session_kill'
    ConsoleSessionDetach = 'console.session_detach'
    CoreVersion = 'core.version'
    CoreStop = 'core.stop'
    CoreSetG = 'core.setg'
    CoreUnsetG = 'core.unsetg'
    CoreSave = 'core.save'
    CoreReloadModules = 'core.reload_modules'
    CoreModuleStats = 'core.module_stats'
    CoreAddModulePath = 'core.add_module_path'
    CoreThreadList = 'core.thread_list'
    CoreThreadKill = 'core.thread_kill'
    CoreLootList = 'core.loot_list'
    CoreLootUpload = 'core.loot_upload'
    CoreLootDownload = 'core.loot_download'
    CoreLootDestory = 'core.loot_destroy'
    DbHosts = 'db.hosts'
    DbServices = 'db.services'
    DbVulns = 'db.vulns'
    DbWorkspaces = 'db.workspaces'
    DbCurrentWorkspace = 'db.current_workspace'
    DbGetWorkspace = 'db.get_workspace'
    DbSetWorkspace = 'db.set_workspace'
    DbDelWorkspace = 'db.del_workspace'
    DbAddWorkspace = 'db.add_workspace'
    DbGetHost = 'db.get_host'
    DbReportHost = 'db.report_host'
    DbReportService = 'db.report_service'
    DbGetService = 'db.get_service'
    DbGetNote = 'db.get_note'
    DbGetClient = 'db.get_client'
    DbReportClient = 'db.report_client'
    DbReportNote = 'db.report_note'
    DbNotes = 'db.notes'
    DbGetRef = 'db.get_ref'
    DbDelVuln = 'db.del_vuln'
    DbDelNote = 'db.del_note'
    DbDelService = 'db.del_service'
    DbDelHost = 'db.del_host'
    DbReportVuln = 'db.report_vuln'
    DbEvents = 'db.events'
    DbReportEvent = 'db.report_event'
    DbReportLoot = 'db.report_loot'
    DbLoots = 'db.loots'
    DbReportCred = 'db.report_cred'
    DbCreds = 'db.creds'
    DbImportData = 'db.import_data'
    DbGetVuln = 'db.get_vuln'
    DbClients = 'db.clients'
    DbDelClient = 'db.del_client'
    DbDriver = 'db.driver'
    DbConnect = 'db.connect'
    DbStatus = 'db.status'
    DbDisconnect = 'db.disconnect'
    JobList = 'job.list'
    JobStop = 'job.stop'
    JobInfo = 'job.info'
    ModuleAllinfo = 'module.allinfo'
    ModuleExploits = 'module.exploits'
    ModuleEvasion = 'module.evasion'
    ModuleAuxiliary = 'module.auxiliary'
    ModulePayloads = 'module.payloads'
    ModuleEncoders = 'module.encoders'
    ModuleNops = 'module.nops'
    ModulePlatforms = 'module.platforms'
    ModulePost = 'module.post'
    ModuleInfo = 'module.info'
    ModuleInfoHTML = 'module.info_html'
    ModuleCompatiblePayloads = 'module.compatible_payloads'
    ModuleCompatibleSessions = 'module.compatible_sessions'
    ModuleTargetCompatiblePayloads = 'module.target_compatible_payloads'
    ModuleOptions = 'module.options'
    ModuleExecute = 'module.execute'
    ModuleEncodeFormats = 'module.encode_formats'
    ModuleEncode = 'module.encode'
    PluginLoad = 'plugin.load'
    PluginUnload = 'plugin.unload'
    PluginLoaded = 'plugin.loaded'
    SessionList = 'session.list'
    SessionStop = 'session.stop'
    SessionShellRead = 'session.shell_read'
    SessionShellWrite = 'session.shell_write'
    SessionShellUpgrade = 'session.shell_upgrade'
    SessionMeterpreterRead = 'session.meterpreter_read'
    SessionRingRead = 'session.ring_read'
    SessionRingPut = 'session.ring_put'
    SessionRingLast = 'session.ring_last'
    SessionRingClear = 'session.ring_clear'
    SessionMeterpreterWrite = 'session.meterpreter_write'
    SessionMeterpreterExecute = 'session.meterpreter_execute'
    SessionMeterpreterSessionDetach = 'session.meterpreter_session_detach'
    SessionMeterpreterSessionKill = 'session.meterpreter_session_kill'
    SessionMeterpreterTabs = 'session.meterpreter_tabs'
    SessionMeterpreterRunSingle = 'session.meterpreter_run_single'
    SessionMeterpreterScript = 'session.meterpreter_script'
    SessionMeterpreterProcessList = 'session.meterpreter_ps'
    SessionMeterpreterEditFile = 'session.meterpreter_edit_file'
    SessionMeterpreterUploadFile = 'session.meterpreter_upload_file'
    SessionMeterpreterDirectorySeparator = 'session.meterpreter_directory_separator'
    SessionCompatibleModules = 'session.compatible_modules'


class MsfCommand:
    show_mount = 'show_mount'
    pwd = 'pwd'
    ls = 'ls'


class MsfJsonRpc:
    def __init__(self, **kwargs):
        self.uri = kwargs.get('uri', '/api/v1/json-rpc')
        self.port = kwargs.get('port', 8081)
        self.host = kwargs.get('server', '127.0.0.1')
        self.ssl = kwargs.get('ssl', False)
        self.token = kwargs.get('token')
        self.id = kwargs.get('id', 1)
    
    def call(self, method, opts=None):
        if not isinstance(opts, list):
            opts = []
        if not self.token:
            raise MsfAuthError('Authenticate to access this resource.')
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': opts,
            'id': self.id,
        }
        if self.ssl is True:
            url = "https://%s:%s%s" % (self.host, self.port, self.uri)
        else:
            url = "http://%s:%s%s" % (self.host, self.port, self.uri)
        
        r = self.post_request(url, payload)

        if r.status_code == 401:
            raise MsfAuthError('Authenticate to access this resource.')

        return r.json()['result']
    
    @retry(tries=3, delay=1, backoff=2)
    def post_request(self, url, payload):
        return requests.post(url, json=payload, auth=BearerTokenAuth(self.token),verify=False)
    
    @property
    def core(self):
        """
        The msf RPC core manager.
        """
        return CoreManager(self)
    
    @property
    def modules(self):
        """
        The msf RPC modules RPC manager.
        """
        return ModuleManager(self)
    
    @property
    def sessions(self):
        """
        The msf RPC sessions (meterpreter & shell) manager.
        """
        return SessionManager(self)

    @property
    def jobs(self):
        """
        The msf RPC jobs manager.
        """
        return JobManager(self)


class MsfManager:

    def __init__(self, rpc):
        """
        Initialize a msf component manager.

        Mandatory Arguments:
        - rpc : the msfrpc client object.
        """
        self.rpc = rpc


class CoreManager(MsfManager):

    @property
    def version(self):
        """
        The version of msf core.
        """
        return self.rpc.call(MsfRpcMethod.CoreVersion)

    def stop(self):
        """
        Stop the core.
        """
        self.rpc.call(MsfRpcMethod.CoreStop)

    def setg(self, var, val):
        """
        Set a global variable

        Mandatory Arguments:
        - var : the variable name
        - val : the variable value
        """
        self.rpc.call(MsfRpcMethod.CoreSetG, [var, val])

    def unsetg(self, var):
        """
        Unset a global variable

        Mandatory Arguments:
        - var : the variable name
        """
        self.rpc.call(MsfRpcMethod.CoreUnsetG, [var])

    def save(self):
        """
        Save the core state.
        """
        self.rpc.call(MsfRpcMethod.CoreSave)

    def reload(self):
        """
        Reload all modules in the core.
        """
        self.rpc.call(MsfRpcMethod.CoreReloadModules)

    @property
    def stats(self):
        """
        Get module statistics from the core.
        """
        return self.rpc.call(MsfRpcMethod.CoreModuleStats)

    def addmodulepath(self, path):
        """
        Add a search path for additional modules.

        Mandatory Arguments:
        - path : the path to search for modules.
        """
        return self.rpc.call(MsfRpcMethod.CoreAddModulePath, [path])

    @property
    def threads(self):
        """
        The current threads running in the core.
        """
        return self.rpc.call(MsfRpcMethod.CoreThreadList)

    def kill(self, threadid):
        """
        Kill a thread running in the core.

        Mandatory Arguments:
        - threadid : the thread ID.
        """
        self.rpc.call(MsfRpcMethod.CoreThreadKill, [threadid])
    
    @property
    def loots(self):
        """
        List file for loot_directory
        """
        return self.rpc.call(MsfRpcMethod.CoreLootList)
    
    def loot_download(self, filename):
        """
        download a file from loot directory

        Args:
            filename: the filename you want to download from loot directory
        """
        data = self.rpc.call(MsfRpcMethod.CoreLootDownload, [filename])['data']
        return base64.b64decode(data.encode())
    
    def loot_upload(self, filename, data):
        """
        upload a file to loot_directory

        Args:
            filename: the filename which you want to upload to loot dir
            data: the content of file which is base64 encode
        """
        data_b64 = base64.b64encode(data).decode()
        return self.rpc.call(MsfRpcMethod.CoreLootUpload, [filename, data_b64])

    def loot_destroy(self, filename):
        """
        destroy a file from loot directory

        Args:
            filename: the filename you want to destroy from loot directory
        """
        return self.rpc.call(MsfRpcMethod.CoreLootDestory, [filename])


class ModuleManager(MsfManager):

    def execute(self, modtype, modname, **kwargs):
        """
        Execute the module.

        Mandatory Arguments:
        - modtype : the module type (e.g. 'exploit')
        - modname : the module name (e.g. 'exploits/windows/http/icecast_header')

        Optional Keyword Arguments:
        - **kwargs : the module's run options
        """
        return self.rpc.call(MsfRpcMethod.ModuleExecute, [modtype, modname, kwargs])
    
    @property
    def allinfo(self):
        """
        A list of all module info
        """
        return self.rpc.call(MsfRpcMethod.ModuleAllinfo)

    @property
    def exploits(self):
        """
        A list of exploit modules.
        """
        return self.rpc.call(MsfRpcMethod.ModuleExploits)['modules']

    @property
    def evasion(self):
        """
        A list of exploit modules.
        """
        return self.rpc.call(MsfRpcMethod.ModuleEvasion)['modules']

    @property
    def payloads(self):
        """
        A list of payload modules.
        """
        return self.rpc.call(MsfRpcMethod.ModulePayloads)['modules']

    @property
    def auxiliary(self):
        """
        A list of auxiliary modules.
        """
        return self.rpc.call(MsfRpcMethod.ModuleAuxiliary)['modules']

    @property
    def post(self):
        """
        A list of post modules.
        """
        return self.rpc.call(MsfRpcMethod.ModulePost)['modules']

    @property
    def encodeformats(self):
        """
        A list of encoding formats.
        """
        return self.rpc.call(MsfRpcMethod.ModuleEncodeFormats)

    @property
    def encoders(self):
        """
        A list of encoder modules.
        """
        return self.rpc.call(MsfRpcMethod.ModuleEncoders)['modules']

    @property
    def nops(self):
        """
        A list of nop modules.
        """
        return self.rpc.call(MsfRpcMethod.ModuleNops)['modules']

    @property
    def platforms(self):
        """
        A list of nop modules.
        """
        return self.rpc.call(MsfRpcMethod.ModulePlatforms)

    def use(self, mtype, mname):
        """
        Returns a module object.

        Mandatory Arguments:
        - mname : the module name (e.g. 'exploits/windows/http/icecast_header')
        """
        if mtype == 'exploit':
            return ExploitModule(self.rpc, mname)
        elif mtype == 'post':
            return PostModule(self.rpc, mname)
        elif mtype == 'encoder':
            return EncoderModule(self.rpc, mname)
        elif mtype == 'auxiliary':
            return AuxiliaryModule(self.rpc, mname)
        elif mtype == 'nop':
            return NopModule(self.rpc, mname)
        elif mtype == 'payload':
            return PayloadModule(self.rpc, mname)
        elif mtype == 'evasion':
            return Evasion(self.rpc, mname)
        raise MsfRpcError('Unknown module type %s not: exploit, post, encoder, auxiliary, nop, or payload' % mname)


class MsfModule:

    def __init__(self, rpc, mtype, mname):
        """
        Initializes an msf module object.

        Mandatory Arguments:
        - rpc : the msfrpc client object.
        - mtype : the module type (e.g. 'exploit')
        - mname : the module name (e.g. 'exploits/windows/http/icecast_header')
        """

        self.moduletype = mtype
        self.modulename = mname
        self.rpc = rpc
        self._info = rpc.call(MsfRpcMethod.ModuleInfo, [mtype, mname])
        property_attributes = ["advanced", "evasion", "options", "required", "runoptions"]
        for k in self._info:
            if k not in property_attributes:
                # don't try to set property attributes
                setattr(self, k, self._info.get(k))
        self._moptions = rpc.call(MsfRpcMethod.ModuleOptions, [mtype, mname])
        self._roptions = []
        self._aoptions = []
        self._eoptions = []
        self._runopts = {}
        for o in self._moptions:
            if self._moptions[o]['required']:
                self._roptions.append(o)
            if self._moptions[o]['advanced']:
                self._aoptions.append(o)
            if self._moptions[o]['evasion']:
                self._eoptions.append(o)
            if 'default' in self._moptions[o]:
                self._runopts[o] = self._moptions[o]['default']

        if mtype in ["auxiliary", "post"]:
            d_act = self._info.get('default_action')
            if d_act is not None:
                act = 'ACTION'
                self._moptions[act] = {"default": d_act}
                self._runopts[act] = self._moptions[act]['default']
    
    @property
    def info(self):
        """
        Get the module info.
        """
        return self._info

    @property
    def options(self):
        """
        All the module options.
        """
        return list(self._moptions.keys())

    @property
    def required(self):
        """
        The required module options.
        """
        return self._roptions

    @property
    def missing_required(self):
        """
        List of missing required options
        """
        outstanding = list(set(self.required).difference(list(self._runopts.keys())))
        return outstanding

    @property
    def evasion(self):
        """
        Module options that are used for evasion.
        """
        return self._eoptions

    @property
    def advanced(self):
        """
        Advanced module options.
        """
        return self._aoptions

    @property
    def runoptions(self):
        """
        The running (currently set) options for a module. This will raise an error
        if some of the required options are missing.
        """
        # outstanding = self.missing_required()
        # if outstanding:
        #     raise TypeError('Module missing required parameter: %s' % ', '.join(outstanding))
        return self._runopts

    def optioninfo(self, option):
        """
        Get information about the module option

        Mandatory Argument:
        - option : the option name.
        """
        return self._moptions[option]

    def __getitem__(self, item):
        """
        Get the current option value.

        Mandatory Arguments:
        - item : the option name.
        """
        if item not in self._moptions and item not in self._runopts:
            raise KeyError("Invalid option '%s'." % item)
        return self._runopts.get(item)

    def __setitem__(self, key, value):
        """
        Set the current option value.

        Mandatory Arguments:
        - key : the option name.
        - value : the option value.
        """

        if key not in self.options:
            self._runopts[key] = value
        elif 'enums' in self._moptions[key] and value not in self._moptions[key]['enums']:
            raise ValueError("Value ('%s') is not one of %s" % (value, repr(self._moptions[key]['enums'])))
        elif self._moptions[key]['type'] == 'bool' and not isinstance(value, bool):
            raise TypeError("Value must be a boolean not '%s'" % type(value).__name__)
        elif self._moptions[key]['type'] in ['integer', 'float'] and value is not None and not isinstance(value, (int, float)):
            raise TypeError("Value must be an integer not '%s'" % type(value).__name__)
        self._runopts[key] = value

    def __delitem__(self, key):
        del self._runopts[key]

    def __contains__(self, item):
        return item in self._runopts

    def update(self, d):
        """
        Update a set of options.

        Mandatory Arguments:
        - d : a dictionary of options
        """
        for k in d:
            self[k] = d[k]
    
    @property
    def info_html(self):
        """
        Returns detailed information about a module in HTML.
        """
        return self.rpc.call(MsfRpcMethod.ModuleInfoHTML, [self.moduletype, self.modulename])

    def payload_generate(self, **kwargs):
        runopts = self.runoptions.copy()
        if not isinstance(self, PayloadModule):
            return None
        data = self.rpc.call(MsfRpcMethod.ModuleExecute, [self.moduletype, self.modulename, runopts])
        return data['payload']

    def execute(self, **kwargs):
        """
        Executes the module with its run options as parameters.

        Optional Keyword Arguments:
        - payload : the payload of an exploit module (this is mandatory if the module is an exploit).
        - **kwargs : can contain any module options.
        """
        runopts = self.runoptions.copy()
        if isinstance(self, ExploitModule):
            payload = kwargs.get('payload')
            runopts['TARGET'] = self.target
            if 'DisablePayloadHandler' in runopts and runopts['DisablePayloadHandler']:
                pass
            elif payload is None:
                runopts['DisablePayloadHandler'] = True
            else:
                if isinstance(payload, PayloadModule):
                    if payload.modulename not in self.payloads:
                        raise ValueError(
                            'Invalid payload (%s) for given target (%d).' % (payload.modulename, self.target)
                        )
                    runopts['PAYLOAD'] = payload.modulename
                    for k, v in payload.runoptions.items():
                        if v is None or (isinstance(v, str) and not v):
                            continue
                        if k not in runopts or runopts[k] is None or \
                                (isinstance(runopts[k], str) and not runopts[k]):
                            runopts[k] = v
                #                    runopts.update(payload.runoptions)
                elif isinstance(payload, str):
                    if payload not in self.payloads:
                        raise ValueError('Invalid payload (%s) for given target (%d).' % (payload, self.target))
                    runopts['PAYLOAD'] = payload
                else:
                    raise TypeError("Expected type str or PayloadModule not '%s'" % type(kwargs['payload']).__name__)

        return self.rpc.call(MsfRpcMethod.ModuleExecute, [self.moduletype, self.modulename, runopts])


class ExploitModule(MsfModule):

    def __init__(self, rpc, exploit):
        """
        Initializes the use of an exploit module.

        Mandatory Arguments:
        - rpc : the rpc client used to communicate with msfrpcd
        - exploit : the name of the exploit module.
        """
        super(ExploitModule, self).__init__(rpc, 'exploit', exploit)
        self._target = self._info.get('default_target', 0)

    @property
    def payloads(self):
        """
        A list of compatible payloads.
        """
        #        return self.rpc.call(MsfRpcMethod.ModuleCompatiblePayloads, self.modulename)['payloads']
        return self.targetpayloads(self.target)

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, target):
        if target not in self.targets:
            raise ValueError('Target must be one of %s' % repr(list(self.targets.keys())))
        self._target = target

    def targetpayloads(self, t=0):
        """
        Returns a list of compatible payloads for a given target ID.

        Optional Keyword Arguments:
        - t : the target ID (default: 0, e.g. 'Automatic')
        """
        return self.rpc.call(MsfRpcMethod.ModuleTargetCompatiblePayloads, [self.modulename, t])['payloads']


class PostModule(MsfModule):

    def __init__(self, rpc, post):
        """
        Initializes the use of a post exploitation module.

        Mandatory Arguments:
        - rpc : the rpc client used to communicate with msfrpcd
        - post : the name of the post exploitation module.
        """
        super(PostModule, self).__init__(rpc, 'post', post)
        self._action = self._info.get('default_action', "")

    @property
    def sessions(self):
        """
        A list of compatible shell/meterpreter sessions.
        """
        return self.rpc.compatiblesessions(self.modulename)

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):
        if action not in self.actions.values():
            raise ValueError('Action must be one of %s' % repr(list(self.actions.values())))
        self._action = action
        self._runopts['ACTION'] = self._action


class EncoderModule(MsfModule):

    def __init__(self, rpc, encoder):
        """
        Initializes the use of an encoder module.

        Mandatory Arguments:
        - rpc : the rpc client used to communicate with msfrpcd
        - encoder : the name of the encoder module.
        """
        super(EncoderModule, self).__init__(rpc, 'encoder', encoder)


class AuxiliaryModule(MsfModule):

    def __init__(self, rpc, auxiliary):
        """
        Initializes the use of an auxiliary module.

        Mandatory Arguments:
        - rpc : the rpc client used to communicate with msfrpcd
        - auxiliary : the name of the auxiliary module.
        """
        super(AuxiliaryModule, self).__init__(rpc, 'auxiliary', auxiliary)
        self._action = self._info.get('default_action', "")

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):
        if action not in self.actions.values():
            raise ValueError('Action must be one of %s' % repr(list(self.actions.values())))
        self._action = action
        self._runopts['ACTION'] = self._action


class PayloadModule(MsfModule):

    def __init__(self, rpc, payload):
        """
        Initializes the use of a payload module.

        Mandatory Arguments:
        - rpc : the rpc client used to communicate with msfrpcd
        - payload : the name of the payload module.
        """
        super(PayloadModule, self).__init__(rpc, 'payload', payload)


class NopModule(MsfModule):

    def __init__(self, rpc, nop):
        """
        Initializes the use of a nop module.

        Mandatory Arguments:
        - rpc : the rpc client used to communicate with msfrpcd
        - nop : the name of the nop module.
        """
        super(NopModule, self).__init__(rpc, 'nop', nop)


class Evasion(MsfModule):

    def __init__(self, rpc, evasion):
        """
        Initializes the use of a evasion module.

        Mandatory Arguments:
        - rpc : the rpc client used to communicate with msfrpcd
        - evasion : the name of the evasion module.
        """
        super(Evasion, self).__init__(rpc, 'evasion', evasion)


class MsfSession:

    def __init__(self, sid, rpc, sd):
        """
        Initialize a meterpreter or shell session.

        Mandatory Arguments:
        - sid : the session identifier.
        - rpc : the msfrpc client object.
        - sd : the session description
        """
        self.sid = sid
        self.rpc = rpc
        self.__dict__.update(sd)
        for s in self.__dict__:
            if re.match(r'\d+', s):
                if 'plugins' not in self.__dict__[s]:
                    self.__dict__[s]['plugins'] = []
                if 'write_dir' not in self.__dict__[s]:
                    self.__dict__[s]['write_dir'] = ''

    def stop(self):
        """
        Stop a meterpreter or shell session.
        """
        return self.rpc.call(MsfRpcMethod.SessionStop, [self.sid])

    @property
    def modules(self):
        """
        A list of compatible session modules.
        """
        return self.rpc.call(MsfRpcMethod.SessionCompatibleModules, [self.sid])['modules']

    @property
    def ring(self):
        return SessionRing(self.rpc, self.sid)


class MeterpreterSession(MsfSession):

    def read(self):
        """
        Read data from the meterpreter session.
        """
        return self.rpc.call(MsfRpcMethod.SessionMeterpreterRead, [self.sid])['data']

    def write(self, data):
        """
        Write data to the meterpreter session.

        Mandatory Arguments:
        - data : arbitrary data or commands
        """
        if not data.endswith('\n'):
            data += '\n'
        self.rpc.call(MsfRpcMethod.SessionMeterpreterWrite, [self.sid, data])
    
    def execute_cmd(self, cmd):
        """
        execute cmd for the meterpreter session.

        Mandatory Arguments:
        - cmd : arbitrary data or commands
        """
        if not cmd.endswith('\n'):
            cmd += '\n'
        return self.rpc.call(MsfRpcMethod.SessionMeterpreterExecute, [self.sid, cmd])['data']

    def runsingle(self, data):
        """
        Run a single meterpreter command

        Mandatory Arguments:
        - data : arbitrary data or command
        """
        self.rpc.call(MsfRpcMethod.SessionMeterpreterRunSingle, [self.sid, data])
        return self.read()

    def runscript(self, path):
        """
        Run a meterpreter script

        Mandatory Arguments:
        - path : path to a meterpreter script on the msfrpcd host.
        """
        self.rpc.call(MsfRpcMethod.SessionMeterpreterScript, [self.sid, path])
        return self.read()

    @property
    def info(self):
        """
        Get the session's data dictionary
        """
        return self.__dict__[self.sid]

    @property
    def sep(self):
        """
        The operating system path separator.
        """
        return self.rpc.call(MsfRpcMethod.SessionMeterpreterDirectorySeparator, [self.sid])['separator']

    def detach(self):
        """
        Detach the meterpreter session.
        """
        return self.rpc.call(MsfRpcMethod.SessionMeterpreterSessionDetach, [self.sid])

    def kill(self):
        """
        Kill the meterpreter session.
        """
        self.rpc.call(MsfRpcMethod.SessionMeterpreterSessionKill, [self.sid])

    def tabs(self, line):
        """
        Return a list of commands for a partial command line (tab completion).

        Mandatory Arguments:
        - line : a partial command line for completion.
        """
        return self.rpc.call(MsfRpcMethod.SessionMeterpreterTabs, [self.sid, line])['tabs']

    def load_plugin(self, plugin):
        """
        Loads a session plugin

        Mandatory Arguments:
        - plugin : name of plugin.
        """
        end_strs = ['Success', 'has already been loaded']
        out = self.run_with_output(f'load {plugin}', end_strs)
        self.__dict__[self.sid]['plugins'].append(plugin)
        return out

    def run_with_output(self, cmd, end_strs=None, timeout=301, timeout_exception=True, api_call='write'):
        """
        Run a command and wait for the output.

        Mandatory Arguments:
        - data : command to run in the session.
        - end_strs : a list of strings which signify you've gathered all the command's output, e.g., ['finished', 'done']

        Optional Arguments:
        - timeout : number of seconds to wait if end_strs aren't found. 300s is default MSF comm timeout.
        - timeout_exception : If True, library will throw an error when it hits the timeout.
                              If False, library will simply return whatever output it got within the timeout limit.
        """
        if api_call == 'write':
            self.write(cmd)
            out = ''
        else:
            out = self.runsingle(cmd)
        time.sleep(1)
        out += self.gather_output(cmd, out, end_strs, timeout, timeout_exception)  # gather last of data buffer
        return out

    def gather_output(self, cmd, out, end_strs, timeout, timeout_exception):
        """
        Wait for session command to get all output.
        """
        counter = 1
        while counter < timeout:
            out += self.read()
            if end_strs == None:
                if len(out) > 0:
                    return out
            else:
                if any(end_str in out for end_str in end_strs):
                    return out
            time.sleep(1)
            counter += 1

        if timeout_exception:
            msg = f"Command <{repr(cmd)[1:-1]}> timed out in <{timeout}s> on session <{self.sid}>"
            if end_strs == None:
                msg += f" without finding any termination strings within <{end_strs}> in the output: <{out}>"
            raise MsfError(msg)
        else:
            return out

    def run_shell_cmd_with_output(self, cmd, end_strs, exit_shell=True):
        """
        Runs a Windows command from a meterpreter shell

        Optional Arguments:
        exit_shell : Exit the shell inside meterpreter once command is done.
        """
        self.start_shell()
        out = self.run_with_output(cmd, end_strs)
        if exit_shell == True:
            self.read()  # Clear buffer
            res = self.detach()
            if 'result' in res:
                if res['result'] != 'success':
                    raise MsfError('Shell failed to exit on meterpreter session ' + self.sid)
        return out

    def start_shell(self):
        """
        Drops meterpreter session into shell
        """
        cmd = 'shell'
        end_strs = ['>']
        self.run_with_output(cmd, end_strs)
        return True

    def import_psh(self, script_path):
        """
        Import a powershell script.

        Mandatory Arguments:
        - script_path : Path on the local machine to the Powershell script.
        """
        if 'powershell' not in self.info['plugins']:
            self.load_plugin('powershell')
        end_strs = ['[-]', '[+]']
        out = self.run_with_output(f'powershell_import {script_path}', end_strs)
        if 'failed to load' in out:
            raise MsfRpcError(f'File {script_path} failed to load.')
        return out

    def run_psh_cmd(self, ps_cmd, timeout=310, timeout_exception=True):
        """
        Runs a powershell command and get the output.

        Mandatory Arguments:
        - ps_cmd : command to run in the session.
        """
        if 'powershell' not in self.info['plugins']:
            self.load_plugin('powershell')
        ps_cmd = f'powershell_execute "{ps_cmd}"'
        out = self.run_with_output(ps_cmd, ['[-]', '[+]'], timeout=timeout, timeout_exception=timeout_exception)
        return out

    def get_writeable_dir(self):
        """
        Gets the temp directory which we are assuming is writeable
        """
        if self.info['write_dir'] == '':
            out = self.run_shell_cmd_with_output('echo %TEMP%', ['>'])
            # Example output: 'echo %TEMP%\nC:\\Users\\user\\AppData\\Local\\Temp\r\n\r\nC:\\Windows\\system32>'
            write_dir = out.split('\n')[1][:-1] + '\\'
            self.__dict__[self.sid]['write_dir'] = write_dir
            return write_dir
        else:
            return self.info['write_dir']
    
    def _dir_result_parse(self, result, dirpath=None, show_mount=False):
        filelist = []
        if show_mount:
            cur_path = '/'
            mount_pattern = re.compile(r'(\S+:\\)\s+?(\w+?)\s+?([\d\.]+\s\w+?)\s+?([\d\.]+\s\w+)')
            for item in mount_pattern.findall(result):
                filelist.append({
                    'modified': '{}|{}'.format(item[3], item[2]),
                    'size': item[3],
                    'type': item[1],
                    'name': item[0].replace('\\', '/').strip()
                })
        else:
            cur_path_pattern = re.compile(r'Listing: (.+)')
            filelist_pattern = re.compile(r'(\d+?/[rwx-]{9})\s+?(\d+?)\s+?(\w+?)\s+?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+\d{4})\s+?(.+)')
            cur_path = dirpath or cur_path_pattern.search(result).group(1)
            for item in filelist_pattern.findall(result):
                filelist.append({
                    'mode': item[0],
                    'size': item[1],
                    'type': item[2],
                    'modified': item[3],
                    'name': item[4].strip(),
                })
        return {
            'pwd': cur_path.replace('\\', '/'),
            'dirs': filelist,
        }

    
    def dir_list(self, dirpath, command=MsfCommand.pwd):
        dirpath = dirpath or '/'
        result = ''
        if dirpath == '/' and command == MsfCommand.ls:
            try:
                result = self.execute_cmd(' '.join([command, dirpath]))
                return self._dir_result_parse(result)
            except:
                result = self.execute_cmd(MsfCommand.show_mount)
                return self._dir_result_parse(result, show_mount=True)
        
        if command == MsfCommand.pwd:
            result = self.execute_cmd('ls')
            return self._dir_result_parse(result)
        elif command == MsfCommand.ls:
            result = self.execute_cmd(' '.join([command, dirpath]))
            return self._dir_result_parse(result, dirpath=dirpath)

    def proc_list(self):
        result = self.rpc.call(MsfRpcMethod.SessionMeterpreterProcessList, [self.sid])
        return result['data']
    
    def edit_file(self, filepath, filetext):
        result = self.rpc.call(MsfRpcMethod.SessionMeterpreterEditFile, [self.sid, filepath, filetext])
        return result
    
    def upload_file(self, src, dest):
        result = self.rpc.call(MsfRpcMethod.SessionMeterpreterUploadFile, [self.sid, src, dest])
        return result


class SessionRing:

    def __init__(self, rpc, token):
        self.rpc = rpc
        self.sid = token

    def read(self, seq=None):
        """
        Reads the session ring.

        Optional Keyword Arguments:
        - seq : the sequence ID of the ring (default: 0)
        """
        if seq is not None:
            return self.rpc.call(MsfRpcMethod.SessionRingRead, [self.sid, seq])
        return self.rpc.call(MsfRpcMethod.SessionRingRead, [self.sid])

    def put(self, line):
        """
        Add a command to the session history.

        Mandatory Arguments:
        - line : arbitrary data.
        """
        self.rpc.call(MsfRpcMethod.SessionRingPut, [self.sid, line])

    @property
    def last(self):
        """
        Returns the last sequence ID in the session ring.
        """
        return int(self.rpc.call(MsfRpcMethod.SessionRingLast, [self.sid])['seq'])

    def clear(self):
        """
        Clear the session ring.
        """
        return self.rpc.call(MsfRpcMethod.SessionRingClear, [self.sid])


class ShellSession(MsfSession):

    def read(self):
        """
        Read data from the shell session.
        """
        return self.rpc.call(MsfRpcMethod.SessionShellRead, [self.sid])['data']

    def write(self, data):
        """
        Write data to the shell session.

        Mandatory Arguments:
        - data : arbitrary data or commands
        """
        if not data.endswith('\n'):
            data += '\n'
        self.rpc.call(MsfRpcMethod.SessionShellWrite, [self.sid, data])

    def upgrade(self, lhost, lport):
        """
        Upgrade the current shell session.
        """
        self.rpc.call(MsfRpcMethod.SessionShellUpgrade, [self.sid, lhost, lport])
        return self.read()

    def run_with_output(self, cmd, end_strs, timeout=310):
        """
        Run a command and wait for the output.

        Mandatory Arguments:
        - data : command to run in the session.
        - end_strs : a list of strings which signify you've gathered all the command's output, e.g., ['finished', 'done']

        Optional Arguments:
        - timeout : number of seconds to wait if end_strs aren't found. 300s is default MSF comm timeout.
        """
        self.write(cmd)
        out = self.gather_output(cmd, end_strs, timeout)
        return out

    def gather_output(self, cmd, end_strs, timeout):
        """
        Wait for session command to get all output.
        """
        out = ''
        counter = 0
        while counter < timeout + 1:
            time.sleep(1)
            out += self.read()
            if any(end_str in out for end_str in end_strs):
                return out
            counter += 1

        raise MsfError(f"Command <{repr(cmd)[1:-1]}> timed out in <{timeout}s> on session <{self.sid}> "
                       f"without finding any termination strings within <{end_strs}> in the output: <{out}>")


class SessionManager(MsfManager):

    @property
    def list(self):
        """
        A list of active sessions.
        """
        return {str(k): v for k, v in self.rpc.call(MsfRpcMethod.SessionList).items()}  # Convert int id to str   

    def session(self, sid):
        """
        Returns a session object for meterpreter or shell sessions.

        Mandatory Arguments:
        - sid : the session identifier or uuid
        """
        s = self.list
        sid = str(sid)
        if sid not in s:
            for k in s:
                if s[k]['uuid'] == sid:
                    if s[k]['type'] == 'meterpreter':
                        return MeterpreterSession(k, self.rpc, s)
                    elif s[k]['type'] == 'shell':
                        return ShellSession(k, self.rpc, s)
            raise KeyError('Session ID (%s) does not exist' % sid)
        if s[sid]['type'] == 'meterpreter':
            return MeterpreterSession(sid, self.rpc, s)
        elif s[sid]['type'] == 'shell':
            return ShellSession(sid, self.rpc, s)
        raise NotImplementedError('Could not determine session type: %s' % s[sid]['type'])


class JobManager(MsfManager):

    @property
    def list(self):
        """
        A list of currently running jobs.
        """
        return self.rpc.call(MsfRpcMethod.JobList)

    def stop(self, jobid):
        """
        Stop a job.

        Mandatory Argument:
        - jobid : the ID of the job.
        """
        self.rpc.call(MsfRpcMethod.JobStop, [jobid])

    def info(self, jobid):
        """
        Get job information for a particular job.

        Mandatory Argument:
        - jobid : the ID of the job.
        """
        return self.rpc.call(MsfRpcMethod.JobInfo, [jobid])
