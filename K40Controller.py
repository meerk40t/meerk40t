import threading
from ctypes import *

import usb.core
import usb.util

from Kernel import *

STATUS_BAD_STATE = 204
# 0xCC, 11001100
STATUS_OK = 206
# 0xCE, 11001110
STATUS_PACKET_REJECTED = 207
# 0xCF, 11001111
STATUS_FINISH = 236
# 0xEC, 11101100
STATUS_BUSY = 238
# 0xEE, 11101110
STATUS_POWER = 239
# 0xEF, 11101111

# 255, 206, 111, 148, 19, 255
# 255, 206, 111, 12, 18, 0

STATUS_NO_DEVICE = -1
USB_LOCK_VENDOR = 0x1a86  # Dev : (1a86) QinHeng Electronics
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


def get_code_string_from_code(code):
    if code == STATUS_OK:
        return "OK"
    elif code == STATUS_BUSY:
        return "Busy"
    elif code == STATUS_PACKET_REJECTED:
        return "Rejected"
    elif code == STATUS_FINISH:
        return "Finish"
    elif code == STATUS_POWER:
        return "Low Power"
    elif code == STATUS_BAD_STATE:
        return "Bad State"
    else:
        return "Unknown: %d" % code


def convert_to_list_bytes(data):
    if isinstance(data, str):  # python 2
        packet = [0] * 30
        for i in range(0, 30):
            packet[i] = ord(data[i])
        return packet
    else:
        packet = [0] * 30
        for i in range(0, 30):
            packet[i] = data[i]
        return packet


crc_table = [
    0x00, 0x5E, 0xBC, 0xE2, 0x61, 0x3F, 0xDD, 0x83,
    0xC2, 0x9C, 0x7E, 0x20, 0xA3, 0xFD, 0x1F, 0x41,
    0x00, 0x9D, 0x23, 0xBE, 0x46, 0xDB, 0x65, 0xF8,
    0x8C, 0x11, 0xAF, 0x32, 0xCA, 0x57, 0xE9, 0x74]


def onewire_crc_lookup(line):
    """
    License: 2-clause "simplified" BSD license
    Copyright (C) 1992-2017 Arjen Lentz
    https://lentz.com.au/blog/calculating-crc-with-a-tiny-32-entry-lookup-table

    :param line: line to be CRC'd
    :return: 8 bit crc of line.
    """
    crc = 0
    for i in range(0, 30):
        crc = line[i] ^ crc
        crc = crc_table[crc & 0x0f] ^ crc_table[16 + ((crc >> 4) & 0x0f)]
    return crc


class ControllerQueueThread(threading.Thread):
    def __init__(self, controller):
        threading.Thread.__init__(self)
        self.controller = controller
        self.state = THREAD_STATE_UNSTARTED
        self.controller.kernel("control_thread", self.state)

    def run(self):
        self.state = THREAD_STATE_STARTED
        self.controller.kernel("control_thread", self.state)
        waited = 0
        self.controller.kernel("status_bar", ("Laser On!", 1))
        while self.state != THREAD_STATE_ABORT:
            if self.controller.process_queue():
                time.sleep(0.1)
                waited += 1
                if waited >= 20:
                    break
            else:
                waited = 0
            while self.state == THREAD_STATE_PAUSED:
                self.controller.kernel("control_thread", self.state)
                time.sleep(1)
        self.controller.kernel("status_bar", (None, 1))
        if self.state == THREAD_STATE_ABORT:
            self.controller.kernel("control_thread", self.state)
            return
        self.state = THREAD_STATE_FINISHED
        self.controller.kernel("control_thread", self.state)


STATE_UNINITIALIZED = -1
STATE_CONNECTING = 0
STATE_DRIVER_FINDING_DEVICES = 10
STATE_DRIVER_NO_BACKEND = 20
STATE_DEVICE_FOUND = 30
STATE_DEVICE_NOT_FOUND = 50
STATE_DEVICE_REJECTED = 60

STATE_USB_SET_CONFIG = 100
STATE_USB_DETACH_KERNEL = 200
STATE_USB_DETACH_KERNEL_SUCCESS = 210
STATE_USB_DETACH_KERNEL_FAIL = 220
STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED = 230

