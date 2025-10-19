# USB Communication API Documentation

## Overview

This document provides comprehensive API documentation for the USB communication modules used in MeerK40t's Balor/JCZ galvo laser controller support. The USB communication layer provides multiple connection strategies with automatic fallback for maximum compatibility across platforms.

## Module Architecture

```
Connection Hierarchy:
┌─────────────────────────────────────────────────────────────┐
│                    GalvoController                          │
│                  (controller.py)                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────┐
            │  Connection Selection   │
            │  (Platform-Specific)    │
            └─────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ MockConnection│  │DirectUSBConn │  │ USBConnection│
│              │  │ (Windows)    │  │  (LibUSB)    │
│ Testing Mode │  │ Native Driver│  │  Cross-Plat  │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Connection Modules

### 1. MockConnection (mock_connection.py)

**Purpose**: Testing and development without hardware

**Use Cases**:
- Hardware-free development
- Protocol debugging and analysis
- CI/CD integration testing
- User training and demonstrations

**Key Features**:
- Command parsing and human-readable logging
- Synthetic response generation
- Repeat detection for log compression
- Serial number emulation

**API**:

```python
class MockConnection:
    def __init__(self, channel) -> None
    def open(self, index: int = 0) -> int
    def close(self, index: int = 0) -> None
    def write(self, index: int = 0, packet: Optional[bytes] = None) -> None
    def read(self, index: int = 0) -> bytes
    def is_open(self, index: int = 0) -> bool
    def set_implied_response(self, data: Optional[Union[str, bytes]]) -> None
```

**Example Usage**:

```python
from meerk40t.balormk.mock_connection import MockConnection

# Create mock with logging
mock = MockConnection(channel)
mock.send = print  # Output commands to console
mock.recv = print  # Output responses to console

# Use like real connection
mock.open(0)
mock.write(0, command_packet)
status = mock.read(0)
mock.close(0)
```

### 2. DirectUSBConnection (direct_usb_connection.py)

**Purpose**: Native Windows driver communication (Lmcv4u.sys)

**Platform**: Windows 10/11 only

**Advantages**:
- No Zadig driver replacement needed
- Compatible with EzCAD2 and other software
- Lower latency (1-2ms vs 3-5ms)
- Uses native Windows Setup API

**Technical Details**:
- Device GUID: `{8bc4c1e1-1dc9-11d9-a23c-000b6a23dc28}`
- Communication: DeviceIoControl with IOCTL codes
- Initialization: `IOCTL_INIT (0x99982028)`
- Commands: `IOCTL_COMMAND (0x99982014)`

**API**:

```python
class DirectUSBConnection:
    def __init__(self, channel) -> None
    def open(self, index: int = 0) -> int
    def close(self, index: int = 0) -> None
    def write(self, index: int = 0, packet: Optional[bytes] = None, attempt: int = 0) -> None
    def read(self, index: int = 0, attempt: int = 0) -> bytes
    def is_open(self, index: int = 0) -> bool
    def bus(self, index: int) -> int
    def address(self, index: int) -> int
    def find_device(self, index: int = 0) -> str
    def _discover_devices(self) -> list[str]
    def _initialize_device(self, index: int = 0) -> bool
```

**Example Usage**:

```python
from meerk40t.balormk.direct_usb_connection import DirectUSBConnection
import struct

# Create direct connection (Windows only)
conn = DirectUSBConnection(channel)

# Open and initialize device
if conn.open(0) >= 0:
    # Send command (12 bytes)
    cmd = struct.pack('<6H', 0x001B, 0x8000, 0x8000, 0, 0, 0)
    conn.write(0, cmd)
    
    # Response received in write operation via DeviceIoControl
    # read() exists for interface compatibility
    
    conn.close(0)
