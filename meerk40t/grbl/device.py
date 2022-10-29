import socket
import threading
import time

import serial
from serial import SerialException

from meerk40t.kernel import CommandSyntaxError, Service

from ..core.cutcode import (
    CubicCut,
    DwellCut,
    GotoCut,
    HomeCut,
    InputCut,
    LineCut,
    OutputCut,
    QuadCut,
    SetOriginCut,
    WaitCut,
)
from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner
from ..core.spoolers import LaserJob, Spooler
from ..core.units import UNITS_PER_INCH, UNITS_PER_MIL, UNITS_PER_MM, ViewPort
from ..device.basedevice import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING

"""
GRBL device.
"""


class GRBLDevice(Service, ViewPort):
    """
    GRBLDevice is driver for the Gcode Controllers
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "GRBLDevice"
        self.extension = "gcode"

        self.setting(str, "label", path)
        _ = self._
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "235mm",
                "type": str,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "subsection": "Dimensions",
                "signals": "bedsize",
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "235mm",
                "type": str,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "subsection": "Dimensions",
                "signals": "bedsize",
            },
            {
                "attr": "scale_x",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("X-Axis"),
                "tip": _(
                    "Scale factor for the X-axis. Board units to actual physical units."
                ),
                "subsection": "Scale",
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y-Axis"),
                "tip": _(
                    "Scale factor for the Y-axis. Board units to actual physical units."
                ),
                "subsection": "Scale",
            },
            {
                "attr": "flip_x",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Flip X"),
                "tip": _(
                    "+X is standard for grbl but sometimes settings can flip that."
                ),
                "subsection": "_10_Flip Axis",
                "signals": ("bedsize"),
            },
            {
                "attr": "flip_y",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Flip Y"),
                "tip": _(
                    "-Y is standard for grbl but sometimes settings can flip that."
                ),
                "subsection": "_10_Flip Axis",
                "signals": ("bedsize"),
            },
            {
                "attr": "swap_xy",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Swap XY"),
                "tip": _(
                    "Swaps the X and Y axis. This happens before the FlipX and FlipY."
                ),
                "subsection": "_20_Axis corrections",
                "signals": "bedsize",
            },
            {
                "attr": "home_bottom",
                "object": self,
                "default": True,
                "type": bool,
                "label": _("Home Bottom"),
                "tip": _("Indicates the device Home is on the bottom"),
                "subsection": "_30_Home position",
                "signals": "bedsize",
            },
            {
                "attr": "home_right",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Home Right"),
                "tip": _("Indicates the device Home is at the right side"),
                "subsection": "_30_Home position",
                "signals": "bedsize",
            },
        ]
        self.register_choices("bed_dim", choices)
        # Tuple contains 4 value pairs: Speed Low, Speed High, Power Low, Power High, each with enabled, value
        self.setting(
            list, "dangerlevel_op_cut", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_engrave", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_hatch", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_raster", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_image", (False, 0, False, 0, False, 0, False, 0)
        )
        self.setting(
            list, "dangerlevel_op_dots", (False, 0, False, 0, False, 0, False, 0)
        )
        ViewPort.__init__(
            self,
            self.bedwidth,
            self.bedheight,
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            flip_x=self.flip_x,
            flip_y=self.flip_y,
            swap_xy=self.swap_xy,
            origin_x=1.0 if self.home_right else 0.0,
            origin_y=1.0 if self.home_bottom else 0.0,
        )

        self.settings = dict()
        self.state = 0

        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "grbl",
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
            },
            {
                "attr": "com_port",
                "object": self,
                "default": "com1",
                "type": str,
                "label": _("COM Port"),
                "tip": _("What com port does this device connect to?"),
                "subsection": "Interface",
            },
            {
                "attr": "baud_rate",
                "object": self,
                "default": 115200,
                "type": int,
                "label": _("Baud Rate"),
                "tip": _("Baud Rate of the device"),
                "subsection": "Interface",
            },
            {
                "attr": "planning_buffer_size",
                "object": self,
                "default": 255,
                "type": int,
                "label": _("Planning Buffer Size"),
                "tip": _("Size of Planning Buffer"),
            },
            {
                "attr": "interpolate",
                "object": self,
                "default": 50,
                "type": int,
                "label": _("Curve Interpolation"),
                "tip": _("Distance of the curve interpolation in mils"),
            },
            {
                "attr": "mock",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Run mock-usb backend"),
                "tip": _(
                    "This starts connects to fake software laser rather than real one for debugging."
                ),
            },
        ]
        self.register_choices("grbl-connection", choices)

        choices = [
            {
                "attr": "use_m3",
                "object": self,
                "default": False,
                "type": bool,
                "label": _("Use M3"),
                "tip": _(
                    "Uses M3 rather than M4 for laser start (see GRBL docs for additional info)"
                ),
            },
        ]
        self.register_choices("grbl-global", choices)

        self.driver = GRBLDriver(self)
        self.controller = GrblController(self)
        self.channel("grbl").watch(self.controller.write)
        self.channel("grbl-realtime").watch(self.controller.realtime)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)

        self.viewbuffer = ""

        _ = self.kernel.translation

        @self.console_argument("com")
        @self.console_option("baud", "b")
        @self.console_command(
            "serial",
            help=_("link the serial connection"),
            input_type=None,
        )
        def serial_connection(
            command,
            channel,
            _,
            data=None,
            com=None,
            baud=115200,
            remainder=None,
            **kwgs,
        ):
            if com is None:
                import serial.tools.list_ports

                ports = serial.tools.list_ports.comports()

                channel("Available COM ports")
                for x in ports:
                    channel(x.description)

        @self.console_command(
            "gcode",
            help=_("Send raw gcode to the device"),
            input_type=None,
        )
        def gcode(command, channel, _, data=None, remainder=None, **kwgs):
            if remainder is not None:
                channel(remainder)
                self.channel("grbl")(remainder + "\r")

        @self.console_command(
            "soft_reset",
            help=_("Send realtime soft reset gcode to the device"),
            input_type=None,
        )
        def soft_reset(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.reset()
            self.signal("pipe;running", False)

        @self.console_command(
            "estop",
            help=_("Send estop to the laser"),
            input_type=None,
        )
        def estop(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.reset()
            self.signal("pipe;running", False)

        @self.console_command(
            "clear_alarm",
            help=_("Send clear_alarm to the laser"),
            input_type=None,
        )
        def clear_alarm(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.clear_alarm()
            self.signal("pipe;running", False)

        @self.console_command(
            "pause",
            help=_("Send realtime soft pause/resume gcode to the device"),
            input_type=None,
        )
        def pause(command, channel, _, data=None, remainder=None, **kwgs):
            if self.driver.paused:
                self.driver.resume()
            else:
                self.driver.pause()

        @self.console_command(
            "resume",
            help=_("Send realtime resume gcode to the device"),
            input_type=None,
        )
        def resume(command, channel, _, data=None, remainder=None, **kwgs):
            self.driver.resume()

        @self.console_command(
            "viewport_update",
            hidden=True,
            help=_("Update grbl codes for movement"),
        )
        def codes_update(**kwargs):
            self.realize()

        @self.console_argument("filename", type=str)
        @self.console_command("save_job", help=_("save job export"), input_type="plan")
        def gcode_save(channel, _, filename, data=None, **kwargs):
            if filename is None:
                raise CommandSyntaxError
            try:
                with open(filename, "w") as f:
                    # f.write(b"(MeerK40t)\n")
                    driver = GRBLDriver(self)
                    job = LaserJob(filename, list(data.plan), driver=driver)
                    driver.grbl = f.write
                    job.execute()

            except (PermissionError, IOError):
                channel(_("Could not save: {filename}").format(filename=filename))

    @property
    def current(self):
        """
        @return: the location in scene units for the current known x value.
        """
        return self.device_to_scene_position(
            self.driver.native_x,
            self.driver.native_y,
        )

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.driver.native_x, self.driver.native_y

    @property
    def current_x(self):
        """
        @return: the location in nm for the current known y value.
        """
        return self.current[0]

    @property
    def current_y(self):
        """
        @return: the location in nm for the current known y value.
        """
        return self.current[1]

    def realize(self):
        self.width = self.bedwidth
        self.height = self.bedheight
        self.origin_x = 1.0 if self.home_right else 0.0
        self.origin_y = 1.0 if self.home_bottom else 0.0
        super().realize()


class GRBLDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.name = str(service)
        self.hold = False
        self.paused = False
        self.native_x = 0
        self.native_y = 0
        self.origin_x = 0
        self.origin_y = 0
        self.stepper_step_size = UNITS_PER_MIL

        self.plot_planner = PlotPlanner(
            self.settings, single=True, smooth=False, ppi=False, shift=False, group=True
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

    def __repr__(self):
        return f"GRBLDriver({self.name})"

    def hold_work(self, priority):
        """
        Required.

        Spooler check. to see if the work cycle should be held.

        @return: hold?
        """
        return priority <= 0 and (self.paused or self.hold)

    def move_ori(self, x, y):
        """
        Requests laser move to origin offset position x,y in physical units

        @param x:
        @param y:
        @return:
        """
        self._g91_absolute()
        self._clean()
        old_current = self.service.current
        x, y = self.service.physical_to_device_position(x, y)
        self._move(self.origin_x + x, self.origin_y + y)
        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

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
        self.grbl("M3\r")

    def laser_on(self, *values):
        """
        Turn laser on in place.

        @param values:
        @return:
        """
        self.grbl("M5\r")

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
            self.grbl("M3\r")
        else:
            self.grbl("M4\r")
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
            if q.power != self.power:
                self.set("power", q.power)
            if (
                q.speed != self.speed
                or q.raster_step_x != self.raster_step_x
                or q.raster_step_y != self.raster_step_y
            ):
                self.set("speed", q.speed)
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
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    while self.paused:
                        time.sleep(0.05)
                    if on > 1:
                        # Special Command.
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

        self.grbl("G1 S0\r")
        self.grbl("M5\r")
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
        if data_type != "gcode":
            return
        for line in data:
            # TODO: Process line does not exist as a function.
            self.process_line(line)

    def home(self):
        """
        Home the laser.

        @return:
        """
        self.native_x = 0
        self.native_y = 0
        self.grbl("G28\r")

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
        self.grbl("M5\r")

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands.
        @param values:
        @return:
        """
        self.grbl("M3\r")

    def raster_mode(self, *values):
        """
        Raster mode is a special form of program mode that suggests the batch of commands will be a raster operation
        many lasers have specialty values
        @param values:
        @return:
        """

    def set(self, key, value):
        """
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
        self.grbl(f"G04 S{time_in_ms / 1000.0}\r")

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

    def status(self):
        """
        Asks that this device status be updated.

        @return:
        """
        self.grbl_realtime("?")

        parts = list()
        parts.append(f"x={self.native_x}")
        parts.append(f"y={self.native_y}")
        parts.append(f"speed={self.settings.get('speed', 0.0)}")
        parts.append(f"power={self.settings.get('power', 0)}")
        status = ";".join(parts)
        self.service.signal("driver;status", status)

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
        self.grbl(" ".join(line) + "\r")

    def _clean(self):
        if self.absolute_dirty:
            if self._absolute:
                self.grbl("G90\r")
            else:
                self.grbl("G91\r")
        self.absolute_dirty = False

        if self.feedrate_dirty:
            if self.feed_mode == 94:
                self.grbl("G94\r")
            else:
                self.grbl("G93\r")
        self.feedrate_dirty = False

        if self.units_dirty:
            if self.units == 20:
                self.grbl("G20\r")
            else:
                self.grbl("G21\r")
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


class GrblController:
    def __init__(self, context):
        self.service = context
        self.com_port = self.service.com_port
        self.baud_rate = self.service.baud_rate
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.send = self.service.channel(f"send-{self.com_port.lower()}")
        self.recv = self.service.channel(f"recv-{self.com_port.lower()}")
        if not self.service.mock:
            self.connection = SerialConnection(self.service)
        else:
            self.connection = MockConnection(self.service)
        self.driver = self.service.driver
        self.sending_thread = None

        self.lock_sending_queue = threading.RLock()
        self.sending_queue = []

        self.lock_realtime_queue = threading.RLock()
        self.realtime_queue = []

        self.commands_in_device_buffer = []
        self.buffer_mode = 1  # 1:1 okay, send lines.
        self.buffered_characters = 0
        self.device_buffer_size = self.service.planning_buffer_size
        self.old_x = 0
        self.old_y = 0
        self.grbl_settings = {
            0: 10,  # step pulse microseconds
            1: 25,  # step idle delay
            2: 0,  # step pulse invert
            3: 0,  # step direction invert
            4: 0,  # invert step enable pin, boolean
            5: 0,  # invert limit pins, boolean
            6: 0,  # invert probe pin
            10: 255,  # status report options
            11: 0.010,  # Junction deviation, mm
            12: 0.002,  # arc tolerance, mm
            13: 0,  # Report in inches
            20: 0,  # Soft limits enabled.
            21: 0,  # hard limits enabled
            22: 0,  # Homing cycle enable
            23: 0,  # Homing direction invert
            24: 25.000,  # Homing locate feed rate, mm/min
            25: 500.000,  # Homing search seek rate, mm/min
            26: 250,  # Homing switch debounce delay, ms
            27: 1.000,  # Homing switch pull-off distance, mm
            30: 1000,  # Maximum spindle speed, RPM
            31: 0,  # Minimum spindle speed, RPM
            32: 1,  # Laser mode enable, boolean
            100: 250.000,  # X-axis steps per millimeter
            101: 250.000,  # Y-axis steps per millimeter
            102: 250.000,  # Z-axis steps per millimeter
            110: 500.000,  # X-axis max rate mm/min
            111: 500.000,  # Y-axis max rate mm/min
            112: 500.000,  # Z-axis max rate mm/min
            120: 10.000,  # X-axis acceleration, mm/s^2
            121: 10.000,  # Y-axis acceleration, mm/s^2
            122: 10.000,  # Z-axis acceleration, mm/s^2
            130: 200.000,  # X-axis max travel mm.
            131: 200.000,  # Y-axis max travel mm
            132: 200.000,  # Z-axis max travel mm.
        }

    def open(self):
        if self.connection.connected:
            return
        self.connection.connect()
        if not self.connection.connected:
            self.channel("Could not connect.")
            return
        self.channel("Connecting to GRBL...")
        while True:
            response = self.connection.read()
            if response is None:
                continue
            self.channel(response)
            self.recv(response)
            if not response:
                time.sleep(0.1)
            if "grbl" in response.lower():
                self.channel("GRBL Connection Established.")
                return
            if "marlin" in response.lower():
                self.channel("Marlin Connection Established.")
                return

    def close(self):
        if self.connection.connected:
            self.connection.disconnect()

    def write(self, data):
        self.start()
        self.service.signal("serial;write", data)
        with self.lock_sending_queue:
            self.sending_queue.append(data)
            self.service.signal(
                "serial;buffer", len(self.sending_queue) + len(self.realtime_queue)
            )

    def realtime(self, data):
        self.start()
        self.service.signal("serial;write", data)
        with self.lock_realtime_queue:
            self.realtime_queue.append(data)
            if "\x18" in data:
                self.sending_queue.clear()
            self.service.signal(
                "serial;buffer", len(self.sending_queue) + len(self.realtime_queue)
            )

    def start(self):
        self.open()
        if self.sending_thread is None:
            self.sending_thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.com_port.lower()}",
                result=self.stop,
                daemon=True,
            )

    def stop(self, *args):
        self.sending_thread = None
        self.close()

    def _sending(self):
        while self.connection.connected:
            write = 0
            while len(self.realtime_queue):
                line = self.realtime_queue[0]
                self.connection.write(line)
                self.send(line)
                self.realtime_queue.pop(0)
                write += 1

            if len(self.sending_queue):
                if len(self.commands_in_device_buffer) <= 1:
                    line = self.sending_queue[0]
                    line_length = len(line)
                    buffer_remaining = (
                        self.device_buffer_size - self.buffered_characters
                    )
                    if buffer_remaining > line_length:
                        if line.startswith("G0 ") or line.startswith("G1 "):
                            cline = line.split()
                            try:
                                xx = float(cline[1][1:])
                            except (ValueError, IndexError):
                                xx = 0
                            try:
                                yy = float(cline[2][1:])
                            except (ValueError, IndexError):
                                yy = 0
                            new_x, new_y = self.service.device_to_scene_position(
                                xx * self.driver.unit_scale, yy * self.driver.unit_scale
                            )
                            # print(f"{cline} -> {xx}, {yy} -> {new_x}, {new_y}")
                            self.service.signal(
                                "driver;position",
                                (self.old_x, self.old_y, new_x, new_y),
                            )
                            self.old_x = new_x
                            self.old_y = new_y
                        elif line.startswith("G28"):
                            # home
                            new_x = self.driver.origin_x
                            new_y = self.driver.origin_y
                            self.service.signal(
                                "driver;position",
                                (self.old_x, self.old_y, new_x, new_y),
                            )
                            self.old_x = new_x
                            self.old_y = new_y
                        self.connection.write(line)
                        self.send(line)
                        self.commands_in_device_buffer.append(line)
                        self.buffered_characters = line_length
                        self.service.signal("serial;buffer", len(self.sending_queue))
                        self.sending_queue.pop(0)
                        write += 1
            read = 0
            while self.connection.connected:
                response = self.connection.read()
                if not response:
                    break
                self.service.signal("serial;response", response)
                self.recv(response)
                if response == "ok":
                    try:
                        line = self.commands_in_device_buffer.pop(0)
                        self.buffered_characters -= len(line)
                    except IndexError:
                        self.channel(f"Response: {response}, but this was unexpected")
                        continue
                    self.channel(f"Response: {response}")
                if response.startswith("echo:"):
                    self.service.channel("console")(response[5:])
                if response.startswith("ALARM"):
                    self.service.signal("warning", f"GRBL: {response}", response, 4)
                if response.startswith("error"):
                    self.channel(f"ERROR: {response}")
                else:
                    self.channel(f"Data: {response}")
                read += 1
            if read == 0 and write == 0:
                time.sleep(0.05)
                self.service.signal("pipe;running", False)
            else:
                self.service.signal("pipe;running", True)

    def __repr__(self):
        return f"GRBLSerial('{self.service.com_port}:{str(self.service.serial_baud_rate)}')"

    def __len__(self):
        return len(self.sending_queue) + len(self.realtime_queue)


class SerialConnection:
    def __init__(self, service):
        self.service = service
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.laser = None
        self.read_buffer = bytearray()

    @property
    def connected(self):
        return self.laser is not None

    def read(self):
        try:
            if self.laser.in_waiting:
                self.read_buffer += self.laser.readall()
        except (SerialException, AttributeError, OSError):
            return None
        f = self.read_buffer.find(b"\n")
        if f == -1:
            return None
        response = self.read_buffer[:f]
        self.read_buffer = self.read_buffer[f + 1 :]
        str_response = str(response, "utf-8")
        str_response = str_response.strip()
        return str_response

    def write(self, line):
        self.laser.write(bytes(line, "utf-8"))

    def connect(self):
        if self.laser:
            self.channel("Already connected")
            return

        try:
            self.channel("Attempting to Connect...")
            com_port = self.service.com_port
            baud_rate = self.service.baud_rate
            self.laser = serial.Serial(
                com_port,
                baud_rate,
                timeout=0,
            )
            self.channel("Connected")
            self.service.signal("serial;status", "connected")
        except ConnectionError:
            self.channel("Connection Failed.")
        except SerialException:
            self.channel("Serial connection could not be established.")

    def disconnect(self):
        self.channel("Disconnected")
        if self.laser:
            self.laser.close()
            del self.laser
            self.laser = None
        self.service.signal("serial;status", "disconnected")


class MockConnection:
    def __init__(self, service):
        self.service = service
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.laser = None
        self.read_buffer = bytearray()
        self.just_connected = False
        self.write_lines = 0

    @property
    def connected(self):
        return self.laser is not None

    def read(self):
        if self.just_connected:
            self.just_connected = False
            return "grbl version fake"
        if self.write_lines:
            time.sleep(0.01)  # takes some time
            self.write_lines -= 1
            return "ok"
        else:
            return ""

    def write(self, line):
        self.write_lines += 1

    def connect(self):
        if self.laser:
            self.channel("Already connected")
            return
        try:
            self.channel("Attempting to Connect...")
            self.laser = True
            self.just_connected = True
            self.channel("Connected")
            self.service.signal("serial;status", "connected")
        except ConnectionError:
            self.channel("Connection Failed.")
        except SerialException:
            self.channel("Serial connection could not be established.")

    def disconnect(self):
        self.channel("Disconnected")
        self.service.signal("serial;status", "disconnected")


class TCPOutput:
    def __init__(self, context):
        super().__init__()
        self.service = context
        self._stream = None

        self.lock = threading.RLock()
        self.buffer = bytearray()
        self.thread = None

    def connect(self):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.service.address, self.service.port))
            self.service.signal("tcp;status", "connected")
        except (ConnectionError, TimeoutError):
            self.disconnect()

    def disconnect(self):
        self.service.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.service.signal("tcp;write", data)
        if isinstance(data, str):
            data = bytes(data, "utf-8")
        with self.lock:
            self.buffer += data
            self.service.signal("tcp;buffer", len(self.buffer))
        self._start()

    realtime_write = write

    def _start(self):
        if self.thread is None:
            self.thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.service.port}",
                result=self._stop,
            )

    def _stop(self, *args):
        self.thread = None

    def _sending(self):
        tries = 0
        while True:
            try:
                if len(self.buffer):
                    if self._stream is None:
                        self.connect()
                        if self._stream is None:
                            return
                    with self.lock:
                        sent = self._stream.send(self.buffer)
                        del self.buffer[:sent]
                        self.service.signal("tcp;buffer", len(self.buffer))
                    tries = 0
                else:
                    tries += 1
                    time.sleep(0.1)
            except (ConnectionError, OSError):
                tries += 1
                self.disconnect()
                time.sleep(0.05)
            if tries >= 20:
                with self.lock:
                    if len(self.buffer) == 0:
                        break

    def __repr__(self):
        return f"TCPOutput('{self.service.address}:{self.service.port}')"

    def __len__(self):
        return len(self.buffer)
