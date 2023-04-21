import threading
import time


from ...kernel import (
    STATE_ACTIVE,
    STATE_BUSY,
    STATE_END,
    STATE_IDLE,
    STATE_INITIALIZE,
    STATE_PAUSE,
    STATE_SUSPEND,
    STATE_TERMINATE,
    STATE_UNKNOWN,
    STATE_WAIT,
)

MILS_IN_MM = 39.3701


STATUS_BAD_STATE = 204
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
    elif code == STATUS_BAD_STATE:
        return "Bad State"
    elif code == 0:
        return "USB Failed"
    else:
        return "UNK %02x" % code


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

    :param line: line to be CRC'd
    :return: 8 bit crc of line.
    """
    crc = 0
    for i in range(0, 30):
        crc = line[i] ^ crc
        crc = crc_table[crc & 0x0F] ^ crc_table[16 + ((crc >> 4) & 0x0F)]
    return crc


class LegacyController:
    """
    This controller is taken wholesale from 0.7.9

    K40 Controller controls the Lhystudios boards sending any queued data to the USB when the signal is not busy.

    Opening and closing of the pipe are dealt with internally. There are three primary monitor data channels.
    'send', 'recv' and 'usb'. They display the reading and writing of information to/from the USB and the USB connection
    log, providing information about the connecting and error status of the USB device.
    """

    def __init__(self, context, name, channel=None, *args, **kwargs):
        context = context.get_context("lhystudios/output/%s" % name)
        self.context = context
        self.name = name
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self.next = None
        self.prev = None

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
        self.context._buffer_size = 0
        self._queue_lock = threading.Lock()
        self._preempt_lock = threading.Lock()
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.connection = None
        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.aborted_retries = False
        self.pre_ok = False
        self.realtime = False

        self.abort_waiting = False
        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=500)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

        from .ch341.ch341 import CH341
        self.ch341 = CH341(context, log=self.usb_log)

        context = self.context

        context.setting(int, "usb_index", -1)
        context.setting(int, "usb_bus", -1)
        context.setting(int, "usb_address", -1)
        context.setting(int, "usb_version", -1)
        context.setting(bool, "mock", False)
        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)

        self.reset()

        self.context.root.listen("lifecycle;ready", self.on_controller_ready)
        self.context.root.listen("lifecycle;shutdown", self.finalize)

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

    def on_controller_ready(self, origin, *args):
        self.context.root.unlisten("lifecycle;ready", self.on_controller_ready)
        self.start()

    def finalize(self, *args, **kwargs):
        if self._thread is not None:
            self.write(b"\x18\n")
        self.context.root.unlisten("lifecycle;shutdown", self.finalize)

    def __repr__(self):
        return "LhystudiosController(%s)" % self.name

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + len(self._queue) + len(self._preempt)

    def open(self):
        self.pipe_channel("open()")
        if self.connection is None:
            self.connection = self.ch341.connect(
                driver_index=self.context.usb_index,
                chipv=self.context.usb_version,
                bus=self.context.usb_bus,
                address=self.context.usb_address,
                mock=False,
            )
        else:
            try:
                self.connection.open()
            except AttributeError:
                raise ConnectionRefusedError("Mock Driver cannot connect with USB")

        if self.connection is None:
            raise ConnectionRefusedError("ch341 connect did not return a connection.")

    def close(self):
        self.pipe_channel("close()")
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def write(self, bytes_to_write):
        """
        Writes data to the queue, this will be moved into the buffer by the thread in a threadsafe manner.

        :param bytes_to_write: data to write to the queue.
        :return:
        """
        f = bytes_to_write.find(b"~")
        if f != -1:
            # ~ was found in bytes. We are in a realtime exception.
            self.realtime = True

            # All code prior to ~ is sent to normal write.
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

        self.pipe_channel("write(%s)" % str(bytes_to_write))
        self._queue_lock.acquire(True)
        self._queue += bytes_to_write
        self._queue_lock.release()
        self.start()
        self.update_buffer()
        return self

    def realtime_write(self, bytes_to_write):
        """
        Writes data to the preempting commands, this will be moved to the front of the buffer by the thread
        in a threadsafe manner.

        :param bytes_to_write: data to write to the front of the queue.
        :return:
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
        self.pipe_channel("realtime_write(%s)" % str(bytes_to_write))
        self._preempt_lock.acquire(True)
        self._preempt = bytearray(bytes_to_write) + self._preempt
        self._preempt_lock.release()
        self.start()
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
                thread_name="LhyPipe(%s)" % self.context.path,
                result=self.stop,
            )
            self._thread.stop = self.stop
            self.update_state(STATE_INITIALIZE)

    def _pause_busy(self):
        """
        BUSY can be called in a paused state to packet halt the controller.

        This can only be done from PAUSE..
        """
        if self.state != STATE_PAUSE:
            self.pause()
        if self.state == STATE_PAUSE:
            self.update_state(STATE_BUSY)

    def _resume_busy(self):
        """
        Resumes from a BUSY to restore the controller. This will return to a paused state.

        This can only be done from BUSY.
        """
        if self.state == STATE_BUSY:
            self.update_state(STATE_PAUSE)
            self.resume()

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
        self._buffer = bytearray()
        self._queue = bytearray()
        self.context.signal("pipe;buffer", 0)
        self.update_state(STATE_TERMINATE)

    def reset(self):
        self.update_state(STATE_INITIALIZE)

    def stop(self, *args):
        self.abort()
        try:
            if self._thread is not None:
                self._thread.join()  # Wait until stop completes before continuing.
            self._thread = None
        except RuntimeError:
            pass  # Stop called by current thread.

    def abort_retry(self):
        self.aborted_retries = True
        self.context.signal("pipe;state", "STATE_FAILED_SUSPENDED")

    def continue_retry(self):
        self.aborted_retries = False
        self.context.signal("pipe;state", "STATE_FAILED_RETRYING")

    def usb_release(self):
        self.connection.release()

    def usb_reset(self):
        self.connection.reset()

    def update_state(self, state):
        if state == self.state:
            return
        self.state = state
        if self.context is not None:
            self.context.signal("pipe;thread", self.state)

    def update_buffer(self):
        if self.context is not None:
            self.context._buffer_size = (
                len(self._realtime_buffer) + len(self._buffer) + len(self._queue)
            )
            self.context.signal("pipe;buffer", len(self))

    def update_packet(self, packet):
        # self.context.signal("pipe;packet", convert_to_list_bytes(packet))
        self.context.signal("pipe;packet_text", packet)
        if self.usb_send_channel:
            self.usb_send_channel(packet)

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self._main_lock.acquire(True)
        self.count = 0
        self.pre_ok = False
        self.is_shutdown = False
        while self.state != STATE_END and self.state != STATE_TERMINATE:
            if self.state == STATE_INITIALIZE:
                # If we are initialized. Change that to active since we're running.
                self.update_state(STATE_ACTIVE)
            if self.state in (STATE_PAUSE, STATE_BUSY, STATE_SUSPEND):
                # If we are paused just keep sleeping until the state changes.
                if len(self._realtime_buffer) == 0 and len(self._preempt) == 0:
                    # Only pause if there are no realtime commands to queue.
                    self.context.signal("pipe;running", False)
                    time.sleep(0.25)
                    continue
            if self.aborted_retries:
                self.context.signal("pipe;running", False)
                time.sleep(0.25)
                continue
            try:
                # We try to process the queue.
                queue_processed = self.process_queue()
                if self.refuse_counts:
                    self.context.signal("pipe;failing", 0)
                self.refuse_counts = 0
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
            except ConnectionRefusedError:
                # The attempt refused the connection.
                self.refuse_counts += 1
                self.pre_ok = False
                if self.refuse_counts >= 5:
                    self.context.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.context.signal("pipe;failing", self.refuse_counts)
                self.context.signal("pipe;running", False)
                time.sleep(3)  # 3 second sleep on failed connection attempt.
                continue
            except ConnectionError:
                # There was an error with the connection, close it and try again.
                self.connection_errors += 1
                self.pre_ok = False

                self.context.signal("pipe;running", False)
                time.sleep(0.5)
                self.close()
                continue
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
            self.context.signal("pipe;running", queue_processed)
        self._thread = None
        self.is_shutdown = False
        self.update_state(STATE_END)
        self.pre_ok = False
        self.context.signal("pipe;running", False)
        self._main_lock.release()

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

        :return: queue process success.
        """
        if len(self._queue):  # check for and append queue
            self._queue_lock.acquire(True)
            self._buffer += self._queue
            self._queue = bytearray()
            self._queue_lock.release()
            self.update_buffer()

        if len(self._preempt):  # check for and prepend preempt
            self._preempt_lock.acquire(True)
            self._realtime_buffer += self._preempt
            self._preempt = bytearray()
            self._preempt_lock.release()
            self.update_buffer()

        if len(self._realtime_buffer) > 0:
            buffer = self._realtime_buffer
            realtime = True
        else:
            if len(self._buffer) > 0:
                buffer = self._buffer
                realtime = False
            else:
                # The buffer and realtime buffers are empty. No packet creation possible.
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
            if packet.endswith(b"-"):  # wait finish
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
                self.state = STATE_TERMINATE
                self.is_shutdown = True
                packet = packet[:-1]
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
        if not realtime and self.state in (STATE_PAUSE, STATE_BUSY):
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
            for attempts in range(300):
                # We'll try to confirm this at 300 times.
                try:
                    self.update_status()
                    status = self._status[1]
                except ConnectionError:
                    # Errors are ignored, must confirm packet.
                    flawless = False
                    continue
                if status == 0:
                    # We did not read a status.
                    continue
                elif status == STATUS_OK:
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
            if status == 0:  # After 300 attempts we could only get status = 0.
                raise ConnectionError  # Broken pipe. 300 attempts. Could not confirm packet.
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
        while self.state != STATE_TERMINATE:
            self.update_status()
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
        if self.state != STATE_PAUSE:
            self.pause()

        while True:
            if self.state != STATE_WAIT:
                self.update_state(STATE_WAIT)
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
                return  # Wait abort was requested.
        self.update_state(original_state)

    @property
    def type(self):
        return "lhystudios"
