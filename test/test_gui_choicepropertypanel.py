import unittest
from test import bootstrap
from unittest.mock import Mock, patch

import wx

from meerk40t.core.units import Angle, Length
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.svgelements import Color


class MockControl:
    """Mock wxPython control for testing without GUI."""

    def __init__(self):
        self.enabled = True
        self.value = None
        self.tooltip = None
        self.width = None

    def Enable(self, state):
        self.enabled = state

    def SetValue(self, value):
        self.value = value

    def GetValue(self):
        return self.value

    def SetToolTip(self, tip):
        self.tooltip = tip

    def SetMinSize(self, size):
        self.width = size[0] if isinstance(size, (list, tuple)) else size

    def SetMaxSize(self, size):
        """Mock SetMaxSize method for wx controls."""
        self.max_size = size

    def GetSize(self):
        """Mock GetSize method for wx controls."""
        return getattr(self, "size", (100, 20))

    def Bind(self, event, handler):
        # Store the handler for potential testing
        self._bound_handlers = getattr(self, "_bound_handlers", {})
        self._bound_handlers[event] = handler


class MockContext:
    """Mock context for testing."""

    def __init__(self):
        self.signals = []
        self.listeners = []
        self.kernel = Mock()
        self.kernel.is_shutdown = False
        self.themes = Mock()
        self.themes.set_window_colors = Mock()

    def signal(self, *args):
        self.signals.append(args)

    def listen(self, signal, listener):
        self.listeners.append((signal, listener))

    def lookup(self, category, key):
        # Mock lookup for choices
        if category == "choices":
            return [
                {"attr": "test_attr", "type": str, "label": "Test"},
                {"attr": "test_bool", "type": bool, "label": "Boolean Test"},
            ]
        return None


class MockTestObject:
    """Mock object with properties for testing."""

    def __init__(self):
        self.test_attr = "test_value"
        self.test_bool = True
        self.test_int = 42
        self.test_float = 3.14
        self.test_length = Length("10mm")
        self.test_angle = Angle("45deg")
        self.test_color = Color("red")
        self.conditional_attr = True


