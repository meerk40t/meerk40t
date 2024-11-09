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

from meerk40t.ch341 import get_ch341_interface

STATUS_SERIAL_CORRECT_M3_FINISH = 204
# 0xCC, 11001100
STATUS_OK = 206
# 0xCE, 11001110
STATUS_ERROR = 207
# 0xCF, 11001111
STATUS_FINISH = 236
# 0xEC, 11101100
STATUS_BUSY = 238
# 0xEE, 11101110
STATUS_POWER = 239


STATE_X_FORWARD_LEFT = (
    0b0000000000000001  # Direction is flagged left rather than right.
)
STATE_Y_FORWARD_TOP = 0b0000000000000010  # Direction is flagged top rather than bottom.
STATE_X_STEPPER_ENABLE = 0b0000000000000100  # X-stepper motor is engaged.
STATE_Y_STEPPER_ENABLE = 0b0000000000001000  # Y-stepper motor is engaged.
STATE_HORIZONTAL_MAJOR = 0b0000000000010000
REQUEST_X = 0b0000000000100000
REQUEST_X_FORWARD_LEFT = 0b0000000001000000  # Requested direction towards the left.
REQUEST_Y = 0b0000000010000000
REQUEST_Y_FORWARD_TOP = 0b0000000100000000  # Requested direction towards the top.
REQUEST_AXIS = 0b0000001000000000
REQUEST_HORIZONTAL_MAJOR = 0b0000010000000000  # Requested horizontal major axis.


def get_code_string_from_code(code):
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_BUSY:
        return "Busy"
    elif code == STATUS_ERROR:
        return "Rejected"
    elif code == STATUS_FINISH:
        return "Finish"
    elif code == STATUS_POWER:
        return "Low Power"
    elif code == STATUS_SERIAL_CORRECT_M3_FINISH:
        return "M3-Finished"
    elif code == 0:
        return "USB Failed"
    else:
        return f"UNK {code:02x}"


