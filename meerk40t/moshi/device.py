import threading
import time

from meerk40t.kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
    Service,
)
from ..core.parameters import Parameters

from ..core.plotplanner import PlotPlanner
from ..core.spoolers import Spooler
from ..core.units import UNITS_PER_MIL, ViewPort
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
from .moshiblob import (
    MOSHI_EPILOGUE,
    MOSHI_ESTOP,
    MOSHI_FREEMOTOR,
    MOSHI_LASER,
    MOSHI_PROLOGUE,
    MOSHI_READ,
    MoshiBlob,
    swizzle_table,
)

STATUS_OK = 205  # Seen before file send. And after file send.
STATUS_PROCESSING = 207  # PROCESSING
STATUS_ERROR = 237  # ERROR
STATUS_RESET = 239  # Seen during reset


def plugin(kernel, lifecycle=None):
    if lifecycle == "plugins":
        from .gui import gui

        return [gui.plugin]

    if lifecycle == "register":
        kernel.register("provider/device/moshi", MoshiDevice)
    if lifecycle == "preboot":
        suffix = "moshi"
        for d in kernel.derivable(suffix):
            kernel.root(
                "service device start -p {path} {suffix}\n".format(
                    path=d, suffix=suffix
                )
            )


def get_code_string_from_moshicode(code):
    """
    Moshiboard CH341 codes into code strings.
    """
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_PROCESSING:
        return "Processing"
    elif code == STATUS_ERROR:
        return "Error"
    elif code == STATUS_RESET:
        return "Resetting"
    elif code == 0:
        return "USB Failed"
    else:
        return "UNK %02x" % code


