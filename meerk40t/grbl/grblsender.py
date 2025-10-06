import queue
import re
import threading
import time

import serial


class CommandTracker:
    def __init__(self, cmd_id, command, log_responses=True):
        self.cmd_id = cmd_id
        self.command = command
        self.command_size = len(command) + 1  # +1 for newline
        self.responses = []
        self.complete = False
        self.error = False
        self.timeout = 10.0  # Default timeout in seconds
        self.timestamp = time.time()
        self.log_responses = log_responses  # Whether to log responses for this command


class GrblSender:
    """
    GRBL CNC Controller Communication Module

    Provides a robust interface for communicating with GRBL-based CNC controllers
    over serial connections. Features include:
    - Thread-safe command queuing and response handling
    - Automatic buffer management to prevent overflow
    - Connection health monitoring and automatic reconnection
    - Comprehensive status parsing (position, feed rate, spindle speed, etc.)
    - GRBL error code interpretation
    - Command timeout handling
    - Debug logging capabilities

    Example usage:
        # Using a port (GrblSender creates its own connection)
        sender = GrblSender(port="COM3", baudrate=115200, debug=True)
        sender.start()

        # Using an existing serial connection
        import serial
        ser = serial.Serial("COM3", 115200, timeout=0.1)
        sender = GrblSender(serial_connection=ser, debug=True)
        sender.start()

        # Send a command and wait for response
        cmd_id = sender.send_command("$$")  # Get GRBL settings
        time.sleep(2)
        response = sender.get_response(cmd_id)

        sender.stop()
    """

    def __init__(
        self,
        port=None,
        serial_connection=None,
        baudrate=115200,
        status_interval=3.0,
        debug=False,
    ):
        # Validate inputs - must have either port or existing serial connection
        if not port and not serial_connection:
            raise ValueError(
                "Either serial port or existing serial connection must be specified"
            )
        if port and serial_connection:
            raise ValueError("Cannot specify both port and existing serial connection")

        self.owns_serial = port is not None  # Track if we created the serial connection
        self.debug = debug  # Set debug flag early for debug_print calls

        if port:
            # Validate inputs for port mode
            if baudrate not in [9600, 19200, 38400, 57600, 115200, 230400, 250000]:
                raise ValueError(f"Unsupported baudrate: {baudrate}")
            if status_interval < 0:
                raise ValueError("Status interval must be positive")

            try:
                print(f"Trying to open serial port {port} at {baudrate} baud...")
                self.serial = serial.Serial(port, baudrate, timeout=0.1)
            except serial.SerialException as e:
                raise ConnectionError(f"Failed to open serial port {port}: {e}") from e
        else:
            # Use existing serial connection
            self.serial = serial_connection
            # Prepare the existing connection for use
            if self.serial.is_open:
                # Ensure proper timeout for readline operations
                if self.serial.timeout != 0.1:
                    self.serial.timeout = 0.1
                    self.debug_print("Adjusted serial timeout to 0.1s")
                self.serial.reset_input_buffer()  # Clear any buffered input
                self.serial.reset_output_buffer()  # Clear any buffered output
                self.debug_print(
                    "Prepared existing serial connection for GRBL communication"
                )
            else:
                raise ConnectionError("Provided serial connection is not open")

        self.command_queue = queue.PriorityQueue()
        self.response_map = {}
        self.buffer_size = 128  # Default for GRBL 1.1
        self.buffer_remaining = self.buffer_size
        self.status_interval = status_interval
        self.running = False
        self.lock = threading.Lock()
        self.response_lock = threading.Lock()
        self.buffer_lock = threading.Lock()
        self.last_command_id = 0
        self.alarm_state = False
        self.active_cmd_id = None
        self.current_status = None
        self.connection_lost = False
        self.last_status_time = 0
        self.command_timeout = 10.0
        self.last_status_query_time = 0

        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        if self.status_interval > 0:
            self.status_thread = threading.Thread(target=self._status_loop, daemon=True)
        else:
            self.status_thread = None

    def debug_print(self, *args, **kwargs):
        """Print debug messages only if debug mode is enabled."""
        if self.debug:
            print(*args, **kwargs)

    def start(self):
        self.running = True
        self.receiver_thread.start()
        self.sender_thread.start()
        if self.status_thread:
            self.status_thread.start()
        self.debug_print("GRBL sender started.")
        # Send immediate status request to wake up GRBL and get initial status
        self.send_realtime("?")
        time.sleep(0.1)  # Give GRBL time to respond

    def soft_reset(self):
        """Send soft reset command (Ctrl-X) to GRBL controller."""
        self.serial.write(b"\x18")  # Ctrl-X: soft reset
        time.sleep(0.1)  # Give GRBL time to respond
        self.debug_print("Soft reset sent to GRBL")

    def stop(self):
        self.running = False

        # Wait for threads to finish
        if self.sender_thread.is_alive():
            self.sender_thread.join(timeout=2.0)
        if self.receiver_thread.is_alive():
            self.receiver_thread.join(timeout=2.0)
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=2.0)  # Clean up serial connection
        if hasattr(self, "serial") and self.owns_serial and self.serial.is_open:
            self.serial.close()

        # Clear command queue and response map
        with self.response_lock:
            self.response_map.clear()

        # Clear command queue (non-blocking)
        try:
            while True:
                self.command_queue.get_nowait()
        except queue.Empty:
            pass

        self.debug_print("GRBL sender stopped and cleaned up.")

    def send_command(self, command: str, priority=10, timeout=10.0, log_responses=True):
        cmd_id = None
        if priority != 0:
            with self.response_lock:
                cmd_id = self.last_command_id
                self.last_command_id += 1
                tracker = CommandTracker(cmd_id, command, log_responses=log_responses)
                tracker.timeout = timeout
                self.response_map[cmd_id] = tracker

        self.command_queue.put((priority, cmd_id, command))
        return cmd_id

    def send_realtime(self, command: str, log_responses=True):
        return self.send_command(command, priority=0, log_responses=log_responses)

    def get_response(self, cmd_id):
        with self.response_lock:
            tracker = self.response_map.get(cmd_id)
            if tracker and tracker.complete:
                return tracker.responses
        return None

    def get_current_status(self):
        """Get the most recent status information from GRBL."""
        with self.response_lock:
            return self.current_status.copy() if self.current_status else None

    def is_connected(self):
        """Check if the GRBL connection is healthy."""
        if self.connection_lost:
            return False
        # Consider disconnected if no status update for 3x the status interval
        return (time.time() - self.last_status_time) < (self.status_interval * 3)

    def get_connection_stats(self):
        """Get connection statistics and health information."""
        current_time = time.time()
        return {
            "connected": self.is_connected(),
            "connection_lost": self.connection_lost,
            "last_status_time": self.last_status_time,
            "time_since_last_status": current_time - self.last_status_time,
            "status_interval": self.status_interval,
            "serial_open": self.serial.is_open if hasattr(self, "serial") else False,
            "buffer_remaining": self.buffer_remaining,
            "buffer_size": self.buffer_size,
            "active_commands": len(
                [t for t in self.response_map.values() if not t.complete]
            ),
            "completed_commands": len(
                [t for t in self.response_map.values() if t.complete]
            ),
        }

    def flush_pending_commands(self):
        """Flush all pending commands from the queue."""
        flushed_count = 0
        try:
            while True:
                self.command_queue.get_nowait()
                flushed_count += 1
        except queue.Empty:
            pass

        self.debug_print(f"Flushed {flushed_count} pending commands")
        return flushed_count

    def wait_for_all_commands(self, timeout=30.0):
        """Wait for all pending commands to complete or timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.response_lock:
                if all(tracker.complete for tracker in self.response_map.values()):
                    return True
            time.sleep(0.1)
        return False

    def get_error_description(self, error_code):
        """Get human-readable description for GRBL error codes."""
        error_descriptions = {
            1: "G-code words consist of an improper command",
            2: "Numeric value format is not valid or missing an expected value",
            3: "GRBL '$' system command was not recognized or supported",
            4: "Negative value received for an expected positive value",
            5: "Homing cycle is not enabled via settings",
            6: "Minimum step pulse time must be greater than 3usec",
            7: "EEPROM read failed. Reset and restored to default values",
            8: "GRBL '$' command cannot be used unless GRBL is idle",
            9: "G-code locked out during alarm or jog state",
            10: "Soft limits cannot be enabled without homing also enabled",
            11: "Max characters per line exceeded. Line was not processed and executed",
            12: "GRBL '$' setting value exceeds the maximum step rate supported",
            13: "Safety door detected as opened and door state initiated",
            14: "Build info or startup line exceeded EEPROM line length limit",
            15: "Jog target exceeds machine travel. Command ignored",
            16: "Jog command with no '=' or contains prohibited g-code",
            17: "Laser mode requires PWM output",
            20: "Unsupported or invalid g-code command found in block",
            21: "More than one g-code command from same modal group found in block",
            22: "Feed rate has not yet been set or is undefined",
            23: "G-code command in block requires an integer value",
            24: "Two G-code commands that both require the use of the XYZ axis words in the block",
            25: "Repeated G-code word found in block",
            26: "No axis words found in block for G-code command or current modal state",
            27: "No axis word targets found in block",
            28: "Line number value is not within the valid range of 1 - 9,999,999",
            29: "G-code command requires an axis word in the block",
            30: "Line number word missing",
            31: "G59.x work coordinate systems are not supported",
            32: "G53 only allowed with G0 and G1 motion modes",
            33: "Axis words found in block when no command or current modal state uses them",
            34: "G2/G3 arc radius value cannot be zero",
            35: "G2/G3 arc coordinate values are invalid",
            36: "G2/G3 arc coordinates have no solution to target",
            37: "Invalid motion command target",
            38: "Arc radius value is too large for the given coordinates",
            39: "No solution to probe within G38.2/G38.3 search distance",
            40: "G38.2/G38.3 probe target is behind the current position",
        }
        return error_descriptions.get(error_code, f"Unknown error code: {error_code}")

    def _send_loop(self):
        while self.running:
            with self.response_lock:
                alarm_active = self.alarm_state

            if alarm_active:
                time.sleep(0.5)
                continue

            # Skip sending if connection is lost
            if self.connection_lost:
                time.sleep(0.5)
                continue

            try:
                priority, cmd_id, command = self.command_queue.get(timeout=0.1)
                with self.buffer_lock:
                    can_send = (
                        priority == 0 or len(command) + 1 <= self.buffer_remaining
                    )

                if can_send:
                    try:
                        if len(command) == 1:
                            self.serial.write(command.encode())  # Realtime: raw byte
                        else:
                            self.serial.write(
                                (command + "\n").encode()
                            )  # G-code: with newline
                        self.debug_print(f"Sent: {command}")

                        # For realtime commands, don't track buffer or active command
                        if priority != 0 and cmd_id is not None:
                            with self.response_lock:
                                self.active_cmd_id = cmd_id
                            # Decrement buffer space when command is sent
                            with self.buffer_lock:
                                self.buffer_remaining -= len(command) + 1
                                # Ensure buffer doesn't go negative
                                self.buffer_remaining = max(0, self.buffer_remaining)
                    except serial.SerialException as e:
                        self.debug_print(f"Serial write error: {e}")
                        self.connection_lost = True
                        # Put command back in queue for retry
                        self.command_queue.put((priority, cmd_id, command))
                        time.sleep(0.5)
                else:
                    # Put command back in queue if buffer is full
                    self.command_queue.put((priority, cmd_id, command))
                    time.sleep(0.05)
            except queue.Empty:
                continue  # Normal, just no commands to send
            except Exception as e:
                self.debug_print(f"Unexpected send loop error: {e}")
                time.sleep(0.1)

    def _receive_loop(self):
        last_successful_read = time.time()
        connection_timeout = 2.0  # Consider connection lost after 2 seconds of no data

        while self.running:
            try:
                raw = self.serial.readline()
                if not raw:  # Empty read
                    current_time = time.time()
                    if (
                        current_time - last_successful_read > connection_timeout
                        and not self.connection_lost
                    ):
                        self.debug_print(
                            f"No data received for {connection_timeout}s, possible connection issue"
                        )
                        self.connection_lost = True
                        time.sleep(1.0)
                    continue

                line = raw.decode("utf-8", errors="ignore").strip()
                if line:
                    last_successful_read = (
                        time.time()
                    )  # Reset timeout on successful read
                    if self.connection_lost:
                        self.connection_lost = False
                        self.debug_print("GRBL connection restored")
                    self._handle_response(line)

            except serial.SerialException as e:
                self.debug_print(f"Serial read error: {e}")
                self.connection_lost = True
                time.sleep(0.5)
            except UnicodeDecodeError as e:
                self.debug_print(f"Unicode decode error: {e}")
                time.sleep(0.1)
            except Exception as e:
                self.debug_print(f"Unexpected receive error: {e}")
                time.sleep(0.1)

    def _handle_response(self, line):
        # Don't log status updates from periodic queries to reduce noise
        current_time = time.time()
        suppress_status = (
            line.startswith("<") and (current_time - self.last_status_query_time) < 0.1
        )
        if not suppress_status:
            self.debug_print("Received:", line)

        if self._is_welcome_message(line):
            self._handle_welcome(line)
        elif line.startswith("<"):
            self._handle_status(line)
        elif line.startswith("["):
            self._handle_bracketed(line)
        elif line == "ok":
            self._finalize_response(error=False)
            # Buffer space is incremented in _finalize_response
        elif "error" in line.lower():
            # Parse GRBL error codes: "error:X" where X is the error number
            error_match = re.search(r"error:(\d+)", line.lower())
            if error_match:
                error_code = int(error_match.group(1))
                error_desc = self.get_error_description(error_code)
                self.debug_print(f"GRBL Error {error_code}: {error_desc}")
                # Store error information in the response
                with self.response_lock:
                    if self.active_cmd_id is not None:
                        tracker = self.response_map.get(self.active_cmd_id)
                        if tracker:
                            tracker.responses.append(
                                f"ERROR {error_code}: {error_desc}"
                            )
            else:
                self.debug_print(f"Unrecognized error format: {line}")
            self._finalize_response(error=True)
            # Buffer space is incremented in _finalize_response
        elif "ALARM" in line:
            with self.response_lock:
                self.alarm_state = True
        elif self._check_for_reset(line):
            self._handle_reset()
        else:
            self._append_to_response(line)

    def _append_to_response(self, line):
        with self.response_lock:
            if self.active_cmd_id is None:
                self.debug_print("No active command to append to.")
                return
            tracker = self.response_map.get(self.active_cmd_id)
            if tracker and not tracker.complete:
                tracker.responses.append(line)
                self.debug_print(f"Appended to cmd_id={self.active_cmd_id}: {line}")

    def _finalize_response(self, error=False):
        with self.response_lock:
            if self.active_cmd_id is None:
                self.debug_print("No active command to finalize.")
                return
            tracker = self.response_map.get(self.active_cmd_id)
            if tracker and not tracker.complete:
                tracker.complete = True
                tracker.error = error
                self.debug_print(
                    f"Finalized cmd_id={self.active_cmd_id} with {'error' if error else 'ok'}"
                )
                # Increment buffer space when command is acknowledged
                with self.buffer_lock:
                    self.buffer_remaining += tracker.command_size
                    # Ensure we don't exceed buffer size
                    self.buffer_remaining = min(self.buffer_remaining, self.buffer_size)
                # Clear active command
                self.active_cmd_id = None

    def _handle_welcome(self, line):
        self.debug_print("Controller welcome:", line)
        # Optional: self.send_command('$I', priority=5)

    def _is_welcome_message(self, line):
        """Check if a line appears to be a GRBL welcome/version message."""
        if not line:
            return False

        line_lower = line.lower()

        # Check for known GRBL variant prefixes (most reliable)
        known_prefixes = ["grbl", "fluidnc", "grbl-mega", "grblhal"]
        if any(line_lower.startswith(prefix) for prefix in known_prefixes):
            return True

        # Check for version patterns that look like software versions
        # Must contain version-like pattern AND welcome indicators
        import re

        has_version = re.search(r"\b\d+\.\d+", line)  # Contains x.y pattern
        has_welcome_indicator = any(
            indicator in line_lower
            for indicator in ["for help", "ready", "initialized", "started", "version"]
        )

        # Only consider it a welcome if it has both version AND welcome indicators
        # OR if it looks like a software name followed by version
        if has_version and has_welcome_indicator:
            return True

        # Check for software name + version pattern (e.g., "SoftwareName v1.2")
        return bool(re.search(r"\w+\s+v?\d+\.\d+", line))

    def _handle_status(self, line):
        # Parse complete GRBL status message: <State|MPos:X,Y,Z|FS:F,S|WCO:X,Y,Z|...>
        # Extract state first
        state_match = re.search(r"<([^|]+)", line)
        state = state_match.group(1) if state_match else "Unknown"

        # Extract machine position
        mpos_match = re.search(r"MPos:([\d\.\-]+),([\d\.\-]+),([\d\.\-]+)", line)
        mpos = None
        if mpos_match:
            mpos = tuple(map(float, mpos_match.groups()))

        # Extract work position (if available)
        wpos_match = re.search(r"WPos:([\d\.\-]+),([\d\.\-]+),([\d\.\-]+)", line)
        wpos = None
        if wpos_match:
            wpos = tuple(map(float, wpos_match.groups()))

        # Extract feed rate and spindle speed (can appear together or separately)
        feed_rate = spindle_speed = None

        # Check for combined FS format first
        fs_match = re.search(r"FS:(\d+),(\d+)", line)
        if fs_match:
            feed_rate = int(fs_match.group(1))
            spindle_speed = int(fs_match.group(2))
        else:
            # Check for separate F and S formats
            f_match = re.search(r"F:(\d+)", line)
            if f_match:
                feed_rate = int(f_match.group(1))

            s_match = re.search(r"S:(\d+)", line)
            if s_match:
                spindle_speed = int(s_match.group(1))

        # Extract work coordinate offset
        wco_match = re.search(r"WCO:([\d\.\-]+),([\d\.\-]+),([\d\.\-]+)", line)
        wco = None
        if wco_match:
            wco = tuple(map(float, wco_match.groups()))

        # Extract overrides (if available)
        ov_match = re.search(r"Ov:(\d+),(\d+),(\d+)", line)
        overrides = None
        if ov_match:
            overrides = {
                "feed": int(ov_match.group(1)),
                "rapid": int(ov_match.group(2)),
                "spindle": int(ov_match.group(3)),
            }

        # Extract accessories (if available)
        accessories_match = re.search(r"A:([SFM]+)", line)
        accessories = accessories_match.group(1) if accessories_match else None

        # Log the parsed status
        status_info = f"State={state}"
        if mpos:
            status_info += f", MPos={mpos}"
        if wpos:
            status_info += f", WPos={wpos}"
        if wco:
            status_info += f", WCO={wco}"
        if feed_rate is not None:
            status_info += f", Feed={feed_rate}"
        if spindle_speed is not None:
            status_info += f", Spindle={spindle_speed}"
        if overrides:
            status_info += f", Overrides={overrides}"
        if accessories:
            status_info += f", Accessories={accessories}"

        self.debug_print(f"Status: {status_info}")

        # Store current status for external access
        self.current_status = {
            "state": state,
            "mpos": mpos,
            "wpos": wpos,
            "wco": wco,
            "feed_rate": feed_rate,
            "spindle_speed": spindle_speed,
            "overrides": overrides,
            "accessories": accessories,
            "timestamp": time.time(),
        }

        # Update connection health
        self.last_status_time = time.time()
        if self.connection_lost:
            self.connection_lost = False
            self.debug_print("GRBL connection restored")

    def _check_connection_health(self):
        """Check if GRBL connection is still healthy based on status updates."""
        if self.connection_lost:
            # Try to reconnect
            self._attempt_reconnection()
            return

        current_time = time.time()
        time_since_last_status = current_time - self.last_status_time

        # If we haven't received a status update in 5x the status interval, consider connection lost
        connection_timeout = self.status_interval * 5.0

        if time_since_last_status > connection_timeout:
            if not self.connection_lost:
                self.connection_lost = True
                self.debug_print(
                    f"GRBL connection lost - no status update for {time_since_last_status:.1f}s"
                )
                self._attempt_reconnection()

    def _attempt_reconnection(self):
        """Attempt to reconnect to GRBL device."""
        if not self.connection_lost:
            return

        try:
            if not self.serial.is_open:
                self.debug_print("Attempting to reopen serial connection...")
                self.serial.open()

            # Send a simple status request to test connection
            self.serial.write(b"?")
            time.sleep(0.1)

            # Reset connection lost flag - will be set again if status check fails
            self.connection_lost = False
            self.last_status_time = time.time()
            self.debug_print("GRBL reconnection successful")

        except serial.SerialException as e:
            self.debug_print(f"Reconnection failed: {e}")
            # Keep connection_lost = True

    def _handle_bracketed(self, line):
        self.debug_print("Bracketed message:", line)
        m = re.search(r"\[BUFFER:(\d+)\]", line)
        if m:
            new_size = int(m.group(1))
            with self.buffer_lock:
                self.buffer_size = new_size
                self.buffer_remaining = new_size
            self.debug_print(f"Detected buffer size: {new_size}")

    def _check_for_reset(self, response):
        """Check if a response indicates GRBL has been reset/restarted during operation."""
        if not response:
            return False
        # Only check for actual reset messages, not welcome messages
        # Welcome messages are handled separately in _handle_welcome
        reset_keywords = [
            "Initializing",
            "Resetting",
            "Board restarted",
            "Reset to continue",  # GRBL reset message
        ]
        resp = response.lower()
        return any(keyword.lower() in resp for keyword in reset_keywords)

    def _handle_reset(self):
        self.debug_print("Controller reset detected. Clearing queue.")
        with self.lock:
            while not self.command_queue.empty():
                try:
                    self.command_queue.get_nowait()
                except queue.Empty:
                    break
        with self.response_lock:
            self.response_map.clear()
            self.active_cmd_id = None
            self.alarm_state = False
            self.current_status = None

    def _status_loop(self):
        while self.running:
            self.last_status_query_time = time.time()
            self.send_realtime("?", log_responses=False)
            time.sleep(self.status_interval)
            # Check connection health
            self._check_connection_health()
            # Periodic cleanup of old completed commands
            self._cleanup_completed_commands()

    def _cleanup_completed_commands(self, max_age=30.0):
        """Clean up completed commands older than max_age seconds to prevent memory leaks."""
        current_time = time.time()
        with self.response_lock:
            to_remove = [
                cmd_id
                for cmd_id, tracker in self.response_map.items()
                if tracker.complete and (current_time - tracker.timestamp) > max_age
            ]

            for cmd_id in to_remove:
                del self.response_map[cmd_id]
                self.debug_print(f"Cleaned up completed command {cmd_id}")

            # Also check for timed out commands
            timed_out = [
                cmd_id
                for cmd_id, tracker in self.response_map.items()
                if not tracker.complete
                and (current_time - tracker.timestamp) > tracker.timeout
            ]

            for cmd_id in timed_out:
                tracker = self.response_map[cmd_id]
                tracker.complete = True
                tracker.error = True
                tracker.responses.append("TIMEOUT")
                self.debug_print(f"Command {cmd_id} timed out: {tracker.command}")


if __name__ == "__main__":
    import sys

    comport = sys.argv[1] if len(sys.argv) > 1 else "com6"
    try:
        sender = GrblSender(port=comport, baudrate=115200, debug=True)
        sender.start()
    except Exception as e:
        print("Failed to start GRBL sender:", e)
        exit(1)

    time.sleep(4)
    cmd_id = None
    # Send a regular command
    cmd_id = sender.send_command("$$")  # will produce multi-line response

    # Send a realtime command
    sender.send_realtime("~")  # cycle start

    # Wait for response
    time.sleep(2)
    response = sender.get_response(cmd_id)
    if response:
        print("Response to $$:")
        for line in response:
            print("  ", line)
    else:
        print("Still waiting for response...")
        for t in list(sender.response_map.values()):
            print(
                f"{t.cmd_id}.{t.command} {'' if t.complete else '(pending)'} -> {t.responses}"
            )

    sender.stop()
