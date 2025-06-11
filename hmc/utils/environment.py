import time
import aiohttp
import logging

from typing import Any
from urllib.parse import urlparse

from hmc.utils.pipes import PipesHub

log = logging.getLogger("hmc")

class Response:
    def __init__(self, status, body, headers):
        self.status  = status
        self.body    = body
        self.headers = headers

        self.text = self.body

class Environment:

    def __init__(self, user_agent=None, memory_max=15):
        
        self._hosts   = {}
        self._history = {}
        
        self._hubs = {}

        self._user_agent = user_agent
        self._memory_max = memory_max

    def get_or_create_hub(self, hub_name):
        _hub = self._hubs.get(hub_name)
        if not _hub:
            _hub = PipesHub()
            self._hubs[hub_name] = _hub
        return _hub

    def _clean_history(self):
        def sort(x):
            host, resp = x
            r, t = resp
            return t

        l = sorted(self._history.items(), key=sort)
        
        rm = l[0][0]
        self._history.pop(rm)

    def save_response(self, url, response):
        self._history[url] = (response, time.time())

        if len(self._history) > self._memory_max:
            self._clean_history()

    def get_response(self, url):
        t = self._history.get(url)
        if not t:
            return None
        resp = t[0]
        self._history[url] = (resp, time.time())
        return resp

    def connect(self, host, http=False):
        assert host not in self._hosts, "Host already connected"

        scheme = "http" if http else "https"
        self._hosts[host] = aiohttp.ClientSession(scheme + "://" + host)
    
    async def disconnect(self, host):
        assert host in self._hosts, "Host not connected"

        _session = self._hosts.get(host)
        await _session.close()

    async def get(self, url:str, update:bool=False, params=None, **kwargs) -> Response:
        if not update and self.get_response(url) is not None:
            response = self.get_response(url)
            log.debug("GET %s : %i [cached]", url, response.status)
            return response

        if not 'headers' in kwargs:
            kwargs['headers'] = {'user-agent': self._user_agent}
        elif not 'user-agent' in kwargs['headers']:
            kwargs['headers']['user-agent'] = self._user_agent

        _close = False
        up = urlparse(url)

        _session = self._hosts.get(up.hostname)
        if not _session:
            _session = aiohttp.ClientSession(up.scheme + "://" + up.hostname)
            _close = True

        try:
            async with _session.get(up.path) as response:
                text = await response.content.read()
                try:
                    text = text.decode()
                except:
                    text = ""

                result = Response(response.status, text, response.headers)
        except:
            return None

        if _close:
            await _session.close()

        self.save_response(url, result)
        log.debug("GET %s : %i", url, result.status)
        return result