import socket

from .kernel import STATE_TERMINATE, Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("module/TCPServer", TCPServer)
        kernel.register("module/UDPServer", UDPServer)


class UDPServer(Module):
    """
    UDPServer opens up a localhost data server and waits for UDP packets.

    Anything sent to the path/send channel is sent as a reply to the last seen UDP packet.
    Any packet the server picks up will be sent to the path/recv channel.
    """

    def __init__(self, context, path, port=23):
        """
        Laser Server init.

        :param context: Context at which this module is attached.
        :param path: Path of this module.
        :param port: UDP listen port.
        """
        Module.__init__(self, context, path)
        self.server_channel = self.context.channel("server")
        self.port = port

        self.udp_address = None
        self.context.channel("%s/send" % path).watch(self.send)
        self.recv = self.context.channel("%s/recv" % path)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.bind(("", self.port))
        self.context.threaded(self.run_udp_listener, thread_name=path)

    def finalize(self, *args, **kwargs):
        self.context.channel("%s/send" % self.name).unwatch(
            self.send
        )  # We stop watching the send channel
        self.server_channel("Shutting down server.")
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def send(self, message):
        if self.udp_address is None:
            self.server_channel(
                "No UDP packet can be sent as reply to a host that has never made contact."
            )
            return
        self.socket.sendto(message, self.udp_address)

    def run_udp_listener(self):
        try:
            self.server_channel("UDP Socket(%d) Listening." % self.port)
            while True:
                try:
                    message, self.udp_address = self.socket.recvfrom(1024)
                except socket.timeout:
                    if self.state == STATE_TERMINATE:
                        return
                    continue
                self.recv(message)
        except OSError:
            pass


class TCPServer(Module):
    """
    TCPServer opens up a localhost server and waits. Any connection is given its own handler.
    """

    def __init__(self, context, path, port=23):
        """
        Laser Server init.

        :param context: Context at which this module is attached.
        :param path: Path of this module.
        :param port: Port being used for the server.
        """
        Module.__init__(self, context, path)
        self.port = port

        self.server_channel = None
        self.socket = None
        self.server_channel = self.context.channel("server")
        self.context.threaded(self.run_tcp_delegater)

    def finalize(self, *args, **kwargs):
        self.server_channel("Shutting down server.")
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def run_tcp_delegater(self):
        """
        TCP Run is a connection thread delegate. Any connections are given a different threaded
        handle to interact with that connection. This thread here waits for sockets and delegates.
        """
        self.socket = socket.socket()
        self.socket.settimeout(2)
        try:
            self.socket.bind(("", self.port))
            self.socket.listen(5)
        except OSError:
            self.server_channel("Could not start listening.")
            return

        while self.state != STATE_TERMINATE:
            self.server_channel("Listening %s on port %d..." % (self.name, self.port))
            connection = None
            addr = None
            try:
                connection, addr = self.socket.accept()
                self.server_channel("Socket Connected: %s" % str(addr))
                self.context.threaded(self.connection_handler(connection, addr))
            except socket.timeout:
                pass
            except OSError:
                self.server_channel("Socket was killed: %s" % str(addr))
                if connection is not None:
                    connection.close()
                break
        if self.socket is not None:
            self.socket.close()

    def connection_handler(self, connection, addr):
        """
        The TCP Connection Handle, handles all connections delegated by the tcp_run() method.
        The threaded context is entirely local and independent.
        """

        def handle():
            def send(e):
                if connection is not None:
                    try:
                        connection.send(bytes(e, "utf-8"))
                        self.server_channel("<-- %s" % str(e))
                    except ConnectionAbortedError:
                        connection.close()

            recv = self.context.channel("%s/recv" % self.name)
            self.context.channel("%s/send" % self.name).watch(send)
            while self.state != STATE_TERMINATE:
                try:
                    data_from_socket = connection.recv(1024)
                    if len(data_from_socket) != 0:
                        self.server_channel("--> %s" % str(data_from_socket))
                    recv(data_from_socket)
                except socket.timeout:
                    self.server_channel("Connection to %s timed out." % str(addr))
                    break
                except socket.error:
                    if connection is not None:
                        connection.close()
                    break
            self.context.channel("%s/send" % self.name).unwatch(send)

        return handle
