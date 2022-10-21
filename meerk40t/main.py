"""
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed
open-source laser cutting software. See https://github.com/meerk40t/meerk40t
for full details.
"""

import argparse
import asyncio
import os
import os.path
import platform
import sys

from .core.exceptions import Mk40tImportAbort
from .kernel import Kernel

APPLICATION_NAME = "MeerK40t"
APPLICATION_VERSION = "0.7.9000"

if not getattr(sys, "frozen", False):
    # If .git directory does not exist we are running from a package like pypi
    # Otherwise we are running from source
    if os.path.isdir(sys.path[0] + "/.git"):
        APPLICATION_VERSION += " git"
    elif os.path.isdir(sys.path[0] + "/.github"):
        APPLICATION_VERSION += " src"
    else:
        APPLICATION_VERSION += " pkg"


def pair(value):
    rv = value.split("=")
    if len(rv) != 2:
        # raise argparse.ArgumentError, do not raise error.
        pass
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
parser.add_argument(
    "-A",
    "--disable-ansi",
    action="store_true",
    default=False,
    help="Disable ANSI colors",
)


def run():
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    if args.version:
        print("%s %s" % (APPLICATION_NAME, APPLICATION_VERSION))
        return
    python_version_required = (3, 6)
    if sys.version_info < python_version_required:
        print(
            "%s %s requires Python %d.%d or greater."
            % (
                APPLICATION_NAME,
                APPLICATION_VERSION,
                python_version_required[0],
                python_version_required[1],
            )
        )
        return

    if args.profile is not None:
        path = "profile%d" % args.profile
    else:
        path = ""
    kernel = Kernel(
        APPLICATION_NAME,
        APPLICATION_VERSION,
        APPLICATION_NAME,
        path,
        ansi=not args.disable_ansi,
    )

    """
    These are frozen bootstraps. They are not dynamically found by entry points they are the configured accepted
    hardcoded addons and plugins permitted by MeerK40t in a compiled bundle.
    """
    from . import kernelserver

    kernel.add_plugin(kernelserver.plugin)

    from .device.ch341 import ch341

    kernel.add_plugin(ch341.plugin)

    from .device import basedevice

    kernel.add_plugin(basedevice.plugin)

    from .core import spoolers

    kernel.add_plugin(spoolers.plugin)

    from .core import drivers

    kernel.add_plugin(drivers.plugin)

    from .core import output

    kernel.add_plugin(output.plugin)

    from .core import inputs

    kernel.add_plugin(inputs.plugin)

    from .core import elements

    kernel.add_plugin(elements.plugin)

    from .core import bindalias

    kernel.add_plugin(bindalias.plugin)

    from .core import webhelp

    kernel.add_plugin(webhelp.plugin)

    from .core import planner

    kernel.add_plugin(planner.plugin)

    from .image import imagetools

    kernel.add_plugin(imagetools.plugin)

    from .device.lhystudios import lhystudiosdevice

    kernel.add_plugin(lhystudiosdevice.plugin)

    from .device.moshi import moshidevice

    kernel.add_plugin(moshidevice.plugin)

    from .device.grbl import grbldevice

    kernel.add_plugin(grbldevice.plugin)

    from .device.ruida import ruidadevice

    kernel.add_plugin(ruidadevice.plugin)

    from .core import svg_io

    kernel.add_plugin(svg_io.plugin)

    from .extra import vectrace

    kernel.add_plugin(vectrace.plugin)

    from .extra import inkscape

    kernel.add_plugin(inkscape.plugin)

    from .extra import embroider

    kernel.add_plugin(embroider.plugin)

    from .extra import pathoptimize

    kernel.add_plugin(pathoptimize.plugin)

    from .extra import updater

    kernel.add_plugin(updater.plugin)

    if platform.system() == "Windows":
        # Windows only plugin.
        try:
            from .extra import winsleep

            kernel.add_plugin(winsleep.plugin)
        except ImportError:
            pass

    try:
        from camera import camera
    except Mk40tImportAbort as e:
        print(
            "Cannot install meerk40t 'camera' plugin - prerequisite '%s' needs to be installed"
            % e
        )
    except ImportError:
        print(
            "Cannot install external 'camera' plugin - see https://github.com/meerk40t/meerk40t-camera"
        )
    else:
        kernel.add_plugin(camera.plugin)

    try:
        from .dxf import dxf_io
    except Mk40tImportAbort as e:
        print(
            "Cannot install meerk40t 'dxf' plugin - prerequisite '%s' needs to be installed"
            % e
        )
    else:
        kernel.add_plugin(dxf_io.plugin)

    if not args.gui_suppress:
        try:
            from .gui import wxmeerk40t
            from .gui.scene import scene
        except Mk40tImportAbort as e:
            args.no_gui = True
            print(
                "Cannot install meerk40t gui - prerequisite '%s' needs to be installed"
                % e
            )
        else:
            kernel.add_plugin(wxmeerk40t.plugin)
            kernel.add_plugin(scene.plugin)
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
            except pkg_resources.DistributionNotFound:
                pass
            except pkg_resources.VersionConflict as e:
                print(
                    "Cannot install plugin - '{entrypoint}' due to version conflict.".format(
                        entrypoint=str(entry_point)
                    )
                )
                print(e)
            else:
                kernel.add_plugin(plugin)

    if args.no_gui:
        kernel.bootstrap("console")
    else:
        kernel.bootstrap("gui")

    kernel_root = kernel.root
    kernel_root.device_version = APPLICATION_VERSION
    kernel_root.device_name = "MeerK40t"

    kernel.bootstrap("preregister")
    kernel.bootstrap("register")
    kernel.bootstrap("configure")
    kernel.boot()

    console = kernel_root.channel("console")

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
            try:
                attr = v[0]
                value = v[1]
                kernel_root("set %s %s\n" % (attr, value))
            except IndexError:
                break

    kernel.bootstrap("ready")

    def __print_delegate(*args, **kwargs):
        if print not in console.watchers:
            print(*args, **kwargs)

    if args.execute:
        # Any execute code segments gets executed here.
        console.watch(__print_delegate)
        for v in args.execute:
            if v is None:
                continue
            kernel_root(v.strip() + "\n")
        console.unwatch(__print_delegate)

    if args.batch:
        # If a batch file is specified it gets processed here.
        console.watch(__print_delegate)
        unprint_console = True
        with args.batch as batch:
            for line in batch:
                kernel_root(line.strip() + "\n")
        if unprint_console:
            console.unwatch(__print_delegate)

    kernel.bootstrap("finished")

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
        kernel_root.save(os.path.realpath(args.output.name))

    if args.console:
        console.watch(__print_delegate)

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
        console.unwatch(__print_delegate)

    kernel.bootstrap("mainloop")  # This is where the GUI loads and runs.
