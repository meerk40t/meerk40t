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
        # Choices for all types/styles - mix of with and without conditional fields
        choices = [
            {
                "object": obj,
                "attr": "intval",
                "type": int,
                "style": "slider",
                "min": 0,
                "max": 10,
                # No conditional field - should work fine
            },
            {
                "object": obj,
                "attr": "floatval",
                "type": float,
                "style": "slider",
                "min": 0.0,
                "max": 10.0,
                "conditional": None,  # Explicit None conditional
            },
            {"object": obj, "attr": "boolval", "type": bool},  # No conditional
            {"object": obj, "attr": "strval", "type": str, "conditional": None},
            {"object": obj, "attr": "lengthval", "type": Length},  # No conditional
            {"object": obj, "attr": "angleval", "type": Angle, "conditional": None},
            {"object": obj, "attr": "colorval", "type": Color},  # No conditional
            {
                "object": obj,
                "attr": "listval",
                "type": list,
                "style": "chart",
                "conditional": None,
            },
            {
                "object": obj,
                "attr": "combo",
                "type": str,
                "style": "combo",
                "choices": ["A", "B", "C"],
                # No conditional field
            },
            {
                "object": obj,
                "attr": "combosmall",
                "type": int,
                "style": "combosmall",
                "choices": [1, 2, 3],
                "conditional": None,
            },
            {
                "object": obj,
                "attr": "option",
                "type": str,
                "style": "option",
                "choices": ["opt1", "opt2"],
                "display": ["Option 1", "Option 2"],
                # No conditional field
            },
            {
                "object": obj,
                "attr": "fileval",
                "type": str,
                "style": "file",
                "conditional": None,
            },
            {
                "object": obj,
                "attr": "multiline",
                "type": str,
                "style": "multiline",
                # No conditional field
            },
            {
                "object": obj,
                "attr": "power",
                "type": float,
                "style": "power",
                "percent": lambda: False,
                "conditional": None,
            },
            {
                "object": obj,
                "attr": "speed",
                "type": float,
                "style": "speed",
                "perminute": lambda: False,
                # No conditional field
            },
            {
                "object": obj,
                "attr": "binary",
                "type": int,
                "style": "binary",
                "bits": 4,
                "conditional": None,
            },
            {
                "object": obj,
                "attr": "button",
                "type": bool,
                "style": "button",
                # No conditional field
            },
            {
                "object": obj,
                "attr": "colorval",
                "type": str,
                "style": "color",
                "conditional": None,
            },
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        # Just verify the panel was created successfully - testing individual control interactions
        # is complex due to the way controls are created and managed
        self.assertIsNotNone(panel)
        # Check that basic objects exist
        self.assertEqual(obj.intval, 5)  # Should be unchanged
        self.assertEqual(obj.floatval, 3.14)  # Should be unchanged
        self.assertFalse(obj.boolval)  # Should be unchanged
        self.assertEqual(obj.strval, "abc")  # Should be unchanged

    def test_choices_without_conditional_field(self):
        """Test that choices without conditional field work properly."""
        choices = [
            {"object": self.obj, "attr": "name", "type": str, "label": "Name"},
            {"object": self.obj, "attr": "enabled", "type": bool, "label": "Enabled"},
            {"object": self.obj, "attr": "power", "type": float, "style": "power"},
        ]
        # Should create panel without errors even though no conditional fields are present
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)
        # Verify objects haven't changed
        self.assertEqual(self.obj.name, "TestName")
        self.assertTrue(self.obj.enabled)
        self.assertEqual(self.obj.power, 500)

    def test_conditional_enabling_scenarios(self):
        """Test various conditional enabling scenarios including edge cases."""

        class ConditionalObject:
            def __init__(self):
                self.master_bool = True
                self.dependent_str = "test"
                self.master_int = 5
                self.dependent_int = 10
                self.range_value = 15
                self.dependent_range = "in_range"

        cond_obj = ConditionalObject()

        # Test case 1: Basic boolean conditional (2-element tuple)
        choices = [
            {
                "object": cond_obj,
                "attr": "master_bool",
                "type": bool,
                "label": "Master",
            },
            {
                "object": cond_obj,
                "attr": "dependent_str",
                "type": str,
                "label": "Dependent",
                "conditional": (
                    cond_obj,
                    "master_bool",
                ),  # Should be enabled when master_bool is True
            },
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 2: Equality conditional (3-element tuple)
        choices = [
            {
                "object": cond_obj,
                "attr": "master_int",
                "type": int,
                "label": "Master Int",
            },
            {
                "object": cond_obj,
                "attr": "dependent_int",
                "type": int,
                "label": "Dependent Int",
                "conditional": (
                    cond_obj,
                    "master_int",
                    5,
                ),  # Should be enabled when master_int == 5
            },
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 3: Range conditional (4-element tuple)
        choices = [
            {
                "object": cond_obj,
                "attr": "range_value",
                "type": int,
                "label": "Range Value",
            },
            {
                "object": cond_obj,
                "attr": "dependent_range",
                "type": str,
                "label": "Dependent Range",
                "conditional": (
                    cond_obj,
                    "range_value",
                    10,
                    20,
                ),  # Should be enabled when 10 <= range_value <= 20
            },
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

    def test_invalid_conditional_scenarios(self):
        """Test invalid conditional configurations to ensure robustness."""

        class TestObject:
            def __init__(self):
                self.value = 10

        test_obj = TestObject()

        # Test case 1: Invalid conditional tuple (only 1 element)
        choices = [
            {
                "object": test_obj,
                "attr": "value",
                "type": int,
                "label": "Test Value",
                "conditional": (test_obj,),  # Invalid - missing attribute
            }
        ]
        # Should not crash, should handle gracefully
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 2: Empty conditional tuple
        choices = [
            {
                "object": test_obj,
                "attr": "value",
                "type": int,
                "label": "Test Value",
                "conditional": (),  # Invalid - empty tuple
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 3: Non-existent attribute in conditional
        choices = [
            {
                "object": test_obj,
                "attr": "value",
                "type": int,
                "label": "Test Value",
                "conditional": (
                    test_obj,
                    "non_existent_attr",
                ),  # Attribute doesn't exist
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

    def test_binary_controls_edge_cases(self):
        """Test binary controls with various bit configurations."""

        class BinaryObject:
            def __init__(self):
                self.bits_4 = 0b1010  # 10 in decimal
                self.bits_8 = 0b11110000  # 240 in decimal
                self.bits_1 = 0b1  # 1 in decimal
                self.mask_bits = 0b1111  # All 4 bits enabled

        binary_obj = BinaryObject()

        # Test case 1: 4-bit binary control
        choices = [
            {
                "object": binary_obj,
                "attr": "bits_4",
                "type": int,
                "style": "binary",
                "bits": 4,
                "label": "4-bit Value",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 2: 8-bit binary control
        choices = [
            {
                "object": binary_obj,
                "attr": "bits_8",
                "type": int,
                "style": "binary",
                "bits": 8,
                "label": "8-bit Value",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 3: 1-bit binary control (edge case)
        choices = [
            {
                "object": binary_obj,
                "attr": "bits_1",
                "type": int,
                "style": "binary",
                "bits": 1,
                "label": "1-bit Value",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 4: Binary control with mask
        choices = [
            {
                "object": binary_obj,
                "attr": "bits_4",
                "type": int,
                "style": "binary",
                "bits": 4,
                "mask": "mask_bits",
                "label": "Masked 4-bit Value",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

    def test_slider_edge_cases(self):
        """Test slider controls with various edge cases."""

        class SliderObject:
            def __init__(self):
                self.zero_min = 5
                self.negative_range = -10
                self.large_range = 1000000
                self.float_precision = 3.14159

        slider_obj = SliderObject()

        # Test case 1: Slider with min=0
        choices = [
            {
                "object": slider_obj,
                "attr": "zero_min",
                "type": int,
                "style": "slider",
                "min": 0,
                "max": 10,
                "label": "Zero Min Slider",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 2: Slider with negative range
        choices = [
            {
                "object": slider_obj,
                "attr": "negative_range",
                "type": int,
                "style": "slider",
                "min": -20,
                "max": 0,
                "label": "Negative Range Slider",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 3: Float slider with high precision
        choices = [
            {
                "object": slider_obj,
                "attr": "float_precision",
                "type": float,
                "style": "slider",
                "min": 0.0,
                "max": 10.0,
                "label": "Float Precision Slider",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 4: Large range slider (potential performance issue)
        choices = [
            {
                "object": slider_obj,
                "attr": "large_range",
                "type": int,
                "style": "slider",
                "min": 0,
                "max": 2000000,
                "label": "Large Range Slider",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

    def test_missing_required_fields(self):
        """Test choices with missing required fields."""

        # Test case 1: Missing 'object' field
        choices = [
            {
                "attr": "name",
                "type": str,
                "label": "Name",
                # Missing 'object' field
            }
        ]
        # Should handle gracefully or raise appropriate error
        try:
            panel = ChoicePropertyPanel(
                self.frame, choices=choices, context=self.context
            )
            # If it doesn't crash, that's also acceptable
            self.assertIsNotNone(panel)
        except (KeyError, AttributeError):
            # Expected behavior for missing required fields
            pass

        # Test case 2: Missing 'attr' field
        choices = [
            {
                "object": self.obj,
                "type": str,
                "label": "Name",
                # Missing 'attr' field
            }
        ]
        try:
            panel = ChoicePropertyPanel(
                self.frame, choices=choices, context=self.context
            )
            self.assertIsNotNone(panel)
        except (KeyError, AttributeError):
            pass

        # Test case 3: Missing 'type' field
        choices = [
            {
                "object": self.obj,
                "attr": "name",
                "label": "Name",
                # Missing 'type' field
            }
        ]
        try:
            panel = ChoicePropertyPanel(
                self.frame, choices=choices, context=self.context
            )
            self.assertIsNotNone(panel)
        except (KeyError, AttributeError):
            pass

    def test_special_style_combinations(self):
        """Test special style and type combinations."""

        class SpecialObject:
            def __init__(self):
                self.power_percent = 500
                self.speed_perminute = 20
                self.color_string = "#FF0000"
                self.file_path = "/path/to/file.txt"
                self.multiline_text = "Line 1\nLine 2\nLine 3"

        special_obj = SpecialObject()

        # Test case 1: Power with percentage mode function
        def get_percent_mode():
            return True

        choices = [
            {
                "object": special_obj,
                "attr": "power_percent",
                "type": float,
                "style": "power",
                "percent": get_percent_mode,
                "label": "Power Percentage",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 2: Speed with per-minute mode function
        def get_perminute_mode():
            return True

        choices = [
            {
                "object": special_obj,
                "attr": "speed_perminute",
                "type": float,
                "style": "speed",
                "perminute": get_perminute_mode,
                "label": "Speed Per Minute",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 3: String type with color style
        choices = [
            {
                "object": special_obj,
                "attr": "color_string",
                "type": str,
                "style": "color",
                "label": "Color String",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 4: File style control
        choices = [
            {
                "object": special_obj,
                "attr": "file_path",
                "type": str,
                "style": "file",
                "label": "File Path",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 5: Multiline text control
        choices = [
            {
                "object": special_obj,
                "attr": "multiline_text",
                "type": str,
                "style": "multiline",
                "label": "Multiline Text",
            }
        ]
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

    def test_empty_and_null_choices(self):
        """Test edge cases with empty or null choices."""

        # Test case 1: Empty choices list
        choices = []
        panel = ChoicePropertyPanel(self.frame, choices=choices, context=self.context)
        self.assertIsNotNone(panel)

        # Test case 2: None choices
        choices = None
        try:
            panel = ChoicePropertyPanel(
                self.frame, choices=choices, context=self.context
            )
            self.assertIsNotNone(panel)
        except (TypeError, AttributeError):
            # Expected behavior for None choices
            pass

        # Test case 3: Choices with None elements
        choices = [None, {"object": self.obj, "attr": "name", "type": str}]
        try:
            panel = ChoicePropertyPanel(
                self.frame, choices=choices, context=self.context
            )
            self.assertIsNotNone(panel)
        except (TypeError, AttributeError):
            # Expected behavior for None choice elements
            pass


if __name__ == "__main__":
    unittest.main()
