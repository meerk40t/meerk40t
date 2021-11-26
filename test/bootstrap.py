from meerk40t.kernel import Kernel


def bootstrap():
    kernel = Kernel("MeerK40t", "0.0.0-testing", "MeerK40t", "")

    from meerk40t import kernelserver

    kernel.add_plugin(kernelserver.plugin)

    from meerk40t.device import dummydevice

    kernel.add_plugin(dummydevice.plugin)

    from meerk40t.core import elements

    kernel.add_plugin(elements.plugin)

    from meerk40t.core import bindalias

    kernel.add_plugin(bindalias.plugin)

    from meerk40t.core import webhelp

    kernel.add_plugin(webhelp.plugin)

    from meerk40t.core import planner

    kernel.add_plugin(planner.plugin)

    from meerk40t.image import imagetools

    kernel.add_plugin(imagetools.plugin)

    from meerk40t.device.ch341 import ch341

    kernel.add_plugin(ch341.plugin)

    from meerk40t.lihuiyu import device as lhystudiosdevice

    kernel.add_plugin(lhystudiosdevice.plugin)

    from meerk40t.moshi import device as moshidevice

    kernel.add_plugin(moshidevice.plugin)

    from meerk40t.grbl import device as grbldevice

    kernel.add_plugin(grbldevice.plugin)

    from meerk40t.ruida import device as ruidadevice

    kernel.add_plugin(ruidadevice.plugin)

    from meerk40t.core import svg_io

    kernel.add_plugin(svg_io.plugin)

    try:
        from meerk40t.dxf import dxf_io

        kernel.add_plugin(dxf_io.plugin)
    except ImportError:
        # This module cannot be loaded. ezdxf missing.
        pass
    kernel()
    kernel.console("channel print console\n")
    kernel.console("service device start dummy 0\n")
    return kernel
