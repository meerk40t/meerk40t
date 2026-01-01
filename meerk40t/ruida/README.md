# Ruida

Ruida classes deal with interactions between MeerK40t and Ruida-devices connected
using either Ethernet (UDP) or USB (serial) devices.

**NOTE:** The latest revision has been tested on Fedora Linux using a Ruida
RDC6442S controller and a monport MP-570 CO2 laser. At this time no other
controllers have been tested. Nor has there been any testing on Windows. In
order for moves to behave as expected and for coordinates to be displayed
correctly, Flip X must be enabled in the Ruida Configuration window.

**NOTE:** Raster layers must be configured with an overscan of 0.

## Untested
Using `ruidacontrol` for example will make a socket connection to make the localhost appear as a ruida laser cutter. Any
commands sent to it will be spooled and the resulting laser code will be sent to the locally configured active laser
device.

## Overview

The Ruida module attempts to provide comprehensive compatibility with Ruida DSP controllers and RDWorks software ecosystem. Unlike direct hardware drivers, this module primarily functions as:

**Untested**
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

#### RuidaControl (`controller.py`)
- **Server Management**: Controls UDP server instances for different ports
- **Traffic Routing**: Implements man-in-the-middle capabilities
- **Bridge Protocol**: Supports LB2RD (Lightburn to Ruida) bridging
- **Device Integration**: Routes commands to active MeerK40t laser devices

### Device Layer (`device.py`)
- **Service Integration**: Registers as MeerK40t device service
- **Configuration Management**: Handles device-specific settings
- **File Loading**: Supports .rd file import with RDLoader
- **Connection Multiplexing**: Supports multiple connection types (UDP and USB/Serial)

### Driver Layer (`driver.py`)
- **Cutcode Translation**: Converts Ruida commands to MeerK40t cutcode
- **Plot Planning**: Integrates with MeerK40t's plot planning system
- **Real-time Control**: Handles jog movements and status updates
- **Power/Speed Control**: Manages laser parameters during operation

### Session Layer (`ruidasession.py`)
- **Session**: Communication session management.
- **Connect/Disconnect**:Automatically connects and reconnects to the Ruida
  controller using either the UDP or USB/Serial transports.

### Transport Layer (`ruidatransport.py` and `udp_transport.py` or `usb_transport.py`)
- **Interface**: Communication device specific connection management.
- **Networked**: UDP protocol.
- **USB/Serial**: Connect via USB.

### USB Serial Devices and Linux
Many Linux distros do not reliably assign USB serial devices when the USB
connection is lost and restored. This can occur when a cable is unplugged and
then plugged back in or the device is turned off and then back on. This can be
annoying at times causing one to reconfigure a connection in MeerK40t in order
to re-establish the connection.

To see if this is occurring on most distros one can watch the assignments using
this command: `ls /dev/ttyU*`

Typically the assignment will be `/dev/ttyUSB0` if the Ruida controller is the
only USB serial device. After connection is lost and restored, the assignment can
change to `/dev/ttyUSB1` or higher. Sometimes waiting for a couple of minutes
while the controller is off will reset this assignment.

To mitigate this problem, a UDEV rule can be used. The serial device for the
known Ruida controllers is an FTDI device. Use `lsusb` while the controller is
connected and powered on to confirm. The ID should be `0403:6001`. The `<serial>`
number can be determined using the command:
`udevadm info -a -n /dev/ttyUSBx | grep '{serial}' | head -n3`

For example, the serial for an monport MP570 laser is: `AB0O3PGG`

The `<name>` can be whatever makes sense for your situation.

The corresponding UDEV rule is (note this may not work on all systems):
`SUBSYSTEM=="tty",ATTRS{idVendor}=="0403",ATTRS{idProduct}=="6001",ATTRS{serial}=="<serial>",SYMLINK+="<name>"`

Alternatively, the bus `<path>` can be used. To determine the path using the
command:
`udevadm info -a -n /dev/ttyUSB<x> | grep 'KERNELS' | head -n3`
The last path is often the one to use. For example, the path for the test laser
is: `1.9.3`. This will vary depending upon your PC and which port you have
the Ruida controller connected to. As long as you maintain the same physical
connection this will be consistent.

The corresponding UDEV rule for this approach is:
`KERNEL=="ttyUSB*",KERNELS=="<path>",SYMLINK+="<name>"`
This creates a symlink to the USB device assigned when it is connected.

I suggest having this rule in `/etc/udev/rules.d/99-lasers.rules`

After making the change activate it using the command:
`sudo udevadm control --reload-rules`


## Technical Features

### File Format Support

#### RD File Processing
- **Complete Parser**: Reads all known Ruida commands
- **Binary Decoding**: Handles Ruida's proprietary binary encoding

**NOTE:** These features are currently untested.
- **Magic Detection**: Automatically detects controller variant from file histogram
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
- **SerialConnection**: Direct serial connection to Ruida controllers

**Unsupported by Ruida controllers.**
- **TCPConnection**: Alternative TCP-based communication
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
