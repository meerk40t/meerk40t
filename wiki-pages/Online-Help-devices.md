# Online Help: Devices

## Overview

The Devices panel is MeerK40t's central device management interface. It provides comprehensive control over all laser devices configured in your system, allowing you to create, configure, activate, and manage multiple laser cutters and engravers from a single unified interface.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\devicepanel.py`

## Category

**GUI**

## Description

The Devices panel serves as the command center for laser device management in MeerK40t. Modern laser cutting workflows often involve multiple devices - different laser types (CO2, fiber, UV, diode), various power levels, or specialized equipment for different materials. The Devices panel makes it easy to:

- **Switch between devices** without restarting the application
- **Configure device-specific settings** for optimal performance
- **Monitor device status** and connection health
- **Organize your workflow** with multiple laser systems

Each device maintains its own complete set of settings, operations, and configuration, allowing you to seamlessly switch between different laser cutters while preserving all your work.

## How to Use

### Accessing the Devices Panel

The Devices panel is available in two ways:

1. **As a pane**: Window → Panes → Devices (docks at bottom of interface)
2. **As a window**: Window → Device-Settings → Device Manager

### Device List Overview

The main device list shows all configured devices with the following information:

- **Device**: User-defined name/label for the device
- **Driver**: Internal driver type (grbl, balor, k40, etc.)
- **Type**: Laser source type (CO2, Fiber, UV, Diode)
- **Status**: Current operational status (idle, busy, paused, etc.)
- **Interface**: Connection method (USB, network, mock)

### Basic Usage

#### Creating a New Device

1. Click **"Create New Device"** button
2. Select your device type from the categorized list:
   - **K-Series CO2-Laser**: K40 and similar Chinese CO2 lasers
   - **Balor**: High-end galvo-based laser systems
   - **GRBL**: Generic GRBL-compatible devices
   - **Newly**: NewlyDraw laser controllers
   - **Moshiboard**: Moshi drawing robot controllers
3. Choose your specific device model
4. MeerK40t automatically assigns a unique name
5. Configure device settings in the device-specific configuration panel

#### Switching Between Devices

1. Select the desired device in the list
2. Click **"Activate"** button (or double-click the device)
3. The active device is highlighted in red
4. All operations and settings now apply to the newly activated device

#### Managing Device Settings

1. Select a device in the list
2. Click **"Config"** button to open device-specific settings
3. Adjust parameters like:
   - Connection settings
   - Laser power and speed defaults
   - Axis corrections and calibration
   - Safety limits and timing

#### Organizing Devices

1. **Rename**: Select device → "Rename" button → enter new name
2. **Duplicate**: Select device → "Duplicate" button → creates copy with "_copy" suffix
3. **Remove**: Select device → "Remove" button → permanently deletes device

## Technical Details

The Devices panel integrates deeply with MeerK40t's service architecture:

- **Service Management**: Each device is a kernel service with isolated settings
- **Signal Integration**: Responds to `pipe;running`, `pause`, and `activate;device` signals
- **Device Registry**: Discovers available device types through the `dev_info` system
- **Configuration Persistence**: All device settings are automatically saved and restored

### Device Lifecycle

1. **Registration**: Device types register themselves with the kernel
2. **Instantiation**: Devices are created with default settings
3. **Configuration**: User adjusts device-specific parameters
4. **Activation**: Device becomes the active laser controller
5. **Operation**: Device processes jobs and commands
6. **Deactivation**: Device can be switched out for another

### Device Types Supported

- **GRBL Devices**: Generic CNC controllers with laser support
- **Balor Devices**: High-performance galvo laser systems
- **K40 Devices**: Popular Chinese CO2 laser cutters
- **Newly Devices**: NewlyDraw laser controller boards
- **Moshiboard Devices**: Moshi drawing robot controllers
- **Mock Devices**: Software simulation for testing

### Configuration Integration

Each device type provides its own configuration panel with settings for:

- **Physical Parameters**: Lens size, laser spot size, bed dimensions
- **Connection Settings**: USB ports, network addresses, serial numbers
- **Operational Limits**: Maximum power, speed, and frequency
- **Safety Features**: Emergency stops, interlocks, and overrides
- **Calibration Data**: Correction files, axis alignment, and positioning

## Safety Considerations

- **Active Device Awareness**: Always verify which device is currently active before starting jobs
- **Device-Specific Limits**: Different lasers have different power and speed capabilities
- **Configuration Backup**: Important device settings should be documented
- **Hardware Verification**: Test new device configurations on scrap material first
- **Emergency Access**: Keep emergency stop buttons accessible when operating

## Troubleshooting

### Device Won't Activate

**Problem**: Clicking "Activate" doesn't switch devices
- **Check Device Status**: Ensure device is properly configured and connected
- **Configuration Errors**: Open device config panel and verify all required settings
- **Driver Issues**: Check USB connections and driver installation
- **Service Conflicts**: Restart MeerK40t if device services are unresponsive

### Device List Empty

**Problem**: No devices appear in the list
- **First Run**: Click "Create New Device" to add your first laser
- **Hidden Devices**: Check if devices are disabled in configuration
- **Service Errors**: Look for error messages in console output

### Configuration Won't Save

**Problem**: Device settings don't persist between sessions
- **Write Permissions**: Ensure MeerK40t has write access to its configuration directory
- **File Corruption**: Try duplicating the device and removing the original
- **Service Restart**: Restart MeerK40t after major configuration changes

### Connection Issues

**Problem**: Device shows as disconnected
- **USB Stability**: Try different USB ports or cables
- **Power Supply**: Ensure laser has proper power and is turned on
- **Driver Installation**: Reinstall USB drivers (especially important for Windows)
- **Device Recognition**: Check device manager for hardware detection issues

### Multiple Device Conflicts

**Problem**: Devices interfere with each other
- **USB Bandwidth**: Spread devices across different USB controllers
- **Serial Numbers**: Configure unique identifiers for identical devices
- **Activation Verification**: Always confirm which device is active before operation

## Related Topics

- [Online Help: Balorconfig](Online-Help-balorconfig) - Balor device configuration
- [Online Help: GRBL Configuration](Online-Help-grblconfiguration) - GRBL device setup
- [Online Help: K40 Controller](Online-Help-k40controller) - K40 laser control
- [Online Help: Device Configuration](Online-Help-deviceconfiguration) - General device settings
- [Online Help: Operations](Online-Help-operations) - Working with laser operations
- [Online Help: Spooler](Online-Help-spooler) - Job queue management

## Advanced Usage

### Multi-Device Workflows

Professional laser operations often involve multiple devices:

**Material-Based Routing**:
- CO2 laser for wood and acrylic
- Fiber laser for metals
- UV laser for plastics and glass

**Power-Based Segmentation**:
- High-power device for cutting
- Low-power device for engraving
- Specialized device for fine detail work

### Device Templates

Create device templates for quick setup:
1. Configure a device completely
2. Duplicate it for similar devices
3. Adjust only the unique parameters (USB port, calibration)

### Network Device Management

For network-connected lasers:
- Configure IP addresses and ports
- Set up authentication credentials
- Monitor network connectivity status
- Handle reconnection after network interruptions

### Automated Device Switching

Advanced users can create scripts that automatically switch devices based on:
- Material type detection
- Job requirements analysis
- Production scheduling
- Maintenance cycles

---

*This help page provides comprehensive documentation for the Devices panel functionality in MeerK40t.*
