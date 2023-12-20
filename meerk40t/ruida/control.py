"""
Ruida control code. This governs the interplay between the active device and the emulator. Taking on some aspects that
are not directly able to be emulated like giving the current state of the device or the location of that device.
"""
import threading

from meerk40t.ruida.emulator import RuidaEmulator


class ThreadedSender:
    def __init__(self, root, destination, name, start=False):
        self.root = root
        self._shutdown = False
        self._lock = threading.Condition()
        self._queue = []
        self._thread = None
        self._destination = destination
        self._name = name
        if start:
            self.start()

    def __call__(self, data, *args, **kwargs):
        self._queue.append(data)
        with self._lock:
            self._lock.notify()

    def shutdown(self):
        self._shutdown = True
        with self._lock:
            self._lock.notify()

    def start(self):
        root = self.root
        self._thread = root.threaded(
            self._thread_execute,
            thread_name=self._name,
            daemon=True,
        )

    def _thread_execute(self):
        while not self._shutdown:
            while self._queue:
                q = self._queue.pop(0)
                self._destination(q)
            with self._lock:
                self._lock.wait()


class RuidaControl:
    def __init__(self, root):
        self.root = root
        self.verbose = None
        self.man_in_the_middle = None
        self.emulator = None
        self.delay_emulator_checksum_write = None
        self._lock = threading.Condition()
        self._shutdown = False
        self._queue = []
        self.udp_program_to_mk = None
        self.udp_program_to_mk_jog = None
        self.mk_to_laser = None
        self.mk_to_laser_jog = None

    def open_udp_to_mk(self, jog=True):
        """
        Opens up UDP servers for ports 50200 and 50207. Called `rd2mk` and `rd2mk-jog`.

        UDP servers open channels {name}/send and {name}/recv.

        Replies go to the last address to send data to the server.

        @return:
        """
        root = self.root
        channel = root.channel("console")
        _ = channel._
        self.udp_program_to_mk = root.open_as("module/UDPServer", "rd2mk", port=50200)
        if self.udp_program_to_mk:
            channel(_("Ruida Data Server opened on port {port}.").format(port=50200))
        if not jog:
            return
        self.udp_program_to_mk_jog = root.open_as(
            "module/UDPServer", "rd2mk-jog", port=50207
        )
        if self.udp_program_to_mk_jog:
            channel(_("Ruida Jog Server opened on port {port}.").format(port=50207))


    def connect_emulator_to_udp(self, jog=True):
        """
        Any data from the program gets fed into the emulator write (delayed)
        Any data from the emulator reply/realtime gets sent as a reply.
        @return:
        """

        self.root.channel("rd2mk/recv").watch(self.delay_emulator_checksum_write)
        self.emulator.reply.watch(self.root.channel("rd2mk/send"))
        if not jog:
            return
        self.root.channel("rd2mk-jog/recv").watch(self.emulator.realtime_write)
        self.emulator.realtime.watch(self.root.channel("rd2mk-jog/send"))

    def open_emulator(self):
        """
        Open the RuidaEmulator.

        Attaches the various info channels

        @return:
        """
        root = self.root
        emulator = RuidaEmulator(root.device, root.device.view.matrix)
        self.emulator = emulator
        self.emulator.reply = root.channel("ruida_reply")
        self.emulator.realtime = root.channel("ruida_reply_realtime")
        self.emulator.channel = root.channel("ruida")

    def open_verbose(self):
        """
        Attaches various channels to the console.
        @return:
        """
        root = self.root
        console = root.channel("console")
        self.emulator.channel.watch(console)
        if self.udp_program_to_mk:
            self.udp_program_to_mk.events_channel.watch(console)
        if self.udp_program_to_mk_jog:
            self.udp_program_to_mk_jog.events_channel.watch(console)

    def issue_warnings(self, channel):
        """
        Warnings about ruidacontrol.

        @param channel:
        @return:
        """
        channel(
            "[red]WARNING: [blue]Non-horizontal rasters may not work well.[normal]",
            ansi=True,
        )
        channel(
            "[red]WARNING: [blue]Cuts are expected below 80mm/s. Rasters above that speed.[normal]",
            ansi=True,
        )

    def issue_mitm_warnings(self, channel):
        """Warning about man-in-the-middle"""
        channel(
            f"[blue]Man in the Middle Destination: {self.man_in_the_middle}[normal]",
            ansi=True,
        )

    def start(self, verbose=False, man_in_the_middle=None, jog=True):
        """
        Start Ruidacontrol server.

        @param verbose:
        @param man_in_the_middle:
        @param jog: Should open jog udp ports too.
        @return:
        """
        self.verbose = verbose
        self.man_in_the_middle = man_in_the_middle
        root = self.root

        self.open_emulator()
        self.delay_emulator_checksum_write = ThreadedSender(
            root,
            destination=self.emulator.checksum_write,
            name="ruidacontrol-sender",
            start=True,
        )

        channel = root.channel("console")
        _ = channel._

        self.issue_warnings(channel)
        if man_in_the_middle:
            self.issue_mitm_warnings(channel)

        try:
            self.open_udp_to_mk(jog=jog)
            self.connect_emulator_to_udp(jog=jog)

            if verbose:
                self.open_verbose()
        except OSError as e:
            channel(_("Server failed."))
            channel(str(e.strerror))

    def quit(self):
        """
        Close down the various modules, and quit.
        @return:
        """
        self.root.close("rd2mk")
        self.root.close("rd2mk-jog")
        self.root.close("mk2lz")
        self.root.close("mk2lz-jog")
        if self.verbose:
            pass

        self.delay_emulator_checksum_write.shutdown()
        self.verbose = None
        self.man_in_the_middle = None
        del self.emulator
        console = self.root.channel("console")
        _ = console._
        console(_("RuidaServer shutdown."))
