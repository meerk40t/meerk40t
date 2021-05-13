import os
from io import BytesIO

from ...core.cutcode import CutCode, LaserSettings, LineCut
from ...kernel import Module
from ...svgelements import Color, Point
from ..lasercommandconstants import COMMAND_PLOT, COMMAND_PLOT_START

STATE_ABORT = -1
STATE_DEFAULT = 0
STATE_CONCAT = 1
STATE_COMPACT = 2

"""
Ruida device interfacing. We do not send or interpret ruida code, but we can emulator ruidacode into cutcode and read
ruida files (*.rd) and turn them likewise into cutcode.
"""


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("load/RDLoader", RDLoader)
        kernel.register("emulator/ruida", RuidaEmulator)

        @kernel.console_option(
            "path", "p", type=str, default="/", help="Path of ruidaserver launch."
        )
        @kernel.console_option("spool", type=bool, action="store_true")
        @kernel.console_command("ruidaserver", help="activate the ruidaserver.")
        def ruidaserver(
            command, channel, _, spool=False, path=None, args=tuple(), **kwargs
        ):
            c = kernel.get_context(path if path is not None else "/")
            if c is None:
                return
            try:
                c.open_as("module/UDPServer", "ruidaserver", port=50200)
                c.open_as("module/UDPServer", "ruidajog", port=50207)
                channel(_("Ruida Data Server opened on port %d.") % 50200)
                channel(_("Ruida Jog Server opened on port %d.") % 50207)

                chan = "ruida"
                c.channel(chan).watch(kernel.channel("console"))
                channel(_("Watching Channel: %s") % chan)

                chan = "server"
                c.channel(chan).watch(kernel.channel("console"))
                channel(_("Watching Channel: %s") % chan)

                emulator = c.open("module/RuidaEmulator")
                c.channel("ruidaserver/recv").watch(emulator.checksum_write)
                c.channel("ruidajog/recv").watch(emulator.realtime_write)
                c.channel("ruida_reply").watch(c.channel("ruidaserver/send"))
                if spool:
                    emulator.spooler = c.spooler
                else:
                    emulator.elements = c.get_context("/").elements
                    # Output to elements
                    pass
            except OSError:
                channel(_("Server failed."))
            return


