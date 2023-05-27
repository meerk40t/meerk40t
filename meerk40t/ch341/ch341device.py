"""
There are 2 primary parts of this code, the first is divided into three sections.

Kernel is needed to open files namely the usb device.
Ole32 is needed briefly to convert the GUID name.
Setupaapi is needed in places to query the devices.

Most of these are taken from pySerial, since that's a lot safer. It is very easy to mess this up and lose compatibility
with various versions of windows.

---
https://github.com/pyserial/pyserial
(C) 2001-2016 Chris Liechti <cliechti@gmx.net>

SPDX-License-Identifier:    BSD-3-Clause
---

The gwangyi library was also highly useful, and largely gave rise to the Ole32 functions.
--
https://github.com/gwangyi/pysetupdi
MIT License
Copyright (c) 2016 gwangyi
---

The second part is largely just mimicking the functionality of the CH341DLL.dll driver. The inclusion of that file
was always a bit iffy and error prone.
"""


import ctypes
import struct
from ctypes import POINTER, Structure, WinDLL, c_int64, c_ulong, c_void_p, sizeof
from ctypes.wintypes import BOOL, BYTE, DWORD, HANDLE, HWND, LPCWSTR, WORD

_stdcall_libraries = {}
_stdcall_libraries["kernel32"] = WinDLL("kernel32")

# some details of the windows API differ between 32 and 64 bit systems..
def is_64bit():
    """Returns true when running on a 64 bit system"""
    return sizeof(c_ulong) != sizeof(c_void_p)


# ULONG_PTR is a an ordinary number, not a pointer and contrary to the name it
# is either 32 or 64 bits, depending on the type of windows...
# so test if this a 32 bit windows...
if is_64bit():
    ULONG_PTR = c_int64
else:
    ULONG_PTR = c_ulong


class _SECURITY_ATTRIBUTES(Structure):
    pass


LPSECURITY_ATTRIBUTES = POINTER(_SECURITY_ATTRIBUTES)


class _OVERLAPPED(Structure):
    pass


OVERLAPPED = _OVERLAPPED
LPOVERLAPPED = POINTER(_OVERLAPPED)
LPDWORD = POINTER(DWORD)
LPVOID = c_void_p


try:
    CreateEventW = _stdcall_libraries["kernel32"].CreateEventW
except AttributeError:
    # Fallback to non-wide char version for old OS...
    from ctypes.wintypes import LPCSTR

    CreateEventA = _stdcall_libraries["kernel32"].CreateEventA
    CreateEventA.restype = HANDLE
    CreateEventA.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCSTR]
    CreateEvent = CreateEventA

    CreateFileA = _stdcall_libraries["kernel32"].CreateFileA
    CreateFileA.restype = HANDLE
    CreateFileA.argtypes = [
        LPCSTR,
        DWORD,
        DWORD,
        LPSECURITY_ATTRIBUTES,
        DWORD,
        DWORD,
        HANDLE,
    ]
    CreateFile = CreateFileA
else:
    CreateEventW.restype = HANDLE
    CreateEventW.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCWSTR]
    CreateEvent = CreateEventW  # alias

    CreateFileW = _stdcall_libraries["kernel32"].CreateFileW
    CreateFileW.restype = HANDLE
    CreateFileW.argtypes = [
        LPCWSTR,
        DWORD,
        DWORD,
        LPSECURITY_ATTRIBUTES,
        DWORD,
        DWORD,
        HANDLE,
    ]
    CreateFile = CreateFileW  # alias


def validate_handle(handle, function, args):
    handle = HANDLE(handle)
    if handle.value == HANDLE(-1).value:
        raise ConnectionError(f"Error {GetLastError()}. Failed to open.")
    return handle


CreateFile.errcheck = validate_handle


GetLastError = _stdcall_libraries["kernel32"].GetLastError
GetLastError.restype = DWORD
GetLastError.argtypes = []

CloseHandle = _stdcall_libraries["kernel32"].CloseHandle
CloseHandle.restype = BOOL
CloseHandle.argtypes = [HANDLE]

