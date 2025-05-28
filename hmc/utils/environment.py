import requests
import logging

from typing import Any

log = logging.getLogger("hmc")

class Environment:

    def __init__(self, user_agent=None):

        self._history = {}
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
        except requests.exceptions.ConnectionError:
            return None

        self._history[url] = response
        log.debug("GET %s : %i", url, response.status_code)
        return response