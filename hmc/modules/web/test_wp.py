import logging

from hmc.modules.workflow import Workflow
from hmc.modules.yaml_module import YAMLModule 

log = logging.getLogger("hmc")

class TestYAML(Workflow):

    __module_name__ = "test_wp"
    __module_desc__ = "Test Worpress Scan"

    def init_modules(self):

        wp = self.add_link("wordpress", False)

        detection = self.add_module(YAMLModule, "wordpress.wordpress_detect", result=wp)
        sfl = self.add_module(YAMLModule, "wordpress.wp_simplefilelist_detect", execute=wp, print_result=True)

    def execute(self):
        if self.links.wordpress:
            self.log_success("Wordpress detected")
            return True

        self.log_failure("This is not a wordpress")
        return False