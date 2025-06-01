import requests
import logging

from typing import Any

log = logging.getLogger("hmc")

class PipeSet:
    """
    Store a set of pipes
    :param list<str> keys: List of keys to add by default (values are None)
    """

    class _Pipe:
        value = None

        def __str__(self):
            return str(self.value)
        
        def __repr__(self):
            return str(self)

    _pipes:dict = {}
    
    def __init__(self, keys:list=[]):
        for key in keys:
            self._pipes[key] = self._Pipe()

    def add_pipes(self, **pipes) -> None:
        """
        Add the given keys and values to the PipeSet's attributes
        """
        for key, value in pipes.items():
            self.add_pipe(key, value)

    def add_pipe(self, key, value):
        if isinstance(value, self._Pipe):
            self._pipes[key] = value
        else:
            if key not in self._pipes:
                self._pipes[key] = self._Pipe()
            self._pipes[key].value = value
        return self._pipes[key]
        
    @property
    def pipes(self):
        return self._pipes.keys()

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except Exception as e:
            pipe = self._pipes.get(name)
            if name is not None:
                return pipe.value
            raise e

    def __setattr__(self, name, value):
        if name in dir(self) or name not in self._pipes:
            return super().__setattr__(name, value)
        self._pipes[name].value = value

class Environment:

    def __init__(self, user_agent=None):

        self._history = {}
        self.pipes = PipeSet()

        self._user_agent = user_agent

    def get(self, url:str, update:bool=False, params=None, **kwargs) -> requests.Response:
        if not update and self._history.get(url) is not None:
            response = self._history.get(url)
            log.debug("GET %s : %i [cached]", url, response.status_code)
            return response

        if not 'headers' in kwargs:
            kwargs['headers'] = {'user-agent': self._user_agent}
        elif not 'user-agent' in kwargs['headers']:
            kwargs['headers']['user-agent'] = self._user_agent
    
        try:
            response = requests.get(url=url, params=params, **kwargs)
        except requests.exceptions.ConnectionError as e:
            log.debug(e)
            return None

        self._history[url] = response
        log.debug("GET %s : %i", url, response.status_code)
        return response