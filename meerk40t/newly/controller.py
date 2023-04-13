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

        # Load Primary Pens
        self.sp0 = self.service.setting(int, "sp0", 0)
        self.sp1 = self.service.setting(int, "sp1", 1)
        self.sp2 = self.service.setting(int, "sp2", 2)

        self.connection = None
        self._is_opening = False
        self._abort_open = False
        self._disable_connect = False

        self._job_x = None
        self._job_y = None

        self._last_x = x
        self._last_y = y

        self._last_updated_x = x
        self._last_updated_y = y

        #######################
        # Preset Modes.
        #######################

        self._set_pen = None
        self._set_cut_dc = None
        self._set_move_dc = None
        self._set_mode = None
        self._set_speed = None
        self._set_power = None
        self._set_pwm_freq = None
        self._set_relative = None
        self._set_bit_depth = None
        self._set_bit_width = None
        self._set_backlash = None
        self._set_corner_speed = None
        self._set_acceleration_length = None

        #######################
        # Current Set Modes.
        #######################

        self._pen = None
        self._cut_dc = None
        self._move_dc = None
        self._mode = None
        self._speed = None
        self._power = None
        self._pwm_frequency = None
        self._relative = None
        self._bit_depth = None
        self._bit_width = None
        self._backlash = None
        self._corner_speed = None
        self._acceleration_length = None

        self._realtime = False

        self.mode = "init"
        self.paused = False
        self._command_buffer = []

    def __call__(self, cmd, *args, **kwargs):
        if isinstance(cmd, str):
            # Any string data sent is latin-1 encoded.
            self._command_buffer.append(cmd.encode("latin-1"))
        else:
            self._command_buffer.append(cmd)

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

    def sync(self):
        self._last_updated_x, self._last_updated_y = self._last_x, self._last_y

    def update(self):
        last_x, last_y = self.service.device.device_to_scene_position(
            self._last_updated_x, self._last_updated_y
        )
        x, y = self.service.device.device_to_scene_position(self._last_x, self._last_y)
        self.sync()
        self.service.signal("driver;position", (last_x, last_y, x, y))

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

    def _clear_settings(self):
        self._set_pen = None
        self._set_cut_dc = None
        self._set_move_dc = None
        self._set_mode = None
        self._set_speed = None
        self._set_power = None
        self._set_pwm_freq = None
        self._set_relative = None
        self._set_bit_depth = None
        self._set_bit_width = None
        self._set_backlash = None
        self._set_corner_speed = None
        self._set_acceleration_length = None

        self._pen = None
        self._cut_dc = None
        self._move_dc = None
        self._mode = None
        self._speed = None
        self._power = None
        self._pwm_frequency = None
        self._relative = None
        self._bit_depth = None
        self._bit_width = None
        self._backlash = None
        self._corner_speed = None
        self._acceleration_length = None

    def _set_move_mode(self):
        """
        Move mode is done for any major movements usually starting out an execution.

        eg.
        VP100;VK100;SP2;SP2;VQ15;VJ24;VS10;DA0;
        @return:
        """
        self._set_pen = self.sp2
        self._set_cut_dc = self.service.cut_dc
        self._set_move_dc = self.service.move_dc
        self._set_mode = "move"
        self._set_speed = self.service.moving_speed
        self._set_pwm_freq = None
        self._set_relative = True
        self._set_bit_depth = None
        self._set_bit_width = None
        self._set_backlash = None
        self._set_corner_speed = None
        self._set_acceleration_length = None

    def _set_goto_mode(self):
        """
        Goto mode is done for minor between movements, where we don't need to set the power to 0, since we will be
        using PU; commands.

        eg.
        SP2;SP2;VQ15;VJ24;VS10;PR;PU2083,-5494;

        @return:
        """
        self._set_pen = self.sp2
        self._set_mode = "goto"
        self._set_speed = self.service.moving_speed
        self._set_relative = True

    def _set_frame_mode(self):
        """
        Frame mode is the standard framing operation settings.
        eg.
        SP0;VS20;PR;PD9891,0;PD0,-19704;PD-9891,0;PD0,19704;ZED;

        @return:
        """

        self._set_cut_dc = self.service.cut_dc
        self._set_move_dc = self.service.move_dc
        self._set_pen = self.sp0
        self._set_power = 0
        self._set_relative = True
        self._set_mode = "frame"
        self._set_speed = self.service.moving_speed
        if self.service.pwm_enabled:
            self._set_pwm_freq = self.service.pwm_frequency

    def _set_vector_mode(self):
        """
        Vector mode typically is just the PD commands for a vector.

        eg.
        PR;SP1;DA65;VS187;PD0,-2534;PD1099,0;PD0,2534;PD-1099,0;
        @return:
        """
        self._set_pen = self.sp1
        self._set_cut_dc = self.service.cut_dc
        self._set_move_dc = self.service.move_dc
        self._set_mode = "vector"
        self._set_speed = self.service.default_cut_speed
        self._set_power = self.service.default_cut_power
        if self.service.pwm_enabled:
            self._set_pwm_freq = self.service.pwm_frequency
        self._set_relative = True
        self._set_bit_depth = None
        self._set_bit_width = None
        self._set_backlash = None

    def _set_raster_mode(self):
        """
        Raster mode is the typical preamble and required settings for running a raster. This usually consists of
        YF, YZ, XF, XZ, and small PU commands.

        EG.
        BT1;DA77;BC0;BD3;SP0;VQ20;VJ10;VS18;YF...
        @return:
        """
        self._set_pen = self.sp0
        self._set_cut_dc = self.service.cut_dc
        self._set_move_dc = self.service.move_dc
        self._set_mode = "raster"
        self._corner_speed = None
        self._acceleration_length = None
        if self.service.pwm_enabled:
            self._set_pwm_freq = self.service.pwm_frequency
        self._set_relative = True
        self._set_bit_depth = 1
        self._set_bit_width = 1
        self._set_speed = self.service.default_raster_speed
        self._set_power = self.service.default_raster_power

    def _write_frame(self, outline):
        self.mode = "frame"
        if outline is not None:
            x, y = self._last_x, self._last_y
            self("DW")
            for pt in outline:
                self.frame(*pt)
            self.frame(*outline[0])
            self.goto(x, y)  # Return to initial x, y if different than outline.
            self._clear_settings()
            self("ZED")

    def _execute_job(self):
        self("ZED")
        cmd = b";".join(self._command_buffer) + b";"
        self.connect_if_needed()
        self.connection.write(index=self._machine_index, data=cmd)
        self._command_buffer.clear()
        self._clear_settings()

    def open_job(self, job=None):
        """
        Opens a job at the declared file_index

        @return:
        """

        outline = None
        try:
            outline = job.outline
        except AttributeError:
            pass
        if outline is not None:
            self.set_xy(*outline[0])
            self._job_x, self._job_y = outline[0]
        self._realtime = False
        self._clear_settings()
        self(f"ZZZFile{self.service.file_index}")
        self._write_frame(outline)
        self("GZ")
        self._clear_settings()

    def close_job(self, job=None):
        """
        Closes the file and sends.
        @return:
        """
        if not self._command_buffer:
            return
        if self.mode in ("realtime", "init"):
            # Job contains no instructions.
            self.mode = "init"
            self._command_buffer.clear()
            return
        if not self._realtime and self._job_x is not None and self._job_y is not None:
            self.goto_rel(self._job_x, self._job_y)

        self._execute_job()
        self.mode = "init"
        if self.service.autoplay and not self._realtime:
            self.replay(self.service.file_index)

    def program_mode(self):
        self._set_vector_mode()

    def rapid_mode(self):
        pass

    #######################
    # Raster Events
    #######################

    def scanline(self, bits, right=False, left=False, top=False, bottom=False):
        """
        Send a scanline movement.

        @param bits: list of bits.
        @param right: Moving right?
        @param left: Moving left?
        @param top: Moving top?
        @param bottom: Moving bottom?
        @return:
        """
        self._commit_settings()
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
        elif bottom:
            self._last_y += count

    def raster(self, raster_cut: RasterCut):
        """
        Run a raster cut with scanlines and default actions.

        @param raster_cut:
        @return:
        """

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

        self("IN")
        self._clear_settings()

        previous_x, previous_y = raster_cut.plot.initial_position_in_scene()

        self.goto(previous_x, previous_y)

        self._set_raster_mode()
        self.set_settings(raster_cut.settings)
        self._set_mode = "raster"

        self._commit_settings()

        if raster_cut.horizontal:
            self.mode = "raster_horizontal"
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
                    self._relative = True
                    self("PR")
                    self._goto(x, y)  # remain standard rastermode
                if dx != 0:
                    # Normal move, extend bytes.
                    scanline.extend([int(on)] * abs(dx))
                previous_x, previous_y = x, y
        else:
            self.mode = "raster_vertical"
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
                    self._relative = True
                    self("PR")
                    self._goto(x, y)  # remain standard rastermode
                if dy != 0:
                    # Normal move, extend bytes
                    scanline.extend([int(on)] * abs(dy))
                previous_x, previous_y = x, y
        commit_scanline()

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        if "speed" in settings:
            self._set_speed = settings.get("speed")
        if "power" in settings:
            self._set_power = settings.get("power")
        if "pwm_frequency" in settings:
            self._set_pwm_freq = settings.get("pwm_frequency")

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def raw(self, data):
        data = bytes(data, "latin1")
        self.connect_if_needed()
        self.connection.write(index=self._machine_index, data=data)

    def frame(self, x, y):
        self._set_frame_mode()
        self._mark(x, y)

    def mark(self, x, y, settings=None, power=None, speed=None):
        """
        Mark either sets default vector settings or sets the settings based on the settings object provided.
        @param x:
        @param y:
        @param settings:
        @return:
        """
        self._set_vector_mode()
        if settings is not None:
            self.set_settings(settings)
        if power is not None:
            self._set_power = power
        if speed is not None:
            self._set_speed = speed
        self._mark(x, y)

    def _mark(self, x, y):
        dx = int(round(x - self._last_x))
        dy = int(round(y - self._last_y))
        if dx == 0 and dy == 0:
            return
        self._commit_settings()
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
        """
        Goto position.
        @param x:
        @param y:
        @return:
        """
        self.goto_rel(x, y)

    def goto_abs(self, x, y):
        """
        Goto given absolute coords value.
        @param x:
        @param y:
        @return:
        """
        self._set_move_mode()
        self._relative = False
        self._goto(x, y)

    def goto_rel(self, x, y):
        """
        Positions are given in absolute coords, but the motion sent to the laser is relative.
        @param x:
        @param y:
        @return:
        """
        self._set_move_mode()
        self._goto(x, y)

    def _goto(self, x, y):
        dx = int(round(x - self._last_x))
        dy = int(round(y - self._last_y))
        if dx == 0 and dy == 0:
            return
        self._commit_settings()
        if self._relative:
            self(f"PU{dy},{dx}")
            self._last_x += dx
            self._last_y += dy
        else:
            x = int(round(x))
            y = int(round(y))
            self(f"PU{y},{x}")
            self._last_x, self._last_y = x, y

    def set_xy(self, x, y):
        self.realtime_job()
        self.mode = "jog"
        self.goto_rel(x, y)
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
        self._last_x = 0
        self._last_y = 0
        self.close_job()

    def origin(self):
        self.realtime_job()
        self.mode = "origin"
        self.goto(0, 0)
        self.close_job()

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
        self._set_power = power

    #######################
    # Commit settings
    #######################

    def _commit_settings(self):
        if self._set_speed is not None:
            # If set speed is set, we set all the various speed chart lookup properties.
            settings = self._get_chart_settings_for_speed(self._set_speed)
            self._set_corner_speed = int(round(settings["corner_speed"]))
            self._set_acceleration_length = int(round(settings["acceleration_length"]))
            self._set_backlash = int(round(settings["backlash"]))

        self.commit_mode()
        self._commit_pwmfreq()
        self._commit_dc()
        if self._mode != "raster":
            self._commit_pen()
        self._commit_power()
        if self._mode == "raster":
            self._commit_raster()
            self._commit_pen()
        if self._mode != "vector":
            self._commit_corner_speed()
            self._commit_acceleration_length()
        self._commit_speed()
        self._commit_relative_mode()

    def commit_mode(self):
        if self._set_mode is None:
            # Quick fail.
            return
        new_mode = self._set_mode
        self._set_mode = None
        if new_mode != self._mode:
            self._mode = new_mode

            # Old speed and power are void on mode change.
            self._speed = None
            self._power = None
            self._corner_speed = None
            self._acceleration_length = None
            self._backlash = None

    #######################
    # Commit DC Info
    #######################

    def _commit_cut_dc(self):
        if self._set_cut_dc is None and self._cut_dc is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_dc = self._set_cut_dc
        self._set_cut_dc = None
        if new_dc is None:
            # Nothing set, set default.
            new_dc = self.service.cut_dc
        if new_dc != self._cut_dc:
            # DC is different
            self._cut_dc = new_dc
            self(f"VP{self._cut_dc}")

    def _commit_move_dc(self):
        if self._set_move_dc is None and self._move_dc is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_dc = self._set_move_dc
        self._set_move_dc = None
        if new_dc is None:
            # Nothing set, set default.
            new_dc = self.service.move_dc
        if new_dc != self._move_dc:
            # DC is different
            self._move_dc = new_dc
            self(f"VK{self._move_dc}")

    def _commit_dc(self):
        self._commit_cut_dc()
        self._commit_move_dc()

    #######################
    # Commit Pen
    #######################

    def _commit_pen(self):
        if self._set_pen is None and self._pen is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_pen = self._set_pen
        self._set_pen = None
        if new_pen is None:
            # Nothing set, set default.
            new_pen = 0
        if new_pen != self._pen:
            # PEN is different
            self._pen = new_pen
            self(f"SP{self._pen}")

    #######################
    # Commit Power
    #######################

    def _map_power(self, power):
        power /= 1000.0  # Scale to 0-1
        power *= self.service.max_power  # Scale by max power %
        power *= 255.0 / 100.0  # range between 000 and 255
        if power > 255:
            return 255
        if power <= 0:
            return 0
        return int(round(power))

    def _commit_power(self):
        """
        Write power information. If the _set_power is set then it takes priority. Otherwise, the power remains set to
        what it was previously set to. If no power is set, then power is set to the default cut power.

        @return:
        """
        if self._set_power is None and self._power is not None:
            return  # quick fail.

        new_power = self._set_power
        self._set_power = None

        if new_power is None:
            return

        if new_power != self._power:
            # Already set power is not the new_power setting.
            self._power = new_power
            self(f"DA{self._map_power(self._power)}")

    def _commit_pwmfreq(self):
        """
        Write pwm frequency information.
        @return:
        """
        if self._set_pwm_freq is None and self._pwm_frequency is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_freq = self._set_pwm_freq
        self._set_pwm_freq = None
        if new_freq is None:
            return
        if new_freq != self._pwm_frequency:
            # Frequency is needed, and different
            self._pwm_frequency = new_freq
            self(f"PL{self._pwm_frequency}")

    #######################
    # Commit speed settings
    #######################

    def _commit_speed(self):
        if self._set_speed is None and self._speed is not None:
            return
        new_speed = self._set_speed
        self._set_speed = None
        if new_speed is not None and new_speed != self._speed:
            self._speed = new_speed
            if self._mode == "vector":
                self(f"VS{self._map_vector_speed(new_speed)}")
            else:
                self(f"VS{self._map_raster_speed(new_speed)}")

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
            if chart_speed > speed and smallest_difference > delta_speed:
                smallest_difference = delta_speed
                closest_index = i
        if closest_index is not None:
            return chart[closest_index]
        return chart[-1]

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

    #######################
    # Commit Speed Chart
    #######################

    def _commit_corner_speed(self):
        if self._set_corner_speed is None and self._corner_speed is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_corner_speed = self._set_corner_speed
        self._set_corner_speed = None
        if new_corner_speed is None:
            # Nothing set, set default.
            return
        if new_corner_speed != self._corner_speed:
            # Corner_speed is different
            self._corner_speed = new_corner_speed
            self(f"VQ{int(round(self._corner_speed))}")

    def _commit_acceleration_length(self):
        if (
            self._set_acceleration_length is None
            and self._acceleration_length is not None
        ):
            # Quick Fail.
            return

        # Fetch Requested.
        new_acceleration_length = self._set_acceleration_length
        self._set_acceleration_length = None
        if new_acceleration_length is None:
            # Nothing set, set default.
            return
        if new_acceleration_length != self._acceleration_length:
            # Acceleration Length is different
            self._acceleration_length = new_acceleration_length
            self(f"VJ{int(round(self._acceleration_length))}")

    #######################
    # Commit Relative Mode
    #######################

    def _commit_relative_mode(self):
        if self._set_relative is None and self._relative is not None:
            return
        new_relative = self._set_relative
        self._set_relative = None

        if new_relative is None:
            new_relative = True

        if new_relative != self._relative:
            self._relative = new_relative
            if self._relative:
                self("PR")
            else:
                self("PA")

    #######################
    # Commit Raster
    #######################

    def _commit_raster_bitdepth(self):
        if self._set_bit_depth is None and self._bit_depth is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_bitdepth = self._set_bit_depth
        self._set_bit_depth = None
        if new_bitdepth is None:
            # Nothing set, set default.
            return
        if new_bitdepth != self._bit_depth:
            # Bitdepth is different
            self._bit_depth = new_bitdepth
            self(f"BT{self._bit_depth}")

    def _commit_raster_bitwidth(self):
        if self._set_bit_width is None and self._bit_width is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_bitwidth = self._set_bit_width
        self._set_bit_width = None
        if new_bitwidth is None:
            # Nothing set, set default.
            return
        if new_bitwidth != self._bit_width:
            # Bitdepth is different
            self._bit_width = new_bitwidth
            self(f"BD{self._bit_width}")

    def _commit_raster_backlash(self):
        if self._set_backlash is None and self._backlash is not None:
            # Quick Fail.
            return

        # Fetch Requested.
        new_backlash = self._set_backlash
        self._set_backlash = None
        if new_backlash is None:
            # Nothing set, set default.
            return
        if new_backlash != self._backlash:
            # backlash is different
            self._backlash = new_backlash
            self(f"BC{self._backlash}")

    def _commit_raster(self):
        self._commit_raster_bitdepth()
        self._commit_raster_backlash()
        self._commit_raster_bitwidth()
