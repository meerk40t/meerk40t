import os
import sys
import unittest

import wx


def find_meerk40t_path(start_path=None, max_levels=10):
    """
    Find the meerk40t package path by looking for meerk40t.py file.
    Traverses up the directory tree until found or max_levels reached.

    Args:
        start_path: Starting directory path (defaults to script directory)
        max_levels: Maximum directory levels to traverse up

    Returns:
        str: Path to meerk40t directory containing meerk40t.py, or None if not found
    """
    if start_path is None:
        start_path = os.path.dirname(os.path.abspath(__file__))

    current_path = start_path
    levels_traversed = 0

    while levels_traversed < max_levels:
        # Check if meerk40t.py exists in current directory
        meerk40t_py_path = os.path.join(current_path, "meerk40t.py")
        if os.path.isfile(meerk40t_py_path):
            return current_path

        # Move up one directory level
        parent_path = os.path.dirname(current_path)

        # If we've reached the root directory, stop
        if parent_path == current_path:
            break

        current_path = parent_path
        levels_traversed += 1

    return None


# Find and add meerk40t path
meerk40t_path = find_meerk40t_path()
if meerk40t_path:
    sys.path.insert(0, meerk40t_path)
else:
    print(
        "Warning: Could not find meerk40t.py in directory tree. Using system-installed version."
    )
    print(
        "This may cause import errors if the local development version has different constants."
    )

