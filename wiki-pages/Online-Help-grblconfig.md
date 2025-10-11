# Online Help: Grblconfig

## Overview

This help page covers the **Grblconfig** functionality in MeerK40t.

The GRBL Configuration window provides comprehensive setup and configuration options for GRBL-based laser controllers. This multi-tab interface allows users to configure all aspects of their GRBL device connection, from basic bed dimensions to advanced communication protocols and laser operation parameters.

The configuration window is organized into 9 tabs, each handling different aspects of device setup and operation. This is typically accessed through **Device Settings → GRBL-Configuration** in the menu system.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\grbl\gui\grblconfiguration.py`

## Category

**GRBL**

## Description

The GRBL Configuration window is the central hub for setting up and managing GRBL-based laser cutters in MeerK40t. Users would use this configuration when:

- **Setting up a new GRBL device** for the first time
- **Configuring connection parameters** (serial, TCP, or WebSocket)
- **Defining bed dimensions** and coordinate systems
- **Adjusting laser operation parameters** like speed limits and power settings
- **Configuring communication protocols** and buffer management
- **Setting up safety features** and warning thresholds
- **Customizing default operation behaviors**

The configuration supports all standard GRBL firmware variants and provides both basic setup for beginners and advanced options for experienced users.

## How to Use

### Configuration Tabs Overview

#### Device Tab
Configures physical laser bed properties and provides auto-configuration tools.

**Key Settings:**
- **Width/Height**: Physical dimensions of the laser bed
- **Laserspot**: Size of the laser beam diameter
- **Scale X/Y**: Coordinate scaling factors
- **Flip X/Y**: Axis direction corrections
- **Home Corner**: Physical home position override

**Auto-Configuration Buttons:**
- **Query properties**: Connects to laser and retrieves hardware settings ($ parameters)
- **Hardware properties**: Opens advanced hardware configuration window

#### Interface Tab
Selects and configures the connection method to the GRBL device.

**Connection Types:**
- **Serial**: Direct USB/serial connection (most common)
  - Port selection (auto-detected)
  - Baud rate (typically 115200)
- **Networked (TCP)**: Network connection via TCP/IP
  - IP address/hostname
  - Port (default: 23, switches from 81)
- **WebSocket**: WebSocket-based connection
  - IP address/hostname
  - Port (default: 81, switches from 23)
- **Mock**: Simulation mode for testing without hardware

#### Protocol Tab
Configures low-level communication parameters.

**Key Settings:**
- **Sending Protocol**: Buffered vs synchronous communication
- **Planning Buffer Size**: GRBL planning buffer size
- **Line Ending**: CR, LF, or CRLF
- **Validation Options**: Connection validation and startup commands

#### Advanced Tab
GRBL-specific operational settings.

**Key Settings:**
- **Use M3**: Laser start command (M3 vs M4)
- **Curve Interpolation**: Path smoothing distance
- **Device has endstops**: Enables homing capabilities
- **Red Dot Simulation**: Low-power positioning laser
- **Maximum Speeds**: Vector and raster speed limits
- **Controller Buffer**: Buffer size management

#### Effects Tab
Configures laser power and speed effects for different operations.

#### Operation Defaults Tab
Sets default parameters for various laser operations (cut, engrave, raster).

#### Warning Tab
Configures safety warnings and danger level thresholds.

#### Default Actions Tab
Configures automatic actions for various events.

#### Display Options Tab
Configures how information is displayed in the interface.

### Basic Usage

1. **Open Configuration**: Go to Device Settings → GRBL-Configuration
2. **Select Interface Type**: Choose Serial, TCP, WebSocket, or Mock based on your setup
3. **Configure Connection**:
   - For Serial: Select COM port and baud rate
   - For Network: Enter IP address and port
4. **Set Bed Dimensions**: Enter your laser bed width and height
5. **Configure Basic Settings**: Set laser spot size and axis scaling
6. **Test Connection**: Use "Query properties" to verify connection and retrieve settings
7. **Adjust Advanced Settings**: Configure speed limits, buffer sizes, and safety features
8. **Save Configuration**: Settings are automatically saved

### Advanced Usage

#### Auto-Configuration Process
The "Query properties" button sends a `$$` command to retrieve all GRBL settings:
- Retrieves bed dimensions ($130, $131 parameters)
- Detects endstop configuration ($21 parameter)
- Updates local configuration automatically

#### Red Dot Positioning
Enable "Simulate reddot" for low-power laser positioning:
- Set appropriate power level (typically 1-5%)
- Use during focusing and material alignment
- Automatically activates during outline operations if enabled

#### Buffer Management
Configure controller buffer limits to prevent overflow:
- Enable buffer limiting
- Set maximum buffer size (typically 100-200 lines)
- Adjust based on your controller's capabilities

## Technical Details

The GRBL Configuration system integrates with MeerK40t's device service architecture. Each configuration tab corresponds to registered choice panels that dynamically generate UI controls based on device capabilities.

**Core Components:**
- **ConfigurationInterfacePanel**: Handles connection type selection and interface-specific settings
- **ChoicePropertyPanel**: Generic property configuration panels for different setting categories
- **Device Registration**: GRBL device registers multiple choice sets (bed_dim, serial, tcp, ws, protocol, grbl-advanced, etc.)

**Key Integration Points:**
- **Signal System**: Settings changes trigger `update_interface`, `bedwidth`, `bedheight`, and other signals
- **Auto-Configuration**: `acquire_properties` and `hw_config` buttons trigger hardware queries
- **Dynamic UI**: Interface panels show/hide based on selected connection type
- **Validation**: Connection validation with configurable welcome messages and startup sequences

**Supported GRBL Variants:**
- Standard GRBL firmware
- GRBL-based controllers with custom welcome messages
- Controllers with different buffer sizes and communication protocols

## Related Topics

- [Online Help: Grblcontoller](Online-Help-grblcontoller) - GRBL controller operations and status
- [Online Help: Grblhwconfig](Online-Help-grblhwconfig) - Hardware-specific GRBL configuration
- [Online Help: Grbloperation](Online-Help-grbloperation) - GRBL device operation and job execution
- [Online Help: Devices](Online-Help-devices) - General device management

## Screenshots

*GRBL Configuration window showing the Interface tab with connection type selection:*

*Device tab showing bed dimensions and auto-configuration buttons:*

*Advanced tab with GRBL-specific operational settings:*

---

This documentation covers the complete GRBL configuration system in MeerK40t, providing guidance for both basic setup and advanced customization of GRBL-based laser controllers.
