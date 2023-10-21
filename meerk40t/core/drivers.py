import time

"""
A driver is a class which implements a set of various functions that are expected to be called to control a particular
laser. 

There is no guarantees with regard to what commands should exist other than `hold_work` which is required by the
spooler. Anything that accesses a driver is expected to call any would-be function as if it may generate an
AttributeError (because it might).
"""

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
    This driver is mostly an example. Nothing uses this and drivers are not required to implement this set of functions
    or any functions, except for hold_work(). get(), set(), and status(). If a particular laser implements something
    no other laser implements. A function should be implemented to access that functionality. If no code calls
    that function, then it will not execute. But, often these will get called with buttons or device specific
    implementations.

    However, most of the time the functions in this file will exist regardless of device, so calling these will be
    effective most of the time. However, sometimes things like unlock rail for a galvo laser (which has no rail) will
    not be implemented for obvious reasons. The driver will lack that function and any calling code will remain
    functional.
    """

    def __init__(self, context, name=None):
        self.context = context
        self.name = name
        self._settings = dict()

        self.native_x = 0
        self.native_y = 0
        self.hold = False
        self.paused = False

    def hold_work(self, priority):
        """
        Required.

        Spooler check. Test if the work cycle should be held, at the given priority.

        @return: hold?
        """
        return self.hold or self.paused

    def get(self, key, default=None):
        """
        Required.

        @param key: Key to get.
        @param default: Default value to use.
        @return:
        """
        return self._settings.get(key, default=default)

    def set(self, key, value):
        """
        Required.

        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.

        @param key:
        @param value:
        @return:
        """
        self._settings[key] = value

    def status(self):
        """
        Required.

        The first value in the status must be either idle, hold, busy.
        The secondary values are subclasses of this state. A hold can be a "door", "alarm", "paused", "hardware-paused",
        etc. depending on the laser. A busy can be the result of a "raster", "raw", "program", "light", or some
        other laser dependant information.

        The expectation is that the driver may query for this information from the laser if the laser provides this,
        otherwise you may receive the driver expected state.

        @return: position (2 or more axis), major-state, minor-state
        """
        state0 = "idle"
        state1 = "idle"
        if self.hold:
            state0 = "hold"
            state1 = "paused" if self.paused else "hold"
        return (self.native_x, self.native_y), state0, state1

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """

    def move_rel(self, dx, dy):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """

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
        Gives the driver cutcode that should be plotted/performed.

        @param plot:
        @return:
        """
        pass

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all cutcode as a group, if this
        is needed by the driver.

        @return:
        """

    def blob(self, data_type, data):
        """
        Blob sends a data blob. This is native code data of the give type. For example in a ruida device it might be a
        bunch of .rd code, or Lihuiyu device it could be .egv code. It's a method of sending pre-chewed data to the
        device.

        @param data_type:
        @param data:
        @return:
        """

    def home(self):
        """
        Home the laser.

        @return:
        """

    def physical_home(self):
        """ "
        This would be the command to go to a real physical home position (ie hitting endstops)
        """

    def lock_rail(self):
        """
        For plotter-style lasers this should prevent the laser bar from moving.

        @return:
        """

    def unlock_rail(self):
        """
        For plotter-style jobs this should free the laser head to be movable by the user.

        @return:
        """

    def rapid_mode(self, *values):
        """
        Rapid mode sets the laser to rapid state. This is usually moving the laser around without it executing a large
        batch of commands.

        @param values:
        @return:
        """

    def finished_mode(self, *values):
        """
        Finished mode is after a large batch of jobs is done. A transition to finished may require the laser process
        all the data in the buffer.

        @param values:
        @return:
        """

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands. Movements in program mode are
        expected to be executed in a list, program, compact mode etc. Depending on the type of driver.

        @param values:
        @return:
        """

    def raster_mode(self, *values):
        """
        Raster mode is a special form of program mode that suggests the batch of commands will be a raster operation
        many lasers have specialty modes for this mode. If the laser doesn't have such a mode, switching to generic
        program mode is sufficient.

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
        time.sleep(time_in_ms / 1000.0)

    def wait_finish(self, *values):
        """
        Wait finish should ensure that no additional commands be processed until the current buffer is completed. This
        does not necessarily imply a change in mode as "finished_mode" would require. Just that the buffer be completed
        before moving on.

        @param values:
        @return:
        """
        self.hold = True

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooling cycle.

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

    def console(self, value):
        """
        This asks that the console command be executed at the appropriate time within the spooled cycle.

        @param value: console command
        @return:
        """

    def signal(self, signal, *args):
        """
        This asks that this signal be broadcast at the appropriate time within the spooling cycle.

        @param signal:
        @param args:
        @return:
        """
        self.context.signal(signal, *args)

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

        To work this command should usually be put into the realtime work queue for the laser, without that it will
        be paused and unable to process the resume.

        @param args:
        @return:
        """
        self.paused = False

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.

        Asks that the device resets, and clears all current work.

        @param args:
        @return:
        """
