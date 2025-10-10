# Online Help: Moshi Configuration

## Overview

This help page covers the **Moshi Configuration** functionality in MeerK40t.

The Moshi Configuration window provides comprehensive settings and controls for Moshi laser devices. This device-specific configuration interface allows you to customize all aspects of your Moshi laser's behavior, from basic bed dimensions to advanced operation defaults and safety warnings.

The configuration is organized into multiple tabs, each focusing on different aspects of device management and operation control.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\moshi\gui\moshidrivergui.py` - Main configuration window implementation
- `meerk40t\device\devicechoices.py` - Effect and operation choice definitions
- Device menu: Device-Settings → Configuration (when Moshi device is active)

## Category

**Moshi**

## Description

The Moshi Configuration window serves as the central control panel for all Moshi device settings and behaviors. It provides device-specific configuration options that are not available in the general MeerK40t preferences, allowing you to:

- **Configure Device Parameters**: Set bed dimensions, coolant support, and hardware-specific options
- **Customize Effects**: Control default hatch and wobble effect parameters
- **Set Operation Defaults**: Define default power and speed settings for different operation types
- **Manage Safety Systems**: Configure warning thresholds and safety parameters
- **Control Default Actions**: Set up automatic behaviors and responses
- **Adjust Display Options**: Customize how operations are displayed and formatted

This configuration window automatically closes if you switch to a different device type, ensuring you only see relevant settings for your current hardware.

## How to Use

### Accessing Moshi Configuration

The Moshi Configuration window is only available when a Moshi device is active:

1. Ensure your Moshi device is selected and active
2. Go to **Device-Settings → Configuration** in the menu
3. The window will open with multiple configuration tabs

### Configuration Tab - Basic Device Settings

#### Bed Dimensions
- **Width**: Physical width of the laser bed (typically in mm)
- **Height**: Physical height of the laser bed (typically in mm)
- These settings define the working area boundaries

#### Coolant Support
- **Enable/Disable**: Whether the device has coolant system support
- **Control Method**: How the coolant system is activated/deactivated
- Important for devices with integrated cooling systems

### Effects Tab - Hatch and Wobble Defaults

#### Hatch Effect Defaults
- **Hatch Distance**: Default spacing between hatch lines (e.g., "1.0mm")
- **Hatch Angle**: Default angle for hatch patterns (e.g., "0deg")
- **Hatch Angle Delta**: Default angle variation for multi-pass hatches (e.g., "0deg")

#### Wobble Effect Defaults
- **Wobble Type**: Default wobble pattern type (circle, square, etc.)
- **Wobble Speed**: Default speed for wobble movements (percentage)
- **Wobble Radius**: Default radius/distance for wobble patterns (e.g., "0.5mm")
- **Wobble Interval**: Default spacing between wobble points (e.g., "0.1mm")

### Operation Defaults Tab - Power and Speed Settings

This tab contains default settings for each operation type:

#### Cut Operations
- **Default Power**: Power level for cutting operations (0-1000)
- **Default Speed**: Speed for cutting operations (mm/s)

#### Engrave Operations
- **Default Power**: Power level for engraving operations (0-1000)
- **Default Speed**: Speed for engraving operations (mm/s)

#### Raster Operations
- **Default Power**: Power level for raster/image operations (0-1000)
- **Default Speed**: Speed for raster operations (mm/s)

#### Image Operations
- **Default Power**: Power level for image processing operations (0-1000)
- **Default Speed**: Speed for image operations (mm/s)

### Warning Tab - Safety and Alert Configuration

#### Danger Level Thresholds
Configure warning thresholds for different operation types:
- **Speed Limits**: Minimum/maximum safe speeds
- **Power Limits**: Safe power ranges
- **Automatic Alerts**: When operations exceed safe parameters

#### Warning Display
- **Visual Indicators**: Color coding for dangerous settings
- **Alert Messages**: Customizable warning messages
- **Override Options**: Allow/disallow parameter overrides

### Default Actions Tab - Automatic Behaviors

#### Startup Actions
- **Auto-Connect**: Automatically connect to device on startup
- **Default Mode**: Initial operation mode when device activates
- **Safety Checks**: Automatic safety verification on startup

#### Operation Actions
- **Auto-Focus**: Automatically focus laser before operations
- **Home Position**: Return to home position after jobs
- **Power Management**: Automatic power cycling behaviors

### Display Options Tab - Formatting and Visualization

#### Operation Display
- **Color Coding**: Visual distinction between operation types
- **Label Formats**: How operations are labeled in the interface
- **Icon Display**: Show/hide operation type icons

#### Status Display
- **Progress Indicators**: Show operation progress visually
- **Parameter Display**: How power/speed values are shown (absolute vs percentage)
- **Unit Preferences**: Display units (mm/s vs mm/min)

## Technical Details

### Device-Specific Integration
The Moshi Configuration window is dynamically loaded only when a Moshi device is active. It integrates with the device service system and automatically unregisters when switching devices.

### Signal Integration
- **`activate;device`**: Monitors device activation to show/hide configuration window
- **Device-specific signals**: Updates configuration when device parameters change

### Configuration Storage
All settings are stored in the device configuration and persist between sessions. Settings are device-specific and don't affect other laser devices.

### Safety Integration
Warning thresholds integrate with the danger level system to provide real-time feedback on potentially unsafe operation parameters.

### Effect System
Hatch and wobble defaults are used when creating new effects without explicit parameters, ensuring consistent behavior across operations.

## Related Topics

*Link to related help topics:*

- [[Online Help: Moshicontroller]]
- [[Online Help: Devices]]
- [[Online Help: Effects]]
- [[Online Help: Warning]]

## Screenshots

*Add screenshots showing the Moshi configuration window with different tabs and settings.*
