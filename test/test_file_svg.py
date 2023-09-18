import os
import unittest
from test import bootstrap

class TestFileSVG(unittest.TestCase):
    def test_load_save_svg(self):
        """
        test svg saving and loading of various files.
        """
        file1 = "test.svg"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("operation* remove\n")
            kernel.console("hatch\n")
            kernel.console(f"rect 2cm 2cm 1cm 1cm engrave -s 15\n")
            kernel.console(f"save {file1}\n")
            kernel.console("element* delete\n")
            kernel.console("operation* remove\n")
            kernel.console(f"load {file1}\n")
            f = list(kernel.elements.elem_branch.flat(types="elem rect"))[0]
            print(f)
        finally:
            kernel.shutdown()

