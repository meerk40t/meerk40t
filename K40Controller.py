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
        self.state = THREAD_STATE_UNSTARTED
        self.controller = controller
        self.controller.listener("control_thread", self.state)

    def run(self):
        self.state = THREAD_STATE_STARTED
        self.controller.listener("control_thread", self.state)
        waited = 0
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
        if self.state == THREAD_STATE_ABORT:
            self.controller.listener("control_thread", self.state)
        self.state = THREAD_STATE_FINISHED
        self.controller.listener("control_thread", self.state)


class K40Controller:
    def __init__(self, listener, usb_index=0, usb_address=-1, usb_bus=-1, mock=False):
        self.listener = listener
        self.usb_index = usb_index
        self.usb_bus = usb_bus  # TODO: permit selecting which device to used based on the USB bus and address variables.
        self.usb_address = usb_address
        self.mock = mock

        self.thread = ControllerQueueThread(self)

        self.status = None

        self.usb = None
        self.interface = None
        self.detached = False

        self.device_log = ""

        self.pause = False
        self.autostart = True

        self.buffer = b''
        self.add_queue = b''
        self.listener("buffer", 0)
        self.packet_count = 0
        self.rejected_count = 0
        self.lock = threading.Lock()
        self.usb_status = None
        self.set_usb_status("Uninitalized")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iadd__(self, other):
        self.lock.acquire()
        self.add_queue += other
        self.lock.release()
        self.listener("buffer", len(self.buffer) + len(self.add_queue))
        if self.autostart:
            self.start_queue_consumer()
        return self

    def log(self, info):
        update = str(info) + '\n'
        self.listener("usb_log", update)
        self.device_log += update

    def start_usb(self):
        try:
            self.open()
        except usb.core.USBError:
            if self.status != STATUS_NO_DEVICE:
                self.status = STATUS_NO_DEVICE
                self.listener("status", self.status)
            return False
        return True

    def start_queue_consumer(self):
        if self.thread.state == THREAD_STATE_FINISHED:
            self.thread = ControllerQueueThread(self)
        if self.thread.state == THREAD_STATE_UNSTARTED:
            self.thread.start()

    def process_queue(self):
        if self.pause:
            return False
        if self.usb is None and not self.mock:
            if not self.start_usb():
                return False
        wait_finish = False
        if len(self.add_queue):
            self.lock.acquire()
            self.buffer += self.add_queue
            self.add_queue = b''
            self.lock.release()
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
            if self.pause:
                return False  # Paused during wait.
            if len(packet) == 30:
                self.buffer = self.buffer[length:]
                self.listener("buffer", len(self.buffer))
            else:
                return True # No valid packet was able to be produced.
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
        self.set_usb_status("Connecting")
        self.log("Attempting connection to USB.")
        devices = usb.core.find(idVendor=0x1A86, idProduct=0x5512, find_all=True)
        d = []
        self.usb = None
        for device in devices:
            self.log("K40 device detected:\n%s\n" % str(device))
            d.append(device)
        if len(d) > self.usb_index:
            self.usb = d[self.usb_index]
        for i, dev in enumerate(d):
            self.log("Device %d Bus: %d Address %d" % (i, dev.bus, dev.address))  # TODO: Verify functions
        if self.usb is None:
            self.set_usb_status("Not Found")
            if len(d) == 0:
                self.log("K40 not found.")
            else:
                self.log("K40 devices were found but the configuration requires #%d." % self.usb_index)
                time.sleep(1)
            raise usb.core.USBError('Unable to find device.')
        self.usb.set_configuration()
        self.log("Device found. Using device: #%d on bus: %d at address %d"
                 % (self.usb_index, self.usb.bus, self.usb.address))  # TODO: Verify functions
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
                    raise usb.core.USBError('Unable to detach from kernel')
        except NotImplementedError:
            self.log("Kernel detach: Not Implemented.")  # Driver does not permit kernel detaching.
        self.log("Attempting to claim interface.")
        usb.util.claim_interface(self.usb, self.interface)
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

    def close(self):
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
        self.set_usb_status("Disconnecting")

    def send_packet(self, packet_byte_data):
        if len(packet_byte_data) != 30:
            raise usb.core.USBError('We can only send 30 byte packets.')
        data = convert_to_list_bytes(packet_byte_data)
        packet = [166] + [0] + data + [166] + [onewire_crc_lookup(data)]

        sending = True
        while sending:
            if not self.mock:
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
