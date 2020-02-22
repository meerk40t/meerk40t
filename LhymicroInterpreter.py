from Kernel import *
from LaserCommandConstants import *
from LaserSpeed import LaserSpeed
from svgelements import *

"""
LhymicroInterpreter provides Lhystudio specific coding for elements and sends it to the backend to write to the usb
the intent is that this class could be switched out for a different class and control a different type of laser if need
be. The middle language of generated commands from the LaserNodes are able to be interpreted by a different driver
or methodology. 
"""

DIRECTION_FLAG_LEFT = 1  # Direction is flagged left rather than right.
DIRECTION_FLAG_TOP = 2  # Direction is flagged top rather than bottom.
DIRECTION_FLAG_X = 4  # X-stepper motor is engaged.
DIRECTION_FLAG_Y = 8  # Y-stepper motor is engaged.

STATE_ABORT = -1
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
        return dist + b'%03d' % v
    return dist + distance_lookup[v]


class LhymicroInterpreter(Interpreter):
    def __init__(self, device):
        Interpreter.__init__(self, device)

        self.CODE_RIGHT = b'B'
        self.CODE_LEFT = b'T'
        self.CODE_TOP = b'L'
        self.CODE_BOTTOM = b'R'
        self.CODE_ANGLE = b'M'
        self.CODE_ON = b'D'
        self.CODE_OFF = b'U'

        self.device.setting(bool, "flip_x", False)
        self.device.setting(bool, "flip_y", False)
        self.device.setting(bool, "home_right", False)
        self.device.setting(bool, "home_bottom", False)
        self.device.setting(int, "home_adjust_x", 0)
        self.device.setting(int, "home_adjust_y", 0)

        self.state = STATE_DEFAULT
        self.properties = 0
        self.is_relative = False
        self.is_on = False
        self.raster_step = 0
        self.speed = 30
        self.power = 1000.0
        self.d_ratio = None
        self.default_SnP = None
        self.pulse_total = 0.0
        self.pulse_modulation = True
        self.group_modulation = False

        current_x = device.current_x
        current_y = device.current_y
        self.next_x = current_x
        self.next_y = current_y
        self.max_x = current_x
        self.max_y = current_y
        self.min_x = current_x
        self.min_y = current_y
        self.start_x = current_x
        self.start_y = current_y

        device.add_control("Realtime Pause", self.pause)
        device.add_control("Realtime Resume", self.resume)

    def __repr__(self):
        return "LhymicroInterpreter()"

    def on_plot(self, x, y, on):
        self.device.signal('interpreter;plot', (x, y, on))
        self.device.hold()

    def ungroup_plots(self, generate):
        current_x = None
        current_y = None
        for next_x, next_y, on in generate:
            if current_x is None or current_y is None:
                current_x = next_x
                current_y = next_y
                yield current_x, current_y, on
                continue
            if next_x > current_x:
                dx = 1
            elif next_x < current_x:
                dx = -1
            else:
                dx = 0
            if next_y > current_y:
                dy = 1
            elif next_y < current_y:
                dy = -1
            else:
                dy = 0
            total_dx = next_x - current_x
            total_dy = next_y - current_y
            if total_dy * dx != total_dx * dy:
                raise ValueError("Must be uniformly diagonal or orthogonal: (%d, %d) is not." % (total_dx, total_dy))
            while current_x != next_x or current_y != next_y:
                current_x += dx
                current_y += dy
                yield current_x, current_y, on

    def group_plots(self, start_x, start_y, generate):
        last_x = start_x
        last_y = start_y
        last_on = 0
        dx = 0
        dy = 0
        x = None
        y = None
        for event in generate:
            try:
                x = event[0]
                y = event[1]
                plot_on = event[2]
            except IndexError:
                plot_on = 1
            if self.pulse_modulation:
                self.pulse_total += self.power * plot_on
                if self.group_modulation and last_on == 1:
                    # If we are group modulating and currently on, the threshold for additional on triggers is 500.
                    if self.pulse_total > 0.0:
                        on = 1
                        self.pulse_total -= 1000.0
                    else:
                        on = 0
                else:
                    if self.pulse_total >= 1000.0:
                        on = 1
                        self.pulse_total -= 1000.0
                    else:
                        on = 0
            else:
                on = int(round(plot_on))
            if x == last_x + dx and y == last_y + dy and on == last_on:
                last_x = x
                last_y = y
                continue
            yield last_x, last_y, last_on
            self.on_plot(last_x, last_y, last_on)
            dx = x - last_x
            dy = y - last_y
            if abs(dx) > 1 or abs(dy) > 1:
                # An error here means the plotting routines are flawed and plotted data more than a pixel apart.
                # The bug is in the code that wrongly plotted the data, not here.
                raise ValueError("dx(%d) or dy(%d) exceeds 1" % (dx, dy))
            last_x = x
            last_y = y
            last_on = on
        yield last_x, last_y, last_on
        self.on_plot(last_x, last_y, last_on)

    def command(self, command, values=None):
        if command == COMMAND_LASER_OFF:
            self.up()
        elif command == COMMAND_LASER_ON:
            self.down()
        elif command == COMMAND_RAPID_MOVE:
            self.to_default_mode()
            x, y = values
            self.move(x, y)
        elif command == COMMAND_SHIFT:
            x, y = values
            sx = self.device.current_x
            sy = self.device.current_y
            self.up()
            self.pulse_modulation = False
            if self.state == STATE_COMPACT:
                for x, y, on in self.group_plots(sx, sy, Line.plot_line(sx, sy, x, y)):
                    self.move(x, y)
            else:
                self.move(x, y)
        elif command == COMMAND_MOVE:
            x, y = values
            sx = self.device.current_x
            sy = self.device.current_y
            self.pulse_modulation = self.is_on

            if self.state == STATE_COMPACT:
                for x, y, on in self.group_plots(sx, sy, Line.plot_line(sx, sy, x, y)):
                    self.move(x, y)
            else:
                self.move(x, y)
        elif command == COMMAND_CUT:
            x, y = values
            sx = self.device.current_x
            sy = self.device.current_y
            self.pulse_modulation = True
            for x, y, on in self.group_plots(sx, sy, Line.plot_line(sx, sy, x, y)):
                if on == 0:
                    self.up()
                else:
                    self.down()
                self.move_absolute(x, y)
        elif command == COMMAND_HSTEP:
            self.v_switch()
        elif command == COMMAND_VSTEP:
            self.h_switch()
        elif command == COMMAND_HOME:
            self.home()
        elif command == COMMAND_LOCK:
            self.lock_rail()
        elif command == COMMAND_UNLOCK:
            self.unlock_rail()
        elif command == COMMAND_PLOT:
            path = values
            if len(path) == 0:
                return
            first_point = path.first_point
            self.move_absolute(first_point[0], first_point[1])
            sx = self.device.current_x
            sy = self.device.current_y
            self.pulse_modulation = True
            try:
                for x, y, on in self.group_plots(sx, sy, path.plot()):
                    if on == 0:
                        self.up()
                    else:
                        self.down()
                    self.move_absolute(x, y)
            except RuntimeError:
                return
        elif command == COMMAND_RASTER:
            raster = values
            sx = self.device.current_x
            sy = self.device.current_y
            self.pulse_modulation = True
            try:
                for e in self.group_plots(sx, sy, self.ungroup_plots(raster.plot())):
                    x, y, on = e
                    dx = x - sx
                    dy = y - sy
                    sx = x
                    sy = y

                    if self.is_prop(DIRECTION_FLAG_X) and dy != 0:
                        if self.is_prop(DIRECTION_FLAG_TOP):
                            if abs(dy) > self.raster_step:
                                self.to_concat_mode()
                                self.move_relative(0, dy + self.raster_step)
                                self.set_prop(DIRECTION_FLAG_X)
                                self.unset_prop(DIRECTION_FLAG_Y)
                                self.to_compact_mode()
                            self.h_switch()
                        else:
                            if abs(dy) > self.raster_step:
                                self.to_concat_mode()
                                self.move_relative(0, dy - self.raster_step)
                                self.set_prop(DIRECTION_FLAG_X)
                                self.unset_prop(DIRECTION_FLAG_Y)
                                self.to_compact_mode()
                            self.h_switch()
                    elif self.is_prop(DIRECTION_FLAG_Y) and dx != 0:
                        if self.is_prop(DIRECTION_FLAG_LEFT):
                            if abs(dx) > self.raster_step:
                                self.to_concat_mode()
                                self.move_relative(dx + self.raster_step,0)
                                self.set_prop(DIRECTION_FLAG_Y)
                                self.unset_prop(DIRECTION_FLAG_X)
                                self.to_compact_mode()
                            self.v_switch()
                        else:
                            if abs(dx) > self.raster_step:
                                self.to_concat_mode()
                                self.move_relative(dx - self.raster_step,0)
                                self.set_prop(DIRECTION_FLAG_Y)
                                self.unset_prop(DIRECTION_FLAG_X)
                                self.to_compact_mode()
                            self.v_switch()
                    else:
                        if on == 0:
                            self.up()
                        else:
                            self.down()
                        self.move_relative(dx, dy)
            except RuntimeError:
                return
        elif command == COMMAND_CUT_QUAD:
            cx, cy, x, y, = values
            sx = self.device.current_x
            sy = self.device.current_y
            self.pulse_modulation = True
            for x, y, on in self.group_plots(sx, sy, QuadraticBezier.plot_quad_bezier(sx, sy, cx, cy, x, y)):
                if on == 0:
                    self.up()
                else:
                    self.down()
                self.move_absolute(x, y)
        elif command == COMMAND_CUT_CUBIC:
            c1x, c1y, c2x, c2y, ex, ey = values
            sx = self.device.current_x
            sy = self.device.current_y
            self.pulse_modulation = True
            for x, y, on in self.group_plots(sx, sy, CubicBezier.plot_cubic_bezier(sx, sy, c1x, c1y, c2x, c2y, ex, ey)):
                if on == 0:
                    self.up()
                else:
                    self.down()
                self.move_absolute(x, y)
        elif command == COMMAND_SET_SPEED:
            speed = values
            self.set_speed(speed)
        elif command == COMMAND_SET_POWER:
            power = values
            self.set_power(power)
        elif command == COMMAND_SET_STEP:
            step = values
            self.set_step(step)
        elif command == COMMAND_SET_D_RATIO:
            d_ratio = values
            self.set_d_ratio(d_ratio)
        elif command == COMMAND_SET_DIRECTION:
            # Left, Top, X-Momentum, Y-Momentum
            left, top, x_dir, y_dir = values
            self.properties = 0
            if left:
                self.set_prop(DIRECTION_FLAG_LEFT)
            if top:
                self.set_prop(DIRECTION_FLAG_TOP)
            if x_dir:
                self.set_prop(DIRECTION_FLAG_X)
            if y_dir:
                self.set_prop(DIRECTION_FLAG_Y)
        elif command == COMMAND_SET_INCREMENTAL:
            self.is_relative = True
        elif command == COMMAND_SET_ABSOLUTE:
            self.is_relative = False
        elif command == COMMAND_SET_POSITION:
            x, y = values
            self.device.current_x = x
            self.device.current_y = y
        elif command == COMMAND_MODE_COMPACT:
            self.to_compact_mode()
        elif command == COMMAND_MODE_DEFAULT:
            self.to_default_mode()
        elif command == COMMAND_MODE_CONCAT:
            self.to_concat_mode()
        elif command == COMMAND_WAIT:
            t = values
            time.sleep(t)
        elif command == COMMAND_WAIT_BUFFER_EMPTY:
            while len(self.device.pipe) > 0:
                time.sleep(0.05)
        elif command == COMMAND_BEEP:
            print('\a')  # Beep.
        elif command == COMMAND_FUNCTION:
            t = values
            if callable(t):
                t()
        elif command == COMMAND_CLOSE:
            self.to_default_mode()
        elif command == COMMAND_OPEN:
            self.reset_modes()
            self.state = STATE_DEFAULT
            self.device.signal('interpreter;mode', self.state)
        elif command == COMMAND_RESET:
            self.device.pipe.realtime_write(b'I*\n')
            self.state = STATE_DEFAULT
            self.device.signal('interpreter;mode', self.state)
        elif command == COMMAND_PAUSE:
            self.pause()
        elif command == COMMAND_STATUS:
            self.device.signal("interpreter;status", self.get_status())
        elif command == COMMAND_RESUME:
            pass  # This command can't be processed since we should be paused.

    def realtime_command(self, command, values=None):
        if command == COMMAND_SET_SPEED:
            speed = values
            self.set_speed(speed)
        elif command == COMMAND_SET_POWER:
            power = values
            self.set_power(power)
        elif command == COMMAND_SET_STEP:
            step = values
            self.set_step(step)
        elif command == COMMAND_SET_D_RATIO:
            d_ratio = values
            self.set_d_ratio(d_ratio)
        elif command == COMMAND_SET_POSITION:
            x, y = values
            self.device.current_x = x
            self.device.current_y = y
        elif command == COMMAND_RESET:
            self.device.pipe.realtime_write(b'I*\n')
            self.state = STATE_DEFAULT
            self.device.signal('interpreter;mode', self.state)
        elif command == COMMAND_PAUSE:
            self.pause()
        elif command == COMMAND_STATUS:
            status = self.get_status()
            self.device.signal('interpreter;status', status)
            return status
        elif command == COMMAND_RESUME:
            self.resume()

    def get_status(self):
        parts = []
        parts.append("x=%f" % self.device.current_x)
        parts.append("y=%f" % self.device.current_y)
        parts.append("speed=%f" % self.speed)
        parts.append("power=%d" % self.power)
        return ";".join(parts)

    def set_prop(self, mask):
        self.properties |= mask

    def unset_prop(self, mask):
        self.properties &= ~mask

    def is_prop(self, mask):
        return bool(self.properties & mask)

    def toggle_prop(self, mask):
        if self.is_prop(mask):
            self.unset_prop(mask)
        else:
            self.set_prop(mask)

    def pause(self):
        self.device.pipe.realtime_write(b'PN!\n')

    def resume(self):
        self.device.pipe.realtime_write(b'PN&\n')

    def move(self, x, y):
        if self.is_relative:
            self.move_relative(x, y)
        else:
            self.move_absolute(x, y)

    def move_absolute(self, x, y):
        self.move_relative(x - self.device.current_x, y - self.device.current_y)

    def move_relative(self, dx, dy):
        if abs(dx) == 0 and abs(dy) == 0:
            return
        dx = int(round(dx))
        dy = int(round(dy))
        if self.state == STATE_DEFAULT:
            self.device.pipe.write(b'I')
            if dx != 0:
                self.move_x(dx)
            if dy != 0:
                self.move_y(dy)
            self.device.pipe.write(b'S1P\n')
            if not self.device.autolock:
                self.device.pipe.write(b'IS2P\n')
        elif self.state == STATE_COMPACT:
            if dx != 0 and dy != 0 and abs(dx) != abs(dy):
                for x, y, on in self.group_plots(self.device.current_x, self.device.current_y,
                                                 Line.plot_line(self.device.current_x, self.device.current_y,
                                                                self.device.current_x + dx, self.device.current_y + dy)
                                                 ):
                    self.move_absolute(x, y)
            elif abs(dx) == abs(dy):
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
            self.device.pipe.write(b'N')
        self.check_bounds()
        self.device.signal('interpreter;position', (self.device.current_x, self.device.current_y,
                                                    self.device.current_x - dx, self.device.current_y - dy))

    def move_xy_line(self, delta_x, delta_y):
        """Strictly speaking if this happens it is because of a bug.
        Nothing should feed the writer this data. It's invalid.
        All moves should be diagonal or orthogonal.

        Zingl-Bresenham line draw algorithm"""

        dx = abs(delta_x)
        dy = -abs(delta_y)

        if delta_x > 0:
            sx = 1
        else:
            sx = -1
        if delta_y > 0:
            sy = 1
        else:
            sy = -1
        err = dx + dy  # error value e_xy
        x0 = 0
        y0 = 0
        while True:  # /* loop */
            if x0 == delta_x and y0 == delta_y:
                break
            mx = 0
            my = 0
            e2 = 2 * err
            if e2 >= dy:  # e_xy+e_y < 0
                err += dy
                x0 += sx
                mx += sx
            if e2 <= dx:  # e_xy+e_y < 0
                err += dx
                y0 += sy
                my += sy
            if abs(mx) == abs(my):
                self.move_angle(mx, my)
            elif mx != 0:
                self.move_x(mx)
            else:
                self.move_y(my)

    def set_speed(self, speed=None):
        change = False
        if self.speed != speed:
            change = True
            self.speed = speed
        if not change:
            return
        if self.state == STATE_COMPACT:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.to_concat_mode()
            self.to_compact_mode()

    def set_power(self, power=1000.0):
        self.power = power

    def set_d_ratio(self, d_ratio=None):
        change = False
        if self.d_ratio != d_ratio:
            change = True
            self.d_ratio = d_ratio
        if not change:
            return
        if self.state == STATE_COMPACT:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.to_concat_mode()
            self.to_compact_mode()

    def set_step(self, step=None):
        change = False
        if self.raster_step != step:
            change = True
            self.raster_step = step
        if not change:
            return
        if self.state == STATE_COMPACT:
            # Compact mode means it's currently slowed. To make the speed have an effect, compact must be exited.
            self.to_concat_mode()
            self.to_compact_mode()

    def down(self):
        if self.is_on:
            return False
        controller = self.device.pipe
        if self.state == STATE_DEFAULT:
            controller.write(b'I')
            controller.write(self.CODE_ON)
            controller.write(b'S1P\n')
            if not self.device.autolock:
                controller.write(b'IS2P\n')
        elif self.state == STATE_COMPACT:
            controller.write(self.CODE_ON)
        elif self.state == STATE_CONCAT:
            controller.write(self.CODE_ON)
            controller.write(b'N')
        self.is_on = True
        return True

    def up(self):
        controller = self.device.pipe
        if not self.is_on:
            return False
        if self.state == STATE_DEFAULT:
            controller.write(b'I')
            controller.write(self.CODE_OFF)
            controller.write(b'S1P\n')
            if not self.device.autolock:
                controller.write(b'IS2P\n')
        elif self.state == STATE_COMPACT:
            controller.write(self.CODE_OFF)
        elif self.state == STATE_CONCAT:
            controller.write(self.CODE_OFF)
            controller.write(b'N')
        self.is_on = False
        return True

    def to_default_mode(self):
        controller = self.device.pipe
        if self.state == STATE_CONCAT:
            controller.write(b'S1P\n')
            if not self.device.autolock:
                controller.write(b'IS2P\n')
        elif self.state == STATE_COMPACT:
            controller.write(b'FNSE-\n')
            self.reset_modes()
        self.state = STATE_DEFAULT
        self.device.signal('interpreter;mode', self.state)

    def to_concat_mode(self):
        controller = self.device.pipe
        self.to_default_mode()
        controller.write(b'I')
        self.state = STATE_CONCAT
        self.device.signal('interpreter;mode', self.state)

    def to_compact_mode(self):
        controller = self.device.pipe
        self.to_concat_mode()
        if self.d_ratio is not None:
            speed_code = LaserSpeed.get_code_from_speed(self.speed,
                                                        self.raster_step,
                                                        self.device.board,
                                                        d_ratio=self.d_ratio)
        else:
            speed_code = LaserSpeed.get_code_from_speed(self.speed,
                                                        self.raster_step,
                                                        self.device.board)
        try:
            speed_code = bytes(speed_code)
        except TypeError:
            speed_code = bytes(speed_code, 'utf8')
        controller.write(speed_code)
        controller.write(b'N')
        self.declare_directions()
        controller.write(b'S1E')
        self.state = STATE_COMPACT
        self.device.signal('interpreter;mode', self.state)

    def h_switch(self):
        controller = self.device.pipe
        if self.is_prop(DIRECTION_FLAG_LEFT):
            controller.write(self.CODE_RIGHT)
            self.unset_prop(DIRECTION_FLAG_LEFT)
        else:
            controller.write(self.CODE_LEFT)
            self.set_prop(DIRECTION_FLAG_LEFT)
        if self.is_prop(DIRECTION_FLAG_TOP):
            self.device.current_y -= self.raster_step
        else:
            self.device.current_y += self.raster_step
        self.is_on = False

    def v_switch(self):
        controller = self.device.pipe
        if self.is_prop(DIRECTION_FLAG_TOP):
            controller.write(self.CODE_BOTTOM)
            self.unset_prop(DIRECTION_FLAG_TOP)
        else:
            controller.write(self.CODE_TOP)
            self.set_prop(DIRECTION_FLAG_TOP)
        if self.is_prop(DIRECTION_FLAG_LEFT):
            self.device.current_x -= self.raster_step
        else:
            self.device.current_x += self.raster_step
        self.is_on = False

    def home(self):
        controller = self.device.pipe
        self.to_default_mode()
        controller.write(b'IPP\n')
        old_x = self.device.current_x
        old_y = self.device.current_y
        self.device.current_x = 0
        self.device.current_y = 0
        self.reset_modes()
        self.state = STATE_DEFAULT
        self.device.signal('interpreter;mode', self.state)
        self.device.signal('interpreter;position', (self.device.current_x, self.device.current_y, old_x, old_y))

    def lock_rail(self):
        controller = self.device.pipe
        self.to_default_mode()
        controller.write(b'IS1P\n')

    def unlock_rail(self, abort=False):
        controller = self.device.pipe
        self.to_default_mode()
        controller.write(b'IS2P\n')

    def abort(self):
        controller = self.device.pipe
        controller.write(b'I\n')

    def check_bounds(self):
        self.min_x = min(self.min_x, self.device.current_x)
        self.min_y = min(self.min_y, self.device.current_y)
        self.max_x = max(self.max_x, self.device.current_x)
        self.max_y = max(self.max_y, self.device.current_y)

    def reset_modes(self):
        self.is_on = False
        self.properties = 0

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
        controller = self.device.pipe
        if abs(dx) != abs(dy):
            raise ValueError('abs(dx) must equal abs(dy)')
        self.set_prop(DIRECTION_FLAG_X)  # Set both on
        self.set_prop(DIRECTION_FLAG_Y)
        if dx > 0:  # Moving right
            if self.is_prop(DIRECTION_FLAG_LEFT):
                controller.write(self.CODE_RIGHT)
                self.unset_prop(DIRECTION_FLAG_LEFT)
        else:  # Moving left
            if not self.is_prop(DIRECTION_FLAG_LEFT):
                controller.write(self.CODE_LEFT)
                self.set_prop(DIRECTION_FLAG_LEFT)
        if dy > 0:  # Moving bottom
            if self.is_prop(DIRECTION_FLAG_TOP):
                controller.write(self.CODE_BOTTOM)
                self.unset_prop(DIRECTION_FLAG_TOP)
        else:  # Moving top
            if not self.is_prop(DIRECTION_FLAG_TOP):
                controller.write(self.CODE_TOP)
                self.set_prop(DIRECTION_FLAG_TOP)
        self.device.current_x += dx
        self.device.current_y += dy
        self.check_bounds()
        controller.write(self.CODE_ANGLE + lhymicro_distance(abs(dy)))

    def declare_directions(self):
        """Declare direction declares raster directions of left, top, with the primary momentum direction going last.
        You cannot declare a diagonal direction."""
        controller = self.device.pipe

        if self.is_prop(DIRECTION_FLAG_LEFT):
            x_dir = self.CODE_LEFT
        else:
            x_dir = self.CODE_RIGHT
        if self.is_prop(DIRECTION_FLAG_TOP):
            y_dir = self.CODE_TOP
        else:
            y_dir = self.CODE_BOTTOM
        if self.is_prop(DIRECTION_FLAG_X):  # FLAG_Y is assumed to be !FLAG_X
            controller.write(y_dir + x_dir)
        else:
            controller.write(x_dir + y_dir)

    @property
    def is_left(self):
        return self.is_prop(DIRECTION_FLAG_X) and \
               not self.is_prop(DIRECTION_FLAG_Y) and \
               self.is_prop(DIRECTION_FLAG_LEFT)

    @property
    def is_right(self):
        return self.is_prop(DIRECTION_FLAG_X) and \
               not self.is_prop(DIRECTION_FLAG_Y) and \
               not self.is_prop(DIRECTION_FLAG_LEFT)

    @property
    def is_top(self):
        return not self.is_prop(DIRECTION_FLAG_X) and \
               self.is_prop(DIRECTION_FLAG_Y) and \
               self.is_prop(DIRECTION_FLAG_TOP)

    @property
    def is_bottom(self):
        return not self.is_prop(DIRECTION_FLAG_X) and \
               self.is_prop(DIRECTION_FLAG_Y) and \
               not self.is_prop(DIRECTION_FLAG_TOP)

    @property
    def is_angle(self):
        return self.is_prop(DIRECTION_FLAG_Y) and \
               self.is_prop(DIRECTION_FLAG_X)

    def set_left(self):
        self.set_prop(DIRECTION_FLAG_X)
        self.unset_prop(DIRECTION_FLAG_Y)
        self.set_prop(DIRECTION_FLAG_LEFT)

    def set_right(self):
        self.set_prop(DIRECTION_FLAG_X)
        self.unset_prop(DIRECTION_FLAG_Y)
        self.unset_prop(DIRECTION_FLAG_LEFT)

    def set_top(self):
        self.unset_prop(DIRECTION_FLAG_X)
        self.set_prop(DIRECTION_FLAG_Y)
        self.set_prop(DIRECTION_FLAG_TOP)

    def set_bottom(self):
        self.unset_prop(DIRECTION_FLAG_X)
        self.set_prop(DIRECTION_FLAG_Y)
        self.unset_prop(DIRECTION_FLAG_TOP)

    def move_right(self, dx=0):
        controller = self.device.pipe
        self.device.current_x += dx
        if not self.is_right or self.state != STATE_COMPACT:
            controller.write(self.CODE_RIGHT)
            self.set_right()
        if dx != 0:
            controller.write(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_left(self, dx=0):
        controller = self.device.pipe
        self.device.current_x -= abs(dx)
        if not self.is_left or self.state != STATE_COMPACT:
            controller.write(self.CODE_LEFT)
            self.set_left()
        if dx != 0:
            controller.write(lhymicro_distance(abs(dx)))
            self.check_bounds()

    def move_bottom(self, dy=0):
        controller = self.device.pipe
        self.device.current_y += dy
        if not self.is_bottom or self.state != STATE_COMPACT:
            controller.write(self.CODE_BOTTOM)
            self.set_bottom()
        if dy != 0:
            controller.write(lhymicro_distance(abs(dy)))
            self.check_bounds()

    def move_top(self, dy=0):
        controller = self.device.pipe
        self.device.current_y -= abs(dy)
        if not self.is_top or self.state != STATE_COMPACT:
            controller.write(self.CODE_TOP)
            self.set_top()
        if dy != 0:
            controller.write(lhymicro_distance(abs(dy)))
            self.check_bounds()
