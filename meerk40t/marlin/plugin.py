"""
Marlin Device Plugin

Registers the required files to run the Marlin device.
"""

from meerk40t.marlin.device import MarlinDevice, MarlinDriver


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]
    elif lifecycle == "invalidate":
        try:
            import serial  # pylint: disable=unused-import
            from serial import SerialException  # pylint: disable=unused-import
        except ImportError:
            print("Marlin plugin could not load because pyserial is not installed.")
            return True
    elif lifecycle == "register":
        _ = kernel.translation

        kernel.register("provider/device/marlin", MarlinDevice)
        kernel.register(
            "dev_info/marlin-generic",
            {
                "provider": "provider/device/marlin",
                "friendly_name": _("Generic (Marlin-Controller)"),
                "extended_info": _("Generic Marlin Laser Device."),
                "priority": 17,
                "family": _("Generic"),
                "family_priority": 20,
                "choices": [
                    {
                        "attr": "label",
                        "default": "Marlin",
                    },
                    {
                        "attr": "source",
                        "default": "generic",
                    },
                ],
            },
        )
        kernel.register("driver/marlin", MarlinDriver)
    elif lifecycle == "preboot":
        prefix = "marlin"
        for d in kernel.section_startswith(prefix):
            kernel.root(f"service device start -p {d} {prefix}\n")
