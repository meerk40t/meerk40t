"""
Galvo Controller

The balor controller takes low level lmc galvo commands and converts them into lists and shorts commands to send
to the hardware controller.
"""

import struct
import time
from copy import copy

from meerk40t.balormk.mock_connection import MockConnection
from meerk40t.balormk.usb_connection import USBConnection
from meerk40t.fill.fills import Wobble

DRIVER_STATE_RAPID = 0
DRIVER_STATE_LIGHT = 1
DRIVER_STATE_PROGRAM = 2
DRIVER_STATE_RAW = 3

nop = [0x02, 0x80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
empty = bytearray(nop * 0x100)

listJumpTo = 0x8001
listEndOfList = 0x8002
listLaserOnPoint = 0x8003
listDelayTime = 0x8004
listMarkTo = 0x8005
listJumpSpeed = 0x8006
listLaserOnDelay = 0x8007
listLaserOffDelay = 0x8008
listMarkFreq = 0x800A
listMarkPowerRatio = 0x800B
listMarkSpeed = 0x800C
listJumpDelay = 0x800D
listPolygonDelay = 0x800F
listWritePort = 0x8011
listMarkCurrent = 0x8012
listMarkFreq2 = 0x8013
listFlyEnable = 0x801A
listQSwitchPeriod = 0x801B
listDirectLaserSwitch = 0x801C
listFlyDelay = 0x801D
listSetCo2FPK = 0x801E
listFlyWaitInput = 0x801F
listFiberOpenMO = 0x8021
listWaitForInput = 0x8022
listChangeMarkCount = 0x8023
listSetWeldPowerWave = 0x8024
listEnableWeldPowerWave = 0x8025
listFiberYLPMPulseWidth = 0x8026
listFlyEncoderCount = 0x8028
listSetDaZWord = 0x8029
listJptSetParam = 0x8050
listReadyMark = 0x8051

DisableLaser = 0x0002
EnableLaser = 0x0004
ExecuteList = 0x0005
SetPwmPulseWidth = 0x0006
GetVersion = 0x0007
GetSerialNo = 0x0009
GetListStatus = 0x000A
GetPositionXY = 0x000C
GotoXY = 0x000D
LaserSignalOff = 0x000E
LaserSignalOn = 0x000F
WriteCorLine = 0x0010
ResetList = 0x0012
RestartList = 0x0013
WriteCorTable = 0x0015
SetControlMode = 0x0016
SetDelayMode = 0x0017
SetMaxPolyDelay = 0x0018
SetEndOfList = 0x0019
SetFirstPulseKiller = 0x001A
SetLaserMode = 0x001B
SetTiming = 0x001C
SetStandby = 0x001D
SetPwmHalfPeriod = 0x001E
StopExecute = 0x001F
StopList = 0x0020
WritePort = 0x0021
WriteAnalogPort1 = 0x0022
WriteAnalogPort2 = 0x0023
WriteAnalogPortX = 0x0024
ReadPort = 0x0025
SetAxisMotionParam = 0x0026
SetAxisOriginParam = 0x0027
AxisGoOrigin = 0x0028
MoveAxisTo = 0x0029
GetAxisPos = 0x002A
GetFlyWaitCount = 0x002B
GetMarkCount = 0x002D
SetFpkParam2 = 0x002E
Fiber_SetMo = 0x0033  # open and close set by value
Fiber_GetStMO_AP = 0x0034
EnableZ = 0x003A
DisableZ = 0x0039
SetZData = 0x003B
SetSPISimmerCurrent = 0x003C
SetFpkParam = 0x0062
Reset = 0x0040
GetFlySpeed = 0x0038
FiberPulseWidth = 0x002F
FiberGetConfigExtend = 0x0030
InputPort = 0x0031  # ClearLockInputPort calls 0x04, then if EnableLockInputPort 0x02 else 0x01, GetLockInputPort
GetMarkTime = 0x0041
GetUserData = 0x0036
SetFlyRes = 0x0032

list_command_lookup = {
    0x8001: "listJumpTo",
    0x8002: "listEndOfList",
    0x8003: "listLaserOnPoint",
    0x8004: "listDelayTime",
    0x8005: "listMarkTo",
    0x8006: "listJumpSpeed",
    0x8007: "listLaserOnDelay",
    0x8008: "listLaserOffDelay",
    0x800A: "listMarkFreq",
    0x800B: "listMarkPowerRatio",
    0x800C: "listMarkSpeed",
    0x800D: "listJumpDelay",
    0x800F: "listPolygonDelay",
    0x8011: "listWritePort",
    0x8012: "listMarkCurrent",
    0x8013: "listMarkFreq2",
    0x801A: "listFlyEnable",
    0x801B: "listQSwitchPeriod",
    0x801C: "listDirectLaserSwitch",
    0x801D: "listFlyDelay",
    0x801E: "listSetCo2FPK",
    0x801F: "listFlyWaitInput",
    0x8021: "listFiberOpenMO",
    0x8022: "listWaitForInput",
    0x8023: "listChangeMarkCount",
    0x8024: "listSetWeldPowerWave",
    0x8025: "listEnableWeldPowerWave",
    0x8026: "listFiberYLPMPulseWidth",
    0x8028: "listFlyEncoderCount",
    0x8029: "listSetDaZWord",
    0x8050: "listJptSetParam",
    0x8051: "listReadyMark",
}

single_command_lookup = {
    0x0002: "DisableLaser",
    0x0004: "EnableLaser",
    0x0005: "ExecuteList",
    0x0006: "SetPwmPulseWidth",
    0x0007: "GetVersion",
    0x0009: "GetSerialNo",
    0x000A: "GetListStatus",
    0x000C: "GetPositionXY",
    0x000D: "GotoXY",
    0x000E: "LaserSignalOff",
    0x000F: "LaserSignalOn",
    0x0010: "WriteCorLine",
    0x0012: "ResetList",
    0x0013: "RestartList",
    0x0015: "WriteCorTable",
    0x0016: "SetControlMode",
    0x0017: "SetDelayMode",
    0x0018: "SetMaxPolyDelay",
    0x0019: "SetEndOfList",
    0x001A: "SetFirstPulseKiller",
    0x001B: "SetLaserMode",
    0x001C: "SetTiming",
    0x001D: "SetStandby",
    0x001E: "SetPwmHalfPeriod",
    0x001F: "StopExecute",
    0x0020: "StopList",
    0x0021: "WritePort",
    0x0022: "WriteAnalogPort1",
    0x0023: "WriteAnalogPort2",
    0x0024: "WriteAnalogPortX",
    0x0025: "ReadPort",
    0x0026: "SetAxisMotionParam",
    0x0027: "SetAxisOriginParam",
    0x0028: "AxisGoOrigin",
    0x0029: "MoveAxisTo",
    0x002A: "GetAxisPos",
    0x002B: "GetFlyWaitCount",
    0x002D: "GetMarkCount",
    0x002E: "SetFpkParam2",
    0x0033: "Fiber_SetMo",
    0x0034: "Fiber_GetStMO_AP",
    0x003A: "EnableZ",
    0x0039: "DisableZ",
    0x003B: "SetZData",
    0x003C: "SetSPISimmerCurrent",
    0x0062: "SetFpkParam",
    0x0040: "Reset",
    0x0038: "GetFlySpeed",
    0x002F: "FiberPulseWidth",
    0x0030: "FiberGetConfigExtend",
    0x0031: "InputPort",
    0x0041: "GetMarkTime",
    0x0036: "GetUserData",
    0x0032: "SetFlyRes",
}

BUSY = 0x04
READY = 0x20


def _bytes_to_words(r):
    b0 = r[1] << 8 | r[0]
    b1 = r[3] << 8 | r[2]
    b2 = r[5] << 8 | r[4]
    b3 = r[7] << 8 | r[6]
    return b0, b1, b2, b3


class GalvoController:
    """
    Galvo controller is tasked with sending queued data to the controller board and ensuring that the connection to the
    controller board is established to perform these actions.

    This should serve as a next generation command sequencer written from scratch for galvo lasers. The goal is to
    provide all the given commands in a coherent queue structure which provides correct sequences between list and
    single commands.
    """

    def __init__(
        self,
        service,
        x=0x8000,
        y=0x8000,
        mark_speed=None,
        goto_speed=None,
        light_speed=None,
        dark_speed=None,
        force_mock=False,
    ):
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

        self._light_bit = service.setting(int, "light_pin", 8)
        self._foot_bit = service.setting(int, "footpedal_pin", 15)

        self._last_x = x
        self._last_y = y
        self._mark_speed = mark_speed
        self._goto_speed = goto_speed
        self._light_speed = light_speed
        self._dark_speed = dark_speed

        self._ready = None
        self._speed = None
        self._travel_speed = None
        self._frequency = None
        self._power = None
        self._pulse_width = None

        self._delay_jump = None
        self._delay_on = None
        self._delay_off = None
        self._delay_poly = None
        self._delay_end = None

        self._wobble = None
        self._port_bits = 0
        self._machine_index = 0

        self.mode = DRIVER_STATE_RAPID
        self._active_list = None
        self._active_index = 0
        self._list_executing = False
        self._number_of_list_packets = 0
        self.paused = False

    @property
    def state(self):
        if self.mode == DRIVER_STATE_RAPID:
            return "idle", "idle"
        if self.paused:
            return "hold", "paused"
        if self.mode == DRIVER_STATE_RAW:
            return "busy", "raw"
        if self.mode == DRIVER_STATE_LIGHT:
            return "busy", "light"
        if self.mode == DRIVER_STATE_PROGRAM:
            return "busy", "program"

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
                "LMC was unreachable. Explicit connect required."
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

    def send(self, data, read=True):
        if self.is_shutdown:
            return -1, -1, -1, -1
        self.connect_if_needed()
        try:
            self.connection.write(self._machine_index, data)
        except ConnectionError:
            return -1, -1, -1, -1
        if read:
            try:
                r = self.connection.read(self._machine_index)
                return struct.unpack("<4H", r)
            except ConnectionError:
                return -1, -1, -1, -1

    def status(self):
        b0, b1, b2, b3 = self.get_version()
        return b3

    #######################
    # MODE SHIFTS
    #######################

    def raw_mode(self):
        self.mode = DRIVER_STATE_RAW

    def rapid_mode(self):
        if self.mode == DRIVER_STATE_RAPID:
            return
        self.list_end_of_list()  # Ensure at least one list_end_of_list
        self._list_end()
        if not self._list_executing and self._number_of_list_packets:
            # If we never ran the list, and we sent some lists.
            self.execute_list()
        self._list_executing = False
        self._number_of_list_packets = 0
        self.wait_idle()
        self.set_fiber_mo(0)
        self.port_off(bit=0)
        self.write_port()
        marktime = self.get_mark_time()
        self.service.signal("galvo;marktime", marktime)
        self.usb_log(f"Time taken for list execution: {marktime}")
        self.mode = DRIVER_STATE_RAPID

    def raster_mode(self):
        self.program_mode()

    def program_mode(self):
        if self.mode == DRIVER_STATE_PROGRAM:
            return
        if self.mode == DRIVER_STATE_LIGHT:
            self.mode = DRIVER_STATE_PROGRAM
            self.light_off()
            self.port_on(bit=0)
            self.write_port()
            self.set_fiber_mo(1)
        else:
            self.mode = DRIVER_STATE_PROGRAM
            self.reset_list()
            self.port_on(bit=0)
            self.write_port()
            self.set_fiber_mo(1)
            self._ready = None
            self._speed = None
            self._travel_speed = None
            self._frequency = None
            self._power = None
            self._pulse_width = None

            self._delay_jump = None
            self._delay_on = None
            self._delay_off = None
            self._delay_poly = None
            self._delay_end = None
            self.list_ready()
            if self.service.delay_openmo != 0:
                self.list_delay_time(int(self.service.delay_openmo * 100))
            self.list_write_port()
            self.list_jump_speed(self.service.default_rapid_speed)

    def light_mode(self):
        if self.mode == DRIVER_STATE_LIGHT:
            return
        if self.mode == DRIVER_STATE_PROGRAM:
            self.set_fiber_mo(0)
            self.port_off(bit=0)
            self.port_on(self._light_bit)
            self.write_port()
        else:
            self._ready = None
            self._speed = None
            self._travel_speed = None
            self._frequency = None
            self._power = None
            self._pulse_width = None

            self._delay_jump = None
            self._delay_on = None
            self._delay_off = None
            self._delay_poly = None
            self._delay_end = None

            self.reset_list()
            self.list_ready()
            self.port_off(bit=0)
            self.port_on(self._light_bit)
            self.list_write_port()
        self.mode = DRIVER_STATE_LIGHT

    #######################
    # LIST APPENDING OPERATIONS
    #######################

    def _list_end(self):
        if self._active_list and self._active_index:
            self.wait_ready()
            while self.paused:
                time.sleep(0.3)
            self.send(self._active_list, False)
            if self.mode != DRIVER_STATE_RAW:
                self.set_end_of_list(0)
            self._number_of_list_packets += 1
            self._active_list = None
            self._active_index = 0
            if self._number_of_list_packets > 2 and not self._list_executing:
                if self.mode != DRIVER_STATE_RAW:
                    self.execute_list()
                self._list_executing = True

    def _list_new(self):
        self._active_list = copy(empty)
        self._active_index = 0

    def _list_write(self, command, v1=0, v2=0, v3=0, v4=0, v5=0):
        if self._active_index >= 0xC00:
            self._list_end()
        if self._active_list is None:
            self._list_new()
        index = self._active_index
        self._active_list[index : index + 12] = struct.pack(
            "<6H", int(command), int(v1), int(v2), int(v3), int(v4), int(v5)
        )
        self._active_index += 12

    def _command(self, command, v1=0, v2=0, v3=0, v4=0, v5=0, read=True):
        cmd = struct.pack(
            "<6H", int(command), int(v1), int(v2), int(v3), int(v4), int(v5)
        )
        return self.send(cmd, read=read)

    def raw_write(self, command, v1=0, v2=0, v3=0, v4=0, v5=0):
        """
        Write this raw command to value. Sends the correct way based on command value.

        @return:
        """
        if command >= 0x8000:
            self._list_write(command, v1, v2, v3, v4, v5)
        else:
            self._command(command, v1, v2, v3, v4, v5)

    def raw_clear(self):
        self._list_new()

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        if self.service.pulse_width_enabled:
            # Global Pulse Width is enabled.
            if str(settings.get("pulse_width_enabled", False)).lower() == "true":
                # Local Pulse Width value is enabled.
                # OpFiberYLPMPulseWidth

                self.list_fiber_ylpm_pulse_width(
                    int(settings.get("pulse_width", self.service.default_pulse_width))
                )
            else:
                # Only global is enabled, use global pulse width value.
                self.list_fiber_ylpm_pulse_width(self.service.default_pulse_width)

        if str(settings.get("rapid_enabled", False)).lower() == "true":
            self.list_jump_speed(
                float(settings.get("rapid_speed", self.service.default_rapid_speed))
            )
        else:
            self.list_jump_speed(self.service.default_rapid_speed)

        self.power(
            float(settings.get("power", self.service.default_power)) / 10.0
        )  # Convert power, out of 1000
        self.frequency(float(settings.get("frequency", self.service.default_frequency)))
        self.list_mark_speed(float(settings.get("speed", self.service.default_speed)))

        if str(settings.get("timing_enabled", False)).lower() == "true":
            self.list_laser_on_delay(
                settings.get("delay_laser_on", self.service.delay_laser_on)
            )
            self.list_laser_off_delay(
                settings.get("delay_laser_off", self.service.delay_laser_off)
            )
            self.list_polygon_delay(
                settings.get("delay_laser_polygon", self.service.delay_polygon)
            )
        else:
            # Use globals
            self.list_laser_on_delay(self.service.delay_laser_on)
            self.list_laser_off_delay(self.service.delay_laser_off)
            self.list_polygon_delay(self.service.delay_polygon)

    def set_wobble(self, settings):
        """
        Set the wobble parameters and mark modifications routines.

        @param settings: The dict setting to extract parameters from.
        @return:
        """
        if settings is None:
            self._wobble = None
            return
        wobble_enabled = str(settings.get("wobble_enabled", False)).lower() == "true"
        if not wobble_enabled:
            self._wobble = None
            return
        wobble_radius = settings.get("wobble_radius", "1.5mm")
        wobble_r = self.service.physical_to_device_length(wobble_radius, 0)[0]
        wobble_interval = settings.get("wobble_interval", "0.3mm")
        wobble_speed = settings.get("wobble_speed", 50.0)
        wobble_type = settings.get("wobble_type", "circle")
        wobble_interval = self.service.physical_to_device_length(wobble_interval, 0)[0]
        algorithm = self.service.lookup(f"wobble/{wobble_type}")
        if self._wobble is None:
            self._wobble = Wobble(
                algorithm=algorithm,
                radius=wobble_r,
                speed=wobble_speed,
                interval=wobble_interval,
            )
        else:
            # set our parameterizations
            self._wobble.algorithm = algorithm
            self._wobble.radius = wobble_r
            self._wobble.speed = wobble_speed

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def mark(self, x, y):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self._mark_speed is not None:
            self.list_mark_speed(self._mark_speed)
        if self._wobble:
            for wx, wy in self._wobble(self._last_x, self._last_y, x, y):
                self.list_mark(wx, wy)
        else:
            self.list_mark(x, y)

    def goto(self, x, y, long=None, short=None, distance_limit=None):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self._goto_speed is not None:
            self.list_jump_speed(self._goto_speed)
        self.list_jump(x, y, long=long, short=short, distance_limit=distance_limit)

    def light(self, x, y, long=None, short=None, distance_limit=None):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self.light_on():
            self.list_write_port()
        if self._light_speed is not None:
            self.list_jump_speed(self._light_speed)
        self.list_jump(x, y, long=long, short=short, distance_limit=distance_limit)

    def dark(self, x, y, long=None, short=None, distance_limit=None):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self.light_off():
            self.list_write_port()
        if self._dark_speed is not None:
            self.list_jump_speed(self._dark_speed)
        self.list_jump(x, y, long=long, short=short, distance_limit=distance_limit)

    def set_xy(self, x, y):
        distance = int(abs(complex(x, y) - complex(self._last_x, self._last_y)))
        if distance > 0xFFFF:
            distance = 0xFFFF
        self.goto_xy(x, y, distance=distance)

    def get_last_xy(self):
        return self._last_x, self._last_y

    #######################
    # Command Shortcuts
    #######################

    def is_busy(self):
        status = self.status()
        return bool(status & BUSY)

    def is_ready(self):
        status = self.status()
        return bool(status & READY)

    def is_ready_and_not_busy(self):
        if self.mode == DRIVER_STATE_RAW:
            return True
        status = self.status()
        return bool(status & READY) and not bool(status & BUSY)

    def wait_finished(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        while not self.is_ready_and_not_busy():
            time.sleep(0.01)
            if self.is_shutdown:
                return

    def wait_ready(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        while not self.is_ready():
            time.sleep(0.01)
            if self.is_shutdown:
                return

    def wait_idle(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        while self.is_busy():
            time.sleep(0.01)
            if self.is_shutdown:
                return

    def abort(self, dummy_packet=True):
        if self.mode == DRIVER_STATE_RAW:
            return
        self.stop_execute()
        self.set_fiber_mo(0)
        self.reset_list()
        if dummy_packet:
            self._list_new()
            self.list_end_of_list()  # Ensure packet is sent on end.
            self._list_end()
            if not self._list_executing:
                self.execute_list()
        self._list_executing = False
        self._number_of_list_packets = 0
        self.set_fiber_mo(0)
        self.port_off(bit=0)
        self.write_port()
        self.mode = DRIVER_STATE_RAPID

    def pause(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        self.paused = True
        self.stop_list()

    def resume(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        self.restart_list()
        self.paused = False

    def init_laser(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        cor_file = self.service.corfile if self.service.corfile_enabled else None
        first_pulse_killer = self.service.first_pulse_killer
        pwm_pulse_width = self.service.pwm_pulse_width
        pwm_half_period = self.service.pwm_half_period
        standby_param_1 = self.service.standby_param_1
        standby_param_2 = self.service.standby_param_2
        timing_mode = self.service.timing_mode
        delay_mode = self.service.delay_mode
        laser_mode = self.service.laser_mode
        control_mode = self.service.control_mode
        fpk2_p1 = self.service.fpk2_p1
        fpk2_p2 = self.service.fpk2_p2
        fpk2_p3 = self.service.fpk2_p3
        fpk2_p4 = self.service.fpk2_p3
        fly_res_p1 = self.service.fly_res_p1
        fly_res_p2 = self.service.fly_res_p2
        fly_res_p3 = self.service.fly_res_p3
        fly_res_p4 = self.service.fly_res_p4

        self.usb_log("Initializing Laser")
        serial_number = self.get_serial_number()
        self.usb_log(f"Serial Number: {serial_number}")
        version = self.get_version()
        self.usb_log(f"Version: {version}")

        self.reset()
        self.usb_log("Reset")
        self.write_correction_file(cor_file)
        self.usb_log("Correction File Sent")
        self.enable_laser()
        self.usb_log("Laser Enabled")
        self.set_control_mode(control_mode)
        self.usb_log("Control Mode")
        self.set_laser_mode(laser_mode)
        self.usb_log("Laser Mode")
        self.set_delay_mode(delay_mode)
        self.usb_log("Delay Mode")
        self.set_timing(timing_mode)
        self.usb_log("Timing Mode")
        self.set_standby(standby_param_1, standby_param_2)
        self.usb_log("Setting Standby")
        self.set_first_pulse_killer(first_pulse_killer)
        self.usb_log("Set First Pulse Killer")
        self.set_pwm_half_period(pwm_half_period)
        self.usb_log("Set PWM Half-Period")
        self.set_pwm_pulse_width(pwm_pulse_width)
        self.usb_log("Set PWM pulse width")
        self.set_fiber_mo(0)  # Close
        self.usb_log("Set Fiber Mo (Closed)")
        self.set_pfk_param_2(fpk2_p1, fpk2_p2, fpk2_p3, fpk2_p4)
        self.usb_log("First Pulse Killer Parameters")
        self.set_fly_res(fly_res_p1, fly_res_p2, fly_res_p3, fly_res_p4)
        self.usb_log("On-The-Fly Res")
        self.enable_z()
        self.usb_log("Z-Enabled")
        self.write_analog_port_1(0x7FF)
        self.usb_log("Analog Port 1")
        self.enable_z()
        self.usb_log("Z-Enabled-part2")
        time.sleep(0.05)
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
        self.list_mark_current(self._convert_power(power))

    def frequency(self, frequency):
        if self._frequency == frequency:
            return
        self._frequency = frequency
        self.list_qswitch_period(self._convert_frequency(frequency))

    def light_on(self):
        if not self.is_port(self._light_bit):
            self.port_on(self._light_bit)
            return True
        return False

    def light_off(self):
        if self.is_port(self._light_bit):
            self.port_off(self._light_bit)
            return True
        return False

    def is_port(self, bit):
        return bool((1 << bit) & self._port_bits)

    def port_on(self, bit):
        self._port_bits = self._port_bits | (1 << bit)

    def port_off(self, bit):
        self._port_bits = ~((~self._port_bits) | (1 << bit))

    def port_set(self, mask, values):
        self._port_bits &= ~mask  # Unset mask.
        self._port_bits |= values & mask  # Set masked bits.

    #######################
    # UNIT CONVERSIONS
    #######################

    def _convert_speed(self, speed):
        """
        Speed in the galvo is given in galvos/ms this means mm/s needs to multiply by galvos_per_mm
        and divide by 1000 (s/ms)

        @param speed:
        @return:
        """
        # return int(speed / 2)
        galvos_per_mm = abs(self.service.physical_to_device_length("1mm", "1mm")[0])
        return int(speed * galvos_per_mm / 1000.0)

    def _convert_frequency(self, frequency_khz):
        """
        Converts frequency to period.

        20000000.0 / frequency in hz

        @param frequency_khz: Frequency to convert
        @return:
        """
        return int(round(20000.0 / frequency_khz)) & 0xFFFF

    def _convert_power(self, power):
        """
        Converts power percent to int value
        @return:
        """
        return int(round(power * 0xFFF / 100.0))

    #######################
    # HIGH LEVEL OPERATIONS
    #######################

    def write_correction_file(self, filename):
        if filename is None:
            self.write_blank_correct_file()
            return
        try:
            table = self._read_correction_file(filename)
            self._write_correction_table(table)
        except OSError:
            self.write_blank_correct_file()
            return

    @staticmethod
    def get_scale_from_correction_file(filename):
        with open(filename, "rb") as f:
            label = f.read(0x16)
            if label.decode("utf-16") == "LMC1COR_1.0":
                unk = f.read(2)
                return struct.unpack("63d", f.read(0x1F8))[43]
            else:
                unk = f.read(6)
                return struct.unpack("d", f.read(8))[0]

    def write_blank_correct_file(self):
        self.write_cor_table(False)

    def _read_float_correction_file(self, f):
        """
        Read table for cor files marked: LMC1COR_1.0
        @param f:
        @return:
        """
        table = []
        for j in range(65):
            for k in range(65):
                dx = int(round(struct.unpack("d", f.read(8))[0]))
                dx = dx if dx >= 0 else -dx + 0x8000
                dy = int(round(struct.unpack("d", f.read(8))[0]))
                dy = dy if dy >= 0 else -dy + 0x8000
                table.append([dx & 0xFFFF, dy & 0xFFFF])
        return table

    def _read_int_correction_file(self, f):
        table = []
        for j in range(65):
            for k in range(65):
                dx = int.from_bytes(f.read(4), "little", signed=True)
                dx = dx if dx >= 0 else -dx + 0x8000
                dy = int.from_bytes(f.read(4), "little", signed=True)
                dy = dy if dy >= 0 else -dy + 0x8000
                table.append([dx & 0xFFFF, dy & 0xFFFF])
        return table

    def _read_correction_file(self, filename):
        """
        Reads a standard .cor file and builds a table from that.

        @param filename:
        @return:
        """
        with open(filename, "rb") as f:
            label = f.read(0x16)
            if label.decode("utf-16") == "LMC1COR_1.0":
                header = f.read(0x1FA)
                return self._read_float_correction_file(f)
            else:
                header = f.read(0xE)
                return self._read_int_correction_file(f)

    def _write_correction_table(self, table):
        assert len(table) == 65 * 65
        self.write_cor_table(True)
        first = True
        for dx, dy in table:
            self.write_cor_line(dx, dy, 0 if first else 1)
            first = False

    #######################
    # COMMAND LIST COMMAND
    #######################

    def list_jump(self, x, y, short=None, long=None, distance_limit=None):
        distance = int(abs(complex(x, y) - complex(self._last_x, self._last_y)))
        if distance_limit and distance > distance_limit:
            delay = long
        else:
            delay = short
        if distance > 0xFFFF:
            distance = 0xFFFF
        angle = 0
        if delay:
            self.list_jump_delay(delay)
        x = int(x)
        y = int(y)
        self._list_write(listJumpTo, x, y, angle, distance)
        self._last_x = x
        self._last_y = y

    def list_end_of_list(self):
        self._list_write(listEndOfList)

    def list_laser_on_point(self, dwell_time):
        self._list_write(listLaserOnPoint, dwell_time)

    def list_delay_time(self, time):
        """
        Delay time in 10 microseconds units

        @param time:
        @return:
        """
        self._list_write(listDelayTime, abs(time))

    def list_mark(self, x, y, angle=0):
        distance = int(abs(complex(x, y) - complex(self._last_x, self._last_y)))
        if distance > 0xFFFF:
            distance = 0xFFFF
        x = int(x)
        y = int(y)
        self._list_write(listMarkTo, x, y, angle, distance)
        self._last_x = x
        self._last_y = y

    def list_jump_speed(self, speed):
        if self._travel_speed == speed:
            return
        self._travel_speed = speed
        c_speed = self._convert_speed(speed)
        if c_speed > 0xFFFF:
            c_speed = 0xFFFF
        self._list_write(listJumpSpeed, c_speed)

    def list_laser_on_delay(self, delay):
        """
        Set laser on delay in microseconds
        @param delay:
        @return:
        """
        if self._delay_on == delay:
            return
        self._delay_on = delay
        self._list_write(listLaserOnDelay, abs(delay), 0x0000 if delay > 0 else 0x8000)

    def list_laser_off_delay(self, delay):
        """
        Set laser off delay in microseconds
        @param delay:
        @return:
        """
        if self._delay_off == delay:
            return
        self._delay_off = delay
        self._list_write(listLaserOffDelay, abs(delay), 0x0000 if delay > 0 else 0x8000)

    def list_mark_frequency(self, frequency):
        """
        This command is used in some machines but it's not clear given the amount of reverse engineering how those
        values are set. This is done for laser_type = 4.

        @param frequency:
        @return:
        """
        # listMarkFreq
        raise NotImplementedError

    def list_mark_power_ratio(self, power_ratio):
        """
        This command is used in some machines. Laser_type=4 and laser_type=0 (CO2), if 0x800A returned 0.

        @param power_ratio:
        @return:
        """
        # listMarkPowerRatio
        self._list_write(listMarkPowerRatio, power_ratio)

    def list_mark_speed(self, speed):
        """
        Sets the marking speed for the laser.

        @param speed:
        @return:
        """
        if self._speed == speed:
            return
        self._speed = speed
        c_speed = self._convert_speed(speed)
        if c_speed > 0xFFFF:
            c_speed = 0xFFFF
        self._list_write(listMarkSpeed, c_speed)

    def list_jump_delay(self, delay):
        """
        Set laser jump delay in microseconds
        @param delay:
        @return:
        """
        if self._delay_jump == delay:
            return
        self._delay_jump = delay
        self._list_write(listJumpDelay, abs(delay), 0x0000 if delay > 0 else 0x8000)

    def list_polygon_delay(self, delay):
        """
        Set polygon delay in microseconds
        @param delay:
        @return:
        """
        if self._delay_poly == delay:
            return
        self._delay_poly = delay
        self._list_write(listPolygonDelay, abs(delay), 0x0000 if delay > 0 else 0x8000)

    def list_write_port(self):
        """
        Writes the set port values to the list.

        @return:
        """
        self._list_write(listWritePort, self._port_bits)

    def list_mark_current(self, current):
        """
        Also called as part of setting the power ratio. This is not correctly understood.
        @param current:
        @return:
        """
        # listMarkCurrent
        self._list_write(listMarkCurrent, current)

    def list_mark_frequency_2(self, frequency):
        """
        Also called as part of setting frequency and is not correctly understood.

        @param frequency:
        @return:
        """
        # listMarkFreq2
        raise NotImplementedError

    def list_fly_enable(self, enabled=1):
        """
        On-The-Fly control enable/disable within list.

        @param enabled:
        @return:
        """
        self._list_write(listFlyEnable, enabled)

    def list_qswitch_period(self, qswitch):
        """
        Sets the qswitch period, which in is the inversely related to frequency.

        @param qswitch:
        @return:
        """
        self._list_write(listQSwitchPeriod, qswitch)

    def list_direct_laser_switch(self):
        """
        This is not understood.
        @return:
        """
        # ListDirectLaserSwitch
        raise NotImplementedError

    def list_fly_delay(self, delay):
        """
        On-the-fly control.

        @param delay:
        @return:
        """
        self._list_write(listFlyDelay, abs(delay), 0x0000 if delay > 0 else 0x8000)

    def list_set_co2_fpk(self):
        """
        Set the CO2 Laser, First Pulse Killer.

        @return:
        """
        self._list_write(listSetCo2FPK)

    def list_fly_wait_input(self):
        """
        Sets the On-the-fly to wait for input.
        @return:
        """
        self._list_write(listFlyWaitInput)

    def list_fiber_open_mo(self, open_mo):
        """
        Sets motion operations, without MO set the laser does not automatically fire while moving.

        @param open_mo:
        @return:
        """
        self._list_write(listFiberOpenMO, open_mo)

    def list_wait_for_input(self, wait_mask, wait_level):
        """
        Unknown.

        @return:
        """
        self._list_write(listWaitForInput, wait_mask, wait_level)

    def list_change_mark_count(self, count):
        """
        Unknown.

        @param count:
        @return:
        """
        self._list_write(listChangeMarkCount, count)

    def list_set_weld_power_wave(self, weld_power_wave):
        """
        Unknown.

        @param weld_power_wave:
        @return:
        """
        self._list_write(listSetWeldPowerWave, weld_power_wave)

    def list_enable_weld_power_wave(self, enabled):
        """
        Unknown.

        @param enabled:
        @return:
        """
        self._list_write(listEnableWeldPowerWave, enabled)

    def list_fiber_ylpm_pulse_width(self, pulse_width):
        """
        Unknown.

        @param pulse_width:
        @return:
        """
        if self._pulse_width == pulse_width:
            return
        self._pulse_width = pulse_width
        self._list_write(listFiberYLPMPulseWidth, pulse_width)

    def list_fly_encoder_count(self, count):
        """
        Unknown.

        @param count:
        @return:
        """
        self._list_write(listFlyEncoderCount, count)

    def list_set_da_z_word(self, word):
        """
        Unknown.

        @param word:
        @return:
        """
        self._list_write(listSetDaZWord, word)

    def list_jpt_set_param(self, param):
        """
        Unknown.

        @param param:
        @return:
        """
        self._list_write(listJptSetParam, param)

    def list_ready(self):
        """
        Seen at the start of any new command list.

        @return:
        """
        self._list_write(listReadyMark)

    #######################
    # COMMAND LIST SHORTCUTS
    #######################

    def disable_laser(self):
        return self._command(DisableLaser)

    def enable_laser(self):
        return self._command(EnableLaser)

    def execute_list(self):
        return self._command(ExecuteList)

    def set_pwm_pulse_width(self, pulse_width):
        return self._command(SetPwmPulseWidth, pulse_width)

    def get_version(self):
        return self._command(GetVersion)

    def get_serial_number(self):
        return self._command(GetSerialNo)

    def get_list_status(self):
        return self._command(GetListStatus)

    def get_position_xy(self):
        return self._command(GetPositionXY)

    def goto_xy(self, x, y, angle=0, distance=0):
        self._last_x = x
        self._last_y = y
        return self._command(GotoXY, int(x), int(y), int(angle), int(distance))

    def laser_signal_off(self):
        return self._command(LaserSignalOff)

    def laser_signal_on(self):
        return self._command(LaserSignalOn)

    def write_cor_line(self, dx, dy, non_first):
        self._command(WriteCorLine, dx, dy, non_first, read=False)

    def reset_list(self):
        return self._command(ResetList)

    def restart_list(self):
        return self._command(RestartList)

    def write_cor_table(self, table: bool = True):
        return self._command(WriteCorTable, int(table))

    def set_control_mode(self, mode):
        return self._command(SetControlMode, mode)

    def set_delay_mode(self, mode):
        return self._command(SetDelayMode, mode)

    def set_max_poly_delay(self, delay):
        return self._command(
            SetMaxPolyDelay, abs(delay), 0x0000 if delay > 0 else 0x8000
        )

    def set_end_of_list(self, end):
        return self._command(SetEndOfList, end)

    def set_first_pulse_killer(self, fpk):
        return self._command(SetFirstPulseKiller, fpk)

    def set_laser_mode(self, mode):
        return self._command(SetLaserMode, mode)

    def set_timing(self, timing):
        return self._command(SetTiming, timing)

    def set_standby(self, standby1, standby2):
        return self._command(SetStandby, standby1, standby2)

    def set_pwm_half_period(self, pwm_half_period):
        return self._command(SetPwmHalfPeriod, pwm_half_period)

    def stop_execute(self):
        return self._command(StopExecute)

    def stop_list(self):
        return self._command(StopList)

    def write_port(self):
        return self._command(WritePort, self._port_bits)

    def write_analog_port_1(self, port):
        return self._command(WriteAnalogPort1, port)

    def write_analog_port_2(self, port):
        return self._command(WriteAnalogPort2, port)

    def write_analog_port_x(self, port):
        return self._command(WriteAnalogPortX, port)

    def read_port(self):
        return self._command(ReadPort)

    def set_axis_motion_param(self, param):
        return self._command(SetAxisMotionParam, param)

    def set_axis_origin_param(self, param):
        return self._command(SetAxisOriginParam, param)

    def axis_go_origin(self):
        return self._command(AxisGoOrigin)

    def move_axis_to(self, a):
        return self._command(MoveAxisTo)

    def get_axis_pos(self):
        return self._command(GetAxisPos)

    def get_fly_wait_count(self):
        return self._command(GetFlyWaitCount)

    def get_mark_count(self):
        return self._command(GetMarkCount)

    def set_pfk_param_2(self, param1, param2, param3, param4):
        return self._command(SetFpkParam2, param1, param2, param3, param4)

    def set_fiber_mo(self, mo):
        """
        mo == 0 close
        mo == 1 open

        @param mo:
        @return:
        """
        return self._command(Fiber_SetMo, mo)

    def get_fiber_st_mo_ap(self):
        return self._command(Fiber_GetStMO_AP)

    def enable_z(self):
        return self._command(EnableZ)

    def disable_z(self):
        return self._command(DisableZ)

    def set_z_data(self, zdata):
        return self._command(SetZData, zdata)

    def set_spi_simmer_current(self, current):
        return self._command(SetSPISimmerCurrent, current)

    def set_fpk_param(self, param):
        return self._command(SetFpkParam, param)

    def reset(self):
        return self._command(Reset)

    def get_fly_speed(self):
        return self._command(GetFlySpeed)

    def fiber_pulse_width(self):
        return self._command(FiberPulseWidth)

    def get_fiber_config_extend(self):
        return self._command(FiberGetConfigExtend)

    def input_port(self, port):
        return self._command(InputPort, port)

    def clear_lock_input_port(self):
        return self._command(InputPort, 0x04)

    def enable_lock_input_port(self):
        return self._command(InputPort, 0x02)

    def disable_lock_input_port(self):
        return self._command(InputPort, 0x01)

    def get_input_port(self):
        return self._command(InputPort)

    def get_mark_time(self):
        """
        Get Mark Time is always called with data 3. With 0 it returns 0. It is unknown what the payload means.
        @return:
        """
        return self._command(GetMarkTime, 3)

    def get_user_data(self):
        return self._command(GetUserData)

    def set_fly_res(self, fly_res1, fly_res2, fly_res3, fly_res4):
        return self._command(SetFlyRes, fly_res1, fly_res2, fly_res3, fly_res4)
