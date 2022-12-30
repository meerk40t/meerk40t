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
            import usb.core   # pylint: disable=unused-import
            import usb.util  # pylint: disable=unused-import
        except ImportError:
            print("Lihuiyu plugin could not load because pyusb is not installed.")
            return True
    if lifecycle == "register":
        kernel.register("provider/device/lhystudios", LihuiyuDevice)
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
        try:
            from .parser import LihuiyuParser

            kernel.register("parser/egv", LihuiyuParser)
        except ImportError:
            pass
    if lifecycle == "preboot":
        suffix = "lhystudios"
        for d in kernel.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
