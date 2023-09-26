"""
Galvo USB Connection

Performs the required interactions with the Galvo backend through pyusb and libusb.
"""
import struct

import usb.core

from usb.util import (
    build_request_type,
    CTRL_OUT,
    CTRL_TYPE_VENDOR,
    CTRL_RECIPIENT_DEVICE,
)

USB_LOCK_VENDOR = 0x9588
USB_LOCK_PRODUCT = 0x9980

request = build_request_type(CTRL_OUT, CTRL_TYPE_VENDOR, CTRL_RECIPIENT_DEVICE)


def _firmware(device, start):
    device.ctrl_transfer(
        request,
        bRequest=0xA0,
        wValue=0xE600,
        wIndex=0x0,
        data_or_wLength=b"\x01" if start else b"\x00",
    )


def _parse(f):
    while True:
        data = f.read(22)
        if data is None or len(data) != 22:
            break
        length, _, value, end, payload, _ = struct.unpack("BBHB16sB", data)
        if end != 0:
            break
        yield value, payload[:length]


def _write_chunks(device, chunks):
    _firmware(device, start=True)
    for value, payload in chunks:
        device.ctrl_transfer(
            request, bRequest=0xA0, wValue=value, wIndex=0x0, data_or_wLength=payload
        )
        print(value, payload)
    _firmware(device, start=False)


def _send_device_sys(device, sys_file, offset=0x4440):
    if isinstance(sys_file, str):
        with open(sys_file, "rb") as f:
            f.seek(offset)
            _write_chunks(device, _parse(f))
    else:
        _write_chunks(device, _parse(sys_file))


def load_sys(sys_file, channel=None):
    try:
        devices = list(usb.core.find(idVendor=USB_LOCK_VENDOR, idProduct=USB_LOCK_PRODUCT, find_all=True))
        if channel:
            channel(f"{len(devices)} devices need initializing.")
        for i, device in enumerate(devices):
            if channel:
                channel(f"Clone board #{i+1} detected. Sending Initialize.")
            _send_device_sys(device, sys_file)
    except usb.core.USBError as e:
        channel(str(e))
        raise ConnectionRefusedError

def load_chunks(chunks, channel=None):
    try:
        devices = list(
            usb.core.find(idVendor=USB_LOCK_VENDOR, idProduct=USB_LOCK_PRODUCT, find_all=True)
        )
        if channel:
            channel(f"{len(devices)} devices need initializing.")
        for i, device in enumerate(devices):
            if channel:
                channel(f"Clone board #{i+1} detected. Sending Initialize.")
            _write_chunks(device, chunks)
    except usb.core.USBError as e:
        channel(str(e))
        raise ConnectionRefusedError


if __name__ == "__main__":
    load_sys("Lmcv2u.sys", channel=print)
