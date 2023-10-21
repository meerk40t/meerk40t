import socket

from meerk40t.kernel import Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("module/UDPServer", UDPServer)


class UDPServer(Module):
    """
    UDPServer opens up a localhost data server and waits for UDP packets.

    Anything sent to the {path}/send channel is sent as a reply to the last seen UDP packet.
    Any packet the server picks up will be sent to the {path}/recv channel.
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
        self.state = "terminate"

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
            while self.state not in ("end", "terminate"):
                try:
                    message, address = self.socket.recvfrom(1024)
                except (socket.timeout, AttributeError):
                    continue
                if address is not None:
                    self.udp_address = address
                self.recv(message)
        except OSError:
            pass
