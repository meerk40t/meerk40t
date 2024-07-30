"""
UDPServer opens up a localhost data server and waits for UDP packets. Utilizing pure MK channels.

Any packet the server picks up will be sent to the `{path}/recv` channel.
Data sent to the `{path}/send` channel is sent as a reply to the last seen UDP packet.

"""

import socket

from meerk40t.kernel import Module


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("module/UDPServer", UDPServer)


class UDPServer(Module):
    def __init__(self, context, name, port=23, udp_address=None):
        """
        Laser Server init.

        @param context: Context at which this module is attached.
        @param name: Name of this module.
        @param port: UDP listen port.
        """
        Module.__init__(self, context, name)

        self.udp_address = udp_address

        self.events_channel = self.context.channel(f"server-udp-{port}")
        self.send_channel = self.context.channel(f"{name}/send", pure=True)
        self.recv_channel = self.context.channel(f"{name}/recv", pure=True)

        self.listen_address = ""
        self.listen_port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.bind((self.listen_address, self.listen_port))

    def module_open(self, *args, **kwargs):
        """
        Module opened. Watch send_channel -> Send and run the upd_listener thread.
        @param args:
        @param kwargs:
        @return:
        """
        self.send_channel.watch(self.send)
        self.context.threaded(self.run_udp_listener, thread_name=self.name, daemon=True)

    def module_close(self, *args, **kwargs):
        _ = self.context._
        self.send_channel.unwatch(self.send)

        self.events_channel(_("Shutting down server."))
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        self.state = "terminate"

    def send(self, message, address=None):
        """
        Watching the {name}/send channel. This will receive any data sent along that channel. And send it to the last
        address at which data was received.

        @param message:  Message to send.
        @param address: (address,port) override if not simply replying.
        @return:
        """
        _ = self.context._
        if self.udp_address is None:
            self.events_channel(
                _(
                    "No UDP packet can be sent as reply to a host that has never made contact."
                )
            )
            return
        if address:
            self.udp_address = address
        self.socket.sendto(message, self.udp_address)

    def run_udp_listener(self):
        """
        UDP Thread Listener. Attempt to read UDP socket. On data read, send to `.recv_channel` ({name}/recv).
        @return:
        """
        _ = self.context._
        self.events_channel(
            _("UDP Socket({port}) Listening.").format(port=self.listen_port)
        )
        try:
            while self.state not in ("end", "terminate"):
                try:
                    message, address = self.socket.recvfrom(1024)
                except (socket.timeout, AttributeError):
                    continue
                if address is not None:
                    self.udp_address = address
                self.recv_channel(message)
        except OSError:
            pass
