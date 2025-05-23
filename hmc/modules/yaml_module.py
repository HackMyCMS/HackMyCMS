import os
import yaml
import logging

from urllib.parse import urlparse

from hmc.modules.http_module import HTTPModule

log = logging.getLogger("hmc")

YAML_PATH = os.environ["PYTHONPATH"] + "discovery"

def open_yaml_file(file:str):
    file_name, file_ext = os.path.splitext(file)

    file_path = file
    if not file_ext or file_ext not in ['.yaml']:
        # Search in discovery
        path = file.replace('.', '/') + '.yaml'
        file_path = os.path.join(YAML_PATH, path)

    with open(file_path, 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)

    return data   

class YAMLModule(HTTPModule):
    """
        Entries:
            - condition
        Outputs:
            - result
    """

    __module_name__ = "yaml"
    __module_desc__ = "YAML default module"

    # Keys
    condition = None
    result = None

    def __init__(self, env, file_path=None, execute:bool=None, result:bool=None, print_result=False):
        super().__init__(env, execute=execute, result=result)

        self._name = None
        self._print = print_result

        if file_path:
            yaml_data = open_yaml_file(file_path)
            self.requests = yaml_data.get('http', [])
            self._name = yaml_data.get('id')

    def execute(self, url, yaml_file:str=None):
        yaml_data = None
        if yaml_file:
            yaml_data = open_yaml_file(yaml_file)
            self.requests = yaml_data.get('http', [])
            self._name = yaml_data.get('id')

        result = super().execute(url)
        if self._name and self._print:
            if result:
                self.log_success("%s : OK", self._name)
            else:
                self.log_failure("%s : KO", self._name)
        self.result = result

    def check_activation(self):
        return self.condition is None or self.condition

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('yaml_file', help='Path to the yaml module', nargs="?")
        