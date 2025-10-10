# Online Help: Defaultactions

## Overview

This help page covers the **Defaultactions** functionality in MeerK40t.

The Default Actions panel provides comprehensive control over automatic operations that execute before and after laser cutting jobs. This feature allows users to create standardized workflows by defining sequences of actions that run automatically at job start and job end, ensuring consistent behavior across all laser operations.

The default actions configuration is accessed through **Device Settings → GRBL-Configuration → Default Actions** tab, or similar device configuration panels.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\device\gui\defaultactions.py`

## Category

**GUI**

## Description

The Default Actions system enables users to define automatic sequences of operations that execute before and after laser jobs. Users would use this feature when they need to:

- **Standardize job workflows** with consistent pre/post-job procedures
- **Automate safety procedures** like homing and coolant control
- **Add audible feedback** with beeps for job status
- **Implement device preparation** sequences before cutting
- **Handle job interruptions** gracefully with cleanup actions
- **Manage system resources** like hibernation prevention during jobs
- **Create custom initialization** sequences for specific materials or techniques

The system provides both predefined standard actions and the ability to customize parameters, ensuring flexible automation of laser cutting workflows.

## How to Use

### Main Interface Components

#### Action Library (Left Panel)
A list of available standard actions with icons and tooltips:

- **Home**: Move laser to logical home position
- **Physical Home**: Move laser to physical home position ($H)
- **Goto Origin/Goto 0,0**: Move to absolute coordinates
- **Beep**: Generate audible feedback
- **Interrupt**: Stop current operation with message
- **Console**: Execute custom console commands
- **Coolant On/Off**: Control cooling systems
- **Hibernation Prevent/Allow**: System sleep management (if available)

#### Job Start Actions (Top Right)
Operations that execute before the main job begins.

#### Job End Actions (Bottom Right)
Operations that execute after the main job completes.

### Key Features

- **Drag-and-Drop Management**: Add actions to start/end lists with parameter customization
- **Order Control**: Move actions up/down to control execution sequence
- **Parameter Modification**: Customize action parameters for specific needs
- **Visual Feedback**: Icons and tooltips for easy action identification
- **Persistent Configuration**: Settings saved and restored between sessions
- **Multi-Selection**: Add multiple actions at once with default parameters

### Basic Usage

1. **Open Default Actions**: Access via Device Settings → [Device]-Configuration → Default Actions tab
2. **Select Action**: Click on desired action from the library (left panel)
3. **Customize Parameters**: Modify the parameter field if needed (optional)
4. **Add to Job Start/End**: Click "Add to Job Start" or "Add to Job End" button
5. **Adjust Order**: Use up/down arrows to reorder actions in the sequence
6. **Modify Parameters**: Select an action and edit its parameter field
7. **Remove Actions**: Select action and click trash icon to remove
8. **Test Configuration**: Run a job to verify the action sequences execute correctly

### Advanced Usage

#### Action Parameter Customization
- **Home Commands**: Choose between logical (`util home`) and physical (`util home True`) homing
- **Coordinate Moves**: Specify exact coordinates like `100,200` or `50mm,30mm`
- **Console Commands**: Execute complex commands like `interrupt "Job paused by user"`
- **Coolant Control**: Use device-specific coolant commands

#### Workflow Examples
- **Pre-Job Setup**: Home laser → Turn on coolant → Prevent system sleep
- **Post-Job Cleanup**: Move to safe position → Turn off coolant → Allow system sleep → Beep completion
- **Safety Sequences**: Physical home → Interrupt check → Coolant verification

#### Multi-Action Management
- **Bulk Addition**: Select multiple actions and add them at once
- **Parameter Templates**: Use default parameters for common actions
- **Sequence Optimization**: Order actions for efficient workflow execution

## Technical Details

The Default Actions system integrates with MeerK40t's job execution pipeline:

**Core Components:**
- **DefaultActionPanel**: Main wxPython interface with dual-list management
- **Action Library**: Predefined standard actions with metadata
- **Parameter System**: Dynamic parameter modification and validation
- **Persistence Layer**: Settings stored in device configuration

**Data Structures:**
- **Standards List**: Array of predefined actions with command, parameter, and tooltip
- **Operation Lists**: Separate arrays for prepend (start) and append (end) actions
- **Parameter Storage**: Each action stores command and parameter strings

**Execution Flow:**
1. **Job Start**: Prepend actions execute in order before main operations
2. **Main Job**: Standard laser operations execute
3. **Job End**: Append actions execute in order after main operations

**Integration Points:**
- **Job Pipeline**: Actions injected into job execution sequence
- **Device Context**: Actions execute within device command context
- **Signal System**: No direct signals, actions execute via command pipeline
- **Configuration**: Settings persist in device settings with numbered attributes

**Command Types:**
- **util commands**: Internal MeerK40t utilities (home, goto, console)
- **console commands**: Direct device console commands
- **Device-specific**: Commands that vary by device type (GRBL, etc.)

## Related Topics

- [[Online Help: Effects]] - Laser operation effects and modifications
- [[Online Help: Formatter]] - Output formatting and processing
- [[Online Help: Warning]] - Warning and safety systems
- [[Online Help: Grblconfig]] - GRBL device configuration

## Screenshots

*Default Actions panel showing action library and job start/end lists:*

*Action parameter customization and order management:*

*Predefined standard actions with icons and tooltips:*

---

This documentation covers the complete Default Actions functionality in MeerK40t, providing guidance for automating laser job workflows with pre and post-job operations.
