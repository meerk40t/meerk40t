
import unittest

from test import bootstrap


class TestKernel(unittest.TestCase):
    def test_kernel_commands(self):
        """
        Tests all commands with no arguments to test for crashes.

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            for cmd, command, sname in kernel.find("command/.*"):
                if "server" in command:
                    continue
                if sname in ("shutdown", "quit"):
                    continue
                if not cmd.regex:
                    kernel.console(sname + "\n")
        finally:
            kernel.shutdown()
