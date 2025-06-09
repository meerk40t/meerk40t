"""
GRBL Driver

Governs the generic commands issued by laserjob and spooler and converts that into regular GRBL Gcode output.
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

from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner
from ..core.units import UNITS_PER_INCH, UNITS_PER_MIL, UNITS_PER_MM, Length
from ..device.basedevice import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from ..kernel import signal_listener
from ..tools.geomstr import Geomstr


class GRBLDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.name = str(service)
        self.line_end = None
        self._set_line_end()
        self.paused = False
        self.native_x = 0
        self.native_y = 0

        self.mpos_x = 0
        self.mpos_y = 0
        self.mpos_z = 0

        self.wpos_x = 0
        self.wpos_y = 0
        self.wpos_z = 0

        self.stepper_step_size = UNITS_PER_MIL

        self.plot_planner = PlotPlanner(
            self.settings,
            single=True,
            ppi=False,
            shift=False,
            group=True,
            require_uniform_movement=False,
        )
        self.queue = []
        self._queue_current = 0
        self._queue_total = 0
        self.plot_data = None

        self.on_value = 0
        self.power_dirty = True
        self.speed_dirty = True
        # Zaxis should not be used by default, so we set the dirty flag to False
        self.zaxis_dirty = False
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True
        self.move_mode = 0

        self._absolute = True
        self.feed_mode = None
        self.feed_convert = None
        self._g94_feedrate()  # G94 DEFAULT, mm mode

        self.unit_scale = None
        self.units = None
        self._g21_units_mm()
        self._g90_absolute()

        self.out_pipe = None
        self.out_real = None

        self.reply = None
        self.elements = None
        self.power_scale = 1.0
        self.speed_scale = 1.0
        self._signal_updates = self.service.setting(bool, "signal_updates", True)

    def __repr__(self):
        return f"GRBLDriver({self.name})"

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

    @signal_listener("line_end")
    def _set_line_end(self, origin=None, *args):
        line_end = self.service.setting(str, "line_end", "CR")
        line_end = line_end.replace(" ", "")
        line_end = line_end.replace("CR", "\r")
        line_end = line_end.replace("LF", "\n")
        self.line_end = line_end

    def hold_work(self, priority):
        """
        Required.

        Spooler check. to see if the work cycle should be held.

        @return: hold?
        """
        if priority > 0:
            # Don't hold realtime work.
            return False
        if (
            self.service.limit_buffer
            and len(self.service.controller) > self.service.max_buffer
        ):
            return True
        return self.paused

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
            self.power_dirty = True
        if key == "speed":
            self.speed_dirty = True
        self.settings[key] = value

    def status(self):
        """
        Wants a status report of what the driver is doing.
        @return:
        """
        # TODO: To calculate status correctly we need to actually have access to the response
        self.out_real("?")
        return (self.native_x, self.native_y), "idle", "unknown"

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        self._g90_absolute()
        self._clean()
        old_current = self.service.current
        x, y = self.service.view.position(x, y)
        self._move(x, y)
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
        # self._g90_absolute()
        # self._clean()
        # old_current = self.service.current
        # x, y = old_current
        # x += dx
        # y += dy
        # x, y = self.service.view.position(x, y)
        # self._move(x, y)

        self._g91_relative()
        self._clean()
        old_current = self.service.current

        unit_dx, unit_dy = self.service.view.position(dx, dy, vector=True)
        self._move(unit_dx, unit_dy)

        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        self.laser_on()  # This can't be sent early since these are timed operations.
        self.wait(time_in_ms)
        self.laser_off()

    def laser_off(self, power=0, *values):
        """
        Turn laser off in place.

        @param power: Power after laser turn off (0=default).
        @param values:
        @return:
        """
        if power is not None:
            spower = f" S{power:.1f}"
            self.power = power
            self.power_dirty = False
            self(f"G1 {spower}{self.line_end}")
        self(f"M5{self.line_end}")

    def laser_on(self, power=None, speed=None, *values):
        """
        Turn laser on in place. This is done specifically with an M3 command so that the laser is on while stationary

        @param speed: Speed for laser turn on.
        @param power: Power at the laser turn on.
        @param values:
        @return:
        """
        spower = ""
        sspeed = ""
        if power is not None:
            spower = f" S{power:.1f}"
            # We already established power, so no need for power_dirty
            self.power = power
            self.power_dirty = False
        if speed is not None:
            sspeed = f"G1 F{speed}{self.line_end}"
            self.speed = speed
            self.speed_dirty = False
        self(f"M3{spower}{self.line_end}{sspeed}")

    def geometry(self, geom):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        # TODO: estop cannot clear the geom.
        self.signal("grbl_red_dot", False)  # We are not using red-dot if we're cutting.
        self.clear_states()
        self._g90_absolute()
        self._g94_feedrate()
        self._clean()
        if self.service.use_m3:
            self(f"M3{self.line_end}")
        else:
            self(f"M4{self.line_end}")
        first = True
        g = Geomstr()
        for segment_type, start, c1, c2, end, sets in geom.as_lines():
            while self.hold_work(0):
                if self.service.kernel.is_shutdown:
                    return
                time.sleep(0.05)
            x = self.native_x
            y = self.native_y
            start_x, start_y = start.real, start.imag
            if x != start_x or y != start_y or first:
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                first = False
                self._move(start_x, start_y)
            if self.on_value != 1.0:
                self.power_dirty = True
            self.on_value = 1.0
            # Default-Values?!
            qpower = sets.get("power", self.power)
            qspeed = sets.get("speed", self.speed)
            qraster_step_x = sets.get("raster_step_x")
            qraster_step_y = sets.get("raster_step_y")
            if qpower != self.power:
                self.set("power", qpower)
            if (
                qspeed != self.speed
                or qraster_step_x != self.raster_step_x
                or qraster_step_y != self.raster_step_y
            ):
                self.set("speed", qspeed)
            self.settings.update(sets)
            if segment_type == "line":
                self.move_mode = 1
                self._move(end.real, end.imag)
            elif segment_type == "end":
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                first = False
            elif segment_type == "quad":
                self.move_mode = 1
                interp = self.service.interp
                g.clear()
                g.quad(complex(start), complex(c1), complex(end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif segment_type == "cubic":
                self.move_mode = 1
                interp = self.service.interp
                g.clear()
                g.cubic(
                    complex(start),
                    complex(c1),
                    complex(c2),
                    complex(end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif segment_type == "arc":
                # TODO: Allow arcs to be directly executed by GRBL which can actually use them.
                self.move_mode = 1
                interp = self.service.interp
                g.clear()
                g.arc(
                    complex(start),
                    complex(c1),
                    complex(end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif segment_type == "point":
                function = sets.get("function")
                if function == "dwell":
                    self.dwell(sets.get("dwell_time"))
                elif function == "wait":
                    self.wait(sets.get("dwell_time"))
                elif function == "home":
                    self.home()
                elif function == "goto":
                    self._move(start.real, start.imag)
                elif function == "input":
                    # GRBL has no core GPIO functionality
                    pass
                elif function == "output":
                    # GRBL has no core GPIO functionality
                    pass
        self(f"G1 S0{self.line_end}")
        self(f"M5{self.line_end}")
        self.clear_states()
        self.wait_finish()
        return False

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
        self.signal("grbl_red_dot", False)  # We are not using red-dot if we're cutting.
        self.clear_states()
        self._g90_absolute()
        self._g94_feedrate()
        self._clean()
        if self.service.use_m3:
            self(f"M3{self.line_end}")
        else:
            self(f"M4{self.line_end}")
        first = True
        total = len(self.queue)
        current = 0
        for q in self.queue:
            # Are there any custom commands to be executed?
            # Usecase (as described in issue https://github.com/meerk40t/meerk40t/issues/2764 ):
            # Switch between M3 and M4 mode for cut / raster
            #   M3=used to cut as gantry acceleration doesn't matter on a cut.
            #   M4=used for Raster/Engrave operations, as grblHAL will
            #   adjust power based on gantry speed including acceleration.

            cmd_string = q.settings.get("custom_commands", "")
            if cmd_string:
                for cmd in cmd_string.splitlines():
                    self(f"{cmd}{self.line_end}")

            current += 1
            self._set_queue_status(current, total)
            while self.hold_work(0):
                if self.service.kernel.is_shutdown:
                    return
                time.sleep(0.05)
            x = self.native_x
            y = self.native_y
            start_x, start_y = q.start
            if x != start_x or y != start_y or first:
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                first = False
                self._move(start_x, start_y)
            if self.on_value != 1.0:
                self.power_dirty = True
            self.on_value = 1.0
            # Do we have a custom z-Value?
            # NB: zaxis is not a property inside Parameters like power/or speed
            # so we need to deal with it more directly
            # (e.g. self.power is the equivalent to self.settings.["power"]))
            qzaxis = q.settings.get("zaxis", self.zaxis)
            if qzaxis != self.zaxis:
                self.zaxis = qzaxis
                self.zaxis_dirty = True
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
                self.move_mode = 1
                self._move(*q.end)
            elif isinstance(q, QuadCut):
                self.move_mode = 1
                interp = self.service.interp
                g = Geomstr()
                g.quad(complex(*q.start), complex(*q.c()), complex(*q.end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif isinstance(q, CubicCut):
                self.move_mode = 1
                interp = self.service.interp
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
                    self._move(p.real, p.imag)
            elif isinstance(q, WaitCut):
                self.wait(q.dwell_time)
            elif isinstance(q, HomeCut):
                self.home()
            elif isinstance(q, GotoCut):
                start = q.start
                self._move(start[0], start[1])
            elif isinstance(q, DwellCut):
                self.dwell(q.dwell_time)
            elif isinstance(q, (InputCut, OutputCut)):
                # GRBL has no core GPIO functionality
                pass
            elif isinstance(q, PlotCut):
                self.move_mode = 1
                self.set("power", 1000)
                for ox, oy, on, x, y in q.plot:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    # q.plot can have different on values, these are parsed
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y)
            else:
                #  Rastercut
                self.plot_planner.push(q)
                self.move_mode = 1
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
                            # self.move_mode = 0
                            self.rapid_mode()
                            self._move(x, y)
                        continue
                    # if on == 0:
                    #     self.move_mode = 0
                    # else:
                    #     self.move_mode = 1
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y)
        self.queue.clear()
        self._set_queue_status(0, 0)

        self(f"G1 S0{self.line_end}")
        self(f"M5{self.line_end}")
        self.clear_states()
        self.wait_finish()
        return False

    def blob(self, data_type, data):
        """
        This is intended to send a blob of gcode to be processed and executed.

        @param data_type:
        @param data:
        @return:
        """
        if data_type != "grbl":
            return
        grbl = bytes.decode(data, "latin-1")
        for split in grbl.split("\r"):
            g = split.strip()
            if g:
                self(f"{g}{self.line_end}")

    def physical_home(self):
        """
        Home the laser physically (i.e. run into endstops).

        @return:
        """
        old_current = self.service.current
        self.native_x = 0
        self.native_y = 0
        if self.service.has_endstops:
            self(f"$H{self.line_end}")
        else:
            self(f"G28{self.line_end}")
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def home(self):
        """
        Home the laser (i.e. goto defined origin)

        @return:
        """
        self.native_x = 0
        self.native_y = 0
        if self.service.rotary.active and self.service.rotary.suppress_home:
            return
        self(f"G28{self.line_end}")

    def rapid_mode(self, *values):
        """
        Rapid mode sets the laser to rapid state. This is usually moving the laser around without it executing a large
        batch of commands.

        @param values:
        @return:
        """
        speedvalue = self.service.setting(float, "rapid_speed", 600.0)
        if self.speed != speedvalue:
            self.speed = speedvalue
            self.speed_dirty = True

    def finished_mode(self, *values):
        """
        Finished mode is after a large batch of jobs is done.

        @param values:
        @return:
        """
        self(f"M5{self.line_end}")

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands.
        @param values:
        @return:
        """
        self(f"M3{self.line_end}")

    def raster_mode(self, *values):
        """
        Raster mode is a special form of program mode that suggests the batch of commands will be a raster operation
        many lasers have specialty values
        @param values:
        @return:
        """

    def wait(self, time_in_ms):
        """
        Wait asks that the work be stalled or current process held for the time time_in_ms in ms. If wait_finished is
        called first this will attempt to stall the machine while performing no work. If the driver in question permits
        waits to be placed within code this should insert waits into the current job. Returning instantly rather than
        holding the processes.

        @param time_in_ms:
        @return:
        """
        self(f"G04 S{time_in_ms / 1000.0}{self.line_end}")

    def wait_finish(self, *values):
        """
        Wait finish should hold the calling thread until the current work has completed. Or otherwise prevent any data
        from being sent with returning True for the until that criteria is met.

        @param values:
        @return:
        """
        while True:
            if self.queue or len(self.service.controller):
                time.sleep(0.05)
                continue
            break

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
        if signal == "coolant":
            onoff = args[0]
            coolid = None
            if hasattr(self.service, "coolant"):
                coolid = self.service.device_coolant
            if not coolid:
                return
            routine = None
            try:
                cool = self.service.context.kernel.root.coolant
                routine = cool.claim_coolant(self.service, coolid)
            except AttributeError:
                routine = None
            if routine:
                try:
                    routine(self.service, onoff)
                except RuntimeError:
                    pass

        else:
            self.service.signal(signal, *args)

    def pause(self, *args):
        """
        Asks that the laser be paused.

        @param args:
        @return:
        """
        self.paused = True
        # self(f"!{self.line_end}", real=True)
        self(chr(0x21), real=True)  # Hex 21 = !
        # Let's make sure we reestablish power...
        self.power_dirty = True
        self.service.signal("pause")

    def resume(self, *args):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser.

        @param args:
        @return:
        """
        self.paused = False
        # self(f"~{self.line_end}", real=True)
        self(chr(0x7E), real=True)  # hex 7e = ~
        self.service.signal("pause")

    def clear_states(self):
        self.power_dirty = True
        self.speed_dirty = True
        self.zaxis_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True
        self.move_mode = 0

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.
        Asks that the device resets, and clears all current work.

        @param args:
        @return:
        """
        self.service.spooler.clear_queue()
        self.queue.clear()
        self.plot_planner.clear()
        self(f"\x18{self.line_end}", real=True)
        self._g94_feedrate()
        self._g21_units_mm()
        self._g90_absolute()

        self.power_dirty = True
        self.speed_dirty = True
        self.zaxis_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True

        self.paused = False
        self.service.signal("pause")

    def clear_alarm(self):
        """
        GRBL clear alarm signal.

        @return:
        """
        self(f"$X{self.line_end}", real=True)
        if self.service.extended_alarm_clear:
            self.reset()

    def declare_modals(self, modals):
        self.move_mode = 0 if "G0" in modals else 1
        if "G90" in modals:
            self._g90_absolute()
            self.absolute_dirty = False
        if "G91" in modals:
            self._g91_relative()
            self.absolute_dirty = False
        if "G94" in modals:
            self._g94_feedrate()
            self.feedrate_dirty = False
        if "G93" in modals:
            self._g93_feedrate()
            self.feedrate_dirty = False
        if "G20" in modals:
            self._g20_units_inch()
            self.units_dirty = False
        if "G21" in modals:
            self._g21_units_mm()
            self.units_dirty = False

    def declare_position(self, x, y):
        self.native_x = x * self.unit_scale
        self.native_y = y * self.unit_scale

    ####################
    # PROTECTED DRIVER CODE
    ####################

    def _move(self, x, y, absolute=False):
        old_current = self.service.current
        if self._absolute:
            self.native_x = x
            self.native_y = y
        else:
            self.native_x += x
            self.native_y += y
        line = []
        if self.move_mode == 0:
            line.append("G0")
        else:
            line.append("G1")
        x /= self.unit_scale
        y /= self.unit_scale
        line.append(f"X{x:.3f}")
        line.append(f"Y{y:.3f}")
        if self.zaxis_dirty:
            self.zaxis_dirty = False
            if self.zaxis is not None:
                try:
                    z = float(Length(self.zaxis) / self.service.view.native_scale_x)
                    z /= self.unit_scale
                    line.append(f"Z{z:.3f}")
                except ValueError:
                    pass

        if self.power_dirty:
            if self.power is not None:
                line.append(f"S{self.power * self.on_value:.1f}")
            self.power_dirty = False
        if self.speed_dirty:
            line.append(f"F{self.feed_convert(self.speed):.1f}")
            self.speed_dirty = False
        self(" ".join(line) + self.line_end)
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def _clean_motion(self):
        if self.absolute_dirty:
            if self._absolute:
                self(f"G90{self.line_end}")
            else:
                self(f"G91{self.line_end}")
        self.absolute_dirty = False

    def _clean_feed_mode(self):
        if self.feedrate_dirty:
            if self.feed_mode == 94:
                self(f"G94{self.line_end}")
            else:
                self(f"G93{self.line_end}")
        self.feedrate_dirty = False

    def _clean_units(self):
        if self.units_dirty:
            if self.units == 20:
                self(f"G20{self.line_end}")
            else:
                self(f"G21{self.line_end}")
        self.units_dirty = False

    def _clean(self):
        self._clean_motion()
        self._clean_feed_mode()
        self._clean_units()

    def _g91_relative(self):
        if not self._absolute:
            return
        self._absolute = False
        self.absolute_dirty = True

    def _g90_absolute(self):
        if self._absolute:
            return
        self._absolute = True
        self.absolute_dirty = True

    def _g93_mms_to_minutes_per_gunits(self, mms):
        millimeters_per_minute = 60.0 * mms
        distance = UNITS_PER_MIL / self.stepper_step_size
        return distance / millimeters_per_minute

    def _g93_feedrate(self):
        if self.feed_mode == 93:
            return
        self.feed_mode = 93
        # Feed Rate in Minutes / Unit
        self.feed_convert = self._g93_mms_to_minutes_per_gunits
        self.feedrate_dirty = True

    def _g94_mms_to_gunits_per_minute(self, mms):
        millimeters_per_minute = 60.0 * mms
        distance = UNITS_PER_MIL / self.stepper_step_size
        return millimeters_per_minute / distance

    def _g94_feedrate(self):
        if self.feed_mode == 94:
            return
        self.feed_mode = 94
        # Feed Rate in Units / Minute
        self.feed_convert = self._g94_mms_to_gunits_per_minute
        # units to mm, seconds to minutes.
        self.feedrate_dirty = True

    def _g20_units_inch(self):
        self.units = 20
        self.unit_scale = UNITS_PER_INCH / self.stepper_step_size  # g20 is inch mode.
        self.units_dirty = True

    def _g21_units_mm(self):
        self.units = 21
        self.unit_scale = UNITS_PER_MM / self.stepper_step_size  # g21 is mm mode.
        self.units_dirty = True

    def set_power_scale(self, factor):
        # Grbl can only deal with factors between 10% and 200%
        if factor <= 0 or factor > 2.0:
            factor = 1.0
        if self.power_scale == factor:
            return
        self.power_scale = factor

        # Grbl can only deal with factors between 10% and 200%
        self("\x99\r", real=True)
        # Upward loop
        start = 1.0
        while start < 2.0 and start < factor:
            self("\x9B\r", real=True)
            start += 0.1
        # Downward loop
        start = 1.0
        while start > 0.0 and start > factor:
            self("\x9A\r", real=True)
            start -= 0.1

    def set_speed_scale(self, factor):
        # Grbl can only deal with factors between 10% and 200%
        if factor <= 0 or factor > 2.0:
            factor = 1.0
        if self.speed_scale == factor:
            return
        self.speed_scale = factor
        self("\x90\r", real=True)
        start = 1.0
        while start < 2.0 and start < factor:
            self("\x91\r", real=True)
            start += 0.1
        # Downward loop
        start = 1.0
        while start > 0.0 and start > factor:
            self("\x92\r", real=True)
            start -= 0.1

    @staticmethod
    def has_adjustable_power():
        return True

    @staticmethod
    def has_adjustable_speed():
        return True
