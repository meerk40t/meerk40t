'''Transport layer interface for USB serial comms.

NOTE: This is a work in progress and is reverse engineered using data captured
using Wireshark and a usbSerial.lua decoder found at:
    (https://github.com/cbcGirard/SerialSnooper/blob/main/usbSerial.lua).

Some relevant information:
  - The Ruida RDC6442 controller uses an FTDI USB serial interface.
  - Vendor/device are: 0x0403:0x6001
  - Byte format is: 8 bit, no parity, 1 stop bit and no break bit.
  - Modem control is used with RTS and DTS enabled but there doesn't appear to
    be any line turnaround handshake.
  - Baud rate setting should be reasonably high.
  - Swizzle is the same.
  - There is no checksum on data sent to the controller.
  - There is no ACK handshake.
  - The controller doesn't reply to ENQ since there is not ACK.

'''

import serial
from serial.serialutil import SerialTimeoutException, SerialException

from meerk40t.kernel import Service

from .ruidatransport import RuidaTransport, TransportTimeout, TransportError

class USBTransport(RuidaTransport):
    def __init__(self, service: Service):
        super().__init__(service)
        self.baud = self.service.baud_rate
        self.serial_port = self.service.serial_port
        self.serial = None

        self._s_to = 0.25 # Serial read timeout. Must be less than or equal to 1.
        self._tries = int(1 / self._s_to)

    def __del__(self):
        self.close()

    def open(self):
        '''Open the transport interface.'''
        if self.is_open:
            return
        try:
            self.serial = serial.Serial(
                self.serial_port,
                115200, #self.baud, # Baud doesn't seem to matter much.
                timeout=self._s_to,
                rtscts=True,
                dsrdtr=True,
            )
        except (FileNotFoundError, SerialException):
            raise TransportError(f'Unable to open: {self.serial_port}')

    def close(self):
        '''Close the transport interface.'''
        if self.is_open:
            try:
                self.serial.close()
            except OSError:
                # This can occur when the Ruida controller is turned on while
                # MK is running and the USB device has not yet stabilized.
                pass
        self.serial = None

    def read(self, n: int) -> bytes:
        '''Read n bytes from the transport interface.

        returns:
            Bytes received from the interface device.

        raises:
            TransportTimeout
        '''
        # Returns an empty byte array if timeout.
        if not self.is_open:
            raise TransportError
        try:
            _data = self.serial.read(n)
            if len(_data) == n:
                return _data
            else:
                raise TransportTimeout
        except (SerialException, TypeError):
            raise TransportTimeout

    def write(self, data: bytes):
        '''Send the data using the transport interface.'''
        if not self.is_open:
            raise TransportError
        try:
            self.serial.write(data)
            pass # For debug
        except SerialException:
            pass

    def set_timeout(self, seconds: float):
        '''Set the receive timeout.

        NOTE: This changes the number of tries for receiving data. It doesn't
        change the timeout of the transport interface.
        '''
        self._s_to = seconds
        if self.is_open:
            self.serial.timeout = self._s_to

    def purge(self):
        '''Purge the comms transport data.

        Receive all data until no more data is available. Flush send
        data if necessary.
        '''
        if not self.is_open:
            return
        _spewing = True
        while _spewing:
            try:
                # try except TypeError and raise TransportError
                try:
                    _b = self.serial.read(1)
                except TypeError: # May not exist if reconnecting.
                    raise TransportError
                _spewing = len(_b) > 0
            except SerialException:
                _spewing = False
                self.dropped_packets += 1

    def location(self):
        '''Return a string with connection info.'''
        return f'usb, Port:{self.serial_port} Baud:{self.baud}'

    @property
    def is_open(self):
        '''Return True if the transport interface has been opened.'''
        return self.serial is not None

    @property
    def connected(self) -> bool:
        '''Return connection status.'''
        return self.serial is not None