class RuidaEmulator(Module):
    def __init__(self, context, path):
        Module.__init__(self, context, path)

        self.cutcode = CutCode()
        # self.layer_settings = []
        self.settings = LaserSettings()
        self._use_set = None
        self.spooler = None
        self.elements = None

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.u = 0.0
        self.magic = 0x88  # 0x11 for the 634XG
        # Should automatically shift encoding if wrong.
        # self.magic = 0x38
        self.lut_swizzle = [self.swizzle_byte(s) for s in range(256)]
        self.lut_unswizzle = [self.unswizzle_byte(s) for s in range(256)]

        self.filename = ""
        self.power1_min = 0
        self.power1_max = 0
        self.power2_min = 0
        self.power2_max = 0

        self.ruida_channel = self.context.channel("ruida")
        self.ruida_reply = self.context.channel("ruida_reply")
        self.ruida_send = self.context.channel("ruida_send")
        self.ruida_describe = self.context.channel("ruida_desc")

        self.process_commands = True
        self.parse_lasercode = True
        self.in_file = False
        self.swizzle_mode = True

    def __repr__(self):
        return "Ruida(%s, %d cuts)" % (self.name, len(self.cutcode))

    def generate(self):
        for cutobject in self.cutcode:
            yield COMMAND_PLOT, cutobject
        yield COMMAND_PLOT_START

    @property
    def cutset(self):
        if self._use_set is None:
            self._use_set = LaserSettings(self.settings)
        return self._use_set

    @staticmethod
    def signed35(v):
        v &= 0x7FFFFFFFF
        if v > 0x3FFFFFFFF:
            return -0x800000000 + v
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
        return RuidaEmulator.decode35(data)

    @staticmethod
    def relcoord(data):
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
            self.ruida_reply(response)
        self.ruida_channel("<-- %s\t(%s)" % (response.hex(), desc))

    def checksum_write(self, sent_data):
        """
        This is a write with a checksum and swizzling. This is how the 50200 packets arrive and need to be processed.

        :param sent_data: Packet data.
        :return:
        """
        self.swizzle_mode = True

        data = sent_data[2:1472]
        checksum_check = (sent_data[0] & 0xFF) << 8 | sent_data[1] & 0xFF
        checksum_sum = sum(data) & 0xFFFF
        if len(sent_data) > 3:
            if self.magic != 0x88 and sent_data[2] == 0xD4:
                self.magic = 0x88
                self.lut_swizzle = [self.swizzle_byte(s) for s in range(256)]
                self.lut_unswizzle = [self.unswizzle_byte(s) for s in range(256)]
                self.ruida_channel("Setting magic to 0x88")
            if self.magic != 0x11 and sent_data[2] == 0x4B:
                self.magic = 0x11
                self.lut_swizzle = [self.swizzle_byte(s) for s in range(256)]
                self.lut_unswizzle = [self.unswizzle_byte(s) for s in range(256)]
                self.ruida_channel("Setting magic to 0x11")

        if checksum_check == checksum_sum:
            response = b"\xCC"
            self.reply(response, desc="Checksum match")
        else:
            response = b"\xCF"
            self.reply(
                response,
                desc="Checksum Fail (%d != %d)" % (checksum_sum, checksum_check),
            )
            self.ruida_channel("--> " + str(data.hex()))
            return
        self.write(BytesIO(self.unswizzle(data)))

    def realtime_write(self, bytes_to_write):
        """
        Real time commands are replied to and sent in realtime. For Ruida devices these are sent along udp 50207.

        :param bytes_to_write: bytes to write.
        :return:
        """
        self.swizzle_mode = False
        self.reply(b"\xCC")  # Clear ACK.
        self.write(BytesIO(bytes_to_write))

    def write(self, data):
        """
        Procedural commands sent in large data chunks. This can be through USB or UDP or a loaded file. These are
        expected to be unswizzled with the swizzle_mode set for the reply. Write will parse out the individual commands
        and send those to the command routine.

        :param data:
        :return:
        """
        for array in self.parse_commands(data):
            self.process(array)

    def process(self, array):
        """
        Parses an individual unswizzled ruida command, updating the emulator state.

        These commands can change the position, settings, speed, color, power, create elements, creates lasercode.
        :param array:
        :return:
        """
        um_per_mil = 25.4
        desc = ""
        respond = None
        respond_desc = None
        start_x = self.x
        start_y = self.y
        if array[0] < 0x80:
            self.ruida_channel("NOT A COMMAND: %d" % array[0])
            raise ValueError
        elif array[0] == 0x80:
            value = self.abscoord(array[2:7])
            if array[1] == 0x00:
                desc = "Axis X Move %f" % (value)
                self.x += value
            elif array[1] == 0x08:
                desc = "Axis Z Move %f" % (value)
                self.z += value
        elif array[0] == 0x88:  # 0b10001000 11 characters.
            self.x = self.abscoord(array[1:6])
            self.y = self.abscoord(array[6:11])
            desc = "Move Absolute (%f, %f)" % (self.x, self.y)
        elif array[0] == 0x89:  # 0b10001001 5 characters
            dx = self.relcoord(array[1:3])
            dy = self.relcoord(array[3:5])
            self.x += dx
            self.y += dy
            desc = "Move Relative (%f, %f)" % (dx, dy)
        elif array[0] == 0x8A:  # 0b10101010 3 characters
            dx = self.relcoord(array[1:3])
            self.x += dx
            desc = "Move Horizontal Relative (%f)" % (dx)
        elif array[0] == 0x8B:  # 0b10101011 3 characters
            dy = self.relcoord(array[1:3])
            self.y += dy
            desc = "Move Vertical Relative (%f)" % (dy)
        elif array[0] == 0xA0:
            value = self.abscoord(array[2:7])
            if array[1] == 0x00:
                desc = "Axis Y Move %f" % (value)
            elif array[1] == 0x08:
                desc = "Axis U Move %f" % (value)
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
                    desc = "Interface +X %s" % key
                elif array[2] == 0x01:
                    desc = "Interface -X %s" % key
                if array[2] == 0x03:
                    desc = "Interface +Y %s" % key
                elif array[2] == 0x04:
                    desc = "Interface -Y %s" % key
                if array[2] == 0x0A:
                    desc = "Interface +Z %s" % key
                elif array[2] == 0x0B:
                    desc = "Interface -Z %s" % key
                if array[2] == 0x0C:
                    desc = "Interface +U %s" % key
                elif array[2] == 0x0D:
                    desc = "Interface -U %s" % key
                elif array[2] == 0x05:
                    desc = "Interface Pulse %s" % key
                elif array[2] == 0x11:
                    desc = "Interface Speed"
                elif array[2] == 0x06:
                    desc = "Interface Start/Pause"
                elif array[2] == 0x09:
                    desc = "Interface Stop"
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
            self.cutcode.append(
                LineCut(
                    Point(start_x / um_per_mil, start_y / um_per_mil),
                    Point(self.x / um_per_mil, self.y / um_per_mil),
                    settings=self.cutset,
                )
            )
            desc = "Cut Absolute (%f, %f)" % (self.x, self.y)
        elif array[0] == 0xA9:  # 0b10101001 5 characters
            dx = self.relcoord(array[1:3])
            dy = self.relcoord(array[3:5])
            self.x += dx
            self.y += dy
            self.cutcode.append(
                LineCut(
                    Point(start_x / um_per_mil, start_y / um_per_mil),
                    Point(self.x / um_per_mil, self.y / um_per_mil),
                    settings=self.cutset,
                )
            )
            desc = "Cut Relative (%f, %f)" % (dx, dy)
        elif array[0] == 0xAA:  # 0b10101010 3 characters
            dx = self.relcoord(array[1:3])
            self.x += dx
            self.cutcode.append(
                LineCut(
                    Point(start_x / um_per_mil, start_y / um_per_mil),
                    Point(self.x / um_per_mil, self.y / um_per_mil),
                    settings=self.cutset,
                )
            )
            desc = "Cut Horizontal Relative (%f)" % (dx)
        elif array[0] == 0xAB:  # 0b10101011 3 characters
            dy = self.relcoord(array[1:3])
            self.y += dy
            self.cutcode.append(
                LineCut(
                    Point(start_x / um_per_mil, start_y / um_per_mil),
                    Point(self.x / um_per_mil, self.y / um_per_mil),
                    settings=self.cutset,
                )
            )
            desc = "Cut Vertical Relative (%f)" % (dy)
        elif array[0] == 0xC7:
            v0 = self.parse_power(array[1:3])
            desc = "Imd Power 1 (%f)" % v0
        elif array[0] == 0xC2:
            v0 = self.parse_power(array[1:3])
            desc = "Imd Power 3 (%f)" % v0
        elif array[0] == 0xC0:
            v0 = self.parse_power(array[1:3])
            desc = "Imd Power 2 (%f)" % v0
        elif array[0] == 0xC3:
            v0 = self.parse_power(array[1:3])
            desc = "Imd Power 4 (%f)" % v0
        elif array[0] == 0xC8:
            v0 = self.parse_power(array[1:3])
            desc = "End Power 1 (%f)" % v0
        elif array[0] == 0xC4:
            v0 = self.parse_power(array[1:3])
            desc = "End Power 3 (%f)" % v0
        elif array[0] == 0xC1:
            v0 = self.parse_power(array[1:3])
            desc = "End Power 2 (%f)" % v0
        elif array[0] == 0xC5:
            v0 = self.parse_power(array[1:3])
            desc = "End Power 4 (%f)" % v0
        elif array[0] == 0xC6:
            if array[1] == 0x01:
                power = self.parse_power(array[2:4])
                desc = "Power 1 min=%f" % (power)
                self.power1_min = power
            elif array[1] == 0x02:
                power = self.parse_power(array[2:4])
                desc = "Power 1 max=%f" % (power)
                self.power1_max = power
            elif array[1] == 0x05:
                power = self.parse_power(array[2:4])
                desc = "Power 3 min=%f" % (power)
            elif array[1] == 0x06:
                power = self.parse_power(array[2:4])
                desc = "Power 3 max=%f" % (power)
            elif array[1] == 0x07:
                power = self.parse_power(array[2:4])
                desc = "Power 4 min=%f" % (power)
            elif array[1] == 0x08:
                power = self.parse_power(array[2:4])
                desc = "Power 4 max=%f" % (power)
            elif array[1] == 0x10:
                interval = self.parse_time(array[2:7])
                desc = "Laser Interval %fms" % (interval)
            elif array[1] == 0x11:
                interval = self.parse_time(array[2:7])
                desc = "Add Delay %fms" % (interval)
            elif array[1] == 0x12:
                interval = self.parse_time(array[2:7])
                desc = "Laser On Delay %fms" % (interval)
            elif array[1] == 0x13:
                interval = self.parse_time(array[2:7])
                desc = "Laser Off Delay %fms" % (interval)
            elif array[1] == 0x15:
                interval = self.parse_time(array[2:7])
                desc = "Laser On2 %fms" % interval
            elif array[1] == 0x16:
                interval = self.parse_time(array[2:7])
                desc = "Laser Off2 %fms" % interval
            elif array[1] == 0x21:
                power = self.parse_power(array[2:4])
                desc = "Power 2 min=%f" % power
                self.power2_min = power
            elif array[1] == 0x22:
                power = self.parse_power(array[2:4])
                desc = "Power 2 max=%f" % power
                self.power2_max = power
            elif array[1] == 0x31:
                part = array[2]
                self.power1_min = self.parse_power(array[3:5])
                desc = "%d, Power 1 Min=(%f)" % (part, self.power1_min)
            elif array[1] == 0x32:
                part = array[2]
                self.power1_max = self.parse_power(array[3:5])
                desc = "%d, Power 1 Max=(%f)" % (part, self.power1_min)
            elif array[1] == 0x35:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = "%d, Power 3 Min (%f)" % (part, power)
            elif array[1] == 0x36:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = "%d, Power 3 Max (%f)" % (part, power)
            elif array[1] == 0x37:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = "%d, Power 4 Min (%f)" % (part, power)
            elif array[1] == 0x38:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = "%d, Power 4 Max (%f)" % (part, power)
            elif array[1] == 0x41:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = "%d, Power 2 Min (%f)" % (part, power)
            elif array[1] == 0x42:
                part = array[2]
                power = self.parse_power(array[3:5])
                desc = "%d, Power 2 Max (%f)" % (part, power)
            elif array[1] == 0x50:
                power = self.parse_power(array[2:4])
                desc = "Through Power 1 (%f)" % (power)
            elif array[1] == 0x51:
                power = self.parse_power(array[2:4])
                desc = "Through Power 2 (%f)" % (power)
            elif array[1] == 0x55:
                power = self.parse_power(array[2:4])
                desc = "Through Power 3 (%f)" % (power)
            elif array[1] == 0x56:
                power = self.parse_power(array[2:4])
                desc = "Through Power 4 (%f)" % (power)
            elif array[1] == 0x60:
                laser = array[2]
                part = array[3]
                frequency = self.parse_frequency(array[4:9])
                desc = "%d, Laser %d, Frequency (%f)" % (part, laser, frequency)
        elif array[0] == 0xC9:
            if array[1] == 0x02:
                speed = self.parse_speed(array[2:7])
                desc = "Speed Laser 1 %fmm/s" % (speed)
                self.settings.speed = speed
                self._use_set = None
            elif array[1] == 0x03:
                speed = self.parse_speed(array[2:7])
                desc = "Axis Speed %fmm/s" % (speed)
            elif array[1] == 0x04:
                part = array[2]
                speed = self.parse_speed(array[3:8])
                self.settings.speed = speed
                self._use_set = None
                desc = "%d, Speed %fmm/s" % (part, speed)
            elif array[1] == 0x05:
                speed = self.parse_speed(array[2:7]) / 1000.0
                desc = "Force Eng Speed %fmm/s" % (speed)
            elif array[1] == 0x06:
                speed = self.parse_speed(array[2:7]) / 1000.0
                desc = "Axis Move Speed %fmm/s" % (speed)
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
                desc = "%d, Layer Number" % (part)
            elif array[1] == 0x03:
                desc = "EnLaserTube Start"
            elif array[1] == 0x04:
                value = array[2]
                desc = "X Sign Map %d" % (value)
            elif array[1] == 0x05:
                c = RuidaEmulator.decodeu35(array[2:7])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.color = c.hex
                self.settings.line_color = Color.rgb_to_int(r, g, b)
                self._use_set = None
                desc = "Layer Color %s" % str(self.color)
            elif array[1] == 0x06:
                part = array[2]
                c = RuidaEmulator.decodeu35(array[3:8])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.color = c.hex
                desc = "%d, Color %s" % (part, self.color)
            elif array[1] == 0x10:
                value = array[2]
                desc = "EnExIO Start %d" % value
            elif array[1] == 0x22:
                part = array[2]
                desc = "%d, Max Layer" % (part)
            elif array[1] == 0x30:
                filenumber = self.parse_filenumber(array[2:4])
                desc = "U File ID %d" % filenumber
            elif array[1] == 0x40:
                value = array[2]
                desc = "ZU Map %d" % value
            elif array[1] == 0x41:
                part = array[2]
                mode = array[3]
                desc = "%d, Work Mode %d" % (part, mode)
        elif array[0] == 0xCC:
            desc = "ACK from machine"
        elif array[0] == 0xCD:
            desc = "ERR from machine"
        elif array[0] == 0xCE:
            desc = "Keep Alive"
        elif array[0] == 0xD7:
            self.in_file = False
            if self.spooler is not None:
                self.spooler.append(self.cutcode)
            if self.elements is not None:
                self.elements.add_element(self.cutcode)
                self.elements.classify([self.cutcode])
            if self.spooler is not None or self.elements is not None:
                self.cutcode = CutCode()
            desc = "End Of File"
        elif array[0] == 0xD8:
            self.in_file = True
            if array[1] == 0x00:
                desc = "Start Process"
            if array[1] == 0x01:
                desc = "Stop Process"
            if array[1] == 0x02:
                desc = "Pause Process"
            if array[1] == 0x03:
                desc = "Restore Process"
            if array[1] == 0x10:
                desc = "Ref Point Mode 2"
            if array[1] == 0x11:
                desc = "Ref Point Mode 1"
            if array[1] == 0x12:
                desc = "Ref Point Mode 0"
            if array[1] == 0x2C:
                self.z = 0.0
                desc = "Home Z"
            if array[1] == 0x2D:
                self.u = 0.0
                desc = "Home U"
            if array[1] == 0x2E:
                desc = "FocusZ"
        elif array[0] == 0xD9:
            options = array[2]
            if options == 0x03:
                param = "Light"
            elif options == 0x02:
                param = ""
            elif options == 0x01:
                param = "Light/Origin"
            else:  # options == 0x00:
                param = "Origin"
            if array[1] == 0x00:
                coord = self.abscoord(array[3:8])
                self.x += coord
                desc = "Move %s X: %f (%f,%f)" % (param, coord, self.x, self.y)
            elif array[1] == 0x01:
                coord = self.abscoord(array[3:8])
                self.y += coord
                desc = "Move %s Y: %f (%f,%f)" % (param, coord, self.x, self.y)
            elif array[1] == 0x02:
                coord = self.abscoord(array[3:8])
                self.z += coord
                desc = "Move %s Z: %f (%f,%f)" % (param, coord, self.x, self.y)
            elif array[1] == 0x03:
                coord = self.abscoord(array[3:8])
                self.u += coord
                desc = "Move %s U: %f (%f,%f)" % (param, coord, self.x, self.y)
            elif array[1] == 0x10:
                desc = "Home %s XY" % param
                self.x = 0
                self.y = 0
        elif array[0] == 0xDA:
            v = 0
            name = None
            if array[2] == 0x00:
                if array[3] == 0x04:
                    name = "IOEnable"
                elif array[3] == 0x05:
                    name = "G0 Velocity"
                    v = 200000  # 200 mm/s
                elif array[3] == 0x0B:
                    name = "Eng Facula"
                    v = 800  # 80%
                elif array[3] == 0x0C:
                    name = "Home Velocity"
                    v = 20000  # 20mm/s
                elif array[3] == 0x0E:
                    name = "Eng Vert Velocity"
                    v = 100000  # 100 mm/s
                elif array[3] == 0x10:
                    name = "System Control Mode"
                elif array[3] == 0x11:
                    name = "Laser PWM Frequency 1"
                elif array[3] == 0x12:
                    name = "Laser Min Power 1"
                elif array[3] == 0x13:
                    name = "Laser Max Power 1"
                elif array[3] == 0x16:
                    name = "Laser Attenuation"
                elif array[3] == 0x17:
                    name = "Laser PWM Frequency 2"
                elif array[3] == 0x18:
                    name = "Laser Min Power 2"
                elif array[3] == 0x19:
                    name = "Laser Max Power 2"
                elif array[3] == 0x1A:
                    name = "Laser Standby Frequency 1"
                elif array[3] == 0x1B:
                    name = "Laser Standby Pulse 1"
                elif array[3] == 0x1C:
                    name = "Laser Standby Frequency 2"
                elif array[3] == 0x1D:
                    name = "Laser Standby Pulse 2"
                elif array[3] == 0x1E:
                    name = "Auto Type Space"
                elif array[3] == 0x20:
                    name = "Axis Control Para 1"
                    v = 0x4000  # True
                elif array[3] == 0x21:
                    name = "Axis Precision 1"
                elif array[3] == 0x23:
                    name = "Axis Max Velocity 1"
                elif array[3] == 0x24:
                    name = "Axis Start Velocity 1"
                elif array[3] == 0x25:
                    name = "Axis Max Acc 1"
                elif array[3] == 0x26:
                    name = "Axis Range 1, Get Frame X"
                    v = 320000
                elif array[3] == 0x27:
                    name = "Axis Btn Start Velocity 1"
                elif array[3] == 0x28:
                    name = "Axis Btn Acc 1"
                elif array[3] == 0x29:
                    name = "Axis Estp Acc 1"
                elif array[3] == 0x2A:
                    name = "Axis Home Offset 1"
                elif array[3] == 0x2B:
                    name = "Axis Backlash 1"
                    v = 0  # 0mm

                elif array[3] == 0x30:
                    name = "Axis Control Para 2"
                    v = 0x4000  # True
                elif array[3] == 0x31:
                    name = "Axis Precision 2"
                elif array[3] == 0x33:
                    name = "Axis Max Velocity 2"
                elif array[3] == 0x34:
                    name = "Axis Start Velocity 2"
                elif array[3] == 0x35:
                    name = "Axis Max Acc 2"
                elif array[3] == 0x36:
                    name = "Axis Range 2, Get Frame Y"
                    v = 220000
                elif array[3] == 0x37:
                    name = "Axis Btn Start Velocity 2"
                elif array[3] == 0x38:
                    name = "Axis Btn Acc 2"
                elif array[3] == 0x39:
                    name = "Axis Estp Acc 2"
                elif array[3] == 0x3A:
                    name = "Axis Home Offset 2"
                elif array[3] == 0x3B:
                    name = "Axis Backlash 2"
                    v = 0  # 0 mm

                elif array[3] == 0x40:
                    name = "Axis Control Para 3"
                    v = 0  # False
                elif array[3] == 0x41:
                    name = "Axis Precision 3"
                elif array[3] == 0x43:
                    name = "Axis Max Velocity 3"
                elif array[3] == 0x44:
                    name = "Axis Start Velocity 3"
                elif array[3] == 0x45:
                    name = "Axis Max Acc 3"
                elif array[3] == 0x46:
                    name = "Axis Range 3, Get Frame Z"
                elif array[3] == 0x47:
                    name = "Axis Btn Start Velocity 3"
                elif array[3] == 0x48:
                    name = "Axis Btn Acc 3"
                elif array[3] == 0x49:
                    name = "Axis Estp Acc 3"
                elif array[3] == 0x4A:
                    name = "Axis Home Offset 3"
                elif array[3] == 0x4B:
                    name = "Axis Backlash 3"

                elif array[3] == 0x50:
                    name = "Axis Control Para 4"
                    v = 0  # False
                elif array[3] == 0x51:
                    name = "Axis Precision 4"
                elif array[3] == 0x53:
                    name = "Axis Max Velocity 4"
                elif array[3] == 0x54:
                    name = "Axis Start Velocity 4"
                elif array[3] == 0x55:
                    name = "Axis Max Acc 4"
                elif array[3] == 0x56:
                    name = "Axis Range 4, Get Frame U"
                elif array[3] == 0x57:
                    name = "Axis Btn Start Velocity 4"
                elif array[3] == 0x58:
                    name = "Axis Btn Acc 4"
                elif array[3] == 0x59:
                    name = "Axis Estp Acc 4"
                elif array[3] == 0x5A:
                    name = "Axis Home Offset 4"
                elif array[3] == 0x5B:
                    name = "Axis Backlash 4"

                elif array[3] == 0x60:
                    name = "Machine Type"

                elif array[3] == 0x63:
                    name = "Laser Min Power 3"
                elif array[3] == 0x64:
                    name = "Laser Max Power 3"
                elif array[3] == 0x65:
                    name = "Laser PWM Frequency 3"
                elif array[3] == 0x66:
                    name = "Laser Standby Frequency 3"
                elif array[3] == 0x67:
                    name = "Laser Standby Pulse 3"

                elif array[3] == 0x68:
                    name = "Laser Min Power 4"
                elif array[3] == 0x69:
                    name = "Laser Max Power 4"
                elif array[3] == 0x6A:
                    name = "Laser PWM Frequency 4"
                elif array[3] == 0x6B:
                    name = "Laser Standby Frequency 4"
                elif array[3] == 0x6C:
                    name = "Laser Standby Pulse 4"
            elif array[2] == 0x02:
                if array[3] == 0x00:
                    name = "System Settings"
                elif array[3] == 0x01:
                    name = "Turn Velocity"
                    v = 20000  # 20 m/s
                elif array[3] == 0x02:
                    name = "Syn Acc"
                    v = 3000000  # 3000 mm/s2
                elif array[3] == 0x03:
                    name = "G0 Delay"
                    v = 0  # 0 ms
                elif array[3] == 0x07:
                    name = "Feed Delay After"
                    v = 0  # 0 s
                elif array[3] == 0x09:
                    name = "Turn Acc"
                    v = 400000  # 400 mm/s
                elif array[3] == 0x0A:
                    name = "G0 Acc"
                    v = 3000000  # 3000 mm/s2
                elif array[3] == 0x0B:
                    name = "Feed Delay Prior"
                    v = 0  # 0 ms
                elif array[3] == 0x0C:
                    name = "Manual Distance"
                elif array[3] == 0x0D:
                    name = "Shut Down Delay"
                elif array[3] == 0x0E:
                    name = "Focus Depth"
                    v = 5000  # 5mm
                elif array[3] == 0x0F:
                    name = "Go Scale Blank"
                    v = 0  # 0 mm
                elif array[3] == 0x17:
                    name = "Array Feed Repay"
                    v = 0  # 0mm
                elif array[3] == 0x1A:
                    name = "Acc Ratio"
                    v = 100  # 100%
                elif array[3] == 0x1B:
                    name = "Turn Ratio"
                    v = 100  # 100% (speed factor)
                elif array[3] == 0x1C:
                    name = "Acc G0 Ratio"
                    v = 100  # 100%
                elif array[3] == 0x1F:
                    name = "Rotate Pulse"
                elif array[3] == 0x21:
                    name = "Rotate D"
                elif array[3] == 0x24:
                    name = "X Min Eng Velocity"
                    v = 10000  # 10mm/s
                elif array[3] == 0x25:
                    name = "X Eng Acc"
                    v = 10000000  # 10000 m/s
                elif array[3] == 0x26:
                    name = "User Para 1"
                elif array[3] == 0x28:
                    name = "Z Home Velocity"
                elif array[3] == 0x29:
                    name = "Z Work Velocity"
                elif array[3] == 0x2A:
                    name = "Z G0 Velocity"
                elif array[3] == 0x2B:
                    name = "Z Pen Up Position"
                elif array[3] == 0x2C:
                    name = "U Home Velocity"
                elif array[3] == 0x2D:
                    name = "U Work Velocity"
                elif array[3] == 0x31:
                    name = "Manual Fast Speed"
                    v = 100000  # 100 mm/s
                elif array[3] == 0x32:
                    name = "Manual Slow Speed"
                    v = 10000  # 10 mm/s
                elif array[3] == 0x34:
                    name = "Y Minimum Eng Velocity"
                    v = 10000  # 10mm/s
                elif array[3] == 0x35:
                    name = "Y Eng Acc"
                    v = 3000000  # 3000 mm/s
                elif array[3] == 0x37:
                    name = "Eng Acc Ratio"
                    v = 100  # Engraving factor 100%
            elif array[2] == 0x03:
                if array[3] == 0x00:
                    name = "Card Language"
                elif 0x01 <= array[3] <= 0x07:
                    name = "PC Lock %d" % array[3]
            elif array[2] == 0x04:
                if array[3] == 0x00:
                    name = "Machine Status"
                    v = 22
                elif array[3] == 0x01:
                    name = "Total Open Time (s)"
                elif array[3] == 0x02:
                    name = "Total Work Time (s)"
                elif array[3] == 0x03:
                    name = "Total Work Number"
                elif array[3] == 0x05:
                    name = "Total Doc Number"
                    v = 0
                elif array[3] == 0x08:
                    name = "Previous Work Time"
                elif array[3] == 0x11:
                    name = "Total Laser Work Time"
                elif array[3] == 0x21:
                    name = "Axis Preferred Position 1, Pos X"
                    v = int(self.x)
                elif array[3] == 0x23:
                    name = "X Total Travel (m)"
                elif array[3] == 0x31:
                    name = "Axis Preferred Position 2, Pos Y"
                    v = int(self.y)
                elif array[3] == 0x33:
                    name = "Y Total Travel (m)"
                elif array[3] == 0x41:
                    name = "Axis Preferred Position 3, Pos Z"
                    v = int(self.z)
                elif array[3] == 0x43:
                    name = "Z Total Travel (m)"
                elif array[3] == 0x51:
                    name = "Axis Preferred Position 3,Pos U"
                    v = int(self.u)
                elif array[3] == 0x53:
                    name = "U Total Travel (m)"
            elif array[2] == 0x05:
                if array[3] == 0x7E:
                    v = 0x65006500
                    name = "Card ID"
                if array[3] == 0x7F:
                    v = b"MEERK40T\x00"
                    name = "Mainboard Version"
            if array[1] == 0x00:
                if name is None:
                    name = "Unmapped"
                desc = "Get %02x %02x (%s)" % (array[2], array[3], name)
                if isinstance(v, int):
                    v = int(v)
                    vencode = RuidaEmulator.encode32(v)
                    respond = b"\xDA\x01" + bytes(array[2:4]) + bytes(vencode)
                    respond_desc = "Respond %02x %02x (%s) = %d (0x%08x)" % (
                        array[2],
                        array[3],
                        name,
                        v,
                        v,
                    )
                else:
                    vencode = v
                    respond = b"\xDA\x01" + bytes(array[2:4]) + bytes(vencode)
                    respond_desc = "Respond %02x %02x (%s) = %s" % (
                        array[2],
                        array[3],
                        name,
                        str(vencode),
                    )
            elif array[1] == 0x01:
                value0 = array[4:9]
                value1 = array[9:14]
                v0 = self.decodeu35(value0)
                v1 = self.decodeu35(value1)
                desc = "Set %02x %02x (%s) = %d (0x%08x) %d (0x%08x)" % (
                    array[2],
                    array[3],
                    name,
                    v0,
                    v0,
                    v1,
                    v1,
                )
        elif array[0] == 0xE6:
            if array[1] == 0x01:
                desc = "Set Absolute"
        elif array[0] == 0xE7:
            if array[1] == 0x00:
                desc = "Block End"
            elif array[1] == 0x01:
                self.filename = ""
                for a in array[2:]:
                    if a == 0x00:
                        break
                    self.filename += chr(a)
                desc = "Filename: %s" % self.filename
            elif array[1] == 0x03:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Process TopLeft (%f, %f)" % (c_x, c_y)
            elif array[1] == 0x04:
                v0 = self.decode14(array[2:4])
                v1 = self.decode14(array[4:6])
                v2 = self.decode14(array[6:8])
                v3 = self.decode14(array[8:10])
                v4 = self.decode14(array[10:12])
                v5 = self.decode14(array[12:14])
                v6 = self.decode14(array[14:16])
                desc = "Process Repeat (%d, %d, %d, %d, %d, %d, %d)" % (
                    v0,
                    v1,
                    v2,
                    v3,
                    v4,
                    v5,
                    v6,
                )
            elif array[1] == 0x05:
                direction = array[2]
                desc = "Array Direction (%d)" % (direction)
            elif array[1] == 0x06:
                v1 = self.decodeu35(array[2:7])
                v2 = self.decodeu35(array[7:12])
                desc = "Feed Repeat (%d, %d)" % (v1, v2)
            elif array[1] == 0x07:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Process BottomRight(%f, %f)" % (c_x, c_y)
            elif array[1] == 0x08:  # Same value given to F2 05
                v0 = self.decode14(array[2:4])
                v1 = self.decode14(array[4:6])
                v2 = self.decode14(array[6:8])
                v3 = self.decode14(array[8:10])
                v4 = self.decode14(array[10:12])
                v5 = self.decode14(array[12:14])
                v6 = self.decode14(array[14:16])
                desc = "Array Repeat (%d, %d, %d, %d, %d, %d, %d)" % (
                    v0,
                    v1,
                    v2,
                    v3,
                    v4,
                    v5,
                    v6,
                )
            elif array[1] == 0x09:
                v1 = self.decodeu35(array[2:7])
                desc = "Feed Length %d" % v1
            elif array[1] == 0x13:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Array Min Point (%f,%f)" % (c_x, c_y)
            elif array[1] == 0x17:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Array Max Point (%f,%f)" % (c_x, c_y)
            elif array[1] == 0x23:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Array Add (%f,%f)" % (c_x, c_y)
            elif array[1] == 0x24:
                v1 = array[2]
                desc = "Array Mirror %d" % (v1)
            elif array[1] == 0x35:
                v1 = self.decodeu35(array[2:7])
                v2 = self.decodeu35(array[7:12])
                desc = "Block X Size %d %d" % (v1, v2)
            elif array[1] == 0x46:
                desc = "BY Test 0x11227766"
            elif array[1] == 0x50:
                c_x = self.abscoord(array[1:6]) / um_per_mil
                c_y = self.abscoord(array[6:11]) / um_per_mil
                desc = "Document Min Point(%f, %f)" % (c_x, c_y)
            elif array[1] == 0x51:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Document Max Point(%f, %f)" % (c_x, c_y)
            elif array[1] == 0x52:
                part = array[2]
                c_x = self.abscoord(array[3:8]) / um_per_mil
                c_y = self.abscoord(array[8:13]) / um_per_mil
                desc = "%d, Min Point(%f, %f)" % (part, c_x, c_y)
            elif array[1] == 0x53:
                part = array[2]
                c_x = self.abscoord(array[3:8]) / um_per_mil
                c_y = self.abscoord(array[8:13]) / um_per_mil
                desc = "%d, MaxPoint(%f, %f)" % (part, c_x, c_y)
            elif array[1] == 0x54:
                axis = array[2]
                c_x = self.abscoord(array[3:8]) / um_per_mil
                desc = "Pen Offset %d: %f" % (axis, c_x)
            elif array[1] == 0x55:
                axis = array[2]
                c_x = self.abscoord(array[3:8]) / um_per_mil
                desc = "Layer Offset %d: %f" % (axis, c_x)
            elif array[1] == 0x60:
                desc = "Set Current Element Index (%d)" % (array[2])
            elif array[1] == 0x61:
                part = array[2]
                c_x = self.abscoord(array[3:8]) / um_per_mil
                c_y = self.abscoord(array[8:13]) / um_per_mil
                desc = "%d, MinPointEx(%f, %f)" % (part, c_x, c_y)
            elif array[1] == 0x62:
                part = array[2]
                c_x = self.abscoord(array[3:8]) / um_per_mil
                c_y = self.abscoord(array[8:13]) / um_per_mil
                desc = "%d, MaxPointEx(%f, %f)" % (part, c_x, c_y)
        elif array[0] == 0xE8:
            if array[1] == 0x00:
                v1 = self.decodeu35(array[2:7])
                v2 = self.decodeu35(array[7:12])
                desc = "Delete Document %d %d" % (v1, v2)
            elif array[1] == 0x01:
                filenumber = self.parse_filenumber(array[2:4])
                desc = "Document Name %d" % (filenumber)
            elif array[1] == 0x02:
                desc = "File transfer"
            elif array[1] == 0x03:
                document = array[2]
                desc = "Select Document %d" % (document)
            elif array[1] == 0x04:
                desc = "Calculate Document Time"
        elif array[0] == 0xEA:
            index = array[1]
            desc = "Array Start (%d)" % (index)
        elif array[0] == 0xEB:
            desc = "Array End"
        elif array[0] == 0xF0:
            desc = "Ref Point Set"
        elif array[0] == 0xF1:
            if array[1] == 0x00:
                index = array[2]
                desc = "Element Max Index (%d)" % (index)
            elif array[1] == 0x01:
                index = array[2]
                desc = "Element Name Max Index(%d)" % (index)
            elif array[1] == 0x02:
                enable = array[2]
                desc = "Enable Block Cutting (%d)" % (enable)
            elif array[1] == 0x03:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Display Offset (%f,%f)" % (c_x, c_y)
            elif array[1] == 0x04:
                enable = array[2]
                desc = "Feed Auto Calc (%d)" % enable
            elif array[1] == 0x20:
                desc = "Unknown (%d,%d)" % (array[2], array[3])
        elif array[0] == 0xF2:
            if array[1] == 0x00:
                index = array[2]
                desc = "Element Index (%d)" % (index)
            if array[1] == 0x01:
                index = array[2]
                desc = "Element Name Index (%d)" % (index)
            if array[1] == 0x02:
                name = bytes(array[2:12])
                desc = "Element Name (%s)" % (str(name))
            if array[1] == 0x03:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Element Array Min Point (%f,%f)" % (c_x, c_y)
            if array[1] == 0x04:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Element Array Max Point (%f,%f)" % (c_x, c_y)
            if array[1] == 0x05:
                v0 = self.decode14(array[2:4])
                v1 = self.decode14(array[4:6])
                v2 = self.decode14(array[6:8])
                v3 = self.decode14(array[8:10])
                v4 = self.decode14(array[10:12])
                v5 = self.decode14(array[12:14])
                v6 = self.decode14(array[14:16])
                desc = "Element Array (%d, %d, %d, %d, %d, %d, %d)" % (
                    v0,
                    v1,
                    v2,
                    v3,
                    v4,
                    v5,
                    v6,
                )
            if array[1] == 0x06:
                c_x = self.abscoord(array[2:7]) / um_per_mil
                c_y = self.abscoord(array[7:12]) / um_per_mil
                desc = "Element Array Add (%f,%f)" % (c_x, c_y)
            if array[1] == 0x07:
                index = array[2]
                desc = "Element Array Mirror (%d)" % (index)
        else:
            desc = "Unknown Command!"

        self.ruida_describe("%s\t%s" % (str(bytes(array).hex()), desc))
        self.ruida_channel("--> %s\t(%s)" % (str(bytes(array).hex()), desc))
        if respond is not None:
            self.reply(respond, desc=respond_desc)

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

    def swizzle_byte(self, b):
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        b ^= self.magic
        b = (b + 1) & 0xFF
        return b

    def unswizzle_byte(self, b):
        b = (b - 1) & 0xFF
        b ^= self.magic
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        return b


class RDLoader:
    @staticmethod
    def load_types():
        yield "RDWorks File", ("rd",), "application/x-rd"

    @staticmethod
    def load(kernel, pathname, channel=None, **kwargs):
        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            ruidaemulator = kernel.get_context("/").open_as(
                "module/RuidaEmulator", basename
            )
            ruidaemulator.write(BytesIO(ruidaemulator.unswizzle(f.read())))
            return [ruidaemulator.cutcode], None, None, pathname, basename
