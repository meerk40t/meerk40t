import argparse
import sys

from DefaultModules import *
from GrblDevice import GrblDevice
from LhystudiosDevice import LhystudiosDevice
from MoshiboardDevice import MoshiboardDevice
from RuidaDevice import RuidaDevice
from LaserServer import *

try:
    from math import tau
except ImportError:
    from math import pi

    tau = pi * 2

"""
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed 
open-source laser cutting software. See https://github.com/meerk40t/meerk40t
for full details.

"""

kernel = Kernel()
kernel.open('module', 'Signaler')

# TODO: CLI Needs an option to change default speed, etc, parameters.
# TODO: CLI Needs home command / lock, unlock.
# TODO: CLI Needs command for load special module.

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--list', type=str, nargs="*", help='list all device properties')
parser.add_argument('-z', '--no_gui', action='store_true', help='run without gui')
parser.add_argument('-a', '--auto', action='store_true', help='start running laser')
parser.add_argument('-e', '--egv', type=str, help='writes raw egv data to the controller')
parser.add_argument('-p', '--path', type=str, help='add SVG Path command')
parser.add_argument('-c', '--control', nargs='+', help="execute control command")
parser.add_argument('-i', '--input', type=argparse.FileType('r'), help='input file name')
parser.add_argument('-o', '--output', type=argparse.FileType('w'), help='output file name')
parser.add_argument('-v', '--verbose', action='store_true', help='display verbose debugging')
parser.add_argument('-t', '--transform', type=str, help="adds SVG Transform command")
parser.add_argument('-m', '--mock', action='store_true', help='uses mock usb device')
parser.add_argument('-s', '--set', action='append', nargs='+', help='set a device variable')
args = parser.parse_args(sys.argv[1:])
subparser = parser.add_subparsers()
parser_grbl = subparser.add_parser('grbl')
parser_grbl.add_argument('-s', '--server', type=int, help='run grbl-emulator on given port.')
parser_grbl.add_argument('-y', '--flip_y', action='store_true', help="grbl y-flip")
parser_grbl.add_argument('-x', '--flip_x', action='store_true', help="grbl x-flip")
parser_grbl.add_argument('-a', '--adjust_x', type=int, help='adjust grbl home_x position')
parser_grbl.add_argument('-b', '--adjust_y', type=int, help='adjust grbl home_y position')
grbl = parser_grbl.parse_args(sys.argv[1:])

if not args.no_gui:
    from wxMeerK40t import wxMeerK40t
    kernel.register_module('wxMeerK40t', wxMeerK40t)
    meerk40tgui = kernel.open('module', 'wxMeerK40t')

kernel.register('module', 'Console', Console)
kernel.register('module', 'LaserServer', LaserServer)
kernel.register('load', 'SVGLoader', SVGLoader)
kernel.register('load', 'ImageLoader', ImageLoader)
kernel.register('load', 'EgvLoader', EgvLoader)
kernel.register('load', 'RDLoader', RDLoader)
kernel.register('load', "DxfLoader", DxfLoader)
kernel.register('save', 'SVGWriter', SVGWriter)
kernel.register('device', 'Lhystudios', LhystudiosDevice)
kernel.register('device', 'Moshiboard', MoshiboardDevice)
kernel.register('device', 'Ruida', RuidaDevice)
kernel.register('device', 'GRBL', GrblDevice)
kernel.register('module', 'RuidaEmulator', RuidaEmulator)
kernel.register('module', 'GrblEmulator', GRBLEmulator)

console = kernel.module_instance_open('Console')

if grbl.server is not None:
    emulator = kernel.module_instance_open('GrblEmulator')
    if grbl.flip_y:
        emulator.flip_y = -1

    if grbl.flip_x:
        emulator.flip_x = -1

    if grbl.adjust_y is not None and grbl.adjust_x is not None:
        emulator.home_adjust = (grbl.adjust_x, grbl.adjust_y)
    elif grbl.adjust_y is not None:
        emulator.home_adjust = (0, grbl.adjust_y)
    elif grbl.adjust_x is not None:
        emulator.home_adjust = (grbl.adjust_x, 0)
    try:
        server = kernel.module_instance_open('LaserServer', port=grbl.server)
        server.set_pipe(emulator)
    except OSError:
        print('Server failed on port: %d' % args.grbl)
        from sys import exit
        exit(1)

if args.list is not None:
    list_name = 'type'
    if len(args.list) != 0:
        list_name = args.list[0]
    if list_name == 'type':
        for v in ('type', 'vars', 'controls'):
            print("Permitted List: %s" % v)
    elif list_name == 'vars':
        for attr in dir(kernel.device):
            v = getattr(kernel.device, attr)
            if attr.startswith('_') or not isinstance(v, (int, float, str, bool)):
                continue
            print('"%s" := %s' % (attr, str(v)))
    elif list_name == 'controls':
        for control_name in kernel.instances['control']:
            print('Control: %s' % control_name)
    exit(0)

if args.set is not None:
    for var in args.set:
        if len(var) <= 1:
            continue  # Need at least two for a set.
        attr = var[0]
        value = var[1]
        if hasattr(kernel.device, attr):
            v = getattr(kernel.device, attr)
            if isinstance(v, bool):
                setattr(kernel.device, attr, bool(value))
            elif isinstance(v, int):
                setattr(kernel.device, attr, int(value))
            elif isinstance(v, float):
                setattr(kernel.device, attr, float(value))
            elif isinstance(v, str):
                setattr(kernel.device, attr, str(value))

if args.input is not None:
    import os

    kernel.load(os.path.realpath(args.input.name))

if args.path is not None:
    from svgelements import Path
    try:
        kernel.elements.append(Path(args.path))
    except Exception:
        pass

if args.verbose:
    kernel.device.execute('Debug Device')

if args.transform:
    m = Matrix(args.transform)
    for e in kernel.elements:
        e *= m

if args.mock:
    kernel.device.setting(bool, 'mock', True)
    kernel.device.mock = True

if args.egv is not None:
    kernel.device.pipe.write(bytes(args.egv.replace('$', '\n') + '\n', "utf8"))

if args.control is not None:
    for control in args.control:
        if control in kernel.instances['control']:
            kernel.device.execute(control)
        else:
            print("Control '%s' not found." % control)
            exit(1)

if args.auto:
    kernel.classify(kernel.elements)
    kernel.device.spooler.send_job(kernel.operations)
    kernel.device.setting(bool, 'quit', True)
    kernel.device.quit = True

if args.output is not None:
    import os

    kernel.save(os.path.realpath(args.output.name))

kernel.boot()
if not args.no_gui:
    if 'device' in kernel.instances:
        for key, device in kernel.instances['device'].items():
            device.open('module', 'MeerK40t', None, -1, "")
    else:
        # No devices were booted. Launch DeviceManager
        kernel.open('module', "DeviceManager", None, -1, "")
    meerk40tgui.MainLoop()
