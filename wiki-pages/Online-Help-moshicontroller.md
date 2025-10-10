# Online Help: Moshi Controller

## Overview

This help page covers the **Moshi Controller** functionality in MeerK40t.

The Moshi Controller window provides direct control and monitoring of Moshi laser devices. This device-specific interface allows you to manage USB connections, monitor device status, view communication logs, and send direct commands to Moshi laser controllers.

The controller panel serves as a diagnostic and control interface for troubleshooting connection issues and monitoring device communication in real-time.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\moshi\gui\moshicontrollergui.py` - Main controller window implementation
- Device menu: Device-Control → Controller (when Moshi device is active)

## Category

**Moshi**

## Description

The Moshi Controller window serves as the primary interface for managing and monitoring Moshi laser device connections. It provides essential functionality for:

- **USB Connection Management**: Connect/disconnect from Moshi devices with visual status indicators
- **Device Identification**: Configure USB matching criteria for multi-device setups
- **Real-time Monitoring**: View device status bytes and packet information
- **Communication Logging**: Monitor USB traffic and device responses
- **Direct Device Control**: Send commands like stop, unlock rail, and reset
- **Diagnostic Tools**: Access buffer views and connection troubleshooting

This controller interface is essential for diagnosing connection problems, verifying device communication, and performing low-level device operations that aren't available in the main MeerK40t interface.

## How to Use

### Accessing Moshi Controller

The Moshi Controller window is only available when a Moshi device is active:

1. Ensure your Moshi device is selected and active
2. Go to **Device-Control → Controller** in the menu
3. The controller window will open with connection and monitoring controls

### USB Connection Management

#### Connection Button
- **Visual Status**: Button color and icon indicate connection state
  - **Green**: Connected successfully
  - **Yellow**: Connecting/disconnecting or disconnected
  - **Red/Orange**: Connection failed
- **Click Behavior**:
  - When disconnected: Attempts to connect to the device
  - When connected: Disconnects from the device

#### Connection Status Display
Shows the current connection status text, such as:
- "STATE_USB_CONNECTED"
- "STATE_USB_DISCONNECTED"
- "STATE_CONNECTION_FAILED"

### Device Identification Settings

#### USB Matching Criteria
Configure how MeerK40t identifies your specific Moshi device when multiple USB devices are present:

- **Device Index**: USB device index (-1 = any, 0+ = specific device)
- **Device Address**: USB device address (-1 = any, 0+ = specific address)
- **Device Bus**: USB bus number (-1 = any, 0+ = specific bus)
- **Chip Version**: Device firmware version (-1 = any, 0+ = specific version)

#### Mock USB Mode
- **Debug Feature**: Simulate USB connection without physical device
- **Purpose**: Test software functionality when device is unavailable
- **Warning**: Only for debugging - does not perform actual laser operations

### Device Status Monitoring

#### Byte Data Status
Displays real-time status information from the Moshi controller:

- **Byte 0-5**: Raw status bytes from device communication
- **Byte 1 Description**: Text interpretation of Byte 1 status
- **Packet Info**: Current packet being processed by the device

#### Status Interpretation
- **Byte 0**: General status flags
- **Byte 1**: Operation mode and state (with text description)
- **Byte 2-5**: Position, buffer, and error status information

### USB Communication Logging

#### Show USB Log Checkbox
- **Enable/Disable**: Toggle visibility of USB communication log
- **Window Resizing**: Automatically adjusts window width when enabled/disabled

#### USB Log Display
- **Real-time Updates**: Shows all USB traffic to/from the device
- **Buffer Size**: Maintains 500 lines of recent communication
- **Thread-safe**: Updates safely from background communication threads

### Menu Commands

#### Tools Menu
- **Reset USB**: Reset the USB connection state
- **Release USB**: Release USB resources and cleanup

#### Commands Menu
- **Stop**: Send emergency stop command to device
- **Free Motor**: Unlock the laser rail (safety feature)

#### Views Menu
- **BufferView**: Open buffer inspection window

### Diagnostic Workflow

#### Connection Troubleshooting
1. Check USB Log for connection attempts and errors
2. Verify device identification settings match your hardware
3. Try different USB ports or cables
4. Use Reset USB if connection is stuck
5. Check device power and status lights

#### Communication Monitoring
1. Enable USB Log to see all device communication
2. Monitor Byte Data Status for device state changes
3. Use BufferView to inspect command queues
4. Check packet information for data flow issues

#### Device Control
1. Use Stop command for emergency situations
2. Use Free Motor to unlock stuck laser heads
3. Monitor status changes during operations

## Technical Details

### Signal Integration
The controller integrates with several device signals:
- **`pipe;status`**: Updates device status bytes and descriptions
- **`pipe;usb_status`**: Monitors USB connection status changes
- **`pipe;state`**: Tracks connection state transitions
- **`moshi_controller_update`**: Triggers USB log updates

### USB Communication
- **Threading**: Uses background threads for USB communication
- **Buffering**: Maintains circular buffer for log display
- **Synchronization**: Thread-safe updates to prevent UI freezing

### Device States
Monitors various connection states:
- `STATE_UNINITIALIZED`: Device not initialized
- `STATE_USB_DISCONNECTED`: USB cable disconnected
- `STATE_CONNECTING`: Attempting to establish connection
- `STATE_USB_CONNECTED`: Successfully connected
- `STATE_CONNECTION_FAILED`: Connection attempt failed

### Status Byte Interpretation
The controller interprets raw device status bytes into human-readable information, providing insights into device operation modes, error conditions, and current activities.

### Buffer Management
Maintains separate buffers for:
- USB communication logs
- Status update queues
- Command execution tracking

## Related Topics

*Link to related help topics:*

- [[Online Help: Moshiconfig]]
- [[Online Help: Devices]]
- [[Online Help: K40Controller]]
- [[Online Help: BufferView]]

## Screenshots

*Add screenshots showing the Moshi controller window with connection status, USB log, and device monitoring.*