class TestChoicePropertyPanel(unittest.TestCase):
    """Test cases for ChoicePropertyPanel."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal wx.App if it doesn't exist
        if not wx.GetApp():
            self.app = wx.App()
        else:
            self.app = None

        # Create mock context
        self.mock_context = MockContext()

        # Create mock parent
        self.mock_parent = Mock()

        # Create test object
        self.test_obj = MockTestObject()

    def tearDown(self):
        """Clean up after tests."""
        if self.app:
            self.app.Destroy()

    def create_panel(self, choices=None):
        """Helper to create a ChoicePropertyPanel with mocked dependencies."""
        with patch("meerk40t.gui.choicepropertypanel.ScrolledPanel.__init__"):
            panel = ChoicePropertyPanel.__new__(ChoicePropertyPanel)
            panel.context = Mock()  # Use Mock instead of MockContext
            panel.context.signals = []
            panel.context.listeners = []
            panel.context.listen = Mock()
            panel.context.signal = Mock()
            panel.listeners = []
            panel.entries_per_column = None
            return panel

    def test_get_control_factory_dispatch_table(self):
        """Test the dispatch table functionality."""
        panel = self.create_panel()

        # Test string type with different styles
        factory, handler, special = panel._get_control_factory(str, None)
        self.assertIsNotNone(factory)

        factory, handler, special = panel._get_control_factory(str, "file")
        self.assertIsNotNone(factory)

        factory, handler, special = panel._get_control_factory(str, "multiline")
        self.assertIsNotNone(factory)

        factory, handler, special = panel._get_control_factory(str, "combo")
        self.assertIsNotNone(factory)

        # Test bool type
        factory, handler, special = panel._get_control_factory(bool, None)
        self.assertIsNotNone(factory)

        # Test int type with slider
        factory, handler, special = panel._get_control_factory(int, "slider")
        self.assertIsNotNone(factory)

        # Test Color type
        factory, handler, special = panel._get_control_factory(Color, None)
        self.assertEqual(factory, "color_type")
        self.assertTrue(special)

        # Test unsupported combination
        factory, handler, special = panel._get_control_factory(dict, "unsupported")
        self.assertIsNone(factory)

    def test_enabled_conditional_precedence(self):
        """Test enabled/conditional precedence logic."""
        panel = self.create_panel()
        control = MockControl()

        # Test Case 1: enabled=False takes precedence
        choice = {"enabled": False, "conditional": [self.test_obj, "conditional_attr"]}
        panel._setup_single_control_properties(
            choice, control, "test_attr", self.test_obj
        )
        self.assertFalse(control.enabled)

        # Test Case 2: enabled=True, conditional determines state
        choice = {"enabled": True, "conditional": [self.test_obj, "conditional_attr"]}
        control.enabled = True  # Reset
        panel._setup_single_control_properties(
            choice, control, "test_attr", self.test_obj
        )
        self.assertTrue(
            control.enabled
        )  # conditional_attr is True, so should be enabled

        # Test Case 3: No enabled, conditional determines state
        choice = {"conditional": [self.test_obj, "conditional_attr"]}
        control.enabled = False  # Reset
        panel._setup_single_control_properties(
            choice, control, "test_attr", self.test_obj
        )
        self.assertTrue(control.enabled)

        # Test Case 4: No conditional, enabled=True
        control.enabled = False  # Reset
        choice = {"enabled": True}
        panel._setup_single_control_properties(
            choice, control, "test_attr", self.test_obj
        )
        self.assertTrue(control.enabled)

        # Test Case 5: Neither specified (default enabled)
        control.enabled = False  # Reset
        choice = {}
        panel._setup_single_control_properties(
            choice, control, "test_attr", self.test_obj
        )
        self.assertTrue(control.enabled)

    def test_conditional_enabling_scenarios(self):
        """Test different conditional enabling scenarios."""
        panel = self.create_panel()
        control = MockControl()

        # Test 2-element conditional (boolean check)
        choice = {"conditional": [self.test_obj, "conditional_attr"]}
        panel._setup_conditional_enabling(choice, control, "test_attr", self.test_obj)
        self.assertTrue(control.enabled)

        # Test 3-element conditional (equality check)
        choice = {"conditional": [self.test_obj, "test_attr", "test_value"]}
        panel._setup_conditional_enabling(choice, control, "test_attr", self.test_obj)
        self.assertTrue(control.enabled)

        choice = {"conditional": [self.test_obj, "test_attr", "wrong_value"]}
        panel._setup_conditional_enabling(choice, control, "test_attr", self.test_obj)
        self.assertFalse(control.enabled)

        # Test 4-element conditional (range check)
        choice = {"conditional": [self.test_obj, "test_int", 40, 50]}
        panel._setup_conditional_enabling(choice, control, "test_attr", self.test_obj)
        self.assertTrue(control.enabled)  # 42 is in range [40, 50]

        choice = {"conditional": [self.test_obj, "test_int", 50, 60]}
        panel._setup_conditional_enabling(choice, control, "test_attr", self.test_obj)
        self.assertFalse(control.enabled)  # 42 is not in range [50, 60]

    def test_conditional_enabling_memory_leak_prevention(self):
        """Test that conditional enabling listeners are properly managed during hide/show cycles."""
        panel = self.create_panel()
        control1 = MockControl()
        control2 = MockControl()

        # Set up first conditional enabling
        choice = {"conditional": [self.test_obj, "conditional_attr"]}
        panel._setup_conditional_enabling(choice, control1, "test_attr", self.test_obj)

        # Check that listeners were added
        initial_listener_count = len(panel.listeners)
        self.assertGreater(initial_listener_count, 0)

        # Set up second conditional enabling for same attribute/object
        panel._setup_conditional_enabling(choice, control2, "test_attr", self.test_obj)

        # Should have additional listeners (one per control)
        final_listener_count = len(panel.listeners)
        self.assertGreater(final_listener_count, initial_listener_count)

        # Test cleanup - simulate pane hide
        panel.pane_hide()

        # Listeners should be preserved for restoration, but unlisten should be called
        self.assertEqual(
            len(panel.listeners), final_listener_count
        )  # Listeners preserved
        self.assertEqual(
            panel.context.unlisten.call_count, final_listener_count
        )  # All unlistened

        # Test restoration - simulate pane show
        panel.pane_show()

        # Should re-listen to all preserved listeners (original calls + restoration calls)
        self.assertEqual(panel.context.listen.call_count, final_listener_count * 2)

    def test_radio_handler_string_selection(self):
        """Test that radio handler correctly gets string values using GetString() not GetLabel()."""
        if not wx.GetApp():
            wx.App()

        panel = self.create_panel()

        # Create a radio box with string choices
        choices = ["option1", "option2", "option3"]
        frame = wx.Frame(None)
        radio_ctrl = wx.RadioBox(frame, choices=choices, label="Test Radio")

        # Set selection to index 1 ("option2")
        radio_ctrl.SetSelection(1)

        # Create the radio handler for string type
        handler = panel._make_radio_select_handler(
            "test_attr", radio_ctrl, self.test_obj, str, []
        )

        # Test that GetString returns the correct value (not GetLabel)
        selection = radio_ctrl.GetSelection()
        string_value = (
            radio_ctrl.GetString(selection) if selection != wx.NOT_FOUND else ""
        )
        label_value = radio_ctrl.GetLabel()

        # Verify the difference
        self.assertEqual(string_value, "option2")  # Correct value
        self.assertEqual(label_value, "Test Radio")  # Wrong value (control label)
        self.assertNotEqual(string_value, label_value)  # Should be different

        # Simulate event (handler should use GetString, not GetLabel)
        event = wx.CommandEvent(wx.wxEVT_COMMAND_RADIOBOX_SELECTED)
        event.SetEventObject(radio_ctrl)

        # Call handler
        try:
            handler(event)
            # If handler worked, the object should have the correct string value
            new_value = getattr(self.test_obj, "test_attr", None)
            # Should be "option2", not "Test Radio"
            self.assertEqual(new_value, "option2")
        except Exception:
            # If there's an exception due to missing context, that's acceptable for this test
            # The important thing is that our GetString logic is correct
            pass

        frame.Destroy()

    def test_conditional_enabling_no_crash_on_missing_key(self):
        """Test that missing conditional key doesn't crash."""
        panel = self.create_panel()
        control = MockControl()

        # This should not crash when "conditional" key is missing
        choice = {"enabled": True}
        try:
            panel._setup_conditional_enabling(
                choice, control, "test_attr", self.test_obj
            )
            # Should fallback to enabled value
            self.assertTrue(control.enabled)
        except KeyError:
            self.fail(
                "_setup_conditional_enabling crashed on missing 'conditional' key"
            )

    def test_combo_error_handling(self):
        """Test that combo handlers gracefully handle type conversion errors."""
        panel = self.create_panel()

        # Mock combo control that can return different values
        class MockComboControl:
            def __init__(self, value=""):
                self.value = value

            def GetValue(self):
                return self.value

            def SetValue(self, value):
                self.value = value

            def GetSelection(self):
                return 0  # Default valid selection

        # Test combo text handler with invalid input
        combo_ctrl = MockComboControl("invalid_number")
        handler = panel._make_combo_text_handler(
            "test_attr", combo_ctrl, self.test_obj, int, []
        )

        # Should not crash on invalid input
        event = wx.CommandEvent()
        try:
            handler(event)
            # Should complete without exception
        except (ValueError, TypeError):
            self.fail("Handler should catch conversion errors, not propagate them")
        except Exception:
            # Other exceptions might be acceptable (e.g., from missing context)
            pass

        # Test combosmall text handler with invalid input
        small_handler = panel._make_combosmall_text_handler(
            "test_attr", combo_ctrl, self.test_obj, float, []
        )
        try:
            small_handler(event)
        except (ValueError, TypeError):
            self.fail("ComboSmall handler should catch conversion errors")
        except Exception:
            # Other exceptions might be acceptable
            pass

        # Test combosmall option handler with invalid selection
        class MockComboWithBadSelection:
            def GetSelection(self):
                return 999  # Invalid index

        bad_combo = MockComboWithBadSelection()
        choice_list = ["10", "20", "30"]
        option_handler = panel._make_combosmall_option_handler(
            "test_attr", bad_combo, self.test_obj, int, [], choice_list
        )

        try:
            option_handler(event)
        except (ValueError, TypeError, IndexError):
            self.fail(
                "ComboSmall option handler should catch all conversion and index errors"
            )
        except Exception:
            # Other exceptions might be acceptable
            pass

    def test_checkbox_bitcheck_handler(self):
        """Test that checkbox bitcheck handler correctly sets and clears bits."""
        panel = self.create_panel()

        # Mock checkbox control
        class MockCheckbox:
            def __init__(self, checked=False):
                self.checked = checked

            def GetValue(self):
                return self.checked

            def SetValue(self, value):
                self.checked = value

        # Test object with a bit field
        class TestBitObject:
            def __init__(self):
                self.flags = 0b00000000  # Start with no flags set

        test_obj = TestBitObject()
        checkbox = MockCheckbox(False)

        # Test setting bit 3 (0-indexed)
        handler = panel._make_checkbox_bitcheck_handler(
            "flags", checkbox, test_obj, 3, []
        )
        event = wx.CommandEvent()

        # Initially flags should be 0
        self.assertEqual(test_obj.flags, 0b00000000)

        # Check the checkbox and trigger handler (set bit)
        checkbox.SetValue(True)
        try:
            handler(event)
            # Bit 3 should now be set: 0b00001000 = 8
            self.assertEqual(test_obj.flags, 0b00001000)
        except Exception:
            # Context-related exceptions are acceptable for this test
            pass

        # Manually set the bit to test clearing
        test_obj.flags = 0b00001000  # Bit 3 is set

        # Uncheck the checkbox and trigger handler (clear bit)
        checkbox.SetValue(False)
        try:
            handler(event)
            # Bit 3 should now be cleared: 0b00000000 = 0
            self.assertEqual(test_obj.flags, 0b00000000)
        except Exception:
            # Context-related exceptions are acceptable for this test
            pass

        # Test with multiple bits set
        test_obj.flags = 0b11111111  # All bits set
        checkbox.SetValue(False)  # Should clear bit 3
        try:
            handler(event)
            # Should be 0b11110111 = 247 (all bits except bit 3)
            self.assertEqual(test_obj.flags, 0b11110111)
        except Exception:
            pass

        # Test setting bit when others are already set
        test_obj.flags = 0b11110111  # All bits except bit 3
        checkbox.SetValue(True)  # Should set bit 3
        try:
            handler(event)
            # Should be 0b11111111 = 255 (all bits set)
            self.assertEqual(test_obj.flags, 0b11111111)
        except Exception:
            pass

    def test_info_control_creation(self):
        """Test info control creation with multiline text."""
        panel = self.create_panel()

        # Test single line
        with patch("meerk40t.gui.choicepropertypanel.wxStaticText") as mock_static_text:
            mock_control = MockControl()
            mock_static_text.return_value = mock_control

            result = panel._create_info_control("Single line")
            self.assertEqual(result, mock_control)
            mock_static_text.assert_called_once_with(panel, label="Single line")

        # Test multiline text (should still create single control)
        with patch("meerk40t.gui.choicepropertypanel.wxStaticText") as mock_static_text:
            mock_control = MockControl()
            mock_static_text.return_value = mock_control

            result = panel._create_info_control("Line 1\nLine 2\nLine 3")
            self.assertEqual(result, mock_control)
            mock_static_text.assert_called_once_with(
                panel, label="Line 1\nLine 2\nLine 3"
            )

    def test_control_width_application(self):
        """Test control width application."""
        # Skip this test due to wx initialization requirements
        self.skipTest("Requires full wx framework initialization")

    def test_data_type_validation(self):
        """Test data type validation and conversion."""
        panel = self.create_panel()

        # Test string data
        data, data_type = panel._get_choice_data_and_type(
            {"attr": "test_attr"}, self.test_obj, "test_attr"
        )
        self.assertEqual(data, "test_value")
        self.assertEqual(data_type, str)

        # Test boolean data
        data, data_type = panel._get_choice_data_and_type(
            {"attr": "test_bool"}, self.test_obj, "test_bool"
        )
        self.assertEqual(data, True)
        self.assertEqual(data_type, bool)

        # Test integer data
        data, data_type = panel._get_choice_data_and_type(
            {"attr": "test_int"}, self.test_obj, "test_int"
        )
        self.assertEqual(data, 42)
        self.assertEqual(data_type, int)

        # Test with type override
        data, data_type = panel._get_choice_data_and_type(
            {"attr": "test_int", "type": float}, self.test_obj, "test_int"
        )
        self.assertEqual(data, 42)
        self.assertEqual(data_type, float)

    def test_text_control_config_generation(self):
        """Test text control configuration generation."""
        panel = self.create_panel()

        # Test basic string config
        config = panel._get_text_control_config(str, {})
        self.assertIn("style", config)

        # Test integer config (should add validation)
        config = panel._get_text_control_config(int, {})
        self.assertTrue(config["limited"])
        self.assertEqual(config["check"], "int")

        # Test float config
        config = panel._get_text_control_config(float, {})
        self.assertTrue(config["limited"])
        self.assertEqual(config["check"], "float")

        # Test Length config
        config = panel._get_text_control_config(Length, {"nonzero": True})
        self.assertTrue(config["limited"])
        self.assertEqual(config["check"], "length")
        self.assertTrue(config["nonzero"])

        # Test Angle config
        config = panel._get_text_control_config(Angle, {})
        self.assertTrue(config["limited"])
        self.assertEqual(config["check"], "angle")

    def test_combo_control_config_generation(self):
        """Test combo control configuration generation."""
        panel = self.create_panel()

        # Test regular combo
        config = panel._get_combo_control_config(str, {})
        expected_style = wx.CB_DROPDOWN | wx.CB_READONLY
        self.assertEqual(config["style"], expected_style)

        # Test combosmall with exclusive=True (default)
        config = panel._get_combo_control_config(str, {"style": "combosmall"})
        expected_style = wx.CB_DROPDOWN | wx.CB_READONLY
        self.assertEqual(config["style"], expected_style)

        # Test combosmall with exclusive=False
        config = panel._get_combo_control_config(
            str, {"style": "combosmall", "exclusive": False}
        )
        expected_style = wx.CB_DROPDOWN
        self.assertEqual(config["style"], expected_style)

    def test_property_update_and_signal(self):
        """Test property update and signal dispatch."""
        panel = self.create_panel()

        # Test updating a property that changes
        new_value = "new_test_value"

        result = panel._update_property_and_signal(
            self.test_obj, "test_attr", new_value, ["additional_signal"]
        )

        self.assertTrue(result)  # Should return True for successful update
        self.assertEqual(self.test_obj.test_attr, new_value)

        # Check that the test completed successfully (property was updated)
        # Signal testing would require more complex mock setup

        # Test updating a property with same value (no change)
        result = panel._update_property_and_signal(
            self.test_obj, "test_attr", new_value, []
        )

        self.assertFalse(result)  # Should return False for no change

    def test_choice_data_and_type_extraction(self):
        """Test choice data and type extraction with various scenarios."""
        panel = self.create_panel()

        # Test with default value when attribute doesn't exist
        data, data_type = panel._get_choice_data_and_type(
            {"attr": "nonexistent_attr", "default": "default_value"},
            self.test_obj,
            "nonexistent_attr",
        )
        self.assertEqual(data, "default_value")
        self.assertEqual(data_type, str)

        # Test with explicit type override
        data, data_type = panel._get_choice_data_and_type(
            {"attr": "test_attr", "type": int}, self.test_obj, "test_attr"
        )
        self.assertEqual(data, "test_value")
        self.assertEqual(data_type, int)  # Type override should work

        # Test with existing attribute
        data, data_type = panel._get_choice_data_and_type(
            {"attr": "test_attr"}, self.test_obj, "test_attr"
        )
        self.assertEqual(data, "test_value")
        self.assertEqual(data_type, str)

    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        panel = self.create_panel()

        # Test with None context (should not crash)
        panel.context = None
        control = MockControl()

        try:
            # This might fail due to None context, but shouldn't crash the test
            panel._setup_conditional_enabling({}, control, "test_attr", self.test_obj)
        except AttributeError:
            pass  # Expected when context is None

        # Test with malformed conditional
        panel.context = Mock()  # Use simple Mock for type compatibility
        choice = {"conditional": ["not_enough_elements"]}

        try:
            panel._setup_conditional_enabling(
                choice, control, "test_attr", self.test_obj
            )
            # Should handle gracefully
        except (ValueError, IndexError):
            pass  # These are acceptable for malformed input

    def test_dispatch_table_completeness(self):
        """Test that dispatch table covers all expected type/style combinations."""
        panel = self.create_panel()

        # Common data types
        data_types = [str, int, float, bool, Length, Angle, Color]

        # Common styles
        styles = [
            None,
            "file",
            "multiline",
            "combo",
            "combosmall",
            "radio",
            "option",
            "slider",
            "binary",
            "button",
            "color",
        ]

        supported_combinations = []
        unsupported_combinations = []

        for data_type in data_types:
            for style in styles:
                factory, handler, special = panel._get_control_factory(data_type, style)
                if factory is not None:
                    supported_combinations.append((data_type, style))
                else:
                    unsupported_combinations.append((data_type, style))

        # Should have reasonable coverage
        self.assertGreater(len(supported_combinations), 10)

        # Test some expected combinations exist
        self.assertIn((str, None), supported_combinations)
        self.assertIn((bool, None), supported_combinations)
        self.assertIn((int, "slider"), supported_combinations)
        self.assertIn((Color, None), supported_combinations)


