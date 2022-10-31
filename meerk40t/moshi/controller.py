import threading
import time

from meerk40t.kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
)

from .builder import (
    MOSHI_EPILOGUE,
    MOSHI_ESTOP,
    MOSHI_FREEMOTOR,
    MOSHI_LASER,
    MOSHI_PROLOGUE,
    MOSHI_READ,
    swizzle_table,
)

STATUS_OK = 205  # Seen before file send. And after file send.
STATUS_PROCESSING = 207  # PROCESSING
STATUS_ERROR = 237  # ERROR
STATUS_RESET = 239  # Seen during reset


def get_code_string_from_moshicode(code):
    """
    Moshiboard CH341 codes into code strings.
    """
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_PROCESSING:
        return "Processing"
    elif code == STATUS_ERROR:
        return "Error"
    elif code == STATUS_RESET:
        return "Resetting"
    elif code == 0:
        return "USB Failed"
    else:
        return f"UNK {code:02x}"


class MoshiController:
    """
    The Moshiboard Controller takes data programs built by the MoshiDriver and sends to the Moshiboard
    according to established moshi protocols.

    The output device is concerned with sending the moshibuilder.data to the control board and control events and
    to the CH341 chip on the Moshiboard. We use the same ch341 driver as the Lihuiyu boards. Giving us
    access to both libusb drivers and windll drivers.

    The protocol for sending rasters is as follows:
    Check processing-state of board, seeking 205
    Send Preamble.
    Check processing-state of board, seeking 205
    Send bulk data of moshibuilder. No checks between packets.
    Send Epilogue.
    While Check processing-state is 207:
        wait 0.2 seconds
    Send Preamble
    Send 0,0 offset 0,0 move.
    Send Epilogue

    Checks done before the Epilogue will have 205 state.
    """

    def __init__(self, context, channel=None, *args, **kwargs):
        self.context = context
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self._thread = None
        self._buffer = (
            bytearray()
        )  # Threadsafe buffered commands to be sent to controller.

        self._programs = []  # Programs to execute.

        self.context._buffer_size = 0
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self._connection = None

        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.abort_waiting = False

        name = self.context.label
        self.pipe_channel = context.channel(f"{name}/events")
        self.usb_log = context.channel(f"{name}/usb", buffer_size=500)
        self.usb_send_channel = context.channel(f"{name}/usb_send")
        self.recv_channel = context.channel(f"{name}/recv")

        self.ch341 = context.open("module/ch341", log=self.usb_log)

        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

    def viewbuffer(self):
        """
        Viewbuffer is used by the BufferView class if such a value exists it provides a view of the
        buffered data. Without this class the BufferView displays nothing. This is optional for any output
        device.
        """
        buffer = f"Current Working Buffer: {str(self._buffer)}\n"
        for p in self._programs:
            buffer += f"{str(p.data)}\n"
        return buffer

    def added(self, *args, **kwargs):
        self.start()

    def shutdown(self, *args, **kwargs):
        if self._thread is not None:
            self.is_shutdown = True

    def __repr__(self):
        return "MoshiController()"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + sum(map(len, self._programs))

    def realtime_read(self):
        """
        The `a7xx` values used before the AC01 commands. Read preamble.

        Also seen randomly 3.2 seconds apart. Maybe keep-alive.
        @return:
        """
        self.pipe_channel("Realtime: Read...")
        self.realtime_pipe(swizzle_table[MOSHI_READ][0])

    def realtime_prologue(self):
        """
        Before a jump / program / turned on:
        @return:
        """
        self.pipe_channel("Realtime: Prologue")
        self.realtime_pipe(swizzle_table[MOSHI_PROLOGUE][0])

    def realtime_epilogue(self):
        """
        Status 205
        After a jump / program
        Status 207
        Status 205 Done.
        @return:
        """
        self.pipe_channel("Realtime: Epilogue")
        self.realtime_pipe(swizzle_table[MOSHI_EPILOGUE][0])

    def realtime_freemotor(self):
        """
        Freemotor command
        @return:
        """
        self.pipe_channel("Realtime: FreeMotor")
        self.realtime_pipe(swizzle_table[MOSHI_FREEMOTOR][0])

    def realtime_laser(self):
        """
        Laser Command Toggle.
        @return:
        """
        self.pipe_channel("Realtime: Laser Active")
        self.realtime_pipe(swizzle_table[MOSHI_LASER][0])

    def realtime_stop(self):
        """
        Stop command (likely same as freemotor):
        @return:
        """
        self.pipe_channel("Realtime: Stop")
        self.realtime_pipe(swizzle_table[MOSHI_ESTOP][0])

    def realtime_pipe(self, data):
        if self._connection is not None:
            try:
                self._connection.write_addr(data)
            except ConnectionError:
                self.pipe_channel("Connection error")
        else:
            self.pipe_channel("Not connected")

    def open(self):
        self.pipe_channel("open()")
        if self._connection is None:
            connection = self.ch341.connect(
                driver_index=self.context.usb_index,
                chipv=self.context.usb_version,
                bus=self.context.usb_bus,
                address=self.context.usb_address,
                mock=self.context.mock,
            )
            self._connection = connection
            if self._connection is None:
                raise ConnectionRefusedError(
                    "ch341 connect did not return a connection."
                )
            if self.context.mock:
                self._connection.mock_status = 205
                self._connection.mock_finish = 207
        else:
            self._connection.open()

    def close(self):
        self.pipe_channel("close()")
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        else:
            raise ConnectionError

    def push_program(self, program):
        self.pipe_channel(f"Pushed: {str(program.data)}")
        self._programs.append(program)
        self.start()

    def unlock_rail(self):
        self.pipe_channel("Control Request: Unlock")
        if self._main_lock.locked():
            return
        else:
            self.realtime_freemotor()

    def start(self):
        """
        Controller state change to `Started`.
        @return:
        """
        if self._thread is None or not self._thread.is_alive():
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name=f"MoshiPipe({self.context.path})",
                result=self.stop,
            )
            self.update_state(STATE_INITIALIZE)

    def pause(self):
        """
        Pause simply holds the controller from sending any additional packets.

        If this state change is done from INITIALIZE it will start the processing.
        Otherwise, it must be done from ACTIVE or IDLE.
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

    def estop(self):
        """
        Abort the current buffer and data queue.
        """
        self._buffer = bytearray()
        self._programs.clear()
        self.context.signal("pipe;buffer", 0)
        self.realtime_stop()
        self.update_state(STATE_TERMINATE)
        self.pipe_channel("Control Request: Stop")

    def stop(self, *args):
        """
        Start the shutdown of the local send thread.
        """
        if self._thread is not None:
            try:
                self._thread.join()  # Wait until stop completes before continuing.
            except RuntimeError:
                pass  # Thread is current thread.
        self._thread = None

    def update_state(self, state):
        """
        Update the local state for the output device
        """
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        """
        Notify listening processes that the buffer size of this output has changed.
        """
        if self.context is not None:
            self.context._buffer_size = len(self._buffer)
            self.context.signal("pipe;buffer", self.context._buffer_size)

    def update_packet(self, packet):
        """
        Notify listening processes that the last sent packet has changed.
        """
        if self.context is not None:
            self.context.signal("pipe;packet_text", packet)
            self.usb_send_channel(packet)

    def _send_buffer(self):
        """
        Send the current Moshiboard buffer
        """
        self.pipe_channel("Sending Buffer...")
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
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_IDLE)
                if self.count > 50:
                    self.count = 50
                time.sleep(0.02 * self.count)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self.pipe_channel(f"Send Thread Start... {len(self._programs)}")
        self._main_lock.acquire(True)
        self.count = 0
        self.is_shutdown = False

        while True:
            self.pipe_channel("While Loop")
            try:
                if self.state == STATE_INITIALIZE:
                    # If we are initialized. Change that to active since we're running.
                    self.update_state(STATE_ACTIVE)
                if self.is_shutdown:
                    break
                if len(self._buffer) == 0 and len(self._programs) == 0:
                    self.pipe_channel("Nothing to process")
                    break  # There is nothing to run.
                if self._connection is None:
                    self.open()
                # Stage 0: New Program send.
                if len(self._buffer) == 0:
                    self.context.signal("pipe;running", True)
                    self.pipe_channel("New Program")
                    self.wait_until_accepting_packets()
                    self.realtime_prologue()
                    self._buffer = self._programs.pop(0).data
                    assert len(self._buffer) != 0

                # Stage 1: Send Program.
                self.context.signal("pipe;running", True)
                self.pipe_channel(f"Sending Data... {len(self._buffer)} bytes")
                self._send_buffer()
                self.update_status()
                self.realtime_epilogue()
                if self.is_shutdown:
                    break

                # Stage 2: Wait for Program to Finish.
                self.pipe_channel("Waiting for finish processing.")
                if len(self._buffer) == 0:
                    self.wait_finished()
                self.context.signal("pipe;running", False)

            except ConnectionRefusedError:
                if self.is_shutdown:
                    break
                # The attempt refused the connection.
                self.refuse_counts += 1

                if self.refuse_counts >= 5:
                    self.context.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.context.signal("pipe;failing", self.refuse_counts)
                self.context.signal("pipe;running", False)
                time.sleep(3)  # 3-second sleep on failed connection attempt.
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                if self.is_shutdown:
                    break
                self.connection_errors += 1
                time.sleep(0.5)
                try:
                    self.close()
                except ConnectionError:
                    pass
                continue
        self.context.signal("pipe;running", False)
        self._thread = None
        self.is_shutdown = False
        self.update_state(STATE_END)
        self._main_lock.release()
        self.pipe_channel("Send Thread Finished...")

    def process_buffer(self):
        """
        Attempts to process the program send from the buffer.

        @return: queue process success.
        """
        if len(self._buffer) > 0:
            buffer = self._buffer
        else:
            return False

        length = min(32, len(buffer))
        packet = buffer[:length]

        # Packet is prepared and ready to send. Open Channel.

        self.send_packet(packet)
        self.context.packet_count += 1

        # Packet was processed. Remove that data.
        self._buffer = self._buffer[length:]
        self.update_buffer()
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        """
        Send packet to the CH341 connection.
        """
        if self._connection is None:
            raise ConnectionError
        self._connection.write(packet)
        self.update_packet(packet)

    def update_status(self):
        """
        Request a status update from the CH341 connection.
        """
        if self._connection is None:
            raise ConnectionError
        self._status = self._connection.get_status()
        if self.context is not None:
            try:
                self.context.signal(
                    "pipe;status",
                    self._status,
                    get_code_string_from_moshicode(self._status[1]),
                )
            except IndexError:
                pass
            self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        """
        Wait until the device can accept packets.
        """
        i = 0
        while self.state != STATE_TERMINATE:
            self.update_status()
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_ERROR:
                raise ConnectionRefusedError
            if status == STATUS_OK:
                return
            time.sleep(0.05)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        """
        Wait until the device has finished the current sending buffer.
        """
        self.pipe_channel("Wait Finished")
        i = 0
        original_state = self.state
        if self.state != STATE_PAUSE:
            self.pause()

        while True:
            if self.state != STATE_WAIT:
                if self.state == STATE_TERMINATE:
                    return  # Abort all the processes was requested. This state change would be after clearing.
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
