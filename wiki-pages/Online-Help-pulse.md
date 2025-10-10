# Online Help: Pulse

## Overview

This help page covers the **Pulse** functionality in MeerK40t.

The Pulse panel provides controls for firing short test laser pulses, allowing you to test laser power, alignment, and focus before running full cutting or engraving jobs.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\navigationpanels.py`

## Category

**Navigation**

## Description

The Pulse panel enables safe testing of laser functionality through short, controlled pulses. It provides adjustable duration and power controls for precise testing scenarios.

The panel consists of:
- **Pulse Button**: Fires a laser pulse with current settings
- **Duration Control**: Adjustable pulse length from 1-1000 milliseconds
- **Power Control**: Optional power adjustment (available on PWM-capable devices)

## How to Use

### Available Controls

- **Pulse Button**: Laser beam icon that fires a test pulse
- **Duration Spinner**: Sets pulse length (1-1000 ms, default 50ms)
- **Power Field**: Sets pulse power (0-1000 PPI or 0-100%, device-dependent)

### Key Features

- Integrates with: `wxpane/Navigation`, `activate;device`
- Variable pulse duration from 1ms to 1000ms
- Power control for PWM-capable devices
- Settings persistence across sessions
- Dynamic UI based on device capabilities

### Basic Usage

1. **Set Duration**: Adjust the spinner to desired pulse length (default 50ms)
2. **Set Power** (if available): Enter power value in PPI or percentage
3. **Position Laser**: Ensure laser is positioned safely for testing
4. **Fire Pulse**: Click the pulse button to test laser output

### Advanced Usage

#### Power Control Modes
- **PPI Mode**: Direct power units (0-1000 PPI)
- **Percentage Mode**: Relative power (0-100%)
- Mode automatically detected from device settings

#### Testing Scenarios
- **Alignment Testing**: Short pulses to verify beam position
- **Power Calibration**: Variable power pulses for material testing
- **Focus Testing**: Different durations to check beam characteristics

## Technical Details

Provides pulse firing controls for laser alignment and testing operations. Features label controls for user interaction. Integrates with wxpane/Navigation, refresh_scene for enhanced functionality.

The Pulse panel implements device-aware pulse generation with support for both basic and PWM-capable laser devices. It maintains settings persistence and provides real-time UI adaptation based on device capabilities.

Key technical components:
- **Command Generation**: Sends "pulse [duration] [-p power]" commands
- **Device Detection**: Automatically shows/hides power controls based on PWM support
- **Settings Management**: Persists duration and power values in device settings
- **Unit Conversion**: Handles PPI/percentage conversion based on device configuration

### Pulse Command Format
```
pulse [duration_ms] [-p power_value]
```

Where:
- **duration_ms**: Pulse length in milliseconds (1-1000)
- **power_value**: Optional power setting (0-1000 PPI or converted percentage)

### Device Compatibility
- **Basic Devices**: Support duration control only
- **PWM Devices**: Support both duration and power control
- **Power Display**: Adapts between PPI and percentage based on `use_percent_for_power_display` setting

## Safety Considerations

- **Short Pulses Only**: Designed for test pulses, not continuous operation
- **Safe Positioning**: Always position laser safely before firing pulses
- **Power Awareness**: Start with low power settings when testing
- **Material Safety**: Use appropriate test materials to avoid damage

## Troubleshooting

### Power Controls Not Visible
- Check if device supports PWM (`supports_pwm` attribute)
- Verify device is properly configured
- Some devices may not support variable power

### Pulse Not Firing
- Ensure device is connected and operational
- Check device status in MeerK40t interface
- Verify pulse duration is within valid range (1-1000ms)

### Power Values Not Applied
- Confirm device supports PWM functionality
- Check power display mode settings
- Verify power value is within device limits

### Settings Not Persisting
- Check device settings storage
- Ensure proper device configuration
- Restart MeerK40t if settings don't save

## Related Topics

- [[Online Help: Jog]] - Manual laser positioning controls
- [[Online Help: Move]] - Coordinate-based positioning
- [[Online Help: Drag]] - Laser alignment and positioning
- [[Online Help: Navigation]] - Complete navigation control suite

## Screenshots

*Screenshots showing the pulse panel with duration and power controls would be helpful here, demonstrating both basic pulse operation and advanced power control features.*

---

*This help page provides comprehensive documentation for the pulse functionality, covering test pulse generation, power control, and device-specific features for safe laser testing.*
