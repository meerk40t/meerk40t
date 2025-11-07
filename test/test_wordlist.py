import os
import tempfile
import unittest
from datetime import datetime

from meerk40t.core.wordlist import Wordlist


class TestWordlist(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.wordlist = Wordlist("1.0.0-test", directory=tempfile.gettempdir())

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up any test files
        test_file = os.path.join(tempfile.gettempdir(), "wordlist.json")
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_initialization(self):
        """Test Wordlist initialization with default values."""
        # Test that default values are set correctly
        self.assertEqual(self.wordlist.fetch("version"), "1.0.0-test")
        self.assertIsNotNone(self.wordlist.fetch("date"))
        self.assertIsNotNone(self.wordlist.fetch("time"))

        # Test prohibited keys
        self.assertIn("version", self.wordlist.prohibited)
        self.assertIn("date", self.wordlist.prohibited)
        self.assertIn("time", self.wordlist.prohibited)

        # Test that transaction is not open initially
        self.assertFalse(self.wordlist.transaction_open)

    def test_add_and_fetch_basic(self):
        """Test basic add and fetch operations."""
        # Test adding a value
        self.wordlist.add("test_key", "test_value")
        self.assertEqual(self.wordlist.fetch("test_key"), "test_value")

        # Test fetching non-existent key
        self.assertIsNone(self.wordlist.fetch("nonexistent"))

        # Test case insensitivity
        self.wordlist.add("UPPERCASE", "upper_value")
        self.assertEqual(self.wordlist.fetch("uppercase"), "upper_value")

    def test_fetch_value_with_index(self):
        """Test fetch_value with specific indices."""
        # Add multiple values to create a list
        self.wordlist.set_value("test_list", "value1", idx=-1, wtype=1)
        self.wordlist.set_value("test_list", "value2", idx=-1, wtype=1)
        self.wordlist.set_value("test_list", "value3", idx=-1, wtype=1)

        # Test fetching specific indices
        self.assertEqual(self.wordlist.fetch_value("test_list", 2), "value1")
        self.assertEqual(self.wordlist.fetch_value("test_list", 3), "value2")
        self.assertEqual(self.wordlist.fetch_value("test_list", 4), "value3")

        # Test fetching out of bounds
        self.assertIsNone(self.wordlist.fetch_value("test_list", 10))

    def test_set_value_operations(self):
        """Test set_value with different scenarios."""
        # Test setting value at specific index
        self.wordlist.set_value("test", "value1", idx=0, wtype=1)
        self.assertEqual(self.wordlist.fetch_value("test", 2), "value1")

        # Test appending values
        self.wordlist.set_value("test", "value2", idx=-1, wtype=1)
        self.assertEqual(self.wordlist.fetch_value("test", 3), "value2")

        # Test setting at current position (default)
        self.wordlist.set_index("test", 3)
        self.wordlist.set_value("test", "value3")  # Should replace value2
        self.assertEqual(self.wordlist.fetch_value("test", 3), "value3")

    def test_set_index_operations(self):
        """Test set_index with different input types."""
        # Create a test list
        self.wordlist.set_value("test", "val1", idx=-1, wtype=1)
        self.wordlist.set_value("test", "val2", idx=-1, wtype=1)
        self.wordlist.set_value("test", "val3", idx=-1, wtype=1)

        # Test setting index with integer
        self.wordlist.set_index("test", 3)
        self.assertEqual(
            self.wordlist.fetch("test"), "val3"
        )  # External index 1 points to val2, index 2 points to val3

        # Test setting index with string (valid)
        self.wordlist.set_index("test", "2")
        self.assertEqual(self.wordlist.fetch("test"), "val3")  # Index 2 points to val3

        # Test setting index with invalid string (should default to 0)
        self.wordlist.set_index("test", "invalid")
        self.assertEqual(self.wordlist.fetch("test"), "val1")

        # Test relative indexing
        self.wordlist.set_index("test", "+1")
        self.assertEqual(self.wordlist.fetch("test"), "val2")

        self.wordlist.set_index("test", "-1")
        self.assertEqual(self.wordlist.fetch("test"), "val1")

    def test_delete_operations(self):
        """Test delete and delete_value operations."""
        # Add test data
        self.wordlist.add("test_key", "test_value")
        self.assertEqual(self.wordlist.fetch("test_key"), "test_value")

        # Test delete existing key
        self.wordlist.delete("test_key")
        self.assertIsNone(self.wordlist.fetch("test_key"))

        # Test delete non-existent key (should not raise error)
        self.wordlist.delete("nonexistent")

        # Test delete_value
        self.wordlist.set_value("test_list", "val1", idx=-1, wtype=1)
        self.wordlist.set_value("test_list", "val2", idx=-1, wtype=1)
        self.assertEqual(
            self.wordlist.fetch_value("test_list", 2), "val1"
        )  # External index 0
        self.assertEqual(
            self.wordlist.fetch_value("test_list", 3), "val2"
        )  # External index 1

        self.wordlist.delete_value("test_list", 0)  # Delete external index 0 ('val1')
        self.assertEqual(
            self.wordlist.fetch_value("test_list", 2), "val2"
        )  # val2 shifts to index 2

    def test_translate_basic(self):
        """Test basic translate functionality."""
        # Add test data
        self.wordlist.add("name", "John Doe")
        self.wordlist.add("age", "30")

        # Test simple replacement
        result = self.wordlist.translate("Hello {name}, you are {age} years old.")
        self.assertEqual(result, "Hello John Doe, you are 30 years old.")

        # Test case insensitivity - variables are case-insensitive
        result = self.wordlist.translate("Hello {NAME}, you are {AGE} years old.")
        self.assertEqual(
            result, "Hello John Doe, you are 30 years old."
        )  # Case-insensitive replacement

        # Test non-existent key
        result = self.wordlist.translate("Hello {nonexistent}.")
        self.assertEqual(result, "Hello .")

        # Test empty pattern
        result = self.wordlist.translate("")
        self.assertEqual(result, "")

        # Test pattern with no brackets
        result = self.wordlist.translate("No brackets here")
        self.assertEqual(result, "No brackets here")

    def test_translate_with_offsets(self):
        """Test translate with offset specifications."""
        # Create a list with multiple values
        self.wordlist.set_value("items", "apple", idx=-1, wtype=1)
        self.wordlist.set_value("items", "banana", idx=-1, wtype=1)
        self.wordlist.set_value("items", "cherry", idx=-1, wtype=1)

        # Test with offset
        result = self.wordlist.translate("First: {items}, Second: {items#1}")
        self.assertEqual(result, "First: apple, Second: banana")

        # Test with negative offset (out of bounds returns the calculated index)
        self.wordlist.set_index("items", 2)  # Point to 'cherry'
        result = self.wordlist.translate(
            "Current: {items}, Previous: {items#-1}", increment=False
        )
        self.assertEqual(result, "Current: cherry, Previous: banana")

    def test_translate_counter(self):
        """Test translate with counter variables."""
        # Create a counter
        self.wordlist.set_value("counter", "5", wtype=2)  # TYPE_COUNTER

        # Test counter increment
        result = self.wordlist.translate("Count: {counter}")
        self.assertEqual(result, "Count: 5")
        self.assertEqual(
            self.wordlist.fetch("counter"), 6
        )  # Should increment to integer

        # Test counter with offset
        result = self.wordlist.translate("Count with offset: {counter#2}")
        self.assertEqual(result, "Count with offset: 8")

    def test_translate_date_time(self):
        """Test translate with date and time variables."""
        # Test date
        result = self.wordlist.translate("Today is {date}")
        self.assertIsNotNone(result)
        self.assertIn("Today is", result)

        # Test time
        result = self.wordlist.translate("Time is {time}")
        self.assertIsNotNone(result)
        self.assertIn("Time is", result)

        # Test custom date format - default format is %x which gives YY-MM-DD or similar
        result = self.wordlist.translate("Date: {date@%y-%m-%d}")
        self.assertRegex(result, r"Date: \d{2}-\d{2}-\d{2}")  # YY-MM-DD format

        # Test custom time format
        result = self.wordlist.translate("Time: {time@%H:%M}")
        self.assertRegex(result, r"Time: \d{2}:\d{2}")

    def test_translate_increment_control(self):
        """Test translate with increment control."""
        # Create a counter
        self.wordlist.set_value("counter", "10", wtype=2)

        # Test with increment=True (default)
        result1 = self.wordlist.translate("{counter}")
        result2 = self.wordlist.translate("{counter}")
        self.assertEqual(result1, "10")
        self.assertEqual(result2, "11")

        # Test with increment=False
        result3 = self.wordlist.translate("{counter}", increment=False)
        result4 = self.wordlist.translate("{counter}", increment=False)
        self.assertEqual(result3, "12")
        self.assertEqual(result4, "12")  # Should not increment

    def test_data_persistence(self):
        """Test load_data and save_data operations."""
        # Add some test data
        self.wordlist.add("test_key", "test_value")
        self.wordlist.set_value("test_list", "item1", idx=-1, wtype=1)
        self.wordlist.set_value("test_list", "item2", idx=-1, wtype=1)

        # Save data
        test_file = os.path.join(tempfile.gettempdir(), "test_wordlist.json")
        self.wordlist.save_data(test_file)

        # Verify file was created
        self.assertTrue(os.path.exists(test_file))

        # Create new wordlist and load data
        new_wordlist = Wordlist("1.0.0-test", directory=tempfile.gettempdir())
        new_wordlist.load_data(test_file)

        # Verify data was loaded
        self.assertEqual(new_wordlist.fetch("test_key"), "test_value")
        self.assertEqual(new_wordlist.fetch_value("test_list", 2), "item1")
        self.assertEqual(new_wordlist.fetch_value("test_list", 3), "item2")

        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_data_persistence_error_handling(self):
        """Test error handling in data persistence."""
        # Test loading non-existent file
        self.wordlist.load_data("nonexistent_file.json")
        # Should not crash, content should remain unchanged
        self.assertIsNotNone(self.wordlist.content)

        # Test loading invalid JSON
        test_file = os.path.join(tempfile.gettempdir(), "invalid.json")
        with open(test_file, "w") as f:
            f.write("invalid json content")

        self.wordlist.load_data(test_file)
        # Should not crash, content should remain unchanged
        self.assertIsNotNone(self.wordlist.content)

        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_csv_loading(self):
        """Test CSV file loading functionality."""
        # Create a test CSV file
        test_csv = os.path.join(tempfile.gettempdir(), "test.csv")
        with open(test_csv, "w", newline="") as f:
            f.write("Name,Age,City\n")
            f.write("John,25,New York\n")
            f.write("Jane,30,London\n")

        # Load CSV - force header detection for consistent behavior
        row_count, col_count, headers = self.wordlist.load_csv_file(
            test_csv, force_header=True
        )

        # Verify results - 2 data rows
        self.assertEqual(row_count, 2)  # 2 data rows
        self.assertEqual(col_count, 3)
        self.assertEqual(headers, ["name", "age", "city"])

        # Verify data was loaded
        self.assertEqual(self.wordlist.fetch("name"), "John")
        self.assertEqual(self.wordlist.fetch("age"), "25")
        self.assertEqual(self.wordlist.fetch("city"), "New York")

        # Test moving to next values
        self.wordlist.move_all_indices(1)
        self.assertEqual(self.wordlist.fetch("name"), "Jane")
        self.assertEqual(self.wordlist.fetch("age"), "30")
        self.assertEqual(self.wordlist.fetch("city"), "London")

        # Clean up
        if os.path.exists(test_csv):
            os.remove(test_csv)

    def test_csv_loading_no_header(self):
        """Test CSV loading without header."""
        # Create a test CSV file without header
        test_csv = os.path.join(tempfile.gettempdir(), "test_no_header.csv")
        with open(test_csv, "w", newline="") as f:
            f.write("John,25,New York\n")
            f.write("Jane,30,London\n")

        # Load CSV with force_header=False
        row_count, col_count, headers = self.wordlist.load_csv_file(
            test_csv, force_header=False
        )

        # Verify results
        self.assertEqual(row_count, 2)
        self.assertEqual(col_count, 3)
        self.assertEqual(headers, ["column_1", "column_2", "column_3"])

        # Verify data was loaded with default column names
        self.assertEqual(self.wordlist.fetch("column_1"), "John")
        self.assertEqual(self.wordlist.fetch("column_2"), "25")
        self.assertEqual(self.wordlist.fetch("column_3"), "New York")

        # Clean up
        if os.path.exists(test_csv):
            os.remove(test_csv)

    def test_transaction_operations(self):
        """Test transaction begin, commit, and rollback."""
        # Add initial data
        self.wordlist.add("original", "value1")

        # Begin transaction
        self.wordlist.begin_transaction()
        self.assertTrue(self.wordlist.transaction_open)

        # Modify data
        self.wordlist.add("new_key", "new_value")
        self.wordlist.set_value("original", "modified", idx=0)

        # Verify changes are visible
        self.assertEqual(self.wordlist.fetch("new_key"), "new_value")
        self.assertEqual(self.wordlist.fetch("original"), "modified")

        # Rollback transaction
        self.wordlist.rollback_transaction()
        self.assertFalse(self.wordlist.transaction_open)

        # Verify rollback worked
        self.assertIsNone(self.wordlist.fetch("new_key"))
        self.assertEqual(self.wordlist.fetch("original"), "value1")

        # Test commit
        self.wordlist.begin_transaction()
        self.wordlist.add("committed", "value")
        self.wordlist.commit_transaction()
        self.assertFalse(self.wordlist.transaction_open)
        self.assertEqual(self.wordlist.fetch("committed"), "value")

    def test_stack_operations(self):
        """Test push and pop operations."""
        # Add initial data
        self.wordlist.add("key1", "value1")
        self.wordlist.add("key2", "value2")

        # Push current state
        self.wordlist.push()

        # Modify data
        self.wordlist.add("key3", "value3")
        self.wordlist.set_value("key1", "modified", idx=0)

        # Verify modifications
        self.assertEqual(self.wordlist.fetch("key3"), "value3")
        self.assertEqual(self.wordlist.fetch("key1"), "modified")

        # Pop to restore
        self.wordlist.pop()

        # Verify restoration
        self.assertIsNone(self.wordlist.fetch("key3"))
        self.assertEqual(self.wordlist.fetch("key1"), "value1")
        self.assertEqual(self.wordlist.fetch("key2"), "value2")

    def test_reset_operations(self):
        """Test reset functionality."""
        # Create test data with specific indices
        self.wordlist.set_value("test1", "val1", idx=-1, wtype=1)
        self.wordlist.set_value("test1", "val2", idx=-1, wtype=1)
        self.wordlist.set_value("test2", "val3", idx=-1, wtype=1)

        # Set indices
        self.wordlist.set_index("test1", 3)  # Point to val2
        self.wordlist.set_index("test2", 2)  # Point to val3

        # Verify current positions
        self.assertEqual(self.wordlist.fetch("test1"), "val2")
        self.assertEqual(self.wordlist.fetch("test2"), "val3")

        # Reset specific key
        self.wordlist.reset("test1")
        self.assertEqual(self.wordlist.fetch("test1"), "val1")  # Back to first value
        self.assertEqual(self.wordlist.fetch("test2"), "val3")  # Unchanged

        # Reset all
        self.wordlist.reset()
        self.assertEqual(self.wordlist.fetch("test1"), "val1")
        self.assertEqual(self.wordlist.fetch("test2"), "val3")  # Still at first value

    def test_move_all_indices(self):
        """Test moving all indices by a delta."""
        # Create test data
        self.wordlist.set_value("list1", "a", idx=-1, wtype=1)
        self.wordlist.set_value("list1", "b", idx=-1, wtype=1)
        self.wordlist.set_value("list1", "c", idx=-1, wtype=1)

        self.wordlist.set_value("list2", "x", idx=-1, wtype=1)
        self.wordlist.set_value("list2", "y", idx=-1, wtype=1)

        # Set initial positions
        self.wordlist.set_index("list1", 0)  # Point to 'a'
        self.wordlist.set_index("list2", 0)  # Point to 'x'

        # Move indices by +1
        self.wordlist.move_all_indices(1)
        self.assertEqual(self.wordlist.fetch("list1"), "b")
        self.assertEqual(self.wordlist.fetch("list2"), "y")

        # Move indices by -1
        self.wordlist.move_all_indices(-1)
        self.assertEqual(self.wordlist.fetch("list1"), "a")
        self.assertEqual(self.wordlist.fetch("list2"), "x")

    def test_rename_key(self):
        """Test renaming keys."""
        # Add test data
        self.wordlist.add("old_key", "test_value")
        self.assertEqual(self.wordlist.fetch("old_key"), "test_value")
        self.assertIsNone(self.wordlist.fetch("new_key"))

        # Rename key
        result = self.wordlist.rename_key("old_key", "new_key")
        self.assertTrue(result)
        self.assertIsNone(self.wordlist.fetch("old_key"))
        self.assertEqual(self.wordlist.fetch("new_key"), "test_value")

        # Try to rename prohibited key
        result = self.wordlist.rename_key("version", "new_version")
        self.assertFalse(result)

        # Try to rename to existing key
        self.wordlist.add("existing", "value")
        result = self.wordlist.rename_key("new_key", "existing")
        self.assertFalse(result)

        # Try to rename non-existent key
        result = self.wordlist.rename_key("nonexistent", "new_name")
        self.assertFalse(result)

    def test_get_variable_list(self):
        """Test getting variable list."""
        # Add test data
        self.wordlist.add("name", "John")
        self.wordlist.add("age", "25")

        # Get variable list
        variables = self.wordlist.get_variable_list()

        # Should contain both variables with their values
        self.assertIn("name (John)", variables)
        self.assertIn("age (25)", variables)

        # Should also contain prohibited variables (this is the actual behavior)
        self.assertIn("version (1.0.0-test)", variables)
        self.assertIn(
            "date", [v.split(" ")[0] for v in variables]
        )  # date with its formatted value

    def test_date_time_formatting(self):
        """Test date and time formatting functions."""
        # Test default date format
        date_str = self.wordlist.wordlist_datestr()
        self.assertIsInstance(date_str, str)
        self.assertNotEqual(date_str, "")

        # Test custom date format
        custom_date = self.wordlist.wordlist_datestr("%Y-%m-%d")
        self.assertRegex(custom_date, r"\d{4}-\d{2}-\d{2}")

        # Test invalid format (should return "invalid")
        invalid_date = self.wordlist.wordlist_datestr("%invalid")
        self.assertEqual(invalid_date, "invalid")

        # Test default time format
        time_str = self.wordlist.wordlist_timestr()
        self.assertIsInstance(time_str, str)
        self.assertNotEqual(time_str, "")

        # Test custom time format
        custom_time = self.wordlist.wordlist_timestr("%H:%M:%S")
        self.assertRegex(custom_time, r"\d{2}:\d{2}:\d{2}")

        # Test invalid time format
        invalid_time = self.wordlist.wordlist_timestr("%invalid")
        self.assertEqual(invalid_time, "invalid")

    def test_wordlist_delta(self):
        """Test wordlist_delta functionality."""
        # Create test data
        self.wordlist.set_value("items", "first", idx=-1, wtype=1)
        self.wordlist.set_value("items", "second", idx=-1, wtype=1)
        self.wordlist.set_value("items", "third", idx=-1, wtype=1)

        # Test positive delta
        result = self.wordlist.wordlist_delta("{items#+1}", 1)
        self.assertEqual(result, "{items#+2}")

        # Test negative delta
        result = self.wordlist.wordlist_delta("{items#-2}", -1)
        self.assertEqual(result, "{items#-3}")

        # Test delta that results in zero
        result = self.wordlist.wordlist_delta("{items#+1}", -1)
        self.assertEqual(result, "{items}")

        # Test with multiple patterns
        text = "Item: {items#+1}, Next: {items#+2}"
        result = self.wordlist.wordlist_delta(text, 1)
        self.assertEqual(
            result, "Item: {items#+3}, Next: {items#+3}"
        )  # Current behavior due to replacement order

    def test_empty_csv(self):
        """Test empty_csv functionality."""
        # Add some CSV data
        self.wordlist.set_value("csv_field1", "value1", wtype=1)
        self.wordlist.set_value("csv_field2", "value2", wtype=1)
        self.wordlist.set_value("regular_field", "regular", wtype=0)

        # Verify CSV fields exist
        self.assertIsNotNone(self.wordlist.fetch("csv_field1"))
        self.assertIsNotNone(self.wordlist.fetch("csv_field2"))
        self.assertIsNotNone(self.wordlist.fetch("regular_field"))

        # Empty CSV data
        self.wordlist.empty_csv()

        # CSV fields should be gone, regular field should remain
        self.assertIsNone(self.wordlist.fetch("csv_field1"))
        self.assertIsNone(self.wordlist.fetch("csv_field2"))
        self.assertIsNotNone(self.wordlist.fetch("regular_field"))

    def test_prohibited_keys(self):
        """Test that prohibited keys cannot be modified."""
        # Try to add prohibited key
        self.wordlist.add("version", "modified")
        self.assertEqual(
            self.wordlist.fetch("version"), "1.0.0-test"
        )  # Should remain unchanged

        # Try to set prohibited key
        self.wordlist.set_value("date", "modified_date", idx=0)
        self.assertNotEqual(
            self.wordlist.fetch("date"), "modified_date"
        )  # Should remain unchanged

    def test_edge_cases(self):
        """Test various edge cases."""
        # Test with None values
        result = self.wordlist.translate(None)
        self.assertEqual(result, "")

        # Test with numeric values
        self.wordlist.add("number", 42)
        result = self.wordlist.translate("Number: {number}")
        self.assertEqual(result, "Number: 42")

        # Test with boolean values
        self.wordlist.add("boolean", True)
        result = self.wordlist.translate("Boolean: {boolean}")
        self.assertEqual(result, "Boolean: True")

        # Test empty brackets (not processed by regex)
        result = self.wordlist.translate("Empty: {}")
        self.assertEqual(result, "Empty: {}")

        # Test malformed brackets (no closing brace)
        result = self.wordlist.translate("Malformed: {unclosed")
        self.assertEqual(result, "Malformed: {unclosed")


if __name__ == "__main__":
    unittest.main()
