import logging
import asyncio
import traceback

from abc import ABCMeta, abstractmethod
from enum import Enum
from inspect import signature, Signature
from typing import Any, AsyncGenerator
from concurrent.futures import ProcessPoolExecutor

from ._hmc_import import *
from ..utils.environment import Environment
from ..utils.pipes import PipeSet, PipesHub, Pipe

log = logging.getLogger("hmc")

_modules = {}

def get_module(name : str):
    """
    Return the Module's class corresponding to 'name', based on Module.module_name

    :param str name: The module's name
    :return: The module's class if exist
    :return: None if not found
    """

    try:
        return _modules[name]
    except KeyError:
        return None

def list_modules(path:str='') -> dict:
    """
    Get all modules contained in the path
    """

    p = _get_path(path)
    if p is None:
        p = load_modules(path)
    return p

class Argument:
    """
    Store arguments
    :param str name: Name of the argument
    :param list[str] keys: Short names for the argument
    :param str desc: Description of the argument
    :param Any default: Default value of the argument
    :param Type arg_type: Type of the argument
    """

    _valid_attr = [
        "default",
        "arg_type"
    ]

    def __init__(self, name:str, *keys:str, desc:str="", **kwargs):
        self.name       = name
        self.keys       = keys
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

    def __eq__(self, o:str) -> bool:
        return self.name == o

    def __str__(self) -> str:
        return f'{self.name} {[key for key in self.keys]} : {self.desc}'

    def __repr__(self) -> str:
        return str(self)

