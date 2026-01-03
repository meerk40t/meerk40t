import time
import unittest

import wx

from meerk40t.gui.wxutils import TextCtrl


class TestTextCtrl(unittest.TestCase):
    def setUp(self):
        # Ensure a wx App exists
        if not hasattr(wx, "GetApp") or wx.GetApp() is None:
            self._app = wx.App(False)
        else:
            self._app = None
        self.frame = wx.Frame(None)
        self.txt = TextCtrl(
            self.frame, id=wx.ID_ANY, value="", style=wx.TE_PROCESS_ENTER
        )

    def tearDown(self):
        try:
            self.frame.Destroy()
        except Exception:
            pass
        if self._app:
            try:
                self._app.Destroy()
            except Exception:
                pass

    def test_set_action_routine_none(self):
        # Set a real action first
        self.txt.SetActionRoutine(lambda: None)
        self.assertIsNotNone(self.txt._action_routine)
        # Now clear it
        self.txt.SetActionRoutine(None)
        self.assertIsNone(self.txt._action_routine)
        self.assertIsNone(getattr(self.txt, "_user_action", None))
        # Calling event handlers should not raise even when action is disabled
        e = wx.CommandEvent(wx.EVT_TEXT.typeId)
        self.txt.on_enter(e)  # should not raise

    def test_context_menu_action_runs(self):
        counter = {"c": 0}

        def action():
            counter["c"] += 1

        self.txt.SetActionRoutine(action)
        # Simulate the steps performed by the context-menu handler but without
        # setting _last_action_called_time here (the guarded wrapper should
        # perform debounce timing itself).
        self.txt.SetValue("10")
        self.txt.prevalidate("enter")
        self.txt._event_generated = wx.EVT_TEXT_ENTER
        now = time.time()
        self.txt._last_action_time = now
        self.txt._last_action_type = wx.EVT_TEXT_ENTER
        try:
            self.txt._action_routine()
        finally:
            self.txt._event_generated = None
        self.assertEqual(counter["c"], 1)


if __name__ == "__main__":
    unittest.main()