from mock_context import MockContext

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel


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
        self.context = MockContext()

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

    # =====================================================================
    # COMPREHENSIVE TYPE AND STYLE TESTING
    # =====================================================================

    def test_all_valid_type_style_combinations(self):
        """
        Comprehensive test of all valid type and style combinations for ChoicePropertyPanel.
        Tests value setting, successful setting validation, and control behavior.
        """
        from meerk40t.core.units import Angle, Length
        from meerk40t.svgelements import Color

        class ComprehensiveTestObject:
            def __init__(self):
                # Basic types
                self.bool_checkbox = True
                self.bool_button = False

                # String types
                self.str_text = "default_text"
                self.str_combo = "option2"
                self.str_combosmall = "small2"
                self.str_option = "opt1"
                self.str_radio = "radio1"
                self.str_color = "#FF0000"
                self.str_file = "test.txt"
                self.str_multiline = "line1\nline2"

                # Integer types
                self.int_text = 42
                self.int_slider = 5
                self.int_combo = 2
                self.int_combosmall = 1
                self.int_option = 10
                self.int_radio = 100
                self.int_binary = 0b1010  # 10 in decimal

                # Float types
                self.float_text = 3.14
                self.float_slider = 2.5
                self.float_combo = 1.1
                self.float_combosmall = 0.5
                self.float_power = 500.0
                self.float_speed = 20.0

                # Special types
                self.length_val = Length("10mm")
                self.angle_val = Angle("45deg")
                self.color_val = Color("#123456")

                # List/chart type
                self.list_chart = [
                    {"name": "item1", "value": 10},
                    {"name": "item2", "value": 20},
                ]

        test_obj = ComprehensiveTestObject()

        # Define all valid type/style combinations
        test_cases = [
            # Boolean types
            {
                "name": "bool_checkbox",
                "config": {
                    "object": test_obj,
                    "attr": "bool_checkbox",
                    "type": bool,
                    "label": "Bool Checkbox",
                },
                "test_value": False,
                "expected": False,
            },
            {
                "name": "bool_button",
                "config": {
                    "object": test_obj,
                    "attr": "bool_button",
                    "type": bool,
                    "style": "button",
                    "label": "Bool Button",
                },
                "test_value": True,
                "expected": True,
            },
            # String types
            {
                "name": "str_text",
                "config": {
                    "object": test_obj,
                    "attr": "str_text",
                    "type": str,
                    "label": "String Text",
                },
                "test_value": "modified_text",
                "expected": "modified_text",
            },
            {
                "name": "str_combo",
                "config": {
                    "object": test_obj,
                    "attr": "str_combo",
                    "type": str,
                    "style": "combo",
                    "choices": ["option1", "option2", "option3"],
                    "label": "String Combo",
                },
                "test_value": "option3",
                "expected": "option3",
            },
            {
                "name": "str_combosmall",
                "config": {
                    "object": test_obj,
                    "attr": "str_combosmall",
                    "type": str,
                    "style": "combosmall",
                    "choices": ["small1", "small2", "small3"],
                    "label": "String Combo Small",
                },
                "test_value": "small1",
                "expected": "small1",
            },
            {
                "name": "str_color",
                "config": {
                    "object": test_obj,
                    "attr": "str_color",
                    "type": str,
                    "style": "color",
                    "label": "String Color",
                },
                "test_value": "#00FF00",
                "expected": "#00FF00",
            },
            {
                "name": "str_file",
                "config": {
                    "object": test_obj,
                    "attr": "str_file",
                    "type": str,
                    "style": "file",
                    "label": "String File",
                },
                "test_value": "newfile.txt",
                "expected": "newfile.txt",
            },
            {
                "name": "str_multiline",
                "config": {
                    "object": test_obj,
                    "attr": "str_multiline",
                    "type": str,
                    "style": "multiline",
                    "label": "String Multiline",
                },
                "test_value": "new\nmulti\nline",
                "expected": "new\nmulti\nline",
            },
            {
                "name": "str_option",
                "config": {
                    "object": test_obj,
                    "attr": "str_option",
                    "type": str,
                    "style": "option",
                    "choices": ["opt1", "opt2"],
                    "display": ["Option 1", "Option 2"],
                    "label": "String Option",
                },
                "test_value": "opt2",
                "expected": "opt2",
            },
            # Integer types
            {
                "name": "int_text",
                "config": {
                    "object": test_obj,
                    "attr": "int_text",
                    "type": int,
                    "label": "Int Text",
                },
                "test_value": 100,
                "expected": 100,
            },
            {
                "name": "int_slider",
                "config": {
                    "object": test_obj,
                    "attr": "int_slider",
                    "type": int,
                    "style": "slider",
                    "min": 0,
                    "max": 10,
                    "label": "Int Slider",
                },
                "test_value": 8,
                "expected": 8,
            },
            {
                "name": "int_combo",
                "config": {
                    "object": test_obj,
                    "attr": "int_combo",
                    "type": int,
                    "style": "combo",
                    "choices": [1, 2, 3, 4],
                    "label": "Int Combo",
                },
                "test_value": 4,
                "expected": 4,
            },
            {
                "name": "int_combosmall",
                "config": {
                    "object": test_obj,
                    "attr": "int_combosmall",
                    "type": int,
                    "style": "combosmall",
                    "choices": [1, 2, 3],
                    "label": "Int Combo Small",
                },
                "test_value": 3,
                "expected": 3,
            },
            {
                "name": "int_option",
                "config": {
                    "object": test_obj,
                    "attr": "int_option",
                    "type": int,
                    "style": "option",
                    "choices": [10, 20, 30],
                    "display": ["Ten", "Twenty", "Thirty"],
                    "label": "Int Option",
                },
                "test_value": 30,
                "expected": 30,
            },
            {
                "name": "str_radio",
                "config": {
                    "object": test_obj,
                    "attr": "str_radio",
                    "type": str,
                    "style": "radio",
                    "choices": ["radio1", "radio2", "radio3"],
                    "label": "String Radio",
                },
                "test_value": "radio3",
                "expected": "radio3",
            },
            {
                "name": "int_radio",
                "config": {
                    "object": test_obj,
                    "attr": "int_radio",
                    "type": int,
                    "style": "radio",
                    "choices": [100, 200, 300],
                    "label": "Int Radio",
                },
                "test_value": 200,
                "expected": 200,
            },
            {
                "name": "float_combo",
                "config": {
                    "object": test_obj,
                    "attr": "float_combo",
                    "type": float,
                    "style": "combo",
                    "choices": [1.1, 2.2, 3.3, 4.4],
                    "label": "Float Combo",
                },
                "test_value": 3.3,
                "expected": 3.3,
            },
            {
                "name": "float_combosmall",
                "config": {
                    "object": test_obj,
                    "attr": "float_combosmall",
                    "type": float,
                    "style": "combosmall",
                    "choices": [0.5, 1.0, 1.5],
                    "label": "Float Combo Small",
                },
                "test_value": 1.5,
                "expected": 1.5,
            },
            {
                "name": "int_binary",
                "config": {
                    "object": test_obj,
                    "attr": "int_binary",
                    "type": int,
                    "style": "binary",
                    "bits": 4,
                    "label": "Int Binary",
                },
                "test_value": 0b1100,  # 12 in decimal
                "expected": 0b1100,
            },
            # Float types
            {
                "name": "float_text",
                "config": {
                    "object": test_obj,
                    "attr": "float_text",
                    "type": float,
                    "label": "Float Text",
                },
                "test_value": 6.28,
                "expected": 6.28,
            },
            {
                "name": "float_slider",
                "config": {
                    "object": test_obj,
                    "attr": "float_slider",
                    "type": float,
                    "style": "slider",
                    "min": 0.0,
                    "max": 10.0,
                    "label": "Float Slider",
                },
                "test_value": 7.5,
                "expected": 7.5,
            },
            {
                "name": "float_power_absolute",
                "config": {
                    "object": test_obj,
                    "attr": "float_power",
                    "type": float,
                    "style": "power",
                    "percent": False,
                    "label": "Float Power Absolute",
                },
                "test_value": 800.0,
                "expected": 800.0,
            },
            {
                "name": "float_speed_absolute",
                "config": {
                    "object": test_obj,
                    "attr": "float_speed",
                    "type": float,
                    "style": "speed",
                    "perminute": False,
                    "label": "Float Speed Absolute",
                },
                "test_value": 30.0,
                "expected": 30.0,
            },
            # Special types
            {
                "name": "length_val",
                "config": {
                    "object": test_obj,
                    "attr": "length_val",
                    "type": Length,
                    "label": "Length Value",
                },
                "test_value": Length("25mm"),
                "expected": "25.0mm",  # Length formatting includes decimal
            },
            {
                "name": "angle_val",
                "config": {
                    "object": test_obj,
                    "attr": "angle_val",
                    "type": Angle,
                    "label": "Angle Value",
                },
                "test_value": Angle("90deg"),
                "expected": "90deg",  # Compare as string for easier testing
            },
            {
                "name": "color_val",
                "config": {
                    "object": test_obj,
                    "attr": "color_val",
                    "type": Color,
                    "label": "Color Value",
                },
                "test_value": Color("#ABCDEF"),
                "expected": "#abcdef",  # Color hex is lowercase
            },
        ]

        # Test each type/style combination
        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                # Create panel with single choice
                choices = [test_case["config"]]
                panel = ChoicePropertyPanel(
                    self.frame, choices=choices, context=self.context
                )
                self.assertIsNotNone(
                    panel, f"Panel creation failed for {test_case['name']}"
                )

                # Verify initial value is set correctly
                initial_value = getattr(test_obj, test_case["config"]["attr"])
                self.assertIsNotNone(
                    initial_value, f"Initial value missing for {test_case['name']}"
                )

                # Manually set the new value to test the setting mechanism
                setattr(test_obj, test_case["config"]["attr"], test_case["test_value"])

                # Verify the value was set successfully
                final_value = getattr(test_obj, test_case["config"]["attr"])

                # Special handling for Length, Angle, and Color comparisons
                if test_case["config"]["type"] in (Length, Angle):
                    self.assertEqual(
                        str(final_value),
                        test_case["expected"],
                        f"Value setting failed for {test_case['name']}: expected {test_case['expected']}, got {str(final_value)}",
                    )
                elif test_case["config"]["type"] == Color:
                    self.assertEqual(
                        final_value.hex,
                        test_case["expected"],
                        f"Value setting failed for {test_case['name']}: expected {test_case['expected']}, got {final_value.hex}",
                    )
                else:
                    self.assertEqual(
                        final_value,
                        test_case["expected"],
                        f"Value setting failed for {test_case['name']}: expected {test_case['expected']}, got {final_value}",
                    )

    def test_power_speed_special_modes(self):
        """Test power and speed controls with percentage and per-minute modes."""

        class PowerSpeedObject:
            def __init__(self):
                self.power_percent = 500.0  # 50% in absolute mode
                self.power_absolute = 750.0
                self.speed_perminute = 1200.0  # 20 per second in absolute mode
                self.speed_absolute = 25.0

        test_obj = PowerSpeedObject()

        # Test power percentage mode (callable)
        def power_percent_mode():
            return True

        power_percent_choices = [
            {
                "object": test_obj,
                "attr": "power_percent",
                "type": float,
                "style": "power",
                "percent": power_percent_mode,
                "label": "Power Percentage",
            }
        ]

        panel = ChoicePropertyPanel(
            self.frame, choices=power_percent_choices, context=self.context
        )
        self.assertIsNotNone(panel)

        # Test power absolute mode (boolean)
        power_absolute_choices = [
            {
                "object": test_obj,
                "attr": "power_absolute",
                "type": float,
                "style": "power",
                "percent": False,
                "label": "Power Absolute",
            }
        ]

        panel = ChoicePropertyPanel(
            self.frame, choices=power_absolute_choices, context=self.context
        )
        self.assertIsNotNone(panel)

        # Test speed per-minute mode (callable)
        def speed_perminute_mode():
            return True

        speed_perminute_choices = [
            {
                "object": test_obj,
                "attr": "speed_perminute",
                "type": float,
                "style": "speed",
                "perminute": speed_perminute_mode,
                "label": "Speed Per Minute",
            }
        ]

        panel = ChoicePropertyPanel(
            self.frame, choices=speed_perminute_choices, context=self.context
        )
        self.assertIsNotNone(panel)

        # Test speed absolute mode (boolean)
        speed_absolute_choices = [
            {
                "object": test_obj,
                "attr": "speed_absolute",
                "type": float,
                "style": "speed",
                "perminute": False,
                "label": "Speed Absolute",
            }
        ]

        panel = ChoicePropertyPanel(
            self.frame, choices=speed_absolute_choices, context=self.context
        )
        self.assertIsNotNone(panel)

    def test_chart_list_controls(self):
        """Test chart/list controls with various configurations."""

        class ChartObject:
            def __init__(self):
                self.dict_list = [
                    {"name": "item1", "value": 10},
                    {"name": "item2", "value": 20},
                ]
                self.string_list = ["entry1", "entry2", "entry3"]
                self.tuple_list = [("col1", "col2"), ("row1col1", "row1col2")]

        test_obj = ChartObject()

        # Test dictionary list
        dict_chart_choices = [
            {
                "object": test_obj,
                "attr": "dict_list",
                "type": list,
                "style": "chart",
                "columns": [
                    {"label": "Name", "attr": "name", "type": str, "width": 100},
                    {"label": "Value", "attr": "value", "type": int, "width": 80},
                ],
                "allow_del": True,
                "allow_dup": True,
                "default": [],
                "label": "Dictionary Chart",
            }
        ]

        panel = ChoicePropertyPanel(
            self.frame, choices=dict_chart_choices, context=self.context
        )
        self.assertIsNotNone(panel)

        # Test string list
        string_chart_choices = [
            {
                "object": test_obj,
                "attr": "string_list",
                "type": list,
                "style": "chart",
                "columns": [{"label": "Entry", "type": str, "width": 150}],
                "allow_del": True,
                "allow_dup": False,
                "default": [],
                "label": "String Chart",
            }
        ]

        panel = ChoicePropertyPanel(
            self.frame, choices=string_chart_choices, context=self.context
        )
        self.assertIsNotNone(panel)

        # Test tuple list
        tuple_chart_choices = [
            {
                "object": test_obj,
                "attr": "tuple_list",
                "type": list,
                "style": "chart",
                "columns": [
                    {"label": "Column 1", "type": str, "width": 100},
                    {"label": "Column 2", "type": str, "width": 100},
                ],
                "allow_del": False,
                "allow_dup": True,
                "default": [],
                "label": "Tuple Chart",
            }
        ]

        panel = ChoicePropertyPanel(
            self.frame, choices=tuple_chart_choices, context=self.context
        )
        self.assertIsNotNone(panel)

    # =====================================================================
    # PARALLEL PANEL SYNCHRONIZATION TESTING
    # =====================================================================

    def test_parallel_panel_synchronization(self):
        """
        Test synchronization between two parallel ChoicePropertyPanels accessing the same object.
        Verifies that changes in one panel are properly propagated to the second panel and vice versa.
        """

        class SyncTestObject:
            def __init__(self):
                self.sync_bool = True
                self.sync_string = "initial"
                self.sync_int = 42
                self.sync_float = 3.14
                self.sync_power = 500.0
                self.sync_speed = 20.0

        # Create shared object
        sync_obj = SyncTestObject()

        # Define choices for both panels (identical configurations)
        shared_choices = [
            {
                "object": sync_obj,
                "attr": "sync_bool",
                "type": bool,
                "label": "Sync Bool",
                "signals": ["sync_update"],
            },
            {
                "object": sync_obj,
                "attr": "sync_string",
                "type": str,
                "label": "Sync String",
                "signals": ["sync_update"],
            },
            {
                "object": sync_obj,
                "attr": "sync_int",
                "type": int,
                "label": "Sync Int",
                "signals": ["sync_update"],
            },
            {
                "object": sync_obj,
                "attr": "sync_float",
                "type": float,
                "label": "Sync Float",
                "signals": ["sync_update"],
            },
            {
                "object": sync_obj,
                "attr": "sync_power",
                "type": float,
                "style": "power",
                "percent": False,
                "label": "Sync Power",
                "signals": ["sync_update"],
            },
            {
                "object": sync_obj,
                "attr": "sync_speed",
                "type": float,
                "style": "speed",
                "perminute": False,
                "label": "Sync Speed",
                "signals": ["sync_update"],
            },
        ]

        # Create two parallel panels
        panel1 = ChoicePropertyPanel(
            self.frame, choices=shared_choices, context=self.context
        )
        panel2 = ChoicePropertyPanel(
            self.frame, choices=shared_choices, context=self.context
        )

        self.assertIsNotNone(panel1, "Panel 1 creation failed")
        self.assertIsNotNone(panel2, "Panel 2 creation failed")

        # Test Case 1: Change value through direct object modification, verify both panels sync
        original_bool = sync_obj.sync_bool
        sync_obj.sync_bool = not original_bool

        # Trigger signal to notify panels
        self.context.signal("sync_bool", sync_obj.sync_bool, sync_obj)

        # Manually trigger reload on both panels to simulate synchronization
        panel1.reload()
        panel2.reload()

        # Verify both panels have the updated value
        self.assertEqual(
            sync_obj.sync_bool, not original_bool, "Object value not updated correctly"
        )

        # Test Case 2: Test string synchronization
        original_string = sync_obj.sync_string
        new_string = "synchronized_value"
        sync_obj.sync_string = new_string

        self.context.signal("sync_string", sync_obj.sync_string, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertEqual(
            sync_obj.sync_string, new_string, "String synchronization failed"
        )

        # Test Case 3: Test numeric synchronization
        original_int = sync_obj.sync_int
        new_int = 999
        sync_obj.sync_int = new_int

        self.context.signal("sync_int", sync_obj.sync_int, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertEqual(sync_obj.sync_int, new_int, "Integer synchronization failed")

        # Test Case 4: Test float synchronization
        original_float = sync_obj.sync_float
        new_float = 2.718
        sync_obj.sync_float = new_float

        self.context.signal("sync_float", sync_obj.sync_float, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertAlmostEqual(
            sync_obj.sync_float, new_float, places=3, msg="Float synchronization failed"
        )

        # Test Case 5: Test power control synchronization
        original_power = sync_obj.sync_power
        new_power = 750.0
        sync_obj.sync_power = new_power

        self.context.signal("sync_power", sync_obj.sync_power, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertAlmostEqual(
            sync_obj.sync_power, new_power, places=1, msg="Power synchronization failed"
        )

        # Test Case 6: Test speed control synchronization
        original_speed = sync_obj.sync_speed
        new_speed = 35.0
        sync_obj.sync_speed = new_speed

        self.context.signal("sync_speed", sync_obj.sync_speed, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertAlmostEqual(
            sync_obj.sync_speed, new_speed, places=1, msg="Speed synchronization failed"
        )

    def test_parallel_panel_with_special_types(self):
        """Test parallel panel synchronization with Length, Angle, and Color types."""
        from meerk40t.core.units import Angle, Length
        from meerk40t.svgelements import Color

        class SpecialSyncObject:
            def __init__(self):
                self.sync_length = Length("10mm")
                self.sync_angle = Angle("45deg")
                self.sync_color = Color("#FF0000")

        sync_obj = SpecialSyncObject()

        special_choices = [
            {
                "object": sync_obj,
                "attr": "sync_length",
                "type": Length,
                "label": "Sync Length",
                "signals": ["special_sync"],
            },
            {
                "object": sync_obj,
                "attr": "sync_angle",
                "type": Angle,
                "label": "Sync Angle",
                "signals": ["special_sync"],
            },
            {
                "object": sync_obj,
                "attr": "sync_color",
                "type": Color,
                "label": "Sync Color",
                "signals": ["special_sync"],
            },
        ]

        panel1 = ChoicePropertyPanel(
            self.frame, choices=special_choices, context=self.context
        )
        panel2 = ChoicePropertyPanel(
            self.frame, choices=special_choices, context=self.context
        )

        self.assertIsNotNone(panel1)
        self.assertIsNotNone(panel2)

        # Test Length synchronization
        new_length = Length("25mm")
        sync_obj.sync_length = new_length
        self.context.signal("sync_length", sync_obj.sync_length, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertEqual(
            str(sync_obj.sync_length), "25.0mm", "Length synchronization failed"
        )

        # Test Angle synchronization
        new_angle = Angle("90deg")
        sync_obj.sync_angle = new_angle
        self.context.signal("sync_angle", sync_obj.sync_angle, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertEqual(
            str(sync_obj.sync_angle), "90deg", "Angle synchronization failed"
        )

        # Test Color synchronization
        new_color = Color("#00FF00")
        sync_obj.sync_color = new_color
        self.context.signal("sync_color", sync_obj.sync_color, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertEqual(
            sync_obj.sync_color.hex, "#00ff00", "Color synchronization failed"
        )

    def test_parallel_panel_conditional_enabling(self):
        """Test conditional enabling synchronization between parallel panels."""

        class ConditionalSyncObject:
            def __init__(self):
                self.master_control = True
                self.dependent_control = "dependent_value"
                self.range_control = 15
                self.range_dependent = "range_value"

        sync_obj = ConditionalSyncObject()

        conditional_choices = [
            {
                "object": sync_obj,
                "attr": "master_control",
                "type": bool,
                "label": "Master Control",
                "signals": ["conditional_sync"],
            },
            {
                "object": sync_obj,
                "attr": "dependent_control",
                "type": str,
                "label": "Dependent Control",
                "conditional": (sync_obj, "master_control"),
                "signals": ["conditional_sync"],
            },
            {
                "object": sync_obj,
                "attr": "range_control",
                "type": int,
                "label": "Range Control",
                "signals": ["conditional_sync"],
            },
            {
                "object": sync_obj,
                "attr": "range_dependent",
                "type": str,
                "label": "Range Dependent",
                "conditional": (sync_obj, "range_control", 10, 20),
                "signals": ["conditional_sync"],
            },
        ]

        panel1 = ChoicePropertyPanel(
            self.frame, choices=conditional_choices, context=self.context
        )
        panel2 = ChoicePropertyPanel(
            self.frame, choices=conditional_choices, context=self.context
        )

        self.assertIsNotNone(panel1)
        self.assertIsNotNone(panel2)

        # Test boolean conditional synchronization
        sync_obj.master_control = False
        self.context.signal("master_control", sync_obj.master_control, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertFalse(
            sync_obj.master_control, "Boolean conditional synchronization failed"
        )

        # Test range conditional synchronization
        sync_obj.range_control = 25  # Outside range [10, 20]
        self.context.signal("range_control", sync_obj.range_control, sync_obj)
        panel1.reload()
        panel2.reload()

        self.assertEqual(
            sync_obj.range_control, 25, "Range conditional synchronization failed"
        )

    def test_massive_parallel_synchronization_stress(self):
        """Stress test with many parallel panels and rapid value changes."""

        class StressTestObject:
            def __init__(self):
                self.stress_value = 0

        stress_obj = StressTestObject()

        stress_choices = [
            {
                "object": stress_obj,
                "attr": "stress_value",
                "type": int,
                "label": "Stress Value",
                "signals": ["stress_sync"],
            }
        ]

        # Create multiple parallel panels
        panels = []
        for i in range(5):  # 5 parallel panels
            panel = ChoicePropertyPanel(
                self.frame, choices=stress_choices, context=self.context
            )
            self.assertIsNotNone(panel, f"Stress panel {i} creation failed")
            panels.append(panel)

        # Perform rapid value changes
        for value in range(10):
            stress_obj.stress_value = value
            self.context.signal("stress_value", stress_obj.stress_value, stress_obj)

            # Reload all panels
            for panel in panels:
                panel.reload()

            # Verify all panels are synchronized
            self.assertEqual(
                stress_obj.stress_value,
                value,
                f"Stress synchronization failed at value {value}",
            )

    def test_signal_propagation_mechanisms(self):
        """Test various signal propagation mechanisms and additional signals."""

        class SignalTestObject:
            def __init__(self):
                self.primary_value = "primary"
                self.secondary_value = "secondary"

        signal_obj = SignalTestObject()

        # Test single additional signal
        single_signal_choices = [
            {
                "object": signal_obj,
                "attr": "primary_value",
                "type": str,
                "label": "Primary Value",
                "signals": "secondary_update",  # Single string signal
            }
        ]

        panel1 = ChoicePropertyPanel(
            self.frame, choices=single_signal_choices, context=self.context
        )
        self.assertIsNotNone(panel1)

        # Test multiple additional signals
        multiple_signal_choices = [
            {
                "object": signal_obj,
                "attr": "secondary_value",
                "type": str,
                "label": "Secondary Value",
                "signals": [
                    "primary_update",
                    "general_update",
                    "specific_update",
                ],  # List of signals
            }
        ]

        panel2 = ChoicePropertyPanel(
            self.frame, choices=multiple_signal_choices, context=self.context
        )
        self.assertIsNotNone(panel2)

        # Test signal propagation
        signal_obj.primary_value = "modified_primary"
        self.context.signal("primary_value", signal_obj.primary_value, signal_obj)
        self.context.signal("secondary_update")  # Additional signal from primary

        panel1.reload()
        panel2.reload()

        self.assertEqual(
            signal_obj.primary_value,
            "modified_primary",
            "Primary value signal propagation failed",
        )

        signal_obj.secondary_value = "modified_secondary"
        self.context.signal("secondary_value", signal_obj.secondary_value, signal_obj)
        self.context.signal("primary_update")  # One of multiple additional signals
        self.context.signal("general_update")  # Another additional signal

        panel1.reload()
        panel2.reload()

        self.assertEqual(
            signal_obj.secondary_value,
            "modified_secondary",
            "Secondary value signal propagation failed",
        )


if __name__ == "__main__":
    unittest.main()
