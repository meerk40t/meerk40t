"""
GRBL Controller

Tasked with sending data to the different connection.

Validation Stages:
        Stage 0 (VALIDATION_STAGE_DISCONNECTED): Disconnected and invalid
        Stage 1 (VALIDATION_STAGE_HELP_REQUEST): Connected, need to check if GRBL with $
        Stage 2 (VALIDATION_STAGE_SETTINGS_QUERY): Parsed $, need to try $$ and $G
        Stage 3 (VALIDATION_STAGE_SETTINGS_PARSED): Successfully parsed $$
        Stage 4 (VALIDATION_STAGE_MODAL_QUERY): Successfully parsed $G, send ?
        Stage 5 (VALIDATION_STAGE_VALIDATED): Successfully parsed ?, fully validated
"""
import ast
import re
import threading
import time

from meerk40t.kernel import signal_listener

# GRBL Validation Stage Constants
VALIDATION_STAGE_DISCONNECTED = 0  # Disconnected and invalid
VALIDATION_STAGE_HELP_REQUEST = 1  # Connected, need to check if GRBL with $
VALIDATION_STAGE_SETTINGS_QUERY = 2  # Parsed $, need to try $$ and $G
VALIDATION_STAGE_SETTINGS_PARSED = 3  # Successfully parsed $$
VALIDATION_STAGE_MODAL_QUERY = 4  # Successfully parsed $G, send ?
VALIDATION_STAGE_VALIDATED = 5  # Successfully parsed ?, fully validated

SETTINGS_MESSAGE = re.compile(r"^\$([0-9]+)=(.*)")

