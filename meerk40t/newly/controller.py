"""
Newly Controller
"""
import struct
import time

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

        self._speed = None
        self._power = None
        self._relative = False
        self._pwm_frequency = None
        self._realtime = False

        self._unknown_bt = 1
        self._unknown_bc = 1
        self._unknown_bd = 1

        self.mode = "init"
        self.paused = False
        self.command_buffer = []

    def __call__(self, cmd, *args, **kwargs):
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
        self.mode = "started"
        self(f"ZZZFile0")

    def _write_position(self, outline):
        pass

    def _write_frame(self, outline):
        self.mode = "frame"
        if outline is not None:
            x, y = self._last_x, self._last_y
            self("DW")
            self._write_dc_information()
            self("SP2")
            self("SP2")
            self._write_speed_information(speed=100, power=0)
            self("PR")
            self._relative = True
            for pt in outline:
                self.goto(*pt)
            self.goto(x, y)
            self("ZED")

    def _execute_job(self):
        self("ZED")
        cmd = ";".join(self.command_buffer) + ";"
        self.connect_if_needed()
        self.connection.write(index=self._machine_index, data=cmd)
        self.command_buffer.clear()

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
        self.program_mode()

    def close_job(self, job=None):
        """
        Closes the file and sends.
        @return:
        """
        if not self.command_buffer:
            return
        if self.mode in ("started", "init"):
            # Job contains no instructions.
            self.mode = "init"
            self.command_buffer.clear()
            return
        self._execute_job()
        self.mode = "init"
        if self.service.autoplay and not self._realtime:
            self.replay(self.service.file_index)

    def _map_speed(self, speed):
        if speed > 100:
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

    def _write_dc_information(self):
        self(f"VP{self.service.cut_dc}")
        self(f"VK{self.service.move_dc}")

    def _write_speed_information(self, speed=None, power=None):
        # Calculate speed and lookup factors in chart.
        speed_at_program_change = self._speed
        if speed_at_program_change is None:
            speed_at_program_change = self.service.default_cut_speed
        if speed is not None:
            speed_at_program_change = speed
        chart = self.service.speedchart
        smallest_difference = float("inf")
        closest_index = None
        for i, c in enumerate(chart):
            chart_speed = c.get("speed", 0)
            delta_speed = chart_speed - speed_at_program_change
            if (
                chart_speed > speed_at_program_change
                and smallest_difference > delta_speed
            ):
                smallest_difference = delta_speed
                closest_index = i
        if closest_index is not None:
            settings = chart[closest_index]
        else:
            settings = chart[-1]

        self(f"VQ{int(round(settings['corner_speed']))}")
        self(f"VJ{int(round(settings['acceleration_length']))}")
        self(f"SP1")
        power_at_program_change = self.service.default_cut_power if self._power is None else self._power
        if power is not None:
            power_at_program_change = power
        self(f"DA{self._map_power(power_at_program_change)}")
        self(f"VS{self._map_speed(speed_at_program_change)}")

    def program_mode(self):
        if self.mode == "program":
            return
        if self.mode == "started":
            if self._pwm_frequency is not None:
                self(f"PL{self._pwm_frequency}")
        self._write_dc_information()
        self("SP2")
        self("SP2")
        self._write_speed_information()
        self._relative = True
        self("PR")

    def rapid_mode(self):
        pass

    def raster_mode_horizontal(self):
        if self.mode == "raster_horizontal":
            return
        self.mode = "raster_horizontal"
        if self.mode == "started":
            if self._pwm_frequency is not None:
                self(f"PL{self._pwm_frequency}")
            self._write_dc_information()
        self("SP2")
        self("SP2")
        self._write_speed_information()
        self._relative = True
        self(f"PR;PR;PR;PR")
        # Moves to the start postion of the raster.
        self(f"BT{self._unknown_bt}")
        power = self.service.default_raster_power if self._power is None else self._power
        self(f"DA{self._map_power(power)}")
        self(f"BC{self._unknown_bc}")
        self(f"BD{self._unknown_bd}")
        self("PR")
        self("SP0")
        self._write_speed_information()

    def write_scanline(self, bits, dx, dy):
        cmd = None
        if dy < 0:  # left movement
            cmd = "YF"
        elif dy > 0:
            cmd = "YZ"
        elif dx < 0:
            cmd = "XF"
        elif dx > 0:
            cmd = "XZ"
        if cmd is None:
            return  # 0,0 goes nowhere.
        count = len(bits)
        self(struct.pack(">i", count)[1:])
        self(bits)

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        new_init = False
        old = self._power
        self._power = settings.get("power")
        if self._power != old:
            new_init = True
        old = self._speed
        self._speed = settings.get("speed")
        if self._speed != old:
            new_init = True
        if new_init:
            self._write_speed_information()

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def raw(self, data):
        data = bytes(data, "latin1")
        self.connect_if_needed()
        self.connection.write(index=self._machine_index, data=data)

    def mark(self, x, y):
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

    def set_xy(self, x, y, relative=False):
        self.realtime_job()
        self.mode = "jog"
        self._write_dc_information()
        self("SP2")
        self("SP2")
        self._write_speed_information(speed=self.service.moving_speed, power=0)
        if relative:
            dx = int(round(x - self._last_x))
            dy = int(round(y - self._last_y))
            self("PR")
            self._relative = True
            self(f"PU{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self("PA")
            self._relative = False
            self(f"PU{y},{x}")
            self._last_x, self._last_y = x, y
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

    def dwell(self, time_in_ms):
        self.connect_if_needed()
        if self._pwm_frequency is not None:
            self(f"PL{self._pwm_frequency}")
        self(f"DA{self._power}")
        while time_in_ms > 255:
            time_in_ms -= 255
            self("TO255")
        if time_in_ms > 0:
            self(f"TO{int(round(time_in_ms))}")

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
