from functools import partial
import platform
import os
import time

from ..core.cutcode import LaserSettings
from ..device.lasercommandconstants import *
from ..kernel import Modifier
from .plotplanner import PlotPlanner

DRIVER_STATE_RAPID = 0
DRIVER_STATE_FINISH = 1
DRIVER_STATE_PROGRAM = 2
DRIVER_STATE_RASTER = 3
DRIVER_STATE_MODECHANGE = 4

PLOT_FINISH = 256
PLOT_RAPID = 4
PLOT_JOG = 2
PLOT_SETTING = 128
PLOT_AXIS = 64
PLOT_DIRECTION = 32


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("modifier/Drivers", Drivers)
        kernel_root = kernel.root
        kernel_root.activate("modifier/Drivers")
    elif lifecycle == "boot":
        pass


class Driver:
    """
    A driver takes spoolable commands and turns those commands into states and code in a language
    agnostic fashion. This is intended to be overridden by a subclass or class with the required methods.

    These drive hardware specific backend information from the reusable spoolers and server objects that may also be
    common within devices.
    """

    def __init__(self, context, name=None):
        self.context = context
        self.name = name
        self.root_context = context.root
        self.settings = LaserSettings()

        self.next = None
        self.prev = None

        self.spooler = None
        self.output = None

        self.process_item = None
        self.spooled_item = None
        self.holds = []
        self.temp_holds = []

        self.current_x = 0
        self.current_y = 0

        context.setting(bool, "plot_shift", False)
        self.plot_planner = PlotPlanner(self.settings)
        self.plot_planner.force_shift = context.plot_shift
        self.plot = None

        self.state = DRIVER_STATE_RAPID
        self.properties = 0
        self.is_relative = False
        self.laser = False
        self.root_context.setting(bool, "opt_rapid_between", True)
        self.root_context.setting(int, "opt_jog_mode", 0)
        self.root_context.setting(int, "opt_jog_minimum", 127)
        context._quit = False

        self.rapid = self.root_context.opt_rapid_between
        self.jog = self.root_context.opt_jog_mode
        self.rapid_override = False
        self.rapid_override_speed_x = 50.0
        self.rapid_override_speed_y = 50.0
        self._thread = None
        self._shutdown = False
        self.context.kernel.listen("lifecycle;ready", "", self.start_driver)
        self.context.kernel.listen("lifecycle;shutdown", "", self.shutdown)

        self.last_fetch = None

    def shutdown(self, *args, **kwargs):
        self.context.kernel.unlisten("lifecycle;ready", "", self.start_driver)
        self.context.kernel.unlisten("lifecycle;shutdown", "", self.shutdown)
        self._shutdown = True

    def start_driver(self, origin=None, *args):
        if self._thread is None:

            def clear_thread(*a):
                self._shutdown = True

            self._thread = self.context.threaded(
                self._driver_threaded,
                result=clear_thread,
                thread_name="Driver(%s)" % self.context.path,
            )
            self._thread.stop = clear_thread

    def _driver_threaded(self, *args):
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
            self.spooler.pop()
            return

        # We are dealing with an iterator/generator
        try:
            e = next(self.spooled_item)
            if not self.command(e):
                raise ValueError
        except StopIteration:
            # The spooled item is finished.
            self.spooled_item = None
            self.spooler.pop()

    def plotplanner_process(self):
        """
        Processes any data in the plot planner. Getting all relevant (x,y,on) plot values and performing the cardinal
        movements. Or updating the laser state based on the settings of the cutcode.

        :return: if execute tick was processed.
        """
        return False

    def _fetch_next_item_from_spooler(self):
        """
        Fetches the next item from the spooler.

        :return:
        """
        if self.spooler is None:
            return  # Spooler does not exist.
        element = self.spooler.peek()

        if self.last_fetch is not None:
            self.context.channel("spooler")(
                "Time between fetches: %f" % (time.time() - self.last_fetch)
            )
            self.last_fetch = None

        if element is None:
            return  # Spooler is empty.

        self.last_fetch = time.time()

        # self.spooler.pop()
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

        DRIVER_COMMANDS = {
            COMMAND_LASER_OFF:      (0, self.laser_off),
            COMMAND_LASER_ON:       (0, self.laser_on),
            COMMAND_LASER_DISABLE:  (0, self.laser_disable),
            COMMAND_LASER_ENABLE:   (0, self.laser_enable),
            COMMAND_CUT:            (2, self.cut),
            COMMAND_MOVE:           (2, self.move),
            COMMAND_HOME:           ("*", self.home),
            COMMAND_LOCK:           (0, self.lock_rail),
            COMMAND_UNLOCK:         (0, self.unlock_rail),
            COMMAND_PLOT:           (1, self.plot_plot),
            COMMAND_BLOB:           (2, self.send_blob),
            COMMAND_PLOT_START:     (0, self.plot_start),
            COMMAND_SET_SPEED:      (1, self.set_speed),
            COMMAND_SET_POWER:      (1, self.set_power),
            COMMAND_SET_PPI:        (1, self.set_ppi),
            COMMAND_SET_PWM:        (1, self.set_pwm),
            COMMAND_SET_STEP:       (1, self.set_step),
            COMMAND_SET_OVERSCAN:   (1, self.set_overscan),
            COMMAND_SET_ACCELERATION:   (1, self.set_acceleration),
            COMMAND_SET_D_RATIO:    (1, self.set_d_ratio),
            COMMAND_SET_INCREMENTAL:    (0, self.set_incremental),
            COMMAND_SET_ABSOLUTE:   (0, self.set_absolute),
            COMMAND_SET_POSITION:   (2, self.set_position),
            COMMAND_MODE_RAPID:     ("*", self.ensure_rapid_mode),
            COMMAND_MODE_PROGRAM:   ("*", self.ensure_program_mode),
            COMMAND_MODE_RASTER:    ("*", self.ensure_raster_mode),
            COMMAND_MODE_FINISHED:  ("*", self.ensure_finished_mode),
            COMMAND_WAIT:           (1, self.wait),
            COMMAND_WAIT_FINISH:    (0, self.wait_finish),
            COMMAND_BEEP:           (0, self.beep),
            COMMAND_FUNCTION:       ("*", self.func_exec),
            COMMAND_CONSOLE:        (1, self.console_exec),
            COMMAND_SIGNAL:         ("*", self.signal_exec),

            # The following codes have been commented out because they refer to methods or opt variables
            # that do not actually exist.
            # In the old code, that would not be a problem if the lines were not executed.
            # In this version, all methods / options needs to exist - and they should exist!

            # COMMAND_SET_DIRECTION:  (4, self.set_directions),
            # COMMAND_JOG:            (2, partial(self.jog, mode=0, min_jog=self.context.opt_jog_minimum)),
            # COMMAND_JOG_SWITCH:     (2, partial(self.jog, mode=1, min_jog=self.context.opt_jog_minimum)),
            # COMMAND_JOG_FINISH:     (2, partial(self.jog, mode=2, min_jog=self.context.opt_jog_minimum)),

            # However even with these lines commented out, the code still creates error messages to the console
            # that were previously just ignored.

            # I simply do not understand this code enough to debug it, so I am leaving this as a proof of concept.
        }

        if command in DRIVER_COMMANDS:
            n, fn = DRIVER_COMMANDS[command]
        else:
            self.context.channel("console")(
                "drivers.py: unknown command: {c}, args {v}".format(c=command, v=values),
            )
            return False
        if n != "*" and len(values) != n:
            self.context.channel("console")(
                "drivers.py: command {c} for {name} requires {n} args called with {l}: {v}".format(
                    c=command, name=fn.__name__, n=n, l=len(values), v=values,
                ),
            )
        fn(*values)

        return True

    def beep(self):
        OS_NAME = platform.system()
        if OS_NAME == "Windows":
            try:
                import winsound

                for x in range(5):
                    winsound.Beep(2000, 100)
            except Exception:
                pass
        elif OS_NAME == "Darwin": # Mac
            os.system('afplay /System/Library/Sounds/Ping.aiff')
        else: # Assuming other linux like system
            print("\a")  # Beep.

    def func_exec(self, t, *args):
        t(*args)

    def console_exec(self, fn, *args):
        fn = self.context.console_function(fn)
        fn(*args)

    def signal_exec(self, name, *args):
        if not args:
            args = None
        self.context.signal(name, *args)

    def realtime_command(self, command, *values):
        """Asks for the execution of a realtime command. Unlike the spooled commands these
        return False if rejected and something else if able to be performed. These will not
        be queued. If rejected. They must be performed in realtime or cancelled.
        """
        DRIVER_REALTIME = {
            REALTIME_PAUSE:         (0, self.pause),
            REALTIME_RESUME:        (0, self.resume),
            REALTIME_RESET:         (0, self.reset),
            REALTIME_STATUS:        (0, self.status),
            REALTIME_SAFETY_DOOR:   (0, self.safety_door),
            REALTIME_JOG_CANCEL:    ("*", self.jog_cancel),
            REALTIME_SPEED_PERCENT: ("*", self.realtime_speed_percent),
            REALTIME_SPEED:         ("*", self.realtime_speed),
            REALTIME_RAPID_PERCENT: ("*", self.realtime_rapid_percent),
            REALTIME_RAPID:         ("*", self.realtime_rapid),
            REALTIME_POWER_PERCENT: ("*", self.realtime_power_percent),
            REALTIME_POWER:         ("*", self.realtime_power),
            REALTIME_OVERSCAN:      ("*", self.realtime_overscan),
            REALTIME_LASER_DISABLE: ("*", self.realtime_laser_disable),
            REALTIME_LASER_ENABLE:  ("*", self.realtime_laser_enable),
            REALTIME_FLOOD_COOLANT: ("*", self.realtime_flood_coolant),
            REALTIME_MIST_COOLANT:  ("*", self.realtime_mist_coolant),
        }

        if command in DRIVER_REALTIME:
            n, fn = DRIVER_REALTIME[command]
        else:
            self.context.channel("console")(
                "drivers.py: unknown realtime: {c}, args {v}".format(c=command, v=values),
            )
            return False
        if n != "*" and len(values) != n:
            self.context.channel("console")(
                "drivers.py: realtime {c} for {name} requires {n} args called with {l}: {v}".format(
                    c=command, name=fn.__name__, n=n, l=len(values), v=values,
                ),
            )
        fn(*values)

        return True

    def data_output(self, e):
        self.output.write(e)

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

    def plot_plot(self, plot):
        """
        :param plot:
        :return:
        """
        self.plot_planner.push(plot)

    def plot_start(self):
        if self.plot is None:
            self.plot = self.plot_planner.gen()

    def jog(self, x, y, mode=0, min_jog=127):
        self.current_x = x
        self.current_y = y

    def move(self, x, y):
        self.current_x = x
        self.current_y = y

    def cut(self, x, y):
        self.current_x = x
        self.current_y = y

    def home(self, *values):
        self.current_x = 0
        self.current_y = 0

    def ensure_rapid_mode(self, *values):
        if self.state == DRIVER_STATE_RAPID:
            return
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)

    def ensure_finished_mode(self, *values):
        if self.state == DRIVER_STATE_FINISH:
            return
        self.state = DRIVER_STATE_FINISH
        self.context.signal("driver;mode", self.state)

    def ensure_program_mode(self, *values):
        if self.state == DRIVER_STATE_PROGRAM:
            return
        self.state = DRIVER_STATE_PROGRAM
        self.context.signal("driver;mode", self.state)

    def ensure_raster_mode(self, *values):
        if self.state == DRIVER_STATE_RASTER:
            return
        self.state = DRIVER_STATE_RASTER
        self.context.signal("driver;mode", self.state)

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
        if self.settings.power > 1000.0:
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
        self.current_x = x
        self.current_y = y

    def wait(self, t):
        time.sleep(float(t))

    def wait_finish(self, *values):
        """Adds an additional holding requirement if the pipe has any data."""
        self.temp_holds.append(lambda: len(self.output) != 0)

    def reset(self):
        if self.spooler is not None:
            self.spooler.clear_queue()
        self.plot_planner.clear()
        self.spooled_item = None
        self.temp_holds.clear()

    def status(self):
        parts = list()
        parts.append("x=%f" % self.current_x)
        parts.append("y=%f" % self.current_y)
        parts.append("speed=%f" % self.settings.speed)
        parts.append("power=%d" % self.settings.power)
        status = ";".join(parts)
        self.context.signal("driver;status", status)

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


