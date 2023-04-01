"""
Moshi Device Plugin

Registers the needed classes for ruida device (or would if the ruida device could be controlled).
"""
from meerk40t.ruida.control import RuidaControl
from meerk40t.ruida.device import RuidaDevice
from meerk40t.ruida.emulator import RuidaEmulator
from meerk40t.ruida.loader import RDLoader
from meerk40t.ruida.rdjob import RDJob


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("provider/device/ruida", RuidaDevice)
        kernel.register("dev_info/ruida-beta", {
            "provider": "provider/device/ruida",
            "friendly_name": _("K50/K60-CO2-Laser (Ruida-Controller) (INCOMPLETE)"),
            "extended_info": _("This driver is incomplete. Use at your own risk."),
            "priority": -1,
            "family": _("CO2-Laser"),
            "choices": [
                {
                    "attr": "label",
                    "default": "ruida",
                },
                {
                    "attr": "source",
                    "default": "co2",
                },
            ]
        })
        kernel.register("spoolerjob/ruida", RDJob)
        kernel.register("load/RDLoader", RDLoader)
        kernel.register("emulator/ruida", RuidaEmulator)

        @kernel.console_option(
            "verbose",
            "v",
            type=bool,
            action="store_true",
            help=_("watch server channels"),
        )
        @kernel.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current ruidaserver"),
        )
        @kernel.console_command(
            "ruidacontrol",
            help=_("activate the ruidaserver."),
            hidden=True,
        )
        def ruidaserver(command, channel, _, verbose=False, quit=False, **kwargs):
            """
            The ruidaserver emulation methods provide a simulation of a ruida device.
            this interprets ruida devices in order to be compatible with software that
            controls that type of device. This would then be sent to the device in a
            somewhat agnostic fashion.
            """
            root = kernel.root
            ruidacontrol = root.device.lookup("ruidacontrol")
            if ruidacontrol is None:
                if quit:
                    return
                ruidacontrol = RuidaControl(root)
                root.device.register("ruidacontrol", ruidacontrol)
                ruidacontrol.start(verbose=verbose)
            if quit:
                ruidacontrol.quit()
                root.device.unregister("ruidacontrol")

    if lifecycle == "preboot":
        suffix = "ruida"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
