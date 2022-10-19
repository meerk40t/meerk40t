import sys
import unittest

state = 0


class TestCommandLineInterface(unittest.TestCase):
    def test_cli(self):
        from meerk40t import main
        sys.argv = "meerk40t -Zpe quit".split(" ")
        main.run()
