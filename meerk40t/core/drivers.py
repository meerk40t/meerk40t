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
    spooler in linear within a single spooler thread. If a method does not exist, it will not be called;
    it will be as if the command didn't exist. Some devices may have other functions which can equally be called through
    spooling particular lasercode.

    Most code however is processed as part of cutcode which is a series of native-coord commands which should be
    processed in order. These can include curves to cut and places to dwell the laser to be executed as part of a
    precompiled set of instructions. Cutcode can't do things like pause the laser or leave the rail unlocked, but should
    be permitted to execute various steps in order, and have that execution manipulated by the most of these remaining
    commands.
    """

    def __init__(self, context, name=None):
        self.context = context
        self.name = name
        self.settings = dict()

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

    def set(self, key, value):
        """
        Required.

        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.

        @param key:
        @param value:
        @return:
        """
        self.settings[key] = value

    def move_ori(self, x, y):
        """
        Requests laser move to origin offset position x,y in physical units

        @param x:
        @param y:
        @return:
        """

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

        @param type:
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

    def set_origin(self, x, y):
        """
        This should set the origin position for the laser. X, Y refer to the origin position. If these are None then the
        origin position should be set to the current position of the laser head (if possible).

        @param x:
        @param y:
        @return:
        """
        pass

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

    def status(self):
        """
        Asks that this device status be updated.

        @return:
        """
        parts = list()
        parts.append(f"x={self.native_x}")
        parts.append(f"y={self.native_y}")
        parts.append(f"speed={self.settings.get('speed', 0.0)}")
        parts.append(f"power={self.settings.get('power', 0)}")
        status = ";".join(parts)
        self.context.signal("driver;status", status)
