import os
import tempfile
import unittest

from meerk40t.core.wordlist import Wordlist, TYPE_CSV


class TestWordlistCSVHeaders(unittest.TestCase):
    def setUp(self):
        self.wl = Wordlist("1.0.0")

    def make_temp_csv(self, content):
        tf = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", newline="")
        tf.write(content)
        tf.flush()
        tf.close()
        return tf.name

    def test_load_csv_headers_normalized_and_unique(self):
        csv_content = (
            "  Foo , \ufeffBar, foo , , Last\n"
            "a,b,c,d,e\n"
        )
        fname = self.make_temp_csv(csv_content)
        try:
            ct, colcount, headers = self.wl.load_csv_file(fname, force_header=True)
            # Expect 2 rows total (header row consumed, one data row)
            self.assertEqual(ct, 1)
            self.assertEqual(colcount, 5)
            # headers should be normalized and unique
            # 'foo' and duplicate should be 'foo_2'
            self.assertIn("foo", headers)
            self.assertIn("bar", headers)
            self.assertIn("foo_2", headers)
            self.assertIn("column_4", headers)
            self.assertIn("last", headers)
            # Values should be present in content
            self.assertEqual(self.wl.fetch("foo"), "a")
            self.assertEqual(self.wl.fetch("bar"), "b")
            self.assertEqual(self.wl.fetch("foo_2"), "c")
            self.assertEqual(self.wl.fetch("column_4"), "d")
            self.assertEqual(self.wl.fetch("last"), "e")
        finally:
            os.unlink(fname)

    def test_load_csv_no_header(self):
        csv_content = "alpha,beta\n1,2\n3,4\n"
        fname = self.make_temp_csv(csv_content)
        try:
            ct, colcount, headers = self.wl.load_csv_file(fname, force_header=False)
            # Now first row should be used as data; total 3 rows processed (header-as-data + 2 rows)
            self.assertEqual(ct, 3)
            self.assertEqual(colcount, 2)
            self.assertEqual(headers, ["column_1", "column_2"])
            # column_1 should have first entry 'alpha' as fetched value
            self.assertEqual(self.wl.fetch("column_1"), "alpha")
            # second column first entry is header 'beta' (first row was used as data)
            self.assertEqual(self.wl.fetch("column_2"), "beta")
        finally:
            os.unlink(fname)


if __name__ == "__main__":
    unittest.main()
