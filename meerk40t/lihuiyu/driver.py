"""
Lihuiyu Driver

Governs the generic commands issued by laserjob and spooler and converts that into regular LHYMicro-GL output.

This generated data is then sent to the controller, which could be a network connection, usb, or mock depending on the
selected output.
"""

import math
import time

from meerk40t.tools.zinglplotter import ZinglPlotter

from ..core.cutcode.dwellcut import DwellCut
from ..core.cutcode.gotocut import GotoCut
from ..core.cutcode.homecut import HomeCut
from ..core.cutcode.inputcut import InputCut
from ..core.cutcode.outputcut import OutputCut
from ..core.cutcode.plotcut import PlotCut
from ..core.cutcode.waitcut import WaitCut
from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner, grouped
from ..device.basedevice import (
    DRIVER_STATE_FINISH,
    DRIVER_STATE_MODECHANGE,
    DRIVER_STATE_PROGRAM,
    DRIVER_STATE_RAPID,
    DRIVER_STATE_RASTER,
    PLOT_AXIS,
    PLOT_DIRECTION,
    PLOT_FINISH,
    PLOT_JOG,
    PLOT_RAPID,
    PLOT_SETTING,
)
from .laserspeed import LaserSpeed

distance_lookup = [
    b"",
    b"a",
    b"b",
    b"c",
    b"d",
    b"e",
    b"f",
    b"g",
    b"h",
    b"i",
    b"j",
    b"k",
    b"l",
    b"m",
    b"n",
    b"o",
    b"p",
    b"q",
    b"r",
    b"s",
    b"t",
    b"u",
    b"v",
    b"w",
    b"x",
    b"y",
    b"|a",
    b"|b",
    b"|c",
    b"|d",
    b"|e",
    b"|f",
    b"|g",
    b"|h",
    b"|i",
    b"|j",
    b"|k",
    b"|l",
    b"|m",
    b"|n",
    b"|o",
    b"|p",
    b"|q",
    b"|r",
    b"|s",
    b"|t",
    b"|u",
    b"|v",
    b"|w",
    b"|x",
    b"|y",
    b"|z",
]


def lhymicro_distance(v):
    if v < 0:
        raise ValueError("Cannot permit negative values.")
    dist = b""
    if v >= 255:
        zs = int(v / 255)
        v %= 255
        dist += b"z" * zs
    if v >= 52:
        return dist + b"%03d" % v
    return dist + distance_lookup[v]


