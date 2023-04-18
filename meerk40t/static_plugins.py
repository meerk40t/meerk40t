def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        plugins = list()

        from .network import kernelserver

        plugins.append(kernelserver.plugin)

        from .device import basedevice

        plugins.append(basedevice.plugin)

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

        from .core import core

        plugins.append(core.plugin)

        from .image import imagetools

        plugins.append(imagetools.plugin)

        from .fill import fills

        plugins.append(fills.plugin)

        from .fill import patternfill

        plugins.append(patternfill.plugin)

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

        from .extra import ezd

        plugins.append(ezd.plugin)

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

        from .newly.plugin import plugin as newlyplugin

        kernel.add_plugin(newlyplugin)

        from .gui.plugin import plugin as wxplugin

        plugins.append(wxplugin)

        from .extra.imageactions import plugin as splitterplugin

        plugins.append(splitterplugin)

        return plugins

    if lifecycle == "invalidate":
        return True
