"""
Ruida control code. This governs the interplay between the active device and the emulator. Taking on some aspects that
are not directly able to be emulated like giving the current state of the device or the location of that device.
"""
import threading

from meerk40t.ruida.emulator import RuidaEmulator


class RuidaControl:
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
                self.emulator.checksum_write(q)
            with self._lock:
                self._lock.wait()

    def add_queue(self, data):
        self._queue.append(data)
        with self._lock:
            self._lock.notify()

    def start(self, verbose=False):
        root = self.root
        self._thread = root.threaded(
            self.thread_execute,
            thread_name=f"ruidacontrol-sender",
            daemon=True,
        )

        channel = root.channel("console")
        channel(
            "[red]WARNING: [blue]This is currently being rewritten and is back in beta. Some parts do not work. Use MeerK40t 0.7.x if you want consistency.[normal]",
            ansi=True,
        )
        _ = channel._
        try:
            r2m = root.open_as("module/UDPServer", "rd2mk", port=50200)
            r2mj = root.open_as("module/UDPServer", "rd2mk-jog", port=50207)
            emulator = RuidaEmulator(root.device, root.device.scene_to_device_matrix())
            self.emulator = emulator
            if r2m:
                channel(
                    _("Ruida Data Server opened on port {port}.").format(port=50200)
                )
            if r2mj:
                channel(_("Ruida Jog Server opened on port {port}.").format(port=50207))

            emulator.reply = root.channel("ruida_reply")
            emulator.realtime = root.channel("ruida_reply_realtime")
            emulator.channel = root.channel("ruida")
            if verbose:
                console = root.channel("console")
                emulator.channel.watch(console)
                if r2m:
                    r2m.events_channel.watch(console)
                if r2mj:
                    r2mj.events_channel.watch(console)
            root.channel("rd2mk/recv").watch(self.add_queue)
            root.channel("rd2mk-jog/recv").watch(emulator.realtime_write)
            emulator.reply.watch(root.channel("rd2mk/send"))
            emulator.realtime.watch(root.channel("rd2mk-jog/send"))
        except OSError as e:
            channel(_("Server failed."))
            channel(str(e.strerror))

    def quit(self):
        self.root.close("rd2mk")
        self.root.close("rd2mk-jog")
        self.root.close("mk2lz")
        self.root.close("mk2lz-jog")
        self._shutdown = True
        with self._lock:
            self._lock.notify()
        del self.emulator
        console = self.root.channel("console")
        _ = console._
        console(_("RuidaServer shutdown."))
