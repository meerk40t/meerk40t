# Online Help: Grblhwconfig

## Overview

This help page covers the **Grblhwconfig** functionality in MeerK40t.

The GRBL Hardware Configuration window provides a comprehensive interface for viewing, editing, and managing all GRBL hardware parameters ($0-$199). This advanced configuration tool allows direct access to the GRBL controller's EEPROM settings, enabling fine-tuning of stepper motors, acceleration, speeds, and other critical hardware parameters.

The hardware configuration window is typically accessed through **Device Settings → GRBL Hardware Config** in the menu system or automatically when using the "Hardware properties" button in the main GRBL configuration.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\grbl\gui\grblhardwareconfig.py`

## Category

**GRBL**

## Description

The GRBL Hardware Configuration is an advanced tool for direct manipulation of GRBL controller parameters stored in EEPROM. Users would use this configuration when they need to:

- **View all current GRBL settings** in a comprehensive table format
- **Modify stepper motor parameters** (steps/mm, acceleration, max rates)
- **Adjust homing and limit switch settings**
- **Configure spindle/laser control parameters**
- **Fine-tune motion control settings** for optimal performance
- **Backup and restore hardware configurations**
- **Access detailed parameter documentation** and explanations
- **Troubleshoot hardware-related issues** by examining current settings

This interface provides direct access to all 200 possible GRBL parameters, with validation, type checking, and real-time hardware synchronization.

## How to Use

### Main Interface Elements

#### Parameter Table
The central table displays all GRBL parameters with the following columns:

- **$#**: Parameter number (0-199)
- **Parameter**: Human-readable parameter name
- **Value**: Current setting value
- **Unit**: Units for the parameter value
- **Description**: Brief parameter description
- **Info**: URL link to detailed documentation

#### Control Buttons

- **Refresh**: Reads current settings from hardware using `$$` command
- **Write**: Writes modified settings back to GRBL EEPROM
- **Export**: Saves current configuration to a .nc file
- **Explanation**: Opens official GRBL settings documentation in web browser

### Key Features

- **Real-time Editing**: Click on any value cell to edit parameters directly
- **Type Validation**: Automatic validation and conversion based on parameter data types
- **Hardware Synchronization**: Changes are written to EEPROM and verified
- **Documentation Links**: Double-click parameter info column to open detailed docs
- **Bulk Operations**: Refresh reads all parameters, Write saves all changes
- **Configuration Backup**: Export saves settings to file for backup/restore

### Basic Usage

1. **Open Hardware Config**: Access via Device Settings → GRBL Hardware Config
2. **Refresh Settings**: Click "Refresh" to read current hardware parameters
3. **Review Parameters**: Scroll through the table to see all current settings
4. **Edit Values**: Click on any value cell and enter new setting
5. **Validate Changes**: System automatically validates data types and ranges
6. **Write to Hardware**: Click "Write" to save changes to GRBL EEPROM
7. **Verify Changes**: Use "Refresh" again to confirm settings were saved
8. **Export Configuration**: Use "Export" to save settings to a file

### Advanced Usage

#### Parameter Categories
GRBL parameters are organized into logical groups:

- **$0-$9**: Stepper motor configuration (steps/mm, max rates, acceleration)
- **$10-$19**: Status report and junction deviation settings
- **$20-$29**: Soft limits, hard limits, and homing settings
- **$30-$39**: Motor current and microstepping settings
- **$100-$129**: Axis configuration (steps/mm for X, Y, Z)
- **$130-$139**: Maximum travel distances

#### Editing Parameters
- **Direct Entry**: Click value cell and type new value
- **Type Conversion**: System handles int/float conversion automatically
- **Range Validation**: Parameters are validated against reasonable ranges
- **Bitmask Support**: Boolean parameters handled as 0/1 values

#### Hardware Operations
- **EEPROM Writes**: Changes are permanently stored in GRBL's EEPROM
- **Batch Operations**: Multiple parameter changes written in sequence
- **Safety Confirmation**: Write operations require user confirmation
- **Error Handling**: Failed writes are reported with error messages

#### Documentation Access
- **Parameter Info**: Double-click info column for detailed parameter docs
- **Official Wiki**: "Explanation" button opens GRBL's official settings guide
- **Context Help**: Tooltips provide additional parameter information

## Technical Details

The GRBL Hardware Configuration integrates deeply with GRBL's parameter system:

**Core Components:**
- **GrblHardwareProperties**: Main scrolled panel with editable parameter table
- **GrblIoButtons**: Control buttons for hardware operations
- **EditableListCtrl**: Custom list control supporting inline editing
- **hardware_settings()**: Parameter definition and validation function

**Parameter System:**
- **$ Parameters**: GRBL's EEPROM-stored configuration values
- **Data Types**: int, float, boolean, bitmask with automatic validation
- **Range Checking**: Parameters validated against manufacturer specifications
- **Documentation Links**: Each parameter links to detailed technical documentation

**Communication Flow:**
1. **Refresh**: Send `$$` command → Parse response → Update table
2. **Edit**: User input → Type validation → Table update
3. **Write**: Generate `$param=value` commands → Send to hardware → EEPROM update
4. **Export**: Read table values → Write to .nc file format

**Integration Points:**
- **Signal**: `grbl:hwsettings` triggers table refresh
- **Controller**: Direct communication with GRBL controller
- **Settings**: Parameters stored in device.hardware_config dictionary
- **Validation**: Type checking and range validation before hardware writes

## Related Topics

- [Online Help: Grblconfig](Online-Help-grblconfig) - General GRBL device configuration
- [Online Help: Grblcontoller](Online-Help-grblcontoller) - Real-time GRBL device control
- [Online Help: Grbloperation](Online-Help-grbloperation) - GRBL device operation and job execution
- [Online Help: Devices](Online-Help-devices) - General device management

## Screenshots

*GRBL Hardware Configuration window showing parameter table:*

*Parameter editing with validation and documentation links:*

*Control buttons for hardware operations and documentation access:*

---

This documentation covers the complete GRBL Hardware Configuration functionality in MeerK40t, providing guidance for advanced GRBL parameter management and hardware optimization.
