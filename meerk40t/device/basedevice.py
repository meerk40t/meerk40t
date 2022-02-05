DRIVER_STATE_RAPID = 0
DRIVER_STATE_FINISH = 1
DRIVER_STATE_PROGRAM = 2
DRIVER_STATE_RASTER = 3
DRIVER_STATE_MODECHANGE = 4

PLOT_START = 2048
PLOT_FINISH = 256
PLOT_RAPID = 4
PLOT_JOG = 2
PLOT_SETTING = 128
PLOT_AXIS = 64
PLOT_DIRECTION = 32
PLOT_LEFT_UPPER = 512
PLOT_RIGHT_LOWER = 1024


def plugin(kernel, lifecycle=None):
    if lifecycle == "boot":
        last_device = kernel.read_persistent(str, "/", "activated_device", None)
        if last_device:
            kernel.activate_service_path("device", last_device)

        if not hasattr(kernel, "device"):
            preferred_device = kernel.root.setting(str, "preferred_device", "lhystudios")
            # Nothing has yet established a device. Boot this device.
            kernel.root(
                "service device start {preferred_device}\n".format(
                    preferred_device=preferred_device
                )
            )
    if lifecycle == "preshutdown":
        setattr(kernel.root, "activated_device", kernel.device.path)
