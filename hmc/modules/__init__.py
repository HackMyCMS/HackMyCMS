import os
import sys
import logging

from abc import ABCMeta, abstractmethod
from enum import Enum
from inspect import signature, Signature
from typing import Any

from ..utils.environment import Environment, PipeSet

log = logging.getLogger("hmc")

_modules = {}
_path    = {}

def _import_file(import_file:str) -> bool:
    file_name, ext = os.path.splitext(os.path.basename(import_file))
    if ext in [".py", ".pyc"]:
        try:
            path = os.path.dirname(import_file)
            sys.path.append(os.path.abspath(path))

            __import__(file_name)

            log.debug(f"""{import_file} successfully imported""")
            return True
        except Exception as e:
            log.warning(f"""error while importing {import_file} : {e}""")
    return False

def _get_lib(base, path:str):
    s = path.split('.')
    c = getattr(base, 'modules', None)

    for p in s:
        if not c:
            return None
        c = getattr(c, p, None)
    return c

def _get_path(path:str, update=False):
    s = path.split('.')
    p = _path

    for x in s:
        if not x in p:
            if update:
                p[x] = {}
            else:
                return None
        p = p[x]
    return p

def get_module(name : str):
    """
    Return the Module's class corresponding to name, based on Module.__module_name__

    Arguments:
    name    - The name of the searched module

    Return:
            - The module's class if exist
            - None if not found
    """

    try:
        return _modules[name]
    except KeyError:
        return None


def load_modules(path:str="") -> dict:
    if os.path.isfile(path):
        found = _import_file(path)
        return {}
    
    full_path = os.path.join(os.environ['PYTHONPATH'], "hmc/modules/", path.replace('.', '/'))

    if not os.path.isdir(full_path):
        full_path = '/'.join(full_path.split('/')[:-1])
        if not os.path.isdir(full_path):
            log.error(f"""Invalid file {path}""")
            return {}
        path = '.'.join(path.split('.')[:-1])

    folder = _get_path(path, update=True)
    for d in os.listdir(full_path):
        if os.path.isdir(os.path.join(full_path, d)) and d not in ['__pycache__']:
            folder[d] = "dir"

    try:
        hmc = __import__("hmc.modules" + ('.' if path else '') + path)
    except Exception as e:
        log.error("Unable to load %s : %s", path, str(e))
        return folder

    modules = _get_lib(hmc, path)
    if not modules:
        return folder

    for module in modules.__all__:
        mod = getattr(modules, module, None)
        if not mod:
            continue
        loaded = get_module(getattr(mod, 'module_name', ''))
        if not loaded:
            continue
        folder[mod.module_name] = mod.module_desc
    
    return folder

def list_modules(path:str='') -> dict:
    p = _get_path(path)
    if p is None:
        p = load_modules(path)
    return p

class Argument:
    """
    Store arguments
    :param str name: Name of the argument
    :param str short_name:Short name for the argument
    :param str desc: Description of the argument
    :param Any default: Default value of the argument
    :param Type arg_type: Type of the argument
    """

    _valid_attr = [
        "default",
        "arg_type"
    ]

    def __init__(self, name, short_name:str=None, desc="", **kwargs):
        self.name       = name
        self.short_name = short_name
        self.desc       = desc
        self.attr       = {}

        self._value = None
        self._ready = False

        for arg, value in kwargs.items():
            if not arg in self._valid_attr:
                raise ValueError("Invalid argument '%s'" % arg)
            self.attr[arg] = value

            if arg == 'default':
                self.value = value
        
    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, value:Any):
        self._value = value
        self._ready = True

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def key(self):
        n = self.name if self.name[:2] != '--' else self.name[2:]
        return n.replace('-', '_')

    @property
    def names(self):
        if self.short_name:
            return [self.name, self.short_name]
        return [self.name]

    def __eq__(self, o:str) -> bool:
        return self.key == o

    def __str__(self):
        return f'{self.name}{(' ' + self.short_name if self.short_name else '')} : {self.desc}'

    def __repr__(self):
        return str(self)

class ParserArgument(Argument):
    """
    Store arguments
    :param str name: Name of the argument
    :param str description: Description of the argument
    :param Any default: Default value of the argument
    :param Type arg_type: Type of the argument
    :param str shortcut: Simplification of the argument (ex 'url' -> 'u')
    """

    _valid_attr = [
        "default",
        "arg_type",
        "shortcut"
    ]

class ModuleState(Enum):
    INITIAL   = 0
    READY     = 1
    RUNNING   = 2
    COMPLETED = 3
    FAILED    = 4
    ERROR     = 5

class _Module_Meta(ABCMeta):

    # Black magic, called when a module's class is imported
    def __new__(cls, name, bases, ns):
        c = super(_Module_Meta, cls).__new__(cls, name, bases, ns)

        # Get the 'module_name' composant from the module
        name = ns.get("module_name")    # ns = NameSpace, see https://docs.python.org/3/tutorial/classes.html#python-scopes-and-namespaces
        if name:
            _modules[name] = c  # Add the module to the list if module_name is defined

        # Return the object
        return c

