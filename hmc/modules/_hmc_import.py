import os
import sys
import logging

from typing import Any

log = logging.getLogger("hmc")
_path    = {}

__all__ = [
    "_import_file",
    "_get_lib",
    "_get_path",
    "load_modules"
]

def _import_file(import_file:str) -> bool:
    file_name, ext = os.path.splitext(os.path.basename(import_file))
    if ext in [".py", ".pyc"]:
        try:
            path = os.path.dirname(import_file)
            sys.path.append(os.path.abspath(path))

            __import__(file_name)

            log.debug(f"""{import_file} successfully imported""")
            return True
        except Exception as e:
            log.warning(f"""error while importing {import_file} : {e}""")
    return False

def _get_lib(base, path:str):
    s = path.split('.')
    c = getattr(base, 'modules', None)

    for p in s:
        if not c:
            return None
        c = getattr(c, p, None)
    return c

def _get_path(path:str, update=False):
    s = path.split('.')
    p = _path

    for x in s:
        if not x in p:
            if update:
                p[x] = {}
            else:
                return None
        p = p[x]
    return p

def load_modules(path:str="") -> dict:
    if os.path.isfile(path):
        found = _import_file(path)
        return {}
    
    full_path = os.path.join(os.environ['PYTHONPATH'], "hmc/modules/", path.replace('.', '/'))

    if not os.path.isdir(full_path):
        full_path = '/'.join(full_path.split('/')[:-1])
        if not os.path.isdir(full_path):
            log.error(f"""Invalid file {path}""")
            return {}
        path = '.'.join(path.split('.')[:-1])

    folder = _get_path(path, update=True)
    for d in os.listdir(full_path):
        if os.path.isdir(os.path.join(full_path, d)) and d not in ['__pycache__']:
            folder[d] = "dir"

    try:
        hmc = __import__("hmc.modules" + ('.' if path else '') + path)
    except Exception as e:
        log.error("Unable to load %s : %s", path, str(e))
        return folder

    modules = _get_lib(hmc, path)
    if not modules:
        return folder

    for module in modules.__all__:
        mod = getattr(modules, module, None)
        if not mod:
            continue
        # loaded = get_module(getattr(mod, 'module_name', ''))
        # if not loaded:
        #     continue
        folder[mod.module_name] = mod.module_desc
    
    return folder
