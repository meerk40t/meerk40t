import struct
import ctypes
from ctypes import windll, wintypes

_setupapi = ctypes.windll.setupapi
_ole32 = ctypes.windll.ole32


USB_LOCK_VENDOR = 0x1A86  # Dev : (1a86) QinHeng Electronics
USB_LOCK_PRODUCT = 0x5512  # (5512) CH341A
BULK_WRITE_ENDPOINT = 0x02  # usb.util.ENDPOINT_OUT|usb.util.ENDPOINT_TYPE_BULK
BULK_READ_ENDPOINT = 0x82  # usb.util.ENDPOINT_IN|usb.util.ENDPOINT_TYPE_BULK
CH341_PARA_MODE_EPP19 = 0x01

mCH341_PARA_CMD_R0 = 0xAC  # 10101100
mCH341_PARA_CMD_R1 = 0xAD  # 10101101
mCH341_PARA_CMD_W0 = 0xA6  # 10100110
mCH341_PARA_CMD_W1 = 0xA7  # 10100111
mCH341_PARA_CMD_STS = 0xA0  # 10100000

mCH341_PACKET_LENGTH = 32
mCH341_PKT_LEN_SHORT = 8
mCH341_SET_PARA_MODE = 0x9A
mCH341_PARA_INIT = 0xB1
mCH341_VENDOR_READ = 0xC0
mCH341_VENDOR_WRITE = 0x40
mCH341A_BUF_CLEAR = 0xB2
mCH341A_DELAY_MS = 0x5E
mCH341A_GET_VER = 0x5F
mCH341A_STATUS = 0x52

CH341_DEVICE_IO = 0x223CD0

LPDWORD = ctypes.POINTER(wintypes.DWORD)
LPOVERLAPPED = wintypes.LPVOID
LPSECURITY_ATTRIBUTES = wintypes.LPVOID

ERROR_INSUFFICIENT_BUFFER = 122
ERROR_STILL_ACTIVE = 259
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
GENERIC_EXECUTE = 0x20000000
GENERIC_ALL = 0x10000000

CREATE_NEW = 1
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
TRUNCATE_EXISTING = 5

FILE_ATTRIBUTE_NORMAL = 0x00000080

INVALID_HANDLE_VALUE = -1

NULL = 0


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(self, guid):
        super().__init__()
        ret = _ole32.CLSIDFromString(
            ctypes.create_unicode_buffer(guid), ctypes.byref(self)
        )
        if ret < 0:
            err_no = ctypes.GetLastError()
            raise WindowsError(err_no, ctypes.FormatError(err_no), guid)

    def __str__(self):
        s = ctypes.c_wchar_p()
        ret = _ole32.StringFromCLSID(ctypes.byref(self), ctypes.byref(s))
        if ret < 0:
            err_no = ctypes.GetLastError()
            raise WindowsError(err_no, ctypes.FormatError(err_no))
        ret = str(s.value)
        _ole32.CoTaskMemFree(s)
        return ret


class _DEV_INFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("ClassGuid", _GUID),
        ("DevInst", ctypes.c_ulong),
        ("Reserved", ctypes.c_void_p),
    ]

    def __init__(self):
        super().__init__()
        self.cbSize = ctypes.sizeof(self)


class _DEV_PROP_KEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_ulong)]

    def __init__(self, guid, pid):
        super().__init__()
        self.fmtid.__init__(guid)
        self.pid = pid


class _CH341_CONTROL_TRANSFER(ctypes.Structure):
    _fields_ = [
        ("command", ctypes.c_int),
        ("size", ctypes.c_int),
        ("bmRequestType", ctypes.c_byte),
        ("bRequest", ctypes.c_byte),
        ("wValue", ctypes.c_ushort),
        ("wIndex", ctypes.c_ushort),
        ("wLength", ctypes.c_byte),
    ]

    def __init__(self, bmRequestType, bRequest, wValue, wIndex, wLength):
        super().__init__()
        self.command = 0x4
        self.size = 0
        self.bmRequestType = bmRequestType
        self.bRequest = bRequest
        self.wValue = wValue
        self.wIndex = wIndex
        self.wLength = wLength


class _CH341_BULK_OUT(ctypes.Structure):
    _fields_ = [
        ("command", ctypes.c_int),
        ("size", ctypes.c_int),
        ("packet", ctypes.c_byte * 31),
    ]

    def __init__(self, packet: bytes, cmd=0x07):
        self.command = cmd
        self.size = len(packet)
        ctypes.memmove(ctypes.addressof(self.packet), packet, self.size)

