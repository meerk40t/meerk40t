"""
Ruida Driver

The Driver has a set of different commands which are sent and utilizes those which can be performed by this driver.
"""
import time

from meerk40t.core.cutcode.cubiccut import CubicCut
from meerk40t.core.cutcode.dwellcut import DwellCut
from meerk40t.core.cutcode.gotocut import GotoCut
from meerk40t.core.cutcode.homecut import HomeCut
from meerk40t.core.cutcode.inputcut import InputCut
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.cutcode.outputcut import OutputCut
from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.cutcode.quadcut import QuadCut
from meerk40t.core.cutcode.waitcut import WaitCut
from meerk40t.device.basedevice import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from meerk40t.core.parameters import Parameters
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.ruida.controller import RuidaController
from meerk40t.tools.geomstr import Geomstr


class RuidaDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.native_x = 0
        self.native_y = 0
        self.name = str(self.service)

        name = self.service.safe_label
        send = service.channel(f"{name}/send")
        self.controller = RuidaController(self.service, send)
        self.controller.job.set_magic(service.magic)

        self.recv = service.channel(f"{name}/recv", pure=True)
        self.recv.watch(self.controller.recv)

        self.on_value = 0
        self.power_dirty = True
        self.speed_dirty = True
        self.absolute_dirty = True
        self._absolute = True
        self.paused = False
        self.is_relative = False
        self.laser = False

        self._shutdown = False

        self.queue = list()
        self._queue_current = 0
        self._queue_total = 0
        self.plot_planner = PlotPlanner(
            dict(), single=True, ppi=False, shift=False, group=True
        )
        self._aborting = False
        self._signal_updates = self.service.setting(bool, "signal_updates", True)

    def __repr__(self):
        return f"RuidaDriver({self.name})"

    def get_internal_queue_status(self):
        return self._queue_current, self._queue_total

    def _set_queue_status(self, current, total):
        self._queue_current = current
        self._queue_total = total

    #############
    # DRIVER COMMANDS
    #############

    def job_start(self, job):
        pass

    def job_finish(self, job):
        pass

    def hold_work(self, priority):
        """
        This is checked by the spooler to see if we should hold any work from being processed from the work queue.

        For example if we pause, we don't want it trying to call some functions. Only priority jobs will execute if
        we hold the work queue. This is so that "resume" commands can be processed.

        @return:
        """
        return priority <= 0 and self.paused

    def get(self, key, default=None):
        """
        Required.

        @param key: Key to get.
        @param default: Default value to use.
        @return:
        """
        return default

    def set(self, key, value):
        """
        Required.

        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.

        @param key:
        @param value:
        @return:
        """

    def status(self):
        """
        Wants a status report of what the driver is doing.
        @return:
        """
        state_major, state_minor = self.controller.state
        return (self.native_x, self.native_y), state_major, state_minor

    def laser_off(self, *values):
        """
        This command expects to stop pulsing the laser in place.

        @param values:
        @return:
        """
        self.laser = False

    def laser_on(self, *values):
        """
        This command expects to start pulsing the laser in place.

        @param values:
        @return:
        """
        self.laser = True

    def plot(self, plot):
        """
        This command is called with bits of cutcode as they are processed through the spooler. This should be optimized
        bits of cutcode data with settings on them from paths etc.

        @param plot:
        @return:
        """
        self.queue.append(plot)

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        # Write layer header information.
        self.controller.start_record()
        self.controller.job.write_header(self.queue)
        first = True
        last_settings = None
        total = len(self.queue)
        current = 0
        for q in self.queue:
            current += 1
            self._set_queue_status(current, total)
            if hasattr(q, "settings"):
                current_settings = q.settings
                if current_settings is not last_settings:
                    self.controller.job.write_settings(current_settings)
                    last_settings = current_settings

            x = self.native_x
            y = self.native_y
            start_x, start_y = q.start
            if x != start_x or y != start_y or first:
                self.on_value = 0
                self.power_dirty = True

                first = False
                self._move(start_x, start_y, cut=False)
            if self.on_value != 1.0:
                self.power_dirty = True
            self.on_value = 1.0
            # Default-Values?!
            qpower = q.settings.get("power", self.power)
            qspeed = q.settings.get("speed", self.speed)
            qraster_step_x = q.settings.get("raster_step_x")
            qraster_step_y = q.settings.get("raster_step_y")
            if qpower != self.power:
                self.set("power", qpower)
            if (
                qspeed != self.speed
                or qraster_step_x != self.raster_step_x
                or qraster_step_y != self.raster_step_y
            ):
                self.set("speed", qspeed)
            self.settings.update(q.settings)
            if isinstance(q, LineCut):
                self._move(*q.end, cut=True)
            elif isinstance(q, QuadCut):
                interp = self.service.interpolate
                g = Geomstr()
                g.quad(complex(*q.start), complex(*q.c()), complex(*q.end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag, cut=True)
            elif isinstance(q, CubicCut):
                interp = self.service.interpolate
                g = Geomstr()
                g.cubic(
                    complex(*q.start),
                    complex(*q.c1()),
                    complex(*q.c2()),
                    complex(*q.end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag, cut=True)
            elif isinstance(q, WaitCut):
                self.controller.job.add_delay(q.dwell_time)
            elif isinstance(q, HomeCut):
                self.home()
            elif isinstance(q, GotoCut):
                start = q.start
                self._move(start[0], start[1], cut=True)
            elif isinstance(q, DwellCut):
                self.controller.job.laser_interval(q.dwell_time)
            elif isinstance(q, (InputCut, OutputCut)):
                # Ruida has no core GPIO functionality
                pass
            elif isinstance(q, PlotCut):
                self.set("power", 1000)
                for ox, oy, on, x, y in q.plot:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    # q.plot can have different on values, these are parsed
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y, cut=True)
            else:
                #  Rastercut
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    while self.hold_work(0):
                        time.sleep(0.05)
                    if on > 1:
                        # Special Command.
                        if isinstance(on, float):
                            on = int(on)
                        if on & PLOT_FINISH:  # Plot planner is ending.
                            break
                        elif on & PLOT_SETTING:  # Plot planner settings have changed.
                            p_set = Parameters(self.plot_planner.settings)
                            if p_set.power != self.power:
                                self.set("power", p_set.power)
                            if (
                                p_set.speed != self.speed
                                or p_set.raster_step_x != self.raster_step_x
                                or p_set.raster_step_y != self.raster_step_y
                            ):
                                self.set("speed", p_set.speed)
                            self.settings.update(p_set.settings)
                        elif on & (
                            PLOT_RAPID | PLOT_JOG
                        ):  # Plot planner requests position change.
                            self._move(x, y, cut=False)
                        continue
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y, cut=True)
        self.queue.clear()
        self._set_queue_status(0, 0)
        # Ruida end data.
        self.controller.job.write_tail()
        self.controller.stop_record()
        return False

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        old_current = self.service.current
        job = self.controller.job
        out = self.controller.write
        job.speed_laser_1(100.0, output=out)
        job.min_power_1(0, output=out)
        job.min_power_2(0, output=out)

        x, y = self.service.view.position(x, y)

        dx = x - self.native_x
        dy = y - self.native_y
        if dx == 0:
            if dy != 0:
                job.rapid_move_y(dy, output=out)
        elif dy == 0:
            job.rapid_move_x(dx, output=out)
        else:
            job.rapid_move_xy(x, y, origin=True, output=out)  # Not relative
        self.native_x = x
        self.native_y = y
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def move_rel(self, dx, dy):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        old_current = self.service.current
        job = self.controller.job
        out = self.controller.write
        dx, dy = self.service.view.position(dx, dy, vector=True)
        if dx == 0:
            if dy != 0:
                job.rapid_move_y(dy, output=out)
        elif dy == 0:
            job.rapid_move_x(dx, output=out)
        else:
            job.rapid_move_xy(
                self.native_x + dx,
                self.native_y + dy,
                origin=True,
                output=out,
            )
        self.native_x += dx
        self.native_y += dy
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def focusz(self):
        """
        This is a FocusZ routine on the Ruida Device.
        @return:
        """
        job = self.controller.job
        out = self.controller.write
        job.focus_z(output=out)

    def home(self):
        """
        This is called home, returns to center.

        @return:
        """
        self.move_abs(0, 0)

    def physical_home(self):
        """ "
        This would be the command to go to a real physical home position (i.e. hitting endstops)
        """
        job = self.controller.job
        out = self.controller.write
        job.home_xy(output=out)

    def rapid_mode(self):
        """
        Expects to be in rapid jogging mode.
        @return:
        """
        self.controller.rapid_mode()

    def program_mode(self):
        """
        Expects to run jobs at a speed in a programmed mode.
        @return:
        """
        self.controller.program_mode()

    def raster_mode(self, *args):
        """
        Expects to run a raster job. Raster information is set in special modes to stop the laser head from moving
        too far.

        @return:
        """
        pass

    def wait_finished(self):
        """
        Expects to be caught up such that the next command will happen immediately rather than get queued.

        @return:
        """
        self.controller.wait_finished()

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooling cycle.

        @param function:
        @return:
        """
        function()

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

    def console(self, value):
        """
        This asks that the console command be executed at the appropriate time within the spooled cycle.

        @param value: console command
        @return:
        """
        self.service(value)

    def beep(self):
        """
        Wants a system beep to be issued.
        This command asks that a beep be executed at the appropriate time within the spooled cycle.

        @return:
        """
        self.service("beep\n")

    def signal(self, signal, *args):
        """
        Wants a system signal to be sent.

        @param signal:
        @param args:
        @return:
        """
        self.service.signal(signal, *args)

    def pause(self):
        """
        Wants the driver to pause.
        @return:
        """
        if self.paused:
            self.resume()
            return
        self.paused = True
        self.controller.pause()
        self.service.signal("pause")

    def resume(self):
        """
        Wants the driver to resume.

        This typically issues from the realtime queue which means it will call even if we tell work_hold that we should
        hold the work.

        @return:
        """
        self.paused = False
        self.controller.resume()
        self.service.signal("pause")

    def reset(self):
        """
        Wants the job to be aborted and action to be stopped.

        @return:
        """
        self.controller.abort()
        self.paused = False
        self.service.signal("pause")

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        job = self.controller.job
        out = self.controller.write
        job.laser_interval(time_in_ms, output=out)

    def set_abort(self):
        self._aborting = True

    ####################
    # PROTECTED DRIVER CODE
    ####################

    def _move(self, x, y, cut=True):
        old_current = self.service.current
        job = self.controller.job
        if self.power_dirty:
            if self.power is not None:
                job.max_power_1(self.power / 10.0 * self.on_value)
                job.min_power_1(self.power / 10.0 * self.on_value)
            self.power_dirty = False
        if self.speed_dirty:
            job.speed_laser_1(self.speed)
            self.speed_dirty = False
        dx = x - self.native_x
        dy = y - self.native_y
        if cut:
            job.mark(x, y, dx, dy)
        else:
            job.jump(x, y, dx, dy)
        self.native_x = x
        self.native_y = y
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )
