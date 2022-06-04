import math
from copy import copy

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
listIPGOpenMO = 0x8021
listWaitForInput = 0x8022
listChangeMarkCount = 0x8023
listSetWeldPowerWave = 0x8024
listEnableWeldPowerWave = 0x8025
listIPGYLPMPulseWidth = 0x8026
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
Unknown_Init = 0x0024
GetFlySpeed = 0x0038
IPGPulseWidth = 0x002F
IPGGetConfigExtend = 0x0030
InputPort = 0x0031  # ClearLockInputPort calls 0x04, then if EnableLockInputPort 0x02 else 0x01, GetLockInputPort
GetMarkTime = 0x0041
GetUserData = 0x0036
SetFlyRes = 0x0032


class CommandSequencer:
    """
    This should serve as a next generation command sequencer written from scratch for galvo lasers. The goal is to
    provide all the given commands in a coherent queue structure which provides correct sequences between list and
    single commands.
    """

    def __init__(
        self,
        x=0x8000,
        y=0x8000,
        mark_speed=None,
        goto_speed=None,
        light_speed=None,
        dark_speed=None,
    ):
        self._queue = list()
        self._active_list = None
        self._active_index = 0
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

        self._delay_on = None
        self._delay_off = None
        self._delay_poly = None
        self._delay_end = None

        self._wobble = None

    def _command_to_bytes(self, command, v1=0, v2=0, v3=0, v4=0, v5=0):
        return bytes(
            [
                command & 0xFF,
                command >> 8 & 0xFF,
                v1 & 0xFF,
                v1 >> 8 & 0xFF,
                v2 & 0xFF,
                v2 >> 8 & 0xFF,
                v3 & 0xFF,
                v3 >> 8 & 0xFF,
                v4 & 0xFF,
                v4 >> 8 & 0xFF,
                v5 & 0xFF,
                v5 >> 8 & 0xFF,
            ]
        )

    def _list_end(self):
        self._queue.append(self._active_list)
        self._active_list = None
        self._active_index = 0

    def _list_new(self):
        self._active_list = copy(empty)
        self._active_index = 0

    def _list_write(self, command, v1=0, v2=0, v3=0, v4=0, v5=0):
        if self._active_index >= 0xC00:
            self._list_end()
        if self._active_list is None:
            self._list_new()
        self._active_list[
            self._active_index : self._active_list + 12
        ] = self._command_to_bytes(command, v1, v2, v3, v4, v5)
        self._active_index += 12

    def _convert_speed(self, speed):
        """
        mm/s speed implies a distance but the galvo head doesn't move mm and doesn't know what lens you are currently
        using which changes the definition of what a mm is, this calculation is likely naive for a particular lens size
        and needs to be scaled according the other relevant factors.

        @param speed:
        @return:
        """
        return int(speed / 2.0)

    def list_jump(self, x, y):
        self._list_write(listJumpTo, int(x), int(y))

    def list_end_of_list(self):
        self._list_write(listEndOfList)

    def list_laser_on_point(self):
        self._list_write(listLaserOnPoint)

    def list_delay_time(self, time):
        """
        Delay time in 10 microseconds units

        @param time:
        @return:
        """
        self._list_write(listDelayTime, time)

    def list_mark(self, x, y, angle=0):
        distance = int(abs(complex(x, y) - complex(self._last_x, self._last_y)))
        if distance > 0xFFFF:
            distance = 0xFFFF
        self._list_write(listMarkTo, x, y, angle, distance)

    def list_jump_speed(self, speed):
        self._list_write(listJumpSpeed, self._convert_speed(speed))

    def list_laser_on_delay(self, delay):
        """
        Set laser on delay in microseconds
        @param delay:
        @return:
        """
        sign = 0
        if delay < 0:
            sign = 0x8000
        self._list_write(listLaserOnDelay, delay, sign)

    def list_laser_off_delay(self, delay):
        """
        Set laser off delay in microseconds
        @param delay:
        @return:
        """
        sign = 0
        if delay < 0:
            sign = 0x8000
        self._list_write(listLaserOffDelay, delay, sign)

    def list_mark_frequency(self, frequency):
        pass