class _CH341_BULK_IN(ctypes.Structure):
    _fields_ = [
        ("command", ctypes.c_int),
        ("size", ctypes.c_int),
    ]

    def __init__(self, length, cmd=0x06):
        self.command = cmd
        self.size = length


def _get_required_size(handle, key, dev_info):
    prop_type = ctypes.c_ulong()
    required_size = ctypes.c_ulong()

    if _setupapi.SetupDiGetDevicePropertyW(
        handle,
        ctypes.byref(dev_info),
        ctypes.byref(key),
        ctypes.byref(prop_type),
        None,
        0,
        ctypes.byref(required_size),
        0,
    ):
        raise WindowsError()
    err_no = ctypes.GetLastError()
    if err_no != ERROR_INSUFFICIENT_BUFFER:
        raise WindowsError()
    return required_size


def _get_prop(handle, key, dev_info):
    prop_type = ctypes.c_ulong()
    required_size = _get_required_size(handle, key, dev_info)
    value_buffer = ctypes.create_string_buffer(required_size.value)
    if _setupapi.SetupDiGetDevicePropertyW(
        handle,
        ctypes.byref(dev_info),
        ctypes.byref(key),
        ctypes.byref(prop_type),
        ctypes.byref(value_buffer),
        required_size.value,
        ctypes.byref(required_size),
        0,
    ):
        return bytes(value_buffer).decode("utf-16").split("\0", 1)[0]
    err_no = ctypes.GetLastError()
    if err_no == 0:
        return
    raise WindowsError(err_no, ctypes.FormatError(err_no))


