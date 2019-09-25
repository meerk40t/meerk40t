import threading
import time

import usb.core
import usb.util

from ThreadConstants import *

STATUS_BAD_STATE = 204
STATUS_OK = 206
STATUS_PACKET_REJECTED = 207
STATUS_FINISH = 236
STATUS_BUSY = 238
STATUS_POWER = 239

STATUS_NO_DEVICE = -1


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
        return "Unknown: " + str(code)


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
        self.controller.listener("control_thread", self.state)

    def run(self):
        self.state = THREAD_STATE_STARTED
        self.controller.listener("control_thread", self.state)
        waited = 0
        self.controller.listener("status_bar", ("Laser On!", 1))
        while self.state != THREAD_STATE_ABORT:
            if self.controller.process_queue():
                time.sleep(0.1)
                waited += 1
                if waited >= 20:
                    break
            else:
                waited = 0
            while self.state == THREAD_STATE_PAUSED:
                self.controller.listener("control_thread", self.state)
                time.sleep(1)
        self.controller.listener("status_bar", (None, 1))
        if self.state == THREAD_STATE_ABORT:
            self.controller.listener("control_thread", self.state)
            return
        self.state = THREAD_STATE_FINISHED
        self.controller.listener("control_thread", self.state)


class UsbConnectThread(threading.Thread):
    def __init__(self, controller):
        threading.Thread.__init__(self)
        self.controller = controller

    def run(self):
        try:
            self.controller.open()
        except usb.core.USBError:
            pass


class UsbDisconnectThread(threading.Thread):
    def __init__(self, controller):
        threading.Thread.__init__(self)
        self.controller = controller

    def run(self):
        try:
            self.controller.close()
        except usb.core.USBError:
            pass


