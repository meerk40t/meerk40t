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

### Zmove Panel - Main Controls
The Zmove panel displaying Z-axis movement controls:
- **Up Arrows**: Three upward movement buttons (0.1mm, 1.0mm, 10.0mm increments)
- **Home Button**: Center button for returning to Z-home position
- **Down Arrows**: Three downward movement buttons (0.1mm, 1.0mm, 10.0mm increments)
- **Device Integration**: Panel only visible for devices supporting Z-axis movement

### Fine Movement Controls
Close-up of the small increment movement buttons:
- **0.1mm Buttons**: Up and down arrows for precise focusing adjustments
- **High Precision**: Suitable for fine-tuning laser focus and material compensation
- **Button States**: Visual feedback showing button press and hold functionality
- **Repeat Behavior**: Continuous movement when buttons are held down

### Medium Movement Controls
The 1.0mm increment buttons for standard adjustments:
- **1.0mm Steps**: Balanced movement speed for general Z-axis positioning
- **Material Thickness**: Appropriate for compensating different material heights
- **Workflow Speed**: Faster than fine adjustments but still precise
- **Visual Indicators**: Clear labeling of movement distances

### Coarse Movement Controls
The 10.0mm increment buttons for rapid positioning:
- **10.0mm Steps**: Large movements for significant Z-axis repositioning
- **Quick Traversal**: Fast repositioning between work areas
- **Safety Consideration**: Large steps require care to avoid collisions
- **Efficiency**: Minimizes button presses for large position changes

### Home Position Button
The center home button with autofocus functionality:
- **Home Symbol**: Central button with home icon for Z-home positioning
- **Right-Click Menu**: Autofocus option available on supported devices
- **Default Position**: Returns to device-defined Z-home coordinate
- **Calibration**: Ensures consistent starting position for operations

### Device-Specific Visibility
The panel showing device-dependent display:
- **Supported Device**: Panel visible when connected device has Z-axis capability
- **Unsupported Device**: Panel hidden for devices without vertical movement
- **Dynamic Updates**: Panel appears/disappears when switching devices
- **Capability Detection**: Automatic detection of `supports_z_axis` attribute

### Continuous Movement Demonstration
Showing button hold functionality for continuous movement:
- **Held Button**: Visual feedback when movement button is pressed and held
- **Repeat Rate**: Continuous movement at configured button repeat speed
- **Acceleration**: Smooth movement with configurable acceleration settings
- **Safety**: Ability to release button to stop movement immediately

---

*This help page is automatically generated. Please update with specific information about the zmove feature.*