class MoshiDevice(Service, ViewPort):
    """
    MoshiDevice is driver for the Moshiboard boards.
    """

    def __init__(self, kernel, path, *args, **kwargs):
        Service.__init__(self, kernel, path)
        self.name = "MoshiDevice"

        self.setting(bool, "opt_rapid_between", True)
        self.setting(int, "opt_jog_mode", 0)
        self.setting(int, "opt_jog_minimum", 256)

        self.setting(int, "usb_index", -1)
        self.setting(int, "usb_bus", -1)
        self.setting(int, "usb_address", -1)
        self.setting(int, "usb_version", -1)
        self.setting(bool, "mock", False)

        self.setting(bool, "home_right", False)
        self.setting(bool, "home_bottom", False)
        self.setting(str, "home_x", "0mm")
        self.setting(str, "home_y", "0mm")
        self.setting(bool, "enable_raster", True)

        self.setting(int, "packet_count", 0)
        self.setting(int, "rejected_count", 0)
        self.setting(str, "label", path)
        self.setting(int, "rapid_speed", 40)

        _ = self._
        choices = [
            {
                "attr": "bedwidth",
                "object": self,
                "default": "330mm",
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
        ViewPort.__init__(
            self,
            self.bedwidth,
            self.bedheight,
            user_scale_x=self.scale_x,
            user_scale_y=self.scale_y,
            native_scale_x=UNITS_PER_MIL,
            native_scale_y=UNITS_PER_MIL,
            # flip_x=self.flip_x,
            # flip_y=self.flip_y,
            # swap_xy=self.swap_xy,
            origin_x=1.0 if self.home_right else 0.0,
            origin_y=1.0 if self.home_bottom else 0.0,
        )

        self.state = 0

        self.driver = MoshiDriver(self)
        self.add_service_delegate(self.driver)

        self.controller = MoshiController(self)
        self.add_service_delegate(self.controller)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)

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

        @self.console_command("usb_connect", help=_("Connect USB"))
        def usb_connect(command, channel, _, **kwargs):
            """
            Force USB Connection Event for Moshiboard
            """
            try:
                self.controller.open()
            except ConnectionRefusedError:
                channel("Connection Refused.")

        @self.console_command("usb_disconnect", help=_("Disconnect USB"))
        def usb_disconnect(command, channel, _, **kwargs):
            """
            Force USB Disconnect Event for Moshiboard
            """
            try:
                self.controller.close()
            except ConnectionError:
                channel("Usb is not connected.")

        @self.console_command("start", help=_("Start Pipe to Controller"))
        def pipe_start(command, channel, _, data=None, **kwargs):
            """
            Start output sending.
            """
            self.controller.update_state(STATE_ACTIVE)
            self.controller.start()
            channel("Moshi Channel Started.")

        @self.console_command("hold", input_type="moshi", help=_("Hold Controller"))
        def pipe_pause(command, channel, _, **kwargs):
            """
            Pause output sending.
            """
            self.controller.update_state(STATE_PAUSE)
            self.controller.pause()
            channel(_("Moshi Channel Paused."))

        @self.console_command("resume", input_type="moshi", help=_("Resume Controller"))
        def pipe_resume(command, channel, _, **kwargs):
            """
            Resume output sending.
            """
            self.controller.update_state(STATE_ACTIVE)
            self.controller.start()
            channel(_("Moshi Channel Resumed."))

        @self.console_command(("estop", "abort"), help=_("Abort Job"))
        def pipe_abort(command, channel, _, **kwargs):
            """
            Abort output job. Usually due to the functionality of Moshiboards this will do
            nothing as the job will have already sent to the backend.
            """
            self.controller.estop()
            channel(_("Moshi Channel Aborted."))

        @self.console_command(
            "status",
            input_type="moshi",
            help=_("Update moshiboard controller status"),
        )
        def realtime_status(channel, _, **kwargs):
            """
            Updates the CH341 Status information for the Moshiboard.
            """
            try:
                self.controller.update_status()
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @self.console_command(
            "continue",
            help=_("abort waiting process on the controller."),
        )
        def realtime_pause(**kwargs):
            """
            Abort the waiting process for Moshiboard. This is usually a wait from BUSY (207) state until the board
            reports its status as READY (205)
            """
            self.controller.abort_waiting = True

    @property
    def viewbuffer(self):
        return self.controller.viewbuffer()

    @property
    def current(self):
        """
        @return: the location in units for the current known position.
        """
        return self.device_to_scene_position(self.driver.native_x, self.driver.native_y)


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
        self.plot_data = None

        self.program = MoshiBlob()

        self.is_paused = False
        self.hold = False
        self.paused = False

        self.service._buffer_size = 0

        self.preferred_offset_x = 0
        self.preferred_offset_y = 0

        name = self.service.label
        self.pipe_channel = service.channel("%s/events" % name)

    def __repr__(self):
        return "MoshiDriver(%s)" % self.name

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

    def laser_off(self, *values):
        """
        Turn laser off in place.

        @param values:
        @return:
        """
        pass

    def laser_on(self, *values):
        """
        Turn laser on in place.

        @param values:
        @return:
        """
        pass

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
        self.plotplanner_process()

    def move_abs(self, x, y):
        x, y = self.service.physical_to_device_position(x, y, 1)
        self.rapid_mode()
        self._move_absolute(int(x), int(y))

    def move_rel(self, dx, dy):
        dx, dy = self.service.physical_to_device_length(dx, dy, 1)
        self.rapid_mode()
        x = self.native_x + dx
        y = self.native_y + dy
        self._move_absolute(int(x), int(y))
        self.rapid_mode()

    def home(self, *values):
        """
        Send a home command to the device. In the case of Moshiboards this is merely a move to
        0,0 in absolute position.
        """
        adjust_x = self.service.home_x
        adjust_y = self.service.home_y
        try:
            adjust_x = values[0]
            adjust_y = values[1]
        except IndexError:
            pass
        adjust_x,  adjust_y = self.service.physical_to_device_position(adjust_x, adjust_y, 1)

        self.rapid_mode()
        self.speed = 40
        self.program_mode(adjust_x,  adjust_y, adjust_x,  adjust_y)
        self.rapid_mode()
        self.native_x = adjust_x
        self.native_y = adjust_y

    def unlock_rail(self):
        """
        Unlock the Rail or send a "FreeMotor" command.
        """
        self.rapid_mode()
        try:
            self.service.controller.unlock_rail()
        except AttributeError:
            pass

    def rapid_mode(self, *values):
        """
        Ensure the driver is currently in a default state. If we are not in a default state the driver
        should end the current program.
        """
        if self.state == DRIVER_STATE_RAPID:
            return

        if self.pipe_channel:
            self.pipe_channel("Rapid Mode")
        if self.state == DRIVER_STATE_FINISH:
            pass
        elif self.state in (
            DRIVER_STATE_PROGRAM,
            DRIVER_STATE_MODECHANGE,
            DRIVER_STATE_RASTER,
        ):
            self.program.termination()
            self.push_program()
        self.state = DRIVER_STATE_RAPID
        self.service.signal("driver;mode", self.state)

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
        self.start_program_mode(offset_x, offset_y, move_x, move_y)

    def start_program_mode(
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
        self.service.signal("driver;mode", self.state)

        self.program.move_abs(move_x, move_y)
        self.native_x = move_x
        self.native_y = move_y

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
        self.start_raster_mode(offset_x, offset_y, move_x, move_y)

    def start_raster_mode(
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
        self.service.signal("driver;mode", self.state)

        self.program.move_abs(move_x, move_y)
        self.native_x = move_x
        self.native_y = move_y

    def set(self, attribute, value):
        """
        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.
        @param key:
        @param value:
        @return:
        """
        if attribute == "power":
            self._set_power(value)
        if attribute == "ppi":
            self._set_power(value)
        if attribute == "pwm":
            self._set_power(value)
        if attribute == "overscan":
            self._set_overscan(value)
        if attribute == "speed":
            self._set_speed(value)
        if attribute == "step":
            self._set_step(value)

    def _set_power(self, power=1000.0):
        self.power = power
        if self.power > 1000.0:
            self.power = 1000.0
        if self.power <= 0:
            self.power = 0.0

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

    def set_position(self, x, y):
        """
        This should set an offset position.
        * Note: This may need to be replaced with something that has better concepts behind it. Currently, this is only
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
        time.sleep(float(t))

    def wait_finish(self, *values):
        """
        Wait finish should hold the calling thread until the current work has completed. Or otherwise prevent any data
        from being sent with returning True for the until that criteria is met.

        @param values:
        @return:
        """
        self.hold = True
        # self.temp_holds.append(lambda: len(self.output) != 0)

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooled cycle.

        @param function:
        @return:
        """
        function()

    def beep(self):
        self.service("beep\n")

    def console(self, value):
        self.service(value)

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

    def resume(self, *args):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser.

        @param args:
        @return:
        """
        self.paused = False

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.

        @param args:
        @return:
        """
        self.service.spooler.clear_queue()
        self.rapid_mode()
        try:
            self.service.controller.estop()
        except AttributeError:
            pass

    def status(self):
        """
        Asks that this device status be updated.

        @return:
        """
        parts = list()
        parts.append(f"x={self.native_x}")
        parts.append(f"y={self.native_y}")
        parts.append(f"speed={self.speed}")
        parts.append(f"power={self.power}")
        status = ";".join(parts)
        self.service.signal("driver;status", status)

    def push_program(self):
        self.pipe_channel("Pushed program to output...")
        if len(self.program):
            self.service.controller.push_program(self.program)
            self.program = MoshiBlob()
            self.program.channel = self.pipe_channel

    def plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        @return:
        """
        if self.plot_data is None:
            return False
        if self.hold:
            return True

        for x, y, on in self.plot_data:
            if self.hold_work():
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
                elif on & PLOT_SETTING:  # Plot planner settings have changed.
                    p_set = self.plot_planner.settings
                    s_set = self.settings
                    if p_set.power != s_set.power:
                        self._set_power(p_set.power)
                    if (
                        p_set.speed != s_set.speed
                        or p_set.raster_step_x != s_set.raster_step_x
                        or p_set.raster_step_y != s_set.raster_step_y
                    ):
                        self._set_speed(p_set.speed)
                        self._set_step(p_set.raster_step_x, p_set.raster_step_y)
                        self.rapid_mode()
                    self.settings.update(p_set.settings)
                continue
            self._goto_absolute(x, y, on & 1)
        self.plot_data = None
        return False

    def _ensure_program_or_raster_mode(self, x, y, x1=None, y1=None):
        """
        Ensure blob mode makes sure it's in program or raster mode.
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
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def laser_disable(self, *values):
        self.laser_enabled = False

    def laser_enable(self, *values):
        self.laser_enabled = True


class MoshiController:
    """
    The Moshiboard Controller takes data programs built by the MoshiDriver and sends to the Moshiboard
    according to established moshi protocols.

    The output device is concerned with sending the moshiblobs to the control board and control events and
    to the CH341 chip on the Moshiboard. We use the same ch341 driver as the Lhystudios boards. Giving us
    access to both libusb drivers and windll drivers.

    The protocol for sending rasters is as follows:
    Check processing-state of board, seeking 205
    Send Preamble.
    Check processing-state of board, seeking 205
    Send bulk data of moshiblob. No checks between packets.
    Send Epilogue.
    While Check processing-state is 207:
        wait 0.2 seconds
    Send Preamble
    Send 0,0 offset 0,0 move.
    Send Epilogue

    Checks done before the Epilogue will have 205 state.
    """

    def __init__(self, context, channel=None, *args, **kwargs):
        self.context = context
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self._thread = None
        self._buffer = (
            bytearray()
        )  # Threadsafe buffered commands to be sent to controller.

        self._programs = []  # Programs to execute.

        self.context._buffer_size = 0
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self._connection = None

        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.abort_waiting = False

        name = self.context.label
        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=500)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)

        self.ch341 = context.open("module/ch341", log=self.usb_log)

        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

    def viewbuffer(self):
        """
        Viewbuffer is used by the BufferView class if such a value exists it provides a view of the
        buffered data. Without this class the BufferView displays nothing. This is optional for any output
        device.
        """
        buffer = "Current Working Buffer: %s\n" % str(self._buffer)
        for p in self._programs:
            buffer += "%s\n" % str(p.data)
        return buffer

    def added(self, *args, **kwargs):
        self.start()

    def shutdown(self, *args, **kwargs):
        if self._thread is not None:
            self.is_shutdown = True

    def __repr__(self):
        return "MoshiController()"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + sum(map(len, self._programs))

    def realtime_read(self):
        """
        The `a7xx` values used before the AC01 commands. Read preamble.

        Also seen randomly 3.2 seconds apart. Maybe keep-alive.
        @return:
        """
        self.pipe_channel("Realtime: Read...")
        self.realtime_pipe(swizzle_table[MOSHI_READ][0])

    def realtime_prologue(self):
        """
        Before a jump / program / turned on:
        @return:
        """
        self.pipe_channel("Realtime: Prologue")
        self.realtime_pipe(swizzle_table[MOSHI_PROLOGUE][0])

    def realtime_epilogue(self):
        """
        Status 205
        After a jump / program
        Status 207
        Status 205 Done.
        @return:
        """
        self.pipe_channel("Realtime: Epilogue")
        self.realtime_pipe(swizzle_table[MOSHI_EPILOGUE][0])

    def realtime_freemotor(self):
        """
        Freemotor command
        @return:
        """
        self.pipe_channel("Realtime: FreeMotor")
        self.realtime_pipe(swizzle_table[MOSHI_FREEMOTOR][0])

    def realtime_laser(self):
        """
        Laser Command Toggle.
        @return:
        """
        self.pipe_channel("Realtime: Laser Active")
        self.realtime_pipe(swizzle_table[MOSHI_LASER][0])

    def realtime_stop(self):
        """
        Stop command (likely same as freemotor):
        @return:
        """
        self.pipe_channel("Realtime: Stop")
        self.realtime_pipe(swizzle_table[MOSHI_ESTOP][0])

    def realtime_pipe(self, data):
        if self._connection is not None:
            try:
                self._connection.write_addr(data)
            except ConnectionError:
                self.pipe_channel("Connection error")
        else:
            self.pipe_channel("Not connected")

    def open(self):
        self.pipe_channel("open()")
        if self._connection is None:
            connection = self.ch341.connect(
                driver_index=self.context.usb_index,
                chipv=self.context.usb_version,
                bus=self.context.usb_bus,
                address=self.context.usb_address,
                mock=self.context.mock,
            )
            self._connection = connection
            if self.context.mock:
                self._connection.mock_status = 205
                self._connection.mock_finish = 207
        else:
            self._connection.open()
        if self._connection is None:
            raise ConnectionRefusedError("ch341 connect did not return a connection.")

    def close(self):
        self.pipe_channel("close()")
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        else:
            raise ConnectionError

    def push_program(self, program):
        self.pipe_channel("Pushed: %s" % str(program.data))
        self._programs.append(program)
        self.start()

    def unlock_rail(self):
        self.pipe_channel("Control Request: Unlock")
        if self._main_lock.locked():
            return
        else:
            self.realtime_freemotor()

    def start(self):
        """
        Controller state change to `Started`.
        @return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name="MoshiPipe(%s)" % self.context.path,
                result=self.stop,
            )
            self.update_state(STATE_INITIALIZE)

    def pause(self):
        """
        Pause simply holds the controller from sending any additional packets.

        If this state change is done from INITIALIZE it will start the processing.
        Otherwise, it must be done from ACTIVE or IDLE.
        """
        if self.state == STATE_INITIALIZE:
            self.start()
            self.update_state(STATE_PAUSE)
        if self.state == STATE_ACTIVE or self.state == STATE_IDLE:
            self.update_state(STATE_PAUSE)

    def resume(self):
        """
        Resume can only be called from PAUSE.
        """
        if self.state == STATE_PAUSE:
            self.update_state(STATE_ACTIVE)

    def estop(self):
        """
        Abort the current buffer and data queue.
        """
        self._buffer = bytearray()
        self._programs.clear()
        self.context.signal("pipe;buffer", 0)
        self.realtime_stop()
        self.update_state(STATE_TERMINATE)
        self.pipe_channel("Control Request: Stop")

    def stop(self, *args):
        """
        Start the shutdown of the local send thread.
        """
        if self._thread is not None:
            try:
                self._thread.join()  # Wait until stop completes before continuing.
            except RuntimeError:
                pass  # Thread is current thread.
        self._thread = None

    def update_state(self, state):
        """
        Update the local state for the output device
        """
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        """
        Notify listening processes that the buffer size of this output has changed.
        """
        if self.context is not None:
            self.context._buffer_size = len(self._buffer)
            self.context.signal("pipe;buffer", self.context._buffer_size)

    def update_packet(self, packet):
        """
        Notify listening processes that the last sent packet has changed.
        """
        if self.context is not None:
            self.context.signal("pipe;packet_text", packet)
            self.usb_send_channel(packet)

    def _send_buffer(self):
        """
        Send the current Moshiboard buffer
        """
        self.pipe_channel("Sending Buffer...")
        while len(self._buffer) != 0:
            queue_processed = self.process_buffer()
            self.refuse_counts = 0

            if queue_processed:
                # Packet was sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_ACTIVE,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_ACTIVE)
                self.count = 0
            else:
                # No packet could be sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_IDLE)
                if self.count > 50:
                    self.count = 50
                time.sleep(0.02 * self.count)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self.pipe_channel("Send Thread Start... %d" % len(self._programs))
        self._main_lock.acquire(True)
        self.count = 0
        self.is_shutdown = False

        while True:
            self.pipe_channel("While Loop")
            try:
                if self.state == STATE_INITIALIZE:
                    # If we are initialized. Change that to active since we're running.
                    self.update_state(STATE_ACTIVE)
                if self.is_shutdown:
                    break
                if len(self._buffer) == 0 and len(self._programs) == 0:
                    self.pipe_channel("Nothing to process")
                    break  # There is nothing to run.
                if self._connection is None:
                    self.open()
                # Stage 0: New Program send.
                if len(self._buffer) == 0:
                    self.context.signal("pipe;running", True)
                    self.pipe_channel("New Program")
                    self.wait_until_accepting_packets()
                    self.realtime_prologue()
                    self._buffer = self._programs.pop(0).data
                    assert len(self._buffer) != 0

                # Stage 1: Send Program.
                self.context.signal("pipe;running", True)
                self.pipe_channel("Sending Data... %d bytes" % len(self._buffer))
                self._send_buffer()
                self.update_status()
                self.realtime_epilogue()
                if self.is_shutdown:
                    break

                # Stage 2: Wait for Program to Finish.
                self.pipe_channel("Waiting for finish processing.")
                if len(self._buffer) == 0:
                    self.wait_finished()
                self.context.signal("pipe;running", False)

            except ConnectionRefusedError:
                if self.is_shutdown:
                    break
                # The attempt refused the connection.
                self.refuse_counts += 1

                if self.refuse_counts >= 5:
                    self.context.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.context.signal("pipe;failing", self.refuse_counts)
                self.context.signal("pipe;running", False)
                time.sleep(3)  # 3-second sleep on failed connection attempt.
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                if self.is_shutdown:
                    break
                self.connection_errors += 1
                time.sleep(0.5)
                try:
                    self.close()
                except ConnectionError:
                    pass
                continue
        self.context.signal("pipe;running", False)
        self._thread = None
        self.is_shutdown = False
        self.update_state(STATE_END)
        self._main_lock.release()
        self.pipe_channel("Send Thread Finished...")

    def process_buffer(self):
        """
        Attempts to process the program send from the buffer.

        @return: queue process success.
        """
        if len(self._buffer) > 0:
            buffer = self._buffer
        else:
            return False

        length = min(32, len(buffer))
        packet = buffer[:length]

        # Packet is prepared and ready to send. Open Channel.

        self.send_packet(packet)
        self.context.packet_count += 1

        # Packet was processed. Remove that data.
        self._buffer = self._buffer[length:]
        self.update_buffer()
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        """
        Send packet to the CH341 connection.
        """
        if self._connection is None:
            raise ConnectionError
        self._connection.write(packet)
        self.update_packet(packet)

    def update_status(self):
        """
        Request a status update from the CH341 connection.
        """
        if self._connection is None:
            raise ConnectionError
        self._status = self._connection.get_status()
        if self.context is not None:
            try:
                self.context.signal(
                    "pipe;status",
                    self._status,
                    get_code_string_from_moshicode(self._status[1]),
                )
            except IndexError:
                pass
            self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        """
        Wait until the device can accept packets.
        """
        i = 0
        while self.state != STATE_TERMINATE:
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_ERROR:
                raise ConnectionRefusedError
            if status == STATUS_OK:
                return
            time.sleep(0.05)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        """
        Wait until the device has finished the current sending buffer.
        """
        self.pipe_channel("Wait Finished")
        i = 0
        original_state = self.state
        if self.state != STATE_PAUSE:
            self.pause()

        while True:
            if self.state != STATE_WAIT:
                self.update_state(STATE_WAIT)
            self.update_status()
            status = self._status[1]
            if status == 0:
                self.close()
                self.open()
                continue
            if status == STATUS_OK:
                break
            if self.context is not None:
                self.context.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
            if status == STATUS_PROCESSING:
                time.sleep(0.5)  # Half a second between requests.
        self.update_state(original_state)
