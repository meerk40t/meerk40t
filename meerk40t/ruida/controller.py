"""
Ruida Encoder

The Ruida Encoder is responsible for turning function calls into binary ruida data.
"""
import threading

from meerk40t.ruida.rdjob import ACK, MEM_CARD_ID, RDJob


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
        self._send_lock = threading.Condition()
        self._send_thread = None
        self.events = service.channel(f"{service.safe_label}/events")

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

    def _data_sender(self):
        while self._send_queue:
            data = self._send_queue.pop(0)
            self.write(data)
            with self._send_lock:
                if not self._send_lock.wait(5):
                    self.service.signal("warning", "Connection Problem.", "Timeout")
                    return
        self._send_queue.clear()
        self._send_thread = None
        self.events("File Sent.")

    def recv(self, reply):
        e = self.job.unswizzle(reply)
        if e == ACK:
            with self._send_lock:
                self._send_lock.notify()
        self.events(f"-->: {e}")

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
