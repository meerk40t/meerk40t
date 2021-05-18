import os
import time

from .plotplanner import PlotPlanner
from ..core.cutcode import LaserSettings
from ..device.lasercommandconstants import *
from ..kernel import Modifier

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
        kernel_root = kernel.get_context("/")
        kernel_root.activate("modifier/Drivers")
    elif lifecycle == "boot":
        pass


class Driver:
    """
    An Driver takes spoolable commands and turns those commands into states and code in a language
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

        self.plot_planner = PlotPlanner(self.settings)
        self.plot = None

        self.state = DRIVER_STATE_RAPID
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
        self.context._kernel.listen("lifecycle;ready", '', self.on_driver_ready)
        self.context._kernel.listen("lifecycle;shutdown", '', self.on_shutdown)

    def on_shutdown(self, *args, **kwargs):
        self.context._kernel.unlisten("lifecycle;ready", '', self.on_driver_ready)
        self.context._kernel.unlisten("lifecycle;shutdown", '', self.on_shutdown)
        self.thread = None

    def on_driver_ready(self, origin, *args):
        self.start_driver()

    def start_driver(self, *args):
        if self._thread is None:

            def clear_thread(*args):
                self._shutdown = True

            self._thread = self.context.threaded(
                self._driver_threaded,
                result=clear_thread,
                thread_name="Driver(%s)" % (self.context._path),
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
        if element is None:
            return  # Spooler is empty.

        self.spooler.pop()
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

    def data_output(self, e):
        self.output.write(e)

    def realtime_data_output(self, e):
        self.output.realtime_write(e)

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
        self.context.current_x = x
        self.context.current_y = y

    def wait(self, t):
        time.sleep(float(t))

    def wait_finish(self, *values):
        """Adds an additional holding requirement if the pipe has any data."""
        self.temp_holds.append(lambda: len(self.output) != 0)

    def reset(self):
        if self.spooler is not None:
            self.spooler.clear_queue()
        self.plot = None
        self.plot_planner.clear()
        self.spooled_item = None
        self.temp_holds.clear()

    def status(self):
        parts = list()
        parts.append("x=%f" % self.context.current_x)
        parts.append("y=%f" % self.context.current_y)
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
        if device[1] is not None and driver_type is None:
            return device[1]
        try:
            for itype in self.context.match("driver/%s" % driver_type):
                driver_class = self.context.registered[itype]
                driver = driver_class(self.context, device_name, **kwargs)
                device[1] = driver
                return driver
        except (KeyError, IndexError):
            return None

    def default_driver(self):
        return self.get_driver(self.context.root.active)

    def attach(self, *a, **kwargs):
        context = self.context
        context.drivers = self

        kernel = self.context._kernel
        _ = kernel.translation

        @context.console_option("new", "n", type=str, help="new driver type")
        @self.context.console_command(
            "driver",
            help="driver<?> <command>",
            regex=True,
            input_type=(None, "spooler"),
            output_type="driver",
        )
        def driver(command, channel, _, data=None, new=None, remainder=None, **kwargs):
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
            help="driver<?> list",
            input_type="driver",
            output_type="driver",
        )
        def driver_list(command, channel, _, data_type=None, data=None, **kwargs):
            driver, name = data
            channel(_("----------"))
            channel(_("Driver:"))
            for i, drv in enumerate(self.context.root.match("device", suffix=True)):
                channel("%d: %s" % (i, drv))
            channel(_("----------"))
            channel(_("Driver %s:" % name))
            channel(str(driver))
            channel(_("----------"))
            return data_type, data

        @context.console_command(
            "type",
            help="list driver types",
            input_type="driver",
        )
        def list_type(channel, _, **kwargs):
            channel(_("----------"))
            channel(_("Drivers permitted:"))
            for i, name in enumerate(context.match("driver/", suffix=True)):
                channel("%d: %s" % (i + 1, name))
            channel(_("----------"))

        @self.context.console_command(
            "reset",
            help="driver<?> reset",
            input_type="driver",
            output_type="driver",
        )
        def driver_reset(data_type=None, data=None, **kwargs):
            driver, name = data
            driver.reset()
            return data_type, data