class Drivers(Modifier):
    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)

    def get_driver(self, driver_name, **kwargs):
        dev = "device/%s" % driver_name
        try:
            return self.context.registered[dev][1]
        except (KeyError, IndexError):
            return None

    def get_or_make_driver(self, device_name, driver_type=None, **kwargs):
        dev = "device/%s" % device_name
        try:
            device = self.context.registered[dev]
        except KeyError:
            device = [None, None, None]
            self.context.registered[dev] = device
            self.context.signal("legacy_spooler_label", device_name)
        if device[1] is not None and driver_type is None:
            return device[1]
        try:
            for itype in self.context.match("driver/%s" % driver_type):
                driver_class = self.context.registered[itype]
                driver = driver_class(self.context, device_name, **kwargs)
                device[1] = driver
                self.context.signal("legacy_spooler_label", device_name)
                return driver
        except (KeyError, IndexError):
            return None

    def default_driver(self):
        return self.get_driver(self.context.root.active)

    def attach(self, *a, **kwargs):
        context = self.context
        context.drivers = self

        _ = self.context._

        @context.console_option("new", "n", type=str, help=_("new driver type"))
        @self.context.console_command(
            "driver",
            help=_("driver<?> <command>"),
            regex=True,
            input_type=(None, "spooler"),
            output_type="driver",
        )
        def driver_base(
            command, channel, _, data=None, new=None, remainder=None, **kwgs
        ):
            spooler = None
            if data is None:
                if len(command) > 6:
                    device_name = command[6:]
                    self.context.active = device_name
                else:
                    device_name = self.context.active
            else:
                spooler, device_name = data

            driver = self.get_or_make_driver(device_name, new)
            if driver is None:
                raise SyntaxError("No Driver.")

            if spooler is not None:
                try:
                    driver.spooler = spooler
                    spooler.next = driver
                    driver.prev = spooler
                except AttributeError:
                    pass
            elif remainder is None:
                channel(_("----------"))
                channel(_("Driver:"))
                for i, drv in enumerate(self.context.root.match("device", suffix=True)):
                    channel("%d: %s" % (i, drv))
                channel(_("----------"))
                channel(_("Driver %s:" % device_name))
                channel(str(driver))
                channel(_("----------"))
            return "driver", (driver, device_name)

        @self.context.console_command(
            "list",
            help=_("driver<?> list"),
            input_type="driver",
            output_type="driver",
        )
        def driver_list(command, channel, _, data_type=None, data=None, **kwgs):
            driver_obj, name = data
            channel(_("----------"))
            channel(_("Driver:"))
            for i, drv in enumerate(self.context.root.match("device", suffix=True)):
                channel("%d: %s" % (i, drv))
            channel(_("----------"))
            channel(_("Driver %s:" % name))
            channel(str(driver_obj))
            channel(_("----------"))
            return data_type, data

        @context.console_command(
            "type",
            help=_("list driver types"),
            input_type="driver",
        )
        def list_type(channel, _, **kwgs):
            channel(_("----------"))
            channel(_("Drivers permitted:"))
            for i, name in enumerate(context.match("driver/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))

        @self.context.console_command(
            "reset",
            help=_("driver<?> reset"),
            input_type="driver",
            output_type="driver",
        )
        def driver_reset(data_type=None, data=None, **kwargs):
            driver_obj, name = data
            driver_obj.reset()
            return data_type, data
