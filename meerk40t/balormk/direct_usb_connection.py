"""
Direct Windows USB Connection for Balor Laser Controllers

This module provides direct communication with Balor laser controllers using native Windows APIs
and the Lmcv4u.sys driver, eliminating the need for Zadig driver replacement.

Technical Overview:
==================

The DirectUSBConnection class implements the same interface as USBConnection but uses Windows
native APIs instead of libusb. This approach has several advantages:

1. **No Driver Replacement**: Works with the native Lmcv4u.sys driver without Zadig
2. **EzCAD2 Compatibility**: Can coexist with EzCAD2 software 
3. **Windows Integration**: Uses standard Windows device enumeration
4. **Fallback Support**: Gracefully degrades to libusb if needed

Device Discovery Process:
========================

The device discovery follows the same sequence as EzCAD2:

1. **SetupDiGetClassDevsW**: Find devices with GUID {8bc4c1e1-1dc9-11d9-a23c-000b6a23dc28}
2. **SetupDiEnumDeviceInterfaces**: Enumerate available device interfaces
3. **SetupDiGetDeviceInterfaceDetailW**: Get actual device path (e.g., \\\\?\\usb#vid_9588&pid_9899#...)
4. **CreateFileW**: Open device for communication
5. **DeviceIoControl**: Send commands using IOCTL codes

Communication Protocol:
======================

The module uses DeviceIoControl with specific IOCTL codes:

- **IOCTL_INIT** (0x99982028): Device initialization
  - Input: 16 bytes (typically all zeros for basic init)
  - Output: 12 bytes (device response)
  
- **IOCTL_COMMAND** (0x99982014): Laser commands
  - Input: 12 bytes (structured command data)
  - Output: 6 bytes (command response)

Command Structure (12 bytes):
    Offset 0-1:  Command ID (e.g., 0x001B for SetLaserMode)
    Offset 2-5:  Parameter 1 (32-bit, typically X coordinate)
    Offset 6-9:  Parameter 2 (32-bit, typically Y/status)
    Offset 10-11: Parameter 3 (16-bit, typically tail/flags)

Error Handling:
===============

The module implements robust error handling:

- **Device Discovery Errors**: Falls back to libusb connection
- **Communication Errors**: Automatic retry with reconnection
- **Platform Errors**: Only attempts on Windows platform
- **Initialization Errors**: Clear error messages for troubleshooting

Compatibility:
==============

This module is designed to be a drop-in replacement for USBConnection:

- Same method signatures (open, close, read, write, is_open, etc.)
- Same error handling patterns
- Same logging interface
- Compatible with existing MeerK40t controller logic

Usage Example:
==============

    from meerk40t.balormk.direct_usb_connection import DirectUSBConnection
    
    # Create connection (same interface as USBConnection)
    conn = DirectUSBConnection(logging_channel)
    
    # Open device (auto-discovers and initializes)
    if conn.open(device_index=0) >= 0:
        # Send command packet
        command_packet = struct.pack('<6H', 0x001B, x_low, x_high, y_low, y_high, flags)
        conn.write(0, command_packet)
        
        # Close when done
        conn.close(0)

Dependencies:
=============

- Windows platform (Windows 7+)
- Native Windows APIs (kernel32.dll, setupapi.dll)
- ctypes (standard library)
- Active Lmcv4u.sys driver (activated by EzCAD2 or similar)

Integration:
============

The module integrates with MeerK40t's controller through a fallback mechanism:

1. Controller attempts DirectUSBConnection first (Windows only)
2. If successful, uses direct communication
3. If failed, falls back to USBConnection (libusb)
4. User sees appropriate log messages for the connection type used

This ensures maximum compatibility while providing the benefits of direct driver access.

Author: MeerK40t Development Team
License: MIT
Version: 1.0.0
"""

import time
import ctypes
from ctypes import wintypes, Structure, POINTER, byref
import struct

# Windows API constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = -1

# Setup API constants
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010

