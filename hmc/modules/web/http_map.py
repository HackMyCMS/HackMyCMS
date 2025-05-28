import os
import re
import time
import logging

from urllib.parse import urlparse, urljoin
from argparse import ArgumentParser

from hmc.modules import ChainedModule

log = logging.getLogger("hmc")

class HTTPMap(ChainedModule):
    __module_name__ = "map"
    __module_desc__ = "Map a site"

    def __init__(self, env, web_pages={}, *args, **kwargs):
        super().__init__(env, web_pages=web_pages, *args, **kwargs)

    def printProgressBar (self, url, path, failed):
        iteration = len(self.web_pages) + 1
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

    def execute(self, domain):

        base_url = "https://%s/" % domain

        self.log_success("Scanning %s", base_url)

        path = [base_url]

        if self.web_pages is None:
            self.web_pages = {}

        self.max_len = 0
        self.d_time = []
        
        failed = []
        while path:
            url = path.pop(0)

            self.printProgressBar(url, path, failed)
            
            page = self.env.get(url)
            self.web_pages[url] = None
            if not page:
                failed.append(url)
                self.log_failure(urlparse(url).path)
                continue
            
            self.web_pages[url] = page.status_code

            result_txt = "%i - %s" % (page.status_code, urlparse(url).path)
            
            links  = re.findall(r'<a .*?href=["\'](%s[^"\']+)["\']' % base_url, page.text)
            l_path = re.findall(r'href=["\'](/[^/"\'][^"\'#?]+)["\']', page.text)

            for link in links:
                l_path.append(urlparse(link).path)

            for link in l_path:
                if link[-1] == '/':
                    link = link[:-1]

                parsed = urljoin(base_url, link)
                # file_name, ext = os.path.splitext(url_path)
                # if ext not in ['', 'html', 'php']:
                #     continue

                # TODO : Change
                # p = urlparse(parsed)
                # parsed = urljoin(parsed, p.path)
                
                if parsed not in path and parsed not in self.web_pages and parsed not in failed:
                    # print(parsed)
                    path.append(parsed)  
                    # self.log_success("\t-> %s", url_path)    
            
            self.log_success(result_txt + ' ' * (self.max_len + 29 - len(result_txt)))
        
        print()

        return True      

    def add_arguments(self, parser):
        parser.add_argument('domain', help='Target domain')
