import unittest

state = 0


class TestRuida(unittest.TestCase):
    def test_magic_keys(self):
        from meerk40t.ruida.rdjob import magic_keys

        keys = magic_keys()
        self.assertEqual(keys[b"\xd4\x89\r\xf7"], 0x88)
        self.assertEqual(keys[b"\xd9\x84\x08\xfe"], 0x83)
        self.assertEqual(keys[b"i4\xb8N"], 0x33)
        self.assertEqual(keys[b"I\x14\x98n"], 0x13)
        self.assertEqual(keys[b"z#\xa7]"], 0x22)
        self.assertEqual(keys[b"K\x12\x96p"], 0x11)
        self.assertEqual(keys[b"-x\xf4\n"], 0x77)
        self.assertEqual(keys[b"\xb6\xefk\x91"], 0xEE)