STATE_USB_CLAIM_INTERFACE = 300
STATE_USB_CLAIM_INTERFACE_SUCCESS = 310
STATE_USB_CLAIM_INTERFACE_FAIL = 320

STATE_USB_CONNECTED = 400
STATE_CH431_PARAMODE = 160

STATE_CONNECTED = 600

STATE_USB_SET_DISCONNECTING = 1000
STATE_USB_ATTACH_KERNEL = 1100
STATE_USB_ATTACH_KERNEL_SUCCESS = 1110
STATE_USB_ATTACH_KERNEL_FAIL = 1120
STATE_USB_RELEASE_INTERFACE = 1200
STATE_USB_RELEASE_INTERFACE_SUCCESS = 1210
STATE_USB_RELEASE_INTERFACE_FAIL = 1220

STATE_USB_DISPOSING_RESOURCES = 1200
STATE_USB_RESET = 1400
STATE_USB_RESET_SUCCESS = 1410
STATE_USB_RESET_FAIL = 1420
STATE_USB_DISCONNECTED = 1500


class CH341LibusbDriver:
    """
    Libusb driver for the CH341 chip. The CH341x is a USB interface chip that can emulate UART, parallel port,
    and synchronous serial (EPP, I2C, SPI). The Lhystudios boards (M2Nano, et al) and Moshi boards and likely others
    use this in EPP 1.9 mode. This class is not and not intended to be a full driver for that chip. Rather we are
    duplicating the function calls and implementing compatible operations to permit a stand-in for the default CH341
    driver. Using libusb to do the usb connection to the chip as well as permitting easy swapping that for the default
    driver. This serves as the basis to permit multiple operative methods, permitting use of either the default driver
    or Libusb driver interchangeably.

    Since these functions will need swapping in MSW we should duplicate the function calls thereof. Also since a stated
    goal is to support multiple devices implicitly, we should also properly support multiple device functionality.

    To this end, this should duplicate the names of the function calls. And the use of index to reference which
    connection to use for each command.
    """

    def __init__(self, kernel):
        self.devices = {}
        self.interface = {}
        self.kernel = kernel

    def set_status(self, code, obj=None):
        message = None
        if code == STATE_CONNECTING:
            message = "Attempting connection to USB."
        elif code == STATE_DRIVER_NO_BACKEND:
            message = "PyUsb detected no backend LibUSB driver."
        elif code == STATE_DEVICE_FOUND:
            message = "K40 device detected:\n%s\n" % str(obj)
        elif code == STATE_DEVICE_NOT_FOUND:
            message = "Not Found"
        elif code == STATE_DEVICE_REJECTED:
            message = "K40 devices were found but they were rejected."
        elif code == STATE_USB_SET_CONFIG:
            message = "Config Set"
        elif code == STATE_USB_DETACH_KERNEL:
            message = "Attempting to detach kernel."
        elif code == STATE_USB_DETACH_KERNEL_SUCCESS:
            message = "Kernel detach: Success."
        elif code == STATE_USB_DETACH_KERNEL_FAIL:
            message = "Kernel detach: Failed."
        elif code == STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED:
            message = "Kernel detach: Not Implemented."
        elif code == STATE_USB_CLAIM_INTERFACE:
            message = "Attempting to claim interface."
        elif code == STATE_USB_CLAIM_INTERFACE_SUCCESS:
            message = "Interface claim: Success"
        elif code == STATE_USB_CLAIM_INTERFACE_FAIL:
            message = "Interface claim: Fail"
        elif code == STATE_USB_CONNECTED:
            message = "USB Connected"
        elif code == STATE_USB_SET_DISCONNECTING:
            message = "Attempting disconnection from USB."
        elif code == STATE_USB_ATTACH_KERNEL:
            message = "Attempting kernel attach"
        elif code == STATE_USB_ATTACH_KERNEL_SUCCESS:
            message = "Kernel attach: Success."
        elif code == STATE_USB_ATTACH_KERNEL_FAIL:
            message = "Kernel attach: Fail."
        elif code == STATE_USB_RELEASE_INTERFACE:
            message = "Attempting to release interface."
        elif code == STATE_USB_RELEASE_INTERFACE_SUCCESS:
            message = "Interface released"
        elif code == STATE_USB_RELEASE_INTERFACE_FAIL:
            message = "Interface did not exist."
        elif code == STATE_USB_DISPOSING_RESOURCES:
            message = "Attempting to dispose resources."
        elif code == STATE_USB_RESET:
            message = "Attempting USB reset."
        elif code == STATE_USB_RESET_FAIL:
            message = "USB connection did not exist."
        elif code == STATE_USB_RESET_SUCCESS:
            message = "USB connection reset."
        elif code == STATE_USB_DISCONNECTED:
            message = "USB Disconnection Successful."
        self.kernel.signal('usb_log', message)
        self.kernel.signal('usb_state', code)

    def choose_device(self, devices, index):
        """
        We have a choice of different devices and must choose which one to connect to.

        :param devices: List of devices to choose from.
        :param index: Index of the device we were asked to choose.
        :return: Device chosen.
        """

        for i, dev in enumerate(devices):
            self.log("Device %d Bus: %d Address %d" % (i, dev.bus, dev.address))
        if devices is None or len(devices) == 0:
            return None
        else:
            return devices[index]
        # if self.kernel.usb_index == -1:
        #     if self.kernel.usb_address == -1 and self.kernel.usb_bus == -1:
        #         if len(d) > 0:
        #             self.usb = d[0]
        #     else:
        #         for dev in d:
        #             if (self.kernel.usb_address == -1 or self.kernel.usb_address == dev.address) and \
        #                     (self.kernel.usb_bus == -1 or self.kernel.usb_bus == dev.bus):
        #                 self.usb = dev
        #                 break
        # else:
        #     if len(d) > self.kernel.usb_index:
        #         self.usb = d[self.kernel.usb_index]

    def connect_find(self, index=0):
        try:
            devices = usb.core.find(idVendor=USB_LOCK_VENDOR, idProduct=USB_LOCK_PRODUCT, find_all=True)
        except usb.core.NoBackendError:
            self.set_status(STATE_DRIVER_NO_BACKEND)
            raise ConnectionError
        self.set_status(STATE_DRIVER_FINDING_DEVICES)
        devices = [d for d in devices]
        if len(devices) == 0:
            self.set_status(STATE_DEVICE_NOT_FOUND)
            raise ConnectionError
        self.set_status(STATE_DEVICE_FOUND, devices)
        device = self.choose_device(devices, index)
        if device is None:
            self.set_status(STATE_DEVICE_REJECTED)
            raise ConnectionError
        return device

    def connect_interface(self, device):
        self.set_status(STATE_USB_SET_CONFIG)
        device.set_configuration()
        self.set_status(STATE_USB_CLAIM_INTERFACE)
        try:
            interface = device.get_active_configuration()[(0, 0)]
            self.set_status(STATE_USB_CLAIM_INTERFACE_SUCCESS)
            return interface
        except usb.core.USBError:
            self.set_status(STATE_USB_CLAIM_INTERFACE_FAIL)
            raise ConnectionError

    def connect_detach(self, device, interface):
        try:
            if device.is_kernel_driver_active(interface.bInterfaceNumber):
                try:
                    self.set_status(STATE_USB_DETACH_KERNEL)
                    device.detach_kernel_driver(interface.bInterfaceNumber)
                    self.set_status(STATE_USB_DETACH_KERNEL_SUCCESS)
                except usb.core.USBError:
                    self.set_status(STATE_USB_DETACH_KERNEL_FAIL)
                    raise ConnectionError
        except NotImplementedError:
            self.set_status(STATE_USB_DETACH_KERNEL_NOT_IMPLEMENTED)  # Driver does not permit kernel detaching.
            # Non-fatal error.

    def connect_claim(self, device, interface):
        self.set_status(STATE_USB_CLAIM_INTERFACE)
        usb.util.claim_interface(device, interface)
        self.set_status(STATE_USB_CLAIM_INTERFACE_SUCCESS)

    def disconnect_detach(self, device, interface):
        try:
            self.set_status(STATE_USB_ATTACH_KERNEL)
            device.attach_kernel_driver(interface.bInterfaceNumber)
            self.set_status(STATE_USB_ATTACH_KERNEL_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_ATTACH_KERNEL_FAIL)
            # Continue and hope it is non-critical.
        except NotImplementedError:
            self.set_status(STATE_USB_ATTACH_KERNEL_FAIL)

    def disconnect_interface(self, device, interface):
        try:
            self.set_status(STATE_USB_RELEASE_INTERFACE)
            usb.util.release_interface(device, interface)
            self.set_status(STATE_USB_RELEASE_INTERFACE_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_RELEASE_INTERFACE_FAIL)
        self.interface = None

    def disconnect_dispose(self, device):
        self.set_status(STATE_USB_DISPOSING_RESOURCES)
        usb.util.dispose_resources(device)

    def disconnect_reset(self, device):
        self.set_status(STATE_USB_RESET)
        try:
            device.reset()
            self.set_status(STATE_USB_RESET_SUCCESS)
        except usb.core.USBError:
            self.set_status(STATE_USB_RESET_FAIL)

    def CH341OpenDevice(self, index=0):
        """Opens device, returns index."""
        self.set_status(STATE_CONNECTING)
        try:
            device = self.connect_find(index)
            self.devices[index] = device
            interface = self.connect_interface(device)
            self.interface[index] = interface

            self.connect_detach(device, interface)
            self.connect_claim(device, interface)

            self.set_status(STATE_USB_CONNECTED)
        except ConnectionError:
            pass

    def CH341CloseDevice(self, index=0):
        """Closes device."""
        device = self.devices[index]
        interface = self.interface[index]
        self.set_status(STATE_USB_SET_DISCONNECTING)
        if device is not None:
            try:
                self.disconnect_detach(device, interface)
                self.disconnect_interface(device, interface)
                del self.interface[index]
                self.disconnect_dispose(device)
                self.disconnect_reset(device)
                del self.devices[index]
                self.set_status(STATE_USB_DISCONNECTED)
            except ConnectionError:
                pass

    def CH341GetVersion(self, index=0):
        device = self.devices[index]
        buffer = device.ctrl_transfer(bmRequestType=mCH341_VENDOR_READ,
                                      bRequest=mCH341A_GET_VER,
                                      wValue=0,
                                      wIndex=0,
                                      data_or_wLength=2,
                                      timeout=5000)
        if len(buffer) < 0:
            return 2
        else:
            return (buffer[1] << 8) | buffer[0]

    def CH341InitParallel(self, index=0, mode=CH341_PARA_MODE_EPP19):  # Mode 1, we need EPP 1.9
        """Permits setting a mode, but our mode is only 1 since the device is using
        EPP 1.9. This is a control transfer event."""
        device = self.devices[index]
        value = mode << 8
        if mode < 256:
            value |= 2
        device.ctrl_transfer(bmRequestType=mCH341_VENDOR_WRITE,
                             bRequest=mCH341_PARA_INIT,
                             wValue=value,
                             wIndex=0,
                             data_or_wLength=0,
                             timeout=5000)

    def CH341SetParaMode(self, index, mode=CH341_PARA_MODE_EPP19):
        device = self.devices[index]
        value = 0x2525
        device.ctrl_transfer(bmRequestType=mCH341_VENDOR_WRITE,
                             bRequest=mCH341_SET_PARA_MODE,
                             wValue=value,
                             wIndex=index,
                             data_or_wLength=mode << 8 | mode,
                             timeout=5000)

    def CH341EPPWrite(self, index=0, buffer=None, length=0, pipe=0):
        if buffer is not None:
            device = self.devices[index]
            while len(buffer) > 31:
                if pipe == 0:
                    packet = [mCH341_PARA_CMD_W0] + buffer[:30]
                else:
                    packet = [mCH341_PARA_CMD_W1] + buffer[:30]
                buffer = buffer[31:]
                data = convert_to_list_bytes(packet)
                device.write(BULK_WRITE_ENDPOINT, data, 10000)

    def CH341EPPRead(self, index=0, buffer=None, length=0, pipe=0):
        b = self.devices[index].read(BULK_READ_ENDPOINT, length, 10000)
        return b

    def CH341GetStatus(self, index=0, status=[0]):
        """D7-0, 8: err, 9: pEmp, 10: Int, 11: SLCT, 12: SDA, 13: Busy, 14: datats, 15: addrs"""
        self.devices[index].write(BULK_WRITE_ENDPOINT, [mCH341_PARA_CMD_STS], 10000)
        status[0] = self.devices[index].read(BULK_READ_ENDPOINT, 6, 10000)
        return status

    def CH341EppReadData(self, index=0, buffer=None, length=0):  # WR=1, DS=0, AS=1, D0-D7 in
        self.CH341EPPRead(buffer, length, 0)

    def CH341EppReadAddr(self, index=0, buffer=None, length=0):  # WR=1, DS=0, AS=1 D0-D7 in
        self.CH341EPPRead(buffer, length, 1)

    def CH341EppWriteData(self, index, buffer=None, length=0):  # WR=0, DS=0, AS=1, D0-D7 out
        self.CH341EPPWrite(buffer, length, 0)

    def CH341EppWriteAddr(self, index, buffer=None, length=0):  # WR=0, DS=1, AS=0, D0-D7 out
        self.CH341EPPWrite(buffer, length, 1)


