import threading

from K40Controller import K40Controller
from Kernel import *
from LaserCommandConstants import *
from LaserSpeed import LaserSpeed
from svgelements import *

"""
Lhymicro provides Lhystudio specific coding for elements and sends it to the K40Controller backend to write to the usb
the intent is that this class could be switched out for a different class and control a different type of laser if need
be. The middle language of generated commands from the ProjectNodes are able to be interpreted by a different driver
or methodology. 
"""

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
        return dist + b'%03d' % v
    return dist + distance_lookup[v]


class SpoolerThread(threading.Thread):
    def __init__(self, project, spooler, controller):
        threading.Thread.__init__(self)
        self.project = project
        project.setting(str, "_controller_buffer", b'')
        project.setting(str, "_controller_queue", b'')
        project.setting(bool, "autostart_controller", True)
        project.setting(int, "buffer_max", 900)
        project.setting(bool, "buffer_limit", True)
        self.spooler = spooler
        self.controller = controller

        self.buffer_size = -1
        self.state = THREAD_STATE_UNSTARTED
        self.project("writer", self.state)

    def start_element_producer(self):
        if self.state != THREAD_STATE_ABORT:
            self.state = THREAD_STATE_STARTED
            self.project("writer", self.state)
            self.start()

    def pause(self):
        self.state = THREAD_STATE_PAUSED
        self.project("writer", self.state)

    def resume(self):
        self.state = THREAD_STATE_STARTED
        self.project("writer", self.state)

    def abort(self, val):
        if val != 0:
            self.state = THREAD_STATE_ABORT
            self.project("writer", self.state)

    def stop(self):
        self.abort(1)

    def get_buffer_size(self):
        return len(self.project._controller_buffer) + len(self.project._controller_queue)

    def thread_pause_check(self, *args):
        while (self.project.buffer_limit and self.get_buffer_size() > self.project.buffer_max) or \
                self.state == THREAD_STATE_PAUSED:
            # Backend is full. Or we are paused. We're waiting.
            time.sleep(0.1)
            if self.state == THREAD_STATE_ABORT:
                raise StopIteration  # abort called.
        if self.state == THREAD_STATE_ABORT:
            raise StopIteration  # abort called.

    def run(self):
        command_index = 0
        self.project.listen("buffer", self.update_buffer_size)
        self.project.listen("abort", self.abort)
        self.spooler.on_plot = self.thread_pause_check
        try:
            while True:
                element = self.spooler.peek()
                if element is None:
                    raise StopIteration
                self.thread_pause_check()
                try:
                    gen = element.generate
                except AttributeError:
                    gen = element
                for e in gen():
                    try:
                        command, values = e
                    except TypeError:
                        command = e
                        values = 0
                    command_index += 1
                    self.thread_pause_check()
                    self.project("command", command_index)
                    self.project.spooler.command(command, values)
                self.spooler.pop()
                self.project("spooler", element)
        except StopIteration:
            pass  # We aborted the loop.
        # Final listener calls.
        self.spooler.on_plot = None
        self.project.unlisten("abort", self.abort)
        self.project.unlisten("buffer", self.update_buffer_size)
        if self.state == THREAD_STATE_ABORT:
            self.spooler.clear_queue()
            self.spooler.state = STATE_DEFAULT
            self.project("writer_mode", self.spooler.state)
            return  # Must no do anything else. Just die as fast as possible.
        self.project.autostart_controller = True
        self.state = THREAD_STATE_FINISHED
        self.project("writer", self.state)

    def update_buffer_size(self, size):
        self.buffer_size = size


