# Online Help: Grbloperation

## Overview

This help page covers the **Grbloperation** functionality in MeerK40t.

The GRBL Operation Configuration panel provides advanced settings for individual GRBL laser operations. This panel appears as an "Advanced" tab in the operation properties dialog, allowing fine-tuned control over Z-axis positioning and custom G-code execution for specific operations.

The operation configuration is accessed when editing individual laser operations (cut, engrave, raster, etc.) in the operations tree, providing GRBL-specific enhancements beyond standard operation parameters.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\grbl\gui\grbloperationconfig.py`

## Category

**GRBL**

## Description

The GRBL Operation Configuration panel extends standard laser operations with GRBL-specific advanced features. Users would use this configuration when they need to:

- **Control Z-axis positioning** for operations requiring specific focal heights
- **Add custom G-code commands** to be executed before an operation starts
- **Implement multi-layer operations** with different Z-heights
- **Execute setup commands** specific to certain materials or techniques
- **Override default Z-behavior** for specialized cutting/engraving requirements
- **Add operation-specific initialization** code for complex workflows

This panel integrates with MeerK40t's operation system to provide per-operation GRBL enhancements while maintaining compatibility with the standard operation workflow.

## How to Use

### Main Configuration Elements

#### Z-Axis Control
- **Set Z-Axis value** (Checkbox): Enables Z-axis position control for this operation
- **Z-Axis Value** (Text Field): Specifies the Z-axis position using length units (mm, inches, etc.)

#### Custom Commands
- **Custom Code** (Multi-line Text Area): G-code commands executed at operation start

### Key Features

- **Per-Operation Z Control**: Override default Z-behavior for specific operations
- **Unit Conversion**: Automatic conversion between different length units
- **G-code Integration**: Direct execution of custom GRBL commands
- **Operation-Specific**: Settings apply only to the current operation
- **Validation**: Input validation for length values and G-code syntax

### Basic Usage

1. **Open Operation Properties**: Right-click on a GRBL operation in the operations tree
2. **Select Advanced Tab**: Switch to the "Advanced" tab in the properties dialog
3. **Enable Z-Axis Control**: Check "Set Z-Axis value" to enable Z-positioning
4. **Set Z-Position**: Enter desired Z-axis position (e.g., "5mm", "0.2in")
5. **Add Custom Commands**: Enter any G-code commands to execute before the operation
6. **Apply Changes**: Click OK to save the operation configuration

### Advanced Usage

#### Z-Axis Applications
- **Focus Adjustment**: Set different focal heights for various materials
- **Multi-Layer Operations**: Create operations at different Z-levels
- **Material Thickness**: Account for material thickness variations
- **Lens Corrections**: Compensate for different focal lengths

#### Custom Command Examples
- **Spindle Setup**: `M3 S1000` (set spindle speed)
- **Feed Rate Override**: `F500` (set feed rate)
- **Coordinate System**: `G54` (select coordinate system)
- **Modal Commands**: `G90` (absolute positioning), `G91` (relative positioning)

#### Workflow Integration
- **Pre-Operation Setup**: Commands execute before the main operation G-code
- **State Management**: Custom commands can set modal states for the operation
- **Device Preparation**: Initialize device settings specific to the operation type

## Technical Details

The GRBL Operation Configuration integrates with MeerK40t's operation property system:

**Core Components:**
- **GRBLAdvancedPanel**: Main configuration panel with Z-axis and custom command controls
- **Operation Integration**: Extends base operation classes with GRBL-specific attributes
- **Unit Conversion**: Uses MeerK40t's Length class for unit handling
- **Property Binding**: Settings stored as operation attributes (`zaxis`, `custom_commands`)

**Data Flow:**
1. **Panel Display**: `set_widgets()` loads current operation settings
2. **User Input**: Controls update operation attributes in real-time
3. **Validation**: Length values validated and converted to internal units
4. **Persistence**: Settings saved with operation in project file

**Integration Points:**
- **Operation System**: Extends standard operation properties
- **GRBL Driver**: Custom commands passed to GRBL driver for execution
- **Z-Axis Support**: Coordinates with device Z-axis capabilities
- **Command Queue**: Custom commands inserted before operation G-code

**Attribute Storage:**
- `zaxis`: Z-axis position as Length object (internal units)
- `custom_commands`: Multi-line string of G-code commands

## Related Topics

- [Online Help: Grblconfig](Online-Help-grblconfig) - General GRBL device configuration
- [Online Help: Grblcontoller](Online-Help-grblcontoller) - Real-time GRBL device control
- [Online Help: Grblhwconfig](Online-Help-grblhwconfig) - GRBL hardware parameter configuration
- [Online Help: Operationproperty](Online-Help-operationproperty) - General operation properties

## Screenshots

*GRBL Operation Configuration panel in operation properties dialog:*

*Z-axis control settings for precise focal height adjustment:*

*Custom commands section for operation-specific G-code:*

---

This documentation covers the complete GRBL Operation Configuration functionality in MeerK40t, providing guidance for advanced per-operation GRBL control and customization.
