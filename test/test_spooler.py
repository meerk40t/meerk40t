import unittest
from test import bootstrap

from meerk40t.core.spoolers import SpoolerJob


class TestSpooler(unittest.TestCase):
    def test_spoolerjob(self):
        """
        Test spooler job

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel.device.spooler.send(SpoolerJob(kernel.device))
            kernel.device.spooler.clear_queue()
            j = SpoolerJob(kernel.device)
            kernel.device.spooler.send(j)
            kernel.device.spooler.remove(j)
        finally:
            kernel()
