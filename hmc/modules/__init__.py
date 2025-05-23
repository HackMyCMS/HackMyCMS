import os
import sys
import logging

from abc import ABCMeta, abstractmethod
from inspect import signature, Signature
from typing import Any

from ..utils.environment import Environment

log = logging.getLogger("hmc")

_modules = {}
_last_module = []

_module_list = []
_directories = []

class ChainedKeys:
    _value      = None
    
    def __init__(self, value=None):
        self._value = value

class _Module_Meta(ABCMeta):

    # Black magic, called when a module's class is imported
    def __new__(cls, name, bases, ns):
        c = super(_Module_Meta, cls).__new__(cls, name, bases, ns)

        # Get the __module_name__ composant from the module
        name = ns.get("__module_name__")    # ns = NameSpace, see https://docs.python.org/3/tutorial/classes.html#python-scopes-and-namespaces
        if name:
            _modules[name] = c  # Add the module to the list if __module_name__ is defined
            _last_module.append(c)

        # Super important, DO NOT REMOVE
        return c

class ChainedModule(metaclass=_Module_Meta):

    __module_desc__ = "Parent class for chained modules"

    env = Environment()
    keys = []

    _keys = {}

    def __init__(self, env:Environment=None, execute=None, **links):
        
        if env is not None:
            self.env = env

        self.set_links(execute=execute, **links)

        # for key in self.keys:
        #     self._keys[key] = ChainedKeys()

    def add_arguments(self, parser) -> None:
        sig = signature(self.execute)
        if not sig.parameters.items():
            return

        # group = parser.add_argument_group(getattr(self, "__module_name__"))
        for param_name, param in sig.parameters.items():
            if param_name in ['env']:
                continue

            sup_args = {}
            if param.default is not param.empty:
                sup_args["default"] = param.default
            
            if param.annotation is bool or isinstance(param.default, bool):
                if param.default is not param.empty and param.default:
                    sup_args["action"] = "store_false"
                else:
                    sup_args["action"] = "store_true"
            parser.add_argument('--%s' % param_name, **sup_args)

    def run(self, kwargs):
        args = {}
        
        sig = signature(self.execute)
        for param_name, param in sig.parameters.items():
            val = kwargs.get(param_name)
            if val is not None:
                args[param_name] = val
        
        self.execute(**args)

    def execute(self) -> bool:
        return True    
        
    def check_activation(self) -> bool:
        return True

    def log_success(self, msg:str, *args):
        log.success('(' + self.__module_name__ + ') ' + msg, *args)
        
    def log_failure(self, msg:str, *args):
        log.failure('(' + self.__module_name__ + ') ' + msg, *args)
    
    def set_links(self, **links):
        for var, link in links.items():
            if link is not None:
                assert isinstance(link, ChainedKeys), "Invalid link" 
            setattr(self, var, link)

    def __getattribute__(self, name):
        var = super().__getattribute__(name)
        if not isinstance(var, ChainedKeys):
            return var
        return var._value
    
    def __setattr__(self, name, value):
        if name in self.__dict__:
            var = self.__dict__[name]
        else:
            return super().__setattr__(name, value)
        
        if not isinstance(var, ChainedKeys):
            return super().__setattr__(name, value)
        var._value = value

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
            print(e)
            log.warning(f"""error while importing {import_file} : {e}""")
    return False

def load_modules(file:str=""):
    if file is None:
        file = ""

    if os.path.isfile(file):
        found = _import_file(file)
        
        if not found:
            log.error(f"""Invalid file {file}""")
        elif _last_module:
            _module_list.append(_last_module.pop())

        return
    
    path = os.environ['PYTHONPATH'] + "hmc/modules/" + file.replace('.', '/')
    t_path = path
    u_path = path

    # _, ext = os.path.splitext(path)
    # if ext != '.py':
    #     t_path = path + '.py'

    # if os.path.isfile(t_path):
    #     found = _import_file(t_path)
    #     if not found:
    #         log.error(f"""Invalid file {t_path}""")
    #     elif _last_module:
    #         _module_list.append(_last_module.pop())

    #     return

    if not os.path.isdir(path):
        path = '/'.join(path.split('/')[:-1])
        file = '.'.join(file.split('.')[:-1])
        if not os.path.isdir(path):
            log.error(f"""Invalid file {path}""")
            return
    else:
        file = ''

    _ignore = [
        "__init__.py",
        "__pycache__"
    ]

    for f in os.listdir(path):
        fpath = os.path.join(path, f)
        file_name, ext = os.path.splitext(f)
        if os.path.isfile(fpath) and f not in _ignore:
            # _import_file(f)
            if ext in [".py", ".pyc"]:
                try:
                    if file != '' and file[-1] != '.':
                        file += '.'
                    __import__("hmc.modules." + file + file_name)

                    if _last_module:
                        _module_list.append(_last_module.pop())

                    log.debug(f"""{f} successfully imported""")
                except Exception as e:
                    print(e)
                    log.warning(f"""error while importing {f} : {e}""")
        elif os.path.isdir(fpath):
            _directories.append(file_name)

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

def get_module_list():
    return _module_list