import usb.core
import usb.util

STATUS_NO_DEVICE = -1
USB_LOCK_VENDOR = 0x1a86  # Dev : (1a86) QinHeng Electronics
USB_LOCK_PRODUCT = 0x5512  # (5512) CH341A
BULK_WRITE_ENDPOINT = 0x02  # usb.util.ENDPOINT_OUT|usb.util.ENDPOINT_TYPE_BULK
BULK_READ_ENDPOINT = 0x82  # usb.util.ENDPOINT_IN|usb.util.ENDPOINT_TYPE_BULK
CH341_PARA_MODE_EPP19 = 0x01

mCH341_PARA_CMD_R0 = 0xAC  # 10101100
mCH341_PARA_CMD_R1 = 0xAD  # 10101101
mCH341_PARA_CMD_W0 = 0xA6  # 10100110
mCH341_PARA_CMD_W1 = 0xA7  # 10100111
mCH341_PARA_CMD_STS = 0xA0  # 10100000

mCH341_PACKET_LENGTH = 32
mCH341_PKT_LEN_SHORT = 8
mCH341_SET_PARA_MODE = 0x9A
mCH341_PARA_INIT = 0xB1
mCH341_VENDOR_READ = 0xC0
mCH341_VENDOR_WRITE = 0x40
mCH341A_BUF_CLEAR = 0xB2
mCH341A_DELAY_MS = 0x5E
mCH341A_GET_VER = 0x5F

STATE_UNINITIALIZED = -1
STATE_CONNECTING = 0
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
STATE_CH431_PARAMODE = 160

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


def convert_to_list_bytes(data):
    if isinstance(data, str):  # python 2
        return [ord(e) for e in data]
    else:
        return [e for e in data]


