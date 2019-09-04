from K40Controller import K40Controller
from LaserSpeed import LaserSpeed

COMMAND_RIGHT = b'B'
COMMAND_LEFT = b'T'
COMMAND_TOP = b'L'
COMMAND_BOTTOM = b'R'
COMMAND_ANGLE = b'M'
COMMAND_ON = b'D'
COMMAND_OFF = b'U'

STATE_DEFAULT = 0
STATE_CONCAT = 1
STATE_COMPACT = 2

distance_lookup = [
    b'',
    b'a', b'b', b'c', b'd', b'e', b'f', b'g', b'h', b'i', b'j', b'k', b'l', b'm',
    b'n', b'o', b'p', b'q', b'r', b's', b't', b'u', b'v', b'w', b'x', b'y',
    b'|a', b'|b', b'|c', b'|d', b'|e', b'|f', b'|g', b'|h', b'|i', b'|j', b'|k', b'|l', b'|m',
    b'|n', b'|o', b'|p', b'|q', b'|r', b'|s', b'|t', b'|u', b'|v', b'|w', b'|x', b'|y', b'|z'
]


def lhymicro_distance(v):
    dist = b''
    if v >= 255:
        zs = int(v / 255)
        v %= 255
        dist += (b'z' * zs)
    if v >= 52:
        return dist + '%03d' % v
    return dist + distance_lookup[v]


