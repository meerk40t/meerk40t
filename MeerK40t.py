import argparse
import sys

from BaseDevice import Spooler
from BindAlias import BindAlias
from CutPlanner import Planner
from DefaultModules import *
from Elements import Elemental
from GrblDevice import GrblDevice
from ImageTools import ImageTools
from LaserCommandConstants import *
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
MEERK40T_VERSION = '0.7.0'
kernel = Kernel()

kernel.register('modifier/Spooler', Spooler)
kernel.register('modifier/BindAlias', BindAlias)
kernel.register('modifier/Elemental', Elemental)
kernel.register('modifier/Planner', Planner)
kernel.register('modifier/ImageTools', ImageTools)

def pair(value):
    rv = value.split('=')
    if len(rv) != 2:
        raise argparse.ArgumentParser()
    return rv


parser = argparse.ArgumentParser()
parser.add_argument('input', nargs='?', type=argparse.FileType('r'), help='input file')
parser.add_argument('-z', '--no_gui', action='store_true', help='run without gui')
parser.add_argument('-V', '--version', action='store_true', help='MeerK40t version')
parser.add_argument('-c', '--console', action='store_true', help='start as console')
parser.add_argument('-a', '--auto', action='store_true', help='start running laser')
parser.add_argument('-p', '--path', type=str, help='add SVG Path command')
parser.add_argument('-t', '--transform', type=str, help="adds SVG Transform command")
parser.add_argument('-o', '--output', type=argparse.FileType('w'), help='output file name')
parser.add_argument('-v', '--verbose', action='store_true', help='display verbose debugging')
parser.add_argument('-m', '--mock', action='store_true', help='uses mock usb device')
parser.add_argument('-s', '--set', action='append', nargs='?', type=pair, metavar='key=value', help='set a device variable')
parser.add_argument('-H', '--home', action='store_true', help="prehome the device")
parser.add_argument('-O', '--origin', action='store_true', help="return back to 0,0 on finish")
parser.add_argument('-b', '--batch', type=argparse.FileType('r'), help='console batch file')
parser.add_argument('-S', '--speed', type=float, help='set the speed of all operations')
parser.add_argument('-gs', '--grbl', type=int, help='run grbl-emulator on given port.')
parser.add_argument('-gy', '--flip_y', action='store_true', help="grbl y-flip")
parser.add_argument('-gx', '--flip_x', action='store_true', help="grbl x-flip")
parser.add_argument('-ga', '--adjust_x', type=int, help='adjust grbl home_x position')
parser.add_argument('-gb', '--adjust_y', type=int, help='adjust grbl home_y position')
parser.add_argument('-rs', '--ruida', action='store_true', help='run ruida-emulator')

args = parser.parse_args(sys.argv[1:])

if args.version:
    print("MeerK40t %s" % MEERK40T_VERSION)
else:
    kernel.register('static/RasterScripts', RasterScripts)
    kernel.register('module/TCPServer', TCPServer)
    kernel.register('module/UDPServer', UDPServer)
    kernel.register('load/SVGLoader', SVGLoader)
    kernel.register('load/ImageLoader', ImageLoader)
    kernel.register('load/DxfLoader', DxfLoader)
    kernel.register('save/SVGWriter', SVGWriter)
    kernel.register('device/Lhystudios', LhystudiosDevice)
    kernel.register('disabled-device/Moshiboard', MoshiboardDevice)
    kernel.register('disabled-device/Ruida', RuidaDevice)
    kernel.register('disabled-device/GRBL', GrblDevice)

    kernel_root = kernel.get_context('/')
    kernel_root.device_version = "0.7.0"
    kernel_root.device_name = "MeerK40t"
    kernel_root.activate('modifier/Elemental')
    kernel_root.activate('modifier/Planner')
    kernel_root.activate('modifier/ImageTools')
    kernel_root.activate('modifier/BindAlias')

    if not args.no_gui:
        from wxMeerK40t import wxMeerK40t

        kernel.register('module/wxMeerK40t', wxMeerK40t)
        meerk40tgui = kernel_root.open('module/wxMeerK40t')

    kernel.boot()

    device_entries = list()
    for dev in kernel_root.derivable():
        try:
            device_entries.append(int(dev))
        except ValueError:
            pass

    if len(device_entries) != 0:
        device = kernel_root.derive(str(device_entries[0]))
        device_name = device.setting(str, 'device_name', 'Lhystudios')
    else:
        device = kernel_root.derive('1')
        device.activate('device/Lhystudios')

    if args.verbose:
        kernel_root._process_spooled_item('Debug Device')

    if args.input is not None:
        import os

        kernel_root.load(os.path.realpath(args.input.name))

    if args.path is not None:
        # Force the inclusion of the path.
        from svgelements import Path
        try:
            path = Path(args.path)
            path.stroke = Color('blue')
            kernel_root.elements.add_elem(path)
        except Exception:
            print("SVG Path Exception to: %s" % ' '.join(sys.argv))

    if args.transform:
        # Transform any data loaded data
        from svgelements import Matrix
        m = Matrix(args.transform)
        for e in kernel_root.elements.elems():
            e *= m
            try:
                e.modified()
            except AttributeError:
                pass

    if args.set is not None:
        # Set the variables requested here.
        for v in args.set:
            attr = v[0]
            value = v[1]
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

    # We can process this stuff only with a real device.
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
        console = device.console('grblserver\n')

    if args.ruida:
        console = device.console('ruidaserver\n')

    if args.home:
        console = device.console('home\n')
        device.setting(bool, 'quit', True)
        device.quit = True

    if args.auto:
        # Automatically classify and start the job.
        elements = kernel.elements
        elements.classify(list(elements.elems()))
        ops = list(elements.ops())
        if args.speed is not None:
            for o in ops:
                o.speed = args.speed
        device.spooler.jobs(ops)
        device.setting(bool, 'quit', True)
        device.quit = True

    if args.origin:
        def origin():
            yield COMMAND_WAIT_FINISH
            yield COMMAND_MODE_RAPID
            yield COMMAND_SET_ABSOLUTE
            yield COMMAND_MOVE, 0, 0
        device.spooler.job(origin)

    if args.output is not None:
        import os
        kernel_root.save(os.path.realpath(args.output.name))

    if args.batch:
        device.channel('console').watch(print)
        with args.batch as batch:
            for line in batch:
                device.console(line.strip() + '\n')
        device.channel('console').unwatch(print)

    if args.console:
        device.channel('console').watch(print)
        kernel_root.channel('shutdown').watch(print)
        while True:
            device_entries = input('>')
            if device._state == STATE_TERMINATE:
                break
            if device_entries == 'quit':
                break
            device.console(device_entries + '\n')
        device.channel('console').unwatch(print)


    if not args.no_gui:
        kernel_root.open('window/MeerK40t', None)
        meerk40tgui.MainLoop()
