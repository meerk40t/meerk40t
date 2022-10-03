"""
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed
open-source laser cutting software. See https://github.com/meerk40t/meerk40t
for full details.
"""
import argparse
import os.path
import sys

from meerk40t.kernel import Kernel

APPLICATION_NAME = "MeerK40t"
APPLICATION_VERSION = "0.8.0032 Beta24"

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
    "-P", "--profile", type=int, default=None, help="Specify a settings profile index"
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


def static_plugins(kernel, lifecycle):
    if lifecycle == "plugins":
        plugins = list()

        from . import kernelserver

        plugins.append(kernelserver.plugin)

        from .device import basedevice

        plugins.append(basedevice.plugin)

        from .lihuiyu import device as lihuiyu

        plugins.append(lihuiyu.plugin)

        from .moshi import device as moshi_driver

        plugins.append(moshi_driver.plugin)

        from .grbl.plugin import plugin as grbl_driver_plugin

        plugins.append(grbl_driver_plugin)

        from .ruida import device as ruida_driver

        plugins.append(ruida_driver.plugin)

        from .rotary import rotary

        plugins.append(rotary.plugin)

        from .core import spoolers

        plugins.append(spoolers.plugin)

        from .core import elements

        plugins.append(elements.plugin)

        from .core import bindalias

        plugins.append(bindalias.plugin)

        from .core import webhelp

        plugins.append(webhelp.plugin)

        from .core import planner

        plugins.append(planner.plugin)

        from .image import imagetools

        plugins.append(imagetools.plugin)

        from .core import svg_io

        plugins.append(svg_io.plugin)

        from .fill import fills

        plugins.append(fills.plugin)

        from .extra import vectrace

        plugins.append(vectrace.plugin)

        from .extra import potrace

        plugins.append(potrace.plugin)

        from .extra import inkscape

        plugins.append(inkscape.plugin)

        from .extra import hershey

        plugins.append(hershey.plugin)

        from .extra import embroider

        plugins.append(embroider.plugin)

        from .extra import pathoptimize

        plugins.append(pathoptimize.plugin)

        from .extra import updater

        plugins.append(updater.plugin)

        from .extra import winsleep

        plugins.append(winsleep.plugin)

        from meerk40t.camera.plugin import plugin as camera_plugin

        plugins.append(camera_plugin)

        from .dxf.plugin import plugin as dxf_io_plugin

        plugins.append(dxf_io_plugin)

        from .extra import cag

        plugins.append(cag.plugin)

        from .balormk.plugin import plugin as balorplugin

        kernel.add_plugin(balorplugin)

        from .gui.plugin import plugin as wxplugin

        plugins.append(wxplugin)

        from .extra.imageactions import plugin as splitterplugin

        plugins.append(splitterplugin)

        return plugins

    if lifecycle == "invalidate":
        return True


def dynamic_plugins(kernel, lifecycle):
    """
    These are dynamic plugins. They are dynamically found by entry points.
    """
    if lifecycle == "plugins":
        if getattr(sys, "frozen", False):
            return
        if kernel.args.no_plugins:
            return

        plugins = list()
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
                plugins.append(plugin)
        return plugins
    if lifecycle == "invalidate":
        return True


def run():
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    # Old python version checks. 2/3 compat code.
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
    kernel = Kernel(
        APPLICATION_NAME,
        APPLICATION_VERSION,
        APPLICATION_NAME,
        ansi=not args.disable_ansi,
    )
    kernel.args = args
    kernel.add_plugin(static_plugins)
    kernel.add_plugin(dynamic_plugins)
    kernel()
