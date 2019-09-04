from __future__ import print_function

import unittest
from LhymicroWriter import LhymicroWriter


class TestWriter(unittest.TestCase):

    def test_write_home(self):
        writer = LhymicroWriter(controller="")
        writer.home()
        self.assertEquals(writer.controller, "IPP\n")

    def test_write_square(self):
        writer = LhymicroWriter(controller="")
        writer.move(100,0)
        writer.move(0, 100)
        writer.move(-100, 0)
        writer.move(0, -100)
        self.assertEquals(writer.controller, "IB100S1P\nIR100S1P\nIT100S1P\nIL100S1P\n")

    def test_write_lock_rail(self):
        writer = LhymicroWriter(controller="")
        writer.lock_rail()
        self.assertEquals(writer.controller, "IS1P\n")

    def test_write_compact_mode_M2(self):
        writer = LhymicroWriter(board="M2", controller="")
        writer.speed = 10
        writer.to_compact_mode()
        writer.move(100, 0)
        writer.move(0, 100)
        writer.move(-100, 0)
        writer.move(0, -100)
        writer.to_default_mode()
        self.assertEquals(writer.controller, "ICV1151911011002218NRBS1EB100R100T100L100FNSE-\n")

    def test_write_compact_mode_B2(self):
        writer = LhymicroWriter(board="B2", controller="")
        writer.speed = 10
        writer.to_compact_mode()
        writer.move(100, 0)
        writer.move(0, 100)
        writer.move(-100, 0)
        writer.move(0, -100)
        writer.to_default_mode()
        self.assertEquals(writer.controller, "ICV0121101011005181NRBS1EB100R100T100L100FNSE-\n")
