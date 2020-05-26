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
            s = self.device.interpreter.parse_power
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
                    spooler.add_command(COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1])
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
                        spooler.add_command(COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1])
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
                        spooler.add_command(COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1])
                elif v == 28.3:
                    spooler.add_command(COMMAND_MODE_RAPID)
                    spooler.add_command(COMMAND_HOME)
                    if self.home_adjust is not None:
                        spooler.add_command(COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1])
                    if 'x' in gc:
                        x = gc['x'].pop(0)
                        if len(gc['x']) == 0:
                            del gc['x']
                        if x is None:
                            x = 0
                        spooler.add_command(COMMAND_MOVE, x, 0)
                    if 'y' in gc:
                        y = gc['y'].pop(0)
                        if len(gc['y']) == 0:
                            del gc['y']
                        if y is None:
                            y = 0
                        spooler.add_command(COMMAND_MOVE, 0, y)
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
                        spooler.add_command(COMMAND_MOVE, self.home_adjust[0], self.home_adjust[1])
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
                    self.feed_invert = lambda s: s * (self.scale * 60.0)
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
                spooler.add_command(COMMAND_MOVE, x, y)
            elif self.move_mode == 1:
                if self.on_mode:
                    spooler.add_command(COMMAND_LASER_ON)
                spooler.add_command(COMMAND_MOVE, x, y)
            elif self.move_mode == 2:
                spooler.add_command(COMMAND_MOVE, x, y)  # TODO: Implement CW_ARC
            elif self.move_mode == 3:
                spooler.add_command(COMMAND_MOVE, x, y)  # TODO: Implement CCW_ARC
        return 0


