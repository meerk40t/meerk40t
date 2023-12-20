"""
Ruida Driver

The Driver has a set of different commands which are sent and utilizes those which can be performed by this driver.
"""
import time

from meerk40t.core.cutcode.cubiccut import CubicCut
from meerk40t.core.cutcode.dwellcut import DwellCut
from meerk40t.core.cutcode.gotocut import GotoCut
from meerk40t.core.cutcode.homecut import HomeCut
from meerk40t.core.cutcode.inputcut import InputCut
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.cutcode.outputcut import OutputCut
from meerk40t.core.cutcode.plotcut import PlotCut
from meerk40t.core.cutcode.quadcut import QuadCut
from meerk40t.core.cutcode.waitcut import WaitCut
from meerk40t.core.drivers import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from meerk40t.core.laserjob import LaserJob
from meerk40t.core.parameters import Parameters
from meerk40t.core.plotplanner import PlotPlanner
from meerk40t.ruida.encoder import RuidaEncoder
from meerk40t.tools.geomstr import Geomstr


class RuidaDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.native_x = 0
        self.native_y = 0
        self.name = str(self.service)

        name = self.service.label.replace(" ", "-")
        name = name.replace("/", "-")
        send = service.channel(f"{name}/send")
        self.encoder = RuidaEncoder(send, send)

        self.encoder.set_magic(service.magic)
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.recv.watch(self.encoder.recv)

        self.on_value = 0
        self.power_dirty = True
        self.speed_dirty = True
        self.absolute_dirty = True
        self._absolute = True
        self.paused = False
        self.is_relative = False
        self.laser = False

        self._shutdown = False

        self.queue = list()
        self.plot_planner = PlotPlanner(
            dict(), single=True, ppi=False, shift=False, group=True
        )
        self._aborting = False

    def __repr__(self):
        return f"RuidaDriver({self.name})"

    #############
    # DRIVER COMMANDS
    #############

    def _calculate_layer_bounds(self, layer):
        max_x = float("-inf")
        max_y = float("-inf")
        min_x = float("inf")
        min_y = float("inf")
        for item in layer:
            try:
                ny = item.upper()
                nx = item.left()

                my = item.lower()
                mx = item.right()
            except AttributeError:
                continue

            if mx > max_x:
                max_x = mx
            if my > max_y:
                max_y = my
            if nx < min_x:
                min_x = nx
            if ny < min_y:
                min_y = ny
        return min_x, min_y, max_x, max_y

    def job_start(self, job):
        pass

    def job_finish(self, job):
        pass

    def hold_work(self, priority):
        """
        This is checked by the spooler to see if we should hold any work from being processed from the work queue.

        For example if we pause, we don't want it trying to call some functions. Only priority jobs will execute if
        we hold the work queue. This is so that "resume" commands can be processed.

        @return:
        """
        return priority <= 0 and self.paused

    def get(self, key, default=None):
        """
        Required.

        @param key: Key to get.
        @param default: Default value to use.
        @return:
        """
        return default

    def set(self, key, value):
        """
        Required.

        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.

        @param key:
        @param value:
        @return:
        """

    def status(self):
        """
        Wants a status report of what the driver is doing.
        @return:
        """
        x, y = self.encoder.get_last_xy()
        state_major, state_minor = self.encoder.state
        return (x, y), state_major, state_minor

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

        @param plot:
        @return:
        """
        self.queue.append(plot)

    def _write_header(self):
        self.encoder.start_record()
        if not self.queue:
            return
        # Optional: Set Tick count.
        self.encoder.ref_point_2()  # abs_pos
        self.encoder.set_absolute()
        self.encoder.ref_point_set()
        self.encoder.enable_block_cutting(0)
        # Optional: Set File Property 1
        self.encoder.start_process()
        self.encoder.feed_repeat(0, 0)
        self.encoder.set_feed_auto_pause(0)
        b = self._calculate_layer_bounds(self.queue)
        min_x, min_y, max_x, max_y = b
        self.encoder.process_top_left(min_x, min_y)
        self.encoder.process_bottom_right(max_x, max_y)
        self.encoder.document_min_point(0, 0)  # Unknown
        self.encoder.document_max_point(max_x, max_y)
        self.encoder.process_repeat(1, 1, 0, 0, 0, 0, 0)
        self.encoder.array_direction(0)
        last_settings = None
        layers = list()

        # Sort out data by layers.
        for item in self.queue:
            if not hasattr(item, "settings"):
                continue
            current_settings = item.settings
            if last_settings is not current_settings:
                if "part" not in current_settings:
                    current_settings["part"] = len(layers)
                    layers.append(list())
            layers[current_settings["part"]].append(item)

        part = 0
        # Write layer Information
        for layer in layers:
            (
                layer_min_x,
                layer_min_y,
                layer_max_x,
                layer_max_y,
            ) = self._calculate_layer_bounds(layer)
            current_settings = layer[0].settings

            # Current Settings is New.
            part = current_settings.get("part", 0)
            speed = current_settings.get("speed", 10)
            power = current_settings.get("power", 1000) / 10.0
            color = current_settings.get("line_color", 0)

            self.encoder.speed_laser_1_part(part, speed)
            self.encoder.min_power_1_part(part, power)
            self.encoder.max_power_1_part(part, power)
            self.encoder.min_power_2_part(part, power)
            self.encoder.max_power_2_part(part, power)
            self.encoder.layer_color_part(part, color)
            self.encoder.work_mode_part(part, 0)
            self.encoder.part_min_point(part, layer_min_x, layer_min_y)
            self.encoder.part_max_point(part, layer_max_x, layer_max_y)
            self.encoder.part_min_point_ex(part, layer_min_x, layer_min_y)
            self.encoder.part_max_point_ex(part, layer_max_x, layer_max_y)
        self.encoder.max_layer_part(part)
        self.encoder.pen_offset(0, 0)
        self.encoder.pen_offset(1, 0)
        self.encoder.layer_offset(0, 0)
        self.encoder.layer_offset(1, 0)
        self.encoder.display_offset(0, 0)

        # Element Info
        # self.encoder.element_max_index(0)
        # self.encoder.element_name_max_index(0)
        # self.encoder.element_index(0)
        # self.encoder.element_name_max_index(0)
        # self.encoder.element_name('\x05*9\x1cA\x04j\x15\x08 ')
        # self.encoder.element_array_min_point(min_x, min_y)
        # self.encoder.element_array_max_point(max_x, max_y)
        # self.encoder.element_array(1, 1, 0, 257, -3072, 2, 5232)
        # self.encoder.element_array_add(0,0)
        # self.encoder.element_array_mirror(0)

        self.encoder.feed_info(0)

        # Array Info
        array_index = 0
        self.encoder.array_start(array_index)
        self.encoder.set_current_element_index(array_index)
        self.encoder.array_en_mirror_cut(array_index)
        self.encoder.array_min_point(min_x, min_y)
        self.encoder.array_max_point(max_x, max_y)
        self.encoder.array_add(0, 0)
        self.encoder.array_mirror(0)
        # self.encoder.array_even_distance(0)  # Unknown.
        self.encoder.array_repeat(1, 1, 0, 1123, -3328, 4, 3480)  # Unknown.
        # Layer and cut information.

    def _write_tail(self):
        # End layer and cut information.
        self.encoder.array_end()
        self.encoder.block_end()
        # self.encoder.set_setting(0x320, 142, 142)
        self.encoder.set_file_sum(self.encoder.calculate_filesum())
        self.encoder.end_of_file()
        self.encoder.stop_record()

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        # Write layer header information.
        self._write_header()
        first = True
        last_settings = None
        for q in self.queue:
            if hasattr(q, "settings"):
                current_settings = q.settings
                if current_settings is not last_settings:
                    part = current_settings.get("part", 0)
                    speed = current_settings.get("speed", 0)
                    power = current_settings.get("power", 0) / 10.0
                    air = current_settings.get("air", True)
                    self.encoder.layer_end()
                    self.encoder.layer_number_part(part)
                    self.encoder.laser_device_0()
                    if air:
                        self.encoder.air_assist_on()
                    else:
                        self.encoder.air_assist_off()
                    self.encoder.speed_laser_1(speed)
                    self.encoder.laser_on_delay(0)
                    self.encoder.laser_off_delay(0)
                    self.encoder.min_power_1(power)
                    self.encoder.max_power_1(power)
                    self.encoder.min_power_2(power)
                    self.encoder.max_power_2(power)
                    self.encoder.en_laser_tube_start()
                    self.encoder.en_ex_io(0)
                    last_settings = current_settings

            x = self.native_x
            y = self.native_y
            start_x, start_y = q.start
            if x != start_x or y != start_y or first:
                self.on_value = 0
                self.power_dirty = True

                first = False
                self._move(start_x, start_y, cut=False)
            if self.on_value != 1.0:
                self.power_dirty = True
            self.on_value = 1.0
            # Default-Values?!
            qpower = q.settings.get("power", self.power)
            qspeed = q.settings.get("speed", self.speed)
            qraster_step_x = q.settings.get("raster_step_x")
            qraster_step_y = q.settings.get("raster_step_y")
            if qpower != self.power:
                self.set("power", qpower)
            if (
                qspeed != self.speed
                or qraster_step_x != self.raster_step_x
                or qraster_step_y != self.raster_step_y
            ):
                self.set("speed", qspeed)
            self.settings.update(q.settings)
            if isinstance(q, LineCut):
                self._move(*q.end, cut=True)
            elif isinstance(q, QuadCut):
                interp = self.service.interpolate
                g = Geomstr()
                g.quad(complex(*q.start), complex(*q.c()), complex(*q.end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag, cut=True)
            elif isinstance(q, CubicCut):
                interp = self.service.interpolate
                g = Geomstr()
                g.cubic(
                    complex(*q.start),
                    complex(*q.c1()),
                    complex(*q.c2()),
                    complex(*q.end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag, cut=True)
            elif isinstance(q, WaitCut):
                self.wait(q.dwell_time)
            elif isinstance(q, HomeCut):
                self.home()
            elif isinstance(q, GotoCut):
                start = q.start
                self._move(start[0], start[1], cut=True)
            elif isinstance(q, DwellCut):
                self.dwell(q.dwell_time)
            elif isinstance(q, (InputCut, OutputCut)):
                # Ruida has no core GPIO functionality
                pass
            elif isinstance(q, PlotCut):
                self.set("power", 1000)
                for ox, oy, on, x, y in q.plot:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    # q.plot can have different on values, these are parsed
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y, cut=True)
            else:
                #  Rastercut
                self.plot_planner.push(q)
                for x, y, on in self.plot_planner.gen():
                    while self.hold_work(0):
                        time.sleep(0.05)
                    if on > 1:
                        # Special Command.
                        if isinstance(on, float):
                            on = int(on)
                        if on & PLOT_FINISH:  # Plot planner is ending.
                            break
                        elif on & PLOT_SETTING:  # Plot planner settings have changed.
                            p_set = Parameters(self.plot_planner.settings)
                            if p_set.power != self.power:
                                self.set("power", p_set.power)
                            if (
                                p_set.speed != self.speed
                                or p_set.raster_step_x != self.raster_step_x
                                or p_set.raster_step_y != self.raster_step_y
                            ):
                                self.set("speed", p_set.speed)
                            self.settings.update(p_set.settings)
                        elif on & (
                            PLOT_RAPID | PLOT_JOG
                        ):  # Plot planner requests position change.
                            self._move(x, y, cut=False)
                        continue
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    self._move(x, y, cut=True)
        self.queue.clear()
        # Ruida end data.
        self._write_tail()
        return False

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        old_current = self.service.current
        self.encoder.speed_laser_1(100.0)
        self.encoder.min_power_1(0)
        self.encoder.min_power_2(0)

        x, y = self.service.view.position(x, y)

        dx = x - self.native_x
        dy = y - self.native_y
        if dx == 0:
            if dy != 0:
                self.encoder.rapid_move_y(dy)
        elif dy == 0:
            self.encoder.rapid_move_x(dx)
        else:
            self.encoder.rapid_move_xy(dx, dy)
        self.native_x = x
        self.native_y = y
        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def move_rel(self, dx, dy):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        old_current = self.service.current
        dx, dy = self.service.view.position(dx, dy, vector=True)
        if dx == 0:
            if dy != 0:
                self.encoder.rapid_move_y(dy)
        elif dy == 0:
            self.encoder.rapid_move_x(dx)
        else:
            self.encoder.rapid_move_xy(dx, dy)
        self.native_x += dx
        self.native_y += dy
        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )

    def focusz(self):
        """
        This is a FocusZ routine on the Ruida Device.
        @return:
        """
        self.encoder.focus_z()

    def home(self):
        """
        This is called home, returns to center.

        @return:
        """
        self.move_abs(0, 0)

    def physical_home(self):
        """ "
        This would be the command to go to a real physical home position (ie hitting endstops)
        """
        self.encoder.home_xy()

    def rapid_mode(self):
        """
        Expects to be in rapid jogging mode.
        @return:
        """
        self.encoder.rapid_mode()

    def program_mode(self):
        """
        Expects to run jobs at a speed in a programmed mode.
        @return:
        """
        self.encoder.program_mode()

    def raster_mode(self, *args):
        """
        Expects to run a raster job. Raster information is set in special modes to stop the laser head from moving
        too far.

        @return:
        """
        pass

    def wait_finished(self):
        """
        Expects to be caught up such that the next command will happen immediately rather than get queued.

        @return:
        """
        self.encoder.wait_finished()

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooling cycle.

        @param function:
        @return:
        """
        function()

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

    def console(self, value):
        """
        This asks that the console command be executed at the appropriate time within the spooled cycle.

        @param value: console command
        @return:
        """
        self.service(value)

    def beep(self):
        """
        Wants a system beep to be issued.
        This command asks that a beep be executed at the appropriate time within the spooled cycle.

        @return:
        """
        self.service("beep\n")

    def signal(self, signal, *args):
        """
        Wants a system signal to be sent.

        @param signal:
        @param args:
        @return:
        """
        self.service.signal(signal, *args)

    def pause(self):
        """
        Wants the driver to pause.
        @return:
        """
        if self.paused:
            self.resume()
            return
        self.paused = True
        self.encoder.pause()
        self.service.signal("pause")

    def resume(self):
        """
        Wants the driver to resume.

        This typically issues from the realtime queue which means it will call even if we tell work_hold that we should
        hold the work.

        @return:
        """
        self.paused = False
        self.encoder.resume()
        self.service.signal("pause")

    def reset(self):
        """
        Wants the job to be aborted and action to be stopped.

        @return:
        """
        self.encoder.abort()
        self.paused = False
        self.service.signal("pause")

    def dwell(self, time_in_ms):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        self.encoder.laser_interval(time_in_ms)

    def set_abort(self):
        self._aborting = True

    ####################
    # PROTECTED DRIVER CODE
    ####################

    def _encode_move(self, x, y):
        dx = x - self.native_x
        dy = y - self.native_y
        if dx == 0 and dy == 0:
            # We are not moving.
            return

        if abs(dx) > 8192 or abs(dy) > 8192:
            # Exceeds encoding limit, use abs.
            self.encoder.move_abs_xy(x, y)
            return

        if dx == 0:
            # Y-relative.
            self.encoder.move_rel_y(dy)
            return
        if dy == 0:
            # X-relative.
            self.encoder.move_rel_x(dx)
            return
        self.encoder.move_rel_xy(dx, dy)

    def _encode_cut(self, x, y):
        dx = x - self.native_x
        dy = y - self.native_y
        if dx == 0 and dy == 0:
            # We are not moving.
            return

        if abs(dx) > 8192 or abs(dy) > 8192:
            # Exceeds encoding limit, use abs.
            self.encoder.cut_abs_xy(x, y)
            return

        if dx == 0:
            # Y-relative.
            self.encoder.cut_rel_y(dy)
            return
        if dy == 0:
            # X-relative.
            self.encoder.cut_rel_x(dx)
            return
        self.encoder.cut_rel_xy(dx, dy)

    def _move(self, x, y, cut=True):
        old_current = self.service.current
        if self.power_dirty:
            if self.power is not None:
                self.encoder.max_power_1(self.power / 10.0 * self.on_value)
                self.encoder.min_power_1(self.power / 10.0 * self.on_value)
            self.power_dirty = False
        if self.speed_dirty:
            self.encoder.speed_laser_1(self.speed)
            self.speed_dirty = False
        if cut:
            self._encode_cut(x, y)
        else:
            self._encode_move(x, y)
        self.native_x = x
        self.native_y = y
        new_current = self.service.current
        self.service.signal(
            "driver;position",
            (old_current[0], old_current[1], new_current[0], new_current[1]),
        )
