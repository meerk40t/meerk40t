import argparse
import sys

from .device.lasercommandconstants import (
    COMMAND_MODE_RAPID,
    COMMAND_MOVE,
    COMMAND_SET_ABSOLUTE,
)
from .kernel import Kernel

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

MEERK40T_VERSION = "0.7.0 Beta-21"


def pair(value):
    rv = value.split("=")
    if len(rv) != 2:
        raise argparse.ArgumentParser()
    return rv


parser = argparse.ArgumentParser()
parser.add_argument("-V", "--version", action="store_true", help="MeerK40t version")
parser.add_argument("input", nargs="?", type=argparse.FileType("r"), help="input file")
parser.add_argument(
    "-o", "--output", type=argparse.FileType("w"), help="output file name"
)
parser.add_argument("-z", "--no_gui", action="store_true", help="run without gui")
parser.add_argument(
    "-b", "--batch", type=argparse.FileType("r"), help="console batch file"
)
parser.add_argument("-c", "--console", action="store_true", help="start as console")
parser.add_argument(
    "-e",
    "--execute",
    action="append",
    type=str,
    nargs="?",
    help="execute console command",
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="display verbose debugging"
)
parser.add_argument("-m", "--mock", action="store_true", help="uses mock usb device")
parser.add_argument(
    "-q", "--quit", action="store_true", help="quit on spooler complete"
)
parser.add_argument("-a", "--auto", action="store_true", help="start running laser")
parser.add_argument(
    "-s",
    "--set",
    action="append",
    nargs="?",
    type=pair,
    metavar="key=value",
    help="set a device variable",
)
parser.add_argument(
    "-O", "--origin", action="store_true", help="return back to 0,0 on finish"
)
parser.add_argument("-S", "--speed", type=float, help="set the speed of all operations")
parser.add_argument(
    "-P", "--profile", type=int, default=None, help="Specify a settings profile index"
)
choices = ["Lhystudios", "Moshi"]
parser.add_argument(
    "-d",
    "--device",
    type=str,
    choices=choices,
    default="Lhystudios",
    help="Specify a default boot device type",
)


