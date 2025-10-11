# Online Help: Autoexec

## Overview

The **Autoexec** (Auto Execute) functionality allows you to define commands that automatically run when a MeerK40t project file is loaded. This powerful feature enables workflow automation, device configuration, and setup tasks to happen automatically, saving time and ensuring consistency across projects.

Autoexec commands are stored within project files and can be configured to execute immediately upon file loading, making it ideal for:
- **Device activation**: Automatically switch to the correct laser device
- **Workflow setup**: Initialize simulation windows or prepare the workspace
- **Configuration**: Set device parameters or preferences
- **Safety checks**: Run validation commands before starting work

## What is Autoexec?

Autoexec is MeerK40t's automation system for project file loading. When enabled, it executes a predefined list of console commands immediately after a project file opens, allowing you to:

- **Automate repetitive tasks**: Eliminate manual setup steps
- **Ensure consistency**: Apply standard configurations automatically
- **Streamline workflows**: Jump straight into productive work
- **Customize environments**: Set up device-specific parameters

### Important Safety Note

⚠️ **Autoexec commands have full access to MeerK40t's functionality**. While this enables powerful automation, it also means autoexec can:
- **Start burns automatically** (potentially dangerous)
- **Change device settings** (may affect other projects)
- **Execute any console command** (including destructive operations)

Always review autoexec commands before enabling them, and consider the security implications.

## Location in MeerK40t

The Autoexec functionality is accessed through:
- **Menu**: `File` → `Startup Commands`
- **Toolbar**: Autoexec button (when available)
- **Source code**: `meerk40t\gui\autoexec.py`

## Category

**GUI**

## Description

The Autoexec panel provides a text editor for defining commands that execute automatically when project files load. It includes safety controls and helpful command suggestions to make automation both powerful and safe.

### Key Features

- **Command Editor**: Multi-line text editor for autoexec commands
- **Enable/Disable Toggle**: Safety control to activate/deactivate autoexec
- **Manual Execution**: Test commands without saving to file
- **Command Suggestions**: Built-in menu of common useful commands
- **Syntax Highlighting**: Clear command formatting and comments support
- **File Integration**: Commands stored within project files

### Command Syntax

Autoexec supports all MeerK40t console commands:
- **One command per line**
- **Comments** start with `#` (ignored during execution)
- **Sequential execution** from top to bottom
- **Error handling** continues despite individual command failures

## How to Use

### Basic Autoexec Setup

1. **Open Autoexec Panel**: Go to `File` → `Startup Commands`
2. **Write Commands**: Enter console commands in the text editor, one per line
3. **Test Commands**: Click "Execute commands" to test without saving
4. **Enable Autoexec**: Check "Execute on load" to activate automatic execution
5. **Save File**: Autoexec commands are stored within the project file

### Writing Autoexec Commands

#### Basic Command Structure
```
# This is a comment (ignored)
device activate MyLaser
window open Simulation z
planz clear copy preprocess validate blob preopt optimize
```

#### Common Autoexec Patterns

**Device Setup:**
```
# Activate specific laser device
device activate K40-CO2

# Set device-specific parameters
device setting speed 100
device setting power 50
```

**Workspace Preparation:**
```
# Open simulation window
window open Simulation z

# Clear and prepare workspace
planz clear copy preprocess validate blob preopt optimize
```

**Safety and Validation:**
```
# Clear console before starting
clear

# Validate project before proceeding
planz validate
```

### Using the Command Helper

The `*` button provides quick access to common commands:

- **Clear console**: Clears the console output
- **Start simulation**: Opens simulation with full processing pipeline
- **Burn content**: Immediately starts burning (⚠️ use with extreme caution)
- **Device activation**: Quick device switching commands

### Advanced Usage

#### Conditional Execution
Use comments to create conditional logic:
```
# Device setup - uncomment appropriate line
# device activate K40-CO2
device activate Galvo-Fiber

# Optional simulation
# window open Simulation z
```

#### Multi-Device Workflows
```
# Switch to engraving device
device activate K40-CO2
device setting speed 200
device setting power 30

# Process engraving operations
planz clear copy preprocess validate blob preopt optimize
```

#### Project-Specific Automation
```
# Project: Logo engraving
device activate FiberLaser
window open Simulation z
planz clear copy preprocess validate blob preopt optimize
```

### Safety Best Practices

#### Before Enabling Autoexec
- **Test commands manually** using "Execute commands" button
- **Review all commands** for potentially destructive operations
- **Consider impact** on other projects using the same device
- **Use comments** to document command purposes

#### Safe Autoexec Patterns
```bash
# Safe startup sequence
clear
device activate SafeDevice
window open Simulation z
# burn  # Commented out for safety
```

#### Risk Mitigation
- **Disable autoexec** for unfamiliar project files
- **Test in simulation** before enabling burn commands
- **Use specific device names** to avoid conflicts
- **Document commands** with clear comments

## Technical Details

The Autoexec system integrates deeply with MeerK40t's command infrastructure:

### Core Components
- **Command Parser**: Processes console commands sequentially
- **File Integration**: Stores commands in project file metadata
- **Safety Controls**: Enable/disable toggle prevents accidental execution
- **Event System**: Responds to file load events automatically

### Key Technologies
- **Console Command System**: Full access to all MeerK40t commands
- **File Metadata**: Commands stored as file properties
- **Event-driven Execution**: Automatic triggering on file load
- **Error Resilience**: Continues execution despite individual command failures

### Execution Flow

1. **File Load Detection**: System detects project file opening
2. **Autoexec Check**: Verifies if autoexec is enabled for this file
3. **Command Parsing**: Breaks multi-line text into individual commands
4. **Sequential Execution**: Runs each command in order
5. **Error Handling**: Logs failures but continues with remaining commands
6. **Completion**: Reports execution status

### Storage Mechanism

Autoexec commands are stored as file metadata:
- **Location**: Within project file structure
- **Format**: Multi-line text with comment support
- **Persistence**: Survives file save/load cycles
- **Sharing**: Included when files are shared or copied

## Related Topics

- [Online Help: Console](Online-Help-console)
- [Online Help: File Operations](Online-Help-fileoperations)
- [Online Help: Device Management](Online-Help-devicemanagement)
- [Online Help: Simulation](Online-Help-simulation)

## Screenshots

*Autoexec panel showing command editor and control buttons*

*Command helper menu with common autoexec commands*

*Autoexec commands stored within project file*

*Safety warning about automatic command execution*

---

*This help page provides comprehensive documentation for MeerK40t's autoexec automation functionality.*
