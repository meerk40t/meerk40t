"""
Galvo Device Plugin

This registers the relevant files for using an LMC Galvo Device.
"""


def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        from meerk40t.galvodlc import galvo_commands
        from meerk40t.galvodlc.gui import gui

        return [gui.plugin, galvo_commands.plugin]
    elif lifecycle == "invalidate":
        try:
            import usb.core  # pylint: disable=unused-import
            import usb.util  # pylint: disable=unused-import
        except ImportError:
            print("Galvo-DLC plugin could not load because pyusb is not installed.")
            return True
    if lifecycle == "register":
        from meerk40t.galvodlc.device import BalorDevice

        kernel.register("provider/device/galvo", BalorDevice)
        kernel.register(
            "provider/friendly/galvo", ("Fibre-Laser (ezcad3 compatible)", 3)
        )
        _ = kernel.translation
        kernel.register(
            "dev_info/galvo-fiber",
            {
                "provider": "provider/device/galvo",
                "friendly_name": _("Fibre-Laser (JCZ-DLC-Controller) (Non-MOPA)"),
                "extended_info": _(
                    "The JCZ Controller is a type of Galvo Laser Controller for several different sources compatible with the EZCad2™ software."
                ),
                "priority": 9,
                "family": _("Generic Fibre-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Galvo-Fiber (DLC)",
                    },
                    {
                        "attr": "source",
                        "default": "fiber",
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/galvo-fiber-mopa",
            {
                "provider": "provider/device/galvo",
                "friendly_name": _("Fibre-Laser (JCZ-DLC-Controller) (MOPA)"),
                "extended_info": _(
                    "The JCZ Controller is a type of Galvo Laser Controller for several different sources compatible with the EZCad2™ software."
                )
                + "\n"
                + _("With this driver we specifically enable the MOPA feature."),
                "priority": 8,
                "family": _("Generic Fibre-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Galvo-Fiber (DLC)",
                    },
                    {
                        "attr": "source",
                        "default": "fiber",
                    },
                    {
                        "attr": "pulse_width_enabled",
                        "default": True,
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/galvo-co2",
            {
                "provider": "provider/device/galvo",
                "friendly_name": _("CO2 (JCZ-DLC-Controller)"),
                "extended_info": _(
                    "The JCZ Controller is a type of Galvo Laser Controller for several different sources compatible with the EZCad2™ software."
                )
                + "\n"
                + _(
                    "With specific settings for the CO2 source. (No specific settings are known)."
                ),
                "priority": 7,
                "family": _("Generic CO2-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Galvo-CO2",
                    },
                    {
                        "attr": "source",
                        "default": "co2",
                    },
                ],
            },
        )
        kernel.register(
            "dev_info/galvo-uv",
            {
                "provider": "provider/device/galvo",
                "friendly_name": _("UV (JCZ-DLC-Controller)"),
                "extended_info": _(
                    "The JCZ Controller is a type of Galvo Laser Controller for several different sources compatible with the EZCad2™ software."
                )
                + "\n"
                + _(
                    "With specific settings for the UV source. (No specific settings are known)."
                ),
                "priority": 6,
                "family": _("Generic UV-Laser"),
                "choices": [
                    {
                        "attr": "label",
                        "default": "Galvo-UV",
                    },
                    {
                        "attr": "source",
                        "default": "uv",
                    },
                ],
            },
        )

    elif lifecycle == "preboot":
        prefix = "galvo"
        for d in kernel.settings.section_startswith(prefix):
            kernel.root(f"service device start -p {d} {prefix}\n")
