
STATE_UNINITIALIZED = -1
STATE_CONNECTING = 0
STATE_CONNECTION_FAILED = 2
STATE_DRIVER_LIBUSB = 3
STATE_DRIVER_CH341 = 4
STATE_DRIVER_MOCK = 5
STATE_DRIVER_FINDING_DEVICES = 10
STATE_DRIVER_NO_BACKEND = 20
STATE_DRIVER_NO_LIBUSB = 21
STATE_DEVICE_FOUND = 30
STATE_DEVICE_NOT_FOUND = 50
STATE_DEVICE_REJECTED = 60

STATE_USB_SET_CONFIG = 100
STATE_USB_SET_CONFIG_SUCCESS = 110
STATE_USB_SET_CONFIG_FAIL = 120
STATE_USB_DETACH_KERNEL = 200
STATE_USB_DETACH_KERNEL_SUCCESS = 210
STATE_USB_DETACH_KERNEL_FAIL = 220
STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED = 230

STATE_USB_SET_ACTIVE_CONFIG = 250
STATE_USB_SET_ACTIVE_CONFIG_SUCCESS = 260
STATE_USB_SET_ACTIVE_CONFIG_FAIL = 270

STATE_USB_CLAIM_INTERFACE = 300
STATE_USB_CLAIM_INTERFACE_SUCCESS = 310
STATE_USB_CLAIM_INTERFACE_FAIL = 320

STATE_USB_CONNECTED = 400
STATE_CH341_PARAMODE = 160
STATE_CH341_PARAMODE_FAIL = 170
STATE_CH341_PARAMODE_SUCCESS = 180

STATE_CONNECTED = 600

INFO_USB_CHIP_VERSION = 0x100000
INFO_USB_DRIVER = 0x200000

STATE_USB_SET_DISCONNECTING = 1000
STATE_USB_ATTACH_KERNEL = 1100
STATE_USB_ATTACH_KERNEL_SUCCESS = 1110
STATE_USB_ATTACH_KERNEL_FAIL = 1120
STATE_USB_RELEASE_INTERFACE = 1200
STATE_USB_RELEASE_INTERFACE_SUCCESS = 1210
STATE_USB_RELEASE_INTERFACE_FAIL = 1220

STATE_USB_DISPOSING_RESOURCES = 1300
STATE_USB_DISPOSING_RESOURCES_SUCCESS = 1310
STATE_USB_DISPOSING_RESOURCES_FAIL = 1320
STATE_USB_RESET = 1400
STATE_USB_RESET_SUCCESS = 1410
STATE_USB_RESET_FAIL = 1420
STATE_USB_DISCONNECTED = 1500


def get_name_for_status(code, obj=None, translation=lambda e: e):
    _ = translation
    if code == STATE_UNINITIALIZED:
        return _("Uninitialized.")
    elif code == STATE_CONNECTING:
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
    elif code == STATE_DRIVER_NO_LIBUSB:
        return _("PyUsb is not installed. Skipping.")
    elif code == STATE_DEVICE_FOUND:
        return _("K40 device detected:")
    elif code == STATE_DEVICE_NOT_FOUND:
        return _("Devices Not Found.")
    elif code == STATE_DEVICE_REJECTED:
        return _("K40 devices were found but they were rejected.")
    elif code == STATE_USB_SET_CONFIG:
        return _("Config Set")
    elif code == STATE_USB_SET_CONFIG_SUCCESS:
        return _("Config Set: Success")
    elif code == STATE_USB_SET_CONFIG_FAIL:
        return _("Config Set: Fail\n(Hint: may recover if you change where the USB is plugged in.)")
    elif code == STATE_USB_DETACH_KERNEL:
        return _("Attempting to detach kernel.")
    elif code == STATE_USB_DETACH_KERNEL_SUCCESS:
        return _("Kernel detach: Success.")
    elif code == STATE_USB_DETACH_KERNEL_FAIL:
        return _("Kernel detach: Failed.")
    elif code == STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED:
        return _("Kernel detach: Not Implemented.")
    elif code == STATE_USB_SET_ACTIVE_CONFIG:
        return _("Setting Active Config")
    elif code == STATE_USB_SET_ACTIVE_CONFIG_SUCCESS:
        return _("Active Config: Success.")
    elif code == STATE_USB_SET_ACTIVE_CONFIG_FAIL:
        return _("Active Config: Failed.")
    elif code == STATE_USB_CLAIM_INTERFACE:
        return _("Attempting to claim interface.")
    elif code == STATE_USB_CLAIM_INTERFACE_SUCCESS:
        return _("Interface claim: Success")
    elif code == STATE_USB_CLAIM_INTERFACE_FAIL:
        return _("Interface claim: Failed. (Interface is in use.)")
    elif code == STATE_USB_CONNECTED:
        return _("USB Connected.")
    elif code == STATE_CH341_PARAMODE:
        return _("Sending CH341 mode change to EPP1.9.")
    elif code == STATE_CH341_PARAMODE_SUCCESS:
        return _("CH341 mode change to EPP1.9: Success.")
    elif code == STATE_CH341_PARAMODE_FAIL:
        return _("CH341 mode change to EPP1.9: Fail.")
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
    elif code == STATE_USB_DISPOSING_RESOURCES_SUCCESS:
        return _("Dispose Resources: Success")
    elif code == STATE_USB_DISPOSING_RESOURCES_FAIL:
        return _("Dispose Resources: Fail")
    elif code == STATE_USB_RESET:
        return _("Attempting USB reset.")
    elif code == STATE_USB_RESET_FAIL:
        return _("USB connection did not exist.")
    elif code == STATE_USB_RESET_SUCCESS:
        return _("USB connection reset.")
    elif code == STATE_USB_DISCONNECTED:
        return _("USB Disconnection Successful.\n")
    elif code & INFO_USB_CHIP_VERSION != 0:
        return _("CH341 Chip Version: %d") % (code & 0xFFFF)
    elif code == (INFO_USB_DRIVER | STATE_DRIVER_LIBUSB):
        return _("Driver Detected: LibUsb")
    elif code == (INFO_USB_DRIVER | STATE_DRIVER_CH341):
        return _("Driver Detected: CH341")
    return _("Unknown")


def convert_to_list_bytes(data):
    if isinstance(data, str):  # python 2
        return [ord(e) for e in data]
    else:
        return [e for e in data]
