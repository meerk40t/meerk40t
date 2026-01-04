"""
Galvo Driver

The Driver has a set of different commands which are standardly sent and utilizes those which can be performed by this
driver.
"""

import threading
import time

from usb.core import NoBackendError

from meerk40t.balormk.controller import GalvoController
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
from meerk40t.core.geomstr import Geomstr
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.device.basedevice import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from meerk40t.kernel import channel


class BalorDriver:
    """Balor (Galvo) device driver.

    Footpedal polling
    -----------------
    - The driver starts a long-lived footpedal polling thread on
      `service_attach()` and stops it on `service_detach()` (service teardown).
    - The polling thread only acts when the controller is connected and
      `service.pedal_mode` != "ignore". That prevents the thread from
      interfering when the device is disconnected.
    - Supported pedal modes (configured via `service.pedal_mode`):
      - "pause_resume_toggle": toggle pause/resume on press
      - "pause_while_pressed": pause while pressed, resume on release
      - "stop": emergency stop on press
    - `service.pedal_active_low` controls semantics of the pedal bit
      (True => bit 0 = pressed, False => bit 1 = pressed).
    - Poll interval is `self._pedal_poll_interval` (default 0.5s).
    - Thread lifecycle and termination:
      - The worker loop checks `self._pedal_thread_running` and
        `self._shutdown` and exits when `_shutdown` is True or the
        running flag is cleared.
      - `stop_pedal_polling(origin=..., force=True)` forces a stop
        and waits briefly for the thread to exit; other internal
        calls to stop are ignored so the thread persists for the
        lifetime of the service.
    - The worker signals changes using `service.signal("pedal_state", foot_state)`
      and will emit channel messages when configured or on emergency stop.

    """

    def __init__(self, service, force_mock=False):
        self.service = service
        self.native_x = 0x8000
        self.native_y = 0x8000
        self.name = str(self.service)

        self.connection = GalvoController(service, force_mock=force_mock)

        self.service.add_service_delegate(self.connection)
        self.paused = False

        self.is_relative = False
        self.laser = False

        self._shutdown = False

        self.queue = list()
        self._queue_current = 0
        self._queue_total = 0
        self.plot_planner = PlotPlanner(
            dict(),
            single=True,
            ppi=False,
            shift=False,
            group=True,
            require_uniform_movement=False,
        )
        self.value_penbox = None
        self.plot_planner.settings_then_jog = True
        self._aborting = False
        self._list_bits = None
        self.service.setting(bool, "signal_updates", True)

        # Footpedal polling thread (uses controller's _usb_lock for synchronization)
        self._pedal_thread = None
        self._pedal_thread_running = False
        self.last_foot_state = None
        self._pedal_poll_interval = 0.5  # 0.5 seconds

    def __repr__(self):
        return f"BalorDriver({self.name})"

    @property
    def connected(self):
        if self.connection is None:
            return False
        return self.connection.connected

    def service_attach(self):
        # Clear shutdown flag and ensure pedal polling thread is running for the lifetime of the service
        # print ("BalorDriver: service_attach called, starting pedal polling thread.")
        self._shutdown = False
        self.start_pedal_polling(origin="service_attach")

    def service_detach(self):
        # Indicate we're shutting down and stop the pedal polling thread for good
        # print ("BalorDriver: service_detach called, shutting down pedal polling thread.")
        self._shutdown = True
        # Force stopping the thread when shutting down the service
        self.stop_pedal_polling(origin="service_detach", force=True)

    def connect(self):
        try:
            self.connection.connect_if_needed()
        except (ConnectionRefusedError, NoBackendError):
            return

    def disconnect(self):
        self.connection.disconnect()

    def abort_retry(self):
        self.connection.abort_connect()

    #############
    # DRIVER COMMANDS
    #############
    def job_start(self, job):
        self._aborting = False

    def hold_work(self, priority):
        """
        This is checked by the spooler to see if we should hold any work from being processed from the work queue.

        For example if we pause, we don't want it trying to call some functions. Only priority jobs will execute if
        we hold the work queue. This is so that "resume" commands can be processed.

        @return:
        """
        return priority <= 0 and self.paused

    def get_internal_queue_status(self):
        return self._queue_current, self._queue_total

    def _set_queue_status(self, current, total):
        self._queue_current = current
        self._queue_total = total

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

        Sets a laser parameter this could be speed, power, number_of_unicorns, or any unknown parameters for
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

    def geometry(self, geom):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        self.service.laser_status = "active"
        con = self.connection
        con._light_speed = None
        con._dark_speed = None
        con._goto_speed = None
        con.program_mode()
        self.start_pedal_polling(origin="geometry start of plot")
        self._list_bits = con._port_bits
        g = Geomstr()
        for segment_type, start, c1, c2, end, sets in geom.as_lines():
            con.set_settings(sets)
            # LOOP CHECKS
            if self._abort_mission():
                return
            while self.paused:
                time.sleep(0.05)
            if segment_type == "line":
                last_x, last_y = con.get_last_xy()
                x, y = start.real, start.imag
                if last_x != x or last_y != y:
                    con.goto(x, y)
                con.mark(end.real, end.imag)
            elif segment_type == "end":
                pass
            elif segment_type == "quad":
                last_x, last_y = con.get_last_xy()
                x, y = start.real, start.imag
                if last_x != x or last_y != y:
                    con.goto(x, y)
                interp = self.service.interp

                g.clear()
                g.quad(start, c1, end)
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)
                    con.mark(p.real, p.imag)
            elif segment_type == "cubic":
                last_x, last_y = con.get_last_xy()
                x, y = start.real, start.imag
                if last_x != x or last_y != y:
                    con.goto(x, y)
                interp = self.service.interp

                g.clear()
                g.cubic(start, c1, c2, end)
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)
                    con.mark(p.real, p.imag)
            elif segment_type == "arc":
                last_x, last_y = con.get_last_xy()
                x, y = start.real, start.imag
                if last_x != x or last_y != y:
                    con.goto(x, y)
                interp = self.service.interp

                g.clear()
                g.arc(start, c1, end)
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)
                    con.mark(p.real, p.imag)
            elif segment_type == "point":
                function = sets.get("function")
                if function == "dwell":
                    con.goto(start.real, start.imag)
                    dwell_time = (
                        sets.get("dwell_time") * 100
                    )  # Dwell time in ms units in 10 us
                    while dwell_time > 0:
                        # LOOP CHECKS
                        if self._abort_mission():
                            return
                        while self.paused:
                            time.sleep(0.05)
                        d = min(dwell_time, 60000)
                        con.list_laser_on_point(int(d))
                        dwell_time -= d
                    con.list_delay_time(int(self.service.delay_end / 10.0))
                elif function == "wait":
                    dwell_time = (
                        sets.get("dwell_time") * 100
                    )  # Dwell time in ms units in 10 us
                    while dwell_time > 0:
                        # LOOP CHECKS
                        if self._abort_mission():
                            return
                        while self.paused:
                            time.sleep(0.05)
                        d = min(dwell_time, 60000)
                        con.list_delay_time(int(d))
                        dwell_time -= d
                elif function == "home":
                    con.goto(0x8000, 0x8000)
                elif function == "goto":
                    con.goto(start.real, start.imag)
                elif function == "input":
                    if self.service.input_operation_hardware:
                        con.list_wait_for_input(sets.get("input_mask"), 0)
                    else:
                        con.rapid_mode()
                        self._wait_for_input_protocol(
                            sets.get("input_mask"), sets.get("input_value")
                        )
                        con.program_mode()
                elif function == "output":
                    con.port_set(sets.get("output_mask"), sets.get("output_value"))
                    con.list_write_port()
        con.list_delay_time(int(self.service.delay_end / 10.0))
        self._list_bits = None
        con.rapid_mode()
        self.service.laser_status = "idle"

        if self.service.redlight_preferred:
            con.light_on()
            con.write_port()
        else:
            con.light_off()
            con.write_port()

    def plot(self, plot):
        """
        This command is called with bits of cutcode as they are processed through the spooler. This should be optimized
        bits of cutcode data with settings on them from paths etc.

        @param plot:
        @return:
        """
        self.queue.append(plot)

    def _wait_for_input_protocol(self, input_mask, input_value):
        required_passes = self.service.input_passes_required
        passes = 0
        while (
            self.connection and not self.connection.is_shutdown and not self._aborting
        ):
            while self.paused:
                time.sleep(0.05)
            read_port = self.connection.read_port()
            b = read_port[1]
            all_matched = True
            for i in range(16):
                if (input_mask >> i) & 1 == 0:
                    continue  # We don't care about this mask.
                if (input_value >> i) & 1 != (b >> i) & 1:
                    all_matched = False
                    time.sleep(0.05)
                    break

            if all_matched:
                passes += 1
                if passes > required_passes:
                    # Success, we matched the wait for protocol.
                    return
            else:
                passes = 0

    def plot_start(self):
        """
        This is called after all the cutcode objects are sent. This says it shouldn't expect more cutcode for a bit.

        @return:
        """

        # preprocess queue to establish steps
        self.service.laser_status = "active"
        con = self.connection
        con._light_speed = None
        con._dark_speed = None
        con._goto_speed = None
        con.program_mode()
        self.start_pedal_polling(origin="start of plot")
        self._list_bits = con._port_bits
        last_on = None
        queue = self.queue
        self.queue = list()
        total = len(queue)
        current = 0
        for q in queue:
            current += 1
            self._set_queue_status(current, total)
            settings = q.settings
            penbox = settings.get("penbox_value")
            if penbox is not None:
                try:
                    self.value_penbox = self.service.penbox.pens[penbox]
                except KeyError:
                    self.value_penbox = None
            con.set_settings(settings)
            # LOOP CHECKS
            if self._abort_mission():
                return
            while self.paused:
                time.sleep(0.05)
            if isinstance(q, LineCut):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                con.mark(*q.end)
            elif isinstance(q, QuadCut):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                interp = self.service.interp

                g = Geomstr()
                g.quad(complex(*q.start), complex(*q.c()), complex(*q.end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)
                    con.mark(p.real, p.imag)
            elif isinstance(q, CubicCut):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                interp = self.service.interp

                g = Geomstr()
                g.cubic(
                    complex(*q.start),
                    complex(*q.c1()),
                    complex(*q.c2()),
                    complex(*q.end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)
                    con.mark(p.real, p.imag)
            elif isinstance(q, PlotCut):
                last_x, last_y = con.get_last_xy()
                x, y = q.start
                if last_x != x or last_y != y:
                    con.goto(x, y)
                for ox, oy, on, x, y in q.plot:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)

                    # q.plot can have different on values, these are parsed
                    if on == 0:
                        con.goto(x, y)
                    else:
                        if last_on is None or on != last_on:
                            # No power change.
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
                                max_power = float(
                                    q.settings.get("power", self.service.default_power)
                                )
                                percent_power = max_power / 10.0
                                # Max power is the percent max power, scaled by the pixel power.
                                con.power(percent_power * on)
                        con.mark(x, y)
            elif isinstance(q, DwellCut):
                start = q.start
                con.goto(start[0], start[1])
                dwell_time = q.dwell_time * 100  # Dwell time in ms units in 10 us
                while dwell_time > 0:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)
                    d = min(dwell_time, 60000)
                    con.list_laser_on_point(int(d))
                    dwell_time -= d
                con.list_delay_time(int(self.service.delay_end / 10.0))
            elif isinstance(q, WaitCut):
                dwell_time = q.dwell_time * 100  # Dwell time in ms units in 10 us
                while dwell_time > 0:
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
                        time.sleep(0.05)
                    d = min(dwell_time, 60000)
                    con.list_delay_time(int(d))
                    dwell_time -= d
            elif isinstance(q, HomeCut):
                con.goto(0x8000, 0x8000)
            elif isinstance(q, GotoCut):
                con.goto(0x8000, 0x8000)
            elif isinstance(q, OutputCut):
                con.port_set(q.output_mask, q.output_value)
                con.list_write_port()
            elif isinstance(q, InputCut):
                if self.service.input_operation_hardware:
                    con.list_wait_for_input(q.input_mask, 0)
                else:
                    con.rapid_mode()
                    self._wait_for_input_protocol(q.input_mask, q.input_value)
                    con.program_mode()
            else:
                # Rastercut
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    # LOOP CHECKS
                    if self._abort_mission():
                        return
                    while self.paused:
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
                                    self.value_penbox = self.service.penbox.pens[penbox]
                                except KeyError:
                                    self.value_penbox = None
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
                                percent_power = (
                                    float(
                                        settings.get(
                                            "power", self.service.default_power
                                        )
                                    )
                                    / 10.0
                                )
                                con.power(percent_power * on)
                        con.mark(x, y)
        con.list_delay_time(int(self.service.delay_end / 10.0))
        self._list_bits = None
        con.rapid_mode()
        self.service.laser_status = "idle"
        self._set_queue_status(0, 0)

        if self.service.redlight_preferred:
            con.light_on()
            con.write_port()
        else:
            con.light_off()
            con.write_port()

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        old_current = self.service.current
        self.native_x, self.native_y = self.service.view.position(x, y)
        if self.native_x > 0xFFFF:
            self.native_x = 0xFFFF
        if self.native_x < 0:
            self.native_x = 0

        if self.native_y > 0xFFFF:
            self.native_y = 0xFFFF
        if self.native_y < 0:
            self.native_y = 0
        self.connection.set_xy(self.native_x, self.native_y)
        if self.service.signal_updates:
            new_current = self.service.current
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def move_rel(self, dx, dy, confined=False):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        old_current = self.service.current
        unit_dx, unit_dy = self.service.view.position(dx, dy, vector=True)
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
        if self.service.signal_updates:
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
        if self.service.rotary.active and self.service.rotary.suppress_home:
            return
        self.move_abs("50%", "50%")

    def physical_home(self):
        """ "
        This would be the command to go to a real physical home position (i.e. hitting endstops)
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
        return

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
        self.service.signal("pause")

    def resume(self):
        """
        Wants the driver to resume.

        This typically issues from the realtime queue which means it will call even if we tell work_hold that we should
        hold the work.

        @return:
        """
        self.paused = False
        self.connection.resume()
        self.service.signal("pause")

    def reset(self):
        """
        Wants the job to be aborted and action to be stopped.

        @return:
        """
        self.paused = False
        self.connection.abort()
        self.service.signal("pause")

    def dwell(self, time_in_ms, settings=None):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        if settings is not None and "power" in settings:
            power = settings.get("power")
        else:
            power = None
        self.pulse(time_in_ms, power=power)

    def pulse(self, pulse_time, power=None):
        self.service.laser_status = "active"
        con = self.connection
        con.program_mode()
        con.frequency(self.service.default_frequency)
        if power is None:
            power = self.service.default_power
        con.power(power)
        if self.service.pulse_width_enabled:
            con.list_fiber_ylpm_pulse_width(self.service.default_pulse_width)
        dwell_time = pulse_time * 100  # Dwell time in ms units in 10 us
        while dwell_time > 0:
            d = min(dwell_time, 60000)
            con.list_laser_on_point(int(d))
            dwell_time -= d
        con.list_delay_time(int(self.service.delay_end / 10.0))
        con.rapid_mode()
        self.service.laser_status = "idle"
        if self.service.redlight_preferred:
            con.light_on()
            con.write_port()
        else:
            con.light_off()
            con.write_port()

    def set_abort(self):
        self._aborting = True

    def _abort_mission(self):
        if self._aborting:
            self.connection.abort()
            self._aborting = False
            self.service.laser_status = "idle"
            return True
        return False

    def start_pedal_polling(self, origin=""):
        """
        Start the background footpedal polling thread.
        Polls every 0.5 seconds to check footpedal status.
        """
        if self._pedal_thread is not None and self._pedal_thread.is_alive():
            return  # Already running

        self._pedal_thread_running = True
        self._pedal_thread = threading.Thread(
            target=self._pedal_polling_worker, daemon=True, name="BalorPedalPolling"
        )
        self._pedal_thread.start()

    def stop_pedal_polling(self, origin="", force: bool = False):
        """
        Stop the background footpedal polling thread.

        By default, calls from within the driver's runtime (e.g. at plot end) will
        not stop the global polling thread; stopping is only performed when
        explicitly forced or when called from service teardown (origin="service_detach").
        """
        # Only stop the thread if explicitly requested or when shutting down the service
        if not force and origin not in ("service_detach", "service_end"):
            # Ignore transient stop requests so the thread runs for the lifetime of the service
            return

        self._pedal_thread_running = False
        if self._pedal_thread is not None:
            # Give the worker a short time to exit; join with timeout
            self._pedal_thread.join(timeout=1.0)
            if self._pedal_thread.is_alive():
                self.service.channel(
                    "Warning: Pedal polling thread did not exit within timeout; continuing."
                )
            self._pedal_thread = None

    def _pedal_polling_worker(self):
        """
        Background worker thread that polls the footpedal status.
        Runs every 0.5 seconds and checks for state changes.
        The inquiry communication is automatically protected by
        controller's list_lock.

        Based on pedal_mode setting:
        - "ignore": No action (only for input operations)
        - "pause_resume_toggle": Toggle pause/resume job on press
        - "pause_while_pressed": Pause while pressed, resume on release
        - "stop": Abort job (emergency stop) on press

        Based on pedal_active_low setting:
        - True: Bit state 0 means "pressed" (active-low)
        - False: Bit state 1 means "pressed" (active-high)
        """
        while self._pedal_thread_running and not self._shutdown:
            # status = self.connection.get_execution_status()
            try:
                # Check if we should poll (only if pedal mode is active)
                action = self.service.pedal_mode.lower()
                if action != "ignore" and self.connected:
                    # Controller's _usb_lock automatically protects this USB communication
                    port_list = self.connection.read_port()
                    # print(f"Pedal Polling: port_list={port_list}")

                    if port_list is not None:
                        # Check footpedal state
                        foot_pin = self.service.footpedal_pin
                        foot_state = (port_list[1] >> foot_pin) & 1
                        # print(
                        #     f"Pedal Polling: foot_state={foot_state} - last state={self.last_foot_state} "
                        # )

                        # Only process state changes
                        if foot_state != self.last_foot_state:
                            prev_state = self.last_foot_state
                            self.last_foot_state = foot_state

                            # Determine if pedal is now pressed based on configuration
                            active_low = self.service.pedal_active_low

                            # Determine what "pressed" means
                            if active_low:
                                # Active-low: bit 0 = pressed, bit 1 = released
                                is_pressed = foot_state == 0
                                was_pressed = (
                                    (prev_state == 0)
                                    if prev_state is not None
                                    else False
                                )
                            else:
                                # Active-high: bit 1 = pressed, bit 0 = released
                                is_pressed = foot_state == 1
                                was_pressed = (
                                    (prev_state == 1)
                                    if prev_state is not None
                                    else False
                                )

                            # Log the state change
                            state_label = "pressed" if is_pressed else "released"
                            # print(
                            #     f"Pedal Polling: Footpedal {state_label} (bit={foot_state}) - action={action}"
                            # )

                            # Execute action based on pedal mode
                            if action == "pause_resume_toggle":
                                # Toggle pause state only on press
                                if not was_pressed and is_pressed:
                                    if self.paused:
                                        self.resume()
                                        # print("Resuming job due to footpedal press.")
                                        self.service.channel(
                                            f"Footpedal pressed: Job resumed"
                                        )
                                    else:
                                        self.pause()
                                        # print("Pausing job due to footpedal press.")
                                        self.service.channel(
                                            f"Footpedal pressed: Job paused"
                                        )

                            elif action == "pause_while_pressed":
                                # Pause while pressed, resume on release
                                if is_pressed and not was_pressed:
                                    # Just pressed - pause
                                    if not self.paused:
                                        self.pause()
                                        # print("Pausing job due to footpedal press.")
                                        self.service.channel(
                                            f"Footpedal pressed: Job paused"
                                        )
                                elif not is_pressed and was_pressed:
                                    # Just released - resume
                                    if self.paused:
                                        self.resume()

                                        # print("Resuming job due to footpedal release.")
                                        self.service.channel(
                                            f"Footpedal released: Job resumed"
                                        )

                            elif action == "stop":
                                # Emergency stop only on press
                                if not was_pressed and is_pressed:
                                    self.reset()
                                    # print("Emergency stop due to footpedal press.")
                                    self.service.channel(
                                        f"Footpedal pressed: Emergency stop"
                                    )
                            # Log non-action changes if logging enabled
                            if self.service.setting(bool, "log_pedal_events", False):
                                self.service.channel(
                                    f"Footpedal {state_label} (bit={foot_state})"
                                )

                            # Always signal state change for other listeners
                            self.service.signal("pedal_state", foot_state)

            except (AttributeError, TypeError, IndexError) as e:
                # Handle errors gracefully (e.g., connection lost)
                # print(f"Pedal Polling: Ignored error: {e}")
                pass
            except Exception as e:
                # Log unexpected errors but keep thread alive
                # print(f"Pedal Polling: Error: {e}")
                self.service.channel(f"Pedal polling error: {e}")

            # Sleep for the configured interval
            # print(f"Will sleep for {self._pedal_poll_interval} seconds.")
            time.sleep(self._pedal_poll_interval)

    def cylinder_validate(self):
        if self.service.cylinder_active:
            self._cylinder_wrap()
        else:
            self._cylinder_restore()

    def _cylinder_restore(self):
        if not hasattr(self, "_original_connection"):
            return
        oc = getattr(self, "_original_connection")
        self.connection = oc
        delattr(self, "_original_connection")

    def _cylinder_wrap(self):
        if hasattr(self, "_original_connection"):
            return
        from .cylindermod import CylinderModifier

        setattr(self, "_original_connection", self.connection)
        setattr(self, "connection", CylinderModifier(self.connection, self.service))
