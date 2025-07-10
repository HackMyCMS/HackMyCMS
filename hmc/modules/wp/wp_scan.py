import logging

from urllib.parse import urlparse

from hmc.utils.pipes import PipesHub
from hmc.modules import Workflow, ModuleState, Argument
from hmc.modules.web import HTTPMap, YAMLModule
from hmc.modules.wp import WPDetectPlugins

log = logging.getLogger("hmc")

MAX_LEN = 100

class WPScan(Workflow):

    module_name = "wp_scan"
    module_desc = "Test Worpress Scan"

    module_args = [
        Argument("domain", desc="The target to scan")
    ]

    _count   = 0
    _pages   = []

    def log_success(self, msg:str, *args):
        if len(msg) < MAX_LEN:
            msg += ' ' * (MAX_LEN - len(msg))
        super().log_success(msg, *args)

    def print_bar(self):
        max_len = 50
        iteration = len(self._pages) + 1
        total = self._count + 1

        prefix = "[%i/%i] %s" % (iteration, total, urlparse(self._pages[-1]).path)
        if len(prefix) > max_len:
            prefix = prefix[:max_len-3] + '...'
        else:
            prefix += ' ' * (max_len - len(prefix))
        
        decimals = 0
        length = 25
        fill = '█'
        printEnd = "\r"
        suffix = ''

        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)

        if self.print_logs:
            print(f'\r[*] ({self.module_name}) {prefix} |{bar}| {percent}% {suffix}', end = printEnd)

    def init_modules(self):
        # self.add_hub("entry", PipesHub(self))
        # scope   = self.add_hub("scope", PipesHub(self))
        # wp      = self.add_hub("wp", PipesHub(self))
        # plugins = self.add_hub("plugins", PipesHub(self))
        # count   = self.add_hub("count", PipesHub(self))

        self.add_module(
            HTTPMap(),
            entries={'domain':'domain'},
            outputs={
                'url'        :'url',
                'pages_count':'count'
            }
        )
        self.add_module(
            YAMLModule(file_path="wordpress.wordpress_detect"),
            entries={'url':'url'},
            outputs={'wp' :'result'}
        )
        self.add_module(
            WPDetectPlugins(),
            entries={'url'    :'url'},
            outputs={'plugins':'plugins'},
            condition=(['wp'], lambda x: x == True)
        )

    def data_received(self, pipe, data):
        # print(pipe, data)
        if pipe == 'wp' and data == True:
            self.log_success("Wordpress detected !")
            self.log_success("")
            self.log_success('Wordpress Plugins:')
        elif pipe == 'plugins':
            plugin, version = data
            self.log_success(f"- {plugin} {version}")
        elif pipe == 'url':
            self._pages.append(data)
            # self.print_bar()
        elif pipe == 'pages_count':
            self._count = data
            self.print_bar()

    async def execute(self, domain):
        self.env.connect(domain)

        self.get_hub('domain').write_eof(domain)
        
        await self.wait_until_done()

        await self.env.disconnect(domain)

        self.log_success("")
        self.log_success('WP Scan done!')
