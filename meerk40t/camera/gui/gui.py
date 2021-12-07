from meerk40t.camera.gui.camerapanel import CameraInterface, register_panel

try:
    import wx
except ImportError as e:
    from meerk40t.core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")


def plugin(kernel, lifecycle):
    # if lifecycle == "service":
    #     return "provider/camera/mk"
    if lifecycle == "register":
        kernel.register("window/CameraInterface", CameraInterface)
        kernel.register("wxpane/CameraPane", register_panel)
