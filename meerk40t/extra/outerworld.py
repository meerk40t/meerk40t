"""
This module exposes a couple of simple commands to send some simple commands to the outer world
"""
import urllib
import os.path

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


    @kernel.console_argument("filename", type=str, help=_("Filename/url to load"))
    @kernel.console_argument("x", type=str, help="Sets the x-position of the data ('c' to center)",)
    @kernel.console_argument("y", type=str, help="Sets the y-position of the data ('c' to center)",)
    @kernel.console_argument("width", type=Length, help="Sets the width of the loaded data",)
    @kernel.console_argument("height", type=Length, help="Sets the height of the loaded data",)
    @kernel.console_option("relative", "r", type=str, help="Establishes the id of an element that will act as the reference, if none given then reference is the scene")
    @kernel.console_command(
        "xload",
        help=_("xload <filename> <x> <y> <width> <height>")
        + "\n"
        + _("Gets a file and puts it on the screen"),
        input_type=None,
        output_type=None,
    )
    def get_xfile(
        command,
        channel,
        _,
        filename=None,
        x=None,
        y=None,
        width=None,
        height=None,
        relative=None,
        data=None,
        post=None,
        **kwargs,
    ):
        if filename is None:
            channel(_("You need to provide a file to load"))
            return
        is_a_url = False
        protocols = ("http://", "https://", "ftp://", "file://")
        for prot in protocols:
            if filename.lower().startswith(prot):
                is_a_url = True
        if is_a_url:
            # Download the file data
            url = filename
            filename = None
            try:
                with urllib.request.urlopen(url) as response:
                    # Try to get the original filename
                    info = response.info()
                    candidate = None
                    if 'Content-Disposition' in info:
                        content_disposition = info['Content-Disposition']
                        if 'filename=' in content_disposition:
                            candidate = content_disposition.split('filename=')[1].strip('"')
                    if candidate is None:
                        # lets split the name
                        parts = url.split("/")
                        if len(parts) > 0:
                            candidate = parts[-1]
                            for invalid in (":", "/", "\\"):
                                candidate = candidate.replace(invalid, "_")
                        else:
                            candidate = "_webload.svg"
                    file_data = response.read()

                    safe_dir = kernel.os_information["WORKDIR"]
                    filename = os.path.join(safe_dir, candidate)
                    channel(f"Writing result to {filename}")
                    with open(filename, "wb") as f:
                        f.write(file_data)
            except Exception as e:
                channel (f"Failed to get {url}: {e}")
                return
        if filename is None:
            channel("Could not load any data")
            return

        # Download the file data
        elements_service = kernel.elements
        units = kernel.root.units_name
        org_x = 0
        org_y = 0
        size_x = kernel.device.view.width
        size_y = kernel.device.view.height
        if relative is not None:
            relative = str(relative).lower()
            # Let's try to find an element with that id
            for e in elements_service.elems():
                if e.id is None:
                    continue
                if str(e.id).lower() == relative:
                    try:
                        bb = e.bounds
                    except AttributeError:
                        continue
                    if bb is None:
                        continue
                    org_x = bb[0]
                    org_y = bb[1]
                    size_x = bb[2] - bb[0]
                    size_y = bb[3] - bb[1]
                    channel (f"Reference element with id '{e.id}' found: '{e.display_label()}'")
                    break
        if org_x != 0 or org_y != 0:
            channel(f"Upper left corner at: {Length(org_x, digits=2, preferred_units=units)}, {Length(org_y, digits=2, preferred_units=units)}")

        res = elements_service.load(filename, svg_ppi = elements_service.svg_ppi)
        if not res:
            channel("Could not load any data")
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

        channel(f"Loaded {len(elements_service.added_elements)} elements")

        with elements_service.undofree():
            require_updates = []
            if width is not None:
                bb = union_box(elements_service.added_elements)
                if bb is not None:
                    wd = float(width)
                    if height is None:
                        # if we don't have a height then we use the ratio
                        ratio = (bb[2] - bb[0]) / (bb[3] - bb[1])
                        ht = wd / ratio
                        channel(f"Setting height to {Length(ht, digits=2, preferred_units=units)}")
                    else:
                        ht = float(height)
                sx = wd / (bb[2] - bb[0])
                sy = ht / (bb[3] - bb[1])
                for n in elements_service.added_elements:
                    if hasattr(n, "matrix"):
                        n.matrix.post_scale(sx, sy)
                        if n.type == "elem image":
                            require_updates.append(n)

            if x is not None and y is not None:
                bb = union_box(elements_service.added_elements)
                dx = 0
                dy = 0
                if bb is not None:
                    if x.lower() == "c":
                        dx = (org_x + size_x / 2) - (bb[0] + bb[2]) / 2
                    else:
                        try:
                            px = float(Length(x))
                            dx = (org_x + px) - bb[0]
                        except ValueError:
                            pass
                    if y.lower() == "c":
                        dy = (org_y + size_y / 2) - (bb[1] + bb[3]) / 2
                    else:
                        try:
                            py = float(Length(y))
                            dy = (org_y + py) - bb[1]
                        except ValueError:
                            pass

                if dx != 0 or dy != 0:
                    for n in elements_service.added_elements:
                        if hasattr(n, "matrix"):
                            n.matrix.post_translate(dx, dy)
            for n in require_updates:
                n.update(context=None)
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
                channel(_("You need to provide a value to set (1 / 0 = or True / False)"))
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