class LhymicroWriter:
    def __init__(self, board="M2", current_x=0, current_y=0, controller=None):
        if controller is None:
            self.controller = K40Controller()
        else:
            self.controller = controller
        self.board = board
        if self.board is None:
            self.board = "M2"
        self.state = STATE_DEFAULT
        self.is_on = False
        self.is_left = False
        self.is_top = False
        self.raster_step = 0
        self.speed = 30

        self.current_x = current_x
        self.current_y = current_y
        self.next_x = current_x
        self.next_y = current_y
        self.max_x = current_x
        self.max_y = current_y
        self.min_x = current_x
        self.min_y = current_y
        self.start_x = current_x
        self.start_y = current_y
        self.position_listener = None

    def open(self):
        try:
            self.controller.open()
        except AttributeError:
            pass
        self.reset_modes()
        self.state = STATE_DEFAULT

    def close(self):
        self.to_default_mode()
        try:
            self.controller.close()
        except AttributeError:
            pass

    def plot(self, x, y):
        dx = x - self.current_x
        dy = y - self.current_y
        if dx != 0 and dy != 0 and abs(dx) != abs(dy):
            dx = self.next_x - self.current_x
            dy = self.next_y - self.current_y
            if dx != 0:
                self.move_x(dx)
            if dy != 0:
                self.move_y(dy)
            if abs(dx) == abs(dy):
                self.move_angle(dx, dy)
        self.next_x = x
        self.next_y = y

    def move(self, dx, dy):
        if dx == 0 and dy == 0:
            return
        if self.state == STATE_DEFAULT:
            self.controller += b'I'
            if dx != 0:
                self.move_x(dx)
            if dy != 0:
                self.move_y(dy)
            self.controller += b'S1P\n'
        elif self.state == STATE_COMPACT:
            if dx != 0 and dy != 0 and abs(dx) != abs(dy):
                raise ValueError("Not an octent %d, %d" % (dx,dy))
            if abs(dx) == abs(dy):
                self.move_angle(dx, dy)
            elif dx != 0:
                self.move_x(dx)
            else:
                self.move_y(dy)
        elif self.state == STATE_CONCAT:
            if dx != 0:
                self.move_x(dx)
            if dy != 0:
                self.move_y(dy)
            self.controller += b'N'
        self.check_bounds()
        if self.position_listener is not None:
            self.position_listener(self.current_x, self.current_y, self.current_x - dx, self.current_y - dy)

    def down(self):
        if self.is_on:
            return False
        if self.state == STATE_DEFAULT:
            self.controller += b'I'
            self.controller += COMMAND_ON
            self.controller += b'S1P\n'
        elif self.state == STATE_COMPACT:
            self.controller += COMMAND_ON
        elif self.state == STATE_CONCAT:
            self.controller += COMMAND_ON
            self.controller += b'N'
        self.is_on = True
        return True

    def up(self):
        if not self.is_on:
            return False
        if self.state == STATE_DEFAULT:
            self.controller += b'I'
            self.controller += COMMAND_OFF
            self.controller += b'S1P\n'
        elif self.state == STATE_COMPACT:
            self.controller += COMMAND_OFF
        elif self.state == STATE_CONCAT:
            self.controller += COMMAND_OFF
            self.controller += b'N'
        self.is_on = False
        return True

    def to_default_mode(self):
        if self.state == STATE_CONCAT:
            self.controller += b'S1P\n'
        elif self.state == STATE_COMPACT:
            self.controller += b'FNSE-\n'
            self.reset_modes()
        self.state = STATE_DEFAULT

    def to_concat_mode(self):
        self.to_default_mode()
        self.controller += b'I'
        self.state = STATE_CONCAT

    def to_compact_mode(self):
        self.to_concat_mode()
        speed_code = LaserSpeed.get_code_from_speed(self.speed, self.raster_step, self.board)
        self.controller += speed_code
        self.controller += b'N'
        self.declare_directions()
        self.controller += b'S1E'
        self.state = STATE_COMPACT

    def h_switch(self):
        if self.is_left:
            self.controller += COMMAND_RIGHT
        else:
            self.controller += COMMAND_LEFT
        self.is_left = not self.is_left
        if self.is_top:
            self.current_y -= self.raster_step
        else:
            self.current_y += self.raster_step

    def v_switch(self):
        if self.is_top:
            self.controller += COMMAND_BOTTOM
        else:
            self.controller += COMMAND_TOP
        self.is_top = not self.is_top
        if self.is_left:
            self.current_x -= self.raster_step
        else:
            self.current_x += self.raster_step

    def home(self):
        self.to_default_mode()
        self.controller += b'IPP\n'
        self.current_x = 0
        self.current_y = 0
        self.reset_modes()
        self.state = STATE_DEFAULT

    def lock_rail(self):
        self.to_default_mode()
        self.controller += b'IS1P\n'

    def unlock_rail(self, abort=False):
        self.to_default_mode()
        self.controller += b'IS2P\n'

    def abort(self):
        self.controller += b'I\n'

    def check_bounds(self):
        self.min_x = min(self.min_x, self.current_x)
        self.min_y = min(self.min_y, self.current_y)
        self.max_x = max(self.max_x, self.current_x)
        self.max_y = max(self.max_y, self.current_y)

    def reset_modes(self):
        self.is_on = False
        self.is_left = False
        self.is_top = False

    def move_x(self, dx):
        if dx > 0:
            self.move_right(dx)
        else:
            self.move_left(dx)

    def move_y(self, dy):
        if dy > 0:
            self.move_bottom(dy)
        else:
            self.move_top(dy)

    def move_angle(self, dx, dy):
        if abs(dx) != abs(dy):
            raise ValueError('abs(dx) must equal abs(dy)')
        if dx > 0:  # Moving right
            if self.is_left:
                self.controller += COMMAND_RIGHT
                self.is_left = False
        else:  # Moving left
            if not self.is_left:
                self.controller += COMMAND_LEFT
                self.is_left = True
        if dy > 0:  # Moving bottom
            if self.is_top:
                self.controller += COMMAND_BOTTOM
                self.is_top = False
        else:  # Moving top
            if not self.is_top:
                self.controller += COMMAND_TOP
                self.is_top = True
        self.current_x += dx
        self.current_y += dy
        self.check_bounds()
        self.controller += COMMAND_ANGLE + lhymicro_distance(abs(dy))

    def declare_directions(self):
        if self.is_top:
            self.controller += COMMAND_TOP
        else:
            self.controller += COMMAND_BOTTOM
        if self.is_left:
            self.controller += COMMAND_LEFT
        else:
            self.controller += COMMAND_RIGHT

    def move_right(self, dx=0):
        self.current_x += dx
        self.is_left = False
        self.controller += COMMAND_RIGHT
        if dx != 0:
            self.controller += lhymicro_distance(abs(dx))
            self.check_bounds()

    def move_left(self, dx=0):
        self.current_x -= abs(dx)
        self.is_left = True
        self.controller += COMMAND_LEFT
        if dx != 0:
            self.controller += lhymicro_distance(abs(dx))
            self.check_bounds()

    def move_bottom(self, dy=0):
        self.current_y += dy
        self.is_top = False
        self.controller += COMMAND_BOTTOM
        if dy != 0:
            self.controller += lhymicro_distance(abs(dy))
            self.check_bounds()

    def move_top(self, dy=0):
        self.current_y -= abs(dy)
        self.is_top = True
        self.controller += COMMAND_TOP
        if dy != 0:
            self.controller += lhymicro_distance(abs(dy))
            self.check_bounds()
