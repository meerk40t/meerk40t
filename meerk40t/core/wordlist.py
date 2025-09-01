"""
Base wordlist class that holds some wordlist logic. Most of the interactions with wordlists are done in the
elements service.
"""

import csv
import json
import os
import re
from copy import copy
from datetime import datetime

from ..extra.encode_detect import EncodingDetectFile

TYPE_INDEX = 0
POSITION_INDEX = 1
DATA_START_INDEX = 2

TYPE_STATIC = 0
TYPE_CSV = 1
TYPE_COUNTER = 2


class Wordlist:
    """
    The Wordlist class provides some logic to hold, update and maintain a set of
    variables for text-fields (and later on for other stuff) to allow for
    on-the-fly recalculation / repopulation
    """

    # Constants for wordlist array indices
    TYPE_INDEX = 0
    POSITION_INDEX = 1
    DATA_START_INDEX = 2

    # Constants for wordlist types
    TYPE_STATIC = 0
    TYPE_CSV = 1
    TYPE_COUNTER = 2

    def __init__(self, versionstr, directory=None):
        # The content-dictionary contains an array per entry
        # index 0 indicates the type:
        #   0 (static) text entry
        #   1 text entry array coming from a csv file
        #   2 is a numeric counter
        # index 1 indicates the position of the current array (always 2 for type 0 and 2)
        # index 2 and onwards contain the actual data
        self.content = {
            "version": [TYPE_STATIC, 2, versionstr],
            "date": [TYPE_STATIC, 2, self.wordlist_datestr()],
            "time": [TYPE_STATIC, 2, self.wordlist_timestr()],
            "op_device": [TYPE_STATIC, 2, "<device>"],
            "op_speed": [TYPE_STATIC, 2, "<speed>"],
            "op_power": [TYPE_STATIC, 2, "<power>"],
            "op_passes": [TYPE_STATIC, 2, "<passes>"],
            "op_dpi": [TYPE_STATIC, 2, "<dpi>"],
        }
        self.prohibited = list(self.content.keys())
        self._stack = []
        self.transaction_open = False
        self.content_backup = {}
        if directory is None:
            directory = os.getcwd()
        self.default_filename = os.path.join(directory, "wordlist.json")
        self.load_data(self.default_filename)

    def add(self, key, value, wtype=None):
        self.add_value(key, value, wtype)

    def fetch(self, key):
        return self.fetch_value(key, None)

    def fetch_value(self, skey, idx):
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

        if 0 <= idx < len(wordlist):
            try:
                result = wordlist[idx]
            except IndexError:
                result = None
        return result

    def add_value(self, skey, value, wtype=None):
        skey = skey.lower()
        if skey not in self.content:
            if wtype is None:
                wtype = TYPE_STATIC
            self.content[skey] = [
                wtype,
                2,
            ]  # incomplete, as it will be appended right after this
        self.content[skey].append(value)

    def delete_value(self, skey, idx):
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

    def move_all_indices(self, delta):
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

    def set_value(self, skey, value, idx=None, wtype=None):
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
                try:
                    idx = int(idx)
                except ValueError:
                    idx = 0
            elif idx < 0:
                # append
                self.content[skey].append(value)
            else:  # Zerobased outside + 2 inside
                idx += 2

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

    def reset(self, skey=None):
        # Resets position
        if skey is None:
            for skey in self.content:
                self.content[skey][self.POSITION_INDEX] = self.DATA_START_INDEX
        else:
            skey = skey.lower()
            self.content[skey][self.POSITION_INDEX] = self.DATA_START_INDEX

    def translate(self, pattern, increment=True):
        """Translate bracketed patterns like {key} or {key#offset} to their values."""
        if not pattern:
            return ""

        result = str(pattern)
        replacements = {}

        # Find all bracketed patterns
        for bracketed_key in re.findall(r"\{[^}]+\}", result):
            key_content = bracketed_key[1:-1].lower().strip()

            # Parse the key and any modifiers
            key, offset = self._parse_key_and_offset(key_content)

            # Get the replacement value
            replacement = self._get_replacement_value(key, offset, increment)

            if replacement is not None:
                replacements[bracketed_key] = str(replacement)

        # Apply all replacements at once for efficiency
        for old, new in replacements.items():
            result = result.replace(old, new)

        return result

    def _parse_key_and_offset(self, key_content):
        """Parse key content and extract offset if present.

        Returns:
            tuple: (key, offset) where offset is 0 if not specified
        """
        if "#" not in key_content:
            return key_content, 0

        pos = key_content.find("#")
        key = key_content[:pos].strip()
        offset_str = key_content[pos + 1 :].strip()

        try:
            offset = int(offset_str)
        except ValueError:
            offset = 0

        return key, offset

    def _get_replacement_value(self, key, offset, increment):
        """Get the replacement value for a given key and offset."""
        # Handle special date/time keys
        if key == "date":
            return self._get_date_value(offset)
        elif key == "time":
            return self._get_time_value(offset)
        elif key.startswith("date@"):
            format_str = key[5:]  # Remove "date@" prefix
            return self.wordlist_datestr(format_str)
        elif key.startswith("time@"):
            format_str = key[5:]  # Remove "time@" prefix
            return self.wordlist_timestr(format_str)

        # Handle regular wordlist keys
        if key not in self.content:
            return None

        wordlist = self.content[key]
        wordlist_type = wordlist[0]  # TYPE_INDEX

        if wordlist_type == 2:  # Counter type
            return self._get_counter_value(wordlist, offset, increment)
        else:  # Static or CSV type
            return self._get_list_value(key, wordlist, offset, increment)

    def _get_date_value(self, offset):
        """Get date value, optionally with custom format."""
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

    def _get_time_value(self, offset):
        """Get time value, optionally with custom format."""
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

    def _get_counter_value(self, wordlist, offset, increment):
        """Get value from a counter-type wordlist."""
        try:
            value = int(wordlist[2])  # DATA_START_INDEX
        except (ValueError, IndexError):
            value = 0

        value += offset

        # Auto-increment if requested
        if increment:
            wordlist[2] = value + 1

        return value

    def _get_list_value(self, key, wordlist, offset, increment):
        """Get value from a static or CSV-type wordlist."""
        if offset != 0:
            # If offset is specified, use it directly as the target index
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
    def wordlist_datestr(sformat=None):
        time = datetime.now()
        if sformat is None:
            sformat = "%x"
        try:
            result = time.strftime(sformat)
        except ValueError:
            result = "invalid"
        return result

    @staticmethod
    def wordlist_timestr(sformat=None):
        time = datetime.now()
        if sformat is None:
            sformat = "%X"
        try:
            result = time.strftime(sformat)
        except ValueError:
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
        if filename is None:
            filename = self.default_filename
        try:
            with open(filename) as f:
                self.content = json.load(f)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        self.transaction_open = False

    def save_data(self, filename):
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
        except KeyError:
            return False
        return True

    def empty_csv(self):
        # remove all traces of the previous csv file
        names = [
            skey for skey in self.content if self.content[skey][TYPE_INDEX] == TYPE_CSV
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
        # print (f"push was called, when name was: '{self.content['name']}'")

    def pop(self):
        """Restores the last added stack entry"""
        if len(self._stack) > 0:
            copied_content = self._stack[-1]
            self._stack.pop(-1)
            self.content = {}
            for key, entry in copied_content.items():
                self.content[key] = copy(entry)
        # print (f"pop was called, name now '{self.content['name']}'")
