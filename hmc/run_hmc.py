import logging
import argparse
import asyncio

import hmc.utils.logger

from hmc.modules import load_modules, get_module, list_modules, Argument
from hmc.utils.environment import Environment

USER_AGENT = "HMC/1.0"

parser = argparse.ArgumentParser(
    prog='hmc', 
    description='HackMyCMS: A swiss army knife for pentesting CMS', 
    add_help=False
)
module_action = parser.add_argument('module', nargs='?', help='The HMC module or application to execute', default="")
parser.add_argument('-L', '--list', action='store_true', default=False, help="List every Modules and Applications available")
parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Enable debug log level')
parser.add_argument('-U', '--user-agent', default=USER_AGENT, help='The user-agent to use')
parser.add_argument('-p', '--proxy', default=None, help='Proxy (e.g., http://127.0.0.1:8080)')
parser.add_argument('-h', '--help', action='store_true', default=False, help='show this help message and exit')

log = logging.getLogger("hmc")

def print_help(parser):
    parser.print_help()

def fill_parser(args:list[Argument], parser:argparse.ArgumentParser):
    for arg in args.values():
        k = {}

        if "arg_type" in arg.attr and arg.attr.get("arg_type") == bool:
            k['action'] = "store_true"
        if 'default' in arg.attr:
            k['default'] = arg.attr.get("default")

        keys = arg.keys if arg.keys else [arg.name]

        parser.add_argument(*keys, help=arg.desc, **k)

args, remaining = parser.parse_known_args()

if args.verbose:
    log.setLevel(logging.DEBUG)
if args.list:
    modules = list_modules(args.module)
    for module_name, module_desc in modules.items():
        if module_desc == "dir":
            print(f"\033[1;34m[*]\033[0m {module_name}")
        else:
            print(f"\033[1;34m[*]\033[0m {module_name:<24} {module_desc}")
    exit(0)
if not args.module or (not args.module and args.help):
    print(args.module)
    print_help(parser) 
    exit(0)

log.debug("Starting HMC")

load_modules(args.module)
mod_name = args.module.split('.')[-1]

module_cls = get_module(mod_name)
if module_cls is None:
    log.error("Module %s not found", args.module)
    exit(1)

env = Environment(user_agent=args.user_agent, proxy=args.proxy)

module = module_cls(env)

parser._remove_action(module_action)
module_parser = argparse.ArgumentParser(
    prog='hmc %s' % module.module_name,
    description=module.module_desc,
    conflict_handler='resolve',
    parents=[parser],
)

fill_parser(module.get_arguments(), module_parser)

if args.help:
    module_parser.print_help()
    exit(0)

modules_args = module_parser.parse_args(remaining)

module.set_arguments(**modules_args.__dict__)

try:
    asyncio.run(module.run())
except KeyboardInterrupt:
    print()
    print("(x_x)")

log.debug("HMC done !")