class CH341LibusbDriver:
    """
    Libusb driver for the CH341 chip. The CH341x is a USB interface chip that can emulate UART, parallel port,
    and synchronous serial (EPP, I2C, SPI). The Lhystudios boards (M2Nano, et al) and Moshi boards and likely others
    use this in EPP 1.9 mode. This class is not and not intended to be a full driver for that chip. Rather we are
    duplicating the function calls and implementing compatible operations to permit a stand-in for the default CH341
    driver. Using libusb to do the usb connection to the chip as well as permitting easy swapping that for the default
    driver. This serves as the basis to permit multiple operative methods, permitting use of either the default driver
    or Libusb driver interchangeably.

    Since these functions will need swapping in MSW we should duplicate the function calls thereof. Also since a stated
    goal is to support multiple devices implicitly, we should also properly support multiple device functionality.

    To this end, this should duplicate the names of the function calls. And the use of index to reference which
    connection to use for each command.
    """

    def __init__(self):
        self.devices = {}
        self.interface = {}
        self.signal = lambda e, f: e  # Nullop.
        self.state = None

    def set_status(self, code, obj=None):
        message = None
        if code == STATE_CONNECTING:
            message = "Attempting connection to USB."
        elif code == STATE_DRIVER_NO_BACKEND:
            message = "PyUsb detected no backend LibUSB driver."
        elif code == STATE_DEVICE_FOUND:
            message = "K40 device detected:\n%s\n" % str(obj)
        elif code == STATE_DEVICE_NOT_FOUND:
            message = "Not Found"
        elif code == STATE_DEVICE_REJECTED:
            message = "K40 devices were found but they were rejected."
        elif code == STATE_USB_SET_CONFIG:
            message = "Config Set"
        elif code == STATE_USB_DETACH_KERNEL:
            message = "Attempting to detach kernel."
        elif code == STATE_USB_DETACH_KERNEL_SUCCESS:
            message = "Kernel detach: Success."
        elif code == STATE_USB_DETACH_KERNEL_FAIL:
            message = "Kernel detach: Failed."
        elif code == STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED:
            message = "Kernel detach: Not Implemented."
        elif code == STATE_USB_CLAIM_INTERFACE:
            message = "Attempting to claim interface."
        elif code == STATE_USB_CLAIM_INTERFACE_SUCCESS:
            message = "Interface claim: Success"
        elif code == STATE_USB_CLAIM_INTERFACE_FAIL:
            message = "Interface claim: Fail"
        elif code == STATE_USB_CONNECTED:
            message = "USB Connected"
        elif code == STATE_USB_SET_DISCONNECTING:
            message = "Attempting disconnection from USB."
        elif code == STATE_USB_ATTACH_KERNEL:
            message = "Attempting kernel attach"
        elif code == STATE_USB_ATTACH_KERNEL_SUCCESS:
            message = "Kernel attach: Success."
        elif code == STATE_USB_ATTACH_KERNEL_FAIL:
            message = "Kernel attach: Fail."
        elif code == STATE_USB_RELEASE_INTERFACE:
            message = "Attempting to release interface."
        elif code == STATE_USB_RELEASE_INTERFACE_SUCCESS:
            message = "Interface released"
        elif code == STATE_USB_RELEASE_INTERFACE_FAIL:
            message = "Interface did not exist."
        elif code == STATE_USB_DISPOSING_RESOURCES:
            message = "Attempting to dispose resources."
        elif code == STATE_USB_RESET:
            message = "Attempting USB reset."
        elif code == STATE_USB_RESET_FAIL:
            message = "USB connection did not exist."
        elif code == STATE_USB_RESET_SUCCESS:
            message = "USB connection reset."
        elif code == STATE_USB_DISCONNECTED:
            message = "USB Disconnection Successful."
        self.signal('usb_log', message)
        self.signal('usb_state', code)
        self.state = code

    def choose_device(self, devices, index):
        """
        We have a choice of different devices and must choose which one to connect to.

        :param devices: List of devices to choose from.
        :param index: Index of the device we were asked to choose.
        :return: Device chosen.
        """

        for i, dev in enumerate(devices):
            # self.log("Device %d Bus: %d Address %d" % (i, dev.bus, dev.address))
            pass
        if devices is None or len(devices) == 0:
            return None
        else:
            return devices[index]
        # if self.kernel.usb_index == -1:
        #     if self.kernel.usb_address == -1 and self.kernel.usb_bus == -1:
        #         if len(d) > 0:
        #             self.usb = d[0]
        #     else:
        #         for dev in d:
        #             if (self.kernel.usb_address == -1 or self.kernel.usb_address == dev.address) and \
        #                     (self.kernel.usb_bus == -1 or self.kernel.usb_bus == dev.bus):
        #                 self.usb = dev
        #                 break
        # else:
        #     if len(d) > self.kernel.usb_index:
        #         self.usb = d[self.kernel.usb_index]

    def connect_find(self, index=0):
        try:
            devices = usb.core.find(idVendor=USB_LOCK_VENDOR, idProduct=USB_LOCK_PRODUCT, find_all=True)
        except usb.core.NoBackendError:
            self.set_status(STATE_DRIVER_NO_BACKEND)
            raise ConnectionError
        self.set_status(STATE_DRIVER_FINDING_DEVICES)
        devices = [d for d in devices]
        if len(devices) == 0:
            self.set_status(STATE_DEVICE_NOT_FOUND)
            raise ConnectionError
        self.set_status(STATE_DEVICE_FOUND, devices)
        device = self.choose_device(devices, index)
        if device is None:
            self.set_status(STATE_DEVICE_REJECTED)
            raise ConnectionError
        return device

    def connect_interface(self, device):
        self.set_status(STATE_USB_SET_CONFIG)
        device.set_configuration()
        self.set_status(STATE_USB_CLAIM_INTERFACE)
        try:
            interface = device.get_active_configuration()[(0, 0)]
            self.set_status(STATE_USB_CLAIM_INTERFACE_SUCCESS)
            return interface
        except usb.core.USBError:
            self.set_status(STATE_USB_CLAIM_INTERFACE_FAIL)
            raise ConnectionError

    def connect_detach(self, device, interface):
        try:
            if device.is_kernel_driver_active(interface.bInterfaceNumber):
                try:
                    self.set_status(STATE_USB_DETACH_KERNEL)
                    device.detach_kernel_driver(interface.bInterfaceNumber)
                    self.set_status(STATE_USB_DETACH_KERNEL_SUCCESS)
                except usb.core.USBError:
                    self.set_status(STATE_USB_DETACH_KERNEL_FAIL)
                    raise ConnectionError
        except NotImplementedError:
            self.set_status(STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED)  # Driver does not permit kernel detaching.
            # Non-fatal error.

    def connect_claim(self, device, interface):
        try:
            self.set_status(STATE_USB_CLAIM_INTERFACE)
            usb.util.claim_interface(device, interface)
            self.set_status(STATE_USB_CLAIM_INTERFACE_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_CLAIM_INTERFACE_FAIL)

    def disconnect_detach(self, device, interface):
        try:
            self.set_status(STATE_USB_ATTACH_KERNEL)
            device.attach_kernel_driver(interface.bInterfaceNumber)
            self.set_status(STATE_USB_ATTACH_KERNEL_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_ATTACH_KERNEL_FAIL)
            # Continue and hope it is non-critical.
        except NotImplementedError:
            self.set_status(STATE_USB_ATTACH_KERNEL_FAIL)

    def disconnect_interface(self, device, interface):
        try:
            self.set_status(STATE_USB_RELEASE_INTERFACE)
            usb.util.release_interface(device, interface)
            self.set_status(STATE_USB_RELEASE_INTERFACE_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_RELEASE_INTERFACE_FAIL)

    def disconnect_dispose(self, device):
        self.set_status(STATE_USB_DISPOSING_RESOURCES)
        usb.util.dispose_resources(device)

    def disconnect_reset(self, device):
        self.set_status(STATE_USB_RESET)
        try:
            device.reset()
            self.set_status(STATE_USB_RESET_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_RESET_FAIL)

    def CH341OpenDevice(self, index=0):
        """Opens device, returns index."""
        self.set_status(STATE_CONNECTING)
        try:
            device = self.connect_find(index)
            self.devices[index] = device
            interface = self.connect_interface(device)
            self.interface[index] = interface

            self.connect_detach(device, interface)
            self.connect_claim(device, interface)

            self.set_status(STATE_USB_CONNECTED)
            return index
        except ConnectionError:
            return -1

    def CH341CloseDevice(self, index=0):
        """Closes device."""
        device = self.devices[index]
        interface = self.interface[index]
        self.set_status(STATE_USB_SET_DISCONNECTING)
        if device is not None:
            try:
                self.disconnect_detach(device, interface)
                self.disconnect_interface(device, interface)
                del self.interface[index]
                self.disconnect_dispose(device)
                self.disconnect_reset(device)
                del self.devices[index]
                self.set_status(STATE_USB_DISCONNECTED)
            except ConnectionError:
                pass

    def CH341InitParallel(self, index=0, mode=CH341_PARA_MODE_EPP19):  # Mode 1, we need EPP 1.9
        """Permits setting a mode, but our mode is only 1 since the device is using
        EPP 1.9. This is a control transfer event."""
        device = self.devices[index]
        value = mode << 8
        if mode < 256:
            value |= 2
        device.ctrl_transfer(bmRequestType=mCH341_VENDOR_WRITE,
                             bRequest=mCH341_PARA_INIT,
                             wValue=value,
                             wIndex=0,
                             data_or_wLength=0,
                             timeout=5000)
        # 0x40, 177, 0x8800, 0, 0

    def CH341SetParaMode(self, index, mode=CH341_PARA_MODE_EPP19):
        device = self.devices[index]
        value = 0x2525
        device.ctrl_transfer(bmRequestType=mCH341_VENDOR_WRITE,
                             bRequest=mCH341_SET_PARA_MODE,
                             wValue=value,
                             wIndex=index,
                             data_or_wLength=mode << 8 | mode,
                             timeout=5000)
        # 0x40, 154, 0x2525, 257, 0

    def CH341EppWrite(self, index=0, buffer=None, length=0, pipe=0):
        if buffer is not None:
            device = self.devices[index]
            data = convert_to_list_bytes(buffer)
            while len(data) > 0:
                if pipe == 0:
                    packet = [mCH341_PARA_CMD_W0] + data[:31]
                else:
                    packet = [mCH341_PARA_CMD_W1] + data[:31]
                data = data[31:]
                device.write(BULK_WRITE_ENDPOINT, packet, 10000)

    def CH341EppRead(self, index=0, buffer=None, length=0, pipe=0):
        try:
            return self.devices[index].read(BULK_READ_ENDPOINT, length, 10000)
        except usb.USBError:
            return None

    def CH341GetStatus(self, index=0, status=[0]):
        """D7-0, 8: err, 9: pEmp, 10: Int, 11: SLCT, 12: SDA, 13: Busy, 14: datats, 15: addrs"""
        device = self.devices[index]
        device.write(BULK_WRITE_ENDPOINT, [mCH341_PARA_CMD_STS], 10000)
        status[0] = device.read(BULK_READ_ENDPOINT, 6, 10000)
        return status[0]

        # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)
    def CH341GetVerIC(self, index=0):
        device = self.devices[index]
        buffer = device.ctrl_transfer(bmRequestType=mCH341_VENDOR_READ,
                                      bRequest=mCH341A_GET_VER,
                                      wValue=0,
                                      wIndex=0,
                                      data_or_wLength=2,
                                      timeout=5000)
        if len(buffer) < 0:
            return 2
        else:
            return (buffer[1] << 8) | buffer[0]

    def CH341EppReadData(self, index=0, buffer=None, length=0):  # WR=1, DS=0, AS=1, D0-D7 in
        self.CH341EppRead(index, buffer, length, 0)

    def CH341EppReadAddr(self, index=0, buffer=None, length=0):  # WR=1, DS=0, AS=1 D0-D7 in
        self.CH341EppRead(index, buffer, length, 1)

    def CH341EppWriteData(self, index, buffer=None, length=0):  # WR=0, DS=0, AS=1, D0-D7 out
        self.CH341EppWrite(index, buffer, length, 0)

    def CH341EppWriteAddr(self, index, buffer=None, length=0):  # WR=0, DS=1, AS=0, D0-D7 out
        self.CH341EppWrite(index, buffer, length, 1)


class CH341Driver:
    def __init__(self, driver_index):
        self.driver = CH341LibusbDriver()
        self.driver_index = driver_index
        self.driver_value = None

    def open(self):
        if self.driver_value is None:
            val = self.driver.CH341OpenDevice(self.driver_index)
            if val == -1:
                raise ConnectionRefusedError
            self.driver_value = val
            self.driver.CH341InitParallel(self.driver_index, 1)  # 0x40, 177, 0x8800, 0, 0

    def close(self):
        self.driver.CH341CloseDevice(self.driver_index)
        self.driver_value = None

    def write(self, packet):
        self.driver.CH341EppWriteData(self.driver_index, packet, len(packet))

    def get_status(self):
        return self.driver.CH341GetStatus(self.driver_index)

    def get_chip_version(self):
        return self.driver.CH341GetVerIC(self.driver_index)  # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)
