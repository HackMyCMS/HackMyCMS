import os
import re
import logging

from urllib.parse import urlparse
from argparse import ArgumentParser

from hmc.modules.http_module import HTTPModule

log = logging.getLogger("hmc")

class HTTPMap(HTTPModule):
    __module_name__ = "map"
    __module_desc__ = "Map a site"

    def execute(self, domain):

        base_url = "https://%s/" % domain

        self.log_success("Scanning %s", base_url)

        path = [base_url]
        
        found = {base_url: 0}

        while path:
            url = path.pop(0)

            page = self.env.get(url)

            found[url] = page.status_code
            self.log_success("%i - %s" % (page.status_code, urlparse(url).path))
            
            links  = re.findall(r'<a .*?href=["\'](%s[^"\']+)["\']' % base_url, page.text)
            l_path = re.findall(r'href=["\'](/[^/"\'][^"\']+)["\']', page.text)
            # print(links)
            # print(l_path)

            for link in links:
                l_path.append(urlparse(link).path)

            for link in l_path:
                parsed = base_url + link[1:]
            
                # file_name, ext = os.path.splitext(url_path)
                # if ext not in ['', 'html', 'php']:
                #     continue

                if parsed not in path and parsed not in found:
                    path.append(parsed)  
                    # self.log_success("\t-> %s", url_path)          

    def add_arguments(self, parser):
        parser.add_argument('-d', '--domain', help='Target domain')