```

### 3. USBConnection (usb_connection.py)

**Purpose**: Cross-platform libusb communication

**Platforms**: Windows, Linux, macOS

**Requirements**:
- Python package: `pyusb`
- Windows: Zadig driver replacement (libusb-win32 or WinUSB)
- Linux: udev rules for device permissions
- macOS: libusb via Homebrew

**Technical Details**:
- Vendor ID: `0x9588` (JCZ Technologies)
- Product ID: `0x9899` (Balor/EZCAD2)
- Write Endpoint: `0x02` (BULK OUT)
- Read Endpoint: `0x88` (BULK IN)
- Timeout: 100ms

**API**:

```python
class USBConnection:
    def __init__(self, channel) -> None
    def open(self, index: int = 0) -> int
    def close(self, index: int = 0) -> None
    def write(self, index: int = 0, packet: Optional[bytes] = None, attempt: int = 0) -> None
    def read(self, index: int = 0, attempt: int = 0) -> bytes
    def is_open(self, index: int = 0) -> bool
    def bus(self, index: int) -> int
    def address(self, index: int) -> int
    def find_device(self, index: int = 0) -> usb.core.Device
    def detach_kernel(self, device, interface) -> None
    def get_active_config(self, device) -> usb.core.Interface
    def set_config(self, device) -> None
    def claim_interface(self, device, interface) -> None
```

**Example Usage**:

```python
from meerk40t.balormk.usb_connection import USBConnection
import struct

# Create libusb connection
conn = USBConnection(channel)

# Open device with full initialization sequence
result = conn.open(0)
if result >= 0:
    # Send command (12 bytes)
    cmd = struct.pack('<6H', 0x001B, 0x8000, 0x8000, 0, 0, 0)
    conn.write(0, cmd)
    
    # Read 8-byte status response
    status = conn.read(0)
    print(f"Status: {status.hex()}")
    
    conn.close(0)
elif result == -2:
    print("LibUSB backend not available")
elif result == -1:
    print("Connection failed")
```

### 4. Dual-Mode Driver (usb_communication.py)

**Purpose**: Unified interface with automatic connection selection

**Features**:
- Combines Windows native and libusb backends
- Automatic platform detection
- Graceful fallback mechanisms
- Consistent error handling

**Connection Logic**:

```python
def create_usb_connection(channel):
    # On Windows: Try DirectUSBConnection first
    if platform.system() == "Windows":
        try:
            conn = WindowsNativeUSBConnection(channel)
            if conn.find_device_path():
                return conn  # Direct driver available
        except:
            pass  # Fall back to libusb
    
    # All platforms: Use libusb
    return LibUSBConnection(channel)
```

**API**:

```python
# Factory function
def create_usb_connection(channel) -> Union[WindowsNativeUSBConnection, LibUSBConnection]

# WindowsNativeUSBConnection (similar to DirectUSBConnection)
class WindowsNativeUSBConnection:
    def __init__(self, channel) -> None
    def open(self, index: int = 0) -> int
    def close(self, index: int = 0) -> None
    def write(self, index: int = 0, packet: Optional[bytes] = None, attempt: int = 0) -> None
    def read(self, index: int = 0, attempt: int = 0) -> bytes
    def is_open(self, index: int = 0) -> bool
    def find_device_path(self) -> Optional[str]

# LibUSBConnection (wrapper around USBConnection)
class LibUSBConnection:
    # Same API as USBConnection
```

## Common Interface

All connection classes implement a common interface for seamless switching:

### Required Methods

```python
def open(self, index=0) -> int:
    """
    Open device connection.
    
    Returns:
        int: Device index (>=0) on success
             -1 on connection failure
             -2 on missing backend (libusb only)
    """

def close(self, index=0) -> None:
    """Close device connection and cleanup resources."""

def write(self, index=0, packet=None, attempt=0) -> None:
    """
    Send command packet to device.
    
    Args:
        packet: 12 bytes (single command) or 3072 bytes (batch)
        
    Raises:
        ConnectionError: Communication failed
    """

def read(self, index=0, attempt=0) -> bytes:
    """
    Read 8-byte status response from device.
    
    Returns:
        bytes: 8-byte status packet
        
    Raises:
        ConnectionError: Communication failed
    """

def is_open(self, index=0) -> bool:
    """Check if device connection is open."""
