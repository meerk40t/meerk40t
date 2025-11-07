"""
Internal plugins are a list of plugins which are included internally with MeerK40t, usually additional features
are written like regular plugins and obey the rules for the meerk40t/kernel plugin system. Plugins can contain
additional plugin references (this is itself a plugin).

For example,
        from .core import core

        plugins.append(core.plugin)

Provides all the core plugins for meerk40t to run which are sub-references from that plugin file.
"""


def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        plugins = list()

        from .network import kernelserver

        plugins.append(kernelserver.plugin)

        from .device import basedevice

        plugins.append(basedevice.plugin)

        from .extra.coolant import plugin as coolantplugin

        plugins.append(coolantplugin)

        from .lihuiyu import plugin as lihuiyu_driver

        plugins.append(lihuiyu_driver.plugin)

        from .moshi import plugin as moshi_driver

        plugins.append(moshi_driver.plugin)

        from .grbl.plugin import plugin as grbl_driver_plugin

        plugins.append(grbl_driver_plugin)

        from .ruida import plugin as ruida_driver

        plugins.append(ruida_driver.plugin)

        from .rotary import rotary

        plugins.append(rotary.plugin)

        from .cylinder import cylinder

        plugins.append(cylinder.plugin)

        from .core import core

        plugins.append(core.plugin)

        from .image import imagetools

        plugins.append(imagetools.plugin)

        from .fill import fills

        plugins.append(fills.plugin)

        from .fill import patterns

        plugins.append(patterns.plugin)

        from .extra import vectrace

        plugins.append(vectrace.plugin)

        from .extra import potrace

        plugins.append(potrace.plugin)

        from .extra import vtracer

        plugins.append(vtracer.plugin)

        from .extra import inkscape

        plugins.append(inkscape.plugin)

        from .extra import hershey

        plugins.append(hershey.plugin)

        from .extra import ezd

        plugins.append(ezd.plugin)

        from .extra import lbrn

        plugins.append(lbrn.plugin)

        from .extra import xcs_reader

        plugins.append(xcs_reader.plugin)

        from .extra import updater

        plugins.append(updater.plugin)

        from .extra import winsleep

        plugins.append(winsleep.plugin)

        from .extra import param_functions

        plugins.append(param_functions.plugin)

        from .extra import serial_exchange

        plugins.append(serial_exchange.plugin)

        from meerk40t.camera.plugin import plugin as camera_plugin

        plugins.append(camera_plugin)

        from .dxf.plugin import plugin as dxf_io_plugin

        plugins.append(dxf_io_plugin)

        from .extra import cag

        plugins.append(cag.plugin)

        from .balormk.plugin import plugin as balorplugin

        kernel.add_plugin(balorplugin)

        from .newly.plugin import plugin as newlyplugin

        kernel.add_plugin(newlyplugin)

        from .gui.plugin import plugin as wxplugin

        plugins.append(wxplugin)

        from .extra.imageactions import plugin as splitterplugin

        plugins.append(splitterplugin)

        from .extra.outerworld import plugin as owplugin

        plugins.append(owplugin)

        return plugins

    if lifecycle == "invalidate":
        return True
