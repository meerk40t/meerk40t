# from __future__ import print_function
#
# import unittest
# from LhymicroWriter import LhymicroWriter
# from Kernel import Kernel
#
#
# class TestWriter(unittest.TestCase):
#
#     def test_write_home(self):
#         writer = LhymicroWriter()
#         k = Kernel()
#         k.controller = b''
#         k.add_module("K40Writer", writer)
#         writer.home()
#         self.assertEqual(k.controller, b"IPP\n")
#
#     def test_write_square(self):
#         writer = LhymicroWriter()
#         k = Kernel()
#         k.controller = b''
#         k.add_module("K40Writer", writer)
#         writer.move_relative(100, 0)
#         writer.move_relative(0, 100)
#         writer.move_relative(-100, 0)
#         writer.move_relative(0, -100)
#         self.assertEqual(k.controller, b"IB100S1P\nIR100S1P\nIT100S1P\nIL100S1P\n")
#
#     def test_write_lock_rail(self):
#         writer = LhymicroWriter()
#         k = Kernel()
#         k.controller = b''
#         k.add_module("K40Writer", writer)
#         writer.lock_rail()
#         self.assertEqual(k.controller, b'IS1P\n')
#
#     def test_write_compact_mode_M2(self):
#         k = Kernel()
#         k.controller = b''
#         k.setting(str, 'board', 'M2')
#         writer = LhymicroWriter()
#         k.add_module("K40Writer", writer)
#         writer.speed = 10
#         writer.to_compact_mode()
#         writer.move_relative(100, 0)
#         writer.move_relative(0, 100)
#         writer.move_relative(-100, 0)
#         writer.move_relative(0, -100)
#         writer.to_default_mode()
#         self.assertEqual(k.controller, b"ICV1151911011002218NRBS1EB100R100T100L100FNSE-\n")
#
#     def test_write_compact_mode_B2(self):
#         k = Kernel()
#         k.setting(str, "board", "B2")
#         writer = LhymicroWriter()
#
#         k.controller = b''
#         k.add_module("K40Writer", writer)
#         writer.speed = 10
#         writer.to_compact_mode()
#         writer.move_relative(100, 0)
#         writer.move_relative(0, 100)
#         writer.move_relative(-100, 0)
#         writer.move_relative(0, -100)
#         writer.to_default_mode()
#         self.assertEqual(k.controller, b"ICV0121101011005181NRBS1EB100R100T100L100FNSE-\n")
