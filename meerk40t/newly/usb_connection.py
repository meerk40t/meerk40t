"""
Newly USB Connection

Performs the required interactions with the Newly backend through pyusb and libusb.
"""
import struct
import time

import usb.core
import usb.util
from usb.backend.libusb1 import LIBUSB_ERROR_ACCESS, LIBUSB_ERROR_NOT_FOUND

USB_LOCK_VENDOR = 0x0471
USB_LOCK_PRODUCT = 0x0999

WRITE_INTERRUPT = 0x01  # Is sent the size of the bulk data
READ_INTERRUPT = 0x81  # Reads 0x01 for OK

WRITE_BULK = 0x02  # Is sent entire big packet.
READ_BULK = 0x82


class USBConnection:
    def __init__(self, channel):
        self.channel = channel
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 100

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
            self.channel(_("Newly device detected:"))
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
                        "Newly devices were found. But something else was connected to them."
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

    def is_open(self, index=0):
        try:
            dev = self.devices[index]
            if dev:
                return True
        except KeyError:
            pass
        return False

    def open(self, index=0):
        """Opens device, returns index."""
        _ = self.channel._
        self.channel(_("Attempting connection to USB."))
        try:
            device = self.find_device(index)
            self.devices[index] = device
            self.set_config(device)
            try:
                interface = self.get_active_config(device)
                self.interface[index] = interface
                self.detach_kernel(device, interface)
                try:
                    self.claim_interface(device, interface)
                except ConnectionRefusedError:
                    # Attempting interface cycle.
                    self.unclaim_interface(device, interface)
                    self.claim_interface(device, interface)
            except usb.core.USBError:
                self.channel(_("Device failed during detach and claim"))
            self.channel(_("USB Connected."))
            return index
        except usb.core.NoBackendError as e:
            self.channel(str(e))
            self.channel(_("PyUsb detected no backend LibUSB driver."))
            return -2
        except ConnectionRefusedError:
            self.channel(_("Connection to USB failed.\n"))
            return -1

    def close(self, index=0):
        """Closes device."""
        _ = self.channel._
        device = self.devices.get(index)
        self.channel(_("Attempting disconnection from USB."))
        if device is not None:
            interface = self.interface.get(index)
            try:
                if interface is not None:
                    self.disconnect_detach(device, interface)
                    self.unclaim_interface(device, interface)
                self.disconnect_dispose(device)
                self.disconnect_reset(device)
                self.channel(_("USB Disconnection Successful.\n"))
                del self.devices[index]
            except ConnectionError:
                pass

    def _read_confirmation(self, index=0, attempt=0):
        try:
            # endpoint, data, timeout
            read = self.devices[index].read(
                endpoint=READ_INTERRUPT, size_or_buffer=1, timeout=self.timeout
            )

        except usb.core.USBError as e:
            if attempt <= 3:
                try:
                    self.close(index)
                    self.open(index)
                except ConnectionError:
                    time.sleep(1)
                self._read_confirmation(index=index, attempt=attempt + 1)
                return
            self.backend_error_code = e.backend_error_code
            self.channel(str(e))
            raise ConnectionError
        except KeyError:
            raise ConnectionError("Not Connected.")

    def _write_packet_size(self, index=0, packet=None, attempt=0):
        packet_length = len(packet)
        try:
            # endpoint, data, timeout
            length_data = struct.pack(">h", packet_length)  # Big-endian size write out.
            self.devices[index].write(
                endpoint=WRITE_INTERRUPT, data=length_data, timeout=self.timeout
            )
        except usb.core.USBError as e:
            if attempt <= 3:
                try:
                    self.close(index)
                    self.open(index)
                except ConnectionError:
                    time.sleep(1)
                self._write_packet_size(index, packet, attempt + 1)
                return
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            raise ConnectionError
        except KeyError:
            raise ConnectionError("Not Connected.")

    def _write_bulk(self, index=0, packet=None, attempt=0):
        try:
            # endpoint, data, timeout
            self.devices[index].write(
                endpoint=WRITE_BULK, data=packet, timeout=self.timeout
            )
        except usb.core.USBError as e:
            if attempt <= 3:
                try:
                    self.close(index)
                    self.open(index)
                except ConnectionError:
                    time.sleep(1)
                self._write_bulk(index, packet, attempt + 1)
                return
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            raise ConnectionError
        except KeyError:
            raise ConnectionError("Not Connected.")

    def abort(self):
        pass

    def write(self, index=0, packet=None, attempt=0):
        packet_length = len(packet)
        assert packet_length <= 0xFFFF
        if packet is not None:
            #####################################
            # Step 1: Write the size of the packet.
            #####################################
            self._write_packet_size(index=index, packet=packet)

            #####################################
            # Step 2: read the confirmation value.
            #####################################
            self._read_confirmation(index=index)

            #####################################
            # Step #3, write the bulk data of the packet.
            #####################################
            self._write_bulk(index=index, packet=packet)
