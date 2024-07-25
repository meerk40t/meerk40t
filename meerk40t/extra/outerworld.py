"""
This module exposes a couple of simple commands to send some simple commands to the outer world
"""

import platform

def plugin(kernel, lifecycle):
    if lifecycle != "register":
        return

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
        @kernel.console_argument("url", type=str, help=_("Web url to call"))
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
