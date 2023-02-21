"""
Newly Controller
"""

import time

from meerk40t.newly.mock_connection import MockConnection
from meerk40t.newly.usb_connection import USBConnection

DRIVER_STATE_RAPID = 0
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

        self._speed = 24
        self._power = 38
        self._acceleration = 15
        self._relative = False

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
                    self.usb_log("Could not connect to the LMC controller.")
                    self.usb_log("Automatic connections disabled.")
                    raise ConnectionRefusedError(
                        "Could not connect to the LMC controller."
                    )
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

    def raster_mode(self):
        self.program_mode()

    def program_mode(self):
        if self.mode == DRIVER_STATE_PROGRAM:
            return
        self.mode = DRIVER_STATE_PROGRAM
        self.command_buffer.append("ZZZFile0")
        self.command_buffer.append("DW")
        self.command_buffer.append("PL2")
        self.command_buffer.append("VP100")
        self.command_buffer.append("VK100")
        self.command_buffer.append("SP2")
        self.command_buffer.append("SP2")
        self.command_buffer.append(f"VQ{int(round(self._acceleration))}")
        self.command_buffer.append(f"VJ{int(round(self._speed))}")
        self.command_buffer.append(f"DA{int(round(self._power))}")
        self.command_buffer.append("SP0")
        self.command_buffer.append("VS20")
        if self.service.use_relative:
            self._relative = True
            self.command_buffer.append("PR")
        else:
            self._relative = True
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
        self._power = settings.get("power", self.service.default_power)
        self._speed = settings.get("speed", self.service.default_speed)
        self._acceleration = settings.get("acceleration", self.service.default_acceleration)

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def mark(self, x, y):
        if self._relative:
            dx = int(round(x - self._last_x))
            dy = int(round(y - self._last_y))
            self.command_buffer.append(f"PD{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self.command_buffer.append(f"PD{y},{x}")
            self._last_x, self._last_y = x, y

    def goto(self, x, y, long=None, short=None, distance_limit=None):
        if self._relative:
            dx = int(round(x - self._last_x))
            dy = int(round(y - self._last_y))
            self.command_buffer.append(f"PU{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self.command_buffer.append(f"PU{y},{x}")
            self._last_x, self._last_y = x, y

    def set_xy(self, x, y):
        self.connect_if_needed()
        command_buffer = list()
        command_buffer.append("ZZZFile0")
        command_buffer.append("VP100")
        command_buffer.append("VK100")
        command_buffer.append("SP2")
        command_buffer.append("SP2")
        command_buffer.append(f"VQ{int(round(self._acceleration))}")
        command_buffer.append(f"VJ{int(round(self._speed))}")
        command_buffer.append("VS10")
        if self.service.use_relative:
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

    def abort(self):
        cmd = f"ZZZFile0;ZQ;ZED"
        self.connection.write(index=self._machine_index, data=cmd)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

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