def convert_to_list_bytes(data):
    if isinstance(data, str):  # python 2
        packet = [0] * 30
        for i in range(0, 30):
            packet[i] = ord(data[i])
        return packet
    else:
        packet = [0] * 30
        for i in range(0, 30):
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
    for i in range(0, 30):
        crc = line[i] ^ crc
        crc = crc_table[crc & 0x0F] ^ crc_table[16 + ((crc >> 4) & 0x0F)]
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
        self.serial_confirmed = None

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
        self.usb_log = service.channel(f"{name}/usb", buffer_size=500)
        self.usb_send_channel = service.channel(f"{name}/usb_send")
        self.recv_channel = service.channel(f"{name}/recv")
        self.usb_log.watch(lambda e: service.signal("pipe;usb_status", e))
        self.reset()

    @property
    def viewbuffer(self):
        buffer = bytes(self._realtime_buffer) + bytes(self._buffer) + bytes(self._queue)
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
        return len(self._buffer) + len(self._queue) + len(self._preempt)

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
                    mock_status=STATUS_OK,
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
        self._buffer = bytearray()
        self._queue = bytearray()
        self._realtime_buffer = bytearray()
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
        packet += b"F" * (30 - len(packet))
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
            if len(self._realtime_buffer) <= 0 and len(self._buffer) <= 0:
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
            with self._queue_lock:
                self._buffer += self._queue
                self._queue.clear()
            self.update_buffer()

        if len(self._preempt):  # check for and prepend preempt
            with self._preempt_lock:
                self._realtime_buffer += self._preempt
                self._preempt.clear()
            self.update_buffer()

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
        if len(self._realtime_buffer) > 0:
            buffer = self._realtime_buffer
            realtime = True
        elif len(self._buffer) > 0:
            buffer = self._buffer
            realtime = False
        else:
            return False

        # Find buffer of 30 or containing '\n'.
        find = buffer.find(b"\n", 0, 30)
        if find == -1:  # No end found.
            length = min(30, len(buffer))
        else:  # Line end found.
            length = min(30, len(buffer), find + 1)
        packet = bytes(buffer[:length])

        # edge condition of catching only pipe command without '\n'
        if packet.endswith((b"-", b"*", b"&", b"!", b"#", b"%", b"\x18")):
            packet += buffer[length : length + 1]
            length += 1
        post_send_command = None
        default_checksum = True

        # find pipe commands.
        if packet.endswith(b"\n"):
            packet = packet[:-1]
            # There's a special case where we have a trailing "\n" at an exactly 30 byte command,
            # that requires another package of 30 x F to be sent, so we need to deal with an empty string...
            if len(packet) == 0:
                packet += b"F"
            if packet.endswith(b"P"):
                # This is a special case where the m3nano seems to fail. So we extend the buffer...
                packet += b"F"
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
            elif packet.endswith(b"\x18"):
                self.update_state("terminate")
                self.is_shutdown = True
                packet = packet[:-1]
            if packet.startswith(b"A"):
                # This is a challenge code. A is only used for serial challenges.
                post_send_command = self._confirm_serial
            if len(packet) != 0:
                if packet.endswith(b"#"):
                    packet = packet[:-1]
                    try:
                        c = packet[-1]
                    except IndexError:
                        c = b"F"  # Packet was simply #. We can do nothing.
                    packet += bytes([c]) * (30 - len(packet))  # Padding. '\n'
                else:
                    packet += b"F" * (30 - len(packet))  # Padding. '\n'
        if not realtime and self.state in ("pause", "busy"):
            return False  # Processing normal queue, PAUSE and BUSY apply.

        # Packet is prepared and ready to send. Open Channel.
        self.open()

        if len(packet) == 30:
            # We have a sendable packet.
            if not self.pre_ok:
                self.wait_until_accepting_packets()
            if default_checksum:
                packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
            else:
                packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet) ^ 0xFF])
            self.connection.write(packet)
            self.pre_ok = False

            # Packet is sent, trying to confirm.
            status = 0
            flawless = True
            for attempts in range(500):
                # We'll try to confirm this at 500 times.
                try:
                    self.update_status()
                    status = self._status[1]
                    if attempts > 10:
                        time.sleep(min(0.001 * attempts, 0.1))
                except ConnectionError:
                    # Errors are ignored, must confirm packet.
                    flawless = False
                    continue
                if status == 0:
                    # We did not read a status.
                    continue
                if status == STATUS_OK:
                    # Packet was fine.
                    self.pre_ok = True
                    break
                elif status == STATUS_BUSY:
                    # Busy. We still do not have our confirmation. BUSY comes before ERROR or OK.
                    continue
                elif status == STATUS_ERROR:
                    if not default_checksum:
                        break
                    self.context.rejected_count += 1
                    if flawless:  # Packet was rejected. The CRC failed.
                        return False
                    else:
                        # The channel had the error, assuming packet was actually good.
                        break
                elif status == STATUS_FINISH:
                    # We finished. If we were going to wait for that, we no longer need to.
                    if post_send_command == self.wait_finished:
                        post_send_command = None
                    continue  # This is not a confirmation.
                elif status == STATUS_SERIAL_CORRECT_M3_FINISH:
                    if post_send_command == self._confirm_serial:
                        # We confirmed the serial number on the card.
                        self.serial_confirmed = True
                        post_send_command = None
                        break
                    elif post_send_command == self.wait_finished:
                        # This is a STATUS_M3_FINISHED, we no longer wait.
                        post_send_command = None
                        continue

            if status == 0:  # After 500 attempts we could only get status = 0.
                raise ConnectionError  # Broken pipe. Could not confirm packet.
            self.context.packet_count += (
                1  # Our packet is confirmed or assumed confirmed.
            )
        else:
            if len(packet) != 0:
                # We could only generate a partial packet, throw it back
                return False
            # We have an empty packet of only commands. Continue work.

        # Packet was processed. Remove that data.
        if realtime:
            del self._realtime_buffer[:length]
        else:
            del self._buffer[:length]
        if len(packet) != 0:
            # Packet was completed and sent. Only then update the channel.
            self.update_packet(packet)
        self.update_buffer()

        if post_send_command is not None:
            # Post send command could be wait_finished, and might have a broken pipe.
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass
        return True  # A packet was prepped and sent correctly.

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
            if status == STATUS_OK:
                self.pre_ok = False
                break
            if status == STATUS_ERROR:
                break
            time.sleep(0.05)
            if self.context is not None:
                self.context.signal("pipe;wait", STATUS_OK, i)
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
            if status == STATUS_ERROR:
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
            if status == STATUS_SERIAL_CORRECT_M3_FINISH:
                self.serial_confirmed = True
                return  # We're done.
        self.serial_confirmed = False
