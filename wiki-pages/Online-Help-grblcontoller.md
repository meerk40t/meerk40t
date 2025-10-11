# Online Help: Grblcontroller

## Overview

This help page covers the **Grblcontroller** functionality in MeerK40t.

The GRBL Controller provides a real-time communication interface for GRBL-compatible laser devices. This window serves as the primary control panel for direct device interaction, allowing users to connect/disconnect, send commands, execute macros, and monitor all communication in real-time.

The controller window is typically accessed through **Device Control → GRBL Controller** in the menu system or via the `grblcontroller` command.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\grbl\gui\grblcontroller.py`

## Category

**GRBL**

## Description

The GRBL Controller is the primary interface for real-time communication and control of GRBL-based laser cutters. Users would use this controller when they need to:

- **Establish or terminate connections** to GRBL devices
- **Send individual G-code commands** for testing and debugging
- **Execute predefined macros** for common operations
- **Monitor device status** and communication in real-time
- **Clear alarms and reset** the device when issues occur
- **Query device parameters** and configuration settings
- **Perform homing operations** and status checks
- **Debug communication issues** by viewing raw data exchange

The interface provides both automated control buttons for common operations and manual command entry for advanced users. All communication is logged in real-time, making it invaluable for troubleshooting device issues.

## How to Use

### Main Control Elements

#### Connection Management
- **Connect/Disconnect Button**: Primary connection control with status color coding
  - Green: Connected successfully
  - Yellow: Connecting/disconnecting or uninitialized
  - Shows current interface (Serial port, TCP address, WebSocket, or Mock)

#### Status Display
- **Device Status Label**: Shows current GRBL state (Idle, Run, Hold, etc.)
- **Error State Button**: Appears when device is in alarm/error condition

#### Communication Log
- **Data Exchange Window**: Real-time display of all sent/received communication
- **Clear Button**: Clears the communication log

### Predefined Command Buttons

The controller provides quick-access buttons for common GRBL operations:

- **Home/Physical Home**: Moves laser to home position ($H or G28)
- **Reset**: Emergency stop and reset (\x18)
- **Status**: Query current device status (?)
- **Clear Alarm**: Clear alarms and unlock device ($X)
- **Gcode Parameters**: Display active G-code parameters ($#)
- **GRBL Parameters**: Display GRBL configuration parameters ($$)
- **Build Info**: Show device build information ($I)

### Macro System

Five customizable macro buttons (Macro 1-5) allow storing frequently used command sequences:

- **Execute Macro**: Left-click to run the stored commands
- **Edit Macro**: Right-click to open editor dialog
- **Multi-line Support**: Macros can contain multiple G-code commands
- **Comment Support**: Lines starting with # are treated as comments

### Manual Command Entry

- **G-code Input Field**: Enter custom commands with Enter to send
- **Command History**: Use Up/Down arrows to navigate previous commands
- **Real-time Commands**: Special commands (! ~ ?) are sent via real-time channel
- **Auto-save History**: Last 50 commands saved to disk automatically

### Key Features

- **Real-time Communication**: All data exchange displayed instantly
- **Color-coded Status**: Visual indication of connection state
- **Command Validation**: Automatic routing of commands to appropriate channels
- **Error Recovery**: Dedicated error state handling and alarm clearing
- **Persistent History**: Command history survives application restarts
- **Multi-interface Support**: Works with Serial, TCP, WebSocket, and Mock connections

### Basic Usage

1. **Open Controller**: Access via Device Control → GRBL Controller or `grblcontroller` command
2. **Connect Device**: Click "Connect" button (shows interface details)
3. **Verify Connection**: Watch communication log for successful connection messages
4. **Send Commands**: Use predefined buttons or enter custom G-code
5. **Monitor Operations**: Observe real-time status and communication
6. **Execute Macros**: Use macro buttons for common command sequences
7. **Handle Errors**: Use Clear Alarm button if device enters error state
8. **Disconnect**: Click "Disconnect" when finished

### Advanced Usage

#### Macro Customization
Right-click any macro button to open the editor:
- Enter multi-line G-code sequences
- Use # for comments
- Commands execute in order
- Macros persist between sessions

#### Command History Navigation
- Press Up arrow to recall previous commands
- Press Down arrow to navigate forward in history
- Commands automatically saved and restored

#### Real-time vs Standard Commands
- Real-time commands (! ~ ?) sent immediately via interrupt
- Standard G-code sent through normal command queue
- Real-time commands don't wait for "ok" responses

#### Status Monitoring
- Device status updates automatically in the interface
- Color coding provides quick visual feedback
- Communication log shows all raw data exchange

## Technical Details

The GRBL Controller integrates deeply with MeerK40t's device communication system:

**Core Components:**
- **GRBLControllerPanel**: Main wxPython interface with controls and display
- **Communication Watcher**: Real-time monitoring of device data exchange
- **Command Routing**: Intelligent routing between real-time and standard command channels
- **State Management**: Color-coded status display with state persistence

**Signal Integration:**
- `update_interface`: Updates button states and connection indicators
- `grbl_controller_update`: Refreshes communication log display
- `grbl;status`: Receives device status updates

**Data Flow:**
1. User input → Command validation → Routing decision
2. Real-time commands → Direct controller interrupt
3. Standard commands → Driver queue → Controller transmission
4. Received data → Watcher callback → Log display update

**File Persistence:**
- Command history: `grblhistory.log` in working directory
- Macro definitions: Stored in device settings
- Window layout: Aspect ratio preservation

## Related Topics

- [Online Help: Grblconfig](Online-Help-grblconfig) - GRBL device configuration and setup
- [Online Help: Grblhwconfig](Online-Help-grblhwconfig) - Hardware-specific GRBL configuration
- [Online Help: Grbloperation](Online-Help-grbloperation) - GRBL device operation and job execution
- [Online Help: Devices](Online-Help-devices) - General device management

## Screenshots

*GRBL Controller window showing connection status and command buttons:*

*Communication log displaying real-time data exchange:*

*Macro editing dialog for customizing command sequences:*

---

This documentation covers the complete GRBL Controller functionality in MeerK40t, providing guidance for both basic device control and advanced communication debugging.
