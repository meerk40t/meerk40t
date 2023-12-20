"""
Ruida control code. This governs the interplay between the active device and the emulator. Taking on some aspects that
are not directly able to be emulated like giving the current state of the device or the location of that device.
"""

from meerk40t.ruida.emulator import RuidaEmulator


class RuidaControl:
    def __init__(self, root):
        self.root = root
        self.verbose = None
        self.man_in_the_middle = None
        self.emulator = None
        # self.delay_emulator_checksum_write = None
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

    def open_udp_to_laser(self, jog=True):
        """
        Opens up UDP servers for ports 40200 and 40207. Called `mk2lz` and `mk2lz-jog`.

        UDP servers open channels {name}/send and {name}/recv.

        Replies go to the last address to send data to the server.

        @return:
        """
        root = self.root
        channel = root.channel("console")
        _ = channel._
        self.mk_to_laser = root.open_as("module/UDPServer", "mk2lz", port=40200)
        self.mk_to_laser.udp_address = (self.man_in_the_middle, 50200)
        if self.mk_to_laser:
            channel(_("Ruida Data Server opened on port {port}.").format(port=40200))
        if not jog:
            return
        self.mk_to_laser_jog = root.open_as("module/UDPServer", "mk2lz-jog", port=40207)
        self.mk_to_laser_jog.udp_address = (self.man_in_the_middle, 50207)
        if self.mk_to_laser_jog:
            channel(_("Ruida Jog Server opened on port {port}.").format(port=40207))

    def connect_man_in_the_middle(self, jog=True):
        """
        Connects the rd2mk to mk2lz and vice versa.

        @param jog:
        @return:
        """

        self.root.channel("mk2lz/send").start(self.root)
        self.root.channel("mk2lz/recv").start(self.root)
        self.root.channel("rd2mk/recv").watch(self.root.channel("mk2lz/send"))
        self.root.channel("rd2mk/send").watch(self.root.channel("mk2lz/recv"))
        self.root.channel("mk2lz/recv").watch(self.root.channel("rd2mk/send"))
        self.root.channel("mk2lz/send").watch(self.root.channel("rd2mk/recv"))
        if not jog:
            return
        self.root.channel("mk2lz-jog/send").start(self.root)
        self.root.channel("mk2lz-jog/recv").start(self.root)

        self.root.channel("rd2mk-jog/recv").watch(self.root.channel("mk2lz-jog/send"))
        self.root.channel("rd2mk-jog/send").watch(self.root.channel("mk2lz-jog/recv"))
        self.root.channel("mk2lz-jog/recv").watch(self.root.channel("rd2mk-jog/send"))
        self.root.channel("mk2lz-jog/send").watch(self.root.channel("rd2mk-jog/recv"))

    def connect_emulator_to_udp(self, jog=True):
        """
        Any data from the program gets fed into the emulator write (delayed)
        Any data from the emulator reply/realtime gets sent as a reply.
        @return:
        """

        self.root.channel("rd2mk/recv").watch(self.emulator.checksum_write)
        self.emulator.reply.watch(self.root.channel("rd2mk/send"))
        self.root.channel("rd2mk/recv").start(self.root)
        self.root.channel("rd2mk/send").start(self.root)
        if not jog:
            return
        self.root.channel("rd2mk-jog/recv").watch(self.emulator.realtime_write)
        self.emulator.realtime.watch(self.root.channel("rd2mk-jog/send"))
        self.root.channel("rd2mk-jog/recv").start(self.root)
        self.root.channel("rd2mk-jog/send").start(self.root)

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

        channel = root.channel("console")
        _ = channel._

        self.issue_warnings(channel)
        if man_in_the_middle:
            self.issue_mitm_warnings(channel)

        try:
            self.open_udp_to_mk(jog=jog)
            self.connect_emulator_to_udp(jog=jog)
            if man_in_the_middle:
                self.open_udp_to_laser(jog=jog)
                self.connect_man_in_the_middle(jog=jog)
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

        # self.delay_emulator_checksum_write.stop()
        self.verbose = None
        self.man_in_the_middle = None
        del self.emulator
        console = self.root.channel("console")
        _ = console._
        console(_("RuidaServer shutdown."))
