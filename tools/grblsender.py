import queue
import re
import threading
import time

import serial


class CommandTracker:
    def __init__(self, cmd_id, command):
        self.cmd_id = cmd_id
        self.command = command
        self.responses = []
        self.complete = False
        self.error = False
        self.timestamp = time.time()


class GrblSender:
    def __init__(self, port, baudrate=115200, status_interval=2.0):
        self.serial = serial.Serial(port, baudrate, timeout=0.1)
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

        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.status_thread = threading.Thread(target=self._status_loop, daemon=True)

    def start(self):
        self.running = True
        self.receiver_thread.start()
        self.sender_thread.start()
        self.status_thread.start()
        print("GRBL sender started.")
        self.serial.write(b"\x18")  # Ctrl-X: soft reset
        time.sleep(0.1)  # Give GRBL time to respond
        self.send_command("$I", priority=5)  # Request version info

    def stop(self):
        self.running = False
        self.serial.close()
        print("GRBL sender stopped.")

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

    def _send_loop(self):
        while self.running:
            if self.alarm_state:
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
                    print(f"Sent: {command}")

                    # For realtime commands, don't track buffer or active command
                    if priority != 0 and cmd_id is not None:
                        with self.response_lock:
                            self.active_cmd_id = cmd_id
                        # Note: Buffer space will be decremented when GRBL acknowledges with "ok"
                else:
                    # Put command back in queue if buffer is full
                    self.command_queue.put((priority, cmd_id, command))
                    time.sleep(0.05)
            except queue.Empty:
                time.sleep(0.05)
            except serial.SerialException as e:
                print(f"Serial write error: {e}")
                time.sleep(0.1)

    def _receive_loop(self):
        while self.running:
            try:
                raw = self.serial.readline()
                line = raw.decode("utf-8", errors="ignore").strip()
                if line:
                    self._handle_response(line)
            except Exception as e:
                print("Receive error:", e)

    def _handle_response(self, line):
        print("Received:", line)

        if line.startswith("Grbl"):
            self._handle_welcome(line)
        elif line.startswith("<"):
            self._handle_status(line)
        elif line.startswith("["):
            self._handle_bracketed(line)
        elif line == "ok":
            self._finalize_response(error=False)
            # Reset buffer when command is acknowledged
            with self.buffer_lock:
                self.buffer_remaining = self.buffer_size
        elif "error" in line.lower():
            self._finalize_response(error=True)
            # Reset buffer on error too
            with self.buffer_lock:
                self.buffer_remaining = self.buffer_size
        elif "ALARM" in line:
            self.alarm_state = True
        elif "RESET" in line or "Grbl" in line:
            self._handle_reset()
        else:
            self._append_to_response(line)

    def _append_to_response(self, line):
        with self.response_lock:
            if self.active_cmd_id is None:
                print("No active command to append to.")
                return
            tracker = self.response_map.get(self.active_cmd_id)
            if tracker and not tracker.complete:
                tracker.responses.append(line)
                print(f"Appended to cmd_id={self.active_cmd_id}: {line}")

    def _finalize_response(self, error=False):
        with self.response_lock:
            if self.active_cmd_id is None:
                print("No active command to finalize.")
                return
            tracker = self.response_map.get(self.active_cmd_id)
            if tracker and not tracker.complete:
                tracker.complete = True
                tracker.error = error
                print(
                    f"Finalized cmd_id={self.active_cmd_id} with {'error' if error else 'ok'}"
                )
                # Clear active command
                self.active_cmd_id = None

    def _handle_welcome(self, line):
        print("Controller welcome:", line)
        # Optional: self.send_command('$I', priority=5)

    def _handle_status(self, line):
        mpos = re.search(r"MPos:([\d\.\-]+),([\d\.\-]+),([\d\.\-]+)", line)
        fs = re.search(r"FS:(\d+),(\d+)", line)
        if mpos and fs:
            pos = tuple(map(float, mpos.groups()))
            feed = int(fs.group(1))
            spindle = int(fs.group(2))
            print(f"Status: Pos={pos}, Feed={feed}, Spindle={spindle}")

    def _handle_bracketed(self, line):
        print("Bracketed message:", line)
        m = re.search(r"\[BUFFER:(\d+)\]", line)
        if m:
            new_size = int(m.group(1))
            with self.buffer_lock:
                self.buffer_size = new_size
                self.buffer_remaining = new_size
            print(f"Detected buffer size: {new_size}")

    def _handle_reset(self):
        print("Controller reset detected. Clearing queue.")
        with self.lock:
            while not self.command_queue.empty():
                try:
                    self.command_queue.get_nowait()
                except queue.Empty:
                    break
        with self.response_lock:
            self.response_map.clear()
        with self.buffer_lock:
            self.buffer_remaining = self.buffer_size
        self.alarm_state = False
        self.active_cmd_id = None

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
                print(f"Cleaned up completed command {cmd_id}")

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
                print(f"Command {cmd_id} timed out: {tracker.command}")


if __name__ == "__main__":
    import sys

    comport = sys.argv[1] if len(sys.argv) > 1 else "com6"
    try:
        sender = GrblSender(port=comport, baudrate=115200)
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
