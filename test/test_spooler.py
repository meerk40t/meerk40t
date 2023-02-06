import unittest
from test import bootstrap


class TestJob:
    def __init__(
        self,
        service,
    ):
        self.stopped = False
        self.service = service
        self.runtime = 0
        self.priority = 0

    @property
    def status(self):
        if self.is_running:
            return "Running"
        else:
            return "Queued"

    def is_running(self):
        return not self.stopped

    def execute(self, driver):
        driver.home()
        return True

    def stop(self):
        self.stopped = True

    def elapsed_time(self):
        """
        How long is this job already running...
        """
        result = 0
        return result

    def estimate_time(self):
        return 0


class TestSpooler(unittest.TestCase):
    def test_spoolerjob(self):
        """
        Test spooler job

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel.device.spooler.send(TestJob(kernel.device))
            kernel.device.spooler.clear_queue()
            j = TestJob(kernel.device)
            kernel.device.spooler.send(j)
            kernel.device.spooler.remove(j)
        finally:
            kernel.shutdown()
