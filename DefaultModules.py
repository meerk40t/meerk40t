import os
from base64 import b64encode
from io import BytesIO
from xml.etree.cElementTree import Element, ElementTree, SubElement

from EgvParser import parse_egv
from Kernel import Module, Pipe
from LaserCommandConstants import *
from svgelements import *

MILS_PER_MM = 39.3701


class GRBLEmulator(Module, Pipe):

    def __init__(self):
        Module.__init__(self)
        self.home_adjust = None
        self.flip_x = 1  # Assumes the GCode is flip_x, -1 is flip, 1 is normal
        self.flip_y = 1  # Assumes the Gcode is flip_y,  -1 is flip, 1 is normal
        self.scale = MILS_PER_MM  # Initially assume mm mode 39.4 mils in an mm. G20 DEFAULT
        self.feed_convert = lambda s: s / (self.scale * 60.0)  # G94 DEFAULT, mm mode
        self.feed_invert = lambda s: self.scale * 60.0 * s
        self.move_mode = 0
        self.home = None
        self.home2 = None
        self.on_mode = 1
        self.buffer = ''
        self.grbl_set_re = re.compile(r'\$(\d+)=([-+]?[0-9]*\.?[0-9]*)')
        self.code_re = re.compile(r'([A-Za-z])')
        self.float_re = re.compile(r'[-+]?[0-9]*\.?[0-9]*')
        self.settings = {
            0: 10,  # step pulse microseconds
            1: 25,  # step idle delay
            2: 0,  # step pulse invert
            3: 0,  # step direction invert
            4: 0,  # invert step enable pin, boolean
            5: 0,  # invert limit pins, boolean
            6: 0,  # invert probe pin
            10: 255,  # status report options
            11: 0.010,  # Junction deviation, mm
            12: 0.002,  # arc tolerance, mm
            13: 0,  # Report in inches
            20: 0,  # Soft limits enabled.
            21: 0,  # hard limits enabled
            22: 0,  # Homing cycle enable
            23: 0,  # Homing direction invert
            24: 25.000,  # Homing locate feed rate, mm/min
            25: 500.000,  # Homing search seek rate, mm/min
            26: 250,  # Homing switch debounce delay, ms
            27: 1.000,  # Homing switch pull-off distance, mm
            30: 1000,  # Maximum spindle speed, RPM
            31: 0,  # Minimum spindle speed, RPM
            32: 1,  # Laser mode enable, boolean
            100: 250.000,  # X-axis steps per millimeter
            101: 250.000,  # Y-axis steps per millimeter
            102: 250.000,  # Z-axis steps per millimeter
            110: 500.000,  # X-axis max rate mm/min
            111: 500.000,  # Y-axis max rate mm/min
            112: 500.000,  # Z-axis max rate mm/min
            120: 10.000,  # X-axis acceleration, mm/s^2
            121: 10.000,  # Y-axis acceleration, mm/s^2
            122: 10.000,  # Z-axis acceleration, mm/s^2
            130: 200.000,  # X-axis max travel mm.
            131: 200.000,  # Y-axis max travel mm
            132: 200.000  # Z-axis max travel mm.
        }
        self.grbl_channel = None

    def initialize(self):
        self.device.add_greet('grbl', b"Grbl 1.1e ['$' for help]\r\n")
        self.grbl_channel = self.device.channel_open('grbl')

    def close(self):
        pass

    def open(self):
        pass

    def realtime_write(self, bytes_to_write):
        interpreter = self.device.interpreter
        if bytes_to_write == '?':  # Status report
            # Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep
            if interpreter.state == 0:
                state = 'Idle'
            else:
                state = 'Busy'
            x = self.device.current_x / self.scale
            y = self.device.current_y / self.scale
            z = 0.0
            parts = list()
            parts.append(state)
            parts.append('MPos:%f,%f,%f' % (x, y, z))
            f = self.feed_invert(self.device.interpreter.speed)
            s = self.device.interpreter.power
            parts.append('FS:%f,%d' % (f, s))
            self.grbl_channel("<%s>\r\n" % '|'.join(parts))
        elif bytes_to_write == '~':  # Resume.
            interpreter.realtime_command(REALTIME_RESUME)
        elif bytes_to_write == '!':  # Pause.
            interpreter.realtime_command(REALTIME_PAUSE)
        elif bytes_to_write == '\x18':  # Soft reset.
            interpreter.realtime_command(REALTIME_RESET)

    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode()
        if '?' in data:
            data = data.replace('?', '')
            self.realtime_write('?')
        if '~' in data:
            data = data.replace('$', '')
            self.realtime_write('~')
        if '!' in data:
            data = data.replace('!', '')
            self.realtime_write('!')
        if '\x18' in data:
            data = data.replace('\x18', '')
            self.realtime_write('\x18')
        self.buffer += data
        while '\b' in self.buffer:
            self.buffer = re.sub('.\b', '', self.buffer, count=1)
            if self.buffer.startswith('\b'):
                self.buffer = re.sub('\b+', '', self.buffer)

        while '\n' in self.buffer:
            pos = self.buffer.find('\n')
            command = self.buffer[0:pos].strip('\r')
            self.buffer = self.buffer[pos + 1:]
            cmd = self.commandline(command)
            if cmd == 0:  # Execute GCode.
                self.grbl_channel("ok\r\n")
            else:
                self.grbl_channel("error:%d\r\n" % cmd)

    def _tokenize_code(self, code_line):
        code = None
        for x in self.code_re.split(code_line):
            x = x.strip()
            if len(x) == 0:
                continue
            if len(x) == 1 and x.isalpha():
                if code is not None:
                    yield code
                code = [x.lower()]
                continue
            if code is not None:
                code.extend([float(v) for v in self.float_re.findall(x) if len(v) != 0])
                yield code
            code = None
        if code is not None:
            yield code

    def commandline(self, data):
        spooler = self.device.spooler
        pos = data.find('(')
        commands = {}
        while pos != -1:
            end = data.find(')')
            if 'comment' not in commands:
                commands['comment'] = []
            commands['comment'].append(data[pos + 1:end])
            data = data[:pos] + data[end + 1:]
            pos = data.find('(')
        pos = data.find(';')
        if pos != -1:
            if 'comment' not in commands:
                commands['comment'] = []
            commands['comment'].append(data[pos + 1:])
            data = data[:pos]
        if data.startswith('$'):
            if data == '$':
                self.grbl_channel("[HLP:$$ $# $G $I $N $x=val $Nx=line $J=line $SLP $C $X $H ~ ! ? ctrl-x]\r\n")
                return 0
            elif data == '$$':
                for s in self.settings:
                    v = self.settings[s]
                    if isinstance(v, int):
                        self.grbl_channel("$%d=%d\r\n" % (s, v))
                    elif isinstance(v, float):
                        self.grbl_channel("$%d=%.3f\r\n" % (s, v))
                return 0
            if self.grbl_set_re.match(data):
                settings = list(self.grbl_set_re.findall(data))[0]
                print(settings)
                try:
                    c = self.settings[int(settings[0])]
                except KeyError:
                    return 3
                if isinstance(c, float):
                    self.settings[int(settings[0])] = float(settings[1])
                else:
                    self.settings[int(settings[0])] = int(settings[1])
                return 0
            elif data == '$I':
                pass
            elif data == '$G':
                pass
            elif data == '$N':
                pass
            elif data == '$H':
                spooler.add_command(COMMAND_HOME)
                if self.home_adjust is not None:
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_MOVE, (self.home_adjust[0], self.home_adjust[1]))
                return 0
                # return 5  # Homing cycle not enabled by settings.
            return 3  # GRBL '$' system command was not recognized or supported.
        if data.startswith('cat'):
            return 2
        for c in self._tokenize_code(data):
            g = c[0]
            if g not in commands:
                commands[g] = []
            if len(c) >= 2:
                commands[g].append(c[1])
            else:
                commands[g].append(None)
        return self.command(commands)

    def command(self, gc):
        spooler = self.device.spooler
        if 'm' in gc:
            for v in gc['m']:
                if v == 0 or v == 1:
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_WAIT_FINISH)
                elif v == 2:
                    return 0
                elif v == 30:
                    return 0
                elif v == 3 or v == 4:
                    self.on_mode = True
                elif v == 5:
                    self.on_mode = False
                    spooler.add_command(COMMAND_LASER_OFF)
                elif v == 7:
                    #  Coolant control.
                    pass
                elif v == 8:
                    spooler.add_command(COMMAND_SIGNAL, ('coolant', True))
                elif v == 9:
                    spooler.add_command(COMMAND_SIGNAL, ('coolant', False))
                elif v == 56:
                    pass  # Parking motion override control.
                elif v == 911:
                    pass  # Set TMC2130 holding currents
                elif v == 912:
                    pass  # M912: Set TMC2130 running currents
                else:
                    return 20
            del gc['m']
        if 'g' in gc:
            for v in gc['g']:
                if v is None:
                    return 2
                elif v == 0.0:
                    self.move_mode = 0
                elif v == 1.0:
                    self.move_mode = 1
                elif v == 2.0:  # CW_ARC
                    self.move_mode = 2
                elif v == 3.0:  # CCW_ARC
                    self.move_mode = 3
                elif v == 4.0:  # DWELL
                    t = 0
                    if 'p' in gc:
                        t = float(gc['p'].pop()) / 1000.0
                        if len(gc['p']) == 0:
                            del gc['p']
                    if 's' in gc:
                        t = float(gc['s'].pop())
                        if len(gc['s']) == 0:
                            del gc['s']
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_WAIT, t)
                elif v == 10.0:
                    if 'l' in gc:
                        l = float(gc['l'].pop(0))
                        if len(gc['l']) == 0:
                            del gc['l']
                        if l == 2.0:
                            pass
                        elif l == 20:
                            pass
                elif v == 17:
                    pass  # Set XY coords.
                elif v == 18:
                    return 2  # Set the XZ plane for arc.
                elif v == 19:
                    return 2  # Set the YZ plane for arc.
                elif v == 20.0 or v == 70.0:
                    self.scale = 1000.0  # g20 is inch mode. 1000 mils in an inch
                elif v == 21.0 or v == 71.0:
                    self.scale = 39.3701  # g21 is mm mode. 39.3701 mils in a mm
                elif v == 28.0:
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.add_command(COMMAND_MOVE, (self.home_adjust[0], self.home_adjust[1]))
                    if self.home is not None:
                        spooler.add_command(COMMAND_MOVE, self.home)
                elif v == 28.1:
                    if 'x' in gc and 'y' in gc:
                        x = gc['x'].pop(0)
                        if len(gc['x']) == 0:
                            del gc['x']
                        y = gc['y'].pop(0)
                        if len(gc['y']) == 0:
                            del gc['y']
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        self.home = (x, y)
                elif v == 28.2:
                    # Run homing cycle.
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.add_command(COMMAND_MOVE, (self.home_adjust[0], self.home_adjust[1]))
                elif v == 28.3:
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.add_command(COMMAND_MOVE, (self.home_adjust[0], self.home_adjust[1]))
                    if 'x' in gc:
                        x = gc['x'].pop(0)
                        if len(gc['x']) == 0:
                            del gc['x']
                        if x is None:
                            x = 0
                        spooler.add_command(COMMAND_MOVE, (x, 0))
                    if 'y' in gc:
                        y = gc['y'].pop(0)
                        if len(gc['y']) == 0:
                            del gc['y']
                        if y is None:
                            y = 0
                        spooler.add_command(COMMAND_MOVE, (0, y))
                elif v == 30.0:
                    # Goto predefined position. Return to secondary home position.
                    if 'p' in gc:
                        p = float(gc['p'].pop(0))
                        if len(gc['p']) == 0:
                            del gc['p']
                    else:
                        p = None
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.add_command(COMMAND_MOVE, (self.home_adjust[0], self.home_adjust[1]))
                    if self.home2 is not None:
                        spooler.add_command(COMMAND_MOVE, self.home2)
                elif v == 30.1:
                    # Stores the current absolute position.
                    if 'x' in gc and 'y' in gc:
                        x = gc['x'].pop(0)
                        if len(gc['x']) == 0:
                            del gc['x']
                        y = gc['y'].pop(0)
                        if len(gc['y']) == 0:
                            del gc['y']
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        self.home2 = (x, y)
                elif v == 38.1:
                    # Touch Plate
                    pass
                elif v == 38.2:
                    # Straight Probe
                    pass
                elif v == 38.3:
                    # Prope towards workpiece
                    pass
                elif v == 38.4:
                    # Probe away from workpiece, signal error
                    pass
                elif v == 38.5:
                    # Probe away from workpiece.
                    pass
                elif v == 40.0:
                    pass  # Compensation Off
                elif v == 43.1:
                    pass  # Dynamic tool Length offsets
                elif v == 49:
                    # Cancel tool offset.
                    pass  # Dynamic tool length offsets
                elif v == 53:
                    pass  # Move in Absolute Coordinates
                elif 54 <= v <= 59:
                    # Fixure offset 1-6, G10 and G92
                    system = v - 54
                    pass  # Work Coordinate Systems
                elif v == 61:
                    # Exact path control mode. GRBL required
                    pass
                elif v == 80:
                    # Motion mode cancel. Canned cycle.
                    pass
                elif v == 90.0:
                    spooler.add_command(COMMAND_SET_ABSOLUTE)
                elif v == 91.0:
                    spooler.add_command(COMMAND_SET_INCREMENTAL)
                elif v == 91.1:
                    # Offset mode for certain cam. Incremental distance mode for arcs.
                    pass  # ARC IJK Distance Modes # TODO Implement
                elif v == 92:
                    # Change the current coords without moving.
                    pass  # Coordinate Offset TODO: Implement
                elif v == 92.1:
                    # Clear Coordinate offset set by 92.
                    pass  # Clear Coordinate offset TODO: Implement
                elif v == 93.0:
                    # Feed Rate in Minutes / Unit
                    self.feed_convert = lambda s: (self.scale * 60.0) / s
                    self.feed_invert = lambda s: (self.scale * 60.0) / s
                elif v == 94.0:
                    # Feed Rate in Units / Minute
                    self.feed_convert = lambda s: s / (self.scale * 60.0)
                    self.feed_invert = lambda s:  s * (self.scale * 60.0)
                    # units to mm, seconds to minutes.
                else:
                    return 20  # Unsupported or invalid g-code command found in block.
            del gc['g']
        if 'comment' in gc:
            del gc['comment']
        if 'f' in gc:  # Feed_rate
            for v in gc['f']:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                feed_rate = self.feed_convert(v)
                spooler.add_command(COMMAND_SET_SPEED, feed_rate)
            del gc['f']
        if 's' in gc:
            for v in gc['s']:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                spooler.add_command(COMMAND_SET_POWER, v)
            del gc['s']
        if 'x' in gc or 'y' in gc:
            if self.move_mode == 0:
                spooler.add_command(COMMAND_LASER_OFF)
                spooler.add_command(COMMAND_MODE_RAPID)
            elif self.move_mode == 1 or self.move_mode == 2 or self.move_mode == 3:
                spooler.add_command(COMMAND_MODE_PROGRAM)
            if 'x' in gc:
                x = gc['x'].pop(0)
                if x is None:
                    x = 0
                else:
                    x *= self.scale * self.flip_x
                if len(gc['x']) == 0:
                    del gc['x']
            else:
                x = 0
            if 'y' in gc:
                y = gc['y'].pop(0)
                if y is None:
                    y = 0
                else:
                    y *= self.scale * self.flip_y
                if len(gc['y']) == 0:
                    del gc['y']
            else:
                y = 0
            if self.move_mode == 0:
                spooler.add_command(COMMAND_LASER_OFF)
                spooler.add_command(COMMAND_MOVE, (x, y))
            elif self.move_mode == 1:
                if self.on_mode:
                    spooler.add_command(COMMAND_LASER_ON)
                spooler.add_command(COMMAND_MOVE, (x, y))
            elif self.move_mode == 2:
                spooler.add_command(COMMAND_MOVE, (x, y))  # TODO: Implement CW_ARC
            elif self.move_mode == 3:
                spooler.add_command(COMMAND_MOVE, (x, y))  # TODO: Implement CCW_ARC
        return 0