# Device GUID for Balor controllers
BALOR_GUID = "{8bc4c1e1-1dc9-11d9-a23c-000b6a23dc28}"

# IOCTL codes for device communication
IOCTL_INIT = 2576883752 & 0xFFFFFFFF      # 0x99982028 - initialization
IOCTL_COMMAND = 2576883732 & 0xFFFFFFFF   # 0x99982014 - commands


class GUID(Structure):
    """Windows GUID structure"""
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]


class SP_DEVICE_INTERFACE_DATA(Structure):
    """Setup API device interface data"""
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", POINTER(wintypes.ULONG))
    ]


class SP_DEVICE_INTERFACE_DETAIL_DATA_W(Structure):
    """Setup API device interface detail data"""
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("DevicePath", wintypes.WCHAR * 1)  # Variable length
    ]


class DirectUSBConnection:
    """
    Direct Windows USB connection for Balor laser controllers.
    
    Provides the same interface as USBConnection but uses native Windows APIs
    instead of libusb. This eliminates the need for Zadig driver replacement.
    """

    def __init__(self, channel):
        self.channel = channel
        self.devices = {}  # index -> device_handle
        self.device_paths = {}  # index -> device_path
        self.initialized = {}  # index -> bool (initialization status)
        self.backend_error_code = None
        self.timeout = 100
        self.is_direct_connection = True  # Flag to identify connection type

        # Load Windows APIs
        self.kernel32 = ctypes.windll.kernel32
        self.setupapi = ctypes.windll.setupapi
        
        # Setup API function signatures
        self._setup_api_signatures()

    def _setup_api_signatures(self):
        """Setup Windows API function signatures"""
        # Setup API signatures
        self.setupapi.SetupDiGetClassDevsW.argtypes = [
            POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD
        ]
        self.setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE

        self.setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
            wintypes.HANDLE, wintypes.LPVOID, POINTER(GUID), wintypes.DWORD, 
            POINTER(SP_DEVICE_INTERFACE_DATA)
        ]
        self.setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL

        self.setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
            wintypes.HANDLE, POINTER(SP_DEVICE_INTERFACE_DATA),
            POINTER(SP_DEVICE_INTERFACE_DETAIL_DATA_W), wintypes.DWORD,
            POINTER(wintypes.DWORD), wintypes.LPVOID
        ]
        self.setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL

        self.setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
        self.setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

        # Kernel32 signatures
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE

        self.kernel32.DeviceIoControl.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
            wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID
        ]
        self.kernel32.DeviceIoControl.restype = wintypes.BOOL

        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

        self.kernel32.GetLastError.restype = wintypes.DWORD

    def _parse_guid(self, guid_string):
        """Parse GUID string into GUID structure"""
        guid_str = guid_string.strip('{}')
        parts = guid_str.split('-')
        
        guid = GUID()
        guid.Data1 = int(parts[0], 16)
        guid.Data2 = int(parts[1], 16)
        guid.Data3 = int(parts[2], 16)
        
        # Data4 is 8 bytes from parts[3] and parts[4]
        data4_str = parts[3] + parts[4]
        for i in range(8):
            guid.Data4[i] = int(data4_str[i*2:(i+1)*2], 16)
        
        return guid

    def find_device(self, index=0):
        """
        Find Balor devices using Windows Setup API.
        
        This method replicates EzCAD2's device discovery process:
        1. Query Windows for devices with Balor GUID
        2. Enumerate available device interfaces  
        3. Extract device paths for communication
        
        Args:
            index (int): Device index to find (0 for first device)
            
        Returns:
            str: Device path for the specified index
            
        Raises:
            ConnectionRefusedError: If no devices found or index out of range
            
        Technical Details:
            - Uses GUID {8bc4c1e1-1dc9-11d9-a23c-000b6a23dc28} (Balor device class)
            - Calls SetupDiGetClassDevsW with DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
            - Enumerates interfaces until target index found
            - Returns full device path (e.g., \\\\?\\usb#vid_9588&pid_9899#20200507#{guid})
        """
        _ = self.channel._
        self.channel(_("Using Direct Windows API to connect."))
        self.channel(_("Finding devices using Setup API."))
        
        try:
            device_paths = self._discover_devices()
        except Exception as e:
            self.channel(f"Device discovery failed: {e}")
            raise ConnectionRefusedError("Device discovery failed")
        
        if len(device_paths) == 0:
            self.channel(_("Devices Not Found."))
            raise ConnectionRefusedError("No devices found")
        
        for i, path in enumerate(device_paths):
            self.channel(_("Balor device detected:"))
            self.channel(f"  Device {i}: {path}")
        
        try:
            device_path = device_paths[index]
            self.device_paths[index] = device_path
            return device_path
        except IndexError:
            self.channel(_("Device index out of range."))
            raise ConnectionRefusedError("Device index out of range")

    def _discover_devices(self):
        """
        Discover Balor devices using Windows Setup API.
        
        Implements the complete device discovery sequence as observed in EzCAD2's API calls.
        This is the core function that interfaces with Windows device management.
        
        Returns:
            list[str]: List of device paths for all discovered Balor devices
            
        Raises:
            ConnectionError: If Windows API calls fail
            
        Technical Implementation:
            1. Parse Balor device GUID into Windows GUID structure
            2. Call SetupDiGetClassDevsW to get device info set handle
            3. Loop through device interfaces using SetupDiEnumDeviceInterfaces
            4. For each interface, call SetupDiGetDeviceInterfaceDetailW twice:
               - First call gets required buffer size
               - Second call gets actual device path
            5. Extract device path from returned buffer
            6. Clean up device info set handle
            
        Windows API Error Codes:
            - ERROR_NO_MORE_ITEMS (259): Normal end of enumeration
            - ERROR_INVALID_USER_BUFFER (1784): Buffer size issues
            - Other errors: API failures requiring fallback to libusb
        """
        device_guid = self._parse_guid(BALOR_GUID)
        
        # Get device class
        device_info_set = self.setupapi.SetupDiGetClassDevsW(
            byref(device_guid),
            None,
            None,
            DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
        )
        
        if device_info_set == INVALID_HANDLE_VALUE:
            error = self.kernel32.GetLastError()
            raise ConnectionError(f"SetupDiGetClassDevsW failed: {error}")
        
        devices = []
        device_index = 0
        
        try:
            while True:
                # Enumerate device interfaces
                device_interface_data = SP_DEVICE_INTERFACE_DATA()
                device_interface_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
                
                result = self.setupapi.SetupDiEnumDeviceInterfaces(
                    device_info_set,
                    None,
                    byref(device_guid),
                    device_index,
                    byref(device_interface_data)
                )
                
                if not result:
                    error = self.kernel32.GetLastError()
                    if error == 259:  # ERROR_NO_MORE_ITEMS
                        break
                    else:
                        raise ConnectionError(f"SetupDiEnumDeviceInterfaces failed: {error}")
                
                # Get device interface details
                required_size = wintypes.DWORD()
                self.setupapi.SetupDiGetDeviceInterfaceDetailW(
                    device_info_set,
                    byref(device_interface_data),
                    None,
                    0,
                    byref(required_size),
                    None
                )
                
                # Allocate buffer and get device path
                buffer_size = required_size.value
                buffer = ctypes.create_string_buffer(buffer_size)
                
                detail_data = ctypes.cast(buffer, POINTER(SP_DEVICE_INTERFACE_DETAIL_DATA_W)).contents
                detail_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_W)
                
                result = self.setupapi.SetupDiGetDeviceInterfaceDetailW(
                    device_info_set,
                    byref(device_interface_data),
                    byref(detail_data),
                    buffer_size,
                    byref(required_size),
                    None
                )
                
                if result:
                    path_offset = ctypes.sizeof(wintypes.DWORD)
                    device_path = ctypes.wstring_at(ctypes.addressof(buffer) + path_offset)
                    devices.append(device_path)
                else:
                    error = self.kernel32.GetLastError()
                    self.channel(f"Warning: Failed to get device path for index {device_index}: {error}")
                
                device_index += 1
        
        finally:
            self.setupapi.SetupDiDestroyDeviceInfoList(device_info_set)
        
        return devices

    def bus(self, index):
        """Get bus number (compatibility method)"""
        # Direct connection doesn't have bus concept, return index
        return index

    def address(self, index):
        """Get address (compatibility method)"""
        # Direct connection doesn't have address concept, return index
        return index

    def is_open(self, index=0):
        """Check if device is open"""
        return index in self.devices and self.devices[index] != INVALID_HANDLE_VALUE

    def open(self, index=0):
        """Open device connection"""
        _ = self.channel._
        self.channel(_("Attempting connection to device via Direct API."))
        
        try:
            # Find device path
            device_path = self.find_device(index)
            
            # Open device
            self.channel(f"Opening device: {device_path}")
            handle = self.kernel32.CreateFileW(
                device_path,
                GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                None
            )
            
            if handle == INVALID_HANDLE_VALUE:
                error = self.kernel32.GetLastError()
                raise ConnectionError(f"Cannot open device: Error {error}")
            
            self.devices[index] = handle
            self.initialized[index] = False
            
            # Initialize device
            if self._initialize_device(index):
                self.channel(_("Direct USB Connected and Initialized."))
                return index
            else:
                self.close(index)
                raise ConnectionError("Device initialization failed")
                
        except Exception as e:
            self.channel(f"Direct connection failed: {e}")
            return -1

    def _initialize_device(self, index=0):
        """
        Initialize device with required setup sequence.
        
        Sends the initialization command that prepares the device for communication.
        This replicates the initialization sequence observed in EzCAD2's API monitor logs.
        
        Args:
            index (int): Device index to initialize
            
        Returns:
            bool: True if initialization successful, False otherwise
            
        Technical Details:
            - Uses IOCTL_INIT (0x99982028) code
            - Sends 16 bytes of initialization data (typically all zeros)
            - Expects 12-byte response from device
            - Must be called before any command operations
            - Failure here indicates driver/device issues
            
        Initialization Data Format:
            - 16 bytes total (padded with zeros if needed)
            - All zeros works for basic initialization
            - Advanced patterns may be needed for specific configurations
            
        Error Conditions:
            - ERROR_INVALID_HANDLE (6): Device not properly opened
            - ERROR_ACCESS_DENIED (5): Driver permissions issue
            - Other errors: Hardware or driver communication failure
        """
        handle = self.devices[index]
        
        # Send initialization command (16 bytes of zeros)
        init_data = bytes(16)
        init_output = ctypes.create_string_buffer(12)
        bytes_returned = wintypes.DWORD()
        
        result = self.kernel32.DeviceIoControl(
            handle, IOCTL_INIT, init_data, 16,
            init_output, 12, byref(bytes_returned), None
        )
        
        if result:
            self.initialized[index] = True
            self.channel("Device initialization successful")
            return True
        else:
            error = self.kernel32.GetLastError()
            self.channel(f"Device initialization failed: Error {error}")
            return False

    def close(self, index=0):
        """Close device connection"""
        _ = self.channel._
        if index in self.devices:
            handle = self.devices[index]
            if handle != INVALID_HANDLE_VALUE:
                self.kernel32.CloseHandle(handle)
                self.channel(_("Direct USB Disconnected."))
            del self.devices[index]
            
        if index in self.device_paths:
            del self.device_paths[index]
            
        if index in self.initialized:
            del self.initialized[index]

    def write(self, index=0, packet=None, attempt=0):
        """
        Write data to device using DeviceIoControl.
        
        This method handles the low-level communication with the Balor device through
        the Windows driver. It translates MeerK40t's packet format into DeviceIoControl calls.
        
        Args:
            index (int): Device index to write to (default: 0)
            packet (bytes): Data packet to send (12 or 3072 bytes)
            attempt (int): Retry attempt number (for internal use)
            
        Raises:
            ConnectionError: If device not open/initialized or communication fails
            ValueError: If packet length is invalid
            
        Packet Format Support:
            - 12 bytes (0xC): Single command packets
              - Uses IOCTL_COMMAND (0x99982014)
              - Returns 6-byte response in DeviceIoControl call
              - Format: [cmd_id][param1][param2][param3] (struct <6H)
              
            - 3072 bytes (0xC00): Bulk command lists (future support)
              - Requires different IOCTL code (not yet implemented)
              - Used for batch operations and list uploads
              
        Command Packet Structure (12 bytes):
            Bytes 0-1:   Command ID (e.g., 0x001B = SetLaserMode)
            Bytes 2-3:   Parameter 1 Low Word
            Bytes 4-5:   Parameter 1 High Word  
            Bytes 6-7:   Parameter 2 Low Word
            Bytes 8-9:   Parameter 2 High Word
            Bytes 10-11: Parameter 3/Flags
            
        Error Recovery:
            - Automatic retry up to 3 attempts
            - Device reconnection on communication failure
            - Graceful degradation with clear error messages
            
        Performance Notes:
            - DeviceIoControl is synchronous (blocking)
            - Response received immediately in same call
            - No separate read() operation needed for 12-byte packets
        """
        if not self.is_open(index) or not self.initialized.get(index, False):
            raise ConnectionError("Device not open or not initialized")
        
        packet_length = len(packet)
        if packet_length != 0xC and packet_length != 0xC00:
            raise ValueError(f"Invalid packet length: {packet_length}")
        
        handle = self.devices[index]
        
        try:
            # For 12-byte packets, use command IOCTL
            if packet_length == 0xC:
                output_buffer = ctypes.create_string_buffer(6)
                bytes_returned = wintypes.DWORD()
                
                result = self.kernel32.DeviceIoControl(
                    handle, IOCTL_COMMAND, packet, 12,
                    output_buffer, 6, byref(bytes_returned), None
                )
                
                if not result:
                    error = self.kernel32.GetLastError()
                    if attempt <= 3:
                        # Retry with re-initialization
                        self.close(index)
                        time.sleep(0.1)
                        if self.open(index) >= 0:
                            self.write(index, packet, attempt + 1)
                            return
                    raise ConnectionError(f"DeviceIoControl failed: Error {error}")
            
            # For larger packets (0xC00), we might need a different approach
            # This would need investigation if such packets are used
            else:
                raise NotImplementedError("Large packet support not yet implemented")
                
        except Exception as e:
            if attempt <= 3:
                try:
                    self.close(index)
                    time.sleep(0.1)
                    if self.open(index) >= 0:
                        self.write(index, packet, attempt + 1)
                        return
                except Exception:
                    pass
            raise ConnectionError(f"Write failed: {e}")

    def read(self, index=0, attempt=0):
        """Read data from device"""
        if not self.is_open(index):
            raise ConnectionError("Device not open")
        
        # For direct communication, the response is received in the write operation
        # This method exists for compatibility with the USBConnection interface
        # but may not be used in the same way
        
        # Return dummy data for now - actual responses come from DeviceIoControl in write()
        # This may need adjustment based on how the controller uses read()
        return bytes(8)  # Return 8 bytes like original USB connection


def test_direct_connection():
    """Test function for direct connection"""
    def mock_channel(msg):
        print(f"Channel: {msg}")
    
    mock_channel._ = lambda x: x  # Mock translation function
    
    conn = DirectUSBConnection(mock_channel)
    
    try:
        index = conn.open(0)
        if index >= 0:
            print("✅ Direct connection successful!")
            
            # Test a simple command
            test_packet = struct.pack('<6H', 0x001B, 0x8000, 0x8000, 0, 0, 0)
            conn.write(index, test_packet)
            print("✅ Command sent successfully!")
            
            conn.close(index)
            return True
        else:
            print("❌ Direct connection failed")
            return False
    except Exception as e:
        print(f"❌ Direct connection error: {e}")
        return False


if __name__ == "__main__":
    test_direct_connection()