DeviceIoControl = _stdcall_libraries["kernel32"].DeviceIoControl
DeviceIoControl.argtypes = [
    HANDLE,
    DWORD,
    LPVOID,
    DWORD,
    LPVOID,
    DWORD,
    LPDWORD,
    LPOVERLAPPED,
]
DeviceIoControl.restype = BOOL
dwBytesReturned = DWORD(0)
lpBytesReturned = ctypes.byref(dwBytesReturned)


ERROR_SUCCESS = 0
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_STILL_ACTIVE = 259

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
GENERIC_EXECUTE = 0x20000000
GENERIC_ALL = 0x10000000

FILE_ATTRIBUTE_NORMAL = 0x00000080

CREATE_NEW = 1
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
TRUNCATE_EXISTING = 5


################################
# ole32 Section.
# Allows creations of GUID structures from strings.
################################

ole32 = ctypes.windll.LoadLibrary("ole32")
CLSIDFromString = ole32.CLSIDFromString

################################
# SetupApi Section.
################################

setupapi = ctypes.windll.LoadLibrary("setupapi")


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", DWORD),
        ("Data2", WORD),
        ("Data3", WORD),
        ("Data4", BYTE * 8),
    ]

    def __init__(self, guid):
        super().__init__()
        ret = CLSIDFromString(ctypes.create_unicode_buffer(guid), ctypes.byref(self))
        if ret < 0:
            err_no = GetLastError()
            raise OSError(err_no, ctypes.FormatError(err_no), guid)

    def __str__(self):
        return "{{{:08x}-{:04x}-{:04x}-{}-{}}}".format(
            self.Data1,
            self.Data2,
            self.Data3,
            "".join(["{:02x}".format(d) for d in self.Data4[:2]]),
            "".join(["{:02x}".format(d) for d in self.Data4[2:]]),
        )


class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("ClassGuid", GUID),
        ("DevInst", DWORD),
        ("Reserved", ULONG_PTR),
    ]

    def __str__(self):
        return "ClassGuid:{} DevInst:{}".format(self.ClassGuid, self.DevInst)


class DEVPROP_KEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", ctypes.c_ulong)]

    def __init__(self, guid, pid):
        super().__init__()
        self.fmtid.__init__(guid)
        self.pid = pid


HDEVINFO = ctypes.c_void_p
PCTSTR = ctypes.c_wchar_p

PSP_DEVINFO_DATA = ctypes.POINTER(SP_DEVINFO_DATA)

PSP_DEVICE_INTERFACE_DETAIL_DATA = ctypes.c_void_p

SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.argtypes = [HDEVINFO]
SetupDiDestroyDeviceInfoList.restype = BOOL

SetupDiEnumDeviceInfo = setupapi.SetupDiEnumDeviceInfo
SetupDiEnumDeviceInfo.argtypes = [HDEVINFO, DWORD, PSP_DEVINFO_DATA]
SetupDiEnumDeviceInfo.restype = BOOL

SetupDiGetClassDevs = setupapi.SetupDiGetClassDevsW
SetupDiGetClassDevs.argtypes = [ctypes.POINTER(GUID), PCTSTR, HWND, DWORD]
SetupDiGetClassDevs.restype = HDEVINFO


def valid_hdevinfo(value, func, arguments):
    if value in (-1, 0):
        err_no = GetLastError()
        raise OSError(err_no, ctypes.FormatError(err_no))
    return value


SetupDiGetClassDevs.errcheck = valid_hdevinfo

SetupDiGetDeviceProperty = setupapi.SetupDiGetDevicePropertyW
SetupDiGetDeviceProperty.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_void_p,
    ctypes.c_uint,
]


def valid_property(value, func, arguments):
    err_no = GetLastError()
    if err_no in (ERROR_SUCCESS, ERROR_INSUFFICIENT_BUFFER):
        return value
    raise OSError(err_no, ctypes.FormatError(err_no))


SetupDiGetDeviceProperty.errcheck = valid_property

DIGCF_PRESENT = 2

################
# CH341 Section
################

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


class CONTROL_TRANSFER(ctypes.Structure):
    """
    Control Transfer governs the control transfer routines for sending single control transfer commands to the CH341
    Kernel-side driver.
    """

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


