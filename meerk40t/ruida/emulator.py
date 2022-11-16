"""
Ruida Emulator

The emulator allows us to listen for connections that send ruida data, we emulate that a ruida controller and turn
the received data into laser commands to be executed by the local driver.
"""

import os
from io import BytesIO
from typing import Tuple, Union

from meerk40t.kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
    Module,
    get_safe_path,
    signal_listener,
)
from ..core.cutcode.cutcode import CutCode
from ..core.cutcode.plotcut import PlotCut

from ..core.node.cutnode import CutNode
from ..core.parameters import Parameters
from ..core.units import UNITS_PER_MM, UNITS_PER_uM
from ..svgelements import Color


class RuidaCommandError(Exception):
    """
    Exception raised when an invalid Ruida command is received.
    """


class RuidaEmulator(Module, Parameters):
    def __init__(self, context, path):
        Module.__init__(self, context, path)
        Parameters.__init__(self)
        self.design = False
        self.control = False
        self.saving = False

        self.filename = None
        self.filestream = None

        self.cutcode = CutCode()
        self.plotcut = PlotCut()

        self._use_set = None
        self.spooler = None
        self.device = None

        self.elements = None
        self.color = None

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.u = 0.0

        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0
        self.magic = 0x88  # 0x11 for the 634XG
        # Should automatically shift encoding if wrong.
        # self.magic = 0x38
        self.lut_swizzle, self.lut_unswizzle = RuidaEmulator.swizzles_lut(self.magic)

        self.power1_min = 0
        self.power1_max = 0
        self.power2_min = 0
        self.power2_max = 0

        self.ruida_channel = self.context.channel("ruida")
        self.ruida_describe = self.context.channel("ruida_desc")

        self.ruida_reply = self.context.channel("ruida_reply")
        self.ruida_reply_realtime = self.context.channel("ruida_reply_realtime")

        self.process_commands = True
        self.parse_lasercode = True
        self.swizzle_mode = True
        self.state = 22

    def __repr__(self):
        return f"Ruida({self.name}, {len(self.cutcode)} cuts @{hex(id(self))})"

    @signal_listener("pipe;thread")
    def on_pipe_state(self, origin, state):
        if self.device is not None and self.device.path != origin:
            return  # This pipe thread change is from the wrong device.
        if not self.control:
            return  # We are not using ruidacontrol mode. Do not update the state.
        if state == STATE_INITIALIZE:
            self.state = 22
        elif state == STATE_TERMINATE:
            self.state = 22
        elif state == STATE_END:
            self.state = 22
        elif state == STATE_PAUSE:
            self.state = 23
        elif state == STATE_BUSY:
            self.state = 23
        elif state == STATE_WAIT:
            self.state = 21
        elif state == STATE_ACTIVE:
            self.state = 21
        elif state == STATE_IDLE:
            self.state = 22
        elif state == STATE_UNKNOWN:
            self.state = 22

    def generate(self):
        for cutobject in self.cutcode:
            yield "plot", cutobject
        yield "plot_start"

    def new_plot_cut(self):
        if len(self.plotcut):
            # TODO: Ruida new plot cut sets the plotcut to cutset which is derived settings.
            self.plotcut.settings = self.cutset()
            self.plotcut.check_if_rasterable()
            self.cutcode.append(self.plotcut)
            self.plotcut = PlotCut()

    def cutset(self):
        if self._use_set is None:
            self._use_set = self.derive()
        return self._use_set

    @staticmethod
    def signed35(v):
        v &= 0x7FFFFFFFF
        if v > 0x3FFFFFFFF:
            return -0x800000000 + v
        else:
            return v

    @staticmethod
    def signed32(v):
        v &= 0xFFFFFFFF
        if v > 0x7FFFFFFF:
            return -0x100000000 + v
        else:
            return v

    @staticmethod
    def signed14(v):
        v &= 0x7FFF
        if v > 0x1FFF:
            return -0x4000 + v
        else:
            return v

    @staticmethod
    def decode14(data):
        return RuidaEmulator.signed14(RuidaEmulator.decodeu14(data))

    @staticmethod
    def decodeu14(data):
        return (data[0] & 0x7F) << 7 | (data[1] & 0x7F)

    @staticmethod
    def encode14(v):
        return [
            (v >> 7) & 0x7F,
            v & 0x7F,
        ]

    @staticmethod
    def decode35(data):
        return RuidaEmulator.signed35(RuidaEmulator.decodeu35(data))

    @staticmethod
    def decode32(data):
        return RuidaEmulator.signed32(RuidaEmulator.decodeu35(data))

    @staticmethod
    def decodeu35(data):
        return (
            (data[0] & 0x7F) << 28
            | (data[1] & 0x7F) << 21
            | (data[2] & 0x7F) << 14
            | (data[3] & 0x7F) << 7
            | (data[4] & 0x7F)
        )

    @staticmethod
    def encode32(v):
        return [
            (v >> 28) & 0x7F,
            (v >> 21) & 0x7F,
            (v >> 14) & 0x7F,
            (v >> 7) & 0x7F,
            v & 0x7F,
        ]

    @staticmethod
    def abscoord(data):
        return RuidaEmulator.decode32(data)

    @staticmethod
    def relcoord(data):
        return RuidaEmulator.decode14(data)

    @staticmethod
    def parse_mem(data):
        return RuidaEmulator.decode14(data)

    @staticmethod
    def parse_filenumber(data):
        return RuidaEmulator.decode14(data)

    @staticmethod
    def parse_speed(data):
        return RuidaEmulator.decode35(data) / 1000.0

    @staticmethod
    def parse_frequency(data):
        return RuidaEmulator.decodeu35(data)

    @staticmethod
    def parse_power(data):
        return RuidaEmulator.decodeu14(data) / 163.84  # 16384 / 100%

    @staticmethod
    def parse_time(data):
        return RuidaEmulator.decodeu35(data) / 1000.0

    @staticmethod
    def parse_commands(f):
        array = list()
        while True:
            byte = f.read(1)
            if len(byte) == 0:
                break
            b = ord(byte)
            if b >= 0x80 and len(array) > 0:
                yield array
                array.clear()
            array.append(b)
        if len(array) > 0:
            yield array

    def reply(self, response, desc="ACK"):
        if self.swizzle_mode:
            self.ruida_reply(self.swizzle(response))
        else:
            self.ruida_reply_realtime(response)
        self.ruida_channel(f"<-- {response.hex()}\t({desc})")

    def checksum_write(self, sent_data):
        """
        This is `write` with a checksum and swizzling. This is how the 50200 packets arrive and need to be processed.

        @param sent_data: Packet data.
        @return:
        """
        self.swizzle_mode = True
        if len(sent_data) < 2:
            return  # Cannot contain a checksum.
        data = sent_data[2:1472]
        checksum_check = (sent_data[0] & 0xFF) << 8 | sent_data[1] & 0xFF
        checksum_sum = sum(data) & 0xFFFF
        if len(sent_data) > 3:
            if self.magic != 0x88 and sent_data[2] == 0xD4:
                self.magic = 0x88
                self.lut_swizzle, self.lut_unswizzle = RuidaEmulator.swizzles_lut(
                    self.magic
                )
                self.ruida_channel("Setting magic to 0x88")
            if self.magic != 0x11 and sent_data[2] == 0x4B:
                self.magic = 0x11
                self.lut_swizzle, self.lut_unswizzle = RuidaEmulator.swizzles_lut(
                    self.magic
                )
                self.ruida_channel("Setting magic to 0x11")

        if checksum_check == checksum_sum:
            response = b"\xCC"
            self.reply(response, desc="Checksum match")
        else:
            response = b"\xCF"
            self.reply(
                response, desc=f"Checksum Fail ({checksum_sum} != {checksum_check})"
            )
            self.ruida_channel("--> " + str(data.hex()))
            return
        self.write(BytesIO(self.unswizzle(data)))

    def realtime_write(self, bytes_to_write):
        """
        Real time commands are replied to and sent in realtime. For Ruida devices these are sent along udp 50207.

        @param bytes_to_write:
        @return: bytes to write.
        """
        self.swizzle_mode = False
        self.reply(b"\xCC")  # Clear ACK.
        self.write(BytesIO(bytes_to_write))

    def write(self, data):
        """
        Procedural commands sent in large data chunks. This can be through USB or UDP or a loaded file. These are
        expected to be unswizzled with the swizzle_mode set for the reply. Write will parse out the individual commands
        and send those to the command routine.

        @param data:
        @return:
        """
        for array in self.parse_commands(data):
            try:
                self.process(array)
            except RuidaCommandError:
                self.ruida_channel(f"Process Failure: {str(bytes(array).hex())}")
            except Exception as e:
                self.ruida_channel(f"Crashed processing: {str(bytes(array).hex())}")
                self.ruida_channel(str(e))
                raise e

    def process(self, array):
        """
        Parses an individual unswizzled ruida command, updating the emulator state.

        These commands can change the position, settings, speed, color, power, create elements, creates lasercode.
        @param array:
        @return:
        """
        desc = ""
        respond = None
        respond_desc = None
        start_x = self.x
        start_y = self.y
        if self.filestream:
            self.filestream.write(self.swizzle(array))
        if array[0] < 0x80:
            self.ruida_channel(f"NOT A COMMAND: {array[0]}")
            raise RuidaCommandError
        elif array[0] == 0x80:
            value = self.abscoord(array[2:7])
            if array[1] == 0x00:
                desc = f"Axis X Move {value}"
                self.x += value
            elif array[1] == 0x08:
                desc = f"Axis Z Move {value}"
                self.z += value
        elif array[0] == 0x88:  # 0b10001000 11 characters.
            if self.speed < 40:
                self.new_plot_cut()

            self.x = self.abscoord(array[1:6])
            self.y = self.abscoord(array[6:11])
            self.plotcut.plot_append(
                int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 0
            )
            desc = f"Move Absolute ({self.x * UNITS_PER_uM} units, {self.y * UNITS_PER_uM} units)"
        elif array[0] == 0x89:  # 0b10001001 5 characters
            if len(array) > 1:
                if self.speed < 40:
                    self.new_plot_cut()
                dx = self.relcoord(array[1:3])
                dy = self.relcoord(array[3:5])
                self.x += dx
                self.y += dy
                self.plotcut.plot_append(
                    int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 0
                )
                desc = f"Move Relative ({dx * UNITS_PER_uM} units, {dy * UNITS_PER_uM} units)"
            else:
                desc = "Move Relative (no coords)"
        elif array[0] == 0x8A:  # 0b10101010 3 characters
            dx = self.relcoord(array[1:3])
            self.x += dx
            self.plotcut.plot_append(
                int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 0
            )
            desc = f"Move Horizontal Relative ({dx * UNITS_PER_uM} units)"
        elif array[0] == 0x8B:  # 0b10101011 3 characters
            dy = self.relcoord(array[1:3])
            self.y += dy
            self.plotcut.plot_append(
                int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 0
            )
            desc = f"Move Vertical Relative ({dy * UNITS_PER_uM} units)"
        elif array[0] == 0x97:
            desc = "Lightburn Swizzle Modulation 97"
        elif array[0] == 0x9B:
            desc = "Lightburn Swizzle Modulation 9b"
        elif array[0] == 0x9E:
            desc = "Lightburn Swizzle Modulation 9e"
        elif array[0] == 0xA0:
            value = self.abscoord(array[2:7])
            if array[1] == 0x00:
                desc = f"Axis Y Move {value}"
            elif array[1] == 0x08:
                desc = f"Axis U Move {value}"
        elif array[0] == 0xA5:
            key = None
            if array[1] == 0x50:
                key = "Down"
            elif array[1] == 0x51:
                key = "Up"
            if array[1] == 0x53:
                if array[2] == 0x00:
                    desc = "Interface Frame"
            else:
                if array[2] == 0x02:
                    desc = f"Interface +X {key}"
                    if self.control:
                        if key == "Down":
                            self.context("+right\n")
                        else:
                            self.context("-right\n")
                elif array[2] == 0x01:
                    desc = f"Interface -X {key}"
                    if self.control:
                        if key == "Down":
                            self.context("+left\n")
                        else:
                            self.context("-left\n")
                if array[2] == 0x03:
                    desc = f"Interface +Y {key}"
                    if self.control:
                        if key == "Down":
                            self.context("+up\n")
                        else:
                            self.context("-up\n")
                elif array[2] == 0x04:
                    desc = f"Interface -Y {key}"
                    if self.control:
                        if key == "Down":
                            self.context("+down\n")
                        else:
                            self.context("-down\n")
                if array[2] == 0x0A:
                    desc = f"Interface +Z {key}"
                elif array[2] == 0x0B:
                    desc = f"Interface -Z {key}"
                if array[2] == 0x0C:
                    desc = f"Interface +U {key}"
                elif array[2] == 0x0D:
                    desc = f"Interface -U {key}"
                elif array[2] == 0x05:
                    desc = f"Interface Pulse {key}"
                    if self.control:
                        if key == "Down":
                            self.context("+laser\n")
                        else:
                            self.context("-laser\n")
                elif array[2] == 0x11:
                    desc = "Interface Speed"
                elif array[2] == 0x06:
                    desc = "Interface Start/Pause"
                    if self.control:
                        self.context("pause\n")
                elif array[2] == 0x09:
                    desc = "Interface Stop"
                    if self.control:
                        self.context("estop\n")
                elif array[2] == 0x5A:
                    desc = "Interface Reset"
                elif array[2] == 0x0F:
                    desc = "Interface Trace On/Off"
                elif array[2] == 0x07:
                    desc = "Interface ESC"
                elif array[2] == 0x12:
                    desc = "Interface Laser Gate"
                elif array[2] == 0x08:
                    desc = "Interface Origin"
        elif array[0] == 0xA8:  # 0b10101000 11 characters.
            self.x = self.abscoord(array[1:6])
            self.y = self.abscoord(array[6:11])
            self.plotcut.plot_append(
                int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 1
            )
            desc = f"Cut Absolute ({self.x * UNITS_PER_uM} units, {self.y * UNITS_PER_uM} units)"
        elif array[0] == 0xA9:  # 0b10101001 5 characters
            dx = self.relcoord(array[1:3])
            dy = self.relcoord(array[3:5])
            self.x += dx
            self.y += dy
            self.plotcut.plot_append(
                int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 1
            )
            desc = (
                f"Cut Relative ({dx * UNITS_PER_uM} units, {dy * UNITS_PER_uM} units)"
            )
        elif array[0] == 0xAA:  # 0b10101010 3 characters
            dx = self.relcoord(array[1:3])
            self.x += dx
            self.plotcut.plot_append(
                int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 1
            )
            desc = f"Cut Horizontal Relative ({dx * UNITS_PER_uM} units)"
        elif array[0] == 0xAB:  # 0b10101011 3 characters
            dy = self.relcoord(array[1:3])
            self.y += dy
            self.plotcut.plot_append(
                int(self.x * UNITS_PER_uM), int(self.y * UNITS_PER_uM), 1
            )
            desc = f"Cut Vertical Relative ({dy * UNITS_PER_uM} units)"
        elif array[0] == 0xC7:
            v0 = self.parse_power(array[1:3])  # TODO: Check command fewer values.
            desc = f"Imd Power 1 ({v0})"
        elif array[0] == 0xC2:
            v0 = self.parse_power(array[1:3])
            desc = f"Imd Power 3 ({v0})"
        elif array[0] == 0xC0:
            v0 = self.parse_power(array[1:3])
            desc = f"Imd Power 2 ({v0})"
        elif array[0] == 0xC3:
            v0 = self.parse_power(array[1:3])
            desc = f"Imd Power 4 ({v0})"
        elif array[0] == 0xC8:
            v0 = self.parse_power(array[1:3])
            desc = f"End Power 1 ({v0})"
        elif array[0] == 0xC4:
            v0 = self.parse_power(array[1:3])
            desc = f"End Power 3 ({v0})"
        elif array[0] == 0xC1:
            v0 = self.parse_power(array[1:3])
            desc = f"End Power 2 ({v0})"
        elif array[0] == 0xC5:
            v0 = self.parse_power(array[1:3])
            desc = f"End Power 4 ({v0})"
        elif array[0] == 0xC6:
            if array[1] == 0x01:
                self.new_plot_cut()
                power = self.parse_power(array[2:4])
                desc = f"Power 1 min={power}"
                self.power1_min = power
                self.power = self.power1_max * 10.0  # 1000 / 100
                self._use_set = None
            elif array[1] == 0x02:
                self.new_plot_cut()
                power = self.parse_power(array[2:4])
                desc = f"Power 1 max={power}"
                self.power1_max = power
                self.power = self.power1_max * 10.0  # 1000 / 100
                self._use_set = None
            elif array[1] == 0x05:
                power = self.parse_power(array[2:4])
                desc = f"Power 3 min={power}"
            elif array[1] == 0x06:
                power = self.parse_power(array[2:4])
                desc = f"Power 3 max={power}"
            elif array[1] == 0x07:
                power = self.parse_power(array[2:4])
                desc = f"Power 4 min={power}"
            elif array[1] == 0x08:
                power = self.parse_power(array[2:4])
                desc = f"Power 4 max={power}"
            elif array[1] == 0x10:
                interval = self.parse_time(array[2:7])
                desc = f"Laser Interval {interval}ms"
            elif array[1] == 0x11:
                interval = self.parse_time(array[2:7])
                desc = f"Add Delay {interval}ms"
            elif array[1] == 0x12:
                interval = self.parse_time(array[2:7])
                desc = f"Laser On Delay {interval}ms"
            elif array[1] == 0x13:
                interval = self.parse_time(array[2:7])
                desc = f"Laser Off Delay {interval}ms"
            elif array[1] == 0x15:
                interval = self.parse_time(array[2:7])
                desc = f"Laser On2 {interval}ms"
            elif array[1] == 0x16:
                interval = self.parse_time(array[2:7])
                desc = f"Laser Off2 {interval}ms"
            elif array[1] == 0x21:
                power = self.parse_power(array[2:4])
                desc = f"Power 2 min={power}"
                self.power2_min = power
            elif array[1] == 0x22:
                power = self.parse_power(array[2:4])
                desc = f"Power 2 max={power}"
                self.power2_max = power
            elif array[1] == 0x31:
                part = array[2]
                self.power1_min = self.parse_power(array[3:5])
                desc = f"{part}, Power 1 Min=({self.power1_min})"
            elif array[1] == 0x32:
                part = array[2]
                self.power1_max = self.parse_power(array[3:5])
                desc = f"{part}, Power 1 Max=({self.power1_max})"
            elif array[1] == 0x35:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = f"{part}, Power 3 Min ({power})"
            elif array[1] == 0x36:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = f"{part}, Power 3 Max ({power})"
            elif array[1] == 0x37:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = f"{part}, Power 4 Min ({power})"
            elif array[1] == 0x38:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = f"{part}, Power 4 Max ({power})"
            elif array[1] == 0x41:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = f"{part}, Power 2 Min ({power})"
            elif array[1] == 0x42:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = f"{part}, Power 2 Max ({power})"
            elif array[1] == 0x50:
                power = self.parse_power(array[2:4])
                desc = f"Through Power 1 ({power})"
            elif array[1] == 0x51:
                power = self.parse_power(array[2:4])
                desc = f"Through Power 2 ({power})"
            elif array[1] == 0x55:
                power = self.parse_power(array[2:4])
                desc = f"Through Power 3 ({power})"
            elif array[1] == 0x56:
                power = self.parse_power(array[2:4])
                desc = f"Through Power 4 ({power})"
            elif array[1] == 0x60:
                laser = array[2]
                part = array[3]
                frequency = self.parse_frequency(array[4:9])
                desc = f"part, Laser {laser}, Frequency ({frequency})"
        elif array[0] == 0xC9:
            if array[1] == 0x02:
                self.new_plot_cut()
                speed = self.parse_speed(array[2:7])
                desc = f"Speed Laser 1 {speed}mm/s"
                self.speed = speed
                self._use_set = None
            elif array[1] == 0x03:
                speed = self.parse_speed(array[2:7])
                desc = f"Axis Speed {speed}mm/s"
            elif array[1] == 0x04:
                self.new_plot_cut()
                part = array[2]
                speed = self.parse_speed(array[3:8])
                self.speed = speed
                self._use_set = None
                desc = f"{part}, Speed {speed}mm/s"
            elif array[1] == 0x05:
                speed = self.parse_speed(array[2:7]) / 1000.0
                desc = f"Force Eng Speed {speed}mm/s"
            elif array[1] == 0x06:
                speed = self.parse_speed(array[2:7]) / 1000.0
                desc = f"Axis Move Speed {speed}mm/s"
        elif array[0] == 0xCA:
            if array[1] == 0x01:
                if array[2] == 0x00:
                    desc = "End Layer"
                elif array[2] == 0x01:
                    desc = "Work Mode 1"
                elif array[2] == 0x02:
                    desc = "Work Mode 2"
                elif array[2] == 0x03:
                    desc = "Work Mode 3"
                elif array[2] == 0x04:
                    desc = "Work Mode 4"
                elif array[2] == 0x55:
                    desc = "Work Mode 5"
                elif array[2] == 0x05:
                    desc = "Work Mode 6"
                elif array[2] == 0x10:
                    desc = "Layer Device 0"
                elif array[2] == 0x11:
                    desc = "Layer Device 1"
                elif array[2] == 0x12:
                    desc = "Air Assist Off"
                elif array[2] == 0x13:
                    desc = "Air Assist On"
                elif array[2] == 0x14:
                    desc = "DbHead"
                elif array[2] == 0x30:
                    desc = "EnLaser2Offset 0"
                elif array[2] == 0x31:
                    desc = "EnLaser2Offset 1"
            elif array[1] == 0x02:
                part = array[2]
                desc = f"{part}, Layer Number"
            elif array[1] == 0x03:
                desc = "EnLaserTube Start"
            elif array[1] == 0x04:
                value = array[2]
                desc = f"X Sign Map {value}"
            elif array[1] == 0x05:
                self.new_plot_cut()
                c = RuidaEmulator.decodeu35(array[2:7])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.color = c.hex
                self.line_color = c
                self._use_set = None
                desc = f"Layer Color {str(self.color)}"
            elif array[1] == 0x06:
                part = array[2]
                c = RuidaEmulator.decodeu35(array[3:8])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.color = c.hex
                desc = f"{part}, Color {self.color}"
            elif array[1] == 0x10:
                value = array[2]
                desc = f"EnExIO Start {value}"
            elif array[1] == 0x22:
                part = array[2]
                desc = f"{part}, Max Layer"
            elif array[1] == 0x30:
                filenumber = self.parse_filenumber(array[2:4])
                desc = f"U File ID {filenumber}"
            elif array[1] == 0x40:
                value = array[2]
                desc = f"ZU Map {value}"
            elif array[1] == 0x41:
                part = array[2]
                mode = array[3]
                desc = f"{part}, Work Mode {mode}"
        elif array[0] == 0xCC:
            desc = "ACK from machine"
        elif array[0] == 0xCD:
            desc = "ERR from machine"
        elif array[0] == 0xCE:
            desc = "Keep Alive"
        elif array[0] == 0xD0:
            if array[1] == 0x29:
                desc = "Unknown LB Command"
        elif array[0] == 0xD7:
            # If not saving send to spooler in control or elements if `design` is set.
            if not self.saving and len(self.cutcode):
                if self.control:
                    matrix = self.device.scene_to_device_matrix()
                    for plot in self.cutcode:
                        for i in range(len(plot.plot)):
                            x, y, laser = plot.plot[i]
                            x, y = matrix.transform_point([x, y])
                            plot.plot[i] = int(x), int(y), laser
                    self.spooler.laserjob([self.cutcode])
                if self.design and self.elements is not None:
                    node = CutNode(cutcode=self.cutcode)
                    self.elements.op_branch.add_node(node)
            self.cutcode = CutCode()
            self.plotcut = PlotCut()
            self.saving = False
            self.filename = None
            if self.filestream is not None:
                self.filestream.close()
                self.filestream = None
            desc = "End Of File"
        elif array[0] == 0xD8:
            if array[1] == 0x00:
                desc = "Start Process"
            if array[1] == 0x01:
                desc = "Stop Process"
                if self.control:
                    self.context("estop\ntimer 1 1 home\n")
            if array[1] == 0x02:
                desc = "Pause Process"
                if self.control:
                    self.context("pause\n")
            if array[1] == 0x03:
                desc = "Restore Process"
                if self.control:
                    self.context("resume\n")
            if array[1] == 0x10:
                desc = "Ref Point Mode 2, Machine Zero/Absolute Position"
            if array[1] == 0x11:
                desc = "Ref Point Mode 1, Anchor Point"
            if array[1] == 0x12:
                desc = "Ref Point Mode 0, Current Position"
            if array[1] == 0x2C:
                self.z = 0.0
                desc = "Home Z"
            if array[1] == 0x2D:
                self.u = 0.0
                desc = "Home U"
            if array[1] == 0x2A:
                self.x = 0.0
                self.y = 0.0
                desc = "Home XY"
                if self.control:
                    self.context("home\n")
            if array[1] == 0x2E:
                desc = "FocusZ"
            if array[1] == 0x20:
                desc = "KeyDown -X +Left"
                if self.control:
                    self.context("+left\n")
            if array[1] == 0x21:
                desc = "KeyDown +X +Right"
                if self.control:
                    self.context("+right\n")
            if array[1] == 0x22:
                desc = "KeyDown +Y +Top"
                if self.control:
                    self.context("+up\n")
            if array[1] == 0x23:
                desc = "KeyDown -Y +Bottom"
                if self.control:
                    self.context("+down\n")
            if array[1] == 0x24:
                desc = "KeyDown +Z"
            if array[1] == 0x25:
                desc = "KeyDown -Z"
            if array[1] == 0x26:
                desc = "KeyDown +U"
            if array[1] == 0x27:
                desc = "KeyDown -U"
            if array[1] == 0x28:
                desc = "KeyDown 0x21"
            if array[1] == 0x30:
                desc = "KeyUp -X +Left"
                if self.control:
                    self.context("-left\n")
            if array[1] == 0x31:
                desc = "KeyUp +X +Right"
                if self.control:
                    self.context("-right\n")
            if array[1] == 0x32:
                desc = "KeyUp +Y +Top"
                if self.control:
                    self.context("-up\n")
            if array[1] == 0x33:
                desc = "KeyUp -Y +Bottom"
                if self.control:
                    self.context("-down\n")
            if array[1] == 0x34:
                desc = "KeyUp +Z"
            if array[1] == 0x35:
                desc = "KeyUp -Z"
            if array[1] == 0x36:
                desc = "KeyUp +U"
            if array[1] == 0x37:
                desc = "KeyUp -U"
            if array[1] == 0x38:
                desc = "KeyUp 0x20"
            if array[1] == 0x39:
                desc = "Home A"
            if array[1] == 0x3A:
                desc = "Home B"
            if array[1] == 0x3B:
                desc = "Home C"
            if array[1] == 0x3C:
                desc = "Home D"
            if array[1] == 0x40:
                desc = "KeyDown 0x18"
            if array[1] == 0x41:
                desc = "KeyDown 0x19"
            if array[1] == 0x42:
                desc = "KeyDown 0x1A"
            if array[1] == 0x43:
                desc = "KeyDown 0x1B"
            if array[1] == 0x44:
                desc = "KeyDown 0x1C"
            if array[1] == 0x45:
                desc = "KeyDown 0x1D"
            if array[1] == 0x46:
                desc = "KeyDown 0x1E"
            if array[1] == 0x47:
                desc = "KeyDown 0x1F"
            if array[1] == 0x48:
                desc = "KeyUp 0x08"
            if array[1] == 0x49:
                desc = "KeyUp 0x09"
            if array[1] == 0x4A:
                desc = "KeyUp 0x0A"
            if array[1] == 0x4B:
                desc = "KeyUp 0x0B"
            if array[1] == 0x4C:
                desc = "KeyUp 0x0C"
            if array[1] == 0x4D:
                desc = "KeyUp 0x0D"
            if array[1] == 0x4E:
                desc = "KeyUp 0x0E"
            if array[1] == 0x4F:
                desc = "KeyUp 0x0F"
            if array[1] == 0x51:
                desc = "Inhale On/Off"
        elif array[0] == 0xD9:
            if len(array) == 1:
                desc = "Unknown Directional Setting"
            else:
                options = array[2]
                if options == 0x03:
                    param = "Light"
                elif options == 0x02:
                    param = ""
                elif options == 0x01:
                    param = "Light/Origin"
                else:  # options == 0x00:
                    param = "Origin"
                if array[1] == 0x00 or array[1] == 0x50:
                    coord = self.abscoord(array[3:8])
                    self.x += coord
                    desc = f"Move {param} X: {coord} ({self.x},{self.y})"
                    if self.control:
                        self.context(
                            f"move -f {self.x * UNITS_PER_uM / UNITS_PER_MM}mm {self.y * UNITS_PER_uM / UNITS_PER_MM}mm\n"
                        )
                elif array[1] == 0x01 or array[1] == 0x51:
                    coord = self.abscoord(array[3:8])
                    self.y += coord
                    desc = f"Move {param} Y: {coord} ({self.x},{self.y})"
                    if self.control:
                        self.context(
                            f"move -f {self.x * UNITS_PER_uM / UNITS_PER_MM}mm {self.y * UNITS_PER_uM / UNITS_PER_MM}mm\n"
                        )
                elif array[1] == 0x02 or array[1] == 0x52:
                    coord = self.abscoord(array[3:8])
                    self.z += coord
                    desc = f"Move {param} Z: {coord} ({self.x},{self.y})"
                elif array[1] == 0x03 or array[1] == 0x53:
                    coord = self.abscoord(array[3:8])
                    self.u += coord
                    desc = f"Move {param} U: {coord} ({self.x},{self.y})"
                elif array[1] == 0x0F:
                    desc = "Feed Axis Move"
                elif array[1] == 0x10 or array[1] == 0x60:
                    self.x = self.abscoord(array[3:8])
                    self.y = self.abscoord(array[8:13])
                    desc = f"Move {param} XY ({self.x * UNITS_PER_uM}, {self.y * UNITS_PER_uM})"
                    # self.x = 0
                    # self.y = 0
                    if self.control:
                        if "Origin" in param:
                            self.context(
                                f"move_origin -f {self.x * UNITS_PER_uM / UNITS_PER_MM}mm {self.y * UNITS_PER_uM / UNITS_PER_MM}mm\n"
                            )
                        else:
                            self.context("home\n")
                elif array[1] == 0x30 or array[1] == 0x70:
                    self.x = self.abscoord(array[3:8])
                    self.y = self.abscoord(array[8:13])
                    self.u = self.abscoord(array[13 : 13 + 5])
                    desc = f"Move {param} XYU: {self.x * UNITS_PER_uM} ({self.y * UNITS_PER_uM},{self.u * UNITS_PER_uM})"
        elif array[0] == 0xDA:
            mem = self.parse_mem(array[2:4])
            name, v = self.mem_lookup(mem)
            if array[1] == 0x00:
                if name is None:
                    name = "Unmapped"
                desc = f"Get {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name})"
                if isinstance(v, int):
                    v = int(v)
                    vencode = RuidaEmulator.encode32(v)
                    respond = b"\xDA\x01" + bytes(array[2:4]) + bytes(vencode)
                    respond_desc = f"Respond {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name}) = {v} (0x{v:08x})"
                else:
                    vencode = v
                    respond = b"\xDA\x01" + bytes(array[2:4]) + bytes(vencode)
                    respond_desc = f"Respond {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name}) = {str(vencode)}"
            elif array[1] == 0x01:
                value0 = array[4:9]
                value1 = array[9:14]
                v0 = self.decodeu35(value0)
                v1 = self.decodeu35(value1)
                desc = f"Set {array[2]:02x} {array[3]:02x} (mem: {mem:04x}) ({name}) = {v0} (0x{v0:08x}) {v1} (0x{v1:08x})"
            elif array[1] == 0x04:
                desc = "OEM On/Off, CardIO On/OFF"
            elif array[1] == 0x05 or array[1] == 0x54:
                desc = "Read Run Info"
                respond = b"\xda\x05" + b"\x00" * 20
                respond_desc = "Read Run Response"
            elif array[1] == 0x06 or array[1] == 0x52:
                desc = "Unknown/System Time."
            elif array[1] == 0x10 or array[1] == 0x53:
                desc = "Unknown Function--3"
            elif array[1] == 0x30:
                # Property requested with select document, upload button "fresh property"
                filenumber = self.parse_filenumber(array[2:4])
                desc = f"Upload Info 0x30 Document {filenumber}"
                respond = b"\xda\x30" + b"\x00" * 20
                # TODO: Requires Response.
            elif array[1] == 0x31:
                # Property requested with select document, upload button "fresh property"
                filenumber = self.parse_filenumber(array[2:4])
                desc = f"Upload Info 0x31 Document {filenumber}"
                # TODO: Requires Response.
                respond = b"\xda\x31" + b"\x00" * 20
            elif array[1] == 0x60:
                # len: 14
                v = self.decode14(array[2:4])
                desc = f"RD-FUNCTION-UNK1 {v}"
        elif array[0] == 0xE5:  # 0xE502
            if len(array) == 1:
                desc = "Lightburn Swizzle Modulation E5"
            else:
                if array[1] == 0x00:
                    # RDWorks File Upload
                    filenumber = array[2]
                    desc = f"Document Page Number {filenumber}"
                    # TODO: Requires Response.
                if array[1] == 0x02:
                    # len 3
                    desc = "Document Data End"
        elif array[0] == 0xE6:
            if array[1] == 0x01:
                desc = "Set Absolute"
                # Only seen in Absolute Coords. MachineZero is Ref2 but does not Set Absolute.
        elif array[0] == 0xE7:
            if array[1] == 0x00:
                self.new_plot_cut()
                desc = "Block End"
            elif array[1] == 0x01:
                self.filename = ""
                for a in array[2:]:
                    if a == 0x00:
                        break
                    self.filename += chr(a)
                desc = f"Filename: {self.filename}"
                if self.saving:
                    self.filestream = open(get_safe_path(f"{self.filename}.rd"), "wb")
            elif array[1] == 0x03:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Process TopLeft ({c_x}, {c_y})"
            elif array[1] == 0x04:
                v0 = self.decode14(array[2:4])
                v1 = self.decode14(array[4:6])
                v2 = self.decode14(array[6:8])
                v3 = self.decode14(array[8:10])
                v4 = self.decode14(array[10:12])
                v5 = self.decode14(array[12:14])
                v6 = self.decode14(array[14:16])
                desc = f"Process Repeat ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            elif array[1] == 0x05:
                direction = array[2]
                desc = f"Array Direction ({direction})"
            elif array[1] == 0x06:
                v1 = self.decodeu35(array[2:7])
                v2 = self.decodeu35(array[7:12])
                desc = f"Feed Repeat ({v1}, {v2})"
            elif array[1] == 0x07:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Process BottomRight({c_x}, {c_y})"
            elif array[1] == 0x08:  # Same value given to F2 05
                v0 = self.decode14(array[2:4])
                v1 = self.decode14(array[4:6])
                v2 = self.decode14(array[6:8])
                v3 = self.decode14(array[8:10])
                v4 = self.decode14(array[10:12])
                v5 = self.decode14(array[12:14])
                v6 = self.decode14(array[14:16])
                desc = f"Array Repeat ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            elif array[1] == 0x09:
                v1 = self.decodeu35(array[2:7])
                desc = f"Feed Length {v1}"
            elif array[1] == 0x0B:
                v1 = array[2]
                desc = f"Unknown 1 {v1}"
            elif array[1] == 0x13:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Array Min Point ({c_x},{c_y})"
            elif array[1] == 0x17:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Array Max Point ({c_x},{c_y})"
            elif array[1] == 0x23:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Array Add ({c_x},{c_y})"
            elif array[1] == 0x24:
                v1 = array[2]
                desc = f"Array Mirror {v1}"
            elif array[1] == 0x32:
                v1 = self.decodeu35(array[2:7])
                desc = f"Unknown Preamble {v1}"
            elif array[1] == 0x35:
                v1 = self.decodeu35(array[2:7])
                v2 = self.decodeu35(array[7:12])
                desc = f"Block X Size {v1} {v2}"
            elif array[1] == 0x38:
                v1 = array[2]
                desc = f"Unknown 2 {v1}"
            elif array[1] == 0x46:
                desc = "BY Test 0x11227766"
            elif array[1] == 0x50:
                c_x = self.abscoord(array[1:6]) * UNITS_PER_uM
                c_y = self.abscoord(array[6:11]) * UNITS_PER_uM
                desc = f"Document Min Point({c_x}, {c_y})"
            elif array[1] == 0x51:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Document Max Point({c_x}, {c_y})"
            elif array[1] == 0x52:
                part = array[2]
                c_x = self.abscoord(array[3:8]) * UNITS_PER_uM
                c_y = self.abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, Min Point({c_x}, {c_y})"
            elif array[1] == 0x53:
                part = array[2]
                c_x = self.abscoord(array[3:8]) * UNITS_PER_uM
                c_y = self.abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, MaxPoint({c_x}, {c_y})"
            elif array[1] == 0x54:
                axis = array[2]
                c_x = self.abscoord(array[3:8]) * UNITS_PER_uM
                desc = f"Pen Offset {axis}: {c_x}"
            elif array[1] == 0x55:
                axis = array[2]
                c_x = self.abscoord(array[3:8]) * UNITS_PER_uM
                desc = f"Layer Offset {axis}: {c_x}"
            elif array[1] == 0x60:
                desc = f"Set Current Element Index ({array[2]})"
            elif array[1] == 0x61:
                part = array[2]
                c_x = self.abscoord(array[3:8]) * UNITS_PER_uM
                c_y = self.abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, MinPointEx({c_x}, {c_y})"
            elif array[1] == 0x62:
                part = array[2]
                c_x = self.abscoord(array[3:8]) * UNITS_PER_uM
                c_y = self.abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, MaxPointEx({c_x}, {c_y})"
        elif array[0] == 0xE8:
            if array[1] == 0x00:
                # e8 00 00 00 00 00
                v1 = self.parse_filenumber(array[2:4])
                v2 = self.parse_filenumber(array[4:6])
                from glob import glob
                from os.path import join, realpath

                files = [
                    name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))
                ]
                if v1 == 0:
                    for f in files:
                        os.remove(f)
                    desc = "Delete All Documents"
                else:
                    name = files[v1 - 1]
                    os.remove(name)
                    desc = f"Delete Document {v1} {v2}"
            elif array[1] == 0x01:
                filenumber = self.parse_filenumber(array[2:4])
                desc = f"Document Name {filenumber}"
                from glob import glob
                from os.path import join, realpath

                files = [
                    name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))
                ]
                name = files[filenumber - 1]
                name = os.path.split(name)[-1]
                name = name.split(".")[0]
                name = name.upper()[:8]

                respond = bytes(array[:4]) + bytes(name, "utf8") + b"\00"
                respond_desc = f"Document {filenumber} Named: {name}"
            elif array[1] == 0x02:
                self.saving = True
                desc = "File transfer"
            elif array[1] == 0x03:
                filenumber = self.parse_filenumber(array[2:4])

                from glob import glob
                from os.path import join, realpath

                files = [
                    name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))
                ]
                name = files[filenumber - 1]
                try:
                    with open(name, "rb") as f:
                        self.write(BytesIO(self.unswizzle(f.read())))
                except IOError:
                    pass
                desc = f"Start Select Document {filenumber}"
            elif array[1] == 0x04:
                filenumber = self.parse_filenumber(array[2:4])
                desc = f"Calculate Document Time {filenumber}"
        elif array[0] == 0xEA:
            index = array[1]  # TODO: Index error raised here.
            desc = f"Array Start ({index})"
        elif array[0] == 0xEB:
            desc = "Array End"
        elif array[0] == 0xF0:
            desc = "Ref Point Set"
        elif array[0] == 0xF1:
            if array[1] == 0x00:
                index = array[2]
                desc = f"Element Max Index ({index})"
            elif array[1] == 0x01:
                index = array[2]
                desc = f"Element Name Max Index({index})"
            elif array[1] == 0x02:
                enable = array[2]
                desc = f"Enable Block Cutting ({enable})"
            elif array[1] == 0x03:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Display Offset ({c_x},{c_y})"
            elif array[1] == 0x04:
                enable = array[2]
                desc = f"Feed Auto Calc ({enable})"
            elif array[1] == 0x20:
                desc = f"Unknown ({array[2]},{array[3]})"
        elif array[0] == 0xF2:
            if array[1] == 0x00:
                index = array[2]
                desc = f"Element Index ({index})"
            if array[1] == 0x01:
                index = array[2]
                desc = f"Element Name Index ({index})"
            if array[1] == 0x02:
                name = bytes(array[2:12])
                desc = f"Element Name ({str(name)})"
            if array[1] == 0x03:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Element Array Min Point ({c_x},{c_y})"
            if array[1] == 0x04:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Element Array Max Point ({c_x},{c_y})"
            if array[1] == 0x05:
                v0 = self.decode14(array[2:4])
                v1 = self.decode14(array[4:6])
                v2 = self.decode14(array[6:8])
                v3 = self.decode14(array[8:10])
                v4 = self.decode14(array[10:12])
                v5 = self.decode14(array[12:14])
                v6 = self.decode14(array[14:16])
                desc = f"Element Array ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            if array[1] == 0x06:
                c_x = self.abscoord(array[2:7]) * UNITS_PER_uM
                c_y = self.abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Element Array Add ({c_x},{c_y})"
            if array[1] == 0x07:
                index = array[2]
                desc = f"Element Array Mirror ({index})"
        else:
            desc = "Unknown Command!"

        self.ruida_describe(f"{str(bytes(array).hex())}\t{desc}")
        self.ruida_channel(f"--> {str(bytes(array).hex())}\t({desc})")
        if respond is not None:
            self.reply(respond, desc=respond_desc)

    def mem_lookup(self, mem) -> Tuple[str, Union[int, bytes]]:
        if mem == 0x0002:
            return "Laser Info", 0  #
        if mem == 0x0003:
            return "Machine Def", 0  #
        if mem == 0x0004:
            return "IOEnable", 0  # 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, bits
        if mem == 0x0005:
            return "G0 Velocity", 200000  # 200 mm/s
        if mem == 0x000B:
            return "Eng Facula", 800  # 80%
        if mem == 0x000C:
            return "Home Velocity", 20000  # 20mm/s
        if mem == 0x000E:
            return "Eng Vert Velocity", 100000  # 100 mm/s
        if mem == 0x0010:
            return "System Control Mode", 0
        if mem == 0x0011:
            return "Laser PWM Frequency 1", 0
        if mem == 0x0012:
            return "Laser Min Power 1", 0
        if mem == 0x0013:
            return "Laser Max Power 1", 0
        if mem == 0x0016:
            return "Laser Attenuation", 0
        if mem == 0x0017:
            return "Laser PWM Frequency 2", 0
        if mem == 0x0018:
            return "Laser Min Power 2", 0
        if mem == 0x0019:
            return "Laser Max Power 2", 0
        if mem == 0x001A:
            return "Laser Standby Frequency 1", 0
        if mem == 0x001B:
            return "Laser Standby Pulse 1", 0
        if mem == 0x001C:
            return "Laser Standby Frequency 2", 0
        if mem == 0x001D:
            return "Laser Standby Pulse 2", 0
        if mem == 0x001E:
            return "Auto Type Space", 0
        if mem == 0x001F:
            return "TriColor", 0
        if mem == 0x0020:
            return "Axis Control Para 1", 0x4000  # True
        if mem == 0x0021:
            return "Axis Precision 1", 0
        if mem == 0x0023:
            return "Axis Max Velocity 1", 0
        if mem == 0x0024:
            return "Axis Start Velocity 1", 0
        if mem == 0x0025:
            return "Axis Max Acc 1", 0
        if mem == 0x0026:
            return "Axis Range 1, Get Frame X", 320000
        if mem == 0x0027:
            return "Axis Btn Start Velocity 1", 0
        if mem == 0x0028:
            return "Axis Btn Acc 1", 0
        if mem == 0x0029:
            return "Axis Estp Acc 1", 0
        if mem == 0x002A:
            return "Axis Home Offset 1", 0
        if mem == 0x002B:
            return "Axis Backlash 1", 0  # 0mm

        if mem == 0x0030:
            return "Axis Control Para 2", 0x4000  # True
        if mem == 0x0031:
            return "Axis Precision 2", 0
        if mem == 0x0033:
            return "Axis Max Velocity 2", 0
        if mem == 0x0034:
            return "Axis Start Velocity 2", 0
        if mem == 0x0035:
            return "Axis Max Acc 2", 0
        if mem == 0x0036:
            return "Axis Range 2, Get Frame Y", 220000
        if mem == 0x0037:
            return "Axis Btn Start Velocity 2", 0
        if mem == 0x0038:
            return "Axis Btn Acc 2", 0
        if mem == 0x0039:
            return "Axis Estp Acc 2", 0
        if mem == 0x003A:
            return "Axis Home Offset 2", 0
        if mem == 0x003B:
            return "Axis Backlash 2", 0  # 0 mm

        if mem == 0x0040:
            return "Axis Control Para 3", 0  # False
        if mem == 0x0041:
            return "Axis Precision 3", 0
        if mem == 0x0043:
            return "Axis Max Velocity 3", 0
        if mem == 0x0044:
            return "Axis Start Velocity 3", 0
        if mem == 0x0045:
            return "Axis Max Acc 3", 0
        if mem == 0x0046:
            return "Axis Range 3, Get Frame Z", 0
        if mem == 0x0047:
            return "Axis Btn Start Velocity 3", 0
        if mem == 0x0048:
            return "Axis Btn Acc 3", 0
        if mem == 0x0049:
            return "Axis Estp Acc 3", 0
        if mem == 0x004A:
            return "Axis Home Offset 3", 0
        if mem == 0x004B:
            return "Axis Backlash 3", 0

        if mem == 0x0050:
            return "Axis Control Para 4", 0  # False
        if mem == 0x0051:
            return "Axis Precision 4", 0
        if mem == 0x0053:
            return "Axis Max Velocity 4", 0
        if mem == 0x0054:
            return "Axis Start Velocity 4", 0
        if mem == 0x0055:
            return "Axis Max Acc 4", 0
        if mem == 0x0056:
            return "Axis Range 4, Get Frame U", 0
        if mem == 0x0057:
            return "Axis Btn Start Velocity 4", 0
        if mem == 0x0058:
            return "Axis Btn Acc 4", 0
        if mem == 0x0059:
            return "Axis Estp Acc 4", 0
        if mem == 0x005A:
            return "Axis Home Offset 4", 0
        if mem == 0x005B:
            return "Axis Backlash 4", 0

        if mem == 0x0060:
            return "Machine Type", 0

        if mem == 0x0063:
            return "Laser Min Power 3", 0
        if mem == 0x0064:
            return "Laser Max Power 3", 0
        if mem == 0x0065:
            return "Laser PWM Frequency 3", 0
        if mem == 0x0066:
            return "Laser Standby Frequency 3", 0
        if mem == 0x0067:
            return "Laser Standby Pulse 3", 0

        if mem == 0x0068:
            return "Laser Min Power 4", 0
        if mem == 0x0069:
            return "Laser Max Power 4", 0
        if mem == 0x006A:
            return "Laser PWM Frequency 4", 0
        if mem == 0x006B:
            return "Laser Standby Frequency 4", 0
        if mem == 0x006C:
            return "Laser Standby Pulse 4", 0

        if mem == 0x006D:
            return "Laser Min Power 5", 0
        if mem == 0x006E:
            return "Laser Max Power 5", 0
        if mem == 0x006F:
            return "Laser PWM Frequency 5", 0
        if mem == 0x0070:
            return "Laser Standby Frequency 5", 0
        if mem == 0x0071:
            return "Laser Standby Pulse 5", 0

        if mem == 0x0072:
            return "Laser Min Power 6", 0
        if mem == 0x0073:
            return "Laser Max Power 6", 0
        if mem == 0x0074:
            return "Laser PWM Frequency 6", 0
        if mem == 0x0075:
            return "Laser Standby Frequency 6", 0
        if mem == 0x0076:
            return "Laser Standby Pulse 6", 0
        if mem == 0x0077:
            return "Auto Type Space 2", 0
        if mem == 0x0077:
            return "Auto Type Space 3", 0
        if mem == 0x0078:
            return "Auto Type Space 4", 0
        if mem == 0x0079:
            return "Auto Type Space 5", 0
        if mem == 0x007A:
            return "Auto Type Space 6", 0
        if mem == 0x0080:
            return "RD-UNKNOWN 2", 0
        if mem == 0x0090:
            return "RD-UNKNOWN 3", 0
        if mem == 0x00A0:
            return "RD-UNKNOWN 4", 0
        if mem == 0x00B0:
            return "RD-UNKNOWN 5", 0
        if mem == 0x0C0:
            return "Offset 8 Start", 0
        if mem == 0x0C1:
            return "Offset 8 End", 0
        if mem == 0x00C2:
            return "Offset 9 Start", 0
        if mem == 0x00C3:
            return "Offset 9 End", 0
        if mem == 0x00C4:
            return "Offset 10 Start", 0
        if mem == 0x00C5:
            return "Offset 10 End", 0
        if mem == 0x00C6:
            return "Offset 7 Start", 0
        if mem == 0x0C7:
            return "Offset 7 End", 0

        if mem == 0x00C8:
            return "Axis Home Velocity 1", 0
        if mem == 0x00C9:
            return "Axis Home Velocity 2", 0
        if mem == 0x00CA:
            return "Margin 1", 0
        if mem == 0x00CB:
            return "Margin 2", 0
        if mem == 0x00CC:
            return "Margin 3", 0
        if mem == 0x00CD:
            return "Margin 4", 0
        if mem == 0x00CE:
            return "VWheelRatio", 0
        if mem == 0x00CF:
            return "VPunchRatio", 0
        if mem == 0x00D8:
            return "VSlotRatio", 0
        if mem == 0x00D0:
            return "In Hale Zone", 0
        if mem == 0x00D9:
            return "VSlot Share Home Offset", 0
        if mem == 0x00DA:
            return "VPunch Share Home Offset", 0
        if mem == 0x00E7:
            return "VWheel Share Home Offset", 0
        if mem == 0x0100:
            return "System Settings", 0  # bits 2,2,1,1,1,1,1,1,1,1,1
        if mem == 0x0101:
            return "Turn Velocity", 20000  # 20 m/s
        if mem == 0x0102:
            return "Syn Acc", 3000000  # 3000 mm/s2
        if mem == 0x0103:
            return "G0 Delay", 0  # 0 ms
        if mem == 0x0104:
            return "Scan Step Factor", 0
        if mem == 0x0115:
            return "Dock Point X", 0
        if mem == 0x0116:
            return "Dock Point Y", 0
        if mem == 0x0105:
            return "User Para 5", 0
        if mem == 0x0107:
            return "Feed Delay After", 0  # 0 s
        if mem == 0x0108:
            return "User Key Fast Velocity", 0
        if mem == 0x0109:
            return "Turn Acc", 400000  # 400 mm/s
        if mem == 0x010A:
            return "G0 Acc", 3000000  # 3000 mm/s2
        if mem == 0x010B:
            return "Feed Delay Prior", 0  # 0 ms
        if mem == 0x010C:
            return "Manual Distance", 0
        if mem == 0x010D:
            return "Shut Down Delay", 0
        if mem == 0x010E:
            return "Focus Depth", 5000  # 5mm
        if mem == 0x010F:
            return "Go Scale Blank", 0  # 0 mm
        if mem == 0x0117:
            return "Array Feed Repay", 0  # 0mm
        if mem == 0x0117:
            return "Rotate On Delay", 0
        if mem == 0x0119:
            return "Rotate Off Delay", 0
        if mem == 0x011A:
            return "Acc Ratio", 100  # 100%
        if mem == 0x011B:
            return "Turn Ratio", 100  # 100% (speed factor)
        if mem == 0x011C:
            return "Acc G0 Ratio", 100  # 100%
        if mem == 0x011F:
            return "Rotate Pulse", 0
        if mem == 0x0121:
            return "Rotate D", 0
        if mem == 0x0122:
            return "Eng Facula Replay", 0
        if mem == 0x0124:
            return "X Min Eng Velocity", 10000  # 10mm/s
        if mem == 0x0125:
            return "X Eng Acc", 10000000  # 10000 m/s
        if mem == 0x0126:
            return "User Para 1", 0
        if mem == 0x0128:
            return "Z Home Velocity", 0
        if mem == 0x0129:
            return "Z Work Velocity", 0
        if mem == 0x012A:
            return "Z G0 Velocity", 0
        if mem == 0x012B:
            return "Union Home Distance", 0
        if mem == 0x012C:
            return "U Home Velocity", 0
        if mem == 0x012D:
            return "U Work Velocity", 0  # Axis Dock Position Other
        if mem == 0x012E:
            return "Feed Repay", 0
        if mem == 0x0131:
            return "Manual Fast Speed", 100000  # 100 mm/s
        if mem == 0x0132:
            return "Manual Slow Speed", 10000  # 10 mm/s
        if mem == 0x0134:
            return "Y Minimum Eng Velocity", 10000  # 10mm/s
        if mem == 0x0135:
            return "Y Eng Acc", 3000000  # 3000 mm/s
        if mem == 0x0137:
            return "Eng Acc Ratio", 100  # Engraving factor 100%
        if mem == 0x0138:
            return "Sts Ahead Time", 0
        if mem == 0x0139:
            return "Repeat Delay", 0
        if mem == 0x013B:
            return "User Para 3", 0
        if mem == 0x013D:
            return "User Para 2", 0
        if mem == 0x013F:
            return "User Para 4", 0  # Pressure Monitor Delay
        if mem == 0x0140:
            return "Axis Home Velocity 3", 0
        if mem == 0x0141:
            return "Axis Work Velocity 3", 0
        if mem == 0x0142:
            return "Axis Home Velocity 4", 0
        if mem == 0x0143:
            return "Axis Work Velocity 4", 0
        if mem == 0x0144:
            return "Axis Home Velocity 5", 0
        if mem == 0x0145:
            return "Axis Work Velocity 5", 0
        if mem == 0x0146:
            return "Axis Home Velocity 6", 0
        if mem == 0x0147:
            return "Axis Work Velocity 6", 0
        if mem == 0x0148:
            return "Axis Home Velocity 7", 0
        if mem == 0x0149:
            return "Axis Work Velocity 7", 0
        if mem == 0x014A:
            return "Axis Home Velocity 8", 0
        if mem == 0x014B:
            return "Axis Work Velocity 8", 0
        if mem == 0x014C:
            return "Laser Reset Time", 0
        if mem == 0x014D:
            return "Laser Start Distance", 0
        if mem == 0x014E:
            return "Z Pen Up Pos", 0  # units 0.001
        if mem == 0x014F:
            return "Z Pen Down Pos", 0  # units 0.001
        if mem == 0x0150:
            return "Offset 1 Start", 0
        if mem == 0x0151:
            return "Offset 1 End", 0
        if mem == 0x0152:
            return "Offset 2 Start", 0
        if mem == 0x0153:
            return "Offset 2 End", 0
        if mem == 0x0154:
            return "Offset 3 Start", 0
        if mem == 0x0155:
            return "Offset 3 End", 0
        if mem == 0x0156:
            return "Offset 6 Start", 0
        if mem == 0x0157:
            return "Offset 6 End", 0
        if mem == 0x0158:
            return "Offset 4 Start", 0
        if mem == 0x0159:
            return "Offset 4 End", 0
        if mem == 0x015A:
            return "Offset 5 Start", 0
        if mem == 0x015B:
            return "Offset 5 End", 0
        if mem == 0x15C:
            return "Delay 6 On", 0
        if mem == 0x15D:
            return "Delay 6 Off", 0
        if mem == 0x15E:
            return "Delay 7 On", 0
        if mem == 0x15F:
            return "Delay 7 Off", 0
        if mem == 0x0160:
            return "Inhale On Delay", 0  # Delay 8
        if mem == 0x0161:
            return "Inhale Off Delay", 0  # Delay 8
        if mem == 0x162:
            return "Delay 5 On", 0
        if mem == 0x163:
            return "Delay 5 Off", 0
        if mem == 0x164:
            return "Delay 2 On", 0
        if mem == 0x165:
            return "Delay 2 Off", 0
        if mem == 0x0166:
            return "VSample Distance", 0
        if mem == 0x016D:
            return "VUp Angle", 0
        if mem == 0x016E:
            return "VRotatePulse", 0
        if mem == 0x177:
            return "Delay 9 On", 0
        if mem == 0x178:
            return "Delay 9 Off", 0
        if mem == 0x0169:
            return "Offset 11 Start", 0
        if mem == 0x016A:
            return "Offset 11 End", 0
        if mem == 0x16B:
            return "Tool Up Pos 4", 0
        if mem == 0x16C:
            return "Tool Down Pos 4", 0
        if mem == 0x170:
            return "Delay 1 On", 0
        if mem == 0x171:
            return "VCorner Precision", 0
        if mem == 0x172:
            return "Delay 3 On", 0
        if mem == 0x173:
            return "Delay 4 Off", 0
        if mem == 0x174:
            return "Delay 4 On", 0
        if mem == 0x175:
            return "Delay 1 Off", 0
        if mem == 0x176:
            return "Delay 3 Off", 0
        if mem == 0x0177:
            return "Idle Long Distance", 0
        if mem == 0x178:
            return "Tool Up Pos 3", 0
        if mem == 0x179:
            return "Tool Down Pos 3", 0
        if mem == 0x17A:
            return "Tool Up Pos 2", 0
        if mem == 0x17B:
            return "Tool Down Pos 2", 0
        if mem == 0x017C:
            return "Punch Rotate Delay", 0
        if mem == 0x017D:
            return "VSlot Angle", 0
        if mem == 0x017F:
            return "Tool Up Delay", 0
        if mem == 0x017E:
            return "VTool Rotate Limit", 0
        if mem == 0x0180:
            return "Card Language", 0
        if 0x181 <= mem <= 0x187:
            return f"PC Lock {mem - 0x181}", 0
        if mem == 0x0188:
            return "User Key Slow Velocity", 0
        if mem == 0x0189:
            return "MachineID 2", 0
        if mem == 0x018A:
            return "MachineID 3", 0
        if mem == 0x018B:
            return "MachineID 4", 0
        if mem == 0x018C:
            return "Blow On Delay", 0
        if mem == 0x018D:
            return "Blow Off Delay", 0
        if mem == 0x018F:
            return "User Para 6, Blower", 0
        if mem == 0x0190:
            return "Jet Time", 0
        if mem == 0x0190:
            return "Color Mark Head Max Distance", 0
        if mem == 0x0191:
            return "Color Mark Head Distance", 0
        if mem == 0x0192:
            return "Color Mark Mark Distance", 0
        if mem == 0x0193:
            return "Color Mark Camera Distance", 0  # JetOffset = 0x193 to 0x194
        if mem == 0x0194:
            return "Color Mark Sensor Offset2", 0
        if mem == 0x0195:
            return "Cylinder Down Delay", 0
        if mem == 0x0196:
            return "Cylinder Up Delay", 0
        if mem == 0x0197:
            return "Press Down Delay", 0
        if mem == 0x0198:
            return "Press Up Delay", 0
        if mem == 0x0199:
            return "Drop Position Start", 0
        if mem == 0x019A:
            return "Drop Position End", 0
        if mem == 0x019B:
            return "Drop Interval", 0
        if mem == 0x019C:
            return "Drop Time", 0
        if mem == 0x019D:
            return "Sharpen Delay On", 0
        if mem == 0x019E:
            return "Sharpen Delay Off", 0
        if mem == 0x019F:
            return "Sharpen Time Limit", 0
        if mem == 0x01A0:
            return "Sharpen Travel Limit", 0
        if mem == 0x01A1:
            return "Work End Time", 0
        if mem == 0x01A2:
            return "Color Mark Offset", 0
        if mem == 0x01A3:
            return "Color Mark Count", 0
        if mem == 0x01A4:
            return "Wheel Press Compensation", 0  # Protect IO Status
        if mem == 0x01A5:
            return "Color Mark Filter Length", 0
        if mem == 0x01A6:
            return "VBlow Back On Delay", 0
        if mem == 0x01A7:
            return "VBlow Back Off Delay", 0
        if mem == 0x01AC:
            return "Y U Safe Distance", 0
        if mem == 0x01AD:
            return "Y U Home Distance", 0
        if mem == 0x01AE:
            return "VTool Preset Position X", 0
        if mem == 0x01AF:
            return "VTool Preset Position Y", 0
        if mem == 0x01B1:
            return "VTool Preset Compensation", 0
        if mem == 0x01B2:
            return "VTool Preset Cur Depth", 0
        if mem == 0x0200:
            return "Machine Status", self.state  # 22 ok, 23 paused. 21 running.
        if mem == 0x0201:
            return "Total Open Time (s)", 0
        if mem == 0x0202:
            return "Total Work Time (s)", 0
        if mem == 0x0203:
            return "Total Work Number", 0
        if mem == 0x0205:
            from glob import glob
            from os.path import join, realpath

            files = [name for name in glob(join(realpath(get_safe_path(".")), "*.rd"))]
            v = len(files)
            return "Total Doc Number", v
        if mem == 0x0206:
            from os.path import realpath
            from shutil import disk_usage

            total, used, free = disk_usage(realpath(get_safe_path(".")))
            v = min(total, 100000000)  # Max 100 megs.
            return "Flash Space", v
        if mem == 0x0207:
            from os.path import realpath
            from shutil import disk_usage

            total, used, free = disk_usage(realpath(get_safe_path(".")))
            v = min(free, 100000000)  # Max 100 megs.
            return "Flash Space", v
        if mem == 0x0208:
            return "Previous Work Time", 0
        if mem == 0x0211:
            return "Total Laser Work Time", 0
        if mem == 0x0212:
            return "File Custom Flag / Feed Info", 0
        if mem == 0x0217:
            return "Total Laser Work Time 2", 0
        if mem == 0x0218:
            # OEM PULSE ENERGY
            return "Total Laser Work Time 3", 0
        if mem == 0x0219:
            # OEM SET CURRENT
            return "Total Laser Work Time 4", 0
        if mem == 0x021A:
            # OEM SET FREQUENCY
            return "Total Laser Work Time 5", 0
        if mem == 0x021F:
            return "Ring Number", 0
        if mem == 0x0221:
            if self.device is not None:
                dev_x, dev_y = self.device.current
                self.x = int(dev_x / UNITS_PER_uM)
            x = int(self.x)
            return "Axis Preferred Position 1, Pos X", x
        if mem == 0x0223:
            return "X Total Travel (m)", 0
        if mem == 0x0224:
            return "Position Point 0", 0
        if mem == 0x0231:
            if self.device is not None:
                dev_x, dev_y = self.device.current
                self.y = int(dev_y / UNITS_PER_uM)
            y = int(self.y)
            return "Axis Preferred Position 2, Pos Y", y
        if mem == 0x0233:
            return "Y Total Travel (m)", 0
        if mem == 0x0234:
            return "Position Point 1", 0
        if mem == 0x0241:
            z = int(self.z)
            return "Axis Preferred Position 3, Pos Z", z
        if mem == 0x0243:
            return "Z Total Travel (m)", 0
        if mem == 0x0251:
            u = int(self.u)
            return "Axis Preferred Position 4, Pos U", u
        if mem == 0x0253:
            return "U Total Travel (m)", 0
        if mem == 0x025A:
            a = int(self.a)
            return "Axis Preferred Position 5, Pos A", a
        if mem == 0x025B:
            b = int(self.b)
            return "Axis Preferred Position 6, Pos B", b
        if mem == 0x025C:
            c = int(self.c)
            return "Axis Preferred Position 7, Pos C", c
        if mem == 0x025D:
            d = int(self.d)
            return "Axis Preferred Position 8, Pos D", d
        if mem == 0x0260:
            return "DocumentWorkNum", 0
        if 0x0261 <= mem < 0x02C4:
            # Unsure if this is where the document numbers end.
            return "Document Number", mem - 0x260
        if mem == 0x02C4:
            return "Read Scan Backlash Flag", 0
        if mem == 0x02C5:
            return "Read Scan Backlash 1", 0
        if mem == 0x02D5:
            return "Read Scan Backlash 2", 0
        if mem == 0x02FE:
            return "Card ID", 0x65006500  # RDC6442G
        if mem == 0x02FF:
            return "Mainboard Version", b"MEERK40T\x00"
        if mem == 0x0313:
            return "Material Thickness", 0
        if mem == 0x031C:
            return "File Fault", 0  # Error counter.
        if mem == 0x0320:
            return "File Total Length", 0
        if mem == 0x0321:
            return "File Progress Len", 0
        if mem == 0x033B:
            return "Read Process Feed Length", 0
        if mem == 0x0340:
            return "Stop Time", 0
        if 0x0391 <= mem < 0x0420:
            return f"Time for File {mem - 0x00390} to Run", 100
        if mem == 0x0591:
            return "Card Lock", 0  # 0x55aaaa55
        if mem == 0x05C0:
            return "Laser Life", 0
        if 0x05C0 <= mem < 0x600:
            pass
        return "Unknown", 0

    def unswizzle(self, data):
        array = list()
        for b in data:
            array.append(self.lut_unswizzle[b])
        return bytes(array)

    def swizzle(self, data):
        array = list()
        for b in data:
            array.append(self.lut_swizzle[b])
        return bytes(array)

    @staticmethod
    def swizzle_byte(b, magic):
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        b ^= magic
        b = (b + 1) & 0xFF
        return b

    @staticmethod
    def unswizzle_byte(b, magic):
        b = (b - 1) & 0xFF
        b ^= magic
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        return b

    @staticmethod
    def swizzles_lut(magic):
        lut_swizzle = [RuidaEmulator.swizzle_byte(s, magic) for s in range(256)]
        lut_unswizzle = [RuidaEmulator.unswizzle_byte(s, magic) for s in range(256)]
        return lut_swizzle, lut_unswizzle

    @staticmethod
    def decode_bytes(data, magic=0x88):
        lut_swizzle, lut_unswizzle = RuidaEmulator.swizzles_lut(magic)
        array = list()
        for b in data:
            array.append(lut_unswizzle[b])
        return bytes(array)

    @staticmethod
    def encode_bytes(data, magic=0x88):
        lut_swizzle, lut_unswizzle = RuidaEmulator.swizzles_lut(magic)
        array = list()
        for b in data:
            array.append(lut_swizzle[b])
        return bytes(array)
