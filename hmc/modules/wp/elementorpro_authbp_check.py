import logging
from hmc.modules import Module, Argument
from urllib.parse import urljoin

log = logging.getLogger("hmc")

class ElementorProAuthBypassCheck(Module):
    module_name = "elementor_pro_auth_bypass_check"
    module_desc = "Elementor Pro Plugin Auth Bypass Check (CVE-2022-3590)"
    module_auth = "sk1ll3ss"

    module_args = [
        Argument("url", desc="Target URL (e.g., http://example.com)")
    ]

    async def execute(self, url):

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        vuln_path = "/wp-json/elementor-pro/v1/users/register"
        full_url = urljoin(url, vuln_path)

        try:
            response = await self.env.get(full_url)

            if response.status == 200 and "user_email" in response.body:
                self.log_success("[+] Potential Elementor Pro auth bypass vulnerability!")
                return {"vuln": True}
            else:
                self.log_failure("[-] Target not vulnerable or endpoint disabled.")
                return {"vuln": False}
        except Exception as e:
            self.log_failure(f"[-] Error: {e}")
            return {"vuln": False}