class BULK_OUT(ctypes.Structure):
    """
    Governs the USB Bulk-Out usb device commands with optional command override. The command tends to govern the type
    of output write. WriteData(), WriteEppData(), WriteEppAddr() are all bulk out commands with different commands.
    """

    _fields_ = [
        ("command", ctypes.c_int),
        ("size", ctypes.c_int),
        ("packet", ctypes.c_byte * 31),
    ]

    def __init__(self, packet: bytes, cmd=0x07):
        self.command = cmd
        self.size = len(packet)
        ctypes.memmove(ctypes.addressof(self.packet), packet, self.size)


class CH341_DEFAULT(ctypes.Structure):
    """
    Default CH341 device command for other types of commands. We primarily support the EPP commands but other commands
    can be sent using the defined types.
    """

    _fields_ = [
        ("command", ctypes.c_int),
        ("data", ctypes.c_int),
    ]

    def __init__(self, command, data):
        self.command = command
        self.data = data


def _get_required_size(handle, key, dev_info):
    """
    Requests the property with a 0 size, this is expected to fail and return the required buffer size for the property.

    @param handle:
    @param key:
    @param dev_info:
    @return:
    """
    prop_type = ctypes.c_ulong()
    required_size = ctypes.c_ulong()

    if SetupDiGetDeviceProperty(
        handle,
        ctypes.byref(dev_info),
        ctypes.byref(key),
        ctypes.byref(prop_type),
        None,
        0,
        ctypes.byref(required_size),
        0,
    ):
        raise OSError()
    return required_size


