import os
import re

import wx
from wx import aui

from ..extra.encode_detect import EncodingDetectFile
from ..kernel import signal_listener
from .icons import (
    get_default_icon_size,
    icon_add_new,
    icon_edit,
    icon_trash,
    icons8_circled_left,
    icons8_circled_right,
    icons8_curly_brackets,
    icons8_paste,
)
from .mwindow import MWindow
from .wxutils import (
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxListCtrl,
    wxRadioBox,
    wxStaticBitmap,
    wxStaticText,
)

_ = wx.GetTranslation


def register_panel_wordlist(window, context):
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(150, 25)
        .FloatingSize(150, 35)
        .Caption(_("Wordlist"))
        .CaptionVisible(not context.pane_lock)
        .Name("wordlist")
        .Hide()
    )
    pane.dock_proportion = 225
    pane.control = WordlistMiniPanel(window, wx.ID_ANY, context=context)
    pane.submenu = "_50_" + _("Tools")
    pane.helptext = _("Display wordlist advancement controls")
    window.on_pane_create(pane)
    context.register("pane/wordlist", pane)


class WordlistMiniPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("wordlist")

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_edit = wxButton(self, wx.ID_ANY, _("Edit"))
        self.button_edit.SetBitmap(
            icons8_curly_brackets.GetBitmap(resize=0.5 * get_default_icon_size(self.context))
        )
        self.button_edit.SetToolTip(_("Manages Wordlist-Entries"))

        self.button_next = wxButton(self, wx.ID_ANY, _("Next"))
        self.button_next.SetBitmap(
            icons8_circled_right.GetBitmap(resize=0.5 * get_default_icon_size(self.context))
        )
        self.button_next.SetToolTip(
            _("Wordlist: go to next page (right-click to next entry)")
        )

        self.button_prev = wxButton(self, wx.ID_ANY, _("Prev"))
        self.button_prev.SetBitmap(
            icons8_circled_left.GetBitmap(resize=0.5 * get_default_icon_size(self.context))
        )
        self.button_prev.SetToolTip(
            _("Wordlist: go to previous page (right-click to previous entry)")
        )

        main_sizer.Add(self.button_prev, 1, wx.EXPAND, 0)
        main_sizer.Add(self.button_edit, 1, wx.EXPAND, 0)
        main_sizer.Add(self.button_next, 1, wx.EXPAND, 0)

        self.button_next.Bind(wx.EVT_BUTTON, self.on_button_next_page)
        self.button_prev.Bind(wx.EVT_BUTTON, self.on_button_prev_page)
        self.button_next.Bind(wx.EVT_RIGHT_DOWN, self.on_button_next)
        self.button_prev.Bind(wx.EVT_RIGHT_DOWN, self.on_button_prev)
        self.button_edit.Bind(wx.EVT_BUTTON, self.on_button_edit)

        self.SetSizer(main_sizer)
        self.Layout()

    def establish_max_delta(self):
        # try to establish the needed delta to satisfy all variables...
        deltamin = 0
        deltamax = 0
        for node in self.context.elements.elems():
            sample = ""
            if node.type == "elem text":
                if node.text is not None:
                    sample = str(node.text)
            elif node.type == "elem path" and hasattr(node, "mktext"):
                if node.mktext is not None:
                    sample = str(node.mktext)
            if sample == "":
                continue
            # we can be rather agnostic on the individual variable,
            # we are interested in the highest {variable#+offset} pattern
            brackets = re.compile(r"\{[^}]+\}")
            for bracketed_key in brackets.findall(sample):
                #            print(f"Key found: {bracketed_key}")
                key = bracketed_key[1:-1].lower().strip()
                relative = 0
                pos = key.find("#")
                if pos > 0:  # Needs to be after first character
                    # Process offset modification.
                    index_string = key[pos + 1 :]
                    key = key[:pos].strip()
                    if index_string.startswith("+") or index_string.startswith("-"):
                        try:
                            # This covers +x, -x, x
                            relative = int(index_string)
                        except ValueError:
                            relative = 0
                deltamin = min(relative, deltamin)
                deltamax = max(relative, deltamax)

        return deltamax

    def on_button_edit(self, event):
        self.context("window toggle Wordlist\n")

    def on_button_prev(self, event):
        self.context.elements.wordlist_advance(-1)

    def on_button_prev_page(self, event):
        delta = self.establish_max_delta()
        self.context.elements.wordlist_advance(-1 - delta)

    def on_button_next(self, event):
        self.context.elements.wordlist_advance(+1)

    def on_button_next_page(self, event):
        delta = self.establish_max_delta()
        self.context.elements.wordlist_advance(+1 + delta)


class WordlistPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("wordlist")
        self.parent_panel = None
        self.wlist = self.context.elements.mywordlist
        self.current_entry = None
        # For Grid editing
        self.cur_skey = None
        self.cur_index = None
        self.to_save_content = None
        self.to_save_wordlist = None

        self.context.setting(bool, "wordlist_autosave", False)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_grids = wx.BoxSizer(wx.HORIZONTAL)
        sizer_grid_left = wx.BoxSizer(wx.VERTICAL)
        sizer_grid_right = wx.BoxSizer(wx.VERTICAL)
        sizer_grids.Add(sizer_grid_left, 1, wx.EXPAND, 0)
        sizer_grids.Add(sizer_grid_right, 1, wx.EXPAND, 0)

        sizer_index_left = wx.BoxSizer(wx.HORIZONTAL)
        sizer_grid_left.Add(sizer_index_left, 0, wx.EXPAND, 0)

        label_2 = wxStaticText(self, wx.ID_ANY, _("Start Index for CSV-based data:"))
        sizer_index_left.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.cbo_Index = wxComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        sizer_index_left.Add(self.cbo_Index, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.grid_wordlist = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES
            | wx.LC_REPORT
            | wx.LC_VRULES
            | wx.LC_SINGLE_SEL
            | wx.LC_EDIT_LABELS,
            context=self.context,
            list_name="list_wordlist"
        )
        sizer_grid_left.Add(self.grid_wordlist, 1, wx.EXPAND, 0)

        self.grid_content = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES
            | wx.LC_REPORT
            | wx.LC_VRULES
            | wx.LC_SINGLE_SEL
            | wx.LC_EDIT_LABELS,
            context=self.context,
            list_name="list_wordlist_content",
        )

        sizer_edit_wordlist_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_edit_content_buttons = wx.BoxSizer(wx.HORIZONTAL)

        dummylabel = wxStaticText(self, wx.ID_ANY, " ")
        sizer_index_left.Add(dummylabel, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_index_left.Add(
            sizer_edit_wordlist_buttons, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )
        testsize = dip_size(self, 20, 20)
        icon_size = testsize[0]

        self.btn_edit_wordlist_del = wxStaticBitmap(
            self, wx.ID_ANY, size=dip_size(self, 25, 25)
        )
        self.btn_edit_wordlist_edit = wxStaticBitmap(
            self, wx.ID_ANY, size=dip_size(self, 25, 25)
        )
        self.btn_edit_content_add = wxStaticBitmap(
            self, wx.ID_ANY, size=dip_size(self, 25, 25)
        )
        self.btn_edit_content_del = wxStaticBitmap(
            self, wx.ID_ANY, size=dip_size(self, 25, 25)
        )
        self.btn_edit_content_edit = wxStaticBitmap(
            self, wx.ID_ANY, size=dip_size(self, 25, 25)
        )
        self.btn_edit_content_paste = wxStaticBitmap(
            self, wx.ID_ANY, size=dip_size(self, 25, 25)
        )
        # Circumvent a WXPython bug at high resolutions under Windows
        bmp = icon_trash.GetBitmap(resize=icon_size, buffer=1)
        self.btn_edit_wordlist_del.SetBitmap(bmp)
        testsize = self.btn_edit_wordlist_del.GetBitmap().Size
        if testsize[0] != icon_size:
            icon_size = int(icon_size * icon_size / testsize[0])

        self.btn_edit_wordlist_del.SetBitmap(
            icon_trash.GetBitmap(resize=icon_size, buffer=1)
        )
        self.btn_edit_wordlist_edit.SetBitmap(
            icon_edit.GetBitmap(resize=icon_size, buffer=1)
        )
        self.btn_edit_content_add.SetBitmap(
            icon_add_new.GetBitmap(resize=icon_size, buffer=1)
        )
        self.btn_edit_content_del.SetBitmap(
            icon_trash.GetBitmap(resize=icon_size, buffer=1)
        )
        self.btn_edit_content_edit.SetBitmap(
            icon_edit.GetBitmap(resize=icon_size, buffer=1)
        )
        self.btn_edit_content_paste.SetBitmap(
            icons8_paste.GetBitmap(resize=icon_size, buffer=1)
        )

        self.btn_edit_wordlist_del.SetToolTip(_("Delete the current variable"))
        self.btn_edit_wordlist_edit.SetToolTip(
            _("Edit the name of the active variable")
        )
        self.btn_edit_content_add.SetToolTip(
            _("Add a new entry for the active variable")
        )
        self.btn_edit_content_del.SetToolTip(
            _("Delete the current entry for the active variable")
        )
        self.btn_edit_content_edit.SetToolTip(
            _("Edit the current entry for the active variable")
        )
        self.btn_edit_content_paste.SetToolTip(
            _(
                "Paste the clipboard as new entries for the active variable, any line as new entry"
            )
        )
        minsize = 23
        self.btn_edit_wordlist_del.SetMinSize(dip_size(self, minsize, minsize))
        self.btn_edit_wordlist_edit.SetMinSize(dip_size(self, minsize, minsize))
        self.btn_edit_content_add.SetMinSize(dip_size(self, minsize, minsize))
        self.btn_edit_content_del.SetMinSize(dip_size(self, minsize, minsize))
        self.btn_edit_content_edit.SetMinSize(dip_size(self, minsize, minsize))
        self.btn_edit_content_paste.SetMinSize(dip_size(self, minsize, minsize))

        sizer_edit_wordlist_buttons.Add(self.btn_edit_wordlist_del, 0, wx.EXPAND, 0)
        sizer_edit_wordlist_buttons.Add(self.btn_edit_wordlist_edit, 0, wx.EXPAND, 0)

        sizer_edit_content_buttons.Add(self.btn_edit_content_add, 0, wx.EXPAND, 0)
        sizer_edit_content_buttons.Add(self.btn_edit_content_del, 0, wx.EXPAND, 0)
        sizer_edit_content_buttons.Add(self.btn_edit_content_edit, 0, wx.EXPAND, 0)
        sizer_edit_content_buttons.Add(self.btn_edit_content_paste, 0, wx.EXPAND, 0)

        sizer_index_right = wx.BoxSizer(wx.HORIZONTAL)
        label_2 = wxStaticText(self, wx.ID_ANY, _("Start Index for field:"))
        sizer_index_right.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.cbo_index_single = wxComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        sizer_index_right.Add(self.cbo_index_single, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        dummylabel = wxStaticText(self, wx.ID_ANY, " ")
        sizer_index_right.Add(dummylabel, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_index_right.Add(
            sizer_edit_content_buttons, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )

        sizer_grid_right.Add(sizer_index_right, 0, wx.EXPAND, 0)
        sizer_grid_right.Add(self.grid_content, 1, wx.EXPAND, 0)

        self.txt_pattern = TextCtrl(self, wx.ID_ANY, "")

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons.Add(self.txt_pattern, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_add = wxButton(self, wx.ID_ANY, _("Add Text"))
        self.btn_add.SetToolTip(_("Add another wordlist entry"))
        sizer_buttons.Add(self.btn_add, 0, 0, 0)

        self.btn_add_counter = wxButton(self, wx.ID_ANY, _("Add Counter"))
        sizer_buttons.Add(self.btn_add_counter, 0, 0, 0)

        self.btn_delete = wxButton(self, wx.ID_ANY, _("Delete"))
        self.btn_delete.SetToolTip(_("Delete the current wordlist entry"))
        sizer_buttons.Add(self.btn_delete, 0, 0, 0)

        sizer_exit = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_backup = wxButton(self, wx.ID_ANY, _("Backup Wordlist"))
        self.btn_backup.SetToolTip(_("Save current wordlist to disk"))
        sizer_exit.Add(self.btn_backup, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_restore = wxButton(self, wx.ID_ANY, _("Restore Wordlist"))
        self.btn_restore.SetToolTip(_("Load wordlist from disk"))
        sizer_exit.Add(self.btn_restore, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.check_autosave = wxCheckBox(self, wx.ID_ANY, _("Autosave"))
        self.check_autosave.SetToolTip(
            _("All changes to the wordlist will be saved immediately")
        )
        sizer_exit.Add(self.check_autosave, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.check_autosave.SetValue(self.context.wordlist_autosave)

        self.lbl_message = wxStaticText(self, wx.ID_ANY, "")
        sizer_exit.Add(self.lbl_message, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_lower = wx.BoxSizer(wx.HORIZONTAL)
        sizer_lower.Add(sizer_buttons, 1, wx.ALL, 0)
        sizer_lower.Add(sizer_exit, 1, wx.ALL, 0)

        sizer_main.Add(sizer_grids, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_lower, 0, wx.ALL, 0)

        self.SetSizer(sizer_main)
        self.Layout()
        self._set_logic()
        self.populate_gui()

    def _set_logic(self):
        self.btn_add.Bind(wx.EVT_BUTTON, self.on_btn_add)
        self.btn_add_counter.Bind(wx.EVT_BUTTON, self.on_add_counter)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_btn_delete)
        self.btn_backup.Bind(wx.EVT_BUTTON, self.on_backup)
        self.btn_restore.Bind(wx.EVT_BUTTON, self.on_restore)
        self.txt_pattern.Bind(wx.EVT_TEXT, self.on_patterntext_change)
        self.cbo_Index.Bind(wx.EVT_COMBOBOX, self.on_cbo_select)
        self.grid_wordlist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_grid_wordlist)
        self.grid_wordlist.Bind(
            wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_begin_edit_wordlist
        )
        self.grid_wordlist.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_edit_wordlist)
        self.grid_content.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_grid_content)
        self.grid_content.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_begin_edit_content)
        self.grid_content.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_edit_content)
        self.grid_content.Bind(wx.EVT_LEFT_DCLICK, self.on_content_dblclick)
        self.check_autosave.Bind(wx.EVT_CHECKBOX, self.on_checkbox_autosave)

        self.btn_edit_wordlist_del.Bind(wx.EVT_LEFT_DOWN, self.on_btn_edit_wordlist_del)
        self.btn_edit_wordlist_edit.Bind(
            wx.EVT_LEFT_DOWN, self.on_btn_edit_wordlist_edit
        )
        self.btn_edit_content_add.Bind(wx.EVT_LEFT_DOWN, self.on_btn_edit_content_add)
        self.btn_edit_content_del.Bind(wx.EVT_LEFT_DOWN, self.on_btn_edit_content_del)
        self.btn_edit_content_edit.Bind(wx.EVT_LEFT_DOWN, self.on_btn_edit_content_edit)
        self.btn_edit_content_paste.Bind(
            wx.EVT_LEFT_DOWN, self.on_btn_edit_content_paste
        )
        self.cbo_index_single.Bind(wx.EVT_COMBOBOX, self.on_single_index)
        # Key handler for F2
        self.grid_content.Bind(wx.EVT_CHAR, self.on_key_grid)
        self.grid_wordlist.Bind(wx.EVT_CHAR, self.on_key_grid)

    def set_parent(self, par_panel):
        self.parent_panel = par_panel

    def pane_show(self):
        self.grid_wordlist.load_column_widths()
        self.grid_content.load_column_widths()
        self.populate_gui()
        self.grid_wordlist.SetFocus()

    def pane_hide(self):
        self.grid_wordlist.save_column_widths()
        self.grid_content.save_column_widths()

    def autosave(self):
        if self.check_autosave.GetValue():
            if self.wlist.default_filename is not None:
                self.wlist.save_data(self.wlist.default_filename)
                msg = _("Saved to ") + self.wlist.default_filename
                self.edit_message(msg)

    def on_key_grid(self, event):
        grid = event.GetEventObject()
        key = event.GetKeyCode()
        if key == wx.WXK_F2:
            index = grid.GetFirstSelected()
            if index >= 0:
                grid.EditLabel(index)
                # that consumes the key
                return
        # Let's make sure the keystroke is processed further
        event.Skip()

    def on_checkbox_autosave(self, event):
        self.context.wordlist_autosave = self.check_autosave.GetValue()
        event.Skip()

    def on_btn_edit_wordlist_del(self, event):
        index = self.grid_wordlist.GetFirstSelected()
        key = self.get_column_text(self.grid_wordlist, index, 0)
        if key in self.wlist.prohibited:
            msg = _("Can't delete internal variable {key}").format(key=key)
            self.edit_message(msg)
            return
        self.wlist.delete(key)
        self.autosave()
        self.refresh_grid_wordlist()

    def on_btn_edit_wordlist_edit(self, event):
        index = self.grid_wordlist.GetFirstSelected()
        if index >= 0:
            self.grid_wordlist.EditLabel(index)

    def on_btn_edit_content_add(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        self.wlist.add_value(self.cur_skey, "---", 0)
        self.refresh_grid_content(skey, 0)
        self.autosave()

    def on_btn_edit_content_del(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        index = self.grid_content.GetFirstSelected()
        if index >= 0:
            pass
        self.wlist.delete_value(skey, index)
        self.refresh_grid_content(skey, 0)
        self.autosave()

    def on_btn_edit_content_edit(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        index = self.grid_content.GetFirstSelected()
        if index >= 0:
            self.cur_index = index
            self.grid_content.EditLabel(self.cur_index)

    def on_btn_edit_content_paste(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        text_data = wx.TextDataObject()
        success = False
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(text_data)
            wx.TheClipboard.Close()
        if not success:
            return
        msg = text_data.GetText()
        if msg is not None and len(msg) > 0:
            lines = msg.splitlines()
            for entry in lines:
                self.wlist.add_value(skey, entry, 0)
            self.refresh_grid_content(skey, 0)
            self.autosave()

    def refresh_grid_wordlist(self):
        self.current_entry = None
        self.grid_wordlist.ClearAll()
        self.cur_skey = None
        self.grid_wordlist.InsertColumn(0, _("Name"))
        self.grid_wordlist.InsertColumn(1, _("Type"))
        self.grid_wordlist.InsertColumn(2, _("Index"))
        typestr = [_("Text"), _("CSV"), _("Counter")]
        for skey in self.wlist.content:
            index = self.grid_wordlist.InsertItem(
                self.grid_wordlist.GetItemCount(), skey
            )
            self.grid_wordlist.SetItem(index, 1, typestr[self.wlist.content[skey][0]])
            self.grid_wordlist.SetItem(index, 2, str(self.wlist.content[skey][1] - 2))
        self.grid_wordlist.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.grid_wordlist.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.grid_wordlist.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.grid_wordlist.resize_columns()

    def get_column_text(self, grid, index, col):
        item = grid.GetItem(index, col)
        return item.GetText()

    def set_column_text(self, grid, index, col, value):
        # item = grid.GetItem(index)
        grid.SetItem(index, col, value)

    def refresh_grid_content(self, skey, current):
        self.cbo_index_single.Clear()
        choices = []
        selidx = 0
        self.grid_content.ClearAll()
        self.cur_skey = skey.lower()
        self.cur_index = None
        self.grid_content.InsertColumn(0, _("Content"))

        for idx in range(2, len(self.wlist.content[skey])):
            myidx = idx - 2
            s_entry = str(self.wlist.content[skey][idx])
            choices.append(f"{myidx:3d} - {s_entry[:10]}")
            index = self.grid_content.InsertItem(
                self.grid_content.GetItemCount(), s_entry
            )
            if idx == current + 2:
                selidx = current
                self.grid_content.SetItemTextColour(index, wx.RED)
        wsize = self.grid_content.GetSize()
        self.grid_content.SetColumnWidth(0, wsize[0] - 10)
        self.grid_content.resize_columns()

        self.cbo_index_single.Set(choices)
        if selidx >= 0:
            self.cbo_index_single.SetSelection(selidx)

    def on_single_index(self, event):
        skey = self.cur_skey
        idx = self.cbo_index_single.GetSelection()
        if skey is None:
            return
        self.wlist.set_index(skey, idx)
        self.refresh_grid_content(skey, idx)
        # We need to refresh the main_index_column as well
        self.set_column_text(self.grid_wordlist, self.current_entry, 2, str(idx))

    def on_grid_wordlist(self, event):
        current_item = event.Index
        self.current_entry = current_item
        skey = self.get_column_text(self.grid_wordlist, current_item, 0).lower()
        try:
            current = int(self.get_column_text(self.grid_wordlist, current_item, 2))
        except ValueError:
            current = 0

        self.refresh_grid_content(skey, current)
        self.txt_pattern.SetValue(skey)
        event.Skip()

    def on_content_dblclick(self, event):
        index = self.grid_content.GetFirstSelected()
        if index >= 0:
            self.cbo_index_single.SetSelection(index)
            self.on_single_index(event)

    def on_grid_content(self, event):
        # Single Click
        event.Skip()

    def on_begin_edit_wordlist(self, event):
        index = self.grid_wordlist.GetFirstSelected()
        if index >= 0:
            # Is this a prevented value?
            skey = self.get_column_text(self.grid_wordlist, index, 0)
            self.to_save_wordlist = (skey, 0)
            if skey in self.wlist.prohibited:
                msg = _("Can't rename internal variable {key}").format(key=skey)
                self.edit_message(msg)
                self.to_save_wordlist = None
                event.Veto()
                return
        event.Allow()

    def on_end_edit_wordlist(self, event):
        if self.to_save_wordlist is None:
            self.edit_message(_("Update failed"))
        else:
            skey = self.to_save_wordlist[0]
            value = event.GetText().lower()
            # We need to replace it...
            self.wlist.rename_key(skey, value)
            self.autosave()
            self.cur_skey = value
            self.refresh_grid_content(value, 0)
            self.txt_pattern.SetValue(value)

        self.to_save_wordlist = None
        event.Allow()

    def on_begin_edit_content(self, event):
        index = self.grid_content.GetFirstSelected()
        if index >= 0:
            self.cur_index = index
        self.to_save_content = (self.cur_skey, self.cur_index)
        event.Allow()

    def on_end_edit_content(self, event):
        if self.to_save_content is None:
            self.edit_message(_("Update failed"))
        else:
            skey = self.to_save_content[0]
            index = self.to_save_content[1]
            value = event.GetText()
            self.wlist.set_value(skey, value, index)
            self.autosave()
        self.to_save_content = None
        event.Allow()

    def populate_gui(self):
        self.cbo_Index.Clear()
        self.cbo_Index.Enable(False)
        maxidx = -1
        self.grid_content.ClearAll()
        self.refresh_grid_wordlist()
        for skey in self.wlist.content:
            if self.wlist.content[skey][0] == 1:  # CSV
                i = len(self.wlist.content[skey]) - 2
                if i > maxidx:
                    maxidx = i
        if maxidx >= 0:
            for i in range(maxidx):
                self.cbo_Index.Append(str(i))
            self.cbo_Index.SetValue("0")
        self.cbo_Index.Enable(True)
        # Let's refresh the scene to acknowledge new changes
        self.context.signal("refresh_scene", "Scene")

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
        if selidx < 0:
            selidx = 0
        self.refresh_grid_wordlist()
        self.grid_wordlist.Select(selidx, True)
        self.autosave()

    def on_btn_add(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey) > 0:
            if skey in self.wlist.content:
                self.wlist.delete(skey)
            self.wlist.add_value(skey, "---", 0)
            self.autosave()
            self.populate_gui()
        event.Skip()

    def on_patterntext_change(self, event):
        enab1 = False
        enab2 = False
        newname = self.txt_pattern.GetValue().lower()
        if len(newname) > 0:
            enab2 = True
            enab1 = True
            if newname in self.wlist.content:
                enab1 = False
        self.btn_add.Enable(enab1)
        self.btn_add_counter.Enable(enab1)
        self.btn_delete.Enable(enab2)

    def on_add_counter(self, event):  # wxGlade: editWordlist.<event_handler>
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey) > 0:
            if skey in self.wlist.content:
                self.wlist.delete(skey)
            self.wlist.add_value(skey, 1, 2)
            self.autosave()
        self.populate_gui()
        event.Skip()

    def on_btn_delete(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey) > 0:
            self.wlist.delete(skey)
            self.autosave()
            self.populate_gui()
        event.Skip()

    def on_backup(self, event):
        if self.wlist.default_filename is not None:
            self.wlist.save_data(self.wlist.default_filename)
            msg = _("Saved to ") + self.wlist.default_filename
            self.edit_message(msg)
        event.Skip()

    def on_restore(self, event):
        if self.wlist.default_filename is not None:
            self.wlist.load_data(self.wlist.default_filename)
            msg = _("Loaded from ") + self.wlist.default_filename
            self.edit_message(msg)
            self.populate_gui()
        event.Skip()

    @signal_listener("wordlist")
    def signal_wordlist(self, origin, *args):
        self.autosave()
        self.refresh_grid_wordlist()


class ImportPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.parent_panel = None
        self.context = context
        self.context.themes.set_window_colors(self)
        self.wlist = self.context.elements.mywordlist
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        info_box = StaticBoxSizer(self, wx.ID_ANY, _("Import CSV"), wx.VERTICAL)
        sizer_csv = wx.BoxSizer(wx.HORIZONTAL)
        info_box.Add(sizer_csv, 1, wx.EXPAND, 0)

        label_1 = wxStaticText(self, wx.ID_ANY, _("Import CSV-File"))
        sizer_csv.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_filename = TextCtrl(self, wx.ID_ANY, "")
        sizer_csv.Add(self.txt_filename, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_fileDialog = wxButton(self, wx.ID_ANY, "...")
        self.btn_fileDialog.SetMinSize(dip_size(self, 23, 23))
        sizer_csv.Add(self.btn_fileDialog, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_import = wxButton(self, wx.ID_ANY, _("Import CSV"))
        sizer_csv.Add(self.btn_import, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        self.rbox_header = wxRadioBox(
            self,
            wx.ID_ANY,
            _("What does the first row contain:"),
            choices=(
                _("Auto-Detect"),
                _("Contains Data"),
                _("Contains Variable-Names"),
            ),
            majorDimension=3,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rbox_header.SetSelection(0)
        sizer_header.Add(self.rbox_header, 1, wx.EXPAND, 0)
        info_box.Add(sizer_header, 0, wx.EXPAND)

        self.text_preview = TextCtrl(
            self, wx.ID_ANY, style=wx.TE_READONLY | wx.TE_MULTILINE
        )

        main_sizer.Add(info_box, 0, wx.EXPAND, 0)
        main_sizer.Add(self.text_preview, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.btn_fileDialog.Bind(wx.EVT_BUTTON, self.on_btn_file)
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_btn_import)
        self.txt_filename.Bind(wx.EVT_TEXT, self.on_filetext_change)
        self.btn_import.Enable(False)

    def set_parent(self, par_panel):
        self.parent_panel = par_panel

    def on_btn_file(self, event):
        myfile = ""
        mydlg = wx.FileDialog(
            self,
            message=_("Choose a csv-file"),
            wildcard="CSV-Files (*.csv)|*.csv|Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW,
        )
        if mydlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            myfile = mydlg.GetPath()
        mydlg.Destroy()
        if myfile != "":
            self.txt_filename.SetValue(myfile)
            # self.on_btn_import(None)

    def import_csv(self, myfile):
        if os.path.exists(myfile):
            self.txt_filename.SetValue(myfile)
            force_header = None
            if self.rbox_header.GetSelection() == 1:
                force_header = False
            elif self.rbox_header.GetSelection() == 2:
                force_header = True
            ct, colcount, headers = self.wlist.load_csv_file(
                myfile, force_header=force_header
            )
            msg = _("Imported file, {col} fields, {row} rows").format(
                col=colcount, row=ct
            )
            if self.parent_panel is not None:
                self.parent_panel.edit_message(msg)
                self.parent_panel.populate_gui()
            return True
        return False

    def on_btn_import(self, event):
        myfile = self.txt_filename.GetValue()
        if os.path.exists(myfile):
            force_header = None
            if self.rbox_header.GetSelection() == 1:
                force_header = False
            elif self.rbox_header.GetSelection() == 2:
                force_header = True
            ct, colcount, headers = self.wlist.load_csv_file(
                myfile, force_header=force_header
            )
            msg = _("Imported file, {col} fields, {row} rows").format(
                col=colcount, row=ct
            )
            if self.parent_panel is not None:
                self.parent_panel.edit_message(msg)
                self.parent_panel.populate_gui()

    def on_filetext_change(self, event):
        myfile = self.txt_filename.GetValue()
        enab = False
        if os.path.exists(myfile):
            enab = True
        self.btn_import.Enable(enab)
        self.preview_it()

    def preview_it(self):
        filename = self.txt_filename.GetValue()

        buffer = ""
        if os.path.exists(filename):
            decoder = EncodingDetectFile()
            result = decoder.load(filename)
            if result:
                encoding, bom_marker, file_content = result
                buffer = file_content

        self.text_preview.SetValue(buffer)


class AboutPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        info_box = StaticBoxSizer(self, wx.ID_ANY, _("How to use..."), wx.VERTICAL)
        self.parent_panel = None
        s = self.context.asset("wordlist_howto")
        info_label = TextCtrl(
            self, wx.ID_ANY, value=s, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )
        info_label.SetFont(font)
        info_label.SetBackgroundColour(self.GetBackgroundColour())
        info_box.Add(info_label, 1, wx.EXPAND, 0)
        main_sizer.Add(info_box, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()

    def set_parent(self, par_panel):
        self.parent_panel = par_panel


class WordlistEditor(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 530, *args, **kwds)

        self.panel_editor = WordlistPanel(self, wx.ID_ANY, context=self.context)
        self.panel_import = ImportPanel(self, wx.ID_ANY, context=self.context)
        self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)

        self.panel_editor.set_parent(self)
        self.panel_import.set_parent(self)
        self.panel_about.set_parent(self)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_curly_brackets.GetBitmap())
        self.SetIcon(_icon)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.window_context.themes.set_window_colors(self.notebook_main)
        bg_std = self.window_context.themes.get("win_bg")
        bg_active = self.window_context.themes.get("highlight")
        self.notebook_main.GetArtProvider().SetColour(bg_std)
        self.notebook_main.GetArtProvider().SetActiveColour(bg_active)

        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)
        self.notebook_main.AddPage(self.panel_editor, _("Editing"))
        self.notebook_main.AddPage(self.panel_import, _("Import/Export"))
        self.notebook_main.AddPage(self.panel_about, _("How to use"))
        # begin wxGlade: Keymap.__set_properties
        self.DragAcceptFiles(True)
        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)
        self.SetTitle(_("Wordlist Editor"))
        self.restore_aspect()

    def on_drop_file(self, event):
        """
        Drop file handler
        Accepts only a single file drop.
        """
        for pathname in event.GetFiles():
            if self.panel_import.import_csv(pathname):
                break

    def delegates(self):
        yield self.panel_editor
        yield self.panel_import
        yield self.panel_about

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/config/Wordlist",
            {
                "label": _("Wordlist Editor"),
                "icon": icons8_curly_brackets,
                "tip": _("Manages Wordlist-Entries"),
                "help": "wordlist",
                "action": lambda v: kernel.console("window toggle Wordlist\n"),
            },
        )

    def window_open(self):
        pass

    def window_close(self):
        pass

    def edit_message(self, msg):
        self.panel_editor.edit_message(msg)

    def populate_gui(self):
        self.panel_editor.populate_gui()

    @staticmethod
    def submenu():
        # Suppress to avoid double menu-appearance
        return "Editing", "Variables + Wordlists", True

    @staticmethod
    def helptext():
        return _("Configure the wordlist (text variable) entries")
