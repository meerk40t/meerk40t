'''
Ruida Session

Establish, manage and terminate communications sessions with a Ruida controller.
This occupies the Session Layer (Layer 5) of the OSI model.

This layer establishes and maintains a communications session with a Ruida
controller. It also restores the session following a communications failure.
e.g. when the Ruida controller has been turned off.

Because the Ruida controller receives and sends swizzled data and this layer
needs to know when communications has failed or is out of sync, swizzling
occurs within this layer.

Data transfers between the presentation layer (controller.py) and the transport
layer are also performed by this layer because doing so requires an active
session and swizzling.

Upper layers are notified of changes in communications status using signals and
events defined by the service. Reply data from the Ruida controller are
forwarded to the upper layers using the service recv channel.

NOTE: Because the Ruida controller behaves differently depending upon which
transport layer is used there is some transport dependent handshake and
connect specific code.
'''
import queue
import struct
import time
import threading

from meerk40t.kernel import Service

from .rdjob import ACK, NAK, ENQ, GET_SETTING, MEM_MACHINE_STATUS

from .ruidatransport import RuidaTransport, TransportTimeout, TransportError
import meerk40t.ruida.udp_transport as udp
import meerk40t.ruida.usb_transport as usb
# TODO: Define Session exceptions.

class RuidaSession:
    def __init__(self, service: Service):
        self.service = service
        self.interface = service.interface
        name = self.service.safe_label
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.send = service.channel(f"{name}/send", pure=True)
        self.events = service.channel(f"{name}/events", pure=True)

        self.transport = None

        # Ruida data
        # TODO: Tune the queue size.
        self.send_q = queue.Queue(2 ** 18) # Power of 2 for efficiency.
        self._q_to = 0.25 # Queue timeout.
        self.swizzle = None
        self.unswizzle = None

        # Status
        self._responding = False
        self._ack_pending = False
        self._reply_pending = False

        # Stats for test and debug.
        self.sends = 0
        self.acks = 0
        self.naks = 0
        self.replies = 0
        self.enqs = 0
        self.dropped_packets = 0

        # Session thread.
        self._handshake_thread = None
        self._timeout = 0.25
        self._tries = 4
        self._is_shutdown = True
        self._shutdown = False
        if self._handshake_thread is None:
            self._handshake_thread = threading.Thread(
                    target=self._ruida_handshaker,
                    daemon=True) # TODO: Can this leave connections open?
            self._handshake_thread.start()

    def __del__(self):
        self.shutdown()

    def set_swizzles(self, swizzle, unswizzle):
        self.swizzle = swizzle
        self.unswizzle = unswizzle

    def open(self):
        '''This is a stub because the connect opens the transport.'''
        return

    def _open(self):
        if self.is_open:
            return
        if self.transport is None:
            if self.interface == 'udp':
                self.transport = udp.UDPTransport(self.service)
            elif self.interface == 'usb':
                self.transport = usb.USBTransport(self.service)
            else:
                raise AttributeError(
                    f'Unsupported transport interface: {self.interface}')
        try:
            self.transport.open()
        except TransportError:
            return
        self.transport.set_timeout(self._timeout)
        # TODO: usb_status is a misnomer.
        self.service.signal("pipe;usb_status", "Opened")
        self.events("Disconnected")

    def close(self):
        if self.transport is None:
            return
        self.transport.close()
        self.transport = None
        self.service.signal("pipe;usb_status", "Disconnected")
        self.events("Disconnected")

    def shutdown(self, *args, **kwargs):
        if not self._is_shutdown:
            self._shutdown = True
            while not self._is_shutdown:
                continue
            self._handshake_thread.join()
            self._handshake_thread = None
            self.close()

    def set_timeout(self, seconds):
        '''Set the receive timeout.

        NOTE: This changes the number of tries for receiving data. It doesn't
        change the timeout of the transport interface.
        '''
        self._tries = int(seconds / self._timeout)

    def location(self):
        if self.transport is not None:
            return self.transport.location()
        raise AttributeError # This is excepted in devicepanel.py.

    @property
    def is_open(self):
        return self.transport is not None and self.transport.is_open

    @property
    def is_connecting(self):
        return not self._responding

    @property
    def connected(self):
        return (not self._is_shutdown
                and self._responding
                and (self.transport is not None
                     and self.transport.connected))

    @property
    def is_busy(self):
        return self._reply_pending or self._ack_pending

    def abort_connect(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None
            self._open()

    def write(self, data):
        '''Provide double buffered data transmission.

        This blocks for a short time when the queue is full and retries a number
        of times for a total of approximately 4 seconds before giving up.

        TODO: What does the calling method do in the case of timeout? How to
        inform the calling method a timeout occurred?
        '''
        # Blocks when queue is full.
        _tries = 12 # Approximately 4 seconds.
        while _tries:
            if not self.connected:
                # Callers of this method should be ready for this and retry
                # if necessary. Don't want to wait here for a connection to
                # be established -- the controller could be powered down.
                raise ConnectionError('Not connected to the Ruida controller.')
            try:
                self.send_q.put(data, timeout=self._q_to)
                break
            except queue.Full:
                _tries -= 1
                if _tries <= 0:
                    self.service.signal("warning", "Ruida", "Send queue FULL")
                continue
        # self.send(data) # TODO: Where this goes is not known at this time.

    def _package(self, data):
        _data = self.swizzle(data)
        if self.interface == 'udp':
            return struct.pack(">H", sum(_data) & 0xFFFF) + _data
        else:
            return _data

    def update_connect_status(self):
        if self.connected:
            _msg = f'Connected: {self.interface} '
            if hasattr(self.transport, 'serial_port'):
                _msg += f'{self.transport.serial_port}'
            elif hasattr(self.transport, 'send_address'):
                _msg += f'{self.transport.send_address}'
            else:
                _msg += 'unknown'
            self.service.signal("pipe;usb_status", _msg)
            self.events(_msg)
        else:
            self.service.signal("pipe;usb_status", "Connecting")
            self.events("Connecting")

    def connect(self):
        '''Initiate or restore comms session with the Ruida controller.

        This happens during startup and when a comms failure occurs. All
        other comms stop until the connection has been verified.

        NOTE: This is intended to run only in the context of the handshaker
         or status monitor (controller.py) threads.
        '''
        # Wait for init to complete. Need the swizzle method from RDJob.
        # TODO: Has the chicken/egg been resolved?
        while self.swizzle is None or self.unswizzle is None:
            time.sleep(0.25)
        if not self.connected:
            self.update_connect_status()
            self._open()
            if self.interface == 'udp':
                _enq = self._package(ENQ)
                _ack = ACK  # True at least for the 6442S. Other controllers
                            # may actually reply with an ENQ?
            elif self.interface == 'usb':
                # When comms is via USB there are no ACK responses so read
                # mem to get a response.
                _enq = self._package(GET_SETTING + MEM_MACHINE_STATUS)
                _ack = b'\xDA\x01' # Indicates a memory read reply.
            else:
                raise TransportError(
                    f'Interface {self.interface} not supported.')
            while not self.connected and not self._shutdown:
                self._ack_pending = True # This causes a is_busy to be True.
                # When the controller is running it should respond immediately.
                try:
                    self.transport.write(_enq)
                    self.enqs += 1
                    _data = self.transport.read(len(_ack))
                    _reply = self.unswizzle(_data)
                    if len(_reply) == len(_ack) and _reply == _ack:
                        self._ack_pending = False
                        self._reply_pending = False
                        self._responding = True

                except (TransportTimeout, TransportError, AttributeError):
                    # Still not responding.
                    time.sleep(1)
                    if self.interface == 'usb':
                        # Try until the OS figures out the USB device.
                        try:
                            if self.transport is None:
                                self._open()
                            else:
                                self.transport.close()
                            self.transport.open()
                        except TransportError:
                            pass
                    continue
                # Drop any replies the controller had been saving to confuse
                # drivers with.
                # Put try/except TransportError and set responding False.
                try:
                    _data = self.transport.purge()
                    self.dropped_packets += 1
                except TransportError:
                    self._responding = False
            # Prime the pump to get things rolling.
            self.send_q.put(_enq, timeout=self._q_to)
            self.update_connect_status()

    def _ruida_handshaker(self):
        '''This is a thread which handles the SEND - ACK - REPLY handshake.

        The purpose is to guarantee message sync and graceful failure handling.
        Sync is required because UDP is a fire and forget protocol and does
        not support sequence numbers.

        The Ruida protocol is a speak only when spoken to protocol meaning
        the Ruida controller doesn't send anything unless it receives a command.
        In most cases the response is a simple ACK but with some commands the
        controller follows the ACK with data.

        Because it is necessary to know when reply data is expected, swizzling
        occurs in this thread.

        This is a brute force state machine containing 3 states:
            IDLE            Waiting for data to be sent.
            ACK_PENDING     Data has been sent and need an acknowledge.
            REPLY_PENDING   A command was sent which requires a reply from the
                            controller.

        Some internal stats are maintained to aid failure diagnosis.
            sends   Number of messages sent.
            acks    Number of ACKs received in reply
            naks    The number of NAKs triggering a resend of a message.
            replies The number of reply data packets received.
        '''
        self._ack_pending = False
        self._responding = False
        self._is_shutdown = False
        while not self._shutdown:
            try:
                # Be sure to allow context switching so the GUI remains
                # responsive.
                # Also shutdown can happen any time this thread is waiting.
                # IDLE
                _message = None
                self.connect()
                while self.connected and not self._shutdown:
                    # Block here for IDLE state.
                    try: # NOTE: The queue will be empty if not opened.
                        # Don't block forever because some earlier versions
                        # of Python and on Windows will not respond to
                        # a keyboard interrupt.
                        _message = self.send_q.get(timeout=self._q_to)
                        break
                    except queue.Empty:
                        continue
                    # TODO: Could add a sanity check on connect state.
                if self._shutdown or _message is None:
                    continue
                # Transition
                # Check for only KNOWN command expecting a reply.
                if (_message[0] == 0xDA
                        and _message[1] != 0x01): # 0x01 is a memory set -- no reply.
                    self._reply_pending = True
                _packet = self._package(_message)
                try:
                    self.transport.write(_packet)
                except TransportError:
                    self._responding = False
                self.sends += 1
                if self.interface == 'udp':
                    self._ack_pending = True

                # ACK_PENDING
                _tries = self._tries
                while self._ack_pending:
                    try:
                        _data = self.transport.read(1)
                    except (TransportTimeout, TransportError, AttributeError):
                        # Handle a receive timeout. This may be the result of a
                        # loss of sync or the controller is no longer responding.
                        # NOTE: This will occur while the controller is executing
                        # a physical home.
                        _tries -= 1
                        if _tries:
                            continue
                        else:
                            # Comms failure.
                            self._responding = False
                            self._ack_pending = False
                            self._reply_pending = False
                            break
                    _ack = self.unswizzle(_data)
                    if len(_ack) == 1:
                        if _ack == ACK:
                            # Signal that the next message can be sent.
                            self._responding = True
                            self._ack_pending = False
                            self.acks += 1
                        elif _ack == NAK:
                            try:
                                self.transport.write(_packet)
                            except TransportError:
                                self._responding = False
                                self._ack_pending = False
                            self.naks += 1
                        elif _ack == ENQ:
                            self.enqs += 1
                    else:
                        if len(_ack) > 0:
                            self.events('Reply data when expecting ACK.')
                            # Reply data in response to a command. Forward to be
                            # processed.
                            self.replies += 1
                            self._reply_pending = False
                            # TODO: May need a way to restore sync.
                            self.recv(_ack) # Just in case

                # REPLY_PENDING
                _tries = self._tries
                while self._reply_pending:
                    try:
                        _data = self.transport.read(9) # Length is USB only.
                        self._reply_pending = False
                        self.replies += 1
                        _reply = self.unswizzle(_data)
                        self.recv(_reply) # Forward to client.
                    except (TransportTimeout, AttributeError):
                        if _tries >= 0:
                            _tries -= 1
                        else:
                            self._responding = False
                            self.recv(None) # Inform the upper layer of failure.
                            self.events('Time out when expecting data.')
                            break
            except OSError:
                if self._responding:
                    self.service.signal(
                        "pipe;usb_status", "Ruida comms ERROR")
                    self.events("Ruida comms error.")
                    self._responding = False
        self._is_shutdown = True
