def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    elif lifecycle == "invalidate":
        try:
            import serial
            from serial import SerialException
        except ImportError:
            print("GRBL plugin could not load because pyserial is not installed.")
            return True
    elif lifecycle == "register":
        from .device import GCodeLoader, GRBLDevice, GRBLDriver

        kernel.register("provider/device/grbl", GRBLDevice)

        _ = kernel.translation
        kernel.register("driver/grbl", GRBLDriver)
        kernel.register("load/GCodeLoader", GCodeLoader)

        @kernel.console_option(
            "grbl", type=int, help=_("run grbl-emulator on given port.")
        )
        @kernel.console_option(
            "flip_x", "X", type=bool, action="store_true", help=_("grbl x-flip")
        )
        @kernel.console_option(
            "flip_y", "Y", type=bool, action="store_true", help=_("grbl y-flip")
        )
        @kernel.console_option(
            "adjust_x", "x", type=int, help=_("adjust grbl home_x position")
        )
        @kernel.console_option(
            "adjust_y", "y", type=int, help=_("adjust grbl home_y position")
        )
        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_option(
            "silent",
            "s",
            type=bool,
            action="store_true",
            help=_("do not watch server channels"),
        )
        @kernel.console_option(
            "watch", "w", type=bool, action="store_true", help=_("watch send/recv data")
        )
        @kernel.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current grblserver"),
        )
        @kernel.console_command("grblserver", help=_("activate the grblserver."))
        def grblserver(
            command,
            channel,
            _,
            port=23,
            path=None,
            flip_x=False,
            flip_y=False,
            adjust_x=0,
            adjust_y=0,
            silent=False,
            watch=False,
            quit=False,
            **kwargs,
        ):
            ctx = kernel.get_context(path if path is not None else "/")
            if ctx is None:
                return
            _ = kernel.translation
            try:
                server = ctx.open_as("module/TCPServer", "grbl", port=port)
                emulator = ctx.open("emulator/grbl")
                if quit:
                    ctx.close("grbl")
                    ctx.close("emulator/grbl")
                    return
                ctx.channel("grbl/send").greet = "Grbl 1.1e ['$' for help]\r"
                channel(_("GRBL Mode."))
                if not silent:
                    console = kernel.channel("console")
                    ctx.channel("grbl").watch(console)
                    server.events_channel.watch(console)
                    if watch:
                        server.events_channel.watch(console)

                emulator.flip_x = flip_x
                emulator.flip_y = flip_y
                emulator.home_adjust = (adjust_x, adjust_y)

                ctx.channel("grbl/recv").watch(emulator.write)
                emulator.recv = ctx.channel("grbl/send")
                channel(_("TCP Server for GRBL Emulator on port: %d" % port))
            except OSError:
                channel(_("Server failed on port: %d") % port)
            return

    elif lifecycle == "preboot":
        suffix = "grbl"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
