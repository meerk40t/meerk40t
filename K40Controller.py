import time
import usb.core
import usb.util


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


class K40Controller:
    def __init__(self):
        self.status = None
        self.usb = None
        self.interface = None
        self.detached = False
        self.listener = None

        self.queue = []
        self.buffer = b''

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iadd__(self, other):
        self.buffer += other
        self.process_queue()
        return self

    def process_queue(self):
        if self.usb is None:
            try:
                self.open()
            except usb.core.USBError:
                self.status = STATUS_NO_DEVICE
                if self.listener is not None:
                    self.listener(1, self.status)
                return
        wait_finish = False
        while True:
            while len(self.buffer) <= 30:
                if len(self.queue) == 0:
                    return  # buffer isn't enough and queue is empty.
                item = self.queue.pop()
                if item[-1] == b'\n':
                    item = item[0:-1]
                    self.pad_buffer()
                if item[-1] == b'-':
                    wait_finish = True
                self.buffer += self.queue.pop()
            # buffer has enough to send a packet.
            packet = self.buffer[0:30]
            self.buffer = self.buffer[30:]

            self.usb.wait(STATUS_OK)
            self.usb.send_packet(convert_to_list_bytes(packet))
            if wait_finish:
                self.usb.wait(STATUS_FINISH)

    def pad_buffer(self):
        self.buffer += b'F' * (len(self.buffer) % 30)

    def open(self):
        self.usb = usb.core.find(idVender=0x1A86, idProduct=0x5512)
        if self.usb is None:
            raise usb.core.USBError('Unable to find device.')
        self.usb.set_configuration()
        self.interface = self.usb.get_active_configuration()[(0, 0)]
        if self.usb.is_kernel_driver_active(self.interface.bInterfaceNumber):
            try:
                self.usb.detach_kernel_driver(self.interface.bInterfaceNumber)
                self.detached = True
            except usb.core.USBError:
                raise usb.core.USBError('Unable to detach from kernel')
        usb.util.claim_interface(self.usb, self.interface)
        self.usb.ctrl_transfer(bmRequestType=64, bRequest=177, wValue=258,
                               wIndex=0, data_or_wLength=0, timeout=5000)

    def close(self):
        if self.usb is not None:
            if self.detached:
                try:
                    self.usb.attach_kernel_driver(self.interface.bInterfaceNumber)
                    self.detached = False
                except usb.core.USBError:
                    raise usb.core.USBError('Unable to reattach driver to kernel')
            usb.util.release_interface(self.usb, self.interface)
            usb.util.dispose_resources(self.usb)
            self.usb.reset()
            self.interface = None
            self.usb = None

    def send_packet(self, data):
        if len(data) != 30:
            raise usb.core.USBError('We can only send 30 byte packets.')
        packet = [166] + [0] + data + [166] + [onewire_crc_lookup(data)]

        sending = True
        while sending:
            self.usb.write(0x82, packet, 10000)  # usb.util.ENDPOINT_OUT | usb.util.ENDPOINT_TYPE_BULK
            if self.listener is not None:
                self.listener(0, packet)
            self.update_status()
            if self.status[1] != STATUS_PACKET_REJECTED:
                sending = False

    def update_status(self):
        self.usb.write(0x82, [160], 10000)
        self.status = self.usb.read(0x02, 6, 10000)  # usb.util.ENDPOINT_IN | usb.util.ENDPOINT_TYPE_BULK
        if self.listener is not None:
            self.listener(1, self.status)

    def wait(self, value):
        i = 0
        while True:
            self.update_status()
            if self.status[1] == value:
                break
            time.sleep(0.1)
            if self.listener is not None:
                if self.listener(2, i):
                    break
            i += 1
