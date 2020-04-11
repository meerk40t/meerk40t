import threading

from CH341DriverBase import *
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
    elif code == 0:
        return "USB Failed"
    else:
        return "UNK %02x" % code


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
    """
    The ControllerQueue thread matches the state of the controller to the state
    of the thread and processes the queue. If you set the controller to
    THREAD_ABORTED it will abort, if THREAD_FINISHED it will finish. THREAD_PAUSE
    it will pause.
    """

    def __init__(self, controller):
        threading.Thread.__init__(self, name='K40-Controller')
        self.controller = controller
        self.state = None
        self.set_state(THREAD_STATE_UNSTARTED)
        self.max_attempts = 5

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.controller.thread_state_update(self.state)

    def run(self):

        self.set_state(THREAD_STATE_STARTED)
        while self.controller.state == THREAD_STATE_UNSTARTED:
            time.sleep(0.1)  # Already started. Unstarted is the desired state. Wait.

        refuse_counts = 0
        connection_errors = 0
        count = 0
        while self.controller.state != THREAD_STATE_ABORT:
            try:
                queue_processed = self.controller.process_queue()
                refuse_counts = 0
            except ConnectionRefusedError:
                refuse_counts += 1
                time.sleep(3)  # 3 second sleep on failed connection attempt.
                if refuse_counts >= self.max_attempts:
                    self.controller.state = THREAD_STATE_ABORT
                    self.controller.device.signal('pipe;error', refuse_counts)
                continue
            except ConnectionError:
                connection_errors += 1
                time.sleep(0.5)
                self.controller.close()
                continue
            if queue_processed:
                count = 0
            else:
                # No packet could be sent.
                if count > 10:
                    if self.controller.device.quit:
                        self.controller.state = THREAD_STATE_FINISHED
                if count > 100:
                    count = 100
                time.sleep(0.01 * count)  # will tick up to 1 second waits if process queue never works.
                count += 2
                if self.controller.state == THREAD_STATE_PAUSED:
                    self.set_state(THREAD_STATE_PAUSED)
                    while self.controller.state == THREAD_STATE_PAUSED:
                        time.sleep(1)
                        if self.controller.state == THREAD_STATE_ABORT:
                            self.set_state(THREAD_STATE_ABORT)
                            return
                    self.set_state(THREAD_STATE_STARTED)
            if len(self.controller) == 0 and self.controller.state == THREAD_STATE_FINISHED:
                # If finished is the desired state we need to actually be finished.
                break
        if self.controller.state == THREAD_STATE_ABORT:
            self.set_state(THREAD_STATE_ABORT)
            return
        else:
            self.set_state(THREAD_STATE_FINISHED)


