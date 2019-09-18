from __future__ import print_function

import unittest
from LhymicroWriter import LhymicroWriter
from LaserProject import LaserProject


class TestWriter(unittest.TestCase):

    def test_write_home(self):
        writer = LhymicroWriter(LaserProject(), controller=b'')
        writer.home()
        self.assertEqual(writer.controller, b"IPP\n")

    def test_write_square(self):
        writer = LhymicroWriter(LaserProject(), controller=b'')
        writer.move_relative(100, 0)
        writer.move_relative(0, 100)
        writer.move_relative(-100, 0)
        writer.move_relative(0, -100)
        self.assertEqual(writer.controller, b"IB100S1P\nIR100S1P\nIT100S1P\nIL100S1P\n")

    def test_write_lock_rail(self):
        writer = LhymicroWriter(LaserProject(), controller=b'')
        writer.lock_rail()
        self.assertEqual(writer.controller, b'IS1P\n')

    def test_write_compact_mode_M2(self):
        writer = LhymicroWriter(LaserProject(), board="M2", controller=b'')
        writer.speed = 10
        writer.to_compact_mode()
        writer.move_relative(100, 0)
        writer.move_relative(0, 100)
        writer.move_relative(-100, 0)
        writer.move_relative(0, -100)
        writer.to_default_mode()
        self.assertEqual(writer.controller, b"ICV1151911011002218NRBS1EB100R100T100L100FNSE-\n")

    def test_write_compact_mode_B2(self):
        writer = LhymicroWriter(LaserProject(), board="B2", controller=b'')
        writer.speed = 10
        writer.to_compact_mode()
        writer.move_relative(100, 0)
        writer.move_relative(0, 100)
        writer.move_relative(-100, 0)
        writer.move_relative(0, -100)
        writer.to_default_mode()
        self.assertEqual(writer.controller, b"ICV0121101011005181NRBS1EB100R100T100L100FNSE-\n")
