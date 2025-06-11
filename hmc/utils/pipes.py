import asyncio
import logging

from typing import Any, Callable

log = logging.getLogger("hmc")

class Pipe:
    
    def __init__(self, name, parent):
        self._name = name
        self._parent = parent

        self._connected = False

    def write(self, data):
        self._parent._append_content(self._name, data)

    def close(self):
        self._parent.close_pipe(self._name)

    def connect(self):
        self._connected = True

    @property
    def connected(self) -> bool:
        return self._connected

class PipeSet:
    
    def __init__(self, pipes:list[str]):
        self._is_closed = False
        self._closing = False
        
        self._contents = []
        self._pipes = {}
        self._hubs  = {}

        for pipe in pipes:
            self._pipes[pipe] = Pipe(pipe, self)
        self._update = None

    def _append_content(self, pipe:str, data:Any):
        assert pipe in self._pipes, "Invalid pipe %s" % pipe

        self._contents.append((pipe, data))
        
        if self._update:
            self._update.set()
            self._update = None

    def add_hub(self, hub_name, hub):
        self._hubs[hub_name] = hub

    def write(self, hub, data):
        _hub = self._hubs.get(hub)
        if _hub:
            _hub.write(data)

    async def read(self):
        assert self._update is None, "Pipe already waiting"
        
        if not self._contents:
            self._update = asyncio.Event()
            await self._update.wait()

        if len(self._contents) <= 1 and self._closing:
            self._is_closed = True
 
        if self._contents:
            return self._contents.pop(0)

        return None, None

    def close(self):
        if self._update:
            self._update.set()
        self._is_closed = True

    def write_eof(self):
        if not self._is_closed:
            self.close()

        for hub in self._hubs.values():
            hub.close_writer(self)
    
    def close_pipe(self, pipe):
        _pipe = self._pipes.pop(pipe)
        if not _pipe:
            raise ValueError("Invalid pipe %s" % pipe)
        
        for pipe in self._pipes.values():
            if pipe.connected:
                return
        if self._contents:
            self._closing = True
        else:
            self.close()

    def closed(self) -> bool:
        return self._is_closed

class PipesHub:
    
    def __init__(self, workflow=None):
        self._pipes     = []
        self._modules   = []
        self._condition = []
        self._contents  = []

        self._opened    = False
        self._closed    = False
        self._workflow  = workflow

        self._writers   = []

    def add_ouptut(self, attr:str, obj):
        _pipe = obj.get_pipe(attr)
        if not _pipe:
            raise ValueError("%s.execute() has no attribute %s" % (obj.module_name, attr))
        if _pipe in self._pipes:
            raise ValueError("%s:%s already connected" % (obj.module_name, attr))

        self._pipes.append(_pipe)
        self._modules.append(obj)            
        _pipe.connect()

    def add_entry(self, attr:str, obj):
        # TODO : verifie obj        
        obj._pipes.add_hub(attr, self)
        self._writers.append(obj._pipes)

    def add_condition(self, obj, condition):
        self._condition.append((condition, obj))

    def write(self, data):
        self._contents.append(data)

        if self._workflow:
            _mods = self._modules.copy()
            for obj in _mods:
                if self._workflow.activate(obj):
                    self._modules.remove(obj)
            conditions = self._condition.copy()
            for c in conditions:
                _cond, _obj = c
                if _cond(data):
                    self._workflow.activate(_obj)
                    self._condition.remove(c) 
        self._opened = True

        for pipe in self._pipes:
            pipe.write(data)

    def write_eof(self, data=None):
        if data:
            self.write(data)
        self.close()

    def close(self):
        self._closed = True

        for pipe in self._pipes:
            pipe.close()

    def close_writer(self, writer):
        if writer in self._writers:
            self._writers.remove(writer)
        if not self._writers:
            self.close()