import serial
import os
import re
import socket
import threading
import time

from serial import SerialException

from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner
from ..core.spoolers import Spooler
from ..core.units import UNITS_PER_INCH, UNITS_PER_MM, ViewPort, UNITS_PER_MIL
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
    PLOT_LEFT_UPPER,
    PLOT_RAPID,
    PLOT_RIGHT_LOWER,
    PLOT_SETTING,
    PLOT_START,
)
from ..kernel import Module, Service

STATE_ABORT = -1
STATE_DEFAULT = 0
STATE_CONCAT = 1
STATE_COMPACT = 2

"""
GRBL device.
"""

GRBL_SET_RE = re.compile(r"\$(\d+)=([-+]?[0-9]*\.?[0-9]*)")
CODE_RE = re.compile(r"([A-Za-z])")
FLOAT_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]*")


def _tokenize_code(code_line):
    pos = code_line.find("(")
    while pos != -1:
        end = code_line.find(")")
        yield ["comment", code_line[pos + 1 : end]]
        code_line = code_line[:pos] + code_line[end + 1 :]
        pos = code_line.find("(")
    pos = code_line.find(";")
    if pos != -1:
        yield ["comment", code_line[pos + 1 :]]
        code_line = code_line[:pos]

    code = None
    for x in CODE_RE.split(code_line):
        x = x.strip()
        if len(x) == 0:
            continue
        if len(x) == 1 and x.isalpha():
            if code is not None:
                yield code
            code = [x.lower()]
            continue
        if code is not None:
            code.extend([float(v) for v in FLOAT_RE.findall(x) if len(v) != 0])
            yield code
        code = None
    if code is not None:
        yield code


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("provider/device/grbl", GRBLDevice)

        _ = kernel.translation
        kernel.register("driver/grbl", GRBLDriver)
        kernel.register("load/GCodeLoader", GCodeLoader)

        @kernel.console_option(
            "grbl", type=int, help=_("run grbl-emulator on given port.")
        )
        @kernel.console_option(
            "flip_x", "X", type=bool, action="store_true", help=_("grbl x-flip")
        )
        @kernel.console_option(
            "flip_y", "Y", type=bool, action="store_true", help=_("grbl y-flip")
        )
        @kernel.console_option(
            "adjust_x", "x", type=int, help=_("adjust grbl home_x position")
        )
        @kernel.console_option(
            "adjust_y", "y", type=int, help=_("adjust grbl home_y position")
        )
        @kernel.console_option(
            "port", "p", type=int, default=23, help=_("port to listen on.")
        )
        @kernel.console_option(
            "silent",
            "s",
            type=bool,
            action="store_true",
            help=_("do not watch server channels"),
        )
        @kernel.console_option(
            "watch", "w", type=bool, action="store_true", help=_("watch send/recv data")
        )
        @kernel.console_option(
            "quit",
            "q",
            type=bool,
            action="store_true",
            help=_("shutdown current grblserver"),
        )
        @kernel.console_command("grblserver", help=_("activate the grblserver."))
        def grblserver(
            command,
            channel,
            _,
            port=23,
            path=None,
            flip_x=False,
            flip_y=False,
            adjust_x=0,
            adjust_y=0,
            silent=False,
            watch=False,
            quit=False,
            **kwargs
        ):
            ctx = kernel.get_context(path if path is not None else "/")
            if ctx is None:
                return
            _ = kernel.translation
            try:
                server = ctx.open_as("module/TCPServer", "grbl", port=port)
                emulator = ctx.open("emulator/grbl")
                if quit:
                    ctx.close("grbl")
                    ctx.close("emulator/grbl")
                    return
                ctx.channel("grbl/send").greet = "Grbl 1.1e ['$' for help]\r\n"
                channel(_("GRBL Mode."))
                if not silent:
                    console = kernel.channel("console")
                    ctx.channel("grbl").watch(console)
                    server.events_channel.watch(console)
                    if watch:
                        server.events_channel.watch(console)

                emulator.flip_x = flip_x
                emulator.flip_y = flip_y
                emulator.home_adjust = (adjust_x, adjust_y)

                ctx.channel("grbl/recv").watch(emulator.write)
                emulator.recv = ctx.channel("grbl/send")
                channel(_("TCP Server for GRBL Emulator on port: %d" % port))
            except OSError:
                channel(_("Server failed on port: %d") % port)
            return

    if lifecycle == "preboot":
        suffix = "grbl"
        for d in kernel.derivable(suffix):
            kernel.root(
                "service device start -p {path} {suffix}\n".format(
                    path=d, suffix=suffix
                )
            )