class K40Controller(Module, Pipe):
    """
    K40 Controller controls the primary Lhystudios boards sending any queued data to the USB when the signal is not
    busy.

    This is registered in the kernel as a module. Saving a few persistent settings like packet_count and registering
    a couple controls like Connect_USB.

    This is also a Pipe. Elements written to the Controller are sent to the USB to the matched device. Opening and
    closing of the pipe are dealt with internally. There are two primary monitor data channels. 'status' and 'log'
    elements monitoring this pipe will be updated on the status. Of the reading and writing of the connected information
    and the log will provide information about the connected and error status of the USB device.
    """

    def __init__(self):
        Pipe.__init__(self)
        self.debug_file = None
        self.driver = None
        self.device = None
        self.state = THREAD_STATE_UNSTARTED

        self.buffer = b''  # Threadsafe buffered commands to be sent to controller.
        self.queue = b''  # Thread-unsafe additional commands to append.
        self.preempt = b''  # Thread-unsafe preempt commands to prepend to the buffer.
        self.queue_lock = threading.Lock()
        self.preempt_lock = threading.Lock()

        self.status = [0] * 6
        self.usb_state = -1

        self.driver = None
        self.thread = None

        self.abort_waiting = False

    def initialize(self, kernel, name=None):
        self.device = kernel.device
        self.device.setting(int, 'packet_count', 0)
        self.device.setting(int, 'rejected_count', 0)

        self.device.control_instance_add("Connect_USB", self.open)
        self.device.control_instance_add("Disconnect_USB", self.close)
        self.device.control_instance_add("Start", self.start)
        self.device.control_instance_add("Stop", self.stop)
        self.device.control_instance_add("Status Update", self.update_status)
        self.reset()

        def abort_wait():
            self.abort_waiting = True

        self.device.control_instance_add("Wait Abort", abort_wait)

        def pause_k40():
            self.state = THREAD_STATE_PAUSED
            self.start()

        self.device.control_instance_add("Pause", pause_k40)

        def resume_k40():
            self.state = THREAD_STATE_STARTED
            self.start()

        self.device.control_instance_add("Resume", resume_k40)

    def __repr__(self):
        return "K40Controller()"

    def __len__(self):
        return len(self.buffer) + len(self.queue) + len(self.preempt)

    def thread_state_update(self, state):
        if self.device is not None:
            self.device.signal('pipe;thread', state)

    def open(self):
        if self.driver is None:
            self.detect_driver_and_open()
        else:
            # Update criteria
            self.driver.index = self.device.usb_index
            self.driver.bus = self.device.usb_bus
            self.driver.address = self.device.usb_address
            self.driver.serial = self.device.usb_serial
            self.driver.chipv = self.device.usb_version
            self.driver.open()
        if self.driver is None:
            raise ConnectionRefusedError

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def write(self, bytes_to_write):
        self.queue_lock.acquire(True)
        self.queue += bytes_to_write
        self.queue_lock.release()
        self.start()
        return self

    def realtime_write(self, bytes_to_write):
        """
        Preempting commands.
        Commands to be sent to the front of the buffer.
        """
        self.preempt_lock.acquire(True)
        self.preempt = bytes_to_write + self.preempt
        self.preempt_lock.release()
        self.start()
        if self.state == THREAD_STATE_PAUSED:
            self.state = THREAD_STATE_STARTED
        return self

    def state_listener(self, code):
        if isinstance(code, int):
            self.usb_state = code
            name = get_name_for_status(code, translation=self.device.kernel.translation)
            self.log(name)
            self.device.signal("pipe;usb_state", code)
            self.device.signal("pipe;usb_status", name)
        else:
            self.log(str(code))

    def detect_driver_and_open(self):
        index = self.device.usb_index
        bus = self.device.usb_bus
        address = self.device.usb_address
        serial = self.device.usb_serial
        chipv = self.device.usb_version

        try:
            from CH341LibusbDriver import CH341Driver
            self.driver = driver = CH341Driver(index=index, bus=bus, address=address, serial=serial, chipv=chipv,
                                               state_listener=self.state_listener)
            driver.open()
            chip_version = driver.get_chip_version()
            self.state_listener(INFO_USB_CHIP_VERSION | chip_version)
            self.device.signal("pipe;chipv", chip_version)
            self.state_listener(INFO_USB_DRIVER | STATE_DRIVER_LIBUSB)
            self.state_listener(STATE_CONNECTED)
            return
        except ConnectionRefusedError:
            self.driver = None
        except ImportError:
             self.state_listener(STATE_DRIVER_NO_LIBUSB)
        try:
            from CH341WindllDriver import CH341Driver
            self.driver = driver = CH341Driver(index=index, bus=bus, address=address, serial=serial, chipv=chipv,
                                               state_listener=self.state_listener)
            driver.open()
            chip_version = driver.get_chip_version()
            self.state_listener(INFO_USB_CHIP_VERSION | chip_version)
            self.device.signal("pipe;chipv", chip_version)
            self.state_listener(INFO_USB_DRIVER | STATE_DRIVER_CH341)
            self.state_listener(STATE_CONNECTED)
        except ConnectionRefusedError:
            self.driver = None

    def log(self, info):
        update = str(info) + '\n'
        self.device.log(update)
        self.post('log', update)

    def state(self):
        return self.thread.state

    def start(self):
        if self.state == THREAD_STATE_ABORT:
            # We cannot reset an aborted thread without specifically calling reset.
            return
        if self.state == THREAD_STATE_FINISHED:
            self.reset()
        if self.state == THREAD_STATE_UNSTARTED:
            self.state = THREAD_STATE_STARTED
            self.thread.start()

    def resume(self):
        self.state = THREAD_STATE_STARTED
        if self.thread.state == THREAD_STATE_UNSTARTED:
            self.thread.start()

    def pause(self):
        self.state = THREAD_STATE_PAUSED
        if self.thread.state == THREAD_STATE_UNSTARTED:
            self.thread.start()

    def abort(self):
        self.state = THREAD_STATE_ABORT
        self.buffer = b''
        self.queue = b''
        self.device.signal('pipe;buffer', 0)

    def reset(self):
        self.thread = ControllerQueueThread(self)
        self.device.thread_instance_add("controller;thread", self.thread)
        self.state = THREAD_STATE_UNSTARTED

    def stop(self):
        self.abort()

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open, 'process_queue_pause = True' (anytime before packet sent),
        self.buffer is empty, or a failure to produce packet.

        Buffer will not be changed unless packet is successfully sent, or pipe commands are processed.

        - : tells the system to require wait finish at the end of the queue processing.
        * : tells the system to clear the buffers, and abort the thread.
        ! : tells the system to pause.
        & : tells the system to resume.

        :return: queue process success.
        """
        if len(self.queue):  # check for and append queue
            self.queue_lock.acquire(True)
            self.buffer += self.queue
            self.queue = b''
            self.queue_lock.release()
            self.device.signal('pipe;buffer', len(self.buffer))

        if len(self.preempt):  # check for and prepend preempt
            self.preempt_lock.acquire(True)
            self.buffer = self.preempt + self.buffer
            self.preempt = b''
            self.preempt_lock.release()
        if len(self.buffer) == 0:
            return False

        # Find buffer of 30 or containing '\n'.
        find = self.buffer.find(b'\n', 0, 30)
        if find == -1:  # No end found.
            length = min(30, len(self.buffer))
        else:  # Line end found.
            length = min(30, len(self.buffer), find + 1)
        packet = self.buffer[:length]

        # edge condition of catching only pipe command without '\n'
        if packet.endswith((b'-', b'*', b'&', b'!')):
            packet += self.buffer[length:length + 1]
            length += 1
        post_send_command = None
        # find pipe commands.
        if packet.endswith(b'\n'):
            packet = packet[:-1]
            if packet.endswith(b'-'):  # wait finish
                packet = packet[:-1]
                post_send_command = self.wait_finished
            elif packet.endswith(b'*'):  # abort
                post_send_command = self.abort
                packet = packet[:-1]
            elif packet.endswith(b'&'):  # resume
                self.resume()  # resume must be done before checking pause state.
                packet = packet[:-1]
            elif packet.endswith(b'!'):  # pause
                post_send_command = self.pause
                packet = packet[:-1]
            if len(packet) != 0:
                packet += b'F' * (30 - len(packet))  # Padding. '\n'
        if self.state == THREAD_STATE_PAUSED:
            return False  # Abort due to pause.

        # Packet is prepared and ready to send.
        if self.device.mock:
            self.state_listener(STATE_DRIVER_MOCK)
        else:
            self.open()

        if len(packet) == 30:
            # check that latest state is okay.
            try:
                self.wait_until_accepting_packets()
            except ConnectionError:
                return False  # Wait suffered connection error.

            if self.state == THREAD_STATE_PAUSED:
                return False  # Paused during packet fetch.

            try:
                self.send_packet(packet)
            except ConnectionError:
                return False  # Error exactly at packet send assumes no packet sent.
            attempts = 0
            status = 0
            while attempts < 300:  # 200 * 300 = 60,000 = 60 seconds.
                try:
                    self.update_status()
                    status = self.status[1]
                    break
                except ConnectionError:
                    attempts += 1
            if status == STATUS_PACKET_REJECTED:
                self.device.rejected_count += 1
                time.sleep(0.05)
                # The packet was rejected. The sent data was not accepted. Return False.
                return False
            if status == 0:
                raise ConnectionError  # Broken pipe.
            self.device.packet_count += 1  # Everything went off without a problem.
        else:
            if len(packet) != 0:  # packet isn't purely a commands len=0, or filled 30.
                return False  # This packet cannot be sent. Toss it back.

        # Packet was processed.
        self.buffer = self.buffer[length:]
        self.device.signal('pipe;buffer', len(self.buffer))

        if post_send_command is not None:
            # Post send command could be wait_finished, and might have a broken pipe.
            try:
                post_send_command()
            except ConnectionError:
                # We should have already sent the packet. So this should be fine.
                pass
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        if self.device.mock:
            time.sleep(0.04)
        else:
            packet = b'\x00' + packet + bytes([onewire_crc_lookup(packet)])
            self.driver.write(packet)
        self.device.signal("pipe;packet", convert_to_list_bytes(packet))
        self.device.signal("pipe;packet_text", packet)
        self.post('send', packet)

    def update_status(self):
        if self.device.mock:
            self.status = [255, 206, 0, 0, 0, 1]
            time.sleep(0.01)
        else:
            self.status = self.driver.get_status()
        self.device.signal("pipe;status", self.status)
        self.post('recv', self.status)

    def wait_until_accepting_packets(self):
        i = 0
        while self.state != THREAD_STATE_ABORT:
            self.update_status()
            status = self.status[1]
            if status == 0:
                raise ConnectionError
            # StateBitWAIT = 0x00002000, 204, 206, 207
            if status & 0x20 == 0:
                break
            time.sleep(0.05)
            self.device.signal("pipe;wait", STATUS_OK, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        while True:
            self.update_status()
            if self.device.mock:  # Mock controller
                self.status = [255, STATUS_FINISH, 0, 0, 0, 1]
            status = self.status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_PACKET_REJECTED:
                self.device.rejected_count += 1
            if status & 0x02 == 0:
                # StateBitPEMP = 0x00000200, Finished = 0xEC, 11101100
                break
            time.sleep(0.05)
            self.device.signal("pipe;wait", status, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.
