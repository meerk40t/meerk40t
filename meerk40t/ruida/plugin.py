"""
Ruida Device Plugin

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
        # We don't want the ruida entry to appear
        # kernel.register("provider/friendly/ruida", ("CO2-Laser (DSP-Ruida)", 6))
        kernel.register(
            "dev_info/ruida-beta",
            {
                "provider": "provider/device/ruida",
                "friendly_name": _("K50/K60-CO2-Laser (Ruida-Controller) (INCOMPLETE)"),
                "extended_info": _("This driver is incomplete. Use at your own risk."),
                "priority": -1,
                "family": _("K-Series CO2-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "ruida",
                    },
                    {
                        "attr": "source",
                        "default": "co2",
                    },
                ],
            },
        )
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
        @kernel.console_option(
            "jogless",
            "j",
            type=bool,
            default=False,
            action="store_true",
            help=_("do not open jog ports"),
        )
        @kernel.console_option(
            "man_in_the_middle",
            "m",
            type=str,
            help=_("Redirect traffic to a real laser"),
        )
        @kernel.console_option(
            "bridge",
            "b",
            type=bool,
            default=False,
            action="store_true",
            help=_("Use LB2RD Bridge Protocol"),
        )
        @kernel.console_command(
            "ruidacontrol",
            help=_("activate the ruidaserver."),
        )
        def ruidaserver(
            command,
            channel,
            _,
            verbose=False,
            quit=False,
            jogless=False,
            man_in_the_middle=None,
            bridge=False,
            **kwargs,
        ):
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
                ruidacontrol.start(
                    verbose=verbose,
                    man_in_the_middle=man_in_the_middle,
                    jog=not jogless,
                    bridge=bridge,
                )
            if quit:
                ruidacontrol.quit()
                root.device.unregister("ruidacontrol")

    if lifecycle == "preboot":
        prefix = "ruida"
        for d in kernel.section_startswith(prefix):
            kernel.root(f"service device start -p {d} {prefix}\n")