class GRBLDevice(Service, ViewPort):
    """
    GRBLDevice is driver for the Gcode Controllers
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "GRBLDevice"

        self.setting(str, "label", path)
        _ = self._
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "310mm",
                "type": str,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "210mm",
                "type": str,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
            },
            {
                "attr": "scale_x",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("X Scale Factor"),
                "tip": _(
                    "Scale factor for the X-axis. Board units to actual physical units."
                ),
            },
            {
                "attr": "scale_y",
                "object": self,
                "default": 1.000,
                "type": float,
                "label": _("Y Scale Factor"),
                "tip": _(
                    "Scale factor for the Y-axis. Board units to actual physical units."
                ),
            },
        ]
        self.register_choices("bed_dim", choices)
        ViewPort.__init__(self, 0, 0, self.bedwidth, self.bedheight)
        self.settings = dict()
        self.state = 0

        self.setting(int, "connection", 1)

        self.setting(str, "com_port", 'COM8')
        self.setting(int, "baud_rate", 115200)

        self.setting(int, "port", 23)
        self.setting(str, "address", "localhost")

        self.setting(str, "line_end", "\n")

        self.driver = GRBLDriver(self)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)

        self.viewbuffer = ""

        _ = self.kernel.translation

        @self.console_command(
            "spool",
            help=_("spool <command>"),
            regex=True,
            input_type=(None, "plan", "device"),
            output_type="spooler",
        )
        def spool(command, channel, _, data=None, remainder=None, **kwgs):
            spooler = self.spooler
            if data is not None:
                # If plan data is in data, then we copy that and move on to next step.
                spooler.jobs(data.plan)
                channel(_("Spooled Plan."))
                self.signal("plan", data.name, 6)

            if remainder is None:
                channel(_("----------"))
                channel(_("Spoolers:"))
                for d, d_name in enumerate(self.match("device", suffix=True)):
                    channel("%d: %s" % (d, d_name))
                channel(_("----------"))
                channel(_("Spooler on device %s:" % str(self.label)))
                for s, op_name in enumerate(spooler.queue):
                    channel("%d: %s" % (s, op_name))
                channel(_("----------"))
            return "spooler", spooler

        @self.console_argument("com")
        @self.console_option("baud", "b")
        @self.console_command(
            "serial",
            help=_("link the serial connection"),
            input_type=None,
        )
        def serial_connection(command, channel, _, data=None, com=None, baud=115200, remainder=None, **kwgs):
            if com is None:
                import serial.tools.list_ports

                ports = serial.tools.list_ports.comports()

                channel("Available COM ports")
                for x in ports:
                    channel(x.description)
            else:
                connection = GrblSerialController(self, com.upper(), baud)
                self.channel("grbl").watch(connection.write)

        @self.console_command(
            "gcode",
            help=_("Send raw gcode to the device"),
            input_type=None,
        )
        def gcode(command, channel, _, data=None, remainder=None, **kwgs):
            if remainder is not None:
                channel(remainder)
                self.channel("grbl")(remainder + self.line_end)

    @property
    def current_x(self):
        """
        @return: the location in nm for the current known x value.
        """
        return float(self.driver.native_x * self.driver.stepper_step_size) / self.scale_x

    @property
    def current_y(self):
        """
        @return: the location in nm for the current known y value.
        """
        return float(self.driver.native_y * self.driver.stepper_step_size) / self.scale_y

    @property
    def get_native_scale_x(self):
        return self.scale_x / float(self.driver.stepper_step_size)

    @property
    def get_native_scale_y(self):
        return self.scale_y / float(self.driver.stepper_step_size)


class GRBLDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.name = str(service)
        self.hold = False
        self.paused = False
        self.native_x = 0
        self.native_y = 0
        self.stepper_step_size = UNITS_PER_MIL

        self.plot_planner = PlotPlanner(self.settings)
        self.plot_data = None

        self.power_dirty = True
        self.speed_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True

        self._absolute = True
        self.feed_mode = None
        self.feed_convert = None
        self.feed_invert = None
        self.g94_feedrate()  # G94 DEFAULT, mm mode

        self.unit_scale = None
        self.units = None
        self.g21_units_mm()
        self.g91_absolute()

        self.grbl = self.service.channel("grbl", line_end=self.service.line_end)
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
        self.home_adjust = None

        self.flip_x = 1  # Assumes the GCode is flip_x, -1 is flip, 1 is normal
        self.flip_y = 1  # Assumes the Gcode is flip_y,  -1 is flip, 1 is normal
        self.move_mode = 0
        self.buffer = ""
        self.reply = None
        self.elements = None

    def __repr__(self):
        return "GRBLDriver(%s)" % self.name

    def hold_work(self):
        """
        Required.

        Spooler check. to see if the work cycle should be held.

        @return: hold?
        """
        return self.hold or self.paused

    def hold_idle(self):
        """
        Required.

        Spooler check. Should the idle job be processed or held.
        @return:
        """
        return False

    def move(self, x, y, absolute=False):
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
        line.append("X%f" % x)
        line.append("Y%f" % y)
        if self.power_dirty:
            if self.power is not None:
                line.append("S%f" % self.power)
            self.power_dirty = False
        if self.speed_dirty:
            line.append("F%f" % self.feed_convert(self.speed))
            self.speed_dirty = False
        self.grbl(" ".join(line))

    def move_abs(self, x, y):
        # TODO: Should use $J syntax
        self.g91_absolute()
        self.clean()
        old_current_x = self.service.current_x
        old_current_y = self.service.current_y

        x = self.service.length(x, 0)
        y = self.service.length(y, 1)
        x = self.service.scale_x * x / self.stepper_step_size
        y = self.service.scale_y * y / self.stepper_step_size
        self.rapid_mode()
        self.move(x, y)
        new_current_x = self.service.current_x
        new_current_y = self.service.current_y
        self.service.signal(
            "driver;position",
            (old_current_x, old_current_y, new_current_x, new_current_y),
        )

    def move_rel(self, dx, dy):
        # TODO: Should use $J syntax
        self.g90_relative()
        self.clean()
        old_current_x = self.service.current_x
        old_current_y = self.service.current_y

        dx = self.service.length(dx, 0)
        dy = self.service.length(dy, 1)
        dx = self.service.scale_x * dx / self.stepper_step_size
        dy = self.service.scale_y * dy / self.stepper_step_size
        self.rapid_mode()
        self.move(dx, dy)

        new_current_x = self.service.current_x
        new_current_y = self.service.current_y
        self.service.signal(
            "driver;position",
            (old_current_x, old_current_y, new_current_x, new_current_y),
        )

    def clean(self):
        if self.absolute_dirty:
            if self._absolute:
                self.grbl("G90")
            else:
                self.grbl("G91")
        self.absolute_dirty = False

        if self.feedrate_dirty:
            if self.feed_mode == 94:
                self.grbl("G94")
            else:
                self.grbl("G93")
        self.feedrate_dirty = False

        if self.units_dirty:
            if self.units == 20:
                self.grbl("G20")
            else:
                self.grbl("G21")
        self.units_dirty = False

    def g90_relative(self):
        if not self._absolute:
            return
        self._absolute = False
        self.absolute_dirty = True

    def g91_absolute(self):
        if self._absolute:
            return
        self._absolute = True
        self.absolute_dirty = True

    def g93_feedrate(self):
        if self.feed_mode == 93:
            return
        self.feed_mode = 93
        # Feed Rate in Minutes / Unit
        self.feed_convert = lambda s: (60.0 / s) * self.stepper_step_size / UNITS_PER_MM
        self.feed_invert = lambda s: (60.0 / s) * UNITS_PER_MM / self.stepper_step_size
        self.feedrate_dirty = True

    def g94_feedrate(self):
        if self.feed_mode == 94:
            return
        self.feed_mode = 94
        # Feed Rate in Units / Minute
        self.feed_convert = lambda s: s / ((self.stepper_step_size / UNITS_PER_MM) * 60.0)
        self.feed_invert = lambda s: s * ((self.stepper_step_size / UNITS_PER_MM) * 60.0)
        # units to mm, seconds to minutes.
        self.feedrate_dirty = True

    def g20_units_inch(self):
        self.units = 20
        self.unit_scale = UNITS_PER_INCH / self.stepper_step_size   # g20 is inch mode.
        self.units_dirty = True

    def g21_units_mm(self):
        self.units = 21
        self.unit_scale = UNITS_PER_MM / self.stepper_step_size  # g21 is mm mode.
        self.units_dirty = True

    def dwell(self, time_in_ms):
        self.laser_on()  # This can't be sent early since these are timed operations.
        self.wait(time_in_ms / 1000.0)
        self.laser_off()

    def laser_off(self, *values):
        """
        Turn laser off in place.

        @param values:
        @return:
        """
        self.grbl("M3")

    def laser_on(self, *values):
        """
        Turn laser on in place.

        @param values:
        @return:
        """
        self.grbl("M5")

    def plot(self, plot):
        """
        Gives the driver a bit of cutcode that should be plotted.
        @param plot:
        @return:
        """
        self.plot_planner.push(plot)

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        if self.plot_data is None:
            self.plot_data = self.plot_planner.gen()
        self.g91_absolute()
        self.g94_feedrate()
        self.clean()
        for x, y, on in self.plot_data:
            while self.hold_work():
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
                            or p_set.raster_step != self.raster_step
                    ):
                        self.set("speed", p_set.speed)
                    self.settings.update(p_set.settings)
                elif on & (
                        PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    self.move_mode = 0
                    self.move(x, y)
                continue
            if on == 0:
                self.move_mode = 0
            else:
                self.move_mode = 1
            self.move(x, y)
        self.plot_data = None
        return False

    def blob(self, data_type, data):
        """
        @param type:
        @param data:
        @return:
        """
        if data_type != "gcode":
            return
        for line in data:
            self.process_line(line)

    def home(self, *values):
        """
        Home the laser.

        @param values:
        @return:
        """
        self.grbl("$H")

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
        self.grbl("M5")

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands.
        @param values:
        @return:
        """
        self.grbl("M3")

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

    def set_position(self, x, y):
        """
        This should set an offset position.
        * Note: This may need to be replaced with something that has better concepts behind it. Currently this is only
        used in step-repeat.

        @param x:
        @param y:
        @return:
        """
        self.native_x = x
        self.native_y = y

    def wait(self, t):
        """
        Wait asks that the work be stalled or current process held for the time t in seconds. If wait_finished is
        called first this should pause the machine without current work acting as a dwell.

        @param t:
        @return:
        """
        self.write("G04 S{time}".format(time=t))

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

    def signal(self, signal, *args):
        """
        This asks that this signal be broadcast.

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
        self.grbl("!")

    def resume(self, *args):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser.

        @param args:
        @return:
        """
        self.paused = False
        self.grbl("~")

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.
        Asks that the device resets, and clears all current work.

        @param args:
        @return:
        """
        self.grbl("\x18")

    def status(self):
        """
        Asks that this device status be updated.

        @return:
        """
        self.grbl("?")

        parts = list()
        parts.append("x=%f" % self.native_x)
        parts.append("y=%f" % self.native_y)
        parts.append("speed=%f" % self.settings.get("speed", 0.0))
        parts.append("power=%d" % self.settings.get("power", 0))
        status = ";".join(parts)
        self.service.signal("driver;status", status)

    ####################
    # EMULATION CODE
    # This code isn't currently used.
    ####################

    def grbl_write(self, data):
        if self.grbl_channel is not None:
            self.grbl_channel(data)
        if self.reply is not None:
            self.reply(data)

    def realtime_write(self, bytes_to_write):
        device = self.device
        if bytes_to_write == "?":  # Status report
            # Idle, Run, Hold, Jog, Alarm, Door, Check, Home, Sleep
            if device.state == 0:
                state = "Idle"
            else:
                state = "Busy"
            x = device.current_x / self.stepper_step_size
            y = device.current_y / self.stepper_step_size
            z = 0.0
            parts = list()
            parts.append(state)
            parts.append("MPos:%f,%f,%f" % (x, y, z))
            speed = device.settings.speed
            if speed is None:
                speed = 30.0
            f = self.feed_invert(speed)
            power = device.settings.power
            if power is None:
                power = 1000
            s = power
            parts.append("FS:%f,%d" % (f, s))
            self.grbl_write("<%s>\r\n" % "|".join(parts))
        elif bytes_to_write == "~":  # Resume.
            self.context("resume\n")
        elif bytes_to_write == "!":  # Pause.
            self.context("pause\n")
        elif bytes_to_write == "\x18":  # Soft reset.
            self.context("estop\n")

    def write2(self, data):
        if isinstance(data, bytes):
            data = data.decode()
        if "?" in data:
            data = data.replace("?", "")
            self.realtime_write("?")
        if "~" in data:
            data = data.replace("$", "")
            self.realtime_write("~")
        if "!" in data:
            data = data.replace("!", "")
            self.realtime_write("!")
        if "\x18" in data:
            data = data.replace("\x18", "")
            self.realtime_write("\x18")
        self.buffer += data
        while "\b" in self.buffer:
            self.buffer = re.sub(".\b", "", self.buffer, count=1)
            if self.buffer.startswith("\b"):
                self.buffer = re.sub("\b+", "", self.buffer)

        while "\n" in self.buffer:
            pos = self.buffer.find("\n")
            command = self.buffer[0:pos].strip("\r")
            self.buffer = self.buffer[pos + 1 :]
            cmd = self.process_line(command)
            if cmd == 0:  # Execute GCode.
                self.grbl_write("ok\r\n")
            else:
                self.grbl_write("error:%d\r\n" % cmd)

    def process_line(self, data):
        if data.startswith("$"):
            if data == "$":
                self.grbl_write(
                    "[HLP:$$ $# $G $I $N $x=val $Nx=line $J=line $SLP $C $X $H ~ ! ? ctrl-x]\r\n"
                )
                return 0
            elif data == "$$":
                for s in self.settings:
                    v = self.settings[s]
                    if isinstance(v, int):
                        self.grbl_write("$%d=%d\r\n" % (s, v))
                    elif isinstance(v, float):
                        self.grbl_write("$%d=%.3f\r\n" % (s, v))
                return 0
            if GRBL_SET_RE.match(data):
                settings = list(GRBL_SET_RE.findall(data))[0]
                print(settings)
                try:
                    c = self.settings[int(settings[0])]
                except KeyError:
                    return 3
                if isinstance(c, float):
                    self.settings[int(settings[0])] = float(settings[1])
                else:
                    self.settings[int(settings[0])] = int(settings[1])
                return 0
            elif data == "$I":
                pass
            elif data == "$G":
                pass
            elif data == "$N":
                pass
            elif data == "$H":
                self.spooler.job("home")
                if self.home_adjust is not None:
                    self.spooler.job("rapid_mode")
                    self.spooler.job(
                        "move", self.home_adjust[0], self.home_adjust[1]
                    )
                return 0
                # return 5  # Homing cycle not enabled by settings.
            return 3  # GRBL '$' system command was not recognized or supported.
        if data.startswith("cat"):
            return 2
        commands = {}
        for c in _tokenize_code(data):
            g = c[0]
            if g not in commands:
                commands[g] = []
            if len(c) >= 2:
                commands[g].append(c[1])
            else:
                commands[g].append(None)
        return self._process_commands(commands)

    def _process_commands(self, gc):
        """
        Process parsed gcode commands.

        @param gc:
        @return:
        """
        if "m" in gc:
            for v in gc["m"]:
                if v == 0 or v == 1:
                    yield "rapid_mode"
                    yield "wait_finish"
                elif v == 2:
                    return
                elif v == 30:
                    return
                elif v == 3 or v == 4:
                    on_mode = True
                elif v == 5:
                    on_mode = False
                    yield "laser_off"
                elif v == 7:
                    #  Coolant control.
                    pass
                elif v == 8:
                    yield "signal", ("coolant", True)
                elif v == 9:
                    yield "signal", ("coolant", False)
                elif v == 56:
                    pass  # Parking motion override control.
                elif v == 911:
                    pass  # Set TMC2130 holding currents
                elif v == 912:
                    pass  # M912: Set TMC2130 running currents
                else:
                    return 20
            del gc["m"]
        if "g" in gc:
            for v in gc["g"]:
                if v is None:
                    return 2
                elif v == 0.0:
                    move_mode = 0
                elif v == 1.0:
                    move_mode = 1
                elif v == 2.0:  # CW_ARC
                    move_mode = 2
                elif v == 3.0:  # CCW_ARC
                    move_mode = 3
                elif v == 4.0:  # DWELL
                    t = 0
                    if "p" in gc:
                        t = float(gc["p"].pop()) / 1000.0
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    if "s" in gc:
                        t = float(gc["s"].pop())
                        if len(gc["s"]) == 0:
                            del gc["s"]
                    yield "rapid_mode"
                    yield "wait", t
                elif v == 10.0:
                    if "l" in gc:
                        l = float(gc["l"].pop(0))
                        if len(gc["l"]) == 0:
                            del gc["l"]
                        if l == 2.0:
                            pass
                        elif l == 20:
                            pass
                elif v == 17:
                    pass  # Set XY coords.
                elif v == 18:
                    return 2  # Set the XZ plane for arc.
                elif v == 19:
                    return 2  # Set the YZ plane for arc.
                elif v == 20.0 or v == 70.0:
                    scale = UNITS_PER_INCH  # g20 is inch mode.
                elif v == 21.0 or v == 71.0:
                    scale = UNITS_PER_MM  # g21 is mm mode.
                elif v == 28.0:
                    yield "rapid_mode"
                    yield "home"
                    if home_adjust is not None:
                        yield "move_abs", home_adjust[0], home_adjust[1]
                    if home is not None:
                        yield "move", home
                elif v == 28.1:
                    if "x" in gc and "y" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        home = (x, y)
                elif v == 28.2:
                    # Run homing cycle.
                    yield "rapid_mode"
                    yield "home"
                    if home_adjust is not None:
                        yield "move_abs", home_adjust[0], home_adjust[1]
                elif v == 28.3:
                    yield "rapid_mode"
                    yield "home"
                    if home_adjust is not None:
                        yield "move", home_adjust[0], home_adjust[1]
                    if "x" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        if x is None:
                            x = 0
                        yield "move", x, 0
                    if "y" in gc:
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if y is None:
                            y = 0
                        yield "move", 0, y
                elif v == 30.0:
                    # Goto predefined position. Return to secondary home position.
                    if "p" in gc:
                        p = float(gc["p"].pop(0))
                        if len(gc["p"]) == 0:
                            del gc["p"]
                    else:
                        p = None
                    yield "rapid_mode"
                    yield "home"
                    if home_adjust is not None:
                        yield "move", home_adjust[0], home_adjust[1]
                    if home2 is not None:
                        yield "move", home2
                elif v == 30.1:
                    # Stores the current absolute position.
                    if "x" in gc and "y" in gc:
                        x = gc["x"].pop(0)
                        if len(gc["x"]) == 0:
                            del gc["x"]
                        y = gc["y"].pop(0)
                        if len(gc["y"]) == 0:
                            del gc["y"]
                        if x is None:
                            x = 0
                        if y is None:
                            y = 0
                        home2 = (x, y)
                elif v == 38.1:
                    # Touch Plate
                    pass
                elif v == 38.2:
                    # Straight Probe
                    pass
                elif v == 38.3:
                    # Prope towards workpiece
                    pass
                elif v == 38.4:
                    # Probe away from workpiece, signal error
                    pass
                elif v == 38.5:
                    # Probe away from workpiece.
                    pass
                elif v == 40.0:
                    pass  # Compensation Off
                elif v == 43.1:
                    pass  # Dynamic tool Length offsets
                elif v == 49:
                    # Cancel tool offset.
                    pass  # Dynamic tool length offsets
                elif v == 53:
                    pass  # Move in Absolute Coordinates
                elif 54 <= v <= 59:
                    # Fixture offset 1-6, G10 and G92
                    system = v - 54
                    pass  # Work Coordinate Systems
                elif v == 61:
                    # Exact path control mode. GRBL required
                    pass
                elif v == 80:
                    # Motion mode cancel. Canned cycle.
                    pass
                elif v == 90.0:
                    yield "set", "relative", False
                elif v == 91.0:
                    yield "set", "relative", True
                elif v == 91.1:
                    # Offset mode for certain cam. Incremental distance mode for arcs.
                    pass  # ARC IJK Distance Modes # TODO Implement
                elif v == 92:
                    # Change the current coords without moving.
                    pass  # Coordinate Offset TODO: Implement
                elif v == 92.1:
                    # Clear Coordinate offset set by 92.
                    pass  # Clear Coordinate offset TODO: Implement
                elif v == 93.0:
                    feed_convert, feed_invert = g93_feed_convert, g93_feed_invert
                elif v == 94.0:
                    feed_convert, feed_invert = g94_feed_convert, g94_feed_invert
                else:
                    return 20  # Unsupported or invalid g-code command found in block.
            del gc["g"]
        if "comment" in gc:
            del gc["comment"]
        if "f" in gc:  # Feed_rate
            for v in gc["f"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                feed_rate = feed_convert(v)
                if speed != feed_rate:
                    speed = feed_rate
            del gc["f"]
        if "s" in gc:
            for v in gc["s"]:
                if v is None:
                    return 2  # Numeric value format is not valid or missing an expected value.
                if 0.0 < v <= 1.0:
                    v *= 1000  # numbers between 0-1 are taken to be in range 0-1.
                power = v
                yield "set", "power", v

            del gc["s"]
        if "x" in gc or "y" in gc:
            if "x" in gc:
                x = gc["x"].pop(0)
                if x is None:
                    x = 0
                else:
                    x *= scale * flip_x
                if len(gc["x"]) == 0:
                    del gc["x"]
            else:
                x = 0
            if "y" in gc:
                y = gc["y"].pop(0)
                if y is None:
                    y = 0
                else:
                    y *= scale * flip_y
                if len(gc["y"]) == 0:
                    del gc["y"]
            else:
                y = 0
            if move_mode == 0:
                yield "program_mode"
                yield "move", x, y
            elif move_mode >= 1:
                yield "program_mode"
                if power == 0:
                    yield "move", x, y
                else:
                    if used_speed != speed:
                        yield "set", "speed", speed
                        used_speed = speed
                    yield "cut", x, y
                # TODO: Implement CW_ARC
                # TODO: Implement CCW_ARC
        return 0


class GrblSerialController:
    def __init__(self, context, com_port, baud_rate):
        self.service = context

        self.com_port = com_port
        self.baud_rate = baud_rate
        self.driver = self.service.driver
        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.send = self.service.channel("send-%s" % com_port.lower())
        self.recv = self.service.channel("recv-%s" % com_port.lower())
        self.laser = None

        self.write_buffer_lock = threading.RLock()
        self.buffer = []
        self.sending_thread = None
        # self.recving_thread = None
        self.buffer_mode = 0  # 1:1 okay, send lines.
        self.line_ok = 0
        self.line_buffer = 0
        self._start()

    def open(self):
        self._connect()
        if not self.laser:
            self.channel("Open Failed.")
            return
        self.channel("Connecting to GRBL...")
        try:
            while True:
                response = self.laser.readline()
                str_response = str(response, 'utf-8')
                self.channel(str_response)

                if "grbl" in str_response.lower() or "marlin" in str_response.lower():
                    self.channel("GRBL Connection Established.")
                    return True
        except TimeoutError:
            pass
        return False

    def close(self):
        if self.laser:
            self._disconnect()

    def _connect(self):
        if self.laser:
            self.channel("Already connected")
            return

        try:
            self.channel("Attempting to Connect...")
            self.laser = serial.Serial(
                self.com_port,
                self.baud_rate,
                timeout=5,
            )
            self.service.signal("serial;status", "connected")
            self.channel("Connected")
        except ConnectionError:
            self.channel("Connection Failed.")
        except SerialException:
            self.channel("Serial connection could not be established.")

    def _disconnect(self):
        self.channel("Disconnected")
        self.service.signal("serial;status", "disconnected")
        if self.laser:
            self.laser.close()

    def write(self, data):
        self.service.signal("serial;write", data)
        with self.write_buffer_lock:
            self.buffer.append(data)
            self.service.signal("serial;buffer", len(self.buffer))

    def _start(self):
        self.open()
        if self.sending_thread is None:
            self.sending_thread = self.service.threaded(
                self._sending,
                thread_name="sender-%s" % self.com_port.lower(),
                result=self._stop,
                daemon=True,
            )
        # if self.recving_thread is None:
        #     self.recving_thread = self.service.threaded(
        #         self._recving,
        #         thread_name="recver-%s" % self.com_port.lower(),
        #         result=self._stop,
        #     )

    def _stop(self, *args):
        self.sending_thread = None
        # self.recving_thread = None
        self.close()

    # def _recving(self):
    #     while self.laser is not None:
    #         try:
    #             response = self.laser.readline()
    #             str_response = str(response, 'utf-8')
    #             str_response = str_response.strip()
    #             self.service.signal("serial;response", str_response)
    #             self.recv(str_response)
    #             if str_response == "ok":
    #                 self.channel("Response: %s" % str_response)
    #             else:
    #                 self.channel("Response Not-Ok: %s" % str_response)
    #         except TimeoutError:
    #             # Loop again.
    #             continue

    def _sending(self):
        tries = 0
        while self.laser is not None:
            if len(self.buffer):
                with self.write_buffer_lock:
                    line = self.buffer[0]
                    self.laser.write(bytes(line, "utf-8"))
                    self.send(line)
                    self.service.signal("serial;buffer", len(self.buffer))

                    response = self.laser.readline()
                    str_response = str(response, 'utf-8')
                    str_response = str_response.strip()
                    self.service.signal("serial;response", str_response)
                    self.recv(str_response)
                    if str_response == "ok":
                        self.channel("Response: %s" % str_response)
                    else:
                        self.channel("Response Not-Ok: %s" % str_response)

                    self.buffer.pop(0)
                tries = 0
            else:
                tries += 1
                time.sleep(0.1)
            # if tries >= 20:
            #     with self.write_buffer_lock:
            #         if len(self.buffer) == 0:
            #             break

    def __repr__(self):
        return "GRBLSerial('%s:%s')" % (
            self.service.com_port,
            str(self.service.serial_baud_rate),
        )

    def __len__(self):
        return len(self.buffer)


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
        with self.lock:
            self.buffer += data
            self.service.signal("tcp;buffer", len(self.buffer))
        self._start()

    realtime_write = write

    def _start(self):
        if self.thread is None:
            self.thread = self.service.threaded(
                self._sending,
                thread_name="sender-%d" % self.service.port,
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
        return "TCPOutput('%s:%s')" % (
            self.service.address,
            self.service.port,
        )

    def __len__(self):
        return len(self.buffer)


class GcodeBlob(list):
    def __init__(self, cmds, name=None):
        super().__init__(cmds)
        self.name = name

    def __repr__(self):
        return "Gcode(%s, %d lines)" % (self.name, len(self))

    def as_svg(self):
        pass


class GCodeLoader:
    @staticmethod
    def load_types():
        yield "Gcode File", ("gcode", "nc", "gc"), "application/x-gcode"

    @staticmethod
    def load(kernel, elements_modifier, pathname, **kwargs):
        basename = os.path.basename(pathname)
        with open(pathname, "r") as f:
            grblemulator = GRBLEmulator(kernel.root, basename)
            grblemulator.elements = elements_modifier
            commandcode = GcodeBlob(get_command_code(f.readlines()), name=basename)
            elements_modifier.op_branch.add(commandcode, type="lasercode")
            kernel.root.close(basename)
        return True
