import threading
import time

from meerk40t.balor.sender import Sender, SET_XY_POSITION, STOP_LIST, RESTART_LIST, BalorMachineException, \
    BalorCommunicationException
from meerk40t.kernel import STATE_UNKNOWN, STATE_INITIALIZE, STATE_END, STATE_TERMINATE, STATE_ACTIVE, STATE_PAUSE, \
    STATE_BUSY, STATE_SUSPEND, STATE_IDLE


class BalorController:
    """
    Balor controller is tasked with sending queued data to the controller board and ensuring that the connection to the
    controller board is established to perform these actions. The model is based on the typical driver for the lihuiyu
    board. Modified to match Balor's specifications
    """
    def __init__(self, service):
        self.service = service
        self.state = STATE_UNKNOWN
        self.is_shutdown = False  # Shutdown finished.

        self._thread = None

        self._queue = list()
        self._preempt = list()
        self._queue_lock = threading.Lock()
        self._preempt_lock = threading.Lock()
        self._main_lock = threading.Lock()  # Primary lock for data send thread

        self.channel = self.service.channel("balor")
        self.connection = Sender(service, debug=self.channel)

        self.max_attempts = 5
        self.refuse_counts = 0
        self.connection_errors = 0
        self.count = 0
        self.aborted_retries = False
        self.realtime = False

        name = self.service.label
        self.pipe_channel = service.channel("%s/events" % name)
        self.usb_log = service.channel("%s/usb" % name, buffer_size=500)
        self.usb_send_channel = service.channel("%s/usb_send" % name)
        self.recv_channel = service.channel("%s/recv" % name)
        self.usb_log.watch(lambda e: service.signal("pipe;usb_status", e))

    def viewbuffer(self):
        return str(self._queue)

    def added(self):
        pass

    def service_detach(self):
        pass

    def shutdown(self, *args, **kwargs):
        if self._thread is not None:
            self.is_shutdown = True

    def write(self, job):
        """
        Writes data to the queue, this will be moved into the buffer by the thread in a threadsafe manner.

        @param job: data to write to the queue.
        @return:
        """
        self.pipe_channel("write(%s)" % str(job))
        self._queue_lock.acquire(True)
        self._queue.append(job)
        self._queue_lock.release()
        self.start()

    def realtime_write(self, job):
        """
        Writes data to the preempting commands, this will be moved to the front of the buffer by the thread
        in a threadsafe manner.

        @param job: data to write to the front of the queue.
        @return:
        """
        self.pipe_channel("realtime_write(%s)" % str(job))
        self._preempt_lock.acquire(True)
        self._preempt.append(job)
        self._preempt_lock.release()
        self.start()

    def job(self, job):
        self.write(("execute", (job,)))

    def port_on(self, bit):
        self.write(("port_on", (bit,)))

    def port_off(self, bit):
        self.write(("port_off", (bit,)))

    def light_on(self):
        self.port_on(8)

    def light_off(self):
        self.port_off(8)

    def set_xy(self, x, y):
        self.write(("command", (SET_XY_POSITION, int(x), int(y))))

    def realtime_pause(self):
        self.realtime_write(("command", (STOP_LIST,)))

    def realtime_resume(self):
        self.realtime_write(("command", (RESTART_LIST,)))

    def get_list_status(self):
        # Requires realtime response.
        if self.state == STATE_ACTIVE:
            return self.connection.raw_get_list_status()

    def get_serial_number(self):
        # Requires realtime response.
        if self.state == STATE_ACTIVE:
            return self.connection.raw_get_serial_no()

    def get_status(self):
        # Requires realtime response.
        if self.state == STATE_ACTIVE:
            return self.connection.read_port()

    def get_port(self):
        if self.connection is not None:
            return self.connection.get_port()

    def wait_finished(self):
        while len(self._queue) or len(self._preempt):
            time.sleep(0.01)
            if self.connection._terminate_execution:
                self._queue.clear()
                self._preempt.clear()
                return
        self.write(("wait_finished", tuple()))

    def start(self):
        """
        Controller state change to `Started`.
        @return:
        """

        if not self.is_shutdown and (
            self._thread is None or not self._thread.is_alive()
        ):
            self._thread = self.service.threaded(
                self._thread_data_send,
                thread_name=f"BalorPipe({self.service.path})",
                result=self.stop,
            )
            self._thread.stop = self.stop
            self.update_state(STATE_INITIALIZE)

    def pause(self):
        """
        Pause simply holds the controller from sending any additional packets.

        If this state change is done from INITIALIZE it will start the processing.
        Otherwise, it must be done from ACTIVE or IDLE.
        """
        if self.state == STATE_INITIALIZE:
            self.start()
            self.update_state(STATE_PAUSE)
        if self.state == STATE_ACTIVE or self.state == STATE_IDLE:
            self.update_state(STATE_PAUSE)

    def resume(self):
        """
        Resume can only be called from PAUSE.
        """
        if self.state == STATE_PAUSE:
            self.update_state(STATE_ACTIVE)

    def abort(self):
        self._queue = list()
        self._preempt = list()
        self.realtime_write(("abort", tuple()))

    def stop(self, *args):
        self.abort()
        try:
            if self._thread is not None:
                self._thread.join()  # Wait until stop completes before continuing.
            self._thread = None
        except RuntimeError:
            pass  # Stop called by current thread.

    def abort_retry(self):
        self.aborted_retries = True
        self.service.signal("pipe;state", "STATE_FAILED_SUSPENDED")

    def continue_retry(self):
        self.aborted_retries = False
        self.service.signal("pipe;state", "STATE_FAILED_RETRYING")

    def _thread_data_send(self):
        """
        Main threaded function to send data. While the controller is working the thread
        will be doing work in this function.
        """
        self._main_lock.acquire(True)
        self.count = 0
        self.is_shutdown = False
        while self.state != STATE_END and self.state != STATE_TERMINATE:
            if self.state == STATE_INITIALIZE:
                # If we are initialized. Change that to active since we're running.
                self.update_state(STATE_ACTIVE)
            if self.state in (STATE_PAUSE, STATE_BUSY, STATE_SUSPEND):
                # If we are paused just keep sleeping until the state changes.
                if len(self._preempt) == 0:
                    # Only pause if there are no realtime commands to queue.
                    self.service.signal("pipe;running", False)
                    time.sleep(0.25)
                    continue
            if self.aborted_retries:
                self.service.signal("pipe;running", False)
                time.sleep(0.25)
                continue
            try:
                # We try to process the queue.
                queue_processed = self.process_queue()
                if self.refuse_counts:
                    self.service.signal("pipe;failing", 0)
                self.refuse_counts = 0
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
            except BalorMachineException:
                # The attempt refused the connection.
                self.refuse_counts += 1
                if self.refuse_counts >= 5:
                    self.service.signal("pipe;state", "STATE_FAILED_RETRYING")
                self.service.signal("pipe;failing", self.refuse_counts)
                self.service.signal("pipe;running", False)
                if self.is_shutdown:
                    break  # Sometimes it could reset this and escape.
                time.sleep(3)  # 3-second sleep on failed connection attempt.
                continue
            except BalorCommunicationException:
                # There was an error with the connection, close it and try again.
                self.connection_errors += 1
                self.service.signal("pipe;running", False)
                time.sleep(0.5)
                self.pipe_channel("close()")
                self.connection.close()
                self.service.signal("pipe;usb_status", "Disconnected")
                continue
            if queue_processed:
                # Packet was sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_ACTIVE,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_ACTIVE)
                self.count = 0
            else:
                # No packet could be sent.
                if self.state not in (
                    STATE_PAUSE,
                    STATE_BUSY,
                    STATE_TERMINATE,
                ):
                    self.update_state(STATE_IDLE)
                if self.count > 50:
                    self.count = 50
                time.sleep(0.02 * self.count)
                # will tick up to 1 second waits if there's never a queue.
                self.count += 1
            self.service.signal("pipe;running", queue_processed)
        self._thread = None
        self.update_state(STATE_END)
        self.service.signal("pipe;running", False)
        self._main_lock.release()

    def update_state(self, state):
        if state == self.state:
            return
        self.state = state
        if self.service is not None:
            self.service.signal("pipe;thread", self.state)

    def process_queue(self):
        if not self.connection.is_open():
            self.pipe_channel("open()")
            self.connection.open()
            if self.service.redlight_preferred:
                self.light_on()
            else:
                self.light_off()
        packet = None
        if len(self._preempt):  # check for and prepend preempt
            self._preempt_lock.acquire(True)
            packet = self._preempt.pop(0)
            self._preempt_lock.release()
        if packet is not None:
            method_str, args = packet
            method = getattr(self.connection, method_str)
            method(*args)
            return True

        if len(self._queue):  # check for and append queue
            self._queue_lock.acquire(True)
            packet = self._queue.pop(0)
            self._queue_lock.release()
        if packet is not None:
            method_str, args = packet
            method = getattr(self.connection, method_str)
            method(*args)
            return True
        return False
