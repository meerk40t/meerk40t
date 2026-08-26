# Moshi - Moshiboard Laser Controller Module

## Overview

Moshiboard classes are intended to deal with USB interactions to and from the CH341 chips on Moshiboards over USB. This
is the result of `Project Moshi` which sought to reverse engineer the Moshiboard interactions and control them with
MeerK40t. Thanks to a generous donation of a Moshiboard by Domm434 ( https://forum.makerforums.info/u/domm434 ).
MeerK40t is now compatible with Moshiboards.

The Moshi module provides comprehensive support for Moshiboard laser controllers, specifically the MS10105 (V.4.XX) series used in older CO2 laser cutters. This module implements the complete MeerK40t device driver pattern with device service, driver, and controller components for robust Moshi protocol handling and hardware control.

## Architecture

### Core Components

- **`device.py`** - Main MoshiDevice service class
  - Inherits from MeerK40t Service and Status classes
  - Manages device lifecycle, configuration, and console commands
  - Extensive settings registration for bed dimensions, scaling, and USB parameters
  - Supports USB (CH341) communication and mock mode for testing

- **`driver.py`** - MoshiDriver implementation
  - Translates MeerK40t cutcode operations to Moshi protocol commands
  - Handles laser power control, movement commands, and coordinate transformations
  - Implements cutcode processing pipeline for vector and raster operations
  - Manages real-time commands and hardware-specific optimizations

- **`controller.py`** - MoshiController class
  - Implements Moshi protocol communication and USB data transmission
  - Manages thread-safe data transmission with proper synchronization
  - Handles command queuing, status monitoring, and error recovery
  - Processes real-time commands including emergency stop functionality

- **`builder.py`** - MoshiBuilder command construction
  - Builds Moshi protocol command data with swizzling tables
  - Handles data encoding and packet formatting
  - Implements preamble/epilogue framing for program data
  - Manages complex data transformation for Moshi protocol

- **`plugin.py`** - Device registration and lifecycle management
  - Registers MoshiDevice with MeerK40t kernel
  - Configures device-specific settings and capabilities
  - Provides console commands for device control

### Supporting Files

- **GUI Components (`gui/`)**:
  - **`gui.py`** - Main GUI integration and panel registration
  - **`moshicontrollergui.py`** - Controller status and monitoring panels
  - **`moshidrivergui.py`** - Driver configuration and settings panels

## Hardware Support

### Supported Controllers

- **Moshiboard MS10105 (V.4.XX)**: Original Moshiboard series
  - Popular around 2013 with red PCBs and large black heatsinks
  - Uses CH341 Universal Interface Chip for USB communication
  - Dual stepper motor chips with heat sink cooling

### Connection Interfaces

- **USB (CH341)**: Direct USB connection using CH341 chipset
- **Mock**: Simulation mode for testing and development

### Laser Types

- **CO2 Lasers**: Infrared gas lasers for organic materials
- **Compatible Systems**: Older CO2 laser cutters using Moshiboard controllers

## Technical Features

### Moshi Protocol

The module implements the proprietary Moshi protocol including:

- **Data Swizzling**: Complex data transformation using lookup tables
- **Packet Framing**: Preamble and epilogue data framing
- **Status Monitoring**: Device state tracking (OK=205, PROCESSING=207, ERROR=237)
- **Real-time Commands**: Emergency stop and status queries
- **Buffer Management**: Thread-safe command queuing and transmission

### Data Swizzling

Moshiboard uses a sophisticated data swizzling system:

```python
# Swizzle table example - converts data for Moshi protocol
swizzle_table = [
    [b"\x00", b"\x01", b"\x40", ...],  # Table 0
    [b"\x08", b"\x11", b"\x48", ...],  # Table 1
    [b"\x80", b"\x05", b"\xc0", ...],  # Table 2
    # ... additional tables
]
```

### Status Codes

Device status monitoring with specific codes:

- **STATUS_OK (205)**: Device ready to accept commands
- **STATUS_PROCESSING (207)**: Device currently processing data
- **STATUS_ERROR (237)**: Error occurred during processing
- **STATUS_RESET (239)**: Device has been reset

### Threading Model

- **Main Processing Thread**: Handles data transmission and synchronization
- **Real-time Commands**: Can interrupt normal processing for emergency operations
- **Buffer Protection**: Central lock protects all buffer/program access
- **Connection Safety**: Thread-safe connection operations

## Configuration

### Bed Dimensions

```python
bedwidth: "330mm"           # Laser bed width
bedheight: "210mm"          # Laser bed height
laserspot: "0.3mm"          # Laser spot size
```

### Coordinate Scaling

```python
scale_x: 1.000              # X-axis scaling factor
scale_y: 1.000              # Y-axis scaling factor
flip_x: False               # X-axis direction flip
flip_y: False               # Y-axis direction flip
swap_xy: False              # Swap X and Y axes
```

### USB Configuration

```python
usb_index: -1               # USB device index (-1 for auto)
usb_bus: -1                 # USB bus number
usb_address: -1             # USB device address
usb_version: -1             # USB version
```

### Jog Settings

```python
opt_rapid_between: True     # Rapid moves between objects
opt_jog_mode: 0             # Jog method selection
opt_jog_minimum: 256        # Minimum distance for rapid jog
```

### Raster Settings

```python
enable_raster: True         # Enable raster operations
legacy_raster: True         # Use legacy raster method
interp: 5                   # Curve interpolation distance (mils)
```

### Performance Settings

```python
rapid_speed: 40             # Rapid movement speed
mock: False                 # Enable mock USB backend
signal_updates: True        # Enable device position updates
```

## Usage Examples

### Basic Device Setup

```python
# Register Moshi device
kernel.register("provider/device/moshi", MoshiDevice)

# Activate device service
kernel.activate("moshi", moshi_device)
```

### Console Commands

```bash
# USB connection management
usb_connect
usb_disconnect

# Controller control
start
hold
resume
abort

# Status monitoring
status

# Continue waiting process
continue
```

### File Operations

```bash
# Export job as Moshi format
save_job filename.mos
```

## Device Variants

### Pre-configured Devices

- **Moshiboard CO2**: Standard Moshiboard MS10105 configuration
  - 330x210mm bed dimensions
  - CH341 USB interface
  - CO2 laser compatibility

### Custom Configuration

Devices can be customized through extensive choice dictionaries supporting:

- Bed dimensions and laser characteristics
- USB device selection and configuration
- Coordinate scaling and axis corrections
- Raster processing options
- Performance and speed settings

## GUI Integration

The module provides several GUI panels:

- **Configuration Panel**: Device settings and USB parameters
- **Controller Panel**: Real-time status monitoring and USB control
- **Driver Panel**: Speed, power, and processing settings

## File Formats

### Supported Formats

- **MOS (.mos)**: Native Moshiboard format
- **MeerK40t Projects**: Native .mk files with MOS export
- **Vector Graphics**: SVG, DXF with MOS conversion

### MOS File Structure

Binary format with swizzled data and protocol framing.

## Performance Optimization

### Buffer Management

- **Thread-safe Queuing**: Protected access to command buffers
- **Status Monitoring**: Real-time device state tracking
- **Error Recovery**: Automatic retry and connection management

### Data Processing

- **Swizzle Optimization**: Efficient data transformation tables
- **Packet Batching**: Optimized USB packet transmission
- **Real-time Interrupts**: Emergency command processing

## Development Notes

### Protocol Implementation

- **Reverse Engineering**: Based on Project Moshi reverse engineering efforts
- **Data Transformation**: Complex swizzling algorithm for data encoding
- **Status Monitoring**: Comprehensive device state tracking
- **Error Handling**: Robust error recovery and connection management

### Threading Model

- **Processing Thread**: Main data transmission and synchronization
- **Real-time Thread**: Emergency command processing
- **Buffer Locks**: Thread-safe access to all data structures
- **Connection Safety**: Protected USB operations

### Hardware Compatibility

- **CH341 Chip**: Universal interface chip for USB communication
- **MS10105 Boards**: Specific board revision support
- **Legacy Systems**: Older CO2 laser cutter compatibility

### Testing

- **Mock Backend**: `mock=True` for offline testing
- **USB Simulation**: Software emulation of Moshiboard responses
- **Protocol Validation**: Command encoding and decoding verification

## Troubleshooting

### Common Issues

- **USB Connection**: Verify CH341 drivers and USB device detection
- **Data Corruption**: Check swizzling table integrity
- **Status Errors**: Monitor device status codes and error conditions
- **Buffer Issues**: Ensure proper thread synchronization

### Diagnostic Commands

```bash
# Check device status
status

# Test USB connection
usb_connect

# Monitor processing
# (Check controller state and buffer status)
```

### Firmware Compatibility

- **MS10105 V.4.XX**: Primary supported firmware version
- **CH341 Drivers**: Required for USB communication
- **Legacy Hardware**: Older Moshiboard series support

## Integration with MeerK40t

### Kernel Services

- **Device Service**: Full device lifecycle management
- **Spooler Integration**: Job queuing and execution
- **Cutcode Processing**: Native cutcode to Moshi protocol translation
- **CH341 Interface**: USB communication via CH341 chipset

### Signal System

- **Status Updates**: Real-time device state reporting
- **Configuration Changes**: Dynamic parameter updates
- **Error Notifications**: Hardware error and communication failure signaling

This module provides MeerK40t with comprehensive Moshiboard support, enabling reliable communication with older CO2 laser systems through the reverse-engineered Moshi protocol.
