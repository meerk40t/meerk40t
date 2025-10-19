"""
Balor USB Communication - Dual Mode Driver

This module provides communication with Balor laser devices via:
1. Windows Native Driver (Lmcv4u.sys) - Works alongside EzCAD2
2. libusb Backend - Requires Zadig driver replacement

The module automatically selects the appropriate method based on what's available.
"""

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Optional

# USB Device IDs
USB_LOCK_VENDOR = 0x9588
USB_LOCK_PRODUCT = 0x9899

# Endpoints
WRITE_ENDPOINT = 0x02
READ_ENDPOINT = 0x88

# ============================================================================
# WINDOWS NATIVE API DEFINITIONS
# ============================================================================

kernel32 = ctypes.windll.kernel32
SetupAPI = ctypes.windll.setupapi

# Device I/O Control Codes for USB
IOCTL_USB_GET_NODE_CONNECTION_INFORMATION = 0x220400
IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION = 0x220410
IOCTL_USB_GET_NODE_CONNECTION_ATTRIBUTES = 0x220408

# Generic I/O Control Codes
FILE_DEVICE_UNKNOWN = 0x00000022
IOCTL_GENERIC_READ = (FILE_DEVICE_UNKNOWN << 16) | (0x0001 << 2) | 3
IOCTL_GENERIC_WRITE = (FILE_DEVICE_UNKNOWN << 16) | (0x0001 << 2) | 3

# File I/O Constants
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_FLAG_OVERLAPPED = 0x40000000
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
INVALID_HANDLE_VALUE = -1

# Setup API Constants
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010

# USB pipe direction
USB_DIR_IN = 0x80
USB_DIR_OUT = 0x00

# Pipe types
USB_ENDPOINT_TYPE_BULK = 0x02


class USB_DEVICE_DESCRIPTOR(ctypes.Structure):
    _fields_ = [
        ("bLength", wintypes.BYTE),
        ("bDescriptorType", wintypes.BYTE),
        ("bcdUSB", wintypes.WORD),
        ("bDeviceClass", wintypes.BYTE),
        ("bDeviceSubClass", wintypes.BYTE),
        ("bDeviceProtocol", wintypes.BYTE),
        ("bMaxPacketSize0", wintypes.BYTE),
        ("idVendor", wintypes.WORD),
        ("idProduct", wintypes.WORD),
        ("bcdDevice", wintypes.WORD),
        ("iManufacturer", wintypes.BYTE),
        ("iProduct", wintypes.BYTE),
        ("iSerialNumber", wintypes.BYTE),
        ("bNumConfigurations", wintypes.BYTE),
    ]


# ============================================================================
# WINDOWS NATIVE USB COMMUNICATION
# ============================================================================


