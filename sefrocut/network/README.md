# SefroCut Network Module

## Overview

The Network Module provides comprehensive remote access capabilities for SefroCut, enabling external systems to interact with the laser cutting software through various network protocols. This module implements multiple server types for remote control, monitoring, and data exchange.

## Architecture

```
sefrocut/network/
├── kernelserver.py      # Main plugin registration hub
├── tcp_server.py       # TCP server for telnet console access
├── udp_server.py       # UDP server for packet-based communication
├── web_server.py       # HTTP web server with HTML interface
├── console_server.py   # Console commands for server management
├── __init__.py          # Module initialization (empty)
└── README.md            # This documentation
```

### Core Components

- **KernelServer (kernelserver.py)**: Central plugin that registers all network services
- **TCPServer (tcp_server.py)**: Multi-threaded TCP server for persistent connections
- **UDPServer (udp_server.py)**: UDP server for stateless packet communication
- **WebServer (web_server.py)**: HTTP server with web interface and REST-like capabilities
- **Console Commands (console_server.py)**: Command-line interface for server management

## Key Features

### Remote Access Protocols
- **Telnet Console**: Full command-line access via TCP port 23
- **UDP Communication**: Packet-based data exchange with reply capabilities
- **Web Interface**: HTML-based control panel with spooler monitoring
- **Multi-threaded Handling**: Concurrent connection support

### Server Management
- **Dynamic Server Creation**: Servers instantiated on-demand via console commands
- **Graceful Shutdown**: Clean termination with connection cleanup
- **Channel Integration**: Full integration with SefroCut's channel system
- **Event Logging**: Comprehensive connection and data flow monitoring

### Web Interface Features
- **Live Spooler Status**: Real-time job queue monitoring with progress tracking
- **Console Commands**: Web form for executing SefroCut commands
- **Device Information**: Active device status and configuration display
- **Responsive Design**: HTML interface with table-based layouts

## Dependencies

### Required
- **Python Standard Library**: `socket`, `urllib.parse`, `math`
- **SefroCut Kernel**: Channel system and module framework

### Optional
- **Threading Support**: Built-in Python threading for concurrent connections

## Core Classes and Functions

### TCPServer
```python
# TCP Server for persistent connections
server = TCPServer(context, "console-server", port=23)

# Features:
# - Multi-threaded connection handling
# - Individual handler threads per connection
# - Channel-based data routing
# - Automatic connection cleanup
```

### UDPServer
```python
# UDP Server for packet-based communication
server = UDPServer(context, "udp-server", port=23)

# Features:
# - Stateless packet reception
# - Reply-to-last-sender capability
# - Channel-based message routing
# - Configurable listen ports
```

### WebServer
```python
# HTTP Server with web interface
server = WebServer(context, "web-server", port=2080)

# Features:
# - HTML interface generation
# - Spooler status monitoring
# - Command execution via web forms
# - JSON response support
```

## Console Commands

The module provides console commands for server management:

### Telnet Console Server
```bash
# Start telnet console server on port 23
consoleserver

# Start on custom port
consoleserver -p 2323

# Start silently (no channel watching)
consoleserver -s

# Suppress input prompt
consoleserver -u

# Shutdown server
consoleserver -q
```

### Web Server
```bash
# Start web server on port 2080
webserver

# Start on custom port
webserver -p 8080

# Start silently
webserver -s

# Shutdown server
webserver -q
```

## Usage Examples

### Remote Console Access
```bash
# Start telnet server
consoleserver

# Connect from remote system
telnet localhost 23

# Execute commands remotely
>> help
>> device list
>> spooler list
```

### Web Interface Access
```bash
# Start web server
webserver

# Open browser to http://localhost:2080
# View spooler status, execute commands via web form
```

### UDP Communication
```python
# Python client example
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(b"hello", ("localhost", 23))

# Server receives data on udp-server/recv channel
# Replies can be sent via udp-server/send channel
```

## Channel Integration

### TCP Server Channels
- **`server-tcp-{port}`**: Connection events and status messages
- **`data-tcp-{port}`**: Raw data transmission logging
- **`{name}/recv`**: Incoming data from connections
- **`{name}/send`**: Outgoing data to connections

### UDP Server Channels
- **`server-udp-{port}`**: Server status and events
- **`{name}/recv`**: Incoming UDP packets
- **`{name}/send`**: Outgoing UDP packets (replies)

### Web Server Channels
- **`server-web-{port}`**: HTTP connection events
- **`data-web-{port}`**: HTTP request/response logging

## Web Interface Features

### Spooler Monitoring
The web interface provides detailed spooler information:
- **Job Queue**: Current jobs with status, type, and progress
- **Device Status**: Active device information
- **Progress Tracking**: Steps completed, passes, priority levels
- **Time Estimates**: Runtime and estimated completion times

