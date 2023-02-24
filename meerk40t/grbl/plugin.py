"""
GRBL Device Plugin

Registers the required files to run the GRBL device.
"""
from meerk40t.grbl.control import GRBLControl
from meerk40t.grbl.device import GRBLDevice, GRBLDriver
from meerk40t.grbl.interpreter import GRBLInterpreter
from meerk40t.grbl.emulator import GRBLEmulator
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
        kernel.register("driver/grbl", GRBLDriver)
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

    elif lifecycle == "preboot":
        suffix = "grbl"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
