import unittest

from test import bootstrap


class TestKernel(unittest.TestCase):
    def test_kernel_commands(self):
        """
        Tests all commands with no arguments to test for crashes...

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            for cmd, path, command in kernel.find("command/.*"):
                if "server" in command:
                    continue
                if "ruida" in command:
                    continue
                if command in ("quit", "shutdown", "loop"):
                    continue
                if not cmd.regex:
                    print("Testing command: %s" % path)
                    kernel.console(command + "\n")
        finally:
            kernel.shutdown()
