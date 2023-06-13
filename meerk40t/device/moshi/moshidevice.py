import threading
import time

from ...core.drivers import Driver
from ...core.plotplanner import PlotPlanner
from ...kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
)
from ..basedevice import (
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

MILS_IN_MM = 39.3701

STATUS_OK = 205  # Seen before file send. And after file send.
STATUS_PROCESSING = 207  # PROCESSING
STATUS_ERROR = 237  # ERROR
STATUS_RESET = 239  # Seen during reset


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        _ = kernel.translation
        kernel.register("driver/moshi", MoshiDriver)
        kernel.register("output/moshi", MoshiController)
        context = kernel.root

        @context.console_command(
            "usb_connect", input_type="moshi", help=_("Connect USB")
        )
        def usb_connect(command, channel, _, data=None, **kwargs):
            """
            Force USB Connection Event for Moshiboard
            """
            spooler, driver, output = data
            try:
                output.open()
            except ConnectionRefusedError:
                channel("Connection Refused.")

        @context.console_command(
            "usb_disconnect", input_type="moshi", help=_("Disconnect USB")
        )
        def usb_disconnect(command, channel, _, data=None, **kwargs):
            """
            Force USB Disconnect Event for Moshiboard
            """
            spooler, driver, output = data
            try:
                output.close()
            except ConnectionError:
                channel("Usb is not connected.")

        @context.console_command(
            "start", input_type="moshi", help=_("Start Pipe to Controller")
        )
        def pipe_start(command, channel, _, data=None, **kwargs):
            """
            Start output sending.
            """
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel("Moshi Channel Started.")

        @context.console_command("hold", input_type="moshi", help=_("Hold Controller"))
        def pipe_pause(command, channel, _, data=None, **kwargs):
            """
            Pause output sending.
            """
            spooler, driver, output = data
            output.update_state(STATE_PAUSE)
            output.pause()
            channel(_("Moshi Channel Paused."))

        @context.console_command(
            "resume", input_type="moshi", help=_("Resume Controller")
        )
        def pipe_resume(command, channel, _, data=None, **kwargs):
            """
            Resume output sending.
            """
            spooler, driver, output = data
            output.update_state(STATE_ACTIVE)
            output.start()
            channel(_("Moshi Channel Resumed."))

        @context.console_command(
            ("estop", "abort"), input_type="moshi", help=_("Abort Job")
        )
        def pipe_abort(command, channel, _, data=None, **kwargs):
            """
            Abort output job. Usually due to the functionality of Moshiboards this will do
            nothing as the job will have already sent to the backend.
            """
            spooler, driver, output = data
            output.estop()
            channel(_("Moshi Channel Aborted."))

        @context.console_command(
            "status",
            input_type="moshi",
            help=_("Update moshiboard controller status"),
        )
        def realtime_status(channel, _, data=None, **kwargs):
            """
            Updates the CH341 Status information for the Moshiboard.
            """
            spooler, driver, output = data
            try:
                output.update_status()
            except ConnectionError:
                channel(_("Could not check status, usb not connected."))

        @context.console_command(
            "continue",
            input_type="moshi",
            help=_("abort waiting process on the controller."),
        )
        def realtime_pause(data=None, **kwargs):
            """
            Abort the waiting process for Moshiboard. This is usually a wait from BUSY (207) state until the board
            reports its status as READY (205)
            """
            spooler, driver, output = data
            output.abort_waiting = True


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


class MoshiDriver(Driver):
    """
    A driver takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. The Moshiboard Driver overloads the Driver class to take spoolable values from
    the spooler and converts them into Moshiboard specific actions.

    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        context = context.get_context("moshi/driver/%s" % name)
        Driver.__init__(self, context=context)

        self.next = None
        self.prev = None

        self.plot_planner = PlotPlanner(self.settings)
        self.plot = None

        self.is_paused = False
        self.context._buffer_size = 0
        self.thread = None
        root_context = context.root

        self.preferred_offset_x = 0
        self.preferred_offset_y = 0

        context.driver = self

        root_context.setting(bool, "opt_rapid_between", True)
        root_context.setting(int, "opt_jog_mode", 0)
        root_context.setting(int, "opt_jog_minimum", 256)

        context.setting(int, "usb_index", -1)
        context.setting(int, "usb_bus", -1)
        context.setting(int, "usb_address", -1)
        context.setting(int, "usb_version", -1)

        context.setting(bool, "home_right", False)
        context.setting(bool, "home_bottom", False)
        context.setting(int, "home_adjust_x", 0)
        context.setting(int, "home_adjust_y", 0)
        context.setting(bool, "enable_raster", True)
        context.setting(int, "rapid_speed", 40)

        self.pipe_channel = context.channel("%s/events" % name)
        self.program = MoshiBlob(channel=self.pipe_channel)

    def __repr__(self):
        return "MoshiDriver(%s)" % self.name

    def push_program(self):
        self.pipe_channel("Pushed program to output...")
        if len(self.program):
            self.output.push_program(self.program)
            self.program = MoshiBlob(channel=self.pipe_channel)

    def ensure_program_mode(self, *values):
        """
        Ensure the laser is currently in a program state. If it is not currently in a program state we begin
        a program state.

        If the the driver is currently in a program state the assurance is made.
        """
        if self.state == DRIVER_STATE_PROGRAM:
            return

        if self.pipe_channel:
            self.pipe_channel("Program Mode")
        if self.state == DRIVER_STATE_RASTER:
            self.ensure_finished_mode()
            self.ensure_rapid_mode()
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

    def ensure_raster_mode(self, *values):
        """
        Ensure the driver is currently in a raster program state. If it is not in a raster program state
        we write the raster program state.
        """
        if self.state == DRIVER_STATE_RASTER:
            return

        if self.pipe_channel:
            self.pipe_channel("Raster Mode")
        if self.state == DRIVER_STATE_PROGRAM:
            self.ensure_finished_mode()
            self.ensure_rapid_mode()
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
        if speed is None and self.settings.speed is not None:
            speed = int(self.settings.speed)
        if speed is None:
            speed = self.context.rapid_speed
        if normal_speed is None:
            normal_speed = speed

        # Normal speed is rapid. Passing same speed so PPI isn't crazy.
        self.program.vector_speed(speed, normal_speed)
        self.program.set_offset(0, offset_x, offset_y)
        self.state = DRIVER_STATE_PROGRAM
        self.context.signal("driver;mode", self.state)

        self.program.move_abs(move_x, move_y)
        self.current_x = move_x
        self.current_y = move_y

    def start_raster_mode(
        self, offset_x, offset_y, move_x=None, move_y=None, speed=None
    ):
        if move_x is None:
            move_x = offset_x
        if move_y is None:
            move_y = offset_y
        if speed is None and self.settings.speed is not None:
            speed = int(self.settings.speed)
        if speed is None:
            speed = 160
        self.program.raster_speed(speed)
        self.program.set_offset(0, offset_x, offset_y)
        self.state = DRIVER_STATE_RASTER
        self.context.signal("driver;mode", self.state)

        self.program.move_abs(move_x, move_y)
        self.current_x = move_x
        self.current_y = move_y

    def ensure_rapid_mode(self, *values):
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
        self.context.signal("driver;mode", self.state)

    def ensure_finished_mode(self, *values):
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
            self.ensure_rapid_mode()

        if self.state == self.state == DRIVER_STATE_RASTER:
            self.pipe_channel("Final Raster Home")
            self.home()
        self.state = DRIVER_STATE_FINISH

    def plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        :return:
        """
        if self.plot is None:
            return False
        if self.hold():
            return True

        for x, y, on in self.plot:
            on = int(on)
            if on > 1:
                # Special Command.
                if on & (
                    PLOT_RAPID | PLOT_JOG
                ):  # Plot planner requests position change.
                    # self.rapid_jog(x, y)
                    self.current_x = x
                    self.current_y = y
                    if self.state != DRIVER_STATE_RAPID:
                        self.move_absolute(x, y)
                    continue
                elif on & PLOT_FINISH:  # Plot planner is ending.
                    self.ensure_finished_mode()
                    break
                elif on & PLOT_START:
                    self.ensure_program_or_raster_mode(
                        self.preferred_offset_x,
                        self.preferred_offset_y,
                        self.current_x,
                        self.current_y,
                    )
                elif on & PLOT_LEFT_UPPER:
                    self.preferred_offset_x = x
                    self.preferred_offset_y = y
                elif on & PLOT_SETTING:  # Plot planner settings have changed.
                    p_set = self.plot_planner.settings
                    s_set = self.settings
                    if p_set.power != s_set.power:
                        self.set_power(p_set.power)
                    if (
                        p_set.speed != s_set.speed
                        or p_set.raster_step != s_set.raster_step
                    ):
                        self.set_speed(p_set.speed)
                        self.set_step(p_set.raster_step)
                        self.ensure_rapid_mode()
                    self.settings.set_values(p_set)
                continue
            self.goto_absolute(x, y, on & 1)
        self.plot = None
        return False

    def ensure_program_or_raster_mode(self, x, y, x1=None, y1=None):
        """
        Ensure blob mode makes sure it's in program or raster mode.
        """
        if self.state in (DRIVER_STATE_RASTER, DRIVER_STATE_PROGRAM):
            return

        if x1 is None:
            x1 = x
        if y1 is None:
            y1 = y
        if self.settings.raster_step == 0:
            self.ensure_program_mode(x, y, x1, y1)
        else:
            if self.context.enable_raster:
                self.ensure_raster_mode(x, y, x1, y1)
            else:
                self.ensure_program_mode(x, y, x1, y1)

    def goto_absolute(self, x, y, cut):
        """
        Goto absolute position. Cut flags whether this should be with or without the laser.
        """
        self.ensure_program_or_raster_mode(x, y)
        old_x = self.program.last_x
        old_y = self.program.last_y

        if self.state == DRIVER_STATE_PROGRAM:
            if cut:
                self.program.cut_abs(x, y)
            else:
                self.program.move_abs(x, y)
        else:
            # DRIVER_STATE_RASTER
            if x == self.current_x and y == self.current_y:
                return
            if cut:
                if x == self.current_x:
                    self.program.cut_vertical_abs(y=y)
                if y == self.current_y:
                    self.program.cut_horizontal_abs(x=x)
            else:
                if x == self.current_x:
                    self.program.move_vertical_abs(y=y)
                if y == self.current_y:
                    self.program.move_horizontal_abs(x=x)
        self.current_x = x
        self.current_y = y
        self.context.signal("driver;position", (old_x, old_y, x, y))

    def cut(self, x, y):
        """
        Cut to a position x, y. Either absolute or relative depending on the state of
        is_relative.
        """
        if self.is_relative:
            self.cut_relative(x, y)
        else:
            self.cut_absolute(x, y)
        self.ensure_rapid_mode()
        self.push_program()

    def cut_absolute(self, x, y):
        """
        Cut to a position x, y. This is an absolute position.
        """
        self.ensure_program_or_raster_mode(x, y)
        self.program.cut_abs(x, y)

        oldx = self.current_x
        oldy = self.current_y
        self.current_x = x
        self.current_y = y
        self.context.signal("driver;position", (oldx, oldy, x, y))

    def cut_relative(self, dx, dy):
        """
        Cut to a position dx, dy. This is relative to the currently laser position.
        """
        x = dx + self.current_x
        y = dy + self.current_y
        self.cut_absolute(x, y)

    def rapid_jog(self, x, y, **kwargs):
        """
        Perform a rapid jog. In Moshiboard this is merely a move.
        """
        self.ensure_program_or_raster_mode(x, y)
        old_x = self.program.last_x
        old_y = self.program.last_y
        self.program.move_abs(x, y)
        self.current_x = x
        self.current_y = y
        new_x = self.program.last_x
        new_y = self.program.last_y
        self.context.signal("driver;position", (old_x, old_y, new_x, new_y))

    def move(self, x, y):
        """
        Move to a position x,y. Either absolute or relative depending on the state of
        is_relative.
        """
        if self.is_relative:
            self.move_relative(x, y)
        else:
            self.move_absolute(x, y)
        self.ensure_rapid_mode()

    def move_absolute(self, x, y):
        """
        Move to a position x, y. This is an absolute position.
        """
        self.ensure_program_or_raster_mode(x, y)
        oldx = self.current_x
        oldy = self.current_y
        self.program.move_abs(x, y)
        self.current_x = x
        self.current_y = y
        x = self.current_x
        y = self.current_y
        self.context.signal("driver;position", (oldx, oldy, x, y))

    def move_relative(self, dx, dy):
        """
        Move to a position dx, dy. This is a relative position.
        """
        x = dx + self.current_x
        y = dy + self.current_y
        self.move_absolute(x, y)

    def set_speed(self, speed=None):
        """
        Set the speed for the driver.
        """
        if self.settings.speed != speed:
            self.settings.speed = speed
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def set_step(self, step=None):
        """
        Set the raster step for the driver.
        """
        if self.settings.raster_step != step:
            self.settings.raster_step = step
            if self.state in (DRIVER_STATE_PROGRAM, DRIVER_STATE_RASTER):
                self.state = DRIVER_STATE_MODECHANGE

    def calc_home_position(self):
        """
        Calculate the home position with the given home adjust and the corner the device is
        expected to home to.
        """
        x = self.context.home_adjust_x
        y = self.context.home_adjust_y
        bed_dim = self.context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)

        if self.context.home_right:
            x += int(bed_dim.bed_width * MILS_IN_MM)
        if self.context.home_bottom:
            y += int(bed_dim.bed_height * MILS_IN_MM)
        return x, y

    def home(self, *values):
        """
        Send a home command to the device. In the case of Moshiboards this is merely a move to
        0,0 in absolute position.
        """
        x, y = self.calc_home_position()
        try:
            x = int(values[0])
        except (ValueError, IndexError):
            pass
        try:
            y = int(values[1])
        except (ValueError, IndexError):
            pass
        self.ensure_rapid_mode()
        self.settings.speed = 40
        self.ensure_program_mode(x, y, x, y)
        self.ensure_rapid_mode()
        self.current_x = x
        self.current_y = y

    def lock_rail(self):
        pass

    def unlock_rail(self, abort=False):
        """
        Unlock the Rail or send a "FreeMotor" command.
        """
        self.ensure_rapid_mode()
        try:
            self.output.unlock_rail()
        except AttributeError:
            pass

    def abort(self):
        """
        Abort the current work.
        """
        self.ensure_rapid_mode()
        try:
            self.output.estop()
        except AttributeError:
            pass

    @property
    def type(self):
        return "moshi"


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

    def __init__(self, context, name, channel=None, *args, **kwargs):
        context = context.get_context("moshi/output/%s" % name)
        self.context = context
        self.name = name
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self.next = None
        self.prev = None

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

        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=500)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)

        self.ch341 = self.context.open("module/ch341", log=self.usb_log)

        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

        context.setting(int, "usb_index", -1)
        context.setting(int, "usb_bus", -1)
        context.setting(int, "usb_address", -1)
        context.setting(int, "usb_version", -1)
        context.setting(bool, "mock", False)
        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)

        self.context.root.listen("lifecycle;ready", self.on_controller_ready)

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

    def on_controller_ready(self, origin, *args):
        self.start()

    def finalize(self, *args, **kwargs):
        self.context.root.unlisten("lifecycle;ready", self.on_controller_ready)
        if self._thread is not None:
            self.is_shutdown = True

    def __repr__(self):
        return "MoshiController()"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + sum(map(len, self._programs))

    def realtime_read(self):
        """
        The a7xx values used before the AC01 commands. Read preamble.

        Also seen randomly 3.2 seconds apart. Maybe keep-alive.
        :return:
        """
        self.pipe_channel("Realtime: Read...")
        self.realtime_pipe(swizzle_table[MOSHI_READ][0])

    def realtime_prologue(self):
        """
        Before a jump / program / turned on:
        :return:
        """
        self.pipe_channel("Realtime: Prologue")
        self.realtime_pipe(swizzle_table[MOSHI_PROLOGUE][0])

    def realtime_epilogue(self):
        """
        Status 205
        After a jump / program
        Status 207
        Status 205 Done.
        :return:
        """
        self.pipe_channel("Realtime: Epilogue")
        self.realtime_pipe(swizzle_table[MOSHI_EPILOGUE][0])

    def realtime_freemotor(self):
        """
        Freemotor command
        :return:
        """
        self.pipe_channel("Realtime: FreeMotor")
        self.realtime_pipe(swizzle_table[MOSHI_FREEMOTOR][0])

    def realtime_laser(self):
        """
        Laser Command Toggle.
        :return:
        """
        self.pipe_channel("Realtime: Laser Active")
        self.realtime_pipe(swizzle_table[MOSHI_LASER][0])

    def realtime_stop(self):
        """
        Stop command (likely same as freemotor):
        :return:
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

    realtime_write = realtime_pipe

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
        Controller state change to Started.
        :return:
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
        Otherwise it must be done from ACTIVE or IDLE.
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
                    if len(self._programs) == 0:
                        # Async clear was called we should quit.
                        break
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
                time.sleep(3)  # 3 second sleep on failed connection attempt.
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

        :return: queue process success.
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

    @property
    def type(self):
        return "moshi"
