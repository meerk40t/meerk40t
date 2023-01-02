"""
GRBL Controller

Tasked with sending data to the different connection.
"""

import threading
import time

from .mock_connection import MockConnection
from .serial_connection import SerialConnection


class GrblController:
    def __init__(self, context):
        self.service = context
        self.serial_port = self.service.serial_port
        self.baud_rate = self.service.baud_rate

        self.channel = self.service.channel("grbl_state", buffer_size=20)
        self.send = self.service.channel(f"send-{self.serial_port.lower()}", pure=True)
        self.recv = self.service.channel(f"recv-{self.serial_port.lower()}", pure=True)
        if not self.service.mock:
            self.connection = SerialConnection(self.service)
        else:
            self.connection = MockConnection(self.service)
        self.driver = self.service.driver
        self.sending_thread = None

        self._lock = threading.Condition()
        self._sending_queue = []
        self._realtime_queue = []

        self.commands_in_device_buffer = []
        self.buffered_characters = 0
        self.device_buffer_size = self.service.planning_buffer_size
        self.old_x = 0
        self.old_y = 0
        self.grbl_settings = {
            0: 10,  # step pulse microseconds
            1: 25,  # step idle delay
            2: 0,  # step pulse invert
            3: 0,  # step direction invert
            4: 0,  # invert step enable pin, boolean
            5: 0,  # invert limit pins, boolean
            6: 0,  # invert probe pin
            10: 255,  # status report options
            11: 0.010,  # Junction deviation, mm
            12: 0.002,  # arc tolerance, mm
            13: 0,  # Report in inches
            20: 0,  # Soft limits enabled.
            21: 0,  # hard limits enabled
            22: 0,  # Homing cycle enable
            23: 0,  # Homing direction invert
            24: 25.000,  # Homing locate feed rate, mm/min
            25: 500.000,  # Homing search seek rate, mm/min
            26: 250,  # Homing switch debounce delay, ms
            27: 1.000,  # Homing switch pull-off distance, mm
            30: 1000,  # Maximum spindle speed, RPM
            31: 0,  # Minimum spindle speed, RPM
            32: 1,  # Laser mode enable, boolean
            100: 250.000,  # X-axis steps per millimeter
            101: 250.000,  # Y-axis steps per millimeter
            102: 250.000,  # Z-axis steps per millimeter
            110: 500.000,  # X-axis max rate mm/min
            111: 500.000,  # Y-axis max rate mm/min
            112: 500.000,  # Z-axis max rate mm/min
            120: 10.000,  # X-axis acceleration, mm/s^2
            121: 10.000,  # Y-axis acceleration, mm/s^2
            122: 10.000,  # Z-axis acceleration, mm/s^2
            130: 200.000,  # X-axis max travel mm.
            131: 200.000,  # Y-axis max travel mm
            132: 200.000,  # Z-axis max travel mm.
        }

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
            self.channel("Could not connect.")
            return
        self.channel("Connecting to GRBL...")
        t = time.time()
        while True:
            response = self.connection.read()
            if not response:
                if (time.time() - t) > 5.0:
                    # 5 second timeout.
                    return
                continue
            self.channel(response)
            self.recv(response)
            if "grbl" in response.lower():
                self.channel("GRBL Connection Established.")
                return
            if "marlin" in response.lower():
                self.channel("Marlin Connection Established.")
                return

    def close(self):
        """
        Close the GRBL connection.

        @return:
        """
        if self.connection.connected:
            self.connection.disconnect()

    def write(self, data):
        """
        Write data to the sending queue.

        @param data:
        @return:
        """
        self.start()
        self.service.signal("serial;write", data)
        with self._lock:
            self._sending_queue.append(data)
            self.service.signal(
                "serial;buffer", len(self._sending_queue) + len(self._realtime_queue)
            )
            print("notify")
            self._lock.notify()

    def realtime(self, data):
        """
        Write data to the realtime queue.

        The realtime queue should preemt the regular dataqueue.

        @param data:
        @return:
        """
        self.start()
        self.service.signal("serial;write", data)
        with self._lock:
            self._realtime_queue.append(data)
            if "\x18" in data:
                self._sending_queue.clear()
            self.service.signal(
                "serial;buffer", len(self._sending_queue) + len(self._realtime_queue)
            )
            print("notify")
            self._lock.notify()

    def start(self):
        """
        Starts the driver thread.

        @return:
        """
        self.open()
        if self.sending_thread is None:
            self.sending_thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.serial_port.lower()}",
                result=self.stop,
                daemon=True,
            )

    def stop(self, *args):
        """
        Processes the stopping of the sending queue.

        @param args:
        @return:
        """
        self.sending_thread = None
        self.close()

    def grbl_alarm_message(self, code):
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

    def _recv_response(self):
        """
        Read and process response from grbl.

        @return:
        """
        # reading responses.
        response = None
        while not response:
            response = self.connection.read()
        self.service.signal("serial;response", response)
        if response == "ok":
            try:
                line = self.commands_in_device_buffer.pop(0)
                self.buffered_characters -= len(line)
            except IndexError:
                self.channel(f"Response: {response}, but this was unexpected")
                raise ConnectionAbortedError
            self.channel(f"Response: {response}")
            self.recv(f"{response} / {self.buffered_characters} / {len(self.commands_in_device_buffer)} -- {line}")
            return True
        elif response.startswith("echo:"):
            self.service.channel("console")(response[5:])
        elif response.startswith("ALARM"):
            short, long = self.grbl_alarm_message(response)
            self.service.signal(
                "warning", f"GRBL: #{response} {short}\n{long}", response, 4
            )
        elif response.startswith("error"):
            try:
                error_num = int(response[6:])
            except ValueError:
                error_num = -1
            self.service.signal("grbl;error", error_num, response)
            self.channel(f"ERROR: {response}")
        else:
            self.channel(f"Data: {response}")

    def _sending_realtime(self):
        """
        Send one line of realtime queue.

        @return:
        """
        line = self._realtime_queue[0]
        self.connection.write(line)
        self.send(line)
        self._realtime_queue.pop(0)

    def _sending_single_line(self):
        """
        Send one line of sending queue.

        @return:
        """
        line = self._sending_queue[0]
        self.connection.write(line)
        self.send(line)
        self.commands_in_device_buffer.append(line)
        self.buffered_characters += len(line)
        self.service.signal("serial;buffer", len(self._sending_queue))
        self._sending_queue.pop(0)
        return True

    @property
    def _length_of_next_line(self):
        """
        Lookahead and provide length of the next line.
        @return:
        """
        if not self._sending_queue:
            return 0
        return len(self._sending_queue[0])

    def _sending_buffered(self):
        """
        Buffered connection sends as much data as fits in the planning buffer. Then it waits
        and for each ok, it reduces the expected size of the plannning buffer and sends the next
        line of data, only when there's enough room to hold that data.

        @return:
        """
        while self._realtime_queue:
            self._sending_realtime()

        if self._sending_queue and self.device_buffer_size > (
            self.buffered_characters + self._length_of_next_line
        ):
            # There is a line and there is enough buffer to send this line.
            self._sending_single_line()
        else:
            if self.commands_in_device_buffer:
                self._recv_response()

    def _sending_sync(self):
        """
        Synchronous mode sends 1 line and waits to receive 1 "ok" from the laser

        @return:
        """
        while self._realtime_queue:
            self._sending_realtime()

        # Send 1, recv 1.
        if self._sending_queue:
            self._sending_single_line()
            self._recv_response()

    def _sending(self):
        """
        Generic sender, delegate the function according to the desired mode.
        @return:
        """
        while self.connection.connected:
            self.service.signal("pipe;running", True)
            if not self._sending_queue and not self._realtime_queue and not self.commands_in_device_buffer:
                # There is nothing to write, or read
                self.service.signal("pipe;running", False)
                with self._lock:
                    print("wait")
                    # We wait until new data is put in the buffer.
                    self._lock.wait()
                self.service.signal("pipe;running", True)
            if self.service.buffer_mode == "sync":
                self._sending_sync()
            else:
                self._sending_buffered()
        self.service.signal("pipe;running", False)

    def __repr__(self):
        return f"GRBLSerial('{self.service.serial_port}:{str(self.service.serial_baud_rate)}')"

    def __len__(self):
        return len(self._sending_queue) + len(self._realtime_queue)