class ModuleState(Enum):
    INITIAL   = 0
    READY     = 1
    RUNNING   = 2
    COMPLETED = 3
    FAILED    = 4

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
    """

    module_name = ""                                    # Name of the module
    module_desc = "Parent class for chained modules"    # Description of the module
    module_auth = "Mageos"                              # Author of the module

    module_args = []

    def __init__(self, env:Environment=None, print_logs:bool=True):
        self.env        = env
        self.print_logs = print_logs
        self.state      = ModuleState.INITIAL

        self._args = {}
        self._init_arguments()
        
        self._pipes = PipeSet(self._args.keys())

    def get_arguments(self) -> list[Argument]:
        """
        Return the module's args
        """
        return self._args

    def set_arguments(self, **kwargs) -> None:
        """
        Set the module's arguments
        """

        ready = True
        for arg in self._args.values():
            if arg.name in kwargs:
                arg.value = kwargs[arg.name]
            ready = ready and arg.ready

        if ready:
            self.state = ModuleState.READY

    def data_received(self, pipe, data) -> bool:
        pass

    async def wait_for_pipes(self) -> None:
        while not self._pipes.closed():
            pipe, data = await self._pipes.read()

            if pipe is None:
                break

            self.data_received(pipe, data)

            self.set_arguments(**{pipe: data})
            if self.state in [ModuleState.READY, ModuleState.RUNNING]:
                await self.run()

                if self.state == ModuleState.FAILED:
                    return

        self.state = ModuleState.COMPLETED
        self._pipes.write_eof()

    def _write_on_pipes(self, result:Any):
        if isinstance(result, dict):
            for key, value in result.items():
                self._pipes.write(key, value)
        else:
            self._pipes.write("result", result)

    async def run(self) -> Any:
        """
        Run the module
        """
        if self.state != ModuleState.READY:
            log.error("Cannot run module : %s not in state 'ready'", self.module_name)
            return
        self.state = ModuleState.RUNNING

        if self.env is None:
            self.env = Environment()

        # Get the module's arguments
        args = {}
        for arg in self._args.values():
            args[arg.name] = arg.value
        
        try:
            execution = self.execute(**args)

            if isinstance(execution, AsyncGenerator):
                result = []
                async for value in execution:
                    result.append(value)
                    self._write_on_pipes(value)
            else:
                result = await execution
                self._write_on_pipes(result)

            return result
        except Exception as e:
            self.state = ModuleState.FAILED
            log.error("(%s) FAILED : %s", self.module_name, str(e))
            print(traceback.format_exc())
        
        return None

    async def execute(self):
        """
        Execute the module code. Do not call directly, use Module.run() instead
        """
        return None

    def log_success(self, msg:str, *args):
        if self.print_logs:
            log.success('(' + self.module_name + ') ' + msg, *args)
        
    def log_failure(self, msg:str, *args):
        if self.print_logs:
            log.failure('(' + self.module_name + ') ' + msg, *args)
    
    def get_pipe(self, pipe:str) -> Pipe:
        return self._pipes._pipes.get(pipe)

    def _init_arguments(self):
        """Add missing arguments accordind to the execute() function signature"""

        sig = signature(self.execute)
        if not sig.parameters.items():
            return
            
        for arg in self.module_args:
            self._args[arg.name] = arg
        for param_name, param in sig.parameters.items():
            if param_name not in self.module_args:
                default = None if param.default is not param.empty else param.default
                p_type = None if param.annotation is not param.empty else param.annotation
                self._args[param_name] = Argument(param_name, '--' + param_name, arg_type=p_type, default=default)

class Workflow(Module):
    """
    Main class for chaining modules
    :param Environment env: The Environment to use
    :param bool print_logs: If results logs should be printed
    :param int max_worker: The maximum number of modules to execute in parallels
    """

    __module_desc__ = "Base workflow"

    def __init__(self, env=None, print_logs=True, max_worker=5):
        super().__init__(env, print_logs)

        self._max_worker = max_worker

        self._modules   = []
        self._queue     = []
        self._workers   = []

        self._completed = asyncio.Event()

        if self.env is None:
            self.env = Environment()
   
        self._conditions = {}
        self.init_modules()
    
    def init_modules(self):
        return

    def create_hub(self, name, Hub=PipesHub):
        _hub = Hub(self)
        self.env._hubs[name] = _hub
        self._pipes._pipes[name] = Pipe(name, self._pipes)
        _hub.add_ouptut(name, self)

        return _hub

    def add_module(self, module:Module, entries={}, outputs={}, condition=([], lambda: True)) -> Module:
        """
        Add the module to the Workflow list of modules
        """
        module.env = self.env
        module.print_logs = False
        self._modules.append(module)
        
        for hub, key in entries.items():
            _hub = self.get_hub(hub)
            if not _hub:
                _hub = self.create_hub(hub)
            self.link(module, hub, key)

        for hub, key in outputs.items():
            _hub = self.get_hub(hub)
            if not _hub:
                _hub = self.create_hub(hub)
            module._pipes.add_hub(key, _hub)

        self._conditions[module] = condition
        _hubs, _func = condition
        for hub in _hubs:
            _hub = self.get_hub(hub)
            if not _hub:
                _hub = self.create_hub(hub)
            _hub._modules.append(module)

        return module

    def link(self, obj, hub, key, auto_start=False):
        _hub = self.env._hubs.get(hub)
        if _hub is None:
            log.error("No hub %s", hub)
            return
        _hub.add_ouptut(key, obj)

    def set_condition(self, obj, hub, condition):
        _hub = self.env._hubs.get(hub)
        if _hub is None:
            log.error("No hub %s", hub)
            return
        _hub.add_condition(obj, condition)

    def get_hub(self, hub_name):
        return self.env._hubs.get(hub_name)

    def _create_worker(self, obj:Module):
        assert len(self._workers) < self._max_worker

        _worker = self._loop.create_task(obj.wait_for_pipes())
        _worker.add_done_callback(self._worker_done)
        self._workers.append(_worker)

    def _worker_done(self, worker):
        self._workers.remove(worker)
        if self._queue:
            obj = self._queue.pop()
            self._create_worker(obj)
        elif not self._workers:
            self._completed.set()
            self.state = ModuleState.COMPLETED

    async def wait_until_done(self):
        while not self._pipes.closed():
            pipe, data = await self._pipes.read()

            if pipe is None:
                break

            self.data_received(pipe, data)

        # await self.wait_for_pipes()
        await self._completed.wait()

    def _check_condition(self, module) -> bool:
        _cond = self._conditions.get(module)
        if not _cond:
            return False

        _hubs, _func = _cond
        _args = []
        for hub in _hubs:
            _hub = self.get_hub(hub)
            if not _hub:
                log.error("No hub named %s", hub)
                return False
            if len(_hub._contents) == 0:
                return False
            _args.append(_hub._contents[-1])
        return _func(*_args)

    def activate(self, obj:Module) -> bool:
        """
        Start a module
        """
        if obj.state != ModuleState.INITIAL:
            return True
        if not self._check_condition(obj):
            return False

        if len(self._workers) >= self._max_worker:
            self._queue.append(obj)
        else:
            self._create_worker(obj)
        
        return True

    async def run(self):
        self._loop = asyncio.get_event_loop()
        
        result = await super().run()
        await asyncio.gather(*self._workers)

        return result

    # def run(self):
    #     self._get_activ_modules()
    #     while self._activ:
    #         for module in self._activ:
    #             try:
    #                 module.run()
    #                 self._done.append(module)
    #             except Exception as e:
    #                 log.error("in module '%s' - %s", module.module_name, e)
    #         self._activ = []
    #         self._get_activ_modules()

    #     return super().run()
