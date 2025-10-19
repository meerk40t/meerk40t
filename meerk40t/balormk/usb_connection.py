"""
Galvo USB Connection - LibUSB Backend

This module provides USB communication with Balor/JCZ galvo laser controllers using the
pyusb library with libusb backend. It serves as the traditional cross-platform connection
method and as a fallback for the DirectUSBConnection on Windows.

Architecture Overview:
=====================

The USBConnection class implements the complete USB device lifecycle management:
1. Device discovery via vendor/product ID enumeration
2. USB configuration and interface claiming
3. Kernel driver detachment (Linux/macOS)
4. Bulk endpoint read/write operations
5. Graceful cleanup and error recovery

Connection Hierarchy:
====================

This module is part of a multi-tier connection strategy:
- **Windows**: DirectUSBConnection → USBConnection (fallback)
- **Linux/macOS**: USBConnection (primary method)
- **All Platforms**: MockConnection (testing mode)

Technical Details:
==================

Device Identification:
    - Vendor ID: 0x9588 (JCZ Technologies)
    - Product ID: 0x9899 (Balor/EZCAD2 controllers)
    - Interface: USB Bulk endpoints
    - Write Endpoint: 0x02 (OUT)
    - Read Endpoint: 0x88 (IN)

Requirements:
    - Python package: pyusb (pip install pyusb)
    - System library: libusb-1.0 or libusb-win32
    - Windows: Requires Zadig driver replacement
    - Linux: Requires udev rules for device permissions
    - macOS: Native libusb support

Communication Protocol:
======================

Command Packets:
    - Single Command: 12 bytes (0xC) - Individual galvo operations
    - Batch Commands: 3072 bytes (0xC00) - Command list uploads
    - Timeout: 100ms per operation

Response Format:
    - Status Response: 8 bytes from READ_ENDPOINT
    - Contains device status, position, and error flags

Error Handling:
===============

The module implements robust error recovery:
- Automatic retry (up to 3 attempts) on communication failures
- Device reconnection on USB errors
- Graceful degradation with user notifications
- Platform-specific error messages and guidance

Interface Compatibility:
========================

This class provides the same interface as DirectUSBConnection for seamless switching:
- open(index) - Opens device connection
- close(index) - Closes device connection
- write(index, packet) - Sends command packet
- read(index) - Reads status response
- is_open(index) - Checks connection status
- bus(index) - Returns USB bus number
- address(index) - Returns USB device address

Usage Example:
==============

    from meerk40t.balormk.usb_connection import USBConnection
    
    # Create connection with logging channel
    connection = USBConnection(logging_channel)
    
    # Open device (first device = index 0)
    if connection.open(0) >= 0:
        # Send command packet
        command = struct.pack('<6H', cmd_id, p1, p2, p3, p4, p5)
        connection.write(0, command)
        
        # Read response
        status = connection.read(0)
        
        # Close when done
        connection.close(0)

Platform-Specific Notes:
========================

Windows:
    - Requires Zadig tool to replace manufacturer driver
    - Install libusb-win32 or WinUSB via Zadig
    - Cannot coexist with EzCAD2 using same driver
    - Alternative: Use DirectUSBConnection for native driver support

Linux:
    - Requires udev rules: /etc/udev/rules.d/99-galvo.rules
    - Rule format: SUBSYSTEM=="usb", ATTRS{idVendor}=="9588", MODE="0666"
    - Reload rules: sudo udevadm control --reload-rules
    - May require user in plugdev group

macOS:
    - Native libusb support via Homebrew
    - May require System Integrity Protection configuration
    - USB permissions typically work without additional setup

Integration:
============

This module integrates with the GalvoController through connection factory logic:
- Platform detection determines availability
- Automatic fallback from DirectUSBConnection on Windows
- Transparent operation for cross-platform compatibility
- Consistent error handling and logging

Author: MeerK40t Development Team
License: MIT
Version: 1.0.0
"""

import time

import usb.core
import usb.util
from usb.backend.libusb1 import LIBUSB_ERROR_ACCESS, LIBUSB_ERROR_NOT_FOUND

USB_LOCK_VENDOR = 0x9588
USB_LOCK_PRODUCT = 0x9899

WRITE_ENDPOINT = 0x02  # usb.util.ENDPOINT_OUT|usb.util.ENDPOINT_TYPE_BULK
READ_ENDPOINT = 0x88

# DEBUG CODE FOR POINTING TO CH341A chip.
# USB_LOCK_VENDOR = 0x1A86  # Dev : (1a86) QinHeng Electronics
# USB_LOCK_PRODUCT = 0x5512  # (5512) CH341A
# WRITE_ENDPOINT = 0x02  # usb.util.ENDPOINT_OUT|usb.util.ENDPOINT_TYPE_BULK
# READ_ENDPOINT = 0x82


