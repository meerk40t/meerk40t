import unittest
from test import bootstrap

class TestKernel(unittest.TestCase):
    def test_kernel_commands(self):
        """
        Tests all commands with no arguments to test for crashes...
        """
        kernel = bootstrap.bootstrap()
        try:
            for command in kernel.match("command/.*"):
                cmd = kernel.registered[command]
                if "server" in command:
                    continue
                if "ruida" in command:
                    continue
                if command in ("quit", "shutdown", "loop"):
                    continue
                if not cmd.regex:
                    print("Testing command: %s" % command)
                    kernel.console(command.split("/")[-1] + "\n")
        finally:
            kernel.shutdown()

class TestGetSafePath(unittest.TestCase):
    def test_get_safe_path(self):
        from meerk40t.kernel import get_safe_path
        import os
        """
        Tests the get_safe_path method for all o/ses
        """
        sep = os.sep
        self.assertEquals(
            str(get_safe_path("test", system="Darwin")),
            (
                os.path.expanduser("~")
                + sep + "Library" + sep + "Application Support" + sep + "test"
            )
        )
        self.assertEquals(
            str(get_safe_path("test", system="Windows")),
            (
                os.path.expandvars("%LOCALAPPDATA%")
                + sep + "test"
            )
        )
        self.assertEquals(
            str(get_safe_path("test", system="Linux")),
            (
                os.path.expanduser("~")
                + sep + ".config" + sep + "test"
            )
        )

