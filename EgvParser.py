#!/usr/bin/env python

from LaserSpeed import LaserSpeed
from path import Path

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
                    yield self.command, self.distance, self.number_value
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
            yield self.command, self.distance, self.number_value

    def append_digit(self, value):
        self.number_value *= 10
        self.number_value += value

    def append_distance(self, amount):
        self.distance += amount


class EgvPlotter:
    def __init__(self, x=0, y=0):
        self.path = Path()
        self.x = x
        self.y = y
        self.cutting = False
        self.data = {"path": self.path}

    def cut(self, dx, dy):
        if dx == 0 and dy == 0:
            return  # Just setting the directions.
        if self.cutting:
            self.path.line((self.x, self.y), (self.x + dx, self.y + dy))
        else:
            self.path.move((self.x, self.y), (self.x + dx, self.y + dy))
        self.x += dx
        self.y += dy

    def off(self):
        self.cutting = False

    def on(self):
        self.path.move((self.x, self.y), (self.x, self.y))
        self.cutting = True


def parse_egv(f, board="M2"):
    if isinstance(f, str):
        with open(f, "rb") as f:
            for element in parse_egv(f, board=board):
                yield element
        return
    try:
        if isinstance(f, unicode):
            with open(f, "rb") as f:
                for element in parse_egv(f, board=board):
                    yield element
            return
    except NameError:
        pass  # Must be Python 3.

    egv_parser = EgvParser()
    egv_parser.skip_header(f)
    speed_code = None
    is_compact = False
    is_left = False
    is_top = False
    is_reset = False
    obj = EgvPlotter()

    for commands in egv_parser.parse(f):
        cmd = commands[0]
        distance = commands[1] + commands[2]
        if cmd is None:
            return
        elif cmd == CMD_RIGHT:  # move right
            obj.cut(distance, 0)
            is_left = False
        elif cmd == CMD_LEFT:  # move left
            obj.cut(-distance, 0)
            is_left = True
        elif cmd == CMD_BOTTOM:  # move bottom
            obj.cut(0, distance)
            is_top = False
        elif cmd == CMD_TOP:  # move top
            obj.cut(0, -distance)
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
            obj.cut(distance_x, distance_y)
        elif cmd == CMD_ON:  # laser on
            obj.on()
        elif cmd == CMD_OFF:  # laser off
            obj.off()
        elif cmd == CMD_S:  # slow
            if commands[2] == 1:
                is_reset = False
                is_compact = True
                yield obj.data
                obj = EgvPlotter(obj.x, obj.y)
                code_value, gear, step_value, diagonal, raster_step = LaserSpeed.parse_speed_code(speed_code)
                b, m, gear = LaserSpeed.get_gearing(board, gear=gear, uses_raster_step=raster_step != 0)
                speed = LaserSpeed.get_speed_from_value(code_value, b, m)
                obj.data['step'] = raster_step
                obj.data['speed'] = speed
            else:
                if not is_compact and not is_reset:
                    is_compact = True  # We jumped out of compact, but then back in.
        elif cmd == CMD_N:
            if is_compact:
                is_compact = False
        elif cmd == CMD_FINISH or cmd == CMD_RESET:  # next
            is_reset = True
            if is_compact:
                is_compact = False
                yield obj.data
                obj = EgvPlotter(obj.x, obj.y)
        elif cmd == CMD_CUT:  # Speed code element
            if speed_code is None:
                speed_code = ""
            speed_code += 'C'
        elif cmd == CMD_VELOCITY:  # Speed code element
            if speed_code is None:
                speed_code = ""
            speed_code += 'V%d' % commands[2]
        elif cmd == CMD_G:  # Speed code element
            value_g = commands[2]
            if speed_code is None:
                speed_code = ""
            speed_code += "G%03d" % value_g
        elif cmd == CMD_E:  # e command
            pass
        elif cmd == CMD_P:  # pop
            pass
        elif cmd == CMD_INTERRUPT:  # interrupt
            pass
    yield obj.data
