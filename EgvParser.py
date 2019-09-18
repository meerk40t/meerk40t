#!/usr/bin/env python

from LaserCommandConstants import *

CMD_RIGHT = b'B'
CMD_LEFT = b'T'
CMD_TOP = b'L'
CMD_BOTTOM = b'R'

CMD_FINISH = b'F'
CMD_ANGLE = b'M'

CMD_RESET = b'@'

CMD_ON = b'D'
CMD_OFF = b'U'
CMD_P = b'P'
CMD_G = b'G'
CMD_INTERRUPT = b'I'
CMD_N = b'N'
CMD_CUT = b'C'
CMD_VELOCITY = b'V'
CMD_S = b'S'
CMD_E = b'E'


class EgvParser:
    def __init__(self):
        self.command = None
        self.distance = 0
        self.number_value = 0

    @staticmethod
    def skip(read, byte, count):
        """Skips forward in the file until we find <count> instances of <byte>"""
        pos = read.tell()
        while count > 0:
            char = read.read(1)
            if char == byte:
                count -= 1
            if char is None or len(char) == 0:
                read.seek(pos, 0)
                # If we didn't skip the right stuff, reset the position.
                break

    def skip_header(self, file):
        self.skip(file, b'\n', 3)
        self.skip(file, b'%', 5)

    def parse(self, f):
        while True:
            byte = f.read(1)
            if byte is None or len(byte) == 0:
                break
            value = ord(byte)
            if ord('0') <= value <= ord('9'):
                self.append_digit(value - ord('0'))  # '0' = 0
                continue
            if ord('a') <= value <= ord('y'):
                self.append_distance(value - ord('a') + 1)  # 'a' = 1, not zero.
                continue
            if ord('A') <= value <= ord('Z') or value == ord('@'):
                if self.command is not None:
                    yield [self.command, self.distance, self.number_value]
                self.distance = 0
                self.number_value = 0
                self.command = byte
                continue
            if value == ord('z'):
                self.append_distance(255)
            if value == ord('|'):
                byte = f.read(1)
                if byte is None or len(byte) == 0:
                    break
                value = ord(byte)
                self.append_distance(25 + value - ord('a') + 1)  # '|a' = 27, not 26
        if self.command is not None:
            yield [self.command, self.distance, self.number_value]

    def append_digit(self, value):
        self.number_value *= 10
        self.number_value += value

    def append_distance(self, amount):
        self.distance += amount


def parse_egv(f):
    if isinstance(f, str):
        with open(f, "rb") as f:
            for element in parse_egv(f):
                yield element
        return
    try:
        if isinstance(f, unicode):
            with open(f, "rb") as f:
                for element in parse_egv(f):
                    yield element
            return
    except NameError:
        pass  # Must be Python 3.

    egv_parser = EgvParser()

    egv_parser.skip_header(f)

    speed_code = None
    value_g = 0
    is_compact = False
    is_on = False
    is_left = False
    is_top = False
    is_speed = False
    is_cut = False
    is_harmonic = False
    is_finishing = False
    is_resetting = False
    value_s = -1
    yield COMMAND_SET_INCREMENTAL, ()
    for commands in egv_parser.parse(f):
        cmd = commands[0]
        distance = commands[1] + commands[2]
        if cmd is None:
            return
        elif cmd == CMD_RIGHT:  # move right
            if is_compact and is_harmonic and is_left:
                if is_top:
                    yield COMMAND_VSTEP, (-value_g)
                else:
                    yield COMMAND_VSTEP, (value_g)
                yield COMMAND_LASER_OFF, ()
                is_on = False
            yield COMMAND_MOVE, (distance, 0)
            is_left = False
        elif cmd == CMD_LEFT:  # move left
            if is_compact and is_harmonic and not is_left:
                if is_top:
                    yield COMMAND_VSTEP, (-value_g)
                else:
                    yield COMMAND_VSTEP, (value_g)
                yield COMMAND_LASER_OFF, ()
                is_on = False
            yield COMMAND_MOVE, (-distance, 0)
            is_left = True
        elif cmd == CMD_BOTTOM:  # move bottom
            if is_compact and is_harmonic and is_top:
                if is_left:
                    yield COMMAND_HSTEP, (-value_g)
                else:
                    yield COMMAND_HSTEP, (value_g)
                yield COMMAND_LASER_OFF, ()
                is_on = False
            yield COMMAND_MOVE, (0, distance)
            is_top = False
        elif cmd == CMD_TOP:  # move top
            if is_compact and is_harmonic and not is_top:
                if is_left:
                    yield COMMAND_HSTEP, (-value_g)
                else:
                    yield COMMAND_HSTEP, (value_g)
                yield COMMAND_LASER_OFF, ()
                is_on = False
            yield COMMAND_MOVE, (0, -distance)
            is_top = True
        elif cmd == CMD_ANGLE:
            if is_left:
                distance_x = -distance
            else:
                distance_x = distance
            if is_top:
                distance_y = -distance
            else:
                distance_y = distance
            yield COMMAND_MOVE, (distance_x, distance_y)
        elif cmd == CMD_ON:  # laser on
            is_on = True
            yield COMMAND_LASER_ON, ()
        elif cmd == CMD_OFF:  # laser off
            is_on = False
            yield COMMAND_LASER_OFF, ()
        elif cmd == CMD_S:  # s command
            value_s = commands[2]  # needed to know which E we are performing.
        elif cmd == CMD_E:  # slow
            is_compact = True
            if is_finishing or is_resetting:
                is_resetting = False
                is_compact = False
                is_on = False
                is_left = False
                is_top = False
                is_speed = False
                speed_code = None
                is_cut = False
                is_harmonic = False
            if is_finishing:
                is_finishing = False
                break
            yield COMMAND_SET_STEP, (value_g)
            yield COMMAND_SET_SPEED, (speed_code)
            yield COMMAND_MODE_COMPACT, ()
        elif cmd == CMD_FINISH:  # finish
            is_compact = True
            yield COMMAND_MODE_DEFAULT, ()
        elif cmd == CMD_P:  # pop
            is_compact = False
            yield COMMAND_MODE_DEFAULT, ()
        elif cmd == CMD_INTERRUPT:  # interrupt
            pass
        elif cmd == CMD_CUT:  # cut
            is_harmonic = False
            is_cut = True
            value_g = 0
            if speed_code is None:
                speed_code = ""
            speed_code += 'C'
        elif cmd == CMD_VELOCITY:  # velocity
            is_speed = True
            if speed_code is None:
                speed_code = ""
            speed_code += 'V%d' % commands[2]
        elif cmd == CMD_G:  # engrave
            is_harmonic = True
            value_g = commands[2]
            if speed_code is None:
                speed_code = ""
            speed_code += "G%03d" % value_g
        elif cmd == CMD_N:  # next
            is_compact = False
            yield COMMAND_MODE_DEFAULT, ()
        elif cmd == CMD_RESET:  # reset
            is_resetting = True
    yield COMMAND_SET_ABSOLUTE, ()