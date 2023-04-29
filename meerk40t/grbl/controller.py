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

        # Channels.
        self.grbl_events = self.service.channel("grbl_state", buffer_size=20)
        self.grbl_send = self.service.channel(
            f"send-{self.service.location()}", pure=True
        )
        self.grbl_recv = self.service.channel(
            f"recv-{self.service.location()}", pure=True
        )

        # Sending variables.
        self._sending_thread = None

        self._sending_lock = threading.Lock()
        self._realtime_lock = threading.Lock()
        self._loop_cond = threading.Condition()
        self._sending_queue = []
        self._realtime_queue = []
        # buffer for feedback...
        self._assembled_response = []
        self._forward_buffer = bytearray()
        self._commands_in_device_buffer = []
        self._device_buffer_size = self.service.planning_buffer_size
        self._buffer_fail = 0

        self._paused = False

    def __repr__(self):
        return f"GRBLController('{self.service.location()}')"

    def __len__(self):
        return len(self._sending_queue) + len(self._realtime_queue)

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
        r = self._forward_buffer.index(b"\r")
        n = self._forward_buffer.index(b"\n")
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
            self.grbl_events("Could not connect.")
            return
        self.grbl_events("Connecting to GRBL...")
        t = time.time()
        while True:
            response = self.connection.read()
            if not response:
                if (time.time() - t) > 5.0:
                    # 5 second timeout.
                    return
                continue
            self.grbl_events(response)
            self.grbl_recv(response)
            if "grbl" in response.lower():
                self.grbl_events("GRBL Connection Established.")
                return
            if "marlin" in response.lower():
                self.grbl_events("Marlin Connection Established.")
                return

    def close(self):
        """
        Close the GRBL connection.

        @return:
        """
        if not self.connection.connected:
            return
        self.connection.disconnect()
        self.grbl_events("Disconnecting from GRBL...")

    def write(self, data):
        """
        Write data to the sending queue.

        @param data:
        @return:
        """
        self.start()
        self.service.signal("serial;write", data)
        with self._sending_lock:
            self._sending_queue.append(data)
        self.service.signal(
            "serial;buffer", len(self._sending_queue) + len(self._realtime_queue)
        )
        with self._loop_cond:
            self._loop_cond.notify()

    def realtime(self, data):
        """
        Write data to the realtime queue.

        The realtime queue should preemt the regular dataqueue.

        @param data:
        @return:
        """
        self.start()
        self.service.signal("serial;write", data)
        with self._realtime_lock:
            self._realtime_queue.append(data)
        if "\x18" in data:
            with self._sending_lock:
                self._sending_queue.clear()
        self.service.signal(
            "serial;buffer", len(self._sending_queue) + len(self._realtime_queue)
        )
        with self._loop_cond:
            self._loop_cond.notify()

    ####################
    # Control GRBL Sender
    ####################

    def start(self):
        """
        Starts the driver thread.

        @return:
        """
        self.open()
        if self._sending_thread is None:
            self._sending_thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.service.location()}",
                result=self.stop,
                daemon=True,
            )

    def stop(self, *args):
        """
        Processes the stopping of the sending queue.

        @param args:
        @return:
        """
        self._sending_thread = None
        self.close()
        with self._loop_cond:
            self._loop_cond.notify()

    ####################
    # GRBL SEND ROUTINES
    ####################

    def _send(self, line):
        """
        Write the line to the connection, announce it to the send channel, and add it to the forward buffer.

        @param line:
        @return:
        """
        self.connection.write(line)
        self.grbl_send(line)
        self._forward_buffer += line

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
        # print(f"Response: '{response}'")
        if response == "ok":
            q = self._index_of_forward_line
            if q == -1:
                # We got an ok. But, had not sent anything.
                self.grbl_events(f"Response: {response}, but this was unexpected")
                self._assembled_response = []
                raise ConnectionAbortedError
            cmd_issued = self._forward_buffer[:q]
            self._forward_buffer = self._forward_buffer[q:]

            self.grbl_events(f"Response: {response}")
            self.grbl_recv(
                f"{response} / {len(self._forward_buffer)} -- {cmd_issued}"
            )
            self.service.signal("grbl;response", cmd_issued, self._assembled_response)
            self._assembled_response = []
            return True
        elif response.startswith("echo:"):
            # Echo asks that this information be displayed.
            self.service.channel("console")(response[5:])
        elif response.startswith("ALARM"):
            try:
                error_num = int(response[6:])
            except ValueError:
                error_num = -1
            short, long = grbl_alarm_message(error_num)
            self.service.signal(
                "warning", f"GRBL: Alarm #{error_num} {short}\n{long}", response, 4
            )
            self.grbl_recv(f"Alarm #{error_num} {short}\n{long}")
            self.grbl_events(f"Alarm #{error_num} {short}\n{long}")
            self._assembled_response = []
        elif response.startswith("error"):
            try:
                error_num = int(response[6:])
            except ValueError:
                error_num = -1
            short, long = grbl_error_code(error_num)
            self.service.signal("grbl;error", f"GRBL: {short}\n{long}", response, 4)
            self.grbl_recv(f"ERROR #{error_num} {short}\n{long}")
            self.grbl_events(f"ERROR #{error_num} {short}\n{long}")
            self._assembled_response = []
        else:
            self.grbl_recv(f"{response}")
            self.grbl_events(f"Data: {response}")
            self._assembled_response.append(response)

    def _sending_realtime(self):
        """
        Send one line of realtime queue.

        @return:
        """
        with self._realtime_lock:
            line = self._realtime_queue.pop(0)
        if "~" in line:
            self._paused = True
        if "!" in line:
            self._paused = False
        if line is not None:
            self._send(line)

    def _sending_single_line(self):
        """
        Send one line of sending queue.

        @return:
        """
        with self._sending_lock:
            line = self._sending_queue.pop(0)
        if line is not None:
            self._commands_in_device_buffer.append(line)
        self._send(line)
        self.service.signal("serial;buffer", len(self._sending_queue))
        return True

    def _sending_buffered(self):
        """
        Buffered connection sends as much data as fits in the planning buffer. Then it waits
        and for each ok, it reduces the expected size of the planning buffer and sends the next
        line of data, only when there's enough room to hold that data.

        @return:
        """
        if self._sending_queue and self._device_buffer_size > (
            len(self._forward_buffer) + self._length_of_next_line
        ):
            # There is a line and there is enough buffer to send this line.
            self._sending_single_line()
            self._buffer_fail = 0
        else:
            # We cannot write any lines because they won't fit (start read buffer).
            if self._forward_buffer:
                self._recv_response()
            else:
                # There is no forward buffer. This is an error state.
                self._buffer_fail += 1
                if self._buffer_fail > 10:
                    pass
                    # we should do something like raising an error... for tat to decide

    def _sending_sync(self):
        """
        Synchronous mode sends 1 line and waits to receive 1 "ok" from the laser

        @return:
        """
        # Send 1, recv 1.
        if self._sending_queue:
            self._sending_single_line()
            while self._forward_buffer:
                self._recv_response()

    def _sending(self):
        """
        Generic sender, delegate the function according to the desired mode.

        This function is only run with the self.sending_thread
        @return:
        """
        while self.connection.connected:
            self.service.signal("pipe;running", True)
            if not self._sending_queue and not self._forward_buffer and not self._realtime_queue:
                # There is nothing to write, or read, realtime
                self.service.signal("pipe;running", False)
                with self._loop_cond:
                    # We wait until new data is put in the buffer.
                    self._loop_cond.wait()
                continue
            if self._realtime_queue:
                # Send realtime data.
                self._sending_realtime()
                continue
            if self._paused:
                # We are paused. We do not send anything other than realtime commands.
                continue
            if self.service.buffer_mode == "sync":
                self._sending_sync()
            else:
                self._sending_buffered()
        self.service.signal("pipe;running", False)
