import os
import re
import time
import logging

from urllib.parse import urlparse, urljoin
from argparse import ArgumentParser

from hmc.modules import Module, Argument

log = logging.getLogger("hmc")

class HTTPMap(Module):
    module_name = "map"
    module_desc = "Map a site"

    args = [
        Argument("domain", desc="The domain to scan"),
        Argument("--http", desc="Use HTTP instead of HTTPS", arg_type=bool, default=False)
    ]

    keys = [
        "page_list"
    ]

    def __init__(self, env=None, page_list={}):
        super().__init__(env)

        self.pipes.add_pipes(page_list=page_list)

    def printProgressBar (self, url, path, failed):
        if not self.print_logs:
            return

        iteration = len(self.pipes.page_list) + 1
        total = iteration + len(path) + len(failed)

        prefix = "[%i/%i] %s" % (iteration, total, urlparse(url).path)
        if len(prefix) > self.max_len:
            self.max_len = len(prefix)
        prefix += ' ' * (self.max_len - len(prefix))
        
        self.d_time.append(time.time())
        if len(self.d_time) > 4:
            if len(self.d_time) > 10:
                self.d_time = self.d_time[-10:]
            delta = 0
            for i in range(1, len(self.d_time)):
                delta += self.d_time[i] - self.d_time[i-1]
            delta /= len(self.d_time) - 1

            suffix = '%is  ' % (round(delta, 0) * (total-iteration))
        else:
            suffix = ''

        decimals = 0
        length = 25
        fill = '█'
        printEnd = "\r"

        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)

    def execute(self, domain:str, http:bool=False):

        scheme = "http" if http else "https"
        base_url = "%s://%s/" % (scheme, domain)

        self.log_success("Scanning %s", base_url)

        path = [base_url]

        if self.pipes.page_list is None:
            self.pipes.page_list = {}

        self.max_len = 0
        self.d_time = []
        
        failed = []
        while path:
            url = path.pop(0)

            self.printProgressBar(url, path, failed)
            
            page = self.env.get(url)
            self.pipes.page_list[url] = None
            if not page:
                failed.append(url)
                self.log_failure(urlparse(url).path)
                continue
            
            self.pipes.page_list[url] = page.status_code

            result_txt = "%i - %s" % (page.status_code, urlparse(url).path)
            
            links  = re.findall(r'<a .*?href=["\'](%s[^"\']+)["\']' % base_url, page.text)
            l_path = re.findall(r'href=["\'](/[^/"\'][^"\'#?]+)["\']', page.text)

            for link in links:
                l_path.append(urlparse(link).path)

            for link in l_path:
                if link[-1] == '/':
                    link = link[:-1]

                parsed = urljoin(base_url, link)
                if parsed not in path and parsed not in self.pipes.page_list and parsed not in failed:
                    path.append(parsed)  
            
            self.log_success(result_txt + ' ' * (self.max_len + 29 - len(result_txt)))
        
        print()

        return True      

    # def add_arguments(self, parser):
    #     parser.add_argument('domain', help='Target domain')
