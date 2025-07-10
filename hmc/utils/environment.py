import time
import aiohttp
import logging

from typing import Any
from urllib.parse import urlparse, urlencode

from hmc.utils.pipes import PipesHub

log = logging.getLogger("hmc")

class Response:
    def __init__(self, status, body, headers):
        self.status  = status
        self.body    = body
        self.headers = headers

        self.text = self.body

class Environment:

    def __init__(self, user_agent=None, proxy=None, memory_max=15):
        
        self._hosts   = {}
        self._history = {}
        
        self._hubs = {}

        self._user_agent = user_agent
        self._proxy      = proxy
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

    def connect(self, host, https=False):
        assert host not in self._hosts, "Host already connected"

        scheme = "https" if https else "http"
        self._hosts[host] = aiohttp.ClientSession(scheme + "://" + host)
    
    async def disconnect(self, host):
        assert host in self._hosts, "Host not connected"

        _session = self._hosts.get(host)
        await _session.close()

    async def get(self, url: str, update: bool = False, **kwargs):
        return await self._request('get', url, update, **kwargs)

    async def post(self, url: str, **kwargs):
        return await self._request('post', url, True, **kwargs)

    async def _request(self, rtype: str, url: str, update: bool = False, **kwargs) -> Response:
        params = kwargs.get('params', {})
        url = url.rstrip('/')
        if params:
            full_url = url + '?' + urlencode(params)
        else:
            full_url = url

        if not update and self.get_response(full_url) is not None:
            response = self.get_response(full_url)
            log.debug("%s %s : %i [cached]", rtype.upper(), full_url, response.status)
            return response
        
        if 'headers' not in kwargs:
            kwargs['headers'] = {'user-agent': self._user_agent}
        elif 'user-agent' not in kwargs['headers']:
            kwargs['headers']['user-agent'] = self._user_agent

        if self._proxy and 'proxy' not in kwargs:
            kwargs['proxy'] = self._proxy

        up = urlparse(full_url)

        _session = self._hosts.get(up.hostname)
        _close = False
        if not _session:
            base = f"{up.scheme}://{up.hostname}" + (f":{up.port}" if up.port else "")
            _session = aiohttp.ClientSession(base_url=base)
            _close = True

        if self._proxy:
            request_url = full_url  
        else:
            request_url = up.path
            if up.query:
                request_url += '?' + up.query

        requests = {
            "get": lambda session, path, **kw: session.get(path, allow_redirects=True, timeout=5, **kw),
            "post": lambda session, path, **kw: session.post(path, allow_redirects=True, timeout=5, **kw),
        }

        try:
            async with requests[rtype](_session, request_url, **kwargs) as response:
                text = await response.read()
                try:
                    text = text.decode()
                except Exception:
                    text = ""

                result = Response(response.status, text, response.headers)
        except Exception as e:
            log.warning("Request failed: %s", e)
            if _close:
                await _session.close()
            return None

        if _close:
            await _session.close()

        self.save_response(full_url, result)
        log.debug("%s %s : %i", rtype.upper(), full_url, result.status)
        return result
