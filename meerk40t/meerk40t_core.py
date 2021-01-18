
def meerk40t_core(kernel, force=False):
    import sys
    if getattr(sys, 'frozen', False) or force:
        from . import kernelserver
        kernelserver.plugin(kernel)

        from . import basedevice
        basedevice.plugin(kernel)

        from . import elements
        elements.plugin(kernel)

        from . import bindalias
        bindalias.plugin(kernel)

        from . import cutplanner
        cutplanner.plugin(kernel)

        from . import imagetools
        imagetools.plugin(kernel)

        from . import defaultmodules
        defaultmodules.plugin(kernel)

        from . import lhystudiosdevice
        lhystudiosdevice.plugin(kernel)

        from . import moshiboarddevice
        moshiboarddevice.plugin(kernel)

        from . import grbldevice
        grbldevice.plugin(kernel)

        from . import ruidadevice
        ruidadevice.plugin(kernel)

        # try:
        #     from . import camera
        #     camera.plugin(kernel)
        # except ImportError:
        #     # OpenCV or Numpy not found. This module cannot be loaded.
        #     print("Module 'Camera' Not Loaded.")
        #     pass

    else:
        import pkg_resources
        found = False
        for entry_point in pkg_resources.iter_entry_points("meerk40t.plugins"):
            plugin = entry_point.load()
            plugin(kernel)
            found = True
        if not found:
            meerk40t_core(kernel, True)

