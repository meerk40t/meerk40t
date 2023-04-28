"""
Grbl control. This code governs the interplay between the driver and the emulator.
"""
import threading


def greet():
    yield "Grbl 1.1f ['$' for help]\r\n"
    yield "[MSG:’$H’|’$X’ to unlock]\r\n"


class GRBLControl:
    def __init__(self, root):
        self.root = root
        self.emulator = None
        self._thread = None
        self._lock = threading.Condition()
        self._shutdown = False
        self._queue = []

    def thread_execute(self):
        while not self._shutdown:
            while self._queue:
                q = self._queue.pop(0)
                self.emulator.write(q)
            with self._lock:
                self._lock.wait()

    def add_queue(self, data):
        self._queue.append(data)
        with self._lock:
            self._lock.notify()

    def start(self, port=23, verbose=False):
        root = self.root
        self._thread = root.threaded(
            self.thread_execute,
            thread_name=f"grblcontrol-sender",
            daemon=True,
        )

        channel = root.channel("console")
        channel(
            "[red]WARNING: [blue]This is currently in beta. Some parts do not work.[normal]",
            ansi=True,
        )
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

            emulator = GRBLEmulator(root.device, root.device.scene_to_device_matrix())
            self.emulator = emulator

            # Link emulator and server.
            tcp_recv_channel = root.channel("grbl/recv", pure=True)
            tcp_recv_channel.watch(self.add_queue)
            tcp_send_channel = root.channel("grbl/send", pure=True)
            emulator.reply = tcp_send_channel

            channel(_("TCP Server for GRBL Emulator on port: {port}").format(port=port))
        except OSError as e:
            channel(_("Server failed on port: {port}").format(port=port))
            channel(str(e.strerror))
        return

    def quit(self):
        self._shutdown = True
        with self._lock:
            self._lock.notify()

        del self.emulator
        self.root.close("grbl")

        console = self.root.channel("console")
        _ = console._
        console(_("GRBLServer shutdown."))
