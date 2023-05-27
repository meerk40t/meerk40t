"""
Moshiboard Controller

Tasked with sending data to usb connection.
"""

import threading
import time

from .builder import MoshiBuilder
from ..ch341 import get_ch341_interface

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

    def __init__(self, context, channel=None, force_mock=False, *args, **kwargs):
        self.context = context
        self.state = "unknown"

        self._programs = []  # Programs to execute.
        self._buffer = (
            bytearray()
        )  # Threadsafe buffered commands to be sent to controller.

        self._thread = None
        self.is_shutdown = False
        self._program_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.connection = None
        self.force_mock = force_mock

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

    def open(self):
        _ = self.usb_log._
        if self.connection is not None and self.connection.is_connected():
            return  # Already connected.
        self.pipe_channel("open()")

        try:
            interfaces = list(
                get_ch341_interface(
                    self.context,
                    self.usb_log,
                    mock=self.force_mock or self.context.mock,
                    mock_status=STATUS_OK,
                    bulk=False,
                )
            )
            if self.context.usb_index != -1:
                # Instructed to check one specific device.
                devices = [self.context.usb_index]
            else:
                devices = range(16)

            for interface in interfaces:
                self.connection = interface
                for i in devices:
                    try:
                        self._open_at_index(i)
                        return  # Opened successfully.
                    except ConnectionRefusedError as e:
                        self.usb_log(str(e))
                        if self.connection is not None:
                            self.connection.close()
                    except IndexError:
                        self.usb_log(_("Connection failed."))
                        self.connection = None
                        break
        except PermissionError as e:
            self.usb_log(str(e))
            return  # OS denied permissions, no point checking anything else.
        if self.connection:
            self.close()
        raise ConnectionRefusedError(
            _("No valid connection matched any given criteria.")
        )

    def _open_at_index(self, usb_index):
        _ = self.context.kernel.translation
        self.connection.open(usb_index=usb_index)
        if not self.connection.is_connected():
            raise ConnectionRefusedError("ch341 connect did not return a connection.")
        if self.context.usb_bus != -1 and self.connection.bus != -1:
            if self.connection.bus != self.context.usb_bus:
                raise ConnectionRefusedError(
                    _("K40 devices were found but they were rejected due to usb bus.")
                )
        if self.context.usb_address != -1 and self.connection.address != -1:
            if self.connection.address != self.context.usb_address:
                raise ConnectionRefusedError(
                    _(
                        "K40 devices were found but they were rejected due to usb address."
                    )
                )
        if self.context.usb_version != -1:
            version = self.connection.get_chip_version()
            if version != self.context.usb_version:
                raise ConnectionRefusedError(
                    _(
                        "K40 devices were found but they were rejected due to chip version."
                    )
                )

    def close(self):
        self.pipe_channel("close()")
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        else:
            raise ConnectionError

    def write(self, data):
        self.open()
        with self._program_lock:
            self._programs.append(data)
        self.start()

    def realtime(self, data):
        if MoshiBuilder.is_estop(data):
            self.context.signal("pipe;buffer", 0)
            self.update_state("terminate")
            with self._program_lock:
                self._programs.clear()
                self._buffer.clear()
        self.open()
        self.connection.write_addr(data)

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
            self.update_state("init")

    def pause(self):
        """
        Pause simply holds the controller from sending any additional packets.

        If this state change is done from INITIALIZE it will start the processing.
        Otherwise, it must be done from ACTIVE or IDLE.
        """
        if self.state == "init":
            self.start()
            self.update_state("pause")
        if self.state in ("active", "idle"):
            self.update_state("pause")

    def resume(self):
        """
        Resume can only be called from PAUSE.
        """
        if self.state == "pause":
            self.update_state("active")

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
        self.context.signal("pipe;buffer", len(self._buffer))

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
                    "pause",
                    "busy",
                    "active",
                    "terminate",
                ):
                    self.update_state("active")
                self.count = 0
            else:
                # No packet could be sent.
                if self.state not in (
                    "pause",
                    "busy",
                    "terminate",
                ):
                    self.update_state("idle")
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
        self.count = 0
        self.is_shutdown = False

        while True:
            self.pipe_channel("While Loop")
            try:
                if self.state == "init":
                    # If we are initialized. Change that to active since we're running.
                    self.update_state("active")
                if self.is_shutdown:
                    break
                if len(self._buffer) == 0 and len(self._programs) == 0:
                    self.pipe_channel("Nothing to process")
                    break  # There is nothing to run.
                if self.connection is None:
                    self.open()
                # Stage 0: New Program send.
                if len(self._buffer) == 0:
                    self.context.signal("pipe;running", True)
                    self.pipe_channel("New Program")
                    self.wait_until_accepting_packets()
                    MoshiBuilder.prologue(self.connection.write_addr, self.pipe_channel)
                    with self._program_lock:
                        self._buffer += self._programs.pop(0)
                    if len(self._buffer) == 0:
                        continue

                # Stage 1: Send Program.
                self.context.signal("pipe;running", True)
                self.pipe_channel(f"Sending Data... {len(self._buffer)} bytes")
                self._send_buffer()
                self.update_status()
                MoshiBuilder.epilogue(self.connection.write_addr, self.pipe_channel)
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
        self.update_state("end")
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

        length = min(33, len(buffer))
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
        if self.connection is None:
            raise ConnectionError
        self.connection.write(packet)
        self.update_packet(packet)

    def update_status(self):
        """
        Request a status update from the CH341 connection.
        """
        if self.connection is None:
            raise ConnectionError
        self._status = self.connection.get_status()
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
        while self.state != "terminate":
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
        if self.state != "pause":
            self.pause()

        while True:
            if self.state != "wait":
                if self.state == "terminate":
                    return  # Abort all the processes was requested. This state change would be after clearing.
                self.update_state("wait")
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
