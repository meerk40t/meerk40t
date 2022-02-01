import time

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
    A driver is a class which implements the spoolable commands which are issued to the spooler by something in the
    system. The spooled command consist of a method and some data. These are sent to the driver associated with that
    spooler in linear order as the driver is ready to receive more data. If a method does not exist, it will
    not be called; it will be as if the command didn't exist.
    """

    def __init__(self, context, name=None):
        self.context = context
        self.name = name
        self.settings = dict()

        self.native_x = 0
        self.native_y = 0
        self.hold = False
        self.paused = False

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
        pass

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """

    def blob(self, data_type, data):
        """
        Blob sends a data blob. This is native code data of the give type. For example in a ruida device it might be a
        bunch of .rd code, or Lihuiyu device it could be egv code. It's a method of sending pre-chewed data to the
        device.

        @param type:
        @param data:
        @return:
        """

    def home(self, *values):
        """
        Home the laser.

        @param values:
        @return:
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
        Finished mode is after a large batch of jobs is done.

        @param values:
        @return:
        """

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands.
        @param values:
        @return:
        """

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
        pass

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

        To work this command should usually be put into the realtime work queue for the laser.

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

    def status(self):
        """
        Asks that this device status be updated.

        @return:
        """
        parts = list()
        parts.append("x=%f" % self.native_x)
        parts.append("y=%f" % self.native_y)
        parts.append("speed=%f" % self.settings.get("speed", 0.0))
        parts.append("power=%d" % self.settings.get("power", 0))
        status = ";".join(parts)
        self.context.signal("driver;status", status)
