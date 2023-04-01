"""
Lihuiyu Device Plugin

Registers the needed classes for the lihuiyu device.
"""

from meerk40t.lihuiyu.device import LihuiyuDevice


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui as lhygui

        return [lhygui.plugin]
    elif lifecycle == "invalidate":
        try:
            import usb.core  # pylint: disable=unused-import
            import usb.util  # pylint: disable=unused-import
        except ImportError:
            print("Lihuiyu plugin could not load because pyusb is not installed.")
            return True
    if lifecycle == "register":
        kernel.register("provider/device/lhystudios", LihuiyuDevice)
        _ = kernel.translation
        kernel.register("dev_info/m2-nano", {
            "provider": "provider/device/lhystudios",
            "friendly_name": _("K40-CO2-Laser (m2nano-Board) (Green)"),
            "extended_info": _("The M2 Nano is the stock card in most K40 machines. Produced by Lihuiyu Studios Labs, the typically small green card is: Designed for Laser Machines. Assembled in China-Hangzhou. The most recent and popular revision version 9, 6C6879-LASER-M2:9."),
            "priority": 100,
            "family": _("CO2-Laser"),
            "choices": [
                {
                    "attr": "label",
                    "default": "M2-Nano",
                },
                {
                    "attr": "board",
                    "default": "M2",
                },
                {
                    "attr": "source",
                    "default": "co2",
                },
            ]
        })

        kernel.register("dev_info/m3-nano", {
            "provider": "provider/device/lhystudios",
            "friendly_name": _("K40-CO2-Laser (m3nano-Board) (Purple/Blue)"),
            "extended_info": _("The M3 Nano is a newer stock variation of the Lihuiyu Studios Labs board. Designed for Laser Machines. Assembled in China-Hangzhou. The most recent and popular revision version 10, 6C6879-LASER-M3:10. Unlike previous boards the M3 Nano has a hardware pause multi-plexing button and PWM control. The M3Nano Plus variation replaces the A4988 stpper motor chips with TMC stepper motor chips."),
            "priority": 99,
            "family": _("CO2-Laser"),
            "choices": [
                {
                    "attr": "board",
                    "default": "M3",
                },
                {
                    "attr": "label",
                    "default": "M3-Nano",
                },
                {
                    "attr": "source",
                    "default": "co2",
                },
            ]
        })

        try:
            from .loader import EgvLoader

            kernel.register("load/EgvLoader", EgvLoader)
        except ImportError:
            pass
        try:
            from .interpreter import LihuiyuInterpreter

            kernel.register("interpreter/lihuiyu", LihuiyuInterpreter)
        except ImportError:
            pass
    if lifecycle == "preboot":
        suffix = "lhystudios"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