class LihuiyuDriver(Parameters):
    """
    LihuiyuDriver provides Lihuiyu specific coding for elements and sends it to the backend
    to write to the usb.
    """

    def __init__(self, service, *args, **kwargs):
        super().__init__()
        self.service = service
        self.name = str(self.service)
        self._topward = False
        self._leftward = False
        self._x_engaged = False
        self._y_engaged = False
        self._horizontal_major = False

        self._request_leftward = None
        self._request_topward = None
        self._request_horizontal_major = None

        self.out_pipe = None

        self.process_item = None
        self.spooled_item = None
        self.holds = []
        self.temp_holds = []

        self.native_x = 0
        self.native_y = 0

        self.plot_planner = PlotPlanner(self.settings)
        self.plot_planner.force_shift = service.plot_shift
        self.plot_data = None

        self.state = DRIVER_STATE_RAPID
        self.properties = 0
        self.is_relative = False
        self.laser = False
        self._thread = None
        self._shutdown = False
        self.last_fetch = None

        self.CODE_RIGHT = b"B"
        self.CODE_LEFT = b"T"
        self.CODE_TOP = b"L"
        self.CODE_BOTTOM = b"R"
        self.CODE_ANGLE = b"M"
        self.CODE_LASER_ON = b"D"
        self.CODE_LASER_OFF = b"U"

        self.paused = False

        def primary_hold():
            if self.out_pipe is None:
                return True
            if hasattr(self.out_pipe, "is_shutdown") and self.out_pipe.is_shutdown:
                raise ConnectionAbortedError("Cannot hold for a shutdown pipe.")
            try:
                buffer = len(self.out_pipe)
            except TypeError:
                buffer = 0
            return self.service.buffer_limit and buffer > self.service.buffer_max

        self.holds.append(primary_hold)

        # Step amount expected of the current operation
        self._raster_step_float = 0

        # Step amount is the current correctly set step amount in the controller.
        self._raster_step_g_value = 0

        # Step index of the current step taken for unidirectional
        self._raster_step_swing_index = 0

        # Step total the count for fractional step amounts
        self._raster_step_fractional_remainder = 0.0

    def __repr__(self):
        return f"LihuiyuDriver({self.name})"

    def __call__(self, e):
        self.out_pipe.write(e)

    def hold_work(self, priority):
        """
        Holds are criteria to use to pause the data interpretation. These halt the production of new data until the
        criteria is met. A hold is constant and will always halt the data while true. A temp_hold will be removed
        as soon as it does not hold the data.

        @return: Whether data interpretation should hold.
        """
        if priority > 0:
            # Don't hold realtime work.
            return False

        temp_hold = False
        fail_hold = False
        for i, hold in enumerate(self.temp_holds):
            if not hold():
                self.temp_holds[i] = None
                fail_hold = True
            else:
                temp_hold = True
        if fail_hold:
            self.temp_holds = [hold for hold in self.temp_holds if hold is not None]
        if temp_hold:
            return True
        for hold in self.holds:
            if hold():
                return True
        return False

    def get(self, key, default=None):
        """
        Required.

        @param key: Key to get.
        @param default: Default value to use.
        @return:
        """
        return self.settings.get(key, default=default)

    def set(self, key, value):
        """
        Required.

        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.

        @param key:
        @param value:
        @return:
        """
        if key == "power":
            self._set_power(value)
        elif key == "ppi":
            self._set_power(value)
        elif key == "pwm":
            self._set_power(value)
        elif key == "overscan":
            self._set_overscan(value)
        elif key == "acceleration":
            self._set_acceleration(value)
        elif key == "relative":
            self.is_relative = value
        elif key == "d_ratio":
            self._set_d_ratio(value)
        elif key == "step":
            self._set_step(*value)
        else:
            self.settings[key] = value

    def status(self):
        """
        Wants a status report of what the driver is doing.
        @return:
        """
        state_major = "idle"
        state_minor = "idle"
        if self.state == DRIVER_STATE_RAPID:
            state_major = "idle"
            state_minor = "idle"
        elif self.state == DRIVER_STATE_FINISH:
            state_major = "idle"
            state_minor = "finished"
        elif self.state == DRIVER_STATE_PROGRAM:
            state_major = "busy"
            state_minor = "program"
        elif self.state == DRIVER_STATE_RASTER:
            state_major = "busy"
            state_minor = "raster"
        elif self.state == DRIVER_STATE_MODECHANGE:
            state_major = "busy"
            state_minor = "changing"
        return (self.native_x, self.native_y), state_major, state_minor

    def pause(self, *values):
        """
        Asks that the laser be paused.

        @return:
        """
        self(b"~PN!\n~")
        self.paused = True

    def resume(self, *values):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser, without that it will
        be paused and unable to process the resume.

        @param values:
        @return:
        """
        self(b"~PN&\n~")
        self.paused = False

    def reset(self):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.

        Asks that the device resets, and clears all current work.

        @return:
        """
        self.service.spooler.clear_queue()
        self.plot_planner.clear()
        self.spooled_item = None
        self.temp_holds.clear()

        self.service.signal("pipe;buffer", 0)
        self(b"~I*\n~")
        self._reset_modes()
        self.state = DRIVER_STATE_RAPID
        self.service.signal("driver;mode", self.state)
        self.paused = False

    def abort(self):
        self(b"I\n")

    def blob(self, blob_type, data):
        """
        Blob sends a data blob. This is native code data of the give type. For example in a ruida device it might be a
        bunch of .rd code, or Lihuiyu device it could be .egv code. It's a method of sending pre-chewed data to the
        device.

        @param blob_type:
        @param data:
        @return:
        """
        if blob_type == "egv":
            self(data)

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        if self.service.swap_xy:
            x, y = y, x
        x, y = self.service.physical_to_device_position(x, y)
        self.rapid_mode()
        self._move_absolute(int(round(x)), int(round(y)))

    def move_rel(self, dx, dy):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        if self.service.swap_xy:
            dx, dy = dy, dx
        dx, dy = self.service.physical_to_device_length(dx, dy)
        self.rapid_mode()
        self._move_relative(dx, dy)

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        self.rapid_mode()
        self.wait_finish()
        self.laser_on()  # This can't be sent early since these are timed operations.
        self.wait(time_in_ms)
        self.laser_off()

    def laser_off(self):
        """
        Turn laser off in place.

        @return:
        """
        if not self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self(b"I")
            self(self.CODE_LASER_OFF)
            self(b"S1P\n")
            if not self.service.autolock:
                self(b"IS2P\n")
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
            self(self.CODE_LASER_OFF)
        elif self.state == DRIVER_STATE_FINISH:
            self(self.CODE_LASER_OFF)
            self(b"N")
        self.laser = False
        return True

    def laser_on(self):
        """
        Turn laser on in place.

        @return:
        """
        if self.laser:
            return False
        if self.state == DRIVER_STATE_RAPID:
            self(b"I")
            self(self.CODE_LASER_ON)
            self(b"S1P\n")
            if not self.service.autolock:
                self(b"IS2P\n")
        elif self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
            self(self.CODE_LASER_ON)
        elif self.state == DRIVER_STATE_FINISH:
            self(self.CODE_LASER_ON)
            self(b"N")
        self.laser = True
        return True

    def rapid_mode(self, *values):
        """
        Rapid mode sets the laser to rapid state. This is usually moving the laser around without it executing a large
        batch of commands.

        @param values:
        @return:
        """
        if self.state == DRIVER_STATE_RAPID:
            return
        if self.state == DRIVER_STATE_FINISH:
            self(b"S1P\n")
            if not self.service.autolock:
                self(b"IS2P\n")
        elif self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self(b"FNSE-\n")
            self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.service.signal("driver;mode", self.state)

    def finished_mode(self, *values):
        """
        Finished mode is after a large batch of jobs is done. A transition to finished may require the laser process
        all the data in the buffer.

        @param values:
        @return:
        """
        if self.state == DRIVER_STATE_FINISH:
            return
        if self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_RASTER,
            DRIVER_STATE_MODECHANGE,
        ):
            self(b"@NSE")
            self.laser = False
        elif self.state == DRIVER_STATE_RAPID:
            self(b"I")
        self.state = DRIVER_STATE_FINISH
        self.service.signal("driver;mode", self.state)

    def raster_mode(self, *values, dx=0, dy=0):
        """
        Raster mode runs in either `G0xx` stepping mode. It  is only intended to move horizontal or
        vertical rastering, usually at a high speed. Accel twitches are required for this mode.

        @param values:
        @param dx: movement during raster mode switch
        @param dy: movement during raster mode switch
        @return:
        """
        if self.raster_step_y == 0 and self.raster_step_x == 0:
            # This is not properly set raster mode.
            self.program_mode(*values, dx=dx, dy=dy)
            return
        if self.state == DRIVER_STATE_RASTER:
            return
        self.finished_mode()

        horizontal = self.raster_step_y != 0
        self._request_horizontal_major = horizontal

        self._raster_step_swing_index = 0
        self._raster_step_float = (
            self.raster_step_y if horizontal else self.raster_step_x
        )
        if self._raster_step_float is None:
            self._raster_step_float = 1
        self._raster_step_g_value = int(math.floor(self._raster_step_float))

        if self._request_leftward is not None:
            self._leftward = self._request_leftward
            self._request_leftward = None
        if self._request_topward is not None:
            self._topward = self._request_topward
            self._request_topward = None
        if self._request_horizontal_major is not None:
            self._horizontal_major = self._request_horizontal_major
            self._request_horizontal_major = None

        if self.service.strict:
            # Override requested or current values only use core initial values.
            self._leftward = False
            self._topward = False
            self._horizontal_major = False
        if self.bidirectional:
            # Bidirectional (step on forward/back swing - rasters both directions)
            raster_step_value = self._raster_step_g_value
        else:
            # Unidirectional (step on forward swing - rasters only going forward)
            raster_step_value = self._raster_step_g_value, 0
        speed_code = LaserSpeed(
            self.service.board,
            self.speed,
            raster_step=raster_step_value,
            d_ratio=self.implicit_d_ratio,
            acceleration=self.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            suffix_c=False,
            fix_speeds=self.service.fix_speeds,
            raster_horizontal=horizontal,
        ).speedcode
        speed_code = bytes(speed_code, "utf8")
        self(speed_code)
        self._goto_xy(dx, dy)
        self(b"N")
        self(self._code_declare_directions())
        self(b"S1E")
        self.state = DRIVER_STATE_RASTER
        self.service.signal("driver;mode", self.state)

    def program_mode(self, *values, dx=0, dy=0):
        """
        Vector Mode implies but doesn't discount rastering. Twitches are used if twitches is set to True.

        @param values: passed information from the driver command
        @param dx: change in dx that should be made while switching to program mode.
        @param dy: change in dy that should be made while switching to program mode.
        @return:
        """
        if self.state == DRIVER_STATE_PROGRAM:
            return
        self.finished_mode()

        self._raster_step_swing_index = 0
        self._raster_step_float = 0
        self._raster_step_g_value = 0

        suffix_c = None
        if (
            not self.service.twitches or self.settings.get("_force_twitchless", False)
        ) and not self._raster_step_float:
            suffix_c = True
        if self._request_leftward is not None:
            self._leftward = self._request_leftward
            self._request_leftward = None
        if self._request_topward is not None:
            self._topward = self._request_topward
            self._request_topward = None
        if self._request_horizontal_major is not None:
            self._horizontal_major = self._request_horizontal_major
            self._request_horizontal_major = None
        if self.service.strict:
            # Override requested or current values only use core initial values.
            self._leftward = False
            self._topward = False
            self._horizontal_major = False

        speed_code = LaserSpeed(
            self.service.board,
            self.speed,
            raster_step=0,
            d_ratio=self.implicit_d_ratio,
            acceleration=self.implicit_accel,
            fix_limit=True,
            fix_lows=True,
            suffix_c=suffix_c,
            fix_speeds=self.service.fix_speeds,
            raster_horizontal=self._horizontal_major,
        ).speedcode
        speed_code = bytes(speed_code, "utf8")
        self(speed_code)
        self._goto_xy(dx, dy)
        self(b"N")
        self(self._code_declare_directions())
        self(b"S1E")
        if self._raster_step_float:
            self.state = DRIVER_STATE_RASTER
        else:
            self.state = DRIVER_STATE_PROGRAM
        self.service.signal("driver;mode", self.state)

    def home(self, *values):
        """
        Home the laser.

        @param values:
        @return:
        """
        if self.service.rotary_active and self.service.rotary_supress_home:
            return
        self.rapid_mode()
        self(b"IPP\n")
        old_current = self.service.current
        self.native_x = 0
        self.native_y = 0
        self._reset_modes()
        self.state = DRIVER_STATE_RAPID
        self.service.signal("driver;mode", self.state)

        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def physical_home(self):
        """ "
        This would be the command to go to a real physical home position (ie hitting endstops)
        """
        self.home()

    def lock_rail(self):
        """
        For plotter-style lasers this should prevent the laser bar from moving.

        @return:
        """
        self.rapid_mode()
        self(b"IS1P\n")

    def unlock_rail(self, abort=False):
        """
        For plotter-style jobs this should free the laser head to be movable by the user.

        @return:
        """
        self.rapid_mode()
        self(b"IS2P\n")

    def laser_disable(self, *values):
        self.laser_enabled = False

    def laser_enable(self, *values):
        self.laser_enabled = True

    def plot(self, plot):
        """
        Gives the driver cutcode that should be plotted/performed.

        @param plot:
        @return:
        """
        if isinstance(plot, InputCut):
            self.plot_start()
            self.wait_finish()
            # We do not have any GPIO-output abilities
        elif isinstance(plot, OutputCut):
            self.plot_start()
            self.wait_finish()
            # We do not have any GPIO-input abilities
        elif isinstance(plot, DwellCut):
            self.plot_start()
            self.rapid_mode()
            start = plot.start
            self.move_abs(start[0], start[1])
            self.wait_finish()
            self.dwell(plot.dwell_time)
        elif isinstance(plot, WaitCut):
            self.plot_start()
            self.wait_finish()
            self.wait(plot.dwell_time)
        elif isinstance(plot, HomeCut):
            self.plot_start()
            self.wait_finish()
            self.home()
        elif isinstance(plot, GotoCut):
            self.plot_start()
            start = plot.start
            self.wait_finish()
            self._move_absolute(start[0], start[1])
        else:
            # LineCut, QuadCut, CubicCut, PlotCut, RasterCut
            if isinstance(plot, PlotCut):
                plot.check_if_rasterable()
            self.plot_planner.push(plot)

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all cutcode as a group, if this
        is needed by the driver.

        @return:
        """
        if self.plot_data is None:
            self.plot_data = self.plot_planner.gen()
        self._plotplanner_process()

    def wait(self, time_in_ms):
        """
        Wait asks that the work be stalled or current process held for the time time_in_ms in ms. If wait_finished is
        called first this will attempt to stall the machine while performing no work. If the driver in question permits
        waits to be placed within code this should insert waits into the current job. Returning instantly rather than
        holding the processes.

        @param time_in_ms:
        @return:
        """
        time.sleep(time_in_ms / 1000.0)

    def wait_finish(self, *values):
        """
        Wait finish should ensure that no additional commands be processed until the current buffer is completed. This
        does not necessarily imply a change in mode as "finished_mode" would require. Just that the buffer be completed
        before moving on.

        @param values:
        @return:
        """

        def temp_hold():
            try:
                return len(self.out_pipe) != 0
            except TypeError:
                return False

        self.temp_holds.append(temp_hold)

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooled cycle.

        @param function:
        @return:
        """
        function()

    def beep(self):
        """
        This command asks that a beep be executed at the appropriate time within the spooled cycle.

        @return:
        """
        self.service("beep\n")

    def console(self, value):
        """
        This asks that the console command be executed at the appropriate time within the spooled cycle.

        @param value: console command
        @return:
        """
        self.service(value)

    def signal(self, signal, *args):
        """
        This asks that this signal be broadcast.

        @param signal:
        @param args:
        @return:
        """
        self.service.signal(signal, *args)

    ######################
    # Property IO
    ######################

    @property
    def is_left(self):
        return self._x_engaged and not self._y_engaged and self._leftward

    @property
    def is_right(self):
        return self._x_engaged and not self._y_engaged and not self._leftward

    @property
    def is_top(self):
        return not self._x_engaged and self._y_engaged and self._topward

    @property
    def is_bottom(self):
        return not self._x_engaged and self._y_engaged and not self._topward

    @property
    def is_angle(self):
        return self._y_engaged and self._x_engaged

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

    ######################
    # PROTECTED DRIVER CODE
    ######################

    def _plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        @return:
        """
        if self.plot_data is None:
            return False
        for x, y, on in self.plot_data:
            while self.hold_work(0):
                time.sleep(0.05)
            sx = self.native_x
            sy = self.native_y
            # print("x: %s, y: %s -- c: %s, %s" % (str(x), str(y), str(sx), str(sy)))
            on = int(on)
            if on > 1:
                # Special Command.
                if on & PLOT_FINISH:  # Plot planner is ending.
                    self.rapid_mode()
                    break
                elif on & PLOT_SETTING:  # Plot planner settings have changed.
                    p_set = Parameters(self.plot_planner.settings)
                    if p_set.power != self.power:
                        self._set_power(p_set.power)
                    if (
                        p_set.raster_step_x != self.raster_step_x
                        or p_set.raster_step_y != self.raster_step_y
                        or p_set.speed != self.speed
                        or self.implicit_d_ratio != p_set.implicit_d_ratio
                        or self.implicit_accel != p_set.implicit_accel
                    ):
                        self._set_speed(p_set.speed)
                        self._set_step(p_set.raster_step_x, p_set.raster_step_y)
                        self._set_acceleration(p_set.implicit_accel)
                        self._set_d_ratio(p_set.implicit_d_ratio)
                    self.settings.update(p_set.settings)
                elif on & PLOT_AXIS:  # Major Axis.
                    # 0 means X Major / Horizontal.
                    # 1 means Y Major / Vertical
                    self._request_horizontal_major = bool(x == 0)
                elif on & PLOT_DIRECTION:
                    # -1: Moving Left -x
                    # 1: Moving Right. +x
                    self._request_leftward = bool(x != 1)
                    # -1: Moving Bottom +y
                    # 1: Moving Top. -y
                    self._request_topward = bool(y != 1)
                elif on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    if (
                        on & PLOT_RAPID
                        or self.state != DRIVER_STATE_PROGRAM
                        or self.service.rapid_override
                    ):
                        # Perform a rapid position change. Always perform this for raster moves.
                        # DRIVER_STATE_RASTER should call this code as well.
                        self.rapid_mode()
                        self._move_absolute(x, y)
                    else:
                        # Jog is performable and requested. # We have not flagged our direction or state.
                        self._jog_absolute(x, y, mode=self.service.opt_jog_mode)
                continue
            dx = x - sx
            dy = y - sy
            step_x = self.raster_step_x
            step_y = self.raster_step_y
            if step_x == 0 and step_y == 0:
                # vector mode
                self.program_mode()
            else:
                self.raster_mode()
                if self._horizontal_major:
                    # Horizontal Rastering.
                    if dy != 0:
                        self._h_switch_g(dy)
                else:
                    # Vertical Rastering.
                    if dx != 0:
                        self._v_switch_g(dx)
                # Update dx, dy (if changed by switches)
                dx = x - self.native_x
                dy = y - self.native_y
            self._goto_octent(dx, dy, on & 1)
        self.plot_data = None
        return False

    def _set_speed(self, speed=None):
        if self.speed != speed:
            self.speed = speed
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_d_ratio(self, d_ratio=None):
        if self.dratio != d_ratio:
            self.dratio = d_ratio
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_acceleration(self, accel=None):
        if self.acceleration != accel:
            self.acceleration = accel
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_step(self, step_x=None, step_y=None):
        if self.raster_step_x != step_x or self.raster_step_y != step_y:
            self.raster_step_x = step_x
            self.raster_step_y = step_y
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_power(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def _set_ppi(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def _set_pwm(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

    def _set_overscan(self, overscan=None):
        self.overscan = overscan

    def _cut(self, x, y):
        self._goto(x, y, True)

    def _jog(self, x, y, **kwargs):
        if self.is_relative:
            self._jog_relative(x, y, **kwargs)
        else:
            self._jog_absolute(x, y, **kwargs)

    def _jog_absolute(self, x, y, **kwargs):
        self._jog_relative(x - self.native_x, y - self.native_y, **kwargs)

    def _jog_relative(self, dx, dy, mode=0):
        self.laser_off()
        dx = int(round(dx))
        dy = int(round(dy))
        if mode == 0:
            self._nse_jog_event(dx, dy)
        elif mode == 1:
            self._mode_shift_on_the_fly(dx, dy)
        else:
            # Finish-out Jog
            self.rapid_mode()
            self._move_relative(dx, dy)
            self.program_mode()

    def _nse_jog_event(self, dx=0, dy=0, speed=None):
        """
        NSE Jog events are performed from program or raster mode and skip out to rapid mode to perform
        a single jog command. This jog effect varies based on the horizontal vertical major setting and
        needs to counteract the jogged head according to those settings.

        NSE jogs will not change the underlying mode even though they temporarily switch into
        rapid mode. nse jogs are not done in raster mode.
        """
        dx = int(round(dx))
        dy = int(round(dy))
        original_state = self.state
        self.state = DRIVER_STATE_RAPID
        self.laser = False
        if self._horizontal_major:
            if not self.is_left and dx >= 0:
                self(self.CODE_LEFT)
            if not self.is_right and dx <= 0:
                self(self.CODE_RIGHT)
        else:
            if not self.is_top and dy >= 0:
                self(self.CODE_TOP)
            if not self.is_bottom and dy <= 0:
                self(self.CODE_BOTTOM)
        self(b"N")
        self._goto_xy(dx, dy)
        self(b"SE")
        self(self._code_declare_directions())
        self.state = original_state

    def _move(self, x, y):
        self._goto(x, y, False)

    def _move_absolute(self, x, y):
        self._goto_absolute(x, y, False)

    def _move_relative(self, x, y):
        self._goto_relative(x, y, False)

    def _goto(self, x, y, cut):
        """
        Goto a position within a cut.

        This depends on whether is_relative is set.

        @param x:
        @param y:
        @param cut:
        @return:
        """
        if self.is_relative:
            self._goto_relative(x, y, cut)
        else:
            self._goto_absolute(x, y, cut)

    def _goto_absolute(self, x, y, cut):
        """
        Goto absolute x and y. With cut set or not set.

        @param x:
        @param y:
        @param cut:
        @return:
        """
        self._goto_relative(x - self.native_x, y - self.native_y, cut)

    def _move_override_speed(self, dx, dy, x_speed, y_speed=None):
        """
        Rapid movement override. Should make programmed jogs.

        @param dx: change in x
        @param dy: change in y
        @param x_speed: max allowed speed in x direction
        @param y_speed: max allowed speed in y direction
        @return:
        """
        if y_speed is None:
            y_speed = x_speed
        original_accel = self.acceleration
        original_speed = self.speed
        original_steps = self.raster_step_x, self.raster_step_y

        # Do not allow custom accel codes, or raster steps.
        self._set_acceleration(None)
        self._set_step(0, 0)
        # We know we will travel dx, dy. Set the initial direction requests.
        self._request_leftward = dx < 0
        self._request_topward = dy < 0
        self._request_horizontal_major = abs(dx) > abs(dy)
        if y_speed <= x_speed and abs(dy) >= abs(dx):
            # y_speed is slowest and dy is larger than dx. The y-shift will take longer than x-shift. Combine.
            self._set_speed(y_speed)
            self.program_mode()
            dy_m = int(
                math.copysign(dx, dy)
            )  # magnitude of shorter in the direction of longer.
            self._goto_octent(dx, dy_m, on=False)
            self._goto_octent(0, dy - dy_m, on=False)
        elif x_speed <= y_speed and abs(dx) >= abs(dy):
            # x_speed is slowest and dx is larger than dy. The x-shift will take longer than y-shift. Combine.
            self._set_speed(x_speed)
            self.program_mode()
            dx_m = int(
                math.copysign(dy, dx)
            )  # magnitude of shorter in the direction of longer.
            self._goto_octent(dx_m, dy, on=False)
            self._goto_octent(dx - dx_m, 0, on=False)
        else:
            # The faster speed is going longer. The slower speed is going shorter. Full zig.
            if dx != 0:
                self._set_speed(x_speed)
                self.program_mode()
                self._goto_octent(dx, 0, on=False)
            if dy != 0:
                self._set_speed(y_speed)
                self.program_mode()
                self._goto_octent(0, dy, on=False)
        self.rapid_mode()

        # We always restore the original settings.
        self._set_acceleration(original_accel)
        self._set_speed(original_speed)
        self._set_step(*original_steps)

    def _move_in_rapid_mode(self, dx, dy, cut):
        if self.service.rapid_override and (dx != 0 or dy != 0):
            y_speed = self.service.rapid_override_speed_y
            x_speed = self.service.rapid_override_speed_x
            self._move_override_speed(dx, dy, x_speed, y_speed)
            return
        self(b"I")
        self._goto_xy(dx, dy)
        self(b"S1P\n")
        if not self.service.autolock:
            self(b"IS2P\n")

    def _goto_relative(self, dx, dy, cut):
        """
        Goto relative dx, dy. With cut set or not set.

        @param dx:
        @param dy:
        @param cut:
        @return:
        """
        if abs(dx) == 0 and abs(dy) == 0:
            return
        dx = int(round(dx))
        dy = int(round(dy))
        old_current = self.service.current
        if self.state == DRIVER_STATE_RAPID:
            self._move_in_rapid_mode(dx, dy, cut)
        elif self.state == DRIVER_STATE_RASTER:
            # goto in raster, switches to program to recall this function.
            self.program_mode()
            self._goto_relative(dx, dy, cut)
            return
        elif self.state == DRIVER_STATE_PROGRAM:
            mx = 0
            my = 0
            line = list(grouped(ZinglPlotter.plot_line(0, 0, dx, dy)))
            for x, y in line:
                self._goto_octent(x - mx, y - my, cut)
                mx = x
                my = y
        elif self.state == DRIVER_STATE_FINISH:
            self._goto_xy(dx, dy)
            self(b"N")
        elif self.state == DRIVER_STATE_MODECHANGE:
            self._mode_shift_on_the_fly(dx, dy)

        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def _mode_shift_on_the_fly(self, dx=0, dy=0):
        """
        Mode-shift on the fly changes the current modes while in programmed or raster mode
        this exits with a @ command that resets the modes. A movement operation can be added after
        the speed code and before the return to into programmed or raster mode.

        This switch is often avoided because testing revealed some chance of a runaway during reset
        switching.

        If the raster step has been changed from zero this can result in shifting from program to raster mode
        """
        dx = int(round(dx))
        dy = int(round(dy))
        self(b"@NSE")
        self.laser = False
        self.state = DRIVER_STATE_RAPID
        self.program_mode(dx, dy)

    def _h_switch_g(self, dy: float):
        """
        Horizontal switch with a Gvalue set. The board will automatically step according to the step_value_set.

        @return:
        """
        set_step = self._raster_step_g_value
        if isinstance(set_step, tuple):
            set_step = set_step[self._raster_step_swing_index % len(set_step)]

        # correct for fractional stepping
        self._raster_step_fractional_remainder += dy
        delta = math.trunc(self._raster_step_fractional_remainder)
        self._raster_step_fractional_remainder -= delta

        step_amount = -abs(set_step) if self._topward else abs(set_step)
        remaining = delta - step_amount
        if (
            remaining > 0
            and self._topward
            or remaining < 0
            and not self._topward
            or abs(remaining) > 15
        ):
            # Remaining value is in the wrong direction, abort and move.
            self.finished_mode()
            self._move_relative(0, remaining)
            self.raster_mode()
            remaining = 0
        if remaining:
            self._goto_octent(
                -abs(remaining) if self._leftward else abs(remaining), remaining, False
            )
        self._x_engaged = True
        self._y_engaged = False
        # We reverse direction and step.
        if self._leftward:
            self(self.CODE_RIGHT)
            self._leftward = False
        else:
            self(self.CODE_LEFT)
            self._leftward = True
        self.native_y += step_amount
        self.laser = False
        self._raster_step_swing_index += 1

    def _v_switch_g(self, dx: float):
        """
        Vertical switch with a Gvalue set. The board will automatically step according to the step_value_set.

        @return:
        """
        set_step = self._raster_step_g_value
        if isinstance(set_step, tuple):
            set_step = set_step[self._raster_step_swing_index % len(set_step)]

        # correct for fractional stepping
        self._raster_step_fractional_remainder += dx
        delta = math.trunc(self._raster_step_fractional_remainder)
        self._raster_step_fractional_remainder -= delta

        step_amount = -set_step if self._leftward else set_step
        remaining = delta - step_amount
        if (
            remaining > 0
            and self._leftward
            or remaining < 0
            and not self._leftward
            or abs(remaining) > 15
        ):
            # Remaining value is in the wrong direction, abort and move.
            self.finished_mode()
            self._move_relative(remaining, 0)
            self.raster_mode()
            remaining = 0
        if remaining:
            self._goto_octent(
                remaining, -abs(remaining) if self._topward else abs(remaining), False
            )
        self._y_engaged = True
        self._x_engaged = False
        # We reverse direction and step.
        if self._topward:
            self(self.CODE_BOTTOM)
            self._topward = False
        else:
            self(self.CODE_TOP)
            self._topward = True
        self.native_x += step_amount
        self.laser = False
        self._raster_step_swing_index += 1

    def _reset_modes(self):
        self.laser = False
        self._request_leftward = None
        self._request_topward = None
        self._request_horizontal_major = None
        self._topward = False
        self._leftward = False
        self._x_engaged = False
        self._y_engaged = False
        self._horizontal_major = False

    def _goto_xy(self, dx, dy, on=None):
        rapid = self.state not in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER)
        if dx != 0:
            self.native_x += dx
            if dx > 0:  # Moving right
                if not self.is_right or rapid:
                    self(self.CODE_RIGHT)
                    self._leftward = False
            else:  # Moving left
                if not self.is_left or rapid:
                    self(self.CODE_LEFT)
                    self._leftward = True
            self._x_engaged = True
            self._y_engaged = False
            if on is not None:
                if on:
                    self.laser_on()
                else:
                    self.laser_off()
            self(lhymicro_distance(abs(dx)))
        if dy != 0:
            self.native_y += dy
            if dy > 0:  # Moving bottom
                if not self.is_bottom or rapid:
                    self(self.CODE_BOTTOM)
                    self._topward = False
            else:  # Moving top
                if not self.is_top or rapid:
                    self(self.CODE_TOP)
                    self._topward = True
            self._x_engaged = False
            self._y_engaged = True
            if on is not None:
                if on:
                    self.laser_on()
                else:
                    self.laser_off()
            self(lhymicro_distance(abs(dy)))

    def _goto_octent(self, dx, dy, on):
        old_current = self.service.current
        if dx == 0 and dy == 0:
            return
        if abs(dx) == abs(dy):
            self._x_engaged = True  # Set both on
            self._y_engaged = True
            if dx > 0:  # Moving right
                if self._leftward:
                    self(self.CODE_RIGHT)
                    self._leftward = False
            else:  # Moving left
                if not self._leftward:
                    self(self.CODE_LEFT)
                    self._leftward = True
            if dy > 0:  # Moving bottom
                if self._topward:
                    self(self.CODE_BOTTOM)
                    self._topward = False
            else:  # Moving top
                if not self._topward:
                    self(self.CODE_TOP)
                    self._topward = True
            self.native_x += dx
            self.native_y += dy
            self(self.CODE_ANGLE)
            if on:
                self.laser_on()
            else:
                self.laser_off()
            self(lhymicro_distance(abs(dy)))
        else:
            self._goto_xy(dx, dy, on=on)

        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def _code_declare_directions(self):
        x_dir = self.CODE_LEFT if self._leftward else self.CODE_RIGHT
        y_dir = self.CODE_TOP if self._topward else self.CODE_BOTTOM
        if self._horizontal_major:
            self._x_engaged = True
            self._y_engaged = False
            return y_dir + x_dir
        else:
            self._x_engaged = False
            self._y_engaged = True
            return x_dir + y_dir
