"""
Ruida Controller

The Ruida Controller occupies the Presentation Layer (Layer 6) and the
Application Layer (Layer 7) of the OSI model.
"""
import threading
import time

from meerk40t.core.units import UNITS_PER_uM, Length

from meerk40t.ruida.rdjob import (
    MEM_CARD_ID,
    MEM_MACHINE_STATUS,
    MACHINE_STATUS_MOVING,
    MACHINE_STATUS_PART_END,
    MACHINE_STATUS_JOB_RUNNING,
    MACHINE_STATUS_TO_LABEL_LUT,
    MEM_BED_SIZE_X,
    MEM_BED_SIZE_Y,
    MEM_CURRENT_X,
    MEM_CURRENT_Y,
    MEM_CURRENT_Z,
    MEM_CURRENT_U,
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
        self.events = service.channel(f"{service.safe_label}/events")

        self.job = RDJob()
        self._send_queue = []
        self._send_thread = None
        self._status_thread_sleep = 0.2 # Time between polls.
        self._status_gross_to = 40 # seconds
        self._status_normal_to = 1 # seconds
        self._connected = False
        self._job_lock = threading.Lock() # To allow running a job.
        self._job_lock.acquire() # Hold threads until told to start.
        self._status_thread = threading.Thread(
            target=self._status_monitor, daemon=True)
        self._status_thread.start()
        self._waiting = False
        self._idle = True
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
        self._x_read = False
        self._y_read = False
        self._last_bed_x = -1.0
        self._last_bed_y = -1.0
        self._last_x = 0.0
        self._last_y = 0.0
        self._last_z = 0.0
        self._last_u = 0.0
        self.show_cursor = self.service.setting(bool, "signal_updates", True)

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

    def resume_monitor(self):
        '''Start the background machine status monitor.'''
        self._job_lock.release()

    def pause_monitor(self):
        '''Stop the background machine status monitor.'''
        self._job_lock.acquire()

    @property
    def is_busy(self):
        return self._waiting or self.service.is_busy

    def gross_timeout(self):
        '''Set a gross comms timeout. This is typically used in situations
        where the Ruida controller is expected to stop communicating for
        extended periods of time, such as when doing a physical home, but is
        still OK.'''
        self.service.set_timeout(self._status_gross_to)

    def normal_timeout(self):
        '''Set a normal comms timeout.'''
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
        if self.job.low_power_warning:
            self.events(f'WARNING: Power less than 10% may not fire CO2.')
        if self.job.high_power_warning:
            self.events(f'WARNING: Power greater than 70% reduces CO2 life.')

    # This table defines the sequence in which specific mem reads occur. It also
    # controls the number of times the same request repeats relative to
    # other requests. The intent is to be able the tune the responsiveness of
    # things like head location updates.
    STATUS_ADDRESSES = (
        MEM_MACHINE_STATUS,
        MEM_BED_SIZE_X,
        MEM_BED_SIZE_Y,
        MEM_CURRENT_X,
        MEM_CURRENT_Y,
        MEM_MACHINE_STATUS,
        MEM_CURRENT_X,
        MEM_CURRENT_Y,
        MEM_MACHINE_STATUS,
        MEM_CURRENT_X,
        MEM_CURRENT_Y,
        MEM_MACHINE_STATUS,
        MEM_CURRENT_X,
        MEM_CURRENT_Y,
        MEM_CARD_ID,
    #    MEM_CURRENT_Z,
    #    MEM_CURRENT_U,
        )

    def _status_monitor(self):
        '''Status monitoring thread.

        The thread runs continually to monitor machine status with a
        Ruida controller. It also updates the UI when status changes.

        NOTE: This thread is blocked while _data_sender is running.'''
        time.sleep(3) # Wait for controller window to init. Need a semaphore.
        while True:
            # if not self.is_busy and not self.service.is_busy:
            if self.service.connected and not self.service.is_busy:
                self._job_lock.acquire() # Wait if sending a job.
                self._waiting = True
                # Step through a series of commands and send/recv each one
                # by one. When received, recv will update the UI.
                _status = self.STATUS_ADDRESSES[self._next]
                try:
                    self.job.get_setting(
                        _status, output=self.write)
                except OSError:
                    pass
                self._job_lock.release()
                self._next += 1
                if self._next >= len(self.STATUS_ADDRESSES):
                    self._next = 0
            else:
                self._waiting = True
                self.service.connect()
                self.card_id = ''
            time.sleep(self._status_thread_sleep)

    def update_card_id(self, card_id):
        if card_id != self.card_id:
            self.card_id = card_id
            # Signal the GUI update.
            _msg = f'Card ID:{card_id}'
            self.service.signal('pipe;usb_status', _msg)
            _msg += f'\nBed width: {self.service.bedwidth}'
            _msg += f' Bed height: {self.service.bedheight}'
            self.events(_msg)

    def update_machine_status(self, status):
        if status != self.machine_status:
            self.machine_status = status
            # WARNING: These strings are checked by the Ruida Controller
            # window (ruidacontroller.py).
            # TODO: Having dependencies on text strings is risky. A single
            # definition is needed.
            if status & MACHINE_STATUS_MOVING:
                _msg = MACHINE_STATUS_TO_LABEL_LUT[MACHINE_STATUS_MOVING]
                self._idle = False
            elif status & MACHINE_STATUS_PART_END:
                _msg = MACHINE_STATUS_TO_LABEL_LUT[MACHINE_STATUS_PART_END]
                self._idle = False
            elif status & MACHINE_STATUS_JOB_RUNNING:
                _msg = MACHINE_STATUS_TO_LABEL_LUT[MACHINE_STATUS_JOB_RUNNING]
                self._idle = False
            else:
                _msg = 'Idle'
                self._idle = True
            # Signal the GUI update.
            self.events(_msg)
            self.service.signal('pipe;usb_status', _msg)

    def update_bed_x(self, bed_x):
        _bed_x = bed_x / 1000
        if _bed_x != self.bed_x:
            self.bed_x = _bed_x
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedwidth = Length(f'{_bed_x:.1f}mm')
            self.service.signal('bedwidth', self.service.bedwidth)

    def update_bed_y(self, bed_y):
        _bed_y = bed_y / 1000
        if _bed_y != self.bed_y:
            self.bed_y = _bed_y
            # Signal the GUI update.
            # TODO: The GUI should define the format and presentation units.
            self.service.bedheight = Length(f'{_bed_y:.1f}mm')
            self.service.signal('bedheight', self.service.bedheight)

    def _update_position(self):
        if self._x_read and self._y_read:
            # Signal the GUI update - convert to system units.
            _last_x = Length(f'{self._last_x}mm').units
            _last_y = Length(f'{self._last_y}mm').units
            _x = Length(f'{self.x}mm').units
            _y = Length(f'{self.y}mm').units

            if self.show_cursor:
                self.service.signal("driver;position", (_last_x, _last_y, _x, _y))
            self._x_read = False
            self._y_read = False
            self._last_x = self.x
            self._last_y = self.y

    def update_x(self, x):
        # The (x - 50) adjusts for a rounding error on the Ruida display.
        _x = round(self.bed_x - (x - 50) / 1000, 1)
        self._x_read = True
        if _x != self.x or self._y_read:
            # Only X and then Y are updated. This avoids stair-stepping.
            self._y_read = False
            self.x = _x
            self._update_position()
            self.service.driver.native_x = x

    def update_y(self, y):
        # The (y - 50) adjusts for a rounding error on the Ruida display.
        _y = round((y + 50) / 1000, 1)
        self._y_read = True
        if _y != self.y or self._x_read:
            self.y = _y
            self._update_position()
            self.service.driver.native_y = y

    def update_z(self, z):
        _z = round(z * UNITS_PER_uM, 1)
        if _z != self.z:
            self.z = _z
            # Signal the GUI update.

    def update_u(self, u):
        _u = round(u * UNITS_PER_uM, 1)
        if _u != self.u:
            self.u = _u
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
                self._waiting = False
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

    def wait_for_move(self, x, y):
        '''Wait until a move completes and the head is at the desired position.

        Because of rounding errors for coordinates reported by the machine
        the position is rounded to the nearest mm.

        The status monitor is paused until the move completes.
        '''
        _exp_x = round(x / 1000)
        _exp_y = round(y / 1000)
        _tries = 10 / 0.2 # wait for 10 seconds max.
        self._job_lock.acquire()
        while _tries > 0:
            _tries -= 1
            if (round(self.service.driver.native_x / 1000) == _exp_x
                and round(self.service.driver.native_y / 1000) == _exp_y):
                break
            for _status in [MEM_MACHINE_STATUS, MEM_CURRENT_X, MEM_CURRENT_Y]:
                self.job.get_setting(
                    _status, output=self.write)
            time.sleep(0.2)
        self._job_lock.release()


        pass

    def wait_ready(self):
        pass

    def wait_idle(self):
        while not self._idle and self.service.connected:
            time.sleep(0.025)
        self.x = -1
        self.y = -1

    def sync(self):
        '''Resync the status monitor.'''
        self.wait_idle()
        self.service.active_session.close() # Reconnects automatically.

    def abort(self):
        self.mode = "rapid"
        self.job.stop_process(output=self.write)

    def pause(self):
        self.paused = True
        self.job.pause_process(output=self.write)

    def resume(self):
        self.paused = False
        self.job.restore_process(output=self.write)