class Wobble:
    def __init__(self, radius=50, speed=50, interval=10):
        self._total_count = 0
        self._total_distance = 0
        self._remainder = 0
        self.previous_angle = None
        self.radius = radius
        self.speed = speed
        self.interval = interval
        self._last_x = None
        self._last_y = None

    def wobble(self, x0, y0, x1, y1):
        distance_change = abs(complex(x0, y0) - complex(x1, y1))
        positions = 1 - self._remainder
        intervals = distance_change / self.interval
        while positions <= intervals:
            amount = positions / intervals
            tx = amount * (x1 - x0) + x0
            ty = amount * (y1 - y0) + y0
            self._total_distance += self.interval
            self._total_count += 1
            yield tx, ty
            positions += 1
        self._remainder += intervals
        self._remainder %= 1

    def circle(self, x0, y0, x1, y1):
        if x1 is None or y1 is None:
            yield x0, y0
            return
        for tx, ty in self.wobble(x0, y0, x1, y1):
            t = self._total_distance / (math.tau * self.radius)
            dx = self.radius * math.cos(t * self.speed)
            dy = self.radius * math.sin(t * self.speed)
            yield tx + dx, ty + dy

    def sinewave(self, x0, y0, x1, y1):
        if x1 is None or y1 is None:
            yield x0, y0
            return
        for tx, ty in self.wobble(x0, y0, x1, y1):
            angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
            d = math.sin(self._total_distance / self.speed)
            dx = self.radius * d * math.cos(angle)
            dy = self.radius * d * math.sin(angle)
            yield tx + dx, ty + dy

    def sawtooth(self, x0, y0, x1, y1):
        if x1 is None or y1 is None:
            yield x0, y0
            return
        for tx, ty in self.wobble(x0, y0, x1, y1):
            angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
            d = -1 if self._total_count % 2 else 1
            dx = self.radius * d * math.cos(angle)
            dy = self.radius * d * math.sin(angle)
            yield tx + dx, ty + dy

    def jigsaw(self, x0, y0, x1, y1):
        if x1 is None or y1 is None:
            yield x0, y0
            return
        for tx, ty in self.wobble(x0, y0, x1, y1):
            angle = math.atan2(y1 - y0, x1 - x0)
            angle_perp = angle + math.tau / 4.0
            d = math.sin(self._total_distance / self.speed)
            dx = self.radius * d * math.cos(angle_perp)
            dy = self.radius * d * math.sin(angle_perp)

            d = -1 if self._total_count % 2 else 1
            dx += self.radius * d * math.cos(angle)
            dy += self.radius * d * math.sin(angle)
            yield tx + dx, ty + dy

    def gear(self, x0, y0, x1, y1):
        if x1 is None or y1 is None:
            yield x0, y0
            return
        for tx, ty in self.wobble(x0, y0, x1, y1):
            angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
            d = -1 if (self._total_count // 2) % 2 else 1
            dx = self.radius * d * math.cos(angle)
            dy = self.radius * d * math.sin(angle)
            yield tx + dx, ty + dy

    def slowtooth(self, x0, y0, x1, y1):
        if x1 is None or y1 is None:
            yield x0, y0
            return
        for tx, ty in self.wobble(x0, y0, x1, y1):
            angle = math.atan2(y1 - y0, x1 - x0) + math.tau / 4.0
            if self.previous_angle is None:
                self.previous_angle = angle
            amount = 1.0 / self.speed
            angle = amount * (angle - self.previous_angle) + self.previous_angle
            d = -1 if self._total_count % 2 else 1
            dx = self.radius * d * math.cos(angle)
            dy = self.radius * d * math.sin(angle)
            self.previous_angle = angle
            yield tx + dx, ty + dy
