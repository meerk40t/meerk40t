# Online Help: Balorconfig

## Overview

The Balor Configuration panel provides comprehensive user interface controls for configuring Balor laser devices in MeerK40t. This panel allows you to adjust all device-specific settings, timing parameters, correction files, and operational defaults for Balor-series galvo laser systems.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\balormk\gui\balorconfig.py`

## Category

**Balor**

## Description

The Balor Configuration panel is the central hub for setting up and fine-tuning Balor laser devices. It provides a tabbed interface with specialized configuration sections for different aspects of device operation, from basic device parameters to advanced timing and correction settings.

Balor lasers are high-speed galvo-based systems that require precise calibration and timing configuration for optimal performance. This configuration panel ensures users can properly set up their devices for reliable cutting, engraving, and marking operations.

## How to Use

### Accessing the Configuration Panel

1. Ensure you have a Balor device selected and activated
2. Navigate to **Window** → **Device-Settings** → **Configuration**
3. The Balor Configuration panel will open with multiple tabs

### Key Features

- **Tabbed Interface**: Organized settings across 8+ configuration tabs
- **Red Dot Testing**: Built-in test functionality for red laser pointer
- **Pin Monitoring**: Real-time display of GPIO pin status
- **Correction File Integration**: Automatic lens size calculation from correction files
- **Device-Specific Settings**: Tailored options for different laser sources (fiber, CO2, UV)

### Basic Usage

1. **Device Setup**: Start with the "Balor" tab to configure basic device parameters
2. **Correction Files**: Enable and load correction files if available for your machine
3. **Timing Calibration**: Adjust timing settings in the "Timings" tab for optimal performance
4. **Red Light Configuration**: Set up red laser pointer behavior in the "Redlight" tab
5. **Test Settings**: Use the "Test" button to verify red light functionality

## Technical Details

The Balor Configuration panel integrates with several key MeerK40t systems:

- **Device Management**: Registers with the kernel's device service system
- **Signal Integration**: Responds to `lens_size`, `balorpin`, and `activate;device` signals
- **Choice Property System**: Uses MeerK40t's choice property panels for organized settings
- **Correction File Processing**: Automatically calculates lens size from loaded correction files
- **GPIO Integration**: Monitors and controls GPIO pins for external devices

### Configuration Tabs

#### Balor Tab
Core device settings including:
- **Laser Source**: Select between fiber, CO2, or UV laser types
- **Lens Size**: Physical working area dimensions (automatically calculated from correction files)
- **Correction Files**: Enable and load machine-specific correction files (.cor)
- **Axis Corrections**: Flip X/Y axes, swap coordinates, and rotate view
- **GPIO Configuration**: Set pin numbers for footpedal and red light laser
- **Device Selection**: Choose specific machine when multiple devices are connected

#### Redlight Tab
Red laser pointer configuration:
- **Travel Speed**: Speed of galvo movement when using red laser
- **Timing Delays**: Separate delays for light and dark movements
- **Position Offsets**: X/Y/angle offsets for red light alignment
- **Auto-On Preference**: Keep red light on after job completion

#### Global Tab
Default operational parameters:
- **Power Settings**: Default power levels for cutting/engraving
- **Speed Settings**: Default speeds for operations and travel
- **Frequency**: Q-switch frequency settings
- **Pulse Width**: MOPA (Master Oscillator Power Amplifier) settings

#### Timings Tab
Critical timing parameters for laser operation:
- **Laser Delays**: On/off timing at start and end of marks
- **Polygon Delays**: Timing between path points
- **Jump Settings**: Different delays for short vs. long distance moves
- **Open MO Delay**: Master oscillator timing

#### Extras Tab
Advanced device parameters:
- **First Pulse Killer**: Suppress initial laser pulses to prevent damage
- **PWM Settings**: Pulse-width modulation for pre-ionization
- **Operating Modes**: Timing, delay, laser, and control modes
- **Fly Resolution**: On-the-fly processing parameters
- **Input Processing**: Hardware-based operation triggering

#### Effects Tab
Visual and operational effects settings for enhanced laser control.

#### Operation Defaults Tab
Default settings applied to new operations created for this device.

#### Warning Tab
Safety and operational warnings configuration.

#### Default Actions Tab
Automatic actions performed on file load or device events.

#### Display Options Tab
How device information and operations are displayed in the interface.

### Red Dot Testing

The configuration panel includes a "Test" button that toggles the red laser pointer on/off for alignment and testing purposes. This helps verify:

- Red light laser functionality
- GPIO pin connections
- Position calibration
- Optical alignment

### Pin Status Monitoring

When connected to a Balor device, the panel displays real-time status of GPIO pins (0-15) showing which pins are active. This is useful for:

- Verifying hardware connections
- Debugging external device integration
- Monitoring footpedal and sensor status

### Correction File Integration

When a correction file (.cor) is loaded:
1. The file is parsed to extract scale information
2. Lens size is automatically calculated: `lens_size = 65536.0 / scale`
3. The device view is updated to reflect the corrected working area

This ensures accurate positioning and prevents distortion in laser output.

## Safety Considerations

- **Red Light Testing**: Use appropriate eye protection when testing red laser pointer
- **Correction Files**: Only use correction files provided by your laser manufacturer
- **Timing Settings**: Incorrect timing can damage equipment or produce poor quality results
- **Power Settings**: Start with conservative power levels and increase gradually
- **Hardware Connections**: Ensure proper grounding and electrical safety when connecting GPIO devices

## Related Topics

- [[Online Help: Balorcontroller]] - Device control and communication
- [[Online Help: Baloroperation]] - Operation-specific settings
- [[Online Help: K40Controller]] - Comparison with K40 laser control
- [[Online Help: Devices]] - General device management
- [[Online Help: Correction Files]] - Working with correction files

## Troubleshooting

### Red Light Not Working
- Check GPIO pin configuration in Balor tab
- Verify hardware connections
- Test with "Test" button in configuration panel

### Correction File Issues
- Ensure file has .cor extension
- Verify file is not corrupted
- Check file permissions and path

### Timing Problems
- Start with default timing values
- Adjust incrementally while testing
- Consider laser source type (fiber/CO2/UV have different requirements)

### Connection Issues
- Verify device is properly connected via USB
- Check machine index selection
- Try mock mode for testing without hardware

---

*This help page provides comprehensive documentation for the Balor Configuration panel functionality in MeerK40t.*