def run():
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    if args.version:
        print("MeerK40t %s" % MEERK40T_VERSION)
        return

    if args.profile is not None:
        path = "profile%d" % args.profile
    else:
        path = ""
    kernel = Kernel("MeerK40t", MEERK40T_VERSION, "MeerK40t", path)

    """
    These are frozen bootstraps. They are not dynamically found by entry points they are the configured accepted
    hardcoded addons and plugins permitted by MeerK40t in a compiled bundle.
    """
    try:
        from . import kernelserver

        kernel.add_plugin(kernelserver.plugin)
    except ImportError:
        pass

    try:
        from .device.ch341 import ch341

        kernel.add_plugin(ch341.plugin)
    except ImportError:
        pass

    try:
        from .device import basedevice

        kernel.add_plugin(basedevice.plugin)
    except ImportError:
        pass

    try:
        from .core import elements

        kernel.add_plugin(elements.plugin)
    except ImportError:
        pass

    try:
        from .core import bindalias

        kernel.add_plugin(bindalias.plugin)
    except ImportError:
        pass

    try:
        from .core import webhelp

        kernel.add_plugin(webhelp.plugin)
    except ImportError:
        pass

    try:
        from .core import planner

        kernel.add_plugin(planner.plugin)
    except ImportError:
        pass

    try:
        from .image import imagetools

        kernel.add_plugin(imagetools.plugin)
    except ImportError:
        pass

    try:
        from .device.lhystudios import lhystudiosdevice

        kernel.add_plugin(lhystudiosdevice.plugin)
    except ImportError:
        pass

    try:
        from .device.moshi import moshidevice

        kernel.add_plugin(moshidevice.plugin)
    except ImportError:
        pass

    try:
        from .device.grbl import grbldevice

        kernel.add_plugin(grbldevice.plugin)
    except ImportError:
        pass

    try:
        from .device.ruida import ruidadevice

        kernel.add_plugin(ruidadevice.plugin)
    except ImportError:
        pass

    try:
        from .core import svg_io

        kernel.add_plugin(svg_io.plugin)
    except ImportError:
        pass

    try:
        from .extra import vectrace

        kernel.add_plugin(vectrace.plugin)
    except ImportError:
        pass

    try:
        from .extra import inkscape

        kernel.add_plugin(inkscape.plugin)
    except ImportError:
        pass

    try:
        from .extra import embroider

        kernel.add_plugin(embroider.plugin)
    except ImportError:
        pass

    try:
        from .extra import pathoptimize

        kernel.add_plugin(pathoptimize.plugin)
    except ImportError:
        pass

    try:
        from camera import camera

        kernel.add_plugin(camera.plugin)
    except ImportError:
        # This module cannot be loaded. opencv is missing.
        pass

    try:
        from .dxf import dxf_io

        kernel.add_plugin(dxf_io.plugin)
    except ImportError:
        # This module cannot be loaded. ezdxf missing.
        pass

    try:
        from .gui import wxmeerk40t

        kernel.add_plugin(wxmeerk40t.plugin)
    except ImportError:
        # This module cannot be loaded. wxPython missing.
        args.no_gui = True

    if not getattr(sys, "frozen", False):
        """
        These are dynamic plugins. They are dynamically found by entry points.
        """
        import pkg_resources

        for entry_point in pkg_resources.iter_entry_points("meerk40t.plugins"):
            try:
                plugin = entry_point.load()
                kernel.add_plugin(plugin)
            except pkg_resources.DistributionNotFound:
                pass

    if args.no_gui:
        kernel.bootstrap("console")
    else:
        kernel.bootstrap("gui")

    kernel_root = kernel.get_context("/")
    kernel_root.device_version = MEERK40T_VERSION
    kernel_root.device_name = "MeerK40t"

    kernel.bootstrap("register")
    kernel.bootstrap("configure")
    kernel.boot()

    devices = list()
    for dev in kernel_root.derivable():
        try:
            devices.append(int(dev))
        except ValueError:
            pass

    if len(devices) != 0:
        device = kernel_root.derive(str(devices[0]))
        device.setting(str, "device_name", args.device)
    else:
        device = kernel_root.derive("1")
        device.activate("device/%s" % args.device)
        kernel.set_active_device(device)

    if args.verbose:
        kernel_root.execute("Debug Device")

    if args.input is not None:
        # Load any input file
        import os

        kernel_root.load(os.path.realpath(args.input.name))
        elements = kernel_root.elements
        elements.classify(list(elements.elems()))

    if args.mock:
        # Set the device to mock.
        device.setting(bool, "mock", True)
        device.mock = True

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

    kernel.bootstrap("ready")

    if args.execute:
        # Any execute code segments gets executed here.
        kernel_root.channel("console").watch(print)
        for v in args.execute:
            if v is None:
                continue
            device(v.strip() + "\n")
        kernel_root.channel("console").unwatch(print)

    if args.batch:
        # If a batch file is specified it gets processed here.
        kernel_root.channel("console").watch(print)
        with args.batch as batch:
            for line in batch:
                device(line.strip() + "\n")
        kernel_root.channel("console").unwatch(print)

    if args.auto:
        # Auto start does the planning and spooling of the data.
        elements = kernel_root.elements
        if args.speed is not None:
            for o in elements.ops():
                o.speed = args.speed
        device("plan copy preprocess validate blob preopt optimize\n")
        if args.origin:
            device("plan append origin\n")
        if args.quit:
            device("plan append shutdown\n")
        device("plan spool\n")
    else:
        if args.quit:
            # Flag quitting on complete.
            device._quit = True

    if args.output is not None:
        # output the file you have at this point.
        import os

        kernel_root.save(os.path.realpath(args.output.name))

    if args.console:
        # Console command gives the user text access to the console as a whole.
        def thread_text_console():
            kernel_root.channel("console").watch(print)
            while True:
                console_command = input(">")
                if device._kernel.lifecycle == "shutdown":
                    return
                device(console_command + "\n")
                if console_command in ("quit", "shutdown"):
                    break
            kernel_root.channel("console").unwatch(print)

        if args.no_gui:
            thread_text_console()
        else:
            kernel.threaded(thread_text_console, thread_name="text_console", daemon=True)

    kernel.bootstrap("mainloop")  # This is where the GUI loads and runs.


