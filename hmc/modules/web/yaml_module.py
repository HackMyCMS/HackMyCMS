import os
import re
import yaml
import logging

from urllib.parse import urlparse

from hmc.modules import Module, Argument

__all__ = [
    "YAMLModule"
]

log = logging.getLogger("hmc")

YAML_PATH = os.path.join(os.environ["PYTHONPATH"], "discovery")

def _open_yaml_file(file:str):
    file_name, file_ext = os.path.splitext(file)

    file_path = file
    if not file_ext or file_ext not in ['.yaml']:
        # Search in discovery
        path = file.replace('.', '/') + '.yaml'
        file_path = os.path.join(YAML_PATH, path)

    with open(file_path, 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)

    return data

def _complete_path(path:str, url:str=None):
    if not url:
        return path

    pu = urlparse(url)

    port = pu.port if pu.port else ("443" if pu.scheme == "https" else "80")

    replacement = {
        "BaseURL"   : pu.geturl(),
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

def _evaluate_word(matcher, text) -> bool:
    words_list = matcher.get('words', [])
    condition = matcher.get('condition', "or")

    result = condition == 'and'
    for word in words_list:
        found = word in text
        result = (result and found) if condition == 'and' else (result or found)
    return result

def _evaluate_regex(matcher, text) -> bool:
    regex_list = matcher.get('regex', [])
    condition = matcher.get('condition', "or")

    if isinstance(text, bytes):
        text = text.decode()

    result = condition == 'and'
    for regex in regex_list:
        found = re.search(regex, text) is not None
        result = (result and found) if condition == 'and' else (result or found)
    return result

def _evaluate_status(matcher, status) -> bool:
    return status == 200


class YAMLModule(Module):
    """
    Convert YAML file following the nuclei convention to an HMC module
    """

    module_name = "yaml"
    module_desc = "YAML default module"

    module_args = [
        Argument("yaml_file", "--yaml-file", "-f", desc="The yaml file to convert"),
        Argument("url", '--url', '-u', desc="The target URL"),
    ]

    def __init__(self, env=None, print_logs=True, file_path=None, result=None, **exec_args):
        super().__init__(env, print_logs=print_logs, **exec_args)

        self._pipes.add_hub('result', result)

        self.requests = []
        if file_path:
            self._args.get('yaml_file').value = file_path

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
            result.append(_complete_path(p, url))
            
        return result

    async def send_request(self, request, url=None, update=False) -> dict:
        result = {}

        method = self.get_method(request)
        path = self.get_path(request, url)

        if not method or not path:
            return result

        headers = request.get('headers', {})
        body = request.get('body', b'')

        index = 1
        for p in path:
            response = await method(p, update=update, headers=headers, data=body)
            if not response:
                break

            result['text'] = response.text
            result['status_code'] = response.status
            result['headers'] = response.headers
            result['body'] = response.body

            result['status_code_%i' % index] = response.status
            result['headers_%i' % index] = response.headers
            result['body_%i' % index] = response.body

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
                'word'  : _evaluate_word,
                'regex' : _evaluate_regex,
                'status': _evaluate_status
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

    async def execute(self, yaml_file:str, url:str):
        yaml_data = _open_yaml_file(yaml_file)
        requests = yaml_data.get('http', [])
        name = yaml_data.get('id')

        for request in requests:
            result = await self.send_request(request, url)
            found  = self.evaluate_matchers(request, result)
            if found:
                # self.pipes.output = True
                self.log_success("%s : OK", name)
                self._pipes.close()
                return True

        self.log_failure("%s : KO", name)
        return False