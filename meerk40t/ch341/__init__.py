def get_ch341_interface(context, log, mock=False, mock_status=206):
    def _state_change(state_value):
        context.signal("pipe;state", state_value)

    _ = log._
    if mock:
        log(_("Using Mock Driver."))
        from .mock import MockCH341Driver as MockDriver
        mock_device = MockDriver(channel=log, state=_state_change)
        mock_device.mock_status = mock_status
        yield mock_device
        return

    try:
        from .libusb import LibCH341Driver

        yield LibCH341Driver(channel=log, state=_state_change)
    except ImportError:
        log(_("PyUsb is not installed. Skipping."))

    try:
        from .windriver import WinCH341Driver

        yield WinCH341Driver(channel=log, state=_state_change)
    except ImportError:
        log(_("No Windll interfacing. Skipping."))