# GRBL Hardware Settings Database
# Format: code -> (default_value, description, units, type, documentation_url, variants)
# variants is a list of GRBL variants that support this setting:
# ['grbl'] = Standard GRBL only
# ['grbl', 'grblhal'] = Standard GRBL and GrblHAL
# ['grblhal'] = GrblHAL only
# ['fluidnc'] = FluidNC only
# ['grbl_esp32'] = GRBL-ESP32 only
# ['all'] = All variants (universal)
GRBL_HARDWARE_SETTINGS = {
    # Standard GRBL settings - supported by all variants
    0: (
        10,
        "step pulse time",
        "microseconds",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#0--step-pulse-microseconds",
        ["all"],
    ),
    1: (
        25,
        "step idle delay",
        "milliseconds",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#1---step-idle-delay-milliseconds",
        ["all"],
    ),
    # Step port invert settings
    2: (
        0,
        "step pulse invert",
        "bitmask",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#2--step-port-invert-mask",
        ["all"],
    ),
    3: (
        0,
        "step direction invert",
        "bitmask",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#3--direction-port-invert-mask",
        ["all"],
    ),
    4: (
        0,
        "invert step enable pin",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#4---step-enable-invert-boolean",
        ["all"],
    ),
    5: (
        0,
        "invert limit pins",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#5----limit-pins-invert-boolean",
        ["all"],
    ),
    6: (
        0,
        "invert probe pin",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#6----probe-pin-invert-boolean",
        ["all"],
    ),
    # Status report settings
    10: (
        255,
        "status report options",
        "bitmask",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#10---status-report-mask",
        ["all"],
    ),
    11: (
        0.010,
        "Junction deviation",
        "mm",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#11---junction-deviation-mm",
        ["all"],
    ),
    12: (
        0.002,
        "arc tolerance",
        "mm",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#12--arc-tolerance-mm",
        ["all"],
    ),
    13: (
        0,
        "Report in inches",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#13---report-inches-boolean",
        ["all"],
    ),
    # Limit and homing settings
    20: (
        0,
        "Soft limits enabled",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#20---soft-limits-boolean",
        ["all"],
    ),
    21: (
        0,
        "hard limits enabled",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#21---hard-limits-boolean",
        ["grbl", "grblhal"],
    ),  # FluidNC uses YAML config
    22: (
        0,
        "Homing cycle enable",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#22---homing-cycle-boolean",
        ["grbl", "grblhal"],
    ),  # FluidNC uses YAML config
    23: (
        0,
        "Homing direction invert",
        "bitmask",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#23---homing-dir-invert-mask",
        ["all"],
    ),
    24: (
        25.000,
        "Homing locate feed rate",
        "mm/min",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#24---homing-feed-mmmin",
        ["all"],
    ),
    25: (
        500.000,
        "Homing search seek rate",
        "mm/min",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#25---homing-seek-mmmin",
        ["all"],
    ),
    26: (
        250,
        "Homing switch debounce delay",
        "ms",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#26---homing-debounce-milliseconds",
        ["all"],
    ),
    27: (
        1.000,
        "Homing switch pull-off distance",
        "mm",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#27---homing-pull-off-mm",
        ["all"],
    ),
    # Spindle settings
    30: (
        1000,
        "Maximum spindle speed",
        "RPM",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#30---max-spindle-speed-rpm",
        ["all"],
    ),
    31: (
        0,
        "Minimum spindle speed",
        "RPM",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#31---min-spindle-speed-rpm",
        ["all"],
    ),
    32: (
        1,
        "Laser mode enable",
        "boolean",
        int,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#32---laser-mode-boolean",
        ["grbl", "grblhal", "grbl_esp32"],
    ),  # FluidNC uses YAML config
    # X/Y/Z axis steps per mm
    100: (
        250.000,
        "X-axis steps per millimeter",
        "steps",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm",
        ["all"],
    ),
    101: (
        250.000,
        "Y-axis steps per millimeter",
        "steps",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm",
        ["all"],
    ),
    102: (
        250.000,
        "Z-axis steps per millimeter",
        "steps",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm",
        ["all"],
    ),
    # X/Y/Z axis max rates
    110: (
        500.000,
        "X-axis max rate",
        "mm/min",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin",
        ["all"],
    ),
    111: (
        500.000,
        "Y-axis max rate",
        "mm/min",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin",
        ["all"],
    ),
    112: (
        500.000,
        "Z-axis max rate",
        "mm/min",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin",
        ["all"],
    ),
    # X/Y/Z axis acceleration
    120: (
        10.000,
        "X-axis acceleration",
        "mm/s^2",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2",
        ["all"],
    ),
    121: (
        10.000,
        "Y-axis acceleration",
        "mm/s^2",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2",
        ["all"],
    ),
    122: (
        10.000,
        "Z-axis acceleration",
        "mm/s^2",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2",
        ["all"],
    ),
    # X/Y/Z axis max travel
    130: (
        200.000,
        "X-axis max travel",
        "mm",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm",
        ["all"],
    ),
    131: (
        200.000,
        "Y-axis max travel",
        "mm",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm",
        ["all"],
    ),
    132: (
        200.000,
        "Z-axis max travel",
        "mm",
        float,
        "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm",
        ["all"],
    ),
    # === GRBL Variant Extended Settings ===
    # These settings are available in GrblHAL, FluidNC, GRBL-ESP32 and other advanced variants
    # Extended control and inversion settings (GrblHAL)
    14: (
        73,
        "invert control signals",
        "control_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    15: (
        0,
        "invert coolant signals",
        "coolant_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    16: (
        0,
        "invert spindle signals",
        "spindle_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    17: (
        0,
        "disable control pullup",
        "control_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    18: (
        0,
        "disable limit pullup",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    19: (
        0,
        "disable probe pullup",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    # Extended homing and motion settings
    28: (
        1.000,
        "G73 retract distance",
        "mm",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    29: (
        0,
        "step pulse delay",
        "microseconds",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    # Extended spindle settings (GrblHAL/FluidNC)
    33: (
        5000,
        "Spindle PWM frequency",
        "Hz",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "grbl_esp32"],
    ),
    34: (
        0,
        "Spindle off PWM duty cycle",
        "percent",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "grbl_esp32"],
    ),
    35: (
        0,
        "Spindle minimum PWM duty cycle",
        "percent",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "grbl_esp32"],
    ),
    36: (
        100,
        "Spindle maximum PWM duty cycle",
        "percent",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "grbl_esp32"],
    ),
    37: (
        0,
        "Steppers deenergized mask",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    38: (
        1,
        "Spindle encoder PPR",
        "pulses",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    39: (
        1,
        "Enable printable realtime commands",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    # Advanced features (GrblHAL)
    40: (
        0,
        "Soft limits for jogging",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    43: (
        1,
        "Number of homing locate cycles",
        "cycles",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    # Homing axis priorities (GrblHAL)
    44: (
        0,
        "Homing axis priority 1",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    45: (
        0,
        "Homing axis priority 2",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    46: (
        0,
        "Homing axis priority 3",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    47: (
        0,
        "Homing axis priority 4",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    48: (
        0,
        "Homing axis priority 5",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    49: (
        0,
        "Homing axis priority 6",
        "axis_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal"],
    ),
    # Jogging settings (GrblHAL/FluidNC)
    50: (
        100,
        "Jogging step speed",
        "mm/min",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "fluidnc"],
    ),
    51: (
        1000,
        "Jogging slow speed",
        "mm/min",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "fluidnc"],
    ),
    52: (
        5000,
        "Jogging fast speed",
        "mm/min",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "fluidnc"],
    ),
    53: (
        0.1,
        "Jogging step distance",
        "mm",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "fluidnc"],
    ),
    54: (
        10,
        "Jogging slow distance",
        "mm",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "fluidnc"],
    ),
    55: (
        100,
        "Jogging fast distance",
        "mm",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ["grblhal", "fluidnc"],
    ),
    # System behavior settings (GrblHAL)
    60: (
        1,
        "Restore overrides after program",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    61: (
        0,
        "Ignore safety door when idle",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    62: (
        0,
        "Enable sleep function",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    63: (
        0,
        "Disable laser during hold",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    64: (
        0,
        "Force initialization alarm",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    65: (
        0,
        "Allow feed override during probe",
        "boolean",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    # Network settings (GrblHAL/FluidNC with WiFi/Ethernet)
    70: (
        0,
        "Network services enabled",
        "network_mask",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    71: (
        "GRBL",
        "Bluetooth device name",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    72: (
        "GRBL serial port",
        "Bluetooth service name",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    73: (
        0,
        "WiFi mode",
        "wifi_mode",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    74: (
        "",
        "WiFi STA SSID",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    75: (
        "",
        "WiFi STA password",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    76: (
        "GRBL",
        "WiFi AP SSID",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    77: (
        "",
        "WiFi AP password",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    78: (
        "",
        "WiFi AP country",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    79: (
        0,
        "WiFi AP channel",
        "channel",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    # PID control settings (Advanced GrblHAL with closed-loop spindle control)
    80: (
        0.0,
        "Spindle PID proportional gain",
        "gain",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    81: (
        0.0,
        "Spindle PID integral gain",
        "gain",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    82: (
        0.0,
        "Spindle PID derivative gain",
        "gain",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    84: (
        0.0,
        "Spindle PID max output error",
        "error",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    85: (
        0.0,
        "Spindle PID max integral error",
        "error",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    90: (
        0.0,
        "Spindle sync PID proportional gain",
        "gain",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    91: (
        0.0,
        "Spindle sync PID integral gain",
        "gain",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    92: (
        0.0,
        "Spindle sync PID derivative gain",
        "gain",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    # Network interface settings (GrblHAL/FluidNC - Interface 0)
    300: (
        "GRBL",
        "Network interface 0 hostname",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    301: (
        1,
        "Network interface 0 IP mode",
        "ip_mode",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    302: (
        "192.168.1.1",
        "Network interface 0 gateway",
        "ip_address",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    303: (
        "192.168.1.100",
        "Network interface 0 IP address",
        "ip_address",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    304: (
        "255.255.255.0",
        "Network interface 0 netmask",
        "ip_address",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    305: (
        23,
        "Network interface 0 telnet port",
        "port",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    306: (
        80,
        "Network interface 0 HTTP port",
        "port",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    307: (
        81,
        "Network interface 0 websocket port",
        "port",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    # Network interface settings (GrblHAL/FluidNC - Interface 1 - WiFi AP)
    310: (
        "GRBL-AP",
        "Network interface 1 hostname",
        "string",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    311: (
        0,
        "Network interface 1 IP mode",
        "ip_mode",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    312: (
        "192.168.4.1",
        "Network interface 1 gateway",
        "ip_address",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    313: (
        "192.168.4.1",
        "Network interface 1 IP address",
        "ip_address",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    314: (
        "255.255.255.0",
        "Network interface 1 netmask",
        "ip_address",
        str,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    315: (
        23,
        "Network interface 1 telnet port",
        "port",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    316: (
        80,
        "Network interface 1 HTTP port",
        "port",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    317: (
        81,
        "Network interface 1 websocket port",
        "port",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    # Advanced tool change and spindle control (GrblHAL with ATC)
    340: (
        0,
        "Spindle at speed tolerance",
        "percent",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    341: (
        0,
        "Manual tool change mode",
        "mode",
        int,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    342: (
        30,
        "Tool change probing distance",
        "mm",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    343: (
        25,
        "Tool change probing slow feed",
        "mm/min",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
    344: (
        200,
        "Tool change probing seek feed",
        "mm/min",
        float,
        "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
    ),
}


def hardware_settings(code):
    """
    Given a $# code returns the parameter and the units.

    @param code: $$ code.
    @return: (default_value, description, units, type, documentation_url, variants) or None if unknown
    """
    return GRBL_HARDWARE_SETTINGS.get(code)


def get_variant_compatible_settings(detected_variant="grbl"):
    """
    Get all settings that are compatible with the specified GRBL variant.

    @param detected_variant: The detected GRBL variant ('grbl', 'grblhal', 'fluidnc', 'grbl_esp32')
    @return: List of setting codes that are supported by the variant
    """
    compatible_settings = []

    for code, setting_data in GRBL_HARDWARE_SETTINGS.items():
        # Handle both old 5-tuple format and new 6-tuple format
        if len(setting_data) >= 6:
            variants = setting_data[5]  # New format with variant info
            if "all" in variants or detected_variant in variants:
                compatible_settings.append(code)
        else:
            # Old format - assign default variant compatibility based on setting code
            # This is a temporary transition approach
            if _is_setting_compatible_with_variant(code, detected_variant):
                compatible_settings.append(code)

    return sorted(compatible_settings)


def _is_setting_compatible_with_variant(code, variant):
    """
    Temporary function to determine compatibility for old format settings.
    This provides default behavior during the transition period.
    """
    # Basic GRBL settings (0-32, 100-132) - supported by all variants
    basic_settings = list(range(0, 33)) + list(range(100, 133))
    if code in basic_settings:
        return True

    # Extended GrblHAL-specific settings
    grblhal_only = list(range(14, 20)) + list(range(33, 100)) + list(range(300, 350))
    if code in grblhal_only:
        return variant in ["grblhal"]

    # Network settings - supported by variants with network capability
    network_settings = list(range(70, 80)) + list(range(300, 320))
    if code in network_settings:
        return variant in ["grblhal", "fluidnc", "grbl_esp32"]

    # Default: assume basic GRBL compatibility
    return variant in ["grbl", "grblhal"]


def add_hardware_setting(
    code, default_value, description, units, value_type, doc_url=None, variants=None
):
    """
    Dynamically add a hardware setting definition (useful for variant-specific settings).

    @param code: Setting code number
    @param default_value: Default value for the setting
    @param description: Human-readable description
    @param units: Units of measurement
    @param value_type: Data type (int or float)
    @param doc_url: Optional documentation URL
    @param variants: List of compatible variants, defaults to ['all']
    """
    if doc_url is None:
        doc_url = (
            f"https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#{code}"
        )

    if variants is None:
        variants = ["all"]

    GRBL_HARDWARE_SETTINGS[code] = (
        default_value,
        description,
        units,
        value_type,
        doc_url,
        variants,
    )


def get_all_settings_codes():
    """Get all known GRBL settings codes."""
    return list(GRBL_HARDWARE_SETTINGS.keys())


def populate_variant_specific_settings():
    """
    Automatically populate variant-specific settings that may not be in the base dictionary.
    This can be called to dynamically add known variant extensions.
    """
    # Additional 4th, 5th, 6th axis settings for 6-axis GrblHAL variants
    axis_extensions = {
        # A-axis (4th axis) settings
        103: (
            250.000,
            "A-axis steps per millimeter",
            "steps",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        113: (
            500.000,
            "A-axis max rate",
            "mm/min",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        123: (
            10.000,
            "A-axis acceleration",
            "mm/s^2",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        133: (
            200.000,
            "A-axis max travel",
            "mm",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        # B-axis (5th axis) settings
        104: (
            250.000,
            "B-axis steps per millimeter",
            "steps",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        114: (
            500.000,
            "B-axis max rate",
            "mm/min",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        124: (
            10.000,
            "B-axis acceleration",
            "mm/s^2",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        134: (
            200.000,
            "B-axis max travel",
            "mm",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        # C-axis (6th axis) settings
        105: (
            250.000,
            "C-axis steps per millimeter",
            "steps",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        115: (
            500.000,
            "C-axis max rate",
            "mm/min",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        125: (
            10.000,
            "C-axis acceleration",
            "mm/s^2",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
        135: (
            200.000,
            "C-axis max travel",
            "mm",
            float,
            "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
        ),
    }

    # Add axis extensions if not already present
    for code, setting in axis_extensions.items():
        if code not in GRBL_HARDWARE_SETTINGS:
            GRBL_HARDWARE_SETTINGS[code] = setting


def add_variant_specific_settings(variant_name):
    """
    Add settings specific to a detected GRBL variant.

    @param variant_name: Name of detected variant (grbl, grblhal, fluidnc, etc.)
    """
    if variant_name == "grblhal":
        # GrblHAL may have additional settings
        grblhal_specific = {
            # More precise timing control
            41: (
                0,
                "Limit switches debounce delay",
                "ms",
                int,
                "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
            ),
            42: (
                0,
                "Probe debounce delay",
                "ms",
                int,
                "https://github.com/grblHAL/core/wiki/Additional-or-extended-settings",
            ),
        }

        for code, setting in grblhal_specific.items():
            if code not in GRBL_HARDWARE_SETTINGS:
                add_hardware_setting(code, *setting)

    elif variant_name == "fluidnc":
        # FluidNC has different configuration approach (YAML), but may have some numeric settings
        fluidnc_specific = {
            # FluidNC may use some compatibility settings
            400: (
                0,
                "FluidNC compatibility mode",
                "mode",
                int,
                "http://wiki.fluidnc.com/en/config/overview",
            ),
        }

        for code, setting in fluidnc_specific.items():
            if code not in GRBL_HARDWARE_SETTINGS:
                add_hardware_setting(code, *setting)

    elif variant_name in ["grbl_esp32", "grbl-esp32"]:
        # GRBL-ESP32 specific settings
        esp32_specific = {
            # ESP32 specific power management
            350: (
                0,
                "WiFi power mode",
                "mode",
                int,
                "https://github.com/bdring/Grbl_Esp32",
            ),
            351: (
                1,
                "Bluetooth enable",
                "boolean",
                int,
                "https://github.com/bdring/Grbl_Esp32",
            ),
        }

        for code, setting in esp32_specific.items():
            if code not in GRBL_HARDWARE_SETTINGS:
                add_hardware_setting(code, *setting)


def grbl_error_code(code):
    error_messages = {
        1: "GCode Command letter was not found.",
        2: "GCode Command value invalid or missing.",
        3: "Grbl '$' not recognized or supported.",
        4: "Negative value for an expected positive value.",
        5: "Homing fail. Homing not enabled in settings.",
        6: "Min step pulse must be greater than 3usec.",
        7: "EEPROM read failed. Default values used.",
        8: "Grbl '$' command Only valid when Idle.",
        9: "GCode commands invalid in alarm or jog state.",
        10: "Soft limits require homing to be enabled.",
        11: "Max characters per line exceeded. Ignored.",
        12: "Grbl '$' setting exceeds the maximum step rate.",
        13: "Safety door opened and door state initiated.",
        14: "Build info or start-up line > EEPROM line length",
        15: "Jog target exceeds machine travel, ignored.",
        16: "Jog Cmd missing '=' or has prohibited GCode.",
        17: "Laser mode requires PWM output.",
        20: "Unsupported or invalid GCode command.",
        21: "> 1 GCode command in a modal group in block.",
        22: "Feed rate has not yet been set or is undefined.",
        23: "GCode command requires an integer value.",
        24: "> 1 GCode command using axis words found.",
        25: "Repeated GCode word found in block.",
        26: "No axis words found in command block.",
        27: "Line number value is invalid.",
        28: "GCode Cmd missing a required value word.",
        29: "G59.x WCS are not supported.",
        30: "G53 only valid with G0 and G1 motion modes.",
        31: "Unneeded Axis words found in block.",
        32: "G2/G3 arcs need >= 1 in-plane axis word.",
        33: "Motion command target is invalid.",
        34: "Arc radius value is invalid.",
        35: "G2/G3 arcs need >= 1 in-plane offset word.",
        36: "Unused value words found in block.",
        37: "G43.1 offset not assigned to tool length axis.",
        38: "Tool number greater than max value.",
    }
    short = f"Error #{code}"
    long = error_messages.get(code, f"Unrecognised error code #{code}")
    return short, long


def grbl_alarm_message(code):
    if code == 1:
        short = "Hard limit"
        long = (
            "Hard limit has been triggered."
            + " Machine position is likely lost due to sudden halt."
            + " Re-homing is highly recommended."
        )
    elif code == 2:
        short = "Soft limit"
        long = (
            "Soft limit alarm. G-code motion target exceeds machine travel."
            + " Machine position retained. Alarm may be safely unlocked."
        )
    elif code == 3:
        short = "Abort during cycle"
        long = (
            "Reset while in motion. Machine position is likely lost due to sudden halt."
            + " Re-homing is highly recommended. May be due to issuing g-code"
            + " commands that exceed the limit of the machine."
        )
    elif code == 4:
        short = "Probe fail"
        long = (
            "Probe fail. Probe is not in the expected initial state before"
            + " starting probe cycle when G38.2 and G38.3 is not triggered"
            + " and G38.4 and G38.5 is triggered."
        )
    elif code == 5:
        short = "Probe fail"
        long = (
            "Probe fail. Probe did not contact the workpiece within the programmed"
            + " travel for G38.2 and G38.4."
        )
    elif code == 6:
        short = "Homing fail"
        long = "Homing fail. The active homing cycle was reset."
    elif code == 7:
        short = "Homing fail"
        long = "Homing fail. Safety door was opened during homing cycle."
    elif code == 8:
        short = "Homing fail"
        long = (
            "Homing fail. Pull off travel failed to clear limit switch."
            + " Try increasing pull-off setting or check wiring."
        )
    elif code == 9:
        short = "Homing fail"
        long = (
            "Homing fail. Could not find limit switch within search distances."
            + " Try increasing max travel, decreasing pull-off distance,"
            + " or check wiring."
        )
    else:
        short = f"Alarm #{code}"
        long = "Unknow alarm status"
    long += "\nTry to clear the alarm status."
    return short, long


class GrblController:
    def __init__(self, context):
        self.service = context
        self.connection = None
        self._validation_stage = VALIDATION_STAGE_DISCONNECTED

        self.update_connection()

        self.driver = self.service.driver

        # Sending variables.
        self._sending_thread = None
        self._recving_thread = None

        self._forward_lock = threading.Lock()
        self._sending_lock = threading.Lock()
        self._realtime_lock = threading.Lock()
        self._loop_cond = threading.Condition()
        self._sending_queue = []
        self._realtime_queue = []
        # buffer for feedback...
        self._assembled_response = []
        self._forward_buffer = bytearray()
        self._device_buffer_size = self.service.planning_buffer_size
        self._log = None

        self._paused = False
        self._watchers = []
        self.is_shutdown = False

        # Validation timeout tracking
        self._cached_descriptions = {}
        self._validation_start_time = None
        self._validation_timeout = 5.0  # 5 seconds timeout per stage

        # Timeout analysis tracking
        self._timeout_history = []  # Track timeout events with details
        self._current_stage_messages = []  # Track messages sent in current stage
        self._stage_start_commands = {}  # Track what command started each stage
        self._welcome_message_history = []  # Track welcome messages for analysis

        # Validation mode selection logic
        self._validation_mode = self._get_validation_mode()
        self._update_validation_timeout()

    def _get_validation_mode(self):
        return self.service.validate_on_connect

    def get_validation_mode_description(self):
        """
        Get a human-readable description of the current validation mode.

        Returns:
            str: Description of the validation mode
        """
        # We read the descriptions dictionary
        if not self._cached_descriptions:
            lookup_choice = self.service.lookup("choices", "protocol")
            if lookup_choice is None:
                return "Could not find choices - call too early?"
            for entry in lookup_choice:
                if entry.get("attr") == "validate_on_connect":
                    keys = entry.get("choices", [])
                    descriptions = entry.get("display", [])
                    for key, desc in zip(keys, descriptions):
                        self._cached_descriptions[key] = desc
                    break

        return self._cached_descriptions.get(
            self._validation_mode, "Unknown validation mode"
        )

    def __repr__(self):
        return f"GRBLController('{self.service.location()}')"

    def __len__(self):
        return (
            len(self._sending_queue)
            + len(self._realtime_queue)
            + len(self._forward_buffer)
        )

    @property
    def _length_of_next_line(self):
        """
        Lookahead and provide length of the next line.
        @return:
        """
        if not self._sending_queue:
            return 0
        return len(self._sending_queue[0])

    @property
    def _index_of_forward_line(self):
        try:
            r = self._forward_buffer.index(b"\r")
        except ValueError:
            r = -1
        try:
            n = self._forward_buffer.index(b"\n")
        except ValueError:
            n = -1

        if n != -1:
            return min(n, r) if r != -1 else n
        else:
            return r

    @signal_listener("update_interface")
    def update_connection(self, origin=None, *args):
        if self.service.permit_serial and self.service.interface == "serial":
            try:
                from .serial_connection import SerialConnection

                self.connection = SerialConnection(self.service, self)
            except ImportError:
                pass
        elif self.service.permit_tcp and self.service.interface == "tcp":
            from meerk40t.grbl.tcp_connection import TCPOutput

            self.connection = TCPOutput(self.service, self)
        elif self.service.permit_ws and self.service.interface == "ws":
            from meerk40t.grbl.ws_connection import WSOutput

            try:
                self.connection = WSOutput(self.service, self)
            except ModuleNotFoundError:
                self.service.kernel.prompt(
                    str, "Could not open websocket-connection (websocket installed?)"
                )
        else:
            # Mock
            from .mock_connection import MockConnection

            self.connection = MockConnection(self.service, self)

    def add_watcher(self, watcher):
        self._watchers.append(watcher)

    def remove_watcher(self, watcher):
        self._watchers.remove(watcher)

    def log(self, data, type):
        for w in self._watchers:
            w(data, type=type)

    def _channel_log(self, data, type=None):
        name = self.service.safe_label
        if type == "send":
            if not hasattr(self, "_grbl_send"):
                self._grbl_send = self.service.channel(f"send-{name}", pure=True)
            self._grbl_send(data)
        elif type == "recv":
            if not hasattr(self, "_grbl_recv"):
                self._grbl_recv = self.service.channel(f"recv-{name}", pure=True)
            self._grbl_recv(data)
        elif type == "event":
            if not hasattr(self, "_grbl_events"):
                self._grbl_events = self.service.channel(f"events-{name}")
            self._grbl_events(data)

    def open(self):
        """
        Opens the connection calling connection.connect.

        Reads the first line this should be GRBL version and information.
        @return:
        """
        if self.connection.connected:
            return
        self.connection.connect()
        if not self.connection.connected:
            self.log("Could not connect.", type="event")
            return
        self.log("Connecting to GRBL...", type="event")
        self.log(f"Using {self.get_validation_mode_description()}", type="event")

        if self.service.reset_on_connect:
            self.driver.reset()

        # Apply validation mode logic
        self._apply_validation_mode()

        if self.service.startup_commands:
            self.log("Queue startup commands", type="event")
            lines = self.service.startup_commands.split("\n")
            line_end = self.service.driver.line_end
            for line in lines:
                if line.startswith("#"):
                    self.log(f"Startup: {line}", type="event")
                else:
                    self.service.driver(f"{line}{line_end}")

    def _apply_validation_mode(self):
        """Apply the selected validation mode strategy."""
        if self._validation_mode == "skip":
            # Skip validation entirely - immediately mark as validated
            self.log("Validation Mode: Skip - Connection assumed valid", type="event")
            self._validation_stage = VALIDATION_STAGE_VALIDATED

        elif self._validation_mode == "strict":
            # Strict mode - wait for welcome message, then validate
            self.log("Validation Mode: Strict - Awaiting welcome message", type="event")
            # Stage 0: Wait for welcome message (handled in _recving)
            self._validation_stage = VALIDATION_STAGE_DISCONNECTED

        elif self._validation_mode == "proactive":
            # Proactive mode - start validation after brief delay
            self.log(
                "Validation Mode: Proactive - Starting validation sequence",
                type="event",
            )
            if self.service.boot_connect_sequence:
                # Give device a moment to settle, then start validation
                name = self.service.safe_label
                self.service(f".timer-proactive-{name} 1 1.0 grbl_force_validate")
            else:
                self._validation_stage = VALIDATION_STAGE_VALIDATED

        elif self._validation_mode == "timeout":
            # Timeout mode - combination of strict with timeout fallback
            self.log("Validation Mode: Timeout - Strict with fallback", type="event")
            if self.service.boot_connect_sequence:
                self._start_validation_sequence("timeout mode")
            else:
                self._validation_stage = VALIDATION_STAGE_VALIDATED

    def force_validate_if_needed(self):
        """Force validation to start if we haven't received a welcome message"""
        if (
            self._validation_stage == VALIDATION_STAGE_DISCONNECTED
            and self.connection.connected
        ):
            self.log(
                "No welcome message received, forcing validation start", type="event"
            )
            if self.service.boot_connect_sequence:
                self._validation_stage = VALIDATION_STAGE_HELP_REQUEST
                self.validate_start("$")
            else:
                self._validation_stage = VALIDATION_STAGE_VALIDATED

    def close(self):
        """
        Close the GRBL connection.

        @return:
        """
        if not self.connection.connected:
            return
        self.connection.disconnect()
        self.log("Disconnecting from GRBL...", type="event")
        self.validate_stop("*")
        self._validation_stage = VALIDATION_STAGE_DISCONNECTED

    def write(self, data):
        """
        Write data to the sending queue.

        @param data:
        @return:
        """
        self.start()
        self.service.signal("grbl;write", data)
        with self._sending_lock:
            self._sending_queue.append(data)
        self.service.signal(
            "grbl;buffer", len(self._sending_queue) + len(self._realtime_queue)
        )
        self._send_resume()

    def realtime(self, data):
        """
        Write data to the realtime queue.

        The realtime queue should preemt the regular dataqueue.

        @param data:
        @return:
        """
        self.start()
        self.service.signal("grbl;write", data)
        with self._realtime_lock:
            self._realtime_queue.append(data)
        if "\x18" in data:
            with self._sending_lock:
                self._sending_queue.clear()
        self.service.signal(
            "grbl;buffer", len(self._sending_queue) + len(self._realtime_queue)
        )
        self._send_resume()

    ####################
    # Control GRBL Sender
    ####################

    def start(self):
        """
        Starts the driver thread.

        @return:
        """
        self.open()
        if self._channel_log not in self._watchers:
            self.add_watcher(self._channel_log)

        if self._sending_thread is None or (
            not isinstance(self._sending_thread, bool)
            and not self._sending_thread.is_alive()
        ):
            self._sending_thread = True  # Avoid race condition.
            self._sending_thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.service.location()}",
                result=self.stop,
                daemon=True,
            )
        if self._recving_thread is None or (
            not isinstance(self._recving_thread, bool)
            and not self._recving_thread.is_alive()
        ):
            self._recving_thread = True  # Avoid race condition.
            self._recving_thread = self.service.threaded(
                self._recving,
                thread_name=f"recver-{self.service.location()}",
                result=self._rstop,
                daemon=True,
            )

    def shutdown(self):
        self.is_shutdown = True
        self._forward_buffer.clear()

    def validate_start(self, cmd):
        delay = self.service.connect_delay / 1000 if cmd == "$" else 0
        name = self.service.safe_label

        # Start timeout tracking for this validation stage
        self._validation_start_time = time.time()

        # Track what command started this stage and reset message tracking
        self._stage_start_commands[self._validation_stage] = cmd
        self._current_stage_messages = []

        # Log the command being sent for this stage
        self.log(
            f"Stage {self._validation_stage}: Starting validation with command '{cmd}'",
            type="event",
        )

        if delay:
            self.service(f".timer 1 {delay} .gcode_realtime {cmd}")
            self.service(
                f".timer-{name}{cmd} 1 {delay} .timer-{name}{cmd} 0 1 gcode_realtime {cmd}"
            )
        else:
            self.service(f".gcode_realtime {cmd}")
            self.service(f".timer-{name}{cmd} 0 1 gcode_realtime {cmd}")

        # Track this message as sent for the current stage
        self._current_stage_messages.append(
            {
                "command": cmd,
                "timestamp": time.time(),
                "stage": self._validation_stage,
                "delay": delay,
            }
        )

    def _check_validation_timeout(self):
        """Check if current validation stage has timed out and advance if needed"""
        if (
            self._validation_start_time is None
            or self._validation_stage == VALIDATION_STAGE_DISCONNECTED
            or self._validation_stage == VALIDATION_STAGE_VALIDATED
        ):
            return False

        elapsed = time.time() - self._validation_start_time
        if elapsed > self._validation_timeout:
            # Record timeout event with detailed information
            timeout_info = {
                "timestamp": time.time(),
                "stage": self._validation_stage,
                "elapsed_time": elapsed,
                "timeout_limit": self._validation_timeout,
                "validation_mode": self._validation_mode,
                "start_command": self._stage_start_commands.get(
                    self._validation_stage, "unknown"
                ),
                "messages_sent": self._current_stage_messages.copy(),
                "responses_received": [],  # Will be populated by _recving thread
            }

            # Log timeout with detailed analysis
            self._log_timeout_analysis(timeout_info)

            # Add to timeout history
            self._timeout_history.append(timeout_info)

            # Advance to next stage
            self._advance_validation_stage()
            return True
        return False

    def _start_validation_sequence(self, reason=""):
        """Start the validation sequence (VALIDATION_STAGE_HELP_REQUEST with $ command)."""
        log_msg = "Starting validation sequence"
        if reason:
            log_msg += f" ({reason})"
        self.log(log_msg, type="event")
        self._validation_stage = VALIDATION_STAGE_HELP_REQUEST
        self.validate_start("$")

    def _suggest_welcome_setting(self, setting_value, description):
        """Log a welcome setting suggestion with consistent format."""
        self.log(
            f">> Suggestion: Change welcome setting to '{setting_value}'", type="event"
        )
        self.log(f"   {description}", type="event")

    def _log_welcome_variants_header(self):
        """Log the header for welcome message variants section."""
        self.log("", type="event")
        self.log("Unique welcome message variants found:", type="event")

    def _handle_variant_detection(self, response):
        """Handle GRBL variant detection and apply variant-specific behavior."""
        variant = self._detect_grbl_variant(response)
        if variant != "unknown":
            self._apply_variant_specific_behavior(variant, response)

    def _log_stage_advancement(self, stage_number, message):
        """Log validation stage advancement with consistent format."""
        self.log(f"Stage {stage_number}: {message}", type="event")
        self._validation_stage = stage_number

    def _detect_grbl_variant(self, welcome_message):
        """Detect GRBL firmware variant from welcome message."""
        if not welcome_message:
            return "unknown"

        msg_lower = welcome_message.lower()

        # Detect specific variants
        if "grblhal" in msg_lower:
            return "grblhal"
        elif "fluidnc" in msg_lower:
            return "fluidnc"
        elif msg_lower.startswith("grbl ") or msg_lower.startswith("grbl v"):
            return "grbl"
        elif "grbl_esp32" in msg_lower or "grbl-esp32" in msg_lower:
            return "grbl_esp32"
        elif "grbl-mega" in msg_lower:
            return "grbl_mega"
        elif "grbl" in msg_lower:
            return "grbl_variant"
        else:
            return "unknown"

    def _get_variant_specific_settings(self, variant):
        """Get variant-specific configuration settings."""
        settings = {
            "grbl": {
                "supports_laser_mode": True,
                "supports_real_time": True,
                "max_buffer_size": 128,
                "requires_ok": True,
                "supports_probe": True,
                "supports_z_axis": True,
                "home_commands": ["$H", "$HZ"],
                "reset_after_alarm": False,
            },
            "grblhal": {
                "supports_laser_mode": True,
                "supports_real_time": True,
                "max_buffer_size": 256,  # Often larger buffer
                "requires_ok": True,
                "supports_probe": True,
                "supports_z_axis": True,
                "home_commands": ["$H", "$HX", "$HY", "$HZ"],  # Individual axis homing
                "reset_after_alarm": False,
                "supports_enhanced_status": True,  # Extended status reports
            },
            "fluidnc": {
                "supports_laser_mode": True,
                "supports_real_time": True,
                "max_buffer_size": 256,  # ESP32 based, larger buffer
                "requires_ok": True,
                "supports_probe": True,
                "supports_z_axis": True,
                "home_commands": ["$H", "$HX", "$HY", "$HZ"],
                "reset_after_alarm": True,  # May need reset after alarms
                "supports_wifi": True,  # ESP32 WiFi capabilities
                "supports_sd_card": True,  # SD card support
            },
            "grbl_esp32": {
                "supports_laser_mode": True,
                "supports_real_time": True,
                "max_buffer_size": 256,
                "requires_ok": True,
                "supports_probe": True,
                "supports_z_axis": True,
                "home_commands": ["$H"],
                "reset_after_alarm": True,
                "supports_wifi": True,
            },
            "grbl_mega": {
                "supports_laser_mode": True,
                "supports_real_time": True,
                "max_buffer_size": 128,
                "requires_ok": True,
                "supports_probe": False,  # Limited probe support
                "supports_z_axis": True,
                "home_commands": ["$H"],
                "reset_after_alarm": False,
            },
            "unknown": {
                "supports_laser_mode": False,  # Conservative defaults
                "supports_real_time": False,
                "max_buffer_size": 64,
                "requires_ok": True,
                "supports_probe": False,
                "supports_z_axis": False,
                "home_commands": ["$H"],
                "reset_after_alarm": False,
            },
        }

        return settings.get(variant, settings["unknown"])

    def _apply_variant_specific_behavior(self, variant, welcome_message):
        """Apply variant-specific controller behavior."""
        settings = self._get_variant_specific_settings(variant)

        self.log("=== GRBL Variant Detection ===", type="event")
        self.log(f"Detected variant: {variant.upper()}", type="event")
        self.log(f"Welcome message: '{welcome_message}'", type="event")

        # Populate variant-specific settings in the hardware settings database
        try:
            add_variant_specific_settings(variant)
            self.log(
                f"Added {variant.upper()}-specific hardware settings to database",
                type="event",
            )
        except Exception as e:
            self.log(
                f"Note: Could not add variant-specific settings: {e}", type="event"
            )

        # Log capabilities
        capabilities = []
        if settings["supports_laser_mode"]:
            capabilities.append("Laser Mode")
        if settings["supports_real_time"]:
            capabilities.append("Real-time Commands")
        if settings["supports_probe"]:
            capabilities.append("Probing")
        if settings.get("supports_enhanced_status"):
            capabilities.append("Enhanced Status")
        if settings.get("supports_wifi"):
            capabilities.append("WiFi")
        if settings.get("supports_sd_card"):
            capabilities.append("SD Card")

        self.log(
            f"Capabilities: {', '.join(capabilities) if capabilities else 'Basic GRBL'}",
            type="event",
        )
        self.log(
            f"Recommended buffer size: {settings['max_buffer_size']} bytes",
            type="event",
        )

        # Store variant info for later use
        self._detected_variant = variant
        self._variant_settings = settings

        # ACTUALLY APPLY THE VARIANT-SPECIFIC SETTINGS
        self._apply_variant_configuration(settings)

        return settings

    def _apply_variant_configuration(self, settings):
        """Apply detected variant settings to controller configuration."""
        # Apply buffer size optimization
        recommended_buffer = settings["max_buffer_size"]
        if self._device_buffer_size != recommended_buffer:
            old_buffer = self._device_buffer_size
            self._device_buffer_size = recommended_buffer
            self.log(
                f"Applied buffer size: {old_buffer} → {recommended_buffer} bytes",
                type="event",
            )

        # Apply validation timeout adjustments for slower variants
        if settings.get("reset_after_alarm"):
            self.log(
                "Note: This variant may require reset after alarm conditions",
                type="event",
            )

        # Adjust validation timeout based on variant characteristics
        if self._validation_mode in ["strict", "timeout"]:
            original_timeout = self._validation_timeout

            # ESP32-based variants may be slower to respond
            if self._detected_variant in ["fluidnc", "grbl_esp32"]:
                self._validation_timeout = max(self._validation_timeout, 8.0)
            # GrblHAL may have more features but should be fast
            elif self._detected_variant == "grblhal":
                self._validation_timeout = max(self._validation_timeout, 6.0)
            # Unknown variants get conservative timeout
            elif self._detected_variant == "unknown":
                self._validation_timeout = max(self._validation_timeout, 10.0)

            if self._validation_timeout != original_timeout:
                self.log(
                    f"Adjusted validation timeout: {original_timeout}s → {self._validation_timeout}s",
                    type="event",
                )

        # Set variant-specific service properties for other components to use
        self.service._grbl_variant = self._detected_variant
        self.service._grbl_variant_settings = settings

        self.log(
            f"Applied {self._detected_variant.upper()} variant configuration",
            type="event",
        )

    def apply_manual_variant(self, variant_name):
        """Manually apply a specific GRBL variant configuration."""
        if variant_name not in [
            "grbl",
            "grblhal",
            "fluidnc",
            "grbl_esp32",
            "grbl_mega",
            "unknown",
        ]:
            self.log(
                f"Unknown variant: {variant_name}. Available: grbl, grblhal, fluidnc, grbl_esp32, grbl_mega, unknown",
                type="event",
            )
            return

        settings = self._get_variant_specific_settings(variant_name)

        self.log(
            f"=== Manually Applying {variant_name.upper()} Configuration ===",
            type="event",
        )

        # Store the variant info
        self._detected_variant = variant_name
        self._variant_settings = settings

        # Apply the configuration
        self._apply_variant_configuration(settings)

        self.log(
            f"Successfully applied {variant_name.upper()} variant configuration",
            type="event",
        )

    def get_variant_specific_commands(self, channel):
        """Get variant-specific command recommendations."""
        if not hasattr(self, "_detected_variant"):
            channel("No variant detected yet. Connect to device first.")
            return

        variant = self._detected_variant
        settings = self._variant_settings

        channel(f"=== {variant.upper()} Command Recommendations ===")

        # Home commands
        home_commands = settings.get("home_commands", ["$H"])
        channel(f"Home Commands: {', '.join(home_commands)}")

        if len(home_commands) > 1:
            channel("  Use individual axis homing for better control:")
            for cmd in home_commands:
                axis = cmd.replace("$H", "")
                axis_name = {"X": "X-axis", "Y": "Y-axis", "Z": "Z-axis"}.get(
                    axis, "All axes" if not axis else f"{axis}-axis"
                )
                channel(f"    {cmd} - Home {axis_name}")

        # Variant-specific command recommendations
        if variant == "grblhal":
            channel("GrblHAL Specific Commands:")
            channel("  $ES - Show extended settings")
            channel("  $S - Show startup lines")
            channel("  $RST=* - Factory reset")

        elif variant == "fluidnc":
            channel("FluidNC Specific Commands:")
            channel("  $SD/List - List SD card files")
            channel("  $LocalFS/List - List local filesystem")
            channel("  $WiFi/IP - Show WiFi IP address")
            channel("  $Settings/List - Show all settings")

        elif variant == "grbl_esp32":
            channel("GRBL-ESP32 Specific Commands:")
            channel("  $WIFI - WiFi configuration")
            channel("  $SLEEP - Enter sleep mode")

        # Common settings recommendations
        channel("Common Settings:")
        if settings.get("supports_laser_mode"):
            channel("  $32=1 - Enable laser mode (recommended for lasers)")

        channel("  $10=255 - Enable all status reports")
        channel("  $13=0 - Report in millimeters")

    def check_variant_compatibility(self, command):
        """Check if a command is compatible with the detected variant."""
        if not hasattr(self, "_detected_variant"):
            return True  # Unknown compatibility, assume compatible

        variant = self._detected_variant
        settings = self._variant_settings

        # Define variant-specific command compatibility
        incompatible_commands = {
            "unknown": ["$SD/", "$WiFi", "$LocalFS/", "$ES", "$SLEEP"],
            "grbl": ["$SD/", "$WiFi", "$LocalFS/", "$ES", "$SLEEP"],
            "grbl_mega": ["$SD/", "$WiFi", "$LocalFS/", "$ES", "$SLEEP"],
        }

        if variant in incompatible_commands:
            for incompatible in incompatible_commands[variant]:
                if command.upper().startswith(incompatible.upper()):
                    self.log(
                        f"Warning: Command '{command}' may not be supported by {variant.upper()}",
                        type="event",
                    )
                    return False

        return True

    def _log_timeout_analysis(self, channel, timeout_info):
        """Log detailed timeout analysis for debugging and pattern recognition"""
        stage = timeout_info["stage"]
        elapsed = timeout_info["elapsed_time"]
        command = timeout_info["start_command"]
        mode = timeout_info["validation_mode"]

        channel(f"*** TIMEOUT ANALYSIS - Stage {stage} ***")
        channel(
            f"   Mode: {mode} | Command: '{command}' | Elapsed: {elapsed:.2f}s",
        )

        if timeout_info["messages_sent"]:
            channel("   Messages sent during this stage:")
            for msg in timeout_info["messages_sent"]:
                delay_info = f" (delayed {msg['delay']}s)" if msg["delay"] > 0 else ""
                channel(
                    f"     - '{msg['command']}' at {time.strftime('%H:%M:%S', time.localtime(msg['timestamp']))}{delay_info}",
                )

        else:
            channel("     - No messages were sent in this stage")

        # Provide suggestions based on timeout pattern
        self._suggest_timeout_solutions(channel, timeout_info)

    def _suggest_timeout_solutions(self, channel, timeout_info):
        """Suggest solutions based on timeout patterns and device behavior"""
        stage = timeout_info["stage"]
        command = timeout_info["start_command"]
        mode = timeout_info["validation_mode"]

        suggestions = []

        if stage == VALIDATION_STAGE_HELP_REQUEST and command == "$":
            suggestions.extend(
                [
                    "Device may not respond to '$' command (help request)",
                    "Try increasing connect_delay in device settings",
                    "Consider switching to 'proactive' validation mode",
                    "Device may be non-standard GRBL firmware",
                ]
            )
        elif stage == VALIDATION_STAGE_SETTINGS_QUERY and command in ["$$", "$G"]:
            suggestions.extend(
                [
                    "Device may not support settings query ('$$') or modal state ('$G')",
                    "This could be a minimal GRBL implementation",
                    "Consider adding custom validation pattern for this device type",
                ]
            )
        elif stage == VALIDATION_STAGE_MODAL_QUERY and command == "?":
            suggestions.extend(
                [
                    "Device may not support status reporting ('?')",
                    "Device might be in alarm state preventing status reports",
                    "Try manual device reset before connection",
                ]
            )

        if mode in ["timeout", "proactive"]:
            suggestions.append(
                "Current mode includes timeout fallbacks - connection should still work"
            )
        elif mode == "strict":
            suggestions.append(
                "Consider switching to 'timeout' mode for better device compatibility"
            )

        # Display suggestions
        if suggestions:
            channel("   >> Suggested solutions:")
            for suggestion in suggestions:
                channel(f"     - {suggestion}")
        else:
            channel(
                "   >> No specific suggestions available for this timeout pattern",
            )

        # Log pattern for potential new validation methods
        pattern_id = f"{stage}_{command}_{mode}"
        channel(
            f"   [PATTERN] {pattern_id} (use for adding new validation methods)",
        )

    def _advance_validation_stage(self):
        """Advance to next validation stage due to timeout or fallback"""
        if self._validation_stage == VALIDATION_STAGE_HELP_REQUEST:
            # $ command timed out, try $$ and $G anyway
            self._log_stage_advancement(
                VALIDATION_STAGE_SETTINGS_QUERY,
                "Advancing without $ confirmation (timeout)",
            )
            self.validate_stop("$")
            self.validate_start("$$")
            self.validate_start("$G")
        elif self._validation_stage == VALIDATION_STAGE_SETTINGS_QUERY:
            # $$ timed out, assume it worked
            self._log_stage_advancement(
                VALIDATION_STAGE_SETTINGS_PARSED, "Assuming $$ worked (timeout)"
            )
            self.validate_stop("$$")
        elif self._validation_stage == VALIDATION_STAGE_SETTINGS_PARSED:
            # $G timed out, try status anyway
            self._log_stage_advancement(
                VALIDATION_STAGE_MODAL_QUERY,
                "Advancing without $G confirmation (timeout)",
            )
            self.validate_stop("$G")
            self.validate_start("?")
        elif self._validation_stage == VALIDATION_STAGE_MODAL_QUERY:
            # Status timed out, assume we're connected
            self._log_stage_advancement(
                VALIDATION_STAGE_VALIDATED, "Connection assumed valid (timeout)"
            )
            self.validate_stop("?")

    def validate_stop(self, cmd):
        name = self.service.safe_label
        if cmd == "*":
            self.service(f".timer-{name}* -q --off")
            return
        self.service(f".timer-{name}{cmd} -q --off")
        if cmd == "$" and len(self._forward_buffer) > 3:
            # If the forward planning buffer is longer than 3 it must have filled with failed attempts.
            with self._forward_lock:
                self._forward_buffer.clear()

    def _rstop(self, *args):
        self._recving_thread = None

    def stop(self, *args):
        """
        Processes the stopping of the sending queue.

        @param args:
        @return:
        """
        self._sending_thread = None
        self.close()
        self._send_resume()

        try:
            self.remove_watcher(self._channel_log)
        except (AttributeError, ValueError):
            pass

    ####################
    # GRBL SEND ROUTINES
    ####################

    def _send(self, line):
        """
        Write the line to the connection, announce it to the send channel, and add it to the forward buffer.

        @param line:
        @return:
        """

        with self._forward_lock:
            self._forward_buffer += bytes(line, encoding="latin-1")
        self.connection.write(line)
        self.log(line, type="send")

        # Track sent messages during validation stages
        validation_stages = [
            VALIDATION_STAGE_HELP_REQUEST,
            VALIDATION_STAGE_SETTINGS_QUERY,
            VALIDATION_STAGE_SETTINGS_PARSED,
            VALIDATION_STAGE_MODAL_QUERY,
        ]
        if self._validation_stage in validation_stages and not self.fully_validated():
            message_info = {
                "command": line.strip(),
                "timestamp": time.time(),
                "stage": self._validation_stage,
                "delay": 0,
            }
            self._current_stage_messages.append(message_info)

    def _sending_realtime(self):
        """
        Send one line of realtime queue.

        @return:
        """
        with self._realtime_lock:
            line = self._realtime_queue.pop(0)
        if "!" in line:
            self._paused = True
        if "~" in line:
            self._paused = False
        if line is not None:
            self._send(line)
        if "\x18" in line:
            self._paused = False
            with self._forward_lock:
                self._forward_buffer.clear()

    def _sending_single_line(self):
        """
        Send one line of sending queue.

        @return:
        """
        with self._sending_lock:
            line = self._sending_queue.pop(0)
        if line:
            self._send(line)
        self.service.signal("grbl;buffer", len(self._sending_queue))
        return True

    def _send_halt(self):
        """
        This is called internally in the _sending command.
        @return:
        """
        with self._loop_cond:
            self._loop_cond.wait()

    def _send_resume(self):
        """
        Other threads are expected to call this routine to permit _sending to resume.

        @return:
        """
        with self._loop_cond:
            self._loop_cond.notify()

    def _sending(self):
        """
        Generic sender, delegate the function according to the desired mode.

        This function is only run with the self.sending_thread
        @return:

        """
        while self.connection.connected:
            if self._realtime_queue:
                # Send realtime data.
                self._sending_realtime()
                continue
            if self._paused or not self.fully_validated():
                # We are paused or invalid. We do not send anything other than realtime commands.
                time.sleep(0.05)
                continue
            if not self._sending_queue:
                # There is nothing to write/realtime
                self.service.laser_status = "idle"
                self._send_halt()
                continue
            buffer = len(self._forward_buffer)
            if buffer:
                self.service.laser_status = "active"

            if self.service.buffer_mode == "sync":
                if buffer:
                    # Any buffer is too much buffer. Halt.
                    self._send_halt()
                    continue
            else:
                # Buffered
                if self._device_buffer_size <= buffer + self._length_of_next_line:
                    # Stop sending when buffer is the size of permitted buffer size.
                    self._send_halt()
                    continue
            # Go for send_line
            self._sending_single_line()
        self.service.laser_status = "idle"

    ####################
    # GRBL RECV ROUTINES
    ####################

    def get_forward_command(self):
        """
        Gets the forward command from the front of the forward buffer. This was the oldest command that the controller
        has not processed.

        @return:
        """
        q = self._index_of_forward_line
        if q == -1:
            raise ValueError("No forward command exists.")
        with self._forward_lock:
            cmd_issued = self._forward_buffer[: q + 1]
            self._forward_buffer = self._forward_buffer[q + 1 :]
        return cmd_issued

    def _recving(self):
        """
        Generic recver, delegate the function according to the desired mode.

        Read and process response from grbl.

        This function is only run with the self.recver_thread
        @return:
        """
        while self.connection.connected:
            # Check for validation timeouts
            if self._check_validation_timeout():
                continue

            # reading responses.
            response = None
            while not response:
                try:
                    response = self.connection.read()
                except (ConnectionAbortedError, AttributeError):
                    return
                if not response:
                    time.sleep(0.01)
                    if self.is_shutdown:
                        return
                    # Check timeout again during waiting
                    if self._check_validation_timeout():
                        break
            self.service.signal("grbl;response", response)
            self.log(response, type="recv")
            if response == "ok":
                # Indicates that the command line received was parsed and executed (or set to be executed).
                try:
                    cmd_issued = self.get_forward_command()
                    cmd_issued = cmd_issued.decode(encoding="latin-1")
                except ValueError:
                    # We got an ok. But, had not sent anything.
                    self.log(
                        f"Response: {response}, but this was unexpected", type="event"
                    )
                    self._assembled_response = []
                    continue
                    # raise ConnectionAbortedError from e
                self.log(
                    f"{response} / {len(self._forward_buffer)} -- {cmd_issued}",
                    type="recv",
                )
                self.service.signal(
                    "grbl;response", cmd_issued, self._assembled_response
                )
                self._assembled_response = []
                self._send_resume()
            elif response.startswith("error"):
                # Indicates that the command line received contained an error, with an error code x, and was purged.
                try:
                    cmd_issued = self.get_forward_command()
                    cmd_issued = cmd_issued.decode(encoding="latin-1")
                except ValueError:
                    cmd_issued = ""
                try:
                    error_num = int(response[6:])
                except ValueError:
                    error_num = -1
                short, long = grbl_error_code(error_num)
                error_desc = f"#{error_num} '{cmd_issued}' {short}\n{long}"
                self.service.signal("grbl;error", f"GRBL: {error_desc}", response, 4)
                self.log(f"ERROR {error_desc}", type="recv")
                self._assembled_response = []
                self._send_resume()
                continue
            elif response.startswith("<"):
                self._process_status_message(response)
            elif response.startswith("["):
                self._process_feedback_message(response)
                continue
            elif response.startswith("$"):
                if self._validation_stage == VALIDATION_STAGE_SETTINGS_QUERY:
                    self.log("Stage 3: $$ was successfully parsed.", type="event")
                    self.validate_stop("$$")
                    self._validation_stage = VALIDATION_STAGE_SETTINGS_PARSED
                self._process_settings_message(response)
            elif response.startswith("Alarm|"):
                # There's no errorcode
                error_num = 1
                short, long = grbl_alarm_message(error_num)
                alarm_desc = f"#{error_num}, {short}\n{long}"
                self.service.signal("warning", f"GRBL: {alarm_desc}", response, 4)
                self.log(f"Alarm {alarm_desc}", type="recv")
                self._assembled_response = []

            elif response.startswith("ALARM"):
                try:
                    error_num = int(response[6:])
                except ValueError:
                    error_num = -1
                short, long = grbl_alarm_message(error_num)
                alarm_desc = f"#{error_num}, {short}\n{long}"
                self.service.signal("warning", f"GRBL: {alarm_desc}", response, 4)
                self.log(f"Alarm {alarm_desc}", type="recv")
                self._assembled_response = []
            elif response.startswith(">"):
                self.log(f"STARTUP: {response}", type="event")
            elif self._is_welcome_message(response):
                self._handle_welcome_message(response)
            else:
                self._assembled_response.append(response)

    def _is_welcome_message(self, response):
        """
        Check if a response looks like a welcome message from GRBL or GRBL-compatible firmware.

        This method is more flexible than exact string matching and can recognize:
        - Standard GRBL: "Grbl 1.1f ['$' for help]"
        - Case variations: "grbl", "GRBL"
        - Version variations: "Grbl v1.1h", "grbl 0.9j"
        - Custom variants: "grbl-Mega", "GrblHAL"

        Args:
            response (str): The response string to check

        Returns:
            bool: True if this looks like a welcome message
        """
        if not response or not isinstance(response, str):
            return False

        response_lower = response.lower().strip()

        # Primary check: starts with configured welcome message (exact match)
        if response.startswith(self.service.welcome):
            self._handle_variant_detection(response)
            return True

        # Flexible patterns for GRBL-like welcome messages
        welcome_patterns = [
            "grbl ",  # Standard: "Grbl 1.1f"
            "grbl v",  # Version format: "Grbl v1.1h"
            "grbl-",  # Custom variants: "grbl-Mega"
            "grblhal",  # GrblHAL firmware
            "grbl_esp32",  # ESP32 variants
            "fluidnc",  # FluidNC (GRBL-compatible)
        ]

        # Check if response starts with any known GRBL pattern
        for pattern in welcome_patterns:
            if response_lower.startswith(pattern):
                self.log(
                    f"Recognized GRBL-like welcome: '{response}' (pattern: {pattern})",
                    type="event",
                )

                # Detect and apply variant-specific behavior
                self._handle_variant_detection(response)

                return True

        # Additional heuristic: contains "grbl" and looks like version info
        if "grbl" in response_lower and any(char.isdigit() for char in response):
            # Likely a version string containing GRBL
            self.log(f"Heuristic match for GRBL welcome: '{response}'", type="event")

            # Detect and apply variant-specific behavior
            self._handle_variant_detection(response)

            return True

        return False

    def _handle_welcome_message(self, response):
        """Handle welcome message based on current validation mode."""
        # Track the welcome message for analysis
        welcome_info = {
            "timestamp": time.time(),
            "message": response,
            "validation_mode": self._validation_mode,
            "expected_welcome": self.service.welcome,
            "exact_match": response.startswith(self.service.welcome),
        }
        self._welcome_message_history.append(welcome_info)

        if self._validation_mode == "skip":
            # Skip mode - already validated
            return

        # Log the actual received welcome message
        self.log(f"Welcome message received: '{response}'", type="event")
        if not welcome_info["exact_match"]:
            self.log(
                f"Note: Welcome differs from expected '{self.service.welcome}'",
                type="event",
            )

        if self._validation_mode == "strict":
            # Strict mode - welcome message is required
            if self.service.boot_connect_sequence:
                self._start_validation_sequence("strict mode")
            else:
                self._validation_stage = 5

        elif self._validation_mode in ("proactive", "timeout"):
            # For proactive and timeout modes, handle welcome message if received
            if not self.service.require_validator:
                # Validation not required, handle reset if needed
                if self.fully_validated():
                    if self.service.boot_connect_sequence:
                        # Boot sequence is required. Restart sequence.
                        self._start_validation_sequence("device reset")
                else:
                    # Start validation sequence
                    if self.service.boot_connect_sequence:
                        # Boot sequence is required. Start sequence.
                        self._start_validation_sequence("proactive/timeout mode")
                    else:
                        # No boot sequence required. Declare fully connected.
                        self._validation_stage = VALIDATION_STAGE_VALIDATED
            else:
                # Validation is required. This was stage 0.
                if self.service.boot_connect_sequence:
                    # Boot sequence is required. Start sequence.
                    self._start_validation_sequence("validation required")
                else:
                    # No boot sequence required. Declare fully connected.
                    self._validation_stage = VALIDATION_STAGE_VALIDATED

    def fully_validated(self):
        return self._validation_stage == VALIDATION_STAGE_VALIDATED

    def force_validate(self):
        self._validation_stage = VALIDATION_STAGE_VALIDATED
        self.validate_stop("*")

    def grbl_force_validate(self):
        """Command handler for forced validation start"""
        self.force_validate_if_needed()

    def grbl_validation_info(self):
        """Command handler to show validation mode information"""
        self.log(f"Current validation mode: {self._validation_mode}", type="event")
        self.log(self.get_validation_mode_description(), type="event")
        self.log(f"Validation stage: {self._validation_stage}", type="event")
        self.log(f"Validation timeout: {self._validation_timeout}s", type="event")
        self.log(f"Timeout events recorded: {len(self._timeout_history)}", type="event")
        self.log(
            f"Welcome messages recorded: {len(self._welcome_message_history)}",
            type="event",
        )

        if self._current_stage_messages:
            self.log(
                f"Current stage messages: {len(self._current_stage_messages)}",
                type="event",
            )

        # Show available timeout analysis commands
        self.log("Available analysis commands:", type="event")
        self.log(
            "  > grbl_timeout_history [count] - Show recent timeout events",
            type="event",
        )
        self.log("  > grbl_timeout_patterns - Analyze timeout patterns", type="event")
        self.log(
            "  > grbl_welcome_history [count] - Show recent welcome messages",
            type="event",
        )
        self.log(
            "  > grbl_welcome_patterns - Analyze welcome message patterns", type="event"
        )
        self.log(
            "  > grbl_suggest_welcome_pattern - Suggest optimal welcome setting",
            type="event",
        )
        self.log(
            "  > grbl_clear_timeout_history - Clear recorded timeout data", type="event"
        )
        self.log(
            "  > grbl_export_timeout_data - Export timeout data for analysis",
            type="event",
        )

    def grbl_set_validation_mode(self, mode):
        """Command handler to manually set validation mode"""
        valid_modes = ["skip", "strict", "proactive", "timeout"]
        if mode not in valid_modes:
            self.log(
                f"Invalid mode '{mode}'. Valid modes: {', '.join(valid_modes)}",
                type="event",
            )
            return

        old_mode = self._validation_mode
        self._validation_mode = mode
        self._update_validation_timeout()

        self.log(f"Validation mode changed from '{old_mode}' to '{mode}'", type="event")
        self.log(self.get_validation_mode_description(), type="event")

        # If currently connected, reapply the validation mode
        if hasattr(self.connection, "connected") and self.connection.connected:
            self.log("Reapplying validation mode to current connection", type="event")
            self._apply_validation_mode()

    def grbl_timeout_history(self, count=None):
        """Command handler to show timeout history"""
        if not self._timeout_history:
            self.log("No timeout events recorded", type="event")
            return

        # Show recent timeouts (default 5, or all if count specified)
        display_count = int(count) if count and count.isdigit() else 5
        recent_timeouts = self._timeout_history[-display_count:]

        self.log(
            f"=== Timeout History (showing {len(recent_timeouts)} of {len(self._timeout_history)} events) ===",
            type="event",
        )

        for i, timeout in enumerate(recent_timeouts, 1):
            timestamp = time.strftime("%H:%M:%S", time.localtime(timeout["timestamp"]))
            self.log(
                f"  {i}. [{timestamp}] Stage {timeout['stage']} - '{timeout['start_command']}' "
                f"({timeout['elapsed_time']:.2f}s/{timeout['timeout_limit']:.1f}s, {timeout['validation_mode']} mode)",
                type="event",
            )

            if timeout["messages_sent"]:
                for msg in timeout["messages_sent"]:
                    msg_time = time.strftime(
                        "%H:%M:%S", time.localtime(msg["timestamp"])
                    )
                    self.log(
                        f"       Sent: '{msg['command']}' at {msg_time}", type="event"
                    )

    def grbl_timeout_patterns(self):
        """Command handler to analyze timeout patterns and suggest new validation methods"""
        if not self._timeout_history:
            self.log("No timeout data available for pattern analysis", type="event")
            return

        # Analyze patterns
        patterns = {}
        for timeout in self._timeout_history:
            pattern_key = f"Stage_{timeout['stage']}_{timeout['start_command']}"
            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    "count": 0,
                    "total_time": 0,
                    "modes": set(),
                    "suggestions": [],
                }

            patterns[pattern_key]["count"] += 1
            patterns[pattern_key]["total_time"] += timeout["elapsed_time"]
            patterns[pattern_key]["modes"].add(timeout["validation_mode"])

        self.log("=== Timeout Pattern Analysis ===", type="event")

        for pattern, data in patterns.items():
            avg_time = data["total_time"] / data["count"]
            modes_str = ", ".join(sorted(data["modes"]))

            self.log(f"  Pattern: {pattern}", type="event")
            self.log(
                f"    Occurrences: {data['count']} | Avg Time: {avg_time:.2f}s | Modes: {modes_str}",
                type="event",
            )

            # Generate suggestions for new validation methods
            stage, command = pattern.split("_")[1], pattern.split("_", 2)[2]
            suggestions = self._generate_pattern_suggestions(
                stage, command, data["count"], avg_time
            )

            if suggestions:
                self.log("    >> Suggestions for new validation method:", type="event")
                for suggestion in suggestions:
                    self.log(f"       - {suggestion}", type="event")

    def _generate_pattern_suggestions(self, stage, command, count, avg_time):
        """Generate suggestions for new validation methods based on patterns"""
        suggestions = []

        if count >= 3:  # Frequent timeout pattern
            suggestions.append(
                f"Create specialized handler for devices that don't respond to '{command}'"
            )

        if avg_time > 8.0:  # Very slow responses
            suggestions.append(
                "Implement extended timeout validation mode for slow devices"
            )

        if stage == str(VALIDATION_STAGE_HELP_REQUEST) and command == "$":
            suggestions.extend(
                [
                    "Add 'no-help' validation mode that skips '$' command entirely",
                    "Implement alternative device detection using different commands",
                ]
            )

        elif stage == str(VALIDATION_STAGE_SETTINGS_QUERY) and command in ["$$", "$G"]:
            suggestions.append(
                "Create 'minimal-grbl' validation mode for basic implementations"
            )

        elif stage == str(VALIDATION_STAGE_MODAL_QUERY) and command == "?":
            suggestions.append(
                "Add 'status-free' validation mode that doesn't require status reporting"
            )

        return suggestions

    def grbl_clear_timeout_history(self):
        """Command handler to clear timeout history"""
        count = len(self._timeout_history)
        self._timeout_history.clear()
        self.log(f"Cleared {count} timeout events from history", type="event")

    def grbl_export_timeout_data(self):
        """Command handler to export timeout data for analysis"""
        if not self._timeout_history:
            self.log("No timeout data to export", type="event")
            return

        self.log("=== Timeout Data Export ===", type="event")
        self.log(
            "Format: timestamp,stage,command,elapsed_time,timeout_limit,mode,messages_sent",
            type="event",
        )

        for timeout in self._timeout_history:
            messages = ";".join([msg["command"] for msg in timeout["messages_sent"]])
            export_line = (
                f"{timeout['timestamp']},{timeout['stage']},{timeout['start_command']},"
                f"{timeout['elapsed_time']:.2f},{timeout['timeout_limit']:.1f},"
                f"{timeout['validation_mode']},{messages}"
            )
            self.log(export_line, type="event")

        self.log(f"Exported {len(self._timeout_history)} timeout events", type="event")

    def grbl_welcome_history(self, count=None):
        """Command handler to show welcome message history"""
        if not self._welcome_message_history:
            self.log("No welcome messages recorded", type="event")
            return

        # Show recent welcome messages (default 10, or all if count specified)
        display_count = int(count) if count and count.isdigit() else 10
        recent_welcomes = self._welcome_message_history[-display_count:]

        self.log(
            f"=== Welcome Message History (showing {len(recent_welcomes)} of {len(self._welcome_message_history)} messages) ===",
            type="event",
        )

        for i, welcome in enumerate(recent_welcomes, 1):
            timestamp = time.strftime("%H:%M:%S", time.localtime(welcome["timestamp"]))
            match_status = "EXACT" if welcome["exact_match"] else "PATTERN"
            self.log(
                f"  {i}. [{timestamp}] {match_status}: '{welcome['message']}'",
                type="event",
            )
            if not welcome["exact_match"]:
                self.log(
                    f"       Expected: '{welcome['expected_welcome']}'", type="event"
                )

    def grbl_welcome_patterns(self):
        """Command handler to analyze welcome message patterns"""
        if not self._welcome_message_history:
            self.log(
                "No welcome message data available for pattern analysis", type="event"
            )
            return

        self.log("=== Welcome Message Pattern Analysis ===", type="event")

        exact_matches = 0
        pattern_matches = 0
        unique_messages = set()

        for welcome in self._welcome_message_history:
            unique_messages.add(welcome["message"])
            if welcome["exact_match"]:
                exact_matches += 1
            else:
                pattern_matches += 1

        total = len(self._welcome_message_history)
        self.log(f"Total welcome messages: {total}", type="event")
        self.log(
            f"Exact matches: {exact_matches} ({exact_matches/total*100:.1f}%)",
            type="event",
        )
        self.log(
            f"Pattern matches: {pattern_matches} ({pattern_matches/total*100:.1f}%)",
            type="event",
        )
        self.log(f"Unique message variants: {len(unique_messages)}", type="event")

        if len(unique_messages) > 1:
            self._log_welcome_variants_header()
            for i, message in enumerate(sorted(unique_messages), 1):
                self.log(f"  {i}. '{message}'", type="event")

            self.log("", type="event")
            self.log(">> Suggestions:", type="event")
            if pattern_matches > 0:
                self.log(
                    "  - Consider updating the 'welcome' setting to match the most common variant",
                    type="event",
                )
                self.log(
                    "  - The pattern matching is working correctly for non-exact matches",
                    type="event",
                )
            if len(unique_messages) > 3:
                self.log(
                    "  - Multiple firmware variants detected - this is normal for different GRBL versions",
                    type="event",
                )

    def grbl_suggest_welcome_pattern(self):
        """Command handler to suggest optimal welcome pattern based on collected data"""
        if not self._welcome_message_history:
            self.log("No welcome message data available", type="event")
            return

        # Count frequency of different messages
        message_counts = {}
        for welcome in self._welcome_message_history:
            msg = welcome["message"]
            message_counts[msg] = message_counts.get(msg, 0) + 1

        # Find most common message
        most_common = max(message_counts.items(), key=lambda x: x[1])
        current_setting = self.service.welcome

        self.log("=== Welcome Pattern Suggestion ===", type="event")
        self.log(f"Current setting: '{current_setting}'", type="event")
        self.log(
            f"Most common message: '{most_common[0]}' ({most_common[1]} times)",
            type="event",
        )

        if most_common[0] != current_setting:
            # Extract a better pattern
            common_msg = most_common[0].lower()

            # Suggest patterns based on analysis
            if common_msg.startswith("grbl "):
                # Standard GRBL with version
                suggested = "Grbl"
                self._suggest_welcome_setting(
                    suggested, "This will match standard GRBL version strings"
                )
            elif "grblhal" in common_msg:
                suggested = "GrblHAL"
                self._suggest_welcome_setting(
                    suggested, "This will match GrblHAL firmware variants"
                )
            elif "fluidnc" in common_msg:
                suggested = "FluidNC"
                self._suggest_welcome_setting(
                    suggested, "This will match FluidNC firmware"
                )
            else:
                # Try to extract common prefix
                words = most_common[0].split()
                if words:
                    suggested = words[0]
                    self._suggest_welcome_setting(
                        suggested, "Based on the first word of most common message"
                    )
        else:
            self.log(">> Current welcome setting appears optimal", type="event")

    def _get_validation_timeout_for_mode(self):
        """Get appropriate timeout value for current validation mode."""
        timeouts = {
            "skip": 0,  # No timeout needed
            "strict": 10.0,  # Longer timeout for strict mode
            "proactive": 3.0,  # Shorter timeout for proactive
            "timeout": 5.0,  # Standard timeout
        }
        return timeouts.get(self._validation_mode, 5.0)

    def _update_validation_timeout(self):
        """Update validation timeout based on current mode."""
        new_timeout = self._get_validation_timeout_for_mode()
        if new_timeout != self._validation_timeout:
            self._validation_timeout = new_timeout
            self.log(
                f"Validation timeout updated to {self._validation_timeout}s for mode '{self._validation_mode}'",
                type="event",
            )

    def _process_status_message(self, response):
        message = response[1:-1]
        data = list(message.split("|"))
        self.service.signal("grbl:state", data[0])
        for datum in data[1:]:
            # While valid some grbl replies might violate the parsing convention.
            try:
                name, info = datum.split(":")
            except ValueError:
                continue
            if name == "F":
                self.service.signal("grbl:speed", float(info))
            elif name == "S":
                self.service.signal("grbl:power", float(info))
            elif name == "FS":
                f, s = info.split(",")
                self.service.signal("grbl:speed", float(f))
                self.service.signal("grbl:power", float(s))
            elif name == "MPos":
                coords = info.split(",")
                try:
                    nx = float(coords[0])
                    ny = float(coords[1])

                    if not self.fully_validated():
                        # During validation, we declare positions.
                        self.driver.declare_position(nx, ny)
                    ox = self.driver.mpos_x
                    oy = self.driver.mpos_y

                    x, y = self.service.view_mm.position(f"{nx}mm", f"{ny}mm")

                    (
                        self.driver.mpos_x,
                        self.driver.mpos_y,
                    ) = self.service.view_mm.scene_position(f"{x}mm", f"{y}mm")

                    if len(coords) >= 3:
                        self.driver.mpos_z = float(coords[2])
                    self.service.signal(
                        "status;position",
                        (ox, oy, self.driver.mpos_x, self.driver.mpos_y),
                    )
                except ValueError:
                    pass
            elif name == "WPos":
                coords = info.split(",")
                self.driver.wpos_x = coords[0]
                self.driver.wpos_y = coords[1]
                if len(coords) >= 3:
                    self.driver.wpos_z = coords[2]
            # See: https://github.com/grbl/grbl/blob/master/grbl/report.c#L421
            # MPos: Coord values. Machine Position.
            # WPos: MPos but with applied work coordinates. Work Position.
            # RX: serial rx buffer count.
            # Buf: plan block buffer count.
            # Ln: line number.
            # Lim: limits states
            # Ctl: control pins and mask (binary).
            self.service.signal(f"grbl:status:{name}", info)
        validation_stages_to_validate = (
            VALIDATION_STAGE_SETTINGS_QUERY,
            VALIDATION_STAGE_SETTINGS_PARSED,
            VALIDATION_STAGE_MODAL_QUERY,
        )
        if self._validation_stage in validation_stages_to_validate:
            self.log("Connection Confirmed.", type="event")
            self._validation_stage = VALIDATION_STAGE_VALIDATED
            self.validate_stop("*")

    def _process_feedback_message(self, response):
        if response.startswith("[MSG:"):
            message = response[5:-1]
            self.log(message, type="event")
            self.service.channel("console")(message)
        elif response.startswith("[GC:"):
            # Parsing $G
            message = response[4:-1]
            states = list(message.split(" "))
            if not self.fully_validated():
                self.log("Stage 4: $G was successfully parsed.", type="event")
                self.driver.declare_modals(states)
                self._validation_stage = VALIDATION_STAGE_MODAL_QUERY
                self.validate_stop("$G")
                self.validate_start("?")
            self.log(message, type="event")
            self.service.signal("grbl:states", states)
        elif response.startswith("[HLP:"):
            # Parsing $
            message = response[5:-1]
            if self._validation_stage == VALIDATION_STAGE_HELP_REQUEST:
                self.log("Stage 2: $ was successfully parsed.", type="event")
                self._validation_stage = VALIDATION_STAGE_SETTINGS_QUERY
                self.validate_stop("$")
                if "$$" in message:
                    self.validate_start("$$")
                if "$G" in message:
                    self.validate_start("$G")
                elif "?" in message:
                    # No $G just request status.
                    self.validate_start("?")
            self.log(message, type="event")
        elif response.startswith("[G54:"):
            message = response[5:-1]
            self.service.signal("grbl:g54", message)
        elif response.startswith("[G55:"):
            message = response[5:-1]
            self.service.signal("grbl:g55", message)
        elif response.startswith("[G56:"):
            message = response[5:-1]
            self.service.signal("grbl:g56", message)
        elif response.startswith("[G57:"):
            message = response[5:-1]
            self.service.signal("grbl:g57", message)
        elif response.startswith("[G58:"):
            message = response[5:-1]
            self.service.signal("grbl:g58", message)
        elif response.startswith("[G59:"):
            message = response[5:-1]
            self.service.signal("grbl:g59", message)
        elif response.startswith("[G28:"):
            message = response[5:-1]
            self.service.signal("grbl:g28", message)
        elif response.startswith("[G30:"):
            message = response[5:-1]
            self.service.signal("grbl:g30", message)
        elif response.startswith("[G92:"):
            message = response[5:-1]
            self.service.signal("grbl:g92", message)
        elif response.startswith("[TLO:"):
            message = response[5:-1]
            self.service.signal("grbl:tlo", message)
        elif response.startswith("[PRB:"):
            message = response[5:-1]
            self.service.signal("grbl:prb", message)
        elif response.startswith("[VER:"):
            message = response[5:-1]
            self.service.signal("grbl:ver", message)
        elif response.startswith("[OPT:"):
            message = response[5:-1]
            opts = list(message.split(","))
            codes = opts[0]
            if len(opts) < 3:
                # If there are not enough options, we assume the defaults.
                opts.extend(["0", "0"])
            block_buffer_size = opts[1]
            rx_buffer_size = opts[2]
            self.log(f"codes: {codes}", type="event")
            if "V" in codes:
                # Variable spindle enabled
                pass
            if "N" in codes:
                # Line numbers enabled
                pass

            if "M" in codes:
                # Mist coolant enabled
                pass
            if "C" in codes:
                # CoreXY enabled
                pass
            if "P" in codes:
                # Parking motion enabled
                pass
            if "Z" in codes:
                # Homing force origin enabled
                pass
            if "H" in codes:
                # Homing single axis enabled
                pass
            if "T" in codes:
                # Two limit switches on axis enabled
                pass
            if "A" in codes:
                # Allow feed rate overrides in probe cycles
                pass
            if "*" in codes:
                # Restore all EEPROM disabled
                pass
            if "$" in codes:
                # Restore EEPROM $ settings disabled
                pass
            if "#" in codes:
                # Restore EEPROM parameter data disabled
                pass
            if "I" in codes:
                # Build info write user string disabled
                pass
            if "E" in codes:
                # Force sync upon EEPROM write disabled
                pass
            if "W" in codes:
                # Force sync upon work coordinate offset change disabled
                pass
            if "L" in codes:
                # Homing init lock sets Grbl into an alarm state upon power up
                pass
            if "2" in codes:
                # Dual axis motors with self-squaring enabled
                pass
            self.log(f"blockBufferSize: {block_buffer_size}", type="event")
            self.log(f"rxBufferSize: {rx_buffer_size}", type="event")
            self.service.signal("grbl:block_buffer", int(block_buffer_size))
            self.service.signal("grbl:rx_buffer", int(rx_buffer_size))
            self.service.signal("grbl:opt", message)
        elif response.startswith("[echo:"):
            message = response[6:-1]
            self.service.channel("console")(message)

    def _process_settings_message(self, response):
        match = SETTINGS_MESSAGE.match(response)
        if match:
            try:
                key = int(match.group(1))
                value = match.group(2)
                try:
                    value = ast.literal_eval(value)
                except SyntaxError:
                    # GRBLHal can have things like "", and "Grbl" and "192.168.1.39" in the settings.
                    pass

                self.service.hardware_config[key] = value
                self.service.signal("grbl:hwsettings", key, value)
            except ValueError:
                pass

    # Variant-specific command handlers

    def grbl_variant_info(self, channel):
        """Command to display detected GRBL variant information."""
        if hasattr(self, "_detected_variant"):
            variant = self._detected_variant
            settings = self._variant_settings

            channel("=== GRBL Variant Information ===")
            channel(f"Detected Variant: {variant.upper()}")

            # Display capabilities
            channel("Capabilities:")
            capabilities = [
                ("Laser Mode", settings.get("supports_laser_mode", False)),
                ("Real-time Commands", settings.get("supports_real_time", False)),
                ("Probing", settings.get("supports_probe", False)),
                ("Enhanced Status", settings.get("supports_enhanced_status", False)),
                ("WiFi Support", settings.get("supports_wifi", False)),
                ("SD Card Support", settings.get("supports_sd_card", False)),
                ("Z-Axis", settings.get("supports_z_axis", False)),
            ]

            for cap_name, supported in capabilities:
                status = "Yes" if supported else "No"
                channel(f"  {cap_name}: {status}")

            channel(f"Max Buffer Size: {settings.get('max_buffer_size', 128)} bytes")
            channel(
                f"Home Commands: {', '.join(settings.get('home_commands', ['$H']))}"
            )

            # Variant-specific recommendations
            self._provide_variant_recommendations(variant, settings, channel)
        else:
            channel("No GRBL variant detected yet. Connect to device first.")

    def _provide_variant_recommendations(self, variant, settings, channel):
        """Provide variant-specific configuration recommendations."""
        channel("=== Configuration Recommendations ===")
        self.log("=== Configuration Recommendations ===", type="event")

        if variant == "grblhal":
            channel("GrblHAL Recommendations:")
            channel(
                "  - Use individual axis homing commands ($HX, $HY, $HZ) for better control"
            )
            channel("  - Enable enhanced status reports for better feedback")
            channel("  - Consider using larger planning buffer (256+ bytes)")

        elif variant == "fluidnc":
            channel("FluidNC Recommendations:")
            channel("  - ESP32-based controller with WiFi capabilities")
            channel("  - May support SD card operations for offline jobs")
            channel("  - Reset after alarms may be required")
            channel("  - Consider using larger buffer sizes (256+ bytes)")

        elif variant == "grbl":
            channel("Standard GRBL Recommendations:")
            channel("  - Classic GRBL with proven stability")
            channel("  - Standard buffer size (128 bytes) is optimal")
            channel("  - Enable laser mode ($32=1) for laser operations")

        elif variant == "grbl_esp32":
            channel("GRBL-ESP32 Recommendations:")
            channel("  - ESP32-based with potential WiFi support")
            channel("  - May need reset after alarm conditions")
            channel("  - Larger buffer sizes supported")

        # Universal recommendations based on capabilities
        if settings.get("supports_laser_mode"):
            channel("  - Ensure laser mode is enabled in firmware settings")

        if not settings.get("supports_probe"):
            channel("  - Probing operations not supported by this variant")

    def grbl_suggest_buffer_size(self, channel):
        """Command to suggest optimal buffer size based on detected variant."""
        if hasattr(self, "_detected_variant"):
            settings = self._variant_settings
            recommended = settings.get("max_buffer_size", 128)
            current = getattr(self.service, "planning_buffer_size", 128)

            channel("=== Buffer Size Recommendation ===")
            channel(f"Detected Variant: {self._detected_variant.upper()}")
            channel(f"Current Buffer Size: {current} bytes")
            channel(f"Recommended Size: {recommended} bytes")

            if current != recommended:
                channel("")
                channel(
                    f">> Recommendation: Update planning buffer to {recommended} bytes"
                )
                channel(
                    "   This can improve performance and reduce communication timeouts"
                )
            else:
                channel("   Current buffer size is optimal for this variant")
        else:
            channel("No GRBL variant detected yet. Connect to device first.")

    # Additional variant-related command handlers

    def grbl_apply_variant(self, channel, variant_name=None):
        """Command handler to manually apply a GRBL variant configuration."""
        if variant_name is None:
            channel("Usage: grbl_apply_variant <variant_name>")
            channel(
                "Available variants: grbl, grblhal, fluidnc, grbl_esp32, grbl_mega, unknown"
            )
            return

        self.apply_manual_variant(variant_name)

    def grbl_variant_commands(self, channel):
        """Command handler to show variant-specific command recommendations."""
        self.get_variant_specific_commands(channel)

    def grbl_list_variants(self, channel):
        """Command handler to list all available GRBL variants and their features."""
        channel("=== Available GRBL Variants ===")

        variants = ["grbl", "grblhal", "fluidnc", "grbl_esp32", "grbl_mega", "unknown"]

        for variant in variants:
            settings = self._get_variant_specific_settings(variant)
            channel(f"  {variant.upper()}:")

            features = []
            if settings["supports_laser_mode"]:
                features.append("Laser Mode")
            if settings["supports_real_time"]:
                features.append("Real-time")
            if settings["supports_probe"]:
                features.append("Probing")
            if settings.get("supports_enhanced_status"):
                features.append("Enhanced Status")
            if settings.get("supports_wifi"):
                features.append("WiFi")
            if settings.get("supports_sd_card"):
                features.append("SD Card")

            channel(f"    Features: {', '.join(features) if features else 'Basic'}")
            channel(f"    Buffer: {settings['max_buffer_size']} bytes")

        channel("")
        channel("Use 'grbl_apply_variant <name>' to manually apply a variant")
        channel("Use 'grbl_variant_commands' to see variant-specific commands")

    def grbl_check_command(self, channel, command=None):
        """Command handler to check if a command is compatible with detected variant."""
        if command is None:
            channel("Usage: grbl_check_command <command>")
            return

        if not hasattr(self, "_detected_variant"):
            channel("No variant detected yet. All commands assumed compatible.")
            return

        is_compatible = self.check_variant_compatibility(command)
        variant = self._detected_variant.upper()

        if is_compatible:
            channel(f"✓ Command '{command}' is compatible with {variant}")
        else:
            channel(f"⚠ Command '{command}' may not be supported by {variant}")

    def grbl_reset_variant(self, channel):
        """Command handler to reset variant detection (force re-detection on next connect)."""
        if hasattr(self, "_detected_variant"):
            old_variant = self._detected_variant
            delattr(self, "_detected_variant")
            delattr(self, "_variant_settings")

            # Reset service properties
            if hasattr(self.service, "_grbl_variant"):
                delattr(self.service, "_grbl_variant")
            if hasattr(self.service, "_grbl_variant_settings"):
                delattr(self.service, "_grbl_variant_settings")

            channel(f"Reset variant detection (was: {old_variant.upper()})")
            channel("Variant will be re-detected on next device connection")
        else:
            channel("No variant currently detected")

    # Hardware Settings Management Commands

    def grbl_list_settings(self, channel):
        """Command handler to list all known GRBL hardware settings."""
        channel("=== Known GRBL Hardware Settings ===")
        channel("")

        # Group settings by category
        categories = {
            "Step Configuration": [0, 1, 2, 3, 4, 29],
            "Input/Output Control": [5, 6, 14, 15, 16, 17, 18, 19],
            "Status Reporting": [10, 11, 12, 13],
            "Limits and Homing": [
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                40,
                43,
                44,
                45,
                46,
                47,
                48,
                49,
            ],
            "Spindle/Laser Control": [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 340],
            "System Behavior": [60, 61, 62, 63, 64, 65],
            "Jogging Control": [50, 51, 52, 53, 54, 55],
            "PID Control": [80, 81, 82, 84, 85, 90, 91, 92],
            "Network/WiFi": [70, 71, 72, 73, 74, 75, 76, 77, 78, 79],
            "Network Interface 0": [300, 301, 302, 303, 304, 305, 306, 307],
            "Network Interface 1": [310, 311, 312, 313, 314, 315, 316, 317],
            "Tool Change": [341, 342, 343, 344],
            "X-Axis": [100, 110, 120, 130],
            "Y-Axis": [101, 111, 121, 131],
            "Z-Axis": [102, 112, 122, 132],
            "A-Axis (4th)": [103, 113, 123, 133],
            "B-Axis (5th)": [104, 114, 124, 134],
            "C-Axis (6th)": [105, 115, 125, 135],
        }

        settings_found = 0

        for category, codes in categories.items():
            found_in_category = False
            category_settings = []

            for code in codes:
                setting = hardware_settings(code)
                if setting:
                    found_in_category = True
                    default, desc, units, value_type, _ = setting
                    category_settings.append(
                        f"  ${code:3d} = {str(default):>8} ({units:<12}) - {desc}"
                    )
                    settings_found += 1

            if found_in_category:
                channel(f"--- {category} ---")
                for setting_line in category_settings:
                    channel(setting_line)
                channel("")

        # Show any additional settings not in categories
        all_categorized = set()
        for codes in categories.values():
            all_categorized.update(codes)

        additional = set(get_all_settings_codes()) - all_categorized
        if additional:
            channel("--- Additional/Variant-Specific Settings ---")
            for code in sorted(additional):
                setting = hardware_settings(code)
                if setting:
                    default, desc, units, value_type, _ = setting
                    channel(f"  ${code:3d} = {str(default):>8} ({units:<12}) - {desc}")
                    settings_found += 1
            channel("")

        channel(
            f"Total: {settings_found} known settings ({len(get_all_settings_codes())} in database)"
        )
        channel(
            "Use 'grbl_setting_info <code>' for detailed information about a specific setting."
        )

        # Show variant information if available
        if hasattr(self, "_detected_variant") and self._detected_variant:
            channel(f"Current variant: {self._detected_variant.upper()}")
            channel(
                "Some settings may be variant-specific and not available on all GRBL controllers."
            )

    def grbl_setting_info(self, channel, code):
        """Command handler to get information about a specific GRBL setting."""
        if code is None:
            channel("Usage: grbl_setting_info <code>")
            channel("Example: grbl_setting_info 32")
            return

        setting = hardware_settings(code)
        if setting is None:
            channel(f"Setting ${code} is not known in the current database.")
            channel("Use 'grbl_add_setting' to add custom setting definitions.")
            return

        default, desc, units, value_type, doc_url = setting

        channel(f"=== GRBL Setting ${code} ===")
        channel(f"Description: {desc}")
        channel(f"Default Value: {default}")
        channel(f"Units: {units}")
        channel(f"Data Type: {value_type.__name__}")
        channel(f"Documentation: {doc_url}")

    def grbl_add_setting(
        self, channel, code, default_value, description, units, value_type, doc_url=None
    ):
        """Command handler to add a custom GRBL setting definition."""
        if None in (code, default_value, description, units, value_type):
            channel(
                "Usage: grbl_add_setting <code> <default_value> <description> <units> <value_type> [doc_url]"
            )
            channel(
                "Example: grbl_add_setting 200 1000 'Custom parameter' 'steps' 'float' 'http://...'"
            )
            return

        # Parse value_type
        if value_type.lower() == "int":
            parsed_type = int
            try:
                parsed_default = int(default_value)
            except ValueError:
                channel(f"Cannot convert default value '{default_value}' to int")
                return
        elif value_type.lower() == "float":
            parsed_type = float
            try:
                parsed_default = float(default_value)
            except ValueError:
                channel(f"Cannot convert default value '{default_value}' to float")
                return
        else:
            channel(f"Invalid value_type '{value_type}'. Must be 'int' or 'float'")
            return

        # Check if setting already exists
        existing = hardware_settings(code)
        if existing:
            channel(f"Setting ${code} already exists: {existing[1]}")
            channel("Continuing will overwrite the existing definition.")

        # Add the setting
        add_hardware_setting(
            code, parsed_default, description, units, parsed_type, doc_url
        )

        channel(f"Added setting ${code}: {description}")
        channel(f"  Default: {parsed_default} ({units})")
        channel(f"  Type: {parsed_type.__name__}")
        if doc_url:
            channel(f"  Documentation: {doc_url}")