```

### Optional Methods

```python
def bus(self, index) -> int:
    """Get USB bus number (0 for non-USB connections)."""

def address(self, index) -> int:
    """Get USB device address (0 for non-USB connections)."""
```

### Identification Attribute

```python
is_direct_connection: bool
    # True: DirectUSBConnection (Windows native driver)
    # False: USBConnection or MockConnection (libusb or mock)
```

## Packet Formats

### Command Packet (Write)

#### Single Command (12 bytes = 0xC)

```
Offset  Size  Description
------  ----  -----------
0-1     2     Command ID (uint16_t, little-endian)
2-5     4     Parameter 1 (uint32_t or 2×uint16_t)
6-9     4     Parameter 2 (uint32_t or 2×uint16_t)
10-11   2     Parameter 3 (uint16_t)
```

**Python Struct Format**: `<6H` (6 unsigned short, little-endian)

**Example**:
```python
import struct

# SetLaserMode command (0x001B)
cmd_id = 0x001B
x_coord = 0x8000  # Center X
y_coord = 0x8000  # Center Y
flags = 0x0000

packet = struct.pack('<6H', cmd_id, x_coord, 0, y_coord, 0, flags)
# Result: 12 bytes
```

#### Batch Commands (3072 bytes = 0xC00)

```
256 × 12-byte commands
Used for list uploads and bulk operations
```

### Status Response (Read)

#### Response Packet (8 bytes)

```
Offset  Size  Description
------  ----  -----------
0       1     Status byte (READY=0x20, BUSY=0x04, AXIS=0x40)
1       1     Flags byte
2-3     2     X position (uint16_t, little-endian)
4-5     2     Y position (uint16_t, little-endian)
6-7     2     Reserved/Error code
```

**Python Unpacking**:
```python
import struct

status = conn.read(0)
status_byte, flags, x_pos, y_pos, reserved = struct.unpack('<2B3H', status)

if status_byte & 0x20:
    print("Device ready")
if status_byte & 0x04:
    print("Device busy")
```

## Error Handling

### Exception Hierarchy

```
Exception
├── ConnectionError
│   ├── ConnectionRefusedError
│   │   └── Device not found / access denied
│   └── Communication failure / timeout
├── PermissionError
│   └── OS-level USB access denied
└── ValueError
    └── Invalid packet format
```

### Error Recovery Patterns

#### Automatic Retry with Reconnection

All connection classes implement automatic retry:

```python
def write(self, index=0, packet=None, attempt=0):
    try:
        # Attempt write
        self._do_write(index, packet)
    except USBError:
        if attempt <= 3:
            self.close(index)
            time.sleep(0.1)
            self.open(index)
            self.write(index, packet, attempt + 1)
        else:
            raise ConnectionError
```

#### Platform-Specific Guidance

```python
try:
    conn.open(0)
except ConnectionRefusedError:
    from platform import system
    if system() == "Windows":
        if hasattr(conn, 'is_direct_connection') and conn.is_direct_connection:
            print("Direct driver failed. Close EzCAD2 or use Zadig.")
        else:
            print("Install libusb via Zadig: https://zadig.akeo.ie/")
    elif system() == "Linux":
        print("Check udev rules: /etc/udev/rules.d/99-galvo.rules")
```

## Integration with GalvoController

### Connection Factory Logic

The GalvoController uses intelligent connection selection:

```python
# In controller.py connect_if_needed()

if mock_mode:
    self.connection = MockConnection(channel)
elif system() == "Windows" and DirectUSBConnection available:
    try:
        self.connection = DirectUSBConnection(channel)
        if self.connection.open(0) < 0:
            raise ConnectionError
    except:
        self.connection = USBConnection(channel)
else:
    self.connection = USBConnection(channel)
```

### Connection Type Detection

```python
# Check which connection type is active
if hasattr(controller.connection, 'is_direct_connection'):
    if controller.connection.is_direct_connection:
        print("Using Windows native driver")
    else:
        print("Using libusb")
```

### Unified Communication

The controller uses the common interface transparently:

```python
# Send command (works with any connection type)
controller.connection.write(0, packet)

