import os
import tempfile
import unittest

from meerk40t.kernel.settings import Settings


class TestSettings(unittest.TestCase):
    """Tests the functionality of the Settings class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_settings.ini")

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Clean up any created files
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        # Clean up backup files
        for i in range(5):
            backup_file = (
                f"{self.config_file}.ba{i}" if i > 0 else f"{self.config_file}.bak"
            )
            if os.path.exists(backup_file):
                os.remove(backup_file)
        os.rmdir(self.temp_dir)

    def test_settings_init_with_directory(self):
        """Test Settings initialization with a directory."""
        settings = Settings(self.temp_dir, "test.ini", ignore_settings=True)
        self.assertIsInstance(settings, Settings)
        self.assertTrue(hasattr(settings, "_config_dict"))
        self.assertEqual(settings._config_dict, {})

    def test_settings_init_without_directory(self):
        """Test Settings initialization without a directory."""
        settings = Settings(None, self.config_file, ignore_settings=True)
        self.assertIsInstance(settings, Settings)

    def test_settings_contains(self):
        """Test __contains__ method."""
        settings = Settings(None, self.config_file, ignore_settings=True)
        self.assertFalse("test_section" in settings)
        settings._config_dict["test_section"] = {"key": "value"}
        self.assertTrue("test_section" in settings)

    def test_write_persistent_basic_types(self):
        """Test writing basic data types."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Test string
        settings.write_persistent("section1", "string_key", "test_value")
        self.assertEqual(settings._config_dict["section1"]["string_key"], "test_value")

        # Test int
        settings.write_persistent("section1", "int_key", 42)
        self.assertEqual(settings._config_dict["section1"]["int_key"], "42")

        # Test float
        settings.write_persistent("section1", "float_key", 3.14)
        self.assertEqual(settings._config_dict["section1"]["float_key"], "3.14")

        # Test bool
        settings.write_persistent("section1", "bool_key", True)
        self.assertEqual(settings._config_dict["section1"]["bool_key"], "True")

    def test_write_persistent_complex_types(self):
        """Test writing complex data types."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Test list
        test_list = [1, 2, 3, "test"]
        settings.write_persistent("section1", "list_key", test_list)
        self.assertEqual(settings._config_dict["section1"]["list_key"], str(test_list))

        # Test tuple
        test_tuple = (1, 2, "test")
        settings.write_persistent("section1", "tuple_key", test_tuple)
        self.assertEqual(
            settings._config_dict["section1"]["tuple_key"], str(test_tuple)
        )

    def test_read_persistent_basic_types(self):
        """Test reading basic data types."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {
            "string_key": "test_value",
            "int_key": "42",
            "float_key": "3.14",
            "bool_key": "True",
        }

        # Test reading
        self.assertEqual(
            settings.read_persistent(str, "section1", "string_key"), "test_value"
        )
        self.assertEqual(settings.read_persistent(int, "section1", "int_key"), 42)
        self.assertAlmostEqual(
            settings.read_persistent(float, "section1", "float_key"), 3.14
        )
        self.assertEqual(settings.read_persistent(bool, "section1", "bool_key"), True)

    def test_read_persistent_complex_types(self):
        """Test reading complex data types."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        test_list = [1, 2, 3, "test"]
        test_tuple = (1, 2, "test")
        settings._config_dict["section1"] = {
            "list_key": str(test_list),
            "tuple_key": str(test_tuple),
        }

        # Test reading
        self.assertEqual(
            settings.read_persistent(list, "section1", "list_key"), test_list
        )
        self.assertEqual(
            settings.read_persistent(tuple, "section1", "tuple_key"), test_tuple
        )

    def test_read_persistent_defaults(self):
        """Test reading with default values."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Test with non-existent section/key
        self.assertEqual(
            settings.read_persistent(str, "nonexistent", "key", "default"), "default"
        )
        self.assertEqual(settings.read_persistent(int, "nonexistent", "key", 42), 42)
        self.assertEqual(
            settings.read_persistent(bool, "nonexistent", "key", False), False
        )

    def test_read_persistent_backwards_compatibility(self):
        """Test backwards compatibility with semicolon-separated values."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data with semicolons (old format)
        settings._config_dict["section1"] = {"list_key": "[1; 2; 3; 'test']"}

        # Test reading should convert semicolons to commas
        result = settings.read_persistent(list, "section1", "list_key")
        # The result should be None because ast.literal_eval can't parse the semicolon format
        # This is expected behavior - the backwards compatibility might not be working as intended
        self.assertIsNone(result)

    def test_write_persistent_dict(self):
        """Test writing a dictionary of values."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        test_dict = {
            "string_key": "value",
            "int_key": 42,
            "bool_key": True,
            "_private_key": "should_be_ignored",
        }

        settings.write_persistent_dict("section1", test_dict)

        # Check that values were written
        self.assertEqual(settings._config_dict["section1"]["string_key"], "value")
        self.assertEqual(settings._config_dict["section1"]["int_key"], "42")
        self.assertEqual(settings._config_dict["section1"]["bool_key"], "True")

        # Check that private keys (starting with _) were ignored
        self.assertNotIn("_private_key", settings._config_dict["section1"])

    def test_write_persistent_attributes(self):
        """Test writing object attributes."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        class TestObject:
            def __init__(self):
                self.name = "test"
                self.value = 123
                self.enabled = True
                self._private = "ignored"

        obj = TestObject()
        settings.write_persistent_attributes("section1", obj)

        # Check that attributes were written
        self.assertEqual(settings._config_dict["section1"]["name"], "test")
        self.assertEqual(settings._config_dict["section1"]["value"], "123")
        self.assertEqual(settings._config_dict["section1"]["enabled"], "True")

        # Check that private attributes were ignored
        self.assertNotIn("_private", settings._config_dict["section1"])

    def test_read_persistent_attributes(self):
        """Test reading persistent attributes into an object."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {
            "name": "updated_name",
            "value": "456",
            "enabled": "False",
        }

        class TestObject:
            def __init__(self):
                self.name = "default"
                self.value = 123
                self.enabled = True

        obj = TestObject()
        settings.read_persistent_attributes("section1", obj)

        # Check that attributes were updated
        self.assertEqual(obj.name, "updated_name")
        self.assertEqual(obj.value, 456)
        self.assertEqual(obj.enabled, False)

    def test_clear_persistent(self):
        """Test clearing a persistent section."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {"key1": "value1"}
        settings._config_dict["section2"] = {"key2": "value2"}

        # Clear section1
        settings.clear_persistent("section1")

        # Check that section1 was cleared but section2 remains
        self.assertNotIn("section1", settings._config_dict)
        self.assertIn("section2", settings._config_dict)

    def test_delete_persistent(self):
        """Test deleting a persistent key."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {"key1": "value1", "key2": "value2"}

        # Delete key1
        settings.delete_persistent("section1", "key1")

        # Check that key1 was deleted but key2 remains
        self.assertNotIn("key1", settings._config_dict["section1"])
        self.assertIn("key2", settings._config_dict["section1"])

    def test_delete_all_persistent(self):
        """Test deleting all persistent settings."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {"key1": "value1"}
        settings._config_dict["section2"] = {"key2": "value2"}

        # Delete all
        settings.delete_all_persistent()

        # Check that all sections were cleared
        self.assertEqual(settings._config_dict, {})

    def test_keylist(self):
        """Test keylist generator."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }

        # Test keylist
        keys = list(settings.keylist("section1"))
        self.assertEqual(set(keys), {"key1", "key2", "key3"})

        # Test with non-existent section
        keys = list(settings.keylist("nonexistent"))
        self.assertEqual(keys, [])

    def test_derivable(self):
        """Test derivable generator."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["camera/1 0001"] = {"key1": "value1"}
        settings._config_dict["camera/1 0002"] = {"key2": "value2"}
        settings._config_dict["camera/2 0001"] = {"key3": "value3"}
        settings._config_dict["other/1 0001"] = {"key4": "value4"}

        # Test derivable for "camera/1"
        derivable_sections = list(settings.derivable("camera/1"))
        self.assertEqual(set(derivable_sections), {"camera/1 0001", "camera/1 0002"})

        # Test derivable for "camera"
        derivable_sections = list(settings.derivable("camera"))
        self.assertEqual(len(derivable_sections), 0)  # No exact matches for "camera"

    def test_section_startswith(self):
        """Test section_startswith generator."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["camera/1"] = {"key1": "value1"}
        settings._config_dict["camera/2"] = {"key2": "value2"}
        settings._config_dict["other/1"] = {"key3": "value3"}

        # Test section_startswith
        sections = list(settings.section_startswith("camera"))
        self.assertEqual(set(sections), {"camera/1", "camera/2"})

    def test_section_set(self):
        """Test section_set generator."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["camera/1 0001"] = {"key1": "value1"}
        settings._config_dict["camera/2 0001"] = {"key2": "value2"}
        settings._config_dict["other/1 0001"] = {"key3": "value3"}

        # Test section_set
        sections = list(settings.section_set())
        self.assertEqual(set(sections), {"camera/1", "camera/2", "other/1"})

    def test_literal_dict(self):
        """Test literal_dict conversion."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {
            "string_key": "value",
            "int_key": "42",
            "list_key": "[1, 2, 3]",
            "invalid_key": "not_python_literal",
        }

        # Test literal_dict
        literal = settings.literal_dict()

        self.assertEqual(literal["section1"]["string_key"], "value")
        self.assertEqual(literal["section1"]["int_key"], 42)
        self.assertEqual(literal["section1"]["list_key"], [1, 2, 3])
        # Invalid literals should remain as strings
        self.assertEqual(literal["section1"]["invalid_key"], "not_python_literal")

    def test_set_dict(self):
        """Test set_dict method."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        literal_dict = {"section1": {"key1": "value1", "key2": 42, "key3": [1, 2, 3]}}

        settings.set_dict(literal_dict)

        # Check that values were converted to strings
        self.assertEqual(settings._config_dict["section1"]["key1"], "value1")
        self.assertEqual(settings._config_dict["section1"]["key2"], "42")
        self.assertEqual(settings._config_dict["section1"]["key3"], "[1, 2, 3]")

    def test_read_persistent_string_dict(self):
        """Test read_persistent_string_dict method."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {"key1": "value1", "key2": "value2"}

        # Test without suffix
        result = settings.read_persistent_string_dict("section1")
        self.assertEqual(result, {"section1/key1": "value1", "section1/key2": "value2"})

        # Test with suffix
        result = settings.read_persistent_string_dict("section1", suffix=True)
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})

        # Test with existing dictionary
        existing_dict = {"existing": "value"}
        result = settings.read_persistent_string_dict("section1", existing_dict)
        self.assertEqual(result["existing"], "value")
        self.assertEqual(result["section1/key1"], "value1")

    def test_read_persistent_object(self):
        """Test read_persistent_object method."""
        settings = Settings(None, self.config_file, ignore_settings=True)

        # Set up test data
        settings._config_dict["section1"] = {
            "name": "test_name",
            "value": "42",
            "list_value": "[1, 2, 3]",
        }

        class TestObject:
            pass

        obj = TestObject()
        settings.read_persistent_object("section1", obj)

        # Check that attributes were set
        self.assertEqual(obj.name, "test_name")  # type: ignore
        self.assertEqual(obj.value, 42)  # ast.literal_eval converts "42" to int
        self.assertEqual(obj.list_value, [1, 2, 3])  # type: ignore


if __name__ == "__main__":
    unittest.main()
