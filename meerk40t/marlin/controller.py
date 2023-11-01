"""
Marlin Controller

Tasked with sending data to the different connection.
"""
import threading
import time

from meerk40t.kernel import signal_listener


class MarlinController:
    def __init__(self, context):
        self.service = context
        self.connection = None

        self.update_connection()

        self.driver = self.service.driver

        # Welcome message into, indicates the device is initialized.
        self.welcome = self.service.setting(str, "welcome", "Marlin")
        self._requires_validation = self.service.setting(
            bool, "requires_validation", True
        )
        self._connection_validated = not self._requires_validation

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
        return f"MarlinController('{self.service.location()}')"

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
            from meerk40t.marlin.tcp_connection import TCPOutput

            self.connection = TCPOutput(self.service, self)
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
        if type == "send":
            if not hasattr(self, "_marlin_send"):
                self._marlin_send = self.service.channel(
                    f"send-{self.service.label}", pure=True
                )
            self._marlin_send(data)
        elif type == "recv":
            if not hasattr(self, "_marlin_recv"):
                self._marlin_recv = self.service.channel(
                    f"recv-{self.service.label}", pure=True
                )
            self._marlin_recv(data)
        elif type == "event":
            if not hasattr(self, "_marlin_events"):
                self._marlin_events = self.service.channel(f"events-{self.service.label}")
            self._marlin_events(data)

    def open(self):
        """
        Opens the connection calling connection.connect.

        Reads the first line this should be Marlin version and information.
        @return:
        """
        if self.connection.connected:
            return
        self.connection.connect()
        if not self.connection.connected:
            self.log("Could not connect.", type="event")
            return
        self.log("Connecting to Marlin...", type="event")

    def close(self):
        """
        Close the Marlin connection.

        @return:
        """
        if not self.connection.connected:
            return
        self.connection.disconnect()
        self._connection_validated = not self._requires_validation
        self.log("Disconnecting from Marlin...", type="event")

    def write(self, data):
        """
        Write data to the sending queue.

        @param data:
        @return:
        """
        self.start()
        self.service.signal("marlin;write", data)
        with self._sending_lock:
            self._sending_queue.append(data)
        self.service.signal(
            "marlin;buffer", len(self._sending_queue) + len(self._realtime_queue)
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
        self.service.signal("marlin;write", data)
        with self._realtime_lock:
            self._realtime_queue.append(data)
        self.service.signal(
            "marlin;buffer", len(self._sending_queue) + len(self._realtime_queue)
        )
        self._send_resume()

    ####################
    # Control Marlin Sender
    ####################

    def start(self):
        """
        Starts the driver thread.

        @return:
        """
        self.open()
        if self._channel_log not in self._watchers:
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

    def shutdown(self):
        self.is_shutdown = True
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
    # MARLIN SEND ROUTINES
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
        self.service.signal("marlin;buffer", len(self._sending_queue))
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
    # MARLIN RECV ROUTINES
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

        Read and process response from marlin.

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
            self.service.signal("marlin;response", response)
            self.log(response, type="recv")
            if response == "ok":
                # Indicates that the command line received was parsed and executed (or set to be executed).
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
                    "marlin;response", cmd_issued, self._assembled_response
                )
                self._assembled_response = []
                self._send_resume()
                continue
            elif response.startswith("<"):
                self._process_status_message(response)
            elif response.startswith("["):
                self._process_feedback_message(response)
                continue
            elif response.startswith("$"):
                self._process_settings_message(response)
                continue
            elif response.startswith(">"):
                self.log(f"STARTUP: {response}", type="event")
            elif response.startswith(self.welcome):
                self.log("Connection Confirmed.", type="event")
                self._connection_validated = True
            else:
                self._assembled_response.append(response)
        self.service.signal("pipe;running", False)

    def _process_status_message(self, response):
        message = response[1:-1]
        data = list(message.split("|"))
        self.service.signal("marlin:state", data[0])
        for datum in data[1:]:
            # While valid some marlin replies might violate the parsing convention.
            try:
                name, info = datum.split(":")
            except ValueError:
                continue
            if name == "F":
                self.service.signal("marlin:speed", float(info))
            elif name == "S":
                self.service.signal("marlin:power", float(info))
            elif name == "FS":
                f, s = info.split(",")
                self.service.signal("marlin:speed", float(f))
                self.service.signal("marlin:power", float(s))
            # MPos: Coord values. Machine Position.
            # WPos: MPos but with applied work coordinates. Work Position.
            # RX: serial rx buffer count.
            # Buf: plan block buffer count.
            # Ln: line number.
            # Lim: limits states
            # Ctl: control pins and mask (binary).
            self.service.signal(f"marlin:status:{name}", info)

    def _process_feedback_message(self, response):
        if response.startswith("[MSG:"):
            message = response[5:-1]
            self.log(message, type="event")
            self.service.channel("console")(message)
        elif response.startswith("[GC:"):
            message = response[4:-1]
            self.log(message, type="event")
            self.service.signal("marlin:states", list(message.split(" ")))
        elif response.startswith("[HLP:"):
            message = response[5:-1]
            self.log(message, type="event")
        elif response.startswith("[G54:"):
            message = response[5:-1]
            self.service.signal("marlin:g54", message)
        elif response.startswith("[G55:"):
            message = response[5:-1]
            self.service.signal("marlin:g55", message)
        elif response.startswith("[G56:"):
            message = response[5:-1]
            self.service.signal("marlin:g56", message)
        elif response.startswith("[G57:"):
            message = response[5:-1]
            self.service.signal("marlin:g57", message)
        elif response.startswith("[G58:"):
            message = response[5:-1]
            self.service.signal("marlin:g58", message)
        elif response.startswith("[G59:"):
            message = response[5:-1]
            self.service.signal("marlin:g59", message)
        elif response.startswith("[G28:"):
            message = response[5:-1]
            self.service.signal("marlin:g28", message)
        elif response.startswith("[G30:"):
            message = response[5:-1]
            self.service.signal("marlin:g30", message)
        elif response.startswith("[G92:"):
            message = response[5:-1]
            self.service.signal("marlin:g92", message)
        elif response.startswith("[TLO:"):
            message = response[5:-1]
            self.service.signal("marlin:tlo", message)
        elif response.startswith("[PRB:"):
            message = response[5:-1]
            self.service.signal("marlin:prb", message)
        elif response.startswith("[VER:"):
            message = response[5:-1]
            self.service.signal("marlin:ver", message)
        elif response.startswith("[OPT:"):
            message = response[5:-1]
            codes, block_buffer_size, rx_buffer_size = message.split(",")
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
                # Homing init lock sets Marlin into an alarm state upon power up
                pass
            if "2" in codes:
                # Dual axis motors with self-squaring enabled
                pass
            self.log(f"blockBufferSize: {block_buffer_size}", type="event")
            self.log(f"rxBufferSize: {rx_buffer_size}", type="event")
            self.service.signal("marlin:block_buffer", int(block_buffer_size))
            self.service.signal("marlin:rx_buffer", int(rx_buffer_size))
            self.service.signal("marlin:opt", message)
        elif response.startswith("[echo:"):
            message = response[6:-1]
            self.service.channel("console")(message)
