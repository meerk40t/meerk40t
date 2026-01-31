from sefrocut.kernel import Kernel


def bootstrap(profile="MeerK40t_TEST", ignore_settings=True, plugins=None):
    kernel = Kernel(
        "MeerK40t",
        "0.0.0-testing",
        profile,
        ansi=False,
        ignore_settings=ignore_settings,
    )

    from sefrocut.network import kernelserver

    kernel.add_plugin(kernelserver.plugin)

    from sefrocut.device import dummydevice

    kernel.add_plugin(dummydevice.plugin)

    from sefrocut.core import core

    kernel.add_plugin(core.plugin)

    from sefrocut.image import imagetools

    kernel.add_plugin(imagetools.plugin)

    from sefrocut.fill import fills

    kernel.add_plugin(fills.plugin)

    from sefrocut.extra.coolant import plugin as coolantplugin

    kernel.add_plugin(coolantplugin)

    from sefrocut.lihuiyu import plugin as lhystudiosdevice

    kernel.add_plugin(lhystudiosdevice.plugin)

    from sefrocut.moshi import plugin as moshidevice

    kernel.add_plugin(moshidevice.plugin)

    from sefrocut.grbl import plugin as grbldevice

    kernel.add_plugin(grbldevice.plugin)

    from sefrocut.ruida import plugin as ruidadevice

    kernel.add_plugin(ruidadevice.plugin)

    from sefrocut.newly import plugin as newlydevice

    kernel.add_plugin(newlydevice.plugin)

    from sefrocut.balormk import plugin as balormkdevice

    kernel.add_plugin(balormkdevice.plugin)

    from sefrocut.core import svg_io

    kernel.add_plugin(svg_io.plugin)

    from sefrocut.dxf.plugin import plugin as dxf_io_plugin

    kernel.add_plugin(dxf_io_plugin)

    from sefrocut.rotary import rotary

    kernel.add_plugin(rotary.plugin)

    if plugins:
        for plugin in plugins:
            kernel.add_plugin(plugin)

    kernel(partial=True)
    kernel.console("channel print console\n")
    kernel.console("service device start dummy 0\n")
    return kernel


def destroy(kernel):
    for i in range(50):
        kernel.console(f"service device destroy {i}\n")
