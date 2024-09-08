"""
This module exposes a couple of simple commands to send some simple commands to the outer world
"""

import platform

def plugin(kernel, lifecycle):
    if lifecycle != "register":
        return
    
    from meerk40t.core.units import Length, DEFAULT_PPI, UNITS_PER_PIXEL

    _ = kernel.translation
    context = kernel.root

    @kernel.console_argument("url", type=str, help=_("Web url to call"))
    @kernel.console_command(
        "call_url",
        help=_("call_url <url>")
        + "\n"
        + _("Opens a webpage or REST-Interface page"),
        input_type=None,
        output_type=None,
    )
    def call_url(
        command,
        channel,
        _,
        url=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if url is None:
            channel(_("You need to provide an url to call"))
            return
        try:
            import urllib
        except ImportError:
            channel("Could not import urllib")
            return

        try:
            with urllib.request.urlopen(url, data=None) as f:
                channel(f.read().decode('utf-8'))
        except Exception as e:
            channel (f"Failed to call {url}: {e}")
            pass

    @kernel.console_argument("url", type=str, help=_("Image url to load"))
    @kernel.console_argument("x", type=Length, help="Sets the x-position of the image",)
    @kernel.console_argument("y", type=Length, help="Sets the y-position of the image",)
    @kernel.console_argument("width", type=Length, help="Sets the width of the given image",)
    @kernel.console_argument("height", type=Length, help="Sets the width of the given image",)
    @kernel.console_command(
        "webimage",
        help=_("webimage <url> <x> <y> <width> <height")
        + "\n"
        + _("Gets an image or an svg file and puts it on the screen"),
        input_type=None,
        output_type=None,
    )
    def get_webimage(
        command,
        channel,
        _,
        url=None,
        x=None,
        y=None,
        width=None,
        height=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if url is None:
            channel(_("You need to provide an url of an image to load"))
            return
        try:
            import urllib
            import io
            from PIL import Image
            from meerk40t.svgelements import Matrix
        except ImportError:
            channel("Could not import urllib")
            return
        # Download the image data
        try:
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
    
            # Open the image using PIL
            image = Image.open(io.BytesIO(image_data))        
        except Exception as e:
            channel (f"Failed to get {url}: {e}")
            return

        elements_service = kernel.elements
        # Now create the image object
        try:
            from PIL import ImageOps

            image = ImageOps.exif_transpose(image)
        except ImportError:
            pass
        _dpi = DEFAULT_PPI
        matrix = Matrix(f"scale({UNITS_PER_PIXEL})")
        try:
            context.setting(bool, "image_dpi", True)
            if context.image_dpi:
                try:
                    dpi = image.info["dpi"]
                except KeyError:
                    dpi = None
                if (
                    isinstance(dpi, tuple)
                    and len(dpi) >= 2
                    and dpi[0] != 0
                    and dpi[1] != 0
                ):
                    matrix.post_scale(
                        DEFAULT_PPI / float(dpi[0]), DEFAULT_PPI / float(dpi[1])
                    )
                    _dpi = round((float(dpi[0]) + float(dpi[1])) / 2, 0)
        except (KeyError, IndexError):
            pass

        element_branch = elements_service.get(type="branch elems")
        n = element_branch.add(
            image=image,
            matrix=matrix,
            # type="image raster",
            type="elem image",
            dpi=_dpi,
        )

        if width is not None:
            bb = n.bbox()
            wd = float(width)
            if height is None:
                # if we don't have a height then we use the image ratio
                ratio = (bb[2] - bb[0]) / (bb[3] - bb[1])
                ht = wd / ratio
            else:
                ht = float(height)
            sx = wd / (bb[2] - bb[0])
            sy = ht / (bb[3] - bb[1])
            n.matrix.post_scale(sx, sy)
        else:
            context.setting(bool, "scale_oversized_images", True)
            if context.scale_oversized_images:
                bb = n.bbox()
                sx = (bb[2] - bb[0]) / context.device.space.width
                sy = (bb[3] - bb[1]) / context.device.space.height
                if sx > 1 or sy > 1:
                    sx = max(sx, sy)
                    n.matrix.post_scale(1 / sx, 1 / sx)

        if x is not None and y is not None:
            bb = n.bbox()
            px = float(x)
            py = float(y)
            dx = px - bb[0]
            dy = py - bb[1]
            n.matrix.post_translate(dx, dy)
        else:
            context.setting(bool, "center_image_on_load", True)
            if context.center_image_on_load:
                bb = n.bbox()
                dx = (context.device.space.width - (bb[2] - bb[0])) / 2
                dy = (context.device.space.height - (bb[3] - bb[1])) / 2

                n.matrix.post_translate(dx, dy)

        post.append(elements_service.post_classify([n]))

        context.signal("refresh_scene", "Scene")


    os_system = platform.system()
    os_machine = platform.machine()
    # 1 = Windows, 2 = Linux, 3 = MacOSX, 4 = RPI
    default_system = 1
    if os_system == "Windows":
        default_system = 1
    elif os_system == "Linux":
        if os_machine in ("armv7l", "aarch64"):
            # Arm processor of a rpi
            default_system = 4
        else:
            default_system = 2
    elif os_system == "Darwin":
        default_system = 3
    if default_system == 4:
        @kernel.console_argument("port", type=int, help=_("Port to use"))
        @kernel.console_argument("value", type=int, help=_("Value to set (0/1)"))
        @kernel.console_command(
            "gpio_set",
            help=_("gpio_set <port> <value>")
            + "\n"
            + _("Sets a GPIO port on the RPI to a given value"),
            input_type=None,
            output_type=None,
        )
        def gpio_set(
            command,
            channel,
            _,
            port=None,
            value=None,
            post=None,
            **kwargs,
        ):
            if port is None:
                channel(_("You need to provide a port between 1 and 16"))
                return
            if value is None:
                channel(_("You need to provide a value to set (1 / = or True / False"))
                return
            if value:
                port_value = gpio.HIGH
            else:
                port_value = gpio.LOW
            try:
                import RPi.GPIO as gpio
            except ImportError:
                channel("Could not raspberry gpio library")
                return

            try:
                gpio.setmode(gpio.BCM)
                gpio.setup(port, gpio.OUT)
                gpio.output(port, port_value)
            except Exception as e:
                channel (f"Failed to set port {port} to {value}: {e}")
                pass
