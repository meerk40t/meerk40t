import ctypes
import threading

from CH341LibusbDriver import STATE_USB_CONNECTED
from Kernel import *
from ctypes import c_byte, c_int, c_void_p, byref

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
        return "Unknown: %d" % code


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
    The ControllerQueue thread matches the state of the controller to the state of the thread and processes the queue.
    If you set the controller to THREAD_ABORTED it will abort, if THREAD_FINISHED it will finish. THREAD_PAUSE it will
    pause.
    """
    def __init__(self, controller):
        threading.Thread.__init__(self)
        self.controller = controller

        self.state = THREAD_STATE_UNSTARTED
        self.controller.kernel("control_thread", self.state)

    def run(self):
        if self.controller.state == THREAD_STATE_UNSTARTED:
            self.state = THREAD_STATE_UNSTARTED
            return
        self.state = THREAD_STATE_STARTED
        self.controller.kernel("control_thread", self.state)

        # waited = 0
        while self.controller.state != THREAD_STATE_ABORT:
            if self.controller.process_queue():
                time.sleep(0.1)
            #     waited += 1
            #     if waited >= 20:
            #         break
            # else:
            #     waited = 0
            while self.controller.state == THREAD_STATE_PAUSED:
                self.state = THREAD_STATE_PAUSED
                self.controller.kernel("control_thread", self.state)
                time.sleep(1)
            if len(self.controller) == 0 and self.controller.state == THREAD_STATE_FINISHED:
                break
        if self.controller.state == THREAD_STATE_ABORT:
            self.state = THREAD_STATE_ABORT
            self.controller.kernel("control_thread", self.state)
            return
        else:
            self.state = THREAD_STATE_FINISHED
            self.controller.kernel("control_thread", self.state)


class K40Controller(Pipe):
    def __init__(self, kernel):
        Pipe.__init__(self, kernel)
        self.driver = None
        self.driver_index = 0
        self.state = THREAD_STATE_UNSTARTED

        self.process_queue_pause = False
        self.queue_lock = threading.Lock()
        self.thread = None

        self.abort_waiting = False
        self.status = [0] * 6

        kernel.setting(int, 'usb_index', -1)
        kernel.setting(int, 'usb_bus', -1)
        kernel.setting(int, 'usb_address', -1)
        kernel.setting(int, 'usb_serial', -1)
        kernel.setting(int, 'usb_chip_version', -1)

        kernel.setting(bool, 'mock', False)
        kernel.setting(int, 'packet_count', 0)
        kernel.setting(int, 'rejected_count', 0)
        kernel.setting(bool, 'autostart_controller', True)
        kernel.setting(str, "_device_log", '')
        kernel.setting(str, "_controller_buffer", b'')
        kernel.setting(str, "_controller_queue", b'')
        kernel.setting(str, "_usb_state", None)
        self.kernel = kernel
        self.driver = None
        self.thread = ControllerQueueThread(self)

        def start_usb():
            self.state = THREAD_STATE_STARTED
            self.start()

        kernel.add_control("K40Usb-Start", start_usb)

        def stop_usb():
            self.state = THREAD_STATE_FINISHED

        kernel.add_control("K40Usb-Stop", stop_usb)

        def abort_wait():
            self.abort_waiting = True

        kernel.add_control("K40-Wait Abort", abort_wait)

        def pause_k40():
            self.state = THREAD_STATE_PAUSED
            self.start()

        kernel.add_control("K40-Pause", pause_k40)

        def resume_k40():
            self.state = THREAD_STATE_STARTED
            self.start()

        kernel.add_control("K40-Resume", resume_k40)

        kernel.signal("control_thread", self.thread.state)
        kernel("buffer", 0)
        kernel.add_thread("ControllerQueueThread", self.thread)
        self.set_usb_status("Uninitialized")

    def __len__(self):
        return len(self.kernel._controller_buffer) + len(self.kernel._controller_queue)

    def __iadd__(self, other):
        self.queue_lock.acquire()
        self.kernel._controller_queue += other
        self.queue_lock.release()
        buffer_size = len(self)
        self.kernel("buffer", buffer_size)
        if self.kernel.autostart_controller:
            self.start()
        return self

    def detect_driver(self):
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

    def open(self):
        if self.driver is None:
            self.detect_driver()
        self.driver.open()

    def close(self):
        self.driver.close()

    def log(self, info):
        update = str(info) + '\n'
        self.kernel("usb_log", update)
        self.kernel._device_log += update

    def state(self):
        return self.thread.state

    def start(self):
        if self.state == THREAD_STATE_ABORT:
            # We cannot reset an aborted thread without specifically calling reset.
            return
        if self.state == THREAD_STATE_FINISHED:
            self.thread = ControllerQueueThread(self)
        if self.state == THREAD_STATE_UNSTARTED:
            self.state = THREAD_STATE_STARTED
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
        # packet = b'I' + b'F' * 29
        # if self.usb is not None:
        #     try:
        #         self.send_packet(packet)
        #     except usb.core.USBError:
        #         pass  # Emergency stop was a failure.
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
        # if self.driver_index in  == STATE_USB_CONNECTED and not self.kernel.mock:
        try:
            self.open()
        except ConnectionRefusedError:
            return True
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
        self.wait(STATUS_OK)
        if self.process_queue_pause:
            return False  # Paused during wait.
        if len(packet) == 30:
            self.kernel._controller_buffer = self.kernel._controller_buffer[length:]
            self.kernel("buffer", len(self.kernel._controller_buffer))
        else:
            return True  # No valid packet was able to be produced.
        self.send_packet(packet)

        if wait_finish:
            self.wait(STATUS_FINISH)
        return False

    def send_packet(self, packet):
        if self.kernel.mock:
            time.sleep(0.1)
        else:
            packet = b'\x00' + packet + bytes([onewire_crc_lookup(packet)])
            self.driver.write(packet)

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
            self.status = self.driver.get_status()
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
