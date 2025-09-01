"""
Wordlist Module

This module provides the Wordlist class, which manages dynamic text variables and templates
for MeerK40t. It supports various data types including static text, CSV-imported data,
and auto-incrementing counters.

The Wordlist class enables template-based text substitution with features like:
- Variable storage and retrieval with case-insensitive keys
- Template translation with bracketed patterns like {key} or {key#offset}
- Custom date/time formatting with {date@%Y-%m-%d} or {time@%H:%M}
- CSV file loading with automatic header detection
- Transaction support for atomic operations
- Stack operations for temporary state management
- Auto-incrementing counters for sequential numbering

Example usage:
    >>> wl = Wordlist("1.0.0")
    >>> wl.add("name", "John Doe")
    >>> wl.translate("Hello {name}!")
    'Hello John Doe!'

    >>> wl.translate("Today is {date@%Y-%m-%d}")
    'Today is 2025-09-01'
"""

import csv
import json
import os
import re
from copy import copy
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from ..extra.encode_detect import EncodingDetectFile

# Type constants
TYPE_INDEX = 0
POSITION_INDEX = 1
DATA_START_INDEX = 2

TYPE_STATIC = 0
TYPE_CSV = 1
TYPE_COUNTER = 2


class Wordlist:
    """
    A comprehensive wordlist management system for dynamic text variables and templates.

    The Wordlist class provides a flexible system for storing and retrieving text variables
    with support for different data types, template substitution, and advanced features
    like transactions and stack operations.

    Attributes:
        content (Dict[str, List]): Dictionary storing all wordlist entries
        prohibited (property): Read-only property returning system keys that cannot be modified
        _initial_system_keys (Tuple[str, ...]): Internal storage of initial system variable names
        _stack (List[Dict]): Stack for push/pop operations
        transaction_open (bool): Whether a transaction is currently active
        content_backup (Dict): Backup of content for transaction rollback

    Data Structure:
        Each entry in self.content is a list with the following structure:
        - Index 0: Type (0=static, 1=CSV, 2=counter)
        - Index 1: Current position/index for iteration
        - Index 2+: Data values

    Template Syntax:
        - {key}: Basic variable substitution
        - {key#offset}: Variable with numeric offset (e.g., {items#1} for next item)
        - {date@format}: Custom date formatting (e.g., {date@%Y-%m-%d})
        - {time@format}: Custom time formatting (e.g., {time@%H:%M})

    Example:
        >>> wl = Wordlist("1.0.0")
        >>> wl.add("greeting", "Hello")
        >>> wl.add("name", "World")
        >>> wl.translate("{greeting} {name}!")
        'Hello World!'
    """

    # Constants for wordlist array indices
    TYPE_INDEX = 0
    POSITION_INDEX = 1
    DATA_START_INDEX = 2

    # Constants for wordlist types
    TYPE_STATIC = 0
    TYPE_CSV = 1
    TYPE_COUNTER = 2

    def __init__(self, versionstr: str, directory: Optional[str] = None) -> None:
        """
        Initialize a new Wordlist instance.

        Args:
            versionstr (str): Version string for the wordlist
            directory (Optional[str]): Directory for persistent storage.
                                     Defaults to current working directory.

        The constructor sets up default system variables and loads any existing
        persistent data from the wordlist.json file.
        """
        # The content-dictionary contains an array per entry
        # index 0 indicates the type:
        #   0 (static) text entry
        #   1 text entry array coming from a csv file
        #   2 is a numeric counter
        # index 1 indicates the position of the current array (always 2 for type 0 and 2)
        # index 2 and onwards contain the actual data
        self.content: Dict[str, List] = {
            "version": [TYPE_STATIC, 2, versionstr],
            "date": [TYPE_STATIC, 2, self.wordlist_datestr()],
            "time": [TYPE_STATIC, 2, self.wordlist_timestr()],
            "op_device": [TYPE_STATIC, 2, "<device>"],
            "op_speed": [TYPE_STATIC, 2, "<speed>"],
            "op_power": [TYPE_STATIC, 2, "<power>"],
            "op_passes": [TYPE_STATIC, 2, "<passes>"],
            "op_dpi": [TYPE_STATIC, 2, "<dpi>"],
        }
        # Store the initial system keys to derive prohibited keys dynamically
        self._initial_system_keys: Tuple[str, ...] = tuple(self.content.keys())
        self._stack: List[Dict[str, List]] = []
        self.transaction_open: bool = False
        self.content_backup: Dict[str, List] = {}
        if directory is None:
            directory = os.getcwd()
        self.default_filename: str = os.path.join(directory, "wordlist.json")
        self.load_data(self.default_filename)

    @property
    def prohibited(self) -> Tuple[str, ...]:
        """
        Get the list of prohibited (system) keys that cannot be modified by users.

        These are the initial system variables that are set up during initialization
        and should not be altered by user operations.

        Returns:
            Tuple[str, ...]: A tuple of prohibited key names
        """
        return self._initial_system_keys

    def add(self, key: str, value: str, wtype: Optional[int] = None) -> None:
        """
        Add a value to a wordlist entry (alias for add_value).

        This is a convenience method that calls add_value() with the same parameters.

        Args:
            key (str): The key to add the value to (case-insensitive)
            value (str): The value to add
            wtype (Optional[int]): The type of wordlist entry to create if it doesn't exist.
                                 Defaults to TYPE_STATIC (0).

        Note:
            If the key doesn't exist, a new entry is created with the specified type.
        """
        self.add_value(key, value, wtype)

    def fetch(self, key: str) -> Optional[str]:
        """
        Fetch the current value for a wordlist key (alias for fetch_value with None index).

        Args:
            key (str): The key to fetch the value for (case-insensitive)

        Returns:
            Optional[str]: The current value for the key, or None if the key doesn't exist

        Note:
            This method uses the current position index for the key.
        """
        return self.fetch_value(key, None)

    def fetch_value(self, skey: str, idx: Optional[int]) -> Optional[str]:
        """
        Fetch a value from a wordlist entry at the specified index.

        Args:
            skey (str): The key to fetch from (case-insensitive)
            idx (Optional[int]): The index to fetch from. If None, uses the current position.

        Returns:
            Optional[str]: The value at the specified index, or None if not found

        Note:
            Special handling for "date" and "time" keys which return formatted current date/time.
            Index bounds are automatically adjusted to stay within valid ranges.
        """
        skey = skey.lower()
        result = None
        try:
            wordlist = self.content[skey]
        except KeyError:
            return None
        if skey == "date":
            return self.wordlist_datestr(None)
        elif skey == "time":
            return self.wordlist_timestr(None)
        # print (f"Retrieve {wordlist} for {skey}")
        if idx is None:  # Default
            idx = wordlist[POSITION_INDEX]

        if idx is not None and 0 <= idx < len(wordlist):
            # Handle out of bounds for data indices
            if idx < self.DATA_START_INDEX:
                # Wrap from the end for negative indices
                diff = self.DATA_START_INDEX - idx
                idx = len(wordlist) - 1 - diff
                if idx < self.DATA_START_INDEX:
                    idx = self.DATA_START_INDEX
            try:
                result = wordlist[idx]
            except IndexError:
                result = None
        return result

    def add_value(self, skey: str, value: str, wtype: Optional[int] = None) -> None:
        """
        Add a value to a wordlist entry, creating the entry if it doesn't exist.

        Args:
            skey (str): The key to add the value to (case-insensitive)
            value (str): The value to add
            wtype (Optional[int]): The type of wordlist entry to create if it doesn't exist.
                                 Defaults to TYPE_STATIC (0). Can be TYPE_STATIC, TYPE_CSV, or TYPE_COUNTER.

        Note:
            If the key doesn't exist, a new entry is created with the specified type.
            For existing entries, the value is appended to the data array.
        """
        skey = skey.lower()
        if skey not in self.content:
            if wtype is None:
                wtype = TYPE_STATIC
            self.content[skey] = [
                wtype,
                2,
            ]  # incomplete, as it will be appended right after this
        self.content[skey].append(value)

    def delete_value(self, skey: str, idx: int) -> None:
        """
        Delete a value from a wordlist entry at the specified index.

        Args:
            skey (str): The key of the wordlist entry (case-insensitive)
            idx (int): The zero-based index of the value to delete

        Note:
            The index is zero-based from the start of the data array (after type and position indices).
            No operation is performed if the key doesn't exist or the index is invalid.
        """
        skey = skey.lower()
        if skey not in self.content:
            return
        if idx is None or idx < 0:
            return

        # Zerobased outside + 2 inside
        idx += 2
        if idx >= len(self.content[skey]):
            return
        self.content[skey].pop(idx)

    def move_all_indices(self, delta: int) -> None:
        """
        Move all wordlist indices by the specified delta value.

        This affects the current position for static and CSV type wordlists,
        and increments counter values for counter type wordlists.

        Args:
            delta (int): The amount to move indices. Positive values move forward,
                        negative values move backward.

        Note:
            Prohibited keys (system variables) are not affected.
            Counter values are clamped to a minimum of 0.
        """
        for wkey in self.content:
            wordlist = self.content[wkey]
            if wkey in self.prohibited:
                continue
            if wordlist[TYPE_INDEX] in (0, 1):  # Text or csv
                last_index = len(wordlist) - 1
                # Zero-based outside, +2 inside
                newidx = min(wordlist[POSITION_INDEX] + delta, last_index)
                newidx = max(newidx, 2)
                wordlist[POSITION_INDEX] = newidx
            elif wordlist[TYPE_INDEX] == TYPE_COUNTER:  # Counter-type
                value = wordlist[DATA_START_INDEX]
                try:
                    value = int(value) + delta
                except ValueError:
                    value = 0
                value = max(value, 0)
                wordlist[DATA_START_INDEX] = value

    def set_value(
        self,
        skey: str,
        value: str,
        idx: Optional[int] = None,
        wtype: Optional[int] = None,
    ) -> None:
        """
        Set a value in a wordlist entry at the specified index.

        Args:
            skey (str): The key of the wordlist entry (case-insensitive)
            value (str): The value to set
            idx (Optional[int]): The index where to set the value.
                               - None: Use current position
                               - Negative: Append to the end
                               - Positive: Set at specific zero-based index
            wtype (Optional[int]): The type of wordlist entry to create if it doesn't exist.
                                 Defaults to TYPE_STATIC (0).

        Note:
            If the key doesn't exist, a new entry is created with the specified type.
            Index is zero-based from the start of the data array.
        """
        # Special treatment:
        # Index = None - use current
        # Index < 0 append
        skey = skey.lower()
        if skey not in self.content:
            # hasn't been there, so establish it
            if wtype is None:
                wtype = TYPE_STATIC
            self.content[skey] = [wtype, 2, value]
        else:
            if idx is None:
                # use current position
                idx = self.content[skey][1]
                if idx is not None:
                    try:
                        idx = int(idx)
                    except ValueError:
                        idx = 0
                else:
                    idx = 0
            elif idx < 0:
                # append
                self.content[skey].append(value)
            else:  # Zerobased outside + 2 inside
                idx += 2

            if idx >= len(self.content[skey]):
                idx = len(self.content[skey]) - 1
            self.content[skey][idx] = value

    def set_index(
        self, skey: str, idx: Union[str, int], wtype: Optional[int] = None
    ) -> None:
        """
        Set the current index/position for one or more wordlist entries.

        Args:
            skey (str): The key(s) to set the index for. Use "@all" to set for all CSV entries.
                        Multiple keys can be separated by commas.
            idx (Union[str, int]): The index to set. Can be an integer or a string with relative
                                 modifiers (+ or - prefix for relative positioning).
            wtype (Optional[int]): Not used in this method, kept for compatibility.

        Note:
            Only affects static and CSV type wordlists. Counter types are not affected.
            Prohibited keys are not affected.
            Relative indices are supported with "+" or "-" prefix.
        """
        skey = skey.lower()

        if isinstance(idx, str):
            relative = idx.startswith("+") or idx.startswith("-")
            try:
                index = int(idx)
            except ValueError:
                index = 0
        else:
            relative = False
            index = idx
        wordlists = []

        if skey == "@all":  # Set it for all fields from a csv file
            wordlists.extend(self.content)
        else:
            wordlists.extend(list(skey.split(",")))
        for wkey in wordlists:
            if wkey not in self.content:
                continue
            wordlist = self.content[wkey]
            if (
                wordlist[TYPE_INDEX] in (0, 1) and wkey not in self.prohibited
            ):  # Variable Wordlist type.
                last_index = len(wordlist) - 1
                # Zero-based outside, +2 inside
                if relative:
                    self.content[wkey][1] = min(
                        wordlist[POSITION_INDEX] + index, last_index
                    )
                else:
                    self.content[wkey][1] = min(index + 2, last_index)

    def reset(self, skey: Optional[str] = None) -> None:
        """
        Reset the position index for wordlist entries to the beginning of their data.

        Args:
            skey (Optional[str]): The key to reset. If None, resets all entries.

        Note:
            Only affects the position index, not the actual data values.
            Prohibited keys are not affected when resetting all.
        """
        # Resets position
        if skey is None:
            for skey in self.content:
                self.content[skey][self.POSITION_INDEX] = self.DATA_START_INDEX
        else:
            skey = skey.lower()
            self.content[skey][self.POSITION_INDEX] = self.DATA_START_INDEX

    def translate(self, pattern: str, increment: bool = True) -> str:
        """
        Translate bracketed patterns like {key} or {key#offset} to their values.

        This method processes text containing wordlist patterns and replaces them
        with their corresponding values from the wordlist.

        Args:
            pattern (str): The text containing patterns to translate
            increment (bool): Whether to auto-increment counters and positions after translation

        Returns:
            str: The translated text with patterns replaced by their values

        Examples:
            >>> wl.add("name", "John")
            >>> wl.translate("Hello {name}!")
            'Hello John!'

            >>> wl.translate("Today is {date@%Y-%m-%d}")
            'Today is 2025-01-15'

            >>> wl.translate("{name#+1}")  # Next value
            'Jane'
        """
        if not pattern:
            return ""

        result = str(pattern)
        replacements = {}

        # Find all bracketed patterns
        for bracketed_key in re.findall(r"\{[^}]+\}", result):
            key_content = bracketed_key[1:-1]

            # Parse the key and any modifiers, preserving case for format strings
            key, offset, original_key = self._parse_key_and_offset(key_content)
            # Get the replacement value
            replacement = self._get_replacement_value(original_key, offset, increment)

            # Always replace, even if None (replace with empty string)
            replacements[bracketed_key] = (
                str(replacement) if replacement is not None else ""
            )

        # Apply all replacements at once for efficiency
        for old, new in replacements.items():
            result = result.replace(old, new)

        return result

    def _parse_key_and_offset(self, key_content: str) -> Tuple[str, int, str]:
        """
        Parse key content and extract offset if present.

        Args:
            key_content (str): The key content to parse (e.g., "name", "name#+1", "date@%Y-%m-%d")

        Returns:
            Tuple[str, int, str]: A tuple containing:
                - lowercased_key: The key in lowercase
                - offset: The offset value (0 if not specified)
                - original_key: The original key with original case
        """
        original_key = key_content.strip()

        if "#" not in original_key:
            lowercased_key = original_key.lower()
            return lowercased_key, 0, original_key

        pos = original_key.find("#")
        key_part = original_key[:pos].strip()
        offset_str = original_key[pos + 1 :].strip()

        try:
            offset = int(offset_str)
        except ValueError:
            offset = 0

        lowercased_key = key_part.lower()
        return lowercased_key, offset, original_key

    def _get_replacement_value(
        self, original_key: str, offset: int, increment: bool
    ) -> Optional[Union[str, int]]:
        """
        Get the replacement value for a given key and offset.

        Args:
            original_key (str): The original key with case preserved
            offset (int): The offset to apply
            increment (bool): Whether to increment counters/positions

        Returns:
            Optional[str]: The replacement value, or None if key not found
        """
        # Parse the key to separate base key from offset
        parsed_key, _, _ = self._parse_key_and_offset(original_key)

        # Handle special date/time keys - use original case for format strings
        if parsed_key == "date":
            return self._get_date_value(offset)
        elif parsed_key == "time":
            return self._get_time_value(offset)
        elif parsed_key.startswith("date@"):
            format_str = original_key[
                5:
            ]  # Remove "date@" prefix from original (preserves case)
            return self.wordlist_datestr(format_str)
        elif parsed_key.startswith("time@"):
            format_str = original_key[
                5:
            ]  # Remove "time@" prefix from original (preserves case)
            return self.wordlist_timestr(format_str)

        # Handle regular wordlist keys
        if parsed_key not in self.content:
            return None

        wordlist = self.content[parsed_key]
        wordlist_type = wordlist[0]  # TYPE_INDEX

        if wordlist_type == 2:  # Counter type
            return self._get_counter_value(wordlist, offset, increment)
        else:  # Static or CSV type
            return self._get_list_value(parsed_key, wordlist, offset, increment)

    def _get_date_value(self, offset: int) -> str:
        """
        Get date value, optionally with custom format.

        Args:
            offset (int): Not used for date values

        Returns:
            str: The formatted date string
        """
        format_str = None
        if "date" in self.content:
            stored_format = self.fetch_value("date", 2)
            if (
                stored_format
                and isinstance(stored_format, str)
                and len(stored_format) > 0
                and "%" in stored_format
            ):
                format_str = stored_format
        return self.wordlist_datestr(format_str)

    def _get_time_value(self, offset: int) -> str:
        """
        Get time value, optionally with custom format.

        Args:
            offset (int): Not used for time values

        Returns:
            str: The formatted time string
        """
        format_str = None
        if "time" in self.content:
            stored_format = self.fetch_value("time", 2)
            if (
                stored_format
                and isinstance(stored_format, str)
                and len(stored_format) > 0
                and "%" in stored_format
            ):
                format_str = stored_format
        return self.wordlist_timestr(format_str)

    def _get_counter_value(self, wordlist: List, offset: int, increment: bool) -> int:
        """
        Get value from a counter-type wordlist.

        Args:
            wordlist (List): The wordlist entry data
            offset (int): The offset to add to the counter value
            increment (bool): Whether to auto-increment the counter

        Returns:
            int: The counter value with offset applied
        """
        try:
            value = int(wordlist[2])  # DATA_START_INDEX
        except (ValueError, IndexError):
            value = 0

        value += offset

        # Auto-increment if requested
        if increment:
            wordlist[2] = value + 1

        return value

    def _get_list_value(
        self, key: str, wordlist: List, offset: int, increment: bool
    ) -> Optional[str]:
        """
        Get value from a static or CSV-type wordlist.

        Args:
            key (str): The wordlist key
            wordlist (List): The wordlist entry data
            offset (int): The offset to apply to the index
            increment (bool): Whether to auto-increment the position

        Returns:
            Optional[str]: The value at the calculated index, or None if not found
        """
        if offset != 0:
            # If offset is specified, add it to the data start index (absolute offset)
            target_index = self.DATA_START_INDEX + offset
        else:
            # Otherwise use the current position
            target_index = wordlist[self.POSITION_INDEX]

        value = self.fetch_value(key, target_index)

        # Auto-increment if requested and no explicit offset
        if increment and offset == 0 and value is not None:
            wordlist[self.POSITION_INDEX] = target_index + 1

        return value

    @staticmethod
    def wordlist_datestr(sformat: Optional[str] = None) -> str:
        """
        Get the current date as a formatted string.

        Args:
            sformat (Optional[str]): Date format string (strftime format).
                                   Defaults to "%x" (locale's date representation).

        Returns:
            str: The formatted date string, or "invalid" if format is invalid.

        Example:
            >>> Wordlist.wordlist_datestr("%Y-%m-%d")
            '2025-01-15'
        """
        time = datetime.now()
        if sformat is None:
            sformat = "%x"
        try:
            result = time.strftime(sformat)
            # Check if the result contains the original format string (indicates invalid format)
            if "%" in result and sformat in result:
                return "invalid"
        except ValueError:
            result = "invalid"
        return result

    @staticmethod
    def wordlist_timestr(sformat: Optional[str] = None) -> str:
        """
        Get the current time as a formatted string.

        Args:
            sformat (Optional[str]): Time format string (strftime format).
                                   Defaults to "%X" (locale's time representation).

        Returns:
            str: The formatted time string, or "invalid" if format is invalid.

        Example:
            >>> Wordlist.wordlist_timestr("%H:%M:%S")
            '14:30:25'
        """
        time = datetime.now()
        if sformat is None:
            sformat = "%X"
        try:
            result = time.strftime(sformat)
            # Check if the result contains the original format string (indicates invalid format)
            if "%" in result and sformat in result:
                return "invalid"
        except ValueError:
            result = "invalid"
        return result

    def get_variable_list(self) -> List[str]:
        """
        Get a list of all wordlist variables with their current values.

        Returns:
            List[str]: A list of strings in the format "key (value)" for each variable

        Example:
            >>> wl.get_variable_list()
            ['name (John)', 'version (1.0.0)', 'date (2025-01-15)']
        """
        choices = []
        for skey in self.content:
            value = self.fetch(skey)
            choices.append(f"{skey} ({value})")
        return choices

    def begin_transaction(self) -> None:
        """
        Begin a transaction to allow atomic rollback of changes.

        Creates a backup of the current wordlist content that can be restored
        using rollback_transaction(). Only one transaction can be active at a time.

        Note:
            If a transaction is already open, this method does nothing.
        """
        # We want to store all our values
        if not self.transaction_open:
            self.content_backup = {}
            for key in self.content:
                item = copy(self.content[key])
                self.content_backup[key] = item
            self.transaction_open = True

    def rollback_transaction(self) -> None:
        """
        Rollback changes made since the last begin_transaction() call.

        Restores the wordlist content to the state it was in when begin_transaction()
        was called. Closes the transaction.

        Note:
            If no transaction is open, this method does nothing.
        """
        if self.transaction_open:
            self.content = {}
            for key in self.content_backup:
                item = copy(self.content_backup[key])
                self.content[key] = item
            self.transaction_open = False
            self.content_backup = {}

    def commit_transaction(self) -> None:
        """
        Commit the current transaction, making all changes permanent.

        Closes the transaction without restoring the backup. The changes made
        since begin_transaction() are kept.

        Note:
            If no transaction is open, this method does nothing.
        """
        if self.transaction_open:
            self.transaction_open = False
            self.content_backup = {}

    def load_data(self, filename: Optional[str] = None) -> None:
        """
        Load wordlist data from a JSON file.

        Args:
            filename (Optional[str]): Path to the JSON file to load. If None,
                                    uses the default filename.

        Note:
            Silently ignores errors if the file doesn't exist or is invalid.
            Closes any open transaction.
        """
        if filename is None:
            filename = self.default_filename
        try:
            with open(filename) as f:
                self.content = json.load(f)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        self.transaction_open = False

    def save_data(self, filename: Optional[str] = None) -> None:
        """
        Save wordlist data to a JSON file.

        Args:
            filename (Optional[str]): Path to the JSON file to save. If None,
                                    uses the default filename.

        Note:
            Closes any open transaction.
        """
        if filename is None:
            filename = self.default_filename
        with open(filename, "w") as f:
            json.dump(self.content, f)
        self.transaction_open = False

    def delete(self, skey: str) -> None:
        """
        Delete a wordlist entry.

        Args:
            skey (str): The key of the entry to delete (case-insensitive)

        Note:
            Silently ignores the operation if the key doesn't exist.
        """
        try:
            self.content.pop(skey)
        except KeyError:
            pass

    def rename_key(self, oldkey: str, newkey: str) -> bool:
        """
        Rename a wordlist entry key.

        Args:
            oldkey (str): The current key to rename (case-insensitive)
            newkey (str): The new key name (case-insensitive)

        Returns:
            bool: True if the rename was successful, False otherwise

        Note:
            Cannot rename prohibited system keys.
            Cannot rename to an existing key.
        """
        oldkey = oldkey.lower()
        newkey = newkey.lower()
        if oldkey in self.prohibited:
            return False
        if oldkey == newkey:
            return True
        if newkey in self.content:
            return False
        try:
            self.content[newkey] = self.content[oldkey]
            self.delete(oldkey)
        except KeyError:
            return False
        return True

    def empty_csv(self) -> None:
        """
        Remove all CSV-type wordlist entries.

        This method clears all wordlist entries that were created from CSV files,
        preparing for loading a new CSV file.
        """
        # remove all traces of the previous csv file
        names = [
            skey for skey in self.content if self.content[skey][TYPE_INDEX] == TYPE_CSV
        ]
        for skey in names:
            self.delete(skey)

    def load_csv_file(
        self, filename: str, force_header: Optional[bool] = None
    ) -> Tuple[int, int, List[str]]:
        """
        Load data from a CSV file into the wordlist.

        This method automatically detects CSV encoding, headers, and dialect.
        It clears any existing CSV data before loading.

        Args:
            filename (str): Path to the CSV file to load
            force_header (Optional[bool]): Force header detection. If None, auto-detect.

        Returns:
            Tuple[int, int, List[str]]: A tuple containing:
                - Number of data rows loaded
                - Number of columns detected
                - List of column headers/keys

        Note:
            Creates wordlist entries for each column with TYPE_CSV.
            Handles various CSV formats and encodings automatically.
        """
        self.empty_csv()
        ct = 0
        headers = []
        decoder = EncodingDetectFile()
        result = decoder.load(filename)
        if result:
            encoding, bom_marker, file_content = result

            try:
                with open(filename, newline="", encoding=encoding) as csvfile:
                    # Check if file is empty first
                    if csvfile.read(1) == "":
                        return 0, 0, []
                    csvfile.seek(0)
                    buffer = csvfile.read(1024)
                    has_header = (
                        csv.Sniffer().has_header(buffer)
                        if force_header is None
                        else force_header
                    )
                    # print (f"Header={has_header}, Force={force_header}")
                    dialect = csv.Sniffer().sniff(buffer)
                    csvfile.seek(0)
                    reader = csv.reader(csvfile, dialect)
                    headers = next(reader)
                    if not has_header:
                        # headers contains the first row of data, don't lowercase it
                        pass
                    else:
                        # Convert headers to lowercase for consistency
                        headers = [h.lower() for h in headers]
                    if not has_header:
                        # Use Line as Data and set some default names
                        for idx, entry in enumerate(headers):
                            skey = f"Column_{idx + 1}"
                            self.set_value(skey=skey, value=entry, idx=-1, wtype=1)
                            headers[idx] = skey.lower()
                        ct = 1
                    else:
                        ct = 0
                    for row in reader:
                        for idx, entry in enumerate(row):
                            skey = headers[idx].lower()
                            if skey.startswith("\\ufeff"):
                                skey = skey[7:]
                            # Append...
                            self.set_value(skey=skey, value=entry, idx=-1, wtype=1)
                        ct += 1
            except (OSError, StopIteration, csv.Error, UnicodeDecodeError):
                ct = 0
                headers = []
        colcount = len(headers)
        return ct, colcount, headers

    def wordlist_delta(self, orgtext: str, increase: int) -> str:
        """
        Adjust offset values in wordlist patterns within text.

        This method finds all {key#offset} patterns in the text and adjusts
        the offset values by the specified amount.

        Args:
            orgtext (str): The original text containing wordlist patterns
            increase (int): The amount to add to each offset value

        Returns:
            str: The modified text with adjusted offset values

        Example:
            >>> wl.wordlist_delta("{name#+1} {name#-2}", 3)
            '{name#+4} {name#+1}'
        """
        newtext = str(orgtext)
        toreplace = []
        # list of tuples, (index found, old, new )
        # Let's gather the {} first...
        brackets = re.compile(r"\{[^}]+\}")
        for bracketed_key in brackets.findall(str(orgtext)):
            key = bracketed_key[1:-1].lower().strip()
            relative = 0
            pos = key.find("#")
            if pos > 0:
                # Needs to be after first character
                # Process offset modification.
                index_string = key[pos + 1 :]
                key = key[:pos].strip()

                if not index_string.startswith("+") and not index_string.startswith(
                    "-"
                ):
                    # We have a #<index> value without + or -, specific index value from 0
                    # no need to do something
                    continue
                try:
                    # This covers +x, -x, x
                    relative = int(index_string)
                except ValueError:
                    relative = 0
            elif key.startswith("time@"):
                key = "time"
            elif key.startswith("date@"):
                key = "date"
            if key not in self.content:
                continue
            if key in self.prohibited:
                continue
            newindex = relative + increase
            if newindex > 0:
                newpattern = f"{{{key}#+{newindex}}}"
            elif newindex < 0:
                newpattern = f"{{{key}#{newindex}}}"
            else:
                # 0
                newpattern = f"{{{key}}}"
            if newpattern != bracketed_key:
                item = [relative, bracketed_key, newpattern]
                toreplace.append(item)

        # Then sort the list according to the direction,
        # as we don't want to replace the same pattern again and again
        if increase >= 0:
            toreplace.sort(key=lambda n: n[0])
        else:
            toreplace.sort(reverse=True, key=lambda n: n[0])
        for item in toreplace:
            newtext = newtext.replace(item[1], item[2])
        return newtext

    def push(self) -> None:
        """
        Push the current wordlist state onto the stack.

        Creates a deep copy of the current content and stores it on the internal stack.
        This allows temporary modifications that can be undone with pop().

        Note:
            The stack is used for temporary state management and can store multiple levels.
        """
        copied_content = {key: copy(entry) for key, entry in self.content.items()}
        self._stack.append(copied_content)
        # print (f"push was called, when name was: '{self.content['name']}'")

    def pop(self) -> None:
        """
        Pop the last pushed wordlist state from the stack.

        Restores the wordlist content to the state it was in when the last push()
        was called. If the stack is empty, this method does nothing.

        Note:
            This completely replaces the current content with the stacked version.
        """
        if len(self._stack) > 0:
            copied_content = self._stack[-1]
            self._stack.pop(-1)
            self.content = {}
            for key, entry in copied_content.items():
                self.content[key] = copy(entry)
        # print (f"pop was called, name now '{self.content['name']}'")
