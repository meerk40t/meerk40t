# Online Help: K40Controller

## Overview

This help page covers the **K40Controller** functionality in MeerK40t. The K40 Controller panel provides real-time monitoring and control of Lihuiyu/K40 laser devices. It displays connection status, packet statistics, byte-level device data, and provides USB connection management tools.

This panel provides controls for lihuiyucontroller functionality. Key controls include "Connection" (button), "Show USB Log" (checkbox), "Reset statistics" (button), and detailed status monitoring displays.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\lihuiyu\gui\lhycontrollergui.py`

## Category

**Lihuiyu/K40**

## Description

The K40 Controller is the primary interface for monitoring and controlling Lihuiyu/K40 laser devices. It provides real-time feedback on device communication, displays detailed packet and byte-level information, and offers connection management tools. Users would use this panel when:

- Monitoring device connection status
- Troubleshooting communication issues
- Viewing detailed device status information
- Managing USB connections
- Debugging laser operations

The controller supports both USB and network connections, with automatic detection and status color-coding for quick visual feedback.

## How to Use

### Accessing the Controller

- **Menu**: Device-Control → Controller
- **Console**: `window open LihuiyuController`
- **Auto-opens**: When device communication begins

### Available Controls

#### Connection Management
- **Connection Button**: Force connection/disconnection from device (changes label and color based on state)
- **Connection Status**: Read-only display of current connection type (USB/Network/Mock)

#### Statistics Controls
- **Reset Statistics Button**: Clears packet count and rejected packet counters
- **Packet Count**: Total number of packets sent to device
- **Rejected Packets**: Total number of packets rejected by device

#### Status Monitoring
- **Last Packet**: Information about the most recently sent packet
- **Byte Data Status**: Six read-only fields showing device status bytes (Byte 0-5)
- **Status Log**: Rolling log of device status messages with duplicate counting

#### Logging Controls
- **Show USB Log**: Checkbox to enable/disable detailed USB communication logging
- **Clear Status-Log**: Button to clear the status log display
- **USB Log Panel**: Multi-line display of raw USB communication data (when enabled)

### Key Features

- **Real-time Status Updates**: Automatic updates via signal listeners (`pipe;status`, `pipe;packet_text`, `pipe;state`)
- **Color-coded States**: Button background changes color based on connection state
- **Connection State Management**: Handles various states (connecting, connected, failed, retrying, etc.)
- **Packet Monitoring**: Tracks all device communication with statistics
- **USB Log Toggle**: Expandable interface showing detailed USB traffic when needed
- **Status Logging**: Maintains history of device status messages with compression for duplicates

### Basic Usage

1. **Open Controller**: Access the controller panel from Device-Control menu
2. **Check Connection**: View connection status and button state
3. **Monitor Activity**: Watch packet counts and status updates during laser operations
4. **View Details**: Check byte data for detailed device status information
5. **Troubleshoot**: Enable USB log if experiencing communication issues
6. **Reset Statistics**: Clear counters when starting new operations

### Advanced Usage

#### Connection States

The controller displays different states with color coding:
- **Green**: Connected successfully
- **Yellow**: Connecting, disconnected, or uninitialized
- **Red**: Connection failed or retrying
- **Blue**: Failed but suspended

#### State Transitions

- **Disconnected → Connecting**: Click "Connect" button
- **Connecting → Connected**: Successful USB handshake
- **Connected → Disconnecting**: Click "Disconnect" button
- **Failed → Retrying**: Automatic retry logic
- **Retrying → Connected**: Successful recovery

#### Packet Analysis

- **Packet Count**: Increments for every command sent to device
- **Rejected Packets**: Commands that device couldn't process
- **Last Packet**: Raw command data for debugging
- **Byte Status**: Device firmware status information

#### USB Logging

- **Enable**: Check "Show USB Log" to expand interface
- **Raw Data**: View actual USB packets sent/received
- **Buffer Size**: 500-line rolling buffer for performance
- **Thread-safe**: Updates handled in GUI thread for safety

## Technical Details

The LihuiyuControllerPanel class provides comprehensive device monitoring:

- **Signal Integration**: Listens to `pipe;status`, `pipe;packet_text`, `pipe;usb_status`, `pipe;state`
- **Threading**: Uses thread-safe buffers for USB log updates
- **State Management**: Complex state machine handling connection lifecycle
- **Color Coding**: Dynamic button colors based on connection state
- **Statistics Tracking**: Persistent counters for packets and rejections
- **Log Management**: Rolling status log with duplicate compression

The controller integrates with the device kernel for command execution and status monitoring, providing the primary user interface for device control operations.

## Troubleshooting

### Common Issues

**Connection Button Disabled**
- Cause: Networked device mode active
- Solution: Check device configuration for network vs USB mode

**High Rejected Packet Count**
- Cause: Device busy or communication errors
- Solution: Check USB connection, reduce operation speed, or reset device

**Empty Status Displays**
- Cause: No active device communication
- Solution: Start a laser operation to generate status updates

**USB Log Not Showing**
- Cause: "Show USB Log" checkbox unchecked
- Solution: Enable checkbox to expand the logging panel

### Error Messages

**"Connection Refused"**
- Indicates USB device not found or inaccessible
- Check USB connections and device power
- Try different USB ports or cables

**"libusb version incompatible"**
- 32-bit vs 64-bit library mismatch
- Try alternative MeerK40t installation or system configuration

### Performance Notes

- USB logging can impact performance with high-frequency operations
- Status log limited to 750 entries for memory efficiency
- Packet statistics persist until manually reset
- Real-time updates use efficient signal-based architecture

## Examples

### Basic Monitoring
1. Open controller panel
2. Start simple laser operation (line engraving)
3. Watch packet count increment
4. Check byte status for device state
5. View last packet information

### Troubleshooting Connection
1. Open controller panel
2. Check connection status display
3. Enable USB log for detailed information
4. Click "Connect" if disconnected
5. Monitor status log for error messages
6. Check rejected packet count for communication issues

### Performance Analysis
1. Reset statistics before operation
2. Run complex job with many operations
3. Monitor packet/rejected ratios
4. Check status log for patterns
5. Use USB log for detailed protocol analysis

## Related Topics

- [[Online Help: K40Operation]]
- [[Online Help: K40Tcp]]
- [[Online Help: Configuration]]
- [[Online Help: Devices]]

## Screenshots

### K40 Controller Main Interface
The main controller panel displaying connection management and monitoring:
- **Connection Button**: Large colored button showing current USB connection state (Green=connected, Yellow=connecting, Red=failed)
- **Status Display**: Text field showing detailed connection status and device information
- **Device Controls**: Emergency stop and other device control buttons
- **Connection Status**: Real-time indicators for USB communication state

### USB Communication Logging
The controller with USB logging enabled showing device communication:
- **USB Log Panel**: Scrollable text area displaying real-time USB traffic between MeerK40t and the K40 device
- **Communication Details**: Command transmissions, device responses, and error messages
- **Log Buffer**: Maintains history of recent USB communication for troubleshooting
- **Thread-safe Updates**: Background logging without interfering with UI responsiveness

### Connection Troubleshooting View
The panel during connection attempts showing diagnostic information:
- **Connection Process**: Step-by-step connection establishment with status updates
- **Error Messages**: Clear indication of connection failures and possible causes
- **Device Detection**: USB device identification and compatibility checking
- **Recovery Options**: Reset and reconnection controls for troubleshooting

### Active Operation Monitoring
The controller during laser operations showing real-time device interaction:
- **Command Transmission**: Live display of commands being sent to the K40 device
- **Device Responses**: Immediate feedback from the laser controller
- **Status Updates**: Current operation state and progress indicators
- **Performance Monitoring**: Real-time tracking of device communication reliability

### Emergency Controls
The panel highlighting safety and emergency control features:
- **Emergency Stop Button**: Prominent stop control for immediate operation termination
- **Safety Indicators**: Visual cues for device state and potential issues
- **Manual Controls**: Direct device command interface for advanced users
- **Status Validation**: Confirmation of command execution and device response

---

*This help page provides comprehensive documentation for the K40 Controller functionality.*
