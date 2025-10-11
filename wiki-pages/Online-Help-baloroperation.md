# Online Help: Baloroperation

## Overview

The Balor Operation Properties panel provides operation-specific parameter controls for Balor laser devices in MeerK40t. This panel allows users to override global device settings with custom values for individual laser operations, providing fine-grained control over cutting, engraving, and marking parameters.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\balormk\gui\baloroperationproperties.py`

## Category

**Balor**

## Description

The Balor Operation Properties panel appears when you select a Balor operation in the operations tree. It provides advanced controls that allow you to customize laser parameters for specific operations, overriding the global device defaults set in the Balor Configuration panel.

This functionality is essential for complex laser jobs where different parts require different settings. For example, you might want fine engraving with slow speeds and low power, while cutting operations need high speed and power. The operation properties panel gives you this level of control.

## How to Use

### Accessing Operation Properties

1. Create or select a Balor operation in the operations tree
2. The properties panel will automatically appear in the right sidebar
3. Configure operation-specific settings as needed

### Key Features

- **Per-Operation Overrides**: Customize settings for individual operations
- **Conditional Controls**: Advanced options appear only when enabled
- **Real-time Updates**: Changes apply immediately to the selected operation
- **Parameter Validation**: Automatic validation and type conversion of settings

### Basic Usage

1. **Select Operation**: Click on a Balor operation in the operations tree
2. **Enable Custom Settings**: Check boxes to enable operation-specific parameters
3. **Adjust Values**: Set custom values for speed, timing, or pulse width
4. **Apply Changes**: Settings are applied automatically as you change them

## Technical Details

The Balor Operation Properties panel integrates with the Balor Parameters system:

- **Parameters Class**: Wraps operation settings with attribute-style access
- **Validation System**: Ensures parameter types and ranges are correct
- **Conditional Display**: Advanced options only show when prerequisite settings are enabled
- **Settings Inheritance**: Falls back to global device defaults when operation settings are disabled

### Available Parameters

#### Rapid Speed Settings
- **Enable Custom Rapid-Speed**: Override global travel speed for this operation
- **Travel Speed**: Custom speed for non-cutting moves (jumps between cuts)

#### Pulse Width Settings (MOPA Lasers)
- **Enable Custom Pulse Width**: Override global pulse width setting
- **Set Pulse Width**: Custom pulse width in nanoseconds (1-250ns range)

#### Timing Settings
- **Enable Custom Timings**: Override global timing delays
- **Laser On Delay**: Delay before laser activates (in microseconds)
- **Laser Off Delay**: Delay after laser deactivates (in microseconds)
- **Polygon Delay**: Delay between polygon points (0-655350 microseconds)

### Parameter Validation

The Parameters class automatically validates and converts settings:
- **Float Parameters**: speed, frequency, power, delays (converted to float)
- **Integer Parameters**: pulse_width (converted to int)
- **Boolean Parameters**: enabled flags (converted to boolean)
- **Range Checking**: Some parameters have min/max limits

## Safety Considerations

- **Parameter Limits**: Always verify that custom settings are within safe ranges for your laser
- **Material Compatibility**: Different materials may require different timing and power settings
- **Testing**: Test custom operation settings on scrap material first
- **Documentation**: Keep records of successful parameter combinations for future reference

## Troubleshooting

### Settings Not Applying

**Problem**: Custom operation settings aren't taking effect
- **Check Enable Boxes**: Ensure the "Enable Custom..." checkboxes are checked
- **Operation Selection**: Verify the correct operation is selected
- **Global Overrides**: Some global settings may still take precedence
- **Parameter Validation**: Check that values are within valid ranges

### Conditional Options Not Showing

**Problem**: Advanced options don't appear in the panel
- **Prerequisites**: Make sure prerequisite options are enabled first
- **Device Compatibility**: Some options only appear for compatible laser types
- **Panel Refresh**: Try selecting a different operation and reselecting

### Parameter Conflicts

**Problem**: Operation settings conflict with global device settings
- **Hierarchy Understanding**: Operation settings override globals when enabled
- **Compatibility**: Ensure operation settings are compatible with device capabilities
- **Testing**: Always test new parameter combinations

## Related Topics

- [Online Help: Balorconfig](Online-Help-balorconfig) - Global device configuration settings
- [Online Help: Balorcontroller](Online-Help-balorcontroller) - Device connection and control
- [Online Help: Operations](Online-Help-operations) - Working with laser operations
- [Online Help: Cut Planning](Online-Help-cutplanning) - How operations are processed
- [Online Help: Laser Parameters](Online-Help-laserparameters) - Understanding laser settings

## Advanced Usage

### Operation-Specific Optimization

Different operations benefit from different settings:

**Fine Engraving**:
- Lower speeds (50-200 mm/min)
- Custom timing enabled
- Precise delays for quality

**High-Speed Cutting**:
- Higher speeds (500-2000 mm/min)
- Custom rapid speeds for efficiency
- Minimal delays for speed

**Complex Shapes**:
- Custom polygon delays
- Appropriate jump speeds
- Pulse width optimization

### Parameter Interactions

Understanding how parameters interact:

- **Speed vs Power**: Higher speeds often require more power for consistent results
- **Timing vs Quality**: Shorter delays increase speed but may reduce quality
- **Pulse Width**: Affects beam characteristics, especially important for metals
- **Rapid Speed**: Should be much faster than cutting speed for efficiency

### Workflow Integration

The operation properties panel works with:

- **Operations Tree**: Select operations to configure
- **Device Settings**: Global defaults that operations can override
- **Cut Planning**: How operation settings affect job execution
- **Material Profiles**: Predefined parameter sets for common materials

---

*This help page provides comprehensive documentation for the Balor Operation Properties panel functionality in MeerK40t.*