def _get_prop(handle, key, dev_info):
    """
    Get property associated with the given key.

    @param handle:
    @param key:
    @param dev_info:
    @return:
    """
    prop_type = ctypes.c_ulong()
    required_size = _get_required_size(handle, key, dev_info)
    value_buffer = ctypes.create_string_buffer(required_size.value)
    if SetupDiGetDeviceProperty(
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


class CH341Device:
    def __init__(self, pdo_name, desc):
        self._handle = None
        self._buffer = (ctypes.c_char * 0x28)()
        self._pointer_buffer = ctypes.pointer(self._buffer)
        self.path = r"\\?\GLOBALROOT" + pdo_name
        self.name = desc
        self.success = True

    @property
    def bytes_returned(self):
        return dwBytesReturned.value

    @property
    def buffer(self):
        return self._buffer[8 : self.bytes_returned]

    @staticmethod
    def enumerate_devices():
        handle = SetupDiGetClassDevs(
            GUID("{77989adf-06db-4025-92e8-40d902c03b0a}"), None, None, DIGCF_PRESENT
        )
        try:
            devinfo = SP_DEVINFO_DATA()
            devinfo.cbSize = ctypes.sizeof(devinfo)
            index = 0
            while SetupDiEnumDeviceInfo(handle, index, ctypes.byref(devinfo)):
                index += 1
                pdo_name = _get_prop(
                    handle,
                    DEVPROP_KEY("{a45c254e-df1c-4efd-8020-67d146a850e0}", 16),
                    devinfo,
                )
                desc = _get_prop(
                    handle,
                    DEVPROP_KEY("{a45c254e-df1c-4efd-8020-67d146a850e0}", 2),
                    devinfo,
                )
                yield CH341Device(pdo_name, desc)

            err_no = GetLastError()
            if err_no not in (ERROR_STILL_ACTIVE, ERROR_SUCCESS):
                raise OSError(err_no, ctypes.FormatError(err_no))

        finally:
            SetupDiDestroyDeviceInfoList(handle)

    def ioctl(
        self, io_control_code, in_buffer, in_buffer_size, out_buffer, out_buffer_size
    ):
        self.success = DeviceIoControl(
            self._handle,
            io_control_code,
            in_buffer,
            in_buffer_size,
            out_buffer,
            out_buffer_size,
            lpBytesReturned,
            None,
        )
        return self.success

    def open(self):
        self._handle = CreateFile(
            self.path,
            GENERIC_READ | GENERIC_WRITE,
            3,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            0,
        )

    def close(self):
        if self._handle is not None:
            CloseHandle(self._handle)
            self._handle = None

    def is_connected(self):
        return self._handle is not None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, typ, val, tb):
        self.close()

    def CH341ReadData(self, length, cmd=0x06):
        self.ioctl(
            CH341_DEVICE_IO,
            ctypes.pointer(CH341_DEFAULT(command=cmd, data=length)),
            0x8,
            self._pointer_buffer,
            length,
        )
        return self._buffer[8 : self.bytes_returned]

    def CH341ReadData0(self, length):
        self.CH341ReadData(length, cmd=0x10)

    def CH341ReadData1(self, length):
        self.CH341ReadData(length, cmd=0x11)

    def CH341WriteData(self, buffer, cmd=0x07):
        if buffer is None:
            return True
        self.success = True
        while len(buffer) > 0:
            packet = buffer[:31]
            buffer = buffer[31:]
            self.ioctl(
                CH341_DEVICE_IO,
                ctypes.pointer(BULK_OUT(packet, cmd=cmd)),
                0x28,
                self._pointer_buffer,
                0x8,
            )
        return self.success

    def CH341EppWriteData(self, buffer):
        return self.CH341WriteData(buffer, cmd=0x12)

    def CH341EppWriteAddr(self, buffer):
        return self.CH341WriteData(buffer, cmd=0x13)

    def CH341InitParallel(self, mode=CH341_PARA_MODE_EPP19):
        value = mode << 8
        if mode < 256:
            value |= 2
        return self.ioctl(
            CH341_DEVICE_IO,
            ctypes.pointer(
                CONTROL_TRANSFER(mCH341_VENDOR_WRITE, mCH341_PARA_INIT, value, 0, 0x0)
            ),
            0x28,
            self._pointer_buffer,
            0x28,
        )

    def CH341ResetDevice(self):
        return self.ioctl(
            CH341_DEVICE_IO,
            ctypes.pointer(CH341_DEFAULT(command=0xC, data=0)),
            0x28,
            self._pointer_buffer,
            0x28,
        )

    def CH341SetDelayMS(self, delay):
        if delay > 0x0F:
            delay = 0x0F
        return self.CH341WriteData(bytes([0xAA, 0x50 | delay, 0x00]))

    def CH341GetStatus(self):
        """D7-0, 8: err, 9: pEmp, 10: Int, 11: SLCT, 12: SDA, 13: Busy, 14: data, 15: addrs"""
        self.ioctl(
            CH341_DEVICE_IO,
            ctypes.pointer(
                CONTROL_TRANSFER(mCH341_VENDOR_READ, mCH341A_STATUS, 0, 0, 0x8)
            ),
            0x28,
            self._pointer_buffer,
            0x28,
        )
        return tuple(self.buffer)

    def CH341GetVerIC(self):
        self.ioctl(
            CH341_DEVICE_IO,
            ctypes.pointer(
                CONTROL_TRANSFER(mCH341_VENDOR_READ, mCH341A_GET_VER, 0, 0, 0x2)
            ),
            0x28,
            self._pointer_buffer,
            0x28,
        )
        return struct.unpack("<h", self.buffer)[0]

    def CH341SetParaMode(self, index, mode=CH341_PARA_MODE_EPP19):
        value = 0x2525
        return self.ioctl(
            CH341_DEVICE_IO,
            ctypes.pointer(
                CONTROL_TRANSFER(
                    mCH341_VENDOR_WRITE,
                    mCH341_SET_PARA_MODE,
                    value,
                    index,
                    mode << 8 | mode,
                )
            ),
            0x28,
            self._pointer_buffer,
            0x28,
        )


if __name__ == "__main__":
    for device in CH341Device.enumerate_devices():
        print(device)
        print(device.name)
        # device.open()
        with device:
            device.CH341WriteData(b"\xA0")
            data = device.CH341ReadData(8)
            print(data)
            device.CH341InitParallel()
            status = device.CH341GetStatus()
            print(status)
            status = device.CH341GetVerIC()
            print(status)
            device.CH341EppWriteData(b"\x00IPPFFFFFFFFFFFFFFFFFFFFFFFFFFF\xe4")