class Module(metaclass=_Module_Meta):
    """
    Parent class to implement Module
    :param Environment env: The Environment to use
    :param bool print_logs: If results logs should be printed

    Variables:
    :param str module_name: Name of the module
    :param str module_desc: Description of the module
    :param str module_auth: Author of the module

    :param list<Argument> args: Detailed Argument for the execute() function
    :param list<str> keys: Names for the module's pipes
    """

    module_name = ""                                    # Name of the module
    module_desc = "Parent class for chained modules"    # Description of the module
    module_auth = "Mageos"                              # Author of the module

    args:list[Argument] = []                            # Detailed Argument for the execute() function
    keys:list[str]      = []                            # Names for the module's pipes

    def __init__(self, env:Environment=None, print_logs:bool=True):
        self.env        = env
        self.print_logs = print_logs
        self.state      = ModuleState.INITIAL

        self.pipes = PipeSet(self.keys)
        
        if not self.args:
            self.args = []
        if not self.keys:
            self.keys = []

        self._init_arguments()

    def get_arguments(self) -> list[Argument]:
        """
        :return: The list of arguments defined in self.args
        """
        return self.args

    def set_arguments(self, **kwargs) -> None:
        """
        Set the module's arguments
        """

        ready = True
        for arg in self.args:
            if arg.key in kwargs:
                arg.value = kwargs[arg.key]
            ready = ready and arg.ready

        if ready:
            self.state = ModuleState.READY

    def run(self) -> None:
        if self.state != ModuleState.READY:
            log.error("Cannot run module : %s not in state 'ready'", self.module_name)
            return
        self.state = ModuleState.RUNNING

        if self.env is None:
            self.env = Environment()

        # Get the module's arguments
        args = {}
        for arg in self.args:
            args[arg.key] = arg.value
        
        try:
            success = self.execute(**args)
            self.state = ModuleState.COMPLETED if success else ModuleState.ERROR
        except Exception as e:
            self.state = ModuleState.ERROR
            log.error("(%s) : %s", self.module_name, str(e))

    def execute(self) -> bool:
        return True    
        
    def check_activation(self) -> bool:
        return True

    def log_success(self, msg:str, *args):
        if self.print_logs:
            log.success('(' + self.module_name + ') ' + msg, *args)
        
    def log_failure(self, msg:str, *args):
        if self.print_logs:
            log.failure('(' + self.module_name + ') ' + msg, *args)
    
    def _init_arguments(self):
        """Add missing arguments accordind to the execute() function signature"""
        sig = signature(self.execute)
        if not sig.parameters.items():
            return
        
        for param_name, param in sig.parameters.items():
            if param_name in self.args:
                continue

            default = None if param.default is not param.empty else param.default
            p_type = None if param.annotation is not param.empty else param.annotation
            self.args.append(Argument('--' + param_name, arg_type=p_type, default=default))

class Workflow(Module):

    __module_desc__ = "Base workflow"

    def __init__(self, env=None, print_logs=True):
        super().__init__(env, print_logs)

        self._modules = []
        self._pipes   = []

        self._activ = []
        self._done  = []
        
        if self.env is None:
            self.env = Environment()
   
        self.init_modules()
    
    def init_modules(self):
        return

    def add_pipe(self, name, value=None):
        return self.env.pipes.add_pipe(name, value)

    def add_module(self, module):
        module.env = self.env
        self._modules.append(module)

    def get_arguments(self) -> None:
        result = []
        for arg in self.args:
            result.append(arg)

        for module in self._modules:
            for arg in module.args:
                if arg in result:
                    log.warning("Argument %s used by multiple modules")
                    continue
                result.append(arg)

        return result

    def set_arguments(self, **kwargs):
        ready = True
        for module in self._modules:
            update = {}
            for arg, value in kwargs.items():
                if arg in module.args:
                    update[arg] = value
            if update:
                module.set_arguments(**update)
            ready = ready and module.state == ModuleState.READY
        
        for arg in self.args:
            if arg.key in kwargs:
                arg.value = kwargs[arg.key]
            ready = ready and arg.ready

        if ready:
            self.state = ModuleState.READY

    def _get_activ_modules(self):
        # TODO : optimize
        for module in self._modules:
            if module.check_activation():
                self._activ.append(module)
        for module in self._activ:
            self._modules.remove(module)

    def run(self):
        self._get_activ_modules()
        while self._activ:
            for module in self._activ:
                try:
                    module.run()
                    self._done.append(module)
                except Exception as e:
                    log.error("in module '%s' - %s", module.module_name, e)
            self._activ = []
            self._get_activ_modules()

        return super().run()
