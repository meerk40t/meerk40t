import queue
import re
import threading
import time

import serial


class CommandTracker:
    def __init__(self, cmd_id, command):
        self.cmd_id = cmd_id
        self.command = command
        self.command_size = len(command) + 1  # +1 for newline
        self.responses = []
        self.complete = False
        self.error = False
        self.timestamp = time.time()


class GrblSender:
    def __init__(self, port, baudrate=115200, status_interval=2.0, debug=False):
        self.serial = serial.Serial(port, baudrate, timeout=0.1)
        self.command_queue = queue.PriorityQueue()
        self.response_map = {}
        self.buffer_size = 128  # Default for GRBL 1.1
        self.buffer_remaining = self.buffer_size
        self.status_interval = status_interval
        self.running = False
        self.debug = debug
        self.lock = threading.Lock()
        self.response_lock = threading.Lock()
        self.buffer_lock = threading.Lock()
        self.last_command_id = 0
        self.alarm_state = False
        self.active_cmd_id = None
        self.current_status = None

        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.status_thread = threading.Thread(target=self._status_loop, daemon=True)

    def debug_print(self, *args, **kwargs):
        """Print debug messages only if debug mode is enabled."""
        if self.debug:
            print(*args, **kwargs)

    def start(self):
        self.running = True
        self.receiver_thread.start()
        self.sender_thread.start()
        self.status_thread.start()
        self.debug_print("GRBL sender started.")
        self.serial.write(b"\x18")  # Ctrl-X: soft reset
        time.sleep(0.1)  # Give GRBL time to respond
        self.send_command("$I", priority=5)  # Request version info

    def stop(self):
        self.running = False
        self.serial.close()
        self.debug_print("GRBL sender stopped.")

    def send_command(self, command: str, priority=10):
        cmd_id = None
        if priority != 0:
            with self.response_lock:
                cmd_id = self.last_command_id
                self.last_command_id += 1
                self.response_map[cmd_id] = CommandTracker(cmd_id, command)

        self.command_queue.put((priority, cmd_id, command))
        return cmd_id

    def send_realtime(self, command: str):
        return self.send_command(command, priority=0)

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

    def _send_loop(self):
        while self.running:
            with self.response_lock:
                alarm_active = self.alarm_state

            if alarm_active:
                time.sleep(0.5)
                continue

            try:
                priority, cmd_id, command = self.command_queue.get(timeout=0.1)
                with self.buffer_lock:
                    can_send = (
                        priority == 0 or len(command) + 1 <= self.buffer_remaining
                    )

                if can_send:
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
                else:
                    # Put command back in queue if buffer is full
                    self.command_queue.put((priority, cmd_id, command))
                    time.sleep(0.05)
            except queue.Empty:
                time.sleep(0.05)
            except serial.SerialException as e:
                self.debug_print(f"Serial write error: {e}")
                time.sleep(0.1)

    def _receive_loop(self):
        while self.running:
            try:
                raw = self.serial.readline()
                line = raw.decode("utf-8", errors="ignore").strip()
                if line:
                    self._handle_response(line)
            except Exception as e:
                self.debug_print("Receive error:", e)

    def _handle_response(self, line):
        self.debug_print("Received:", line)

        if line.startswith("Grbl"):
            self._handle_welcome(line)
        elif line.startswith("<"):
            self._handle_status(line)
        elif line.startswith("["):
            self._handle_bracketed(line)
        elif line == "ok":
            self._finalize_response(error=False)
            # Buffer space is incremented in _finalize_response
        elif "error" in line.lower():
            self._finalize_response(error=True)
            # Buffer space is incremented in _finalize_response
        elif "ALARM" in line:
            with self.response_lock:
                self.alarm_state = True
        elif "RESET" in line or "Grbl" in line:
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

    def _handle_bracketed(self, line):
        self.debug_print("Bracketed message:", line)
        m = re.search(r"\[BUFFER:(\d+)\]", line)
        if m:
            new_size = int(m.group(1))
            with self.buffer_lock:
                self.buffer_size = new_size
                self.buffer_remaining = new_size
            self.debug_print(f"Detected buffer size: {new_size}")

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
            self.send_realtime("?")
            time.sleep(self.status_interval)
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
                if not tracker.complete and (current_time - tracker.timestamp) > 10.0
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
        sender = GrblSender(port=comport, baudrate=115200, debug=False)
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
