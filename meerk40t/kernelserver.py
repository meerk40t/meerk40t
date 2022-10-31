import socket

from meerk40t.kernel import STATE_END, STATE_TERMINATE, Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("module/TCPServer", TCPServer)
        kernel.register("module/UDPServer", UDPServer)

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


class UDPServer(Module):
    """
    UDPServer opens up a localhost data server and waits for UDP packets.

    Anything sent to the path/send channel is sent as a reply to the last seen UDP packet.
    Any packet the server picks up will be sent to the path/recv channel.
    """

    def __init__(self, context, name, port=23, udp_address=None):
        """
        Laser Server init.

        @param context: Context at which this module is attached.
        @param name: Name of this module.
        @param port: UDP listen port.
        """
        Module.__init__(self, context, name)
        self.port = port
        self.events_channel = self.context.channel(f"server-udp-{port}")

        self.udp_address = udp_address
        self.context.channel(f"{name}/send").watch(self.send)
        self.recv = self.context.channel(f"{name}/recv")

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.bind(("", self.port))
        self.context.threaded(self.run_udp_listener, thread_name=name, daemon=True)

    def module_close(self, *args, **kwargs):
        _ = self.context._
        self.context.channel(f"{self.name}/send").unwatch(self.send)
        # We stop watching the `send channel`
        self.events_channel(_("Shutting down server."))
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        self.state = STATE_TERMINATE

    def send(self, message):
        _ = self.context._
        if self.udp_address is None:
            self.events_channel(
                _(
                    "No UDP packet can be sent as reply to a host that has never made contact."
                )
            )
            return
        self.socket.sendto(message, self.udp_address)

    def run_udp_listener(self):
        _ = self.context._
        try:
            self.events_channel(
                _("UDP Socket({port}) Listening.").format(port=self.port)
            )
            while self.state != STATE_END and self.state != STATE_TERMINATE:
                try:
                    message, address = self.socket.recvfrom(1024)
                except (socket.timeout, AttributeError):
                    continue
                if address is not None:
                    self.udp_address = address
                self.recv(message)
        except OSError:
            pass


class TCPServer(Module):
    """
    TCPServer opens up a localhost server and waits. Any connection is given its own handler.
    """

    def __init__(self, context, name, port=23):
        """
        Laser Server init.

        @param context: Context at which this module is attached.
        @param name: Name of this module
        @param port: Port being used for the server.
        """
        Module.__init__(self, context, name)
        self.port = port

        self.socket = None
        self.events_channel = self.context.channel(f"server-tcp-{port}")
        self.data_channel = self.context.channel(f"data-tcp-{port}")
        self.context.threaded(
            self.run_tcp_delegater, thread_name=f"tcp-{port}", daemon=True
        )

    def stop(self):
        self.state = STATE_TERMINATE

    def module_close(self, *args, **kwargs):
        _ = self.context._
        self.events_channel(_("Shutting down server."))
        self.state = STATE_TERMINATE
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def run_tcp_delegater(self):
        """
        TCP Run is a connection thread delegate. Any connections are given a different threaded
        handle to interact with that connection. This thread here waits for sockets and delegates.
        """
        _ = self.context._
        self.socket = socket.socket()
        # self.socket.settimeout(0)
        try:
            self.socket.bind(("", self.port))
            self.socket.listen(1)
        except OSError:
            self.events_channel(_("Could not start listening."))
            return
        handle = 1
        while self.state != STATE_TERMINATE:
            self.events_channel(
                _("Listening {name} on port {port}...").format(
                    name=self.name, port=self.port
                )
            )
            connection = None
            address = None
            try:
                connection, address = self.socket.accept()
                self.events_channel(
                    _("Socket Connected: {address}").format(address=address)
                )
                self.context.threaded(
                    self.connection_handler(connection, address),
                    thread_name=f"handler-{self.port}-{handle}",
                    daemon=True,
                )
                handle += 1
            except socket.timeout:
                pass
            except OSError:
                self.events_channel(
                    _("Socket was killed: {address}").format(address=address)
                )
                if connection is not None:
                    connection.close()
                break
            except AttributeError:
                self.events_channel(_("Socket did not exist to accept connection."))
                break
        if self.socket is not None:
            self.socket.close()

    def connection_handler(self, connection, address):
        """
        The TCP Connection Handle, handles all connections delegated by the tcp_run() method.
        The threaded context is entirely local and independent.
        """
        _ = self.context._

        def handle():
            def send(e):
                if connection is not None:
                    try:
                        connection.send(bytes(e, "utf-8"))
                        self.data_channel(f"<-- {str(e)}")
                    except (ConnectionAbortedError, ConnectionResetError):
                        connection.close()

            recv = self.context.channel(f"{self.name}/recv", pure=True)
            send_channel_name = f"{self.name}/send"
            self.context.channel(send_channel_name, pure=True).watch(send)
            while self.state != STATE_TERMINATE:
                try:
                    data_from_socket = connection.recv(1024)
                    if len(data_from_socket):
                        self.data_channel(f"--> {str(data_from_socket)}")
                    else:
                        break
                    recv(data_from_socket)
                except socket.timeout:
                    self.events_channel(
                        _("Connection to {address} timed out.").format(address=address)
                    )
                    break
                except socket.error:
                    if connection is not None:
                        connection.close()
                    break
            self.context.channel(send_channel_name).unwatch(send)
            self.events_channel(
                _("Connection to {address} was closed.").format(address=address)
            )

        return handle
