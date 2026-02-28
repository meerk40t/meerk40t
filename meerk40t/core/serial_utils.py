"""
Serial port utilities shared across drivers.
"""

import re

import serial
from serial import SerialException


def serial_open(port: str, baud_rate: int, **kwargs) -> serial.Serial:
    """Open a serial port, with automatic Windows extended-name fallback.

    On Windows, COM ports with numbers above 9 require the extended UNC
    notation ``\\\\.\\COMx`` to open reliably.  This helper tries the name
    as-is first; if that raises a ``SerialException`` and the name matches
    the ``COMx`` pattern (case-insensitive), it retries with the extended
    notation.  Any other failure, or a second failure, propagates normally.

    Args:
        port: Port name, e.g. ``"COM3"``, ``"COM12"``, ``"/dev/ttyUSB0"``.
        baud_rate: Baud rate to open the port with.
        **kwargs: Forwarded verbatim to ``serial.Serial``.

    Returns:
        An open ``serial.Serial`` instance.

    Raises:
        SerialException: If the port cannot be opened.
    """
    try:
        return serial.Serial(port, baud_rate, **kwargs)
    except SerialException:
        if re.match(r"^COM\d+$", port, re.IGNORECASE):
            return serial.Serial(f"\\\\.\\{port}", baud_rate, **kwargs)
        raise
