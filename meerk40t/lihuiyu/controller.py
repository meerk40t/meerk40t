"""
Lihuiyu Controller

Deals with the sending of data via the registered connection, and processes some limited realtime commands.

    - : require wait finish at the end of the queue processing.
    * : clear the buffers, and abort the thread.
    ! : pause.
    & : resume.
    % : fail checksum, do not resend
    ~ : begin/end realtime exception (Note, these characters would be consumed during
            the write process and should not exist in the queue)
    \x18 : quit.

"""

import threading
import time
from enum import IntEnum

from meerk40t.ch341 import get_ch341_interface

# Protocol Constants
PACKET_SIZE = 30  # Lihuiyu packet size
MAX_CONFIRMATION_ATTEMPTS = 500  # Maximum attempts to confirm packet
CONFIRMATION_DELAY_START = 10  # Attempts before starting delay
MIN_CONFIRMATION_DELAY = 0.001  # Minimum delay between attempts
MAX_CONFIRMATION_DELAY = 0.1  # Maximum delay between attempts
USB_LOG_BUFFER_SIZE = 500


class LihuiyuStatus(IntEnum):
    """Status codes returned by Lihuiyu laser controllers."""

    # Device Status Codes
    SERIAL_CORRECT_M3_FINISH = 204  # 0xCC - Serial number confirmed on M3
    OK = 206  # 0xCE - Device ready to accept commands
    ERROR = 207  # 0xCF - Error occurred during processing
    FINISH = 236  # 0xEC - Processing finished
    BUSY = 238  # 0xEE - Device is busy processing
    POWER = 239  # 0xEF - Low power condition


class LihuiyuState(IntEnum):
    """State flags for Lihuiyu controller stepper motors and directions."""

    # Direction States
    X_FORWARD_LEFT = 0b0000000000000001  # X-axis moving left
    Y_FORWARD_TOP = 0b0000000000000010  # Y-axis moving up

    # Motor Enable States
    X_STEPPER_ENABLE = 0b0000000000000100  # X-stepper motor engaged
    Y_STEPPER_ENABLE = 0b0000000000001000  # Y-stepper motor engaged

    # Axis States
    HORIZONTAL_MAJOR = 0b0000000000010000  # Horizontal major axis active

    # Request States
    REQUEST_X = 0b0000000000100000  # X-axis requested
    REQUEST_X_FORWARD_LEFT = 0b0000000001000000  # X-axis left direction requested
    REQUEST_Y = 0b0000000010000000  # Y-axis requested
    REQUEST_Y_FORWARD_TOP = 0b0000000100000000  # Y-axis up direction requested
    REQUEST_AXIS = 0b0000001000000000  # Axis operation requested
    REQUEST_HORIZONTAL_MAJOR = 0b0000010000000000  # Horizontal major axis requested


# Backward compatibility - keep old constants but mark as deprecated
STATUS_SERIAL_CORRECT_M3_FINISH = LihuiyuStatus.SERIAL_CORRECT_M3_FINISH.value
STATUS_OK = LihuiyuStatus.OK.value
STATUS_ERROR = LihuiyuStatus.ERROR.value
STATUS_FINISH = LihuiyuStatus.FINISH.value
STATUS_BUSY = LihuiyuStatus.BUSY.value
STATUS_POWER = LihuiyuStatus.POWER.value

