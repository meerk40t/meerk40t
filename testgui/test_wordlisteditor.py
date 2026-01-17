import os
import sys
import unittest
import wx


def find_meerk40t_path(start_path=None, max_levels=10):
    if start_path is None:
        start_path = os.path.dirname(os.path.abspath(__file__))

    current_path = start_path
    levels_traversed = 0

    while levels_traversed < max_levels:
        meerk40t_py_path = os.path.join(current_path, "meerk40t.py")
        if os.path.isfile(meerk40t_py_path):
            return current_path

        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            break
        current_path = parent_path
        levels_traversed += 1

    return None


meerk40t_path = find_meerk40t_path()
if meerk40t_path:
    sys.path.insert(0, meerk40t_path)
else:
    print("Warning: Could not find meerk40t.py in directory tree. Using system-installed version.")

from types import SimpleNamespace

from mock_context import MockContext
from meerk40t.core.wordlist import Wordlist
from meerk40t.gui.wordlisteditor import WordlistPanel


class DummyEvent:
    def __init__(self, text=None):
        self._text = text

    def GetText(self):
        return self._text

    def Allow(self):
        return None

    def Veto(self):
        return None


class WordlistEditorGuiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = wx.App(False)
        self.frame = wx.Frame(None)
        self.context = MockContext()
        # Provide missing settings expected by WordlistPanel
        self.context.wordlist_autosave = False

        # Minimal elements container with Wordlist
        wl = Wordlist("test-version")
        # Add two keys to force a rename conflict
        wl.add("jj", "value_jj")
        wl.add("kk", "value_kk")
        self.context.elements = SimpleNamespace(mywordlist=wl)

    def tearDown(self):
        self.frame.Destroy()
        self.app.Destroy()

    def test_rename_conflict_does_not_crash_and_shows_message(self):
        panel = WordlistPanel(self.frame, context=self.context)
        # Ensure GUI is populated
        panel.populate_gui()

        # Find the index for 'jj'
        jj_index = None
        for i in range(panel.grid_wordlist.GetItemCount()):
            if panel.get_column_text(panel.grid_wordlist, i, 0).lower() == "jj":
                jj_index = i
                break
        self.assertIsNotNone(jj_index, "Could not find 'jj' entry in grid")

        # Select the item and begin edit
        panel.grid_wordlist.Select(jj_index, True)
        panel.on_begin_edit_wordlist(DummyEvent())

        # Attempt to rename 'jj' to 'kk' which already exists -> should fail
        panel.on_end_edit_wordlist(DummyEvent("kk"))

        # Rename should have failed, original key should still exist
        self.assertIn("jj", self.context.elements.mywordlist.content)
        self.assertIn("kk", self.context.elements.mywordlist.content)

        # The panel should not have crashed; message label should indicate failure
        msg = panel.lbl_message.GetLabel()
        self.assertTrue("Rename failed" in msg or len(msg) > 0)


if __name__ == "__main__":
    unittest.main()
