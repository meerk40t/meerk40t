"""
GRBL Device Plugin

Registers the required files to run the GRBL device.
"""
from meerk40t.grbl.control import GRBLControl, greet
from meerk40t.grbl.device import GRBLDevice, GRBLDriver
from meerk40t.grbl.emulator import GRBLEmulator
from meerk40t.grbl.gcodejob import GcodeJob
from meerk40t.grbl.interpreter import GRBLInterpreter
from meerk40t.grbl.loader import GCodeLoader


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    elif lifecycle == "invalidate":
        try:
            import serial  # pylint: disable=unused-import
            from serial import SerialException  # pylint: disable=unused-import
        except ImportError:
            print("GRBL plugin could not load because pyserial is not installed.")
            return True
    elif lifecycle == "register":
        _ = kernel.translation

        kernel.register("provider/device/grbl", GRBLDevice)
        kernel.register("provider/friendly/grbl", ("GRBL-Diode-Laser", 2))
        kernel.register(
            "dev_info/grbl-generic",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Generic (GRBL-Controller)"),
                "extended_info": _("Generic GRBL Laser Device."),
                "priority": 17,
                "family": _("Generic Diode-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Grbl",
                    },
                    {
                        "attr": "source",
                        "default": "generic",
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-fluidnc",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("GRBL-FluidNC (FluidNC-Controller)"),
                "extended_info": _(
                    "Any of a variety of ESP32 based FluidNC drivers that implement GRBL as a protocol"
                ),
                "priority": 20,
                "family": _("Generic"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "FluidNC",
                    },
                    {
                        "attr": "source",
                        "default": "generic",
                    },
                    {
                        "attr": "flavor",
                        "default": "fluidnc",
                    },
                    {
                        "attr": "require_validator",
                        "default": False,
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-k40",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("K40 CO2 (GRBL-Controller)"),
                "extended_info": _("K40 laser with a modified GRBL laser controller."),
                "priority": 18,
                "family": _("K-Series CO2-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "GRBL-K40-CO2",
                    },
                    {
                        "attr": "has_endstops",
                        "default": True,
                    },
                    {
                        "attr": "bedwidth",
                        "default": "235mm",
                    },
                    {
                        "attr": "bedheight",
                        "default": "235mm",
                    },
                    {
                        "attr": "source",
                        "default": "co2",
                    },
                    {
                        "attr": "require_validator",
                        "default": True,
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-diode",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Diode-Laser (GRBL-Controller)"),
                "extended_info": _(
                    "Any of a variety of inexpensive GRBL based diode lasers."
                ),
                "priority": 19,
                "family": _("Generic"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Grbl-Diode",
                    },
                    {
                        "attr": "has_endstops",
                        "default": False,
                    },
                    {
                        "attr": "source",
                        "default": "diode",
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-ortur",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Ortur Laser Master 2 (GRBL)"),
                "extended_info": _("Ortur-branded self-assembled grbl diode lasers"),
                "priority": 21,
                "family": _("Ortur Diode-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Ortur-LM2",
                    },
                    {
                        "attr": "has_endstops",
                        "default": True,
                    },
                    {
                        "attr": "source",
                        "default": "diode",
                    },
                    {
                        "attr": "require_validator",
                        "default": False,
                    },
                    {"attr": "bedheight", "default": "430mm"},
                    {"attr": "bedwidth", "default": "400mm"},
                ],
            },
        )
        kernel.register(
            "dev_info/grbl-longer-ray5",
            {
                "provider": "provider/device/grbl",
                "friendly_name": _("Longer Ray5 (GRBL)"),
                "extended_info": _("Longer-branded 5w/10w/20w grbl diode laser.\nMake sure you verify your bed size! This machine has several upgrade kits."),
                "priority": 21,
                "family": _("Longer Diode-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Longer-Ray5",
                    },
                    {
                        "attr": "has_endstops",
                        "default": False,
                    },
                    {
                        "attr": "source",
                        "default": "diode",
                    },
                    {
                        "attr": "require_validator",
                        "default": False,
                    },
                    {"attr": "bedheight", "default": "450mm"},
                    {"attr": "bedwidth", "default": "450mm"},
                ],
            },
        )
        kernel.register("driver/grbl", GRBLDriver)
        kernel.register("spoolerjob/grbl", GcodeJob)
        kernel.register("interpreter/grbl", GRBLInterpreter)
        kernel.register("emulator/grbl", GRBLEmulator)
        kernel.register("load/GCodeLoader", GCodeLoader)

        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_option(
            "verbose",
            "v",
            type=bool,
            action="store_true",
            help=_("watch server channels"),
        )
        @kernel.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current grblserver"),
        )
        @kernel.console_command(
            "grblcontrol",
            help=_("activate the grblserver."),
            hidden=True,
        )
        def grblserver(
            port=23,
            verbose=False,
            quit=False,
            **kwargs,
        ):
            """
            The grblserver emulation methods provide a simulation of a grbl device.
            this emulates a grbl devices in order to be compatible with software that
            controls that type of device.
            """
            root = kernel.root
            grblcontrol = root.device.lookup("grblcontrol")
            if grblcontrol is None:
                if quit:
                    return
                grblcontrol = GRBLControl(root)
                root.device.register("grblcontrol", grblcontrol)
                grblcontrol.start(port, verbose)
            if quit:
                grblcontrol.quit()
                root.device.unregister("grblcontrol")

        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_command(
            "grblmock", help=_("starts a grblmock server on port 23 (telnet)")
        )
        def server_console(command, channel, _, port=23, **kwargs):
            root = kernel.root

            try:
                root.open_as("module/TCPServer", "grblmock", port=port)
                tcp_recv_channel = root.channel("grblmock/recv", pure=True)
                tcp_send_channel = root.channel("grblmock/send", pure=True)
                tcp_send_channel.greet = greet

                def everything_ok(line):
                    for c in line:
                        if c == ord("\n") or c == ord("\r"):
                            tcp_send_channel("ok\r\n")
                        if c == ord("?"):
                            x = 0
                            y = 0
                            z = 0
                            f = 0
                            s = 0
                            status = (
                                f"<Idle|MPos:{x:.3f},{y:.3f},{z:.3f}|FS:{f},{s}>\r\n"
                            )
                            tcp_send_channel(status)

                tcp_send_channel.watch(print)
                tcp_recv_channel.watch(print)
                tcp_recv_channel.watch(everything_ok)
            except (OSError, ValueError):
                channel(_("Server failed on port: {port}").format(port=port))
            return

    elif lifecycle == "preboot":
        prefix = "grbl"
        for d in kernel.section_startswith(prefix):
            kernel.root(f"service device start -p {d} {prefix}\n")
