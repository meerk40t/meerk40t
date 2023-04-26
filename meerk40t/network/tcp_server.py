import socket

from meerk40t.kernel import Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("module/TCPServer", TCPServer)


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
        self.state = "terminate"

    def module_close(self, *args, **kwargs):
        _ = self.context._
        self.events_channel(_("Shutting down server."))
        self.state = "terminate"
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
        while self.state != "terminate":
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
            while self.state != "terminate":
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
                except OSError:
                    if connection is not None:
                        connection.close()
                    break
            self.context.channel(send_channel_name).unwatch(send)
            self.events_channel(
                _("Connection to {address} was closed.").format(address=address)
            )

        return handle