class RuidaEmulator(Module):

    def __init__(self):
        Module.__init__(self)
        self.buffer = b''
        self.error_x = 0.0
        self.error_y = 0.0

    @staticmethod
    def signed32(v):
        v &= 0xFFFFFFFF
        if v > 0x7FFFFFFF:
            return - 0x80000000 + v
        else:
            return v

    def abscoord(self, data):
        return RuidaEmulator.signed32(
            (data[0] & 0x7F) << 28 |
            (data[1] & 0x7F) << 21 |
            (data[2] & 0x7F) << 14 |
            (data[3] & 0x7F) << 7 |
            (data[4] & 0x7F))

    @staticmethod
    def signed14(v):
        v &= 0x7FFF
        if v > 0x1FFF:
            return - 0x4000 + v
        else:
            return v

    def relcoord(self, data):
        return RuidaEmulator.signed14((data[0] & 0x7F) << 7 | (data[1] & 0x7F))

    def filenumber(self, data):
        return (data[0] & 0x7F) << 7 | \
               (data[1] & 0x7F)

    def speed(self, data):
        return (data[0] & 0x7F) << 28 | \
               (data[1] & 0x7F) << 21 | \
               (data[2] & 0x7F) << 14 | \
               (data[3] & 0x7F) << 7 | \
               (data[4] & 0x7F)

    def power(self, data):
        return (data[0] & 0x7F) << 7 | \
               (data[1] & 0x7F)

    def sum(self, data):
        return (data[0] & 0xFF) << 8 | \
               (data[1] & 0xFF)

    def checksum(self, data):
        sum = 0
        for b in data:
            sum += b
        return sum

    def parse(self, sent_data):
        x = 0.0
        y = 0.0
        um_per_mil = 25.4
        name = ''
        speed = 20.0
        power1_min = 0
        power2_min = 0
        power1_max = 0
        power2_max = 0
        path_d = list()
        array = list()
        for b in sent_data:
            array.append(self.unswizzle_byte(b))
        while len(array) > 0:
            if array[0] == 0xC6:
                if array[1] == 0x01:
                    power1_min = self.power(array[2:4])
                elif array[1] == 0x21:
                    power2_min = self.power(array[2:4])
                elif array[1] == 0x02:
                    power1_max = self.power(array[2:4])
                elif array[1] == 0x22:
                    power2_max = self.power(array[2:4])
            elif array[0] == 0xC9:
                if array[1] == 0x02:
                    # Speed in micrometers/sec
                    speed = self.speed(array[2:7]) / 1000.0
                if array[1] == 0x04:
                    if array[2] == 0x00:
                        # speed in micrometers/sec
                        speed = self.speed(array[3:8]) / 1000.0
            elif array[0] == 0xD9:
                if array[1] == 0x00:
                    if array[2] == 0x02:
                        x = self.abscoord(array[3:8]) / um_per_mil
                        path_d.append("M%04f,%04f" % (x, y))
                        x = x
                    elif array[2] == 0x03:
                        y = self.abscoord(array[3:8]) / um_per_mil
                        path_d.append("M%04f,%04f" % (x, y))
            elif array[0] == 0xA8:
                x = self.abscoord(array[1:6]) / um_per_mil
                y = self.abscoord(array[7:12]) / um_per_mil
                path_d.append("L%0.4f,%0.4f" % (x, y))
            elif array[0] == 0xA9:
                dx = self.relcoord(array[1:3]) / um_per_mil
                dy = self.relcoord(array[3:5]) / um_per_mil
                path_d.append("l%0.4f,%0.4f" % (dx, dy))
                x += dx
                y += dy
            elif array[0] == 0xE8:
                if array[1] == 0x02:
                    if array[2] == 0xE7:
                        if array[3] == 0x01:
                            for a in array[4:]:
                                if a == 0x00:
                                    break
                                name += ord(a)
            elif array[0] == 0x88:
                x = self.abscoord(array[1:6]) / um_per_mil
                y = self.abscoord(array[7:12]) / um_per_mil
                if len(path_d) != 0:
                    path = Path(' '.join(path_d))
                    path.values['name'] = name
                    path.values['speed'] = speed
                    path.values['power'] = (power1_min, power2_min, power1_max, power2_max)
                    yield path
                    path_d.clear()
                path_d.append("M%f,%f" % (x, y))
            elif array[0] == 0x89:
                dx = self.relcoord(array[1:3]) / um_per_mil
                dy = self.relcoord(array[3:5]) / um_per_mil
                if len(path_d) != 0:
                    path = Path(' '.join(path_d))
                    path.values['name'] = name
                    path.values['speed'] = speed
                    path.values['power'] = (power1_min, power2_min, power1_max, power2_max)
                    yield path
                    path_d.clear()
                path_d.append("m%f,%f" % (dx, dy))
                x += dx
                y += dy
            del array[0]
        if len(path_d) != 0:
            path = Path(' '.join(path_d))
            path.values['name'] = name
            path.values['speed'] = speed
            path.values['power'] = (power1_min, power2_min, power1_max, power2_max)
            yield path

    def interface(self, sent_data):
        array = list()
        check = self.checksum(sent_data[2:])
        sum = self.sum(sent_data[:2])
        print(check)
        print(sum)
        if check == sum:
            yield self.swizzle(b'\xCF')
            print(self.swizzle(b'\xCF'))
            print("checksum match")
        else:
            yield self.swizzle(b'\xD0')
            print(self.swizzle(b'\xD0'))
            print("checksum fail")
            return
        for b in sent_data[2:]:
            array.append(self.unswizzle_byte(b))
        if array[0] == 0xC6:
            if array[1] == 0x01:
                print("1st laser source min power: %d" % self.power(array[2:3]))
            elif array[1] == 0x21:
                print("2nd laser source min power: %d" % self.power(array[2:3]))
            elif array[1] == 0x02:
                print("1st laser source max power: %d" % self.power(array[2:3]))
            elif array[1] == 0x22:
                print("2nd laser source max power: %d" % self.power(array[2:3]))
        elif array[0] == 0xC9:
            if array[1] == 0x02:
                # Speed in micrometers/sec
                speed = self.speed(array[2:7]) / 1000.0
                print("Speed set at %f" % speed)
            if array[1] == 0x04:
                if array[2] == 0x00:
                    # speed in micrometers/sec
                    speed = self.speed(array[3:8]) / 1000.0
                    print("Speed set at %f" % speed)
        elif array[0] == 0xD9:
            if array[1] == 0x00:
                if array[2] == 0x02:
                    print("Move X: %d" % self.abscoord(array[3:8]))
                elif array[2] == 0x03:
                    print("Move Y: %d" % self.abscoord(array[3:8]))
                elif array[2] == 0x04:
                    print("Move Z: %d" % self.abscoord(array[3:8]))
                elif array[2] == 0x05:
                    print("Move U: %d" % self.abscoord(array[3:8]))
        elif array[0] == 0xCC:
            print("ACK from machine")
        elif array[0] == 0xCD:
            print("ERR from machine")
        elif array[0] == 0xDA:
            if array[1] == 0x00:
                print("get %02x %02x from machine" % (array[2], array[3]))
                if array[2] == 0x05 and array[3] == 0x7e:
                    yield b'\xd4\x09\x0d\xf7\x8f\xa1\x09\xc3\x89'
                    # Checksum 04:66
                    print(b'\xd4\x09\x0d\xf7\x8f\xa1\x09\xc3\x89')
                    print(self.swizzle(b'\xDA\x01' + bytearray(array[2:4]) + b'\x06\x28\x01\x4a\x00'))
                elif array[2] == 0x00 and array[3] == 0x04:
                    print("responding2...")
                    yield b'\xd4\x09\x89\x8d\x89\x89\x89\x89\xab'
                    print(self.swizzle(b'\xDA\x01' + bytearray(array[2:4]) + b'\x00\x00\x00\x00\x22'))
                elif array[2] == 0x04 or array[3] == 0x05:
                    print("Saved Job Count")
                else:
                    print("Unknown Request.")
            elif array[1] == 0x01:
                print("Response to DA 00 XX XX <VALUE>")
        elif array[0] == 0xA8:
            print("Straight cut to absolute %d %d" % (self.abscoord(array[1:6]), self.abscoord(array[7:12])))
        elif array[0] == 0xA9:
            print("Straight cut to relative %d %d" % (self.relcoord(array[1:2]), self.relcoord(array[3:4])))
        elif array[0] == 0xE7:
            if array[1] == 0x50:
                print("Bounding box top left %d %d" % (self.abscoord(array[1:6]), self.abscoord(array[7:12])))
            if array[1] == 0x50:
                print("Bounding box bottom right %d %d" % (self.abscoord(array[1:6]), self.abscoord(array[7:12])))
        elif array[0] == 0xE8:
            if array[1] == 0x01:
                print("Read filename number: %d" % (self.filenumber(array[1:2])))
            if array[1] == 0x02:
                if array[2] == 0xE7:
                    if array[3] == 0x01:
                        name = ""
                        for a in array[4:]:
                            if a == 0x00:
                                break
                            name += ord(a)
                        print("Set filname for transfer: %s" % name)
        elif array[0] == 0x88:
            print("Straight move to absolute %d %d" % (self.abscoord(array[1:6]), self.abscoord(array[7:12])))
        elif array[0] == 0x89:
            print("Straight move to relative %d %d" % (self.relcoord(array[1:2]), self.relcoord(array[3:4])))
        print("u:" + str(bytes(array).hex()))

    def realtime_write(self, bytes_to_write):
        print(bytes_to_write)

    def unswizzle(self, data):
        array = list()
        for b in data:
            array.append(self.unswizzle_byte(b))
        return bytes(array)

    def swizzle(self, data):
        array = list()
        for b in data:
            array.append(self.swizzle_byte(b))
        return bytes(array)

    def swizzle_byte(self, b):
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        b ^= 0xB0
        b ^= 0x38
        b = (b + 1) & 0xFF
        return b

    def unswizzle_byte(self, b):
        b = (b - 1) & 0xFF
        b ^= 0xB0
        b ^= 0x38
        b ^= (b >> 7) & 0xFF
        b ^= (b << 7) & 0xFF
        b ^= (b >> 7) & 0xFF
        return b


