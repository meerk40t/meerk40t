# Online Help: Newlycontroller

## Overview

This help page covers the **Newlycontroller** functionality in MeerK40t.

The Newly Controller panel provides real-time USB connection management and communication monitoring for Newly laser devices. It offers direct control over device connectivity and displays live USB communication logs.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\newly\gui\newlycontroller.py`

## Category

**Newly**

## Description

The Newly Controller is essential for managing the USB connection between MeerK40t and your Newly laser device. It provides a visual interface to connect/disconnect from the device, monitor connection status, and view real-time communication logs. This is particularly useful for troubleshooting connection issues, monitoring device communication, and ensuring reliable laser operation.

## How to Use

### Available Controls

- **Connection Button**: Main control for connecting/disconnecting from the device

### Key Features

- Integrates with: `newly_controller_update`
- Integrates with: `pipe;usb_status`
- Real-time USB communication logging
- Visual connection status indicators
- Connection state management

### Basic Usage

1. **Open Controller Panel**: Access from Device-Control → Newly-Controller menu
2. **Check Connection Status**: Observe button color and label for current state
3. **Connect Device**: Click the Connection button when disconnected (yellow)
4. **Monitor Communication**: Watch the USB log for device interactions
5. **Disconnect if Needed**: Click button again when connected (green) to disconnect

## Connection States

### Visual Indicators

**Disconnected State**:
- Button background: Yellow (#dfdf00)
- Button icon: Disconnected symbol
- Button label: Shows current USB status

**Connected State**:
- Button background: Green (#00ff00)
- Button icon: Connected symbol
- Button label: Shows active connection status

**Connecting State**:
- Button shows intermediate status during connection attempts

## USB Communication Log

### Log Display

The large text area at the bottom displays real-time USB communication logs including:
- Connection attempts and status messages
- Device identification information
- Command transmissions
- Error messages and warnings
- Status updates from the laser device

### Log Features

- **Auto-scrolling**: New messages automatically appear at the bottom
- **Thread-safe**: Uses locking mechanisms for concurrent access
- **Monospaced font**: Easy-to-read technical formatting
- **Persistent display**: Shows communication history during the session

## Technical Details

The NewlyControllerPanel class extends wx.ScrolledWindow and provides a comprehensive USB interface management system.

**Key Technical Components**:
- Thread-safe buffer management for log updates
- Signal listeners for USB status changes (`pipe;usb_status`)
- Channel watching for device-specific communication
- Connection state management with visual feedback
- Integration with device driver connection methods

**Communication Flow**:
1. User clicks Connection button
2. Panel checks current connection state via `service.driver.connected`
3. Issues `usb_connect` or `usb_disconnect` commands to kernel
4. Monitors status changes through signal listeners
5. Updates UI and logs communication events

**USB Channel Monitoring**:
- Watches device-specific channel: `{device_safe_label}/usb`
- Buffers incoming messages for thread-safe GUI updates
- Signals GUI updates through `newly_controller_update`

## Usage Guidelines

### Connection Management

**Initial Setup**:
1. Ensure your Newly device is powered on and USB cable is connected
2. Open the Newly Controller panel
3. Click the Connection button to establish communication
4. Verify connection by checking button color change and log messages

**Troubleshooting Connections**:
1. Check USB cable connections
2. Verify device power status
3. Look for error messages in the communication log
4. Try disconnecting and reconnecting if issues persist

### Monitoring Operations

**During Laser Jobs**:
- Keep the controller panel open to monitor communication
- Watch for any error messages or connection warnings
- Use the log to verify command transmission to the device

**Debugging Issues**:
- Communication logs help identify timing issues
- Status messages reveal device state changes
- Error logs assist in diagnosing hardware problems

## Troubleshooting

### Connection Problems

**Device Not Found**:
- Verify USB cable is securely connected
- Check that the device is powered on
- Try different USB ports
- Check device manager for driver issues

**Connection Drops**:
- Monitor the communication log for error patterns
- Check USB cable quality and length
- Verify power supply stability
- Look for electromagnetic interference sources

**Communication Errors**:
- Review log messages for specific error codes
- Check device firmware version compatibility
- Verify MeerK40t version compatibility
- Test with different USB cables

### Performance Issues

**Slow Response**:
- Check USB port speed (should be USB 2.0 or higher)
- Monitor system resource usage
- Close unnecessary applications
- Update USB drivers

**Log Overload**:
- High-frequency logging may impact performance
- Consider filtering log levels if available
- Monitor system memory usage during extended sessions

## Advanced Features

### Real-time Monitoring

The controller provides live monitoring capabilities:
- **Status Updates**: Immediate visual feedback on connection state
- **Communication Logs**: Detailed record of all USB transactions
- **Error Detection**: Automatic highlighting of communication issues
- **State Persistence**: Maintains connection status across panel hide/show

### Integration Features

**Signal Integration**:
- Responds to `pipe;usb_status` signals for status updates
- Emits `newly_controller_update` for log display updates
- Integrates with device driver connection management

**Channel Watching**:
- Monitors device-specific communication channels
- Thread-safe message buffering and display
- Automatic cleanup on panel hide/show

## Related Topics

*Link to related help topics:*

- [[Online Help: Newlyconfig]]
- [[Online Help: K40Controller]]
- [[Online Help: K40Operation]]
- [[Online Help: Devices]]

## Screenshots

### Newly Controller Main Interface
The main controller panel displays connection management and monitoring:
- **Connection Button**: Large colored button showing current state (Yellow=disconnected, Green=connected)
- **Status Label**: Text below button indicating current USB connection status
- **Device Information**: Shows connected device details and identification
- **Connection Controls**: Primary interface for establishing and breaking USB connections

### Disconnected State View
The disconnected state shows the initial connection interface:
- **Yellow Button Background**: Indicates device is not connected
- **Disconnected Icon**: Visual indicator of connection state
- **Status Message**: Shows "Disconnected" or current USB status information
- **Ready to Connect**: Button is clickable to initiate connection process

### Connected State View
The connected state displays active communication:
- **Green Button Background**: Confirms successful device connection
- **Connected Icon**: Visual confirmation of active USB link
- **Status Message**: Shows "Connected" with device identification details
- **Active Monitoring**: Button ready for disconnection if needed

### USB Communication Log Display
The communication log panel shows real-time device interaction:
- **Log Text Area**: Large scrollable area displaying USB communication history
- **Real-time Updates**: New messages appear automatically as they occur
- **Technical Formatting**: Monospaced font for easy reading of technical data
- **Message Types**: Shows connection attempts, commands, responses, and error messages

### Connection Process Monitoring
During connection establishment:
- **Connecting Status**: Button shows intermediate state during connection attempts
- **Progress Messages**: Log displays step-by-step connection process
- **Device Detection**: Shows USB device identification and validation
- **Success/Failure**: Clear indication of connection outcome with detailed messages

### Active Operation Monitoring
During laser operations:
- **Command Transmission**: Shows commands being sent to the device
- **Device Responses**: Displays device acknowledgments and status updates
- **Error Detection**: Highlights any communication issues or device errors
- **Performance Monitoring**: Tracks command timing and response patterns

---

*This help page provides comprehensive documentation for Newly device USB controller management in MeerK40t.*
