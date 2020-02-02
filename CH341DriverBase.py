
STATE_UNINITIALIZED = -1
STATE_CONNECTING = 0
STATE_CONNECTION_FAILED = 2
STATE_DRIVER_LIBUSB = 3
STATE_DRIVER_CH341 = 4
STATE_DRIVER_MOCK = 5
STATE_DRIVER_FINDING_DEVICES = 10
STATE_DRIVER_NO_BACKEND = 20
STATE_DEVICE_FOUND = 30
STATE_DEVICE_NOT_FOUND = 50
STATE_DEVICE_REJECTED = 60

STATE_USB_SET_CONFIG = 100
STATE_USB_DETACH_KERNEL = 200
STATE_USB_DETACH_KERNEL_SUCCESS = 210
STATE_USB_DETACH_KERNEL_FAIL = 220
STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED = 230

STATE_USB_CLAIM_INTERFACE = 300
STATE_USB_CLAIM_INTERFACE_SUCCESS = 310
STATE_USB_CLAIM_INTERFACE_FAIL = 320

STATE_USB_CONNECTED = 400
STATE_CH341_PARAMODE = 160

STATE_CONNECTED = 600

STATE_USB_SET_DISCONNECTING = 1000
STATE_USB_ATTACH_KERNEL = 1100
STATE_USB_ATTACH_KERNEL_SUCCESS = 1110
STATE_USB_ATTACH_KERNEL_FAIL = 1120
STATE_USB_RELEASE_INTERFACE = 1200
STATE_USB_RELEASE_INTERFACE_SUCCESS = 1210
STATE_USB_RELEASE_INTERFACE_FAIL = 1220

STATE_USB_DISPOSING_RESOURCES = 1200
STATE_USB_RESET = 1400
STATE_USB_RESET_SUCCESS = 1410
STATE_USB_RESET_FAIL = 1420
STATE_USB_DISCONNECTED = 1500


def get_name_for_status(code, obj=None, translation=lambda e: e):
    _ = translation
    if code == STATE_CONNECTING:
        return _("Attempting connection to USB.")
    elif code == STATE_CONNECTION_FAILED:
        return _("Connection to USB failed.\n")
    elif code == STATE_DRIVER_LIBUSB:
        return _("Using LibUSB to connect.")
    elif code == STATE_DRIVER_CH341:
        return _("Using CH341 Driver to connect.")
    elif code == STATE_DRIVER_MOCK:
        return _("Using Mock Driver.")
    elif code == STATE_DRIVER_FINDING_DEVICES:
        return _("Finding devices.")
    elif code == STATE_DRIVER_NO_BACKEND:
        return _("PyUsb detected no backend LibUSB driver.")
    elif code == STATE_DEVICE_FOUND:
        return _("K40 device detected:\n%s\n") % str(obj)
    elif code == STATE_DEVICE_NOT_FOUND:
        return _("Devices Not Found.")
    elif code == STATE_DEVICE_REJECTED:
        return _("K40 devices were found but they were rejected.")
    elif code == STATE_USB_SET_CONFIG:
        return _("Config Set")
    elif code == STATE_USB_DETACH_KERNEL:
        return _("Attempting to detach kernel.")
    elif code == STATE_USB_DETACH_KERNEL_SUCCESS:
        return _("Kernel detach: Success.")
    elif code == STATE_USB_DETACH_KERNEL_FAIL:
        return _("Kernel detach: Failed.")
    elif code == STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED:
        return _("Kernel detach: Not Implemented.")
    elif code == STATE_USB_CLAIM_INTERFACE:
        return _("Attempting to claim interface.")
    elif code == STATE_USB_CLAIM_INTERFACE_SUCCESS:
        return _("Interface claim: Success")
    elif code == STATE_USB_CLAIM_INTERFACE_FAIL:
        return _("Interface claim: Fail")
    elif code == STATE_USB_CONNECTED:
        return _("USB Connected.")
    elif code == STATE_CH341_PARAMODE:
        return _("Sending CH341 mode change to EPP1.9.")
    elif code == STATE_CONNECTED:
        return _("Device Connected.\n")
    elif code == STATE_USB_SET_DISCONNECTING:
        return _("Attempting disconnection from USB.")
    elif code == STATE_USB_ATTACH_KERNEL:
        return _("Attempting kernel attach")
    elif code == STATE_USB_ATTACH_KERNEL_SUCCESS:
        return _("Kernel attach: Success.")
    elif code == STATE_USB_ATTACH_KERNEL_FAIL:
        return _("Kernel attach: Fail.")
    elif code == STATE_USB_RELEASE_INTERFACE:
        return _("Attempting to release interface.")
    elif code == STATE_USB_RELEASE_INTERFACE_SUCCESS:
        return _("Interface released.")
    elif code == STATE_USB_RELEASE_INTERFACE_FAIL:
        return _("Interface did not exist.")
    elif code == STATE_USB_DISPOSING_RESOURCES:
        return _("Attempting to dispose resources.")
    elif code == STATE_USB_RESET:
        return _("Attempting USB reset.")
    elif code == STATE_USB_RESET_FAIL:
        return _("USB connection did not exist.")
    elif code == STATE_USB_RESET_SUCCESS:
        return _("USB connection reset.")
    elif code == STATE_USB_DISCONNECTED:
        return _("USB Disconnection Successful.\n")
    return _("Unknown")


def convert_to_list_bytes(data):
    if isinstance(data, str):  # python 2
        return [ord(e) for e in data]
    else:
        return [e for e in data]
