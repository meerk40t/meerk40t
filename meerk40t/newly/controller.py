"""
Newly Controller
"""

import time

from meerk40t.newly.mock_connection import MockConnection
from meerk40t.newly.usb_connection import USBConnection

DRIVER_STATE_RAPID = 0
DRIVER_STATE_RASTER = 1
DRIVER_STATE_PROGRAM = 2


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

        self._speed = 15
        self._power = 1000
        self._acceleration = 24
        self._scan_speed = 200  # 200 mm/s
        self._file_index = 0
        self._relative = False
        self._pwm_frequency = None
        self._unknown_vp = 100
        self._unknown_vk = 100

        self.mode = DRIVER_STATE_RAPID
        self.paused = False
        self.command_buffer = []

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

    def rapid_mode(self):
        if self.command_buffer:
            self.command_buffer.append("ZED;")
            cmd = ";".join(self.command_buffer)
            self.connect_if_needed()
            self.connection.write(index=self._machine_index, data=cmd)
            self.command_buffer.clear()
        self.mode = DRIVER_STATE_RAPID

    def raster_mode(self):
        if self.mode == DRIVER_STATE_RASTER:
            return
        self.mode = DRIVER_STATE_RASTER
        self.command_buffer.append(f"ZZZFile{self._file_index}")
        self.command_buffer.append("DW")
        if self._pwm_frequency is not None:
            self.command_buffer.append(f"PL{self._pwm_frequency}")
        self.command_buffer.append(f"VP{self.service.cut_dc}")
        self.command_buffer.append(f"VK{self.service.move_dc}")
        self.command_buffer.append("SP2")
        self.command_buffer.append("SP2")

        speed_at_raster_change = self._speed
        if speed_at_raster_change is None:
            speed_at_raster_change = self.service.default_raster_speed
        chart = self.service.speedchart
        smallest_difference = float("inf")
        closest_index = None
        for i, c in enumerate(chart):
            chart_speed = c.get("speed", 0)
            delta_speed = chart_speed - speed_at_raster_change
            if chart_speed > speed_at_raster_change and smallest_difference > delta_speed:
                smallest_difference = delta_speed
                closest_index = i
        if closest_index is not None:
            settings = chart[closest_index]
        else:
            settings = chart[-1]
        self.command_buffer.append(f"VQ{int(round(settings['corner_speed']))}")
        self.command_buffer.append(f"VJ{int(round(settings['acceleration_length']))}")
        self.command_buffer.append(f"VS{int(round(speed_at_raster_change / 10))}")
        self.command_buffer.append(f"PR;PR;PR;PR")

        # "VQ15;VJ24;VS10;PR;PR;PR;PR;PU5481,-14819;BT1;DA128;BC0;BD8;PR;PU8,0;SP0;VQ20;VJ14;VS30;YZ"

    def program_mode(self, relative=True):
        if self.mode == DRIVER_STATE_PROGRAM:
            return
        self.mode = DRIVER_STATE_PROGRAM
        self.command_buffer.append(f"ZZZFile{self.service.file_index}")
        self.command_buffer.append("DW")
        if self._pwm_frequency is not None:
            self.command_buffer.append(f"PL{self._pwm_frequency}")
        self.command_buffer.append(f"VP{self.service.cut_dc}")
        self.command_buffer.append(f"VK{self.service.move_dc}")
        self.command_buffer.append("SP2")
        self.command_buffer.append("SP2")
        speed_at_program_change = self._speed
        if speed_at_program_change is None:
            speed_at_program_change = self.service.default_cut_speed
        chart = self.service.speedchart
        smallest_difference = float("inf")
        closest_index = None
        for i, c in enumerate(chart):
            chart_speed = c.get("speed", 0)
            delta_speed = chart_speed - speed_at_program_change
            if chart_speed > speed_at_program_change and smallest_difference > delta_speed:
                smallest_difference = delta_speed
                closest_index = i
        if closest_index is not None:
            settings = chart[closest_index]
        else:
            settings = chart[-1]
        self.command_buffer.append(f"VQ{int(round(settings['corner_speed']))}")
        self.command_buffer.append(f"VJ{int(round(settings['acceleration_length']))}")
        power = self.service.default_cut_power if self._power is None else self._power
        da_power = int(
            round((power / 1000.0) * self.service.max_power * 255.0 / 100.0)
        )
        self.command_buffer.append(f"DA{da_power}")
        self.command_buffer.append("SP0")
        self.command_buffer.append(f"VS{int(round(speed_at_program_change))}")
        if relative:
            self._relative = True
            self.command_buffer.append("PR")
        else:
            self._relative = False
            self.command_buffer.append("PA")

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        old = self._power
        self._power = settings.get("power")
        if old != self._power:
            self.rapid_mode()

        old = self._speed
        self._speed = settings.get("speed")
        if old != self._speed:
            self.rapid_mode()

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def raw(self, data):
        self.connect_if_needed()
        self.connection.write(index=self._machine_index, data=data)

    def mark(self, x, y):
        dx = int(round(x - self._last_x))
        dy = int(round(y - self._last_y))
        if dx == 0 and dy == 0:
            return
        if self._relative:
            self.command_buffer.append(f"PD{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self.command_buffer.append(f"PD{y},{x}")
            self._last_x, self._last_y = x, y

    def goto(self, x, y, long=None, short=None, distance_limit=None):
        dx = int(round(x - self._last_x))
        dy = int(round(y - self._last_y))
        if dx == 0 and dy == 0:
            return
        if self._relative:
            self.command_buffer.append(f"PU{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self.command_buffer.append(f"PU{y},{x}")
            self._last_x, self._last_y = x, y

    def set_xy(self, x, y, relative=False):
        self.connect_if_needed()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append(f"VP{self.service.cut_dc}")
        command_buffer.append(f"VK{self.service.move_dc}")
        command_buffer.append("SP2")
        command_buffer.append("SP2")
        command_buffer.append(f"VQ{int(round(self.service.default_corner_speed))}")
        command_buffer.append(
            f"VJ{int(round(self.service.default_acceleration_distance))}"
        )
        command_buffer.append(f"VS{int(round(self.service.moving_speed / 10.0))}")
        if relative:
            dx = int(round(x - self._last_x))
            dy = int(round(y - self._last_y))
            command_buffer.append("PR")
            command_buffer.append(f"PU{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            command_buffer.append("PA")
            command_buffer.append(f"PU{y},{x}")
            self._last_x, self._last_y = x, y
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def get_last_xy(self):
        return self._last_x, self._last_y

    #######################
    # Command Shortcuts
    #######################

    def move_frame(self, file_index):
        self.connect_if_needed()
        self.rapid_mode()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append(f"ZK{file_index}")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def draw_frame(self, file_index):
        self.connect_if_needed()
        self.rapid_mode()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append(f"ZH{file_index}")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def replay(self, file_index):
        self.connect_if_needed()
        self.rapid_mode()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append(f"ZG{file_index}")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def home(self):
        self.connect_if_needed()
        self.rapid_mode()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append("RS")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def origin(self):
        self.home()
        # self.rapid_mode()
        # command_buffer = list()
        # command_buffer.append(f"ZZZFile{self._file_index}")
        # command_buffer.append("1")
        # command_buffer.append("ZED;")
        # self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def abort(self):
        self.connect_if_needed()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append("ZQ")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def dwell(self, time_in_ms):
        self.connect_if_needed()
        self.rapid_mode()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        if self._pwm_frequency is not None:
            self.command_buffer.append(f"PL{self._pwm_frequency}")
        self.command_buffer.append(f"DA{self._power}")
        while time_in_ms > 255:
            time_in_ms -= 255
            command_buffer.append("TO255")
        if time_in_ms > 0:
            command_buffer.append(f"TO{int(round(time_in_ms))}")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))

    def pause(self):
        self.connect_if_needed()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append("ZT")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))
        self.paused = True

    def resume(self):
        self.connect_if_needed()
        command_buffer = list()
        command_buffer.append(f"ZZZFile0")
        command_buffer.append("ZG")
        command_buffer.append("ZED;")
        self.connection.write(index=self._machine_index, data=";".join(command_buffer))
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