class Console(Module, Pipe):
    def __init__(self):
        Module.__init__(self)
        self.channel = None
        self.pipe = None
        self.buffer = ''
        self.active_device = None

    def initialize(self):
        self.channel = self.device.channel_open('console')
        self.active_device = self.device

    def write(self, data):
        if data == 'exit\n':  # process first to quit a delegate.
            self.pipe = None
            self.channel("Exited Mode.\n")
            return
        if self.pipe is not None:
            self.pipe.write(data)
            return
        if isinstance(data, bytes):
            data = data.decode()
        self.buffer += data
        while '\n' in self.buffer:
            pos = self.buffer.find('\n')
            command = self.buffer[0:pos].strip('\r')
            self.buffer = self.buffer[pos + 1:]
            self.commandline(command)

    def commandline(self, command):
        kernel = self.device.device_root
        active_device = self.active_device
        if command == "grbl":
            self.channel("GRBL Mode.\n")
            if 'GrblEmulator' in self.device.instances['module']:
                self.pipe = active_device.instances['module']['GrblEmulator']
            else:
                self.pipe = active_device.open('module', 'GrblEmulator')
            active_device.add_watcher('grbl', self.channel)
            return
        elif command == "lhy":
            self.channel("Lhymicro-gl Mode.\n")
            self.pipe = self.device.instances['modules']['LhystudioController']
            self.device.add_watcher('lhy', self.channel)
            return
        elif command == "ruidaserver":
            port = 50200
            tcp = False
            try:
                server = kernel.module_instance_open('LaserServer', port=port, tcp=tcp)
                self.channel("Ruida Server opening on port %d.\n" % port)
                if 'RuidaEmulator' in self.device.instances['module']:
                    pipe = active_device.instances['module']['RuidaEmulator']
                else:
                    pipe = active_device.open('module', 'RuidaEmulator')
                active_device.add_watcher('ruida', self.channel)
                active_device.add_watcher('server', self.channel)
                server.set_pipe(pipe)
            except OSError:
                self.channel('Server failed on port: %d' % port)
        elif command == "set":
            for attr in dir(active_device):
                v = getattr(active_device, attr)
                if attr.startswith('_') or not isinstance(v, (int, float, str, bool)):
                    continue
                self.channel('"%s" := %s\n' % (attr, str(v)))
        elif command.startswith('set '):
            var = list(command.split(' '))
            if len(var) >= 3:
                attr = var[1]
                value = var[2]
                if hasattr(active_device, attr):
                    v = getattr(active_device, attr)
                    if isinstance(v, bool):
                        if value == 'False' or value == 'false' or value == 0:
                            setattr(active_device, attr, False)
                        else:
                            setattr(active_device, attr, True)
                    elif isinstance(v, int):
                        setattr(active_device, attr, int(value))
                    elif isinstance(v, float):
                        setattr(active_device, attr, float(value))
                    elif isinstance(v, str):
                        setattr(active_device, attr, str(value))
        elif command == 'control':
            for control_name in active_device.instances['control']:
                self.channel('%s\n' % control_name)
        elif command.startswith('control '):
            control_name = command[len('control '):]
            if control_name in active_device.instances['control']:
                active_device.execute(control_name)
                self.channel("Executed '%s'\n" % control_name)
            else:
                self.channel("Control '%s' not found.\n" % control_name)
        elif command == 'device':
            self.channel('%d: %s\n' % (0, 'device_root'))
            for i, name in enumerate(kernel.instances['device']):
                self.channel('%d: %s\n' % (i+1, name))
        elif command.startswith('device '):
            value = command[len('device '):]
            try:
                value = int(value)
                if value == 0:
                    self.active_device = kernel
                    self.channel('Device set: device_root\n')
                else:
                    for i, name in enumerate(kernel.instances['device']):
                        if i + 1 == value:
                            self.active_device = kernel.instances['device'][name]
                            self.channel('Device set: %d\n' % value)
                            break
            except ValueError:
                pass
        elif command == 'refresh':
            active_device.signal('refresh_scene')
            self.channel("Refreshed.\n")
        else:
            self.channel("Error.\n")


