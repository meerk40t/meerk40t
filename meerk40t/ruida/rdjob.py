import threading
import time

from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.units import UNITS_PER_uM
from meerk40t.svgelements import Color

from .exceptions import RuidaCommandError


def signed35(v):
    v &= 0x7FFFFFFFF
    if v > 0x3FFFFFFFF:
        return -0x800000000 + v
    else:
        return v


def signed32(v):
    v &= 0xFFFFFFFF
    if v > 0x7FFFFFFF:
        return -0x100000000 + v
    else:
        return v


def signed14(v):
    v &= 0x7FFF
    if v > 0x1FFF:
        return -0x4000 + v
    else:
        return v


def decode14(data):
    return signed14(decodeu14(data))


def decodeu14(data):
    return (data[0] & 0x7F) << 7 | (data[1] & 0x7F)


def encode14(v):
    return [
        (v >> 7) & 0x7F,
        v & 0x7F,
    ]


def decode35(data):
    return signed35(decodeu35(data))


def decode32(data):
    return signed32(decodeu35(data))


def decodeu35(data):
    return (
        (data[0] & 0x7F) << 28
        | (data[1] & 0x7F) << 21
        | (data[2] & 0x7F) << 14
        | (data[3] & 0x7F) << 7
        | (data[4] & 0x7F)
    )


def encode32(v):
    return [
        (v >> 28) & 0x7F,
        (v >> 21) & 0x7F,
        (v >> 14) & 0x7F,
        (v >> 7) & 0x7F,
        v & 0x7F,
    ]


def abscoord(data):
    return decode32(data)


def relcoord(data):
    return decode14(data)


def parse_mem(data):
    return decode14(data)


def parse_filenumber(data):
    return decode14(data)


def parse_speed(data):
    return decode35(data) / 1000.0


def parse_frequency(data):
    return decodeu35(data)


def parse_power(data):
    return decodeu14(data) / 163.84  # 16384 / 100%


def parse_time(data):
    return decodeu35(data) / 1000.0


def parse_commands(data):
    array = list()
    for b in data:
        if b >= 0x80 and len(array) > 0:
            yield list(array)
            array.clear()
        array.append(b)
    if len(array) > 0:
        yield array


def swizzle_byte(b, magic):
    b ^= (b >> 7) & 0xFF
    b ^= (b << 7) & 0xFF
    b ^= (b >> 7) & 0xFF
    b ^= magic
    b = (b + 1) & 0xFF
    return b


def unswizzle_byte(b, magic):
    b = (b - 1) & 0xFF
    b ^= magic
    b ^= (b >> 7) & 0xFF
    b ^= (b << 7) & 0xFF
    b ^= (b >> 7) & 0xFF
    return b


def swizzles_lut(magic):
    lut_swizzle = [swizzle_byte(s, magic) for s in range(256)]
    lut_unswizzle = [unswizzle_byte(s, magic) for s in range(256)]
    return lut_swizzle, lut_unswizzle


def decode_bytes(data, magic=0x88):
    lut_swizzle, lut_unswizzle = swizzles_lut(magic)
    array = list()
    for b in data:
        array.append(lut_unswizzle[b])
    return bytes(array)


def encode_bytes(data, magic=0x88):
    lut_swizzle, lut_unswizzle = swizzles_lut(magic)
    array = list()
    for b in data:
        array.append(lut_swizzle[b])
    return bytes(array)


