import os
import time
from threading import Lock

from meerk40t.svgelements import Length

from ..core.cutcode import LaserSettings
from ..kernel import Modifier
from .lasercommandconstants import *

INTERPRETER_STATE_RAPID = 0
INTERPRETER_STATE_FINISH = 1
INTERPRETER_STATE_PROGRAM = 2
INTERPRETER_STATE_RASTER = 3
INTERPRETER_STATE_MODECHANGE = 4

PLOT_FINISH = 256
PLOT_RAPID = 4
PLOT_JOG = 2
PLOT_SETTING = 128
PLOT_AXIS = 64
PLOT_DIRECTION = 32


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Spooler", Spooler)
        context = kernel.get_context('/')
        bed_dim = kernel.get_context('/')

        def execute_absolute_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
            )

            def move():
                yield COMMAND_SET_ABSOLUTE
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)

            return move

        def execute_relative_position(position_x, position_y):
            x_pos = Length(position_x).value(
                ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
            )
            y_pos = Length(position_y).value(
                ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
            )

            def move():
                yield COMMAND_SET_INCREMENTAL
                yield COMMAND_MODE_RAPID
                yield COMMAND_MOVE, int(x_pos), int(y_pos)
                yield COMMAND_SET_ABSOLUTE

            return move

        @context.console_option("path", "p", type=str, help="Path to Device")
        @context.console_command(
            "device",
            help="device",
            output_type="device"
        )
        def device(channel, _, path=None, **kwargs):
            if path is None:
                device_context = context.active
                if device_context is None:
                    device_context = context.get_context('1')
            else:
                device_context = context.get_context(path)
            if not hasattr(device_context, "spooler"):
                device_context.activate("modifier/Spooler")
            return "device", device_context

        @context.console_command(
            "list",
            help="list devices",
            input_type="device",
            output_type="device",
        )
        def list(channel, _, data, **kwargs):
            channel(_("----------"))
            channel(_("Devices:"))
            for i, ctx_name in enumerate(kernel.contexts):
                ctx = kernel.contexts[ctx_name]
                if hasattr(ctx, "spooler"):
                    channel("Device: %s, %s" % (ctx._path, str(ctx)))
            channel("----------")
            return "device", data

        @context.console_command(
            "type",
            help="list device types",
            input_type="device",
            output_type="device",
        )
        def list_type(channel, _, data, **kwargs):
            channel(_("----------"))
            channel(_("Backends permitted:"))
            for i, name in enumerate(context.match("device/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))
            return "device", data

        @context.console_command(
            "activate",
            help="activate device",
            input_type="device",
            output_type="device",
        )
        def activate(channel, _, data, **kwargs):
            context._kernel.set_active_device(data)
            channel(_("Device at context '%s' activated" % data._path))
            return "device", data

        @context.console_argument("device", help="Device to initialize...")
        @context.console_command(
            "init",
            help="init <device>, eg. init Lhystudios",
            input_type="device",
            output_type="device",
        )
        def init(channel, _, data, device=None, **kwargs):
            if device is None:
                raise SyntaxError
            try:
                data.activate("device/%s" % device)
            except KeyError:
                channel(_("Device %s is not valid type. 'device type' for a list of valid types."))
                return
            channel(_("Device %s, initialized at %s" % (device, data._path)))
            return "device", data

        @context.console_argument("type", type=str, help="type of pipe to use")
        @context.console_command(
            "pipe",
            help="pipe to utilize on this device",
            input_type="device",
            output_type="device",
        )
        def pipe(data=None, **kwargs):
            # TODO: MAKE THIS WORK.
            if data is None:
                data = context.active
            data.pipe = None
            return 'device', data

        @context.console_command("+laser", hidden=True, input_type=("device", None), output_type='device', help="turn laser on in place")
        def plus_laser(data, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            spooler.job(COMMAND_LASER_ON)
            return 'device', data

        @context.console_command("-laser", hidden=True, input_type=("device", None), output_type='device', help="turn laser off in place")
        def minus_laser(data, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            spooler.job(COMMAND_LASER_ON)
            return 'device', data

        @context.console_argument(
            "amount", type=Length, help="amount to move in the set direction."
        )
        @context.console_command(("left", "right", "up", "down"), input_type=("device", None), output_type='device', help="cmd <amount>")
        def direction(command, channel, _, data=None, amount=None, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler

            if spooler is None:
                channel(_("Device has no spooler."))
                return
            if amount is None:
                amount = Length("1mm")
            max_bed_height = bed_dim.bed_height * 39.3701
            max_bed_width = bed_dim.bed_width * 39.3701
            if command.endswith("right"):
                data.dx += amount.value(ppi=1000.0, relative_length=max_bed_width)
            elif command.endswith("left"):
                data.dx -= amount.value(ppi=1000.0, relative_length=max_bed_width)
            elif command.endswith("up"):
                data.dy -= amount.value(ppi=1000.0, relative_length=max_bed_height)
            elif command.endswith("down"):
                data.dy += amount.value(ppi=1000.0, relative_length=max_bed_height)
            kernel._console_queue("device -p %s jog" % data._path)
            #TODO: Try replacing with trigger: .trigger 1 0 device -p %s jog
            return 'device', data

        @context.console_command(
            "jog", hidden=True, input_type="device", output_type='device', help="executes outstanding jog buffer"
        )
        def jog(command, channel, _, data, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            idx = int(data.dx)
            idy = int(data.dy)
            if idx == 0 and idy == 0:
                return
            if spooler.job_if_idle(execute_relative_position(idx, idy)):
                channel(_("Position moved: %d %d") % (idx, idy))
                data.dx -= idx
                data.dy -= idy
            else:
                channel(_("Busy Error"))
            return 'device', data

        @context.console_argument("x", type=Length, help="change in x")
        @context.console_argument("y", type=Length, help="change in y")
        @context.console_command(
            ("move", "move_absolute"), input_type=("device", None), output_type='device', help="move <x> <y>: move to position."
        )
        def move(channel, _, x, y, data=None, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            if y is None:
                raise SyntaxError
            if not spooler.job_if_idle(execute_absolute_position(x, y)):
                channel(_("Busy Error"))
            return 'device', data

        @context.console_argument("dx", type=Length, help="change in x")
        @context.console_argument("dy", type=Length, help="change in y")
        @context.console_command("move_relative", input_type=("device", None), output_type='device', help="move_relative <dx> <dy>")
        def move_relative(channel, _, dx, dy, data=None, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            if dy is None:
                raise SyntaxError
            if not spooler.job_if_idle(execute_relative_position(dx, dy)):
                channel(_("Busy Error"))
            return 'device', data

        @context.console_argument("x", type=Length, help="x offset")
        @context.console_argument("y", type=Length, help="y offset")
        @context.console_command("home", input_type=("device", None), output_type='device', help="home the laser")
        def home(x=None, y=None, data=None,  **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            if x is not None and y is not None:
                x = x.value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
                y = y.value(
                    ppi=1000.0, relative_length=bed_dim.bed_height * 39.3701
                )
                spooler.job(COMMAND_HOME, int(x), int(y))
                return 'device', data
            spooler.job(COMMAND_HOME)
            return 'device', data

        @context.console_command("unlock", input_type=("device", None), output_type='device', help="unlock the rail")
        def unlock(data=None, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            spooler.job(COMMAND_UNLOCK)
            return 'device', data

        @context.console_command("lock", input_type=("device", None), output_type='device', help="lock the rail")
        def lock(data, **kwargs):
            if data is None:
                data = context.active
            spooler = data.spooler
            spooler.job(COMMAND_LOCK)
            return 'device', data


class Device(Modifier):
    def __init__(
        self, context, interpreter=None, name=None, channel=None, *args, **kwargs
    ):
        Modifier.__init__(self, context, name, channel)
        self.context.activate("modifier/Spooler")
        self.spooler = self.context.spooler
        if interpreter is not None:
            self.context.activate(interpreter)
        else:
            self.interpreter = None
        self.pipes = []

    def __repr__(self):
        return "Spooler()"

    def attach(self, *a, **kwargs):
        """Overloaded attach to demand .spooler attribute."""
        self.context.spooler = self.spooler
        self.context.pipes = self.pipes
        self.context.interpreter = self.interpreter


class Interpreter:
    """
    An Interpreter Module takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. This is intended to be overridden by a subclass or class with the required methods.

    Interpreters register themselves as context.interpreter objects.
    Interpreters expect the context.spooler object exists to provide spooled commands as needed.

    These modules function to interpret hardware specific backend information from the reusable spoolers and server
    objects that may also be common within devices.
    """

    def __init__(self, context):
        self.context = context
        self.root_context = context.get_context("/")
        self.settings = LaserSettings()

        self.process_item = None
        self.spooled_item = None
        self.holds = []
        self.temp_holds = []

        self.state = INTERPRETER_STATE_RAPID
        self.properties = 0
        self.is_relative = False
        self.laser = False
        context.setting(int, "current_x", 0)
        context.setting(int, "current_y", 0)
        self.root_context.setting(bool, "opt_rapid_between", True)
        self.root_context.setting(int, "opt_jog_mode", 0)
        self.root_context.setting(int, "opt_jog_minimum", 127)
        context._quit = False

        context.current_x = 0
        context.current_y = 0
        self.rapid = self.root_context.opt_rapid_between
        self.jog = self.root_context.opt_jog_mode
        self.rapid_override = False
        self.rapid_override_speed_x = 50.0
        self.rapid_override_speed_y = 50.0
        self._thread = None
        self._shutdown = False

    def start_interpreter(self, *args):
        if self._thread is None:

            def clear_thread(*args):
                self._shutdown = True

            self._thread = self.context.threaded(
                self._interpret_threaded,
                result=clear_thread,
                thread_name="Interpreter(%s)" % (self.context._path),
            )
            self._thread.stop = clear_thread

    def _interpret_threaded(self, *args):
        """
        Fetch and Execute.

        :param args:
        :return:
        """
        while True:
            if self._shutdown:
                return
            if self.spooled_item is None:
                self._fetch_next_item_from_spooler()
            if self.spooled_item is None:
                # There is no data to interpret. Fetch Failed.
                if self.context._quit:
                    self.context("quit\n")
                    self._shutdown = True
                    return
                time.sleep(0.1)
            self._process_spooled_item()

    def _process_spooled_item(self):
        """
        Default Execution Cycle. If Held, we wait. Otherwise we process the spooler.

        Processes one item in the spooler. If the spooler item is a generator. Process one generated item.
        """
        if self.hold():
            time.sleep(0.01)
            return
        if self.plotplanner_process():
            return
        if self.spooled_item is None:
            return  # Fetch Next.

        # We have a spooled item to process.
        if self.command(self.spooled_item):
            self.spooled_item = None
            return

        # We are dealing with an iterator/generator
        try:
            e = next(self.spooled_item)
            if not self.command(e):
                raise ValueError
        except StopIteration:
            # The spooled item is finished.
            self.spooled_item = None

    def plotplanner_process(self):
        """
        Executes the device specific processing.

        :return: if execute tick was processed.
        """
        return False

    def _fetch_next_item_from_spooler(self):
        """
        Fetches the next item from the spooler.

        :return:
        """
        element = self.context.spooler.peek()
        if element is None:
            return  # Spooler is empty.

        self.context.spooler.pop()
        if isinstance(element, int):
            self.spooled_item = (element,)
        elif isinstance(element, tuple):
            self.spooled_item = element
        else:
            self.rapid = self.root_context.opt_rapid_between
            self.jog = self.root_context.opt_jog_mode
            try:
                self.spooled_item = element.generate()
            except AttributeError:
                try:
                    self.spooled_item = element()
                except TypeError:
                    # This could be a text element, some unrecognized type.
                    return

    def command(self, command, *values):
        """Commands are middle language LaserCommandConstants there values are given."""
        if isinstance(command, tuple):
            values = command[1:]
            command = command[0]
        if not isinstance(command, int):
            return False  # Command type is not recognized.

        try:
            if command == COMMAND_LASER_OFF:
                self.laser_off()
            elif command == COMMAND_LASER_ON:
                self.laser_on()
            elif command == COMMAND_LASER_DISABLE:
                self.laser_disable()
            elif command == COMMAND_LASER_ENABLE:
                self.laser_enable()
            elif command == COMMAND_CUT:
                x, y = values
                self.cut(x, y)
            elif command == COMMAND_MOVE:
                x, y = values
                self.move(x, y)
            elif command == COMMAND_JOG:
                x, y = values
                self.jog(x, y, mode=0, min_jog=self.context.opt_jog_minimum)
            elif command == COMMAND_JOG_SWITCH:
                x, y = values
                self.jog(x, y, mode=1, min_jog=self.context.opt_jog_minimum)
            elif command == COMMAND_JOG_FINISH:
                x, y = values
                self.jog(x, y, mode=2, min_jog=self.context.opt_jog_minimum)
            elif command == COMMAND_HOME:
                self.home(*values)
            elif command == COMMAND_LOCK:
                self.lock_rail()
            elif command == COMMAND_UNLOCK:
                self.unlock_rail()
            elif command == COMMAND_PLOT:
                self.plot_plot(values[0])
            elif command == COMMAND_PLOT_START:
                self.plot_start()
            elif command == COMMAND_SET_SPEED:
                self.set_speed(values[0])
            elif command == COMMAND_SET_POWER:
                self.set_power(values[0])
            elif command == COMMAND_SET_PPI:
                self.set_ppi(values[0])
            elif command == COMMAND_SET_PWM:
                self.set_pwm(values[0])
            elif command == COMMAND_SET_STEP:
                self.set_step(values[0])
            elif command == COMMAND_SET_OVERSCAN:
                self.set_overscan(values[0])
            elif command == COMMAND_SET_ACCELERATION:
                self.set_acceleration(values[0])
            elif command == COMMAND_SET_D_RATIO:
                self.set_d_ratio(values[0])
            elif command == COMMAND_SET_DIRECTION:
                self.set_directions(values[0], values[1], values[2], values[3])
            elif command == COMMAND_SET_INCREMENTAL:
                self.set_incremental()
            elif command == COMMAND_SET_ABSOLUTE:
                self.set_absolute()
            elif command == COMMAND_SET_POSITION:
                self.set_position(values[0], values[1])
            elif command == COMMAND_MODE_RAPID:
                self.ensure_rapid_mode()
            elif command == COMMAND_MODE_PROGRAM:
                self.ensure_program_mode()
            elif command == COMMAND_MODE_RASTER:
                self.ensure_raster_mode()
            elif command == COMMAND_MODE_FINISHED:
                self.ensure_finished_mode()
            elif command == COMMAND_WAIT:
                self.wait(values[0])
            elif command == COMMAND_WAIT_FINISH:
                self.wait_finish()
            elif command == COMMAND_BEEP:
                if os.name == "nt":
                    try:
                        import winsound

                        for x in range(5):
                            winsound.Beep(2000, 100)
                    except Exception:
                        pass
                if os.name == "posix":
                    # Mac or linux.
                    print("\a")  # Beep.
                    os.system('say "Ding"')
                else:
                    print("\a")  # Beep.
            elif command == COMMAND_FUNCTION:
                if len(values) >= 1:
                    t = values[0]
                    if callable(t):
                        t()
            elif command == COMMAND_SIGNAL:
                if isinstance(values, str):
                    self.context.signal(values, None)
                elif len(values) >= 2:
                    self.context.signal(values[0], *values[1:])
        except AttributeError:
            pass
        return True

    def realtime_command(self, command, *values):
        """Asks for the execution of a realtime command. Unlike the spooled commands these
        return False if rejected and something else if able to be performed. These will not
        be queued. If rejected. They must be performed in realtime or cancelled.
        """
        try:
            if command == REALTIME_PAUSE:
                self.pause()
            elif command == REALTIME_RESUME:
                self.resume()
            elif command == REALTIME_RESET:
                self.reset()
            elif command == REALTIME_STATUS:
                self.status()
            elif command == REALTIME_SAFETY_DOOR:
                self.safety_door()
            elif command == REALTIME_JOG_CANCEL:
                self.jog_cancel(*values)
            elif command == REALTIME_SPEED_PERCENT:
                self.realtime_speed_percent(*values)
            elif command == REALTIME_SPEED:
                self.realtime_speed(*values)
            elif command == REALTIME_RAPID_PERCENT:
                self.realtime_rapid_percent(*values)
            elif command == REALTIME_RAPID:
                self.realtime_rapid(*values)
            elif command == REALTIME_POWER_PERCENT:
                self.realtime_power_percent(*values)
            elif command == REALTIME_POWER:
                self.realtime_power(*values)
            elif command == REALTIME_OVERSCAN:
                self.realtime_overscan(*values)
            elif command == REALTIME_LASER_DISABLE:
                self.realtime_laser_disable(*values)
            elif command == REALTIME_LASER_ENABLE:
                self.realtime_laser_enable(*values)
            elif command == REALTIME_FLOOD_COOLANT:
                self.realtime_flood_coolant(*values)
            elif command == REALTIME_MIST_COOLANT:
                self.realtime_mist_coolant(*values)
        except AttributeError:
            pass  # Method doesn't exist.

    def hold(self):
        """
        Holds are criteria to use to pause the data interpretation. These halt the production of new data until the
        criteria is met. A hold is constant and will always halt the data while true. A temp_hold will be removed
        as soon as it does not hold the data.

        :return: Whether data interpretation should hold.
        """
        temp_hold = False
        fail_hold = False
        for i, hold in enumerate(self.temp_holds):
            if not hold():
                self.temp_holds[i] = None
                fail_hold = True
            else:
                temp_hold = True
        if fail_hold:
            self.temp_holds = [hold for hold in self.temp_holds if hold is not None]
        if temp_hold:
            return True
        for hold in self.holds:
            if hold():
                return True
        return False

    def laser_off(self, *values):
        self.laser = False

    def laser_on(self, *values):
        self.laser = True

    def laser_disable(self, *values):
        self.settings.laser_enabled = False

    def laser_enable(self, *values):
        self.settings.laser_enabled = True

    def jog(self, x, y, mode=0, min_jog=127):
        self.context.current_x = x
        self.context.current_y = y

    def move(self, x, y):
        self.context.current_x = x
        self.context.current_y = y

    def cut(self, x, y):
        self.context.current_x = x
        self.context.current_y = y

    def home(self, *values):
        self.context.current_x = 0
        self.context.current_y = 0

    def ensure_rapid_mode(self, *values):
        if self.state == INTERPRETER_STATE_RAPID:
            return
        self.state = INTERPRETER_STATE_RAPID
        self.context.signal("interpreter;mode", self.state)

    def ensure_finished_mode(self, *values):
        if self.state == INTERPRETER_STATE_FINISH:
            return
        self.state = INTERPRETER_STATE_FINISH
        self.context.signal("interpreter;mode", self.state)

    def ensure_program_mode(self, *values):
        if self.state == INTERPRETER_STATE_PROGRAM:
            return
        self.state = INTERPRETER_STATE_PROGRAM
        self.context.signal("interpreter;mode", self.state)

    def ensure_raster_mode(self, *values):
        if self.state == INTERPRETER_STATE_RASTER:
            return
        self.state = INTERPRETER_STATE_RASTER
        self.context.signal("interpreter;mode", self.state)

    def set_speed(self, speed=None):
        self.settings.speed = speed

    def set_power(self, power=1000.0):
        self.settings.power = power
        if self.settings.power > 1000.0:
            self.settings.power = 1000.0
        if self.settings.power <= 0:
            self.settings.power = 0.0

    def set_ppi(self, power=1000.0):
        self.settings.power = power
        if self.settings.power > 1000.0:
            self.settings.power = 1000.0
        if self.settings.power <= 0:
            self.settings.power = 0.0

    def set_pwm(self, power=1000.0):
        self.settings.power = power
        if self.power > 1000.0:
            self.settings.power = 1000.0
        if self.settings.power <= 0:
            self.settings.power = 0.0

    def set_d_ratio(self, d_ratio=None):
        self.settings.d_ratio = d_ratio

    def set_acceleration(self, accel=None):
        self.settings.acceleration = accel

    def set_step(self, step=None):
        self.settings.raster_step = step

    def set_overscan(self, overscan=None):
        self.settings.overscan = overscan

    def set_incremental(self, *values):
        self.is_relative = True

    def set_absolute(self, *values):
        self.is_relative = False

    def set_position(self, x, y):
        self.context.current_x = x
        self.context.current_y = y

    def wait(self, t):
        # TODO: This doesn't work without scheduler.
        self.next_run = t

    def wait_finish(self, *values):
        """Adds an additional holding requirement if the pipe has any data."""
        self.temp_holds.append(lambda: self.context._buffer_size != 0)

    def reset(self):
        self.context.spooler.clear_queue()
        self.spooled_item = None
        self.temp_holds.clear()

    def status(self):
        parts = list()
        parts.append("x=%f" % self.context.current_x)
        parts.append("y=%f" % self.context.current_y)
        parts.append("speed=%f" % self.settings.speed)
        parts.append("power=%d" % self.settings.power)
        status = ";".join(parts)
        self.context.signal("interpreter;status", status)

    def set_prop(self, mask):
        self.properties |= mask

    def unset_prop(self, mask):
        self.properties &= ~mask

    def is_prop(self, mask):
        return bool(self.properties & mask)

    def toggle_prop(self, mask):
        if self.is_prop(mask):
            self.unset_prop(mask)
        else:
            self.set_prop(mask)


class Spooler(Modifier):
    """
    The spooler module stores spoolable lasercode events as a synchronous queue.

    Spooler registers itself as the device.spooler object and provides a standard location to send data to an unknown
    device.

    * peek()
    * pop()
    * job(job)
    * jobs(iterable<job>)
    * job_if_idle(job) -- Will enqueue the job if the device is currently idle.
    * clear_queue()
    * remove(job)
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)
        self.queue_lock = Lock()
        self._queue = []

    def __repr__(self):
        return "Spooler()"

    def attach(self, *a, **kwargs):
        """Overloaded attach to demand .spooler attribute."""
        self.context.spooler = self

    def append(self, item):
        self.job(item)

    def peek(self):
        if len(self._queue) == 0:
            return None
        return self._queue[0]

    def pop(self):
        if len(self._queue) == 0:
            return None
        self.queue_lock.acquire(True)
        queue_head = self._queue[0]
        del self._queue[0]
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))
        return queue_head

    def job(self, *job):
        """
        Send a single job event with parameters as needed.

        The job can be a single command with (COMMAND_MOVE 20 20) or without parameters (COMMAND_HOME), or a generator
        which can yield many lasercode commands.

        :param job: job to send to the spooler.
        :return:
        """
        self.queue_lock.acquire(True)

        if len(job) == 1:
            self._queue.extend(job)
        else:
            self._queue.append(job)
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))

    def jobs(self, jobs):
        """
        Send several jobs generators to be appended to the end of the queue.

        The jobs parameter must be suitable to be .extended to the end of the queue list.
        :param jobs: jobs to extend
        :return:
        """
        self.queue_lock.acquire(True)
        if isinstance(jobs, (list, tuple)):
            self._queue.extend(jobs)
        else:
            self._queue.append(jobs)
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))

    def job_if_idle(self, element):
        if len(self._queue) == 0:
            self.job(element)
            return True
        else:
            return False

    def clear_queue(self):
        self.queue_lock.acquire(True)
        self._queue = []
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))

    def remove(self, element):
        self.queue_lock.acquire(True)
        self._queue.remove(element)
        self.queue_lock.release()
        self.context.signal("spooler;queue", len(self._queue))
