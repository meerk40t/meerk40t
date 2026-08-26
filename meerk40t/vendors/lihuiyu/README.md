# Lihuiyu - M2/M3 Nano Laser Controller Module

## Overview

Driver for the M2/M3 Nano boards by Lihuiyu and other closely related boards. This is the primary user of CH341
interfacing drivers. And the most complete driver available. This includes parsing of Lhymicro-GL, production of
Lhymicro-GL, channels of the data being sent over the USB, as well as emulation and parsing the commands.

The Lihuiyu module provides comprehensive support for Lihuiyu Studios Labs laser controllers, including the M2 Nano and M3 Nano series used in K40 CO2 laser cutters. This module implements the complete MeerK40t device driver pattern with device service, driver, and controller components for robust LHYMicro-GL protocol handling and hardware control.

## Architecture

### Core Components

- **`device.py`** - Main LihuiyuDevice service class
  - Inherits from MeerK40t Service and Status classes
  - Manages device lifecycle, configuration, and console commands
  - Extensive settings registration for board-specific parameters
  - Supports USB (CH341) and TCP network connections

- **`driver.py`** - LihuiyuDriver implementation
  - Translates MeerK40t cutcode operations to LHYMicro-GL commands
  - Handles laser power control, movement commands, and speed codes
  - Implements cutcode processing pipeline for vector and raster operations
  - Manages real-time commands and hardware-specific optimizations

- **`controller.py`** - LihuiyuController class
  - Implements LHYMicro-GL protocol communication and packet handling
  - Manages USB communication via CH341 interface
  - Handles command queuing, response parsing, and error recovery
  - Processes real-time commands and status monitoring

- **`plugin.py`** - Device registration and lifecycle management
  - Registers M2 and M3 Nano device variants with MeerK40t kernel
  - Configures device-specific settings and capabilities
  - Provides console commands for device control and emulation

### Supporting Files

- **`parser.py`** - LHYMicro-GL code parser and state machine
- **`laserspeed.py`** - Speed code conversion and acceleration calculations
- **`tcp_connection.py`** - TCP network communication for remote control
- **`interpreter.py`** - Interactive LHYMicro-GL command interpreter
- **`loader.py`** - EGV file loading and parsing
- **`emulator.py`** - Lihuiyu device emulation for testing

### GUI Components (`gui/`)

- **`gui.py`** - Main GUI integration and panel registration
- **`lhycontrollergui.py`** - Controller status and monitoring panels
- **`lhydrivergui.py`** - Driver configuration and settings panels
- **`lhyoperationproperties.py`** - Operation-specific property panels
- **`lhyaccelgui.py`** - Acceleration and speed configuration
- **`tcpcontroller.py`** - TCP connection management interface

## Hardware Support

### Supported Controllers

- **M2 Nano**: Original Lihuiyu controller (green/blue board)
  - Used in most K40 laser cutters
  - Revision 6C6879-LASER-M2:9
  - Basic speed code support

- **M3 Nano**: Enhanced Lihuiyu controller (purple/blue board)
  - Revision 6C6879-LASER-M3:10
  - Hardware PWM support for laser power control
  - Pause button multiplexing
  - M3 Nano Plus with TMC stepper chips

- **Compatible Variants**: B2, M, M1, A, B, B1 boards
  - Various Lihuiyu Studios Labs controller revisions
  - Different acceleration and speed characteristics

### Connection Interfaces

- **USB (CH341)**: Direct USB connection using CH341 chipset
- **TCP Network**: Network connection for remote control
- **Mock**: Simulation mode for testing and development

### Laser Types

- **CO2 Lasers**: Infrared gas lasers for organic materials
- **Diode Lasers**: Semiconductor lasers (with appropriate controllers)
- **Multi-source Support**: Configurable for different laser technologies

## Technical Features

### LHYMicro-GL Protocol

The module implements the complete LHYMicro-GL protocol including:

- **Movement Commands**: Absolute and relative positioning
- **Laser Control**: Power modulation via speed codes and PWM
- **Speed Codes**: Acceleration-based velocity control (1-4 levels)
- **Raster Operations**: Image engraving with bidirectional scanning
- **Real-time Commands**: Pause, resume, abort, and status queries

### Speed Code System