class LhymicroWriter:
    def __init__(self, current_x=0, current_y=0):
        self.project = None
        self.state = STATE_DEFAULT
        self.is_on = False
        self.is_left = False
        self.is_top = False
        self.is_relative = False
        self.raster_step = 0
        self.speed = 30
        self.power = 1000.0
        self.d_ratio = None
        self.default_SnP = None
        self.pulse_total = 0.0
        self.pulse_modulation = True

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
        self.on_plot = None
        self.queue_lock = threading.Lock()
        self.queue = []
        self.thread = None

    def initialize(self, project):
        self.project = project
        self.project.spooler = self
        project.setting(str, "board", "M2")
        project.setting(bool, "autolock", True)
        project.setting(bool, "autostart", True)
        project.setting(bool, "rotary", False)
        project.setting(float, "scale_x", 1.0)
        project.setting(float, "scale_y", 1.0)
        project.setting(int, "_stepping_force", None)
        project.autostart = True  # Setting still exists but false values do weird things.
        project.setting(float, "_acceleration_breaks", float("inf"))

        def spool(commands):
            self.send_job(commands)

        project.add_control("Spool", spool)
        if self.project.controller is None:
            self.project.controller = K40Controller()
            self.project.add_module(self.project.controller)

        project.add_control("Emergency Stop", self.emergency_stop)

        def break_acceleration10():
            self.project._acceleration_breaks = 10.0

        def break_acceleration20():
            self.project._acceleration_breaks = 20.0

        def break_acceleration30():
            self.project._acceleration_breaks = 30.0

        def break_acceleration40():
            self.project._acceleration_breaks = 40.0

        def break_acceleration_inf():
            self.project._acceleration_breaks = float("inf")

        project.add_control("acceleration Breaks 10mm/s", break_acceleration10)
        project.add_control("acceleration Breaks 20mm/s", break_acceleration20)
        project.add_control("acceleration Breaks 30mm/s", break_acceleration30)
        project.add_control("acceleration Breaks 40mm/s", break_acceleration40)
        project.add_control("acceleration Breaks off", break_acceleration_inf)

        self.thread = SpoolerThread(project, self, self.project.controller)
        project.add_thread("K40Spooler", self.thread)

    def emergency_stop(self):
        self.clear_queue()
        self.thread.state = THREAD_STATE_ABORT
        self.project._controller_buffer = b''
        self.project._controller_queue = b''
        self.abort()

    def peek(self):
        if len(self.queue) == 0:
            return None
        return self.queue[0]

    def pop(self):
        if len(self.queue) == 0:
            return None
        self.queue_lock.acquire()
        queue_head = self.queue[0]
        del self.queue[0]
        self.queue_lock.release()
        return queue_head

    def clear_queue(self):
        self.queue_lock.acquire()
        self.queue = []
        self.queue_lock.release()
        self.project("spooler", 0)

    def add_queue(self, elements):
        self.queue_lock.acquire()
        self.queue += elements
        self.queue_lock.release()
        if self.project.autostart:
            self.start_queue_consumer()
        self.project("spooler", 0)

    def send_job(self, element):
        self.queue_lock.acquire()
        self.queue.append(element)
        self.queue_lock.release()
        if self.project.autostart:
            self.start_queue_consumer()
        self.project("spooler", 0)

    def reset_thread(self):
        self.thread = SpoolerThread(self.project, self, self.project.controller)
        self.project("writer", self.thread.state)

    def start_queue_consumer(self):
        if self.thread.state == THREAD_STATE_ABORT:
            # We cannot reset an aborted thread without specifically calling reset.
            return
        if self.thread.state == THREAD_STATE_FINISHED:
            self.thread = SpoolerThread(self.project, self, self.project.controller)
        if self.thread.state == THREAD_STATE_UNSTARTED:
            self.thread.state = THREAD_STATE_STARTED
            self.thread.start()
            self.project("writer", self.thread.state)

    def open(self):
        try:
            self.project.controller.open()
        except AttributeError:
            pass
        self.reset_modes()
        self.state = STATE_DEFAULT

    def close(self):
        self.to_default_mode()
        try:
            self.project.controller.close()
        except AttributeError:
            pass

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
        """PPI is Pulses per inch."""
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
            if self.on_plot is not None:
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
        if self.on_plot is not None:
            self.on_plot(last_x, last_y, last_on)

    def command(self, command, values):
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
            sx = self.current_x
            sy = self.current_y
            self.up()
            self.pulse_modulation = False
            if self.state == STATE_COMPACT:
                for x, y, on in self.group_plots(sx, sy, Line.plot_line(sx, sy, x, y)):
                    self.move(x, y)
            else:
                self.move(x, y)
        elif command == COMMAND_MOVE:
            x, y = values
            sx = self.current_x
            sy = self.current_y
            self.pulse_modulation = self.is_on

            if self.state == STATE_COMPACT:
                for x, y, on in self.group_plots(sx, sy, Line.plot_line(sx, sy, x, y)):
                    self.move(x, y)
            else:
                self.move(x, y)
        elif command == COMMAND_CUT:
            x, y = values
            sx = self.current_x
            sy = self.current_y
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
            sx = self.current_x
            sy = self.current_y
            self.pulse_modulation = True
            try:
                x2 = y2 = x1 = y1 = None
                for x, y, on in self.group_plots(sx, sy, path.plot()):
                    if on == 0:
                        self.up()
                    else:
                        self.down()
                    try:
                        change = abs(((x2 > x1) - (x2 < x1) + (y2 > y1) - (y2 < y1)) -
                                     ((x1 > x) - (x1 < x) + (y1 > y) - (y1 < y)))
                    except TypeError:
                        change = 0
                    if self.state == STATE_COMPACT and \
                            change >= 2 and \
                            self.speed >= self.project._acceleration_breaks:
                        self.to_default_mode()
                        self.to_compact_mode()
                        x1 = y1 = None
                    self.move_absolute(x, y)
                    x2, y2 = x1, y1
                    x1, y1 = x, y
            except RuntimeError:
                return
        elif command == COMMAND_RASTER:
            raster = values
            sx = self.current_x
            sy = self.current_y
            self.pulse_modulation = True
            try:
                for e in self.group_plots(sx, sy, self.ungroup_plots(raster.plot())):
                    x, y, on = e
                    dx = x - sx
                    dy = y - sy
                    sx = x
                    sy = y
                    if dy != 0:
                        if self.is_top:
                            if abs(dy) > self.raster_step:
                                self.to_concat_mode()
                                self.move_relative(0, dy + self.raster_step)
                                self.to_compact_mode()
                            self.h_switch()
                        else:
                            if abs(dy) > self.raster_step:
                                self.to_concat_mode()
                                self.move_relative(0, dy - self.raster_step)
                                self.to_compact_mode()
                            self.h_switch()
                    if on == 0:
                        self.up()
                    else:
                        self.down()
                    if dx != 0:
                        self.move_relative(dx, dy)
            except RuntimeError:
                return
        elif command == COMMAND_CUT_QUAD:
            cx, cy, x, y, = values
            sx = self.current_x
            sy = self.current_y
            self.pulse_modulation = True
            for x, y, on in self.group_plots(sx, sy, QuadraticBezier.plot_quad_bezier(sx, sy, cx, cy, x, y)):
                if on == 0:
                    self.up()
                else:
                    self.down()
                self.move_absolute(x, y)
        elif command == COMMAND_CUT_CUBIC:
            c1x, c1y, c2x, c2y, ex, ey = values
            sx = self.current_x
            sy = self.current_y
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
            x_dir, y_dir = values
            self.is_left = x_dir < 0
            self.is_top = y_dir < 0
        elif command == COMMAND_SET_INCREMENTAL:
            self.is_relative = True
        elif command == COMMAND_SET_ABSOLUTE:
            self.is_relative = False
        elif command == COMMAND_SET_POSITION:
            x, y = values
            self.current_x = x
            self.current_y = y
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
            if self.thread is not None:
                while self.thread.buffer_size > 0:
                    time.sleep(0.05)
        elif command == COMMAND_BEEP:
            print('\a')  # Beep.
        elif command == COMMAND_FUNCTION:
            t = values
            if callable(t):
                t()

    def move(self, x, y):
        if self.is_relative:
            self.move_relative(x, y)
        else:
            self.move_absolute(x, y)

    def move_absolute(self, x, y):
        self.move_relative(x - self.current_x, y - self.current_y)

    def move_relative(self, dx, dy):
        if abs(dx) == 0 and abs(dy) == 0:
            return
        dx = int(round(dx))
        dy = int(round(dy))
        if self.state == STATE_DEFAULT:
            self.project.controller += b'I'
            if dx != 0:
                self.move_x(dx)
            if dy != 0:
                self.move_y(dy)
            # Todo, combine these calling 'NS2P\n'
            self.project.controller += b'S1P\n'
            if not self.project.autolock:
                self.project.controller += b'IS2P\n'
        elif self.state == STATE_COMPACT:
            if dx != 0 and dy != 0 and abs(dx) != abs(dy):
                for x, y, on in self.group_plots(self.current_x, self.current_y,
                                                 Line.plot_line(self.current_x, self.current_y,
                                                                self.current_x + dx, self.current_y + dy)
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
            self.project.controller += b'N'
        self.check_bounds()
        self.project("position", (self.current_x, self.current_y, self.current_x - dx, self.current_y - dy))

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
        controller = self.project.controller
        if self.state == STATE_DEFAULT:
            controller += b'I'
            controller += COMMAND_ON
            controller += b'S1P\n'
            if not self.project.autolock:
                controller += b'IS2P\n'
        elif self.state == STATE_COMPACT:
            controller += COMMAND_ON
        elif self.state == STATE_CONCAT:
            controller += COMMAND_ON
            controller += b'N'
        self.is_on = True
        return True

    def up(self):
        controller = self.project.controller
        if not self.is_on:
            return False
        if self.state == STATE_DEFAULT:
            controller += b'I'
            controller += COMMAND_OFF
            controller += b'S1P\n'
            if not self.project.autolock:
                controller += b'IS2P\n'
        elif self.state == STATE_COMPACT:
            controller += COMMAND_OFF
        elif self.state == STATE_CONCAT:
            controller += COMMAND_OFF
            controller += b'N'
        self.is_on = False
        return True

    def to_default_mode(self):
        controller = self.project.controller
        if self.state == STATE_CONCAT:
            controller += b'S1P\n'
            if not self.project.autolock:
                controller += b'IS2P\n'
        elif self.state == STATE_COMPACT:
            controller += b'FNSE-\n'
            self.reset_modes()
        self.state = STATE_DEFAULT
        self.project("writer_mode", self.state)

    def to_concat_mode(self):
        controller = self.project.controller
        self.to_default_mode()
        controller += b'I'
        self.state = STATE_CONCAT
        self.project("writer_mode", self.state)

    def to_compact_mode(self):
        controller = self.project.controller
        self.to_concat_mode()
        if self.d_ratio is not None:
            speed_code = LaserSpeed.get_code_from_speed(self.speed, self.raster_step, self.project.board,
                                                        d_ratio=self.d_ratio, gear=self.project._stepping_force)
        else:
            speed_code = LaserSpeed.get_code_from_speed(self.speed, self.raster_step, self.project.board,
                                                        gear=self.project._stepping_force)
        try:
            speed_code = bytes(speed_code)
        except TypeError:
            speed_code = bytes(speed_code, 'utf8')
        controller += speed_code
        controller += b'N'
        self.declare_directions()
        controller += b'S1E'
        self.state = STATE_COMPACT
        self.project("writer_mode", self.state)

    def h_switch(self):
        controller = self.project.controller
        if self.is_left:
            controller += COMMAND_RIGHT
        else:
            controller += COMMAND_LEFT
        self.is_left = not self.is_left
        if self.is_top:
            self.current_y -= self.raster_step
        else:
            self.current_y += self.raster_step
        self.is_on = False

    def v_switch(self):
        controller = self.project.controller
        if self.is_top:
            controller += COMMAND_BOTTOM
        else:
            controller += COMMAND_TOP
        self.is_top = not self.is_top
        if self.is_left:
            self.current_x -= self.raster_step
        else:
            self.current_x += self.raster_step
        self.is_on = False

    def home(self):
        controller = self.project.controller
        self.to_default_mode()
        controller += b'IPP\n'
        old_x = self.current_x
        old_y = self.current_y
        self.current_x = 0
        self.current_y = 0
        self.reset_modes()
        self.state = STATE_DEFAULT
        self.project("position", (self.current_x, self.current_y, old_x, old_y))

    def lock_rail(self):
        controller = self.project.controller
        self.to_default_mode()
        controller += b'IS1P\n'

    def unlock_rail(self, abort=False):
        controller = self.project.controller
        self.to_default_mode()
        controller += b'IS2P\n'

    def abort(self):
        controller = self.project.controller
        controller += b'I\n'

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
        controller = self.project.controller
        if abs(dx) != abs(dy):
            raise ValueError('abs(dx) must equal abs(dy)')
        if dx > 0:  # Moving right
            if self.is_left:
                controller += COMMAND_RIGHT
                self.is_left = False
        else:  # Moving left
            if not self.is_left:
                controller += COMMAND_LEFT
                self.is_left = True
        if dy > 0:  # Moving bottom
            if self.is_top:
                controller += COMMAND_BOTTOM
                self.is_top = False
        else:  # Moving top
            if not self.is_top:
                controller += COMMAND_TOP
                self.is_top = True
        self.current_x += dx
        self.current_y += dy
        self.check_bounds()
        controller += COMMAND_ANGLE + lhymicro_distance(abs(dy))

    def declare_directions(self):
        controller = self.project.controller
        if self.is_top:
            controller += COMMAND_TOP
        else:
            controller += COMMAND_BOTTOM
        if self.is_left:
            controller += COMMAND_LEFT
        else:
            controller += COMMAND_RIGHT

    def move_right(self, dx=0):
        controller = self.project.controller
        self.current_x += dx
        self.is_left = False
        controller += COMMAND_RIGHT
        if dx != 0:
            controller += lhymicro_distance(abs(dx))
            self.check_bounds()

    def move_left(self, dx=0):
        controller = self.project.controller
        self.current_x -= abs(dx)
        self.is_left = True
        controller += COMMAND_LEFT
        if dx != 0:
            controller += lhymicro_distance(abs(dx))
            self.check_bounds()

    def move_bottom(self, dy=0):
        controller = self.project.controller
        self.current_y += dy
        self.is_top = False
        controller += COMMAND_BOTTOM
        if dy != 0:
            controller += lhymicro_distance(abs(dy))
            self.check_bounds()

    def move_top(self, dy=0):
        controller = self.project.controller
        self.current_y -= abs(dy)
        self.is_top = True
        controller += COMMAND_TOP
        if dy != 0:
            controller += lhymicro_distance(abs(dy))
            self.check_bounds()
