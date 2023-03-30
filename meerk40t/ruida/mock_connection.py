"""
Mock Connection for Ruida Devices

The mock connection is used for debug and research purposes. And simply prints the data sent to it rather than engaging
any hardware.
"""

import random
import struct


class MockConnection:
    def __init__(self, channel):
        self.channel = channel
        self.send = None
        self.recv = None
        self.devices = {}
        self.interface = {}
        self.backend_error_code = None
        self.timeout = 500

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
        packet_length = len(packet)
        assert packet_length == 0xC or packet_length == 0xC00
        if packet is not None:
            device = self.devices[index]
            if not device:
                raise ConnectionError
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

    def read(self, index=0):
        read = bytearray(8)
        for r in range(len(read)):
            read[r] = random.randint(0, 255)
        read = struct.pack("8B", *read)
        device = self.devices[index]
        if not device:
            raise ConnectionError
        if self.recv:
            self.recv(
                f"{read[0]:02x}:{read[1]:02x}:{read[2]:02x}:{read[3]:02x}"
                f"{read[4]:02x}:{read[5]:02x}:{read[6]:02x}:{read[7]:02x}"
            )
        return read
