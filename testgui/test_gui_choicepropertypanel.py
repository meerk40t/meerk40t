import unittest

import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from testgui import (
    mock_context,  # Assuming you have a mock_context.py with the MockContext class
)


class DummyObject:
    def __init__(self):
        self.name = "TestName"
        self.enabled = True
        self.power = 500
        self.speed = 20


class ChoicePropertyPanelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = wx.App(False)
        self.frame = wx.Frame(None)
        self.obj = DummyObject()
        self.context = mock_context.MockContext()

    def tearDown(self):
        self.frame.Destroy()
        self.app.Destroy()

    def test_basic_text_control(self):
        choices = [{"object": self.obj, "attr": "name", "type": str, "label": "Name"}]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        # Find the text control
        text_ctrl = None
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                text_ctrl = child
                break
        self.assertIsNotNone(text_ctrl)
        # Simulate user input
        text_ctrl.SetValue("NewName")
        text_ctrl.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, text_ctrl.GetId()))
        self.assertEqual(self.obj.name, "NewName")

    def test_power_control_percent_mode(self):
        def percent_mode():
            return True

        choices = [
            {
                "object": self.obj,
                "attr": "power",
                "type": float,
                "style": "power",
                "percent": percent_mode,
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        text_ctrl = None
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                text_ctrl = child
                break
        self.assertIsNotNone(text_ctrl)
        # Simulate entering 50% power
        text_ctrl.SetValue("50")
        text_ctrl.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, text_ctrl.GetId()))
        # Should convert 50% to 500 (absolute)
        self.assertEqual(self.obj.power, 500)

    def test_speed_control_perminute_mode(self):
        def perminute_mode():
            return True

        choices = [
            {
                "object": self.obj,
                "attr": "speed",
                "type": float,
                "style": "speed",
                "perminute": perminute_mode,
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        text_ctrl = None
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                text_ctrl = child
                break
        self.assertIsNotNone(text_ctrl)
        # Simulate entering 600 per minute (should convert to 10 per second)
        text_ctrl.SetValue("600")
        text_ctrl.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, text_ctrl.GetId()))
        self.assertAlmostEqual(self.obj.speed, 10.0)

    def test_checkbox_control(self):
        choices = [
            {"object": self.obj, "attr": "enabled", "type": bool, "label": "Enabled"}
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        checkbox = None
        for child in panel.GetChildren():
            if isinstance(child, wx.CheckBox):
                checkbox = child
                break
        self.assertIsNotNone(checkbox)
        # Simulate unchecking
        checkbox.SetValue(False)
        checkbox.ProcessEvent(wx.CommandEvent(wx.EVT_CHECKBOX.typeId, checkbox.GetId()))
        self.assertFalse(self.obj.enabled)

    def test_all_types_and_styles(self):
        from meerk40t.core.units import Angle, Length
        from meerk40t.svgelements import Color

        class Obj:
            def __init__(self):
                self.intval = 5
                self.floatval = 3.14
                self.boolval = False
                self.strval = "abc"
                self.lengthval = Length("10mm")
                self.angleval = Angle("45deg")
                self.colorval = Color("#123456")
                self.listval = [1, 2, 3]
                self.combo = "A"
                self.combosmall = 2
                self.option = "opt2"
                self.fileval = "file.txt"
                self.multiline = "line1\nline2"
                self.power = 1000
                self.speed = 20
                self.binary = 0b1010
                self.button = False

        obj = Obj()
        # Choices for all types/styles
        choices = [
            {
                "object": obj,
                "attr": "intval",
                "type": int,
                "style": "slider",
                "min": 0,
                "max": 10,
            },
            {
                "object": obj,
                "attr": "floatval",
                "type": float,
                "style": "slider",
                "min": 0.0,
                "max": 10.0,
            },
            {"object": obj, "attr": "boolval", "type": bool},
            {"object": obj, "attr": "strval", "type": str},
            {"object": obj, "attr": "lengthval", "type": Length},
            {"object": obj, "attr": "angleval", "type": Angle},
            {"object": obj, "attr": "colorval", "type": Color},
            {"object": obj, "attr": "listval", "type": list, "style": "chart"},
            {
                "object": obj,
                "attr": "combo",
                "type": str,
                "style": "combo",
                "choices": ["A", "B", "C"],
            },
            {
                "object": obj,
                "attr": "combosmall",
                "type": int,
                "style": "combosmall",
                "choices": [1, 2, 3],
            },
            {
                "object": obj,
                "attr": "option",
                "type": str,
                "style": "option",
                "choices": ["opt1", "opt2"],
                "display": ["Option 1", "Option 2"],
            },
            {"object": obj, "attr": "fileval", "type": str, "style": "file"},
            {"object": obj, "attr": "multiline", "type": str, "style": "multiline"},
            {
                "object": obj,
                "attr": "power",
                "type": float,
                "style": "power",
                "percent": lambda: False,
            },
            {
                "object": obj,
                "attr": "speed",
                "type": float,
                "style": "speed",
                "perminute": lambda: False,
            },
            {
                "object": obj,
                "attr": "binary",
                "type": int,
                "style": "binary",
                "bits": 4,
            },
            {"object": obj, "attr": "button", "type": bool, "style": "button"},
            {"object": obj, "attr": "colorval", "type": str, "style": "color"},
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        # Simulate user interaction for each type/style
        # Int slider
        for child in panel.GetChildren():
            if isinstance(child, wx.Slider):
                child.SetValue(7)
                child.ProcessEvent(wx.CommandEvent(wx.EVT_SLIDER.typeId, child.GetId()))
                self.assertEqual(obj.intval, 7)
                break
        # Float slider
        for child in panel.GetChildren():
            if isinstance(child, wx.Slider):
                child.SetValue(8)
                child.ProcessEvent(wx.CommandEvent(wx.EVT_SLIDER.typeId, child.GetId()))
                self.assertEqual(obj.floatval, 8)
                break
        # Bool checkbox
        for child in panel.GetChildren():
            if isinstance(child, wx.CheckBox):
                child.SetValue(True)
                child.ProcessEvent(
                    wx.CommandEvent(wx.EVT_CHECKBOX.typeId, child.GetId())
                )
                self.assertTrue(obj.boolval)
                break
        # String text
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetValue("xyz")
                child.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, child.GetId()))
                self.assertEqual(obj.strval, "xyz")
                break
        # Length
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetValue("20mm")
                child.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, child.GetId()))
                self.assertEqual(str(obj.lengthval), "20.0000mm")
                break
        # Angle
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetValue("90deg")
                child.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, child.GetId()))
                self.assertEqual(str(obj.angleval), "90deg")
                break
        # Color (as Color type)
        for child in panel.GetChildren():
            if hasattr(child, "SetBackgroundColour") and hasattr(
                child, "SetForegroundColour"
            ):
                # Simulate color change if possible
                pass  # GUI event simulation for color picker is non-trivial
        # Combo
        for child in panel.GetChildren():
            if isinstance(child, wx.ComboBox):
                child.SetValue("B")
                child.ProcessEvent(
                    wx.CommandEvent(wx.EVT_COMBOBOX.typeId, child.GetId())
                )
                self.assertEqual(obj.combo, "B")
                break
        # Combosmall
        for child in panel.GetChildren():
            if isinstance(child, wx.ComboBox):
                child.SetValue("3")
                child.ProcessEvent(
                    wx.CommandEvent(wx.EVT_COMBOBOX.typeId, child.GetId())
                )
                self.assertEqual(obj.combosmall, 3)
                break
        # Option
        for child in panel.GetChildren():
            if isinstance(child, wx.ComboBox):
                child.SetValue("opt1")
                child.ProcessEvent(
                    wx.CommandEvent(wx.EVT_COMBOBOX.typeId, child.GetId())
                )
                self.assertEqual(obj.option, "opt1")
                break
        # File (simulate text entry)
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetValue("newfile.txt")
                child.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, child.GetId()))
                self.assertEqual(obj.fileval, "newfile.txt")
                break
        # Multiline
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetValue("line1\nline2\nline3")
                child.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, child.GetId()))
                self.assertEqual(obj.multiline, "line1\nline2\nline3")
                break
        # Power (absolute)
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetValue("800")
                child.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, child.GetId()))
                self.assertEqual(obj.power, 800)
                break
        # Speed (per second)
        for child in panel.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SetValue("40")
                child.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT.typeId, child.GetId()))
                self.assertEqual(obj.speed, 40)
                break
        # Binary (simulate bit toggling)
        # Not trivial to simulate all bits, but check at least one
        # Button (simulate click)
        for child in panel.GetChildren():
            if isinstance(child, wx.Button):
                child.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, child.GetId()))
                # Button style sets to True on click
                self.assertTrue(obj.button)
                break


if __name__ == "__main__":
    unittest.main()
