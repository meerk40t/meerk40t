"""
Moshi Device Plugin

Registers the needed classes for ruida device (or would if the ruida device could be controlled).
"""


from meerk40t.ruida.device import RuidaDevice
from meerk40t.ruida.emulator import RuidaEmulator
from meerk40t.ruida.loader import RDLoader
from meerk40t.ruida.parser import RuidaParser


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "register":
        kernel.register("provider/device/ruida", RuidaDevice)

        _ = kernel.translation
        kernel.register("load/RDLoader", RDLoader)
        kernel.register("emulator/ruida", RuidaEmulator)
        kernel.register("parser/ruida", RuidaParser)

        @kernel.console_option(
            "verbose",
            "v",
            type=bool,
            action="store_true",
            help=_("do not watch server channels"),
        )
        @kernel.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current ruidaserver"),
        )
        @kernel.console_option(
            "laser",
            "l",
            type=str,
            default=None,
            help=_("relay commands to physical laser at the given network address"),
        )
        @kernel.console_command(
            ("ruidacontrol", "ruidadesign", "ruidaemulator"),
            help=_("activate the ruidaserver."),
            hidden=True,
        )
        def ruidaserver(
            command, channel, _, laser=None, verbose=False, quit=False, **kwargs
        ):
            """
            The ruidaserver emulation methods provide a simulation of a ruida device.
            this interprets ruida devices in order to be compatible with software that
            controls that type of device. This would then be sent to the device in a
            somewhat agnostic fashion. Commands like Ruida ACS's pause and stop require
            that the meerk40t device has a "pause" command and stop requires it has an
            "estop". You cannot stop a file output for example. Most of the other commands
            are device-agnostic, including the data sent.

            Laser is optional and only useful for a man-in-the-middle decoding

            ruidacontrol gives the ruida device control over the active device.
            ruidadesign accepts the ruida signals but turns them only into cutcode to be run locally.
            ruidabounce sends data to the ruidaemulator but sends data to the set bounce server.
            """
            root = kernel.root
            try:
                r2m = root.open_as("module/UDPServer", "rd2mk", port=50200)
                r2mj = root.open_as("module/UDPServer", "rd2mk-jog", port=50207)
                if laser:
                    m2l = root.open_as(
                        "module/UDPServer",
                        "mk2lz",
                        port=40200,
                        upd_address=(laser, 50200),
                    )
                    m2lj = root.open_as(
                        "module/UDPServer",
                        "mk2lz-jog",
                        port=40207,
                        upd_address=(laser, 50207),
                    )
                else:
                    m2l = None
                    m2lj = None
                emulator = root.open("emulator/ruida")
                if quit:
                    root.close("rd2mk")
                    root.close("rd2mk-jog")
                    root.close("mk2lz")
                    root.close("mk2lz-jog")
                    root.close("emulator/ruida")
                    channel(_("RuidaServer shutdown."))
                    return
                if r2m:
                    channel(
                        _("Ruida Data Server opened on port {port}.").format(port=50200)
                    )
                if r2mj:
                    channel(
                        _("Ruida Jog Server opened on port {port}.").format(port=50207)
                    )
                if m2l:
                    channel(
                        _("Ruida Data Destination opened on port {port}.").format(
                            port=40200
                        )
                    )
                if m2lj:
                    channel(
                        _("Ruida Jog Destination opened on port {port}.").format(
                            port=40207
                        )
                    )

                if verbose:
                    console = kernel.channel("console")
                    chan = "ruida"
                    root.channel(chan).watch(console)
                    if r2m:
                        r2m.events_channel.watch(console)
                    if r2mj:
                        r2mj.events_channel.watch(console)
                    if m2l:
                        m2l.events_channel.watch(console)
                    if m2lj:
                        m2lj.events_channel.watch(console)

                root.channel("rd2mk/recv").watch(emulator.checksum_write)
                root.channel("rd2mk-jog/recv").watch(emulator.realtime_write)
                if laser:
                    root.channel("mk2lz/recv").watch(emulator.checksum_write)
                    root.channel("mk2lz-jog/recv").watch(emulator.realtime_write)

                    root.channel("mk2lz/recv").watch("rd2mk/send")
                    root.channel("mk2lz-jog/recv").watch("rd2mk-jog/send")

                    root.channel("rd2mk/recv").watch("mk2lz/send")
                    root.channel("rd2mk-jog/recv").watch("mk2lz-jog/send")
                else:
                    root.channel("ruida_reply").watch(root.channel("rd2mk/send"))
                    root.channel("ruida_reply_realtime").watch(
                        root.channel("rd2mk-jog/send")
                    )

                emulator.spooler = kernel.device.spooler
                emulator.device = kernel.device
                emulator.elements = kernel.elements

                if command == "ruidadesign":
                    emulator.design = True
                elif command == "ruidacontrol":
                    emulator.control = True
                elif command == "ruidaemulator":
                    pass
            except OSError as e:
                channel(_("Server failed."))
                channel(str(e.strerror))
            return

    if lifecycle == "preboot":
        suffix = "ruida"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