class CH341Device:
    def __init__(self, pdo_name, desc):
        self._handle = None
        self._file_handle = None
        self.buffer = (ctypes.c_char * 0x28)()
        self.point_buffer = ctypes.pointer(self.buffer)
        self.path = r"\\?\GLOBALROOT" + pdo_name
        self.name = desc

    @staticmethod
    def enumerate_devices():
        GUID = "{77989adf-06db-4025-92e8-40d902c03b0a}"
        _guid = _GUID(GUID)
        handle = _setupapi.SetupDiGetClassDevsW(_guid, None, None, 2)
        if handle == -1:
            err_no = ctypes.GetLastError()
            raise WindowsError(err_no, ctypes.FormatError(err_no), (None, None, 2))

        try:
            idx = 0
            dev_info = _DEV_INFO_DATA()
            while _setupapi.SetupDiEnumDeviceInfo(handle, idx, ctypes.byref(dev_info)):
                idx += 1
                pdo_name = _get_prop(
                    handle,
                    _DEV_PROP_KEY("{a45c254e-df1c-4efd-8020-67d146a850e0}", 16),
                    dev_info,
                )
                desc = _get_prop(
                    handle,
                    _DEV_PROP_KEY("{a45c254e-df1c-4efd-8020-67d146a850e0}", 2),
                    dev_info,
                )
                yield CH341Device(pdo_name, desc)

            err_no = ctypes.GetLastError()
            if err_no != ERROR_STILL_ACTIVE:
                raise WindowsError(err_no, ctypes.FormatError(err_no), (None, None, 2))

        finally:
            _setupapi.SetupDiDestroyDeviceInfoList(handle)

    def _validate(self):
        if self._file_handle is None:
            raise ConnectionError("Not connected.")
        if self._file_handle.value == wintypes.HANDLE(INVALID_HANDLE_VALUE).value:
            raise ConnectionError(f"Error {ctypes.GetLastError()}. Failed to open.")

    def ioctl(self, ctl, inbuf, inbufsiz, outbuf, outbufsiz):
        self._validate()
        DeviceIoControl = windll.kernel32.DeviceIoControl
        DeviceIoControl.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            LPDWORD,
            LPOVERLAPPED,
        ]
        DeviceIoControl.restype = wintypes.BOOL
        dwBytesReturned = wintypes.DWORD(0)
        lpBytesReturned = ctypes.byref(dwBytesReturned)
        status = DeviceIoControl(
            self._file_handle,
            ctl,
            inbuf,
            inbufsiz,
            outbuf,
            outbufsiz,
            lpBytesReturned,
            None,
        )
        return status, dwBytesReturned

    def open(self):
        access = GENERIC_READ | GENERIC_WRITE
        CreateFileW = windll.kernel32.CreateFileW
        CreateFileW.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            LPSECURITY_ATTRIBUTES,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        CreateFileW.restype = wintypes.HANDLE
        self._file_handle = wintypes.HANDLE(
            CreateFileW(
                self.path, access, 3, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL
            )
        )
        self._validate()

    def close(self):
        try:
            self._validate()
            windll.kernel32.CloseHandle(self._file_handle)
        except ConnectionError:
            pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, typ, val, tb):
        self.close()

    def CH341ReadData(self, length, cmd=0x06):
        bi = _CH341_BULK_IN(length, cmd=cmd)
        point_bi = ctypes.pointer(bi)
        status, bytes_returned = self.ioctl(
            CH341_DEVICE_IO, point_bi, 0x8, self.point_buffer, length
        )
        return self.buffer[8:bytes_returned.value]

    def CH341ReadData0(self, length):
        self.CH341ReadData(length, cmd=0x10)

    def CH341ReadData0(self, length):
        self.CH341ReadData(length, cmd=0x11)

    def CH341WriteData(self, buffer, cmd=0x07):
        if buffer is None:
            return
        status = True
        while len(buffer) > 0:
            packet = buffer[:31]
            buffer = buffer[31:]
            bo = _CH341_BULK_OUT(packet, cmd=cmd)
            point_bo = ctypes.pointer(bo)
            status, bytes_returned = self.ioctl(
                CH341_DEVICE_IO, point_bo, 0x28, self.point_buffer, 0x8
            )
        return status

    def CH341EppWriteData(self, buffer):
        return self.CH341WriteData(buffer, cmd=0x12)

    def CH341EppWriteAddr(self, buffer):
        return self.CH341WriteData(buffer, cmd=0x13)

    def CH341InitParallel(self, mode=CH341_PARA_MODE_EPP19):
        value = mode << 8
        if mode < 256:
            value |= 2
        ct = _CH341_CONTROL_TRANSFER(
            mCH341_VENDOR_WRITE, mCH341_PARA_INIT, value, 0, 0x0
        )
        point_ct = ctypes.pointer(ct)
        status, bytes_returned = self.ioctl(
            CH341_DEVICE_IO, point_ct, 0x28, self.point_buffer, 0x28
        )
        return status

    def CH341SetDelayMS(self, delay):
        if delay > 0x0F:
            delay = 0x0F
        data = bytes([0xAA, 0x50 | delay, 0x00])
        self.CH341WriteData(data)

    def CH341GetStatus(self):
        """D7-0, 8: err, 9: pEmp, 10: Int, 11: SLCT, 12: SDA, 13: Busy, 14: data, 15: addrs"""
        ct = _CH341_CONTROL_TRANSFER(mCH341_VENDOR_READ, mCH341A_STATUS, 0, 0, 0x8)
        point_ct = ctypes.pointer(ct)
        status, bytes_returned = self.ioctl(
            CH341_DEVICE_IO, point_ct, 0x28, self.point_buffer, 0x28
        )
        return tuple(self.buffer[8:bytes_returned.value])

    def CH341GetVerIC(self):
        ct = _CH341_CONTROL_TRANSFER(mCH341_VENDOR_READ, mCH341A_GET_VER, 0, 0, 0x2)
        point_ct = ctypes.pointer(ct)
        status, bytes_returned = self.ioctl(
            CH341_DEVICE_IO, point_ct, 0x28, self.point_buffer, 0x28
        )
        return struct.unpack("<h", self.buffer[8:bytes_returned.value])[0]

    def CH341SetParaMode(self, index, mode=CH341_PARA_MODE_EPP19):
        value = 0x2525
        ct = _CH341_CONTROL_TRANSFER(
            mCH341_VENDOR_WRITE,
            mCH341_SET_PARA_MODE,
            value,
            index,
            mode << 8 | mode,
        )
        point_ct = ctypes.pointer(ct)
        status, bytes_returned = self.ioctl(
            CH341_DEVICE_IO, point_ct, 0x28, self.point_buffer, 0x28
        )
        return status


if __name__ == "__main__":
    for device in CH341Device.enumerate_devices():
        print(device)
        print(device.name)

        # with ch341 as device:
        device.open()
        device.CH341WriteData(b"\xA0")
        data = device.CH341ReadData(8)
        print(data)
        device.CH341InitParallel()
        status = device.CH341GetStatus()
        print(status)
        status = device.CH341GetVerIC()
        # print(status)
        device.CH341EppWriteData(b"\x00IPPFFFFFFFFFFFFFFFFFFFFFFFFFFF\xe4")
        device.close()
