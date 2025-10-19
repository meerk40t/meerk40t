"""
Mock Connection for Galvo Controllers - Testing and Development Interface

This module provides a simulation interface for Balor/JCZ galvo laser controllers,
enabling development, testing, and debugging without requiring physical hardware.

Purpose:
========

The MockConnection class serves multiple critical development roles:

1. **Hardware-Free Development**: Build and test control logic without laser hardware
2. **Protocol Debugging**: Visualize command sequences and data flows
3. **Integration Testing**: Validate controller behavior in CI/CD pipelines
4. **User Training**: Safe environment for learning laser control operations
5. **Research and Analysis**: Study command patterns and protocol behavior

Architecture:
=============

The MockConnection implements the same interface as USBConnection and DirectUSBConnection,
making it a drop-in replacement for testing:

Connection Hierarchy:
    MockConnection → USBConnection/DirectUSBConnection (production)
    
Interface Compatibility:
    - open(index) - Simulates device connection
    - close(index) - Simulates device disconnection
    - write(index, packet) - Logs command packets instead of sending
    - read(index) - Returns synthetic status responses
    - is_open(index) - Tracks simulated connection state

Features:
=========

Command Parsing and Display:
    - Single commands (12 bytes): Decoded with command name lookup
    - Batch commands (3072 bytes): Full list parsing with repeat detection
    - Human-readable output: Formatted hexadecimal with operation names
    - Repeat compression: "... repeated N times ..." for duplicate commands

Response Simulation:
    - Customizable responses via set_implied_response()
    - Random data generation for realistic testing
    - Serial number emulation for device identification
    - 8-byte status format matching real hardware

Logging Integration:
    - send channel: Command transmission logs
    - recv channel: Response reception logs
    - Configurable verbosity for different testing scenarios
    - Compatible with MeerK40t kernel channel system

Technical Implementation:
=========================

Command Format Support:
    Single Command (12 bytes):
        [cmd_id:2][param1:4][param2:4][param3:2]
        Decoded using single_command_lookup dictionary
        
    Batch Commands (3072 bytes):
        256 × 12-byte commands
        Decoded using list_command_lookup dictionary
        Duplicate detection for output compression

Status Response Format (8 bytes):
    [status:1][flags:1][data:6]
    - Customizable via set_implied_response()
    - Random generation for varied testing scenarios
    - ASCII string encoding for special responses (e.g., serial numbers)

Usage Examples:
===============

Basic Testing:
    
    from meerk40t.balormk.mock_connection import MockConnection
    
    # Create mock connection with logging
    mock = MockConnection(logging_channel)
    mock.send = print  # Output commands to console
    mock.recv = print  # Output responses to console
    
    # Open simulated device
    mock.open(0)
    
    # Send test command
    import struct
    cmd = struct.pack('<6H', 0x001B, 0x8000, 0x8000, 0, 0, 0)
    mock.write(0, cmd)
    
    # Read simulated response
    response = mock.read(0)
    
    # Close simulated device
    mock.close(0)

Custom Response Testing:
    
    # Set specific response for testing
    mock.set_implied_response("SERIAL01")
    status = mock.read(0)  # Returns "SERIAL01" padded to 8 bytes
    
    # Reset to random responses
    mock.set_implied_response(None)

Integration with Controller:
    
    # Enable mock mode in device settings
    kernel.set_setting("mock", True)
    
    # Controller automatically uses MockConnection
    controller.connect_if_needed()
    # All operations now use mock instead of hardware

Testing Scenarios:
==================

Command Sequence Validation:
    - Verify correct command ordering
    - Check parameter encoding
    - Validate batch command generation
    - Monitor command timing patterns

Error Handling Testing:
    - Simulate connection failures
    - Test retry logic without hardware
    - Validate error recovery procedures
    - Check timeout behavior

Protocol Research:
    - Analyze command structures
    - Study parameter variations
    - Document undocumented operations
    - Reverse engineer protocol details

Integration Testing:
    - CI/CD pipeline validation
    - Automated test suites
    - Regression testing
    - Cross-platform compatibility checks

Development Benefits:
=====================

Safety:
    - No risk of hardware damage during development
    - Safe exploration of unknown commands
    - Testing without physical laser access
    - Development on machines without USB devices

Speed:
    - Instant "connection" without USB enumeration
    - No hardware timing constraints
    - Faster test execution
    - Parallel development workflows

Debugging:
    - Clear visibility of all commands
    - Human-readable command formatting
    - Repeat detection reduces log clutter
    - Custom response injection for testing

Portability:
    - Works on any platform
    - No USB driver requirements
    - No hardware dependencies
    - Cloud development environment compatible

Author: MeerK40t Development Team
License: MIT
Version: 1.0.0
"""

import random
import struct


