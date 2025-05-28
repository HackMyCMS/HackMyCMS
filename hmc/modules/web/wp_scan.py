import logging

from hmc.modules.workflow import Workflow
from hmc.modules.yaml_module import YAMLModule
from hmc.modules.web.http_map import HTTPMap
from hmc.modules.wp.detect_plugins import WPDetectPlugins 

log = logging.getLogger("hmc")

class TestYAML(Workflow):

    __module_name__ = "wp_scan"
    __module_desc__ = "Test Worpress Scan"

    def init_modules(self):

        wp = self.add_link("wordpress", False)
        pages = self.add_link("pages")

        pages_map = self.add_module(HTTPMap, web_pages=pages)
        detection = self.add_module(YAMLModule, "wordpress.wordpress_detect", result=wp, urls=pages)
        detect_plugins = self.add_module(WPDetectPlugins, is_wordpress=wp, urls=pages)

    def execute(self):
        if self.links.wordpress:
            self.log_success("Wordpress detected")
            return True

        self.log_failure("This is not a wordpress")
        return False