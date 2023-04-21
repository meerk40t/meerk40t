def get_ch341_interface(context, log):
    def _state_change(state_value):
        context.signal("pipe;state", state_value)

    _ = log._
    if context.interface == "mock":
        log(_("Using Mock Driver."))
        from .mock import MockCH341Driver as MockDriver

        yield MockDriver(channel=log, state=_state_change)
        return

    try:
        from .libusb import LibCH341Driver

        yield LibCH341Driver(channel=log, state=_state_change)
    except ImportError:
        log(_("PyUsb is not installed. Skipping."))

    try:
        from .windll import WinCH341Driver

        yield WinCH341Driver(channel=log, state=_state_change)
    except ImportError:
        log(_("No Windll interfacing. Skipping."))
