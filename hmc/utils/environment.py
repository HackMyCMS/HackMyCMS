import requests

from typing import Any

class Environment:

    def __init__(self, user_agent=None):

        self._history = {}
        self._user_agent = user_agent

    def get(self, url:str, update:bool=False, params=None, **kwargs) -> requests.Response:
        if not update and self._history.get(url) is not None:
            return self._history.get(url)

        if not 'headers' in kwargs:
            kwargs['headers'] = {'user-agent': self._user_agent}
        elif not 'user-agent' in kwargs['headers']:
            kwargs['headers']['user-agent'] = self._user_agent

        response = requests.get(url=url, params=params, **kwargs)

        self._history[url] = response
        return response