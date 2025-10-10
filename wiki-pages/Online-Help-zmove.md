# Online Help: Zmove

## Overview

This help page covers the **Zmove** functionality in MeerK40t.

The Zmove panel provides Z-axis movement controls for laser devices that support vertical (Z-axis) positioning. This feature allows you to adjust the laser head's height for focusing, material thickness compensation, and multi-level cutting operations.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\navigationpanels.py`

## Category

**Navigation**

## Description

The Zmove panel is designed for laser devices that support Z-axis movement, such as those with autofocus capabilities or adjustable focus lenses. It provides precise control over the laser head's vertical position, allowing you to:

- Move the laser head up or down in precise increments
- Return to a predefined home position
- Perform autofocus operations (on supported devices)
- Compensate for different material thicknesses
- Set up multi-level cutting operations

This panel only appears when your connected device supports Z-axis movement. The controls integrate with MeerK40t's button repeat settings, allowing continuous movement while holding down buttons.

## How to Use

### Available Controls

- **Up Arrow (Small)** - Move laser head up by 0.1mm
- **Up Arrow (Medium)** - Move laser head up by 1.0mm
- **Up Arrow (Large)** - Move laser head up by 10.0mm
- **Home Button** - Move to defined Z-home position
- **Down Arrow (Small)** - Move laser head down by 0.1mm
- **Down Arrow (Medium)** - Move laser head down by 1.0mm
- **Down Arrow (Large)** - Move laser head down by 10.0mm

### Key Features

- **Button Repeat**: Hold buttons for continuous movement (speed controlled by button repeat settings)
- **Autofocus**: Right-click the home button for automatic focus (on supported devices)
- **Device Integration**: Only shows for devices with Z-axis support
- **Precise Movement**: Three step sizes for fine, medium, and coarse adjustments

### Basic Usage

1. **Check Device Support**: The Zmove panel only appears for devices that support Z-axis movement
2. **Select Movement Direction**: Click up/down arrows for the desired direction and step size
3. **Continuous Movement**: Hold buttons down for repeated movement at the set repeat rate
4. **Return Home**: Click the home button to return to the defined Z-home position
5. **Autofocus**: Right-click the home button to perform automatic focusing (if available)

## Technical Details

The Zmove panel implements Z-axis movement through the following commands:

- `z_move <distance>` - Moves the Z-axis by the specified distance in millimeters
- `z_home` - Moves to the device-defined Z-home position
- `z_focus` - Performs automatic Z-axis focusing (device-dependent)

Movement distances are internally multiplied by 0.1, so the step values (1, 10, 100) correspond to 0.1mm, 1.0mm, and 10.0mm respectively. The panel integrates with MeerK40t's TimerButtons system for smooth repeated movement and respects the global button repeat and acceleration settings.

The panel dynamically shows/hides based on the `supports_z_axis` attribute of the active device and listens to the "activate;device" signal to update its visibility when devices change.

## Related Topics

*Link to related help topics:*

- [[Online Help: Jog]] - Manual laser head positioning
- [[Online Help: Move]] - Coordinate-based positioning
- [[Online Help: Pulse]] - Test pulse firing
- [[Online Help: Devices]] - Device configuration and capabilities

## Screenshots

*Add screenshots showing the Zmove panel with Z-axis controls and device integration.*

---

*This help page is automatically generated. Please update with specific information about the zmove feature.*
