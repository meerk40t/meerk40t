from ...core.plotplanner import PlotPlanner
from ...kernel import Modifier
from ..basedevice import (
    INTERPRETER_STATE_FINISH,
    INTERPRETER_STATE_MODECHANGE,
    INTERPRETER_STATE_PROGRAM,
    INTERPRETER_STATE_RAPID,
    INTERPRETER_STATE_RASTER,
    PLOT_AXIS,
    PLOT_DIRECTION,
    PLOT_FINISH,
    PLOT_JOG,
    PLOT_RAPID,
    PLOT_SETTING,
    Interpreter,
)
from .moshiconstants import swizzle_table


class MoshiInterpreter(Interpreter, Modifier):
    def __init__(self, context, job_name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, job_name, channel)
        Interpreter.__init__(self, context=context)

        self.plot_planner = PlotPlanner(self.settings)

        self.plot = None
        self.plot_gen = None

        self.offset_x = 0
        self.offset_y = 0
        self.next_x = None
        self.next_y = None
        self.max_x = None
        self.max_y = None
        self.min_x = None
        self.min_y = None
        self.start_x = None
        self.start_y = None
        self.is_paused = False
        self.context._buffer_size = 0
        self.pipe = self.context.channel("pipe/send")
        self.control = self.context.channel("pipe/control")
        self.thread = None

    def attach(self, *a, **kwargs):
        context = self.context
        root_context = context.get_context("/")
        kernel = context._kernel
        _ = kernel.translation

        context.interpreter = self

        context.setting(int, "home_adjust_x", 0)
        context.setting(int, "home_adjust_y", 0)
        context.setting(bool, "home_right", False)
        context.setting(bool, "home_bottom", False)
        context.setting(int, "current_x", 0)
        context.setting(int, "current_y", 0)
        root_context.setting(bool, "opt_rapid_between", True)
        root_context.setting(int, "opt_jog_mode", 0)
        root_context.setting(int, "opt_jog_minimum", 127)

        context.get_context("/").listen("lifecycle;ready", self.on_interpreter_ready)

    def detach(self, *args, **kwargs):
        self.context.get_context("/").unlisten(
            "lifecycle;ready", self.on_interpreter_ready
        )
        self.thread = None

    def on_interpreter_ready(self, *args):
        self.start_interpreter()

    def __repr__(self):
        return "MoshiInterpreter()"

    def swizzle(self, b, p7, p6, p5, p4, p3, p2, p1, p0):
        return (
            ((b >> 0) & 1) << p0
            | ((b >> 1) & 1) << p1
            | ((b >> 2) & 1) << p2
            | ((b >> 3) & 1) << p3
            | ((b >> 4) & 1) << p4
            | ((b >> 5) & 1) << p5
            | ((b >> 6) & 1) << p6
            | ((b >> 7) & 1) << p7
        )

    def convert(self, q):
        if q & 1:
            return self.swizzle(q, 7, 6, 2, 4, 3, 5, 1, 0)
        else:
            return self.swizzle(q, 5, 1, 7, 2, 4, 3, 6, 0)

    def reconvert(self, q):
        for m in range(5):
            q = self.convert(q)
        return q

    def pipe_int8(self, value):
        v = bytes(
            bytearray(
                [
                    value & 0xFF,
                ]
            )
        )
        self.pipe(v)

    def pipe_int16le(self, value):
        v = bytes(
            bytearray(
                [
                    (value >> 0) & 0xFF,
                    (value >> 8) & 0xFF,
                ]
            )
        )
        self.pipe(v)

    def write_vector_speed(self, speed_mms, normal_speed_mms):
        """
        Vector Speed Byte. (0x00 position), followed by 2 int8 values.
        Speed and Normal Speed.
        :return:
        """
        self.pipe(swizzle_table[5][0])
        if speed_mms > 256:
            speed_mms = 256
        if speed_mms < 1:
            speed_mms = 1
        self.pipe_int8(speed_mms - 1)
        self.pipe_int8(normal_speed_mms - 1)  # Unknown

    def write_raster_speed(self, speed_mms):
        self.pipe(swizzle_table[4][0])
        speed_cms = int(round(speed_mms / 10))
        if speed_cms == 0:
            speed_cms = 1
        self.pipe_int8(speed_cms - 1)

    def write_set_offset(self, z, x, y):
        """
        2nd Command For Jump. (0x03 position), followed by 3 int16le (2)
        :return:
        """
        self.pipe(swizzle_table[0][0])
        self.pipe_int16le(z)  # Unknown, always zero.
        self.pipe_int16le(x)  # x
        self.pipe_int16le(y)  # y

    def write_termination(self):
        """
        Terminal Commands for Jump/Program. (last 7 bytes). (4)
        :return:
        """
        for i in range(7):
            self.pipe(swizzle_table[2][0])

    def write_cut_abs(self, x, y):
        self.pipe(swizzle_table[15][1])
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.context.current_x = x
        self.context.current_y = y
        x -= self.offset_x
        y -= self.offset_y
        self.pipe_int16le(int(x))
        self.pipe_int16le(int(y))

    def write_move_abs(self, x, y):
        self.pipe(swizzle_table[7][0])
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.context.current_x = x
        self.context.current_y = y
        x -= self.offset_x
        y -= self.offset_y
        self.pipe_int16le(int(x))
        self.pipe_int16le(int(y))

    def write_move_vertical_abs(self, y):
        self.context.current_y = y
        y -= self.offset_y
        self.pipe(swizzle_table[3][0])
        self.pipe_int16le(int(y))

    def write_move_horizontal_abs(self, x):
        self.context.current_x = x
        x -= self.offset_x
        self.pipe(swizzle_table[6][0])
        self.pipe_int16le(int(x))

    def write_cut_horizontal_abs(self, x):
        self.context.current_x = x
        x -= self.offset_x
        self.pipe(swizzle_table[14][0])
        self.pipe_int16le(int(x))

    def write_cut_vertical_abs(self, y):
        self.context.current_y = y
        y -= self.offset_y
        self.pipe(swizzle_table[11][0])
        self.pipe_int16le(int(y))

    def ensure_program_mode(self):
        if self.state == INTERPRETER_STATE_PROGRAM:
            return
        if self.state == INTERPRETER_STATE_RASTER:
            self.ensure_rapid_mode()
        speed = int(self.settings.speed)
        # Normal speed is rapid. Passing same speed so PPI isn't crazy.
        self.write_vector_speed(speed, speed)
        x, y = self.calc_home_position()
        self.offset_x = x
        self.offset_y = y
        self.write_set_offset(0, x, y)
        self.state = INTERPRETER_STATE_PROGRAM
        self.context.signal("interpreter;mode", self.state)

    def ensure_raster_mode(self):
        if self.state == INTERPRETER_STATE_RASTER:
            return
        if self.state == INTERPRETER_STATE_PROGRAM:
            self.ensure_rapid_mode()
        speed = int(self.settings.speed)
        self.write_raster_speed(speed)
        x, y = self.calc_home_position()
        self.offset_x = x
        self.offset_y = y
        self.write_set_offset(0, x, y)
        self.state = INTERPRETER_STATE_RASTER
        self.context.signal("interpreter;mode", self.state)
        self.write_move_abs(0, 0)

    def ensure_rapid_mode(self):
        if self.state == INTERPRETER_STATE_RAPID:
            return
        if self.state == INTERPRETER_STATE_FINISH:
            self.state = INTERPRETER_STATE_RAPID
        elif (
            self.state == INTERPRETER_STATE_PROGRAM
            or self.state == INTERPRETER_STATE_MODECHANGE
            or self.state == INTERPRETER_STATE_RASTER
        ):
            self.write_termination()
            self.control("execute\n")
        self.state = INTERPRETER_STATE_RAPID
        self.context.signal("interpreter;mode", self.state)

    def ensure_finished_mode(self):
        if self.state == INTERPRETER_STATE_FINISH:
            return
        if (
            self.state == INTERPRETER_STATE_PROGRAM
            or self.state == INTERPRETER_STATE_MODECHANGE
            or self.state == INTERPRETER_STATE_RASTER
        ):
            self.ensure_rapid_mode()
            self.state = INTERPRETER_STATE_FINISH

    def plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        :return:
        """
        if self.plot is not None:
            while True:
                try:
                    if self.hold():
                        return True
                    x, y, on = next(self.plot)
                except StopIteration:
                    break
                except TypeError:
                    break
                on = int(on)
                if on & PLOT_FINISH:  # Plot planner is ending.
                    self.ensure_rapid_mode()
                    continue
                if on & PLOT_SETTING:  # Plot planner settings have changed.
                    p_set = self.plot_planner.settings
                    s_set = self.settings
                    if p_set.power != s_set.power:
                        self.set_power(p_set.power)
                    if (
                        p_set.speed != s_set.speed
                        or p_set.raster_step != s_set.raster_step
                    ):
                        self.set_speed(p_set.speed)
                        self.set_step(p_set.raster_step)
                        self.ensure_rapid_mode()
                    self.settings.set_values(p_set)
                    continue
                if on & PLOT_AXIS:  # Major Axis.
                    continue
                if on & PLOT_DIRECTION:
                    continue
                if on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    self.ensure_rapid_mode()
                    self.move_absolute(x, y)
                    continue
                self.goto_absolute(x, y, on & 1)
            self.plot = None
        return False

    def goto_absolute(self, x, y, cut):
        if self.settings.raster_step == 0:
            self.ensure_program_mode()
        else:
            self.ensure_program_mode()
            # self.ensure_raster_mode() # Rastermode is not functional.
        if self.state == INTERPRETER_STATE_PROGRAM:
            if cut:
                self.write_cut_abs(x, y)
            else:
                self.write_move_abs(x, y)
        else:
            if x == self.context.current_x and y == self.context.current_y:
                return
            if cut:
                if x == self.context.current_x:
                    self.write_cut_vertical_abs(y=y)
                if y == self.context.current_y:
                    self.write_cut_horizontal_abs(x=x)
            else:
                if x == self.context.current_x:
                    self.write_move_vertical_abs(y=y)
                if y == self.context.current_y:
                    self.write_move_horizontal_abs(x=x)
        oldx = self.context.current_x
        oldy = self.context.current_y
        self.context.current_x = x
        self.context.current_y = y
        self.context.signal("interpreter;position", (oldx, oldy, x, y))

    def plot_plot(self, plot):
        """
        :param plot:
        :return:
        """
        self.plot_planner.push(plot)

    def plot_start(self):
        if self.plot is None:
            self.plot = self.plot_planner.gen()

    def cut(self, x, y):
        if self.is_relative:
            self.cut_relative(x, y)
        else:
            self.cut_absolute(x, y)
        self.ensure_rapid_mode()
        self.control("execute\n")

    def cut_absolute(self, x, y):
        self.ensure_program_mode()
        self.write_cut_abs(x, y)

        oldx = self.context.current_x
        oldy = self.context.current_y
        self.context.current_x = x
        self.context.current_y = y
        self.context.signal("interpreter;position", (oldx, oldy, x, y))

    def cut_relative(self, dx, dy):
        x = dx + self.context.current_x
        y = dy + self.context.current_y
        self.cut_absolute(x, y)

    def jog(self, x, y, **kwargs):
        self.move(x, y)

    def move(self, x, y):
        if self.is_relative:
            self.move_relative(x, y)
        else:
            self.move_absolute(x, y)
        self.ensure_rapid_mode()
        self.control("execute\n")

    def move_absolute(self, x, y):
        self.ensure_program_mode()
        oldx = self.context.current_x
        oldy = self.context.current_y
        self.write_move_abs(x, y)
        x = self.context.current_x
        y = self.context.current_y
        self.context.signal("interpreter;position", (oldx, oldy, x, y))

    def move_relative(self, dx, dy):
        x = dx + self.context.current_x
        y = dy + self.context.current_y
        self.move_absolute(x, y)

    def set_speed(self, speed=None):
        if self.settings.speed != speed:
            self.settings.speed = speed
            if (
                self.state == INTERPRETER_STATE_PROGRAM
                or self.state == INTERPRETER_STATE_RASTER
            ):
                self.state = INTERPRETER_STATE_MODECHANGE

    def set_step(self, step=None):
        if self.settings.raster_step != step:
            self.settings.raster_step = step
            if (
                self.state == INTERPRETER_STATE_PROGRAM
                or self.state == INTERPRETER_STATE_RASTER
            ):
                self.state = INTERPRETER_STATE_MODECHANGE

    def calc_home_position(self):
        x = self.context.home_adjust_x
        y = self.context.home_adjust_y
        bed_dim = self.context.get_context("/")
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        if self.context.home_right:
            x += int(bed_dim.bed_width * 39.3701)
        if self.context.home_bottom:
            y += int(bed_dim.bed_height * 39.3701)
        return x, y

    def home(self, *values):
        self.offset_x = 0
        self.offset_y = 0

        x, y = self.calc_home_position()
        try:
            x = int(values[0])
        except (ValueError, IndexError):
            pass
        try:
            y = int(values[1])
        except (ValueError, IndexError):
            pass
        self.ensure_rapid_mode()
        self.is_relative = False
        self.move(x, y)

    def lock_rail(self):
        pass

    def unlock_rail(self, abort=False):
        self.ensure_rapid_mode()
        self.control("unlock\n")

    def abort(self):
        self.control("stop\n")
