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
        return 10, "step pulse time", "microseconds", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#0--step-pulse-microseconds"
    if code == 1:
        return 25, "step idle delay", "milliseconds", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#1---step-idle-delay-milliseconds"
    if code == 2:
        return 0, "step pulse invert", "bitmask", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#2--step-port-invert-mask"
    if code == 3:
        return 0, "step direction invert", "bitmask", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#3--direction-port-invert-mask"
    if code == 4:
        return 0, "invert step enable pin", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#4---step-enable-invert-boolean"
    if code == 5:
        return 0, "invert limit pins", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#5----limit-pins-invert-boolean"
    if code == 6:
        return 0, "invert probe pin", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#6----probe-pin-invert-boolean"
    if code == 10:
        return 255, "status report options", "bitmask", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#10---status-report-mask"
    if code == 11:
        return 0.010, "Junction deviation", "mm", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#11---junction-deviation-mm"
    if code == 12:
        return 0.002, "arc tolerance", "mm", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#12--arc-tolerance-mm"
    if code == 13:
        return 0, "Report in inches", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#13---report-inches-boolean"
    if code == 20:
        return 0, "Soft limits enabled", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#20---soft-limits-boolean"
    if code == 21:
        return 0, "hard limits enabled", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#21---hard-limits-boolean"
    if code == 22:
        return 0, "Homing cycle enable", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#22---homing-cycle-boolean"
    if code == 23:
        return 0, "Homing direction invert", "bitmask", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#23---homing-dir-invert-mask"
    if code == 24:
        return 25.000, "Homing locate feed rate", "mm/min", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#24---homing-feed-mmmin"
    if code == 25:
        return 500.000, "Homing search seek rate", "mm/min", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#25---homing-seek-mmmin"
    if code == 26:
        return 250, "Homing switch debounce delay", "ms", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#26---homing-debounce-milliseconds"
    if code == 27:
        return 1.000, "Homing switch pull-off distance", "mm", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#27---homing-pull-off-mm"
    if code == 30:
        return 1000, "Maximum spindle speed", "RPM", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#30---max-spindle-speed-rpm"
    if code == 31:
        return 0, "Minimum spindle speed", "RPM", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#31---min-spindle-speed-rpm"
    if code == 32:
        return 1, "Laser mode enable", "boolean", int, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#32---laser-mode-boolean"
    if code == 100:
        return 250.000, "X-axis steps per millimeter", "steps", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm"
    if code == 101:
        return 250.000, "Y-axis steps per millimeter", "steps", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm"
    if code == 102:
        return 250.000, "Z-axis steps per millimeter", "steps", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#100-101-and-102--xyz-stepsmm"
    if code == 110:
        return 500.000, "X-axis max rate", "mm/min", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin"
    if code == 111:
        return 500.000, "Y-axis max rate", "mm/min", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin"
    if code == 112:
        return 500.000, "Z-axis max rate", "mm/min", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#110-111-and-112--xyz-max-rate-mmmin"
    if code == 120:
        return 10.000, "X-axis acceleration", "mm/s^2", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2"
    if code == 121:
        return 10.000, "Y-axis acceleration", "mm/s^2", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2"
    if code == 122:
        return 10.000, "Z-axis acceleration", "mm/s^2", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#120-121-122--xyz-acceleration-mmsec2"
    if code == 130:
        return 200.000, "X-axis max travel", "mm", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm"
    if code == 131:
        return 200.000, "Y-axis max travel", "mm", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm"
    if code == 132:
        return 200.000, "Z-axis max travel", "mm", float, "https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md#130-131-132--xyz-max-travel-mm"


def grbl_error_code(code):
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
        long = f"Unrecognised error code #{code}"
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
                response = self.service.kernel.prompt(str, "Could not open websocket-connection (websocket installed?)")
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
        if self.service.reset_on_connect:
            self.driver.reset()
        if not self.service.require_validator:
            # We are required to wait for the validation.
            if self.service.boot_connect_sequence:
                self._validation_stage = 1
                self.validate_start("$")
            else:
                self._validation_stage = 5
        if self.service.startup_commands:
            self.log("Queue startup commands", type="event")
            lines = self.service.startup_commands.split("\n")
            line_end = self.service.driver.line_end
            for line in lines:
                if line.startswith("#"):
                    self.log(f"Startup: {line}", type="event")
                else:
                    self.service.driver(f"{line}{line_end}")

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
            self._sending_thread != True and not self._sending_thread.is_alive()
        ):
            self._sending_thread = True  # Avoid race condition.
            self._sending_thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.service.location()}",
                result=self.stop,
                daemon=True,
            )
        if self._recving_thread is None or (
            self._recving_thread != True and not self._recving_thread.is_alive()
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
        if cmd == "$":
            delay = self.service.connect_delay / 1000
        else:
            delay = 0
        name = self.service.safe_label
        if delay:
            self.service(f".timer 1 {delay} .gcode_realtime {cmd}")
            self.service(
                f".timer-{name}{cmd} 1 {delay} .timer-{name}{cmd} 0 1 gcode_realtime {cmd}"
            )
        else:
            self.service(f".gcode_realtime {cmd}")
            self.service(f".timer-{name}{cmd} 0 1 gcode_realtime {cmd}")

    def validate_stop(self, cmd):
        name = self.service.safe_label
        if cmd == "*":
            self.service(f".timer-{name}* -q --off")
            return
        self.service(f".timer-{name}{cmd} -q --off")
        if cmd == "$":
            if len(self._forward_buffer) > 3:
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
            elif response.startswith(self.service.welcome):
                if not self.service.require_validator:
                    # Validation is not required, we reboot.
                    if self.fully_validated():
                        if self.service.boot_connect_sequence:
                            # Boot sequence is required. Restart sequence.
                            self.log(
                                "Device Reset, revalidation required", type="event"
                            )
                            self._validation_stage = 1
                            self.validate_start("$")
                else:
                    # Validation is required. This was stage 0.
                    if self.service.boot_connect_sequence:
                        # Boot sequence is required. Restart sequence.
                        self._validation_stage = 1
                        self.validate_start("$")
                    else:
                        # No boot sequence required. Declare fully connected.
                        self._validation_stage = 5
            else:
                self._assembled_response.append(response)

    def fully_validated(self):
        return self._validation_stage == 5

    def force_validate(self):
        self._validation_stage = 5
        self.validate_stop("*")

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
