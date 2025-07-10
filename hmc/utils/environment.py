import time
import aiohttp
import logging

from typing import Any
from urllib.parse import urlparse, urlencode, parse_qs

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
        _nhost = aiohttp.ClientSession(scheme + "://" + host, proxy=self._proxy)
        self._hosts[host] = _nhost
        return _nhost

    def get_session(self, host:str) -> aiohttp.ClientSession:
        return self._hosts.get(host, None)

    async def disconnect(self, host):
        assert host in self._hosts, "Host not connected"

        _session = self._hosts.get(host)
        await _session.close()

    async def get(self, url: str, update: bool = False, **kwargs):
        return await self._request('get', url, update, **kwargs)

    async def post(self, url: str, **kwargs):
        return await self._request('post', url, True, **kwargs)

    async def _request(self, rtype: str, url: str, update: bool = False, **kwargs) -> Response:
        params = kwargs.get('params')
        _url_full = url + (('?' + urlencode(params)) if params else '')

        if not update and self.get_response(_url_full) is not None:
            response = self.get_response(_url_full)
            log.debug("%s %s : %i [cached]", rtype.upper(), _url_full, response.status)
            return response
        
        if 'headers' not in kwargs:
            kwargs['headers'] = {'user-agent': self._user_agent}
        elif 'user-agent' not in kwargs['headers']:
            kwargs['headers']['user-agent'] = self._user_agent

        if self._proxy and 'proxy' not in kwargs:
            kwargs['proxy'] = self._proxy

        up = urlparse(url)

        _session = self._hosts.get(up.hostname)
        _close = False
        if not _session:
            base = f"{up.scheme}://{up.hostname}" + (f":{up.port}" if up.port else "")
            _session = aiohttp.ClientSession(base_url=base, proxy=self._proxy)
            _close = True

        request_url = f"{up.scheme}://{up.netloc}{up.path}"
        if up.query:
            kwargs['params'] = parse_qs(up.query)

        requests = {
            "get" : lambda session, path, **kw: session.get (path, allow_redirects=True, timeout=2, **kw),
            "post": lambda session, path, **kw: session.post(path, allow_redirects=True, timeout=2, **kw),
        }

        if rtype not in requests:
            return None

        try:
            async with requests.get(rtype)(_session, request_url, **kwargs) as response:
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

        self.save_response(_url_full, result)
        log.debug("%s %s : %i", rtype.upper(), _url_full, result.status)
        return result