# Read response
status = controller.connection.read(0)

# Check connection state
if controller.connection.is_open(0):
    print("Connected")
```

## Platform-Specific Setup

### Windows

#### Option 1: Direct Driver (Recommended)

**Requirements**:
- Windows 10/11
- Lmcv4u.sys driver (installed with EzCAD2)

**Advantages**:
- No additional setup required
- Works alongside EzCAD2
- Best performance

**Setup**: None - automatic

#### Option 2: LibUSB (Alternative)

**Requirements**:
- Python: `pip install pyusb`
- Zadig tool: https://zadig.akeo.ie/

**Setup**:
1. Download and run Zadig
2. Options → List All Devices
3. Select "JCZ Laser Controller" or VID:9588 PID:9899
4. Select "libusb-win32" or "WinUSB" driver
5. Click "Replace Driver"

**Note**: Cannot run EzCAD2 with libusb driver

### Linux

#### Requirements
- Python: `pip install pyusb`
- libusb: `sudo apt install libusb-1.0-0`

#### udev Rules

Create `/etc/udev/rules.d/99-galvo.rules`:

```bash
# JCZ Laser Controller
SUBSYSTEM=="usb", ATTRS{idVendor}=="9588", ATTRS{idProduct}=="9899", MODE="0666", GROUP="plugdev"
```

Reload rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Add user to plugdev group:
```bash
sudo usermod -a -G plugdev $USER
# Logout and login for group change to take effect
```

### macOS

#### Requirements
- Python: `pip install pyusb`
- libusb: `brew install libusb`

#### Setup
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install libusb
brew install libusb

# Install pyusb
pip install pyusb
```

**Note**: May require disabling System Integrity Protection for some operations

## Testing and Debugging

### Enable Mock Mode

```python
# In device configuration
device.setting(bool, "mock", True)

# In controller initialization
controller = GalvoController(service, force_mock=True)
```

### Command Logging

```python
# Set up send/recv channels for mock connection
mock.send = lambda cmd: print(f"TX: {cmd}")
mock.recv = lambda resp: print(f"RX: {resp}")

# All commands and responses will be logged
```

### Connection Type Verification

```python
# Check active connection type
connection = controller.connection

print(f"Connection type: {type(connection).__name__}")
print(f"Is direct: {getattr(connection, 'is_direct_connection', 'N/A')}")
print(f"Is open: {connection.is_open(0)}")

if hasattr(connection, 'bus'):
    print(f"USB Bus: {connection.bus(0)}")
    print(f"USB Address: {connection.address(0)}")
```

### Performance Testing

```python
import time

# Measure command latency
times = []
for _ in range(100):
    start = time.time()
    controller.connection.write(0, test_packet)
    controller.connection.read(0)
    times.append(time.time() - start)

avg_time = sum(times) / len(times)
print(f"Average command time: {avg_time*1000:.2f}ms")

# Expected results:
# - Direct Connection: 1-2ms
# - LibUSB Connection: 3-5ms
# - Mock Connection: <0.1ms
```

## API Version History

### Version 1.0.0 (Current)
- Initial unified API documentation
- DirectUSBConnection for Windows native driver
- Enhanced USBConnection with comprehensive docs
- MockConnection with command parsing
- Dual-mode driver with automatic selection

## References

### Related Documentation
- `README.md` (in this directory) - Module overview and architecture
- `DIRECT_CONNECTION_GUIDE.md` (in this directory) - Windows driver setup guide
- `controller.py` (in this directory) - GalvoController implementation
- [MeerK40t Wiki](https://github.com/meerk40t/meerk40t/wiki) - General installation and usage

### External Resources
- [PyUSB Documentation](https://github.com/pyusb/pyusb)
- [libusb Documentation](https://libusb.info/)
- [Zadig Tool](https://zadig.akeo.ie/)
- [Windows Setup API Reference](https://docs.microsoft.com/en-us/windows-hardware/drivers/install/setupapi)

---

**Author**: MeerK40t Development Team  
**License**: MIT  
**Last Updated**: 2025-10-19
