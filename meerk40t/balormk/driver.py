import time

from meerk40t.balor.command_list import CommandList
from meerk40t.balormk.controller import BalorController
from meerk40t.core.cutcode import LineCut, QuadCut, CubicCut, PlotCut, DwellCut, WaitCut
from meerk40t.core.drivers import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.fill.fills import Wobble


class BalorDriver:
    def __init__(self, service):
        self.service = service
        self.native_x = 0x8000
        self.native_y = 0x8000
        self.name = str(self.service)
        self.connection = BalorController(service)
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
        self.wobble = None
        self.value_penbox = None
        self.plot_planner.settings_then_jog = True

    def __repr__(self):
        return "BalorDriver(%s)" % self.name

    def service_attach(self):
        self._shutdown = False

    def service_detach(self):
        self._shutdown = True

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

    def balor_job(self, job):
        self.connection.job(job)
        if self.service.redlight_preferred:
            self.connection.light_on()
        else:
            self.connection.light_off()

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

    def light(self, job):
        """
        This is not a typical meerk40t command. But, the light commands in the main balor add this as the idle job.

        self.spooler.set_idle(("light", self.driver.cutcode_to_light_job(cutcode)))
        That will the spooler's idle job be calling "light" on the driver with the light job. Which is a BalorJob.Job class
        We serialize that and hand it to the send_data routine of the connection.

        @param job:
        @return:
        """
        self.connection.light_off()
        self.connection.job(job)
        if self.service.redlight_preferred:
            self.connection.light_on()
        else:
            self.connection.light_off()

    def _set_settings(self, job, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param job: The job to set these settings on
        @param settings: The current settings dictionary
        @return:
        """
        if self.service.pulse_width_enabled:
            # Global Pulse Width is enabled.
            if str(settings.get("pulse_width_enabled", False)).lower() == "true":
                # Local Pulse Width value is enabled.
                # OpFiberYLPMPulseWidth

                job.set_fiber_pulse_width(int(settings.get(
                    "pulse_width", self.service.default_pulse_width
                )))
            else:
                # Only global is enabled, use global pulse width value.
                job.set_fiber_pulse_width(self.service.default_pulse_width)

        if (
                str(settings.get("rapid_enabled", False)).lower() == "true"
        ):
            job.set_travel_speed(float(settings.get(
                "rapid_speed", self.service.default_rapid_speed
            )))
        else:
            job.set_travel_speed(self.service.default_rapid_speed)
        job.set_power((
                float(settings.get("power", self.service.default_power)) / 10.0
        ))  # Convert power, out of 1000
        job.set_frequency(float(settings.get(
            "frequency", self.service.default_frequency
        )))
        job.set_cut_speed(float(settings.get("speed", self.service.default_speed)))

        if (
                str(settings.get("timing_enabled", False)).lower() == "true"
        ):
            job.set_laser_on_delay(settings.get(
                "delay_laser_on", self.service.delay_laser_on
            ))
            job.set_laser_off_delay(settings.get(
                "delay_laser_off", self.service.delay_laser_off
            ))
            job.set_polygon_delay(settings.get(
                "delay_laser_polygon", self.service.delay_polygon
            ))
        else:
            # Use globals
            job.set_laser_on_delay(self.service.delay_laser_on)
            job.set_laser_off_delay(self.service.delay_laser_off)
            job.set_polygon_delay(self.service.delay_polygon)

    def _set_wobble(self, job, settings):
        """
        Set the wobble parameters and mark modifications routines.

        @param job: The job to set these wobble parameters on.
        @param settings: The dict setting to extract parameters from.
        @return:
        """
        wobble_enabled = (
                str(settings.get("wobble_enabled", False)).lower() == "true"
        )
        if not wobble_enabled:
            job._mark_modification = None
            return
        wobble_radius = settings.get("wobble_radius", "1.5mm")
        wobble_r = self.service.physical_to_device_length(
            wobble_radius, 0
        )[0]
        wobble_interval = settings.get("wobble_interval", "0.3mm")
        wobble_speed = settings.get("wobble_speed", 50.0)
        wobble_type = settings.get("wobble_type", "circle")
        wobble_interval = self.service.physical_to_device_length(
            wobble_interval, 0
        )[0]
        algorithm = self.service.lookup(f"wobble/{wobble_type}")
        if self.wobble is None:
            self.wobble = Wobble(
                algorithm=algorithm,
                radius=wobble_r,
                speed=wobble_speed,
                interval=wobble_interval,
            )
        else:
            # set our parameterizations
            self.wobble.algorithm = algorithm
            self.wobble.radius = wobble_r
            self.wobble.speed = wobble_speed
        job._mark_modification = self.wobble

    def plot_start(self):
        """
        This is called after all the cutcode objects are sent. This says it shouldn't expect more cutcode for a bit.

        @return:
        """
        job = CommandList()
        job.ready()
        job.raw_mark_end_delay(0x0320)
        job.set_write_port(self.connection.get_port())
        job.set_travel_speed(self.service.default_rapid_speed)
        job.goto(0x8000, 0x8000)
        last_on = None
        self.wobble = None
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
            self._set_settings(job, settings)
            self._set_wobble(job, settings)

            if isinstance(q, LineCut):
                last_x, last_y = job.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    job.goto(x, y)
                job.mark(*q.end)
            elif isinstance(q, (QuadCut, CubicCut)):
                last_x, last_y = job.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    job.goto(x, y)
                interp = self.service.interpolate
                step_size = 1.0 / float(interp)
                t = step_size
                for p in range(int(interp)):
                    while self.hold_work():
                        time.sleep(0.05)
                    p = q.point(t)
                    job.mark(*p)
                    t += step_size
            elif isinstance(q, PlotCut):
                last_x, last_y = job.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    job.goto(x, y)
                for x, y, on in q.plot[1:]:
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
                            self._set_settings(job, settings)
                        else:
                            # We are using traditional power-scaling
                            settings = self.plot_planner.settings
                            current_power = (
                                    float(settings.get("power", self.service.default_power)) / 10.0
                            )
                            job.set_power(current_power * on)
                    job.mark(x, y)
            elif isinstance(q, DwellCut):
                start = q.start
                job.goto(start[0], start[1])
                dwell_time = q.dwell_time
                while dwell_time > 0:
                    d = min(dwell_time, 60000)
                    job.raw_laser_on_point(int(d))
                    dwell_time -= d
                job.raw_mark_end_delay(self.service.delay_end)
            elif isinstance(q, WaitCut):
                job.raw_mark_end_delay(q.dwell_time)
            else:
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
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
                                    self.value_penbox = self.service.elements.penbox[penbox]
                                except KeyError:
                                    self.value_penbox = None
                            self._set_settings(job, settings)
                            self._set_wobble(job, settings)
                        elif on & (
                                PLOT_RAPID | PLOT_JOG
                        ):  # Plot planner requests position change.
                            job.set_travel_speed(self.service.default_rapid_speed)
                            job.goto(x, y)
                        continue
                    if on == 0:
                        job.set_travel_speed(self.service.default_rapid_speed)
                        job.goto(x, y)
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
                                self._set_settings(job, settings)
                            else:
                                # We are using traditional power-scaling
                                settings = self.plot_planner.settings
                                current_power = (
                                        float(settings.get("power", self.service.default_power)) / 10.0
                                )
                                job.set_power(current_power * on)
                        job.mark(x, y)
        job.flush()
        job.raw_mark_end_delay(self.service.delay_end)

        self.connection.job(job)
        if self.service.redlight_preferred:
            self.connection.light_on()
        else:
            self.connection.light_off()

    def move_abs(self, x, y):
        """
        This is called with the actual x and y values with units. If without units we should expect to move in native
        units.

        @param x:
        @param y:
        @return:
        """
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

    def move_rel(self, dx, dy):
        """
        This is called with dx and dy values to move a relative amount.

        @param dx:
        @param dy:
        @return:
        """
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

    def home(self, x=None, y=None):
        """
        This is called with x, and y, to set an adjusted home or use whatever home we have.
        @param x:
        @param y:
        @return:
        """
        self.move_abs("50%", "50%")

    def blob(self, data_type, data):
        """
        This is called to give pure data to the backend. Data is assumed to be native data-type as loaded from a file.

        @param data_type:
        @param data:
        @return:
        """
        if data_type == "balor":
            self.connection.job(data)

    def set(self, attribute, value):
        """
        This is called to set particular attributes. These attributes will be set in the cutcode as well but sometimes
        there is a need to set these outside that context. This can also set the default values to be used inside
        the cutcode being processed.

        @param attribute:
        @param value:
        @return:
        """
        if attribute == "speed":
            pass
        print(attribute, value)

    def rapid_mode(self):
        """
        Expects to be in rapid jogging mode.
        @return:
        """
        pass

    def program_mode(self):
        """
        Expects to run jobs at a speed in a programmed mode.
        @return:
        """
        pass

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

    def wait(self, secs):
        time.sleep(secs)

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
        self.connection.realtime_pause()

    def resume(self):
        """
        Wants the driver to resume.

        This typically issues from the realtime queue which means it will call even if we tell work_hold that we should
        hold the work.

        @return:
        """
        self.paused = False
        self.connection.realtime_resume()

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
