def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation

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
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current lhyserver"),
        )
        @kernel.console_command(
            "consoleserver", help=_("starts a console_server on port 23 (telnet)")
        )
        def server_console(
            command, channel, _, port=23, silent=False, quit=False, **kwargs
        ):
            root = kernel.root
            try:
                server = root.open_as("module/TCPServer", "console-server", port=port)
                if quit:
                    root.close("console-server")
                    return
                send = root.channel("console-server/send")
                send.greet = _(
                    "{kernel_name} {kernel_version} Telnet Console.\r\n"
                ).format(kernel_name=kernel.name, kernel_version=kernel.version)
                send.line_end = "\r\n"

                recv = root.channel("console-server/recv")
                recv.watch(root.console)
                channel(
                    _(
                        "{name} {version} console server on port: {port}".format(
                            name=kernel.name, version=kernel.version, port=port
                        )
                    )
                )

                if not silent:
                    console = root.channel("console")
                    console.watch(send)
                    server.events_channel.watch(console)

            except (OSError, ValueError):
                channel(_("Server failed on port: {port}").format(port=port))
            return