class WindowsNativeUSBConnection:
    """
    Communicates with Balor device via Windows native Lmcv4u.sys driver.
    This allows EzCAD2 and MeerK40t to coexist on the same system.
    """

    def __init__(self, channel):
        self.channel = channel
        self.devices = {}  # device_handle indexed by machine_index
        self.timeout = 100  # milliseconds
        self.backend_error_code = None
        self._lock = threading.RLock()

    def find_device_path(self) -> Optional[str]:
        r"""
        Locate the Balor device symbolic link in Windows registry.
        Returns the device path (e.g., \\?\USB#VID_9588&PID_9899#20200507#...)
        """
        _ = self.channel._
        self.channel(_("Searching for Balor device in Windows registry..."))

        try:
            import winreg

            # Search USB device registry
            usb_key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Enum\USB",
            )

            # Look for VID_9588&PID_9899
            try:
                device_subkey = winreg.OpenKey(usb_key, f"VID_{USB_LOCK_VENDOR:04X}&PID_{USB_LOCK_PRODUCT:04X}")
            except FileNotFoundError:
                self.channel(_("Device not found in USB registry"))
                return None

            # Get the device instance ID
            try:
                subkey_names = winreg.QueryInfoKey(device_subkey)[0]
                if subkey_names == 0:
                    self.channel(_("No device instances found"))
                    return None

                instance_id = winreg.EnumKey(device_subkey, 0)
                self.channel(_(f"Device instance: {instance_id}"))
            except Exception as e:
                self.channel(_(f"Error reading device instance: {e}"))
                return None

            # Get device properties
            try:
                instance_key = winreg.OpenKey(
                    device_subkey, instance_id
                )
                # The device path is typically in the symbolic links
                device_path = None

                # Try to construct the path from known device interface GUIDs
                # GUID_DEVINTERFACE_USB_DEVICE
                try:
                    dev_key = winreg.OpenKey(
                        instance_key,
                        r"Device Parameters"
                    )
                    device_path = winreg.QueryValueEx(dev_key, "DevicePath")[0]
                except Exception:
                    pass

                if not device_path:
                    # Construct device path from instance ID
                    device_path = f"\\\\?\\USB#{USB_LOCK_VENDOR:04X}_{USB_LOCK_PRODUCT:04X}#{instance_id}"

                self.channel(_(f"Device path: {device_path}"))
                return device_path

            except Exception as e:
                self.channel(_(f"Error reading device path: {e}"))
                return None

        except Exception as e:
            self.channel(_(f"Registry search failed: {e}"))
            return None

    def find_device(self, index=0):
        """Find and open the Balor device."""
        _ = self.channel._

        device_path = self.find_device_path()
        if not device_path:
            self.channel(_("Balor device not found"))
            raise ConnectionRefusedError("Device not found")

        # Attempt to open the device
        try:
            device_handle = kernel32.CreateFileW(
                ctypes.c_wchar_p(device_path),
                GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OVERLAPPED,
                None,
            )

            if device_handle == INVALID_HANDLE_VALUE:
                error_code = kernel32.GetLastError()
                self.channel(_(f"Failed to open device. Error: {error_code}"))
                raise ConnectionRefusedError(f"CreateFileW failed with error {error_code}")

            self.channel(_("Device opened successfully via Windows driver"))
            return device_handle

        except Exception as e:
            self.channel(_(f"Error opening device: {e}"))
            raise ConnectionRefusedError(f"Failed to open device: {e}")

    def open(self, index=0):
        """Opens device connection."""
        _ = self.channel._
        self.channel(_("Attempting connection to USB via Windows native driver"))

        try:
            device_handle = self.find_device(index)
            self.devices[index] = device_handle
            self.channel(_("USB Connected via Windows driver"))
            return index
        except ConnectionRefusedError:
            self.channel(_("Connection to USB failed"))
            return -1
        except Exception as e:
            self.channel(_(f"Unexpected error: {e}"))
            return -1

    def close(self, index=0):
        """Closes device connection."""
        _ = self.channel._
        self.channel(_("Attempting disconnection from USB"))

        try:
            device_handle = self.devices.get(index)
            if device_handle is not None:
                kernel32.CloseHandle(ctypes.c_void_p(device_handle))
                del self.devices[index]
                self.channel(_("USB Disconnection Successful"))
        except Exception as e:
            self.channel(_(f"Error during disconnect: {e}"))

    def is_open(self, index=0):
        """Check if device is open."""
        return index in self.devices and self.devices[index] is not None

    def write(self, index=0, packet=None, attempt=0):
        """
        Write command packet to device.
        
        Args:
            index: Device index
            packet: Data to send (12 bytes for single command or 3072 bytes for batch)
            attempt: Retry counter
        """
        if packet is None:
            raise ValueError("Packet cannot be None")
            
        packet_length = len(packet)
        assert packet_length in (0xC, 0xC00), f"Invalid packet length: {packet_length}"

        if packet is None:
            raise ValueError("Packet cannot be None")

        try:
            device_handle = self.devices.get(index)
            if device_handle is None:
                raise ConnectionError("Device not connected")

            # Write to endpoint 0x02
            bytes_written = wintypes.DWORD()
            
            # Try direct write first
            result = kernel32.WriteFile(
                ctypes.c_void_p(device_handle),
                ctypes.c_char_p(packet),
                len(packet),
                ctypes.byref(bytes_written),
                None  # Synchronous I/O
            )

            if not result:
                error_code = kernel32.GetLastError()
                # Error code 1 = INVALID_FUNCTION (driver doesn't support this I/O method)
                # This is expected with Lmcv4u.sys - try alternative methods
                
                if error_code == 1 and attempt < 1:
                    # Try IOCTL_USB_GET_NODE_CONNECTION_INFORMATION first
                    return self._write_via_ioctl(index, packet, attempt)
                
                if attempt <= 3:
                    time.sleep(0.1)
                    try:
                        self.close(index)
                        self.open(index)
                    except ConnectionError:
                        time.sleep(1)
                    return self.write(index, packet, attempt + 1)
                
                raise ConnectionError(f"WriteFile failed with error {error_code}")

            if bytes_written.value != len(packet):
                raise ConnectionError(
                    f"WriteFile: Expected {len(packet)} bytes, got {bytes_written.value}"
                )

        except ConnectionError:
            raise
        except KeyError:
            raise ConnectionError("Not Connected.")
        except Exception as e:
            if attempt <= 3:
                time.sleep(0.1)
                try:
                    self.close(index)
                    self.open(index)
                except ConnectionError:
                    time.sleep(1)
                return self.write(index, packet, attempt + 1)
            raise ConnectionError(f"Write operation failed: {e}")

    def _write_via_ioctl(self, index, packet, attempt):
        """
        Alternative: Try writing via IOCTL if standard WriteFile fails.
        This is a fallback for driver compatibility.
        """
        try:
            device_handle = self.devices.get(index)
            if device_handle is None:
                raise ConnectionError("Device not connected")

            # Construct USB pipe handle for bulk out (0x02)
            # Format: pipe_type (2 bits) | direction (1 bit) | endpoint_address (5 bits)
            # out_pipe = (USB_ENDPOINT_TYPE_BULK << 6) | (USB_DIR_OUT) | WRITE_ENDPOINT

            output_buffer = wintypes.DWORD()
            bytes_returned = wintypes.DWORD()

            # Try USB-specific IOCTL
            result = kernel32.DeviceIoControl(
                ctypes.c_void_p(device_handle),
                IOCTL_USB_GET_NODE_CONNECTION_INFORMATION,
                ctypes.c_char_p(packet),
                len(packet),
                ctypes.byref(output_buffer),
                ctypes.sizeof(output_buffer),
                ctypes.byref(bytes_returned),
                None,
            )

            if not result:
                error_code = kernel32.GetLastError()
                if attempt <= 2:
                    time.sleep(0.1)
                    return self.write(index, packet, attempt + 1)
                raise ConnectionError(f"IOCTL write failed with error {error_code}")

        except Exception:
            if attempt <= 2:
                time.sleep(0.1)
                return self.write(index, packet, attempt + 1)
            raise

    def read(self, index=0, attempt=0):
        """
        Read status response from device (8 bytes from endpoint 0x88).
        
        Args:
            index: Device index
            attempt: Retry counter
            
        Returns:
            bytes: 8-byte status response
        """
        try:
            device_handle = self.devices.get(index)
            if device_handle is None:
                raise ConnectionError("Device not connected")

            # Read from endpoint 0x88 (8 bytes)
            read_buffer = ctypes.create_string_buffer(8)
            bytes_read = wintypes.DWORD()

            result = kernel32.ReadFile(
                ctypes.c_void_p(device_handle),
                read_buffer,
                8,
                ctypes.byref(bytes_read),
                None  # Synchronous I/O
            )

            if not result:
                error_code = kernel32.GetLastError()
                if attempt <= 3:
                    time.sleep(0.1)
                    try:
                        self.close(index)
                        self.open(index)
                    except ConnectionError:
                        time.sleep(1)
                    return self.read(index, attempt + 1)
                raise ConnectionError(f"ReadFile failed with error {error_code}")

            return read_buffer.raw[:bytes_read.value]

        except ConnectionError:
            raise
        except KeyError:
            raise ConnectionError("Not Connected.")
        except Exception as e:
            if attempt <= 3:
                time.sleep(0.1)
                try:
                    self.close(index)
                    self.open(index)
                except ConnectionError:
                    time.sleep(1)
                return self.read(index, attempt + 1)
            raise ConnectionError(f"Read operation failed: {e}")

    def bus(self, index):
        """Get USB bus number for device."""
        return 0  # Not readily available from Windows driver

    def address(self, index):
        """Get USB device address."""
        return 0  # Not readily available from Windows driver


