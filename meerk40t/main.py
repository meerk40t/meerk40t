"""
Laser software for the Stock-LIHUIYU laserboard.

MeerK40t (pronounced MeerKat) is a built-from-the-ground-up MIT licensed
open-source laser cutting software. See https://github.com/meerk40t/meerk40t
for full details.
"""

import os.path
import sys

from meerk40t.kernel import Kernel

APPLICATION_NAME = "MeerK40t"
APPLICATION_VERSION = "0.8.0001"

if not getattr(sys, "frozen", False):
    # If .git directory does not exist we are running from a package like pypi
    # Otherwise we are running from source
    if os.path.isdir(sys.path[0] + "/.git"):
        APPLICATION_VERSION += " git"
    elif os.path.isdir(sys.path[0] + "/.github"):
        APPLICATION_VERSION += " src"
    else:
        APPLICATION_VERSION += " pkg"


def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        plugins = list()

        from . import kernelserver

        plugins.append(kernelserver.plugin)

        from .device import basedevice

        plugins.append(basedevice.plugin)

        from .lihuiyu import device as lhystudios_driver

        plugins.append(lhystudios_driver.plugin)

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

        from .extra import vectrace

        plugins.append(vectrace.plugin)

        from .extra import inkscape

        plugins.append(inkscape.plugin)

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

        from .gui.plugin import plugin as wxplugin
        plugins.append(wxplugin)

        return plugins
    if lifecycle == "establish":
        return False


def run():
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
    kernel = Kernel(APPLICATION_NAME, APPLICATION_VERSION, APPLICATION_NAME)
    kernel.add_plugin(plugin)
    kernel()