Lihuiyu controllers use a proprietary speed code system:

```python
# Speed code calculation example
# For M2 board: value = 65536 - (5120 + 12120 * period_ms)
# Encoded as two 3-digit ASCII values (0-255)
# CV1410801 - speed code for ~12.7 mm/s with acceleration factor 1
```

**Acceleration Levels:**
- **Level 1**: 0-25.4 mm/s (slow speeds)
- **Level 2**: 25.4-60 mm/s (medium speeds)
- **Level 3**: 60-127 mm/s (fast speeds)
- **Level 4**: 127+ mm/s (maximum speeds)

### PWM Support (M3 Only)

Hardware PWM laser power control for M3 Nano boards:

```python
# PWM configuration
supports_pwm: True          # Hardware PWM capability
pwm_speedcode: False        # Use PWM in speed codes
power_scale: 30             # Maximum power percentage
```

### Packet Protocol

USB communication uses 30-byte packets with confirmation:

- **Packet Size**: 30 bytes maximum
- **Confirmation**: Device acknowledges each packet
- **Error Recovery**: Automatic retry on failed transmissions
- **Status Codes**: Device state reporting (OK=206, BUSY=238, FINISH=236)

## Configuration

### Board Selection

```python
board: "M2"                 # Controller board type (M2, M3, B2, M, M1, A, B, B1)
```

### Bed Dimensions

```python
bedwidth: "310mm"           # Laser bed width
bedheight: "210mm"          # Laser bed height
laserspot: "0.3mm"          # Laser spot size
```

### Coordinate Scaling

```python
user_scale_x: 1.000         # X-axis scaling factor
user_scale_y: 1.000         # Y-axis scaling factor
flip_x: False               # X-axis direction flip
flip_y: False               # Y-axis direction flip
swap_xy: False              # Swap X and Y axes
```

### Speed and Power Limits

```python
max_vector_speed: 140       # Maximum vector cutting speed (mm/min)
max_raster_speed: 750       # Maximum raster engraving speed (mm/min)
power_scale: 30             # Maximum laser power percentage (M3 PWM)
```

### Plot Planner Settings

```python
plot_phase_type: 0          # PPI carry-forward algorithm (Sequential/Random/Progressive/Static)
plot_shift: False           # Pulse grouping for reduced stuttering
strict: False               # Force directional speed mode changes
twitches: False             # Enable unnecessary directional moves
```

### Jog Settings

```python
opt_rapid_between: True     # Rapid moves between objects
opt_jog_minimum: 256        # Minimum distance for rapid jog
opt_jog_mode: 0             # Jog method (Default/Reset/Finish)
```

### Rapid Override

```python
rapid_override: False       # Override rapid movement speeds
rapid_override_speed_x: 50.0 # X-axis rapid speed (mm/min)
rapid_override_speed_y: 50.0 # Y-axis rapid speed (mm/min)
```

## Usage Examples

### Basic Device Setup

```python
# Register Lihuiyu device
kernel.register("provider/device/lhystudios", LihuiyuDevice)

# Activate device service
kernel.activate("lhystudios", lihuiyu_device)
```

### Console Commands

```bash
# Send LHYMicro-GL commands
egv IABC123

# Challenge code for serial validation
challenge ABC123

# Pulse laser
pulse 100 -p 50%

# Set driver speed
device_speed 25.4

# Set driver power
power 500

# Set acceleration level
acceleration 2

# Start/stop controller
start
hold
resume

# USB connection management
usb_connect
usb_disconnect
usb_reset
usb_release
```

### File Operations

```bash
# Export job as EGV file
save_job filename.egv

# Import EGV file
egv_import filename.egv

# Export current buffer
egv_export filename.egv
```

### Network Control

```bash
# Start TCP server for remote control
lhyserver -p 23

# Enable network mode
device.networked = True
```

## Device Variants

### Pre-configured Devices

- **M2-Nano**: Standard K40 controller (green/blue board)
  - 310x210mm bed dimensions
  - Basic speed code support
  - No hardware PWM

- **M3-Nano**: Enhanced K40 controller (purple/blue board)
  - Hardware PWM support
  - Pause button functionality
  - Improved stepper control

### Custom Configuration

Devices can be customized through extensive choice dictionaries supporting:

- Board type selection and firmware variants
- Bed dimensions and laser characteristics
- Speed limits and acceleration settings
- Network vs USB communication modes
- PWM and power control options

## GUI Integration

The module provides several GUI panels:

- **Configuration Panel**: Device settings and board parameters
- **Controller Panel**: Real-time status monitoring and USB control
- **Driver Panel**: Speed, power, and acceleration settings
- **Operation Properties**: Laser operation parameters
- **Acceleration GUI**: Speed code and acceleration configuration
- **TCP Controller**: Network connection management

## File Formats

### Supported Formats

- **EGV (.egv)**: Native Lihuiyu engraving format
- **MeerK40t Projects**: Native .mk files with EGV export
- **G-code**: Limited G-code compatibility
- **Vector Graphics**: SVG, DXF with EGV conversion

### EGV File Structure

```
Document type : LHYMICRO-GL file
File version: 1.0.01
Copyright: Unknown
Creator-Software: MeerK40t v{version}

%0%0%0%0%
{LHYMicro-GL commands}
```

## Performance Optimization

### Pulse Grouping

Reduces laser stuttering by grouping on/off pulses:

```python
plot_shift: True  # Enable pulse grouping
# Converts X_X_ to XX__ for smoother operation
```

### Acceleration Management

Automatic acceleration level selection based on speed:

- **Non-Raster**: 4 acceleration levels (25.4mm/s breakpoints)
- **Raster**: 3 acceleration levels (127mm/s breakpoints)
- **Ramping Distance**: 128-256 mil acceleration/deceleration zones

### Buffer Management

```python
buffer_max: 900              # Maximum buffer size
buffer_limit: True           # Enable buffer limiting
```

## Development Notes

### Protocol Implementation

- **State Machine**: Parser uses state diagram for LHYMicro-GL interpretation
- **Packet Handling**: 30-byte USB packets with confirmation protocol
- **Real-time Commands**: Immediate execution for pause/resume/abort
- **Error Recovery**: Automatic retry and reconnection logic

### Threading Model

- **Main Thread**: UI and kernel communication
- **Controller Thread**: USB communication and packet processing
- **Driver Thread**: LHYMicro-GL generation and cutcode processing

### Hardware Variants

Different board revisions have varying capabilities:

- **M2 Series**: Basic speed code support, no PWM
- **M3 Series**: Hardware PWM, enhanced features
- **B-Series**: Alternative stepper configurations
- **Firmware Variants**: Different acceleration characteristics

### Testing

- **Mock Connection**: `mock_connection.py` for offline testing
- **Emulator**: Device simulation for protocol validation
- **Interpreter**: Interactive command testing
- **Unit Tests**: Comprehensive test coverage in `test_drivers_lihuiyu.py`

## Troubleshooting

### Common Issues

- **USB Connection**: Verify CH341 drivers and USB permissions
- **Speed Accuracy**: Lihuiyu speeds are ~92% of requested (use fix_speeds correction)
- **Buffer Errors**: Reduce buffer size or check USB stability
- **PWM Issues**: Ensure M3 board and compatible firmware
- **Network Mode**: Check TCP port availability and firewall settings

### Diagnostic Commands

```bash
# Check device status
status

# Test USB connection
usb_connect
usb_reset

# Validate speed codes
device_speed 25.4

# Check buffer state
# (Monitor controller buffer usage)
```

### Firmware Compatibility

- **M2 Boards**: All firmware versions supported
- **M3 Boards**: Firmware >= 2024.01.18g required for PWM
- **Board Detection**: Automatic board type identification
- **Speed Correction**: Optional 92% speed factor correction

## Integration with MeerK40t

### Kernel Services

- **Device Service**: Full device lifecycle management
- **Spooler Integration**: Job queuing and execution
- **Cutcode Processing**: Native cutcode to LHYMicro-GL translation
- **CH341 Interface**: USB communication via CH341 chipset

### Signal System

- **Status Updates**: Real-time device state reporting
- **Configuration Changes**: Dynamic parameter updates
- **Error Notifications**: Hardware error and communication failure signaling

This module provides MeerK40t with comprehensive Lihuiyu controller support, enabling reliable communication with K40 and compatible CO2 laser systems through the LHYMicro-GL protocol.