class RuidaEmulator(Module):

    def __init__(self):
        Module.__init__(self)
        self.channel = lambda e: e
        self.path_d = list()
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.u = 0.0

        self.name = ''
        self.speed = 20.0
        self.power1_min = 0
        self.power2_min = 0
        self.power1_max = 0
        self.power2_max = 0

    def initialize(self):
        self.channel = self.device.channel_open('ruida')

    @staticmethod
    def signed32(v):
        v &= 0xFFFFFFFF
        if v > 0x7FFFFFFF:
            return - 0x80000000 + v
        else:
            return v

    @staticmethod
    def signed14(v):
        v &= 0x7FFF
        if v > 0x1FFF:
            return - 0x4000 + v
        else:
            return v

    @staticmethod
    def decode14(data):
        return RuidaEmulator.signed14((data[0] & 0x7F) << 7 | (data[1] & 0x7F))

    @staticmethod
    def udecode14(data):
        return (data[0] & 0x7F) << 7 | (data[1] & 0x7F)

    @staticmethod
    def encode14(v):
        return [
            (v >> 7) & 0x7F,
            v & 0x7F,
        ]

    @staticmethod
    def decode32(data):
        return RuidaEmulator.signed32((data[0] & 0x7F) << 28 |
                                      (data[1] & 0x7F) << 21 |
                                      (data[2] & 0x7F) << 14 |
                                      (data[3] & 0x7F) << 7 |
                                      (data[4] & 0x7F))

    @staticmethod
    def encode32(v):
        return [
            (v >> 28) & 0x7F,
            (v >> 21) & 0x7F,
            (v >> 14) & 0x7F,
            (v >> 7) & 0x7F,
            v & 0x7F,
        ]

    def abscoord(self, data):
        return RuidaEmulator.decode32(data)

    def relcoord(self, data):
        return RuidaEmulator.decode14(data)

    def parse_filenumber(self, data):
        return RuidaEmulator.decode14(data)

    def parse_speed(self, data):
        return RuidaEmulator.decode32(data)

    def parse_power(self, data):
        return RuidaEmulator.udecode14(data)

    def parse_commands(self, f):
        array = list()
        while True:
            byte = f.read(1)
            if len(byte) == 0:
                break
            byte = self.unswizzle_byte(ord(byte))
            if byte >= 0x80 and len(array) > 0:
                yield array
                array.clear()
            array.append(byte)
        if len(array) > 0:
            yield array

    def checksum_parse(self, sent_data, reply=None, channel=None, elements=None):
        if channel is None:
            channel = self.channel
        if reply is None:
            reply = lambda e: e
        if elements is None:
            elements = lambda e: e
        data = sent_data[2:1472]
        checksum_check = (sent_data[0] & 0xFF) << 8 | sent_data[1] & 0xFF
        checksum_sum = sum(data) & 0xFFFF
        if checksum_check == checksum_sum:
            response = b'\xCC'
            reply(self.swizzle(response))
            channel("<-- " + str(response.hex()))
            channel("    checksum match")
        else:
            response = b'\xCF'
            reply(self.swizzle(response))
            channel("--> " + str(data.hex()))
            channel("<-- " + str(response.hex()))
            channel("    checksum fail (%d != %d)" % (checksum_sum, checksum_check))
            return
        self.parse(BytesIO(data), reply=reply, channel=channel, elements=elements)

    def parse(self, data, reply=None, channel=None, elements=None):
        um_per_mil = 25.4
        if channel is None:
            channel = self.channel
        if reply is None:
            reply = lambda e: e
        if elements is None:
            elements = lambda e: e
        path_d = self.path_d

        for array in self.parse_commands(data):
            channel("--> " + str(bytes(array).hex()))
            if array[0] < 0x80:
                raise ValueError("Not a command.")
            elif array[0] == 0x88:  # 0b10001000 11 characters.
                self.x = self.abscoord(array[1:6]) / um_per_mil
                self.y = self.abscoord(array[6:11]) / um_per_mil
                if len(path_d) != 0:
                    path = Path(' '.join(path_d))
                    path.values['name'] = self.name
                    path.values['speed'] = self.speed
                    path.values['power'] = self.power1_min
                    path.values['power_range'] = (self.power1_min, self.power2_min, self.power1_max, self.power2_max)
                    path.stroke = Color('black')
                    elements(path)
                    path_d.clear()
                path_d.append("M%f,%f" % (self.x, self.y))
                channel("    Move Absolute %d %d" % (self.x, self.y))
            elif array[0] == 0x89:  # 0b10001001 5 characters
                dx = self.relcoord(array[1:3]) / um_per_mil
                dy = self.relcoord(array[3:5]) / um_per_mil
                if len(path_d) != 0:
                    path = Path(' '.join(path_d))
                    path.values['name'] = self.name
                    path.values['speed'] = self.speed
                    path.values['power'] = self.power1_min
                    path.values['power_range'] = (self.power1_min, self.power2_min, self.power1_max, self.power2_max)
                    path.stroke = Color('black')
                    elements(path)
                    path_d.clear()
                self.x += dx
                self.y += dy
                path_d.append("M%f,%f" % (self.x, self.y))
                channel("    Move Relative %f %f" % (dx, dy))
            elif array[0] == 0xA8:  # 0b10101000 11 characters.
                self.x = self.abscoord(array[1:6]) / um_per_mil
                self.y = self.abscoord(array[6:11]) / um_per_mil
                path_d.append("L%0.4f,%0.4f" % (self.x, self.y))
                channel("    Cut Absolute %g %g" % (self.x, self.y))
            elif array[0] == 0xA9:  # 0b10101001 5 characters
                dx = self.relcoord(array[1:3]) / um_per_mil
                dy = self.relcoord(array[3:5]) / um_per_mil
                path_d.append("l%0.4f,%0.4f" % (dx, dy))
                self.x += dx
                self.y += dy
                channel("    Cut Relative %g %g" % (dx, dy))
            elif array[0] == 0xAA:  # 0b10101010 3 characters
                dx = self.relcoord(array[1:3]) / um_per_mil
                path_d.append("h%0.4f" % (dx))
                self.x += dx
                channel("    Horizontal cut to relative %g" % (dx))
            elif array[0] == 0xAB:  # 0b10101011 3 characters
                dy = self.relcoord(array[1:3]) / um_per_mil
                path_d.append("v%0.4f" % (dy))
                self.y += dy
                channel("    Vertical cut to relative %g" % (dy))
            elif array[0] == 0xC6:  # 0b11000110 4 characters
                if array[1] == 0x01:
                    self.power1_min = self.parse_power(array[2:4])
                    channel("    (1st laser source min power: %d)" % self.power1_min)
                elif array[1] == 0x02:
                    self.power1_max = self.parse_power(array[2:4])
                    channel("    (1st laser source max power: %d)" % self.power1_max)
                elif array[1] == 0x05:
                    power = self.parse_power(array[2:4])
                    channel("    (c6 05 power: %f)" % power)
                elif array[1] == 0x06:
                    power = self.parse_power(array[2:4])
                    channel("    (c6 06 power: %f)" % power)
                elif array[1] == 0x07:
                    power = self.parse_power(array[2:4])
                    channel("    (c6 07 power: %f)" % power)
                elif array[1] == 0x08:
                    power = self.parse_power(array[2:4])
                    channel("    (c6 08 power: %f)" % power)
                elif array[1] == 0x15:
                    channel("    C6 15")
                elif array[1] == 0x16:
                    channel("    C6 16")
                elif array[1] == 0x21:
                    self.power2_min = self.parse_power(array[2:4])
                    channel("    (2nd laser source min power: %d)" % self.power2_min)
                elif array[1] == 0x22:
                    self.power2_max = self.parse_power(array[2:4])
                    channel("    (2nd laser source max power: %d)" % self.power2_max)
                elif array[1] == 0x31:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    1 C6 31 (%f)" % (c_x))
                elif array[1] == 0x32:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    2 C6 32 (%f)" % (c_x))
                elif array[1] == 0x41:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    3 C6 41 (%f)" % (c_x))
                elif array[1] == 0x42:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    4 C6 42 (%f)" % (c_x))
                elif array[1] == 0x35:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    5 C6 35 (%f)" % (c_x))
                elif array[1] == 0x36:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    6 C6 36 (%f)" % (c_x))
                elif array[1] == 0x37:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    7 C6 37 (%f)" % (c_x))
                elif array[1] == 0x38:
                    c_x = self.relcoord(array[2:5]) / um_per_mil
                    channel("    8 C6 38 (%f)" % (c_x))
            elif array[0] == 0xC9:  # 0b11001001 - 7 or 8 characters
                if array[1] == 0x02:
                    # Speed in micrometers/sec
                    speed = self.parse_speed(array[2:7]) / 1000.0
                    channel("    Speed set at %f" % speed)
                if array[1] == 0x04:
                    if array[2] == 0x00:
                        # speed in micrometers/sec
                        speed = self.parse_speed(array[3:8]) / 1000.0
                        channel("    Speed set at %f" % speed)
            elif array[0] == 0xCA:
                if array[1] == 0x01:
                    channel("    CA 01 coords (%d)" % (array[2]))
                elif array[1] == 0x02:
                    channel("    CA 02 coords (%d)" % (array[2]))
                elif array[1] == 0x03:
                    channel("    CA 03 coords (%d)" % (array[2]))
                elif array[1] == 0x06:
                    c_x = self.abscoord(array[2:7]) / um_per_mil
                    channel("    CA 06 coords (%f)" % (c_x))
                elif array[1] == 0x10:
                    channel("    CA 10 coords (%d)" % (array[2]))
                elif array[1] == 0x22:
                    channel("    CA 22 coords (%d)" % (array[2]))
                elif array[1] == 0x41:
                    channel("    CA 41 coords (%d,%d)" % (array[2], array[3]))
            elif array[0] == 0xCC:  # 0b11001100
                channel("    ACK from machine")
            elif array[0] == 0xCD:  # 0b11001101
                channel("    ERR from machine")
            elif array[0] == 0xD7:  # D7 or EB Finished?
                if len(path_d) != 0:
                    path = Path(' '.join(path_d))
                    path.values['name'] = self.name
                    path.values['speed'] = self.speed
                    path.values['power'] = self.power1_min
                    path.values['power_range'] = (self.power1_min, self.power2_min, self.power1_max, self.power2_max)
                    path.stroke = Color('black')
                    elements(path)
                    path_d.clear()
                channel("    Final Command")
            elif array[0] == 0xD8:
                if array[1] == 0x00:
                    channel("    Program Item 5")
                if array[1] == 0x12:
                    channel("    Program Item 1")
                if array[1] == 0x2C:
                    channel("    Home Z")
                if array[1] == 0x2D:
                    channel("    Home U")
                if array[1] == 0x2E:
                    channel("    Focus")
            elif array[0] == 0xD9:
                if array[1] == 0x00:
                    self.x = self.abscoord(array[3:8]) / um_per_mil
                    path_d.append("M%04f,%04f" % (self.x, self.y))
                    if array[2] == 0x03:
                        channel("    Move Light X: %d" % self.x)
                    elif array[2] == 0x02:
                        channel("    Move X: %f" % self.x)
                    elif array[2] == 0x01:
                        channel("    Move Light/Origin X: %f" % self.y)
                    elif array[2] == 0x00:
                        channel("    Move Origin X: %f" % self.x)
                if array[1] == 0x01:
                    self.y = self.abscoord(array[3:8]) / um_per_mil
                    path_d.append("M%04f,%04f" % (self.x, self.y))
                    if array[2] == 0x03:
                        channel("    Move Light Y: %f" % self.y)
                    elif array[2] == 0x02:
                        channel("    Move Y: %f" % self.y)
                    elif array[2] == 0x01:
                        channel("    Move Light/Origin Y: %f" % self.y)
                    elif array[2] == 0x00:
                        channel("    Move Origin Y: %f" % self.y)
                if array[1] == 0x02:
                    self.z = self.abscoord(array[3:8]) / um_per_mil
                    if array[2] == 0x03:
                        channel("    Move Light Z: %f" % self.z)
                    elif array[2] == 0x02:
                        channel("    Move Z: %f" % self.z)
                    elif array[2] == 0x01:
                        channel("    Move Light/Origin Z: %f" % self.z)
                    elif array[2] == 0x00:
                        channel("    Move Origin Z: %f" % self.z)
                if array[1] == 0x03:
                    self.u = self.abscoord(array[3:8]) / um_per_mil
                    if array[2] == 0x03:
                        channel("    Move Light U: %f" % self.u)
                    elif array[2] == 0x02:
                        channel("    Move U: %f" % self.u)
                    elif array[2] == 0x01:
                        channel("    Move Light/Origin U: %f" % self.u)
                    elif array[2] == 0x00:
                        channel("    Move Origin U: %f" % self.u)
                if array[1] == 0x10:
                    if array[2] == 0x01:
                        channel("    Home XY")
                        self.x = 0
                        self.y = 0
                        path_d.append("M%04f,%04f" % (self.x, self.y))
            elif array[0] == 0xDA:
                if array[1] == 0x00:
                    channel("    get %02x %02x from machine" % (array[2], array[3]))
                    v = 0
                    name = "UNMAPPED"
                    if array[2] == 0x00:
                        if array[3] == 0x04:
                            name = "Items 1 & 6"
                            v = 0x00000000
                        if array[3] == 0x05:
                            name = "00 05 UNKNOWN"
                            v = 0x00000000
                        if array[3] == 0x20:
                            name = "X Position Request"
                            v = 0x00000000
                        if array[3] == 0x21:
                            name = "Item 4"
                            v = 0x00000000
                        if array[3] == 0x26:
                            name = "Item 2"
                            v = 0x00000000
                        if array[3] == 0x30:
                            name = "Y Position Request"
                            v = 0x00000000
                        if array[3] == 0x31:
                            name = "Item 5"
                            v = 0x00000000
                        if array[3] == 0x36:
                            name = "Item 3"
                            v = 0x00000000
                        if array[3] == 0x40:
                            name = "Z Position Request"
                            v = 0x00000000
                        if array[3] == 0x50:
                            name = "U Position Request"
                            v = 0x00000000
                    if array[2] == 0x04:
                        if array[3] == 0x00:
                            name = "Reply 22"
                            v = 0x00000022
                        if array[3] == 0x05:
                            name = "Previous Work Time"
                            v = 0x00000000  # work time in seconds
                        if array[3] == 0x08:
                            name = "Previous Work Time2"
                            v = 0x00000000  # work time in seconds
                        if array[3] == 0x21:
                            name = "Position X"
                            v = 0x00000000
                        if array[3] == 0x31:
                            name = "Position Y"
                            v = 0x00000000
                        if array[3] == 0x41:
                            name = "Position Z"
                            v = 0x00000000
                        if array[3] == 0x51:
                            name = "Position U"
                            v = 0x00000000
                    if array[2] == 0x05:
                        if array[3] == 0x7e:
                            name = "0x65006500"
                            v = 0x65006500  # Other answers force fail.
                    if array[2] == 0x0B:
                        if array[3] == 0x12:
                            name = "Item 0B12-5B"
                    response = b'\xDA\x01' + bytes(array[2:4]) + bytes(RuidaEmulator.encode32(v))
                    channel("<-- " + str(response.hex()))
                    reply(self.swizzle(response))
                    channel("     Responding %02x %02x(%s) equals %d (%08x)" % (array[2], array[3], name, v, v))
                elif array[1] == 0x01:
                    channel("    response to DA 00 XX XX <VALUE")
            elif array[0] == 0xE7:
                if array[1] == 0x00:
                    channel("    E7 00 Finishing.")
                elif array[1] == 0x03:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Program Item 7 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x04:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    c_z = self.abscoord(array[11:16]) / um_per_mil
                    channel("    Program Item 11 (%f,%f,%f)" % (c_x, c_y, c_z))
                elif array[1] == 0x05:
                    channel("    Program Item 12 (%d)" % (array[2]))
                elif array[1] == 0x06:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Program Item 6 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x07:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Program Item 8 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x08:  # Same value given to F2 05
                    channel("    E7 08 (14 characters)")
                elif array[1] == 0x13:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    E7 13 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x17:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    E7 17 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x23:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    E7 23 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x24:
                    channel("    E7 24 (%d)" % (array[2]))
                elif array[1] == 0x50:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Program Item 9 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x51:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Program Item 10 (%f,%f)" % (c_x, c_y))
                elif array[1] == 0x52:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Coord 52: %f %f" % (c_x, c_y))
                elif array[1] == 0x53:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Coord 53: %f %f" % (c_x, c_y))
                elif array[1] == 0x54:
                    if array[2] == 0x00:
                        c_x = self.abscoord(array[3:8]) / um_per_mil
                        channel("    Coord 54 00: %f" % (c_x))
                    if array[2] == 0x01:
                        c_x = self.abscoord(array[3:8]) / um_per_mil
                        channel("    Coord 54 01: %f" % (c_x))
                elif array[1] == 0x55:
                    if array[2] == 0x00:
                        c_x = self.abscoord(array[3:8]) / um_per_mil
                        channel("    Coord 55 00: %f" % (c_x))
                    if array[2] == 0x01:
                        c_x = self.abscoord(array[3:8]) / um_per_mil
                        channel("    Coord 55 01: %f" % (c_x))
                elif array[1] == 0x60:
                    channel("    E7 60 (%d)" % (array[2]))
                elif array[1] == 0x61:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Coord 61: %f %f" % (c_x, c_y))
                elif array[1] == 0x62:
                    c_x = self.abscoord(array[1:6]) / um_per_mil
                    c_y = self.abscoord(array[6:11]) / um_per_mil
                    channel("    Coord 62: %f %f" % (c_x, c_y))
                else:
                    channel("    Unknown E7 Command!")
            elif array[0] == 0xE8:
                if array[1] == 0x01:
                    for a in array[4:]:
                        if a == 0x00:
                            break
                        self.name += ord(a)
                    channel("    Read filename number: %d" % (self.parse_filenumber(array[1:3])))
                if array[1] == 0x02:
                    if array[2] == 0xE7:
                        if array[3] == 0x01:
                            self.name = ""
                            for a in array[4:]:
                                if a == 0x00:
                                    break
                                self.name += ord(a)
                            channel("    Set filename for transfer: %s" % self.name)
            elif array[0] == 0xEA:
                channel("    EA (%d)" % (array[1]))
            elif array[0] == 0xEB:
                channel("    EB Stop cutting commands.")
            elif array[0] == 0xF0:
                channel("    Program Item 2")
            elif array[0] == 0xF1:
                if array[1] == 0x00:
                    channel("    F1 00 (%d)" % (array[2]))
                if array[1] == 0x01:
                    channel("    F1 01 (%d)" % (array[2]))
                if array[1] == 0x02:
                    channel("    Program Item 3 (%d)" % array[2])
                if array[1] == 0x03:
                    c_x = self.abscoord(array[2:7]) / um_per_mil
                    c_y = self.abscoord(array[7:12]) / um_per_mil
                    channel("    F1 03 (%f,%f)" % (c_x, c_y))
                if array[1] == 0x04:
                    channel("    Program Item 4 (%d)" % array[2])
                if array[1] == 0x20:
                    channel("    F1 10 (%d,%d)" % (array[2],  array[3]))
            elif array[0] == 0xF2:
                if array[1] == 0x00:
                    channel("    F2 00 (%d)" % (array[2]))
                if array[1] == 0x01:
                    channel("    F2 01 (%d)" % (array[2]))
                if array[1] == 0x02:
                    c_x = self.abscoord(array[2:7]) / um_per_mil
                    c_y = self.abscoord(array[7:12]) / um_per_mil
                    channel("    F2 02 (%f,%f)" % (c_x, c_y))
                if array[1] == 0x03:
                    c_x = self.abscoord(array[2:7]) / um_per_mil
                    c_y = self.abscoord(array[7:12]) / um_per_mil
                    channel("    F2 03 (%f,%f)" % (c_x, c_y))
                if array[1] == 0x04:
                    c_x = self.abscoord(array[2:7]) / um_per_mil
                    c_y = self.abscoord(array[7:12]) / um_per_mil
                    channel("    F2 04 (%f,%f)" % (c_x, c_y))
                if array[1] == 0x05:
                    channel("    F2 05 (14 characters)")
                if array[1] == 0x06:
                    c_x = self.abscoord(array[2:7]) / um_per_mil
                    c_y = self.abscoord(array[7:12]) / um_per_mil
                    channel("    F2 06 (%f,%f)" % (c_x, c_y))
                if array[1] == 0x07:
                    channel("    F2 07 (%d)" % (array[2]))
            else:
                channel("    Unknown Command!")

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
            try:
                if element.values['visibility'] == 'hidden':
                    continue
            except KeyError:
                pass
            except AttributeError:
                pass
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
        elements = list()
        with open(pathname, 'rb') as f:
            ruidaemulator.parse(f, elements=elements.append)
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
