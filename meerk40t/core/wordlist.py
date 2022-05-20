from datetime import datetime
import csv
import re
import pickle

class Wordlist():
    """
    The Wordlist class provides some logic to hold, update and maintain a set of
    variables for text-fields (and later on for other stuff) to allow for
    on-the-fly recalculation / repopulation
    """
    def __init__(self, versionstr):
        self.content = []
        # The content-dictionary contains an array per entry
        # index 0 indicates the type:
        #   0 (static) text entry
        #   1 text entry array coming from a csv file
        #   2 is a numeric counter
        # index 1 indicates the position of the current array (always 2 for type 0 and 2)
        # index 2 and onwards contain the actual data
        self.content = {"version": [0, 2, versionstr],
        "date": [0, 2, self.wordlist_datestr()],
        "time": [0, 2, self.wordlist_timestr()]}

    def add(self, key, value, type=None):
        self.add_value(key, value, type)

    def fetch(self, key):
        result = self.fetch_value(key, None)
        return result

    def fetch_value(self, skey, idx):
        skey = skey.lower()
        try:
            wordlist = self.content[skey]
        except KeyError:
            return None
        if idx is None: # Default
            idx = wordlist[1]

        if (idx>len(wordlist)):
            idx = len(wordlist) - 1
        try:
            result = wordlist[idx]
        except IndexError:
            result = None
        return result

    def add_value(self, skey, value, type=None):
        skey = skey.lower()
        if skey not in self.content:
            if type is None:
                type = 0
            self.content[skey] = [type, 2] # incomplete, as it will be appended right after this
        self.content[skey].append(value)

    def set_value(self, skey, value, idx = None, type = None):
        # Special treatment:
        # Index = None - use current
        # Index < 0 append
        skey = skey.lower()
        if not skey in self.content:
            # hasnt been there, so establish it
            if type is None:
                type = 0
            self.content[skey] = [type, 2, value]
        else:
            if idx is None:
                # use current position
                idx = self.content[skey][1]
            elif idx<0:
                # append
                self.content[skey].append(value)
            else: # Zerobased outside + 2 inside
                idx += 2

            if idx>=len(self.content[skey]):
                idx = len(self.content[skey]) - 1
            self.content[skey][idx] = value

    def set_index(self, skey, idx, type = None):
        skey = skey.lower()
        if idx is None:
            idx = 2
        else: # Zerobased outside + 2 inside
            idx += 2
        print("index", skey, idx)
        if skey=="@all": # Set it for all fields from a csv file
            for skey in self.content:
                maxlen = len(self.content[skey]) - 1
                if self.content[skey][0] == 1: # csv
                    self.content[skey][1] = min(idx, maxlen)
        else:
            if idx>=len(self.content[skey]):
                idx = 2
            self.content[skey][1] = idx

    #def debug_me(self, header):
    #    print ("Wordlist (%s):" % header)
    #    for key in self.content:
    #        print ("Key: %s" % key, self.content[key])

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
        for vkey in brackets.findall(result):
            skey = vkey[1:-1].lower()
            # Lets check whether we have a modifier at the end: #<num>
            index= None
            idx = skey.find("#")
            if idx>0: # Needs to be after first character
                idx_str = skey[idx+1:]
                skey = skey [:idx]
                if skey in self.content:
                    curridx = self.content[skey][1]
                    currval = self.content[skey][2]
                else:
                    continue
                try:
                    relative = int(idx_str)
                except ValueError:
                    relative = 0
                if curridx == self.content[skey][0] == 2: # Counter
                    if idx_str.startswith("+") or idx_str.startswith("-"):
                        value = currval + relative
                    else:
                        value = relative
                else:
                    if idx_str.startswith("+") or idx_str.startswith("-"):
                        index = curridx + relative
                    else:
                        index = relative
                    value = self.fetch_value(skey, index)
            else:
                value = self.fetch_value(skey, index)

            # And now date and time...
            if skey== "date":
                value = self.wordlist_datestr(None)
            elif skey == "time":
                value = self.wordlist_timestr(None)
            elif skey.startswith("date@"):
                format = skey[5:]
                value = self.wordlist_datestr(format)
            elif skey.startswith("time@"):
                format = skey[5:]
                value = self.wordlist_timestr(format)
            if not value is None:
                result = result.replace(vkey, str(value))

        return result

    @staticmethod
    def wordlist_datestr(format = None):
        time = datetime.now()
        if format is None:
            format = "%x"
        try:
            result = time.strftime(format)
        except:
            result="invalid"
        return result

    @staticmethod
    def wordlist_timestr(format = None):
        time = datetime.now()
        if format is None:
            format = "%X"
        try:
            result = time.strftime(format)
        except ValueError:
            result="invalid"
        return result

    def get_variable_list(self):
        choices = []
        for skey in self.content:
            value = self.fetch(skey)
            svalue = skey + " (" + value + ")"
            choices.append(svalue)
        return choices

    def load_data(self, filename):
        try:
            with open(filename, 'rb') as f:
                self.content = pickle.load(f)
        except:
            pass

    def save_data(self, filename):
        try:
            with open(filename, 'wb') as f:
                pickle.dump(self.content, f)
        except:
            pass

    def empty_csv(self):
        # remove all traces of the previous csv file
        names=[]
        for skey in self.content:
            if self.content[skey][0] == 1: # csv
                names.append (skey)
        for skey in names:
            try:
                self.content.pop(skey)
            except KeyError:
                pass

    def load_csv_file(self, filename):
        self.empty_csv()
        headers = []
        with open(filename, newline='', mode='r') as csvfile:
            buffer = csvfile.read(1024)
            has_header = csv.Sniffer().has_header(buffer)
            dialect = csv.Sniffer().sniff(buffer)
            csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)
            headers = next(reader)
            if not has_header:
                # USe Line as Data amd set some default names
                for idx, entry in enumerate(headers):
                    skey = "Column_{ct}".format(ct=idx + 1)
                    self.set_value(skey=skey, value=entry, idx=-1, type=1)
                    headers[idx] = skey
                ct = 1
            else:
                ct = 0
            for row in reader:
                for idx, entry in enumerate(row):
                    skey = headers[idx]
                    # Append...
                    self.set_value(skey=skey, value=entry, idx=-1, type=1)
                ct += 1

        colcount = len(headers)
        return ct, colcount, headers

    def edit(self):
        return
