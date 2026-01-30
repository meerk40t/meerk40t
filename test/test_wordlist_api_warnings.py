import unittest

from meerk40t.core.wordlist import Wordlist, TYPE_COUNTER, TYPE_STATIC


class TestWordlistAPIWarnings(unittest.TestCase):
    def setUp(self):
        self.wl = Wordlist("1.0.0")

    def test_get_load_warnings_populated(self):
        data = {"short": [0, 2], "good": [0, 2, "ok"]}
        import tempfile, json, os

        tf = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
        json.dump(data, tf)
        tf.flush()
        tf.close()
        try:
            self.wl.load_data(tf.name)
            self.assertTrue(self.wl.has_load_warnings())
            self.assertEqual(self.wl.get_warnings(), self.wl.get_load_warnings())
            self.assertTrue(any("short" in w for w in self.wl.get_warnings()))
        finally:
            os.unlink(tf.name)

    def test_validate_content_detects_issues(self):
        # Manually craft some broken entries
        self.wl.content = {
            "good": [TYPE_STATIC, 2, "x"],
            "badcounter": [TYPE_COUNTER, 2, "notint"],
            "badpos": [TYPE_STATIC, 100, "a", "b"],
            "badstruct": "nope",
        }
        issues = self.wl.validate_content()
        self.assertTrue(any("badcounter" in s for s in issues))
        self.assertTrue(any("badpos" in s for s in issues))
        self.assertTrue(any("badstruct" in s for s in issues))
        self.assertFalse(any("good" in s for s in issues))


if __name__ == "__main__":
    unittest.main()
