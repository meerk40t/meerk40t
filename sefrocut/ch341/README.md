# CH341 USB Interface

The CH341 module provides cross-platform USB communication support for CH341-based devices, primarily used in laser cutting controllers like Lihuiyu boards (K40 lasers) and Moshiboards.

## Overview

The CH341 is a USB interface chip that can emulate UART, parallel port, and synchronous serial interfaces (EPP, I2C, SPI). In SefroCut, it's primarily used in EPP 1.9 mode for communication with laser controllers.

## Architecture

### Driver Implementations

The module provides multiple driver implementations for different platforms and use cases:

#### LibUSB Driver (`libusb.py`)
Cross-platform driver using libusb for direct USB communication.

**Features:**
- Platform-independent USB communication
- Direct hardware access without proprietary drivers
- Automatic device detection and enumeration
- Bulk transfer support for high-speed data

**Requirements:**
```python
pip install pyusb
```

**Usage:**
```python
from sefrocut.ch341 import get_ch341_interface

# Get libusb driver (automatic selection)
for driver in get_ch341_interface(context, channel):
    if driver.driver_name == "LibUSB":
        # Use libusb driver
        break
```

#### Windows DLL Driver (`windriver.py`)
Windows-specific driver using the proprietary CH341DLL.dll.

**Features:**
- Native Windows performance
- Official CH341 driver integration
- Windows-specific optimizations
- Device enumeration through Windows APIs

**Requirements:**
- Windows operating system
- CH341DLL.dll installed (usually bundled with device drivers)

#### Mock Driver (`mock.py`)
Testing and development driver that simulates CH341 behavior.

**Features:**
- No hardware dependencies
- Configurable response simulation
- Development and testing support
- Error condition simulation

**Usage:**
```python
from sefrocut.ch341 import get_ch341_interface

# Get mock driver for testing
for driver in get_ch341_interface(context, channel, mock=True):
    # Use mock driver
    break
```

## Device Support

### Supported Hardware

**Lihuiyu Boards:**
- M2 Nano
- M3
- K40 laser systems

**Moshiboards:**
- Various Moshiboard controllers

**Other CH341-based devices:**
- Any device using CH341 in EPP 1.9 mode

### Device Detection

```python
# Device constants
USB_LOCK_VENDOR = 0x1A86   # QinHeng Electronics
USB_LOCK_PRODUCT = 0x5512  # CH341A
```

## Interface Factory

### get_ch341_interface()

The main entry point for obtaining CH341 drivers:

```python
def get_ch341_interface(context, log, mock=False, mock_status=206, bulk=True):
    """
    Factory function for CH341 drivers.

    Args:
        context: SefroCut context
        log: Logging channel
        mock: Use mock driver for testing
        mock_status: Mock status code
        bulk: Enable bulk transfer mode

    Yields:
        CH341 driver instances in order of preference
    """
```

**Driver Priority:**
1. **Mock Driver** (when `mock=True`)
2. **LibUSB Driver** (cross-platform)
3. **Windows DLL Driver** (Windows only)

## Driver Interface

All CH341 drivers implement a common interface:

### Connection Management

```python
class CH341Driver:
    def open(self, usb_index=0):
        """Open connection to CH341 device"""
        pass

    def close(self):
        """Close connection to device"""
        pass

    def is_connected(self):
        """Check if device is connected"""
        return bool
```

### Data Transfer

```python
class CH341Driver:
    def write(self, data):
        """Write data to device"""
        pass

    def read(self, length):
        """Read data from device"""
        pass

    def get_status(self):
        """Get device status"""
        return int
```

### Device Information

```python
class CH341Driver:
    @property
    def driver_name(self):
        """Driver implementation name"""
        return str

    @property
    def address(self):
        """USB device address"""
        return str

    @property
    def bus(self):
        """USB bus number"""
        return int
```

## EPP 1.9 Protocol

### Command Set

The module implements the EPP 1.9 protocol used by laser controllers:

```python
# Read commands
mCH341_PARA_CMD_R0 = 0xAC  # Read data register 0
mCH341_PARA_CMD_R1 = 0xAD  # Read data register 1

# Write commands
mCH341_PARA_CMD_W0 = 0xA6  # Write data register 0
mCH341_PARA_CMD_W1 = 0xA7  # Write data register 1

# Status commands
mCH341_PARA_CMD_STS = 0xA0  # Get status

# Control commands
mCH341_SET_PARA_MODE = 0x9A  # Set parallel mode
mCH341_PARA_INIT = 0xB1      # Initialize device
mCH341A_BUF_CLEAR = 0xB2     # Clear buffers
```

### Packet Structure

