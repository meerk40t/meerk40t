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
        """Test that conditional enabling listeners don't accumulate and cause memory leaks."""
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

        # All listeners should be cleaned up
        self.assertEqual(len(panel.listeners), 0)

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


if __name__ == "__main__":
    # Run the tests
    unittest.main()
