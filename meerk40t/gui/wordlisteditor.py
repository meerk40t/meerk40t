import os
import wx

from .icons import icons8_curly_brackets_50
from .mwindow import MWindow

_ = wx.GetTranslation

class WordlistPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.wlist = self.context.elements.mywordlist
        # For Grid editing
        self.cur_skey = None
        self.cur_index = None
        self.to_save = None

        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_csv = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_csv, 0, wx.EXPAND, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, _("Import CSV-File"))
        sizer_csv.Add(label_1, 0, 0, 0)

        self.txt_filename = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_csv.Add(self.txt_filename, 1, 0, 0)

        self.btn_fileDialog = wx.Button(self, wx.ID_ANY, "...")
        self.btn_fileDialog.SetMinSize((23, 23))
        sizer_csv.Add(self.btn_fileDialog, 0, 0, 0)

        self.btn_import = wx.Button(self, wx.ID_ANY, _("Import CSV"))
        sizer_csv.Add(self.btn_import, 0, 0, 0)

        sizer_index = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_index, 0, wx.EXPAND, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("Current Index for Data:"))
        sizer_index.Add(label_2, 0, 0, 0)

        self.cbo_Index = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN|wx.CB_READONLY)
        sizer_index.Add(self.cbo_Index, 0, 0, 0)

        sizer_vdata = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(sizer_vdata, 1, wx.EXPAND, 0)

        sizer_hdata = wx.BoxSizer(wx.VERTICAL)
        sizer_vdata.Add(sizer_hdata, 1, wx.EXPAND, 0)

        sizer_grids = wx.BoxSizer(wx.HORIZONTAL)
        sizer_hdata.Add(sizer_grids, 1, wx.EXPAND, 0)

        self.grid_wordlist = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL)
        sizer_grids.Add(self.grid_wordlist, 1, wx.ALL | wx.EXPAND, 1)

        self.grid_content = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL | wx.LC_EDIT_LABELS)
        sizer_grids.Add(self.grid_content, 1, wx.ALL | wx.EXPAND, 1)

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_hdata.Add(sizer_buttons, 0, wx.EXPAND, 0)

        self.txt_pattern = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_buttons.Add(self.txt_pattern, 1, 0, 0)

        self.btn_add = wx.Button(self, wx.ID_ANY, _("Add Text"))
        self.btn_add.SetToolTip(_("Add another wordlist entry"))
        sizer_buttons.Add(self.btn_add, 0, 0, 0)

        self.btn_add_counter = wx.Button(self, wx.ID_ANY, _("Add Counter"))
        sizer_buttons.Add(self.btn_add_counter, 0, 0, 0)

        self.btn_delete = wx.Button(self, wx.ID_ANY, _("Delete"))
        self.btn_delete.SetToolTip(_("Delete the current wordlist entry"))
        sizer_buttons.Add(self.btn_delete, 0, 0, 0)
        self.lbl_message = wx.StaticText(self, wx.ID_ANY, "")
        sizer_buttons.Add(self.lbl_message, 1, 0, 0)


        sizer_exit = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_exit, 0, wx.ALL, 4)

        self.btn_backup = wx.Button(self, wx.ID_ANY, _("Backup Wordlist"))
        self.btn_backup.SetToolTip(_("Save current wordlist to disk"))
        sizer_exit.Add(self.btn_backup, 0, 0, 0)

        self.btn_restore = wx.Button(self, wx.ID_ANY, _("Restore Wordlist"))
        self.btn_restore.SetToolTip(_("Load wordlist from disk"))
        sizer_exit.Add(self.btn_restore, 0, 0, 0)

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)

        self.Layout()

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

    def pane_show(self):
        self.populate_gui()
        self.grid_wordlist.SetFocus()

    def pane_hide(self):
        pass

    def refresh_grid_wordlist(self):
        self.grid_wordlist.ClearAll()
        self.cur_skey = None
        self.grid_wordlist.InsertColumn(0, _("Type"))
        self.grid_wordlist.InsertColumn(1, _("Name"))
        self.grid_wordlist.InsertColumn(2, _("Index"))
        typestr= [_("Text"), _("CSV"), _("Counter")]
        for skey in self.wlist.content:
            index = self.grid_wordlist.InsertItem(self.grid_wordlist.GetItemCount(), typestr[self.wlist.content[skey][0]])
            self.grid_wordlist.SetItem(index, 1, skey)
            self.grid_wordlist.SetItem(index, 2, str(self.wlist.content[skey][1] - 2))

    def get_column_text(self, grid, index, col):
        item = grid.GetItem(index, col)
        return item.GetText()

    def refresh_grid_content(self, skey, current):
        self.grid_content.ClearAll()
        self.cur_skey = skey
        self.cur_index = None
        self.grid_content.InsertColumn(0, _("Content"))
        for idx in range(2, len(self.wlist.content[skey])):
            index = self.grid_content.InsertItem(self.grid_content.GetItemCount(), str(self.wlist.content[skey][idx]))
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
            self.edit_message(_("Update failed"))
        else:
            skey = self.to_save[0]
            index = self.to_save[1]
            value = event.GetText()
            self.wlist.set_value(skey, value, index)
        self.to_save = None
        event.Allow()

    def populate_gui(self):
        self.cbo_Index.Clear()
        self.cbo_Index.Enable(False)
        maxidx = -1
        self.grid_content.ClearAll()
        self.refresh_grid_wordlist()
        for skey in self.wlist.content:
            if self.wlist.content[skey][0] == 1: # CSV
                i = len(self.wlist.content[skey]) - 2
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
        except ValueError:
            idx = 0
        self.wlist.set_index(skey="@all", idx=idx)
        selidx = self.grid_wordlist.GetFirstSelected()
        if selidx<0:
            selidx = 0
        self.refresh_grid_wordlist()
        self.grid_wordlist.Select(selidx, True)

    def on_btn_add(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey)>0:
            if skey in self.wlist.content:
                self.wlist.delete(skey)
            self.wlist.add_value(skey, "---", 0)
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
            self, message=_("Choose a csv-file"),
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
            ct, colcount, headers = self.wlist.load_csv_file(myfile)
            msg =_("Imported file, {col} fields, {row} rows").format(col=colcount, row = ct)
            self.edit_message(msg)
            self.populate_gui()

    def on_add_counter(self, event):  # wxGlade: editWordlist.<event_handler>
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey)>0:
            if skey in self.wlist.content:
                self.wlist.delete(skey)
            self.wlist.add_value(skey, 1, 2)
            self.populate_gui()
        event.Skip()

    def on_btn_delete(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey)>0:
            self.wlist.delete(skey)
            self.populate_gui()
        event.Skip()

    def on_backup(self, event):
        if not self.wlist.default_filename is None:
            self.wlist.save_data(self.wlist.default_filename)
            msg = _("Saved to ") +  self.wlist.default_filename
            self.edit_message(msg)
        event.Skip()

    def on_restore(self, event):
        if not self.wlist.default_filename is None:
            self.wlist.load_data(self.wlist.default_filename)
            msg = _("Loaded from ") +  self.wlist.default_filename
            self.edit_message(msg)
            self.populate_gui()
        event.Skip()

class WordlistEditor(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 530, *args, **kwds)

        self.panel = WordlistPanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_curly_brackets_50.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle(_("Wordlist Editor"))

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/config/Wordlist",
            {
                "label": _("Wordlist"),
                "icon": icons8_curly_brackets_50,
                "tip": _("Manages Wordlist-Entries"),
                "action": lambda v: kernel.console("window toggle Wordlist\n"),
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
