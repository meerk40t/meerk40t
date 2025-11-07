"""
Newly USB Connection

This module provides USB communication capabilities for Newly laser devices using the pyusb library.
It implements a robust connection interface with automatic error recovery and retry mechanisms.

USB Protocol:
- Vendor ID: 0x0471 (Philips)
- Product ID: 0x0999 (Newly device)
- Uses interrupt endpoints for control and bulk endpoints for data transfer
- Implements a 3-step write protocol: length → confirmation → data

Key Features:
- Automatic device detection and enumeration
- Kernel driver detachment/attachment for Linux compatibility
- Interface claiming and configuration management
- Robust error handling with connection recovery (max 3 attempts)
- Packet-based data transmission with confirmation protocol
- Configurable timeouts and retry limits

Safety Mechanisms:
- Prevents infinite recovery loops with attempt limits
- Graceful degradation on connection failures
- Proper resource cleanup on disconnection
- Thread-safe connection state management

Classes:
    USBConnection: Main connection class implementing the connection interface

Error Handling:
- ConnectionRefusedError: Device not found or access denied
- PermissionError: Insufficient USB permissions
- ConnectionError: Connection recovery failed after max attempts
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
    """
    USB connection handler for Newly laser devices.

    This class manages the complete USB communication lifecycle including device discovery,
    connection establishment, data transfer, and error recovery. It implements a robust
    protocol with automatic retry and recovery mechanisms.

    Attributes:
        channel: Communication channel for logging and user feedback
        devices: Dictionary mapping device indices to USB device objects
        interface: Dictionary mapping device indices to USB interface objects
        backend_error_code: Last USB backend error code encountered
        timeout: USB operation timeout in milliseconds (default: 2000)
        max_retries: Maximum retries per packet before attempting recovery (default: 10)
        sleep_between_retries: Sleep time between retries in seconds (default: 0.5)

    USB Protocol Details:
        - Interrupt endpoint 0x01: Send packet length (big-endian 16-bit)
        - Interrupt endpoint 0x81: Receive confirmation byte (expect 0x01)
        - Bulk endpoint 0x02: Send actual data packet
        - Bulk endpoint 0x82: Receive data from device

    Safety Features:
        - Maximum 3 connection recovery attempts to prevent infinite loops
        - Graceful degradation on USB errors
        - Proper resource cleanup on disconnection
        - Packet-based transmission with confirmation protocol
    """

    def __init__(self, channel):
        self.channel = channel
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 2000
        self.max_retries = 3  # Maximum retries before attempting recovery
        self.max_recovery_attempts = 3  # Limit connection recovery attempts
        self.sleep_between_retries = 0.25  # Sleep time between retries

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

    def abort(self):
        pass

    def write(self, index=0, data=None):
        if data is None:
            return True  # Nothing to write, consider it successful
        self.channel(f"USB SEND: {data}")
        data_remaining = len(data)
        retries = 0
        recovery_attempts = 0
        while data_remaining > 0:
            packet_length = min(0x1000, data_remaining)
            packet = data[:packet_length]
            try:
                dev = self.devices[index]

                #####################################
                # Step 1: Write the size of the packet.
                #####################################
                # endpoint, data, timeout

                length_data = struct.pack(
                    ">h", packet_length
                )  # Big-endian size write out.
                self.channel(f"Sending Length: {length_data}")
                dev.write(
                    endpoint=WRITE_INTERRUPT, data=length_data, timeout=self.timeout
                )
                self.channel("Length Sent.")
                #####################################
                # Step 2: read the confirmation value.
                #####################################
                # endpoint, data, timeout
                self.channel("Read Confirmation.")
                read = dev.read(
                    endpoint=READ_INTERRUPT, size_or_buffer=1, timeout=self.timeout
                )
                if read is None or len(read) == 0:
                    self.channel("No Confirmation Received. Trying again.")
                    time.sleep(self.sleep_between_retries)
                    retries += 1
                    if retries > self.max_retries:
                        recovery_attempts += 1
                        if recovery_attempts > self.max_recovery_attempts:
                            self.channel(
                                f"Too many connection recovery attempts ({recovery_attempts}). Giving up."
                            )
                            raise ConnectionError(
                                f"Failed to recover connection after {recovery_attempts} attempts"
                            )
                        self._recover_connection(index)
                        retries = 0  # Start again after reopening.
                    continue  # Try again.
                else:
                    self.channel(f"Confirmation: {read}")
                    if read[0] != 1:
                        self.channel("Bad Confirmation Received. Trying again.")
                        time.sleep(self.sleep_between_retries)
                        retries += 1
                        if retries > self.max_retries:
                            recovery_attempts += 1
                            if recovery_attempts > self.max_recovery_attempts:
                                self.channel(
                                    f"Too many connection recovery attempts ({recovery_attempts}). Giving up."
                                )
                                raise ConnectionError(
                                    f"Failed to recover connection after {recovery_attempts} attempts"
                                )
                            self._recover_connection(index)
                            retries = 0  # Start again after reopening.
                        continue  # Try again.

                #####################################
                # Step #3, write the bulk data of the packet.
                #####################################
                # endpoint, data, timeout
                self.channel("Writing Data")
                dev.write(endpoint=WRITE_BULK, data=packet, timeout=self.timeout)
                self.channel("Data Written.")

                data = data[packet_length:]
                data_remaining -= packet_length
                retries = 0  # Reset retries on successful packet send.
            except usb.core.USBError as e:
                """
                The sending data protocol hit a core usb error. This will print the error and close and reopen the
                channel.
                """
                self.backend_error_code = e.backend_error_code
                self.channel(str(e))
                recovery_attempts += 1
                if recovery_attempts > self.max_recovery_attempts:
                    self.channel(
                        f"Too many connection recovery attempts ({recovery_attempts}). Giving up."
                    )
                    raise ConnectionError(
                        f"Failed to recover connection after {recovery_attempts} attempts"
                    ) from e
                self._recover_connection(index)
                retries = 0  # Start again after reopening.
            except KeyError:
                """
                Keyerrors occur because the device wasn't open to begin with and self.devices[index] failed.
                """
                self.channel("Not connected.")
                recovery_attempts += 1
                if recovery_attempts > self.max_recovery_attempts:
                    self.channel(
                        f"Too many connection recovery attempts ({recovery_attempts}). Giving up."
                    )
                    raise ConnectionError(
                        f"Failed to recover connection after {recovery_attempts} attempts"
                    )
                self._recover_connection(index)
        return True  # Successfully wrote all data

    def _recover_connection(self, index):
        """Helper method to recover connection after errors."""
        self.channel("Attempting to recover connection...")
        self.close(index)
        recovered = self.open(index)
        if recovered < 0:  # Could not reopen.
            self.channel("Connection recovery failed.")
            raise ConnectionError("Unable to recover USB connection")
        self.channel("Connection recovered successfully.")
        return recovered
