import usb.core
import usb.util
from usb.backend.libusb1 import LIBUSB_ERROR_ACCESS, LIBUSB_ERROR_NOT_FOUND

STATUS_NO_DEVICE = -1
USB_LOCK_VENDOR = 0x1A86  # Dev : (1a86) QinHeng Electronics
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


def convert_to_list_bytes(data):
    if isinstance(data, str):  # python 2
        return [ord(e) for e in data]
    else:
        return [e for e in data]


class Ch341LibusbDriver:
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

    def __init__(self, channel):
        self.devices = {}
        self.interface = {}
        self.channel = channel
        self.backend_error_code = None
        self.timeout = 500

    def find_device(self, index=0):
        _ = self.channel._
        self.channel(_("Using LibUSB to connect."))
        self.channel(_("Finding devices."))
        try:
            devices = list(
                usb.core.find(
                    idVendor=USB_LOCK_VENDOR, idProduct=USB_LOCK_PRODUCT, find_all=True
                )
            )
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            raise ConnectionRefusedError
        if len(devices) == 0:
            self.channel(_("Devices Not Found."))
            raise ConnectionRefusedError
        for d in devices:
            self.channel(_("K40 device detected:"))
            string = str(d)
            string = string.replace("\n", "\n\t")
            self.channel(string)
        try:
            device = devices[index]
        except IndexError:
            if self.backend_error_code == LIBUSB_ERROR_ACCESS:
                self.channel(_("Your OS does not give you permissions to access USB."))
                raise PermissionError
            elif self.backend_error_code == LIBUSB_ERROR_NOT_FOUND:
                self.channel(
                    _(
                        "K40 devices were found. But something else was connected to them."
                    )
                )
            else:
                self.channel(
                    _(
                        "K40 devices were found but they were rejected by device criteria in Controller."
                    )
                )
            raise ConnectionRefusedError
        return device

    def detach_kernel(self, device, interface):
        _ = self.channel._
        try:
            if device.is_kernel_driver_active(interface.bInterfaceNumber):
                try:
                    self.channel(_("Attempting to detach kernel."))
                    device.detach_kernel_driver(interface.bInterfaceNumber)
                    self.channel(_("Kernel detach: Success."))
                except usb.core.USBError as e:
                    self.backend_error_code = e.backend_error_code

                    self.channel(str(e))
                    self.channel(_("Kernel detach: Failed."))
                    raise ConnectionRefusedError
        except NotImplementedError:
            self.channel(
                _("Kernel detach: Not Implemented.")
            )  # Driver does not permit kernel detaching.
            # Non-fatal error.

    def get_active_config(self, device):
        _ = self.channel._
        self.channel(_("Getting Active Config"))
        try:
            interface = device.get_active_configuration()[(0, 0)]
            self.channel(_("Active Config: Success."))
            return interface
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            self.channel(_("Active Config: Failed."))
            raise ConnectionRefusedError

    def set_config(self, device):
        _ = self.channel._
        self.channel(_("Config Set"))
        try:
            device.set_configuration()
            self.channel(_("Config Set: Success"))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            self.channel(
                _(
                    "Config Set: Fail\n(Hint: may recover if you change where the USB is plugged in.)"
                )
            )
            # raise ConnectionRefusedError

    def claim_interface(self, device, interface):
        _ = self.channel._
        try:
            self.channel(_("Attempting to claim interface."))
            usb.util.claim_interface(device, interface)
            self.channel(_("Interface claim: Success"))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            self.channel(_("Interface claim: Failed. (Interface is in use.)"))
            raise ConnectionRefusedError
            # Already in use. This is critical.

    def disconnect_detach(self, device, interface):
        _ = self.channel._
        try:
            self.channel(_("Attempting kernel attach"))
            device.attach_kernel_driver(interface.bInterfaceNumber)
            self.channel(_("Kernel attach: Success."))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            self.channel(_("Kernel attach: Fail."))
            # Continue and hope it is non-critical.
        except NotImplementedError:
            self.channel(_("Kernel attach: Fail."))

    def unclaim_interface(self, device, interface):
        _ = self.channel._
        try:
            self.channel(_("Attempting to release interface."))
            usb.util.release_interface(device, interface)
            self.channel(_("Interface released."))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            self.channel(_("Interface did not exist."))

    def disconnect_dispose(self, device):
        _ = self.channel._
        try:
            self.channel(_("Attempting to dispose resources."))
            usb.util.dispose_resources(device)
            self.channel(_("Dispose Resources: Success"))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            self.channel(_("Dispose Resources: Fail"))

    def disconnect_reset(self, device):
        _ = self.channel._
        try:
            self.channel(_("Attempting USB reset."))
            device.reset()
            self.channel(_("USB connection reset."))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            self.channel(_("USB connection did not exist."))

    def bus(self, index):
        return self.devices[index].bus

    def address(self, index):
        return self.devices[index].address

    def CH341OpenDevice(self, index=0):
        """Opens device, returns index."""
        _ = self.channel._
        self.channel(_("Attempting connection to USB."))
        try:
            device = self.find_device(index)
            self.devices[index] = device
            self.set_config(device)
            interface = self.get_active_config(device)
            self.interface[index] = interface

            self.detach_kernel(device, interface)
            try:
                self.claim_interface(device, interface)
            except ConnectionRefusedError:
                # Attempting interface cycle.
                self.unclaim_interface(device, interface)
                self.claim_interface(device, interface)
            self.channel(_("USB Connected."))
            return index
        except usb.core.NoBackendError as e:
            self.channel(str(e))
            self.channel(_("PyUsb detected no backend LibUSB driver."))
            return -2
        except ConnectionRefusedError:
            self.channel(_("Connection to USB failed.\n"))
            return -1

    def CH341CloseDevice(self, index=0):
        """Closes device."""
        _ = self.channel._
        device = self.devices[index]
        interface = self.interface[index]
        self.channel(_("Attempting disconnection from USB."))
        if device is not None:
            try:
                self.disconnect_detach(device, interface)
                self.unclaim_interface(device, interface)
                self.disconnect_dispose(device)
                self.disconnect_reset(device)
                self.channel(_("USB Disconnection Successful.\n"))
            except ConnectionError:
                pass

    def CH341InitParallel(
        self, index=0, mode=CH341_PARA_MODE_EPP19
    ):  # Mode 1, we need EPP 1.9
        """Permits setting a mode, but our mode is only 1 since the device is using
        EPP 1.9. This is a control transfer event."""
        device = self.devices[index]
        value = mode << 8
        if mode < 256:
            value |= 2
        try:
            device.ctrl_transfer(
                bmRequestType=mCH341_VENDOR_WRITE,
                bRequest=mCH341_PARA_INIT,
                wValue=value,
                wIndex=0,
                data_or_wLength=0,
                timeout=self.timeout,
            )
            # 0x40, 177, 0x8800, 0, 0
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            # Device was not found. Timed out, etc.
            raise ConnectionError

    def CH341SetParaMode(self, index, mode=CH341_PARA_MODE_EPP19):
        device = self.devices[index]
        value = 0x2525
        try:
            device.ctrl_transfer(
                bmRequestType=mCH341_VENDOR_WRITE,
                bRequest=mCH341_SET_PARA_MODE,
                wValue=value,
                wIndex=index,
                data_or_wLength=mode << 8 | mode,
                timeout=self.timeout,
            )
            # 0x40, 154, 0x2525, 257, 0
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
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
                    # endpoint, data, timeout
                    device.write(
                        endpoint=BULK_WRITE_ENDPOINT, data=packet, timeout=self.timeout
                    )
                except usb.core.USBError as e:
                    self.backend_error_code = e.backend_error_code

                    self.channel(str(e))
                    raise ConnectionError

    def CH341EppRead(self, index=0, buffer=None, length=0, pipe=0):
        try:
            return self.devices[index].read(
                endpoint=BULK_READ_ENDPOINT, size_or_buffer=length, timeout=self.timeout
            )
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            raise ConnectionError

    # pylint: disable=dangerous-default-value
    def CH341GetStatus(self, index=0, status=[0]):
        """D7-0, 8: err, 9: pEmp, 10: Int, 11: SLCT, 12: SDA, 13: Busy, 14: datas, 15: addrs"""
        device = self.devices[index]
        try:
            device.write(
                endpoint=BULK_WRITE_ENDPOINT,
                data=[mCH341_PARA_CMD_STS],
                timeout=self.timeout,
            )
            # read(self, endpoint, size_or_buffer, timeout = None)
            status[0] = device.read(
                endpoint=BULK_READ_ENDPOINT, size_or_buffer=6, timeout=self.timeout
            )
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            raise ConnectionError
        return status[0]
        # 48, reads 0xc0, 95, 0, 0 (30,00? = 48)

    def CH341GetVerIC(self, index=0):
        device = self.devices[index]
        try:
            buffer = device.ctrl_transfer(
                bmRequestType=mCH341_VENDOR_READ,
                bRequest=mCH341A_GET_VER,
                wValue=0,
                wIndex=0,
                data_or_wLength=2,
                timeout=self.timeout,
            )
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            raise ConnectionError
        if len(buffer) < 0:
            return 2
        else:
            return (buffer[1] << 8) | buffer[0]

    def CH341EppReadData(
        self, index=0, buffer=None, length=0
    ):  # WR=1, DS=0, AS=1, D0-D7 in
        self.CH341EppRead(index, buffer, length, 0)

    def CH341EppReadAddr(
        self, index=0, buffer=None, length=0
    ):  # WR=1, DS=0, AS=1 D0-D7 in
        self.CH341EppRead(index, buffer, length, 1)

    def CH341EppWriteData(
        self, index, buffer=None, length=0
    ):  # WR=0, DS=0, AS=1, D0-D7 out
        self.CH341EppWrite(index, buffer, length, 0)

    def CH341EppWriteAddr(
        self, index, buffer=None, length=0
    ):  # WR=0, DS=1, AS=0, D0-D7 out
        self.CH341EppWrite(index, buffer, length, 1)