class USBConnection:
    """
    LibUSB-based USB connection for Balor/JCZ galvo laser controllers.
    
    This class provides cross-platform USB communication using pyusb and libusb.
    It handles device discovery, interface management, and bulk transfer operations
    with automatic error recovery.
    
    Attributes:
        channel: Logging channel for user communication
        devices (dict): Device objects indexed by machine index
        interface (dict): USB interface objects indexed by machine index
        backend_error_code: Last libusb error code for diagnostics
        timeout (int): USB transfer timeout in milliseconds (default: 100)
        is_direct_connection (bool): Always False (identifies connection type)
    
    Connection Lifecycle:
        1. find_device() - Enumerate USB devices by VID/PID
        2. set_config() - Set USB configuration
        3. get_active_config() - Get active interface
        4. detach_kernel() - Detach kernel driver (Linux/macOS)
        5. claim_interface() - Claim USB interface
        6. write()/read() - Perform bulk transfers
        7. unclaim_interface() - Release USB interface
        8. disconnect_detach() - Reattach kernel driver
        9. disconnect_dispose() - Dispose USB resources
        10. disconnect_reset() - Reset USB device
    
    Error Handling:
        - ConnectionRefusedError: Device not found or access denied
        - PermissionError: OS-level USB access denied
        - ConnectionError: Communication failure during operation
        - USBError: Low-level libusb errors with backend_error_code set
    """
    
    def __init__(self, channel):
        """
        Initialize USB connection manager.
        
        Args:
            channel: Logging channel for status messages and user feedback.
                    Must implement __call__ for message output and have
                    a _ attribute for translation function.
        """
        self.channel = channel
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 100
        self.is_direct_connection = False  # Flag to identify connection type

    def find_device(self, index=0):
        """
        Find and enumerate Balor/JCZ galvo devices via libusb.
        
        Searches for USB devices matching the Balor vendor/product ID and
        returns the device at the specified index. Provides detailed logging
        of discovered devices and platform-specific error guidance.
        
        Args:
            index (int): Device index to return (0 for first device, 1 for second, etc.)
        
        Returns:
            usb.core.Device: USB device object for the requested index
        
        Raises:
            ConnectionRefusedError: No devices found or index out of range
            PermissionError: OS denies USB access permissions
            
        Technical Details:
            - Searches for VID 0x9588, PID 0x9899 (JCZ Controllers)
            - Uses pyusb find() with find_all=True for multi-device support
            - Logs all discovered devices before returning requested one
            - Sets backend_error_code for diagnostic purposes
            
        Platform-Specific Errors:
            - LIBUSB_ERROR_ACCESS: Permissions issue (Linux udev, macOS SIP)
            - LIBUSB_ERROR_NOT_FOUND: Device in use by another process
            - Other errors: Device criteria mismatch or hardware issues
        """
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
            self.channel(_("Galvo device detected:"))
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
                        "Galvo devices were found. But something else was connected to them."
                    )
                )
            else:
                self.channel(
                    _(
                        "Galvo devices were found but they were rejected by device criteria in Controller."
                    )
                )
            raise ConnectionRefusedError
        return device

    def detach_kernel(self, device, interface):
        _ = self.channel._
        try:
            if device.is_kernel_driver_active(interface.bInterfaceNumber):
                # TODO: This can raise USBError on entity not found.
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
        """
        Open USB connection to Balor/JCZ device.
        
        Performs the complete USB device initialization sequence:
        1. Find device by index via libusb enumeration
        2. Set USB configuration (typically config 1)
        3. Get active interface (interface 0, alternate setting 0)
        4. Detach kernel driver if active (Linux/macOS only)
        5. Claim USB interface for exclusive access
        6. Handle interface conflicts with automatic retry
        
        Args:
            index (int): Device index to open (0 for first device)
        
        Returns:
            int: Device index on success (>=0)
                 -1 on connection failure
                 -2 on missing libusb backend
        
        Connection Sequence Details:
            - Device Configuration: Activates default USB configuration
            - Interface Claiming: Exclusive control required for bulk transfers
            - Kernel Driver Management: Detaches on Linux/macOS (if active)
            - Retry Logic: Automatic unclaim/claim cycle on conflict
        
        Platform-Specific Behavior:
            Windows:
                - Requires Zadig driver replacement (libusb-win32 or WinUSB)
                - NoBackendError triggers Zadig installation guidance
                - Cannot coexist with manufacturer driver
            
            Linux:
                - Kernel driver detachment may be required
                - udev rules needed for non-root access
                - Automatic permission elevation not supported
            
            macOS:
                - Native libusb support via Homebrew
                - Kernel driver detachment typically not needed
                - May require SIP configuration for some operations
        
        Error Handling:
            - NoBackendError: Missing libusb library (returns -2)
            - ConnectionRefusedError: Device unavailable or access denied (returns -1)
            - USBError: Recoverable errors trigger automatic retry
        
        Side Effects:
            - Stores device object in self.devices[index]
            - Stores interface object in self.interface[index]
            - Sets backend_error_code on libusb errors
            - Logs status messages to self.channel
        """
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
            from platform import system

            osname = system()
            if osname == "Windows":
                self.channel(
                    _(
                        "Did you install the libusb driver via Zadig (https://zadig.akeo.ie/)?"
                    )
                )
                self.channel(
                    _(
                        "Consult the wiki: https://github.com/meerk40t/meerk40t/wiki/Install%3A-Windows"
                    )
                )
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

    def write(self, index=0, packet=None, attempt=0):
        """
        Write command packet to galvo device via USB bulk transfer.
        
        Sends command data to the device's write endpoint (0x02) using USB bulk
        transfer. Implements automatic retry with reconnection on communication failures.
        
        Args:
            index (int): Device index to write to (default: 0)
            packet (bytes): Command data to send
                - 12 bytes (0xC): Single command packet
                - 3072 bytes (0xC00): Batch command list
            attempt (int): Internal retry counter (default: 0)
        
        Packet Format:
            Single Command (12 bytes):
                [cmd_id:2][param1:4][param2:4][param3:2]
                - Command ID: 16-bit operation code
                - Parameters: Operation-specific data
            
            Batch Commands (3072 bytes):
                256 × 12-byte commands for efficient bulk operations
        
        Error Recovery:
            - Automatic retry up to 3 times on USBError
            - Device reconnection between retries
            - 1-second delay on reconnection failure
            - Raises ConnectionError after exhausting retries
        
        Raises:
            ConnectionError: Device not connected or communication failed
            AssertionError: Invalid packet length (not 12 or 3072 bytes)
            USBError: USB communication error after all retries
        
        Technical Details:
            - Endpoint: 0x02 (BULK OUT)
            - Timeout: 100ms (self.timeout)
            - Transfer Type: Synchronous bulk transfer
            - Backend errors stored in backend_error_code
        """
        packet_length = len(packet)
        assert packet_length == 0xC or packet_length == 0xC00
        if packet is not None:
            try:
                # endpoint, data, timeout
                self.devices[index].write(
                    endpoint=WRITE_ENDPOINT, data=packet, timeout=self.timeout
                )
            except usb.core.USBError as e:
                if attempt <= 3:
                    try:
                        self.close(index)
                        self.open(index)
                    except ConnectionError:
                        time.sleep(1)
                    self.write(index, packet, attempt + 1)
                    return
                self.backend_error_code = e.backend_error_code

                self.channel(str(e))
                raise ConnectionError
            except KeyError:
                raise ConnectionError("Not Connected.")

    def read(self, index=0, attempt=0):
        """
        Read status response from galvo device via USB bulk transfer.
        
        Reads an 8-byte status packet from the device's read endpoint (0x88)
        using USB bulk transfer. Implements automatic retry with reconnection
        on communication failures.
        
        Args:
            index (int): Device index to read from (default: 0)
            attempt (int): Internal retry counter (default: 0)
        
        Returns:
            bytes: 8-byte status response containing:
                - Device status flags (ready, busy, error states)
                - Current position coordinates
                - Error codes and hardware state
        
        Response Format (8 bytes):
            [status:1][flags:1][x_pos:2][y_pos:2][reserved:2]
            - Status byte: READY (0x20), BUSY (0x04), AXIS (0x40)
            - Position data: Current galvo mirror coordinates
            - Error flags: Hardware-specific error indicators
        
        Error Recovery:
            - Automatic retry up to 3 times on USBError
            - Device reconnection between retries
            - 1-second delay on reconnection failure
            - Raises ConnectionError after exhausting retries
        
        Raises:
            ConnectionError: Device not connected or communication failed
            USBError: USB communication error after all retries
        
        Technical Details:
            - Endpoint: 0x88 (BULK IN)
            - Buffer Size: 8 bytes (fixed)
            - Timeout: 100ms (self.timeout)
            - Transfer Type: Synchronous bulk transfer
            - Backend errors stored in backend_error_code
        
        Usage Pattern:
            Typically called after write() to verify command execution:
            
            connection.write(0, command_packet)
            status = connection.read(0)
            if status[0] & 0x20:  # Check READY flag
                # Command completed successfully
        """
        try:
            return self.devices[index].read(
                endpoint=READ_ENDPOINT, size_or_buffer=8, timeout=self.timeout
            )
        except usb.core.USBError as e:
            if attempt <= 3:
                try:
                    self.close(index)
                    self.open(index)
                except ConnectionError:
                    time.sleep(1)
                return self.read(index, attempt + 1)
            self.backend_error_code = e.backend_error_code

            self.channel(str(e))
            raise ConnectionError
        except KeyError:
            raise ConnectionError("Not Connected.")
