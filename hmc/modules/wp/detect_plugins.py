import os
import re
import logging

from urllib.parse import urlparse
from argparse import _ArgumentGroup

from hmc.modules.http_module import HTTPModule

log = logging.getLogger("hmc")

class WPDetectPlugins(HTTPModule):
    __module_name__ = "detect_plugins"
    __module_desc__ = "Scan the given url to find plugins revealed in the page's code"

    def __init__(self, *args, urls={}, wp_plugins={}, is_wordpress=None, **kwargs):
        super().__init__(urls=urls, wp_plugins=wp_plugins, start=is_wordpress, *args, **kwargs)

    def _verify_plugin(self, url, plugin_name):
        if plugin_name in self.wp_plugins:
            return

        self.wp_plugins[plugin_name] = ''        
    
        up = urlparse(url)
        path = "%s://%s/wp-content/plugins/%s/readme.txt" % (up.scheme, up.hostname, plugin_name)

        page = self.env.get(path)
        if not page or page.status_code != 200:
            self.log_success("%s detected !", plugin_name)
            return

        version = re.findall(r'Stable tag: ((\d+\.?)+)', page.text)
        if version:
            self.wp_plugins[plugin_name] = version[0][0]
            self.log_success("%s %s detected !", plugin_name, version[0][0])
        else:
            self.log_success("%s detected !", plugin_name)

    def execute(self, url=None):

        if url:
            path = [url]
        elif self.urls:
            path = list(self.urls.keys())
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

    def add_arguments(self, parser:_ArgumentGroup):
        parser.description = self.__module_desc__
        parser.add_argument('-u', '--url', help='URL to scan', default=None)
