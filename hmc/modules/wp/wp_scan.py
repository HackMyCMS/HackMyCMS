import logging

from hmc.modules import Workflow
from hmc.modules.web import HTTPMap, YAMLModule
from hmc.modules.wp import WPDetectPlugins

log = logging.getLogger("hmc")

class WPScan(Workflow):

    module_name = "wp_scan"
    module_desc = "Test Worpress Scan"

    def init_modules(self):

        wp = self.add_pipe("wordpress", False)
        scope = self.add_pipe("scope")

        self.add_module(HTTPMap(page_list=scope))
        self.add_module(YAMLModule(file_path="wordpress.wordpress_detect", output=wp, scope=scope))
        # self.add_module(WPDetectPlugins(is_wordpress=wp, scope=scope))

    def execute(self):
        if self.pipes.wordpress:
            self.log_success("Wordpress detected")
            return True

        self.log_failure("This is not a wordpress")
        return False