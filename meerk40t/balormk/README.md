# BalorMK - JCZ Galvo Laser Controller Module

## Overview

BalorMK began life as the meerk40t plugin-driver for Balor by Bryce Schroeder which controls the LMC ezcad2 galvo laser boards. This was eventually rewritten but still uses many of the original names. Even as the backend was rewritten.

The BalorMK module provides comprehensive support for JCZ Technologies galvo laser controllers, including the EZCAD2 series and compatible devices. It implements the complete MeerK40t device driver pattern with device service, driver, and controller components for high-performance galvo laser control.

## Architecture

### Core Components

- **`device.py`** - Main BalorDevice service class (1136 lines)
  - Inherits from MeerK40t Service and Status classes
  - Manages device lifecycle, settings, and console commands
  - Registers device choices for configuration panels
  - Handles device activation and service integration

- **`driver.py`** - BalorDriver implementation (795 lines)
  - Translates MeerK40t cutcode operations to galvo commands
  - Manages laser power control, timing, and positioning
  - Implements cutcode processing pipeline for vector operations
  - Handles hardware-specific optimizations

- **`controller.py`** - GalvoController class (1650 lines)
  - Implements LMC (Laser Marking Controller) command protocol
  - Manages USB communication with galvo controllers
  - Processes command queues and hardware responses
  - Handles real-time control and status monitoring

- **`plugin.py`** - Device registration and plugin lifecycle
  - Registers BalorDevice with MeerK40t kernel
  - Supports multiple JCZ controller variants
  - Configures device capabilities and settings

### Supporting Files

- **`balor_params.py`** - Hardware parameter definitions and calibration data
- **`galvo_commands.py`** - LMC command structure definitions
- **`usb_connection.py`** - USB communication layer using pyusb
- **`direct_usb_connection.py`** - Direct Windows driver communication (New)
- **`mock_connection.py`** - Simulation interface for testing
- **`livelightjob.py`** - Real-time light operations and preview
- **`clone_loader.py`** - Device configuration loading utilities

### GUI Components (`gui/`)

- **`gui.py`** - Main GUI integration and panel registration
- **`balorconfig.py`** - Device configuration interface
- **`balorcontroller.py`** - Controller status and monitoring panels
- **`baloroperationproperties.py`** - Operation-specific property panels
- **`corscene.py`** - Coordinate system visualization

## Hardware Support

### Supported Controllers

- **JCZ EZCAD2 Series**: Full compatibility with EZCAD2 controllers
- **LMC Controllers**: Laser Marking Controller protocol implementation
- **Galvo Systems**: XY galvo mirror positioning systems

### Laser Types

- **Fiber Lasers**: Q-switched and MOPA (Master Oscillator Power Amplifier)
- **CO2 Lasers**: Infrared gas lasers for organic materials
- **UV Lasers**: Ultraviolet lasers for specialized applications
- **Multi-wavelength Support**: Configurable for different laser sources

### Interface Protocols

- **Direct Windows Driver**: Native Lmcv4u.sys communication (Windows)
- **USB Communication**: High-speed USB interface using pyusb/libusb
- **EPP 1.9 Protocol**: Enhanced Parallel Port protocol for legacy support
- **Real-time Control**: Low-latency command processing for precise timing

## Connection Methods

### 1. Direct Windows Driver (New)

The module now supports direct communication with the Windows Lmcv4u.sys driver, eliminating the need for Zadig driver replacement on Windows systems.

**Features:**
- **Native Driver Access**: Uses Windows Setup API for device discovery
- **EzCAD2 Compatibility**: Works alongside EzCAD2 without driver conflicts
- **No Zadig Required**: Preserves original Windows driver installation
- **Automatic Fallback**: Falls back to libusb if direct connection fails

**Technical Implementation:**
- Uses `DirectUSBConnection` class in `direct_usb_connection.py`
- Windows Setup API device enumeration with GUID `{8bc4c1e1-1dc9-11d9-a23c-000b6a23dc28}`
- DeviceIoControl communication using IOCTL codes:
  - `0x99982028`: Device initialization 
  - `0x99982014`: Command transmission
- Platform-specific connection logic in `controller.py`

**Connection Flow:**
```
Windows:    Mock → Direct Driver → LibUSB (fallback)
Linux/macOS: Mock → LibUSB
```

### 2. LibUSB Communication (Traditional)

Standard USB communication using pyusb library with libusb backend.

**Requirements:**
- **Windows**: Zadig driver replacement required
- **Linux/macOS**: Native libusb support
- **Cross-platform**: Consistent behavior across all platforms

### 3. Mock Connection (Testing)

Simulation interface for development and testing without hardware.

## Technical Features

### LMC Command Protocol

The controller implements the complete LMC command set including:

- **Positioning Commands**: Absolute and relative galvo positioning
- **Laser Control**: Power modulation, pulse timing, and frequency control
- **Marking Operations**: Vector drawing, raster scanning, and complex patterns
- **Calibration**: Galvo calibration and correction algorithms
- **Status Monitoring**: Real-time feedback and error reporting

### Performance Optimizations

- **Command Batching**: Efficient command queue processing
- **Real-time Processing**: Low-latency execution for smooth operations
- **Memory Management**: Optimized data structures for large jobs
- **Threading**: Asynchronous processing for UI responsiveness

### Integration Features

