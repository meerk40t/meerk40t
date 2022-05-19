from datetime import datetime
import csv
import re

class clsWordlist():
    """
    The Wordlist class provides some logic to hold, update and maintain Make Raster turns an iterable of elements and a bounds into an image of the designated size, taking into account
    the step size. The physical pixels in the image is reduced by the step size then the matrix for the element is
    scaled up by the same amount. This makes step size work like inverse dpi and correctly sets the image scale to
    the step scale for 1:1 sizes independent of the scale.

    This function requires both wxPython and Pillow.

    @param nodes: elements to render.
    @param bounds: bounds of those elements for the viewport.
    @param width: desired width of the resulting raster
    @param height: desired height of the resulting raster
    @param bitmap: bitmap to use rather than provisioning
    @param step: raster step rate, int scale rate of the image.
    @return:
    """
    def __init__(self, versionstr):
        self.content = []
        self.content = {"version": [1, versionstr],
        "date": [1, self.wordlist_datestr()],
        "time": [1, self.wordlist_timestr()]}
        self.specialkeys = {
            "date": self.wordlist_datestr,
            "time": self.wordlist_timestr,
        }


    def add(self, key, value):
        if key not in self.content:
            self.content[key] = [1]
        self.content[key].append(value)

    def fetch(self, key):
        try:
            wordlist = self.content[key]
        except KeyError:
            return None

        try:
            wordlist[0] += 1
            return wordlist[wordlist[0]]
        except IndexError:
            wordlist[0] = 1
            return wordlist[wordlist[0]]

    def reset(self, key=None):
        if key is None:
            for key in self.content:
                self.content[key][0] = 1
        else:
            self.content[key][0] = 1

    def translate(self, pattern):
        result = pattern
        brackets = re.compile(r"\{[^}]+\}")
        for vkey in brackets.findall(result):
            skey = vkey[1:-1]
            value = self.fetch(skey)

            if skey in self.specialkeys:
                value = self.specialkeys[skey]()
            # And now date and time...
            if skey.startswith("date@"):
                format = skey[5:]
                value = self.wordlist_datestr(format)
            elif skey.startswith("time@"):
                format = skey[5:]
                value = self.wordlist_timestr(format)
            if not value is None:
                result = result.replace(vkey, value)

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

    def load_csv_file(self, filename):
        choices = []
        with open(filename, newline='') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(1024))
            print ("Dialect", dialect)
            csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)
            ct = 0
            for row in reader:
                ct += 1
                print ("Row #" % ct, row)

        colcount = len(choices)
        return colcount, choices

    def eof_csv(self):
        return True

    def advance_csv(self):
        # Switch to the next entry in the csv-file
        # return false if eof (will stick with the last)
        return False