class K40Controller:
    def __init__(self, listener, usb_index=-1, usb_address=-1, usb_bus=-1, mock=False):
        self.listener = listener
        self.usb_index = usb_index
        self.usb_bus = usb_bus
        self.usb_address = usb_address
        self.mock = mock

        self.thread = ControllerQueueThread(self)
        self.listener("control_thread", self.thread.state)

        self.status = None

        self.usb = None
        self.interface = None
        self.detached = False

        self.device_log = ""

        self.process_queue_pause = False
        self.autostart = True

        self.buffer = b''
        self.add_queue = b''
        self.listener("buffer", 0)
        self.packet_count = 0
        self.rejected_count = 0
        self.queue_lock = threading.Lock()
        self.usb_lock = threading.Lock()

        self.usb_status = None
        self.set_usb_status("Uninitialized")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iadd__(self, other):
        self.queue_lock.acquire()
        self.add_queue += other
        self.queue_lock.release()
        self.listener("buffer", len(self.buffer) + len(self.add_queue))
        if self.autostart:
            self.start_queue_consumer()
        return self

    def log(self, info):
        update = str(info) + '\n'
        self.listener("usb_log", update)
        self.device_log += update

    def start_usb(self):
        self.set_usb_status("Connecting")
        usb_thread = UsbConnectThread(self)
        usb_thread.start()

    def stop_usb(self):
        self.set_usb_status("Disconnecting")
        usb_thread = UsbDisconnectThread(self)
        usb_thread.start()

    def emergency_stop(self):
        self.thread.state = THREAD_STATE_ABORT
        packet = b'I' + b'F' * 29
        if self.usb is not None:
            self.send_packet(packet)
        self.buffer = b''
        self.add_queue = b''
        self.listener("buffer", len(self.buffer))
        self.listener("control_thread", self.thread.state)

    def reset_thread(self):
        self.thread = ControllerQueueThread(self)

    def start_queue_consumer(self):
        if self.thread.state == THREAD_STATE_ABORT:
            # We cannot reset an aborted thread without specifically calling reset.
            return
        if self.thread.state == THREAD_STATE_FINISHED:
            self.thread = ControllerQueueThread(self)
        if self.thread.state == THREAD_STATE_UNSTARTED:
            self.thread.state = THREAD_STATE_STARTED
            self.thread.start()
            self.listener("control_thread", self.thread.state)

    def pause(self):
        self.process_queue_pause = True
        self.thread.state = THREAD_STATE_PAUSED
        self.listener("control_thread", self.thread.state)

    def resume(self):
        self.process_queue_pause = False
        self.thread.state = THREAD_STATE_STARTED
        self.listener("control_thread", self.thread.state)

    def process_queue(self):
        if self.process_queue_pause:
            return False
        if self.usb is None and not self.mock:
            try:
                self.open()
            except usb.core.USBError:
                return False
        wait_finish = False
        if len(self.add_queue):
            self.queue_lock.acquire()
            self.buffer += self.add_queue
            self.add_queue = b''
            self.queue_lock.release()
            self.listener("buffer", len(self.buffer))
        if len(self.buffer) == 0:
            return True
        find = self.buffer.find(b'\n', 0, 30)
        if find != -1:
            length = min(30, len(self.buffer), find + 1)
        else:
            length = min(30, len(self.buffer))
        packet = self.buffer[:length]
        if packet.endswith(b'-'):  # edge condition of "-\n" catching only the '-' exactly at 30.
            packet += self.buffer[length:length + 1]
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
                self.buffer = self.buffer[length:]
                self.listener("buffer", len(self.buffer))
            else:
                return True  # No valid packet was able to be produced.
            self.send_packet(packet)
        except usb.core.USBError:
            # Execution should have broken at wait. Therefore not corrupting packet. Failed a reconnect demand.
            return False
        if wait_finish:
            self.wait(STATUS_FINISH)
        return False

    def set_usb_status(self, status):
        if status == self.usb_status:
            return
        self.usb_status = status
        self.listener("usb_status", self.usb_status)

    def open(self):
        self.usb_lock.acquire()
        self.set_usb_status("Connecting")
        self.log("Attempting connection to USB.")
        try:
            devices = usb.core.find(idVendor=0x1A86, idProduct=0x5512, find_all=True)
        except usb.core.NoBackendError:
            self.log("PyUsb detected no backend LibUSB driver.")
            self.set_usb_status("No Driver")
            time.sleep(1)
            return
        d = []
        self.usb = None
        for device in devices:
            self.log("K40 device detected:\n%s\n" % str(device))
            d.append(device)
        if self.usb_index == -1:
            if self.usb_address == -1 and self.usb_bus == -1:
                if len(d) > 0:
                    self.usb = d[0]
            else:
                for dev in d:
                    if (self.usb_address == -1 or self.usb_address == dev.address) and \
                            (self.usb_bus == -1 or self.usb_bus == dev.bus):
                        self.usb = dev
                        break
        else:
            if len(d) > self.usb_index:
                self.usb = d[self.usb_index]
        for i, dev in enumerate(d):
            self.log("Device %d Bus: %d Address %d" % (i, dev.bus, dev.address))
        if self.usb is None:
            self.set_usb_status("Not Found")
            if len(d) == 0:
                self.log("K40 not found.")
            else:
                self.log("K40 devices were found but the configuration requires #%d Bus: %d, Add: %d"
                         % (self.usb_index, self.usb_bus, self.usb_address))
            time.sleep(1)
            self.usb_lock.release()
            raise usb.core.USBError('Unable to find device.')
        self.usb.set_configuration()
        self.log("Device found. Using device: #%d on bus: %d at address %d"
                 % (self.usb_index, self.usb.bus, self.usb.address))
        self.interface = self.usb.get_active_configuration()[(0, 0)]
        try:
            if self.usb.is_kernel_driver_active(self.interface.bInterfaceNumber):
                try:
                    self.log("Attempting to detach kernel")
                    self.usb.detach_kernel_driver(self.interface.bInterfaceNumber)
                    self.log("Kernel detach: Success")
                    self.detached = True
                except usb.core.USBError:
                    self.log("Kernel detach: Failed")
                    self.usb_lock.release()
                    raise usb.core.USBError('Unable to detach from kernel')
        except NotImplementedError:
            self.log("Kernel detach: Not Implemented.")  # Driver does not permit kernel detaching.
        self.log("Attempting to claim interface.")
        usb.util.claim_interface(self.usb, self.interface)
        # TODO: A second attempt to claim the same interface will lag out at this point.
        self.log("Interface claimed.")
        self.log("Requesting Status.")
        self.update_status()
        self.log(str(self.status))
        self.log("Sending control transfer.")
        self.usb.ctrl_transfer(bmRequestType=64, bRequest=177, wValue=258,
                               wIndex=0, data_or_wLength=0, timeout=5000)
        self.log("Requesting Status.")
        self.update_status()
        self.log(str(self.status))
        self.log("USB Connection Successful.")
        self.set_usb_status("Connected")
        self.usb_lock.release()

    def close(self):
        self.usb_lock.acquire()
        self.set_usb_status("Disconnecting")
        self.log("Attempting disconnection from USB.")
        if self.usb is not None:
            if self.detached:
                self.log("Kernel was detached.")
                try:
                    self.log("Attempting kernel attach")
                    self.usb.attach_kernel_driver(self.interface.bInterfaceNumber)
                    self.detached = False
                    self.log("Kernel succesfully attach")
                except usb.core.USBError:
                    self.log("Error while attempting kernel attach")
                    self.usb_lock.release()
                    raise usb.core.USBError('Unable to reattach driver to kernel')
            else:
                self.log("Kernel was not detached.")
            self.log("Attempting to release interface.")
            try:
                usb.util.release_interface(self.usb, self.interface)
                self.log("Interface released")
            except usb.core.USBError:
                self.log("Interface did not exist.")
            self.log("Attempting to dispose resources.")
            usb.util.dispose_resources(self.usb)
            self.log("Resources disposed.")
            self.log("Attempting USB reset.")
            try:
                self.usb.reset()
                self.log("USB reset.")
            except usb.core.USBError:
                self.log("USB connection did not exist.")
            self.interface = None
            self.usb = None
            self.log("USB Disconnection Successful.")
        else:
            self.log("No connection was found.")
        self.set_usb_status("Disconnected")
        self.usb_lock.release()

    def send_packet(self, packet_byte_data):
        if len(packet_byte_data) != 30:
            raise usb.core.USBError('We can only send 30 byte packets.')
        data = convert_to_list_bytes(packet_byte_data)
        packet = [166] + [0] + data + [166] + [onewire_crc_lookup(data)]

        sending = True
        while sending:
            if self.mock:
                time.sleep(0.02)
            else:
                self.usb.write(0x2, packet, 10000)  # usb.util.ENDPOINT_OUT | usb.util.ENDPOINT_TYPE_BULK
            self.packet_count += 1
            self.listener("packet", packet)
            self.listener("packet_text", packet_byte_data)
            self.update_status()
            if self.status[1] != STATUS_PACKET_REJECTED:
                sending = False

    def update_status(self):
        if self.mock:
            self.status = [STATUS_OK] * 6
            time.sleep(0.01)
        else:
            try:
                self.usb.write(0x02, [160], 10000)  # usb.util.ENDPOINT_IN | usb.util.ENDPOINT_TYPE_BULK
            except usb.core.USBError as e:
                self.log("Usb refused status check.")
                self.close()
                self.open()
                self.usb.write(0x02, [160], 10000)
                self.log("Sending original status check.")
            self.status = self.usb.read(0x82, 6, 10000)
        self.listener("status", self.status)

    def wait(self, value):
        i = 0
        while True:
            self.update_status()
            if self.mock:  # Mock controller
                self.status = [value] * 6
            status = self.status[1]
            if status == STATUS_PACKET_REJECTED:
                self.rejected_count += 1
            if status == value:
                break
            time.sleep(0.1)
            self.listener("wait", (value, i))
            i += 1
