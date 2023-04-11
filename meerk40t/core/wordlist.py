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


class Wordlist:
    """
    The Wordlist class provides some logic to hold, update and maintain a set of
    variables for text-fields (and later on for other stuff) to allow for
    on-the-fly recalculation / repopulation
    """

    def __init__(self, versionstr, directory=None):
        # The content-dictionary contains an array per entry
        # index 0 indicates the type:
        #   0 (static) text entry
        #   1 text entry array coming from a csv file
        #   2 is a numeric counter
        # index 1 indicates the position of the current array (always 2 for type 0 and 2)
        # index 2 and onwards contain the actual data
        self.content = {
            "version": [0, 2, versionstr],
            "date": [0, 2, self.wordlist_datestr()],
            "time": [0, 2, self.wordlist_timestr()],
            "op_device": [0, 2, "<device>"],
            "op_speed": [0, 2, "<speed>"],
            "op_power": [0, 2, "<power>"],
            "op_passes": [0, 2, "<passes>"],
            "op_dpi": [0, 2, "<dpi>"],
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
        self._stack = list()
        self.transaction_open = False
        self.content_backup = {}
        if directory is None:
            directory = os.getcwd()
        self.default_filename = os.path.join(directory, "wordlist.json")
        self.load_data(self.default_filename)

    def add(self, key, value, wtype=None):
        self.add_value(key, value, wtype)

    def fetch(self, key):
        result = self.fetch_value(key, None)
        return result

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
            idx = wordlist[1]

        if idx <= len(wordlist):
            try:
                result = wordlist[idx]
            except IndexError:
                result = None
        return result

    def add_value(self, skey, value, wtype=None):
        skey = skey.lower()
        if skey not in self.content:
            if wtype is None:
                wtype = 0
            self.content[skey] = [
                wtype,
                2,
            ]  # incomplete, as it will be appended right after this
        self.content[skey].append(value)

    def delete_value(self, skey, idx):
        skey = skey.lower()
        if not skey in self.content:
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
            if wordlist[0] in (0, 1):  # Text or csv
                last_index = len(wordlist) - 1
                # Zero-based outside, +2 inside
                newidx = min(wordlist[1] + delta, last_index)
                if newidx < 2:
                    newidx = 2
                wordlist[1] = newidx
            elif wordlist[0] == 2:  # Counter-type
                value = wordlist[2]
                try:
                    value = int(value) + delta
                except ValueError:
                    value = 0
                if value < 0:
                    value = 0
                wordlist[2] = value

    def set_value(self, skey, value, idx=None, wtype=None):
        # Special treatment:
        # Index = None - use current
        # Index < 0 append
        skey = skey.lower()
        if not skey in self.content:
            # hasn't been there, so establish it
            if wtype is None:
                wtype = 0
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
            index = int(idx)
        else:
            relative = False
            index = idx
        wordlists = []

        if skey == "@all":  # Set it for all fields from a csv file
            wordlists.extend(self.content)
        else:
            wordlists.extend(list(skey.split(",")))
        for wkey in wordlists:
            wordlist = self.content[wkey]
            if (
                wordlist[0] in (0, 1) and wkey not in self.prohibited
            ):  # Variable Wordlist type.
                last_index = len(wordlist) - 1
                # Zero-based outside, +2 inside
                if relative:
                    self.content[wkey][1] = min(wordlist[1] + index, last_index)
                else:
                    self.content[wkey][1] = min(index + 2, last_index)

    def reset(self, skey=None):
        # Resets position
        skey = skey.lower()
        if skey is None:
            for skey in self.content:
                self.content[skey][1] = 2
        else:
            self.content[skey][1] = 2

    def translate(self, pattern, increment=True):
        result = pattern
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
                    value = self.fetch_value(key, 2)
                    if value is not None and isinstance(value, str) and len(value) > 0:
                        if "%" in value:
                            # Seems to be a format string, so let's try it...
                            sformat = value
                value = self.wordlist_datestr(sformat)
            elif key == "time":
                # Do we have a format str?
                sformat = None
                if key in self.content:
                    value = self.fetch_value(key, 2)
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
                    # This is not a wordlist name.
                    continue
                wordlist = self.content[key]

                if wordlist[0] == 2:  # Counter-type
                    # Counter index is the value.
                    value = wordlist[2] if not reset else 0
                    try:
                        value = int(value)
                    except ValueError:
                        value = 0
                    value += relative
                    if autoincrement and increment:
                        # autoincrement of counter means value + 1
                        wordlist[2] = value + 1
                else:
                    # This is a variable wordlist.
                    current_index = wordlist[1] if not reset else 0
                    current_index += relative
                    value = self.fetch_value(key, current_index)
                    if autoincrement and increment:
                        # Index set to current index + 1
                        wordlist[1] = current_index + 1

            if value is not None:
                result = result.replace(bracketed_key, str(value))

        return result

    @staticmethod
    def wordlist_datestr(format=None):
        time = datetime.now()
        if format is None:
            format = "%x"
        try:
            result = time.strftime(format)
        except:
            result = "invalid"
        return result

    @staticmethod
    def wordlist_timestr(format=None):
        time = datetime.now()
        if format is None:
            format = "%X"
        try:
            result = time.strftime(format)
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
        except (json.JSONDecodeError, PermissionError, OSError, FileNotFoundError):
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
        except:
            return False
        return True

    def empty_csv(self):
        # remove all traces of the previous csv file
        names = []
        for skey in self.content:
            if self.content[skey][0] == 1:  # csv
                names.append(skey)
        for skey in names:
            self.delete(skey)

    def load_csv_file(self, filename, force_header=None):
        self.empty_csv()
        headers = []
        try:
            with open(filename, newline="") as csvfile:
                buffer = csvfile.read(1024)
                if force_header is None:
                    has_header = csv.Sniffer().has_header(buffer)
                else:
                    has_header = force_header
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
                        # Append...
                        self.set_value(skey=skey, value=entry, idx=-1, wtype=1)
                    ct += 1
        except (csv.Error, PermissionError, OSError, FileNotFoundError):
            ct = 0
            headers = []
        colcount = len(headers)
        return ct, colcount, headers

    def wordlist_delta(self, orgtext, increase):
        newtext = str(orgtext)
        toreplace = []
        # list of tuples, (index found, old, new )
        # Lets gather the {} first...
        brackets = re.compile(r"\{[^}]+\}")
        for bracketed_key in brackets.findall(str(orgtext)):
            #            print(f"Key found: {bracketed_key}")
            newpattern = ""
            key = bracketed_key[1:-1].lower().strip()
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
                    # no need to do something
                    continue
                try:
                    # This covers +x, -x, x
                    relative = int(index_string)
                except ValueError:
                    relative = 0
            else:
                # it's the unmodified key...
                if key.startswith("time@"):
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
        # as we dont want to replace the same pattern again and again
        if increase >= 0:
            toreplace.sort(key=lambda n: n[0])
        else:
            toreplace.sort(reverse=True, key=lambda n: n[0])
        for item in toreplace:
            newtext = newtext.replace(item[1], item[2])
        return newtext

    def push(self):
        """ Stores the current content on the stack """
        copied_content = {}
        for key, entry in self.content.items():
            copied_content[key] = copy(entry)
        self._stack.append(copied_content)
        # print (f"push was called, when name was: '{self.content['name']}'")

    def pop(self):
        """ Restores the last added stack entry """
        if len(self._stack) > 0:
            copied_content = self._stack[-1]
            self._stack.pop(-1)
            self.content = {}
            for key, entry in copied_content.items():
                self.content[key] = copy(entry)
        # print (f"pop was called, name now '{self.content['name']}'")
