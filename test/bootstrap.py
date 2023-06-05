from meerk40t.kernel import Kernel


def bootstrap():
    kernel = Kernel("MeerK40t", "0.0.0-testing", "MeerK40t_TEST", ansi=False)

    from meerk40t.network import kernelserver

    kernel.add_plugin(kernelserver.plugin)

    from meerk40t.device import dummydevice

    kernel.add_plugin(dummydevice.plugin)

    from meerk40t.core import core

    kernel.add_plugin(core.plugin)

    from meerk40t.image import imagetools

    kernel.add_plugin(imagetools.plugin)

    from meerk40t.fill import fills

    kernel.add_plugin(fills.plugin)

    from meerk40t.lihuiyu import plugin as lhystudiosdevice

    kernel.add_plugin(lhystudiosdevice.plugin)

    from meerk40t.moshi import plugin as moshidevice

    kernel.add_plugin(moshidevice.plugin)

    from meerk40t.grbl import plugin as grbldevice

    kernel.add_plugin(grbldevice.plugin)

    from meerk40t.ruida import plugin as ruidadevice

    kernel.add_plugin(ruidadevice.plugin)

    from meerk40t.core import svg_io

    kernel.add_plugin(svg_io.plugin)

    from meerk40t.dxf.plugin import plugin as dxf_io_plugin

    kernel.add_plugin(dxf_io_plugin)

    kernel()
    kernel.console("channel print console\n")
    kernel.console("service device start dummy 0\n")
    return kernel


def destroy(kernel):
    for i in range(50):
        kernel.console(f"service device destroy {i}\n")
