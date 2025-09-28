"""
GRBL Controller

Tasked with sending data to the different connection.

Validation Stages.
        Stage 0, we are disconnected and invalid.
        Stage 1, we are connected and need to check if we are GRBL send $
        Stage 2, we parsed $ and need to try $$ $G
        Stage 3, we successfully parsed $$
        Stage 4, we successfully parsed $G, send ?
        Stage 5, we successfully parsed ?
"""
import ast
import re
import threading
import time

from meerk40t.kernel import signal_listener

SETTINGS_MESSAGE = re.compile(r"^\$([0-9]+)=(.*)")


def hardware_settings(code):
    """
    Given a $# code returns the parameter and the units.

    @param code: $$ code.
    @return: parameter, units
    """
    if code == 0:
        return (
            10,
            "step pulse time",
            "microseconds",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#0--step-pulse-microseconds",
        )
    if code == 1:
        return (
            25,
            "step idle delay",
            "milliseconds",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#1---step-idle-delay-milliseconds",
        )
    if code == 2:
        return (
            0,
            "step pulse invert",
            "bitmask",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#2--step-port-invert-mask",
        )
    if code == 3:
        return (
            0,
            "step direction invert",
            "bitmask",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#3--direction-port-invert-mask",
        )
    if code == 4:
        return (
            0,
            "invert step enable pin",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#4---step-enable-invert-boolean",
        )
    if code == 5:
        return (
            0,
            "invert limit pins",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#5----limit-pins-invert-boolean",
        )
    if code == 6:
        return (
            0,
            "invert probe pin",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#6----probe-pin-invert-boolean",
        )
    if code == 10:
        return (
            255,
            "status report options",
            "bitmask",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#10---status-report-mask",
        )
    if code == 11:
        return (
            0.010,
            "Junction deviation",
            "mm",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#11---junction-deviation-mm",
        )
    if code == 12:
        return (
            0.002,
            "arc tolerance",
            "mm",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#12--arc-tolerance-mm",
        )
    if code == 13:
        return (
            0,
            "Report in inches",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#13---report-inches-boolean",
        )
    if code == 20:
        return (
            0,
            "Soft limits enabled",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#20---soft-limits-boolean",
        )
    if code == 21:
        return (
            0,
            "hard limits enabled",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#21---hard-limits-boolean",
        )
    if code == 22:
        return (
            0,
            "Homing cycle enable",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#22---homing-cycle-boolean",
        )
    if code == 23:
        return (
            0,
            "Homing direction invert",
            "bitmask",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#23---homing-dir-invert-mask",
        )
    if code == 24:
        return (
            25.000,
            "Homing locate feed rate",
            "mm/min",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#24---homing-feed-mmmin",
        )
    if code == 25:
        return (
            500.000,
            "Homing search seek rate",
            "mm/min",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#25---homing-seek-mmmin",
        )
    if code == 26:
        return (
            250,
            "Homing switch debounce delay",
            "ms",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#26---homing-debounce-milliseconds",
        )
    if code == 27:
        return (
            1.000,
            "Homing switch pull-off distance",
            "mm",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#27---homing-pull-off-mm",
        )
    if code == 30:
        return (
            1000,
            "Maximum spindle speed",
            "RPM",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#30---max-spindle-speed-rpm",
        )
    if code == 31:
        return (
            0,
            "Minimum spindle speed",
            "RPM",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#31---min-spindle-speed-rpm",
        )
    if code == 32:
        return (
            1,
            "Laser mode enable",
            "boolean",
            int,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#32---laser-mode-boolean",
        )
    if code == 100:
        return (
            250.000,
            "X-axis steps per millimeter",
            "steps",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm",
        )
    if code == 101:
        return (
            250.000,
            "Y-axis steps per millimeter",
            "steps",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm",
        )
    if code == 102:
        return (
            250.000,
            "Z-axis steps per millimeter",
            "steps",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm",
        )
    if code == 110:
        return (
            500.000,
            "X-axis max rate",
            "mm/min",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin",
        )
    if code == 111:
        return (
            500.000,
            "Y-axis max rate",
            "mm/min",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin",
        )
    if code == 112:
        return (
            500.000,
            "Z-axis max rate",
            "mm/min",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin",
        )
    if code == 120:
        return (
            10.000,
            "X-axis acceleration",
            "mm/s^2",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2",
        )
    if code == 121:
        return (
            10.000,
            "Y-axis acceleration",
            "mm/s^2",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2",
        )
    if code == 122:
        return (
            10.000,
            "Z-axis acceleration",
            "mm/s^2",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2",
        )
    if code == 130:
        return (
            200.000,
            "X-axis max travel",
            "mm",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm",
        )
    if code == 131:
        return (
            200.000,
            "Y-axis max travel",
            "mm",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm",
        )
    if code == 132:
        return (
            200.000,
            "Z-axis max travel",
            "mm",
            float,
            "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm",
        )


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
        self._validation_stage = 0

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
        self._validation_start_time = None
        self._validation_timeout = 5.0  # 5 seconds timeout per stage

        # Timeout analysis tracking
        self._timeout_history = []  # Track timeout events with details
        self._current_stage_messages = []  # Track messages sent in current stage
        self._stage_start_commands = {}  # Track what command started each stage
        self._welcome_message_history = []  # Track welcome messages for analysis

        # Validation mode selection logic
        self._validation_mode = self._select_validation_mode()
        self._update_validation_timeout()

    def _select_validation_mode(self):
        """
        Select the appropriate validation mode based on device configuration.

        Returns:
            str: Validation mode - 'strict', 'timeout', 'proactive', or 'skip'
        """
        # Mode 1: Skip validation entirely
        if (
            not self.service.require_validator
            and not self.service.boot_connect_sequence
        ):
            return "skip"

        # Mode 2: Strict validation (traditional GRBL approach)
        if self.service.require_validator and self.service.boot_connect_sequence:
            return "strict"

        # Mode 3: Proactive validation (for non-compliant devices)
        if not self.service.require_validator and self.service.boot_connect_sequence:
            return "proactive"

        # Mode 4: Timeout-based validation (fallback)
        return "timeout"

    def get_validation_mode_description(self):
        """
        Get a human-readable description of the current validation mode.

        Returns:
            str: Description of the validation mode
        """
        descriptions = {
            "skip": "Skip Validation - Connection assumed immediately valid",
            "strict": "Strict Validation - Requires welcome message before validation",
            "proactive": "Proactive Validation - Starts validation proactively without waiting",
            "timeout": "Timeout Validation - Strict with timeout fallback mechanisms",
        }
        return descriptions.get(self._validation_mode, "Unknown validation mode")

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
            self._validation_stage = 5

        elif self._validation_mode == "strict":
            # Strict mode - wait for welcome message, then validate
            self.log("Validation Mode: Strict - Awaiting welcome message", type="event")
            # Stage 0: Wait for welcome message (handled in _recving)
            self._validation_stage = 0

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
                self._validation_stage = 5

        elif self._validation_mode == "timeout":
            # Timeout mode - combination of strict with timeout fallback
            self.log("Validation Mode: Timeout - Strict with fallback", type="event")
            if self.service.boot_connect_sequence:
                self._start_validation_sequence("timeout mode")
            else:
                self._validation_stage = 5

    def force_validate_if_needed(self):
        """Force validation to start if we haven't received a welcome message"""
        if self._validation_stage == 0 and self.connection.connected:
            self.log(
                "No welcome message received, forcing validation start", type="event"
            )
            if self.service.boot_connect_sequence:
                self._validation_stage = 1
                self.validate_start("$")
            else:
                self._validation_stage = 5

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
        self._validation_stage = 0

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
            or self._validation_stage == 0
            or self._validation_stage == 5
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
        """Start the validation sequence (stage 1 with $ command)."""
        log_msg = "Starting validation sequence"
        if reason:
            log_msg += f" ({reason})"
        self.log(log_msg, type="event")
        self._validation_stage = 1
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

        # Apply buffer size recommendation
        if hasattr(self.service, "planning_buffer_size"):
            current_buffer = getattr(self.service, "planning_buffer_size", 128)
            recommended_buffer = settings["max_buffer_size"]
            if current_buffer != recommended_buffer:
                self.log(
                    f">> Recommendation: Update planning buffer to {recommended_buffer} bytes",
                    type="event",
                )
                self.log(
                    f"   Current: {current_buffer} bytes | Optimal for {variant}: {recommended_buffer} bytes",
                    type="event",
                )

        # Store variant info for later use
        self._detected_variant = variant
        self._variant_settings = settings

        return settings

    def _log_timeout_analysis(self, timeout_info):
        """Log detailed timeout analysis for debugging and pattern recognition"""
        stage = timeout_info["stage"]
        elapsed = timeout_info["elapsed_time"]
        command = timeout_info["start_command"]
        mode = timeout_info["validation_mode"]

        self.log(f"*** TIMEOUT ANALYSIS - Stage {stage} ***", type="event")
        self.log(
            f"   Mode: {mode} | Command: '{command}' | Elapsed: {elapsed:.2f}s",
            type="event",
        )

        if timeout_info["messages_sent"]:
            self.log("   Messages sent during this stage:", type="event")
            for msg in timeout_info["messages_sent"]:
                delay_info = f" (delayed {msg['delay']}s)" if msg["delay"] > 0 else ""
                self.log(
                    f"     - '{msg['command']}' at {time.strftime('%H:%M:%S', time.localtime(msg['timestamp']))}{delay_info}",
                    type="event",
                )
        else:
            self.log("     - No messages were sent in this stage", type="event")

        # Provide suggestions based on timeout pattern
        self._suggest_timeout_solutions(timeout_info)

    def _suggest_timeout_solutions(self, timeout_info):
        """Suggest solutions based on timeout patterns and device behavior"""
        stage = timeout_info["stage"]
        command = timeout_info["start_command"]
        mode = timeout_info["validation_mode"]

        suggestions = []

        if stage == 1 and command == "$":
            suggestions.extend(
                [
                    "Device may not respond to '$' command (help request)",
                    "Try increasing connect_delay in device settings",
                    "Consider switching to 'proactive' validation mode",
                    "Device may be non-standard GRBL firmware",
                ]
            )
        elif stage == 2 and command in ["$$", "$G"]:
            suggestions.extend(
                [
                    "Device may not support settings query ('$$') or modal state ('$G')",
                    "This could be a minimal GRBL implementation",
                    "Consider adding custom validation pattern for this device type",
                ]
            )
        elif stage == 4 and command == "?":
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
            self.log("   >> Suggested solutions:", type="event")
            for suggestion in suggestions:
                self.log(f"     - {suggestion}", type="event")
        else:
            self.log(
                "   >> No specific suggestions available for this timeout pattern",
                type="event",
            )

        # Log pattern for potential new validation methods
        pattern_id = f"{stage}_{command}_{mode}"
        self.log(
            f"   [PATTERN] {pattern_id} (use for adding new validation methods)",
            type="event",
        )

    def _advance_validation_stage(self):
        """Advance to next validation stage due to timeout or fallback"""
        if self._validation_stage == 1:
            # $ command timed out, try $$ and $G anyway
            self._log_stage_advancement(2, "Advancing without $ confirmation (timeout)")
            self.validate_stop("$")
            self.validate_start("$$")
            self.validate_start("$G")
        elif self._validation_stage == 2:
            # $$ timed out, assume it worked
            self._log_stage_advancement(3, "Assuming $$ worked (timeout)")
            self.validate_stop("$$")
        elif self._validation_stage == 3:
            # $G timed out, try status anyway
            self._log_stage_advancement(
                4, "Advancing without $G confirmation (timeout)"
            )
            self.validate_stop("$G")
            self.validate_start("?")
        elif self._validation_stage == 4:
            # Status timed out, assume we're connected
            self._log_stage_advancement(5, "Connection assumed valid (timeout)")
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
        if self._validation_stage in [1, 2, 3, 4] and not self.fully_validated():
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
                if self._validation_stage == 2:
                    self.log("Stage 3: $$ was successfully parsed.", type="event")
                    self.validate_stop("$$")
                    self._validation_stage = 3
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
                        self._validation_stage = 5
            else:
                # Validation is required. This was stage 0.
                if self.service.boot_connect_sequence:
                    # Boot sequence is required. Start sequence.
                    self._start_validation_sequence("validation required")
                else:
                    # No boot sequence required. Declare fully connected.
                    self._validation_stage = 5

    def fully_validated(self):
        return self._validation_stage == 5

    def force_validate(self):
        self._validation_stage = 5
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

        if stage == "1" and command == "$":
            suggestions.extend(
                [
                    "Add 'no-help' validation mode that skips '$' command entirely",
                    "Implement alternative device detection using different commands",
                ]
            )

        elif stage == "2" and command in ["$$", "$G"]:
            suggestions.append(
                "Create 'minimal-grbl' validation mode for basic implementations"
            )

        elif stage == "4" and command == "?":
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
        if self._validation_stage in (2, 3, 4):
            self.log("Connection Confirmed.", type="event")
            self._validation_stage = 5
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
                self._validation_stage = 4
                self.validate_stop("$G")
                self.validate_start("?")
            self.log(message, type="event")
            self.service.signal("grbl:states", states)
        elif response.startswith("[HLP:"):
            # Parsing $
            message = response[5:-1]
            if self._validation_stage == 1:
                self.log("Stage 2: $ was successfully parsed.", type="event")
                self._validation_stage = 2
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

    def grbl_variant_info(self):
        """Command to display detected GRBL variant information."""
        if hasattr(self, "_detected_variant"):
            variant = self._detected_variant
            settings = self._variant_settings

            self.log("=== GRBL Variant Information ===", type="event")
            self.log(f"Detected Variant: {variant.upper()}", type="event")

            # Display capabilities
            self.log("Capabilities:", type="event")
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
                self.log(f"  {cap_name}: {status}", type="event")

            self.log(
                f"Max Buffer Size: {settings.get('max_buffer_size', 128)} bytes",
                type="event",
            )
            self.log(
                f"Home Commands: {', '.join(settings.get('home_commands', ['$H']))}",
                type="event",
            )

            # Variant-specific recommendations
            self._provide_variant_recommendations(variant, settings)
        else:
            self.log(
                "No GRBL variant detected yet. Connect to device first.", type="event"
            )

    def _provide_variant_recommendations(self, variant, settings):
        """Provide variant-specific configuration recommendations."""
        self.log("", type="event")
        self.log("=== Configuration Recommendations ===", type="event")

        if variant == "grblhal":
            self.log("GrblHAL Recommendations:", type="event")
            self.log(
                "  - Use individual axis homing commands ($HX, $HY, $HZ) for better control",
                type="event",
            )
            self.log(
                "  - Enable enhanced status reports for better feedback", type="event"
            )
            self.log(
                "  - Consider using larger planning buffer (256+ bytes)", type="event"
            )

        elif variant == "fluidnc":
            self.log("FluidNC Recommendations:", type="event")
            self.log("  - ESP32-based controller with WiFi capabilities", type="event")
            self.log(
                "  - May support SD card operations for offline jobs", type="event"
            )
            self.log("  - Reset after alarms may be required", type="event")
            self.log(
                "  - Consider using larger buffer sizes (256+ bytes)", type="event"
            )

        elif variant == "grbl":
            self.log("Standard GRBL Recommendations:", type="event")
            self.log("  - Classic GRBL with proven stability", type="event")
            self.log("  - Standard buffer size (128 bytes) is optimal", type="event")
            self.log("  - Enable laser mode ($32=1) for laser operations", type="event")

        elif variant == "grbl_esp32":
            self.log("GRBL-ESP32 Recommendations:", type="event")
            self.log("  - ESP32-based with potential WiFi support", type="event")
            self.log("  - May need reset after alarm conditions", type="event")
            self.log("  - Larger buffer sizes supported", type="event")

        # Universal recommendations based on capabilities
        if settings.get("supports_laser_mode"):
            self.log(
                "  - Ensure laser mode is enabled in firmware settings", type="event"
            )

        if not settings.get("supports_probe"):
            self.log(
                "  - Probing operations not supported by this variant", type="event"
            )

    def grbl_suggest_buffer_size(self):
        """Command to suggest optimal buffer size based on detected variant."""
        if hasattr(self, "_detected_variant"):
            settings = self._variant_settings
            recommended = settings.get("max_buffer_size", 128)
            current = getattr(self.service, "planning_buffer_size", 128)

            self.log("=== Buffer Size Recommendation ===", type="event")
            self.log(
                f"Detected Variant: {self._detected_variant.upper()}", type="event"
            )
            self.log(f"Current Buffer Size: {current} bytes", type="event")
            self.log(f"Recommended Size: {recommended} bytes", type="event")

            if current != recommended:
                self.log("", type="event")
                self.log(
                    f">> Recommendation: Update planning buffer to {recommended} bytes",
                    type="event",
                )
                self.log(
                    "   This can improve performance and reduce communication timeouts",
                    type="event",
                )
            else:
                self.log(
                    "   Current buffer size is optimal for this variant", type="event"
                )
        else:
            self.log(
                "No GRBL variant detected yet. Connect to device first.", type="event"
            )
