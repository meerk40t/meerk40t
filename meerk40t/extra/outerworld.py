"""
This module exposes a couple of simple commands to send some simple commands to the outer world
"""
import urllib

from meerk40t.kernel import get_safe_path

HTTPD = None
SERVER_THREAD = None
KERN = None

def plugin(kernel, lifecycle):
    if lifecycle != "register":
        return

    import platform

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
            with urllib.request.urlopen(url, data=None) as f:
                channel(f.read().decode('utf-8'))
        except Exception as e:
            channel (f"Failed to call {url}: {e}")


    @kernel.console_argument("url", type=str, help=_("Image url to load"))
    @kernel.console_argument("x", type=Length, help="Sets the x-position of the image",)
    @kernel.console_argument("y", type=Length, help="Sets the y-position of the image",)
    @kernel.console_argument("width", type=Length, help="Sets the width of the given image",)
    @kernel.console_argument("height", type=Length, help="Sets the width of the given image",)
    @kernel.console_command(
        "webload",
        help=_("webload <url> <x> <y> <width> <height")
        + "\n"
        + _("Gets a file and puts it on the screen"),
        input_type=None,
        output_type=None,
    )
    def get_webfile(
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
            channel(_("You need to provide an url of a file to load"))
            return
        try:
            import urllib
            import os.path
            from meerk40t.svgelements import Matrix
        except ImportError:
            channel("Could not import urllib")
            return
        # Download the file data
        tempfile = None
        try:
            with urllib.request.urlopen(url) as response:
                # Try to get the original filename
                info = response.info()
                filename = None
                if 'Content-Disposition' in info:
                    content_disposition = info['Content-Disposition']
                    if 'filename=' in content_disposition:
                        filename = content_disposition.split('filename=')[1].strip('"')
                if filename is None:
                    # lets split the name
                    parts = url.split("/")
                    if len(parts) > 0:
                        filename = parts[-1]
                        for invalid in (":", "/", "\\"):
                            filename = filename.replace(invalid, "_")
                    else:
                        filename = "_webload.svg"
                file_data = response.read()

                safe_dir = os.path.realpath(get_safe_path(kernel.name))
                tempfile = os.path.join(safe_dir, filename)
                channel(f"Writing result to {tempfile}")
                with open(tempfile, "wb") as f:
                    f.write(file_data)
        except Exception as e:
            channel (f"Failed to get {url}: {e}")
            return
        if tempfile is None:
            channel("Could not load any data")
            return
        elements_service = kernel.elements
        res = elements_service.load(tempfile)
        if not res:
            return

        def union_box(elements):
            boxes = []
            for e in elements:
                if not hasattr(e, "bbox"):
                    continue
                box = e.bbox()
                if box is None:
                    continue
                boxes.append(box)
            if len(boxes) == 0:
                return None
            (xmins, ymins, xmaxs, ymaxs) = zip(*boxes)
            return min(xmins), min(ymins), max(xmaxs), max(ymaxs)

        if width is not None:
            bb = union_box(elements_service.added_elements)
            if bb is not None:
                wd = float(width)
                if height is None:
                    # if we don't have a height then we use the ratio
                    ratio = (bb[2] - bb[0]) / (bb[3] - bb[1])
                    ht = wd / ratio
                else:
                    ht = float(height)
            sx = wd / (bb[2] - bb[0])
            sy = ht / (bb[3] - bb[1])
            for n in elements_service.added_elements:
                if hasattr(n, "matrix"):
                    n.matrix.post_scale(sx, sy)

        if x is not None and y is not None:
            bb = union_box(elements_service.added_elements)
            if bb is not None:
                px = float(x)
                py = float(y)
                dx = px - bb[0]
                dy = py - bb[1]
            for n in elements_service.added_elements:
                if hasattr(n, "matrix"):
                    n.matrix.post_translate(dx, dy)
        elements_service.clear_loaded_information()

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
