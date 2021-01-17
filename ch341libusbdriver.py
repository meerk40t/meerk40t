import usb.core
import usb.util
from ch341driverbase import *

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


class CH341LibusbDriver:
    """
    Libusb driver for the CH341 chip. The CH341x is a USB interface chip that can emulate UART, parallel port,
    and synchronous serial (EPP, I2C, SPI). The Lhystudios boards (M2Nano, et al) and Moshiboards and likely others
    use this in EPP 1.9 mode. This class is not and not intended to be a full driver for that chip. Rather we are
    duplicating the function calls and implementing compatible operations to permit a stand-in for the default CH341
    driver. Using libusb to do the usb connection to the chip as well as permitting easy swapping that for the default
    driver. This serves as the basis to permit multiple operative methods, permitting use of either the default driver
    or Libusb driver interchangeably.

    Since these functions will need swapping in MSW we should duplicate the function calls thereof. Also since a stated
    goal is to support multiple devices implicitly, we should also properly support multiple device functionality.

    To this end, this should duplicate the names of the function calls. And the use of index to reference which
    connection to use for each command.

    All the commands during the opening phase will raise a ConnectionRefusedError.
    All commands during read and write raise ConnectionErrors
    All commands during close don't care about errors, if it broke it's likely already closed.
    """

    def __init__(self, state_listener=None):
        self.devices = {}
        self.interface = {}
        self.state_listener = state_listener
        self.state = None

    def set_status(self, code):
        self.state_listener(code)
        if isinstance(code, int):
            self.state = code

    def connect_find(self, index=0):
        self.set_status(STATE_DRIVER_LIBUSB)
        self.set_status(STATE_DRIVER_FINDING_DEVICES)
        try:
            devices = usb.core.find(idVendor=USB_LOCK_VENDOR, idProduct=USB_LOCK_PRODUCT, find_all=True)
        except usb.core.USBError:
            raise ConnectionRefusedError
        devices = [d for d in devices]
        if len(devices) == 0:
            self.set_status(STATE_DEVICE_NOT_FOUND)
            raise ConnectionRefusedError
        for d in devices:
            self.set_status(STATE_DEVICE_FOUND)
            string = str(d)
            string = string.replace('\n', '\n\t')
            self.set_status(string)
        try:
            device = devices[index]
        except IndexError:
            self.set_status(STATE_DEVICE_REJECTED)
            raise ConnectionRefusedError
        return device

    def connect_detach(self, device, interface):
        try:
            if device.is_kernel_driver_active(interface.bInterfaceNumber):
                try:
                    self.set_status(STATE_USB_DETACH_KERNEL)
                    device.detach_kernel_driver(interface.bInterfaceNumber)
                    self.set_status(STATE_USB_DETACH_KERNEL_SUCCESS)
                except usb.core.USBError:
                    self.set_status(STATE_USB_DETACH_KERNEL_FAIL)
                    raise ConnectionRefusedError
        except NotImplementedError:
            self.set_status(STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED)  # Driver does not permit kernel detaching.
            # Non-fatal error.

    def connect_interface(self, device):
        self.set_status(STATE_USB_SET_CONFIG)
        try:
            device.set_configuration()
            self.set_status(STATE_USB_SET_CONFIG_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_SET_CONFIG_FAIL)
            raise ConnectionRefusedError
        self.set_status(STATE_USB_SET_ACTIVE_CONFIG)
        try:
            interface = device.get_active_configuration()[(0, 0)]
            self.set_status(STATE_USB_SET_ACTIVE_CONFIG_SUCCESS)
            return interface
        except usb.core.USBError:
            self.set_status(STATE_USB_SET_ACTIVE_CONFIG_FAIL)
            raise ConnectionRefusedError

    def connect_claim(self, device, interface):
        try:
            self.set_status(STATE_USB_CLAIM_INTERFACE)
            usb.util.claim_interface(device, interface)
            self.set_status(STATE_USB_CLAIM_INTERFACE_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_CLAIM_INTERFACE_FAIL)
            raise ConnectionRefusedError
            # Already in use. This is critical.

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
        try:
            self.set_status(STATE_USB_DISPOSING_RESOURCES)
            usb.util.dispose_resources(device)
            self.set_status(STATE_USB_DISPOSING_RESOURCES_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_DISPOSING_RESOURCES_FAIL)
            pass

    def disconnect_reset(self, device):
        try:
            self.set_status(STATE_USB_RESET)
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
            try:
                self.connect_claim(device, interface)
            except ConnectionRefusedError:
                # Attempting interface cycle.
                self.disconnect_interface(device, interface)
                self.connect_claim(device, interface)
            self.set_status(STATE_USB_CONNECTED)
            return index
        except usb.core.NoBackendError:
            self.set_status(STATE_DRIVER_NO_BACKEND)
            return -1
        except ConnectionRefusedError:
            self.set_status(STATE_CONNECTION_FAILED)
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
                self.disconnect_dispose(device)
                self.disconnect_reset(device)
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
        try:
            device.ctrl_transfer(bmRequestType=mCH341_VENDOR_WRITE,
                                 bRequest=mCH341_PARA_INIT,
                                 wValue=value,
                                 wIndex=0,
                                 data_or_wLength=0,
                                 timeout=500)
            # 0x40, 177, 0x8800, 0, 0
        except usb.core.USBError:
            # Device was not found. Timed out, etc.
            raise ConnectionError

    def CH341SetParaMode(self, index, mode=CH341_PARA_MODE_EPP19):
        device = self.devices[index]
        value = 0x2525
        try:
            device.ctrl_transfer(bmRequestType=mCH341_VENDOR_WRITE,
                                 bRequest=mCH341_SET_PARA_MODE,
                                 wValue=value,
                                 wIndex=index,
                                 data_or_wLength=mode << 8 | mode,
                                 timeout=500)
            # 0x40, 154, 0x2525, 257, 0
        except usb.core.USBError:
            raise ConnectionError

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
                try:
                    device.write(BULK_WRITE_ENDPOINT, packet, 200)
                except usb.core.USBError:
                    raise ConnectionError

    def CH341EppRead(self, index=0, buffer=None, length=0, pipe=0):
        try:
            return self.devices[index].read(BULK_READ_ENDPOINT, length, 200)
        except usb.core.USBError:
            raise ConnectionError

    def CH341GetStatus(self, index=0, status=[0]):
        """D7-0, 8: err, 9: pEmp, 10: Int, 11: SLCT, 12: SDA, 13: Busy, 14: datas, 15: addrs"""
        device = self.devices[index]
        try:
            device.write(BULK_WRITE_ENDPOINT, [mCH341_PARA_CMD_STS], 200)
            status[0] = device.read(BULK_READ_ENDPOINT, 6, 200)
        except usb.core.USBError:
            raise ConnectionError
        return status[0]
        # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)

    def CH341GetVerIC(self, index=0):
        device = self.devices[index]
        try:
            buffer = device.ctrl_transfer(bmRequestType=mCH341_VENDOR_READ,
                                          bRequest=mCH341A_GET_VER,
                                          wValue=0,
                                          wIndex=0,
                                          data_or_wLength=2,
                                          timeout=200)
        except usb.core.USBError:
            raise ConnectionError
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
    def __init__(self, index=-1, bus=-1, address=-1, serial=-1, chipv=-1, state_listener=None):
        if state_listener is None:
            self.state_listener = lambda code: None
        else:
            self.state_listener = state_listener
        self.driver = CH341LibusbDriver(state_listener=state_listener)
        self.driver_index = 0
        self.index = index
        self.bus = bus
        self.address = address
        self.serial = serial
        self.chipv = chipv
        self.driver_value = None
        self.state = None

    def set_status(self, code):
        self.state_listener(code)
        self.state = code

    def try_open(self, i):
        """Tries to open device at index, with given criteria"""
        self.driver_index = i
        val = self.driver.CH341OpenDevice(self.driver_index)
        self.driver_value = val
        if val == -1:
            self.driver_value = None
            self.set_status(STATE_CONNECTION_FAILED)
            raise ConnectionRefusedError  # No more devices.
        # There is a device.
        if self.chipv != -1:
            chipv = self.get_chip_version()
            if self.chipv != chipv:
                # Rejected.
                self.set_status(STATE_DEVICE_REJECTED)
                self.driver.CH341CloseDevice(self.driver_index)
                self.driver_value = val
                return -1
        if self.bus != -1:
            bus = self.driver.devices[val].bus
            if self.bus != bus:
                # Rejected.
                self.set_status(STATE_DEVICE_REJECTED)
                self.driver.CH341CloseDevice(self.driver_index)
                self.driver_value = val
                return -1
        if self.address != -1:
            address = self.driver.devices[val].bus
            if self.address != address:
                # Rejected
                self.set_status(STATE_DEVICE_REJECTED)
                self.driver.CH341CloseDevice(self.driver_index)
                self.driver_value = val
                return -1
        if self.serial != -1:
            pass  # No driver has a serial number.
        # The device passes our tests.
        return val

    def open(self):
        """
        Opens the driver for unknown criteria.
        """
        if self.driver_value is None:
            self.set_status(STATE_DRIVER_LIBUSB)
            self.set_status(STATE_CONNECTING)
            if self.index == -1:
                for i in range(0, 16):
                    if self.try_open(i) == 0:
                        break  # We have our driver.
            else:
                self.try_open(self.index)
            self.set_status(STATE_USB_CONNECTED)
            self.set_status(STATE_CH341_PARAMODE)
            try:
                self.driver.CH341InitParallel(self.driver_index, 1)  # 0x40, 177, 0x8800, 0, 0
                self.set_status(STATE_CH341_PARAMODE_SUCCESS)
            except ConnectionError:
                self.set_status(STATE_CH341_PARAMODE_FAIL)
                self.driver.CH341CloseDevice(self.driver_index)
                raise ConnectionRefusedError
            self.set_status(STATE_CONNECTED)

    def close(self):
        self.driver.CH341CloseDevice(self.driver_index)
        self.driver_value = None

    def write(self, packet):
        self.driver.CH341EppWriteData(self.driver_index, packet, len(packet))

    def get_status(self):
        return self.driver.CH341GetStatus(self.driver_index)

    def get_chip_version(self):
        return self.driver.CH341GetVerIC(self.driver_index)  # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)
