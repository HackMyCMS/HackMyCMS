import logging
from hmc.modules import Module, Argument
from urllib.parse import urljoin

log = logging.getLogger("hmc")

class WPRESTAPIContentInjectionCheck(Module):
    module_name = "wp_rest_api_content_injection_check"
    module_desc = "WordPress REST API Post Content Injection (CVE-2017-5487)"
    module_auth = "sk1ll3ss"

    module_args = [
        Argument("url", desc="Target URL (e.g., http://example.com)")
    ]

    async def execute(self, url):

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        api_url = urljoin(url, "/wp-json/wp/v2/posts/1")

        try:
            response = await self.env.get(api_url)

            if response.status == 200 and '"id":1' in response.body:
                self.log_success("[+] Target vulnerable to REST API Post Injection!")
                return {"vuln": True}
            else:
                self.log_failure("[-] Target not vulnerable or post not accessible.")
                return {"vuln": False}
        except Exception as e:
            self.log_failure(f"[-] Error: {e}")
            return {"vuln": False}
