import logging
from hmc.modules import Module, Argument
from hmc.modules.web.yaml_module import YAMLModule

log = logging.getLogger("hmc")

class DrupalDetect(Module):
    """Détection SPIP via YAMLModule"""

    module_name = "detect"
    module_desc = "Detect Drupal via YAML rules"
    module_auth = "Hatsu"

    module_args = [
        Argument("domain", desc="Durpal target URL (e.g. http://example.org)")
    ]

    async def execute(self, domain):
        url = f"http://{domain}/" if not domain.startswith(("http://", "https://")) else domain

        yaml_module = YAMLModule(env=self.env, print_logs=self.print_logs, file_path="drupal.drupal-detect")

        detected = await yaml_module.execute("drupal.drupal-detect", url)

        if detected:
            self.log_success(f"[+] Drupal detected on {url}")
            return True
        else:
            self.log_failure(f"[-] Drupal not detected on {url}")
            return False