# ============================================================================
# LIBUSB FALLBACK (Original Implementation)
# ============================================================================


class LibUSBConnection:
    """
    Original libusb-based communication (requires Zadig driver).
    Kept for backward compatibility and cross-platform support.
    """

    def __init__(self, channel):
        self.channel = channel
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 100
        self._usb_available = False
        self._check_usb_available()

    def _check_usb_available(self):
        """Check if pyusb and libusb are available."""
        try:
            import importlib.util
            self._usb_available = importlib.util.find_spec("usb") is not None
        except ImportError:
            self._usb_available = False

    def find_device(self, index=0):
        """Find Balor device via libusb."""
        _ = self.channel._
        if not self._usb_available:
            raise ImportError("PyUSB not available")

        import usb.core
        import usb.util  # noqa: F401
        from usb.backend.libusb1 import LIBUSB_ERROR_ACCESS, LIBUSB_ERROR_NOT_FOUND

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
            self.channel(_("Balor device detected:"))
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
                    _("Balor devices were found. But something else was connected to them.")
                )
            else:
                self.channel(
                    _(
                        "Balor devices were found but they were rejected by device criteria."
                    )
                )
            raise ConnectionRefusedError

        return device

    def detach_kernel(self, device, interface):
        """Detach kernel driver if active."""
        _ = self.channel._
        import usb

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
            self.channel(_("Kernel detach: Not Implemented."))

    def get_active_config(self, device):
        """Get active USB configuration."""
        _ = self.channel._
        import usb

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
        """Set USB device configuration."""
        _ = self.channel._
        import usb

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

    def claim_interface(self, device, interface):
        """Claim USB interface."""
        _ = self.channel._
        import usb
        import usb.util

        try:
            self.channel(_("Attempting to claim interface."))
            usb.util.claim_interface(device, interface)
            self.channel(_("Interface claim: Success"))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code
            self.channel(str(e))
            self.channel(_("Interface claim: Failed. (Interface is in use.)"))
            raise ConnectionRefusedError

    def disconnect_detach(self, device, interface):
        """Reattach kernel driver."""
        _ = self.channel._
        import usb

        try:
            self.channel(_("Attempting kernel attach"))
            device.attach_kernel_driver(interface.bInterfaceNumber)
            self.channel(_("Kernel attach: Success."))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code
            self.channel(str(e))
            self.channel(_("Kernel attach: Fail."))
        except NotImplementedError:
            self.channel(_("Kernel attach: Fail."))

    def unclaim_interface(self, device, interface):
        """Release USB interface."""
        _ = self.channel._
        import usb
        import usb.util

        try:
            self.channel(_("Attempting to release interface."))
            usb.util.release_interface(device, interface)
            self.channel(_("Interface released."))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code
            self.channel(str(e))
            self.channel(_("Interface did not exist."))

    def disconnect_dispose(self, device):
        """Dispose USB resources."""
        _ = self.channel._
        import usb
        import usb.util

        try:
            self.channel(_("Attempting to dispose resources."))
            usb.util.dispose_resources(device)
            self.channel(_("Dispose Resources: Success"))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code
            self.channel(str(e))
            self.channel(_("Dispose Resources: Fail"))

    def disconnect_reset(self, device):
        """Reset USB device."""
        _ = self.channel._
        import usb

        try:
            self.channel(_("Attempting USB reset."))
            device.reset()
            self.channel(_("USB connection reset."))
        except usb.core.USBError as e:
            self.backend_error_code = e.backend_error_code
            self.channel(str(e))
            self.channel(_("USB connection did not exist."))

    def bus(self, index):
        """Get USB bus number."""
        return self.devices[index].bus

    def address(self, index):
        """Get USB device address."""
        return self.devices[index].address

    def is_open(self, index=0):
        """Check if device is open."""
        try:
            dev = self.devices[index]
            if dev:
                return True
        except KeyError:
            pass
        return False

    def open(self, index=0):
        """Open device via libusb."""
        _ = self.channel._
        import usb.core  # noqa: F401
        import usb.util

        self.channel(_("Attempting connection to USB via libusb."))
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
                    self.unclaim_interface(device, interface)
                    self.claim_interface(device, interface)
            except usb.core.USBError:
                self.channel(_("Device failed during detach and claim"))
            self.channel(_("USB Connected via libusb."))
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
        """Close device."""
        _ = self.channel._
        import usb

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
        """Write command packet."""
        if packet is None:
            raise ValueError("Packet cannot be None")
            
        import usb
        packet_length = len(packet)
        assert packet_length in (0xC, 0xC00)
        if packet is not None:
            try:
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
        """Read status response."""
        import usb

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


