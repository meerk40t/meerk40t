"""
Wordlist System for MeerK40t

This module provides the core Wordlist class that manages dynamic variable substitution
for text elements in laser cutting operations. The wordlist system allows users to define
variables that can be referenced in text using {variable_name} syntax, enabling dynamic
content generation during laser operations.

The wordlist system supports:
- Static text variables
- CSV file-based variable arrays
- Numeric counters with auto-increment
- Date and time formatting
- Operation-specific parameters (speed, power, passes, etc.)
- Persistent storage in JSON format

Typical usage involves creating text elements with patterns like:
- "Hello {first} {second}!"
- "{date} - Job #{counter}"
- "Power: {op_power}, Speed: {op_speed}"

The elements service integrates with this class to provide wordlist_translate() functionality
for text rendering during laser operations.
"""

import csv
import json
import os
import re
from copy import copy
from datetime import datetime
from ..extra.encode_detect import EncodingDetectFile

# Type constants
TYPE_STATIC = 0
TYPE_CSV = 1
TYPE_COUNTER = 2

# Index constants
IDX_TYPE = 0
IDX_POSITION = 1
IDX_DATA_START = 2


class Wordlist:
    """
    Dynamic variable substitution system for text elements.

    The Wordlist class manages a collection of named variables that can be used for
    dynamic text generation in laser cutting operations. Variables are referenced
    using {variable_name} syntax and can contain static text, arrays from CSV files,
    or auto-incrementing counters.

    Data Structure:
        Each variable is stored as a list with the format:
        [type, current_index, value1, value2, ...]

        Type codes:
        - 0: Static text entry (single value)
        - 1: Text array from CSV file
        - 2: Numeric counter (auto-incrementing)

        The current_index points to the active value within the list.

    Built-in Variables:
        - version: Software version string
        - date: Current date (formatted)
        - time: Current time (formatted)
        - op_device: Device label
        - op_speed: Operation speed setting
        - op_power: Operation power setting
        - op_passes: Operation passes setting
        - op_dpi: Operation DPI setting

    Example:
        >>> wl = Wordlist("1.0.0")
        >>> wl.add("name", "John Doe")
        >>> wl.translate("Hello {name}!")
        'Hello John Doe!'

        >>> wl.add("counter", 1, wtype=2)  # Counter type
        >>> wl.translate("Job #{counter}")
        'Job #1'
        >>> wl.translate("Job #{counter}")  # Auto-increments
        'Job #2'

    Notes:
        - Keys are normalized (trimmed and lower-cased). Passing `None`, non-string,
          or whitespace-only keys to methods is treated as invalid.
        - Use `has_value(key, entry)` to check membership.
        - `add_value_unique(key, entry, wtype=None)` will add only if the value is
          not present and returns a tuple `(added: bool, reason: Optional[str])`.
    """

    def __init__(self, versionstr, directory=None):
        """
        Initialize a new Wordlist instance.

        Args:
            versionstr (str): Version string for the {version} variable
            directory (str, optional): Directory for wordlist.json persistence.
                                      Defaults to current working directory.
        """
        # The content-dictionary contains an array per entry
        # index 0 indicates the type:
        #   0 (static) text entry
        #   1 text entry array coming from a csv file
        #   2 is a numeric counter
        # index 1 indicates the position of the current array (always 2 for type 0 and 2)
        # index 2 and onwards contain the actual data
        self.content = {
            "version": [TYPE_STATIC, IDX_DATA_START, versionstr],
            "date": [TYPE_STATIC, IDX_DATA_START, self.wordlist_datestr()],
            "time": [TYPE_STATIC, IDX_DATA_START, self.wordlist_timestr()],
            "op_device": [TYPE_STATIC, IDX_DATA_START, "<device>"],
            "op_speed": [TYPE_STATIC, IDX_DATA_START, "<speed>"],
            "op_power": [TYPE_STATIC, IDX_DATA_START, "<power>"],
            "op_passes": [TYPE_STATIC, IDX_DATA_START, "<passes>"],
            "op_dpi": [TYPE_STATIC, IDX_DATA_START, "<dpi>"],
        }
        self.prohibited = (
            "version",
            "date",
            "time",
            "op_device",
            "op_speed",
            "op_power",
            "op_passes",
            "op_dpi",
        )
        self._stack = []
        self.transaction_open = False
        self.content_backup = {}
        self._last_load_warnings = []
        if directory is None:
            directory = os.getcwd()
        self.default_filename = os.path.join(directory, "wordlist.json")
        self.load_data(self.default_filename)

    def _normalize_key(self, skey):
        """Normalize and validate a key.

        Returns a lowercase stripped key string, or None for invalid input (None, non-string, or empty/whitespace-only).
        """
        if skey is None or not isinstance(skey, str):
            return None
        s = skey.strip()
        if s == "":
            return None
        return s.lower()

    def _is_valid_entry(self, item):
        """Quick structural validation of an entry loaded from JSON.

        Returns True if item is a list with an allowed type and at least one data value.
        """
        if not isinstance(item, list):
            return False
        if len(item) < IDX_DATA_START + 1:
            return False
        try:
            t = int(item[IDX_TYPE])
        except Exception:
            return False
        if t not in (TYPE_STATIC, TYPE_CSV, TYPE_COUNTER):
            return False
        return True

    def _sanitize_entry(self, item):
        """Return a sanitized/normalized copy of an entry or None if it cannot be used.

        - Coerces numeric fields, enforces correct lengths, and normalizes positions to valid ranges.
        """
        if not isinstance(item, list):
            return None
        if len(item) < IDX_DATA_START + 1:
            return None
        try:
            t = int(item[IDX_TYPE])
        except Exception:
            return None
        # reject unknown types
        if t not in (TYPE_STATIC, TYPE_CSV, TYPE_COUNTER):
            return None
        # Position
        pos = None
        try:
            pos = int(item[IDX_POSITION])
        except Exception:
            pos = IDX_DATA_START

        if t == TYPE_COUNTER:
            # Ensure we have a counter value and coerce to int
            if len(item) <= IDX_DATA_START:
                return None
            try:
                val = int(item[IDX_DATA_START])
            except Exception:
                val = 0
            return [t, IDX_DATA_START, val]
        else:
            # Static or CSV: ensure at least one data value
            data = list(item[IDX_DATA_START:]) if len(item) > IDX_DATA_START else [""]
            # Normalize position to be within data range
            maxpos = IDX_DATA_START + len(data) - 1
            if pos < IDX_DATA_START:
                pos = IDX_DATA_START
            if pos > maxpos:
                pos = maxpos
            return [t, pos] + data

    def add(self, key, value, wtype=None):
        """
        Add a value to the wordlist (alias for add_value).

        Args:
            key (str): Variable name (case-insensitive)
            value: Value to store
            wtype (int, optional): Variable type (0=static, 1=csv, 2=counter)
        """
        self.add_value(key, value, wtype)

    def fetch(self, key):
        """
        Fetch the current value for a variable.

        Args:
            key (str): Variable name to fetch

        Returns:
            str or None: Current value of the variable, or None if not found
        """
        result = self.fetch_value(key, None)
        return result

    def fetch_value(self, skey, idx):
        """
        Fetch a value from the wordlist with optional index.

        Args:
            skey (str): Variable name (case-insensitive)
            idx (int, optional): Specific index to fetch, uses current index if None

        Returns:
            str or None: Value at the specified index, or None if not found
        """
        skey = self._normalize_key(skey)
        if skey is None:
            return None
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
        if idx is None or idx < 0:  # Default
            idx = wordlist[IDX_POSITION]

        if idx < len(wordlist):
            result = wordlist[idx]
        else:
            result = None
        return result

    def add_value(self, skey, value, wtype=None):
        """
        Add a value to a wordlist variable.

        Args:
            skey (str): Variable name (case-insensitive)
            value: Value to add (string, number, or list for CSV data)
            wtype (int, optional): Variable type:
                0 = static text (single value)
                1 = CSV/array data (multiple values)
                2 = counter (numeric value that increments)
                If None, defaults to 0 for new variables
        """
        skey = self._normalize_key(skey)
        if skey is None:
            return
        if skey not in self.content:
            if wtype is None:
                wtype = TYPE_STATIC
            self.content[skey] = [
                wtype,
                IDX_DATA_START,
            ]  # incomplete, as it will be appended right after this
        self.content[skey].append(value)

    def has_value(self, skey, entry):
        """Return True if the variable contains an entry equal to `entry` (string comparison)."""
        skey = self._normalize_key(skey)
        if skey is None:
            return False
        if skey not in self.content:
            return False
        try:
            for v in self.content[skey][IDX_DATA_START:]:
                if str(v) == str(entry):
                    return True
        except Exception:
            return False
        return False

    def add_value_unique(self, skey, entry, wtype=None):
        """
        Add value only if it does not already exist.

        Returns:
            (bool, Optional[str]): (added, reason)
                - (True, None): added successfully
                - (False, 'invalid_key'): invalid or empty key
                - (False, 'empty'): entry is None or empty/whitespace
                - (False, 'duplicate'): entry already exists
        """
        skey = self._normalize_key(skey)
        if skey is None:
            return False, "invalid_key"
        # Reject empty entries
        if entry is None or (isinstance(entry, str) and entry.strip() == ""):
            return False, "empty"
        if self.has_value(skey, entry):
            return False, "duplicate"
        self.add_value(skey, entry, wtype)
        return True, None

    def delete_value(self, skey, idx):
        """
        Delete a value from a wordlist variable at the specified index.

        Args:
            skey (str): Variable name (case-insensitive)
            idx (int): Zero-based index of the value to delete
        """
        skey = self._normalize_key(skey)
        if skey is None:
            return
        if skey not in self.content:
            return
        if idx is None or idx < 0:
            return

        # Zerobased outside + 2 inside
        idx += IDX_DATA_START
        if idx >= len(self.content[skey]):
            return
        self.content[skey].pop(idx)

    def move_all_indices(self, delta):
        for wkey in self.content:
            wordlist = self.content[wkey]
            if wkey in self.prohibited:
                continue
            if wordlist[IDX_TYPE] in (TYPE_STATIC, TYPE_CSV):  # Text or csv
                last_index = len(wordlist) - 1
                # Zero-based outside, +2 inside
                newidx = min(wordlist[IDX_POSITION] + delta, last_index)
                if newidx < IDX_DATA_START:
                    newidx = IDX_DATA_START
                wordlist[IDX_POSITION] = newidx
            elif wordlist[IDX_TYPE] == TYPE_COUNTER:  # Counter-type
                value = wordlist[IDX_DATA_START]
                try:
                    value = int(value) + delta
                except ValueError:
                    value = 0
                if value < 0:
                    value = 0
                wordlist[IDX_DATA_START] = value

    def set_value(self, skey, value, idx=None, wtype=None):
        # Special treatment:
        # Index = None - use current
        # Index < 0 append
        skey = self._normalize_key(skey)
        if skey is None:
            return
        if skey not in self.content:
            # hasn't been there, so establish it
            if wtype is None:
                wtype = TYPE_STATIC
            self.content[skey] = [wtype, IDX_DATA_START, value]
        else:
            if idx is None:
                # use current position
                idx = self.content[skey][IDX_POSITION]
                try:
                    idx = int(idx)
                except ValueError:
                    idx = 0
            elif idx < 0:
                # append
                self.content[skey].append(value)
            else:  # Zerobased outside + 2 inside
                idx += IDX_DATA_START

            if idx >= len(self.content[skey]):
                idx = len(self.content[skey]) - 1
            self.content[skey][idx] = value

    def set_index(self, skey, idx, wtype=None):
        skey = self._normalize_key(skey)
        if skey is None:
            return

        if isinstance(idx, str):
            relative = idx.startswith("+") or idx.startswith("-")
            try:
                index = int(idx)
            except ValueError:
                index = 0  # Default to 0 for invalid input
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
                wordlist[IDX_TYPE] in (TYPE_STATIC, TYPE_CSV)
                and wkey not in self.prohibited
            ):  # Variable Wordlist type.
                last_index = len(wordlist) - 1
                # Zero-based outside, +2 inside
                if relative:
                    self.content[wkey][IDX_POSITION] = min(
                        wordlist[IDX_POSITION] + index, last_index
                    )
                else:
                    self.content[wkey][IDX_POSITION] = min(
                        index + IDX_DATA_START, last_index
                    )

    def reset(self, skey=None):
        """
        Reset the current index position for wordlist variables.

        For array-type variables, resets the current index to the first item.
        For counter-type variables, this method doesn't apply.

        Args:
            skey (str, optional): Specific variable to reset, or None to reset all
        """
        # Resets position
        if skey is None:
            for key in self.content:
                self.content[key][IDX_POSITION] = IDX_DATA_START
            return
        skey = self._normalize_key(skey)
        if skey is None:
            return
        if skey in self.content:
            self.content[skey][IDX_POSITION] = IDX_DATA_START

    def translate(self, pattern, increment=True):
        """
        Translate a pattern string by replacing {variable} placeholders with values.

        This method performs variable substitution using the wordlist data. Variables
        are referenced using {variable_name} syntax. Supports various modifiers:

        - {variable#n} - Get specific index n (0-based)
        - {variable#+n} - Get current index + n
        - {variable#-n} - Get current index - n
        - {date@format} - Date with custom format string
        - {time@format} - Time with custom format string

        For array variables, the current index is incremented after access unless
        increment=False or a specific index is requested.

        Args:
            pattern (str): String containing {variable} placeholders to replace
            increment (bool): Whether to increment counters after fetching values

        Returns:
            str: Pattern with all variables replaced by their values

        Examples:
            >>> wordlist.add("name", "John")
            >>> wordlist.translate("Hello {name}")
            'Hello John'

            >>> wordlist.add("names", ["Alice", "Bob", "Charlie"], 1)
            >>> wordlist.translate("Hi {names}")  # Gets current value and increments
            'Hi Alice'
            >>> wordlist.translate("Hi {names}")  # Gets next value
            'Hi Bob'
            >>> wordlist.translate("Hi {names#0}")  # Gets first value, no increment
            'Hi Alice'
        """
        if pattern is None:
            return ""
        result = str(pattern)
        brackets = re.compile(r"\{[^}]+\}")
        for bracketed_key in brackets.findall(result):
            #            print(f"Key found: {bracketed_key}")
            key = bracketed_key[1:-1].lower().strip()
            # Let's check whether we have a modifier at the end: #<num>
            # if key.endswith("++"):
            #     autoincrement = True
            #     key = key[:-2].strip()
            # else:
            #     autoincrement = False
            autoincrement = False

            reset = False
            relative = 0
            pos = key.find("#")
            if pos > 0:  # Needs to be after first character
                # Process offset modification.
                index_string = key[pos + 1 :]
                key = key[:pos].strip()

                if not index_string.startswith("+") and not index_string.startswith(
                    "-"
                ):
                    # We have a #<index> value without + or -, specific index value from 0
                    reset = True
                try:
                    # This covers +x, -x, x
                    relative = int(index_string)
                except ValueError:
                    relative = 0

            # And now date and time...
            if key == "date":
                # Do we have a format str?
                sformat = None
                if key in self.content:
                    value = self.fetch_value(key, IDX_DATA_START)
                    if value is not None and isinstance(value, str) and len(value) > 0:
                        if "%" in value:
                            # Seems to be a format string, so let's try it...
                            sformat = value
                value = self.wordlist_datestr(sformat)
            elif key == "time":
                # Do we have a format str?
                sformat = None
                if key in self.content:
                    value = self.fetch_value(key, IDX_DATA_START)
                    if value is not None and isinstance(value, str) and len(value) > 0:
                        if "%" in value:
                            # Seems to be a format string, so let's try it...
                            sformat = value
                value = self.wordlist_timestr(sformat)
            elif key.startswith("date@"):
                # Original cASEs, vkey is already lowered...
                sformat = bracketed_key[6:-1]
                value = self.wordlist_datestr(sformat)
            elif key.startswith("time@"):
                # Original cASEs, vkey is already lowered...
                sformat = bracketed_key[6:-1]
                value = self.wordlist_timestr(sformat)
            else:
                # Must be a wordlist type.
                if key not in self.content:
                    # This is not a wordlist name - replace with empty string
                    value = ""
                else:
                    wordlist = self.content[key]

                    if wordlist[IDX_TYPE] == TYPE_COUNTER:  # Counter-type
                        # Counter index is the value.
                        value = wordlist[
                            IDX_DATA_START
                        ]  # Always use current value for counters
                        try:
                            value = int(value)
                        except ValueError:
                            value = 0
                        value += relative
                        if increment:  # Counters always increment when accessed (unless specific index)
                            wordlist[IDX_DATA_START] = value + 1
                    else:
                        # This is a variable wordlist.
                        current_index = (
                            IDX_DATA_START if reset else wordlist[IDX_POSITION]
                        )  # 2 as 2 based
                        current_index += relative
                        value = self.fetch_value(key, current_index)
                        if autoincrement and increment:
                            # Index set to current index + 1
                            wordlist[IDX_POSITION] = current_index + 1

            if value is not None:
                result = result.replace(bracketed_key, str(value))

        return result

    @staticmethod
    def wordlist_datestr(date_format=None):
        time = datetime.now()
        if date_format is None:
            date_format = "%x"
        try:
            result = time.strftime(date_format)
            if "%" in result:
                # Seems invalid!
                result = "invalid"
        except Exception:
            result = "invalid"
        return result

    @staticmethod
    def wordlist_timestr(time_format=None):
        time = datetime.now()
        if time_format is None:
            time_format = "%X"
        try:
            result = time.strftime(time_format)
            if "%" in result:
                # Seems invalid!
                result = "invalid"
        except Exception:
            result = "invalid"

        return result

    def get_variable_list(self):
        choices = []
        for skey in self.content:
            value = self.fetch(skey)
            choices.append(f"{skey} ({value})")
        return choices

    def begin_transaction(self):
        # We want to store all our values
        if not self.transaction_open:
            self.content_backup = {}
            for key in self.content:
                item = copy(self.content[key])
                self.content_backup[key] = item
            self.transaction_open = True

    def rollback_transaction(self):
        if self.transaction_open:
            self.content = {}
            for key in self.content_backup:
                item = copy(self.content_backup[key])
                self.content[key] = item
            self.transaction_open = False
            self.content_backup = {}

    def commit_transaction(self):
        if self.transaction_open:
            self.transaction_open = False
            self.content_backup = {}

    def load_data(self, filename):
        """
        Load wordlist data from a JSON file.

        Args:
            filename (str, optional): File path to load from. If None, uses default filename.
        """
        if filename is None:
            filename = self.default_filename
        warnings = []
        try:
            with open(filename) as f:
                raw = json.load(f)
            new_content = {}
            if isinstance(raw, dict):
                for key, item in raw.items():
                    nk = self._normalize_key(key)
                    if nk is None:
                        warnings.append(f"Skipping wordlist entry '{key}': invalid key")
                        continue
                    san = self._sanitize_entry(item)
                    if san is None:
                        warnings.append(
                            f"Skipping wordlist entry '{key}': malformed or invalid"
                        )
                        continue
                    new_content[nk] = san
                # Ensure builtins exist (preserve defaults if not present)
                for k in self.prohibited:
                    if k not in new_content:
                        new_content[k] = self.content.get(
                            k, [TYPE_STATIC, IDX_DATA_START, f"<{k}>"]
                        )
                self.content = new_content
            else:
                warnings.append(
                    f"wordlist file {filename} has non-dict top-level; ignoring"
                )
        except (json.JSONDecodeError, PermissionError, OSError, FileNotFoundError) as e:
            warnings.append(f"Failed to load wordlist file {filename}: {e}")
            # Keep existing content on error
        self.transaction_open = False
        # Store last warnings for later inspection
        self._last_load_warnings = list(warnings)
        # No return value (callers should use get_warnings/has_warnings)

    def get_load_warnings(self):
        """Return a list of warnings produced by the last call to `load_data()`.

        Returns a shallow copy of the last warnings list (may be empty).
        """
        return list(self._last_load_warnings)

    def has_load_warnings(self):
        """Return True if the last load produced any warnings."""
        return len(self._last_load_warnings) > 0

    # Convenience aliases - prefer using these for clearer intent
    def get_warnings(self):
        """Alias for :meth:`get_load_warnings()`.

        Kept for API clarity: call this after ``load_data()`` to inspect any warnings.
        """
        return self.get_load_warnings()

    def has_warnings(self):
        """Alias for :meth:`has_load_warnings()`.

        Call immediately after ``load_data()`` to know whether any warnings occurred.
        """
        return self.has_load_warnings()

    def validate_content(self):
        """Validate the current `content` and return a list of issues found.

        This performs structural checks on each entry and returns human-readable
        messages describing any problems (empty list if no issues).
        """
        issues = []
        for key, item in list(self.content.items()):
            if not self._is_valid_entry(item):
                issues.append(f"Key '{key}': invalid structure or type")
                continue
            t = item[IDX_TYPE]
            if t == TYPE_COUNTER:
                # Check counter value is an integer
                try:
                    int(item[IDX_DATA_START])
                except Exception:
                    issues.append(f"Key '{key}': counter value is not integer")
            else:
                # For static/csv ensure position is within bounds
                data_len = len(item) - IDX_DATA_START
                pos = item[IDX_POSITION]
                if pos < IDX_DATA_START or pos > IDX_DATA_START + data_len - 1:
                    issues.append(
                        f"Key '{key}': position {pos} out of range for data length {data_len}"
                    )
        return issues

    def save_data(self, filename):
        """
        Save the wordlist data to a JSON file.

        Args:
            filename (str, optional): File path to save to. If None, uses default filename.
        """
        if filename is None:
            filename = self.default_filename
        with open(filename, "w") as f:
            json.dump(self.content, f)
        self.transaction_open = False

    def delete(self, skey):
        skey = self._normalize_key(skey)
        if skey is None:
            return
        try:
            self.content.pop(skey)
        except KeyError:
            pass

    def rename_key(self, oldkey, newkey):
        oldkey = self._normalize_key(oldkey)
        newkey = self._normalize_key(newkey)
        if oldkey is None or newkey is None:
            return False
        if oldkey in self.prohibited:
            return False
        if oldkey == newkey:
            return True
        if newkey in self.content:
            return False
        try:
            self.content[newkey] = self.content[oldkey]
            self.delete(oldkey)
        except Exception:
            return False
        return True

    def empty_csv(self):
        # remove all traces of the previous csv file
        names = [
            skey for skey in self.content if self.content[skey][IDX_TYPE] == TYPE_CSV
        ]
        for skey in names:
            self.delete(skey)

    def load_csv_file(self, filename, force_header=None):
        """Load a CSV into wordlist entries.

        Returns a tuple: (row_count, column_count, headers)
        Any warnings (errors or issues) are recorded in
        `self._last_load_warnings` and can be inspected with
        `get_load_warnings()` / `has_load_warnings()`.
        """
        self.empty_csv()
        ct = 0
        headers = []
        warnings = []
        decoder = EncodingDetectFile()
        result = decoder.load(filename)
        if not result:
            warnings.append(f"Could not read CSV file {filename}")
            self._last_load_warnings = list(warnings)
            return 0, 0, []

        encoding, bom_marker, file_content = result

        # Quick sanity check: unmatched quotes likely indicate malformed CSV
        if file_content.count('"') % 2 != 0:
            warnings.append(f"Malformed CSV file {filename}: unmatched quotes detected")
            self._last_load_warnings = list(warnings)
            return 0, 0, []

        try:
            # If the file is very large, switch to a streaming parse to avoid high memory use
            MAX_STREAM_SIZE = 2 * 1024 * 1024  # 2 MB
            MAX_ROWS = 100000  # safety upper bound to prevent extremely long imports

            # Find a safe buffer that ends with a complete line
            buffer_limit = min(1024, len(file_content))
            last_newline = file_content.rfind("\n", 0, buffer_limit)
            if last_newline > 0:
                buffer = file_content[: last_newline + 1]  # Include the newline
            else:
                # Fallback to original behavior if no newline found
                buffer = file_content[:buffer_limit]

            if force_header is None:
                try:
                    has_header = csv.Sniffer().has_header(buffer)
                except Exception:
                    has_header = False
                    warnings.append(
                        f"CSV header detection failed for {filename}; treating as data"
                    )
            else:
                has_header = force_header

            dialect = None
            # If caller explicitly set force_header, avoid running the sometimes expensive sniffer and use default excel dialect.
            if force_header is None:
                try:
                    dialect = csv.Sniffer().sniff(buffer)
                except Exception:
                    # Fall back to default dialect and warn
                    warnings.append(f"CSV dialect detection failed for {filename}; using default")
                    dialect = csv.get_dialect("excel")
            else:
                dialect = csv.get_dialect("excel")

            # If file content is large, or user file seems likely to be big, parse in streaming mode
            if len(file_content) > MAX_STREAM_SIZE:
                warnings.append(f"Large CSV file detected ({len(file_content)} bytes); using streaming parser to avoid high memory usage")
                # Re-open the file using detected encoding and stream rows
                try:
                    with open(filename, "r", encoding=encoding, errors="replace") as fh:
                        # Prepare CSV reader on the file handle using the sniffed dialect
                        reader = csv.reader(fh, dialect)
                        try:
                            raw_headers = next(reader)
                        except StopIteration:
                            # empty file
                            self._last_load_warnings = list(warnings)
                            return 0, 0, []
                        # Clean BOM and whitespace from headers (remove BOM regardless of surrounding whitespace)
                        cleaned = [ (h.replace("\ufeff", "") if h is not None else "").strip() for h in raw_headers ]

                        headers = []
                        seen = {}

                        def make_unique(name, idx):
                            if name is None or name == "":
                                base = f"column_{idx + 1}"
                            else:
                                base = name
                            base_norm = self._normalize_key(base) or f"column_{idx + 1}"
                            # Ensure uniqueness
                            if base_norm in seen:
                                seen[base_norm] += 1
                                unique = f"{base_norm}_{seen[base_norm]}"
                            else:
                                seen[base_norm] = 1
                                unique = base_norm
                            return unique

                        if not has_header:
                            # Treat first row as data; create Column_N keys and store first row
                            for idx, entry in enumerate(cleaned):
                                skey = make_unique(None, idx)
                                headers.append(skey)
                                value = entry
                                self.set_value(skey=skey, value=value, idx=-1, wtype=TYPE_CSV)
                            ct = 1
                        else:
                            ct = 0
                            for idx, h in enumerate(cleaned):
                                skey = make_unique(h, idx)
                                headers.append(skey)

                        # Stream the remaining rows
                        for row in reader:
                            if ct >= MAX_ROWS:
                                warnings.append(f"Import aborted: exceeded maximum row limit ({MAX_ROWS})")
                                break
                            for idx, entry in enumerate(row):
                                if idx >= len(headers):
                                    newkey = make_unique(None, idx)
                                    headers.append(newkey)
                                skey = headers[idx]
                                clean_entry = entry.replace("\ufeff", "").strip()
                                self.set_value(skey=skey, value=clean_entry, idx=-1, wtype=TYPE_CSV)
                            ct += 1
                except (OSError, PermissionError) as e:
                    warnings.append(f"Failed to open CSV file {filename} for streaming: {e}")
                    self._last_load_warnings = list(warnings)
                    return 0, 0, []
            else:
                # Use the already BOM-stripped content from EncodingDetectFile
                from io import StringIO

                reader = csv.reader(StringIO(file_content), dialect)
                try:
                    raw_headers = next(reader)
                except StopIteration:
                    # empty file
                    self._last_load_warnings = list(warnings)
                    return 0, 0, []
                # Debug note: record detected delimiter and raw headers
                # Debug: record detected delimiter and raw headers for dev diagnostics, but do not treat them as user-visible warnings
                # print(f"CSV delimiter detected: {repr(dialect.delimiter)}")
                # print(f"CSV raw headers: {raw_headers}")
                # Clean BOM and whitespace from headers (remove BOM regardless of surrounding whitespace)
                cleaned = [ (h.replace("\ufeff", "") if h is not None else "").strip() for h in raw_headers ]

                headers = []
                seen = {}

                def make_unique(name, idx):
                    if name is None or name == "":
                        base = f"column_{idx + 1}"
                    else:
                        base = name
                    base_norm = self._normalize_key(base) or f"column_{idx + 1}"
                    # Ensure uniqueness
                    if base_norm in seen:
                        seen[base_norm] += 1
                        unique = f"{base_norm}_{seen[base_norm]}"
                    else:
                        seen[base_norm] = 1
                        unique = base_norm
                    return unique

                if not has_header:
                    # Treat first row as data; create Column_N keys and store first row
                    for idx, entry in enumerate(cleaned):
                        skey = make_unique(None, idx)
                        headers.append(skey)
                        # Clean data and append
                        value = entry
                        self.set_value(skey=skey, value=value, idx=-1, wtype=TYPE_CSV)
                    ct = 1
                else:
                    ct = 0
                    # Normalize headers and make unique
                    for idx, h in enumerate(cleaned):
                        skey = make_unique(h, idx)
                        headers.append(skey)
                # Now process remaining rows
                for row in reader:
                    for idx, entry in enumerate(row):
                        if idx >= len(headers):
                            # New header for extra column
                            newkey = make_unique(None, idx)
                            headers.append(newkey)
                        skey = headers[idx]
                        # Clean BOM and whitespace from data values too (remove BOM regardless of surrounding whitespace)
                        clean_entry = entry.replace("\ufeff", "").strip()
                        # Append...
                        self.set_value(
                            skey=skey, value=clean_entry, idx=-1, wtype=TYPE_CSV
                        )
                    ct += 1
        except (csv.Error, PermissionError, OSError, FileNotFoundError) as e:
            ct = 0
            headers = []
            warnings.append(f"Failed to load CSV file {filename}: {e}")
        # Save warnings for later inspection
        self._last_load_warnings = list(warnings)
        colcount = len(headers)
        return ct, colcount, headers
    def wordlist_delta(self, orgtext, increase):
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
            # it's the unmodified key...
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

    def push(self):
        """Stores the current content on the stack"""
        copied_content = {key: copy(entry) for key, entry in self.content.items()}
        self._stack.append(copied_content)

    def pop(self):
        """Restores the last added stack entry"""
        if len(self._stack) > 0:
            copied_content = self._stack[-1]
            self._stack.pop(-1)
            self.content = {}
            for key, entry in copied_content.items():
                self.content[key] = copy(entry)
        # print (f"pop was called, name now '{self.content['name']}'")
