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
        if directory is None:
            directory = os.getcwd()
        self.default_filename = os.path.join(directory, "wordlist.json")
        self.load_data(self.default_filename)

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
        if idx is None or idx < 0:  # Default
            idx = wordlist[IDX_POSITION]

        if idx <= len(wordlist):
            try:
                result = wordlist[idx]
            except IndexError:
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
        skey = skey.lower()
        if skey not in self.content:
            if wtype is None:
                wtype = TYPE_STATIC
            self.content[skey] = [
                wtype,
                IDX_DATA_START,
            ]  # incomplete, as it will be appended right after this
        self.content[skey].append(value)

    def delete_value(self, skey, idx):
        """
        Delete a value from a wordlist variable at the specified index.

        Args:
            skey (str): Variable name (case-insensitive)
            idx (int): Zero-based index of the value to delete
        """
        skey = skey.lower()
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
        skey = skey.lower()
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
        skey = skey.lower()

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
        else:
            skey = skey.lower()
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
        except:
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
        except:
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
        try:
            with open(filename) as f:
                self.content = json.load(f)
        except (json.JSONDecodeError, PermissionError, OSError, FileNotFoundError):
            pass
        self.transaction_open = False

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
        try:
            self.content.pop(skey)
        except KeyError:
            pass

    def rename_key(self, oldkey, newkey):
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
        except:
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
        self.empty_csv()
        ct = 0
        headers = []
        decoder = EncodingDetectFile()
        result = decoder.load(filename)
        if result:
            encoding, bom_marker, file_content = result

            try:
                # Use the already BOM-stripped content from EncodingDetectFile
                from io import StringIO

                # Find a safe buffer that ends with a complete line
                # Look for the last newline within the first ~1024 characters
                buffer_limit = min(1024, len(file_content))
                last_newline = file_content.rfind("\n", 0, buffer_limit)
                if last_newline > 0:
                    buffer = file_content[: last_newline + 1]  # Include the newline
                else:
                    # Fallback to original behavior if no newline found
                    buffer = file_content[:buffer_limit]

                if force_header is None:
                    has_header = csv.Sniffer().has_header(buffer)
                else:
                    has_header = force_header
                # print (f"Header={has_header}, Force={force_header}")
                dialect = csv.Sniffer().sniff(buffer)
                reader = csv.reader(StringIO(file_content), dialect)
                headers = next(reader)
                # Clean BOM characters from headers
                headers = [h.lstrip("\ufeff") for h in headers]
                if not has_header:
                    # Use Line as Data and set some default names
                    for idx, entry in enumerate(headers):
                        skey = f"Column_{idx + 1}"
                        self.set_value(skey=skey, value=entry, idx=-1, wtype=TYPE_CSV)
                        headers[idx] = skey.lower()
                    ct = 1
                else:
                    ct = 0
                    # Lowercase headers for return value
                    headers = [h.lower() for h in headers]
                for row in reader:
                    for idx, entry in enumerate(row):
                        skey = headers[idx].lower().lstrip("\ufeff")
                        # Clean BOM from data values too
                        clean_entry = entry.lstrip("\ufeff")
                        # Append...
                        self.set_value(
                            skey=skey, value=clean_entry, idx=-1, wtype=TYPE_CSV
                        )
                    ct += 1
            except (csv.Error, PermissionError, OSError, FileNotFoundError) as e:
                ct = 0
                headers = []
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
