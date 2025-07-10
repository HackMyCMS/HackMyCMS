import logging
from hmc.modules import Module, Argument
from urllib.parse import urljoin

log = logging.getLogger("hmc")

class WPFileManagerCheck(Module):
    module_name = "wp_filemanager_check"
    module_desc = "Upload file via WP File Manager plugin (CVE-2020-25213)"
    module_auth = "sk1ll3ss"

    module_args = [
        Argument("url", desc="Target URL (e.g., http://example.com)")
    ]

    async def execute(self, url, cmd):

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        payload_url = urljoin(url, "/wp-content/plugins/wp-file-manager/lib/php/connector.minimal.php")

        try:
            response = await self.env.get(payload_url)

            if "{\"error\":[\"errUnknownCmd\"]}" in response.body:
                self.log_success("[+] Target vulnerable!")
                return {"rce": response.body.strip()}
            else:
                self.log_failure("[-] Target not vulnerable or no output.")
                return {"rce": None}
        except Exception as e:
            self.log_failure(f"[-] Error: {e}")
            return {"rce": None}
