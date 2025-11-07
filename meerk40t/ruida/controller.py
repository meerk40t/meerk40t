"""
Ruida Encoder

The Ruida Encoder is responsible for turning function calls into binary ruida data.
"""
import threading
import time

from meerk40t.ruida.rdjob import (
    MEM_CARD_ID,
    MEM_MACHINE_STATUS,
    MACHINE_STATUS_MOVING,
    MACHINE_STATUS_PART_END,
    MACHINE_STATUS_JOB_RUNNING,
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
        self._status_gross_to = 40 # seconds
        self._status_normal_to = 1 # seconds
        self._status_tries = self._status_normal_to / self._status_thread_sleep
        self._connected = False
        self._job_lock = threading.Lock() # To allow running a job.
        self._status_thread = threading.Thread(
            target=self._status_monitor, daemon=True)
        self._expected_status = None
        self._next = 0
        self._start = False
        self.card_id = b''
        self.machine_status = None
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

    def start(self):
        '''Start the background threads.'''
        self._status_thread.start()

    @property
    def is_busy(self):
        return self._expected_status is not None

    def sync_coords(self):
        '''
        Sync native coordinates with device coordinates.

        This is typically used after actions such as physical home.'''
        while self.is_busy:
            time.sleep(self._status_thread_sleep)
        self.service.driver.native_x = self.service.driver.device_x
        self.service.driver.native_y = self.service.driver.device_y

    def gross_timeout(self):
        '''Set a gross comms timeout. This is typically used in situations
        where the Ruida controller is expected to stop communicating for
        extended periods of time but is still OK.'''
        self._status_tries = self._status_gross_to / self._status_thread_sleep
        self.service.set_timeout(self._status_gross_to)

    def normal_timeout(self):
        '''Set a gross comms timeout. This is typically used in situations
        where the Ruida controller is expected to stop communicating for
        extended periods of time but is still OK.'''
        self._status_tries = self._status_normal_to / self._status_thread_sleep
        self.service.set_timeout(self._status_normal_to)

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

    def _next_status(self):
        '''The expected status has been received. Advance to the next.
        '''
        self._next += 1
        if self._next >= len(STATUS_ADDRESSES):
            self._next = 0
        self._expected_status = None

    def _status_monitor(self):
        '''Status monitoring thread.

        The thread runs continually to monitor connection status with a
        Ruida controller. It also updates the UI when status changes.

        NOTE: This thread is blocked while _data_sender is running.'''
        _tries = 0
        time.sleep(3) # Wait for controller window to init.
        self.service.connect()
        try:
            while True:
                # if not self.is_busy and not self.service.is_busy:
                if self.service.connected:
                    if not self.service.is_busy:
                        self._job_lock.acquire() # Wait if running a job.
                        # Step through a series of commands and send/recv each one
                        # by one. When received, recv will update the UI.
                        _status = STATUS_ADDRESSES[self._next]
                        self.job.get_setting(
                            _status, output=self.write)
                        self._expected_status = _status
                        self._job_lock.release()
                        _tries = 0
                    else:
                        _tries += 1
                        if _tries > self._status_tries:
                            if self._expected_status is not None:
                                self.job.get_setting(
                                    self._expected_status, output=self.write)
                            _tries = 0
                            # self._expected_status = None
                else:
                    self.card_id = ''
                time.sleep(self._status_thread_sleep)
        except OSError:
            pass

    def update_card_id(self, card_id):
        if card_id != self.card_id:
            self.card_id = card_id
            # Signal the GUI update.
            _msg = f'Card ID:{card_id}'
            self.service.signal('pipe;usb_status', _msg)
            self.events(_msg)

    def update_machine_status(self, status):
        if status != self.machine_status:
            self.machine_status = status
            # WARNING: These strings are checked by the Ruida Controller
            # window (ruidacontroller.py).
            # TODO: Having dependencies on text strings is risky. A single
            # definition is needed.
            if status & MACHINE_STATUS_MOVING:
                _msg = 'Moving'
            elif status & MACHINE_STATUS_PART_END:
                _msg = 'Part end'
            elif status & MACHINE_STATUS_JOB_RUNNING:
                _msg = 'Job running'
            else:
                _msg = 'Idle'
            # Signal the GUI update.
            self.events(_msg)
            self.service.signal('pipe;usb_status', _msg)

    def update_bed_x(self, bed_x):
        _bed_x = bed_x / 1000
        if _bed_x != self.bed_x:
            self.bed_x = _bed_x
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedwidth = f'{_bed_x:.1f}mm'
            self.service.signal('bedwidth', self.service.bedwidth)

    def update_bed_y(self, bed_y):
        _bed_y = bed_y / 1000
        if _bed_y != self.bed_y:
            self.bed_y = _bed_y
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedheight = f'{_bed_y:.1f}mm'
            self.service.signal('bedheight', self.service.bedheight)

    # TODO: Factor discovered by trial and error -- why necessary?
    # The precise value was discovered in a project file.
    COORD_SCALE_FACTOR = 2.5801195035

    def update_x(self, x):
        _x = (self.bed_x * 1000 - x) * self.COORD_SCALE_FACTOR
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
            self.service.driver.native_x = x

    def update_y(self, y):
        _y = y * self.COORD_SCALE_FACTOR
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
            self.service.driver.native_y = y

    def update_z(self, z):
        if z != self.z:
            self.z = z
            # Signal the GUI update.

    def update_u(self, u):
        if u != self.u:
            self.u = u
            # Signal the GUI update.

    _dispatch_lut = {
        MEM_CARD_ID: update_card_id,
        MEM_MACHINE_STATUS: update_machine_status,
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
                self._connected = True
                if _mem == self._expected_status:
                    self._next_status()
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
