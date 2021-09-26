
import unittest

from test import bootstrap


class TestKernel(unittest.TestCase):
    def test_kernel_commands(self):
        """
        Tests all commands with no arguments to test for crashes.

        :return:
        """
        kernel = bootstrap.bootstrap()

        for command in kernel.match("command/.*"):
            cmd = kernel.registered[command]
            if not cmd.regex:
                cmd = command.split("/")[-1]
                # The following condition has been added to allow tests to complete
                # rather than hang the tests due to infinite loop or wait for external event or crash
                if cmd not in ["grblserver", "trace_hull", "trace_quick"]:
                    print(cmd)
                    kernel.console(cmd + "\n")