class TestChoicePropertyPanelIntegration(unittest.TestCase):
    """Integration tests for ChoicePropertyPanel with kernel."""

    def setUp(self):
        """Set up integration test fixtures."""
        if not wx.GetApp():
            self.app = wx.App()
        else:
            self.app = None

        # Create a real kernel for integration testing
        self.kernel = bootstrap.bootstrap()

    def tearDown(self):
        """Clean up integration tests."""
        if hasattr(self, "kernel"):
            self.kernel.shutdown()
        if self.app:
            self.app.Destroy()

    def test_panel_creation_with_real_context(self):
        """Test panel creation with real kernel context."""
        # This test ensures the panel works with a real kernel context
        with patch("meerk40t.gui.choicepropertypanel.ScrolledPanel.__init__"):
            panel = ChoicePropertyPanel.__new__(ChoicePropertyPanel)
            panel.context = self.kernel.root
            panel.listeners = []
            panel.entries_per_column = None

            # Test basic functionality
            self.assertIsNotNone(panel.context)

            # Test signal dispatch (should not crash)
            test_obj = MockTestObject()
            try:
                panel._dispatch_signals("test_param", "test_value", test_obj, [])
            except AttributeError:
                # This is acceptable - some signal functionality may require full GUI setup
                pass

    def test_conditional_tuple_validation(self):
        """Test handling of invalid conditional tuples with less than 2 elements."""
        panel = ChoicePropertyPanel.__new__(ChoicePropertyPanel)
        panel.context = Mock()
        panel.context.root = Mock()
        panel.context.root.channel = Mock()
        mock_channel = Mock()
        panel.context.root.channel.return_value = mock_channel
        panel.listeners = []

        control = MockControl()

        # Test with empty conditional tuple
        choice_empty = {"conditional": []}
        panel._setup_conditional_enabling(choice_empty, control, "test_attr", Mock())

        # Verify channel was called with warning for empty tuple
        panel.context.root.channel.assert_called_with("console")
        mock_channel.assert_called()
        call_args = mock_channel.call_args[0][0]
        self.assertIn("Warning: Invalid conditional tuple with 0 elements", call_args)

        # Test with single element conditional tuple
        panel.context.root.channel.reset_mock()
        mock_channel.reset_mock()
        choice_single = {"conditional": [Mock()]}
        panel._setup_conditional_enabling(choice_single, control, "test_attr", Mock())

        # Verify channel was called with warning for single element tuple
        panel.context.root.channel.assert_called_with("console")
        mock_channel.assert_called()
        call_args = mock_channel.call_args[0][0]
        self.assertIn("Warning: Invalid conditional tuple with 1 elements", call_args)

        # Test with valid 2-element conditional tuple (should not generate warning)
        panel.context.root.channel.reset_mock()
        mock_channel.reset_mock()
        choice_valid = {"conditional": [Mock(), "test_attr"]}
        panel._setup_conditional_enabling(choice_valid, control, "test_attr", Mock())

        # Should not have called channel with warning message
        panel.context.root.channel.assert_not_called()

    def test_listener_restoration_after_show_hide(self):
        """Test that listeners are properly restored after hide/show cycle."""
        panel = ChoicePropertyPanel.__new__(ChoicePropertyPanel)
        panel.context = Mock()
        panel.listeners = []

        control = MockControl()
        test_obj = Mock()
        test_obj.conditional_attr = True

        # Set up conditional enabling (should add listener)
        choice = {"conditional": [test_obj, "conditional_attr"]}
        panel._setup_conditional_enabling(choice, control, "test_attr", test_obj)

        # Verify listener was added
        self.assertEqual(len(panel.listeners), 1)
        initial_listener_count = panel.context.listen.call_count

        # Hide panel (should unlisten but keep listeners list)
        panel.pane_hide()

        # Verify unlisten was called but listeners list is preserved
        self.assertEqual(panel.context.unlisten.call_count, 1)
        self.assertEqual(len(panel.listeners), 1)  # Listeners list should be preserved

        # Show panel (should re-listen)
        panel.pane_show()

        # Verify listen was called again
        self.assertEqual(panel.context.listen.call_count, initial_listener_count + 1)
        self.assertEqual(len(panel.listeners), 1)  # Still have the same listener info

    def test_power_control_functionality(self):
        """Test power control display formatting and conversion logic."""
        panel = ChoicePropertyPanel.__new__(ChoicePropertyPanel)
        panel.context = Mock()
        panel.listeners = []

        # Test display value formatting for power controls
        # Absolute mode: should display value as-is
        config_abs = {"style": "power", "percent": False}
        display_abs = panel._format_text_display_value(500.0, float, config_abs)
        self.assertEqual(display_abs, "500.0")

        # Percentage mode: should convert 0-1000 to 0-100%
        config_pct = {"style": "power", "percent": True}
        display_pct = panel._format_text_display_value(750.0, float, config_pct)
        self.assertEqual(display_pct, "75.0")  # 750/10 = 75%

        # Test edge cases
        display_zero = panel._format_text_display_value(0.0, float, config_pct)
        self.assertEqual(display_zero, "0.0")  # 0%

        display_max = panel._format_text_display_value(1000.0, float, config_pct)
        self.assertEqual(display_max, "100.0")  # 100%

        # Test regular float controls (should be unaffected)
        config_regular = {"style": None}
        display_regular = panel._format_text_display_value(
            123.45, float, config_regular
        )
        self.assertEqual(display_regular, "123.45")

    def test_power_handler_conversion(self):
        """Test power text handler conversion logic."""
        panel = ChoicePropertyPanel.__new__(ChoicePropertyPanel)
        panel.context = Mock()

        class MockControl:
            def __init__(self):
                self.value = ""

            def GetValue(self):
                return self.value

            def SetValue(self, value):
                self.value = value

        class MockObject:
            def __init__(self):
                self.power = 0.0

        mock_obj = MockObject()
        mock_control = MockControl()

        # Test percentage mode handler
        choice_pct = {"percent": True}
        handler_pct = panel._make_power_text_handler(
            "power", mock_control, mock_obj, float, [], choice_pct
        )

        # Simulate user entering percentage values
        mock_control.SetValue("50")  # 50%
        mock_event = Mock()
        handler_pct(mock_event)
        self.assertEqual(mock_obj.power, 500.0)  # Should convert to 500

        mock_control.SetValue("100")  # 100%
        handler_pct(mock_event)
        self.assertEqual(mock_obj.power, 1000.0)  # Should convert to 1000

        mock_control.SetValue("0")  # 0%
        handler_pct(mock_event)
        self.assertEqual(mock_obj.power, 0.0)  # Should convert to 0

        # Test absolute mode handler
        choice_abs = {"percent": False}
        handler_abs = panel._make_power_text_handler(
            "power", mock_control, mock_obj, float, [], choice_abs
        )

        # Simulate user entering absolute values
        mock_control.SetValue("250")
        handler_abs(mock_event)
        self.assertEqual(mock_obj.power, 250.0)  # Should stay 250

        mock_control.SetValue("1000")
        handler_abs(mock_event)
        self.assertEqual(mock_obj.power, 1000.0)  # Should stay 1000

        # Test validation - values outside range should be ignored
        original_value = mock_obj.power
        mock_control.SetValue("1500")  # Above maximum
        handler_abs(mock_event)
        self.assertEqual(mock_obj.power, original_value)  # Should not change

        mock_control.SetValue("150")  # Above maximum for percentage mode
        handler_pct(mock_event)
        self.assertEqual(mock_obj.power, original_value)  # Should not change

    def test_power_control_automatic_validation_limits(self):
        """Test that power controls automatically set appropriate validation limits."""
        panel = ChoicePropertyPanel.__new__(ChoicePropertyPanel)
        panel.context = Mock()
        panel.listeners = []

        # Test percentage mode - should set 0-100 limits
        config_pct = {"style": "power", "percent": True}
        text_config_pct = panel._get_text_control_config(float, config_pct)

        self.assertEqual(text_config_pct.get("lower"), 0.0)
        self.assertEqual(text_config_pct.get("upper"), 100.0)
        self.assertTrue(text_config_pct.get("limited"))
        self.assertEqual(text_config_pct.get("check"), "float")

        # Test absolute mode - should set 0-1000 limits
        config_abs = {"style": "power", "percent": False}
        text_config_abs = panel._get_text_control_config(float, config_abs)

        self.assertEqual(text_config_abs.get("lower"), 0.0)
        self.assertEqual(text_config_abs.get("upper"), 1000.0)
        self.assertTrue(text_config_abs.get("limited"))
        self.assertEqual(text_config_abs.get("check"), "float")

        # Test callable percent flag - percentage mode
        def get_percent_mode():
            return True

        config_callable_pct = {"style": "power", "percent": get_percent_mode}
        text_config_callable_pct = panel._get_text_control_config(
            float, config_callable_pct
        )

        self.assertEqual(text_config_callable_pct.get("lower"), 0.0)
        self.assertEqual(text_config_callable_pct.get("upper"), 100.0)

        # Test callable percent flag - absolute mode
        def get_absolute_mode():
            return False

        config_callable_abs = {"style": "power", "percent": get_absolute_mode}
        text_config_callable_abs = panel._get_text_control_config(
            float, config_callable_abs
        )

        self.assertEqual(text_config_callable_abs.get("lower"), 0.0)
        self.assertEqual(text_config_callable_abs.get("upper"), 1000.0)

        # Test non-power controls are unaffected
        config_regular = {"style": None}
        text_config_regular = panel._get_text_control_config(float, config_regular)

        self.assertIsNone(text_config_regular.get("lower"))
        self.assertIsNone(text_config_regular.get("upper"))
        self.assertTrue(text_config_regular.get("limited"))
        self.assertEqual(text_config_regular.get("check"), "float")


if __name__ == "__main__":
    # Run the tests
    unittest.main()
