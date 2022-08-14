from meerk40t.kernel import CommandSyntaxError


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "cli":
        try:
            import cv2
            import numpy as np
        except ImportError:
            return
        kernel.set_feature("camera")
    if lifecycle == "invalidate":
        try:
            import cv2
        except ImportError as e:
            print("OpenCV is not installed. Disabling Camera. Install with:")
            print("\tpip install opencv-python-headless")
            return True
        try:
            import numpy as np
        except ImportError as e:
            print("Numpy is not installed. Disabling Camera.")
            return True

    elif lifecycle == "register":

        from meerk40t.camera.camera import Camera

        kernel.register("camera-enabled", True)
        _ = kernel.translation

        @kernel.console_option("width", "w", type=int, help="force the camera width")
        @kernel.console_option("height", "h", type=int, help="force the camera height")
        @kernel.console_option(
            "contrast", "c", help="Turn on AutoContrast", type=bool, action="store_true"
        )
        @kernel.console_option(
            "nocontrast",
            "C",
            help="Turn off AutoContrast",
            type=bool,
            action="store_true",
        )
        @kernel.console_option("uri", "u", type=str)
        @kernel.console_command(
            "camera\d*",
            regex=True,
            help="camera commands and modifiers.",
            output_type="camera",
        )
        def camera(
            command,
            uri=None,
            width=None,
            height=None,
            contrast=None,
            nocontrast=None,
            **kwargs,
        ):
            if len(command) > 6:
                current_camera = command[6:]
                camera_path = f"camera/{current_camera}"
                if camera_path not in kernel.contexts:
                    kernel.add_service("camera", Camera(kernel, camera_path))
                kernel.activate_service_path("camera", camera_path)
            cam = kernel.camera
            if contrast:
                cam.autonormal = True
            if nocontrast:
                cam.autonormal = False
            if width:
                cam.width = width
            if height:
                cam.height = height
            if uri is not None:
                cam.set_uri(uri)
            return "camera", cam

        @kernel.console_option(
            "tries", "t", type=int, default=10, help="Attempts to recover connection"
        )
        @kernel.console_option(
            "frame_tries", "f", type=int, default=10, help="Attempts to fetch frame"
        )
        @kernel.console_command(
            "start", help="Start Camera.", input_type="camera", output_type="camera"
        )
        def start_camera(data=None, tries=None, frame_tries=None, **kwargs):
            if tries is not None:
                data.max_tries_connect = tries
            if frame_tries is not None:
                data.max_tries_frame = frame_tries
            data.open_camera()
            return "camera", data

        @kernel.console_command(
            "stop", help="Stop Camera", input_type="camera", output_type="camera"
        )
        def stop_camera(data=None, **kwargs):
            data.close_camera()
            return "camera", data

        @kernel.console_argument("subcommand", type=str, help="capture/reset")
        @kernel.console_command(
            "fisheye",
            help="fisheye subcommand",
            input_type="camera",
            output_type="camera",
        )
        def fisheye_camera(data=None, subcommand=None, **kwargs):
            if subcommand is None:
                raise CommandSyntaxError
            if subcommand == "capture":
                data.fisheye_capture()
            elif subcommand == "reset":
                data.reset_fisheye()
            elif subcommand == "back":
                data.backtrack_fisheye()
            return "camera", data

        @kernel.console_argument("subcommand", type=str, help="reset/set")
        @kernel.console_argument("corner", type=int)
        @kernel.console_argument("x", type=float)
        @kernel.console_argument("y", type=float)
        @kernel.console_command(
            "perspective",
            help="perspective (set <#> <value>|reset)",
            input_type="camera",
            output_type="camera",
        )
        def perspective_camera(
            _, data=None, subcommand=None, corner=None, x=None, y=None, **kwargs
        ):
            if subcommand is None:
                raise CommandSyntaxError
            if subcommand == "reset":
                data.reset_perspective()
                return "camera", data
            elif subcommand == "set":
                if y is None:
                    raise CommandSyntaxError
                data.perspective[corner] = x, y
                return "camera", camera
            else:
                raise CommandSyntaxError

        @kernel.console_command(
            "background",
            help="set background image",
            input_type="camera",
            output_type="image-array",
        )
        def background_camera(data=None, **kwargs):
            image_array = data.background()
            return "image-array", image_array

        @kernel.console_command(
            "export",
            help="export camera image",
            input_type="camera",
            output_type="image-array",
        )
        def export_camera(data=None, **kwargs):
            image_array = data.export()
            return "image-array", image_array

        @kernel.console_argument("setting", type=int)
        @kernel.console_argument("value", type=float)
        @kernel.console_command(
            "set", help="set a particular setting in the camera", input_type="camera"
        )
        def set_camera(
            command, _, channel, data=None, setting=None, value=None, **kwargs
        ):
            if value is None:
                raise CommandSyntaxError
            if data.capture is None:
                channel(_("Camera is not currently running..."))
                return
            prop = None
            for i in range(100):
                for name in dir(cv2):
                    if not name.startswith("CAP_PROP"):
                        continue
                    if getattr(cv2, name) == setting:
                        prop = name
                        break
            v0 = data.capture.get(setting)
            try:
                data.capture.set(setting, value)
            except cv2.error:
                channel(_("Attempt to change setting failed, raised cv2 error."))
                return
            v1 = data.capture.get(setting)
            channel(
                _(
                    "Attempt camera setting ({property}) to {value}. {current}->{old}"
                ).format(property=prop, value=value, current=v0, old=v1)
            )

        @kernel.console_command(
            "list", help="list camera settings", input_type="camera"
        )
        def list_camera(command, _, channel, data=None, **kwargs):
            if data.capture is None:
                channel(_("Camera is not currently running..."))
                return
            for i in range(100):
                try:
                    v = data.capture.get(i)
                    prop = None
                    for name in dir(cv2):
                        if not name.startswith("CAP_PROP"):
                            continue
                        if getattr(cv2, name) == i:
                            prop = name
                            break
                    if prop is None:
                        continue
                    channel(f"{i}: {str(prop)} -- {str(v)}")
                except:
                    pass
