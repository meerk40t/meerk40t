"""
Moshiboard Driver

Governs the generic commands issued by laserjob and spooler and converts that into regular Moshi laser output.
"""

import time

from ..core.cutcode.cubiccut import CubicCut
from ..core.cutcode.dwellcut import DwellCut
from ..core.cutcode.gotocut import GotoCut
from ..core.cutcode.homecut import HomeCut
from ..core.cutcode.inputcut import InputCut
from ..core.cutcode.linecut import LineCut
from ..core.cutcode.outputcut import OutputCut
from ..core.cutcode.plotcut import PlotCut
from ..core.cutcode.quadcut import QuadCut
from ..core.cutcode.waitcut import WaitCut
from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner
from ..device.basedevice import (
    DRIVER_STATE_FINISH,
    DRIVER_STATE_MODECHANGE,
    DRIVER_STATE_PROGRAM,
    DRIVER_STATE_RAPID,
    DRIVER_STATE_RASTER,
    PLOT_FINISH,
    PLOT_JOG,
    PLOT_LEFT_UPPER,
    PLOT_RAPID,
    PLOT_SETTING,
    PLOT_START,
)
from ..tools.geomstr import Geomstr
from .builder import MoshiBuilder


class MoshiDriver(Parameters):
    """
    A driver takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. The Moshiboard Driver overloads the Driver class to take spoolable values from
    the spooler and converts them into Moshiboard specific actions.

    """

    def __init__(self, service, channel=None, *args, **kwargs):
        super().__init__()
        self.service = service
        self.name = str(self.service)
        self.state = 0

        self.native_x = 0
        self.native_y = 0

        self.plot_planner = PlotPlanner(self.settings)
        self.queue = []
        self._queue_current = 0
        self._queue_total = 0

        self.program = MoshiBuilder()

        self.paused = False
        self.holds = []
        self.temp_holds = []

        self.preferred_offset_x = 0
        self.preferred_offset_y = 0

        self.pipe_channel = service.channel(f"{service.safe_label}/events")
        self.program.channel = self.pipe_channel

        self.out_pipe = None
        self.out_real = None

        self._signal_updates = self.service.setting(bool, "signal_updates", True)

        def primary_hold():
            if self.out_pipe is None:
                return True
            if (
                hasattr(self.service.controller, "is_shutdown")
                and self.service.controller.is_shutdown
            ):
                raise ConnectionAbortedError("Cannot hold for a shutdown pipe.")
            return self.paused

        self.holds.append(primary_hold)

    def __repr__(self):
        return f"MoshiDriver({self.name})"

    def __call__(self, e, real=False):
        if real:
            self.out_real(e)
        else:
            self.out_pipe(e)

    def get_internal_queue_status(self):
        return self._queue_current, self._queue_total

    def _set_queue_status(self, current, total):
        self._queue_current = current
        self._queue_total = total

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

    def job_start(self, job):
        pass

    def job_finish(self, job):
        self.rapid_mode()

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
        elif key == "speed":
            self._set_speed(value)
        elif key == "step":
            self._set_step(value)
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

    def laser_off(self, *values):
        """
        Turn laser off in place.

        Moshiboards do not support this command.

        @param values:
        @return:
        """
        pass

    def laser_on(self, *values):
        """
        Turn laser on in place.

        Moshiboards do not support this command.

        @param values:
        @return:
        """
        pass

    def geometry(self, geom):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        # TODO: Raster geom strokes need to be run in raster mode for moshi.
        g = Geomstr()
        for segment_type, start, c1, c2, end, sets in geom.as_lines():
            x = self.native_x
            y = self.native_y
            if x != start.real or y != start.imag:
                self._goto_absolute(start.real, start.imag, 0)
            self.settings.update(sets)

            if segment_type == "line":
                self._goto_absolute(end.real, end.imag, 1)
            elif segment_type == "end":
                pass
            elif segment_type == "quad":
                interp = self.service.interp
                g.clear()
                g.quad(start, c1, end)
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    self._goto_absolute(p.real, p.imag, 1)
            elif segment_type == "cubic":
                interp = self.service.interp
                g.clear()
                g.cubic(start, c1, c2, end)
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    self._goto_absolute(p.real, p.imag, 1)
            elif segment_type == "arc":
                interp = self.service.interp
                g.clear()
                g.arc(start, c1, end)
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    self._goto_absolute(p.real, p.imag, 1)
            elif segment_type == "point":
                function = sets.get("function")
                if function == "dwell":
                    # Moshi cannot fire in place.
                    pass
                elif function == "wait":
                    # Moshi has no forced wait functionality.
                    pass
                elif function == "home":
                    self.home()
                elif function == "goto":
                    self._goto_absolute(start.real, start.imag, 0)
                elif function == "input":
                    # Moshi has no core GPIO functionality
                    pass
                elif function == "output":
                    # Moshi has no core GPIO functionality
                    pass

    def plot(self, plot):
        """
        Gives the driver a bit of cutcode that should be plotted.
        @param plot:
        @return:
        """
        self.queue.append(plot)

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        total = len(self.queue)
        current = 0
        for q in self.queue:
            current += 1
            self._set_queue_status(current, total)
            p_set = Parameters(q.settings)
            if p_set.power != self.power:
                self._set_power(p_set.power)
            if (
                p_set.speed != self.speed
                or p_set.raster_step_x != self.raster_step_x
                or p_set.raster_step_y != self.raster_step_y
            ):
                self._set_speed(p_set.speed)
                self._set_step(p_set.raster_step_x, p_set.raster_step_y)
                self.rapid_mode()
            self.settings.update(q.settings)

            x = self.native_x
            y = self.native_y
            start_x, start_y = q.start
            if x != start_x or y != start_y:
                self._goto_absolute(start_x, start_y, 0)
            if isinstance(q, LineCut):
                x0, y0, x1, y1 = int(q.start[0]), int(q.start[1]), int(q.end[0]), int(q.end[1])
                dx, dy = abs(x1 - x0), abs(y1 - y0)
                # horizontal, vertical or 45 deg angled line
                if dx == 0 or dy == 0 or dx == dy:
                    self._goto_absolute(*q.end, 1)
                else:
                    # other oblique line
                    if dx > dy:
                        d = dy
                        sx = float((x1 - x0) / dy)
                        if y1 - y0 > 0:
                            sy = 1
                        else:
                            sy = -1
                    else:
                        d = dx
                        if x1 - x0 > 0:
                            sx = 1
                        else:
                            sx = -1
                        sy = float((y1 - y0) / dx)
                    x = x0
                    y = y0
                    self._goto_absolute(*q.start, 0)
                    for i in range(d):
                        while self.hold_work(0):
                            time.sleep(0.05)
                        x += sx
                        y += sy
                        self._goto_absolute(int(x), int(y), 1)
            elif isinstance(q, QuadCut):
                interp = self.service.interp
                g = Geomstr()
                g.quad(complex(*q.start), complex(*q.c()), complex(*q.end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    self._goto_absolute(p.real, p.imag, 1)
            elif isinstance(q, CubicCut):
                interp = self.service.interp
                g = Geomstr()
                g.cubic(
                    complex(*q.start),
                    complex(*q.c1()),
                    complex(*q.c2()),
                    complex(*q.end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    self._goto_absolute(p.real, p.imag, 1)
            elif isinstance(q, HomeCut):
                self.home()
            elif isinstance(q, GotoCut):
                start = q.start
                self._goto_absolute(start[0], start[1], 0)
            elif isinstance(q, WaitCut):
                # Moshi has no forced wait functionality.
                # self.wait_finish()
                # self.wait(q.dwell_time)
                pass
            elif isinstance(q, DwellCut):
                # Moshi cannot fire in place.
                pass
            elif isinstance(q, (InputCut, OutputCut)):
                # Moshi has no core GPIO functionality
                pass
            else:
                # Rastercut, PlotCut
                if isinstance(q, PlotCut):
                    q.check_if_rasterable()
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    if self.hold_work(0):
                        time.sleep(0.05)
                        continue
                    on = int(on)
                    if on > 1:
                        # Special Command.
                        if on & (
                            PLOT_RAPID | PLOT_JOG
                        ):  # Plot planner requests position change.
                            # self.rapid_jog(x, y)
                            self.native_x = x
                            self.native_y = y
                            if self.state != DRIVER_STATE_RAPID:
                                self._move_absolute(x, y)
                            continue
                        elif on & PLOT_FINISH:  # Plot planner is ending.
                            self.finished_mode()
                            break
                        elif on & PLOT_START:
                            self._ensure_program_or_raster_mode(
                                self.preferred_offset_x,
                                self.preferred_offset_y,
                                self.native_x,
                                self.native_y,
                            )
                        elif on & PLOT_LEFT_UPPER:
                            self.preferred_offset_x = x
                            self.preferred_offset_y = y
                        elif on & PLOT_SETTING:
                            # Plot planner settings have changed.
                            p_set = Parameters(self.plot_planner.settings)
                            if p_set.power != self.power:
                                self._set_power(p_set.power)
                            if (
                                p_set.speed != self.speed
                                or p_set.raster_step_x != self.raster_step_x
                                or p_set.raster_step_y != self.raster_step_y
                            ):
                                self._set_speed(p_set.speed)
                                self._set_step(p_set.raster_step_x, p_set.raster_step_y)
                                self.rapid_mode()
                            self.settings.update(p_set.settings)
                        continue
                    self._goto_absolute(x, y, on & 1)
        self.queue.clear()
        self._set_queue_status(0, 0)

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        x, y = self.service.view.position(x, y)
        self.rapid_mode()
        self._move_absolute(int(x), int(y))

    def move_rel(self, dx, dy):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        unit_dx, unit_dy = self.service.view.position(dx, dy, vector=True)
        self.rapid_mode()
        x = self.native_x + unit_dx
        y = self.native_y + unit_dy
        self._move_absolute(int(x), int(y))
        self.rapid_mode()

    def home(self):
        """
        Send a home command to the device. In the case of Moshiboards this is merely a move to
        0,0 in absolute position.
        """
        if self.service.rotary.active and self.service.rotary.suppress_home:
            return
        self.rapid_mode()
        self.set("speed", 40)
        self.program_mode(0, 0, 0, 0)
        self.rapid_mode()
        self.native_x = 0
        self.native_y = 0

    def physical_home(self):
        """ "
        This would be the command to go to a real physical home position (i.e. hitting endstops)
        """
        self.home()

    def unlock_rail(self):
        """
        Unlock the Rail or send a "FreeMotor" command.
        """
        self.rapid_mode()
        self.pipe_channel("Realtime: FreeMotor")
        MoshiBuilder.freemotor(self.out_real, self.pipe_channel)

    def rapid_mode(self, *values):
        """
        Ensure the driver is currently in a default state. If we are not in a default state the driver
        should end the current program.
        """
        if self.state == DRIVER_STATE_RAPID:
            return
        self.commit()
        if self.pipe_channel:
            self.pipe_channel("Rapid Mode")
        self.state = DRIVER_STATE_RAPID

    def finished_mode(self, *values):
        """
        Ensure the driver is currently in a finished state. If we are not in a finished state the driver
        should end the current program and return to rapid mode.

        Finished is required between rasters since it's an absolute home.
        """
        if self.state == DRIVER_STATE_FINISH:
            return

        if self.pipe_channel:
            self.pipe_channel("Finished Mode")
        if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_MODECHANGE):
            self.rapid_mode()

        if self.state == self.state == DRIVER_STATE_RASTER:
            self.pipe_channel("Final Raster Home")
            self.home()
        self.state = DRIVER_STATE_FINISH

    def program_mode(self, *values):
        """
        Ensure the laser is currently in a program state. If it is not currently in a program state we begin
        a program state.

        If the driver is currently in a program state the assurance is made.
        """
        if self.state == DRIVER_STATE_PROGRAM:
            return

        if self.pipe_channel:
            self.pipe_channel("Program Mode")
        if self.state == DRIVER_STATE_RASTER:
            self.finished_mode()
            self.rapid_mode()
        try:
            offset_x = int(values[0])
        except (ValueError, IndexError):
            offset_x = 0
        try:
            offset_y = int(values[1])
        except (ValueError, IndexError):
            offset_y = 0
        try:
            move_x = int(values[2])
        except (ValueError, IndexError):
            move_x = 0
        try:
            move_y = int(values[3])
        except (ValueError, IndexError):
            move_y = 0
        self._start_program_mode(offset_x, offset_y, move_x, move_y)

    def raster_mode(self, *values):
        """
        Ensure the driver is currently in a raster program state. If it is not in a raster program state
        we write the raster program state.
        """
        if self.state == DRIVER_STATE_RASTER:
            return

        if self.pipe_channel:
            self.pipe_channel("Raster Mode")
        if self.state == DRIVER_STATE_PROGRAM:
            self.finished_mode()
            self.rapid_mode()
        try:
            offset_x = int(values[0])
        except (ValueError, IndexError):
            offset_x = 0
        try:
            offset_y = int(values[1])
        except (ValueError, IndexError):
            offset_y = 0
        try:
            move_x = int(values[2])
        except (ValueError, IndexError):
            move_x = 0
        try:
            move_y = int(values[3])
        except (ValueError, IndexError):
            move_y = 0
        self._start_raster_mode(offset_x, offset_y, move_x, move_y)

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
        Wait finish should hold the calling thread until the current work has completed. Or otherwise prevent any data
        from being sent with returning True for the until that criteria is met.

        @param values:
        @return:
        """

        def temp_hold():
            try:
                return (
                    self.service.controller.state == "wait"
                    or len(self.service.controller) != 0
                )
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
        Wants a system beep to be issued.
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
        This asks that this signal be broadcast at the appropriate time within the spooling cycle.

        @param signal:
        @param args:
        @return:
        """
        self.service.signal(signal, *args)

    def pause(self, *args):
        """
        Asks that the laser be paused.

        @param args:
        @return:
        """
        self.paused = True
        self.service.signal("pause")

    def resume(self, *args):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser.

        @param args:
        @return:
        """
        self.paused = False
        self.service.signal("pause")

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.

        @param args:
        @return:
        """
        self.service.spooler.clear_queue()
        self.rapid_mode()
        self.queue.clear()
        self.pipe_channel("Realtime: Stop")
        MoshiBuilder.stop(self.out_real)
        self.pipe_channel("Control Request: Stop")
        self.paused = False
        self.service.signal("pause")

    ####################
    # Protected Driver Functions
    ####################

    def _start_program_mode(
        self,
        offset_x,
        offset_y,
        move_x=None,
        move_y=None,
        speed=None,
        normal_speed=None,
    ):
        if move_x is None:
            move_x = offset_x
        if move_y is None:
            move_y = offset_y
        if speed is None and self.speed is not None:
            speed = int(self.speed)
        if speed is None:
            speed = 20
        if normal_speed is None:
            normal_speed = speed
        # Normal speed is rapid. Passing same speed so PPI isn't crazy.
        self.program.vector_speed(speed, normal_speed)
        self.program.set_offset(0, offset_x, offset_y)
        self.state = DRIVER_STATE_PROGRAM

        self.program.move_abs(move_x, move_y)
        self.native_x = move_x
        self.native_y = move_y

    def _start_raster_mode(
        self, offset_x, offset_y, move_x=None, move_y=None, speed=None
    ):
        if move_x is None:
            move_x = offset_x
        if move_y is None:
            move_y = offset_y
        if speed is None and self.speed is not None:
            speed = int(self.speed)
        if speed is None:
            speed = 160
        self.program.raster_speed(speed)
        self.program.set_offset(0, offset_x, offset_y)
        self.state = DRIVER_STATE_RASTER

        self.program.move_abs(move_x, move_y)
        self.native_x = move_x
        self.native_y = move_y

    def _set_power(self, power=1000.0):
        self.power = max(0, min(1000, power))

    def _set_overscan(self, overscan=None):
        self.overscan = overscan

    def _set_speed(self, speed=None):
        """
        Set the speed for the driver.
        """
        if self.speed != speed:
            self.speed = speed
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def _set_step(self, step_x=None, step_y=None):
        """
        Set the raster step for the driver.
        """
        if self.raster_step_x != step_x or self.raster_step_y != step_y:
            self.raster_step_x = step_x
            self.raster_step_y = step_y
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def commit(self):
        self.pipe_channel("Pushed program to output...")
        if len(self.program):
            self.program.termination()
            if self.service.mock:
                self.program.debug(self.pipe_channel)
            self(bytearray(self.program.data))
        self.program.clear()

    def _ensure_program_or_raster_mode(self, x, y, x1=None, y1=None):
        """
        Ensure builder is needed. Makes sure it's in program or raster mode.
        """
        if self.state in (DRIVER_STATE_RASTER, DRIVER_STATE_PROGRAM):
            return

        if x1 is None:
            x1 = x
        if y1 is None:
            y1 = y
        if self.raster_step_x == 0 and self.raster_step_y == 0:
            self.program_mode(x, y, x1, y1)
        else:
            if self.service.enable_raster:
                self.raster_mode(x, y, x1, y1)
            else:
                self.program_mode(x, y, x1, y1)

    def _goto_absolute(self, x, y, cut):
        """
        Goto absolute position. Cut flags whether this should be with or without the laser.
        """
        self._ensure_program_or_raster_mode(x, y)
        old_current = self.service.current

        if self.state == DRIVER_STATE_PROGRAM:
            if cut:
                self.program.cut_abs(x, y)
            else:
                self.program.move_abs(x, y)
        else:
            # DRIVER_STATE_RASTER
            if x == self.native_x and y == self.native_y:
                return
            if cut:
                if x == self.native_x:
                    self.program.cut_vertical_abs(y=y)
                if y == self.native_y:
                    self.program.cut_horizontal_abs(x=x)
            else:
                if x == self.native_x:
                    self.program.move_vertical_abs(y=y)
                if y == self.native_y:
                    self.program.move_horizontal_abs(x=x)
        self.native_x = x
        self.native_y = y

        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def _move_absolute(self, x, y):
        """
        Move to a position x, y. This is an absolute position.
        """
        old_current = self.service.current
        self._ensure_program_or_raster_mode(x, y)
        self.program.move_abs(x, y)
        self.native_x = x
        self.native_y = y

        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def laser_disable(self, *values):
        self.laser_enabled = False

    def laser_enable(self, *values):
        self.laser_enabled = True
