def bootstrap(kernel, force=False):
    import sys

    if getattr(sys, "frozen", False) or force:
        from . import kernelserver

        kernelserver.plugin(kernel)

        from .device import basedevice

        basedevice.plugin(kernel)

        from .core import elements

        elements.plugin(kernel)

        from .core import bindalias

        bindalias.plugin(kernel)

        from .core import cutplanner

        cutplanner.plugin(kernel)

        from .image import imagetools

        imagetools.plugin(kernel)

        from .core import svg_io

        svg_io.plugin(kernel)

        try:
            from .dxf import dxf_io

            dxf_io.plugin(kernel)
        except ImportError:
            # This module cannot be loaded. ezdxf missing.
            pass

        from .device.lhystudios import lhystudiosdevice

        lhystudiosdevice.plugin(kernel)

        from .device.moshi import moshiboarddevice

        moshiboarddevice.plugin(kernel)

        from .device.grbl import grbldevice

        grbldevice.plugin(kernel)

        from .device.ruida import ruidadevice

        ruidadevice.plugin(kernel)
        try:
            # This will only attempt to load the optional plugin if within an app-bundle.
            from camera import camera

            camera.plugin(kernel)
        except ImportError:
            # This module cannot be loaded.
            pass

    else:
        import pkg_resources

        found = False
        for entry_point in pkg_resources.iter_entry_points("meerk40t.plugins"):
            plugin = entry_point.load()
            plugin(kernel)
            found = True
        if not found:
            bootstrap(kernel, True)
