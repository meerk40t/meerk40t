import argparse
import sys

from meerk40t.bootstrap import bootstrap
from . kernel import Kernel, STATE_TERMINATE
from . device.lasercommandconstants import COMMAND_WAIT_FINISH, COMMAND_MODE_RAPID, COMMAND_SET_ABSOLUTE, COMMAND_MOVE

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


def pair(value):
    rv = value.split('=')
    if len(rv) != 2:
        raise argparse.ArgumentParser()
    return rv


parser = argparse.ArgumentParser()
parser.add_argument('-V', '--version', action='store_true', help='MeerK40t version')
parser.add_argument('input', nargs='?', type=argparse.FileType('r'), help='input file')
parser.add_argument('-o', '--output', type=argparse.FileType('w'), help='output file name')
parser.add_argument('-z', '--no_gui', action='store_true', help='run without gui')
parser.add_argument('-b', '--batch', type=argparse.FileType('r'), help='console batch file')
parser.add_argument('-c', '--console', action='store_true', help='start as console')
parser.add_argument('-e', '--execute', action='append', type=str, nargs='?', help='execute console command')
parser.add_argument('-v', '--verbose', action='store_true', help='display verbose debugging')
parser.add_argument('-m', '--mock', action='store_true', help='uses mock usb device')
parser.add_argument('-q', '--quit', action='store_true', help="quit on spooler complete")
parser.add_argument('-a', '--auto', action='store_true', help='start running laser')
parser.add_argument('-s', '--set', action='append', nargs='?', type=pair, metavar='key=value',
                    help='set a device variable')
parser.add_argument('-O', '--origin', action='store_true', help="return back to 0,0 on finish")
parser.add_argument('-S', '--speed', type=float, help='set the speed of all operations')


def run():
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    if args.version:
        print("MeerK40t %s" % MEERK40T_VERSION)
        return

    kernel = Kernel()
    bootstrap(kernel,True)

    kernel_root = kernel.get_context('/')
    kernel_root.activate('modifier/Elemental')
    kernel_root.activate('modifier/Planner')
    kernel_root.activate('modifier/ImageTools')
    kernel_root.activate('modifier/BindAlias')
    kernel_root.device_version = MEERK40T_VERSION
    kernel_root.device_name = "MeerK40t"

    if not args.no_gui:
        from .gui.wxmeerk40t import wxMeerK40t

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
        kernel.active = device

    if args.verbose:
        kernel_root.execute('Debug Device')

    if args.input is not None:
        import os

        kernel_root.load(os.path.realpath(args.input.name))

    if args.mock:
        # Set the device to mock.
        device.setting(bool, 'mock', True)
        device.mock = True

    if args.quit:
        device.setting(bool, 'quit', True)
        device.quit = True

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

    if args.execute:
        kernel_root.channel('console').watch(print)
        for v in args.execute:
            device.console(v.strip() + '\n')
        kernel_root.channel('console').unwatch(print)

    if args.batch:
        kernel_root.channel('console').watch(print)
        with args.batch as batch:
            for line in batch:
                device.console(line.strip() + '\n')
        kernel_root.channel('console').unwatch(print)

    if args.console:
        kernel_root.channel('console').watch(print)
        # kernel_root.channel('shutdown').watch(print)
        while True:
            device_entries = input('>')
            if device._state == STATE_TERMINATE:
                break
            if device_entries == 'quit':
                break
            device.console(device_entries + '\n')
        kernel_root.channel('console').unwatch(print)

    if not args.no_gui:
        kernel_root.open('window/MeerK40t', None)
        meerk40tgui.MainLoop()
