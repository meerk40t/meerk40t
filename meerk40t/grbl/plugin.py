"""
GRBL Device Plugin

Registers the required files to run the GRBL device.
"""


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

        from .device import GRBLDevice, GRBLDriver

        kernel.register("provider/device/grbl", GRBLDevice)
        kernel.register("driver/grbl", GRBLDriver)

        from .interpreter import GRBLInterpreter

        kernel.register("interpreter/grbl", GRBLInterpreter)

        from .emulator import GRBLEmulator

        kernel.register("emulator/grbl", GRBLEmulator)

        from .loader import GCodeLoader

        kernel.register("load/GCodeLoader", GCodeLoader)

        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_option(
            "verbose",
            "v",
            type=bool,
            action="store_true",
            help=_("do not watch server channels"),
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
            command,
            channel,
            _,
            port=23,
            verbose=False,
            quit=False,
            **kwargs,
        ):
            root = kernel.root
            try:
                server = root.open_as("module/TCPServer", "grbl", port=port)
                from meerk40t.grbl.emulator import GRBLEmulator

                if quit:
                    try:
                        emulator = server.emulator
                        emulator.driver = None
                        del emulator
                    except AttributeError:
                        pass
                    root.close("grbl")
                    return

                def greet():
                    yield "Grbl 1.1f ['$' for help]\r"
                    yield "[MSG:’$H’|’$X’ to unlock]"

                root.channel("grbl/send", pure=True).greet = greet

                channel(_("GRBL Mode."))
                if verbose:
                    console = kernel.channel("console")
                    root.channel("grbl").watch(console)
                    server.events_channel.watch(console)

                emulator = GRBLEmulator(
                    root.device.driver, root.device.scene_to_device_matrix()
                )
                server.emulator = emulator

                # Link emulator and server.
                tcp_recv_channel = root.channel("grbl/recv", pure=True)
                tcp_recv_channel.watch(emulator.write)
                tcp_send_channel = root.channel("grbl/send", pure=True)
                emulator.reply = tcp_send_channel

                channel(
                    _("TCP Server for GRBL Emulator on port: {port}").format(port=port)
                )
            except OSError as e:
                channel(_("Server failed on port: {port}").format(port=port))
                channel(str(e.strerror))
            return

    elif lifecycle == "preboot":
        suffix = "grbl"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
