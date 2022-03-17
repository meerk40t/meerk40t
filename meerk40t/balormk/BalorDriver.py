import sys
import time

from meerk40t.core.parameters import Parameters

from balor.Cal import Cal
from balor.command_list import CommandList
from balor.sender import Sender, BalorMachineException


class BalorDriver(Parameters):
    def __init__(self, service):
        Parameters.__init__(self)
        self.service = service
        self.native_x = 0x8000
        self.native_y = 0x8000
        self.name = str(self.service)
        self.channel = self.service.channel("balor", buffer_size=50)
        self.connection = Sender(debug=self.channel)
        self.paused = False

        self.connected = False

        self.is_relative = False
        self.laser = False

        self._shutdown = False

        self.queue = []
        self.redlight_preferred = False

    def __repr__(self):
        return "BalorDriver(%s)" % self.name

    def service_attach(self):
        self._shutdown = False

    def service_detach(self):
        self._shutdown = True

    def connect_if_needed(self):
        if not self.connected:
            self.connect()

    def connect(self):
        """
        Connect to the Balor Sender

        :return:
        """
        self.connected = False
        while not self.connected:
            try:
                self.connected = self.connection.open(
                    mock=self.service.mock,
                    machine_index=self.service.machine_index,
                    cor_file=self.service.corfile,
                    first_pulse_killer=self.service.first_pulse_killer,
                    pwm_pulse_width=self.service.pwm_pulse_width,
                    pwm_half_period=self.service.pwm_half_period,
                    standby_param_1=self.service.standby_param_1,
                    standby_param_2=self.service.standby_param_2,
                    timing_mode=self.service.timing_mode,
                    delay_mode=self.service.delay_mode,
                    laser_mode=self.service.laser_mode,
                    control_mode=self.service.control_mode,
                    fpk2_p1=self.service.fpk2_p1,
                    fpk2_p2=self.service.fpk2_p2,
                    fpk2_p3=self.service.fpk2_p3,
                    fpk2_p4=self.service.fpk2_p3,
                    fly_res_p1=self.service.fly_res_p1,
                    fly_res_p2=self.service.fly_res_p2,
                    fly_res_p3=self.service.fly_res_p3,
                    fly_res_p4=self.service.fly_res_p4,
                )
                if self.redlight_preferred:
                    self.connection.light_on()
                else:
                    self.connection.light_off()
            except BalorMachineException as e:
                self.service.signal("pipe;usb_status", str(e))
                self.channel(str(e))
                return
            if not self.connected:
                self.service.signal("pipe;usb_status", "Connecting...")
                if self._shutdown:
                    self.service.signal("pipe;usb_status", "Failed to connect")
                    return
                time.sleep(1)
        self.connected = True
        self.service.signal("pipe;usb_status", "Connected")

    def disconnect(self):
        self.connection.close()
        self.connected = False
        self.service.signal("pipe;usb_status", "Disconnected")

    def group(self, plot):
        """
        avoids yielding any place where 0, 1, 2 are in a straight line or equal power.

        This might be a little naive compared to other methods of plotplanning but a general solution does not
        necessarily exist.
        :return:
        """
        plot = list(plot)
        for i in range(0, len(plot)):
            if len(plot[i]) == 2:
                try:
                    x0, y0 = plot[i - 1]
                    x1, y1 = plot[i]
                    x2, y2 = plot[i + 1]
                    if x2 - x1 == x1 - x0 and y2 - y1 == y1 - y0:
                        continue
                except IndexError:
                    pass
            else:
                try:
                    x0, y0, on0 = plot[i - 1]
                    x1, y1, on1 = plot[i]
                    x2, y2, on2 = plot[i + 1]
                    if (
                        x2 - x1 == x1 - x0
                        and y2 - y1 == y1 - y0
                        and on0 == on1
                        and on1 == on2
                    ):
                        continue
                except IndexError:
                    pass
            yield plot[i]

    # def cutcode_to_light_job(self, queue):
    #     """
    #     Converts a queue of cutcode operations into a light job.
    #
    #     The cutcode objects will have properties like speed. These are currently not being respected.
    #
    #     :param queue:
    #     :return:
    #     """
    #     cal = None
    #     if self.service.calibration_file is not None:
    #         try:
    #             cal = Cal(self.service.calibration_file)
    #         except TypeError:
    #             pass
    #     job = CommandList(cal=cal)
    #     job.set_travel_speed(self.service.travel_speed)
    #     for plot in queue:
    #         start = plot.start()
    #         job.light(start[0], start[1], False)
    #         for e in self.group(plot.generator()):
    #             on = 1
    #             if len(e) == 2:
    #                 x, y = e
    #             else:
    #                 x, y, on = e
    #             if on == 0:
    #                 try:
    #                     job.light(x, y, True)
    #                 except ValueError:
    #                     print("Not including this stroke path:", file=sys.stderr)
    #             else:
    #                 job.light(x, y, False)
    #     job.light_off()
    #     return job

    def cutcode_to_mark_job(self, queue):
        """
        Convert cutcode to a mark job.

        @param queue:
        @return:
        """
        cal = None
        if self.service.calibration_file is not None:
            try:
                cal = Cal(self.service.calibration_file)
            except TypeError:
                pass
        job = CommandList(cal=cal)
        job.set_mark_settings(
            travel_speed=self.service.travel_speed,
            power=self.service.laser_power,
            frequency=self.service.q_switch_frequency,
            cut_speed=self.service.cut_speed,
            laser_on_delay=100,
            laser_off_delay=100,
            polygon_delay=100,
        )
        job.set_write_port(self.connection.get_port())
        job.goto(0x8000, 0x8000)
        job.laser_control(True)
        last_on = None
        for plot in queue:
            start = plot.start
            job.goto(start[0], start[1])

            for e in self.group(plot.generator()):
                on = 1
                if len(e) == 2:
                    x, y = e
                else:
                    x, y, on = e
                if on == 0:
                    try:
                        job.goto(x, y)
                    except ValueError:
                        print("Not including this stroke path:", file=sys.stderr)
                else:
                    if last_on is None or on != last_on:
                        last_on = on
                        job.set_power(self.service.laser_power * on)
                    job.mark(x, y)
        job.laser_control(False)
        return job

    def hold_work(self):
        """
        This is checked by the spooler to see if we should hold any work from being processed from the work queue.

        For example if we pause, we don't want it trying to call some functions. Only priority jobs will execute if
        we hold the work queue. This is so that "resume" commands can be processed.

        :return:
        """
        return self.paused

    def hold_idle(self):
        """
        This is checked by the spooler to see if we should abort checking if there's any idle job after the work queue
        was found to be empty.
        :return:
        """
        return False

    def balor_job(self, job):
        self.connect_if_needed()
        self.connection.execute(job, 1)
        if self.redlight_preferred:
            self.connection.light_on()
        else:
            self.connection.light_off()

    def laser_off(self, *values):
        """
        This command expects to stop pulsing the laser in place.

        @param values:
        @return:
        """
        self.laser = False

    def laser_on(self, *values):
        """
        This command expects to start pulsing the laser in place.

        @param values:
        @return:
        """
        self.laser = True

    def plot(self, plot):
        """
        This command is called with bits of cutcode as they are processed through the spooler. This should be optimized
        bits of cutcode data with settings on them from paths etc.

        :param plot:
        :return:
        """
        self.queue.append(plot)

    def light(self, job):
        """
        This is not a typical meerk40t command. But, the light commands in the main balor add this as the idle job.

        self.spooler.set_idle(("light", self.driver.cutcode_to_light_job(cutcode)))
        That will the spooler's idle job be calling "light" on the driver with the light job. Which is a BalorJob.Job class
        We serialize that and hand it to the send_data routine of the connection.

        @param job:
        @return:
        """
        self.connect_if_needed()
        self.connection.light_off()
        self.connection.execute(job, 1)
        if self.redlight_preferred:
            self.connection.light_on()
        else:
            self.connection.light_off()

    def plot_start(self):
        """
        This is called after all the cutcode objects are sent. This says it shouldn't expect more cutcode for a bit.

        :return:
        """
        self.connect_if_needed()
        job = self.cutcode_to_mark_job(self.queue)
        self.queue = []
        self.connection.execute(job, 1)
        if self.redlight_preferred:
            self.connection.light_on()
        else:
            self.connection.light_off()

    def move_abs(self, x, y):
        """
        This is called with the actual x and y values with units. If without units we should expect to move in native
        units.

        :param x:
        :param y:
        :return:
        """
        self.connect_if_needed()
        unit_x = self.service.length(
            x, 0, relative_length=self.service.lens_size, as_float=True
        )
        unit_y = self.service.length(
            y, 1, relative_length=self.service.lens_size, as_float=True
        )
        unit_x *= self.service.get_native_scale_x
        unit_y *= self.service.get_native_scale_y
        self.native_x = unit_x
        self.native_y = unit_y

        if self.native_x > 0xFFFF:
            self.native_x = 0xFFFF
        if self.native_x < 0:
            self.native_x = 0

        if self.native_y > 0xFFFF:
            self.native_y = 0xFFFF
        if self.native_y < 0:
            self.native_y = 0

        self.connection.set_xy(self.native_x, self.native_y)

    def move_rel(self, dx, dy):
        """
        This is called with dx and dy values to move a relative amount.

        :param dx:
        :param dy:
        :return:
        """
        self.connect_if_needed()
        unit_dx = self.service.length(
            dx, 0, relative_length=self.service.lens_size, as_float=True
        )
        unit_dy = self.service.length(
            dy, 1, relative_length=self.service.lens_size, as_float=True
        )
        unit_dx *= self.service.get_native_scale_x
        unit_dy *= self.service.get_native_scale_y
        self.native_x += unit_dx
        self.native_y += unit_dy
        self.native_x = int(self.native_x)
        self.native_y = int(self.native_y)

        if self.native_x > 0xFFFF:
            self.native_x = 0xFFFF
        if self.native_x < 0:
            self.native_x = 0

        if self.native_y > 0xFFFF:
            self.native_y = 0xFFFF
        if self.native_y < 0:
            self.native_y = 0

        self.connection.set_xy(self.native_x, self.native_y)

    def home(self, x=None, y=None):
        """
        This is called with x, and y, to set an adjusted home or use whatever home we have.
        :param x:
        :param y:
        :return:
        """
        self.move_abs("50%", "50%")

    def blob(self, data_type, data):
        """
        This is called to give pure data to the backend. Data is assumed to be native data-type as loaded from a file.

        :param data_type:
        :param data:
        :return:
        """
        if data_type == "balor":
            self.connect_if_needed()
            self.connection.execute(data, 1)

    def set(self, attribute, value):
        """
        This is called to set particular attributes. These attributes will be set in the cutcode as well but sometimes
        there is a need to set these outside that context. This can also set the default values to be used inside
        the cutcode being processed.

        :param attribute:
        :param value:
        :return:
        """
        if attribute == "speed":
            pass
        print(attribute, value)

    def rapid_mode(self):
        """
        Expects to be in rapid jogging mode.
        :return:
        """
        pass

    def program_mode(self):
        """
        Expects to run jobs at a speed in a programmed mode.
        :return:
        """
        pass

    def raster_mode(self, *args):
        """
        Expects to run a raster job. Raster information is set in special modes to stop the laser head from moving
        too far.

        :return:
        """
        pass

    def wait_finished(self):
        """
        Expects to be caught up such that the next command will happen immediately rather than get queued.

        :return:
        """
        pass

    def function(self, function):
        function()

    def wait(self, secs):
        time.sleep(secs)

    def console(self, value):
        self.service(value)

    def beep(self):
        """
        Wants a system beep to be issued.

        :return:
        """
        self.service("beep\n")

    def signal(self, signal, *args):
        """
        Wants a system signal to be sent.

        :param signal:
        :param args:
        :return:
        """
        self.service.signal(signal, *args)

    def pause(self):
        """
        Wants the driver to pause.
        :return:
        """
        self.connect_if_needed()
        if self.paused:
            self.resume()
            return
        self.paused = True
        self.connection.raw_stop_list()

    def resume(self):
        """
        Wants the driver to resume.

        This typically issues from the realtime queue which means it will call even if we tell work_hold that we should
        hold the work.

        :return:
        """
        self.connect_if_needed()
        self.paused = False
        self.connection.raw_restart_list()

    def reset(self):
        """
        Wants the job to be aborted and action to be stopped.

        :return:
        """
        self.connection.abort()

    def status(self):
        """
        Wants a status report of what the driver is doing.
        :return:
        """
        pass
