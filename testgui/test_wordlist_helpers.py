# GUI test group - helper tests that are safe to run in GUI-capable environments.
# This test was moved here from `test/` to avoid running it in headless CI pipelines.

import unittest
import os
import sys

# When running this file directly, ensure that the project root is on sys.path
# so `from meerk40t.core.wordlist import Wordlist` works outside discovery.
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from meerk40t.core.wordlist import Wordlist


class TestWordlistHelpers(unittest.TestCase):
    def setUp(self):
        self.wl = Wordlist("0.0.0")

    def test_has_value_and_add_unique(self):
        # Initially no entry
        self.assertFalse(self.wl.has_value("people", "Alice"))
        # add unique returns True
        added, reason = self.wl.add_value_unique("people", "Alice")
        self.assertTrue(added)
        self.assertIsNone(reason)
        # has_value is True now
        self.assertTrue(self.wl.has_value("people", "Alice"))
        # add duplicate returns False with duplicate reason
        added, reason = self.wl.add_value_unique("people", "Alice")
        self.assertFalse(added)
        self.assertEqual(reason, "duplicate")
        # add another unique
        added, reason = self.wl.add_value_unique("people", "Bob")
        self.assertTrue(added)
        self.assertIsNone(reason)
        self.assertTrue(self.wl.has_value("people", "Bob"))

    def test_normalization_and_case_insensitive(self):
        self.wl.add_value("  Name  ", "Val1")
        # has_value should normalize key and compare strings
        self.assertTrue(self.wl.has_value("name", "Val1"))
        self.assertTrue(self.wl.has_value("NAME", "Val1"))
        # add_value_unique should respect normalization
        added, reason = self.wl.add_value_unique("name ", "Val1")
        self.assertFalse(added)
        self.assertEqual(reason, "duplicate")

    def test_add_empty_entry_reports_empty(self):
        # empty string
        added, reason = self.wl.add_value_unique("people", "")
        self.assertFalse(added)
        self.assertEqual(reason, "empty")
        # None
        added, reason = self.wl.add_value_unique("people", None)
        self.assertFalse(added)
        self.assertEqual(reason, "empty")

if __name__ == "__main__":
    unittest.main()