```python
mCH341_PACKET_LENGTH = 32    # Standard packet size
mCH341_PKT_LEN_SHORT = 8     # Short packet size
```

## Windows Implementation Details

### CH341Device Class (`ch341device.py`)

Low-level Windows API bindings for CH341 communication:

**Features:**
- Direct Windows API calls (kernel32, ole32, setupapi)
- Device enumeration and management
- GUID-based device discovery
- ctypes-based foreign function interface

**Key Components:**
- Device enumeration functions
- USB handle management
- Overlapped I/O support
- Error handling and status reporting

**Windows API Dependencies:**
- `kernel32.dll` - File and device operations
- `ole32.dll` - GUID string conversion
- `setupapi.dll` - Device enumeration

## Cross-Platform Implementation

### LibUSB Implementation (`libusb.py`)

Pure Python implementation using pyusb library:

**Features:**
- No platform-specific code
- Direct USB communication
- Automatic endpoint detection
- Error handling with backend-specific codes

**USB Endpoints:**
```python
BULK_WRITE_ENDPOINT = 0x02  # Output endpoint
BULK_READ_ENDPOINT = 0x82   # Input endpoint
```

**Error Handling:**
- `LIBUSB_ERROR_ACCESS` - Permission denied
- `LIBUSB_ERROR_NOT_FOUND` - Device not found
- Connection timeout handling

## Testing and Development

### Mock Driver Usage

For development without hardware:

```python
# Enable mock mode
kernel = bootstrap.bootstrap()
kernel.mock = True

# Configure mock responses
driver = get_ch341_interface(context, channel, mock=True, mock_status=206)

# Test error conditions
driver = get_ch341_interface(context, channel, mock=True, mock_status=207)
```

### Mock Driver Features

**Configurable Responses:**
- `mock_status` - Normal operation status
- `mock_error` - Error condition simulation
- `mock_finish` - Completion status

**State Simulation:**
- Connection state changes
- Data transfer simulation
- Timeout and error condition handling

## Integration with SefroCut

### Device Registration

CH341 devices are registered as SefroCut device drivers:

```python
# In device plugin
from sefrocut.ch341 import get_ch341_interface

def plugin(kernel, lifecycle):
    if lifecycle == "register":
        # Register CH341-based device
        kernel.register("device/ch341", CH341Device)
```

### State Management

Device state changes are signaled through the kernel:

```python
def _state_change(state_value):
    context.signal("pipe;state", state_value)

# States include:
# - STATE_USB_CONNECTING
# - STATE_CONNECTION_FAILED
# - STATE_CONNECTED
# - STATE_USB_DISCONNECTED
```

## Troubleshooting

### Common Issues

**Permission Errors (Linux/macOS):**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Or run with sudo (not recommended)
sudo python -m sefrocut
```

**Driver Conflicts (Windows):**
- Uninstall conflicting CH341 drivers
- Use Zadig to replace with libusb drivers
- Ensure no other applications are using the device

**Device Not Found:**
- Check USB cable connections
- Verify device is powered on
- Use `lsusb` (Linux) or Device Manager (Windows) to confirm detection

**Connection Timeouts:**
- Increase timeout values in driver configuration
- Check for USB power management issues
- Verify device firmware is compatible

### Diagnostic Commands

**Check Device Detection:**
```bash
# SefroCut console
ch341 list
ch341 status
```

**Test Communication:**
```bash
# Send test commands
ch341 write 0xA0
ch341 read 1
```

## Performance Considerations

### Transfer Modes

**Bulk Mode:**
- High-speed data transfer
- Preferred for large data blocks
- Enabled by default (`bulk=True`)

**Non-Bulk Mode:**
- Compatible with older implementations
- Lower throughput but higher compatibility

### Buffer Management

**Automatic Buffer Clearing:**
- `mCH341A_BUF_CLEAR` command
- Prevents data corruption
- Called during initialization

### Timeout Handling

**Configurable Timeouts:**
- `timeout = 1500ms` (standard operations)
- `timeoutEPPWrite = 60000ms` (write operations)
- Adjustable based on device performance

## Development Notes

### Code Attribution

**Based on existing libraries:**
- **pySerial**: Windows API device enumeration code
- **pysetupdi**: GUID conversion functions
- **gwangyi/pysetupdi**: Device discovery patterns

**License Compliance:**
- BSD-3-Clause for pySerial-derived code
- MIT License for other components

### Future Enhancements

**Potential Improvements:**
- Async I/O support
- Multiple device simultaneous operation
- Enhanced error recovery
- Performance optimizations
- Additional platform support

This CH341 module provides robust, cross-platform USB communication for laser controllers, enabling SefroCut to work with a wide range of CH341-based hardware across different operating systems.