"""
GRBL Driver

Governs the generic commands issued by laserjob and spooler and converts that into regular GRBL Gcode output.
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

from ..core.geomstr import Geomstr
from ..core.parameters import Parameters
from ..core.plotplanner import PlotPlanner
from ..core.units import UNITS_PER_INCH, UNITS_PER_MIL, UNITS_PER_MM, Length
from ..device.basedevice import PLOT_FINISH, PLOT_JOG, PLOT_RAPID, PLOT_SETTING
from ..kernel import signal_listener


class GRBLDriver(Parameters):
    def __init__(self, service, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.name = str(service)
        self.line_end = None
        self._set_line_end()
        self.paused = False
        self.native_x = 0
        self.native_y = 0

        self.mpos_x = 0
        self.mpos_y = 0
        self.mpos_z = 0

        self.wpos_x = 0
        self.wpos_y = 0
        self.wpos_z = 0

        self.stepper_step_size = UNITS_PER_MIL

        self.plot_planner = PlotPlanner(
            self.settings,
            single=True,
            ppi=False,
            shift=False,
            group=True,
            require_uniform_movement=False,
        )
        self.queue = []
        self._queue_current = 0
        self._queue_total = 0
        self.plot_data = None

        self.on_value = 0
        self.power_dirty = True
        self.speed_dirty = True
        # Zaxis should not be used by default, so we set the dirty flag to False
        self.zaxis_dirty = False
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True
        self.move_mode = 0

        self._absolute = True
        self.feed_mode = None
        self.feed_convert = None
        self._g94_feedrate()  # G94 DEFAULT, mm mode

        self.unit_scale = None
        self.units = None
        self._g21_units_mm()
        self._g90_absolute()

        self.out_pipe = None
        self.out_real = None

        self.reply = None
        self.elements = None
        self.power_scale = 1.0
        self.max_s_value = 1000  # Default GRBL max S value (configurable via $30)
        self.detected_max_s = None  # Auto-detected from firmware settings

        # Firmware-specific power ranges
        self.firmware_power_ranges = {
            "grbl": 1000,       # GRBL default (0-1000, configurable via $30)
            "grblhal": 1000,    # grblHAL default (0-1000, configurable)
            "marlin": 255,      # Marlin typical range (0-255)
            "smoothieware": 1000, # Smoothieware (0-1000)
            "custom": 1000,     # Custom default (user configurable)
        }
        self.speed_scale = 1.0
        self._signal_updates = self.service.setting(bool, "signal_updates", True)

        # Command translation for different firmware types
        # This dictionary maps logical command names to firmware-specific G-code/control strings
        # Includes:
        #   - Basic G-code commands (G0, G1, G20, G21, G28, G90, G91, G92, G94, G93, M3, M4, M5)
        #   - Realtime commands (!, ~, \x18, ?)
        #   - System commands ($H, $X, $J=)
        #   - Query commands ($, $$, $G, $#, $I, $N)
        # Firmware support:
        #   - grbl: Full GRBL 1.1 command set
        #   - grblhal: grblHAL - modern GRBL evolution with extended commands
        #   - marlin: Marlin firmware (mostly compatible, uses M999 for unlock instead of $X)
        #   - smoothieware: Smoothieware firmware (GRBL-compatible in grbl_mode, uses G28 instead of $H)
        #   - fluidnc: FluidNC - ESP32-based GRBL (fully GRBL-compatible, use grbl type)
        #   - custom: User-customizable (defaults to GRBL)
        self.command_translations = {
            "grbl": {
                "laser_on": "M3",
                "laser_off": "M5",
                "laser_mode": "M4",
                "move_rapid": "G0",
                "move_linear": "G1",
                "dwell": "G4",
                "units_mm": "G21",
                "units_inches": "G20",
                "absolute_mode": "G90",
                "relative_mode": "G91",
                "feedrate_mode": "G94",
                "feedrate_inverse": "G93",
                "home": "G28",
                "set_position": "G92",
                # Coolant control
                "coolant_mist_on": "M7",   # Mist coolant ON
                "coolant_flood_on": "M8",  # Flood coolant ON
                "coolant_off": "M9",       # All coolant OFF
                # Realtime commands (single-byte)
                "pause": "!",           # Feed hold
                "resume": "~",          # Cycle start/resume
                "reset": "\x18",        # Soft reset (Ctrl-X)
                "status_query": "?",    # Status report query
                # System commands
                "home_cycle": "$H",     # Run homing cycle
                "unlock": "$X",         # Kill alarm lock
                "jog": "$J=",           # Jogging mode prefix
                # Query commands (for validation/status)
                "query_help": "$",      # View help and check connection
                "query_settings": "$$", # View all settings
                "query_parser": "$G",   # View parser state (modal commands)
                "query_params": "$#",   # View work coordinate parameters
                "query_build": "$I",    # View build info
                "query_startup": "$N",  # View startup blocks
                # Realtime override commands (single-byte, instant response)
                "override_reset": "\x99",        # Reset all overrides to 100%
                "override_feed_inc": "\x9B",     # Increase feed override by 10%
                "override_feed_dec": "\x9A",     # Decrease feed override by 10%
                "override_feed_reset": "\x90",   # Reset feed override to 100%
                "override_rapid_inc": "\x91",    # Increase rapid override by 25%
                "override_rapid_dec": "\x92",    # Decrease rapid override by 25%
                "override_spindle_inc": "\x9C",  # Increase spindle/laser override by 10%
                "override_spindle_dec": "\x9D",  # Decrease spindle/laser override by 10%
            },
            "marlin": {
                "laser_on": "M3",
                "laser_off": "M5",
                "laser_mode": "M4",
                "move_rapid": "G0",
                "move_linear": "G1",
                "dwell": "G4",
                "units_mm": "G21",
                "units_inches": "G20",
                "absolute_mode": "G90",
                "relative_mode": "G91",
                "feedrate_mode": "G94",
                "feedrate_inverse": "G93",
                "home": "G28",
                "set_position": "G92",
                # Coolant control (Marlin supports if enabled)
                "coolant_mist_on": "M7",   # Mist coolant ON (if COOLANT_MIST enabled)
                "coolant_flood_on": "M8",  # Flood coolant / Air Assist ON (if COOLANT_FLOOD or AIR_ASSIST)
                "coolant_off": "M9",       # All coolant / Air Assist OFF
                # Realtime commands (Marlin uses same as GRBL)
                "pause": "!",
                "resume": "~",
                "reset": "\x18",
                "status_query": "?",
                # System commands
                "home_cycle": "G28",    # Marlin uses G28 for homing
                "unlock": "M410",       # Marlin quickstop (closest to alarm clear, not full restart)
                "alarm_clear": "M410",  # Marlin doesn't have direct equivalent to GRBL $X
                "firmware_restart": "M999",  # Full firmware restart (heavy operation)
                "jog": "G0",            # Marlin doesn't have $J, uses G0
                # Query commands (Marlin uses M-codes for queries)
                "query_help": "M115",   # Firmware info (closest to GRBL $)
                "query_settings": "M503", # Print settings (closest to GRBL $$)
                "query_parser": "M115", # Marlin doesn't have exact equivalent
                "query_params": "M114", # Get current position
                "query_build": "M115",  # Build info
                "query_startup": "M115", # No direct equivalent
                # Realtime override commands (Marlin doesn't support these realtime overrides)
                # Provided as no-ops for compatibility
                "override_reset": "",        # Not supported in Marlin
                "override_feed_inc": "",     # Not supported in Marlin
                "override_feed_dec": "",     # Not supported in Marlin
                "override_feed_reset": "",   # Not supported in Marlin
                "override_rapid_inc": "",    # Not supported in Marlin
                "override_rapid_dec": "",    # Not supported in Marlin
                "override_spindle_inc": "",  # Not supported in Marlin (use M220/M221 for different purpose)
                "override_spindle_dec": "",  # Not supported in Marlin
            },
            "grblhal": {
                # grblHAL - Modern GRBL evolution, fully compatible with GRBL 1.1 commands
                # Plus extensive additions (G33, G73, G81-G89, G96/G97, M62-M68, M70-M73, etc.)
                "laser_on": "M3",
                "laser_off": "M5",
                "laser_mode": "M4",
                "move_rapid": "G0",
                "move_linear": "G1",
                "dwell": "G4",
                "units_mm": "G21",
                "units_inches": "G20",
                "absolute_mode": "G90",
                "relative_mode": "G91",
                "feedrate_mode": "G94",
                "feedrate_inverse": "G93",
                "home": "G28",
                "set_position": "G92",
                # Coolant control (full support in grblHAL)
                "coolant_mist_on": "M7",   # Mist coolant ON
                "coolant_flood_on": "M8",  # Flood coolant ON
                "coolant_off": "M9",       # All coolant OFF
                # Realtime commands (same as GRBL)
                "pause": "!",
                "resume": "~",
                "reset": "\x18",
                "status_query": "?",
                # System commands (same as GRBL)
                "home_cycle": "$H",
                "unlock": "$X",
                "alarm_clear": "$X",    # Clear alarm state
                "jog": "$J=",
                # Query commands (same as GRBL)
                "query_help": "$",
                "query_settings": "$$",
                "query_parser": "$G",
                "query_params": "$#",
                "query_build": "$I",
                "query_startup": "$N",
                # Realtime override commands (same as GRBL)
                "override_reset": "\x99",        # Reset all overrides to 100%
                "override_feed_inc": "\x9B",     # Increase feed override by 10%
                "override_feed_dec": "\x9A",     # Decrease feed override by 10%
                "override_feed_reset": "\x90",   # Reset feed override to 100%
                "override_rapid_inc": "\x91",    # Increase rapid override by 25%
                "override_rapid_dec": "\x92",    # Decrease rapid override by 25%
                "override_spindle_inc": "\x9C",  # Increase spindle/laser override by 10%
                "override_spindle_dec": "\x9D",  # Decrease spindle/laser override by 10%
            },
            "smoothieware": {
                "laser_on": "M3",
                "laser_off": "M5",
                "laser_mode": "M4",
                "move_rapid": "G0",
                "move_linear": "G1",
                "dwell": "G4",
                "units_mm": "G21",
                "units_inches": "G20",
                "absolute_mode": "G90",
                "relative_mode": "G91",
                "feedrate_mode": "G94",
                "feedrate_inverse": "G93",
                "home": "G28",
                "set_position": "G92",
                # Coolant control
                "coolant_mist_on": "M7",   # Mist coolant ON
                "coolant_flood_on": "M8",  # Flood coolant ON
                "coolant_off": "M9",       # All coolant OFF
                # Realtime commands (Smoothie compatible with GRBL)
                "pause": "!",
                "resume": "~",
                "reset": "\x18",        # Ctrl-X for reset
                "status_query": "?",    # Status query in GRBL mode
                # System commands
                "home_cycle": "G28",    # Smoothie uses G28 for homing
                "unlock": "$X",         # Compatible with GRBL alarm clear
                "alarm_clear": "$X",    # Clear alarm state in GRBL mode
                "jog": "G0",            # Smoothie doesn't have $J, uses G0
                # Query commands (Smoothie in GRBL mode supports these)
                "query_help": "$",      # Help in GRBL mode
                "query_settings": "$$", # Settings in GRBL mode
                "query_parser": "$G",   # Parser state in GRBL mode
                "query_params": "$#",   # Work coordinates in GRBL mode
                "query_build": "$I",    # Build info in GRBL mode
                "query_startup": "$N",  # Startup blocks in GRBL mode
                # Realtime override commands (compatible with GRBL in grbl_mode)
                "override_reset": "\x99",        # Reset all overrides to 100%
                "override_feed_inc": "\x9B",     # Increase feed override by 10%
                "override_feed_dec": "\x9A",     # Decrease feed override by 10%
                "override_feed_reset": "\x90",   # Reset feed override to 100%
                "override_rapid_inc": "\x91",    # Increase rapid override by 25%
                "override_rapid_dec": "\x92",    # Decrease rapid override by 25%
                "override_spindle_inc": "\x9C",  # Increase spindle/laser override by 10%
                "override_spindle_dec": "\x9D",  # Decrease spindle/laser override by 10%
            },
            "custom": {
                # Default to GRBL commands, can be customized
                "laser_on": "M3",
                "laser_off": "M5",
                "laser_mode": "M4",
                "move_rapid": "G0",
                "move_linear": "G1",
                "dwell": "G4",
                "units_mm": "G21",
                "units_inches": "G20",
                "absolute_mode": "G90",
                "relative_mode": "G91",
                "feedrate_mode": "G94",
                "feedrate_inverse": "G93",
                "home": "G28",
                "set_position": "G92",
                # Coolant control
                "coolant_mist_on": "M7",   # Mist coolant ON
                "coolant_flood_on": "M8",  # Flood coolant ON
                "coolant_off": "M9",       # All coolant OFF
                # Realtime commands
                "pause": "!",
                "resume": "~",
                "reset": "\x18",
                "status_query": "?",
                # System commands
                "home_cycle": "$H",
                "unlock": "$X",
                "alarm_clear": "$X",    # Clear alarm state
                "jog": "$J=",
                # Query commands
                "query_help": "$",
                "query_settings": "$$",
                "query_parser": "$G",
                "query_params": "$#",
                "query_build": "$I",
                "query_startup": "$N",
                # Realtime override commands (default to GRBL)
                "override_reset": "\x99",        # Reset all overrides to 100%
                "override_feed_inc": "\x9B",     # Increase feed override by 10%
                "override_feed_dec": "\x9A",     # Decrease feed override by 10%
                "override_feed_reset": "\x90",   # Reset feed override to 100%
                "override_rapid_inc": "\x91",    # Increase rapid override by 25%
                "override_rapid_dec": "\x92",    # Decrease rapid override by 25%
                "override_spindle_inc": "\x9C",  # Increase spindle/laser override by 10%
                "override_spindle_dec": "\x9D",  # Decrease spindle/laser override by 10%
            }
        }

    def translate_command(self, command_key):
        """
        Translate a command key to the appropriate firmware-specific command.

        For "custom" firmware type, loads command values from settings with GRBL defaults as fallback.
        This allows users to override individual commands via settings like:
        - custom_command_laser_on = "M3"
        - custom_command_home_cycle = "$H"
        etc.

        @param command_key: The key for the command (e.g., 'laser_on', 'move_linear')
        @return: The translated command string
        """
        firmware_type = self.service.setting(str, "firmware_type", "grbl")
        
        if firmware_type == "custom":
            # For custom firmware, load from settings with GRBL defaults as fallback
            grbl_default = self.command_translations["grbl"].get(command_key, command_key)
            setting_key = f"custom_command_{command_key}"
            return self.service.setting(str, setting_key, grbl_default)
        else:
            # For predefined firmware types, use the translation table
            translations = self.command_translations.get(firmware_type, self.command_translations["grbl"])
            return translations.get(command_key, command_key)  # Return key if not found
    
    def jog_command(self, gcode_params):
        """
        Generate a jog command appropriate for the firmware type.
        
        For GRBL: Uses $J=G91G21X10F1000 format
        For Marlin/Smoothieware: Uses G0 G91 G21 X10 F1000 format
        
        @param gcode_params: G-code parameters (e.g., "G91G21X10F1000")
        @return: Formatted jog command string
        """
        firmware_type = self.service.setting(str, "firmware_type", "grbl")
        jog_prefix = self.translate_command("jog")
        
        if jog_prefix == "$J=":
            # GRBL style - keep format compact
            return f"$J={gcode_params}"
        else:
            # Marlin/Smoothieware style - add spaces for compatibility
            # Convert "G91G21X10F1000" to "G91 G21 X10 F1000"
            import re
            # Add spaces before G, M, X, Y, Z, F letters
            formatted = re.sub(r'([GMXYZF])', r' \1', gcode_params).strip()
            return formatted

    def __repr__(self):
        return f"GRBLDriver({self.name})"

    def _format_number(self, value):
        """
        Format a number for G-code output, removing unnecessary trailing zeros.
        
        Examples:
            1000.0 -> "1000" (removes .0 for whole numbers)
            0.0 -> "0"
            127.5 -> "127.5"
            123.456 -> "123.456"
        """
        # Format with 6 decimal places then strip trailing zeros
        formatted = f"{value:.6f}".rstrip('0').rstrip('.')
        return formatted

    def __call__(self, e, real=False):
        if real:
            self.out_real(e)
        else:
            self.out_pipe(e)

    def get_internal_queue_status(self):
        return self._queue_current, self._queue_total

    def _set_queue_status(self, current, total):
        self._queue_current = current
        self._queue_total = total

    @signal_listener("line_end")
    def _set_line_end(self, origin=None, *args):
        line_end = self.service.setting(str, "line_end", "CR")
        line_end = line_end.replace(" ", "")
        line_end = line_end.replace("CR", "\r")
        line_end = line_end.replace("LF", "\n")
        self.line_end = line_end

    def hold_work(self, priority):
        """
        Required.

        Spooler check. to see if the work cycle should be held.

        @return: hold?
        """
        if priority > 0:
            # Don't hold realtime work.
            return False
        if (
            self.service.limit_buffer
            and len(self.service.controller) > self.service.max_buffer
        ):
            return True
        return self.paused

    def get(self, key, default=None):
        """
        Required.

        @param key: Key to get.
        @param default: Default value to use.
        @return:
        """
        return self.settings.get(key, default=default)

    def set(self, key, value):
        """
        Required.

        Sets a laser parameter this could be speed, power, wobble, number_of_unicorns, or any unknown parameters for
        yet to be written drivers.

        @param key:
        @param value:
        @return:
        """
        if key == "power":
            self.power_dirty = True
        if key == "speed":
            self.speed_dirty = True
        self.settings[key] = value

    def status(self):
        """
        Wants a status report of what the driver is doing.
        @return:
        """
        # TODO: To calculate status correctly we need to actually have access to the response
        self.out_real("?")
        return (self.native_x, self.native_y), "idle", "unknown"

    def move_abs(self, x, y):
        """
        Requests laser move to absolute position x, y in physical units

        @param x:
        @param y:
        @return:
        """
        self._g90_absolute()
        self._clean()
        old_current = self.service.current
        x, y = self.service.view.position(x, y)
        self._move(x, y)
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def move_rel(self, dx, dy, confined=False):
        """
        Requests laser move relative position dx, dy in physical units

        @param dx:
        @param dy:
        @return:
        """
        # self._g90_absolute()
        # self._clean()
        # old_current = self.service.current
        # x, y = old_current
        # x += dx
        # y += dy
        # x, y = self.service.view.position(x, y)
        # self._move(x, y)
        if confined:
            new_x = self.native_x * self.service.view.native_scale_x + dx
            new_y = self.native_y * self.service.view.native_scale_y + dy
            if new_x < 0:
                dx = -self.native_x * self.service.view.native_scale_x
            elif new_x > self.service.view.width:
                dx = (
                    self.service.view.width
                    - self.native_x * self.service.view.native_scale_x
                )
            if new_y < 0:
                dy = -self.native_y * self.service.view.native_scale_y
            elif new_y > self.service.view.height:
                dy = (
                    self.service.view.height
                    - self.native_y * self.service.view.native_scale_y
                )
        self._g91_relative()
        self._clean()
        old_current = self.service.current

        unit_dx, unit_dy = self.service.view.position(dx, dy, vector=True)
        self._move(unit_dx, unit_dy)

        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def dwell(self, time_in_ms, settings=None):
        """
        Requests that the laser fire in place for the given time period. This could be done in a series of commands,
        move to a location, turn laser on, wait, turn laser off. However, some drivers have specific laser-in-place
        commands so calling dwell is preferred.

        @param time_in_ms:
        @return:
        """
        if settings is not None and "power" in settings:
            power = settings["power"]
        else:
            power = self.power
        self.laser_on(
            power=power
        )  # This can't be sent early since these are timed operations.
        self.wait(time_in_ms)
        self.laser_off()

    def scale_power_to_firmware(self, power):
        """
        Scale power value (0-1000 internal) to firmware-specific S parameter range.
        
        GRBL uses 0-1000 (or 0 to $30 setting)
        Marlin typically uses 0-255
        
        @param power: Internal power value (0-1000 range)
        @return: Scaled power for firmware S parameter
        """
        firmware_type = self.service.settings.get("firmware_type", "grbl")
        
        # Use detected max from $30 setting if available
        if self.detected_max_s is not None:
            target_max = self.detected_max_s
        else:
            target_max = self.firmware_power_ranges.get(firmware_type, 1000)
        
        # If target is different from our internal range, scale it
        if target_max != 1000:
            scaled = (power / 1000.0) * target_max
            return scaled
        
        return power

    def update_max_s_from_settings(self, settings_dict):
        """
        Update max S value from firmware settings.
        For GRBL, this is $30 (maximum spindle speed).
        
        @param settings_dict: Dictionary of firmware settings
        """
        if 30 in settings_dict:
            # GRBL $30 = maximum spindle speed (also max S value)
            try:
                self.detected_max_s = float(settings_dict[30])
                self.service.signal("grbl:max_s", self.detected_max_s)
            except (ValueError, TypeError):
                pass

    def laser_off(self, power=0, *values):
        """
        Turn laser off in place.

        @param power: Power after laser turn off (0=default).
        @param values:
        @return:
        """
        if power is not None:
            scaled_power = self.scale_power_to_firmware(power)
            spower = f" S{self._format_number(scaled_power)}"
            self.power = power
            self.power_dirty = False
            self(f"{self.translate_command('move_linear')} {spower}{self.line_end}")
        self(f"{self.translate_command('laser_off')}{self.line_end}")

    def laser_on(self, power=None, speed=None, *values):
        """
        Turn laser on in place. This is done specifically with an M3 command so that the laser is on while stationary

        @param speed: Speed for laser turn on.
        @param power: Power at the laser turn on.
        @param values:
        @return:
        """
        spower = ""
        sspeed = ""
        if power is not None:
            scaled_power = self.scale_power_to_firmware(power)
            spower = f" S{self._format_number(scaled_power)}"
            # We already established power, so no need for power_dirty
            self.power = power
            self.power_dirty = False
        if speed is not None:
            sspeed = f"{self.translate_command('move_linear')} F{speed}{self.line_end}"
            self.speed = speed
            self.speed_dirty = False
        self(f"{self.translate_command('laser_on')}{spower}{self.line_end}{sspeed}")

    def geometry(self, geom):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        # TODO: estop cannot clear the geom.
        self.signal("grbl_red_dot", False)  # We are not using red-dot if we're cutting.
        self.clear_states()
        self._g90_absolute()
        self._g94_feedrate()
        self._clean()
        # Use M4 dynamic power if supported and not explicitly disabled
        laser_cmd = self.get_laser_command(use_constant_power=self.service.use_m3)
        self(f"{self.translate_command(laser_cmd)}{self.line_end}")
        first = True
        g = Geomstr()
        for segment_type, start, c1, c2, end, sets in geom.as_lines():
            while self.hold_work(0):
                if self.service.kernel.is_shutdown:
                    return
                time.sleep(0.05)
            x = self.native_x
            y = self.native_y
            start_x, start_y = start.real, start.imag
            if x != start_x or y != start_y or first:
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                first = False
                self._move(start_x, start_y)
            if self.on_value != 1.0:
                self.power_dirty = True
            self.on_value = 1.0
            # Default-Values?!
            qpower = sets.get("power", self.power)
            qspeed = sets.get("speed", self.speed)
            qraster_step_x = sets.get("raster_step_x")
            qraster_step_y = sets.get("raster_step_y")
            if qpower != self.power:
                self.set("power", qpower)
            if (
                qspeed != self.speed
                or qraster_step_x != self.raster_step_x
                or qraster_step_y != self.raster_step_y
            ):
                self.set("speed", qspeed)
            self.settings.update(sets)
            if segment_type == "line":
                self.move_mode = 1
                self._move(end.real, end.imag)
            elif segment_type == "end":
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                first = False
            elif segment_type == "quad":
                self.move_mode = 1
                interp = self.service.interp
                g.clear()
                g.quad(complex(start), complex(c1), complex(end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif segment_type == "cubic":
                self.move_mode = 1
                interp = self.service.interp
                g.clear()
                g.cubic(
                    complex(start),
                    complex(c1),
                    complex(c2),
                    complex(end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif segment_type == "arc":
                # TODO: Allow arcs to be directly executed by GRBL which can actually use them.
                self.move_mode = 1
                interp = self.service.interp
                g.clear()
                g.arc(
                    complex(start),
                    complex(c1),
                    complex(end),
                )
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif segment_type == "point":
                function = sets.get("function")
                if function == "dwell":
                    self.dwell(sets.get("dwell_time"))
                elif function == "wait":
                    self.wait(sets.get("dwell_time"))
                elif function == "home":
                    self.home()
                elif function == "goto":
                    self._move(start.real, start.imag)
                elif function == "input":
                    # GRBL has no core GPIO functionality
                    pass
                elif function == "output":
                    # GRBL has no core GPIO functionality
                    pass
        self(f"{self.translate_command('move_linear')} S0{self.line_end}")
        self(f"{self.translate_command('laser_off')}{self.line_end}")
        self.clear_states()
        self.wait_finish()
        return False

    def plot(self, plot):
        """
        Gives the driver a bit of cutcode that should be plotted.
        @param plot:
        @return:
        """
        self.queue.append(plot)

    def plot_start(self):
        """
        Called at the end of plot commands to ensure the driver can deal with them all as a group.

        @return:
        """
        self.signal("grbl_red_dot", False)  # We are not using red-dot if we're cutting.
        self.clear_states()
        self._g90_absolute()
        self._g94_feedrate()
        self._clean()
        if self.service.use_m3:
            self(f"{self.translate_command('laser_on')}{self.line_end}")
        else:
            self(f"{self.translate_command('laser_mode')}{self.line_end}")
        first = True
        total = len(self.queue)
        current = 0
        for q in self.queue:
            # Are there any custom commands to be executed?
            # Usecase (as described in issue https://github.com/meerk40t/meerk40t/issues/2764 ):
            # Switch between M3 and M4 mode for cut / raster
            #   M3=used to cut as gantry acceleration doesn't matter on a cut.
            #   M4=used for Raster/Engrave operations, as grblHAL will
            #   adjust power based on gantry speed including acceleration.

            cmd_string = q.settings.get("custom_commands", "")
            if cmd_string:
                for cmd in cmd_string.splitlines():
                    self(f"{cmd}{self.line_end}")

            current += 1
            self._set_queue_status(current, total)
            while self.hold_work(0):
                if self.service.kernel.is_shutdown:
                    return
                time.sleep(0.05)
            x = self.native_x
            y = self.native_y
            start_x, start_y = q.start
            if x != start_x or y != start_y or first:
                self.on_value = 0
                self.power_dirty = True
                self.move_mode = 0
                first = False
                self._move(start_x, start_y)
            if self.on_value != 1.0:
                self.power_dirty = True
            self.on_value = 1.0
            # Do we have a custom z-Value?
            # NB: zaxis is not a property inside Parameters like power/or speed
            # so we need to deal with it more directly
            # (e.g. self.power is the equivalent to self.settings.["power"]))
            qzaxis = q.settings.get("zaxis", self.zaxis)
            if qzaxis != self.zaxis:
                self.zaxis = qzaxis
                self.zaxis_dirty = True
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
                self.move_mode = 1
                self._move(*q.end)
            elif isinstance(q, QuadCut):
                self.move_mode = 1
                interp = self.service.interp
                g = Geomstr()
                g.quad(complex(*q.start), complex(*q.c()), complex(*q.end))
                for p in list(g.as_equal_interpolated_points(distance=interp))[1:]:
                    while self.paused:
                        time.sleep(0.05)
                    self._move(p.real, p.imag)
            elif isinstance(q, CubicCut):
                self.move_mode = 1
                interp = self.service.interp
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
                    self._move(p.real, p.imag)
            elif isinstance(q, WaitCut):
                self.wait(q.dwell_time)
            elif isinstance(q, HomeCut):
                self.home()
            elif isinstance(q, GotoCut):
                start = q.start
                self._move(start[0], start[1])
            elif isinstance(q, DwellCut):
                self.dwell(q.dwell_time)
            elif isinstance(q, (InputCut, OutputCut)):
                # GRBL has no core GPIO functionality
                pass
            elif isinstance(q, PlotCut):
                self.move_mode = 1
                self.set("power", 1000)
                for ox, oy, on, x, y in q.plot:
                    while self.hold_work(0):
                        time.sleep(0.05)
                    # q.plot can have different on values, these are parsed
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    if on == 0:
                        self.move_mode = 0
                    else:
                        self.move_mode = 1
                    self._move(x, y)
            else:
                #  Rastercut
                self.plot_planner.push(q)
                self.move_mode = 1
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
                            # self.move_mode = 0
                            self.rapid_mode()
                            self._move(x, y)
                        continue
                    # if on == 0:
                    #     self.move_mode = 0
                    # else:
                    #     self.move_mode = 1
                    if self.on_value != on:
                        self.power_dirty = True
                    self.on_value = on
                    if on == 0:
                        self.move_mode = 0
                    else:
                        self.move_mode = 1
                    self._move(x, y)
        self.queue.clear()
        self._set_queue_status(0, 0)

        self(f"{self.translate_command('move_linear')} S0{self.line_end}")
        self(f"{self.translate_command('laser_off')}{self.line_end}")
        self.clear_states()
        self.wait_finish()
        return False

    def blob(self, data_type, data):
        """
        This is intended to send a blob of gcode to be processed and executed.

        @param data_type:
        @param data:
        @return:
        """
        if data_type != "grbl":
            return
        grbl = bytes.decode(data, "latin-1")
        for split in grbl.split("\r"):
            g = split.strip()
            if g:
                self(f"{g}{self.line_end}")

    def physical_home(self):
        """
        Home the laser physically (i.e. run into endstops).

        @return:
        """
        old_current = self.service.current
        self.native_x = 0
        self.native_y = 0
        if self.service.has_endstops:
            self(f"{self.translate_command('home_cycle')}{self.line_end}")
        else:
            self(f"{self.translate_command('home')}{self.line_end}")
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def home(self):
        """
        Home the laser (i.e. goto defined origin)

        @return:
        """
        self.native_x = 0
        self.native_y = 0
        if self.service.rotary.active and self.service.rotary.suppress_home:
            return
        self(f"{self.translate_command('home')}{self.line_end}")
        
        # For Marlin, G28 may not result in position (0,0)
        # Set work coordinate to 0,0 explicitly
        firmware_type = self.service.settings.get("firmware_type", "grbl")
        if firmware_type == "marlin":
            # After G28, explicitly set current position as work zero
            self(f"{self.translate_command('set_position')} X0 Y0{self.line_end}")

    def rapid_mode(self, *values):
        """
        Rapid mode sets the laser to rapid state. This is usually moving the laser around without it executing a large
        batch of commands.

        @param values:
        @return:
        """
        speedvalue = self.service.setting(float, "rapid_speed", 600.0)
        if self.speed != speedvalue:
            self.speed = speedvalue
            self.speed_dirty = True

    def finished_mode(self, *values):
        """
        Finished mode is after a large batch of jobs is done.

        @param values:
        @return:
        """
        self(f"{self.translate_command('laser_off')}{self.line_end}")

    def program_mode(self, *values):
        """
        Program mode is the state lasers often use to send a large batch of commands.
        @param values:
        @return:
        """
        self(f"{self.translate_command('laser_on')}{self.line_end}")

    def raster_mode(self, *values):
        """
        Raster mode is a special form of program mode that suggests the batch of commands will be a raster operation
        many lasers have specialty values
        @param values:
        @return:
        """

    def wait(self, time_in_ms):
        """
        Wait asks that the work be stalled or current process held for the time time_in_ms in ms. If wait_finished is
        called first this will attempt to stall the machine while performing no work. If the driver in question permits
        waits to be placed within code this should insert waits into the current job. Returning instantly rather than
        holding the processes.

        @param time_in_ms:
        @return:
        """
        self(f"{self.translate_command('dwell')} S{time_in_ms / 1000.0}{self.line_end}")

    def wait_finish(self, *values):
        """
        Wait finish should hold the calling thread until the current work has completed. Or otherwise prevent any data
        from being sent with returning True for the until that criteria is met.

        @param values:
        @return:
        """
        while True:
            if self.queue or len(self.service.controller):
                time.sleep(0.05)
                continue
            break

    def function(self, function):
        """
        This command asks that this function be executed at the appropriate time within the spooled cycle.

        @param function:
        @return:
        """
        function()

    def beep(self):
        """
        Wants a system beep to be issued.
        This command asks that a beep be executed at the appropriate time within the spooled cycle.

        @return:
        """
        self.service("beep\n")

    def console(self, value):
        """
        This asks that the console command be executed at the appropriate time within the spooled cycle.

        @param value: console command
        @return:
        """
        self.service(value)

    def signal(self, signal, *args):
        """
        This asks that this signal be broadcast at the appropriate time within the spooling cycle.

        @param signal:
        @param args:
        @return:
        """
        if signal == "coolant":
            onoff = args[0]
            coolid = None
            if hasattr(self.service, "coolant"):
                coolid = self.service.device_coolant
            if not coolid:
                return
            routine = None
            try:
                cool = self.service.context.kernel.root.coolant
                routine = cool.claim_coolant(self.service, coolid)
            except AttributeError:
                routine = None
            if routine:
                try:
                    routine(self.service, onoff)
                except RuntimeError:
                    pass

        else:
            self.service.signal(signal, *args)

    def pause(self, *args):
        """
        Asks that the laser be paused.

        @param args:
        @return:
        """
        self.paused = True
        # self(f"!{self.line_end}", real=True)
        self(self.translate_command('pause'), real=True)
        # Let's make sure we reestablish power...
        self.power_dirty = True
        self.service.signal("pause")

    def resume(self, *args):
        """
        Asks that the laser be resumed.

        To work this command should usually be put into the realtime work queue for the laser.

        @param args:
        @return:
        """
        self.paused = False
        # self(f"~{self.line_end}", real=True)
        self(self.translate_command('resume'), real=True)
        self.service.signal("pause")

    def clear_states(self):
        self.power_dirty = True
        self.speed_dirty = True
        self.zaxis_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True
        self.move_mode = 0

    def reset(self, *args):
        """
        This command asks that this device be emergency stopped and reset. Usually that queue data from the spooler be
        deleted.
        Asks that the device resets, and clears all current work.

        @param args:
        @return:
        """
        self.service.spooler.clear_queue()
        self.queue.clear()
        self.plot_planner.clear()
        self(f"{self.translate_command('reset')}{self.line_end}", real=True)
        self._g94_feedrate()
        self._g21_units_mm()
        self._g90_absolute()

        self.power_dirty = True
        self.speed_dirty = True
        self.zaxis_dirty = True
        self.absolute_dirty = True
        self.feedrate_dirty = True
        self.units_dirty = True

        self.paused = False
        self.service.signal("pause")

    def clear_alarm(self):
        """
        GRBL clear alarm signal.

        @return:
        """
        self(f"{self.translate_command('unlock')}{self.line_end}", real=True)
        if self.service.extended_alarm_clear:
            self.reset()

    def declare_modals(self, modals):
        self.move_mode = 0 if "G0" in modals else 1
        if "G90" in modals:
            self._g90_absolute()
            self.absolute_dirty = False
        if "G91" in modals:
            self._g91_relative()
            self.absolute_dirty = False
        if "G94" in modals:
            self._g94_feedrate()
            self.feedrate_dirty = False
        if "G93" in modals:
            self._g93_feedrate()
            self.feedrate_dirty = False
        if "G20" in modals:
            self._g20_units_inch()
            self.units_dirty = False
        if "G21" in modals:
            self._g21_units_mm()
            self.units_dirty = False

    def declare_position(self, x, y):
        self.native_x = x * self.unit_scale
        self.native_y = y * self.unit_scale

    ####################
    # PROTECTED DRIVER CODE
    ####################

    def _move(self, x, y, absolute=False):
        old_current = self.service.current
        if self._absolute:
            self.native_x = x
            self.native_y = y
        else:
            self.native_x += x
            self.native_y += y
        line = []
        if self.move_mode == 0:
            if self.power_dirty and self.service.use_g1_for_power:
                if self.power is not None:
                    # Turn off laser before rapid move if power is changing
                    scaled_power = self.scale_power_to_firmware(self.power * self.on_value)
                    line.append(f"{self.translate_command('move_linear')} S{self._format_number(scaled_power)}")
                self.power_dirty = False
            line.append(self.translate_command("move_rapid"))
        else:
            line.append(self.translate_command("move_linear"))
        x /= self.unit_scale
        y /= self.unit_scale
        line.append(f"X{x:.3f}")
        line.append(f"Y{y:.3f}")
        if self.zaxis_dirty:
            self.zaxis_dirty = False
            if self.zaxis is not None:
                try:
                    z = float(Length(self.zaxis) / self.service.view.native_scale_x)
                    z /= self.unit_scale
                    line.append(f"Z{z:.3f}")
                except ValueError:
                    pass

        if self.power_dirty:
            if self.power is not None:
                scaled_power = self.scale_power_to_firmware(self.power * self.on_value)
                line.append(f"S{self._format_number(scaled_power)}")
            self.power_dirty = False
        if self.speed_dirty:
            line.append(f"F{self._format_number(self.feed_convert(self.speed))}")
            self.speed_dirty = False
        self(" ".join(line) + self.line_end)
        new_current = self.service.current
        if self._signal_updates:
            self.service.signal(
                "driver;position",
                (old_current[0], old_current[1], new_current[0], new_current[1]),
            )

    def _clean_motion(self):
        if self.absolute_dirty:
            if self._absolute:
                self(f"{self.translate_command('absolute_mode')}{self.line_end}")
            else:
                self(f"{self.translate_command('relative_mode')}{self.line_end}")
        self.absolute_dirty = False

    def _clean_feed_mode(self):
        if self.feedrate_dirty:
            if self.feed_mode == 94:
                self(f"{self.translate_command('feedrate_mode')}{self.line_end}")
            else:
                self(f"{self.translate_command('feedrate_inverse')}{self.line_end}")
        self.feedrate_dirty = False

    def _clean_units(self):
        if self.units_dirty:
            if self.units == 20:
                self(f"{self.translate_command('units_inches')}{self.line_end}")
            else:
                self(f"{self.translate_command('units_mm')}{self.line_end}")
        self.units_dirty = False

    def _clean(self):
        self._clean_motion()
        self._clean_feed_mode()
        self._clean_units()

    def _g91_relative(self):
        if not self._absolute:
            return
        self._absolute = False
        self.absolute_dirty = True

    def _g90_absolute(self):
        if self._absolute:
            return
        self._absolute = True
        self.absolute_dirty = True

    def _g93_mms_to_minutes_per_gunits(self, mms):
        millimeters_per_minute = 60.0 * mms
        distance = UNITS_PER_MIL / self.stepper_step_size
        return distance / millimeters_per_minute

    def _g93_feedrate(self):
        if self.feed_mode == 93:
            return
        self.feed_mode = 93
        # Feed Rate in Minutes / Unit
        self.feed_convert = self._g93_mms_to_minutes_per_gunits
        self.feedrate_dirty = True

    def _g94_mms_to_gunits_per_minute(self, mms):
        millimeters_per_minute = 60.0 * mms
        distance = UNITS_PER_MIL / self.stepper_step_size
        return millimeters_per_minute / distance

    def _g94_feedrate(self):
        if self.feed_mode == 94:
            return
        self.feed_mode = 94
        # Feed Rate in Units / Minute
        self.feed_convert = self._g94_mms_to_gunits_per_minute
        # units to mm, seconds to minutes.
        self.feedrate_dirty = True

    def _g20_units_inch(self):
        self.units = 20
        self.unit_scale = UNITS_PER_INCH / self.stepper_step_size  # g20 is inch mode.
        self.units_dirty = True

    def _g21_units_mm(self):
        self.units = 21
        self.unit_scale = UNITS_PER_MM / self.stepper_step_size  # g21 is mm mode.
        self.units_dirty = True

    def set_power_scale(self, factor):
        # Grbl can only deal with factors between 10% and 200%
        if factor <= 0 or factor > 2.0:
            factor = 1.0
        if self.power_scale == factor:
            return
        self.power_scale = factor

        # Grbl can only deal with factors between 10% and 200%
        self(f"{self.translate_command('override_reset')}\r", real=True)
        # Upward loop
        start = 1.0
        while start < 2.0 and start < factor:
            self(f"{self.translate_command('override_feed_inc')}\r", real=True)
            start += 0.1
        # Downward loop
        start = 1.0
        while start > 0.0 and start > factor:
            self(f"{self.translate_command('override_feed_dec')}\r", real=True)
            start -= 0.1

    def set_speed_scale(self, factor):
        # Grbl can only deal with factors between 10% and 200%
        if factor <= 0 or factor > 2.0:
            factor = 1.0
        if self.speed_scale == factor:
            return
        self.speed_scale = factor
        self(f"{self.translate_command('override_feed_reset')}\r", real=True)
        start = 1.0
        while start < 2.0 and start < factor:
            self(f"{self.translate_command('override_rapid_inc')}\r", real=True)
            start += 0.1
        # Downward loop
        start = 1.0
        while start > 0.0 and start > factor:
            self(f"{self.translate_command('override_rapid_dec')}\r", real=True)
            start -= 0.1

    @property
    def has_adjustable_power(self):
        """
        Check if the firmware supports realtime power/spindle override.
        
        Returns True for GRBL, grblHAL, and Smoothieware (with grbl_mode).
        Returns False for Marlin (no realtime override support).
        """
        firmware_type = self.service.settings.get("firmware_type", "grbl")
        # Only GRBL, grblHAL, and Smoothieware support realtime overrides
        return firmware_type in ("grbl", "grblhal", "smoothieware", "custom")

    @property
    def has_adjustable_speed(self):
        """
        Check if the firmware supports realtime feed/speed override.
        
        Returns True for GRBL, grblHAL, and Smoothieware (with grbl_mode).
        Returns False for Marlin (no realtime override support).
        """
        firmware_type = self.service.settings.get("firmware_type", "grbl")
        # Only GRBL, grblHAL, and Smoothieware support realtime overrides
        return firmware_type in ("grbl", "grblhal", "smoothieware", "custom")

    @property
    def supports_m4_dynamic_power(self):
        """
        Check if the firmware supports M4 dynamic power mode.
        
        M4 scales laser power based on actual speed vs programmed speed.
        This ensures consistent laser energy per distance.
        
        Returns True for GRBL, grblHAL, and Smoothieware.
        Returns False for Marlin (M4 support varies, generally not reliable).
        """
        firmware_type = self.service.settings.get("firmware_type", "grbl")
        # GRBL, grblHAL, and Smoothieware support M4 dynamic power
        # Marlin support is inconsistent and version-dependent
        return firmware_type in ("grbl", "grblhal", "smoothieware", "custom")

    def get_laser_command(self, use_constant_power=None):
        """
        Get the appropriate laser on command based on power mode preference.
        
        @param use_constant_power: If True, use M3 (constant power).
                                   If False and supported, use M4 (dynamic power).
                                   If None, use service setting.
        @return: Command key for laser on ("laser_on" for M3, "laser_mode" for M4)
        """
        if use_constant_power is None:
            use_constant_power = self.service.use_m3
        
        # If constant power requested or M4 not supported, use M3
        if use_constant_power or not self.supports_m4_dynamic_power:
            return "laser_on"  # M3
        
        return "laser_mode"  # M4

    @property
    def execution_direct_list(self):
        """
        A list of commands the driver wants to deal with it directly.
        """
        return ("grbl", "gcode")

    def execute_direct(self, line):
        self(f"{line}{self.line_end}")
