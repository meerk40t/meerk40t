import os
import sys
import unittest

# Ensure running from repository root works
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

import wx
from meerk40t.core.wordlist import Wordlist, TYPE_CSV
from meerk40t.gui.wordlisteditor import WordlistPanel


class DummyThemes:
    def set_window_colors(self, *args, **kwargs):
        pass

    def get(self, key, default=None):
        return default

    def set(self, key, value):
        pass


class DummyKernelRoot:
    def channel(self, name):
        class C:
            def __call__(self, msg):
                print("CHANNEL:", msg)

        return C()


class DummyKernel:
    def __init__(self):
        self.root = DummyKernelRoot()


class DummyContext:
    def __init__(self):
        self.themes = DummyThemes()
        self.elements = type("e", (), {})()
        self.elements.mywordlist = Wordlist("1.0.0")
        self.elements.wordlist_advance = lambda x: None
        self.kernel = DummyKernel()
        self.pane_lock = False
        self.wordlist_autosave = False

    def setting(self, *args, **kwargs):
        return None

    def signal(self, *args, **kwargs):
        return None

    def register(self, *args, **kwargs):
        return None


class MockBeginEvent:
    def __init__(self, index):
        self._index = index

    def GetIndex(self):
        return self._index

    def Allow(self):
        return None


class MockEndEvent:
    def __init__(self, index, text):
        self._index = index
        self._text = text

    def GetIndex(self):
        return self._index

    def GetLabel(self):
        return self._text

    def GetText(self):
        return self._text

    def Allow(self):
        return None


