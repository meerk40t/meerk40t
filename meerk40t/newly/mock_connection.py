"""
Mock Connection for Newly

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

    def write(self, index=0, data=None):
        if data is None:
            return
        data_remaining = len(data)
        while data_remaining > 0:
            packet_length = min(0x1000, data_remaining)
            packet = data[:packet_length]

            #####################################
            # Step 1: Write the size of the packet.
            #####################################
            self._write_packet_size(index=index, packet=packet)

            #####################################
            # Step 2: read the confirmation value.
            #####################################
            self._read_confirmation(index=index)

            #####################################
            # Step #3, write the bulk data of the packet.
            #####################################
            self._write_bulk(index=index, packet=packet)

            data = data[packet_length:]
            data_remaining -= packet_length

    def _write_packet_size(self, index=0, packet=None, attempt=0):
        packet_length = len(packet)
        length_data = struct.pack(">h", packet_length)
        self.channel(f"{length_data}")

    def _read_confirmation(self, index=0, attempt=0):
        self.channel("1")

    def _write_bulk(self, index=0, packet: str=None):
        self.channel(packet)
