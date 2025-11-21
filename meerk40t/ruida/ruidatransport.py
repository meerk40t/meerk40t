'''
Ruida Transport

This is a base class defining a standard interface for comms transport layer
(Layer 4) protocols such as UDP or serial.

Defined are the standard methods the derived classes must support.
'''
from meerk40t.kernel import Service

class TransportTimeout(Exception):
    def __init__(self, message='Transport layer timeout.'):
        self.message = message
        super().__init__(self.message)

class TransportError(Exception):
    def __init__(self, message='Transport layer exception.'):
        self.message = message
        super().__init__(self.message)

class RuidaTransport:
    def __init__(self, service: Service):
        self.service = service
        self.name = service.name
        self.interface = service.interface
        self.dropped_packets = 0

    def _tbd(self, method):
        raise NotImplementedError(f'{self.name}: {method} not implemented.')

    def open(self):
        '''Open the transport interface.'''
        self._tbd(__name__)

    def close(self):
        '''Close the transport interface.'''
        self._tbd(__name__)

    def read(self, n: int) -> bytes:
        '''Read n bytes from the transport interface.

        returns:
            Bytes received from the interface device.

        raises:
            TransportTimeout
        '''
        self._tbd(__name__)

    def write(self, data: bytes):
        '''Send the data using the transport interface.'''
        self._tbd(__name__)

    def set_timeout(self, seconds: float):
        '''Set the receive timeout.

        NOTE: This changes the number of tries for receiving data. It doesn't
        change the timeout of the transport interface.
        '''
        self._s_to = seconds
        # Put set timeout here.

    def purge(self):
        '''Purge the comms transport data.

        Receive all data until no more data is available. Flush send
        data if necessary.
        '''
        self._tbd(__name__)

    def location(self):
        '''Return a string with connection info.'''
        self._tbd(__name__)

    @property
    def is_open(self):
        '''Return True if the transport interface has been opened.'''
        self._tbd(__name__)
        return None

    @property
    def connected(self) -> bool:
        '''Return connection status.'''
        self._tbd(__name__)
        return None
