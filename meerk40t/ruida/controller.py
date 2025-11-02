"""
Ruida Encoder

The Ruida Encoder is responsible for turning function calls into binary ruida data.
"""
import threading
import time

from meerk40t.ruida.rdjob import (
    MEM_CARD_ID,
    MEM_BED_SIZE_X,
    MEM_BED_SIZE_Y,
    MEM_CURRENT_X,
    MEM_CURRENT_Y,
    MEM_CURRENT_Z,
    MEM_CURRENT_U,
    STATUS_ADDRESSES,
    RDJob)


class RuidaController:
    """
    Implements the Ruida protocol data sending.
    """

    def __init__(self, service, pipe, magic=-1):
        self.service = service
        self.mode = "init"
        self.paused = False

        self.write = pipe

        self.job = RDJob()
        self._send_queue = []
        self._send_thread = None
        self.events = service.channel(f"{service.safe_label}/events")
        self._status_thread_sleep = 0.25 # Time between polls.
        self._connected = False
        self._job_lock = threading.Lock() # To allow running a job.
        self._status_thread = threading.Thread(
            target=self._status_monitor, daemon=True)
        self._status_thread.start()
        self._expect_status = None
        self.card_id = b''
        self.bed_x = -1.0
        self.bed_y = -1.0
        self.x = -1.0
        self.y = -1.0
        self.z = -1.0
        self.u = -1.0
        self._last_card_id = b''
        self._last_bed_x = -1.0
        self._last_bed_y = -1.0
        self._last_x = 0.0
        self._last_y = 0.0
        self._last_z = 0.0
        self._last_u = 0.0

    def start_sending(self):
        self._send_thread = threading.Thread(target=self._data_sender, daemon=True)
        self.events("Sending File...")
        self.divide_data_into_queue()
        self.events(f"File in {len(self._send_queue)} chunk(s)")
        self._send_thread.start()

    def divide_data_into_queue(self):
        last = 0
        total = 0
        data = self.job.buffer
        for i, command in enumerate(data):
            total += len(command)
            if total > 1000:
                self._send_queue.append(self.job.get_contents(last, i))
                last = i
                total = 0
        if last != len(data):
            self._send_queue.append(self.job.get_contents(last))

    @property
    def busy(self):
        return self._expect_status is not None

    def sync_coords(self):
        '''
        Sync native coordinates with device coordinates.

        This is typically used after actions such as physical home.'''
        while self.busy:
            time.sleep(self._status_thread_sleep)
        self.service.driver.native_x = self.service.driver.device_x
        self.service.driver.native_y = self.service.driver.device_y

    def _data_sender(self):
        '''Data send thread.

        This is a transient thread which is created after job data has been
        queued. This runs until the queue is empty at which point it
        terminates.'''
        self._job_lock.acquire()
        while self._send_queue:
            data = self._send_queue.pop(0)
            self.write(data)
        self._send_queue.clear()
        self._send_thread = None
        self.events("File Sent.")
        self._job_lock.release()

    def _status_monitor(self):
        '''Status monitoring thread.

        The thread runs continually to monitor connection status with a
        Ruida controller. It also updates the UI when status changes.

        NOTE: This thread is blocked while _data_sender is running.'''
        self._expect_status = None
        _next = 0
        try:
            while True:
                if self._expect_status is None:
                    self._job_lock.acquire() # Wait if running a job.
                    # Step through a series of commands and send/recv each one
                    # by one. When received, recv will update the UI.
                    _status = STATUS_ADDRESSES[_next]
                    self.job.get_setting(
                        _status, output=self.write)
                    self._expect_status = _status
                    _next += 1
                    if _next >= len(STATUS_ADDRESSES):
                        _next = 0
                    self._job_lock.release()
                time.sleep(self._status_thread_sleep)
        except OSError:
            pass

    def update_card_id(self, card_id):
        if self._expect_status == MEM_CARD_ID:
            self._expect_status = None
        if card_id != self.card_id:
            self.card_id = card_id
            # Signal the GUI update.

    def update_bed_x(self, bed_x):
        if self._expect_status == MEM_BED_SIZE_X:
            self._expect_status = None
        _bed_x = bed_x / 1000
        if _bed_x != self.bed_x:
            self.bed_x = _bed_x
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedwidth = f'{_bed_x:.1f}mm'
            self.service.signal('bedwidth', self.service.bedwidth)

    def update_bed_y(self, bed_y):
        if self._expect_status == MEM_BED_SIZE_Y:
            self._expect_status = None
        _bed_y = bed_y / 1000
        if _bed_y != self.bed_y:
            self.bed_y = _bed_y
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedheight = f'{_bed_y:.1f}mm'
            self.service.signal('bedheight', self.service.bedheight)

    def update_x(self, x):
        if self._expect_status == MEM_CURRENT_X:
            self._expect_status = None
        # TODO: Factor discovered by trial and error -- why necessary?
        # _x = x * 2.58
        _x = (self.bed_x * 1000 - x) * 2.58
        if True or _x != self.x:
            self.x = _x
            # Signal the GUI update.
            self.service.signal(
                "driver;position",
                (self._last_x, self._last_y, self.x, self.y))
            self._last_x = self.x
            # TODO: Updating native_x here causes intermittent move
            # behavior.
            self.service.driver.device_x = x

    def update_y(self, y):
        if self._expect_status == MEM_CURRENT_Y:
            self._expect_status = None
        # TODO: Factor discovered by trial and error -- why necessary?
        _y = y * 2.58
        if True or _y != self.y:
            self.y = _y
            # Signal the GUI update.
            self.service.signal(
                "driver;position",
                (self._last_x, self._last_y, self.x, self.y))
            self._last_y = self.y
            # TODO: Updating native_y here causes intermittent move
            # behavior.
            self.service.driver.device_y = y

    def update_z(self, z):
        if self._expect_status == MEM_CURRENT_Z:
            self._expect_status = None
        if z != self.z:
            self.z = z
            # Signal the GUI update.

    def update_u(self, u):
        if self._expect_status == MEM_CURRENT_U:
            self._expect_status = None
        if u != self.u:
            self.u = u
            # Signal the GUI update.

    _dispatch_lut = {
        MEM_CARD_ID: update_card_id,
        MEM_BED_SIZE_X: update_bed_x,
        MEM_BED_SIZE_Y: update_bed_y,
        MEM_CURRENT_X: update_x,
        MEM_CURRENT_Y: update_y,
        MEM_CURRENT_Z: update_z,
        MEM_CURRENT_U: update_u,
    }

    def recv(self, reply):
        '''Receive reply from the controller.

        The only reason this will be called is in response to a command
        which requires reply data from the controller. Forward to the
        RDJob for parsing.'''
        if reply is not None:
            _mem, _value, _decoded = self.job.decode_reply(reply)
            if _mem is not None:
                if _mem in self._dispatch_lut:
                    # Dispatch to the corresponding updater.
                    self._dispatch_lut[_mem](self, _value)
                self.events(
                    f"-->:Addr: {int.from_bytes(_mem):04X}={_value:08X}: {_decoded}")
                self._connected = True
        else:
            # Comm failure -- timeout.
            self._connected = False
            pass

    def start_record(self):
        self.job.get_setting(MEM_CARD_ID, output=self.write)
        self.job.clear()

    def stop_record(self):
        self.start_sending()

    @property
    def state(self):
        return "idle", "idle"

    def added(self):
        pass

    def service_detach(self):
        pass

    #######################
    # MODE SHIFTS
    #######################

    def rapid_mode(self):
        if self.mode == "rapid":
            return
        self.mode = "rapid"

    def raster_mode(self):
        self.program_mode()

    def program_mode(self):
        if self.mode == "rapid":
            return
        self.mode = "program"

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        pass

    #######################
    # Command Shortcuts
    #######################

    def wait_finished(self):
        pass

    def wait_ready(self):
        pass

    def wait_idle(self):
        pass

    def abort(self):
        self.mode = "rapid"
        self.job.stop_process(output=self.write)

    def pause(self):
        self.paused = True
        self.job.pause_process(output=self.write)

    def resume(self):
        self.paused = False
        self.job.restore_process(output=self.write)
