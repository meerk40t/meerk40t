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


class GrblSender:
    def __init__(self, port, baudrate=115200, status_interval=2.0):
        self.serial = serial.Serial(port, baudrate, timeout=0.1)
        self.command_queue = queue.PriorityQueue()
        self.response_map = {}
        self.buffer_size = 128
        self.buffer_remaining = self.buffer_size
        self.status_interval = status_interval
        self.running = False
        self.lock = threading.Lock()
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

    def stop(self):
        self.running = False
        self.serial.close()
        print("GRBL sender stopped.")

    def send_command(self, command: str, priority=10):
        cmd_id = self.last_command_id
        self.last_command_id += 1
        self.command_queue.put((priority, cmd_id, command))
        self.response_map[cmd_id] = CommandTracker(cmd_id, command)
        return cmd_id

    def send_realtime(self, command: str):
        return self.send_command(command, priority=0)

    def get_response(self, cmd_id):
        tracker = self.response_map.get(cmd_id)
        if tracker:
            print(
                f"Tracker for cmd_id={cmd_id}: complete={tracker.complete}, error={tracker.error}, lines={len(tracker.responses)}"
            )
            if tracker.complete:
                return tracker.responses
        else:
            print(f"No tracker found for cmd_id={cmd_id}")
        return None

    def _send_loop(self):
        while self.running:
            if self.alarm_state:
                time.sleep(0.5)
                continue

            try:
                priority, cmd_id, command = self.command_queue.get(timeout=0.1)
                if priority == 0 or len(command) + 1 <= self.buffer_remaining:
                    self.serial.write((command + "\n").encode())
                    self.serial.flush()
                    print(f"Sent: {command}")
                    if priority != 0:
                        self.buffer_remaining -= len(command) + 1
                        self.active_cmd_id = cmd_id
                else:
                    self.command_queue.put((priority, cmd_id, command))
                    time.sleep(0.05)
            except queue.Empty:
                time.sleep(0.05)

    def _receive_loop(self):
        while self.running:
            try:
                raw = self.serial.readline()
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                self._handle_response(line)
            except Exception as e:
                print("Receive error:", e)

    def _handle_response(self, line):
        print("Received:", line)

        if line.startswith("Grbl"):
            self._handle_welcome(line)
        elif line.startswith("<"):
            self._handle_status(line)
        elif line == "ok":
            self._finalize_response(error=False)
            self.buffer_remaining = self.buffer_size
        elif "error" in line.lower():
            self._finalize_response(error=True)
        elif "ALARM" in line:
            self.alarm_state = True
        elif "RESET" in line or "Grbl" in line:
            self._handle_reset()
        else:
            self._append_to_response(line)

    def _append_to_response(self, line):
        if self.active_cmd_id is None:
            print("No active command to append to.")
            return
        tracker = self.response_map.get(self.active_cmd_id)
        if tracker and not tracker.complete:
            tracker.responses.append(line)
            print(f"Appended to cmd_id={self.active_cmd_id}: {line}")

    def _finalize_response(self, error=False):
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
            self.active_cmd_id = None

    def _handle_welcome(self, line):
        print("Controller welcome:", line)
        self.send_command("$I", priority=5)

    def _handle_status(self, line):
        mpos = re.search(r"MPos:([\d\.\-]+),([\d\.\-]+),([\d\.\-]+)", line)
        fs = re.search(r"FS:(\d+),(\d+)", line)
        if mpos and fs:
            pos = tuple(map(float, mpos.groups()))
            feed = int(fs.group(1))
            spindle = int(fs.group(2))
            print(f"Status: Pos={pos}, Feed={feed}, Spindle={spindle}")

    def _handle_reset(self):
        print("Controller reset detected. Clearing queue.")
        with self.lock:
            while not self.command_queue.empty():
                self.command_queue.get()
            self.response_map.clear()
            self.buffer_remaining = self.buffer_size
            self.alarm_state = False
            self.active_cmd_id = None

    def _status_loop(self):
        while self.running:
            self.send_realtime("?")
            time.sleep(self.status_interval)


if __name__ == "__main__":
    sender = GrblSender(port="com6", baudrate=115200)
    sender.start()

    time.sleep(4)
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
                f"{t.cmd_id}.{t.command} {'(pending)' if not t.complete else ''} -> {t.responses}"
            )

    sender.stop()