class SVGWriter:
    @staticmethod
    def save_types():
        yield "Scalable Vector Graphics", "svg", "image/svg+xml"

    @staticmethod
    def versions():
        yield 'default'

    @staticmethod
    def save(kernel, f, version='default'):
        root = Element(SVG_NAME_TAG)
        root.set(SVG_ATTR_VERSION, SVG_VALUE_VERSION)
        root.set(SVG_ATTR_XMLNS, SVG_VALUE_XMLNS)
        root.set(SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK)
        root.set(SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV)
        root.set("xmlns:meerK40t", "https://github.com/meerk40t/meerk40t/wiki/Namespace")
        # Native unit is mils, these must convert to mm and to px
        mils_per_mm = 39.3701
        mils_per_px = 1000.0 / 96.0
        px_per_mils = 96.0 / 1000.0
        if kernel.device is None:
            kernel.setting(int, "bed_width", 320)
            kernel.setting(int, "bed_height", 220)
            mm_width = kernel.bed_width
            mm_height = kernel.bed_height
        else:
            kernel.device.setting(int, "bed_width", 320)
            kernel.device.setting(int, "bed_height", 220)
            mm_width = kernel.device.bed_width
            mm_height = kernel.device.bed_height
        root.set(SVG_ATTR_WIDTH, '%fmm' % mm_width)
        root.set(SVG_ATTR_HEIGHT, '%fmm' % mm_height)
        px_width = mm_width * mils_per_mm * px_per_mils
        px_height = mm_height * mils_per_mm * px_per_mils

        viewbox = '%d %d %d %d' % (0, 0, round(px_width), round(px_height))
        scale = 'scale(%f)' % px_per_mils
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = kernel.elements
        for element in elements:
            if isinstance(element, Path):
                subelement = SubElement(root, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d())
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                for key, val in element.values.items():
                    if key in ('stroke-width', 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            elif isinstance(element, SVGText):
                subelement = SubElement(root, SVG_TAG_TEXT)
                subelement.text = element.text
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                for key, val in element.values.items():
                    if key in ('stroke-width', 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio',
                               'font-family', 'font-size', 'font-weight'):
                        subelement.set(key, str(val))
            else:  # Image.
                subelement = SubElement(root, SVG_TAG_IMAGE)
                stream = BytesIO()
                element.image.save(stream, format='PNG')
                png = b64encode(stream.getvalue()).decode('utf8')
                subelement.set('xlink:href', "data:image/png;base64,%s" % (png))
                subelement.set(SVG_ATTR_X, '0')
                subelement.set(SVG_ATTR_Y, '0')
                subelement.set(SVG_ATTR_WIDTH, str(element.image.width))
                subelement.set(SVG_ATTR_HEIGHT, str(element.image.height))
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                for key, val in element.values.items():
                    if key in ('stroke-width', 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            stroke = str(element.stroke)
            fill = str(element.fill)
            if stroke == 'None':
                stroke = SVG_VALUE_NONE
            if fill == 'None':
                fill = SVG_VALUE_NONE
            subelement.set(SVG_ATTR_STROKE, stroke)
            subelement.set(SVG_ATTR_FILL, fill)
        tree = ElementTree(root)
        tree.write(f)


class SVGLoader:

    @staticmethod
    def load_types():
        yield "Scalable Vector Graphics", ("svg",), "image/svg+xml"

    @staticmethod
    def load(kernel, pathname):
        kernel.setting(int, "bed_width", 320)
        kernel.setting(int, "bed_height", 220)
        elements = []
        basename = os.path.basename(pathname)
        scale_factor = 1000.0 / 96.0
        svg = SVG.parse(source=pathname,
                        width='%fmm' % (kernel.bed_width),
                        height='%fmm' % (kernel.bed_height),
                        ppi=96.0,
                        transform='scale(%f)' % scale_factor)
        for element in svg.elements():
            if isinstance(element, SVGText):
                elements.append(element)
            elif isinstance(element, Path):
                elements.append(element)
            elif isinstance(element, Shape):
                e = Path(element)
                e.reify()  # In some cases the shape could not have reified, the path must.
                elements.append(e)
            elif isinstance(element, SVGImage):
                try:
                    element.load(os.path.dirname(pathname))
                    if element.image is not None:
                        elements.append(element)
                except OSError:
                    pass
        return elements, pathname, basename


class EgvLoader:

    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, pathname):
        elements = []
        basename = os.path.basename(pathname)

        for event in parse_egv(pathname):
            path = event['path']
            if len(path) > 0:
                elements.append(path)
                if 'speed' in event:
                    path.values['speed'] = event['speed']
            if 'raster' in event:
                raster = event['raster']
                image = raster.get_image()
                if image is not None:
                    elements.append(image)
                    if 'speed' in event:
                        image.values['speed'] = event['speed']
        return elements, pathname, basename


class RDLoader:
    @staticmethod
    def load_types():
        yield "RDWorks File", ("rd",), "application/x-rd"

    @staticmethod
    def load(kernel, pathname):
        basename = os.path.basename(pathname)
        ruidaemulator = RuidaEmulator()
        buffer = list()
        with open(pathname, 'rb') as f:
            while True:
                byte = f.read(1)
                if len(byte) == 0:
                    break
                buffer.append(ord(byte))
        elements = list(ruidaemulator.parse(bytes(buffer)))
        for e in elements:
            e.stroke = Color('black')
        return elements, pathname, basename


class ImageLoader:

    @staticmethod
    def load_types():
        yield "Portable Network Graphics", ("png",), "image/png"
        yield "Bitmap Graphics", ("bmp",), "image/bmp"
        yield "EPS Format", ("eps",), "image/eps"
        yield "GIF Format", ("gif",), "image/gif"
        yield "Icon Format", ("ico",), "image/ico"
        yield "JPEG Format", ("jpg", "jpeg", "jpe"), "image/jpeg"
        yield "Webp Format", ("webp",), "image/webp"

    @staticmethod
    def load(kernel, pathname):
        basename = os.path.basename(pathname)

        image = SVGImage({'href': pathname, 'width': "100%", 'height': "100%"})
        image.load()
        return [image], pathname, basename


class DxfLoader:

    @staticmethod
    def load_types():
        yield "Drawing Exchange Format", ("dxf",), "image/vnd.dxf"

    @staticmethod
    def load(kernel, pathname):
        """"
        Load dxf content. Requires ezdxf which tends to also require Python 3.6 or greater.

        Dxf data has an origin point located in the lower left corner. +y -> top
        """
        kernel.setting(int, "bed_width", 320)
        kernel.setting(int, "bed_height", 220)

        import ezdxf

        basename = os.path.basename(pathname)
        dxf = ezdxf.readfile(pathname)
        elements = []
        for entity in dxf.entities:

            try:
                entity.transform_to_wcs(entity.ocs())
            except AttributeError:
                pass
            if entity.dxftype() == 'CIRCLE':
                element = Circle(center=entity.dxf.center, r=entity.dxf.radius)
            elif entity.dxftype() == 'ARC':
                circ = Circle(center=entity.dxf.center,
                              r=entity.dxf.radius)
                element = Path(circ.arc_angle(Angle.degrees(entity.dxf.start_angle),
                                              Angle.degrees(entity.dxf.end_angle)))
            elif entity.dxftype() == 'ELLIPSE':
                # TODO: needs more math, axis is vector, ratio is to minor.
                element = Ellipse(center=entity.dxf.center,
                                  # major axis is vector
                                  # ratio is the ratio of major to minor.
                                  start_point=entity.start_point,
                                  end_point=entity.end_point,
                                  start_angle=entity.dxf.start_param,
                                  end_angle=entity.dxf.end_param)
            elif entity.dxftype() == 'LINE':
                #  https://ezdxf.readthedocs.io/en/stable/dxfentities/line.html
                element = SimpleLine(x1=entity.dxf.start[0], y1=entity.dxf.start[1],
                                     x2=entity.dxf.end[0], y2=entity.dxf.end[1])
            elif entity.dxftype() == 'LWPOLYLINE':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html
                points = list(entity)
                if entity.closed:
                    element = Polygon(*[(p[0], p[1]) for p in points])
                else:
                    element = Polyline(*[(p[0], p[1]) for p in points])
                # TODO: If bulges are defined they should be included as arcs.
            elif entity.dxftype() == 'HATCH':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html
                element = Path()
                if entity.bgcolor is not None:
                    Path.fill = Color(entity.bgcolor)
                for p in entity.paths:
                    if p.path_type_flags & 2:
                        for v in p.vertices:
                            element.line(v[0], v[1])
                        if p.is_closed:
                            element.closed()
                    else:
                        for e in p.edges:
                            if type(e) == "LineEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.LineEdge
                                element.line(e.start, e.end)
                            elif type(e) == "ArcEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.ArcEdge
                                circ = Circle(center=e.center,
                                              radius=e.radius, )
                                element += circ.arc_angle(Angle.degrees(e.start_angle), Angle.degrees(e.end_angle))
                            elif type(e) == "EllipseEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.EllipseEdge
                                element += Arc(radius=e.radius,
                                               start_angle=Angle.degrees(e.start_angle),
                                               end_angle=Angle.degrees(e.end_angle),
                                               ccw=e.is_counter_clockwise)
                            elif type(e) == "SplineEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.SplineEdge
                                if e.degree == 3:
                                    for i in range(len(e.knot_values)):
                                        control = e.control_values[i]
                                        knot = e.knot_values[i]
                                        element.quad(control, knot)
                                elif e.degree == 4:
                                    for i in range(len(e.knot_values)):
                                        control1 = e.control_values[2 * i]
                                        control2 = e.control_values[2 * i + 1]
                                        knot = e.knot_values[i]
                                        element.cubic(control1, control2, knot)
                                else:
                                    for i in range(len(e.knot_values)):
                                        knot = e.knot_values[i]
                                        element.line(knot)
            elif entity.dxftype() == 'IMAGE':
                bottom_left_position = entity.insert
                size = entity.image_size
                imagedef = entity.image_def_handle
                element = SVGImage(href=imagedef.filename,
                                   x=bottom_left_position[0],
                                   y=bottom_left_position[1] - size[1],
                                   width=size[0],
                                   height=size[1])
            elif entity.dxftype() == 'MTEXT':
                insert = entity.dxf.insert
                element = SVGText(x=insert[0], y=insert[1], text=entity.dxf.text)
            elif entity.dxftype() == 'TEXT':
                insert = entity.dxf.insert
                element = SVGText(x=insert[0], y=insert[1], text=entity.dxf.text)
            elif entity.dxftype() == 'POLYLINE':
                if entity.is_2d_polyline:
                    if entity.is_closed:
                        element = Polygon([(p[0], p[1]) for p in entity.points()])
                    else:
                        element = Polyline([(p[0], p[1]) for p in entity.points()])
            elif entity.dxftype() == 'SOLID' or entity.dxftype() == 'TRACE':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/solid.html
                element = Path()
                element.move((entity[0][0], entity[0][1]))
                element.line((entity[1][0], entity[1][1]))
                element.line((entity[2][0], entity[2][1]))
                element.line((entity[3][0], entity[3][1]))
                element.closed()
                element.fill = Color('Black')
            elif entity.dxftype() == 'SPLINE':
                element = Path()
                # TODO: Additional research.
                # if entity.dxf.degree == 3:
                #     element.move(entity.knots[0])
                #     print(entity.dxf.n_control_points)
                #     for i in range(1, entity.dxf.n_knots):
                #         print(entity.knots[i])
                #         print(entity.control_points[i-1])
                #         element.quad(
                #             entity.control_points[i-1],
                #             entity.knots[i]
                #         )
                # elif entity.dxf.degree == 4:
                #     element.move(entity.knots[0])
                #     for i in range(1, entity.dxf.n_knots):
                #         element.quad(
                #             entity.control_points[2 * i - 2],
                #             entity.control_points[2 * i - 1],
                #             entity.knots[i]
                #         )
                # else:
                element.move(entity.control_points[0])
                for i in range(1, entity.dxf.n_control_points):
                    element.line(entity.control_points[i])
                if entity.closed:
                    element.closed()
            else:
                continue
                # Might be something unsupported.
            if entity.rgb is not None:
                element.stroke = Color(entity.rgb)
            else:
                element.stroke = Color('black')
            element.transform.post_scale(MILS_PER_MM, -MILS_PER_MM)
            element.transform.post_translate_y(kernel.bed_height * MILS_PER_MM)
            if isinstance(element, SVGText):
                elements.append(element)
            else:
                elements.append(abs(Path(element)))

        return elements, pathname, basename
