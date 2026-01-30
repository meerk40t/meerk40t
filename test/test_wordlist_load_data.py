import json
import os
import tempfile
import unittest

from meerk40t.core.wordlist import Wordlist, TYPE_COUNTER


class TestWordlistLoadData(unittest.TestCase):
    def setUp(self):
        self.wl = Wordlist("1.0.0")

    def make_temp_json(self, content):
        tf = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
        json.dump(content, tf)
        tf.flush()
        tf.close()
        return tf.name

    def test_load_data_normalize_and_validate(self):
        data = {
            "  Foo ": [0, 2, "val"],
            "Bar": [2, 2, "5"],  # counter as string should be coerced
            "InvalidList": "notalist",
            "Another": [99, 2, "x"],  # invalid type
        }
        fname = self.make_temp_json(data)
        try:
            self.wl.load_data(fname)
            self.assertIn("foo", self.wl.content)
            self.assertEqual(self.wl.fetch("foo"), "val")
            self.assertIn("bar", self.wl.content)
            # Counter should be int 5
            self.assertEqual(self.wl.fetch("bar"), 5)
            # Invalid entries should be skipped
            self.assertNotIn("invalidlist", self.wl.content)
            self.assertNotIn("another", self.wl.content)
        finally:
            os.unlink(fname)

    def test_counters_increment_on_translate(self):
        # Create a counter and ensure translate increments it
        self.wl.content["ctr"] = [TYPE_COUNTER, 2, 10]
        out = self.wl.translate("{ctr}")
        self.assertEqual(out, "10")
        # Now it should have incremented
        self.assertEqual(self.wl.content["ctr"][2], 11)

    def test_load_data_non_dict_root_keeps_existing(self):
        # JSON root is not a dict; load_data should keep existing content unchanged
        fname = self.make_temp_json([1, 2, 3])
        try:
            before = dict(self.wl.content)
            self.wl.load_data(fname)
            # No new non-normalized keys should be present; builtins still present
            for k in ("version", "date", "time"):
                self.assertIn(k, self.wl.content)
            # content should not be replaced by a list
            self.assertEqual(self.wl.content.get("version")[2], "1.0.0")
            self.assertEqual(set(self.wl.content.keys()) & set(["0", "1", "2"]), set())
        finally:
            os.unlink(fname)

    def test_load_data_skips_malformed_entries(self):
        data = {
            "short": [0, 2],  # too short
            "badtype": [3, 2, "x"],  # invalid type
            "good": [0, 2, "ok"],
        }
        fname = self.make_temp_json(data)
        try:
            self.wl.load_data(fname)
            # Ensure warnings were emitted for skipped entries
            self.assertTrue(self.wl.has_warnings())
            warnings = self.wl.get_warnings()
            self.assertTrue(any("Skipping wordlist entry 'short'" in w for w in warnings))
            self.assertTrue(any("Skipping wordlist entry 'badtype'" in w for w in warnings))
            self.assertIn("good", self.wl.content)
            self.assertNotIn("short", self.wl.content)
            self.assertNotIn("badtype", self.wl.content)
        finally:
            os.unlink(fname)

    def test_load_data_non_dict_root_keeps_existing(self):
        # JSON root is not a dict; load_data should keep existing content unchanged
        fname = self.make_temp_json([1, 2, 3])
        try:
            self.wl.load_data(fname)
            # Check warning about non-dict top level
            self.assertTrue(self.wl.has_warnings())
            warnings = self.wl.get_warnings()
            self.assertTrue(any("non-dict top-level" in w for w in warnings))
            for k in ("version", "date", "time"):
                self.assertIn(k, self.wl.content)
            # content should not be replaced by a list
            self.assertEqual(self.wl.content.get("version")[2], "1.0.0")
            self.assertEqual(set(self.wl.content.keys()) & set(["0", "1", "2"]), set())
        finally:
            os.unlink(fname)

    def test_save_and_load_roundtrip(self):
        # Add a custom key with csv entries
        self.wl.set_value("MyKey", "one", idx=-1, wtype=1)
        self.wl.set_value("MyKey", "two", idx=-1, wtype=1)
        tf = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
        try:
            tfname = tf.name
            tf.close()
            self.wl.save_data(tfname)
            wl2 = Wordlist("2.0.0")
            wl2.load_data(tfname)
            # The loaded content should include 'mykey'
            self.assertIn("mykey", wl2.content)
            # Ensure the entries exist
            self.assertEqual(wl2.fetch("mykey"), "one")
        finally:
            os.unlink(tfname)


if __name__ == "__main__":
    unittest.main()