- **MeerK40t Kernel**: Full service integration with kernel channels and settings
- **Cutcode Processing**: Compatible with MeerK40t's cutcode data structures
- **Device Management**: Automatic device detection and configuration
- **Console Commands**: Extensive command-line interface for control

## Configuration

### Device Settings

The module provides comprehensive configuration options:

```python
# Example device registration choices
choices = [
    {
        "attr": "laser_type",
        "object": self,
        "default": "fiber",
        "type": str,
        "choices": ["fiber", "co2", "uv"],
        "label": _("Laser Type"),
        "section": "_10_Balor"
    },
    {
        "attr": "max_power",
        "object": self,
        "default": 100.0,
        "type": float,
        "label": _("Maximum Power %"),
        "section": "_10_Balor"
    }
]
```

### Hardware Parameters

- **Galvo Calibration**: XY positioning correction matrices
- **Laser Parameters**: Power curves, pulse characteristics
- **Timing Settings**: Command delays, synchronization
- **Safety Limits**: Power and speed constraints

## Usage Examples

### Basic Device Setup

```python
# Register Balor device
kernel.register("provider/device/balor", BalorDevice)

# Activate device service
kernel.activate("balor", balor_device)
```

### Connection Management

```python
# Windows: Automatic connection with Direct Driver first, LibUSB fallback
controller.connect_if_needed()

# Check connection type
if hasattr(controller.connection, 'is_direct_connection'):
    if controller.connection.is_direct_connection:
        print("Using Direct Windows Driver")
    else:
        print("Using LibUSB Connection")
```

### Direct Driver Testing (Windows)

```python
# Test direct Windows driver communication
from meerk40t.balormk.direct_usb_connection import DirectUSBConnection

try:
    connection = DirectUSBConnection()
    if connection.find_device():
        print("Direct driver connection successful")
        # Send test command
        test_data = bytes([0x1B, 0x00, 0x01, 0x02, 0x03, 0x04])
        response = connection.write(test_data)
        print(f"Response: {response}")
    else:
        print("Device not found via direct driver")
except Exception as e:
    print(f"Direct connection failed: {e}")
```

### Console Commands

```bash
# List available Balor commands
balor list

# Start device connection
balor connect

# Execute light operations
balor light <x> <y> <power>
```

### Cutcode Processing

```python
# Process cutcode operations
driver.process_cutcode(cutcode_list)

# Execute marking job
controller.execute_job(job_data)
```

## GUI Integration

The module provides several GUI panels:

- **Configuration Panel**: Device settings and hardware parameters
- **Controller Panel**: Real-time status monitoring and control
- **Operation Properties**: Laser-specific operation settings
- **Coordinate Scene**: Visual coordinate system calibration

## Troubleshooting

### Connection Issues

#### Direct Windows Driver Problems

**Symptom**: Direct connection fails, falls back to LibUSB
```
Possible causes:
1. EzCAD2 currently running and has exclusive device access
2. Windows Setup API cannot find device
3. Lmcv4u.sys driver not properly installed
4. Device not recognized by Windows
```

**Solutions**:
1. **Close EzCAD2**: Ensure EzCAD2 is completely closed before connecting
2. **Device Manager Check**: Verify device appears in Device Manager without errors
3. **Driver Reinstall**: Reinstall original manufacturer drivers if needed
4. **USB Port**: Try different USB port or cable

#### LibUSB Connection Problems

**Symptom**: Both direct and LibUSB connections fail
```
Common issues:
1. Driver conflicts between Zadig and original drivers
2. Device permissions on Linux/macOS
3. USB enumeration problems
```

**Solutions**:
1. **Windows**: Use Zadig to replace driver with libusb-win32
2. **Linux**: Check udev rules for device permissions
3. **macOS**: Verify System Integrity Protection settings

### Performance Issues

#### Slow Communication

**Check connection type first**:
```python
# In MeerK40t console
balor status
```

**Direct Connection**: Should show minimal latency
**LibUSB Connection**: May have higher latency but should be stable

#### Command Timeouts

**Increase timeout values** in device settings:
- USB Read Timeout
- Command Response Timeout
- Device Initialize Timeout

### Platform-Specific Notes

#### Windows

- **Direct driver** provides best performance and EzCAD2 compatibility
- **LibUSB fallback** requires Zadig driver replacement
- **Mixed environments** work seamlessly with automatic detection

#### Linux

- Only LibUSB connection available
- Requires proper udev rules for device access
- No driver replacement needed

#### macOS

- LibUSB connection with potential permission requirements
- May require disabling System Integrity Protection for some operations

## Development Notes

### Threading Model

- **Main Thread**: UI and kernel communication
- **Controller Thread**: Hardware communication and command processing
- **Driver Thread**: Cutcode translation and optimization

### Error Handling

- **USB Communication**: Robust error recovery and reconnection
- **Hardware Limits**: Automatic constraint checking and warnings
- **Status Monitoring**: Comprehensive error reporting and diagnostics

### Testing

- **Mock Connection**: `mock_connection.py` for offline testing
- **Unit Tests**: Comprehensive test coverage in `test_drivers_galvo.py`
- **Integration Tests**: End-to-end hardware validation

## Licensing

Balor's original code was GPL licenced but was completely scrapped in pieces over time for this project. The new code still uses the name balor but was recoded from scratch based on various needs. For example the old balor code wasn't well suited to run uncompleted code and send packets while code in another thread is building that data. The replacement uses the name balor but is only based on some of the original research and none of the original code, outside of sections which were written specifically by me (Tatarize) originally anyway. 
