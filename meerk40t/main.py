import argparse
import sys

from .core.exceptions import Mk40tImportAbort
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
APPLICATION_NAME = "MeerK40t"
APPLICATION_VERSION = "0.8.0-beta1"

if not getattr(sys, "frozen", False):
    APPLICATION_VERSION += " src"


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
        print("%s %s" % (APPLICATION_NAME, APPLICATION_VERSION))
        return
    python_version_required = (3, 5)
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
    kernel = Kernel(APPLICATION_NAME, APPLICATION_VERSION, APPLICATION_NAME, path)
    kernel.args = args

    """
    These are frozen plugins. They are not dynamically found by entry points they are the configured accepted
    hardcoded addons and plugins permitted by MeerK40t in a compiled bundle.
    """
    from . import kernelserver

    kernel.add_plugin(kernelserver.plugin)

    from .device.ch341 import ch341

    kernel.add_plugin(ch341.plugin)

    from .lihuiyu import device as lhystudios_driver

    kernel.add_plugin(lhystudios_driver.plugin)

    from .moshi import device as moshi_driver

    kernel.add_plugin(moshi_driver.plugin)

    from .grbl import device as grbl_driver

    kernel.add_plugin(grbl_driver.plugin)

    from .ruida import device as ruida_driver

    kernel.add_plugin(ruida_driver.plugin)

    # from .device import dummydevice
    #
    # kernel.add_plugin(dummydevice.plugin)

    from .core import spoolers

    kernel.add_plugin(spoolers.plugin)

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

    if sys.platform == "win32":
        # Windows only plugin.
        try:
            from .extra import winsleep

            kernel.add_plugin(winsleep.plugin)
        except ImportError:
            pass

    try:
        from meerk40t.camera import camera
    except Mk40tImportAbort as e:
        print(
            "Cannot install meerk40t 'camera' plugin - prerequisite '%s' needs to be installed"
            % e
        )
    # except ImportError:
    #     print(
    #         "Cannot install external 'camera' plugin - see https://github.com/meerk40t/meerk40t-camera"
    #     )
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
            from .grbl.gui import gui as grblgui
            from .gui import wxmeerk40t
            from .gui.scene import scene
            from .camera.gui import gui as cameragui
            from .lihuiyu.gui import gui as lhygui
            from .moshi.gui import gui as moshigui
            from .ruida.gui import gui as ruidagui
        except Mk40tImportAbort as e:
            args.no_gui = True
            print(
                "Cannot install meerk40t gui - prerequisite '%s' needs to be installed"
                % e
            )
        else:
            kernel.add_plugin(wxmeerk40t.plugin)
            kernel.add_plugin(scene.plugin)
            kernel.add_plugin(lhygui.plugin)
            kernel.add_plugin(moshigui.plugin)
            kernel.add_plugin(grblgui.plugin)
            kernel.add_plugin(ruidagui.plugin)
            kernel.add_plugin(cameragui.plugin)
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
                try:
                    plugin = entry_point.load()
                except ImportError:
                    continue  # Registered plugin suffered import error.
            except pkg_resources.DistributionNotFound:
                pass
            else:
                kernel.add_plugin(plugin)

    kernel()
