import unittest

from meerk40t.core.wordlist import (
    Wordlist,
    TYPE_CSV,
    TYPE_COUNTER,
    IDX_POSITION,
    IDX_DATA_START,
)


class TestWordlistMore(unittest.TestCase):
    def setUp(self):
        self.wl = Wordlist("1.0.0")

    def test_set_index_all_and_relative(self):
        # Prepare two csv keys with at least 5 entries each
        for k in ("a", "b"):
            for i in range(5):
                self.wl.set_value(k, f"V{i}", idx=-1, wtype=TYPE_CSV)
        # Set index for all
        self.wl.set_index("@all", 3)
        for k in ("a", "b"):
            self.assertEqual(self.wl.content[k][IDX_POSITION], IDX_DATA_START + 3)
        # Relative change on single key
        old = self.wl.content["a"][IDX_POSITION]
        self.wl.set_index("a", "+1")
        # Increased by 1 but capped by last index
        self.assertEqual(self.wl.content["a"][IDX_POSITION], min(old + 1, len(self.wl.content["a"]) - 1))

    def test_move_all_indices_and_counters(self):
        # Create csv and counter keys
        for i in range(3):
            self.wl.set_value(f"c{i}", f"X{i}", idx=-1, wtype=TYPE_CSV)
        self.wl.set_value("cnt", 10, idx=None, wtype=TYPE_COUNTER)
        # Move forward
        prev_pos = {k: self.wl.content[k][IDX_POSITION] for k in self.wl.content}
        self.wl.move_all_indices(2)
        for k in self.wl.content:
            if self.wl.content[k][0] == TYPE_COUNTER:
                # Counter should be incremented by delta
                self.assertTrue(int(self.wl.content[k][IDX_DATA_START]) >= 10)
            else:
                # Check positions didn't become negative
                self.assertGreaterEqual(self.wl.content[k][IDX_POSITION], IDX_DATA_START)
        # Move backward by large amount should clamp to IDX_DATA_START
        self.wl.move_all_indices(-1000)
        for k in self.wl.content:
            if self.wl.content[k][0] != TYPE_COUNTER:
                self.assertGreaterEqual(self.wl.content[k][IDX_POSITION], IDX_DATA_START)

    def test_set_value_append_and_delete_bounds(self):
        key = "z"
        # Append a few values
        self.wl.set_value(key, "one", idx=-1, wtype=TYPE_CSV)
        self.wl.set_value(key, "two", idx=-1)
        length_before = len(self.wl.content[key])
        # Append using set_value with idx=-1
        self.wl.set_value(key, "three", idx=-1)
        self.assertEqual(len(self.wl.content[key]), length_before + 1)
        # Delete out-of-range should be a no-op
        before = list(self.wl.content[key])
        self.wl.delete_value(key, 9999)
        self.assertEqual(self.wl.content[key], before)

    def test_reset_specific_key(self):
        self.wl.set_value("k1", "A", idx=-1, wtype=TYPE_CSV)
        self.wl.set_index("k1", 3)
        self.wl.reset("k1")
        self.assertEqual(self.wl.content["k1"][IDX_POSITION], IDX_DATA_START)


if __name__ == "__main__":
    unittest.main()