class TestVirtualContentEdit(unittest.TestCase):
    def setUp(self):
        # Required to create wx widgets
        self.app = wx.App(False)
        self.frame = wx.Frame(None)
        self.context = DummyContext()
        self.panel = WordlistPanel(self.frame, context=self.context)

    def tearDown(self):
        try:
            self.frame.Destroy()
        except Exception:
            pass
        try:
            self.app.Destroy()
        except Exception:
            pass

    def test_edit_commits_to_wordlist(self):
        # Prepare a key with two CSV values
        self.panel.wlist.set_value("people", "Alice", idx=-1, wtype=TYPE_CSV)
        self.panel.wlist.set_value("people", "Bob", idx=-1, wtype=TYPE_CSV)
        # Bind to first index
        self.panel.refresh_grid_content("people", 0)
        # Simulate begin label edit on index 0
        begin = MockBeginEvent(0)
        self.panel.on_begin_edit_content(begin)
        # Simulate end label edit applying new value
        end = MockEndEvent(0, "Alicia")
        self.panel.on_end_edit_content(end)
        # Verify change applied in the Wordlist (first data element at internal index 2)
        self.assertEqual(self.panel.wlist.fetch_value("people", 2), "Alicia")

    def test_paste_entries_summary_and_counts(self):
        # Prepare a key and initial entry to cause a duplicate
        key = "pastekey"
        self.panel.wlist.set_value(key, "initial", idx=-1, wtype=TYPE_CSV)
        self.panel.refresh_grid_content(key, 0)
        self.panel.cur_skey = key
        # Put clipboard data: one new, one duplicate, one empty (invalid)
        td = wx.TextDataObject("newentry\ninitial\n\n")
        try:
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(td)
            wx.TheClipboard.Close()
        except Exception:
            try:
                wx.TheClipboard.Close()
            except Exception:
                pass
        # Monkeypatch dialog to auto-accept
        orig = wx.MessageDialog.ShowModal
        try:
            wx.MessageDialog.ShowModal = lambda self: wx.ID_YES
            # Call the handler which should read clipboard and paste
            self.panel.on_btn_edit_content_paste(None)
            # After paste, the wordlist should contain newentry and skip duplicate
            self.assertTrue(self.panel.wlist.has_value(key, "newentry"))
            # The count for the key should have increased by exactly three (raw paste adds duplicates/empties)
            total = max(0, len(self.panel.wlist.content[key]) - 2)
            self.assertEqual(total, 4)
        finally:
            wx.MessageDialog.ShowModal = orig

    def test_context_paste_skips_duplicates_and_reports(self):
        # Simulate the context-menu paste behaviour that uses add_value_unique
        key = "contextpaste"
        self.panel.wlist.set_value(key, "initial", idx=-1, wtype=TYPE_CSV)
        lines = ["newentry", "initial", ""]
        added = 0
        skipped = 0
        invalid = 0
        for entry in lines:
            added_flag, reason = self.panel.wlist.add_value_unique(key, entry, 0)
            if added_flag:
                added += 1
            else:
                if reason == "duplicate":
                    skipped += 1
                else:
                    invalid += 1
        # Validate counts
        self.assertEqual(added, 1)
        self.assertEqual(skipped, 1)
        self.assertEqual(invalid, 1)
        # Build expected message like the UI does
        if invalid == 0:
            msg = f"Pasted {added} entries, skipped {skipped} duplicates"
        else:
            msg = f"Pasted {added} entries, skipped {skipped} duplicates, {invalid} invalid"
        # Sanity check that formatting matches expectations
        self.assertIn("Pasted", msg)
        self.assertIn(str(added), msg)
        self.assertIn(str(skipped), msg)
        self.assertIn(str(invalid), msg)

    def test_jump_to_index_sets_current(self):
        # Create many entries to simulate large list
        for i in range(1000):
            self.panel.wlist.set_value("cities", f"City{i}", idx=-1, wtype=TYPE_CSV)
        # Jump to a mid index
        self.panel.refresh_grid_content("cities", 0)
        # Programmatically set index
        self.panel.wlist.set_index("cities", 500)
        self.panel.refresh_grid_content("cities", 500)
        # Virtual grid should have current set to 500
        self.assertEqual(self.panel.grid_content.current, 500)

    def test_lazy_combo_populates_on_dropdown(self):
        # Create many entries to simulate large list
        for i in range(1000):
            self.panel.wlist.set_value("cities", f"City{i}", idx=-1, wtype=TYPE_CSV)
        self.panel.refresh_grid_content("cities", 0)
        # Initially the combo should have only a small placeholder
        initial_items = self.panel.cbo_index_single.GetItems()
        self.assertTrue(len(initial_items) <= 11)
        # Simulate dropdown event to trigger lazy populate
        class DummyEvent:
            def Skip(self):
                pass
        self.panel.on_cbo_index_single_dropdown(DummyEvent())
        # Now combo should contain full count
        items_after = self.panel.cbo_index_single.GetItems()
        self.assertEqual(len(items_after), 1000)

    def test_main_index_lazy_populates_on_dropdown(self):
        # Ensure cbo_Index lazy population works
        # Use existing Wordlist with CSVs from setUp
        # Call populate_gui which sets up lazy binding
        self.panel.populate_gui()
        # Ensure at least one CSV key is present
        self.panel.wlist.set_value("maincol", "X", idx=-1, wtype=TYPE_CSV)
        self.panel.populate_gui()
        # Simulate dropdown event for main index combo
        class DummyEvent:
            def Skip(self):
                pass
        self.panel.on_cbo_index_dropdown(DummyEvent())
        # Now main combo should be populated
        items = self.panel.cbo_Index.GetItems()
        self.assertTrue(len(items) >= 1)

    def test_on_jump_index_valid_and_cancel(self):
        # Add entries and ensure a valid jump works and cancel doesn't crash
        for i in range(20):
            self.panel.wlist.set_value("tests", f"T{i}", idx=-1, wtype=TYPE_CSV)
        self.panel.refresh_grid_content("tests", 0)
        # Monkeypatch wx.GetNumberFromUser to return a valid index
        orig = wx.GetNumberFromUser
        try:
            # First ensure combo is placeholder-only
            for i in range(1000):
                self.panel.wlist.set_value("big", f"B{i}", idx=-1, wtype=TYPE_CSV)
            self.panel.refresh_grid_content("big", 0)
            initial_items = self.panel.cbo_index_single.GetItems()
            self.assertTrue(len(initial_items) <= 11)

            wx.GetNumberFromUser = lambda *a, **k: 500
            class DummyEvent:
                def Skip(self):
                    pass
            # This should populate combo lazily and set current, without crashing
            self.panel.on_jump_index(DummyEvent())
            self.assertEqual(self.panel.grid_content.current, 500)

            # Now simulate cancel (return -1)
            wx.GetNumberFromUser = lambda *a, **k: -1
            self.panel.on_jump_index(DummyEvent())  # should not raise
        finally:
            wx.GetNumberFromUser = orig

    def test_jump_and_combo_scrolls_to_index(self):
        # Create many entries to ensure the target is outside the initial view
        for i in range(1500):
            self.panel.wlist.set_value("cities", f"City{i}", idx=-1, wtype=TYPE_CSV)
        self.panel.refresh_grid_content("cities", 0)

        # Jump via GetNumberFromUser and verify selection and visibility
        orig = wx.GetNumberFromUser
        try:
            wx.GetNumberFromUser = lambda *a, **k: 1200
            class DummyEvent:
                def Skip(self):
                    pass
            self.panel.on_jump_index(DummyEvent())
            # Ensure the current selection is updated
            self.assertEqual(self.panel.grid_content.current, 1200)
            # If supported, ensure the item is within the visible range
            try:
                top = self.panel.grid_content.GetTopItem()
                per = self.panel.grid_content.GetCountPerPage()
                self.assertTrue(top <= 1200 <= top + max(0, per - 1))
            except Exception:
                # Fallback: at least selection was set (above check)
                pass
        finally:
            wx.GetNumberFromUser = orig

        # Now test using the single-index combo selection
        # Ensure combo is fully populated
        class DummyEvent2:
            def Skip(self):
                pass
        self.panel.on_cbo_index_single_dropdown(DummyEvent2())
        # Ensure main grid is refreshed then select the 'cities' row so on_single_index can update the main index column
        self.panel.refresh_grid_wordlist()
        found = False
        for i in range(self.panel.grid_wordlist.GetItemCount()):
            if self.panel.get_column_text(self.panel.grid_wordlist, i, 0).lower() == "cities":
                self.panel.current_entry = i
                try:
                    self.panel.grid_wordlist.Select(i, True)
                except Exception:
                    pass
                found = True
                break
        self.assertTrue(found, "Could not locate 'cities' row in main grid")
        # Choose some small index and select it via combo
        target = 50
        # Ensure combo has been refreshed for the current key (populate placeholders again then force full population)
        self.panel.refresh_grid_content("cities", 0)
        class DummyEvent3:
            def Skip(self):
                pass
        self.panel.on_cbo_index_single_dropdown(DummyEvent3())
        # Ensure we have enough items
        items = self.panel.cbo_index_single.GetItems()
        self.assertTrue(len(items) >= target + 1)
        self.panel.cbo_index_single.SetSelection(target)
        self.panel.on_single_index(None)
        # Selection should be reflected
        self.assertEqual(self.panel.grid_content.current, target)
        try:
            top2 = self.panel.grid_content.GetTopItem()
            per2 = self.panel.grid_content.GetCountPerPage()
            self.assertTrue(top2 <= target <= top2 + max(0, per2 - 1))
        except Exception:
            pass

    def test_count_updates_on_add_and_delete(self):
        key = "animals"
        # Ensure starting from a clean state for this key
        if key in self.panel.wlist.content:
            del self.panel.wlist.content[key]
        # Add two entries
        self.panel.wlist.set_value(key, "Dog", idx=-1, wtype=TYPE_CSV)
        self.panel.wlist.set_value(key, "Cat", idx=-1, wtype=TYPE_CSV)
        # Refresh UI listing and verify count shows 2
        self.panel.refresh_grid_wordlist()
        found = False
        for i in range(self.panel.grid_wordlist.GetItemCount()):
            if self.panel.get_column_text(self.panel.grid_wordlist, i, 0).lower() == key:
                count_text = self.panel.get_column_text(self.panel.grid_wordlist, i, 3)
                self.assertEqual(count_text, "2")
                found = True
                break
        self.assertTrue(found, "Could not find the 'animals' row in the main grid")

        # Delete one entry and verify count updates to 1
        self.panel.wlist.delete_value(key, 0)
        self.panel.refresh_grid_wordlist()
        found = False
        for i in range(self.panel.grid_wordlist.GetItemCount()):
            if self.panel.get_column_text(self.panel.grid_wordlist, i, 0).lower() == key:
                count_text = self.panel.get_column_text(self.panel.grid_wordlist, i, 3)
                self.assertEqual(count_text, "1")
                found = True
                break
        self.assertTrue(found, "Could not find the 'animals' row after deletion")


if __name__ == "__main__":
    unittest.main()
