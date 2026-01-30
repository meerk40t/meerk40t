import os
import tempfile
import unittest

from meerk40t.core.wordlist import Wordlist


class TestWordlistCSVWarnings(unittest.TestCase):
    def setUp(self):
        self.wl = Wordlist("1.0.0")

    def test_missing_file_reports_warning(self):
        fname = os.path.join(tempfile.gettempdir(), "definitely-not-a-file-12345.csv")
        # Ensure file doesn't exist
        if os.path.exists(fname):
            os.remove(fname)
        rows, cols, headers = self.wl.load_csv_file(fname)
        self.assertEqual(rows, 0)
        self.assertEqual(cols, 0)
        self.assertEqual(headers, [])
        self.assertTrue(self.wl.has_load_warnings())
        warnings = self.wl.get_load_warnings()
        self.assertTrue(any("Could not read CSV file" in w or "Failed to load CSV file" in w for w in warnings))

    def test_malformed_csv_reports_warning(self):
        # Create a file with an unterminated quote to trigger csv.Error
        fname = os.path.join(tempfile.gettempdir(), "malformed_wordlist.csv")
        with open(fname, "w", encoding="utf-8") as f:
            f.write('col1,col2\n"bad line without closing quote\n')
        rows, cols, headers = self.wl.load_csv_file(fname)
        # On failure, it should report zero rows and an empty headers list
        self.assertEqual(rows, 0)
        self.assertEqual(headers, [])
        self.assertTrue(self.wl.has_load_warnings())
        warnings = self.wl.get_load_warnings()
        # Accept either the previous generic failure message or the new malformed CSV warning
        self.assertTrue(any("Failed to load CSV file" in w or "Malformed CSV file" in w for w in warnings))
        os.remove(fname)


if __name__ == "__main__":
    unittest.main()