# State constants for backward compatibility
STATE_X_FORWARD_LEFT = LihuiyuState.X_FORWARD_LEFT.value
STATE_Y_FORWARD_TOP = LihuiyuState.Y_FORWARD_TOP.value
STATE_X_STEPPER_ENABLE = LihuiyuState.X_STEPPER_ENABLE.value
STATE_Y_STEPPER_ENABLE = LihuiyuState.Y_STEPPER_ENABLE.value
STATE_HORIZONTAL_MAJOR = LihuiyuState.HORIZONTAL_MAJOR.value
REQUEST_X = LihuiyuState.REQUEST_X.value
REQUEST_X_FORWARD_LEFT = LihuiyuState.REQUEST_X_FORWARD_LEFT.value
REQUEST_Y = LihuiyuState.REQUEST_Y.value
REQUEST_Y_FORWARD_TOP = LihuiyuState.REQUEST_Y_FORWARD_TOP.value
REQUEST_AXIS = LihuiyuState.REQUEST_AXIS.value
REQUEST_HORIZONTAL_MAJOR = LihuiyuState.REQUEST_HORIZONTAL_MAJOR.value


def get_code_string_from_code(code):
    """
    Convert Lihuiyu status codes to human-readable strings.

    Args:
        code (int): The status code returned by the Lihuiyu device

    Returns:
        str: Human-readable description of the status code

    Status Code Reference:
        204 (SERIAL_CORRECT_M3_FINISH): Serial number confirmed on M3 device
        206 (OK): Device is ready to accept commands
        207 (ERROR): An error occurred during processing
        236 (FINISH): Processing has finished
        238 (BUSY): Device is currently busy processing
        239 (POWER): Low power condition detected
        0: USB connection failed
        Other: Unknown status code in hex format
    """
    try:
        status = LihuiyuStatus(code)
        return status.name.replace("_", " ").title()
    except ValueError:
        return "USB Failed" if code == 0 else f"UNK {code:02x}"


def convert_to_list_bytes(data):
    packet = [0] * PACKET_SIZE
    data_len = min(len(data), PACKET_SIZE)
    if isinstance(data, str):  # python 2
        for i in range(data_len):
            packet[i] = ord(data[i])
    else:
        for i in range(data_len):
            packet[i] = data[i]
    return packet


crc_table = [
    0x00,
    0x5E,
    0xBC,
    0xE2,
    0x61,
    0x3F,
    0xDD,
    0x83,
    0xC2,
    0x9C,
    0x7E,
    0x20,
    0xA3,
    0xFD,
    0x1F,
    0x41,
    0x00,
    0x9D,
    0x23,
    0xBE,
    0x46,
    0xDB,
    0x65,
    0xF8,
    0x8C,
    0x11,
    0xAF,
    0x32,
    0xCA,
    0x57,
    0xE9,
    0x74,
]


def onewire_crc_lookup(line):
    """
    License: 2-clause "simplified" BSD license
    Copyright (C) 1992-2017 Arjen Lentz
    https://lentz.com.au/blog/calculating-crc-with-a-tiny-32-entry-lookup-table

    @param line: line to be CRC'd
    @return: 8 bit crc of line.
    """

    crc = 0
    for i in range(PACKET_SIZE):
        crc = line[i] ^ crc
        crc = crc_table[crc & 0x0F] ^ crc_table[16 + ((crc >> 4) & 0x0F)]

    """ Print the line in hex and ascii format for debugging purposes.
    def hex_repr(data):
        return " ".join(f"{x:02x}" for x in data)

    def ascii_repr(data):
        return "".join(chr(x) if 32 <= x < 127 else "." for x in data)

    print (f"Line ({len(line)} bytes): {hex_repr(line)} {ascii_repr(line)} CRC: {hex(crc)}")
    """
    return crc


