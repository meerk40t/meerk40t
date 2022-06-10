def plugin(kernel, lifecycle):
    if lifecycle == "plugins":
        from meerk40t.balormk.gui import gui

        return [gui.plugin]
    if lifecycle == "invalidate":
        try:
            import numpy
        except ImportError:
            return True
    if lifecycle == "register":
        from meerk40t.balormk.device import BalorDevice

        kernel.register("provider/device/balor", BalorDevice)
    elif lifecycle == "preboot":
        suffix = "balor"
        for d in kernel.settings.derivable(suffix):
            kernel.root(
                "service device start -p {path} {suffix}\n".format(
                    path=d, suffix=suffix
                )
            )
