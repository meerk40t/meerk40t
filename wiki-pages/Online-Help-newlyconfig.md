# Online Help: Newlyconfig

## Overview

This help page covers the **Newlyconfig** functionality in MeerK40t.

The Newly Configuration panel provides comprehensive control over Newly laser device settings, effects, operation defaults, and safety parameters. This panel is organized into multiple tabs for different configuration categories.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\newly\gui\newlyconfig.py`

## Category

**Newly**

## Description

Newly devices are high-performance laser cutters that support advanced features like PWM power control, raster speed optimization, and multi-file output. The configuration panel allows you to customize device behavior, optimize performance, and set safety thresholds for your laser operations.

## How to Use

### Key Features

- Integrates with: `activate;device`
- Multi-tab configuration interface
- Device-specific parameter control
- Safety threshold management
- Performance optimization tools

### Basic Usage

1. **Access Configuration**: Open the Newly Configuration panel from Device Settings → Configuration
2. **Configure Device**: Set basic device parameters (dimensions, DPI, power settings)
3. **Optimize Performance**: Adjust raster speed charts and acceleration parameters
4. **Set Safety Limits**: Configure danger level thresholds for different operations
5. **Customize Effects**: Set up hatch patterns and wobble effects

## Configuration Tabs

### Newly Tab

Contains general device identification and basic operational settings.

**Device Label**: Custom name for your Newly device (default: "newly-device")

**Dimensions**:
- **Width**: Laser bed width (default: 310mm)
- **Height**: Laser bed height (default: 210mm)
- **Laserspot**: Laser beam diameter (default: 0.3mm)

**Parameters**:
- **X-Margin/Y-Margin**: User-defined offsets from bed edges
- **Home Position**: Override native home location (auto/top-left/top-right/bottom-left/bottom-right/center)
- **Axis Corrections**: Flip X, Flip Y, or Swap XY axes for coordinate system adjustments
- **Curve Interpolation**: Number of interpolation points for smooth curves (default: 5)

**General Settings**:
- **Mock USB Backend**: Enable for software testing without hardware
- **Machine Index**: Select which machine to connect to (for multi-machine setups)

**Output Settings**:
- **Output File**: Select file index (0-9) for job output
- **Automatically Start**: Begin job execution immediately after sending

**Screen Updates**:
- **Device Position**: Enable/disable position indicator updates

### Device Tab

Hardware-specific parameters for Newly device operation.

**Axis DPI**:
- **Horizontal DPI**: Dots-per-inch resolution across X-axis (default: 1000)
- **Vertical DPI**: Dots-per-inch resolution across Y-axis (default: 1000)

**Backlash Compensation**:
- **Horizontal Backlash**: X-axis backlash correction in mm (default: 0)
- **Vertical Backlash**: Y-axis backlash correction in mm (default: 0)

**Power Settings**:
- **Max Power**: Maximum laser power percentage (default: 20%)
- **Max Pulse Power**: Maximum power for pulse operations (default: 65%)
- **PWM Power**: Enable/disable Pulse Width Modulation
- **PWM Frequency**: PWM cycle frequency in kHz (1-255, default: 2)

**Current Control**:
- **Cut DC**: Current level for cutting movements (default: 100)
- **Move DC**: Current level for positioning movements (default: 100)

**Raster Settings**:
- **Maximum Raster Jog**: Maximum distance for raster step movements (default: 15)

### Global Tab

Default operational parameters that can be overridden by individual operation settings.

**Cut Settings**:
- **Cut Speed**: Default cutting speed (can be overridden by operations)
- **Cut Power**: Default cutting power percentage (can be overridden by operations)

**Timing Controls**:
- **On Delay**: Delay before laser activation in milliseconds
- **Off Delay**: Delay after laser deactivation in milliseconds

**Raster Settings**:
- **Raster Speed**: Default raster engraving speed (can be overridden by operations)
- **Raster Power**: Default raster power percentage (can be overridden by operations)

**Movement Settings**:
- **Moving Speed**: Speed for non-cutting movements
- **Corner Speed**: Speed when changing direction at corners
- **Acceleration Distance**: Distance required to reach full speed

**Framing Settings**:
- **Rect Speed**: Speed for frame tracing operations
- **Rect Power**: Power level for frame drawing (typically 0%)

### Raster Chart Tab

Advanced speed optimization chart for raster operations. Defines acceleration parameters based on speed thresholds.

**Chart Columns**:
- **Speed <=**: Maximum speed for this parameter set
- **Acceleration Length**: Distance needed to reach target speed
- **Backlash**: Backlash compensation for this speed range
- **Corner Speed**: Speed for direction changes at this speed level

**Default Chart Entries**:
- Speed ≤100: Acceleration 8mm, Backlash 0, Corner Speed 20
- Speed ≤200: Acceleration 10mm, Backlash 0, Corner Speed 20
- Speed ≤300: Acceleration 14mm, Backlash 0, Corner Speed 20
- Speed ≤400: Acceleration 16mm, Backlash 0, Corner Speed 20
- Speed ≤500: Acceleration 18mm, Backlash 0, Corner Speed 20

The chart automatically sorts entries by speed and allows adding/removing custom speed ranges.

### Effects Tab

Configuration for hatch and wobble effects applied during laser operations.

**Available Effects**:
- **Hatch Patterns**: Various fill patterns for area operations
- **Wobble Settings**: Beam oscillation patterns for improved material processing
- **Effect Parameters**: Amplitude, frequency, and pattern-specific settings

Effects can be customized per operation type and material.

### Operation Defaults Tab

Default settings for different operation types (Cut, Engrave, Raster, etc.).

**Operation-Specific Defaults**:
- Speed and power settings for each operation type
- Material-specific parameter presets
- Quality vs. speed optimization profiles

### Warning Tab

Safety threshold configuration to prevent dangerous operations.

**Danger Level Settings**: Define acceptable parameter ranges for:
- Cutting operations (speed and power limits)
- Engraving operations
- Hatch operations
- Raster operations
- Image operations
- Dot operations

Each operation type can have independent safety thresholds with enable/disable controls.

### Default Actions Tab

Pre-configured action sequences for common operations.

**Available Actions**:
- Standard job execution workflows
- Safety check sequences
- Calibration procedures
- Maintenance routines

### Display Options Tab

User interface customization for the Newly device panel.

**Display Settings**:
- Information display preferences
- Status indicator configuration
- Panel layout options
- Theme integration settings

## Technical Details

The NewlyConfiguration class inherits from MWindow and provides a tabbed notebook interface using wx.aui.AuiNotebook. Each tab corresponds to a different choice category registered with the device kernel.

**Key Technical Components**:
- ChoicePropertyPanel for parameter configuration
- EffectsPanel for hatch/wobble effects
- WarningPanel for safety thresholds
- DefaultActionPanel for pre-configured actions
- FormatterPanel for display customization

The panel automatically hides/shows based on device activation signals and supports developer mode for additional hidden settings.

## Usage Guidelines

### Basic Setup
1. Configure device dimensions to match your laser bed
2. Set appropriate DPI values for your machine
3. Adjust power settings based on your laser capabilities
4. Configure backlash compensation if needed

### Performance Optimization
1. Use the Raster Chart to optimize acceleration for different speed ranges
2. Enable PWM for smoother power control if supported
3. Adjust timing delays for specific materials
4. Configure operation defaults for common materials

### Safety Configuration
1. Set appropriate danger level thresholds
2. Enable warnings for critical parameter ranges
3. Configure automatic safety checks
4. Test settings with low-power operations first

## Troubleshooting

### Connection Issues
- Verify machine index selection
- Check USB connection stability
- Use mock backend for testing without hardware

### Performance Problems
- Adjust acceleration distances in Raster Chart
- Modify backlash compensation values
- Optimize PWM frequency settings
- Check current settings for motor performance

### Quality Issues
- Fine-tune DPI settings for resolution
- Adjust curve interpolation for smooth paths
- Modify timing delays for material compatibility
- Configure appropriate power levels

## Advanced Features

### Multi-File Output
Newly devices support up to 10 output files (0-9). File 0 executes immediately, while others require manual start commands.

### PWM Power Control
When enabled, provides smoother power modulation for improved engraving quality and reduced material scorching.

### Speed Chart Optimization
The raster speed chart allows fine-tuning of acceleration parameters for different speed ranges, optimizing both quality and performance.

### Developer Mode
Additional hidden settings become available when developer mode is enabled in MeerK40t preferences.

## Related Topics

*Link to related help topics:*

- [[Online Help: Newlycontroller]]
- [[Online Help: K40Controller]]
- [[Online Help: K40Operation]]

## Screenshots

### Newly Tab - Basic Device Configuration
The Newly tab displays fundamental device settings:
- **Device Label**: Text field for custom device naming
- **Dimensions Panel**: Width, Height, and Laserspot input fields with mm units
- **Parameters Section**: X-Margin, Y-Margin, Home Position dropdown, and axis correction checkboxes
- **General Settings**: Mock USB backend checkbox and Machine Index selection
- **Output Settings**: File index dropdown (0-9) and auto-start checkbox
- **Screen Updates**: Device position indicator toggle

### Device Tab - Hardware Parameters
The Device tab shows hardware-specific controls:
- **Axis DPI Settings**: Horizontal and Vertical DPI input fields (default 1000)
- **Backlash Compensation**: Horizontal and Vertical backlash correction in mm
- **Power Settings**: Max Power, Max Pulse Power, PWM Power checkbox, and PWM Frequency slider
- **Current Control**: Cut DC and Move DC current level settings
- **Raster Settings**: Maximum Raster Jog distance input field

### Global Tab - Default Operation Parameters
The Global tab contains default operational settings:
- **Cut Settings**: Cut Speed and Cut Power default values
- **Timing Controls**: On Delay and Off Delay in milliseconds
- **Raster Settings**: Raster Speed and Raster Power defaults
- **Movement Settings**: Moving Speed, Corner Speed, and Acceleration Distance
- **Framing Settings**: Rect Speed and Rect Power for frame operations

### Raster Chart Tab - Speed Optimization
The Raster Chart tab displays the acceleration optimization table:
- **Chart Table**: Columns for Speed ≤, Acceleration Length, Backlash, and Corner Speed
- **Default Entries**: Five speed ranges (≤100, ≤200, ≤300, ≤400, ≤500) with preset values
- **Add/Remove Buttons**: Controls for modifying chart entries
- **Auto-sort**: Table automatically sorts by speed threshold

### Effects Tab - Hatch and Wobble Configuration
The Effects tab shows laser effect parameters:
- **Hatch Patterns**: Various fill pattern options for area engraving
- **Wobble Settings**: Oscillation type, amplitude, frequency, and pattern controls
- **Effect Parameters**: Material-specific effect customization options

### Operation Defaults Tab - Type-Specific Settings
The Operation Defaults tab contains per-operation configurations:
- **Operation Categories**: Separate sections for Cut, Engrave, Raster, Image operations
- **Parameter Sets**: Speed and power defaults for each operation type
- **Material Presets**: Pre-configured settings for common materials

### Warning Tab - Safety Thresholds
The Warning tab displays safety configuration:
- **Danger Level Settings**: Enable/disable toggles for each operation type
- **Parameter Thresholds**: Speed and power limit settings for safe operation
- **Warning Indicators**: Visual alerts for operations exceeding safe parameters

### Default Actions Tab - Pre-configured Workflows
The Default Actions tab shows automated sequences:
- **Action Categories**: Job execution, safety checks, calibration, and maintenance
- **Workflow Selection**: Dropdown or list of available pre-configured actions
- **Execution Controls**: Run, edit, or customize default action sequences

### Display Options Tab - Interface Customization
The Display Options tab controls UI appearance:
- **Information Display**: Toggle options for status information visibility
- **Status Indicators**: Configuration for progress and state displays
- **Panel Layout**: Customization options for the device panel arrangement
- **Theme Integration**: Settings for visual theme compatibility

---

*This help page provides comprehensive documentation for Newly device configuration in MeerK40t.*
