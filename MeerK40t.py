import argparse
import sys

from Console import Console
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
parser.add_argument('-z', '--no_gui', action='store_true', help='run without gui')
parser.add_argument('-c', '--console', action='store_true', help='start as console')
parser.add_argument('-a', '--auto', action='store_true', help='start running laser')
parser.add_argument('-p', '--path', type=str, help='add SVG Path command')
parser.add_argument('-t', '--transform', type=str, help="adds SVG Transform command")
parser.add_argument('-i', '--input', type=argparse.FileType('r'), help='input file name')
parser.add_argument('-o', '--output', type=argparse.FileType('w'), help='output file name')
parser.add_argument('-v', '--verbose', action='store_true', help='display verbose debugging')
parser.add_argument('-m', '--mock', action='store_true', help='uses mock usb device')
parser.add_argument('-s', '--set', action='append', nargs='+', help='set a device variable')
parser.add_argument('-b', '--batch', type=argparse.FileType('r'), help='console batch file')
parser.add_argument('-gs', '--grbl', type=int, help='run grbl-emulator on given port.')
parser.add_argument('-gy', '--flip_y', action='store_true', help="grbl y-flip")
parser.add_argument('-gx', '--flip_x', action='store_true', help="grbl x-flip")
parser.add_argument('-ga', '--adjust_x', type=int, help='adjust grbl home_x position')
parser.add_argument('-gb', '--adjust_y', type=int, help='adjust grbl home_y position')
parser.add_argument('-rs', '--ruida', action='store_true', help='run ruida-emulator')
args = parser.parse_args(sys.argv[1:])

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

kernel.boot()
device = None

if 'device' in kernel.instances:
    # Device was booted by kernel boot.
    for key, d in kernel.instances['device'].items():
        device = d
        break
else:
    if args.no_gui:
        # Without a booted device, if also no gui, just start a default device.
        device = kernel.open('device', 'Lhystudios')
        device.boot()
    else:
        # There is a gui but the device wasn't booted. Set device to kernel and start the DeviceManager
        device = kernel
        kernel.open('window', "DeviceManager", None, -1, "")


if args.verbose:
    # Debug the device.
    device.execute('Debug Device')

if args.input is not None:
    # load the given filename.
    import os

    kernel.load(os.path.realpath(args.input.name))

if args.path is not None:
    # Force the inclusion of the path.
    from svgelements import Path
    try:
        path = Path(args.path)
        path.stroke = Color('blue')
        kernel.elements.append(path)
    except Exception:
        print("SVG Path Exception to: %s" % ' '.join(sys.argv))
if args.transform:
    # Transform any data loaded data
    from svgelements import Matrix
    m = Matrix(args.transform)
    for e in kernel.elements:
        e *= m

if device is not kernel:  # We can process this stuff since only with a real device.
    if args.grbl is not None:
        # Start the GRBL server on the device.
        emulator = device.open('module', 'GrblEmulator')
        if args.flip_y:
            emulator.flip_y = -1
        if args.flip_x:
            emulator.flip_x = -1
        if args.adjust_y is not None and args.adjust_x is not None:
            emulator.home_adjust = (args.adjust_x, args.adjust_y)
        elif args.adjust_y is not None:
            emulator.home_adjust = (0, args.adjust_y)
        elif args.adjust_x is not None:
            emulator.home_adjust = (args.adjust_x, 0)
        try:
            server = kernel.open('module', 'LaserServer', port=args.server, tcp=True)
            server.set_pipe(emulator)
        except OSError:
            print('Grblserver failed on port: %d' % args.grbl)
            from sys import exit
            exit(1)
    if args.ruida:
        console = device.using('module', 'Console').write('ruidaserver\n')
    if args.auto:
        # Automatically classify and start the job.
        kernel.classify(kernel.elements)
        device.spooler.send_job(kernel.operations)
        device.setting(bool, 'quit', True)
        device.quit = True

if args.set is not None:
    # Set the variables requested here.
    for var in args.set:
        if len(var) <= 1:
            continue  # Need at least two for a set.
        attr = var[0]
        value = var[1]
        if hasattr(device, attr):
            v = getattr(device, attr)
            if isinstance(v, bool):
                setattr(device, attr, bool(value))
            elif isinstance(v, int):
                setattr(device, attr, int(value))
            elif isinstance(v, float):
                setattr(device, attr, float(value))
            elif isinstance(v, str):
                setattr(device, attr, str(value))
if args.mock:
    # Set the device to mock.
    device.setting(bool, 'mock', True)
    device.mock = True
if args.output is not None:
    import os
    kernel.save(os.path.realpath(args.output.name))
if args.batch:
    device.add_watcher('console', print)
    console = device.using('module', 'Console')
    with args.batch as batch:
        for line in batch:
            console.write(line.strip() + '\n')
    device.remove_watcher('console', print)
if args.console:
    console = device.using('module', 'Console')
    device.add_watcher('console', print)
    while True:
        q = input('>')
        if q == 'quit':
            break
        console.write(q + '\n')
    device.remove_watcher('console', print)
if not args.no_gui:
    if 'device' in kernel.instances:
        for key, device in kernel.instances['device'].items():
            device.open('window', 'MeerK40t', None, -1, "")
    meerk40tgui.MainLoop()