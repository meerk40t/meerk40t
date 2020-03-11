#!/usr/bin/env python

from LaserSpeed import LaserSpeed
from svgelements import *

CMD_RIGHT = ord(b'B')
CMD_LEFT = ord(b'T')
CMD_TOP = ord(b'L')
CMD_BOTTOM = ord(b'R')

CMD_FINISH = ord(b'F')
CMD_ANGLE = ord(b'M')

CMD_RESET = ord(b'@')

CMD_ON = ord(b'D')
CMD_OFF = ord(b'U')
CMD_P = ord(b'P')
CMD_G = ord(b'G')
CMD_INTERRUPT = ord(b'I')
CMD_N = ord(b'N')
CMD_CUT = ord(b'C')
CMD_VELOCITY = ord(b'V')
CMD_S = ord(b'S')
CMD_E = ord(b'E')


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
            b = f.read(1024)
            for byte in b:
                if isinstance(byte, str):
                    byte = ord(byte)  # Python 2.7
                value = byte
                if ord('0') <= value <= ord('9'):
                    self.append_digit(value - ord('0'))  # '0' = 0
                elif ord('a') <= value <= ord('y'):
                    self.append_distance(value - ord('a') + 1)  # 'a' = 1, not zero.
                elif ord('A') <= value <= ord('Z') or value == ord('@'):
                    if self.command is not None:
                        yield self.command, self.distance, self.number_value
                    self.distance = 0
                    self.number_value = 0
                    self.command = byte
                elif value == ord('z'):
                    self.append_distance(255)
                elif value == ord('|'):
                    self.append_distance(26)
            if len(b) == 0:
                return

    def append_digit(self, value):
        self.number_value *= 10
        self.number_value += value

    def append_distance(self, amount):
        self.distance += amount


class EgvRaster:
    def __init__(self):
        self.tiles = {}
        self.min_x = None
        self.min_y = None
        self.max_x = None
        self.max_y = None
        self.bytes = None

    def get_tile(self, x, y, create=True):
        tile_x = x
        tile_y = y
        tile_key = (tile_x & 0xFFFFF000) | (tile_y & 0xFFF)
        if tile_key in self.tiles:
            tile = self.tiles[tile_key]
        else:
            if not create:
                return None
            tile = [0] * (0xFFF + 1)
            self.tiles[tile_key] = tile
        return tile

    def __setitem__(self, key, value):
        x, y = key
        tile = self.get_tile(x, y, True)
        tindex = x & 0xFFF
        tile[tindex] = value
        if self.min_x is None or self.min_x > x:
            self.min_x = x
        if self.min_y is None or self.min_y > y:
            self.min_y = y
        if self.max_x is None or self.max_x < x:
            self.max_x = x
        if self.max_y is None or self.max_y < x:
            self.max_y = x
        self.bytes = None

    def __getitem__(self, item):
        x, y = item
        if self.min_x <= x <= self.max_x and self.min_y <= x <= self.max_y:
            tile = self.get_tile(x, y, False)
            if tile is None:
                return 0
            tindex = x & 0xFFF
            return tile[tindex]
        return 0

    @property
    def width(self):
        if self.max_x is None:
            return 0
        return self.max_x - self.min_x

    @property
    def height(self):
        if self.max_y is None:
            return 0
        return self.max_y - self.min_y

    @property
    def size(self):
        return self.width, self.height

    def get_image(self):
        from PIL import Image
        if self.bytes is None:
            b = bytearray(b'')
            if self.min_y is None and self.max_y is None and self.min_x is None and self.max_x is None:
                return None
            for y in range(self.min_y, self.max_y + 1):
                tile = self.get_tile(self.min_x, y, False)
                for x in range(self.min_x, self.max_x + 1):
                    tindex = x & 0xFFF
                    if tindex == 0:
                        tile = self.get_tile(x, y, False)
                    if tile is None or tile[tindex] == 0:
                        b.append(0xFF)
                    else:
                        b.append(0)
            self.bytes = bytes(b)
        image = Image.frombytes("L", self.size, self.bytes)
        return image


class EgvPlotter:
    def __init__(self, x=0, y=0):
        self.path = Path()
        self.raster = EgvRaster()
        self.x = x
        self.y = y
        self.cutting = False
        self.data = {'path': self.path}
        self.cut = self.vector_cut
        self.on = self.vector_on

    def vector_cut(self, dx, dy):
        if dx == 0 and dy == 0:
            return  # Just setting the directions.
        if self.cutting:
            self.path.line((self.x + dx, self.y + dy))
        else:
            self.path.move((self.x + dx, self.y + dy))
        self.x += dx
        self.y += dy

    def raster_cut(self, dx, dy):
        if dx == 0 and dy == 0:
            return  # Just setting the directions.
        if self.cutting:
            if dy == 0:
                for d in range(0, dx):
                    self.raster[self.x + d, self.y] = 1
        self.x += dx
        self.y += dy

    def set_raster(self, value):
        if value:
            self.cut = self.raster_cut
            self.on = self.raster_on
            self.data['raster'] = self.raster
        else:
            self.on = self.vector_on
            self.cut = self.vector_cut

    def vstep(self):
        self.raster_cut(0, self.data['step'])

    def off(self):
        self.cutting = False

    def vector_on(self):
        self.path.move((self.x, self.y))
        self.cutting = True

    def raster_on(self):
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
    is_harmonic = False
    obj = EgvPlotter()

    for commands in egv_parser.parse(f):
        cmd = commands[0]
        distance = commands[1] + commands[2]
        if cmd is None:
            return
        elif cmd == CMD_RIGHT:  # move right
            obj.cut(distance, 0)
            if is_harmonic and is_left:
                obj.vstep()
            is_left = False
        elif cmd == CMD_LEFT:  # move left
            obj.cut(-distance, 0)
            if is_harmonic and not is_left:
                obj.vstep()
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
                b, m, gear = LaserSpeed.get_equation(board, accel=gear, raster_horizontal=raster_step != 0)
                speed = LaserSpeed.get_speed_from_value(code_value, b, m)
                obj.data['step'] = raster_step
                obj.data['speed'] = speed
                if raster_step != 0:
                    is_harmonic = True
                    obj.set_raster(True)
            else:
                if not is_compact and not is_reset:
                    is_compact = True  # We jumped out of compact, but then back in.
        elif cmd == CMD_N:
            if is_compact:
                is_compact = False
        elif cmd == CMD_FINISH or cmd == CMD_RESET:
            is_reset = True
            speed_code = None
            if is_compact:
                is_compact = False
                is_harmonic = False
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
