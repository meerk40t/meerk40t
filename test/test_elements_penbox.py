import unittest
from test import bootstrap


class TestPenbox(unittest.TestCase):
    def test_penbox(self):
        """
        Test penbox code

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            kernel_root = kernel.get_context("/")
            kernel_root("penbox testpasses add 5 set 0-4 hatch_angle 0-90\n")
            self.assertEqual(len(kernel_root.penbox.pens["testpasses"]), 5)
            self.assertEqual(
                kernel_root.elements.penbox.pens["testpasses"][-1]["hatch_angle"], 90
            )

        finally:
            kernel.shutdown()
