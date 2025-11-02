"""
UDP Connection handles Ruida UDP data sending and receiving and the Ruida protocols therein.
"""

import socket
import queue
import struct

from meerk40t.ruida.rdjob import ACK, NAK, KEEP_ALIVE, ERR

class UDPConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.safe_label
        self.recv = service.channel(f"{name}/recv", pure=True)
        self.send = service.channel(f"{name}/send", pure=True)
        self.events = service.channel(f"{name}/events", pure=True)
        self.is_shutdown = False
        self.recv_address = None
        self.send_port = 50200
        self.listen_port = 40200
        self.ctrl_port = 50207
        self.ctrl_listen_port = 40207
        self.socket = None
        self.swizzle = None
        self.unswizzle = None
        self.send_q = queue.Queue(2 ** 18) # Power of 2 for efficiency.
        self._q_to = 0.25 # Queue timeout.
        self._s_to = 1.0 # UDP socket timeout.
        self._tries = 40

    # Should verify type is a callable method.
    def set_swizzles(self, swizzle, unswizzle):
        self.swizzle = swizzle
        self.unswizzle = unswizzle

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    def open(self):
        if self.connected:
            return
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # TODO: Want non-blocking. Handling send/rcv using states and blocking
        # on the send queue.
        self.socket.settimeout(self._s_to)
        self.socket.bind(("", self.listen_port))

        name = self.service.safe_label
        self.service.threaded(
            self._ruida_handshaker, thread_name=f"thread-{name}", daemon=True
        )
        # TODO: usb_status is a misnomer.
        self.service.signal("pipe;usb_status", "Opened")
        self.events("Disconnected")

    def close(self):
        if not self.connected:
            return
        self.socket.close()
        self.socket = None

    @property
    def is_connecting(self):
        return False

    @property
    def connected(self):
        return not self.is_shutdown and self.socket is not None

    def abort_connect(self):
        pass

    def write(self, data):
        '''Provide double buffered data transmission.

        This blocks for a short time when the queue is full and retries a number
        of times for a total of approximately 4 seconds before giving up.

        TODO: What does the calling method do in the case of timeout? How to
        inform the calling method a timeout occurred?
        '''
        self.open()
        # Blocks when queue is full.
        _tries = 12 # Approximately 4 seconds.
        while _tries:
            try:
                self.send_q.put(data, timeout=self._q_to)
                break
            except queue.Full:
                _tries -= 1
                if _tries == 0:
                    self.service.signal("warning", "Ruida", "Send queue FULL")
                continue
        self.send(data) # TODO: Where this goes is not known at this time.

    def _package(self, data):
        _data = self.swizzle(data)
        return struct.pack(">H", sum(_data) & 0xFFFF) + _data

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
        self.sends = 0
        self.acks = 0
        self.naks = 0
        self.keep_alives = 0
        self.replies = 0
        _ack_pending = False
        _reply_pending = False
        _responding = False
        try:
            while True: # Run forever -- until shutdown externally.
                # Be sure to allow context switching so the GUI remains
                # responsive.

                # IDLE
                while True: # Block here for IDLE state.
                    try: # NOTE: The queue will be empty if not opened.
                        # Don't block forever because some earlier versions
                        # of Python and on Windows will not respond to
                        # a keyboard interrupt.
                        _message = self.send_q.get(timeout=self._q_to)
                        break
                    except queue.Empty:
                        continue
                    # TODO: Could add a sanity check on connect state.

                # Transition
                # Check for only KNOWN command expecting a reply.
                if (_message[0] == 0xDA and
                    _message[1] != 0x01): # 0x01 is a memory set -- no reply.
                    _reply_pending = True
                    self.events('Expecting reply data.')
                _packet = self._package(_message)
                self.socket.sendto(_packet,
                                   (self.service.address, self.send_port))
                _ack_pending = True

                # ACK_PENDING
                _tries = self._tries
                while _ack_pending:
                    try:
                        _data, _address = self.socket.recvfrom(1024)
                    except (socket.timeout, AttributeError):
                        # Handle a receive timeout. This may be the result of a
                        # loss of sync or the controller is no longer responding.
                        # NOTE: This will occur while the controller is executing
                        # a physical home.
                        _tries -= 1
                        if _tries:
                            _enq = self._package(KEEP_ALIVE)
                            # self.socket.sendto(_enq,
                            #        (self.service.address, self.send_port))
                            continue
                        else:
                            # Comms failure.
                            if _responding: # If was responding.
                                self.service.signal(
                                    "pipe;usb_status", "Disconnected")
                                self.events("Disconnected")
                            _responding = False
                            _ack_pending = False
                            _reply_pending = False
                            break
                    if _address is not None:
                        # TODO: Need to understand how the address can be used
                        # further connection sanity checking.
                        self.recv_address = _address
                    if not _responding:
                        self.service.signal(
                            "pipe;usb_status", "Connected")
                        self.events("Connected")
                    _responding = True
                    _ack = self.unswizzle(_data)
                    if len(_ack) == 1:
                        if _ack == ACK:
                            # Signal that the next message can be sent.
                            _ack_pending = False
                            self.acks += 1
                        elif _ack == NAK:
                            self.socket.sendto(_packet,
                                   (self.service.address, self.send_port))
                            self.naks += 1
                        elif _ack == KEEP_ALIVE:
                            self.keep_alives += 1
                    else:
                        self.events('Reply data when expecting ACK.')
                        # Reply data in response to a command. Forward to be
                        # processed.
                        self.replies += 1
                        _reply_pending = False
                        # TODO: May need a way to restore sync.
                        self.recv(_ack) # Just in case

                # REPLY_PENDING
                _tries = 4
                while _reply_pending:
                    try:
                        _data, _address = self.socket.recvfrom(1024)
                        self.recv_address = _address
                        # TODO: Add address sanity check?
                        _reply_pending = False
                        self.replies += 1
                        _reply = self.unswizzle(_data)
                        self.recv(_reply) # Forward to client.
                    except socket.error as e:
                        if e.errno in [socket.EWOULDBLOCK, socket.EAGAIN]:
                            _tries -= 1
                        if _tries:
                            continue
                        else:
                            self.recv(None) # Inform the upper layer of failure.
                            self.events('Time out when expecting data.')
                            break
        except OSError:
            pass
