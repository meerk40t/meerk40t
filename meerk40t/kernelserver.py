import socket

from .kernel import STATE_TERMINATE, Module


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
                send.greet = _("%s %s Telnet Console.\r\n") % (
                    kernel.name,
                    kernel.version,
                )
                send.line_end = "\r\n"

                recv = root.channel("console-server/recv")
                recv.watch(root.console)
                channel(
                    _(
                        "%s %s console server on port: %d"
                        % (kernel.name, kernel.version, port)
                    )
                )

                if not silent:
                    console = root.channel("console")
                    console.watch(send)
                    server.events_channel.watch(console)

            except (OSError, ValueError):
                channel(_("Server failed on port: %d") % port)
            return


class UDPServer(Module):
    """
    UDPServer opens up a localhost data server and waits for UDP packets.

    Anything sent to the path/send channel is sent as a reply to the last seen UDP packet.
    Any packet the server picks up will be sent to the path/recv channel.
    """

    def __init__(self, context, name, port=23):
        """
        Laser Server init.

        :param context: Context at which this module is attached.
        :param name: Name of this module.
        :param port: UDP listen port.
        """
        Module.__init__(self, context, name)
        self.port = port
        self.events_channel = self.context.channel("server-udp-%d" % port)

        self.udp_address = None
        self.context.channel("%s/send" % name).watch(self.send)
        self.recv = self.context.channel("%s/recv" % name)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.bind(("", self.port))
        self.context.threaded(self.run_udp_listener, thread_name=name)

    def finalize(self, *args, **kwargs):
        _ = self.context._
        self.context.channel("%s/send" % self.name).unwatch(
            self.send
        )  # We stop watching the send channel
        self.events_channel(_("Shutting down server."))
        if self.socket is not None:
            self.socket.close()
            self.socket = None

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
            self.events_channel(_("UDP Socket(%d) Listening.") % self.port)
            while True:
                try:
                    message, address = self.socket.recvfrom(1024)
                except socket.timeout:
                    if self.state == STATE_TERMINATE:
                        return
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

        :param context: Context at which this module is attached.
        :param name: Name of this module
        :param port: Port being used for the server.
        """
        Module.__init__(self, context, name)
        self.port = port

        self.socket = None
        self.events_channel = self.context.channel("server-tcp-%d" % port)
        self.data_channel = self.context.channel("data-tcp-%d" % port)
        self.context.threaded(
            self.run_tcp_delegater, thread_name="tcp-%d" % port, daemon=True
        )

    def stop(self):
        self.state = STATE_TERMINATE

    def finalize(self, *args, **kwargs):
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
                _("Listening %s on port %d...") % (self.name, self.port)
            )
            connection = None
            addr = None
            try:
                connection, addr = self.socket.accept()
                self.events_channel(_("Socket Connected: %s") % str(addr))
                self.context.threaded(
                    self.connection_handler(connection, addr),
                    thread_name="handler-%d-%d" % (self.port, handle),
                    daemon=True,
                )
                handle += 1
            except socket.timeout:
                pass
            except OSError:
                self.events_channel(_("Socket was killed: %s") % str(addr))
                if connection is not None:
                    connection.close()
                break
            except AttributeError:
                self.events_channel(_("Socket did not exist to accept connection."))
                break
        if self.socket is not None:
            self.socket.close()

    def connection_handler(self, connection, addr):
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
                        self.data_channel("<-- %s" % str(e))
                    except (ConnectionAbortedError, ConnectionResetError):
                        connection.close()

            recv = self.context.channel("%s/recv" % self.name)
            send_channel_name = "%s/send" % self.name
            self.context.channel(send_channel_name).watch(send)
            while self.state != STATE_TERMINATE:
                try:
                    data_from_socket = connection.recv(1024)
                    if len(data_from_socket):
                        self.data_channel("--> %s" % str(data_from_socket))
                    else:
                        break
                    recv(data_from_socket)
                except socket.timeout:
                    self.events_channel(_("Connection to %s timed out.") % str(addr))
                    break
                except socket.error:
                    if connection is not None:
                        connection.close()
                    break
            self.context.channel(send_channel_name).unwatch(send)
            self.events_channel(_("Connection to %s was closed.") % str(addr))

        return handle
