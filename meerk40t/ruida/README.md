# Ruida

Ruida classes deal with interactions between MeerK40t and Ruida-devices. Currently, this is limited to reading .rd files
and accepting mock Ruida connections from software that connects through UDP connections. Including RDWorks, Lightburn,
and a Ruida android application. As well as anything else that produces Ruida code. The parser is able to read every
Ruida command known.

Using `ruidacontrol` for example will make a socket connection to make the localhost appear as a ruida laser cutter. Any
commands sent to it will be spooled and the resulting laser code will be sent to the locally configured active laser
device.

## Overview

The Ruida module provides comprehensive compatibility with Ruida DSP controllers and RDWorks software ecosystem. Unlike direct hardware drivers, this module primarily functions as:

- **File Format Handler**: Complete parser for .rd (Ruida) files
- **Protocol Emulator**: Simulates Ruida controllers for third-party software compatibility
- **Bridge Interface**: Translates between Ruida protocol and MeerK40t's internal cutcode
- **Network Server**: Provides UDP/TCP endpoints for external software connections

## Architecture

The Ruida module follows a multi-layered architecture designed for protocol compatibility and file processing:

### Core Components

#### RDJob (`rdjob.py`)
- **File Processing**: Parses and generates Ruida .rd file format
- **Command Encoding**: Implements complete Ruida command set (2000+ lines)
- **Magic Key Support**: Handles different Ruida controller variants (0x88, 0x11, 0x38)
- **Data Encoding**: Supports 14-bit, 32-bit, and U35 coordinate encoding
- **Swizzle LUT**: Implements Ruida's coordinate transformation algorithms

#### RuidaEmulator (`emulator.py`)
- **Protocol Simulation**: Emulates Ruida DSP controller behavior
- **Network Interface**: Handles UDP connections from RDWorks/Lightburn
- **Real-time Processing**: Processes jog commands, status requests, and file transfers
- **Coordinate Mapping**: Translates between Ruida and MeerK40t coordinate systems

#### RuidaControl (`control.py`)
- **Server Management**: Controls UDP server instances for different ports
- **Traffic Routing**: Implements man-in-the-middle capabilities
- **Bridge Protocol**: Supports LB2RD (Lightburn to Ruida) bridging
- **Device Integration**: Routes commands to active MeerK40t laser devices

### Device Layer (`device.py`)
- **Service Integration**: Registers as MeerK40t device service
- **Configuration Management**: Handles device-specific settings
- **File Loading**: Supports .rd file import with RDLoader
- **Connection Multiplexing**: Supports multiple connection types (UDP, TCP, Serial, Mock)

### Driver Layer (`driver.py`)
- **Cutcode Translation**: Converts Ruida commands to MeerK40t cutcode
- **Plot Planning**: Integrates with MeerK40t's plot planning system
- **Real-time Control**: Handles jog movements and status updates
- **Power/Speed Control**: Manages laser parameters during operation

## Technical Features

### File Format Support

#### RD File Processing
- **Complete Parser**: Reads all known Ruida commands
- **Magic Detection**: Automatically detects controller variant from file histogram
- **Binary Decoding**: Handles Ruida's proprietary binary encoding
- **Command Viewer**: Provides human-readable command interpretation

```python
# Example RD file structure
# Magic byte detection
magic = determine_magic_via_histogram(data)  # 0x88, 0x11, or 0x38

# Command parsing
job = RDJob()
job.write_blob(data)
commands = parse_commands(data, magic)
```

#### Supported Commands
The parser handles the complete Ruida command set including:
- **Movement Commands**: Absolute/relative positioning, axis control
- **Laser Control**: Power settings, pulse control, gate operations
- **System Commands**: Status queries, configuration, memory operations
- **Jog Commands**: Real-time movement control
- **File Operations**: Program loading, memory management

### Network Protocol Emulation

#### UDP Server Ports
- **50200**: Main data channel for RDWorks/Lightburn communication
- **50207**: Jog control channel for real-time movement
- **40200**: Laser control channel (when bridging)
- **40207**: Laser jog channel (when bridging)

#### Connection Types
- **UDPConnection**: Primary network interface for external software
- **TCPConnection**: Alternative TCP-based communication
- **SerialConnection**: Direct serial connection to Ruida controllers
- **MockConnection**: Development and testing interface

### Bridge Protocols

#### Man-in-the-Middle Mode
```bash
ruidacontrol --man_in_the_middle=192.168.1.100:50200
```
Routes traffic between external software and real Ruida controllers.