### Command Execution
- **GET Requests**: URL-based command execution (`?cmd=command`)
- **POST Forms**: Web form for multi-line command input
- **Thread Safety**: Commands executed in main thread via handover mechanism

### HTML Generation
```html
<!-- Example spooler table -->
<table>
  <tr>
    <td>#</td><td>Device</td><td>Name</td><td>Items</td>
    <td>Status</td><td>Type</td><td>Steps</td><td>Passes</td>
    <td>Priority</td><td>Runtime</td><td>Estimate</td>
  </tr>
  <!-- Job rows dynamically generated -->
</table>
```

## Threading Model

### Connection Handling
- **Delegator Thread**: Main thread accepting new connections
- **Handler Threads**: Individual threads per active connection
- **Daemon Threads**: Background execution with automatic cleanup
- **Thread Naming**: Descriptive names for debugging (`tcp-23`, `handler-23-1`)

### Thread Safety
- **Channel Watches**: Thread-safe communication via SefroCut channels
- **Handover Mechanism**: GUI thread handover for command execution
- **State Management**: Atomic state changes with proper synchronization

## Error Handling

### Connection Management
- **Graceful Degradation**: Continued operation despite individual connection failures
- **Timeout Handling**: Configurable timeouts for connection acceptance
- **Socket Cleanup**: Automatic resource cleanup on disconnection
- **Error Logging**: Comprehensive error reporting through channels

### Network Errors
- **Port Conflicts**: Clear error messages for unavailable ports
- **Connection Failures**: Robust handling of network interruptions
- **Encoding Issues**: UTF-8 decoding with fallback error handling
- **Buffer Management**: Proper handling of partial data reception

## Security Considerations

### Network Exposure
- **Localhost Binding**: Servers bind to all interfaces by default
- **Firewall Awareness**: Users should configure network security
- **Command Validation**: All commands executed with full privileges
- **Access Logging**: Comprehensive connection and command logging

### Best Practices
- **Port Selection**: Use non-standard ports to avoid conflicts
- **Network Isolation**: Consider running on isolated networks
- **Command Auditing**: Monitor executed commands for security
- **Timeout Configuration**: Set appropriate connection timeouts

## Performance Characteristics

### Scalability
- **Concurrent Connections**: Multiple simultaneous connections supported
- **Thread Overhead**: Minimal overhead for connection handling
- **Memory Usage**: Efficient memory usage with connection pooling
- **CPU Utilization**: Low CPU overhead for typical usage

### Limitations
- **Single UDP Reply**: UDP server replies only to last sender
- **No Authentication**: No built-in user authentication mechanisms
- **Plain Text Protocols**: Telnet and HTTP without encryption
- **Resource Limits**: Dependent on system thread and socket limits

## Integration with SefroCut

### Plugin Lifecycle
```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        # Register all network server plugins
        return [tcp_plugin, udp_plugin, web_plugin, console_plugin]
```

### Service Registration
```python
kernel.register("module/TCPServer", TCPServer)
kernel.register("module/UDPServer", UDPServer)
kernel.register("module/WebServer", WebServer)
```

### Channel Routing
- **Kernel Channels**: Integration with central channel system
- **Context Isolation**: Each server operates in its own context
- **Event Propagation**: Events routed through appropriate channels
- **Data Flow**: Bidirectional data flow between network and kernel

## Testing and Validation

### Connection Testing
```bash
# Test TCP connection
echo "help" | nc localhost 23

# Test UDP communication
echo "test" | nc -u localhost 23

# Test web interface
curl http://localhost:2080
```

### Server Management Testing
```bash
# Start and verify servers
consoleserver
webserver

# Check active modules
module list

# Verify channels
channel list
```

## Future Enhancements

### Potential Improvements
- **SSL/TLS Support**: Encrypted connections for security
- **Authentication**: User authentication and authorization
- **REST API**: Proper RESTful API endpoints
- **WebSocket Support**: Real-time bidirectional communication
- **Rate Limiting**: Protection against abuse
- **Configuration UI**: Graphical server configuration
- **Logging Integration**: Structured logging with rotation
- **Metrics Collection**: Performance and usage metrics

### Protocol Extensions
- **MQTT Support**: IoT protocol integration
- **WebRTC**: Browser-based real-time communication
- **GraphQL API**: Flexible query interface
- **Binary Protocols**: Efficient binary data transfer

## Contributing

When contributing to the network module:
1. Maintain thread safety in all network operations
2. Follow SefroCut's channel-based communication patterns
3. Implement proper error handling and logging
4. Test with multiple concurrent connections
5. Consider security implications of network exposure
6. Document new server types and protocols
7. Provide console commands for server management

## Related Modules

- **kernel**: Core channel system and module framework
- **core**: Main application logic and device management
- **gui**: Graphical interface with handover mechanisms
- **device**: Hardware device communication and control