class K40Controller:
    def __init__(self, driver=0):
        self.driver = driver
        self.kernel = None

        self.controller_state = STATE_UNINITIALIZED
        self.desired_state = STATE_UNINITIALIZED

        self.process_queue_pause = False
        self.queue_lock = threading.Lock()
        self.usb_lock = threading.Lock()
        self.thread = None

        self.abort_waiting = False

        self.status = STATE_UNINITIALIZED

    def initialize(self, kernel):
        self.kernel = kernel
        if self.driver == 0:
            self.driver = CH341LibusbDriver(kernel)
        else:
            self.driver = windll.LoadLibrary("CH341DLL.dll")
        self.kernel.controller = self
        kernel.setting(int, 'usb_index', -1)
        kernel.setting(int, 'usb_bus', -1)
        kernel.setting(int, 'usb_address', -1)
        kernel.setting(int, 'usb_serial', -1)
        kernel.setting(bool, 'mock', False)
        kernel.setting(int, 'packet_count', 0)
        kernel.setting(int, 'rejected_count', 0)
        kernel.setting(bool, 'autostart_controller', True)
        kernel.setting(str, "_device_log", '')
        kernel.setting(str, "_controller_buffer", b'')
        kernel.setting(str, "_controller_queue", b'')
        kernel.setting(str, "_usb_state", None)

        def start_usb():
            self.desired_state = STATE_CONNECTED
            self.start()

        kernel.add_control("K40Usb-Start", start_usb)

        def stop_usb():
            self.set_usb_status("Disconnecting")
            self.desired_state = STATE_USB_DISCONNECTED

        kernel.add_control("K40Usb-Stop", stop_usb)

        def abort_wait():
            self.abort_waiting = True

        kernel.add_control("K40-Wait Abort", abort_wait)

        self.thread = ControllerQueueThread(self)

        def pause_k40():
            self.pause()

        kernel.add_control("K40-Pause", pause_k40)

        def resume_k40():
            self.resume()

        kernel.add_control("K40-Resume", resume_k40)

        kernel.signal("control_thread", self.thread.state)
        kernel("buffer", 0)
        kernel.add_thread("ControllerQueueThread", self.thread)
        self.set_usb_status("Uninitialized")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iadd__(self, other):
        self.queue_lock.acquire()
        self.kernel._controller_queue += other
        self.queue_lock.release()
        buffer_size = len(self.kernel._controller_buffer) + len(self.kernel._controller_queue)
        self.kernel("buffer", buffer_size)
        if self.kernel.autostart_controller:
            self.start()
        return self

    def log(self, info):
        update = str(info) + '\n'
        self.kernel("usb_log", update)
        self.kernel._device_log += update

    def state(self):
        return self.thread.state

    def start(self):
        if self.thread.state == THREAD_STATE_ABORT:
            # We cannot reset an aborted thread without specifically calling reset.
            return
        if self.thread.state == THREAD_STATE_FINISHED:
            self.thread = ControllerQueueThread(self)
        if self.thread.state == THREAD_STATE_UNSTARTED:
            self.thread.state = THREAD_STATE_STARTED
            self.thread.start()
            self.kernel("control_thread", self.thread.state)

    def resume(self):
        self.process_queue_pause = False
        self.thread.state = THREAD_STATE_STARTED
        self.kernel("control_thread", self.thread.state)

    def pause(self):
        self.process_queue_pause = True
        self.thread.state = THREAD_STATE_PAUSED
        self.kernel("control_thread", self.thread.state)

    def abort(self):
        self.thread.state = THREAD_STATE_ABORT
        packet = b'I' + b'F' * 29
        if self.usb is not None:
            try:
                self.send_packet(packet)
            except usb.core.USBError:
                pass  # Emergency stop was a failure.
        self.kernel._controller_buffer = b''
        self.kernel._controller_queue = b''
        self.kernel("buffer", len(self.kernel._controller_buffer))
        self.kernel("control_thread", self.thread.state)

    def reset(self):
        self.thread = ControllerQueueThread(self)

    def stop(self):
        self.abort()

    def process_queue(self):
        if self.process_queue_pause:
            return False
        if self.usb is None and not self.kernel.mock:
            try:
                self.open()
            except usb.core.USBError:
                return False
        wait_finish = False
        if len(self.kernel._controller_queue):
            self.queue_lock.acquire()
            self.kernel._controller_buffer += self.kernel._controller_queue
            self.kernel._controller_queue = b''
            self.queue_lock.release()
            self.kernel("buffer", len(self.kernel._controller_buffer))
        if len(self.kernel._controller_buffer) == 0:
            return True
        find = self.kernel._controller_buffer.find(b'\n', 0, 30)
        if find != -1:
            length = min(30, len(self.kernel._controller_buffer), find + 1)
        else:
            length = min(30, len(self.kernel._controller_buffer))
        packet = self.kernel._controller_buffer[:length]
        if packet.endswith(b'-'):  # edge condition of "-\n" catching only the '-' exactly at 30.
            packet += self.kernel._controller_buffer[length:length + 1]
            length += 1
        if packet.endswith(b'\n'):
            packet = packet[:-1]
            if packet.endswith(b'-'):
                packet = packet[:-1]
                wait_finish = True
            packet += b'F' * (30 - len(packet))
        # try to send packet
        try:
            self.wait(STATUS_OK)
            if self.process_queue_pause:
                return False  # Paused during wait.
            if len(packet) == 30:
                self.kernel._controller_buffer = self.kernel._controller_buffer[length:]
                self.kernel("buffer", len(self.kernel._controller_buffer))
            else:
                return True  # No valid packet was able to be produced.
            self.send_packet(packet)
        except usb.core.USBError:
            # Execution should have broken at wait. Therefore not corrupting packet. Failed a reconnect demand.
            return False
        if wait_finish:
            self.wait(STATUS_FINISH)
        return False

    def send_packet(self, packet):
        self.driver.CH341EPPWrite(0, packet, len(packet), 0)
        self.kernel.packet_count += 1
        self.kernel("packet", packet)
        self.kernel("packet_text", packet)

    def set_usb_status(self, state):
        if state == self.kernel._usb_state:
            return
        self.kernel._usb_state = state
        self.kernel("usb_state", state)

    def update_status(self):
        if self.kernel.mock:
            self.status = [STATUS_OK] * 6
            time.sleep(0.01)
        else:
            try:
                self.usb.write(BULK_WRITE_ENDPOINT, [mCH341_PARA_CMD_STS], 10000)
            except usb.core.USBError as e:
                self.log("Usb refused status check.")
                while True:
                    try:
                        self.close()
                        self.open()
                    except usb.core.USBError:
                        pass
                    if self.usb is not None:
                        break
                # TODO: will sometimes crash here after failing to actually reclaim USB connection.
                self.usb.write(BULK_WRITE_ENDPOINT, [mCH341_PARA_CMD_STS], 10000)
                self.log("Sending original status check.")
            self.status = self.usb.read(BULK_READ_ENDPOINT, 6, 10000)
        self.kernel("status", self.status)

    def wait(self, value):
        i = 0
        while True:
            self.update_status()
            if self.kernel.mock:  # Mock controller
                self.status = [value] * 6
            status = self.status[1]
            if status == STATUS_PACKET_REJECTED:
                self.kernel.rejected_count += 1
            if status == value:
                break
            time.sleep(0.1)
            self.kernel("wait", (value, i))
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
