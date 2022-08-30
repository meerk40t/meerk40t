from meerk40t.core.units import Length
from meerk40t.kernel import CommandSyntaxError


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

        @kernel.console_argument("x", type=str, help="x position")
        @kernel.console_argument("y", type=str, help="y position")
        @kernel.console_argument("width", type=str, help="width of view")
        @kernel.console_argument("height", type=str, help="height of view")
        @kernel.console_option(
            "animate",
            "a",
            type=bool,
            action="store_true",
            help="perform focus with animation",
        )
        @kernel.console_command(
            "focus", input_type="camera", all_arguments_required=True
        )
        def camera_focus(
            command, _, channel, data, x, y, width, height, animate=False, **kwgs
        ):
            try:
                gui = data.gui
            except AttributeError:
                gui = None
            if gui is None:
                channel(_("Camera window not registered, cannot move window."))
                return

            try:
                _x = Length(x, relative_length=f"{data.width}px").pixels
                _y = Length(y, relative_length=f"{data.height}px").pixels
                _width = Length(width, relative_length=f"{data.width}px").pixels
                _height = Length(height, relative_length=f"{data.height}px").pixels
            except ValueError:
                raise CommandSyntaxError("Not a valid length.")
            bbox = (_x, _y, _width, _height)
            root_widget = gui.widget_scene.widget_root
            matrix = root_widget.scene_widget.matrix
            root_widget.focus_viewport_scene(
                bbox, gui.display_camera.Size, animate=animate
            )
            gui.widget_scene.request_refresh()
            channel(str(matrix))
            return "scene", data
