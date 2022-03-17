def plugin(kernel, lifecycle):
    if lifecycle == "invalidate":
        if not kernel.has_feature("camera", "wx"):
            return True
    if lifecycle == "register":
        from meerk40t.camera.gui.camerapanel import (
            CameraInterface,
            register_panel_camera,
        )

        kernel.register("window/CameraInterface", CameraInterface)
        kernel.register("wxpane/CameraPane", register_panel_camera)
