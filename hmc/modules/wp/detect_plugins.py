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

    def __init__(self, env=None, print_logs=True, plugins=None, **exec_args):
        super().__init__(env, print_logs, **exec_args)
        
        self._pipes.add_hub('plugins', plugins)

        self._plugins = {}

    async def _verify_plugin(self, url, plugin_name):
        if plugin_name in self._plugins:
            return None

        # self.pipes.wp_plugins[plugin_name] = ''        
        self._plugins[plugin_name] = ''

        up = urlparse(url)
        path = "%s://%s/wp-content/plugins/%s/readme.txt" % (up.scheme, up.hostname, plugin_name)

        page = await self.env.get(path)
        if not page or page.status != 200:
            self.log_success("%s detected !", plugin_name)
            return ''

        version = re.findall(r'Stable tag: ((\d+\.?)+)', page.body)
        if version:
            self.log_success("%s %s detected !", plugin_name, version[0][0])
            self._plugins[plugin_name] = version[0][0]
            return version[0][0]
        else:
            self.log_success("%s detected !", plugin_name)
            return ''

    async def execute(self, url:str):
        page = await self.env.get(url)
        if not page:
            return

        plugins = re.findall(r'/wp-content/plugins/([^"\'/]+)/', page.body)

        for plugin in plugins:
            version = await self._verify_plugin(url, plugin)
            
            if version is not None:
                yield {'plugins': (plugin, version)}
