import csv
import json
import os
import re
from datetime import datetime


class Wordlist:
    """
    The Wordlist class provides some logic to hold, update and maintain a set of
    variables for text-fields (and later on for other stuff) to allow for
    on-the-fly recalculation / repopulation
    """

    def __init__(self, versionstr, directory=None):
        self.content = []
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
        }
        self.prohibited = (
            "version",
            "date",
            "time",
            "op_device",
            "op_speed",
            "op_power",
        )
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
            if wordlist[0] == 1:  # Variable Wordlist type.
                last_index = len(wordlist) - 1
                # Zero-based outside, +2 inside
                if relative:
                    wordlist[1] = min(wordlist[1] + index, last_index)
                else:
                    wordlist[1] = min(index + 2, last_index)

    def reset(self, skey=None):
        # Resets position
        skey = skey.lower()
        if skey is None:
            for skey in self.content:
                self.content[skey][1] = 2
        else:
            self.content[skey][1] = 2

    def translate(self, pattern):
        result = pattern
        brackets = re.compile(r"\{[^}]+\}")
        for bracketed_key in brackets.findall(result):
            key = bracketed_key[1:-1].lower()
            # Let's check whether we have a modifier at the end: #<num>
            if key.endswith("++"):
                autoincrement = True
                key = key[:-2]
            else:
                autoincrement = False

            reset = False
            relative = 0
            pos = key.find("#")
            if pos > 0:  # Needs to be after first character
                # Process offset modification.
                index_string = key[pos + 1 :]
                key = key[:pos]

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
                value = self.wordlist_datestr(None)
            elif key == "time":
                value = self.wordlist_timestr(None)
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
                    if autoincrement:
                        # autoincrement of counter means value + 1
                        wordlist[2] = value + 1
                else:
                    # This is a variable wordlist.
                    current_index = wordlist[1] if not reset else 0
                    current_index += relative
                    value = self.fetch_value(key, current_index)
                    if autoincrement:
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

    def load_data(self, filename):
        if filename is None:
            filename = self.default_filename
        try:
            with open(filename, "r") as f:
                self.content = json.load(f)
        except (json.JSONDecodeError, PermissionError, OSError, FileNotFoundError):
            pass

    def save_data(self, filename):
        if filename is None:
            filename = self.default_filename
        with open(filename, "w") as f:
            json.dump(self.content, f)

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
            with open(filename, newline="", mode="r") as csvfile:
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
