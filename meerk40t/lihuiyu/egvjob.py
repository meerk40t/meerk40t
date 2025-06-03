"""
Minimal handler for EGV jobs.
This handler is used to process EGV files, which are specific to Lihuiyu laser systems. 
"""

import time
import threading

class EGVJob:
    def __init__(
        self, driver=None, units_to_device_matrix=None, priority=0, channel=None
    ):
        self.units_to_device_matrix = units_to_device_matrix
        self._driver = driver
        self.channel = channel
        self.reply = None
        self.buffer = list()
        self.label = "EGV Job"
        self.priority = priority

        self.time_submitted = time.time()
        self.time_started = None
        self.runtime = 0

        self._stopped = True
        self.enabled = True
        self._estimate = 0

        self.lock = threading.Lock()


    @property
    def status(self):
        if self.is_running():
            if self.time_started:
                return "Running"
            else:
                return "Queued"
        else:
            if self.enabled:
                return "Waiting"
            else:
                return "Disabled"

    def execute(self, driver=None):
        """
        Execute calls each item in the list of items in order. This is intended to be called by the spooler thread. And
        hold the spooler while these items are executing.
        @return:
        """
        self._stopped = False
        if self.time_started is None:
            self.time_started = time.time()
        try:
            with self.lock:
                blob = self.buffer.pop(0)
                self._driver.blob("egv", blob)
                self._estimate = len(blob) / 1000.0  # Estimate time based on blob size, adjust as needed.
        except IndexError:
            # Could not pop, list is empty. Job is done.
            pass
        if not self.buffer:
            # Buffer is empty now. Job is complete
            self.runtime += time.time() - self.time_started
            self._stopped = True
            return True  # All steps were executed.
        return False

    def stop(self):
        """
        Stop this current laser-job, cannot be called from the spooler thread.
        @return:
        """
        if not self._stopped:
            self.runtime += time.time() - self.time_started
        self._stopped = True

    def is_running(self):
        return not self._stopped

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        if self.is_running():
            return time.time() - self.time_started
        else:
            return self.runtime

    def estimate_time(self):
        """
        Give laser job time estimate.
        @return:
        """
        return self._estimate
    
    def write(self, data):
        """
        Write data to the buffer.
        @param data: Data to write to the buffer.
        """
        with self.lock:
            self.buffer.append(data)
    
    def write_blob(self, blob):
        """
        Write a blob to the buffer.
        @param blob: Blob to write to the buffer.
        """
        with self.lock:
            self.buffer.append(blob)    
