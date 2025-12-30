# GRBL - G-Code Laser Controller Module

## Overview

Provides and registers the GRBL driver for meerk40t.

The GRBL module implements comprehensive support for GRBL (G-code based laser controller) devices, enabling MeerK40t to communicate with a wide variety of CNC laser cutters and engravers. This module follows the standard MeerK40t device driver pattern with device service, driver, and controller components for robust G-code generation and hardware control.

https://github.com/gnea/grbl/wiki

## Architecture

### Core Components

- **`device.py`** - Main GRBLDevice service class
  - Inherits from MeerK40t Service and Status classes
  - Manages device lifecycle, configuration, and console commands
  - Extensive settings registration for bed dimensions, scaling, and hardware parameters
  - Supports multiple connection interfaces (serial, TCP, WebSocket)I would remove e

- **`driver.py`** - GRBLDriver implementation
  - Translates MeerK40t cutcode operations to G-code commands
  - Handles laser power control, movement commands, and coordinate transformations
  - Implements cutcode processing pipeline for vector and raster operations
  - Manages real-time commands and status monitoring

- **`controller.py`** - GRBLController class
  - Implements GRBL protocol communication and validation
  - Manages connection state through validation stages (0-5)
  - Handles command queuing, response parsing, and error recovery
  - Supports multiple connection types with automatic detection

- **`plugin.py`** - Device registration and lifecycle management
  - Registers multiple GRBL device variants with MeerK40t kernel
  - Configures device-specific settings and capabilities
  - Provides console commands for device control and emulation

### Supporting Files

- **`serial_connection.py`** - Serial communication using pyserial
- **`tcp_connection.py`** - TCP network communication
- **`ws_connection.py`** - WebSocket communication
- **`mock_connection.py`** - Simulation interface for testing
- **`emulator.py`** - GRBL device emulation for compatibility testing
- **`gcodejob.py`** - G-code job processing and export
- **`interpreter.py`** - Interactive GRBL command interpreter
- **`loader.py`** - G-code file loading and parsing
- **`control.py`** - GRBL control server for remote access
- **`esp3d_upload.py`** - ESP3D-WEBUI file upload and execution (see [ESP3D_README.md](ESP3D_README.md))

### GUI Components (`gui/`)

- **`gui.py`** - Main GUI integration and panel registration
- **`grblconfiguration.py`** - Device configuration interface
- **`grblcontroller.py`** - Controller status and monitoring panels
- **`grblhardwareconfig.py`** - Hardware parameter configuration
- **`grbloperationconfig.py`** - Operation-specific settings panels
- **`esp3dconfig.py`** - ESP3D upload configuration panel

## Hardware Support

### Supported GRBL Variants

- **Generic GRBL**: Standard GRBL implementation for CNC controllers
- **FluidNC**: ESP32-based GRBL-compatible controllers
- **K40 CO2 Lasers**: Modified GRBL controllers for CO2 laser cutters
- **Diode Lasers**: Various inexpensive GRBL-based diode laser systems
- **Ortur Laser Master 2**: Ortur-branded GRBL diode lasers
- **Longer Ray5**: Longer-branded 5W/10W/20W GRBL diode lasers

### Connection Interfaces

- **Serial (USB)**: Direct USB connection using pyserial
- **TCP Network**: Network connection to GRBL devices over TCP
- **WebSocket**: WebSocket-based communication for web interfaces
- **ESP3D Upload**: Wireless file upload to ESP3D-equipped devices (see [ESP3D_README.md](ESP3D_README.md))
- **Mock**: Simulation mode for testing and development

### Laser Types

- **CO2 Lasers**: Infrared gas lasers for organic materials
- **Diode Lasers**: Semiconductor lasers for various applications
- **Multi-source Support**: Configurable for different laser technologies

## Technical Features

### G-Code Implementation

The driver implements comprehensive G-code support including:

- **Movement Commands**: G0/G1 for rapid/linear movement
- **Coordinate Systems**: Absolute (G90) and relative (G91) positioning
- **Laser Control**: M3/M4 for spindle/laser activation
- **Power Modulation**: S-parameter for laser power control
- **Feed Rates**: F-parameter for movement speed
- **Dwell Commands**: G4 for timed pauses

### Cutcode Processing

- **Vector Operations**: Line, curve, and complex path processing
- **Raster Operations**: Image engraving with power modulation
- **Travel Optimization**: Minimizes non-cutting movement
- **Power Control**: Dynamic laser power adjustment
- **Speed Control**: Adaptive feed rate management

### Real-time Commands

- **Status Queries**: `?` command for position and state information
- **Feed Hold**: `!` command for pausing operations
- **Resume**: `~` command for continuing paused operations
- **Soft Reset**: Ctrl+X for emergency stop
- **Jogging**: `$J` commands for manual positioning

## Configuration

### Device Settings

The module provides extensive configuration options:

#### Bed Dimensions
```python
bedwidth: "235mm"    # Laser bed width
bedheight: "235mm"   # Laser bed height
laserspot: "0.3mm"   # Laser spot size
```

#### Coordinate Scaling
```python
scale_x: 1.000       # X-axis scaling factor
scale_y: 1.000       # Y-axis scaling factor
flip_x: False        # X-axis direction flip
flip_y: True         # Y-axis direction flip (GRBL standard)
swap_xy: False       # Swap X and Y axes
```

#### Homing Configuration
```python
home_corner: "auto"  # Home position (auto/top-left/top-right/bottom-left/bottom-right/center)
has_endstops: False  # Device has endstop switches
z_home_command: "$HZ" # Z-axis homing command
```

#### Speed Limits
```python
max_vector_speed: 140    # Maximum vector cutting speed (mm/min)
max_raster_speed: 750    # Maximum raster engraving speed (mm/min)
rapid_speed: 600         # Travel speed between operations (mm/min)
```

#### Buffer Management
```python
limit_buffer: True       # Enable controller buffer limiting
max_buffer: 200          # Maximum buffer size (lines)
buffer_mode: "buffered"  # buffered/sync sending mode
```

### Connection Settings

#### Serial Interface
```python
serial_port: "COM1"      # Serial port (auto-detected)
baud_rate: 115200        # Communication baud rate
```

#### Network Interface
```python
address: "localhost"     # TCP/WebSocket host address
port: 23                 # TCP port (23) or WebSocket port (81)
```

#### Protocol Settings
```python
line_end: "CR"           # Line ending (CR/LF/CRLF)
planning_buffer_size: 128 # GRBL planning buffer size
connect_delay: 0         # Delay after connection (ms)
```

## Usage Examples

### Basic Device Setup

```python
# Register GRBL device
kernel.register("provider/device/grbl", GRBLDevice)

# Activate device service
kernel.activate("grbl", grbl_device)
```

### Console Commands

```bash
# Send raw G-code
gcode G0 X0 Y0

# Send realtime G-code
gcode_realtime M3 S1000

# Query status
gcode ?

# Emergency stop
soft_reset

# Clear alarm
clear_alarm

# Pause/resume
pause

# Manual jogging
grbl_binds  # Setup WASD keys for jogging
```

### Red Dot Feature

```bash
# Enable red dot for positioning
red on

# Set red dot power level
red on -s 300

# Disable red dot
red off
```

### Pulse Laser

```bash
# Pulse laser for 100ms at 50% power
pulse 100 -p 50%

# Override safety limit (dangerous)
pulse 2000 -p 1000 --idonotlovemyhouse
```

### Device Control

```bash
# Home device
gcode $H

# Set work coordinates to current position
gcode G92 X0 Y0 Z0

# Enable laser mode
gcode $32=1
```

## GUI Integration

The module provides several GUI panels:

- **Configuration Panel**: Device settings and connection parameters
- **Controller Panel**: Real-time status monitoring and control
- **Hardware Config**: GRBL parameter configuration ($ settings)
- **Operation Config**: Laser operation settings and power curves

## Device Variants

### Pre-configured Devices

- **Generic GRBL**: Basic GRBL controller setup
- **GRBL-FluidNC**: ESP32-based FluidNC controllers
- **GRBL-K40-CO2**: K40 laser with GRBL controller (235x235mm bed)
- **GRBL-Diode**: Generic diode laser configurations
- **GRBL-Ortur-LM2**: Ortur Laser Master 2 (400x430mm bed)
- **GRBL-Longer-Ray5**: Longer Ray5 series (450x450mm bed)

### Custom Configuration

Devices can be customized through extensive choice dictionaries supporting:

- Bed dimensions and laser spot size
- Axis scaling and flipping
- Homing behavior and endstop configuration
- Speed limits and buffer management
- Connection parameters and protocol settings

## Development Notes

### Connection Validation

The controller implements a 6-stage validation process:

1. **Disconnected**: Invalid connection state
2. **Connected**: Basic connection established
3. **GRBL Check**: Send `$` command for GRBL identification
4. **Settings Parse**: Parse `$$` settings response
5. **G-code Parse**: Parse `$G` modal state response
6. **Status Query**: Parse `?` status response

### Error Handling

- **Serial Exceptions**: Automatic reconnection on communication errors
- **Buffer Overflow**: Command queuing with size limits
- **Protocol Errors**: Response validation and retry logic
- **Hardware Alarms**: Alarm state detection and clearing

### Threading Model

- **Main Thread**: UI and kernel communication
- **Controller Thread**: Hardware communication and response processing
- **Driver Thread**: G-code generation and cutcode processing

### Testing

- **Mock Connection**: `mock_connection.py` for offline testing
- **Emulator**: `emulator.py` for GRBL device simulation
- **Unit Tests**: Comprehensive test coverage in `test_drivers_grbl.py`
- **Integration Tests**: Hardware validation and protocol testing

## File Formats

### Supported Input Formats

- **G-code**: Standard `.gcode`, `.nc`, `.tap` files
- **MeerK40t Projects**: Native `.mk` files with GRBL export
- **Vector Graphics**: SVG, DXF with G-code conversion

### Export Capabilities

```bash
# Export job as G-code file
save_job filename.gcode
```

## Performance Optimization

### Command Batching

- **Buffer Management**: Prevents controller overflow
- **Planning Ahead**: Pre-calculates movement commands
- **Real-time Commands**: Immediate execution for critical operations

### Motion Control

- **Curve Interpolation**: Smooth curve approximation
- **Travel Optimization**: Minimizes rapid movements
- **Power Ramping**: Gradual power changes to prevent artifacts

## Troubleshooting

### Common Issues

- **Connection Problems**: Check serial port settings and baud rate
- **Buffer Errors**: Reduce buffer size or increase planning buffer
- **Position Errors**: Verify axis scaling and homing configuration
- **Power Issues**: Check M3/M4 mode and S-parameter scaling

### Diagnostic Commands

```bash
# View GRBL settings
gcode $$

# Check modal state
gcode $G

# Query current status
gcode ?

# View build info
gcode $I
```

## Integration with MeerK40t

### Kernel Services

- **Device Service**: Full device lifecycle management
- **Spooler Integration**: Job queuing and execution
- **Cutcode Processing**: Native cutcode to G-code translation
- **Settings Management**: Persistent configuration storage

### Signal System

- **Status Updates**: Real-time position and state reporting
- **Error Notifications**: Hardware error and alarm signaling
- **Configuration Changes**: Dynamic reconfiguration support

This module provides MeerK40t with comprehensive GRBL controller support, enabling reliable communication with a wide variety of G-code based laser systems.

