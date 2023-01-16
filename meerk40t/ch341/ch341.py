def get_driver(context, log):
    def _state_change(state_value):
        context.signal("pipe;state", state_value)

    _ = log._
    if context.mock:
        log(_("Using Mock Driver."))
        from .mock import MockCH341Driver as MockDriver
        return MockDriver(channel=log, state=_state_change)

    try:
        from .libusb import LibCH341Driver

        return LibCH341Driver(channel=log, state=_state_change)
    except ImportError:
        log(_("PyUsb is not installed. Skipping."))
    try:
        from .windll import WinCH341Driver

        return WinCH341Driver(channel=log, state=_state_change)
    except ImportError:
        log(_("No Windll interfacing. Skipping."))
