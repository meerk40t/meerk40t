from datetime import datetime
import csv
import re
import pickle
import wx
import os

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
        self.default_filename = os.path.join(os.getcwd(), "wordlist.pkl")
        # For Grid editing
        self.cur_skey = None
        self.cur_index = None
        self.to_save = None

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
        if filename is None:
            filename = self.default_filename
        try:
            with open(filename, 'rb') as f:
                self.content = pickle.load(f)
        except:
            pass

    def save_data(self, filename):
        if filename is None:
            filename = self.default_filename
        try:
            with open(filename, 'wb') as f:
                pickle.dump(self.content, f)
        except:
            pass

    def delete(self, skey):
        try:
            self.content.pop(skey)
        except KeyError:
            pass

    def empty_csv(self):
        # remove all traces of the previous csv file
        names=[]
        for skey in self.content:
            if self.content[skey][0] == 1: # csv
                names.append (skey)
        for skey in names:
            self.delete(skey)

    def load_csv_file(self, filename):
        print ("Load csv from %s" % filename)
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
                # Use Line as Data amd set some default names
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

        self.dialog = wx.Dialog(None, wx.ID_ANY, "")
        self.dialog.SetTitle("Edit Wordlist")

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_csv = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_csv, 0, wx.EXPAND, 0)

        label_1 = wx.StaticText(self.dialog, wx.ID_ANY, "Import CSV-File")
        sizer_csv.Add(label_1, 0, 0, 0)

        self.txt_filename = wx.TextCtrl(self.dialog, wx.ID_ANY, "")
        sizer_csv.Add(self.txt_filename, 1, 0, 0)

        self.btn_fileDialog = wx.Button(self.dialog, wx.ID_ANY, "...")
        self.btn_fileDialog.SetMinSize((23, 23))
        sizer_csv.Add(self.btn_fileDialog, 0, 0, 0)

        self.btn_import = wx.Button(self.dialog, wx.ID_ANY, "Import CSV")
        sizer_csv.Add(self.btn_import, 0, 0, 0)

        sizer_index = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_index, 0, wx.EXPAND, 0)

        label_2 = wx.StaticText(self.dialog, wx.ID_ANY, "Current Index for Data:")
        sizer_index.Add(label_2, 0, 0, 0)

        self.cbo_Index = wx.ComboBox(self.dialog, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN|wx.CB_READONLY)
        sizer_index.Add(self.cbo_Index, 0, 0, 0)

        sizer_vdata = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(sizer_vdata, 1, wx.EXPAND, 0)

        sizer_hdata = wx.BoxSizer(wx.VERTICAL)
        sizer_vdata.Add(sizer_hdata, 1, wx.EXPAND, 0)

        sizer_grids = wx.BoxSizer(wx.HORIZONTAL)
        sizer_hdata.Add(sizer_grids, 1, wx.EXPAND, 0)

        self.grid_wordlist = wx.ListCtrl(self.dialog, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL)
        sizer_grids.Add(self.grid_wordlist, 1, wx.ALL | wx.EXPAND, 1)

        self.grid_content = wx.ListCtrl(self.dialog, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL | wx.LC_EDIT_LABELS)
        sizer_grids.Add(self.grid_content, 1, wx.ALL | wx.EXPAND, 1)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_hdata.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.txt_pattern = wx.TextCtrl(self.dialog, wx.ID_ANY, "")
        sizer_buttons.Add(self.txt_pattern, 1, 0, 0)

        self.btn_add = wx.Button(self.dialog, wx.ID_ANY, "Add Text")
        self.btn_add.SetToolTip("Add another wordlist entry")
        sizer_buttons.Add(self.btn_add, 0, 0, 0)

        self.btn_add_counter = wx.Button(self.dialog, wx.ID_ANY, "Add Counter")
        sizer_buttons.Add(self.btn_add_counter, 0, 0, 0)

        self.btn_delete = wx.Button(self.dialog, wx.ID_ANY, "Delete")
        self.btn_delete.SetToolTip("Delete the current wordlist entry")
        sizer_buttons.Add(self.btn_delete, 0, 0, 0)
        self.lbl_message = wx.StaticText(self.dialog, wx.ID_ANY, "")
        sizer_buttons.Add(self.lbl_message, 1, 0, 0)


        sizer_exit = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_exit, 0, wx.ALL, 4)

        self.btn_backup = wx.Button(self.dialog, wx.ID_ANY, "Backup Wordlist")
        self.btn_backup.SetToolTip("Save current wordlist to disk")
        sizer_exit.Add(self.btn_backup, 0, 0, 0)

        self.btn_restore = wx.Button(self.dialog, wx.ID_ANY, "Restore Wordlist")
        self.btn_restore.SetToolTip("Load wordlist from disk")
        sizer_exit.Add(self.btn_restore, 0, 0, 0)

        sizer_exit.Add((100, 20), 0, 0, 0)

        self.button_OK = wx.Button(self.dialog, wx.ID_OK, "")
        self.button_OK.SetDefault()
        sizer_exit.Add(self.button_OK, 0, 0, 0)

        self.dialog.SetSizer(sizer_1)
        sizer_1.Fit(self.dialog)

        self.dialog.SetAffirmativeId(self.button_OK.GetId())

        self.dialog.Layout()

        self.btn_add.Bind(wx.EVT_BUTTON, self.on_btn_add)
        self.btn_add_counter.Bind(wx.EVT_BUTTON, self.on_add_counter)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_btn_delete)
        self.btn_backup.Bind(wx.EVT_BUTTON, self.on_backup)
        self.btn_restore.Bind(wx.EVT_BUTTON, self.on_restore)
        self.btn_fileDialog.Bind(wx.EVT_BUTTON, self.on_btn_file)
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_btn_import)
        self.txt_filename.Bind(wx.EVT_TEXT, self.on_filetext_change)
        self.txt_pattern.Bind(wx.EVT_TEXT, self.on_patterntext_change)
        self.cbo_Index.Bind(wx.EVT_COMBOBOX, self.on_cbo_select)
        self.grid_wordlist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_grid_wordlist)
        self.grid_content.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_grid_content)
        self.grid_content.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_begin_edit)
        self.grid_content.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_edit)

        self.btn_import.Enable(False)
        self.populate_gui()

        self.dialog.ShowModal()
        self.dialog.Destroy()

    def refresh_grid_wordlist(self):
        self.grid_wordlist.ClearAll()
        self.cur_skey = None
        self.grid_wordlist.InsertColumn(0, "Type")
        self.grid_wordlist.InsertColumn(1, "Name")
        self.grid_wordlist.InsertColumn(2, "Index")
        typestr= ["Text", "CSV", "Counter"]
        for skey in self.content:
            index = self.grid_wordlist.InsertItem(self.grid_wordlist.GetItemCount(), typestr[self.content[skey][0]])
            self.grid_wordlist.SetItem(index, 1, skey)
            self.grid_wordlist.SetItem(index, 2, str(self.content[skey][1] - 2))

    def get_column_text(self, grid, index, col):
        item = grid.GetItem(index, col)
        return item.GetText()

    def refresh_grid_content(self, skey, current):
        self.grid_content.ClearAll()
        self.cur_skey = skey
        self.cur_index = None
        self.grid_content.InsertColumn(0, "Content")
        for idx in range(2, len(self.content[skey])):
            index = self.grid_content.InsertItem(self.grid_content.GetItemCount(), str(self.content[skey][idx]))
            if idx==current+2:
                self.grid_content.SetItemTextColour(index, wx.RED)

    def on_grid_wordlist(self, event):
        current_item = event.Index
        skey = self.get_column_text(self.grid_wordlist, current_item, 1)
        try:
            current = int(self.get_column_text(self.grid_wordlist, current_item, 2))
        except ValueError:
            current = 0
        self.refresh_grid_content(skey, current)
        self.txt_pattern.SetValue(skey)
        event.Skip()

    def on_grid_content(self, event):
        # Single Click
        event.Skip()

    def on_begin_edit(self, event):
        index = self.grid_content.GetFirstSelected()
        if index>=0:
            self.cur_index = index
        self.to_save = (self.cur_skey, self.cur_index)
        event.Allow()

    def on_end_edit(self, event):
        if self.to_save is None:
            self.edit_message("Update failed")
        else:
            skey = self.to_save[0]
            index = self.to_save[1]
            value = event.GetText()
            self.set_value(skey, value, index)
        self.to_save = None
        event.Allow()

    def populate_gui(self):
        self.cbo_Index.Clear()
        self.cbo_Index.Enable(False)
        maxidx = -1
        self.grid_content.ClearAll()
        self.refresh_grid_wordlist()
        for skey in self.content:
            if self.content[skey][0] == 1: # CSV
                i = len(self.content[skey]) - 2
                if i>maxidx:
                    maxidx = i
        if maxidx>=0:
            for i in range(maxidx + 1):
                self.cbo_Index.Append(str(i))
            self.cbo_Index.SetValue("0")
        self.cbo_Index.Enable(True)

    def edit_message(self, text):
        self.lbl_message.Label = text
        self.lbl_message.Refresh()

    def on_cbo_select(self, event):
        try:
            idx = int(self.cbo_Index.GetValue())
        except:
            idx = 0
        self.set_index(skey="@all", idx=idx)
        selidx = self.grid_wordlist.GetFirstSelected()
        if selidx<0:
            selidx = 0
        self.refresh_grid_wordlist()
        self.grid_wordlist.Select(selidx, True)

    def on_btn_add(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey)>0:
            if skey in self.content:
                self.delete(skey)
            self.add_value(skey, "---", 0)
            self.populate_gui()
        event.Skip()

    def on_filetext_change(self, event):
        myfile = self.txt_filename.GetValue()
        enab = False
        if os.path.exists(myfile):
            enab = True
        self.btn_import.Enable(enab)

    def on_patterntext_change(self, event):
        enab = len(self.txt_pattern.GetValue())>0
        self.btn_add.Enable(enab)
        self.btn_add_counter.Enable(enab)
        self.btn_delete.Enable(enab)

    def on_btn_file(self, event):
        mydlg = wx.FileDialog(
            self.dialog, message="Choose a csv-file",
            wildcard="CSV-Files (*.csv)|*.csv|Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW
            )
        if mydlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            myfile = mydlg.GetPath()
            self.txt_filename.SetValue(myfile)
        mydlg.Destroy()

    def on_btn_import(self, event):
        myfile = self.txt_filename.GetValue()
        if os.path.exists(myfile):
            ct, colcount, headers = self.load_csv_file(myfile)
            msg ="Imported file, {col} fields, {row} rows".format(col=colcount, row = ct)
            self.edit_message(msg)
            self.populate_gui()

    def on_add_counter(self, event):  # wxGlade: editWordlist.<event_handler>
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey)>0:
            if skey in self.content:
                self.delete(skey)
            self.add_value(skey, 1, 2)
            self.populate_gui()
        event.Skip()

    def on_btn_delete(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey)>0:
            self.delete(skey)
            self.populate_gui()
        event.Skip()

    def on_backup(self, event):  # wxGlade: editWordlist.<event_handler>
        if not self.default_filename is None:
            self.save_data(self.default_filename)
            msg = "Saved wordlist to " +  self.default_filename
            self.edit_message(msg)
        event.Skip()

    def on_restore(self, event):  # wxGlade: editWordlist.<event_handler>
        if not self.default_filename is None:
            self.load_data(self.default_filename)
            msg = "Loaded wordlist from " +  self.default_filename
            self.edit_message(msg)
            self.populate_gui()
        event.Skip()