class LihuiyuController:
    """
    K40 Controller controls the Lihuiyu boards sending any queued data to the USB when the signal is not busy.

    Opening and closing of the pipe are dealt with internally. There are three primary monitor data channels.
    'send', 'recv' and 'usb'. They display the reading and writing of information to/from the USB and the USB connection
    log, providing information about the connecting and error status of the USB device.
    """

    def __init__(self, service, *args, **kwargs):
        self.context = service
        self.state = "unknown"
        self.is_shutdown = False
        self.serial_confirmed = False  # Initialize as boolean, not None

        self._thread = None
        self._buffer = (
            bytearray()
        )  # Threadsafe buffered commands to be sent to controller.
        self._realtime_buffer = (
            bytearray()  # Threadsafe realtime buffered commands to be sent to the controller.
        )
        self._queue = bytearray()  # Thread-unsafe additional commands to append.
        self._preempt = (
            bytearray()
        )  # Thread-unsafe preempt commands to prepend to the buffer.
        self._buffer_lock = threading.Lock()
        self._queue_lock = threading.Lock()
        self._preempt_lock = threading.Lock()
        self._main_lock = threading.Lock()
        self._connect_lock = threading.RLock()
        self._loop_cond = threading.Condition()

        self._status = [0] * 6
        self._usb_state = -1

        self.connection = None
        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.aborted_retries = False
        self.pre_ok = False
        self.realtime = False

        self.abort_waiting = False

        name = service.safe_label
        self.pipe_channel = service.channel(f"{name}/events")
        self.usb_log = service.channel(f"{name}/usb", buffer_size=USB_LOG_BUFFER_SIZE)
        self.usb_send_channel = service.channel(f"{name}/usb_send")
        self.recv_channel = service.channel(f"{name}/recv")
        # Keep reference to prevent garbage collection with weak=True default
        self._usb_status_handler = lambda e: service.signal("pipe;usb_status", e)
        self.usb_log.watch(self._usb_status_handler)
        self.reset()

    def _acquire_all_buffer_locks(self):
        """
        Acquire all buffer-related locks in a consistent order to prevent deadlocks.
        Always acquire locks in the same order: buffer, queue, preempt.
        """
        self._buffer_lock.acquire()
        self._queue_lock.acquire()
        self._preempt_lock.acquire()

    def _release_all_buffer_locks(self):
        """
        Release all buffer-related locks in reverse order.
        """
        self._preempt_lock.release()
        self._queue_lock.release()
        self._buffer_lock.release()

    @property
    def viewbuffer(self):
        self._acquire_all_buffer_locks()
        try:
            buffer = (
                bytes(self._realtime_buffer) + bytes(self._buffer) + bytes(self._queue)
            )
        finally:
            self._release_all_buffer_locks()
        try:
            buffer_str = buffer.decode()
        except ValueError:
            try:
                buffer_str = buffer.decode("utf8")
            except UnicodeDecodeError:
                buffer_str = str(buffer)
        except AttributeError:
            buffer_str = buffer
        return buffer_str

    def added(self):
        self.start()

    def service_detach(self):
        pass

    def shutdown(self, *args, **kwargs):
        if self._thread is not None:
            self.realtime_write(b"\x18\n")

    def __repr__(self):
        return f"LihuiyuController({str(self.context)})"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        self._acquire_all_buffer_locks()
        try:
            return len(self._buffer) + len(self._queue) + len(self._preempt)
        finally:
            self._release_all_buffer_locks()

    def open(self):
        with self._connect_lock:
            self._process_open()

    def _process_open(self):
        if self.connection is not None and self.connection.is_connected():
            return  # Already connected.
        _ = self.usb_log._
        self.pipe_channel("open()")
        try:
            interfaces = list(
                get_ch341_interface(
                    self.context,
                    self.usb_log,
                    mock=self.context.mock,
                    mock_status=LihuiyuStatus.OK.value,
                    bulk=True,
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
        if self.context.serial_enable and self.context.serial is not None:
            if self.serial_confirmed:
                return  # already passed.
            self.usb_log(_("Requires serial number confirmation."))
            self.challenge(self.context.serial)
            t = time.time()
            while time.time() - t < 0.5:
                if self.serial_confirmed:
                    break
            if not self.serial_confirmed:
                raise ConnectionRefusedError("Serial number confirmation failed.")
            else:
                self.usb_log(_("Serial number confirmed."))

    def close(self):
        self.pipe_channel("close()")
        with self._connect_lock:
            if self.connection is None:
                return
            self.connection.close()
            self.connection = None

    def write(self, bytes_to_write):
        """
        Writes data to the queue, this will be moved into the buffer by the thread in a threadsafe manner.

        @param bytes_to_write: data to write to the queue.
        @return:
        """
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are in a realtime exception.
            self.realtime = True

            # All code prior to ~ is sent to write.
            queue_bytes = bytes_to_write[:f]
            if queue_bytes:
                self.write(queue_bytes)

            # All code after ~ is sent to realtime write.
            preempt_bytes = bytes_to_write[f + 1 :]
            if preempt_bytes:
                self.realtime_write(preempt_bytes)
            return self
        if self.realtime:
            # We are in a realtime exception that has not been terminated.
            self.realtime_write(bytes_to_write)
            return self

        self.pipe_channel(f"write({str(bytes_to_write)})")
        with self._queue_lock:
            self._queue += bytes_to_write
        self.start()
        self.update_buffer()
        return self

    def realtime_write(self, bytes_to_write):
        """
        Writes data to the preempting commands, this will be moved to the front of the buffer by the thread
        in a threadsafe manner.

        @param bytes_to_write: data to write to the front of the queue.
        @return:
        """
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are leaving realtime exception.
            self.realtime = False

            # All date prior to the ~ is sent to realtime write.
            preempt_bytes = bytes_to_write[:f]
            if preempt_bytes:
                self.realtime_write(preempt_bytes)

            # All data after ~ is sent back to normal write.
            queue_bytes = bytes_to_write[f + 1 :]
            if queue_bytes:
                self.write(queue_bytes)
            return self
        self.pipe_channel(f"realtime_write({str(bytes_to_write)})")
        if b"*" in bytes_to_write:
            self.abort_waiting = True
        with self._preempt_lock:
            self._preempt = bytearray(bytes_to_write) + self._preempt
        self.start()
        self.update_buffer()
        return self

    def start(self):
        """
        Controller state change to `Started`.
        @return:
        """
        with self._loop_cond:
            self._loop_cond.notify()
        if not self.is_shutdown and (
            self._thread is None or not self._thread.is_alive()
        ):
            self.update_state("init")
            self._thread = self.context.threaded(
                self._thread_data_send,
                thread_name=f"LhyPipe({self.context.path})",
                result=self.stop,
            )
            self._thread.stop = self.stop

    def _pause_busy(self):
        """
        BUSY can be called in a paused state to packet halt the controller.

        This can only be done from PAUSE.
        """
        if self.state != "pause":
            self.pause()
        if self.state == "pause":
            self.update_state("busy")

    def _resume_busy(self):
        """
        Resumes from a BUSY to restore the controller. This will return to a paused state.

        This can only be done from BUSY.
        """
        if self.state == "busy":
            self.update_state("pause")
            self.resume()

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

    def abort(self):
        self._acquire_all_buffer_locks()
        try:
            self._buffer.clear()
            self._queue.clear()
            self._realtime_buffer.clear()
        finally:
            self._release_all_buffer_locks()
        self.abort_waiting = False
        self.context.signal("pipe;buffer", 0)
        self.update_state("terminate")

    def reset(self):
        self.update_state("init")

    def stop(self, *args):
        self.abort()
        try:
            if self._thread is not None:
                self._thread.join()  # Wait until stop completes before continuing.
            self._thread = None
        except RuntimeError:
            pass  # Stop called by current thread.

    def abort_retry(self):
        with self._loop_cond:
            self._loop_cond.notify()
        self.aborted_retries = True
        self.context.signal("pipe;state", "STATE_FAILED_SUSPENDED")

    def continue_retry(self):
        with self._loop_cond:
            self._loop_cond.notify()
        self.aborted_retries = False
        self.context.signal("pipe;state", "STATE_FAILED_RETRYING")

    def usb_release(self):
        if self.connection:
            self.connection.release()
        else:
            raise ConnectionError

    def usb_reset(self):
        if self.connection:
            self.connection.reset()
        else:
            raise ConnectionError

    def challenge(self, serial):
        if serial is None:
            return

        from hashlib import md5

        challenge = bytearray.fromhex(md5(bytes(serial.upper(), "utf8")).hexdigest())
        packet = b"A%s" % challenge
        packet = self._pad_packet_to_size(packet, b"F")
        packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
        self.connection.write(packet)
        try:
            self._confirm_serial()
        except ConnectionError:
            # If we could not access the status, then we did not confirm the serial number.
            pass

    def update_state(self, state):
        with self._loop_cond:
            self._loop_cond.notify()
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        self.context.signal("pipe;buffer", len(self))

    def update_packet(self, packet):
        self.context.signal("pipe;packet", convert_to_list_bytes(packet))
        self.context.signal("pipe;packet_text", packet)
        if self.usb_send_channel:
            self.usb_send_channel(packet)

    def _thread_loop(self):
        while self.state not in ("end", "terminate"):
            if self.state == "init":
                # If we are initialized. Change that to active since we're running.
                self.update_state("active")
            elif self.state in ("pause", "busy", "suspend"):
                # If we are paused just wait until the state changes.
                if len(self._realtime_buffer) == 0 and len(self._preempt) == 0:
                    # Only pause if there are no realtime commands to queue.
                    self.context.laser_status = "idle"
                    with self._loop_cond:
                        self._loop_cond.wait()
                    continue
            if self.aborted_retries:
                # We are not trying reconnection anymore.
                self.context.laser_status = "idle"
                with self._loop_cond:
                    self._loop_cond.wait()
                continue

            self._check_transfer_buffer()
            self._acquire_all_buffer_locks()
            try:
                buffer_empty = (
                    len(self._realtime_buffer) <= 0 and len(self._buffer) <= 0
                )
            finally:
                self._release_all_buffer_locks()
            if buffer_empty:
                # The buffer and realtime buffers are empty. No packet creation possible.
                self.context.laser_status = "idle"
                with self._loop_cond:
                    self._loop_cond.wait()
                continue

            try:
                # We try to process the queue.
                queue_processed = self.process_queue()
                if self.refuse_counts:
                    self.context.signal("pipe;failing", 0)
                self.refuse_counts = 0
                if self.is_shutdown:
                    return  # Sometimes it could reset this and escape.
            except ConnectionRefusedError:
                # The attempt refused the connection.
                self.refuse_counts += 1
                self.pre_ok = False
                if self.refuse_counts >= 5:
                    self.context.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.context.signal("pipe;failing", self.refuse_counts)
                self.context.laser_status = "idle"
                if self.is_shutdown:
                    return  # Sometimes it could reset this and escape.
                time.sleep(3)  # 3-second sleep on failed connection attempt.
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                self.connection_errors += 1
                self.pre_ok = False

                self.context.laser_status = "idle"
                time.sleep(0.5)
                self.close()
                continue

            self.context.laser_status = "active" if queue_processed else "idle"
            if queue_processed:
                # Packet was sent.
                if self.state not in (
                    "pause",
                    "busy",
                    "active",
                    "terminate",
                ):
                    self.update_state("active")
                continue
            # No packet could be sent.
            if self.state not in (
                "pause",
                "busy",
                "terminate",
            ):
                self.update_state("idle")

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        with self._main_lock:
            self.pre_ok = False
            self.is_shutdown = False
            self._thread_loop()
            self._thread = None
            self.update_state("end")
            self.pre_ok = False
            self.context.laser_status = "idle"

    def _check_transfer_buffer(self):
        if len(self._queue):  # check for and append queue
            self._acquire_all_buffer_locks()
            try:
                self._buffer += self._queue
                self._queue.clear()
            finally:
                self._release_all_buffer_locks()
            self.update_buffer()

        if len(self._preempt):  # check for and prepend preempt
            self._acquire_all_buffer_locks()
            try:
                self._realtime_buffer += self._preempt
                self._preempt.clear()
            finally:
                self._release_all_buffer_locks()
            self.update_buffer()

    def debug_packet(self, packet):
        """
        Debugging function to print the packet in a readable format.
        We will output both hex and ascii representation of the packet.
        @param packet: Packet to debug.
        """
        hex_packet = " ".join(f"{b:02x}" for b in packet)
        ascii_packet = "".join(chr(b) if 32 <= b < 127 else "." for b in packet)
        print(f"Packet: {hex_packet} | ASCII: {ascii_packet} (len={len(packet)})")

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open, 'process_queue_pause = True' (anytime before packet sent),
        self._buffer is empty, or a failure to produce packet.

        Buffer will not be changed unless packet is successfully sent, or pipe commands are processed.

        The following are meta commands for the controller
        - : require wait finish at the end of the queue processing.
        * : clear the buffers, and abort the thread.
        ! : pause.
        & : resume.
        % : fail checksum, do not resend
        ~ : begin/end realtime exception (Note, these characters would be consumed during
                the write process and should not exist in the queue)
        \x18 : quit.

        @return: queue process success.
        """
        # Get buffer snapshot and determine which buffer to use
        buffer, realtime = self._get_buffer_snapshot()
        if buffer is None:
            return False

        # Extract packet from buffer
        (
            packet,
            length,
            post_send_command,
            default_checksum,
        ) = self._extract_packet_from_buffer(buffer)

        # Check if we should process this packet
        if not realtime and self.state in ("pause", "busy"):
            return False  # Processing normal queue, PAUSE and BUSY apply.

        # Send and confirm packet if it's the right size
        packet_sent = self._send_and_confirm_packet(packet, default_checksum)

        # Update buffer after processing
        self._update_buffer_after_processing(realtime, length, packet)

        # Execute post-send command if any
        self._execute_post_send_command(post_send_command)

        return packet_sent

    def _get_buffer_snapshot(self):
        """
        Get a snapshot of the buffer to process and determine which buffer to use.

        @return: tuple of (buffer_bytes, is_realtime) or (None, None) if no buffer available
        """
        self._acquire_all_buffer_locks()
        try:
            if len(self._realtime_buffer) > 0:
                return bytes(self._realtime_buffer), True
            elif len(self._buffer) > 0:
                return bytes(self._buffer), False
            else:
                return None, None
        finally:
            self._release_all_buffer_locks()

    def _extract_packet_from_buffer(self, buffer):
        """
        Extract a packet from the buffer, handling pipe commands and special cases.

        @param buffer: The buffer bytes to extract from
        @return: tuple of (packet, length, post_send_command, default_checksum)
        """
        # Find buffer of PACKET_SIZE or containing '\n'.
        find = buffer.find(b"\n", 0, PACKET_SIZE)
        if find == -1:  # No end found.
            length = min(PACKET_SIZE, len(buffer))
        else:  # Line end found.
            length = min(PACKET_SIZE, len(buffer), find + 1)
        packet = bytes(buffer[:length])

        # Handle edge condition of catching only pipe command without '\n'
        if packet.endswith((b"-", b"*", b"&", b"!", b"#", b"%", b"\x18")):
            packet += buffer[length : length + 1]
            length += 1

        # Process pipe commands and prepare packet
        return self._process_pipe_commands(packet, length)

    def _process_pipe_commands(self, packet, length):
        """
        Process pipe commands (meta-commands) and prepare the packet for sending.

        @param packet: The raw packet bytes
        @param length: The length of data to remove from buffer
        @return: tuple of (processed_packet, length, post_send_command, default_checksum)
        """
        post_send_command = None
        default_checksum = True

        # Handle AT command special case
        if packet.startswith(b"AT"):
            packet, length = self._handle_at_command(packet, length)

        # Process pipe commands if packet ends with newline
        if packet.endswith(b"\n"):
            packet, post_send_command, default_checksum = self._handle_newline_commands(
                packet
            )

        # Apply final padding if needed
        if len(packet) != 0:
            packet = self._pad_packet_to_size(packet)

        return packet, length, post_send_command, default_checksum

    def _handle_at_command(self, packet, length):
        """
        Handle special AT command processing for M3 devices.

        @param packet: The packet starting with AT
        @param length: Current packet length
        @return: tuple of (processed_packet, updated_length)
        """
        if packet.endswith(b"\n"):
            packet = packet[:-1]
        packet = self._pad_packet_to_size(packet, b"\x00")
        return packet, length

    def _handle_newline_commands(self, packet):
        """
        Handle pipe commands when packet ends with newline.

        @param packet: The packet ending with newline
        @return: tuple of (processed_packet, post_send_command, default_checksum)
        """
        post_send_command = None
        default_checksum = True

        packet = packet[:-1]  # Remove newline

        # Handle empty packet case
        if len(packet) == 0:
            packet += b"F"

        # Handle special cases
        if packet.endswith(b"P"):
            packet += b"F"  # Extend buffer for m3nano
        elif packet.endswith(b"-"):  # wait finish
            packet = packet[:-1]
            post_send_command = self.wait_finished
        elif packet.endswith(b"*"):  # abort
            post_send_command = self.abort
            packet = packet[:-1]
        elif packet.endswith(b"&"):  # resume
            self._resume_busy()
            packet = packet[:-1]
        elif packet.endswith(b"!"):  # pause
            self._pause_busy()
            packet = packet[:-1]
        elif packet.endswith(b"%"):  # alt-checksum
            default_checksum = False
            packet = packet[:-1]
        elif packet.endswith(b"\x18"):  # quit
            self.update_state("terminate")
            self.is_shutdown = True
            packet = packet[:-1]

        # Handle serial challenge
        if packet.startswith(b"A") and not packet.startswith(b"AT"):
            post_send_command = self._confirm_serial

        return packet, post_send_command, default_checksum

    def _pad_packet_to_size(self, packet, padder=None):
        """
        Pad a packet to PACKET_SIZE using the specified padder character.

        @param packet: The packet to pad
        @param padder: The padding character (bytes). If None, uses default logic:
                       - For packets ending with "#": uses the last character before "#" or "F" if empty
                       - For AT commands: uses b"\x00"
                       - For all other packets: uses b"F"
        @return: The padded packet
        """
        if padder is None:
            if packet.endswith(b"#"):
                packet = packet[:-1]
                try:
                    padder = bytes([packet[-1]])
                except IndexError:
                    padder = b"F"  # Packet was simply #. We can do nothing.
            else:
                padder = b"\x00" if packet.startswith(b"AT") else b"F"
        packet += padder * (PACKET_SIZE - len(packet))
        return packet

    def _send_and_confirm_packet(self, packet, default_checksum):
        """
        Send a packet and wait for confirmation.

        @param packet: The packet to send
        @param default_checksum: Whether to use default checksum
        @return: True if packet was sent successfully, False otherwise
        """
        if len(packet) != PACKET_SIZE:
            return len(packet) == 0  # Empty packets are considered successful

        # Packet is prepared and ready to send. Open Channel.
        self.open()

        # We have a sendable packet.
        if not self.pre_ok:
            self.wait_until_accepting_packets()

        # Add checksum and send
        if default_checksum:
            packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
        else:
            packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet) ^ 0xFF])

        self.connection.write(packet)
        self.pre_ok = False

        # Confirm packet was received
        return self._confirm_packet_receipt(default_checksum)

    def _confirm_packet_receipt(self, default_checksum):
        """
        Wait for confirmation that the packet was received correctly.

        @param default_checksum: Whether default checksum was used
        @return: True if packet was confirmed, False otherwise
        """
        status = 0
        flawless = True

        for attempts in range(MAX_CONFIRMATION_ATTEMPTS):
            try:
                self.update_status()
                # Make sure we have a valid status
                if self._status is not None and len(self._status) > 1:
                    status = self._status[1]
                if attempts > CONFIRMATION_DELAY_START:
                    time.sleep(
                        min(MIN_CONFIRMATION_DELAY * attempts, MAX_CONFIRMATION_DELAY)
                    )
            except ConnectionError:
                flawless = False
                continue

            if status == 0:
                continue

            # Check status codes
            if status == LihuiyuStatus.OK.value:
                self.pre_ok = True
                self.context.packet_count += 1
                return True
            elif status == LihuiyuStatus.BUSY.value:
                continue
            elif status == LihuiyuStatus.ERROR.value:
                if not default_checksum:
                    return True
                self.context.rejected_count += 1
                return not flawless  # Return True if there were connection errors
            elif status == LihuiyuStatus.FINISH.value:
                continue  # This is not a confirmation.
            elif status == LihuiyuStatus.SERIAL_CORRECT_M3_FINISH.value:
                self.context.packet_count += 1
                return True

        # After all attempts, if we still have status 0, it's a broken pipe
        if status == 0:
            raise ConnectionError("Broken pipe. Could not confirm packet.")
        return False

    def _update_buffer_after_processing(self, realtime, length, packet):
        """
        Update the buffer by removing processed data.

        @param realtime: Whether this was a realtime buffer
        @param length: Length of data to remove
        @param packet: The packet that was processed
        """
        # Packet was processed. Remove that data.
        self._acquire_all_buffer_locks()
        try:
            if realtime:
                del self._realtime_buffer[:length]
            else:
                del self._buffer[:length]
        finally:
            self._release_all_buffer_locks()

        if len(packet) != 0:
            # Packet was completed and sent. Only then update the channel.
            self.update_packet(packet)
        self.update_buffer()

    def _execute_post_send_command(self, post_send_command):
        """
        Execute post-send command if one was specified.

        @param post_send_command: The command to execute after sending
        """
        if post_send_command is not None:
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass

    def update_status(self):
        try:
            self._status = self.connection.get_status()
        except AttributeError:
            # self.connection was closed by something.
            raise ConnectionError
        if self.context is not None:
            try:
                self.context.signal(
                    "pipe;status",
                    self._status,
                    get_code_string_from_code(self._status[1]),
                )
            except IndexError:
                pass
            if self.recv_channel:
                self.recv_channel(str(self._status))

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != "terminate":
            self.update_status()
            if self._status is None:
                raise ConnectionError
            status = self._status[1]
            if status == 0:
                raise ConnectionError
            if status == LihuiyuStatus.OK.value:
                self.pre_ok = False
                break
            if status == LihuiyuStatus.ERROR.value:
                break
            time.sleep(0.05)
            if self.context is not None:
                self.context.signal("pipe;wait", LihuiyuStatus.OK.value, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
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
                raise ConnectionError
            if status == LihuiyuStatus.ERROR.value:
                self.context.rejected_count += 1
            if status & 0x02 == 0:
                # StateBitPEMP = 0x00000200, Finished = 0xEC, 11101100
                break
            if self.context is not None:
                self.context.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                break  # Wait abort was requested.
            time.sleep(0.001)  # Only if we are using control transfer status checks.
        self.update_state(original_state)

    def _confirm_serial(self):
        t = time.time()
        while time.time() - t < 0.5:  # We spend up to half a second to confirm.
            if self.state == "terminate":
                # We are not confirmed.
                return  # Abort all the processes was requested. This state change would be after clearing.
            self.update_status()
            status = self._status[1]
            if status == LihuiyuStatus.SERIAL_CORRECT_M3_FINISH.value:
                self.serial_confirmed = True
                return  # We're done.
        self.serial_confirmed = False
