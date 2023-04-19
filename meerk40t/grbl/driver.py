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
from meerk40t.core.cutcode.quadcut import QuadCut
from meerk40t.core.cutcode.setorigincut import SetOriginCut
from meerk40t.core.cutcode.waitcut import WaitCut

from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner
from ..core.units import UNITS_PER_INCH, UNITS_PER_MIL, UNITS_PER_MM
from ..device.basedevice import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from ..kernel import signal_listener


class GRBLDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.name = str(service)
        self.line_end = None
        self._set_line_end()
        self.hold = False
        self.paused = False
        self.native_x = 0
        self.native_y = 0
        self.origin_x = 0
        self.origin_y = 0
        self.stepper_step_size = UNITS_PER_MIL

        self.plot_planner = PlotPlanner(
            self.settings, single=True, ppi=False, shift=False, group=True
        )
        self.queue = []
        self.plot_data = None

        self.on_value = 0
        self.power_dirty = True
        self.speed_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True

        self._absolute = True
        self.feed_mode = None
        self.feed_convert = None
        self._g94_feedrate()  # G93 DEFAULT, mm mode

        self.unit_scale = None
        self.units = None
        self._g21_units_mm()
        self._g91_absolute()

        self.grbl = self.service.channel("grbl", pure=True)
        self.grbl_realtime = self.service.channel("grbl-realtime", pure=True)

        self.move_mode = 0
        self.reply = None
        self.elements = None
        self.power_scale = 1.0
        self.speed_scale = 1.0

    def __repr__(self):
        return f"GRBLDriver({self.name})"

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
        return priority <= 0 and (self.paused or self.hold)

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
        self.grbl_realtime("?")
        return (self.native_x, self.native_y), "idle", "unknown"

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        self._g91_absolute()
        self._clean()
        old_current = self.service.current
        x, y = self.service.physical_to_device_position(x, y)
        self._move(x, y)
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
        self._g90_relative()
        self._clean()
        old_current = self.service.current

        dx, dy = self.service.physical_to_device_length(dx, dy)
        # self.rapid_mode()
        self._move(dx, dy)

        new_current = self.service.current
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

    def laser_off(self, *values):
        """
        Turn laser off in place.

        @param values:
        @return:
        """
        self.grbl(f"M5{self.line_end}")

    def laser_on(self, power=None, speed=None, *values):
        """
        Turn laser on in place.

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
        self.grbl(f"M3{spower}{self.line_end}{sspeed}")

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
        self._g91_absolute()
        self._g94_feedrate()
        self._clean()
        if self.service.use_m3:
            self.grbl(f"M3{self.line_end}")
        else:
            self.grbl(f"M4{self.line_end}")
        for q in self.queue:
            x = self.native_x
            y = self.native_y
            start_x, start_y = q.start
            if x != start_x or y != start_y:
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                self._move(start_x, start_y)
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
                self.move_mode = 1
                self._move(*q.end)
            elif isinstance(q, (QuadCut, CubicCut)):
                self.move_mode = 1
                interp = self.service.interpolate
                step_size = 1.0 / float(interp)
                t = step_size
                for p in range(int(interp)):
                    while self.paused:
                        time.sleep(0.05)
                    self._move(*q.point(t))
                    t += step_size
                last_x, last_y = q.end
                self._move(last_x, last_y)
            elif isinstance(q, WaitCut):
                self.wait(q.dwell_time)
            elif isinstance(q, HomeCut):
                self.home()
            elif isinstance(q, GotoCut):
                start = q.start
                self._move(self.origin_x + start[0], self.origin_y + start[1])
            elif isinstance(q, SetOriginCut):
                if q.set_current:
                    x = self.native_x
                    y = self.native_y
                else:
                    x, y = q.start
                self.set_origin(x, y)
            elif isinstance(q, DwellCut):
                self.dwell(q.dwell_time)
            elif isinstance(q, (InputCut, OutputCut)):
                # GRBL has no core GPIO functionality
                pass
            else:
                #  Rastercut, PlotCut
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    while self.paused:
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
                            self.move_mode = 0
                            self._move(x, y)
                        continue
                    if on == 0:
                        self.move_mode = 0
                    else:
                        self.move_mode = 1
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y)
        self.queue.clear()

        self.grbl(f"G1 S0{self.line_end}")
        self.grbl(f"M5{self.line_end}")
        self.power_dirty = True
        self.speed_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True
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
        for line in data:
            grbl = bytes.decode(line, "utf-8")
            for split in grbl.split("\r"):
                g = split.strip()
                if g:
                    self.grbl(f"{g}{self.line_end}")

    def physical_home(self):
        """
        Home the laser physically (ie run into endstops).

        @return:
        """
        self.native_x = 0
        self.native_y = 0
        if self.service.has_endstops:
            self.grbl(f"$H{self.line_end}")
        else:
            self.grbl(f"G28{self.line_end}")

    def home(self):
        """
        Home the laser (ie goto defined origin)

        @return:
        """
        self.native_x = 0
        self.native_y = 0
        if self.service.rotary_active and self.service.rotary_supress_home:
            return
        self.grbl(f"G28{self.line_end}")

    def rapid_mode(self, *values):
        """
        Rapid mode sets the laser to rapid state. This is usually moving the laser around without it executing a large
        batch of commands.

        @param values:
        @return:
        """

    def finished_mode(self, *values):
        """
        Finished mode is after a large batch of jobs is done.

        @param values:
        @return:
        """
        self.grbl(f"M5{self.line_end}")

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands.
        @param values:
        @return:
        """
        self.grbl(f"M3{self.line_end}")

    def raster_mode(self, *values):
        """
        Raster mode is a special form of program mode that suggests the batch of commands will be a raster operation
        many lasers have specialty values
        @param values:
        @return:
        """

    def set_origin(self, x, y):
        """
        This should set the origin position.

        @param x:
        @param y:
        @return:
        """
        self.origin_x = x
        self.origin_y = y

    def wait(self, time_in_ms):
        """
        Wait asks that the work be stalled or current process held for the time time_in_ms in ms. If wait_finished is
        called first this will attempt to stall the machine while performing no work. If the driver in question permits
        waits to be placed within code this should insert waits into the current job. Returning instantly rather than
        holding the processes.

        @param time_in_ms:
        @return:
        """
        self.grbl(f"G04 S{time_in_ms / 1000.0}{self.line_end}")

    def wait_finish(self, *values):
        """
        Wait finish should hold the calling thread until the current work has completed. Or otherwise prevent any data
        from being sent with returning True for the until that criteria is met.

        @param values:
        @return:
        """
        pass

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
        self.grbl_realtime("!")

    def resume(self, *args):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser.

        @param args:
        @return:
        """
        self.paused = False
        self.grbl_realtime("~")

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.
        Asks that the device resets, and clears all current work.

        @param args:
        @return:
        """
        self.service.spooler.clear_queue()
        self.plot_planner.clear()
        self.grbl_realtime("\x18")
        self.paused = False

    def clear_alarm(self):
        """
        GRBL clear alarm signal.

        @return:
        """
        self.grbl_realtime("$X\n")

    ####################
    # PROTECTED DRIVER CODE
    ####################

    def _move(self, x, y, absolute=False):
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
        if self.power_dirty:
            if self.power is not None:
                line.append(f"S{self.power * self.on_value:.1f}")
            self.power_dirty = False
        if self.speed_dirty:
            line.append(f"F{self.feed_convert(self.speed):.1f}")
            self.speed_dirty = False
        self.grbl(" ".join(line) + self.line_end)

    def _clean(self):
        if self.absolute_dirty:
            if self._absolute:
                self.grbl(f"G90{self.line_end}")
            else:
                self.grbl(f"G91{self.line_end}")
        self.absolute_dirty = False

        if self.feedrate_dirty:
            if self.feed_mode == 94:
                self.grbl(f"G94{self.line_end}")
            else:
                self.grbl(f"G93{self.line_end}")
        self.feedrate_dirty = False

        if self.units_dirty:
            if self.units == 20:
                self.grbl(f"G20{self.line_end}")
            else:
                self.grbl(f"G21{self.line_end}")
        self.units_dirty = False

    def _g90_relative(self):
        if not self._absolute:
            return
        self._absolute = False
        self.absolute_dirty = True

    def _g91_absolute(self):
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
        if 0 < factor < 100:
            self.power_scale = factor
        else:
            self.power_scale = 1.0
        # Grbl can only deal with factors between 10% and 200%
        ifactor = int(self.power_scale * 10 + 10)
        ifactor = min(20, max(1, ifactor))
        self.grbl_realtime("\x99")
        if ifactor < 10:
            for idx in range(10 - ifactor):
                self.grbl_realtime("\x9A")
        elif ifactor > 10:
            for idx in range(ifactor - 10):
                self.grbl_realtime("\x9B")

    def set_speed_scale(self, factor):
        if 0 < factor < 100:
            self.speed_scale = factor
        else:
            self.speed_scale = 1.0
        # Grbl can only deal with factors between 10% and 200%
        ifactor = int(self.speed_scale * 10 + 10)
        ifactor = min(20, max(1, ifactor))
        self.grbl_realtime("\x90")
        if ifactor < 10:
            for idx in range(10 - ifactor):
                self.grbl_realtime("\x92")
        elif ifactor > 10:
            for idx in range(ifactor - 10):
                self.grbl_realtime("\x91")

    @staticmethod
    def has_adjustable_power():
        return True

    @staticmethod
    def has_adjustable_speed():
        return True
