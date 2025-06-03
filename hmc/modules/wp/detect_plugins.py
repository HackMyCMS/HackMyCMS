import os
import re
import logging

from urllib.parse import urlparse
from argparse import _ArgumentGroup

from hmc.modules import Module, Argument

log = logging.getLogger("hmc")

class WPDetectPlugins(Module):

    module_name = "detect_plugins"
    module_desc = "Scan the given url to find plugins revealed in the page's code"

    keys = [
        "is_wordpress",
        "wp_plugins",
        "scope"
    ]

    def __init__(self, env=None, print_logs=True, is_wordpress=None, wp_plugins={}, scope=None):
        super().__init__(env, print_logs)
        self.pipes.add_pipes(is_wordpress=is_wordpress, wp_plugins=wp_plugins, scope=scope)

    def _verify_plugin(self, url, plugin_name):
        if plugin_name in self.pipes.wp_plugins:
            return

        self.pipes.wp_plugins[plugin_name] = ''        

        up = urlparse(url)
        path = "%s://%s/wp-content/plugins/%s/readme.txt" % (up.scheme, up.hostname, plugin_name)

        page = self.env.get(path)
        if not page or page.status_code != 200:
            self.log_success("%s detected !", plugin_name)
            return

        version = re.findall(r'Stable tag: ((\d+\.?)+)', page.text)
        if version:
            self.pipes.wp_plugins[plugin_name] = version[0][0]
            self.log_success("%s %s detected !", plugin_name, version[0][0])
        else:
            self.log_success("%s detected !", plugin_name)

    def execute(self, url=None):

        if url:
            path = [url]
        elif self.pipes.scope:
            path = list(self.pipes.scope.keys())
        else:
            log.error("No url found")
            return False

        while path:
            url = path.pop(0)

            page = self.env.get(url)
            if not page:
                continue

            plugins = re.findall(r'/wp-content/plugins/([^"\'/]+)/', page.text)

            for plugin in plugins:
                self._verify_plugin(url, plugin)
            
        return True      
