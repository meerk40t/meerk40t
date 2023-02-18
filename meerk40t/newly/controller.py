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
        self._power = 100
        self._acceleration = 15

        self.mode = DRIVER_STATE_RAPID
        self.paused = False
        

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
        pass

    def raster_mode(self):
        self.program_mode()

    def program_mode(self):
        if self.mode == DRIVER_STATE_PROGRAM:
            return
        self.mode = DRIVER_STATE_PROGRAM
        
        self._speed = None
        self._power = None

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
        print(f"mark({x},{y})")

    def goto(self, x, y, long=None, short=None, distance_limit=None):
        print(f"goto({x},{y})")

    def set_xy(self, x, y):
        self.connect_if_needed()
        cmd = f"ZZZFile0;VP100;VK100;SP2;SP2;VQ{int(round(self._acceleration))};VJ{int(round(self._speed))};VS10;PR;PU{int(round(x))},{int(round(y))};ZED;"
        self.connection.write(index=self._machine_index, packet=cmd)
        self._last_x, self._last_y = x, y

    def get_last_xy(self):
        return self._last_x, self._last_y

    #######################
    # Command Shortcuts
    #######################

    def abort(self):
        cmd = f"ZZZFile0;ZQ;ZED"
        self.connection.write(index=self._machine_index, packet=cmd)

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
