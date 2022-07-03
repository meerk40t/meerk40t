import time

from meerk40t.core.cutcode import (
    CubicCut,
    DwellCut,
    InputCut,
    LineCut,
    OutputCut,
    PlotCut,
    QuadCut,
    WaitCut,
)
from meerk40t.core.drivers import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.balormk.lmc_controller import GalvoController


class BalorDriver:
    def __init__(self, service):
        self.service = service
        self.native_x = 0x8000
        self.native_y = 0x8000
        self.name = str(self.service)

        self.connection = GalvoController(service)

        self.service.add_service_delegate(self.connection)
        self.paused = False

        self.connected = False

        self.is_relative = False
        self.laser = False

        self._shutdown = False

        self.queue = list()
        self.plot_planner = PlotPlanner(
            dict(), single=True, smooth=False, ppi=False, shift=False, group=True
        )
        self.value_penbox = None
        self.plot_planner.settings_then_jog = True
        self._aborting = False
        self._list_bits = None

    def __repr__(self):
        return "BalorDriver(%s)" % self.name

    def service_attach(self):
        self._shutdown = False

    def service_detach(self):
        self._shutdown = True

    def connect(self):
        self.connection.connect_if_needed()

    def disconnect(self):
        self.connection.disconnect()

    def hold_work(self):
        """
        This is checked by the spooler to see if we should hold any work from being processed from the work queue.

        For example if we pause, we don't want it trying to call some functions. Only priority jobs will execute if
        we hold the work queue. This is so that "resume" commands can be processed.

        @return:
        """
        return self.paused

    def hold_idle(self):
        """
        This is checked by the spooler to see if we should abort checking if there's any idle job after the work queue
        was found to be empty.
        @return:
        """
        return False

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

    def light_loop(self, job):
        self.connection.rapid_mode()
        self.connection.light_mode()
        while job(self.connection):
            if self._shutdown:
                break
        self.connection.abort()

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
        con = self.connection
        con.program_mode()
        self._list_bits = con._port_bits
        last_on = None
        con.set_wobble(None)
        queue = self.queue
        self.queue = list()
        for q in queue:
            settings = q.settings
            penbox = settings.get("penbox_value")
            if penbox is not None:
                try:
                    self.value_penbox = self.service.elements.penbox[penbox]
                except KeyError:
                    self.value_penbox = None
            con.set_settings(settings)
            con.set_wobble(settings)
            # LOOP CHECKS
            if self._aborting:
                con.abort()
                self._aborting = False
                return
            if con._port_bits != self._list_bits:
                con.list_write_port()
                self._list_bits = con._port_bits
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
                    if con._port_bits != self._list_bits:
                        con.list_write_port()
                        self._list_bits = con._port_bits
                    while self.hold_work():
                        time.sleep(0.05)

                    p = q.point(t)
                    con.mark(*p)
                    t += step_size
            elif isinstance(q, PlotCut):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                for x, y, on in q.plot[1:]:
                    # LOOP CHECKS
                    if self._aborting:
                        con.abort()
                        self._aborting = False
                        return
                    if con._port_bits != self._list_bits:
                        con.list_write_port()
                        self._list_bits = con._port_bits
                    while self.hold_work():
                        time.sleep(0.05)

                    # q.plot can have different on values, these are parsed
                    if last_on is None or on != last_on:
                        last_on = on
                        if self.value_penbox:
                            # There is an active value_penbox
                            settings = dict(q.settings)
                            limit = len(self.value_penbox) - 1
                            m = int(round(on * limit))
                            try:
                                pen = self.value_penbox[m]
                                settings.update(pen)
                            except IndexError:
                                pass
                            # Power scaling is exclusive to this penbox. on is used as a lookup and does not scale power.
                            con.set_settings(settings)
                        else:
                            # We are using traditional power-scaling
                            settings = self.plot_planner.settings
                            current_power = (
                                float(settings.get("power", self.service.default_power))
                                / 10.0
                            )
                            con.power(current_power * on)
                    con.mark(x, y)
            elif isinstance(q, DwellCut):
                start = q.start
                con.goto(start[0], start[1])
                dwell_time = q.dwell_time * 100  # Dwell time in ms units in 10 us
                while dwell_time > 0:
                    d = min(dwell_time, 60000)
                    con.list_laser_on_point(int(d))
                    dwell_time -= d
                con.list_delay_time(self.service.delay_end)
            elif isinstance(q, WaitCut):
                dwell_time = q.dwell_time * 100  # Dwell time in ms units in 10 us
                while dwell_time > 0:
                    d = min(dwell_time, 60000)
                    con.list_delay_time(int(d))
                    dwell_time -= d
            elif isinstance(q, OutputCut):
                con.port_set(q.output_mask, q.output_value)
                con.list_write_port()
            elif isinstance(q, InputCut):
                input_value = q.input_value
                con.list_wait_for_input(input_value)
            else:
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    # LOOP CHECKS
                    if self._aborting:
                        con.abort()
                        self._aborting = False
                        return
                    if con._port_bits != self._list_bits:
                        self._list_bits = con._port_bits
                        con.list_write_port()
                    while self.hold_work():
                        time.sleep(0.05)

                    if on > 1:
                        # Special Command.
                        if on & PLOT_FINISH:  # Plot planner is ending.
                            break
                        elif on & PLOT_SETTING:  # Plot planner settings have changed.
                            settings = self.plot_planner.settings
                            penbox = settings.get("penbox_value")
                            if penbox is not None:
                                try:
                                    self.value_penbox = self.service.elements.penbox[
                                        penbox
                                    ]
                                except KeyError:
                                    self.value_penbox = None
                            con.set_settings(settings)
                            con.set_wobble(settings)
                        elif on & (
                            PLOT_RAPID | PLOT_JOG
                        ):  # Plot planner requests position change.
                            con.list_jump_speed(self.service.default_rapid_speed)
                            con.goto(x, y)
                        continue
                    if on == 0:
                        con.list_jump_speed(self.service.default_rapid_speed)
                        con.goto(x, y)
                    else:
                        # on is in range 0 exclusive and 1 inclusive.
                        # This is a regular cut position
                        if last_on is None or on != last_on:
                            last_on = on
                            if self.value_penbox:
                                # There is an active value_penbox
                                settings = dict(self.plot_planner.settings)
                                limit = len(self.value_penbox) - 1
                                m = int(round(on * limit))
                                try:
                                    pen = self.value_penbox[m]
                                    settings.update(pen)
                                except IndexError:
                                    pass
                                # Power scaling is exclusive to this penbox. on is used as a lookup and does not scale power.
                                con.set_settings(settings)
                            else:
                                # We are using traditional power-scaling
                                settings = self.plot_planner.settings
                                current_power = (
                                    float(
                                        settings.get(
                                            "power", self.service.default_power
                                        )
                                    )
                                    / 10.0
                                )
                                con.power(current_power * on)
                        con.mark(x, y)
        con.list_delay_time(self.service.delay_end)
        self._list_bits = None
        con.rapid_mode()

        if self.service.redlight_preferred:
            con.light_on()
            con.write_port()
        else:
            con.light_off()
            con.write_port()

    def move_abs(self, x, y):
        """
        This is called with the actual x and y values with units. If without units we should expect to move in native
        units.

        @param x:
        @param y:
        @return:
        """
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
        This is called with dx and dy values to move a relative amount.

        @param dx:
        @param dy:
        @return:
        """
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

    def home(self, x=None, y=None):
        """
        This is called with x, and y, to set an adjusted home or use whatever home we have.
        @param x:
        @param y:
        @return:
        """
        self.move_abs("50%", "50%")

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
        function()

    def wait(self, time_in_ms):
        time.sleep(time_in_ms * 1000.0)

    def console(self, value):
        self.service(value)

    def beep(self):
        """
        Wants a system beep to be issued.

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

    def status(self):
        """
        Wants a status report of what the driver is doing.
        @return:
        """
        pass

    def pulse(self, pulse_time):
        con = self.connection
        con.program_mode()
        con.frequency(self.service.default_frequency)
        con.power(self.service.default_power)
        if self.service.pulse_width_enabled:
            con.list_fiber_ylpm_pulse_width(self.service.default_pulse_width)
        dwell_time = pulse_time * 100  # Dwell time in ms units in 10 us
        while dwell_time > 0:
            d = min(dwell_time, 60000)
            con.list_laser_on_point(int(d))
            dwell_time -= d
        con.list_delay_time(self.service.delay_end)
        con.rapid_mode()
        if self.service.redlight_preferred:
            con.light_on()
            con.write_port()
        else:
            con.light_off()
            con.write_port()

    def set_abort(self):
        self._aborting = True
