"""
Galvo Device Plugin

This registers the relevant files for using an LMC Galvo Device.
"""


def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        from meerk40t.balormk.gui import gui

        return [gui.plugin]
    elif lifecycle == "invalidate":
        try:
            import usb.core  # pylint: disable=unused-import
            import usb.util  # pylint: disable=unused-import
        except ImportError:
            print("Galvo plugin could not load because pyusb is not installed.")
            return True
    if lifecycle == "register":
        from meerk40t.balormk.device import BalorDevice

        kernel.register("provider/device/balor", BalorDevice)
    elif lifecycle == "preboot":
        suffix = "balor"
        for d in kernel.settings.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
