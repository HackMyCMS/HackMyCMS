import logging
import argparse

import hmc.utils.logger

from hmc.modules import load_modules, get_module, get_module_list
from hmc.utils.environment import Environment

USER_AGENT = "HMC/1.0"

parser = argparse.ArgumentParser(
    prog='hmc', 
    description='HackMyCMS: A swiss army knife for pentesting CMS', 
    add_help=False
)
parser.add_argument('module', nargs='?', help='The HMC module or application to execute')
parser.add_argument('-L', '--list', action='store_true', default=False, help="List every Modules and Applications available")
parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Enable debug log level')
parser.add_argument('-U', '--user-agent', default=USER_AGENT, help='The user-agent to use')
parser.add_argument('-h', '--help', action='store_true', default=False, help='show this help message and exit')

log = logging.getLogger("hmc")

def print_help(parser):
    parser.print_help()

args, remaining = parser.parse_known_args()

load_modules(args.module)
if args.verbose:
    log.setLevel(logging.DEBUG)
if args.list:
    modules = get_module_list()
    for module in modules:
        print('-', module.__module_name__, ':', module.__module_desc__)
    exit(0)
if not args.module and args.help:
    print(args.module)
    print_help(parser) 
    exit(0)

log.debug("Starting HMC")


mod_name = args.module.split('.')[-1]

module_cls = get_module(mod_name)
if module_cls is None:
    log.error("Module %s not found", args.module)
    exit(1)

env = Environment(user_agent=args.user_agent)

module = module_cls(env)

module_parser = argparse.ArgumentParser(
    prog='hmc %s' % module.__module_name__,
    description='HackMyCMS: A swiss army knife for pentesting CMS'
)
module.add_arguments(module_parser)
if args.help:
    module_parser.print_help()
    exit(0)

modules_args = module_parser.parse_args(remaining)
module.run(vars(modules_args))

log.debug("HMC done !")