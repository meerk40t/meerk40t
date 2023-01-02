import unittest
from test import bootstrap


class TestKernel(unittest.TestCase):
    def test_kernel_commands(self):
        """
        Tests all commands with no arguments to test for crashes...
        """
        kernel = bootstrap.bootstrap()
        try:
            for cmd, path, command in kernel.find("command/.*"):
                if "server" in command:
                    continue
                if "ruida" in command:
                    continue
                if "grbl" in command:
                    continue
                if "quit" in command:
                    continue
                if "shutdown" in command:
                    continue
                if "interrupt" in command:
                    continue
                if not cmd.regex:
                    print(f"Testing command: {command}")
                    # command should be generated with something like
                    # kernel.console(" ".join(command.split("/")[1:]) + "\n")
                    # if first parameter is not base but this fails so not
                    # changing yet
                    kernel.console(command.split("/")[-1] + "\n")
        finally:
            kernel.shutdown()


class TestGetSafePath(unittest.TestCase):
    def test_get_safe_path(self):
        import os

        from meerk40t.kernel import get_safe_path

        """
        Tests the get_safe_path method for all o/ses
        """
        sep = os.sep
        self.assertEqual(
            str(get_safe_path("test", system="Darwin")),
            (
                os.path.expanduser("~")
                + sep
                + "Library"
                + sep
                + "Application Support"
                + sep
                + "test"
            ),
        )
        self.assertEqual(
            str(get_safe_path("test", system="Windows")),
            (os.path.expandvars("%LOCALAPPDATA%") + sep + "test"),
        )
        self.assertEqual(
            str(get_safe_path("test", system="Linux")),
            (os.path.expanduser("~") + sep + ".config" + sep + "test"),
        )


class TestEchoCommand(unittest.TestCase):
    def test_echo_and_ansi(self):
        """
        Tests all echo options separately and combined
        with output to ansi terminal window
        """
        echo_commands = [
            "echo",
            "echo [bg-white][black] black text",
            "echo [red] red text",
            "echo [green] green text",
            "echo [yellow] yellow text",
            "echo [blue] blue text",
            "echo [magenta] magenta text",
            "echo [cyan] cyan text",
            "echo [bg-black][white] white text",
            "echo [bg-black][white] black background",
            "echo [bg-red] red background",
            "echo [bg-green] green background",
            "echo [bg-yellow] yellow background",
            "echo [bg-blue] blue background",
            "echo [bg-magenta] magenta background",
            "echo [bg-cyan] cyan background",
            "echo [bg-white][black] white background",
            "echo [bg-white][black] bright black text",
            "echo [bold][red] bright red text",
            "echo [bold][green] bright green text",
            "echo [bold][yellow] bright yellow text",
            "echo [bold][blue] bright blue text",
            "echo [bold][magenta] bright magenta text",
            "echo [bold][cyan] bright cyan text",
            "echo [bold][bg-black][white] bright white text",
            "echo [bold] bold text [/bold] normal text",
            "echo [italic] italic text [/italic] normal text",
            "echo [underline] underline text [/underline] normal text",
            "echo [underscore] underscore text [/underscore] normal text",
            "echo [negative] negative text [positive] positive text",
            "echo [negative] negative text [normal] normal text",
            "echo [raw][red] red bbcode and normal text",
        ]

        kernel = bootstrap.bootstrap()
        try:
            for echo in echo_commands:
                print(f"Testing echo command: {echo}")
                kernel.console(echo + "\n")
        finally:
            kernel.shutdown()
