import threading

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
        threading.Thread.__init__(self)
        self.controller = controller
        self.state = None
        self.set_state(THREAD_STATE_UNSTARTED)

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.controller.thread_state_update(self.state)

    def run(self):
        self.set_state(THREAD_STATE_STARTED)
        while self.controller.state == THREAD_STATE_UNSTARTED:
            time.sleep(0.1)  # Already started. Unstarted is the desired state. Wait.

        count = 0
        while self.controller.state != THREAD_STATE_ABORT:

            if self.controller.process_queue():
                # Some queue was processed.
                count = 0
            else:
                # No packet could be sent.
                if count > 100:
                    count = 100
                time.sleep(0.01 * count)  # will tick up to 1 second waits if process queue never works.
                count += 1
            while self.controller.state == THREAD_STATE_PAUSED:
                self.set_state(THREAD_STATE_PAUSED)
                time.sleep(1)
            if len(self.controller) == 0 and self.controller.state == THREAD_STATE_FINISHED:
                # If finished is the desired state we need to actually be finished.
                break
        if self.controller.state == THREAD_STATE_ABORT:
            self.set_state(THREAD_STATE_ABORT)
            return
        else:
            self.set_state(THREAD_STATE_FINISHED)


class K40Controller(Pipe):
    def __init__(self, backend=None):
        Pipe.__init__(self, backend)
        self.driver = None
        self.driver_index = 0
        self.state = THREAD_STATE_UNSTARTED

        self.buffer = b''  # Threadsafe buffered commands to be sent to controller.
        self.queue = b''  # Thread-unsafe additional commands to append.
        self.queue_lock = threading.Lock()
        self.thread = None
        self.mock = backend.kernel.mock
        self.packet_count = 0
        self.rejected_count = 0

        self.abort_waiting = False
        self.status = [0] * 6

        self.driver = None
        self.thread = None
        self.reset()

        def start_usb():
            self.state = THREAD_STATE_STARTED
            self.start()

        self.backend.add_control("Start", start_usb)

        def stop_usb():
            self.state = THREAD_STATE_FINISHED

        self.backend.add_control("Stop", stop_usb)

        def abort_wait():
            self.abort_waiting = True

        self.backend.add_control("Wait Abort", abort_wait)

        def pause_k40():
            self.state = THREAD_STATE_PAUSED
            self.start()

        self.backend.add_control("Pause", pause_k40)

        def resume_k40():
            self.state = THREAD_STATE_STARTED
            self.start()

        self.backend.add_control("Resume", resume_k40)

    def __len__(self):
        return len(self.buffer) + len(self.queue)

    def thread_state_update(self, state):
        self.backend.signal('pipe;thread', state)

    @property
    def name(self):
        return self.backend.uid

    def open(self):
        if self.driver is None:
            self.detect_driver()
        if self.driver is None:
            raise ConnectionRefusedError
        self.driver.open()

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def write(self, bytes_to_write):
        self.queue_lock.acquire()
        self.queue += bytes_to_write
        self.queue_lock.release()
        self.start()
        return self

    def read(self, size=-1):
        return self.status

    def realtime_write(self, bytes_to_write):
        """Must write directly to the controller without delay."""
        pass

    def detect_driver(self):
        # TODO: Match the specific requirements of the backend driver protocol.
        # If you match more than one device. You should connect to the one that lets you connect.
        try:
            from CH341LibusbDriver import CH341Driver
            self.driver = driver = CH341Driver(self.driver_index)
            driver.open()
            chip_version = driver.get_chip_version()
            driver.close()
        except: # Import Error (libusb isn't installed), ConnectionRefusedError (wrong driver)
            try:
                from CH341WindllDriver import CH341Driver
                self.driver = driver = CH341Driver(self.driver_index)
                driver.open()
                chip_version = driver.get_chip_version()
                driver.close()
            except:
                self.driver = None

    def log(self, info):
        update = str(info) + '\n'
        self.backend.log(update)

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
        self.backend.signal('pipe;buffer', 0)

    def reset(self):
        self.thread = ControllerQueueThread(self)
        self.backend.add_thread("controller;thread", self.thread)

    def stop(self):
        self.abort()

    def process_queue(self):
        """
        Attempts to process the buffer/queue
        Will fail on ConnectionRefusedError at open.
        process_queue_pause = True anytime before packet send.
        self.buffer is empty.
        Failure to produce packet.

        :return: some queue was processed.
        """
        if self.state == THREAD_STATE_PAUSED:
            return False
        # if self.driver_index in  == STATE_USB_CONNECTED and not self.kernel.mock:
        try:
            self.open()
        except ConnectionRefusedError:
            return False

        wait_finish = False
        if len(self.queue):
            self.queue_lock.acquire()
            self.buffer += self.queue
            self.queue = b''
            self.queue_lock.release()
            self.backend.signal('pipe;buffer', len(self.buffer))
        if len(self.buffer) == 0:
            return False
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
            self.wait_ok()
        except ConnectionError:
            return False
        if self.state == THREAD_STATE_PAUSED:
            return False  # Paused during packet fetch.

        # TODO: Remove packet from queue only once sent. If send_packet errors, queue is still correct.
        if len(packet) == 30:
            self.buffer = self.buffer[length:]
            self.backend.signal('pipe;buffer', len(self.buffer))
        else:
            return False  # No valid packet was able to be produced.
        self.send_packet(packet)

        if wait_finish:
            self.wait_finished()
        return True  # A packet was prepped and sent correctly.

    def send_packet(self, packet):
        if self.mock:
            time.sleep(0.1)
        else:
            packet = b'\x00' + packet + bytes([onewire_crc_lookup(packet)])
            self.driver.write(packet)

        self.packet_count += 1
        self.backend.signal("pipe;packet", convert_to_list_bytes(packet))
        self.backend.signal("pipe;packet_text", packet)

    def update_status(self):
        if self.mock:
            self.status = [255, 206, 0, 0, 0, 0]
            time.sleep(0.01)
        else:
            self.status = self.driver.get_status()
        self.backend.signal("pipe;status", self.status)

    def wait_ok(self):
        i = 0
        while True:
            self.update_status()
            status = self.status[1]
            if status == 0:
                raise ConnectionError
            if status == STATUS_PACKET_REJECTED:
                self.rejected_count += 1
            if status == STATUS_OK:
                break
            time.sleep(0.1)
            self.backend.signal("pipe;wait", STATUS_OK, i)
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

    def wait_finished(self):
        i = 0
        while True:
            self.update_status()
            if self.mock:  # Mock controller
                self.status = [255, STATUS_FINISH, 0, 0, 0, 0]
            status = self.status[1]
            if status == STATUS_PACKET_REJECTED:
                self.rejected_count += 1
            if status & 0x02 == 0:
                # StateBitPEMP = 0x00000200, Finished = 0xEC, 11101100
                break
            time.sleep(0.05)
            self.backend.signal("pipe;wait", (status, i))
            i += 1
            if self.abort_waiting:
                self.abort_waiting = False
                return  # Wait abort was requested.