class RDJob:
    def __init__(
        self, driver=None, units_to_device_matrix=None, priority=0, channel=None
    ):
        self.units_to_device_matrix = units_to_device_matrix
        self._driver = driver
        self.channel = channel
        self.reply = None
        self.buffer = list()
        self.plotcut = None

        self.priority = priority

        self.time_submitted = time.time()
        self.time_started = None
        self.runtime = 0

        self._stopped = True
        self._estimate = 0

        self.scale = UNITS_PER_uM

        self.speed = None
        self.power = None
        self.frequency = None
        self.power1_max = None
        self.power1_min = None
        self.power2_max = None
        self.power2_min = None

        self.color = None
        self.magic = 0x11  # 0x11 for the 634XG
        # self.magic = 0x88
        self.lut_swizzle, self.lut_unswizzle = swizzles_lut(self.magic)

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.u = 0.0

        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0

        self.lock = threading.Lock()

    def __str__(self):
        return f"{self.__class__.__name__}({len(self.buffer)} lines)"

    @property
    def status(self):
        if self.is_running and self.time_started is not None:
            return "Running"
        elif not self.is_running:
            return "Disabled"
        else:
            return "Queued"

    def write_blob(self, data, magic=None):
        """
        Procedural commands sent in large data chunks. This can be through USB or UDP or a loaded file. These are
        expected to be unswizzled with the swizzle_mode set for the reply. Write will parse out the individual commands
        and send those to the command routine.

        @param data:
        @param magic: magic number for unswizzling
        @return:
        """
        if magic is None:
            d12 = 0
            d89 = 0
            for d in data:
                if d == 0x12:
                    d12 += 1
                elif d == 0x89:
                    d89 += 1
            if d89 + d12 > 10:
                if d89 > d12:
                    magic = 0x88
                else:
                    magic = 0x11
        if magic is not None and magic != self.magic:
            self.magic = magic
            self.lut_swizzle, self.lut_unswizzle = swizzles_lut(self.magic)
        packet = self.unswizzle(data)
        with self.lock:
            self.buffer.extend(parse_commands(packet))

    def write_command(self, command):
        with self.lock:
            self.buffer.append(command)

    def execute(self, driver=None):
        """
        Execute calls each item in the list of items in order. This is intended to be called by the spooler thread. And
        hold the spooler while these items are executing.
        @return:
        """
        self._stopped = False
        if self.time_started is None:
            self.time_started = time.time()
        with self.lock:
            array = self.buffer.pop(0)
        self.process(array)
        if not self.buffer:
            # Buffer is empty now. Job is complete
            self.runtime += time.time() - self.time_started
            self._stopped = True
            return True  # All steps were executed.
        return False

    def stop(self):
        """
        Stop this current laser-job, cannot be called from the spooler thread.
        @return:
        """
        if not self._stopped:
            self.runtime += time.time() - self.time_started
        self._stopped = True

    def is_running(self):
        return not self._stopped

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        result = 0
        if self.is_running():
            result = time.time() - self.time_started
        else:
            result = self.runtime
        return result

    def estimate_time(self):
        """
        Give laser job time estimate.
        @return:
        """
        return self._estimate

    def plot_location(self, x, y, power):
        """
        Adds this particular location to the current plotcut.

        Or, starts a new plotcut if one is not already started.

        First plotcut is a 0-power move to the current position. X and Y are set to plotted location

        @param x:
        @param y:
        @param power:
        @return:
        """
        matrix = self.units_to_device_matrix
        if matrix is None:
            # Using job for something other than point plotting
            return
        if self.plotcut is None:
            self.x = x
            self.y = y
            ox, oy = matrix.transform_point([self.x, self.y])
            self.plotcut = PlotCut(
                settings={
                    "speed": self.speed,
                    "power": self.power,
                    "frequency": self.frequency,
                }
            )
            self.plotcut.plot_init(int(round(ox)), int(round(oy)))
        tx, ty = matrix.transform_point([x, y])
        self.plotcut.plot_append(int(round(tx)), int(round(ty)), power * (self.power / 1000.0))
        self.x = x
        self.y = y

    def plot_commit(self):
        """
        Force commits the old plotcut and unsets the current plotcut.

        @return:
        """
        if self.plotcut is None:
            return
        self.plot(self.plotcut)
        self.plotcut = None

    def plot(self, plot):
        try:
            self._driver.plot(plot)
        except AttributeError:
            pass

    def __repr__(self):
        return f"RuidaEmulator(@{hex(id(self))})"

    @property
    def current(self):
        return self.x, self.y

    def set_color(self, color):
        self.color = color

    def process(self, array):
        """
        Parses an individual unswizzled ruida command, updating the emulator state.

        These commands can change the position, settings, speed, color, power, create elements, creates lasercode.
        @param array:
        @return:
        """
        desc = ""
        if array[0] < 0x80:
            if self.channel:
                self.channel(f"NOT A COMMAND: {array[0]}")
            raise RuidaCommandError
        elif array[0] == 0x80:
            value = abscoord(array[2:7])
            if array[1] == 0x00:
                desc = f"Axis X Move {value}"
                self.x += value
            elif array[1] == 0x08:
                desc = f"Axis Z Move {value}"
                self.z += value
        elif array[0] == 0x88:  # 0b10001000 11 characters.
            x = abscoord(array[1:6]) * self.scale
            y = abscoord(array[6:11]) * self.scale
            self.plot_location(x, y, 0)
            desc = f"Move Absolute ({x} units, {y} units)"
        elif array[0] == 0x89:  # 0b10001001 5 characters
            if len(array) > 1:
                dx = relcoord(array[1:3]) * self.scale
                dy = relcoord(array[3:5]) * self.scale
                self.plot_location(self.x + dx, self.y + dy, 0)
                desc = f"Move Relative ({dx} units, {dy} units)"
            else:
                desc = "Move Relative (no coords)"
        elif array[0] == 0x8A:  # 0b10101010 3 characters
            dx = relcoord(array[1:3]) * self.scale
            self.plot_location(self.x + dx, self.y, 0)
            desc = f"Move Horizontal Relative ({dx} units)"
        elif array[0] == 0x8B:  # 0b10101011 3 characters
            dy = relcoord(array[1:3]) * self.scale
            self.plot_location(self.x, self.y + dy, 0)
            desc = f"Move Vertical Relative ({dy} units)"
        elif array[0] == 0x97:
            desc = "Lightburn Swizzle Modulation 97"
        elif array[0] == 0x9B:
            desc = "Lightburn Swizzle Modulation 9b"
        elif array[0] == 0x9E:
            desc = "Lightburn Swizzle Modulation 9e"
        elif array[0] == 0xA0:
            value = abscoord(array[2:7])
            if array[1] == 0x00:
                desc = f"Axis Y Move {value}"
            elif array[1] == 0x08:
                desc = f"Axis U Move {value}"
        elif array[0] == 0xA8:  # 0b10101000 11 characters.
            x = abscoord(array[1:6]) * self.scale
            y = abscoord(array[6:11]) * self.scale
            self.plot_location(x, y, 1)
            desc = f"Cut Absolute ({x} units, {y} units)"
        elif array[0] == 0xA9:  # 0b10101001 5 characters
            dx = relcoord(array[1:3]) * self.scale
            dy = relcoord(array[3:5]) * self.scale
            self.plot_location(self.x + dx, self.y + dy, 1)
            desc = f"Cut Relative ({dx} units, {dy} units)"
        elif array[0] == 0xAA:  # 0b10101010 3 characters
            dx = relcoord(array[1:3]) * self.scale
            self.plot_location(self.x + dx, self.y, 1)
            desc = f"Cut Horizontal Relative ({dx} units)"
        elif array[0] == 0xAB:  # 0b10101011 3 characters
            dy = relcoord(array[1:3]) * self.scale
            self.plot_location(self.x, self.y + dy, 1)
            desc = f"Cut Vertical Relative ({dy} units)"
        elif array[0] == 0xC7:
            try:
                v0 = parse_power(array[1:3])
            except IndexError:
                v0 = 0
            desc = f"Imd Power 1 ({v0})"
        elif array[0] == 0xC2:
            v0 = parse_power(array[1:3])
            desc = f"Imd Power 3 ({v0})"
        elif array[0] == 0xC0:
            v0 = parse_power(array[1:3])
            desc = f"Imd Power 2 ({v0})"
        elif array[0] == 0xC3:
            v0 = parse_power(array[1:3])
            desc = f"Imd Power 4 ({v0})"
        elif array[0] == 0xC8:
            v0 = parse_power(array[1:3])
            desc = f"End Power 1 ({v0})"
        elif array[0] == 0xC4:
            v0 = parse_power(array[1:3])
            desc = f"End Power 3 ({v0})"
        elif array[0] == 0xC1:
            v0 = parse_power(array[1:3])
            desc = f"End Power 2 ({v0})"
        elif array[0] == 0xC5:
            v0 = parse_power(array[1:3])
            desc = f"End Power 4 ({v0})"
        elif array[0] == 0xC6:
            if array[1] == 0x01:
                power = parse_power(array[2:4])
                self.power1_min = power
                power = self.power1_min
                desc = f"Power 1 min={power}"
                self.power = power * 10  # 1000 / 100
            elif array[1] == 0x02:
                power = parse_power(array[2:4])
                self.power1_max = power
                power = self.power1_max
                desc = f"Power 1 max={power}"
                self.power = power * 10  # 1000 / 100
            elif array[1] == 0x05:
                power = parse_power(array[2:4])
                desc = f"Power 3 min={power}"
            elif array[1] == 0x06:
                power = parse_power(array[2:4])
                desc = f"Power 3 max={power}"
            elif array[1] == 0x07:
                power = parse_power(array[2:4])
                desc = f"Power 4 min={power}"
            elif array[1] == 0x08:
                power = parse_power(array[2:4])
                desc = f"Power 4 max={power}"
            elif array[1] == 0x10:
                interval = parse_time(array[2:7])
                desc = f"Laser Interval {interval}ms"
            elif array[1] == 0x11:
                interval = parse_time(array[2:7])
                desc = f"Add Delay {interval}ms"
            elif array[1] == 0x12:
                interval = parse_time(array[2:7])
                desc = f"Laser On Delay {interval}ms"
            elif array[1] == 0x13:
                interval = parse_time(array[2:7])
                desc = f"Laser Off Delay {interval}ms"
            elif array[1] == 0x15:
                interval = parse_time(array[2:7])
                desc = f"Laser On2 {interval}ms"
            elif array[1] == 0x16:
                interval = parse_time(array[2:7])
                desc = f"Laser Off2 {interval}ms"
            elif array[1] == 0x21:
                power = parse_power(array[2:4])
                desc = f"Power 2 min={power}"
                self.power2_min = power
            elif array[1] == 0x22:
                power = parse_power(array[2:4])
                desc = f"Power 2 max={power}"
                self.power2_max = power
            elif array[1] == 0x31:
                part = array[2]
                self.power1_min = parse_power(array[3:5])
                desc = f"{part}, Power 1 Min=({self.power1_min})"
            elif array[1] == 0x32:
                part = array[2]
                self.power1_max = parse_power(array[3:5])
                desc = f"{part}, Power 1 Max=({self.power1_max})"
            elif array[1] == 0x35:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 3 Min ({power})"
            elif array[1] == 0x36:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 3 Max ({power})"
            elif array[1] == 0x37:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 4 Min ({power})"
            elif array[1] == 0x38:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 4 Max ({power})"
            elif array[1] == 0x41:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 2 Min ({power})"
            elif array[1] == 0x42:
                part = array[2]
                power = parse_power(array[3:5])
                desc = f"{part}, Power 2 Max ({power})"
            elif array[1] == 0x50:
                power = parse_power(array[2:4])
                desc = f"Through Power 1 ({power})"
            elif array[1] == 0x51:
                power = parse_power(array[2:4])
                desc = f"Through Power 2 ({power})"
            elif array[1] == 0x55:
                power = parse_power(array[2:4])
                desc = f"Through Power 3 ({power})"
            elif array[1] == 0x56:
                power = parse_power(array[2:4])
                desc = f"Through Power 4 ({power})"
            elif array[1] == 0x60:
                laser = array[2]
                part = array[3]
                frequency = parse_frequency(array[4:9])
                desc = f"part, Laser {laser}, Frequency ({frequency})"
                if frequency != self.frequency:
                    self.frequency = frequency
        elif array[0] == 0xC9:
            if array[1] == 0x02:
                self.plot_commit()
                speed = parse_speed(array[2:7])
                if speed != self.speed:
                    self.speed = speed
                desc = f"Speed Laser 1 {speed}mm/s"
            elif array[1] == 0x03:
                speed = parse_speed(array[2:7])
                desc = f"Axis Speed {speed}mm/s"
            elif array[1] == 0x04:
                self.plot_commit()
                part = array[2]
                speed = parse_speed(array[3:8])
                if speed != self.speed:
                    self.speed = speed
                desc = f"{part}, Speed {speed}mm/s"
            elif array[1] == 0x05:
                speed = parse_speed(array[2:7]) / 1000.0
                desc = f"Force Eng Speed {speed}mm/s"
            elif array[1] == 0x06:
                speed = parse_speed(array[2:7]) / 1000.0
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
                self.plot_commit()
                c = decodeu35(array[2:7])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.set_color(c.hex)
                desc = f"Layer Color {str(self.color)}"
            elif array[1] == 0x06:
                part = array[2]
                c = decodeu35(array[3:8])
                r = c & 0xFF
                g = (c >> 8) & 0xFF
                b = (c >> 16) & 0xFF
                c = Color(red=r, blue=b, green=g)
                self.set_color(c.hex)
                desc = f"{part}, Color {self.color}"
            elif array[1] == 0x10:
                value = array[2]
                desc = f"EnExIO Start {value}"
            elif array[1] == 0x22:
                part = array[2]
                desc = f"{part}, Max Layer"
            elif array[1] == 0x30:
                filenumber = parse_filenumber(array[2:4])
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
            zone = array[1]
            desc = f"Set Inhale Zone {zone}"
        elif array[0] == 0xD7:
            self.plot_commit()
            try:
                self._driver.plot_start()
            except AttributeError:
                pass
            desc = "End Of File"
        elif array[0] == 0xD8:
            if array[1] == 0x00:
                desc = "Start Process"
            if array[1] == 0x10:
                desc = "Ref Point Mode 2, Machine Zero/Absolute Position"
            if array[1] == 0x11:
                desc = "Ref Point Mode 1, Anchor Point"
            if array[1] == 0x12:
                desc = "Ref Point Mode 0, Current Position"
        elif array[0] == 0xDA:
            mem = parse_mem(array[2:4])
            if array[1] == 0x01:
                value0 = array[4:9]
                value1 = array[9:14]
                v0 = decodeu35(value0)
                v1 = decodeu35(value1)
                desc = f"Set {array[2]:02x} {array[3]:02x} (mem: {mem:04x})= {v0} (0x{v0:08x}) {v1} (0x{v1:08x})"
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
                elif array[1] == 0x05:
                    sum = decodeu35(array[2:7])
                    desc = f"Set File Sum {sum}"

        elif array[0] == 0xE6:
            if array[1] == 0x01:
                desc = "Set Absolute"
                # Only seen in Absolute Coords. MachineZero is Ref2 but does not Set Absolute.
        elif array[0] == 0xE7:
            if array[1] == 0x00:
                self.plot_commit()
                desc = "Block End"
            elif array[1] == 0x01:
                pass  # Set filename for job (only realtime, see emulator)
            elif array[1] == 0x03:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Process TopLeft ({c_x}, {c_y})"
            elif array[1] == 0x04:
                v0 = decode14(array[2:4])
                v1 = decode14(array[4:6])
                v2 = decode14(array[6:8])
                v3 = decode14(array[8:10])
                v4 = decode14(array[10:12])
                v5 = decode14(array[12:14])
                v6 = decode14(array[14:16])
                desc = f"Process Repeat ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            elif array[1] == 0x05:
                direction = array[2]
                desc = f"Array Direction ({direction})"
            elif array[1] == 0x06:
                v1 = decodeu35(array[2:7])
                v2 = decodeu35(array[7:12])
                desc = f"Feed Repeat ({v1}, {v2})"
            elif array[1] == 0x07:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Process BottomRight({c_x}, {c_y})"
            elif array[1] == 0x08:  # Same value given to F2 04
                v0 = decode14(array[2:4])
                v1 = decode14(array[4:6])
                v2 = decode14(array[6:8])
                v3 = decode14(array[8:10])
                v4 = decode14(array[10:12])
                v5 = decode14(array[12:14])
                v6 = decode14(array[14:16])
                desc = f"Array Repeat ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            elif array[1] == 0x09:
                v1 = decodeu35(array[2:7])
                desc = f"Feed Length {v1}"
            elif array[1] == 0x0A:
                desc = f"Feed Info"
            elif array[1] == 0x0B:
                v1 = array[2]
                desc = f"Array En Mirror Cut {v1}"
            elif array[1] == 0x0C:
                v1 = array[2]
                desc = f"Array Mirror Cut Distance {v1}"
            elif array[1] == 0x0C:
                v1 = array[2]
                desc = f"Set File Head Distance {v1}"
            elif array[1] == 0x13:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Array Min Point ({c_x},{c_y})"
            elif array[1] == 0x17:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Array Max Point ({c_x},{c_y})"
            elif array[1] == 0x23:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Array Add ({c_x},{c_y})"
            elif array[1] == 0x24:
                v1 = array[2]
                desc = f"Array Mirror {v1}"
            elif array[1] == 0x32:
                v1 = decodeu35(array[2:7])
                desc = f"Set Tick Count {v1}"
            elif array[1] == 0x35:
                v1 = decodeu35(array[2:7])
                v2 = decodeu35(array[7:12])
                desc = f"Block X Size {v1} {v2}"
            elif array[1] == 0x32:
                desc = f"Set File Empty"
            elif array[1] == 0x37:
                v1 = decodeu35(array[2:7])
                desc = f"Array Even Distance {v1}"
            elif array[1] == 0x38:
                v1 = array[2]
                desc = f"Set Feed Auto Pause {v1}"
            elif array[1] == 0x3A:
                desc = f"Union Block Property"
            elif array[1] == 0x3B:
                v1 = array[2]
                desc = f"Set File Property {v1}"
            elif array[1] == 0x46:
                desc = "BY Test 0x11227766"
            elif array[1] == 0x50:
                c_x = abscoord(array[1:6]) * UNITS_PER_uM
                c_y = abscoord(array[6:11]) * UNITS_PER_uM
                desc = f"Document Min Point({c_x}, {c_y})"
            elif array[1] == 0x51:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Document Max Point({c_x}, {c_y})"
            elif array[1] == 0x52:
                part = array[2]
                c_x = abscoord(array[3:8]) * UNITS_PER_uM
                c_y = abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, Min Point({c_x}, {c_y})"
            elif array[1] == 0x53:
                part = array[2]
                c_x = abscoord(array[3:8]) * UNITS_PER_uM
                c_y = abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, MaxPoint({c_x}, {c_y})"
            elif array[1] == 0x54:
                axis = array[2]
                c_x = abscoord(array[3:8]) * UNITS_PER_uM
                desc = f"Pen Offset {axis}: {c_x}"
            elif array[1] == 0x55:
                axis = array[2]
                c_x = abscoord(array[3:8]) * UNITS_PER_uM
                desc = f"Layer Offset {axis}: {c_x}"
            elif array[1] == 0x57:
                desc = f"PList Feed"
            elif array[1] == 0x60:
                desc = f"Set Current Element Index ({array[2]})"
            elif array[1] == 0x61:
                part = array[2]
                c_x = abscoord(array[3:8]) * UNITS_PER_uM
                c_y = abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, MinPointEx({c_x}, {c_y})"
            elif array[1] == 0x62:
                part = array[2]
                c_x = abscoord(array[3:8]) * UNITS_PER_uM
                c_y = abscoord(array[8:13]) * UNITS_PER_uM
                desc = f"{part}, MaxPointEx({c_x}, {c_y})"
        elif array[0] == 0xE8:
            # Realtime command.
            pass
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
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
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
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Element Array Min Point ({c_x},{c_y})"
            if array[1] == 0x04:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Element Array Max Point ({c_x},{c_y})"
            if array[1] == 0x05:
                v0 = decode14(array[2:4])
                v1 = decode14(array[4:6])
                v2 = decode14(array[6:8])
                v3 = decode14(array[8:10])
                v4 = decode14(array[10:12])
                v5 = decode14(array[12:14])
                v6 = decode14(array[14:16])
                desc = f"Element Array ({v0}, {v1}, {v2}, {v3}, {v4}, {v5}, {v6})"
            if array[1] == 0x06:
                c_x = abscoord(array[2:7]) * UNITS_PER_uM
                c_y = abscoord(array[7:12]) * UNITS_PER_uM
                desc = f"Element Array Add ({c_x},{c_y})"
            if array[1] == 0x07:
                index = array[2]
                desc = f"Element Array Mirror ({index})"
        else:
            desc = "Unknown Command!"
        if self.channel:
            self.channel(f"-**-> {str(bytes(array).hex())}\t({desc})")

    def unswizzle(self, data):
        return bytes([self.lut_unswizzle[b] for b in data])

    def swizzle(self, data):
        return bytes([self.lut_swizzle[b] for b in data])
