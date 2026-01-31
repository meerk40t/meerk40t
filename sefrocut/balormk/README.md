# BalorMK - JCZ Galvo Laser Controller Module

## Overview

BalorMK began life as the sefrocut plugin-driver for Balor by Bryce Schroeder which controls the LMC ezcad2 galvo laser boards. This was eventually rewritten but still uses many of the original names. Even as the backend was rewritten.

The BalorMK module provides comprehensive support for JCZ Technologies galvo laser controllers, including the EZCAD2 series and compatible devices. It implements the complete SefroCut device driver pattern with device service, driver, and controller components for high-performance galvo laser control.

## Architecture

### Core Components

- **`device.py`** - Main BalorDevice service class (1136 lines)
  - Inherits from SefroCut Service and Status classes
  - Manages device lifecycle, settings, and console commands
  - Registers device choices for configuration panels
  - Handles device activation and service integration

- **`driver.py`** - BalorDriver implementation (795 lines)
  - Translates SefroCut cutcode operations to galvo commands
  - Manages laser power control, timing, and positioning
  - Implements cutcode processing pipeline for vector operations
  - Handles hardware-specific optimizations

- **`controller.py`** - GalvoController class (1650 lines)
  - Implements LMC (Laser Marking Controller) command protocol
  - Manages USB communication with galvo controllers
  - Processes command queues and hardware responses
  - Handles real-time control and status monitoring

- **`plugin.py`** - Device registration and plugin lifecycle
  - Registers BalorDevice with SefroCut kernel
  - Supports multiple JCZ controller variants
  - Configures device capabilities and settings

### Supporting Files

- **`balor_params.py`** - Hardware parameter definitions and calibration data
- **`galvo_commands.py`** - LMC command structure definitions
- **`usb_connection.py`** - USB communication layer using pyusb
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

- **USB Communication**: High-speed USB interface using pyusb/libusb
- **EPP 1.9 Protocol**: Enhanced Parallel Port protocol for legacy support
- **Real-time Control**: Low-latency command processing for precise timing

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

- **SefroCut Kernel**: Full service integration with kernel channels and settings
- **Cutcode Processing**: Compatible with SefroCut's cutcode data structures
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
