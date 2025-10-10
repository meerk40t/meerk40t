# Online Help: Operationproperty

## Overview

This help page covers the **Operationproperty** functionality in MeerK40t.

The Operation Properties panel provides comprehensive control over laser operation parameters, including layer settings, speed/power controls, raster configurations, passes, dwell times, and operation information. This panel is the central hub for configuring how laser operations execute.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\propertypanels\operationpropertymain.py`

## Category

**Operation Properties**

## Description

The Operation Properties panel is a multi-section configuration interface that allows you to fine-tune every aspect of laser operations. It includes controls for classification rules, speed and power settings, raster patterns, operation passes, timing parameters, and informational displays. This panel adapts its interface based on the operation type (Cut, Engrave, Raster, Image, or Dots).

## How to Use

### Key Features

- Integrates with: `tree_changed`
- Integrates with: `activate_single_node`
- Integrates with: `service/device/active`
- Multi-panel configuration interface
- Operation-type-specific controls
- Real-time parameter updates

### Basic Usage

1. **Select Operation**: Choose an operation in the elements tree to display its properties
2. **Configure Layer Settings**: Set classification rules and operation behavior
3. **Adjust Speed/Power**: Configure movement speed and laser power parameters
4. **Set Passes**: Define how many times the operation should repeat
5. **Configure Raster**: Set raster direction and optimization for image operations
6. **Review Information**: Check element counts and time estimates

## Property Panels

### ID Panel

**Operation Identification**:
- Unique operation identifier
- Custom operation labeling
- Hierarchical organization support

### Layer Settings Panel

**Color Classification**:
- **Layer Color**: Visual identifier and classification color for the operation
- **Stroke Classification**: Use stroke color to match elements to this operation
- **Fill Classification**: Use fill color to match elements to this operation
- **Stop Classification**: Prevent further classification when this operation matches

**Operation Control**:
- **Enable**: Include/exclude operation from job execution
- **Visible**: Show/hide operation elements on canvas
- **Default**: Allow operation to accept unassigned elements of matching color

### Speed/PPI Panel

**Speed Settings**:
- **Speed**: Movement speed in mm/s or mm/min (configurable display)
- **Power**: Laser power in PPI (pulses per inch) or percentage
- **Frequency**: Laser pulse frequency in kHz (if supported)

**Safety Warnings**:
- Visual indicators for parameters outside recommended ranges
- Configurable warning thresholds based on device capabilities
- Real-time validation against danger level settings

### Passes Panel

**Operation Repetition**:
- **Passes**: Number of times to repeat the operation (when enabled)
- **Kerf Compensation**: Adjust path for laser beam width (Cut operations only)
- **Coolant Control**: Manage coolant system state during operation

**Kerf Settings**:
- Positive values: outward compensation (larger cut)
- Negative values: inward compensation (smaller cut)
- Measured in millimeters with length validation

### Raster Settings Panel (Image/Raster Operations)

**Resolution Control**:
- **DPI Override**: Override image DPI settings
- **Laser Dot Consideration**: Optimize for laser beam diameter
- **Grayscale Mode**: Use grayscale instead of black/white conversion

**Direction Control**:
- **Raster Direction**: Choose from multiple scanning patterns:
  - Top to Bottom / Bottom to Top (recommended for X-axis scanning)
  - Left to Right / Right to Left (Y-axis scanning, slower)
  - Crosshatch (two-pass: horizontal then vertical)
  - Greedy Horizontal/Vertical (optimize for sparse images)
  - Spiral and Diagonal patterns

**Movement Optimization**:
- **Bidirectional**: Scan on both forward and return sweeps
- **Overscan**: Add padding at line ends for speed control
- **Start Preference**: Control scanning start position and direction

### Dwell Settings Panel (Dots Operations)

**Timing Control**:
- **Dwell Time**: Duration in milliseconds at each dot location
- Precise control over laser exposure time for dot-based operations

### Info Panel

**Operation Statistics**:
- **Children**: Number of elements assigned to the operation
- **Estimated Time**: Calculated execution time for the operation
- **Re-Classify**: Reassign elements based on current classification rules

## Operation Types

### Cut Operations

**Available Panels**: All panels except Raster Settings and Dwell Settings
**Key Features**:
- Kerf compensation for accurate cutting
- Speed and power optimization
- Multiple passes for thick materials
- Coolant system integration

### Engrave Operations

**Available Panels**: All panels except Raster Settings and Dwell Settings
**Key Features**:
- Vector-based engraving parameters
- Speed and power control
- Multi-pass capabilities
- Classification by stroke/fill colors

### Raster Operations

**Available Panels**: All panels including Raster Settings
**Key Features**:
- Image-based engraving with full raster control
- Multiple scanning patterns and optimizations
- DPI and resolution management
- Grayscale processing options

### Image Operations

**Available Panels**: All panels including Raster Settings
**Key Features**:
- Advanced image processing capabilities
- Raster direction optimization
- Laser dot diameter consideration
- Overscan and bidirectional control

### Dots Operations

**Available Panels**: All panels except Raster Settings, plus Dwell Settings
**Key Features**:
- Precise dot placement with dwell time control
- Speed and power management
- Multi-pass dot engraving
- Classification and assignment controls

## Technical Details

The ParameterPanel class extends ScrolledPanel and orchestrates multiple specialized sub-panels for comprehensive operation configuration.

**Key Technical Components**:
- **Modular Panel System**: Individual panels for different parameter categories
- **Dynamic Panel Display**: Panels show/hide based on operation type compatibility
- **Signal Integration**: Real-time updates through signal listeners
- **Device Integration**: Adapts to device capabilities and settings
- **Property Validation**: Range checking and safety warnings

**Panel Management**:
- **accepts() Method**: Determines which operations each panel supports
- **set_widgets()**: Populates panel controls with operation parameters
- **Signal Listeners**: Respond to property changes and device updates
- **Layout Management**: Dynamic sizing and scrolling for complex interfaces

**Data Flow**:
1. Operation selection triggers panel updates
2. Each sub-panel loads relevant parameters
3. User changes propagate through signal system
4. Real-time validation and UI updates
5. Changes saved to operation objects

## Usage Guidelines

### Parameter Optimization

**Speed vs. Quality**:
- Higher speeds reduce execution time but may affect quality
- Lower speeds provide better control but increase processing time
- Balance based on material and desired finish

**Power Management**:
- PPI mode: Precise control over laser energy delivery
- Percentage mode: Simplified power scaling
- Consider material thickness and laser capabilities

### Raster Optimization

**Direction Selection**:
- X-axis scanning (T2B/B2T) generally faster and smoother
- Y-axis scanning provides alternative patterns but slower
- Greedy modes optimize for images with white space
- Bidirectional scanning reduces total job time

**Resolution Settings**:
- Higher DPI increases detail but slows processing
- Laser dot consideration prevents over-burning overlaps
- Overscan helps with acceleration/deceleration

### Safety Considerations

**Parameter Validation**:
- Pay attention to warning indicators for unsafe settings
- Configure danger level thresholds in device settings
- Test new parameter combinations on scrap material
- Monitor equipment during operation

**Multi-Pass Operations**:
- Use passes for thick materials or special effects
- Allow cooling time between passes
- Verify alignment between passes
- Consider ventilation for extended operations

## Troubleshooting

### Panel Not Displaying

**Operation Selection**:
- Ensure a valid operation is selected in the tree
- Check that the operation type is supported
- Try refreshing the tree or restarting the panel

**Compatibility Issues**:
- Some panels only appear for specific operation types
- Verify operation type matches panel requirements
- Check for device capability restrictions

### Parameter Changes Not Applying

**Signal Issues**:
- Changes should apply immediately through signal system
- Try clicking outside the control to trigger updates
- Check console for error messages
- Restart MeerK40t if problems persist

### Time Estimates Incorrect

**Calculation Issues**:
- Ensure operation has valid speed and power settings
- Check that elements are properly assigned
- Verify device capabilities are correctly configured
- Try recalculating estimates manually

### Raster Settings Not Available

**Operation Type**:
- Raster settings only appear for Raster and Image operations
- Switch operation type if raster control is needed
- Verify operation classification is correct

## Advanced Features

### Dynamic Panel Adaptation

**Context-Aware Interface**:
- Panels appear/disappear based on operation type
- Controls enable/disable according to device capabilities
- Tooltips provide detailed parameter explanations
- Validation adapts to device-specific limits

### Real-time Validation

**Safety Monitoring**:
- Warning levels based on device danger settings
- Visual indicators for parameter ranges
- Automatic validation on value changes
- Integration with device capability detection

### Classification Integration

**Smart Element Assignment**:
- Color-based automatic classification
- Stroke/fill attribute matching
- Stop rules for classification precedence
- Default operation fallback behavior

## Related Topics

*Link to related help topics:*

- [[Online Help: Operationinfo]]
- [[Online Help: Opbranchproperty]]
- [[Online Help: Pathproperty]]
- [[Online Help: Laserpanel]]

## Screenshots

*Add screenshots showing the operation properties panel with different operation types and configuration options.*

---

*This help page provides comprehensive documentation for the Operation Properties panel in MeerK40t.*
