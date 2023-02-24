"""
Grbl control. This code governs the interplay between the driver and the emulator.
"""


def greet():
    yield "Grbl 1.1f ['$' for help]\r"
    yield "[MSG:’$H’|’$X’ to unlock]"


class GRBLControl:
    def __init__(self, root):
        self.root = root
        self.emulator = None

    def start(self, port=23, verbose=False):
        root = self.root
        channel = root.channel("console")
        _ = channel._
        try:
            server = root.open_as("module/TCPServer", "grbl", port=port)
            from meerk40t.grbl.emulator import GRBLEmulator

            root.channel("grbl/send", pure=True).greet = greet

            channel(_("GRBL Mode."))
            if verbose:
                console = root.channel("console")
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

            channel(_("TCP Server for GRBL Emulator on port: {port}").format(port=port))
        except OSError as e:
            channel(_("Server failed on port: {port}").format(port=port))
            channel(str(e.strerror))
        return

    def quit(self):
        try:
            self.emulator.driver = None
            del self.emulator
        except AttributeError:
            pass
        self.root.close("grbl")

        console = self.root.channel("console")
        _ = console._
        console(_("GRBLServer shutdown."))
