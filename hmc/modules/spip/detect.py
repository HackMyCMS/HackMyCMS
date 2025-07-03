import logging
from hmc.modules import Module, Argument
from hmc.modules.web.yaml_module import YAMLModule

log = logging.getLogger("hmc")

class SPIPDetect(Module):
    """Détection SPIP via YAMLModule"""

    module_name = "detect"
    module_desc = "Detect SPIP via YAML rules"
    module_auth = "wayko"

    module_args = [
        Argument("domain", desc="SPIP target URL (e.g. http://example.org)")
    ]

    async def execute(self, domain):
        url = f"http://{domain}/" if not domain.startswith(("http://", "https://")) else domain

        yaml_module = YAMLModule(env=self.env, print_logs=self.print_logs, file_path="spip.spip_detect")

        detected = await yaml_module.execute("spip.spip_detect", url)

        if detected:
            self.log_success(f"[+] SPIP detected on {url}")
            return True
        else:
            self.log_failure(f"[-] SPIP not detected on {url}")
            return False
