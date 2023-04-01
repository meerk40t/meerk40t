"""
Newly Controller
"""
import math
import struct
import time

from meerk40t.core.cutcode.rastercut import RasterCut
from meerk40t.newly.mock_connection import MockConnection
from meerk40t.newly.usb_connection import USBConnection


class NewlyController:
    """
    Newly Controller
    """

    def __init__(
        self,
        service,
        x=0,
        y=0,
        force_mock=False,
    ):
        self._machine_index = 0
        self.service = service
        self.force_mock = force_mock
        self.is_shutdown = False  # Shutdown finished.

        name = self.service.label
        self.usb_log = service.channel(f"{name}/usb", buffer_size=500)
        self.usb_log.watch(lambda e: service.signal("pipe;usb_status", e))

        self.connection = None
        self._is_opening = False
        self._abort_open = False
        self._disable_connect = False

        self._last_x = x
        self._last_y = y

        self._set_power = None
        self._set_speed = None
        self._set_pwm_freq = None
        self._set_relative_mode = None

        self._cut_dc = None
        self._move_dc = None
        self._speed = None
        self._power = None
        self._pwm_frequency = None
        self._selected_pen = None
        self._speed_mode = None
        self._relative = None

        self._realtime = False

        self.raster_bit_depth = 1

        self.mode = "init"
        self.paused = False
        self.command_buffer = []

    def __call__(self, cmd, *args, **kwargs):
        if isinstance(cmd, str):
            # Any string data sent is latin-1 encoded.
            self.command_buffer.append(cmd.encode("latin-1"))
        else:
            self.command_buffer.append(cmd)

    def set_disable_connect(self, status):
        self._disable_connect = status

    def added(self):
        pass

    def service_detach(self):
        pass

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    @property
    def connected(self):
        if self.connection is None:
            return False
        return self.connection.is_open(self._machine_index)

    @property
    def is_connecting(self):
        if self.connection is None:
            return False
        return self._is_opening

    def abort_connect(self):
        self._abort_open = True
        self.usb_log("Connect Attempts Aborted")

    def disconnect(self):
        try:
            self.connection.close(self._machine_index)
        except (ConnectionError, ConnectionRefusedError, AttributeError):
            pass
        self.connection = None
        # Reset error to allow another attempt
        self.set_disable_connect(False)

    def connect_if_needed(self):
        if self._disable_connect:
            # After many failures automatic connects are disabled. We require a manual connection.
            self.abort_connect()
            self.connection = None
            raise ConnectionRefusedError(
                "NewlyController was unreachable. Explicit connect required."
            )
        if self.connection is None:
            if self.service.setting(bool, "mock", False) or self.force_mock:
                self.connection = MockConnection(self.usb_log)
                name = self.service.label
                self.connection.send = self.service.channel(f"{name}/send")
                self.connection.recv = self.service.channel(f"{name}/recv")
            else:
                self.connection = USBConnection(self.usb_log)
        self._is_opening = True
        self._abort_open = False
        count = 0
        while not self.connection.is_open(self._machine_index):
            try:
                if self.connection.open(self._machine_index) < 0:
                    raise ConnectionError
                self.init_laser()
            except (ConnectionError, ConnectionRefusedError):
                time.sleep(0.3)
                count += 1
                # self.usb_log(f"Error-Routine pass #{count}")
                if self.is_shutdown or self._abort_open:
                    self._is_opening = False
                    self._abort_open = False
                    return
                if self.connection.is_open(self._machine_index):
                    self.connection.close(self._machine_index)
                if count >= 10:
                    # We have failed too many times.
                    self._is_opening = False
                    self.set_disable_connect(True)
                    self.usb_log("Could not connect to the controller.")
                    self.usb_log("Automatic connections disabled.")
                    raise ConnectionRefusedError("Could not connect to the controller.")
                time.sleep(0.3)
                continue
        self._is_opening = False
        self._abort_open = False

    #######################
    # MODE SHIFTS
    #######################

    def realtime_job(self, job=None):
        """
        Starts a realtime job, which runs on file0
        @return:
        """
        if self.mode != "init":
            return
        self._realtime = True
        self.mode = "realtime"
        self(f"ZZZFile0")
        self._clear_settings()

    def _write_position(self, outline):
        pass

    def _write_frame(self, outline):
        self.mode = "frame"
        if outline is not None:
            x, y = self._last_x, self._last_y
            self("DW")
            self._write_dc_information()
            self._write_pen_info(2)
            self._set_speed = self.service.moving_speed
            self._set_power = 0
            self._write_speed_info(vector=True)
            self._write_power_info(vector=True)
            self._set_relative()
            for pt in outline:
                self.mark(*pt)
            self.mark(x, y)
            self._clear_settings()
            self("ZED")

    def _execute_job(self):
        self("ZED")
        cmd = b";".join(self.command_buffer) + b";"
        self.connect_if_needed()
        self.connection.write(index=self._machine_index, data=cmd)
        self.command_buffer.clear()
        self._clear_settings()

    def open_job(self, job=None):
        """
        Opens a job at the declared file_index

        @return:
        """

        outline = None
        try:
            # print(job.outline)
            outline = job.outline
        except AttributeError:
            pass

        if outline is not None:
            self.set_xy(*outline[0], relative=False)

        self._realtime = False
        self._speed = None
        self._power = None
        self(f"ZZZFile{self.service.file_index}")
        self._write_frame(outline)
        self("GZ")
        self._clear_settings()

    def close_job(self, job=None):
        """
        Closes the file and sends.
        @return:
        """
        if not self.command_buffer:
            return
        if self.mode in ("realtime", "init"):
            # Job contains no instructions.
            self.mode = "init"
            self.command_buffer.clear()
            return
        self._execute_job()
        self.mode = "init"
        if self.service.autoplay and not self._realtime:
            self.replay(self.service.file_index)

    def _map_raster_speed(self, speed):
        v = int(round(speed / 10))
        if v == 0:
            v = 1
        return v

    def _map_vector_speed(self, speed):
        if speed >= 93:
            return int(round(speed / 10))
        if speed >= 15:
            return 162 + int(round(speed))
        if speed >= 5:
            return 147 + int(round(speed * 2))
        if speed >= 1:
            return 132 + int(round(speed * 5))
        else:
            return 127 + int(round(speed * 10))

    def _map_power(self, power):
        power /= 1000.0  # Scale to 0-1
        power *= self.service.max_power  # Scale by max power %
        power *= 255.0 / 100.0  # range between 000 and 255
        if power > 255:
            return 255
        if power <= 0:
            return 0
        return int(round(power))

    def _clear_settings(self):
        self._set_power = None
        self._set_speed = None
        self._set_pwm_freq = None
        self._set_relative_mode = None

        self._cut_dc = None
        self._move_dc = None
        self._speed = None
        self._power = None
        self._pwm_frequency = None
        self._corner_speed = None
        self._acceleration_length = None
        self._selected_pen = None
        self._speed_mode = None
        self._relative = None

    def _write_dc_information(self):
        if self._cut_dc != self.service.cut_dc:
            self._cut_dc = self.service.cut_dc
            self(f"VP{self._cut_dc}")

        if self._move_dc != self.service.move_dc:
            self._move_dc = self.service.move_dc
            self(f"VK{self._move_dc}")

    def _get_chart_settings_for_speed(self, speed):
        """
        Get charted settings for a particular speed. Given a speed this provides other required settings for this
        same speed.

        @param speed:
        @return:
        """
        chart = self.service.speedchart
        smallest_difference = float("inf")
        closest_index = None
        for i, c in enumerate(chart):
            chart_speed = c.get("speed", 0)
            delta_speed = chart_speed - speed
            if (
                    chart_speed > speed
                    and smallest_difference > delta_speed
            ):
                smallest_difference = delta_speed
                closest_index = i
        if closest_index is not None:
            return chart[closest_index]
        return chart[-1]

    def _write_power_info(self, vector=False):
        """
        Write power information. If the _set_power is set then it takes priority. Otherwise, the power remains set to
        what it was previously set to. If no power is set, then power is set to the default cut power.

        @return:
        """
        requested_power = self._set_power
        self._set_power = None
        if requested_power is not None:
            # Requested power is the priority.
            new_power = requested_power
        elif self._power is None:
            # No power is set, use default.
            if vector:
                new_power = self.service.default_cut_power
            else:
                new_power = self.service.default_raster_power
        else:
            # no new power is requested and a power already exists.
            return
        if new_power != self._power:
            # Already set power is not the new_power setting.
            self._power = new_power
            self(f"DA{self._map_power(self._power)}")

    def _write_pen_info(self, pen):
        if self._selected_pen != pen:
            self._selected_pen = pen
            self(f"SP{int(pen)}")

    def _write_pwmfreq_info(self):
        """
        Write pwm frequency information.
        @return:
        """
        requested_pwmfreq = self._set_pwm_freq
        self._set_pwm_freq = None

        if requested_pwmfreq is not None:
            # Priority requested frequency
            new_freq = requested_pwmfreq
        elif self._pwm_frequency is None:
            # Frequency is not set.
            if self.service.pwm_enabled:
                # Frequency should be set.
                new_freq = self.service.pwm_frequency
            else:
                # Frequency should not be set. Exit.
                return
        else:
            # no new frequency is requested and one is already set.
            return
        if new_freq != self._pwm_frequency:
            self._pwm_frequency = new_freq
            # Frequency is needed, and different
            self(f"PL{self._pwm_frequency}")

    def _write_speed_info(self, vector=True):
        speed_mode = "vector" if vector else "raster"

        requested_speed = self._set_speed
        self._set_speed = None
        if requested_speed is not None:
            # Priority speed is requested.
            new_speed = requested_speed
        elif self._speed is None or self._speed_mode != speed_mode:
            # Priority speed is not requested but speed is unset or mode is changed.
            if vector:
                new_speed = self.service.default_cut_speed
            else:
                new_speed = self.service.default_raster_speed
        else:
            # No speed is requested, and a speed is already set.
            return

        if new_speed != self._speed or self._speed_mode != speed_mode:
            self._speed_mode = speed_mode
            self._speed = new_speed
            settings = self._get_chart_settings_for_speed(new_speed)
            self(f"VQ{int(round(settings['corner_speed']))}")
            self(f"VJ{int(round(settings['acceleration_length']))}")
            self._write_pen_info(1)
            if vector:
                self(f"VS{self._map_vector_speed(new_speed)}")
            else:
                self(f"VS{self._map_raster_speed(new_speed)}")

    def _write_relative_mode(self):
        if self._relative is None:
            self._relative = self._set_relative_mode
            self._set_relative_mode = None
            if self._relative:
                self("PR")
            else:
                self("PA")

    def _set_relative(self):
        self._set_relative_mode = True

    def _set_absolute(self):
        self._set_relative_mode = False

    def program_mode(self):
        self._write_pwmfreq_info()
        self._write_dc_information()
        self._write_pen_info(2)
        self._write_speed_info(vector=True)
        self._write_power_info(vector=True)
        self._set_relative()

    def rapid_mode(self):
        pass

    def scanline(self, bits, right=False, left=False, top=False, bottom=False):
        cmd = None
        if left:  # left movement
            cmd = bytearray(b"YF")
            bits = bits[::-1]
        elif right:
            cmd = bytearray(b"YZ")
            bits = bits[::-1]
        elif top:
            cmd = bytearray(b"XF")
            bits = bits[::-1]
        elif bottom:
            cmd = bytearray(b"XZ")
            bits = bits[::-1]
        if cmd is None:
            return  # 0,0 goes nowhere.
        count = len(bits)
        byte_length = int(math.ceil(count / 8))
        cmd += struct.pack(">i", count)[1:]
        binary = "".join([str(b) for b in bits])
        cmd += int(binary, 2).to_bytes(byte_length, "little")
        self(cmd)
        if left:
            self._last_x -= count
        elif right:
            self._last_x += count
        elif top:
            self._last_y -= count
        elif right:
            self._last_y += count

    def raster(self, raster_cut: RasterCut):
        self._speed = raster_cut.settings.get(
            "speed", self.service.default_raster_speed
        )
        self._power = raster_cut.settings.get(
            "power", self.service.default_raster_power
        )
        scanline = []
        increasing = True

        def commit_scanline():
            if scanline:
                # If there is a scanline commit the scanline.
                if raster_cut.horizontal:
                    # Horizontal Raster.
                    if increasing:
                        self.scanline(scanline, right=True)
                        scanline.clear()
                    else:
                        self.scanline(scanline, left=True)
                        scanline.clear()
                else:
                    # Vertical raster.
                    if increasing:
                        self.scanline(scanline, bottom=True)
                        scanline.clear()
                    else:
                        self.scanline(scanline, top=True)
                        scanline.clear()

        previous_x, previous_y = raster_cut.plot.initial_position_in_scene()
        self.goto(previous_x, previous_y)

        if raster_cut.horizontal:
            self.raster_mode(horizontal=True)
            for x, y, on in raster_cut.plot.plot():
                dx = x - previous_x
                dy = y - previous_y
                if dx < 0 and increasing or dx > 0 and not increasing:
                    # X direction has switched.
                    commit_scanline()
                    increasing = not increasing
                if dy != 0:
                    # We are moving in the Y direction.
                    commit_scanline()
                    self.goto(x, y)
                if dx != 0:
                    # Normal move, extend bytes.
                    scanline.extend([int(on)] * abs(dx))
                previous_x, previous_y = x, y
        else:
            self.raster_mode(horizontal=False)
            for x, y, on in raster_cut.plot.plot():
                dx = x - previous_x
                dy = y - previous_y
                if dy < 0 and increasing or dy > 0 and not increasing:
                    # Y direction has switched.
                    commit_scanline()
                    increasing = not increasing
                if dx != 0:
                    # We are moving in the X direction.
                    commit_scanline()
                    self.goto(x, y)
                if dy != 0:
                    # Normal move, extend bytes
                    scanline.extend([int(on)] * abs(dx))
                previous_x, previous_y = x, y
        commit_scanline()

    def raster_mode(self, horizontal=True):
        mode = "raster_horizontal" if horizontal else "raster_vertical"
        if self.mode == mode:
            return
        self.mode = mode
        bc = 0
        bd = 1
        self("IN")
        self._write_pwmfreq_info()
        self._write_dc_information()
        self._write_pen_info(2)
        self._write_speed_info(vector=False)
        self._write_power_info(vector=False)
        self._set_relative()
        # TODO: This section is for the write of the movement to the start of the vector.

        # Moves to the start position of the raster.
        self(f"BT{self.raster_bit_depth}")
        self(f"BC{bc}")
        self(f"BD{bd}")
        self._write_pen_info(0)
        self._write_speed_info(vector=False)
        self._write_power_info(vector=False)
        # IN;PL5;VP100;VK100;SP2;SP2;VQ15;VJ24;VS10;PR;PR;PR;PR;PU1000,-394;BT1;DA40;BC0;BD4;PR;PU-4,0;SP0;VQ20;VJ8;VS9;YF
        # IN;PL5;VP100;VK100;SP2;SP2;VQ15;VJ24;VS10;PR;PR;PR;PR;PU1000,-1147;BT8;BC0;BD4;SP0;VQ20;VJ8;VS6;YZ...


    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        self._set_speed = settings.get("speed")
        self._set_power = settings.get("power")
        self._set_pwm_freq = settings.get("pwm_frequency")

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def raw(self, data):
        data = bytes(data, "latin1")
        self.connect_if_needed()
        self.connection.write(index=self._machine_index, data=data)

    def mark(self, x, y):
        self._write_relative_mode()
        dx = int(round(x - self._last_x))
        dy = int(round(y - self._last_y))
        if dx == 0 and dy == 0:
            return
        if self._relative:
            self(f"PD{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self(f"PD{y},{x}")
            self._last_x, self._last_y = x, y

    def goto(self, x, y):
        self._write_relative_mode()
        dx = int(round(x - self._last_x))
        dy = int(round(y - self._last_y))
        if dx == 0 and dy == 0:
            return
        if self._relative:
            self(f"PU{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self(f"PU{y},{x}")
            self._last_x, self._last_y = x, y

    def set_xy(self, x, y, relative=None):
        self.realtime_job()
        if relative is not None:
            if relative:
                self._set_relative()
            else:
                self._set_absolute()
        self.mode = "jog"
        self._write_dc_information()
        self._write_pen_info(2)
        self._set_speed = self.service.moving_speed
        self._set_power = 0
        self._write_speed_info(vector=True)
        self._write_power_info(vector=True)
        self.goto(x, y)
        self.close_job()

    def get_last_xy(self):
        return self._last_x, self._last_y

    #######################
    # Command Shortcuts
    #######################

    def move_frame(self, file_index):
        self.realtime_job()
        self.mode = "move_frame"
        self(f"ZK{file_index}")
        self.close_job()

    def draw_frame(self, file_index):
        self.realtime_job()
        self.mode = "draw_frame"
        self(f"ZH{file_index}")
        self.close_job()

    def replay(self, file_index):
        self.realtime_job()
        self.mode = "replay"
        self(f"ZG{file_index}")
        self.close_job()

    def home_speeds(self, x_speed, y_speed, m_speed):
        self.realtime_job()
        self.mode = "home_speeds"
        self(f"VX{int(round(x_speed / 10))}")
        self(f"VY{int(round(y_speed / 10))}")
        self(f"VM{int(round(m_speed / 10))}")
        self.close_job()

    def z_relative(self, amount, speed=100):
        self.realtime_job()
        self.mode = "zmove"
        self(f"CV{int(round(speed / 10))}")
        self(f"CR{int(round(amount))}")
        self.close_job()

    def z_absolute(self, z_position, speed=100):
        self.realtime_job()
        self.mode = "zmove"
        self(f"CV{int(round(speed / 10))}")
        self(f"CU{int(round(z_position))}")
        self.close_job()

    def w_relative(self, amount, speed=100):
        self.realtime_job()
        self.mode = "wmove"
        self(f"WV{int(round(speed / 10))}")
        self(f"WR{int(round(amount))}")
        self.close_job()

    def w_absolute(self, w_position, speed=100):
        self.realtime_job()
        self.mode = "wmove"
        self(f"WV{int(round(speed / 10))}")
        self(f"WU{int(round(w_position))}")
        self.close_job()

    def pulse(self, pulse_time_ms):
        self.realtime_job()
        self.mode = "pulse"
        self.dwell(pulse_time_ms)
        self.close_job()

    def home(self):
        self.realtime_job()
        self.mode = "home"
        self("RS")
        self.close_job()

    def origin(self):
        self.home()
        # self.rapid_mode()
        # command_buffer = list()
        # command_buffer.append(f"ZZZFile{self._file_index}")
        # command_buffer.append("1")
        # command_buffer.append("ZED;")
        # self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def abort(self):
        self.realtime_job()
        self.mode = "abort"
        self("ZQ")
        self.close_job()

    def wait(self, time_in_ms):
        while time_in_ms > 255:
            time_in_ms -= 255
            self("TO255")
        if time_in_ms > 0:
            self(f"TO{int(round(time_in_ms))}")

    def dwell(self, time_in_ms):
        if self._pwm_frequency is not None:
            self(f"PL{self._pwm_frequency}")
        power = self.service.default_cut_power if self._power is None else self._power
        self(f"DA{self._map_power(power)}")
        while time_in_ms > 255:
            time_in_ms -= 255
            self("TX255")
        if time_in_ms > 0:
            self(f"TX{int(round(time_in_ms))}")

    def pause(self):
        self.realtime_job()
        self.mode = "pause"
        self("ZT")
        self.close_job()
        self.paused = True

    def resume(self):
        self.realtime_job()
        self.mode = "resume"
        self("ZG")
        self.close_job()
        self.paused = False

    def wait_finished(self):
        # No known method to force the laser to single state.
        pass

    def init_laser(self):
        self.usb_log("Ready")

    def power(self, power):
        """
        Accepts power in percent, automatically converts to power_ratio

        @param power:
        @return:
        """
        if self._power == power:
            return
        self._power = power
