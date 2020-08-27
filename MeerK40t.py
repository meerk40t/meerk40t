import argparse
import sys

from Console import Console
from DefaultModules import *
from GrblDevice import GrblDevice
from LhystudiosDevice import LhystudiosDevice
from MoshiboardDevice import MoshiboardDevice
from RasterScripts import RasterScripts
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
kernel.open('module', 'Elemental')

parser = argparse.ArgumentParser()
parser.add_argument('input', nargs='?', type=argparse.FileType('r'), help='input file')
parser.add_argument('-z', '--no_gui', action='store_true', help='run without gui')
parser.add_argument('-c', '--console', action='store_true', help='start as console')
parser.add_argument('-a', '--auto', action='store_true', help='start running laser')
parser.add_argument('-p', '--path', type=str, help='add SVG Path command')
parser.add_argument('-t', '--transform', type=str, help="adds SVG Transform command")
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
# args = parser.parse_args(["-zc"])

kernel.register('static', 'RasterScripts', RasterScripts)
kernel.register('module', 'Console', Console)
kernel.register('module', 'LaserServer', LaserServer)
kernel.register('load', 'SVGLoader', SVGLoader)
kernel.register('load', 'ImageLoader', ImageLoader)
kernel.register('load', "DxfLoader", DxfLoader)
kernel.register('save', 'SVGWriter', SVGWriter)
kernel.register('device', 'Lhystudios', LhystudiosDevice)
kernel.register('disabled-device', 'Moshiboard', MoshiboardDevice)
kernel.register('disabled-device', 'Ruida', RuidaDevice)
kernel.register('disabled-device', 'GRBL', GrblDevice)

if not args.no_gui:
    from wxMeerK40t import wxMeerK40t
    kernel.register_module('wxMeerK40t', wxMeerK40t)
    meerk40tgui = kernel.open('module', 'wxMeerK40t', device=kernel)

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
        device = kernel.open('device', 'Lhystudios', instance_name='1', uid=1)
        device.boot()
        pass
    else:
        # There is a gui but the device wasn't booted.
        devices = list(kernel.derivable())
        device_entries = list()
        for dev in devices:
            try:
                device_entries.append(int(dev))
            except ValueError:
                continue
        if len(device_entries) == 0:
            # There are no device entries in the kernel.
            kernel.device_add('Lhystudios', 1)
            kernel.device_boot()
            for key, d in kernel.instances['device'].items():
                device = d
                break
        if device is None:
            #  Set device to kernel and start the DeviceManager
            device = kernel
            kernel.open('window', "DeviceManager", None)


if args.verbose:
    # Debug the device.
    device.execute('Debug Device')
    kernel.execute('Debug Device')

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
        kernel.elements.add(path)
    except Exception:
        print("SVG Path Exception to: %s" % ' '.join(sys.argv))
if args.transform:
    # Transform any data loaded data
    from svgelements import Matrix
    m = Matrix(args.transform)
    for e in kernel.elements.elems():
        e *= m
        try:
            e.modified()
        except AttributeError:
            pass

if device is not kernel:  # We can process this stuff only with a real device.
    if args.grbl is not None:
        # Start the GRBL server on the device.
        device.setting(int, 'grbl_flip_x', 1)
        device.setting(int, 'grbl_flip_y', 1)
        device.setting(int, 'grbl_home_x', 0)
        device.setting(int, 'grbl_home_y', 0)
        if args.flip_y:
            device.grbl_flip_x = -1
        if args.flip_x:
            device.grbl_flip_y = -1
        if args.adjust_y is not None:
            device.grbl_home_y = args.adjust_y
        if args.adjust_x is not None:
            device.grbl_home_x = args.adjust_x
        console = device.using('module', 'Console').write('grblserver\n')

    if args.ruida:
        console = device.using('module', 'Console').write('ruidaserver\n')

    if args.auto:
        # Automatically classify and start the job.
        elements = kernel.elements
        elements.classify(list(elements.elems()))
        device.spooler.jobs(list(elements.ops()))
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
    kernel.add_watcher('shutdown', print)
    while True:
        device_entries = input('>')
        if device.state == STATE_TERMINATE:
            break
        if device_entries == 'quit':
            break
        console.write(device_entries + '\n')

    device.remove_watcher('console', print)
if not args.no_gui:
    if device.state != STATE_TERMINATE:
        if 'device' in kernel.instances:
            for key, device in kernel.instances['device'].items():
                device.open('window', 'MeerK40t', None)
        meerk40tgui.MainLoop()
