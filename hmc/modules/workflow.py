import logging
import argparse

from hmc.modules import ChainedModule, ChainedKeys

log = logging.getLogger("hmc")

class KeyBank:

    _keys = {}

    def add_key(self, key, value):
        self._keys[key] = value
    
    def remove_key(self, key):
        self._keys.pop(key)

    def __getattribute__(self, name):
        if name == '_keys' or name not in self._keys:
            return super().__getattribute__(name)
        return self._keys[name]._value

class Workflow(ChainedModule):

    __module_desc__ = "Base workflow"

    def __init__(self, env,*args, **kwargs):
        super().__init__(*args, **kwargs)

        self.modules = []

        self._activ = []
        self._done  = []

        self.links = KeyBank()
        
        self.init_modules()

    def init_modules(self):
        return

    def get_link(self, link):
        return self.links._keys.get(link)

    def add_link(self, name, value=None):
        n_key = ChainedKeys(value)
        self.links.add_key(name, n_key)

        return n_key

    def add_module(self, module_cls, *args, **kwargs):
        module = module_cls(self.env, *args, **kwargs)
        self.modules.append(module)
        
        return module

    def add_arguments(self, parser:argparse.ArgumentParser) -> None:
        for module in self.modules:
            try:
                module_group = parser.add_argument_group(module.__module_name__, module.__module_desc__)
                module.add_arguments(module_group)                    
            except argparse.ArgumentError as e:
                log.warning("Argument %s used by multiple modules", e.argument_name)

    def _get_activ_modules(self):
        # TODO : optimize
        for module in self.modules:
            if module.check_activation():
                self._activ.append(module)
        for module in self._activ:
            self.modules.remove(module)

    def run(self, kwargs):
        self._get_activ_modules()
        while self._activ:
            for module in self._activ:
                try:
                    module.run(kwargs)
                    self._done.append(module)
                except Exception as e:
                    log.error("in module '%s' - %s", module.__module_name__, e)
            self._activ = []
            self._get_activ_modules()

        return super().run(kwargs)
        
