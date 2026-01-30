import unittest

from meerk40t.core.wordlist import (
    Wordlist,
    TYPE_CSV,
    IDX_POSITION,
    IDX_DATA_START,
)


class TestWordlistKeys(unittest.TestCase):
    def setUp(self):
        self.wl = Wordlist("1.0.0")

    def test_fetch_none_empty(self):
        self.assertIsNone(self.wl.fetch(None))
        self.assertIsNone(self.wl.fetch(""))
        self.assertIsNone(self.wl.fetch("   "))

    def test_set_none_empty_noop(self):
        before = dict(self.wl.content)
        # Should not raise
        self.wl.set_value(None, "x")
        self.wl.set_value("", "y")
        self.wl.set_value("   ", "z")
        self.assertEqual(before, self.wl.content)

    def test_add_none_empty_noop(self):
        before = dict(self.wl.content)
        self.wl.add_value(None, "x")
        self.wl.add_value("", "y")
        self.assertEqual(before, self.wl.content)

    def test_delete_value_none_empty_noerror(self):
        self.wl.add_value("foo", "one")
        before = dict(self.wl.content)
        # Should not raise and not modify content
        self.wl.delete_value(None, 0)
        self.wl.delete_value("", 0)
        self.assertEqual(before, self.wl.content)

    def test_set_index_none_empty_noerror(self):
        # add a key and attempt to call set_index with invalid keys
        self.wl.add_value("bar", "a")
        before = dict(self.wl.content)
        self.wl.set_index(None, 1)
        self.wl.set_index("", 1)
        self.assertEqual(before, self.wl.content)

    def test_rename_key_invalid(self):
        self.assertFalse(self.wl.rename_key(None, "a"))
        self.assertFalse(self.wl.rename_key("a", None))
        self.assertFalse(self.wl.rename_key("", "b"))
        self.assertFalse(self.wl.rename_key("a", ""))

    def test_reset_empty_noop_and_reset_none_resets_all(self):
        # create csv-like list by adding values with wtype
        self.wl.add_value("baz", "one", wtype=TYPE_CSV)
        self.wl.add_value("baz", "two", wtype=TYPE_CSV)
        # set index to 2 (zero-based outside => internal pos = IDX_DATA_START + 2)
        self.wl.set_index("baz", 2)
        pos_before = self.wl.content["baz"][IDX_POSITION]
        # reset with empty string should be a no-op
        self.wl.reset("")
        self.assertEqual(pos_before, self.wl.content["baz"][IDX_POSITION])
        # reset(None) should reset all
        self.wl.reset(None)
        self.assertEqual(self.wl.content["baz"][IDX_POSITION], IDX_DATA_START)

    def test_normalize_and_trim(self):
        # Directly test helper behavior
        self.assertIsNone(self.wl._normalize_key(None))
        self.assertIsNone(self.wl._normalize_key(""))
        self.assertIsNone(self.wl._normalize_key("   "))
        self.assertEqual(self.wl._normalize_key("  FooBar  "), "foobar")

    def test_set_fetch_with_padded_keys(self):
        # set with padded key should create lowercased trimmed key
        self.wl.set_value("  MixedCase ", "value")
        self.assertIn("mixedcase", self.wl.content)
        self.assertEqual(self.wl.fetch(" mixedcase "), "value")
        self.assertEqual(self.wl.fetch("MIXEDcase"), "value")

    def test_delete_and_rename_with_padded_keys(self):
        self.wl.add_value("  ToBeRenamed  ", "one")
        self.assertIn("toberenamed", self.wl.content)
        # rename with padding
        ok = self.wl.rename_key("  ToBeRenamed  ", "  NewName ")
        self.assertTrue(ok)
        self.assertIn("newname", self.wl.content)
        # delete with padded key
        self.wl.delete("  NewName  ")
        self.assertNotIn("newname", self.wl.content)


if __name__ == "__main__":
    unittest.main()
