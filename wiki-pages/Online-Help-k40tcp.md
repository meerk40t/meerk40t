# Online Help: K40Tcp

## Overview

The **K40Tcp** feature provides network control capabilities for K40 laser systems, allowing MeerK40t to communicate with and control a K40 laser connected to another computer on the network via TCP/IP connection.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t/lihuiyu/gui/tcpcontroller.py`

## Category

**Lihuiyu/K40**

## Description

The TCP Controller enables remote operation of K40 lasers by establishing a network connection to a computer running MeerK40t with a locally connected K40 device. This is particularly useful for:

- **Remote Laser Operation**: Control a laser from a different computer on the network
- **Centralized Control**: Manage multiple lasers from a single workstation
- **Distributed Workflows**: Separate design work from laser operation
- **Shared Resources**: Allow multiple users to access laser equipment over a network

The system uses TCP sockets to transmit laser commands and receive status information, with built-in buffer management to ensure reliable data transmission.

## How to Use

### Accessing the TCP Controller

1. **Open TCP Controller**: Navigate to `Device-Control → TCP Controller` in the menu
2. **Configure Connection**: Enter the IP address/hostname and port of the target computer
3. **Connect**: Click the Connect button to establish the network connection
4. **Monitor Status**: Watch the connection status and buffer indicators

### Available Controls

#### Connection Management
- **Connection Button**: Connect/disconnect from remote laser
  - Green background = Connected
  - Yellow background = Disconnected
  - Changes label between "Connect" and "Disconnect"

#### Network Configuration
- **Address Field**: IP address or hostname of the computer with the laser
- **Port Field**: TCP port number (default varies by setup)

#### Status Monitoring
- **Status Display**: Shows current connection state
- **Buffer Gauge**: Visual indicator of data in transmission buffer
- **Buffer Size**: Current bytes waiting to be sent
- **Max Buffer Size**: Peak buffer usage during session

### Basic Usage Workflow

#### Setting Up Remote Control

1. **On Laser Computer**: Ensure MeerK40t is running with K40 device configured
2. **On Control Computer**: Open TCP Controller window
3. **Enter Network Details**:
   - Address: IP/hostname of laser computer
   - Port: TCP port (usually 23 or custom)
4. **Click Connect**: Establish network connection
5. **Verify Connection**: Status should show "connected"
6. **Send Jobs**: Laser operations will be transmitted over network

#### Monitoring Transmission

- **Buffer Size**: Shows data queued for transmission
- **Buffer Gauge**: Visual progress of buffer emptying
- **Status**: Connection state and any error conditions

### Advanced Usage

#### Buffer Management
The TCP system includes intelligent buffer management:
- **Automatic Retry**: Failed transmissions are automatically retried
- **Flow Control**: Prevents buffer overflow during high-speed operations
- **Status Monitoring**: Real-time buffer status for performance tuning

#### Network Configuration
- **Port Selection**: Choose appropriate TCP port (avoid conflicts)
- **Address Resolution**: Supports both IP addresses and hostnames
- **Connection Persistence**: Maintains connection across job submissions

## Technical Details

### TCP Communication Protocol
The system establishes a TCP socket connection and transmits laser commands as byte streams. The protocol includes:

- **Command Transmission**: Laser operations encoded as binary data
- **Status Feedback**: Connection state and buffer information
- **Error Handling**: Automatic reconnection on network failures
- **Flow Control**: Buffer management prevents data loss

### Buffer System
- **Write Buffer**: Queues outgoing laser commands
- **Size Monitoring**: Tracks buffer utilization in real-time
- **Peak Tracking**: Records maximum buffer usage
- **Threading**: Dedicated send thread for reliable transmission

### Signal Integration
The TCP controller integrates with MeerK40t's signal system:
- `tcp;status`: Connection state changes
- `tcp;buffer`: Buffer size updates
- `tcp;write`: Data transmission events
- `network_update`: Network availability changes

### Threading Architecture
- **Main Thread**: UI updates and user interaction
- **Send Thread**: Dedicated background thread for data transmission
- **Signal Thread**: Asynchronous status updates

## Safety Considerations

- **Network Security**: Ensure network connections are secure and trusted
- **Connection Stability**: Monitor connection status during long jobs
- **Buffer Monitoring**: Watch for buffer overflow indicating network issues
- **Remote Safety**: Ensure proper safety protocols when operating remotely

## Troubleshooting

### Connection Issues

#### "Connection Error"
**Problem**: Cannot establish TCP connection
**Solutions**:
- Verify IP address/hostname is correct
- Check port number matches server configuration
- Ensure target computer is running and accessible
- Check firewall settings allow TCP connections

#### "Timeout Connect"
**Problem**: Connection attempt times out
**Solutions**:
- Verify target computer is online
- Check network connectivity
- Try different port numbers
- Check for network congestion

#### "Address Resolve Error"
**Problem**: Cannot resolve hostname to IP address
**Solutions**:
- Use IP address instead of hostname
- Check DNS configuration
- Verify hostname spelling

### Buffer Issues

#### Buffer Not Emptying
**Problem**: Data remains in buffer
**Solutions**:
- Check network connection stability
- Monitor target computer performance
- Reduce job complexity if needed

#### High Buffer Usage
**Problem**: Buffer frequently fills up
**Solutions**:
- Check network bandwidth
- Reduce laser speed/complexity
- Optimize job for network transmission

### Performance Issues

#### Slow Response
**Problem**: Delayed command execution
**Solutions**:
- Check network latency
- Verify target computer performance
- Reduce buffer size if needed

## Related Topics

- [[Online Help: K40Controller]] - Direct USB connection to K40 devices
- [[Online Help: K40Operation]] - Advanced K40 operation settings
- [[Online Help: Devices]] - Device configuration and management
- [[Online Help: Network]] - Network-related features and configuration

## Screenshots

*Screenshots would show:*
- *TCP Controller window with connection settings*
- *Connected state showing green button and status*
- *Buffer monitoring during active laser operation*
- *Network configuration examples*

---

*This help page is automatically generated. Please update with specific information about the k40tcp feature.*
