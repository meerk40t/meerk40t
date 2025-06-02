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
            "suppress",
            "u",
            type=bool,
            action="store_true",
            help=_("suppress input prompt '>>'"),
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
            command,
            channel,
            _,
            port=23,
            silent=False,
            quit=False,
            suppress=False,
            **kwargs,
        ):
            if suppress is None:
                suppress = False
            kernel.show_aio_prompt = not suppress
            root = kernel.root
            # Variable to store input
            root.__console_buffer = ""
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
            except (OSError, ValueError):
                channel(_("Server failed on port: {port}").format(port=port))
                return

            def exec_command(data: str) -> None:
                # We are in a different thread, so let's hand over stuff to the gui
                if isinstance(data, bytes):
                    try:
                        data = data.decode()
                    except UnicodeDecodeError as e:
                        return
                start = 0
                while True:
                    idx = data.find("|", start)
                    if idx < 0:
                        break
                    # Is the amount of quotation marks odd (ie non-even)?
                    # Yes: we are in the middle of a str
                    # No: we can split the command
                    quotations = data.count('"', 0, idx)
                    if quotations % 2 == 0:
                        data = data[:idx].rstrip() + "\n" + data[idx + 1 :].lstrip()
                    start = idx + 1
                root.__console_buffer += data
                while "\n" in root.__console_buffer:
                    pos = root.__console_buffer.find("\n")
                    command = root.__console_buffer[0:pos].strip("\r")
                    root.__console_buffer = root.__console_buffer[pos + 1 :]
                    if handover is None:
                        root.console(command + "\n")
                    else:
                        handover(command)

            handover = None
            for result in root.find("gui/handover"):
                # Do we have a thread handover routine?
                if result is not None:
                    handover, _path, suffix_path = result
                    break
            recv.watch(exec_command)

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

        @kernel.console_option(
            "port", "p", type=int, default=2080, help=_("port to listen on.")
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
            help=_("shutdown current webserver"),
        )
        @kernel.console_command(
            "webserver", help=_("starts a web-serverconsole_server on port 2080 (http)")
        )
        def server_web(
            command, channel, _, port=2080, silent=False, quit=False, **kwargs
        ):
            root = kernel.root
            try:
                server = root.open_as("module/WebServer", "web-server", port=port)
                if quit:
                    root.close("web-server")
                    return
                channel(
                    _(
                        "{name} {version} console server on port: {port}".format(
                            name=kernel.name, version=kernel.version, port=port
                        )
                    )
                )
                # We could show stuff on the console
                if not silent:
                    console = root.channel("console")
                    server.events_channel.watch(console)

            except (OSError, ValueError):
                channel(_("Server failed on port: {port}").format(port=port))
            return
