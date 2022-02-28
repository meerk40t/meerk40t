from meerk40t.camera.gui.camerapanel import CameraInterface, register_panel_camera

try:
    import wx
except ImportError as e:
    from meerk40t.core.exceptions import Mk40tImportAbort

    raise Mk40tImportAbort("wxpython")


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        t = list(kernel.lookup_all("camera-enabled"))
        if not t:
            return
        kernel.register("window/CameraInterface", CameraInterface)
        kernel.register("wxpane/CameraPane", register_panel_camera)
