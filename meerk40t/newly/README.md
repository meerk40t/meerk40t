# Newly

Newly is a driver for replacing some NewlyDraw driver code.

## Overview

The Newly module provides support for CO2 laser controllers that use the NewlyDraw software protocol. This module implements a complete laser controller stack including device management, USB communication, cutcode processing, and hardware-specific optimizations.

## Architecture

The Newly module follows MeerK40t's standard device driver pattern with three main components:

### Device Layer (`device.py`)
- **NewlyDevice**: Main service class inheriting from `Service` and `Status`
- Manages device lifecycle, configuration, and user interface
- Handles extensive configuration options including:
  - Bed dimensions and positioning modes
  - PWM settings and laser power control
  - Speed charts with acceleration and backlash compensation
  - Axis configuration and Z-axis control
  - Board-specific parameters

### Driver Layer (`driver.py`)
- **NewlyDriver**: Translates cutcode operations to device commands
- Implements plot planner integration for optimized cutting paths
- Manages job queue processing and real-time execution
- Handles coordinate transformations and scaling

### Controller Layer (`controller.py`)
- **NewlyController**: Manages USB communication protocol
- Implements machine index tracking and job coordinate management
- Handles device status monitoring and error recovery
- Provides logging and debugging capabilities

## Hardware Support

The Newly module supports a wide range of CO2 laser controllers running NewlyDraw software, including:

### Supported Manufacturers and Models
- **Artsign**: JSM-40U/3040U/3060U series
- **Beijing SZTaiming**: Various models
- **Cybertech**: U-SET series
- **DongGuan EverTech**: ETL3525 series
- **Duowei Laser**: Laser U series
- **Gama**: Various models
- **Greatsign**: LE40U/3040U/3060U series
- **Helo**: HLG 40N series
- **HPC Laser**: LS 3020 series
- **Jinan DaGong**: TLU series
- **Jinan Jinweik**: Laser B series
- **Jinan Ruijie**: Laser U series
- **Jinan Senfeng**: Laser U series
- **Jinan Suke**: Various models
- **Jinan Xinyi**: USB series
- **Light Technology**: LH40U/3040U/3060U series
- **Liaocheng Xinxing**: U series
- **Lion Laser**: Various models
- **Mini Laser**: USB series
- **Rabbit**: Rabbit40B series
- **RayLaser/U-SET**: Various models
- **Sicano**: SIC-L40B series
- **Villa L. & Figlio S.R.L.**: Laser B series
- **Weifang Tiangong**: Laser B series
- **Wuhan Anwei**: AW-U series
- **Wuhan Jinli**: JL Cylinder series
- **ZhengZhou LeCai**: LC Laser and LC Plasma series
- **ZL Tech**: ZL40B series

### Hardware Features
- **Bed Sizes**: 308x220mm to 2500x1300mm (plasma cutters)
- **Positioning Modes**: Multiple coordinate systems and axis configurations
- **Z-Axis Support**: Automatic height control for different materials
- **PWM Control**: Precise laser power modulation
- **Speed Optimization**: Configurable acceleration and backlash compensation

## Technical Features

### USB Communication Protocol
- **Vendor ID**: 0x0471 (Philips)
- **Product ID**: 0x0999
- **Endpoints**:
  - Interrupt Write (0x01): Packet size transmission
  - Interrupt Read (0x81): Confirmation responses
  - Bulk Write (0x02): Data transmission
  - Bulk Read (0x82): Status responses
- **Packet Protocol**: Big-endian size prefix followed by bulk data transfer
- **Error Recovery**: Automatic reconnection on USB errors

### Configuration System
The module provides extensive configuration options through MeerK40t's settings system:

```python
# Example device configuration
{
    "bedwidth": "900mm",
    "bedheight": "600mm",
    "axis": 1,  # Axis configuration mode
    "pos_mode": 1,  # Positioning mode
    "board": 1,  # Board type
    "z_type": 2,  # Z-axis control type
    "z_dir": 0,  # Z-axis direction
    "speedchart": [...],  # Speed optimization data
    "source": "Older CO2"  # Laser source type
}
```

### Speed Optimization
- **Speed Charts**: Pre-configured acceleration profiles for different speeds
- **Backlash Compensation**: Automatic adjustment for mechanical play
- **Corner Speed Control**: Optimized velocity at direction changes
- **Acceleration Length**: Distance required to reach target speed

## Usage

### Device Setup
1. Connect your NewlyDraw-compatible laser via USB
2. Select the appropriate device model from the device list
3. Configure bed dimensions and positioning parameters
4. Adjust speed charts and PWM settings as needed

### Console Commands
The Newly device provides several console commands for advanced control:

```bash
# Start the device service
service device start newly

# Configure device parameters
newly bedwidth 900mm
newly bedheight 600mm
newly axis 1

# Monitor device status
newly status
```

### Integration with MeerK40t
The Newly module integrates seamlessly with MeerK40t's core systems:

- **Element Processing**: Converts vector graphics to cutcode
- **Cut Planning**: Optimizes cutting paths for efficiency
- **Spooler Integration**: Manages job queue and execution
- **Real-time Control**: Live position monitoring and control

## Development

### Key Classes
- `NewlyDevice`: Main device service and configuration
- `NewlyDriver`: Cutcode processing and command translation
- `NewlyController`: USB communication and protocol handling
- `USBConnection`: Low-level USB interface management
- `NewlyParams`: Parameter validation and type checking

### Testing
The module includes comprehensive testing support:

```bash
# Run Newly-specific tests
python -m unittest test_drivers_newly.py

# Test with mock connection for development
# (Uses MockConnection instead of USBConnection)
```

### Dependencies
- `pyusb`: USB communication library
- `libusb`: Backend USB driver
- MeerK40t core libraries

## Troubleshooting

### Common Issues
- **USB Permission Errors**: Ensure proper USB device permissions on Linux
- **Driver Conflicts**: Disable conflicting kernel drivers
- **Connection Timeouts**: Check USB cable and power supply
- **Configuration Errors**: Verify bed dimensions and positioning modes

### Debug Mode
Enable verbose logging for troubleshooting:

```python
# In device configuration
"debug": True  # Enables detailed USB communication logging
```

### Mock Connection
For development and testing without hardware:

```python
# Use MockConnection class for offline testing
from meerk40t.newly.mock_connection import MockConnection
```

## Thanks

Thanks to Betaeta for technical specs and data.
Thanks to Lynxis (Alexander Couzens) for his very helpful explanations https://github.com/lynxis/laserusb