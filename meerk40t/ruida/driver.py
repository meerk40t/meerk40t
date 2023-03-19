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
from meerk40t.core.cutcode.setorigincut import SetOriginCut
from meerk40t.core.cutcode.waitcut import WaitCut
from meerk40t.core.drivers import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.ruida.controller import RuidaController


class RuidaDriver:
    def __init__(self, service, force_mock=False):
        self.service = service
        self.native_x = 0x8000
        self.native_y = 0x8000
        self.name = str(self.service)

        self.connection = RuidaController(service, force_mock=force_mock)

        self.service.add_service_delegate(self.connection)
        self.paused = False

        self.is_relative = False
        self.laser = False

        self._shutdown = False

        self.queue = list()
        self.plot_planner = PlotPlanner(
            dict(), single=True, ppi=False, shift=False, group=True
        )
        self._aborting = False

    def __repr__(self):
        return f"RuidaDriver({self.name})"

    @property
    def connected(self):
        if self.connection is None:
            return False
        return self.connection.connected

    def service_attach(self):
        self._shutdown = False

    def service_detach(self):
        self._shutdown = True

    def connect(self):
        self.connection.connect_if_needed()

    def disconnect(self):
        self.connection.disconnect()

    def abort_retry(self):
        self.connection.abort_connect()

    #############
    # DRIVER COMMANDS
    #############

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
        x, y = self.connection.get_last_xy()
        state_major, state_minor = self.connection.state
        return (x, y), state_major, state_minor

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
        This is called after all the cutcode objects are sent. This says it shouldn't expect more cutcode for a bit.

        @return:
        """
        # preprocess queue to establish steps
        con = self.connection
        con.program_mode()
        last_on = None
        queue = self.queue
        self.queue = list()
        for q in queue:
            settings = q.settings
            con.set_settings(settings)
            # LOOP CHECKS
            if self._aborting:
                con.abort()
                self._aborting = False
                return
            if isinstance(q, LineCut):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                con.mark(*q.end)
            elif isinstance(q, (QuadCut, CubicCut)):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                interp = self.service.interpolate
                step_size = 1.0 / float(interp)
                t = step_size
                for p in range(int(interp)):
                    # LOOP CHECKS
                    if self._aborting:
                        con.abort()
                        self._aborting = False
                        return
                    while self.paused:
                        time.sleep(0.05)

                    p = q.point(t)
                    con.mark(*p)
                    t += step_size
            elif isinstance(q, PlotCut):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                for ox, oy, on, x, y in q.plot:
                    # LOOP CHECKS
                    if self._aborting:
                        con.abort()
                        self._aborting = False
                        return
                    while self.paused:
                        time.sleep(0.05)

                    # q.plot can have different on values, these are parsed
                    if last_on is None or on != last_on:
                        # No power change.
                        last_on = on

                        # We are using traditional power-scaling
                        max_power = float(
                            q.settings.get("power", self.service.default_power)
                        )
                        percent_power = max_power / 10.0
                        con.max_power_1(percent_power)
                        con.min_power_1(percent_power)
                    con.mark(x, y)
            elif isinstance(q, DwellCut):
                start = q.start
                con.goto(start[0], start[1])
                dwell_time = q.dwell_time
                # TODO: Unknown accuracy
                con.laser_interval(dwell_time)
            elif isinstance(q, WaitCut):
                dwell_time = q.dwell_time
                # TODO: Unknown accuracy
                con.add_delay(dwell_time)
            elif isinstance(q, HomeCut):
                con.home_xy()
            elif isinstance(q, GotoCut):
                con.goto(0,0)
            elif isinstance(q, SetOriginCut):
                # Currently not supporting set origin cut.
                pass
            elif isinstance(q, OutputCut):
                pass
            elif isinstance(q, InputCut):
                pass
            else:
                # Rastercut
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    # LOOP CHECKS
                    if self._aborting:
                        con.abort()
                        self._aborting = False
                        return
                    while self.paused:
                        time.sleep(0.05)

                    if on > 1:
                        # Special Command.
                        if on & PLOT_FINISH:  # Plot planner is ending.
                            break
                        elif on & PLOT_SETTING:  # Plot planner settings have changed.
                            settings = self.plot_planner.settings
                            con.set_settings(settings)
                        elif on & (
                            PLOT_RAPID | PLOT_JOG
                        ):  # Plot planner requests position change.
                            con.goto(x, y)
                        continue
                    if on == 0:
                        con.goto(x, y)
                    else:
                        # on is in range 0 exclusive and 1 inclusive.
                        if last_on is None or on != last_on:
                            last_on = on
                            # We are using traditional power-scaling
                            settings = self.plot_planner.settings
                            percent_power = (
                                float(
                                    settings.get(
                                        "power", self.service.default_power
                                    )
                                )
                            )
                            con.max_power_1(percent_power)
                            con.min_power_1(percent_power)
                        con.mark(x, y)
        con.rapid_mode()

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        if self.service.swap_xy:
            x, y = y, x
        old_current = self.service.current
        self.native_x, self.native_y = self.service.physical_to_device_position(x, y)
        if self.native_x > 0xFFFF:
            self.native_x = 0xFFFF
        if self.native_x < 0:
            self.native_x = 0

        if self.native_y > 0xFFFF:
            self.native_y = 0xFFFF
        if self.native_y < 0:
            self.native_y = 0
        self.connection.set_xy(self.native_x, self.native_y)
        new_current = self.service.current
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
        if self.service.swap_xy:
            dx, dy = dy, dx
        old_current = self.service.current
        unit_dx, unit_dy = self.service.physical_to_device_length(dx, dy)
        self.native_x += unit_dx
        self.native_y += unit_dy

        if self.native_x > 0xFFFF:
            self.native_x = 0xFFFF
        if self.native_x < 0:
            self.native_x = 0

        if self.native_y > 0xFFFF:
            self.native_y = 0xFFFF
        if self.native_y < 0:
            self.native_y = 0
        self.connection.set_xy(self.native_x, self.native_y)
        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def home(self):
        """
        This is called home, returns to center.

        @return:
        """
        self.move_abs(0, 0)

    def physical_home(self):
        """ "
        This would be the command to go to a real physical home position (ie hitting endstops)
        """
        self.home()

    def rapid_mode(self):
        """
        Expects to be in rapid jogging mode.
        @return:
        """
        self.connection.rapid_mode()

    def program_mode(self):
        """
        Expects to run jobs at a speed in a programmed mode.
        @return:
        """
        self.connection.program_mode()

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
        self.connection.wait_finished()

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
        self.connection.pause()

    def resume(self):
        """
        Wants the driver to resume.

        This typically issues from the realtime queue which means it will call even if we tell work_hold that we should
        hold the work.

        @return:
        """
        self.paused = False
        self.connection.resume()

    def reset(self):
        """
        Wants the job to be aborted and action to be stopped.

        @return:
        """
        self.connection.abort()

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """

        self.connection.laser_interval(time_in_ms)

    def set_abort(self):
        self._aborting = True
