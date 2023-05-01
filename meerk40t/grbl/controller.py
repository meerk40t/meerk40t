"""
GRBL Controller

Tasked with sending data to the different connection.
"""

import threading
import time

from meerk40t.kernel import signal_listener


def grbl_error_code(code):
    long = ""
    short = f"Error #{code}"
    if code == 1:
        long = "GCode Command letter was not found."
    elif code == 2:
        long = "GCode Command value invalid or missing."
    elif code == 3:
        long = "Grbl '$' not recognized or supported."
    elif code == 4:
        long = "Negative value for an expected positive value."
    elif code == 5:
        long = "Homing fail. Homing not enabled in settings."
    elif code == 6:
        long = "Min step pulse must be greater than 3usec."
    elif code == 7:
        long = "EEPROM read failed. Default values used."
    elif code == 8:
        long = "Grbl '$' command Only valid when Idle."
    elif code == 9:
        long = "GCode commands invalid in alarm or jog state."
    elif code == 10:
        long = "Soft limits require homing to be enabled."
    elif code == 11:
        long = "Max characters per line exceeded. Ignored."
    elif code == 12:
        long = "Grbl '$' setting exceeds the maximum step rate."
    elif code == 13:
        long = "Safety door opened and door state initiated."
    elif code == 14:
        long = "Build info or start-up line > EEPROM line length"
    elif code == 15:
        long = "Jog target exceeds machine travel, ignored."
    elif code == 16:
        long = "Jog Cmd missing '=' or has prohibited GCode."
    elif code == 17:
        long = "Laser mode requires PWM output."
    elif code == 20:
        long = "Unsupported or invalid GCode command."
    elif code == 21:
        long = "> 1 GCode command in a modal group in block."
    elif code == 22:
        long = "Feed rate has not yet been set or is undefined."
    elif code == 23:
        long = "GCode command requires an integer value."
    elif code == 24:
        long = "> 1 GCode command using axis words found."
    elif code == 25:
        long = "Repeated GCode word found in block."
    elif code == 26:
        long = "No axis words found in command block."
    elif code == 27:
        long = "Line number value is invalid."
    elif code == 28:
        long = "GCode Cmd missing a required value word."
    elif code == 29:
        long = "G59.x WCS are not supported."
    elif code == 30:
        long = "G53 only valid with G0 and G1 motion modes."
    elif code == 31:
        long = "Unneeded Axis words found in block."
    elif code == 32:
        long = "G2/G3 arcs need >= 1 in-plane axis word."
    elif code == 33:
        long = "Motion command target is invalid."
    elif code == 34:
        long = "Arc radius value is invalid."
    elif code == 35:
        long = "G2/G3 arcs need >= 1 in-plane offset word."
    elif code == 36:
        long = "Unused value words found in block."
    elif code == 37:
        long = "G43.1 offset not assigned to tool length axis."
    elif code == 38:
        long = "Tool number greater than max value."
    else:
        long = f"Unrecodgnised error code #{code}"
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
        self._connection_validated = False
        self.update_connection()

        self.driver = self.service.driver
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

    def __repr__(self):
        return f"GRBLController('{self.service.location()}')"

    def __len__(self):
        return len(self._sending_queue) + len(self._realtime_queue) + len(self._forward_buffer)

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

                self.connection = SerialConnection(self.service)
            except ImportError:
                pass
        elif self.service.permit_tcp and self.service.interface == "tcp":
            from meerk40t.grbl.tcp_connection import TCPOutput

            self.connection = TCPOutput(self.service)
        else:
            # Mock
            from .mock_connection import MockConnection

            self.connection = MockConnection(self.service)

    def add_watcher(self, watcher):
        self._watchers.append(watcher)

    def remove_watcher(self, watcher):
        self._watchers.remove(watcher)

    def log(self, data, type):
        for w in self._watchers:
            w(data, type=type)

    def _channel_log(self, data, type=None):
        if type == "send":
            if not hasattr(self, "_grbl_send"):
                self._grbl_send = self.service.channel(f"send-{self.service.label}", pure=True)
            self._grbl_send(data)
        elif type == "recv":
            if not hasattr(self, "_grbl_recv"):
                self._grbl_recv = self.service.channel(f"recv-{self.service.label}", pure=True)
            self._grbl_recv(data)
        elif type == "event":
            if not hasattr(self, "_grbl_events"):
                self._grbl_events = self.service.channel(f"events-{self.service.label}")
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

    def close(self):
        """
        Close the GRBL connection.

        @return:
        """
        if not self.connection.connected:
            return
        self.connection.disconnect()
        self._connection_validated = False
        self.log("Disconnecting from GRBL...", type="event")

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

        self.add_watcher(self._channel_log)

        if self._sending_thread is None:
            self._sending_thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.service.location()}",
                result=self.stop,
                daemon=True,
            )
        if self._recving_thread is None:
            self._recving_thread = self.service.threaded(
                self._recving,
                thread_name=f"recver-{self.service.location()}",
                result=self._rstop,
                daemon=True,
            )

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
        if "\x18" in line:
            with self._forward_lock:
                self._forward_buffer.clear()
        if line is not None:
            self._send(line)

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
            self.service.signal("pipe;running", False)
            self._loop_cond.wait()
            self.service.signal("pipe;running", True)

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
        self.service.signal("pipe;running", True)
        while self.connection.connected:
            if self._realtime_queue:
                # Send realtime data.
                self._sending_realtime()
                continue
            if self._paused or not self._connection_validated:
                # We are paused. We do not send anything other than realtime commands.
                time.sleep(0.05)
                continue
            if not self._sending_queue:
                # There is nothing to write/realtime
                self._send_halt()
                continue
            buffer = len(self._forward_buffer)
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
        self.service.signal("pipe;running", False)

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
            # reading responses.
            response = None
            while not response:
                try:
                    response = self.connection.read()
                except (ConnectionAbortedError, AttributeError):
                    return
                if not response:
                    time.sleep(0.01)
            self.service.signal("grbl;response", response)
            self.log(response, type="recv")
            if response == "ok":
                try:
                    cmd_issued = self.get_forward_command()
                    cmd_issued = cmd_issued.decode(encoding="latin-1")
                except ValueError as e:
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
                continue
            elif response.startswith("echo:"):
                # Echo asks that this information be displayed.
                self.service.channel("console")(response[5:])
            elif response.startswith("ALARM"):
                try:
                    cmd_issued = self.get_forward_command()
                    cmd_issued = cmd_issued.decode(encoding="latin-1")
                except ValueError as e:
                    cmd_issued = ""
                try:
                    error_num = int(response[6:])
                except ValueError:
                    error_num = -1
                short, long = grbl_alarm_message(error_num)
                alarm_desc = f"#{error_num}, '{cmd_issued}' {short}\n{long}"
                self.service.signal(
                    "warning", f"GRBL: {alarm_desc}", response, 4
                )
                self.log(f"Alarm {alarm_desc}", type="recv")
                self._assembled_response = []
            elif response.startswith("error"):
                try:
                    cmd_issued = self.get_forward_command()
                    cmd_issued = cmd_issued.decode(encoding="latin-1")
                except ValueError as e:
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
            elif response.startswith("Grbl"):
                self.log("Connection Confirmed.", type="event")
                self._connection_validated = True
            else:
                self._assembled_response.append(response)
        self.service.signal("pipe;running", False)
