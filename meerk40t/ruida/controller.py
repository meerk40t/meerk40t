"""
Ruida Encoder

The Ruida Encoder is responsible for turning function calls into binary ruida data.
"""
import queue
import socket
import struct
import threading
import time

from meerk40t.ruida.rdjob import (
    ACK,
    KEEP_ALIVE,
    MEM_BED_SIZE_X,
    MEM_BED_SIZE_Y,
    MEM_CARD_ID,
    MEM_CURRENT_X,
    MEM_CURRENT_Y,
    MEM_CURRENT_Z,
    MEM_CURRENT_U,
    NAK,
    RDJob,
    STATUS_ADDRESSES,
)


class RuidaController:
    """
    Implements the Ruida protocol data sending with connection-agnostic protocol handling.
    """

    def __init__(self, service, connection=None, magic=-1):
        self.service = service
        self.connection = connection
        self.mode = "init"
        self.paused = False

        # Legacy write pipe for backward compatibility with swizzle application
        if connection:
            def _swizzled_write(data):
                if self.job.swizzle:
                    data = self.job.swizzle(data)
                return connection.write(data)
            self.write = _swizzled_write
        else:
            self.write = None

        self.job = RDJob()
        self._send_queue = []
        self._send_thread = None
        self.events = service.channel(f"{service.safe_label}/events")
        self._status_thread_sleep = 0.25 # Time between polls.
        self._connected = False
        self._job_lock = threading.Lock() # To allow running a job.
        self._status_thread = threading.Thread(
            target=self._status_monitor, daemon=True)
        self._status_thread.start()
        self._expect_status = None
        self.card_id = b''
        self.bed_x = -1.0
        self.bed_y = -1.0
        self.x = -1.0
        self.y = -1.0
        self.z = -1.0
        self.u = -1.0

        # Protocol handling state (moved from UDP connection)
        self.send_q = queue.Queue(2 ** 18)  # Power of 2 for efficiency.
        self._q_to = 0.25  # Queue timeout.
        self._s_to = 1.0   # Socket timeout.
        self._tries = 40
        self._protocol_thread = None
        self._shutdown = False

    def start_protocol_handler(self):
        """Start the protocol handler thread for reliable communication."""
        if self._protocol_thread is None:
            self._shutdown = False
            self._protocol_thread = threading.Thread(
                target=self._ruida_protocol_handler, daemon=True
            )
            self._protocol_thread.start()

    def stop_protocol_handler(self):
        """Stop the protocol handler thread."""
        self._shutdown = True
        if self._protocol_thread:
            self._protocol_thread.join(timeout=1.0)
            self._protocol_thread = None

    def _package_data(self, data):
        """Package data with checksum and swizzle for transmission."""
        if self.job.swizzle:
            data = self.job.swizzle(data)
        return struct.pack(">H", sum(data) & 0xFFFF) + data

    def _ruida_protocol_handler(self):
        """
        Connection-agnostic Ruida protocol handler.

        This handles the SEND - ACK - REPLY handshake for reliable communication
        across all connection types. The protocol ensures message sync and
        graceful failure handling.

        State machine with 3 states:
            IDLE: Waiting for data to be sent
            ACK_PENDING: Data sent, waiting for acknowledge
            REPLY_PENDING: Command sent which requires reply from controller
        """
        self.sends = 0
        self.acks = 0
        self.naks = 0
        self.keep_alives = 0
        self.replies = 0
        _ack_pending = False
        _reply_pending = False
        _responding = False

        try:
            while not self._shutdown:
                # IDLE - Wait for data to send
                while not self._shutdown:
                    try:
                        _message = self.send_q.get(timeout=self._q_to)
                        break
                    except queue.Empty:
                        continue

                if self._shutdown:
                    break

                # Check if this command expects a reply
                if (_message[0] == 0xDA and _message[1] != 0x01):  # 0x01 is memory set
                    _reply_pending = True
                    self.events('Expecting reply data.')

                # Send the packaged data
                _packet = self._package_data(_message)
                if self.connection:
                    self.connection.send(_packet)
                _ack_pending = True

                # ACK_PENDING - Wait for acknowledgment
                _tries = self._tries
                while _ack_pending and not self._shutdown:
                    try:
                        # For different connection types, this will behave differently
                        if self.connection and hasattr(self.connection, 'recv'):
                            _data = self.connection.recv()
                        else:
                            # Fallback for connections without recv or no connection
                            time.sleep(0.1)
                            continue

                        if _data is None:
                            continue

                    except (socket.timeout, AttributeError, OSError):
                        # Handle timeout - may indicate controller is busy (e.g., homing)
                        _tries -= 1
                        if _tries:
                            # Send keep-alive to maintain connection
                            if self.connection and hasattr(self.connection, 'send'):
                                _enq = self._package_data(KEEP_ALIVE)
                                self.connection.send(_enq)
                            continue
                        else:
                            # Communication failure
                            if _responding:
                                self.service.signal("pipe;usb_status", "disconnected")
                                self.events("Disconnected")
                            _responding = False
                            _ack_pending = False
                            _reply_pending = False
                            break

                    # Process received data
                    if not _responding:
                        self.service.signal("pipe;usb_status", "connected")
                        self.events("Connected")
                    _responding = True

                    if self.job.unswizzle:
                        _ack = self.job.unswizzle(_data)
                    else:
                        _ack = _data

                    if len(_ack) == 1:
                        if _ack == ACK:
                            _ack_pending = False
                            self.acks += 1
                        elif _ack == NAK:
                            # Resend the packet
                            if self.connection and hasattr(self.connection, 'send'):
                                self.connection.send(_packet)
                            self.naks += 1
                        elif _ack == KEEP_ALIVE:
                            self.keep_alives += 1
                    else:
                        # Reply data when expecting ACK
                        self.events('Reply data when expecting ACK.')
                        self.replies += 1
                        _reply_pending = False
                        # Forward reply data
                        if hasattr(self.connection, 'recv_channel'):
                            self.connection.recv_channel(_ack)

                # REPLY_PENDING - Wait for reply data
                _tries = 4
                while _reply_pending and not self._shutdown:
                    try:
                        if self.connection and hasattr(self.connection, 'recv'):
                            _data = self.connection.recv()
                        else:
                            time.sleep(0.1)
                            continue

                        if _data is None:
                            continue

                        self.recv_address = getattr(self.connection, 'recv_address', None)
                        _reply_pending = False
                        self.replies += 1

                        if self.job.unswizzle:
                            _reply = self.job.unswizzle(_data)
                        else:
                            _reply = _data

                        # Forward reply to client
                        if hasattr(self.connection, 'recv_channel'):
                            self.connection.recv_channel(_reply)
                        break

                    except (socket.error, OSError) as e:
                        if hasattr(e, 'errno') and e.errno in [socket.EWOULDBLOCK, socket.EAGAIN]:
                            _tries -= 1
                        if _tries:
                            continue
                        else:
                            # Inform upper layer of failure
                            if hasattr(self.connection, 'recv_channel'):
                                self.connection.recv_channel(None)
                            self.events('Timeout when expecting data.')
                            break

        except OSError:
            pass
        self._last_card_id = b''
        self._last_bed_x = -1.0
        self._last_bed_y = -1.0
        self._last_x = 0.0
        self._last_y = 0.0
        self._last_z = 0.0
        self._last_u = 0.0

    def start_sending(self):
        self._send_thread = threading.Thread(target=self._data_sender, daemon=True)
        self.events("Sending File...")
        self.divide_data_into_queue()
        self.events(f"File in {len(self._send_queue)} chunk(s)")
        self._send_thread.start()

    def divide_data_into_queue(self):
        last = 0
        total = 0
        data = self.job.buffer
        for i, command in enumerate(data):
            total += len(command)
            if total > 1000:
                self._send_queue.append(self.job.get_contents(last, i))
                last = i
                total = 0
        if last != len(data):
            self._send_queue.append(self.job.get_contents(last))

    @property
    def busy(self):
        return self._expect_status is not None

    def sync_coords(self):
        '''
        Sync native coordinates with device coordinates.

        This is typically used after actions such as physical home.'''
        while self.busy:
            time.sleep(self._status_thread_sleep)
        self.service.driver.native_x = self.service.driver.device_x
        self.service.driver.native_y = self.service.driver.device_y

    def _data_sender(self):
        '''Data send thread.

        This is a transient thread which is created after job data has been
        queued. This runs until the queue is empty at which point it
        terminates. Now uses the protocol handler for reliable transmission.'''
        self._job_lock.acquire()
        while self._send_queue:
            data = self._send_queue.pop(0)
            # Queue data for protocol handler instead of direct write
            _tries = 12  # Approximately 4 seconds
            while _tries:
                try:
                    self.send_q.put(data, timeout=self._q_to)
                    break
                except queue.Full:
                    _tries -= 1
                    if _tries == 0:
                        self.service.signal("warning", "Ruida", "Send queue FULL")
                    continue
        self._send_queue.clear()
        self._send_thread = None
        self.events("File Sent.")
        self._job_lock.release()

    def _status_monitor(self):
        '''Status monitoring thread.

        The thread runs continually to monitor connection status with a
        Ruida controller. It also updates the UI when status changes.

        NOTE: This thread is blocked while _data_sender is running.'''
        self._expect_status = None
        _next = 0
        try:
            while True:
                if self._expect_status is None:
                    self._job_lock.acquire() # Wait if running a job.
                    # Step through a series of commands and send/recv each one
                    # by one. When received, recv will update the UI.
                    _status = STATUS_ADDRESSES[_next]
                    self.job.get_setting(
                        _status, output=self.write)
                    self._expect_status = _status
                    _next += 1
                    if _next >= len(STATUS_ADDRESSES):
                        _next = 0
                    self._job_lock.release()
                time.sleep(self._status_thread_sleep)
        except OSError:
            pass

    def update_card_id(self, card_id):
        if self._expect_status == MEM_CARD_ID:
            self._expect_status = None
        if card_id != self.card_id:
            self.card_id = card_id
            # Signal the GUI update.

    def update_bed_x(self, bed_x):
        if self._expect_status == MEM_BED_SIZE_X:
            self._expect_status = None
        _bed_x = bed_x / 1000
        if _bed_x != self.bed_x:
            self.bed_x = _bed_x
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedwidth = f'{_bed_x:.1f}mm'
            self.service.signal('bedwidth', self.service.bedwidth)

    def update_bed_y(self, bed_y):
        if self._expect_status == MEM_BED_SIZE_Y:
            self._expect_status = None
        _bed_y = bed_y / 1000
        if _bed_y != self.bed_y:
            self.bed_y = _bed_y
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedheight = f'{_bed_y:.1f}mm'
            self.service.signal('bedheight', self.service.bedheight)

    def update_x(self, x):
        if self._expect_status == MEM_CURRENT_X:
            self._expect_status = None
        # TODO: Factor discovered by trial and error -- why necessary?
        # _x = x * 2.58
        _x = (self.bed_x * 1000 - x) * 2.58
        if True or _x != self.x:
            self.x = _x
            # Signal the GUI update.
            self.service.signal(
                "driver;position",
                (self._last_x, self._last_y, self.x, self.y))
            self._last_x = self.x
            # TODO: Updating native_x here causes intermittent move
            # behavior.
            self.service.driver.device_x = x

    def update_y(self, y):
        if self._expect_status == MEM_CURRENT_Y:
            self._expect_status = None
        # TODO: Factor discovered by trial and error -- why necessary?
        _y = y * 2.58
        if True or _y != self.y:
            self.y = _y
            # Signal the GUI update.
            self.service.signal(
                "driver;position",
                (self._last_x, self._last_y, self.x, self.y))
            self._last_y = self.y
            # TODO: Updating native_y here causes intermittent move
            # behavior.
            self.service.driver.device_y = y

    def update_z(self, z):
        if self._expect_status == MEM_CURRENT_Z:
            self._expect_status = None
        if z != self.z:
            self.z = z
            # Signal the GUI update.

    def update_u(self, u):
        if self._expect_status == MEM_CURRENT_U:
            self._expect_status = None
        if u != self.u:
            self.u = u
            # Signal the GUI update.

    _dispatch_lut = {
        MEM_CARD_ID: update_card_id,
        MEM_BED_SIZE_X: update_bed_x,
        MEM_BED_SIZE_Y: update_bed_y,
        MEM_CURRENT_X: update_x,
        MEM_CURRENT_Y: update_y,
        MEM_CURRENT_Z: update_z,
        MEM_CURRENT_U: update_u,
    }

    def recv(self, reply):
        '''Receive reply from the controller.

        The only reason this will be called is in response to a command
        which requires reply data from the controller. Forward to the
        RDJob for parsing.'''
        if reply is not None:
            _mem, _value, _decoded = self.job.decode_reply(reply)
            if _mem is not None:
                if _mem in self._dispatch_lut:
                    # Dispatch to the corresponding updater.
                    self._dispatch_lut[_mem](self, _value)
                self.events(
                    f"-->:Addr: {int.from_bytes(_mem):04X}={_value:08X}: {_decoded}")
                self._connected = True
        else:
            # Comm failure -- timeout.
            self._connected = False
            pass

    def start_record(self):
        self.job.get_setting(MEM_CARD_ID, output=self.write)
        self.job.clear()

    def stop_record(self):
        self.start_sending()

    @property
    def state(self):
        return "idle", "idle"

    def added(self):
        pass

    def service_detach(self):
        pass

    #######################
    # MODE SHIFTS
    #######################

    def rapid_mode(self):
        if self.mode == "rapid":
            return
        self.mode = "rapid"

    def raster_mode(self):
        self.program_mode()

    def program_mode(self):
        if self.mode == "rapid":
            return
        self.mode = "program"

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        pass

    #######################
    # Command Shortcuts
    #######################

    def wait_finished(self):
        pass

    def wait_ready(self):
        pass

    def wait_idle(self):
        pass

    def abort(self):
        self.mode = "rapid"
        self.job.stop_process(output=self.write)

    def pause(self):
        self.paused = True
        self.job.pause_process(output=self.write)

    def resume(self):
        self.paused = False
        self.job.restore_process(output=self.write)
