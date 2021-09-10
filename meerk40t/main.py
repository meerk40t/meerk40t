import argparse
import asyncio
import sys

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

MEERK40T_VERSION = "0.7.0 RC-13d"

if not getattr(sys, "frozen", False):
    MEERK40T_VERSION += "s"


def pair(value):
    rv = value.split("=")
    if len(rv) != 2:
        raise argparse.ArgumentError
    return rv


parser = argparse.ArgumentParser()
parser.add_argument("-V", "--version", action="store_true", help="MeerK40t version")
parser.add_argument("input", nargs="?", type=argparse.FileType("r"), help="input file")
parser.add_argument(
    "-o", "--output", type=argparse.FileType("w"), help="output file name"
)
parser.add_argument("-z", "--no-gui", action="store_true", help="run without gui")
parser.add_argument(
    "-Z", "--gui-suppress", action="store_true", help="completely suppress gui"
)
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
parser.add_argument(
    "-p",
    "--no-plugins",
    action="store_true",
    help="Do not load meerk40t.plugins entrypoints",
)


def run():
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    if args.version:
        print("MeerK40t %s" % MEERK40T_VERSION)
        return
    python_version_required = (3, 5)
    if sys.version_info < python_version_required:
        print("MeerK40t %s requires Python %d.%d or greater." %
              (
                    MEERK40T_VERSION,
                    python_version_required[0],
                    python_version_required[1])
              )
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
        from .core import spoolers

        kernel.add_plugin(spoolers.plugin)
    except ImportError:
        pass

    try:
        from .core import drivers

        kernel.add_plugin(drivers.plugin)
    except ImportError:
        pass

    try:
        from .core import output

        kernel.add_plugin(output.plugin)
    except ImportError:
        pass

    try:
        from .core import inputs

        kernel.add_plugin(inputs.plugin)
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

    if not args.gui_suppress:
        try:
            from .gui import wxmeerk40t

            kernel.add_plugin(wxmeerk40t.plugin)

            from .gui.scene import scene

            kernel.add_plugin(scene.plugin)
        except ImportError:
            # This module cannot be loaded. wxPython missing.
            args.no_gui = True
    else:
        # Complete Gui Suppress implies no-gui.
        args.no_gui = True

    if not getattr(sys, "frozen", False) and not args.no_plugins:
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

    kernel_root = kernel.root
    kernel_root.device_version = MEERK40T_VERSION
    kernel_root.device_name = "MeerK40t"

    kernel.bootstrap("preregister")
    kernel.bootstrap("register")
    kernel.bootstrap("configure")
    kernel.boot()

    device_context = kernel.get_context("devices")
    if not hasattr(device_context, "_devices") or device_context._devices == 0:
        if args.device == "Moshi":
            dev = "spool0 -r driver -n moshi output -n moshi\n"
        else:
            dev = "spool0 -r driver -n lhystudios output -n lhystudios\n"
        kernel_root(dev)

    if args.verbose:
        kernel._start_debugging()
        kernel_root.execute("Debug Device")

    if args.input is not None:
        # Load any input file
        import os

        kernel_root.load(os.path.realpath(args.input.name))
        elements = kernel_root.elements
        elements.classify(list(elements.elems()))

    if args.mock:
        # TODO: Mock needs to find the settings of the active output and set that value there.
        # Set the device to mock.
        kernel_root.setting(bool, "mock", True)
        kernel_root.mock = True

    if args.set is not None:
        # Set the variables requested here.
        for v in args.set:
            attr = v[0]
            value = v[1]
            kernel_root("set %s %s\n" % (attr, value))

    kernel.bootstrap("ready")

    if args.execute:
        # Any execute code segments gets executed here.
        kernel_root.channel("console").watch(print)
        for v in args.execute:
            if v is None:
                continue
            kernel_root(v.strip() + "\n")
        kernel_root.channel("console").unwatch(print)

    if args.batch:
        # If a batch file is specified it gets processed here.
        kernel_root.channel("console").watch(print)
        with args.batch as batch:
            for line in batch:
                kernel_root(line.strip() + "\n")
        kernel_root.channel("console").unwatch(print)

    if args.auto:
        # Auto start does the planning and spooling of the data.
        elements = kernel_root.elements
        if args.speed is not None:
            for o in elements.ops():
                o.speed = args.speed
        kernel_root("plan copy preprocess validate blob preopt optimize\n")
        if args.origin:
            kernel_root("plan append origin\n")
        if args.quit:
            kernel_root("plan append shutdown\n")
        kernel_root("plan spool\n")
    else:
        if args.quit:
            # Flag quitting on complete.
            kernel_root._quit = True

    if args.output is not None:
        # output the file you have at this point.
        import os

        kernel_root.save(os.path.realpath(args.output.name))

    if args.console:
        kernel_root.channel("console").watch(print)

        async def aio_readline(loop):
            while kernel.lifecycle != "shutdown":
                print(">>", end="", flush=True)

                line = await loop.run_in_executor(None, sys.stdin.readline)
                kernel_root("." + line + "\n")
                if line in ("quit", "shutdown"):
                    break

        loop = asyncio.get_event_loop()
        loop.run_until_complete(aio_readline(loop))
        loop.close()
        kernel_root.channel("console").unwatch(print)

    kernel.bootstrap("mainloop")  # This is where the GUI loads and runs.
