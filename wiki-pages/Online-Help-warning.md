# Online Help: Warning

## Overview

This help page covers the **Warning** functionality in MeerK40t.

The Warning system provides safety monitoring for laser operations by alerting users when power and speed settings may be too extreme for their laser hardware. It displays visual warning indicators in the operation tree when configured thresholds are exceeded.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\device\gui\warningpanel.py`

## Category

**GUI**

## Description

The Warning system is a critical safety feature that helps prevent damage to laser equipment and materials by monitoring operation parameters. It allows users to set safe operating limits for power and speed across different operation types (cut, engrave, raster, image, dots, hatch), and provides immediate visual feedback when those limits are exceeded.

This feature is essential for:

- **Equipment Protection**: Preventing laser damage from excessive power settings
- **Material Safety**: Avoiding material damage from inappropriate speed/power combinations
- **Workflow Safety**: Providing visual cues during job setup and optimization
- **Quality Assurance**: Ensuring consistent and safe operation parameters

The system displays a warning indicator (❌) in the operation node labels when configured thresholds are violated, helping users identify potentially problematic operations before execution.

## How to Use

### Accessing Warning Configuration

The Warning panel is available in device configuration dialogs for laser controllers:

1. **Device Configuration**: Open device settings for your laser controller
2. **Warning Tab**: Navigate to the Warning configuration section
3. **Threshold Setup**: Configure minimum and maximum limits for each operation type

### Available Controls

The Warning panel displays a grid of controls organized by operation type and parameter:

#### Operation Types
- **Cut**: Vector cutting operations
- **Engrave**: Vector engraving operations
- **Raster**: Raster engraving operations
- **Image**: Image-based operations
- **Dots**: Single point operations
- **Hatch**: Hatching/fill operations

#### Parameters per Operation
- **Power**: Laser power settings (displayed in % or PPI based on preferences)
- **Speed**: Movement speed (displayed in mm/min or mm/s based on preferences)

#### Threshold Controls
For each operation and parameter combination:
- **Enable Checkbox (<)**: Activate minimum threshold warning
- **Minimum Value**: Threshold value below which warnings are triggered
- **Enable Checkbox (>)**: Activate maximum threshold warning
- **Maximum Value**: Threshold value above which warnings are triggered

### Key Features

- **Visual Indicators**: Warning symbols (❌) appear in operation tree labels
- **Unit Awareness**: Automatically adapts to power (%) and speed (mm/min) display preferences
- **Real-time Updates**: Warnings update immediately when parameters change
- **Operation-Specific**: Different thresholds for each operation type
- **Dual Thresholds**: Separate minimum and maximum limits per parameter

### Basic Usage Workflow

1. **Assess Equipment**: Determine safe operating ranges for your laser
2. **Configure Thresholds**: Set minimum and maximum limits for each operation type
3. **Monitor Operations**: Watch for warning indicators in the operation tree
4. **Adjust Parameters**: Modify operation settings when warnings appear
5. **Verify Safety**: Ensure all operations are within safe ranges before execution

### Advanced Configuration

- **Power Units**: Thresholds automatically convert between percentage and PPI
- **Speed Units**: Automatic conversion between mm/min and mm/s
- **Operation Categories**: Different safety limits for cutting vs engraving operations
- **Material Considerations**: Set different thresholds for different materials
- **Progressive Warnings**: Use both minimum and maximum thresholds for comprehensive monitoring

## Technical Details

The Warning system integrates deeply with MeerK40t's operation management:

### Warning Storage
Settings are stored per device with keys like `dangerlevel_op_cut`, `dangerlevel_op_engrave`, etc. Each operation type maintains an 8-element array:
```
[min_power_active, min_power_value, max_power_active, max_power_value,
 min_speed_active, min_speed_value, max_speed_active, max_speed_value]
```

### Visual Integration
Warnings appear as danger indicators in the operation tree through the `updateop_tree` signal. The tree rendering code checks operation parameters against configured thresholds and displays warning symbols when violations occur.

### Unit Conversion
The system automatically handles unit conversions:
- **Power**: Converts between percentage (100%) and PPI (1000) based on display preferences
- **Speed**: Converts between mm/min (60000) and mm/s (1000) based on display preferences

### Signal Integration
- **power_percent**: Updates when power display units change
- **speed_min**: Updates when speed display units change
- **updateop_tree**: Triggers tree refresh when warning thresholds change

## Troubleshooting

### Common Issues

- **Warnings not appearing**: Ensure thresholds are enabled and values are set correctly
- **Incorrect units**: Check power/speed display preferences in the main preferences
- **Tree not updating**: Try refreshing the operation tree or restarting MeerK40t
- **Thresholds not saving**: Ensure device configuration is saved after changes

### Threshold Configuration Tips

- **Start Conservative**: Set initial thresholds based on manufacturer specifications
- **Test Gradually**: Increase limits incrementally while monitoring equipment
- **Material Specific**: Different materials may require different safety limits
- **Operation Aware**: Cutting operations typically need higher power than engraving

### Performance Considerations

- **Minimal Overhead**: Warning calculations have negligible performance impact
- **Real-time Updates**: Threshold checking occurs during tree rendering
- **Memory Efficient**: Settings stored as simple arrays with minimal memory usage

## Related Topics

*Link to related help topics:*

- [[Online Help: Operationproperty]] - Operation parameter configuration
- [[Online Help: Preferences]] - Power and speed display unit settings
- [[Online Help: Tree]] - Operation tree display and navigation
- [[Online Help: Devices]] - Device-specific configuration access

## Screenshots

The Warning configuration panel includes:

1. **Information Header**: Explains the warning system's purpose and visual indicators
2. **Operation Grid**: Matrix of operation types (cut, engrave, raster, etc.) with power and speed controls
3. **Threshold Controls**: Checkboxes and text fields for minimum/maximum thresholds
4. **Unit Labels**: Dynamic labels showing current power (%) and speed (mm/min) units
5. **Visual Feedback**: Icons for each operation type to aid identification

The panel automatically adapts to display preferences and provides tooltips for all controls. Warning indicators appear as red "❌" symbols next to operation labels in the tree view when thresholds are exceeded.

---

*This help page provides comprehensive documentation for MeerK40t's laser safety warning and threshold monitoring system.*
