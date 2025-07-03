import re
import logging
from urllib.parse import urlparse
from hmc.modules import Module, Argument

log = logging.getLogger("hmc")

class SPIPDetectPlugins(Module):
    module_name = "detect_plugins"
    module_desc = "SPIP Plugins Detection with Version Extraction"
    module_auth = "wayko"

    module_args = [
        Argument("url", desc="The target SPIP URL to scan for plugins")
    ]

    def __init__(self, env=None, print_logs=True):
        super().__init__(env, print_logs)
        self._plugins = {}
        self._common_plugins = [
            'aide', 'archiviste', 'bigup', 'compagnon', 'compresseur', 'dump', 'filtres_images',
            'forum', 'mediabox', 'medias', 'mots', 'plan', 'porte_plume', 'revisions',
            'safehtml', 'sites', 'statistiques', 'svp', 'textwheel', 'urls_etendues'
        ]

    def _log_formatted(self, protocol, host, port, message):
        self.log_success(f"{protocol:<12} {host:<22} {port:<16} {message}")

    async def _check_plugin(self, url, plugin_name, method="direct"):
        if plugin_name in self._plugins:
            return None

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        up = urlparse(url)
        protocol = up.scheme.upper()
        host = up.hostname
        port = up.port or (80 if up.scheme == 'http' else 443)
        base_url = f"{up.scheme}://{host}:{port}" if up.port else f"{up.scheme}://{host}"

        paths = [
            (f"{base_url}/plugins-dist/{plugin_name}/plugin.xml", "plugin.xml"),
            (f"{base_url}/plugins-dist/{plugin_name}/paquet.xml", "paquet.xml"),
            (f"{base_url}/plugins/{plugin_name}/plugin.xml", "plugins/plugin.xml"),
            (f"{base_url}/plugins/{plugin_name}/paquet.xml", "plugins/paquet.xml")
        ]

        for path, path_type in paths:
            try:
                response = await self.env.get(path)
                if response and response.status == 200:
                    version = re.search(r'version="([^"]+)"', response.body) or \
                              re.search(r'<version>([^<]+)</version>', response.body) or \
                              re.search(r'version\s*=\s*[\"\']([^\"\']+)[\"\']', response.body)
                    version = version.group(1) if version else "unknown"
                   
                    # CVE Verification
                    is_vuln = False
                    if plugin_name == "porte_plume":
                        def version_lt(a, b):
                            def to_list(v):
                                return list(map(int, v.split(".")))
                            return to_list(a) < to_list(b)

                        if version != "unknown" and version_lt(version, "3.2.0"):
                            is_vuln = True
                        else:
                            self._log_formatted(protocol, host, port,
                                "[+] porte_plume version is safe")

                    self._plugins[plugin_name] = {
                        'name': plugin_name,
                        'version': version,
                        'method': method,
                        'path': path_type,
                        'vulnerable': is_vuln
                    }
                    return self._plugins[plugin_name]
            except Exception:
                continue

        return None
    
    async def execute(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        up = urlparse(url)
        protocol = up.scheme.upper()
        host = up.hostname
        port = up.port or (80 if up.scheme == 'http' else 443)

        try:
            response = await self.env.get(url)
            if not response or response.status != 200:
                self._log_formatted(protocol, host, port, "[-] Could not access target page")
                return

            for plugin in self._common_plugins:
                p = await self._check_plugin(url, plugin, "common")
                if p:
                    yield{
                        'plugin':p
                    }

            self._display_results(url)
            return

        except Exception as e:
            self._log_formatted(protocol, host, port, f"[-] Error during plugin detection: {str(e)}")
            return 

    def _display_results(self, url):
        """Affiche les résultats dans le format demandé."""
        from urllib.parse import urlparse

        up = urlparse(url)
        protocol = up.scheme.upper()
        host = up.hostname or url.split('://')[1].split('/')[0]
        port = up.port or (80 if up.scheme == 'http' else 443)

        if not self._plugins:
            self._log_formatted(protocol, host, port, "[-] No SPIP plugins detected")
            return

        self._log_formatted(protocol, host, port, "[+] Detected plugins")
        self._log_formatted(protocol, host, port, "Name         Version")
        self._log_formatted(protocol, host, port, "----         -------")

        for plugin_name in sorted(self._plugins.keys()):
            plugin_info = self._plugins[plugin_name]
            version = plugin_info['version']
            vuln_flag = ""

            if plugin_info.get("vulnerable"):
                vuln_flag = " (VULNERABLE CVE-2024-7954)"

            formatted_line = f"{plugin_name:<13} {version}{vuln_flag}"
            self._log_formatted(protocol, host, port, formatted_line)