# ============================================================================
# FACTORY FUNCTION - Selects Appropriate Connection Type
# ============================================================================


def create_usb_connection(channel):
    """
    Create appropriate USB connection object.
    
    Tries in order:
    1. Windows Native Driver (Lmcv4u.sys) - No Zadig required
    2. libusb via PyUSB - Requires Zadig
    
    Returns:
        Connection object with open(), close(), write(), read() methods
    """
    _ = channel._

    # Try Windows native driver first
    try:
        channel(_("Trying Windows native driver (Lmcv4u.sys)..."))
        connection = WindowsNativeUSBConnection(channel)
        # Quick test: can we find the device?
        device_path = connection.find_device_path()
        if device_path:
            channel(_("✓ Windows native driver available"))
            return connection
        else:
            channel(_("✗ Device not found via Windows driver"))
    except Exception as e:
        channel(_(f"Windows native driver test failed: {e}"))

    # Fallback to libusb
    try:
        channel(_("Trying libusb via PyUSB..."))
        connection = LibUSBConnection(channel)
        if connection._usb_available:
            channel(_("✓ libusb backend available"))
            return connection
        else:
            channel(_("✗ PyUSB not available"))
    except Exception as e:
        channel(_(f"libusb test failed: {e}"))

    # No backend available
    channel(
        _(
            "ERROR: No USB communication backend available!\n"
            "Options:\n"
            "1. Windows native driver (Lmcv4u.sys) - Required to find device\n"
            "2. Or install: pip install pyusb\n"
            "   Then use Zadig to install libusb-win32 driver"
        )
    )
    raise ConnectionError("No USB backend available")
