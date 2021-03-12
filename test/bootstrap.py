
from meerk40t.kernel import Kernel


def bootstrap():
    kernel = Kernel("MeerK40t", "0.0.0-testing", "MeerK40t", "")
    try:
        from meerk40t import kernelserver

        kernel.add_plugin(kernelserver.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.device import basedevice

        kernel.add_plugin(basedevice.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.core import elements

        kernel.add_plugin(elements.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.core import bindalias

        kernel.add_plugin(bindalias.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.core import webhelp

        kernel.add_plugin(webhelp.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.core import cutplanner

        kernel.add_plugin(cutplanner.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.image import imagetools

        kernel.add_plugin(imagetools.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.device.lhystudios import lhystudiosdevice

        kernel.add_plugin(lhystudiosdevice.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.device.moshi import moshidevice

        kernel.add_plugin(moshidevice.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.device.grbl import grbldevice

        kernel.add_plugin(grbldevice.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.device.ruida import ruidadevice

        kernel.add_plugin(ruidadevice.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.core import svg_io

        kernel.add_plugin(svg_io.plugin)
    except ImportError:
        pass

    try:
        from meerk40t.dxf import dxf_io

        kernel.add_plugin(dxf_io.plugin)
    except ImportError:
        # This module cannot be loaded. ezdxf missing.
        pass
    kernel_root = kernel.get_context("/")
    kernel.bootstrap("register")
    kernel.bootstrap("configure")
    kernel.boot()
    kernel.bootstrap("ready")
    kernel.bootstrap("mainloop")
    return kernel