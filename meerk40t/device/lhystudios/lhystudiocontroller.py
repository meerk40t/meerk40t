import threading
import time

from ...kernel import (
    STATE_UNKNOWN,
    Module,
    STATE_ACTIVE,
    STATE_PAUSE,
    STATE_INITIALIZE,
    STATE_BUSY,
    STATE_IDLE,
    STATE_TERMINATE,
    STATE_END,
    STATE_WAIT,
)


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


class LhystudioController(Module):
    """
    K40 Controller controls the Lhystudios boards sending any queued data to the USB when the signal is not busy.

    This is registered in the kernel as a module. Saving a few persistent settings like packet_count and registering
    a couple controls like Connect_USB.

    This is also a Pipe. Elements written to the Controller are sent to the USB to the matched device. Opening and
    closing of the pipe are dealt with internally. There are three primary monitor data channels. 'send', 'recv' and
    'usb'. They display the reading and writing of information to/from the USB and the USB connection log, providing
    information about the connecting and error status of the USB device.
    """

    def __init__(self, context, name, channel=None, *args, **kwargs):
        Module.__init__(self, context, name, channel)
        self.state = STATE_UNKNOWN
        self.is_shutdown = False

        self._thread = None
        self._buffer = bytearray()  # Threadsafe buffered commands to be sent to controller.
        self._realtime_buffer = (
             bytearray()  # Threadsafe realtime buffered commands to be sent to the controller.
        )
        self._queue = bytearray()  # Thread-unsafe additional commands to append.
        self._preempt = bytearray()  # Thread-unsafe preempt commands to prepend to the buffer.
        self.context._buffer_size = 0
        self._queue_lock = threading.Lock()
        self._preempt_lock = threading.Lock()
        self._main_lock = threading.Lock()

        self._status = [0] * 6
        self._usb_state = -1

        self.driver = None
        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.pre_ok = False

        self.abort_waiting = False
        self.pipe_channel = context.channel("%s/events" % name)
        self.usb_log = context.channel("%s/usb" % name, buffer_size=20)
        self.usb_send_channel = context.channel("%s/usb_send" % name)
        self.recv_channel = context.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: context.signal("pipe;usb_status", e))

        send = context.channel("%s/send" % name)
        send.watch(self.write)
        send.__len__ = lambda: len(self._buffer) + len(self._queue)
        context.channel("%s/send_realtime" % name).watch(self.realtime_write)

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

    def initialize(self, *args, **kwargs):
        context = self.context

        @self.context.console_argument("filename", type=str)
        @self.context.console_command(
            "egv_import", help="Lhystudios Engrave Buffer Import. egv_import <egv_file>"
        )
        def egv_import(command, channel, _, filename, args=tuple(), **kwargs):
            if filename is None:
                raise SyntaxError

            def skip(read, byte, count):
                """Skips forward in the file until we find <count> instances of <byte>"""
                pos = read.tell()
                while count > 0:
                    char = read.read(1)
                    if char == byte:
                        count -= 1
                    if char is None or len(char) == 0:
                        read.seek(pos, 0)
                        # If we didn't skip the right stuff, reset the position.
                        break

            def skip_header(file):
                skip(file, "\n", 3)
                skip(file, "%", 5)

            with open(filename, "r") as f:
                skip_header(f)
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    buffer = bytes(data, "utf8")
                    self.write(buffer)
                self.write(b"\n")

        @self.context.console_argument("filename", type=str)
        @self.context.console_command(
            "egv_export", help="Lhystudios Engrave Buffer Export. egv_export <egv_file>"
        )
        def egv_export(command, channel, _, filename, args=tuple(), **kwargs):
            if filename is None:
                raise SyntaxError
            try:
                with open(filename, "w") as f:
                    f.write("Document type : LHYMICRO-GL file\n")
                    f.write("File version: 1.0.01\n")
                    f.write("Copyright: Unknown\n")
                    f.write("Creator-Software: %s v%s\n" % (self.context._kernel.name,
                                                            self.context._kernel.version))
                    f.write("\n")
                    f.write("%0%0%0%0%\n")
                    buffer = bytes(self._buffer)
                    buffer += bytes(self._queue)
                    f.write(buffer.decode("utf-8"))
            except (PermissionError, IOError):
                channel(_("Could not save: %s" % filename))

        @self.context.console_command(
            "egv", help="Lhystudios Engrave Code Sender. egv <lhymicro-gl>"
        )
        def egv(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel("Lhystudios Engrave Code Sender. egv <lhymicro-gl>")
            else:
                self.write(bytes(args[0].replace("$", "\n"), "utf8"))

        @self.context.console_command("usb_connect", help="Connect USB")
        def usb_connect(command, channel, _, args=tuple(), **kwargs):
            try:
                self.open()
            except ConnectionRefusedError:
                channel("Connection Refused.")

        @self.context.console_command("usb_disconnect", help="Disconnect USB")
        def usb_disconnect(command, channel, _, args=tuple(), **kwargs):
            if self.driver is not None:
                self.close()
            else:
                channel("Usb is not connected.")

        @self.context.console_command("start", help="Start Pipe to Controller")
        def pipe_start(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_ACTIVE)
            self.start()
            channel("Lhystudios Channel Started.")

        @self.context.console_command("hold", help="Hold Controller")
        def pipe_pause(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_PAUSE)
            self.pause()
            channel("Lhystudios Channel Paused.")

        @self.context.console_command("resume", help="Resume Controller")
        def pipe_resume(command, channel, _, args=tuple(), **kwargs):
            self.update_state(STATE_ACTIVE)
            self.start()
            channel("Lhystudios Channel Resumed.")

        @self.context.console_command("abort", help="Abort Job")
        def pipe_abort(command, channel, _, args=tuple(), **kwargs):
            self.reset()
            channel("Lhystudios Channel Aborted.")

        context.setting(int, "packet_count", 0)
        context.setting(int, "rejected_count", 0)

        context.register("control/Connect_USB", self.open)
        context.register("control/Disconnect_USB", self.close)
        context.register("control/Status Update", self.update_status)
        self.reset()

        def abort_wait():
            self.abort_waiting = True

        context.register("control/Wait Abort", abort_wait)

        def pause_k40():
            self.update_state(STATE_PAUSE)
            self.start()

        context.register("control/Pause", pause_k40)

        def resume_k40():
            self.update_state(STATE_ACTIVE)
            self.start()

        context.register("control/Resume", resume_k40)

        self.context.get_context("/").listen(
            "lifecycle;ready", self.on_controller_ready
        )

    def on_controller_ready(self, *args):
        self.start()

    def finalize(self, *args, **kwargs):
        self.context.get_context("/").unlisten(
            "lifecycle;ready", self.on_controller_ready
        )
        if self._thread is not None:
            self.write(b"\x18\n")

    def __repr__(self):
        return "LhystudioController()"

    def __len__(self):
        """Provides the length of the buffer of this device."""
        return len(self._buffer) + len(self._queue) + len(self._preempt)

    def open(self):
        self.pipe_channel("open()")
        if self.driver is None:
            self.detect_driver_and_open()
        else:
            # Update criteria
            self.driver.index = self.context.usb_index
            self.driver.bus = self.context.usb_bus
            self.driver.address = self.context.usb_address
            self.driver.serial = self.context.usb_serial
            self.driver.chipv = self.context.usb_version
            self.driver.open()
        if self.driver is None:
            raise ConnectionRefusedError

    def close(self):
        self.pipe_channel("close()")
        if self.driver is not None:
            self.driver.close()

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
                self._thread_data_send, thread_name="LhyPipe(%s)" % (self.context._path)
            )
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

    def stop(self):
        self.abort()
        self._thread.join()  # Wait until stop completes before continuing.

    def detect_driver_and_open(self):
        index = self.context.usb_index
        bus = self.context.usb_bus
        address = self.context.usb_address
        serial = self.context.usb_serial
        chipv = self.context.usb_version
        _ = self.usb_log._

        def state(state_value):
            self.context.signal("pipe;state", state_value)

        try:
            from ..ch341libusbdriver import CH341Driver

            self.driver = driver = CH341Driver(
                index=index,
                bus=bus,
                address=address,
                serial=serial,
                chipv=chipv,
                channel=self.usb_log,
                state=state,
            )
            driver.open()
            chip_version = driver.get_chip_version()
            self.usb_log(_("CH341 Chip Version: %d") % chip_version)
            self.context.signal("pipe;chipv", chip_version)
            self.usb_log(_("Driver Detected: LibUsb"))
            state("STATE_CONNECTED")
            self.usb_log(_("Device Connected.\n"))
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
            self.usb_log(_("PyUsb is not installed. Skipping."))

        try:
            from ..ch341windlldriver import CH341Driver

            self.driver = driver = CH341Driver(
                index=index,
                bus=bus,
                address=address,
                serial=serial,
                chipv=chipv,
                channel=self.usb_log,
                state=state,
            )
            driver.open()
            chip_version = driver.get_chip_version()
            self.usb_log(_("CH341 Chip Version: %d") % chip_version)
            self.context.signal("pipe;chipv", chip_version)
            self.usb_log(_("Driver Detected: CH341"))
            state("STATE_CONNECTED")
            self.usb_log(_("Device Connected.\n"))
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
            self.usb_log(_("No Windll interfacing. Skipping."))

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
            self.context.signal("pipe;buffer", self.context._buffer_size)

    def update_packet(self, packet):
        if self.context is not None:
            self.context.signal("pipe;packet", convert_to_list_bytes(packet))
            self.context.signal("pipe;packet_text", packet)
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
            if self.state == STATE_PAUSE or self.state == STATE_BUSY:
                # If we are paused just keep sleeping until the state changes.
                if len(self._realtime_buffer) == 0 and len(self._preempt) == 0:
                    # Only pause if there are no realtime commands to queue.
                    time.sleep(0.25)
                    continue
            try:
                # We try to process the queue.
                queue_processed = self.process_queue()
                self.refuse_counts = 0
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
            except ConnectionRefusedError:
                # The attempt refused the connection.
                self.refuse_counts += 1
                self.pre_ok = False
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
                self.pre_ok = False
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
                continue
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
        self._thread = None
        self.is_shutdown = False
        self.update_state(STATE_END)
        self.pre_ok = False
        self._main_lock.release()

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open, 'process_queue_pause = True' (anytime before packet sent),
        self._buffer is empty, or a failure to produce packet.

        Buffer will not be changed unless packet is successfully sent, or pipe commands are processed.

        - : tells the system to require wait finish at the end of the queue processing.
        * : tells the system to clear the buffers, and abort the thread.
        ! : tells the system to pause.
        & : tells the system to resume.
        \x18 : tells the system to quit.

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
        if packet.endswith((b"-", b"*", b"&", b"!", b"#", b"\x18")):
            packet += buffer[length : length + 1]
            length += 1
        post_send_command = None

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
        if self.context.mock:
            _ = self.usb_log._
            self.usb_log(_("Using Mock Driver."))
        else:
            self.open()

        if len(packet) == 30:
            # We have a sendable packet.
            if not self.pre_ok:
                self.wait_until_accepting_packets()
            self.send_packet(packet)

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
            self._realtime_buffer = self._realtime_buffer[length:]
        else:
            self._buffer = self._buffer[length:]
        self.update_buffer()

        if post_send_command is not None:
            # Post send command could be wait_finished, and might have a broken pipe.
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        packet = b"\x00" + packet + bytes([onewire_crc_lookup(packet)])
        if self.context.mock:
            time.sleep(0.04)
        else:
            self.driver.write(packet)
        self.update_packet(packet)
        self.pre_ok = False

    def update_status(self):
        if self.context.mock:
            from random import randint

            if randint(0, 500) == 0:
                self._status = [255, STATUS_ERROR, 0, 0, 0, 1]
            else:
                self._status = [255, STATUS_OK, 0, 0, 0, 1]
            time.sleep(0.01)
        else:
            self._status = self.driver.get_status()
        if self.context is not None:
            self.context.signal("pipe;status", self._status, get_code_string_from_code(self._status[1]))
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
            if self.context.mock:  # Mock controller
                self._status = [255, STATUS_FINISH, 0, 0, 0, 1]
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
