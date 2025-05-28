import re
import logging

from argparse import ArgumentParser
from urllib.parse import urlparse

from hmc.modules import ChainedModule

log = logging.getLogger("hmc")

def complete_path(path:str, url:str=None):
    if not url:
        return path

    pu = urlparse(url)

    port = pu.port if pu.port else ("443" if pu.scheme == "https" else "80")

    replacement = {
        "BaseURL"   : pu.geturl()[:-1],
        "RootURL"   : pu.scheme + "://" + pu.hostname + (':' + pu.port if pu.port else ""),
        "Hostname"  : pu.hostname + (':' + pu.port if pu.port else ""),
        "Host"      : pu.hostname,
        "Port"      : port,
        "Path"      : pu.path,
        "File"      : url.split("/")[-1],
        "Scheme"    : pu.scheme
    }

    for key, value in replacement.items():
        path = path.replace('{{%s}}' % (key), value)
    
    return path

def evaluate_word(matcher, text) -> bool:
    words_list = matcher.get('words', [])
    condition = matcher.get('condition', "or")

    result = condition == 'and'
    for word in words_list:
        found = word in text
        result = (result and found) if condition == 'and' else (result or found)
    return result

def evaluate_regex(matcher, text) -> bool:
    regex_list = matcher.get('regex', [])
    condition = matcher.get('condition', "or")

    if isinstance(text, bytes):
        text = text.decode()

    result = condition == 'and'
    for regex in regex_list:
        found = re.search(regex, text) is not None
        result = (result and found) if condition == 'and' else (result or found)
    return result

def evaluate_status(matcher, status) -> bool:
    return status == 200

class HTTPModule(ChainedModule):
    # __module_name__ = "http_module"
    __module_desc__ = "Send HTTP requests"

    # requests = [
    #     {
    #         'method': 'GET',
    #         'path': [
    #             "{{BaseURL}}"
    #         ],
    #         'matchers': [
    #             {
    #                 'type': 'regex',
    #                 'regex': [
    #                     "www.*.org"
    #                 ],
    #                 'part': 'body_1'
    #             }
    #         ]
    #     }
    # ]

    requests = []

    def __init__(self, env, update:bool=False, urls=None, *args, **kwargs):
        super().__init__(env, urls=urls, *args, **kwargs)

        self.update = update

    def get_method(self, request):
        implemented_methods = {
            'GET': self.env.get
        }

        method = request.get('method')
        if not method:
            log.error("'method' field not found")
            return None
        if method not in implemented_methods:
            log.error("Method %s not implemented", method)
            return None

        return implemented_methods[method]

    def get_path(self, request, url):
        path = request.get('path')
        if not path:
            log.error("'path' field not found")
            return

        result = []
        for p in path:
            result.append(complete_path(p, url))
            
        return result

    def send_request(self, request, url=None) -> dict:
        result = {}

        method = self.get_method(request)
        path = self.get_path(request, url)

        if not method or not path:
            return result

        headers = request.get('headers', {})
        body = request.get('body', b'')

        index = 1
        for p in path:
            response = method(p, update=self.update, headers=headers, data=body)
            if not response:
                break

            result['text'] = response.text
            result['status_code'] = response.status_code
            result['headers'] = response.headers
            result['body'] = response.content

            result['status_code_%i' % index] = response.status_code
            result['headers_%i' % index] = response.headers
            result['body_%i' % index] = response.content

            index += 1

        return result

    def evaluate_matchers(self, request, outputs) -> bool:
        if not request:
            return False

        matchers_condition = request.get('matchers-condition', "and")
        matchers = request.get("matchers")
        if not matchers:
            log.error("'matchers' field not found")
            return False

        result = matchers_condition == 'and'
        for matcher in matchers:
            types = {
                'word'  : evaluate_word,
                'regex' : evaluate_regex,
                'status': evaluate_status
            }

            matcher_type = matcher.get("type")
            if not matcher_type in types:
                log.error("Invalide matcher type %s", matcher_type)
                return False

            part = matcher.get('part', "text")
            if matcher_type == 'status':
                part = 'status_code'

            if not part in outputs:
                log.error("Invalide matcher part %s", part)
                return False

            
            found = types[matcher_type](matcher, outputs[part])
            result = (result and found) if matchers_condition == 'and' else (result or found)

        return result

    def execute(self, url):
        
        found = False
        for request in self.requests:
            result = self.send_request(request, url)
            found  |= self.evaluate_matchers(request, result)

        return found

    def add_arguments(self, parser):
        parser.add_argument('-u', '--url', help='Target URL')