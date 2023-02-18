"""
Newly Device Plugin

"""


def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        from meerk40t.newly.gui import gui

        return [gui.plugin]
    elif lifecycle == "invalidate":
        try:
            import usb.core  # pylint: disable=unused-import
            import usb.util  # pylint: disable=unused-import
        except ImportError:
            print("Newly plugin could not load because pyusb is not installed.")
            return True
    if lifecycle == "register":
        from meerk40t.newly.device import NewlyDevice

        kernel.register("provider/device/newly", NewlyDevice)
    elif lifecycle == "preboot":
        suffix = "newly"
        for d in kernel.settings.derivable(suffix):
            kernel.root(f"service device start -p {d} {suffix}\n")