#### LB2RD Bridge Protocol
```bash
ruidacontrol --bridge
```
Implements Lightburn-to-Ruida protocol translation for enhanced compatibility.

## Usage

### Basic Operation

#### Starting Ruida Control Server
```bash
# Start Ruida emulation server
ruidacontrol

# Start with verbose logging
ruidacontrol --verbose

# Start without jog ports
ruidacontrol --jogless

# Stop the server
ruidacontrol stop
```

#### Loading RD Files
```python
# Files are automatically loaded through RDLoader
# Supports .rd extension with MIME type application/x-rd
loader = RDLoader()
loader.load(kernel, service, "design.rd")
```

### Advanced Configuration

#### Device Registration
```python
# Register Ruida device (marked as incomplete)
kernel.register("provider/device/ruida", RuidaDevice)
kernel.register("dev_info/ruida-beta", {
    "provider": "provider/device/ruida",
    "friendly_name": "K50/K60-CO2-Laser (Ruida-Controller) (INCOMPLETE)",
    "priority": -1,  # Low priority due to incomplete status
})
```

#### Server Configuration Options
- **verbose**: Enable detailed logging of server operations
- **jogless**: Disable jog control ports for reduced resource usage
- **man_in_the_middle**: Redirect traffic to real laser hardware
- **bridge**: Enable LB2RD bridge protocol

## Protocol Details

### Ruida Command Format
Ruida uses a binary protocol with variable-length commands:

```
Command Structure:
[Command Byte] [Parameter Data...]

Example Commands:
\x88 [x_coord] [y_coord]    # Absolute XY move
\x89 [dx] [dy]             # Relative XY move
\x80\x00 [x_coord]         # X-axis move
```

### Coordinate Systems
- **Ruida Coordinates**: Device-specific units (typically 1/1000 mm)
- **MeerK40t Units**: Internal micron-based coordinate system
- **Transformation**: Automatic conversion via units_to_device_matrix

### Magic Keys
Different Ruida controller variants use different magic keys:
- **0x88**: Standard Ruida controllers (most common)
- **0x11**: 634XG series controllers
- **0x38**: Alternative encoding variant

## Development

### Key Classes
- `RDJob`: Core file processing and command encoding
- `RuidaEmulator`: Network protocol emulation
- `RuidaControl`: Server management and traffic routing
- `RuidaDevice`: MeerK40t device service integration
- `RuidaDriver`: Cutcode translation and execution

### Testing
```bash
# Run Ruida-specific tests
python -m unittest test_ruida.py

# Test file loading
python -c "from meerk40t.ruida.loader import RDLoader; print('RD loader available')"
```

### Dependencies
- MeerK40t core libraries
- Network socket libraries (built-in)
- File I/O libraries (built-in)

## Compatibility

### Supported Software
- **RDWorks**: Full compatibility via UDP emulation
- **Lightburn**: Supported through bridge protocols
- **Ruida Android App**: Network connectivity
- **Third-party Ruida software**: Generic protocol support

### Hardware Compatibility
- **Ruida DSP Controllers**: K-Series (K50, K60) and others
- **Network-enabled lasers**: Any device supporting Ruida protocol
- **USB/Serial Ruida devices**: Through connection abstraction layer

## Limitations

### Current Status
- **INCOMPLETE**: Marked as beta/incomplete in device registration
- **Emulation Only**: Does not provide direct hardware control
- **File Format Focus**: Primarily designed for file compatibility
- **Bridge Functionality**: Main use case is software compatibility

### Known Issues
- Direct hardware control not implemented
- Some advanced Ruida features may not be fully supported
- Real-time performance depends on network latency

## Troubleshooting

### Connection Issues
- **Port Conflicts**: Ensure ports 50200/50207 are available
- **Firewall Settings**: Allow UDP traffic on Ruida ports
- **Network Configuration**: Verify IP address binding

### File Loading Problems
- **Magic Key Detection**: Check file histogram for correct variant
- **Encoding Errors**: Verify file integrity and Ruida version
- **Command Parsing**: Use command viewer for debugging

### Performance Optimization
- **Jog Port Control**: Use --jogless for reduced resource usage
- **Verbose Logging**: Enable --verbose for detailed diagnostics
- **Bridge Mode**: Consider bridge protocols for specific software

## Future Development

### Planned Features
- Direct hardware control implementation
- Enhanced real-time performance
- Additional Ruida controller variant support
- Extended bridge protocol capabilities

### Extension Points
- Connection abstraction allows easy addition of new transport layers
- Command parser is extensible for new Ruida variants
- Emulator architecture supports additional protocol features
