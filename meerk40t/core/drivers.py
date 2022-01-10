import os
import platform
import time

from ..core.cutcode import LaserSettings
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
        context._quit = False

        self._thread = None
        self._shutdown = False
        self.last_fetch = None


    # self.laser_off()
    # self.laser_on()
    # self.laser_disable()
    # self.laser_enable()
    # self.cut(x, y)
    # self.move(x, y)
    # self.home(*values)
    # self.lock_rail()
    # self.unlock_rail()
    # self.plot_plot(values[0])
    # self.send_blob(values[0], values[1])
    # self.plot_start()
    # self.set_speed(values[0])
    # self.set_power(values[0])
    # self.set_ppi(values[0])
    # self.set_pwm(values[0])
    # self.set_step(values[0])
    # self.set_overscan(values[0])
    # self.set_acceleration(values[0])
    # self.set_d_ratio(values[0])
    # self.set_directions(values[0], values[1], values[2], values[3])
    # self.set_incremental()
    # self.set_absolute()
    # self.set_position(values[0], values[1])
    # self.ensure_rapid_mode(*values)
    # self.ensure_program_mode(*values)
    # self.ensure_raster_mode(*values)
    # self.ensure_finished_mode(*values)
    # self.wait(values[0])
    # self.wait_finish()
    # self.function()
    # self.signal()
    # # Realtime:
    # self.pause()
    # self.resume()
    # self.reset()
    # self.status()


    def hold_work(self):
        return self.hold()

    def hold_idle(self):
        return False

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

    def jog(self, x, y, **kwargs):
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

    def rapid_mode(self, *values):
        if self.state == DRIVER_STATE_RAPID:
            return
        self.state = DRIVER_STATE_RAPID
        self.context.signal("driver;mode", self.state)

    def finished_mode(self, *values):
        if self.state == DRIVER_STATE_FINISH:
            return
        self.state = DRIVER_STATE_FINISH
        self.context.signal("driver;mode", self.state)

    def program_mode(self, *values):
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
