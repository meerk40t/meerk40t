'''Transport layer interface for UDP comms.'''

import socket

from meerk40t.kernel import Service

from .ruidatransport import RuidaTransport, TransportTimeout, TransportError

class UDPTransport(RuidaTransport):
    def __init__(self, service: Service):
        super().__init__(service)
        self.send_address = service.address
        self.recv_address = None
        self.socket = None

        # These are defined by the Ruida controller and NOT configurable.
        self.send_port = 50200
        self.listen_port = 40200

        # Currently, not used but defined in case a keypad interface is used at
        # a later time.
        self.ctrl_port = 50207
        self.ctrl_listen_port = 40207

        self._s_to = 0.25 # UDP socket timeout. Must be less than or equal to 1.
        self._tries = int(1 / self._s_to)

    def __del__(self):
        self.close()

    def open(self):
        '''Open the transport interface.'''
        if self.is_open:
            return
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self._s_to)
            self.socket.bind(("", self.listen_port))
        except OSError:
            raise TransportError

    def close(self):
        '''Close the transport interface.'''
        if not self.is_open:
            return
        self.socket.close()
        self.socket = None

    def read(self, n: int) -> bytes:
        '''Read n bytes from the transport interface.

        NOTE: For UDP n is ignored.
        returns:
            Bytes received from the interface device.

        raises:
            TransportTimeout
        '''
        if not self.is_open:
            raise TransportError
        try:
            _data, _ = self.socket.recvfrom(1024)
        except (socket.timeout, AttributeError, OSError):
            raise TransportTimeout
        return _data

    def write(self, data: bytes):
        '''Send the data using the transport interface.'''
        if not self.is_open:
            raise TransportError
        try:
            self.socket.sendto(data, (self.send_address, self.send_port))
        except OSError:
            raise TransportError

    def set_timeout(self, seconds: float):
        '''Set the receive timeout.

        NOTE: This changes the number of tries for receiving data. It doesn't
        change the timeout of the transport interface.
        '''
        self._s_to = seconds
        self.socket.settimeout(self._s_to)

    def purge(self):
        '''Purge the comms transport data.

        Receive all data until no more data is available. Flush send
        data if necessary.
        '''
        _spewing = True
        while _spewing and self.is_open:
            try:
                self.socket.recvfrom(1024)
                self.dropped_packets += 1
            except (socket.timeout):
                _spewing = False

    def location(self):
        '''Return a string with connection info.'''
        return f'udp, ports: {self.send_port},{self.listen_port}'

    @property
    def is_open(self):
        '''Return True if the transport interface has been opened.'''
        return (self.socket is not None
                and self.socket.getsockname() != '0.0.0.0')

    @property
    def connected(self) -> bool:
        '''Return connection status.'''
        return self.socket is not None