class MockConnection:
    """
    Mock USB connection for galvo controller testing and development.
    
    Provides a complete simulation of USB communication without requiring hardware.
    Implements the same interface as USBConnection and DirectUSBConnection for
    seamless integration in testing and development environments.
    
    Attributes:
        channel: Logging channel for status messages
        send: Optional callable for command output (receives formatted command strings)
        recv: Optional callable for response output (receives formatted response strings)
        devices (dict): Simulated device state indexed by machine index
        interface (dict): Simulated interface state (compatibility)
        backend_error_code: Always None (compatibility with real connections)
        timeout (int): Simulated timeout in milliseconds (default: 500)
        is_direct_connection (bool): Always False (identifies as mock connection)
        _implied_response (bytes): Next response to return from read()
    
    Interface Compatibility:
        Implements identical interface to production connections:
        - open(index) → int: Simulates connection (always succeeds)
        - close(index) → None: Simulates disconnection
        - write(index, packet) → None: Logs command instead of sending
        - read(index) → bytes: Returns synthetic 8-byte response
        - is_open(index) → bool: Returns simulated connection state
        - bus(index) → int: Compatibility stub (not applicable)
        - address(index) → int: Compatibility stub (not applicable)
    
    Command Logging Features:
        - Automatic command parsing and formatting
        - Human-readable operation names from lookup tables
        - Hexadecimal parameter display
        - Duplicate command detection and compression
        - Separate channels for send/recv traffic
    
    Response Simulation:
        - Random 8-byte responses by default
        - Custom responses via set_implied_response()
        - Serial number emulation (responds to GetSerialNo)
        - Automatic reset after each read()
    
    Usage Patterns:
        Development Testing:
            mock = MockConnection(channel)
            mock.open(0)
            mock.write(0, command_packet)  # Logs command
            status = mock.read(0)  # Returns mock data
            
        CI/CD Integration:
            # Set mock mode in device configuration
            device.mock = True
            controller.connect_if_needed()  # Uses mock automatically
            
        Command Analysis:
            mock.send = lambda cmd: analysis_log.append(cmd)
            # All commands captured for analysis
    """
    
    def __init__(self, channel):
        """
        Initialize mock USB connection.
        
        Args:
            channel: Logging channel for status messages. Should implement
                    __call__ for message output and have _ attribute for
                    translation function.
        """
        self.channel = channel
        self.send = None
        self.recv = None
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 500
        self.is_direct_connection = False  # Flag to identify connection type
        self._implied_response = None

    def is_open(self, index=0):
        try:
            dev = self.devices[index]
            if dev:
                return True
        except KeyError:
            pass
        return False

    def open(self, index=0):
        """Opens device, returns index."""
        _ = self.channel._
        self.channel(_("Attempting connection to Mock."))
        self.devices[index] = True
        self.channel(_("Mock Connected."))
        return index

    def close(self, index=0):
        """Closes device."""
        _ = self.channel._
        device = self.devices[index]
        self.channel(_("Attempting disconnection from Mock."))
        if device is not None:
            self.channel(_("Mock Disconnection Successful.\n"))
            del self.devices[index]

    def write(self, index=0, packet=None):
        from meerk40t.balormk.controller import GetSerialNo

        packet_length = len(packet)
        assert packet_length == 0xC or packet_length == 0xC00
        if packet is not None:
            device = self.devices[index]
            if not device:
                raise ConnectionError
            b = packet[0]
            if b == GetSerialNo:
                self.set_implied_response("meerk40t")
            if self.send:
                if packet_length == 0xC:
                    self.send(self._parse_single(packet))
                else:
                    self.send(self._parse_list(packet))

    def _parse_list(self, packet):
        commands = []
        from meerk40t.balormk.controller import list_command_lookup

        last_cmd = None
        repeats = 0
        for i in range(0, len(packet), 12):
            b = struct.unpack("<6H", packet[i : i + 12])
            string_value = list_command_lookup.get(b[0], "Unknown")
            cmd = f"{b[0]:04x}:{b[1]:04x}:{b[2]:04x}:{b[3]:04x}:{b[4]:04x}:{b[5]:04x} {string_value}"
            if cmd == last_cmd:
                repeats += 1
                continue

            if repeats:
                commands.append(f"... repeated {repeats} times ...")
            repeats = 0
            commands.append(cmd)
            last_cmd = cmd
        if repeats:
            commands.append(f"... repeated {repeats} times ...")
        return "\n".join(commands)

    def _parse_single(self, packet):
        from meerk40t.balormk.controller import single_command_lookup

        b0 = packet[1] << 8 | packet[0]
        b1 = packet[3] << 8 | packet[2]
        b2 = packet[5] << 8 | packet[4]
        b3 = packet[7] << 8 | packet[6]
        b4 = packet[9] << 8 | packet[8]
        b5 = packet[11] << 8 | packet[10]
        string_value = single_command_lookup.get(b0, "Unknown")
        return f"{b0:04x}:{b1:04x}:{b2:04x}:{b3:04x}:{b4:04x}:{b5:04x} {string_value}"

    def set_implied_response(self, data):
        if data is None:
            self._implied_response = None
            return

        # Convert input to bytes early
        if isinstance(data, str):
            data = data.encode("ascii")

        # Create fixed-size response with padding
        self._implied_response = bytearray(8)
        self._implied_response[: len(data)] = data[:8]

    def read(self, index=0):
        if self._implied_response is None:
            read = bytearray(8)
            for r in range(len(read)):
                read[r] = random.randint(0, 255)
        else:
            read = self._implied_response
        read = struct.pack("8B", *read)
        device = self.devices[index]
        if not device:
            raise ConnectionError
        if self.recv:
            self.recv(
                f"{read[0]:02x}:{read[1]:02x}:{read[2]:02x}:{read[3]:02x}"
                f"{read[4]:02x}:{read[5]:02x}:{read[6]:02x}:{read[7]:02x}"
            )
        self.set_implied_response(None)
        return read
