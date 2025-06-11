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
    module_auth = "Mageos"

    module_args = [
        Argument("domain", desc="The domain to scan"),
        Argument("http", "--http", desc="Use HTTP instead of HTTPS", arg_type=bool, default=False)
    ]

    def printProgressBar (self, url, path, found, failed):
        if not self.print_logs:
            return

        iteration = len(found) + 1
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

    async def execute(self, domain:str, http:bool=False):

        scheme = "http" if http else "https"
        base_url = "%s://%s/" % (scheme, domain)

        self.log_success("Scanning %s", base_url)

        path = [base_url]

        self.max_len = 0
        self.d_time = []
        
        found  = []
        failed = []
        while path:
            url = path.pop(0)

            self.printProgressBar(url, path, found, failed)
            
            page = await self.env.get(url)
            # self.pipes.page_list[url] = None
            if not page:
                failed.append(url)
                self.log_failure(urlparse(url).path)
                continue
            
            found.append(url)
            # self.pipes.page_list[url] = page.status_code

            result_txt = "%i - %s" % (page.status, urlparse(url).path)
            
            links  = re.findall(r'<a .*?href=["\'](%s[^"\']+)["\']' % base_url, page.text)
            l_path = re.findall(r'href=["\'](/[^/"\'][^"\'#?]+)["\']', page.text)

            for link in links:
                l_path.append(urlparse(link).path)

            for link in l_path:
                if link[-1] == '/':
                    link = link[:-1]

                parsed = urljoin(base_url, link)
                if parsed not in path and parsed not in found and parsed not in failed:
                    path.append(parsed)  
            

            count = len(found) + len(path) + len(failed) 
            self.log_success(result_txt + ' ' * (self.max_len + 29 - len(result_txt)))            
            yield {
                "url": url,
                "count": count
            }
