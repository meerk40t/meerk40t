import threading
import time

from ...kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
    Module,
)
from .moshiconstants import swizzle_table

STATUS_OK = 205  # Seen before file send. And after file send.
STATUS_PROCESSING = 207  # PROCESSING


def get_code_string_from_moshicode(code):
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_PROCESSING:
        return "Processing"
    elif code == 0:
        return "USB Failed"
    else:
        return "UNK %02x" % code


class MoshiController(Module):
    def __init__(self, context, name, channel=None, *args, **kwargs):
        Module.__init__(self, context, name, channel)
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self._thread = None
        self._buffer = b""  # Threadsafe buffered commands to be sent to controller.
        self._queue = bytearray()  # Queued additional commands programs.
        self._programs = []  # Programs to execute.

        self.context._buffer_size = 0
        self._queue_lock = threading.Lock()
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.ch341 = self.context.open("module/ch341")
        self.connection = None

        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.abort_waiting = False

        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=20)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

        send = context.channel("%s/send" % name)
        send.watch(self.write)
        send.__len__ = lambda: len(self._buffer)

        control = context.channel("%s/control" % name)
        control.watch(self.control)

    def initialize(self, *args, **kwargs):
        context = self.context

        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)

        context.register("control/Status Update", self.update_status)
        self.reset()

        @self.context.console_command("usb_connect", help="Connect USB")
        def usb_connect(command, channel, _, args=tuple(), **kwargs):
            try:
                self.open()
            except ConnectionRefusedError:
                channel("Connection Refused.")

        @self.context.console_command("usb_disconnect", help="Disconnect USB")
        def usb_disconnect(command, channel, _, args=tuple(), **kwargs):
            if self.connection is not None:
                self.close()
            else:
                channel("Usb is not connected.")

        @self.context.console_command("start", help="Start Pipe to Controller")
        def pipe_start(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_ACTIVE)
            self.start()
            channel("Moshi Channel Started.")

        @self.context.console_command("hold", help="Hold Controller")
        def pipe_pause(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_PAUSE)
            self.pause()
            channel("Moshi Channel Paused.")

        @self.context.console_command("resume", help="Resume Controller")
        def pipe_resume(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_ACTIVE)
            self.start()
            channel("Moshi Channel Resumed.")

        @self.context.console_command("abort", help="Abort Job")
        def pipe_abort(command, channel, _, args=tuple(), **kwargs):
            self.reset()
            channel("Moshi Channel Aborted.")

        def abort_wait():
            self.abort_waiting = True

        context.register("control/Wait Abort", abort_wait)

    def finalize(self, *args, **kwargs):
        if self._thread is not None:
            self.is_shutdown = True

    def viewbuffer(self):
        buffer = "Current Working Buffer: %s\n" % str(self._buffer)
        for p in self._programs:
            buffer += "%s\n" % str(p)
        buffer += "Building Buffer: %s\n" % str(self._queue)
        return buffer

    def __repr__(self):
        return "MoshiController()"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + sum(map(len, self._programs)) + len(self._queue)

    def realtime_read(self):
        """
        The a7xx values used before the AC01 commands. Read preamble.
        :return:
        """
        self.realtime_pipe(swizzle_table[14][0])

    def realtime_prologue(self):
        """
        Before a jump / program / turned on:
        :return:
        """
        self.realtime_pipe(swizzle_table[6][0])

    def realtime_epilogue(self):
        """
        Status 205
        After a jump / program
        Status 207
        Status 205 Done.
        :return:
        """
        self.realtime_pipe(swizzle_table[2][0])

    def realtime_freemotor(self):
        """
        Freemotor command
        :return:
        """
        self.realtime_pipe(swizzle_table[1][0])

    def realtime_laser(self):
        """
        Laser Command Toggle.
        :return:
        """
        self.realtime_pipe(swizzle_table[7][0])

    def realtime_stop(self):
        """
        Stop command (likely same as freemotor):
        :return:
        """
        self.realtime_pipe(swizzle_table[1][0])

    def realtime_pipe(self, data):
        self.connection.write_addr(data)

    def open(self):
        self.pipe_channel("open()")
        if self.connection is None:
            self.connection = self.ch341.connect(
                driver_index=self.context.usb_index,
                chipv=self.context.usb_version,
                bus=self.context.usb_bus,
                address=self.context.usb_address,
                mock=self.context.mock,
            )
            if self.context.mock:
                self.connection.mock_status = 205
                self.connection.mock_finish = 207
        else:
            self.connection.open()
        if self.connection is None:
            raise ConnectionRefusedError

    def close(self):
        self.pipe_channel("close()")
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def control(self, command):
        if command == "execute\n":
            if len(self._queue) == 0:
                return
            self._queue_lock.acquire(True)
            program = self._queue
            self._queue = bytearray()
            self._queue_lock.release()
            self._programs.append(program)
            self.start()
        elif command == "stop\n":
            self.realtime_stop()
        elif command == "unlock\n":
            if self._main_lock.locked():
                return
            else:
                self.realtime_freemotor()

    def write(self, bytes_to_write):
        """
        Writes data to the queue, this will be moved into the buffer by the thread in a threadsafe manner.

        :param bytes_to_write: data to write to the queue.
        :return:
        """
        self.pipe_channel("write(%s)" % str(bytes_to_write))
        self._queue_lock.acquire(True)
        self._queue += bytes_to_write
        self._queue_lock.release()
        self.update_buffer()
        return self

    def start(self):
        """
        Controller state change to Started.
        :return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name="MoshiPipe(%s)" % (self.context._path),
            )
            self.update_state(STATE_INITIALIZE)

    def pause(self):
        """
        Pause simply holds the controller from sending any additional packets.

        If this state change is done from INITIALIZE it will start the processing.
        Otherwise it must be done from ACTIVE or IDLE.
        """
        if self.state == STATE_INITIALIZE:
            self.start()
            self.update_state(STATE_PAUSE)
        if self.state == STATE_ACTIVE or self.state == STATE_IDLE:
            self.update_state(STATE_PAUSE)

    def resume(self):
        """
        Resume can only be called from PAUSE.
        """
        if self.state == STATE_PAUSE:
            self.update_state(STATE_ACTIVE)

    def abort(self):
        self._buffer = b""
        self._queue = bytearray()
        self.context.signal("pipe;buffer", 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)

    def stop(self):
        self.abort()
        self._thread.join()  # Wait until stop completes before continuing.

    def update_state(self, state):
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        if self.context is not None:
            self.context._buffer_size = len(self._buffer)
            self.context.signal("pipe;buffer", self.context._buffer_size)

    def update_packet(self, packet):
        if self.context is not None:
            self.context.signal("pipe;packet_text", packet)
            self.usb_send_channel(packet)

    def _new_program(self):
        if len(self._buffer) == 0:
            if len(self._programs) == 0:
                return  # There is nothing to run.
            self.wait_until_accepting_packets()
            self.realtime_prologue()
            self._buffer = self._programs.pop(0)

    def _send_buffer(self):
        while len(self._buffer) != 0:
            queue_processed = self.process_buffer()
            self.refuse_counts = 0

            if queue_processed:
                # Packet was sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_ACTIVE,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_ACTIVE)
                self.count = 0
            else:
                # No packet could be sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_BUSY,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_IDLE)
                if self.count > 50:
                    self.count = 50
                time.sleep(0.02 * self.count)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1

    def _wait_cycle(self):
        if len(self._buffer) == 0:
            self.realtime_epilogue()
            self.wait_finished()

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """

        with self._main_lock:
            self.count = 0
            self.is_shutdown = False
            stage = 0
            while self.state != STATE_END and self.state != STATE_TERMINATE:
                try:
                    self.open()
                    if self.state == STATE_INITIALIZE:
                        # If we are initialized. Change that to active since we're running.
                        self.update_state(STATE_ACTIVE)
                    if stage == 0:
                        self._new_program()
                        stage = 1
                    if len(self._buffer) == 0:
                        break
                    # We try to process the queue.
                    if stage == 1:
                        self._send_buffer()
                        stage = 2
                    if self.is_shutdown:
                        break
                    if stage == 2:
                        self._wait_cycle()
                        stage = 0
                except ConnectionRefusedError:
                    # The attempt refused the connection.
                    self.refuse_counts += 1
                    time.sleep(3)  # 3 second sleep on failed connection attempt.
                    if self.refuse_counts >= self.max_attempts:
                        # We were refused too many times, kill the thread.
                        self.update_state(STATE_TERMINATE)
                        self.context.signal("pipe;error", self.refuse_counts)
                        break
                    continue
                except ConnectionError:
                    # There was an error with the connection, close it and try again.
                    self.connection_errors += 1
                    time.sleep(0.5)
                    self.close()
                    continue
            self._thread = None
            self.is_shutdown = False
            self.update_state(STATE_END)

    def process_buffer(self):
        """
        :return: queue process success.
        """
        if len(self._buffer) > 0:
            buffer = self._buffer
        else:
            return False

        length = min(32, len(buffer))
        packet = bytes(buffer[:length])

        # Packet is prepared and ready to send. Open Channel.

        self.send_packet(packet)
        self.context.packet_count += 1

        # Packet was processed. Remove that data.
        self._buffer = self._buffer[length:]
        self.update_buffer()
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        self.connection.write(packet)
        self.update_packet(packet)

    def update_status(self):
        if self.connection is None:
            raise ConnectionError
        self._status = self.connection.get_status()
        if self.context is not None:
            self.context.signal(
                "pipe;status",
                self._status,
                get_code_string_from_moshicode(self._status[1]),
            )
            self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != STATE_TERMINATE:
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_OK:
                return
            time.sleep(0.05)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        original_state = self.state
        if self.state != STATE_PAUSE:
            self.pause()

        while True:
            if self.state != STATE_WAIT:
                self.update_state(STATE_WAIT)
            self.update_status()
            status = self._status[1]
            if status == 0:
                self.close()
                self.open()
                continue
            if status == STATUS_OK:
                break
            if self.context is not None:
                self.context.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
            if status == STATUS_PROCESSING:
                time.sleep(0.5)  # Half a second between requests.
        self.update_state(original_state)
