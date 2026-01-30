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
from ..core.wordlist import TYPE_CSV

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


class VirtualContentList(wxListCtrl):
    """A virtual list control that fetches content on demand from a Wordlist.

    It implements OnGetItemText and OnGetItemAttr so the control can display
    very large lists without adding items to the control, keeping the UI
    responsive.
    """

    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL | wx.LC_EDIT_LABELS,
        context=None,
        list_name=None,
    ):
        # Ensure the control is created with LC_VIRTUAL regardless of caller-supplied style
        style = style | wx.LC_VIRTUAL
        # Note: call super with positional id to match wrapper signature in wxutils.wxListCtrl
        super().__init__(parent, id, style=style, context=context, list_name=list_name)
        self.key = None
        self.wlist = None
        self.current = None
        # Use modern ItemAttr when available, fall back for older wx versions
        try:
            self._attr_current = wx.ItemAttr()
        except AttributeError:
            self._attr_current = wx.ListItemAttr()
        try:
            # Set the text color for the current item highlight
            self._attr_current.SetTextColour(wx.RED)
        except Exception:
            pass

    def set_key(self, key, wlist, current=None):
        """Bind the control to a specific wordlist key and set the current index.

        Note: callers should update the item count with SetItemCount(total) after
        calling this method to avoid redundant work.
        """
        self.key = key
        self.wlist = wlist
        self.current = current

    def set_current(self, current):
        self.current = current
        # Refresh visible items
        self.Refresh()

    # Methods called by wx for virtual lists
    def OnGetItemText(self, item, col):
        try:
            if self.key is None or self.wlist is None:
                return ""
            return str(self.wlist.content[self.key][item + 2])
        except Exception:
            return ""

    def OnGetItemAttr(self, item):
        if item == self.current:
            return self._attr_current
        return None


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
    """WordlistMiniPanel - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for wordlistmini functionality. Features button controls for user interaction. Integrates with wordlist, refresh_scene for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for wordlistmini functionality. Key controls include "Edit" (button), "Next" (button), "Prev" (button)."""

    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("wordlist")

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_edit = wxButton(self, wx.ID_ANY, _("Edit"))
        self.button_edit.SetBitmap(
            icons8_curly_brackets.GetBitmap(
                resize=0.5 * get_default_icon_size(self.context)
            )
        )
        self.button_edit.SetToolTip(_("Manages Wordlist-Entries"))

        self.button_next = wxButton(self, wx.ID_ANY, _("Next"))
        self.button_next.SetBitmap(
            icons8_circled_right.GetBitmap(
                resize=0.5 * get_default_icon_size(self.context)
            )
        )
        self.button_next.SetToolTip(
            _("Wordlist: go to next page (right-click to next entry)")
        )

        self.button_prev = wxButton(self, wx.ID_ANY, _("Prev"))
        self.button_prev.SetBitmap(
            icons8_circled_left.GetBitmap(
                resize=0.5 * get_default_icon_size(self.context)
            )
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
    """WordlistPanel - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for wordlist functionality. Features button controls for user interaction. Integrates with wordlist, refresh_scene for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for wordlist functionality. Key controls include "Edit" (button), "Next" (button), "Prev" (button)."""

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

        # Filter / Search for variables
        sizer_search = wx.BoxSizer(wx.HORIZONTAL)
        lbl_filter = wxStaticText(self, wx.ID_ANY, _("Filter:"))
        self.txt_filter = TextCtrl(self, wx.ID_ANY, "")
        self.txt_filter.SetMinSize(dip_size(self, 120, -1))
        sizer_search.Add(lbl_filter, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_search.Add(self.txt_filter, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_grid_left.Add(sizer_search, 0, wx.EXPAND, 0)

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
            list_name="list_wordlist",
        )
        self.grid_wordlist.SetMinSize(dip_size(self, 200, 100))
        sizer_grid_left.Add(self.grid_wordlist, 1, wx.EXPAND, 0)

        # Use a virtual list to avoid populating very large content lists on the UI thread
        self.grid_content = VirtualContentList(
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
        self.grid_content.SetMinSize(dip_size(self, 200, 100))

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

        # Jump button allows direct numeric jump without populating huge comboboxes
        self.btn_jump_index = wxButton(self, wx.ID_ANY, _("Jump"))
        self.btn_jump_index.SetToolTip(_("Jump to a specific index"))
        sizer_index_right.Add(self.btn_jump_index, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        dummylabel = wxStaticText(self, wx.ID_ANY, " ")
        sizer_index_right.Add(dummylabel, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_index_right.Add(
            sizer_edit_content_buttons, 0, wx.ALIGN_CENTER_VERTICAL, 0
        )

        sizer_grid_right.Add(sizer_index_right, 0, wx.EXPAND, 0)
        sizer_grid_right.Add(self.grid_content, 1, wx.EXPAND, 0)

        self.txt_pattern = TextCtrl(self, wx.ID_ANY, "")
        self.txt_pattern.SetMinSize(dip_size(self, 70, -1))

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons.Add(self.txt_pattern, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_add = wxButton(self, wx.ID_ANY, _("Add Text"))
        self.btn_add.SetToolTip(_("Add another wordlist entry"))
        sizer_buttons.Add(self.btn_add, 0, 0, 0)

        self.btn_add_counter = wxButton(self, wx.ID_ANY, _("Add Counter"))
        sizer_buttons.Add(self.btn_add_counter, 0, 0, 0)

        self.btn_preview = wxButton(self, wx.ID_ANY, _("Preview"))
        self.btn_preview.SetToolTip(_("Preview the translation of the pattern"))
        sizer_buttons.Add(self.btn_preview, 0, 0, 0)

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

        sizer_message = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_message = wxStaticText(self, wx.ID_ANY, "")
        sizer_message.Add(self.lbl_message, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_lower = wx.BoxSizer(wx.HORIZONTAL)
        sizer_lower.Add(sizer_buttons, 1, wx.ALL, 0)
        sizer_lower.Add(sizer_exit, 0, wx.EXPAND, 0)

        sizer_main.Add(sizer_grids, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_lower, 0, wx.ALL, 0)
        sizer_main.Add(sizer_message, 0, wx.ALL, 0)

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
        self.grid_content.Bind(wx.EVT_CONTEXT_MENU, self.on_context_content)
        self.grid_wordlist.Bind(wx.EVT_CONTEXT_MENU, self.on_context_wordlist)
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
        self.btn_jump_index.Bind(wx.EVT_BUTTON, self.on_jump_index)
        # Key handler for F2
        self.grid_content.Bind(wx.EVT_CHAR, self.on_key_grid)
        self.grid_wordlist.Bind(wx.EVT_CHAR, self.on_key_grid)
        # Filter handler
        self.txt_filter.Bind(wx.EVT_TEXT, self.on_filter_change)
        # Preview handler
        self.btn_preview.Bind(wx.EVT_BUTTON, self.on_preview)

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
        if index < 0:
            return
        key = self.get_column_text(self.grid_wordlist, index, 0)
        if key in self.wlist.prohibited:
            msg = _("Can't delete internal variable {key}").format(key=key)
            self.edit_message(msg)
            return
        dlg = wx.MessageDialog(
            self,
            _("Delete variable '{key}'?").format(key=key),
            _("Confirm Delete"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if dlg.ShowModal() == wx.ID_YES:
            self.wlist.delete(key)
            self.autosave()
            self.refresh_grid_wordlist()
        dlg.Destroy()

    def on_btn_edit_wordlist_edit(self, event):
        index = self.grid_wordlist.GetFirstSelected()
        if index >= 0:
            self.grid_wordlist.EditLabel(index)

    def on_btn_edit_content_add(self, event):
        skey = self.cur_skey
        if skey is None:
            self.edit_message(_("No variable selected"))
            return
        val = "---"
        # Attempt to add value and report reason on failure
        added, reason = self.wlist.add_value_unique(skey, val, 0)
        if not added:
            if reason == "duplicate":
                self.edit_message(_("Entry already exists"))
            elif reason == "empty":
                self.edit_message(_("Invalid entry"))
            else:
                self.edit_message(_("Failed to add entry"))
            return
        self.refresh_grid_content(skey, 0)
        self.autosave()
        # Update the wordlist overview (counts)
        try:
            self.refresh_grid_wordlist()
        except Exception:
            pass

    def on_btn_edit_content_del(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        index = self.grid_content.GetFirstSelected()
        if index < 0:
            return
        entry_text = self.get_column_text(self.grid_content, index, 0)
        dlg = wx.MessageDialog(
            self,
            _("Delete entry '{entry}'?").format(entry=entry_text),
            _("Confirm Delete"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if dlg.ShowModal() == wx.ID_YES:
            self.wlist.delete_value(skey, index)
            self.refresh_grid_content(skey, 0)
            self.autosave()
            try:
                self.refresh_grid_wordlist()
            except Exception:
                pass
        dlg.Destroy()

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
            dlg = wx.MessageDialog(
                self,
                _("Paste {n} entries into '{key}'?").format(n=len(lines), key=skey),
                _("Confirm Paste"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            )
            if dlg.ShowModal() == wx.ID_YES:
                for entry in lines:
                    self.wlist.add_value(skey, entry, 0)
                self.refresh_grid_content(skey, 0)
                self.autosave()
                try:
                    self.refresh_grid_wordlist()
                except Exception:
                    pass
            dlg.Destroy()

    def refresh_grid_wordlist(self):
        # Preserve selection so we can restore it after repopulating the grid
        prev_selected = None
        try:
            sel_idx = self.grid_wordlist.GetFirstSelected()
            if sel_idx >= 0:
                prev_selected = self.get_column_text(
                    self.grid_wordlist, sel_idx, 0
                ).lower()
        except Exception:
            prev_selected = None

        self.current_entry = None
        self.grid_wordlist.ClearAll()
        self.cur_skey = None
        self.grid_wordlist.InsertColumn(0, _("Name"))
        self.grid_wordlist.InsertColumn(1, _("Type"))
        self.grid_wordlist.InsertColumn(2, _("Index"))
        self.grid_wordlist.InsertColumn(3, _("Count"))
        typestr = [_("Text"), _("CSV"), _("Counter")]
        filt = getattr(self, "filter_text", "")
        if filt is None:
            filt = ""
        filt = filt.lower().strip()
        for skey in self.wlist.content:
            if filt and filt not in skey.lower():
                continue
            index = self.grid_wordlist.InsertItem(
                self.grid_wordlist.GetItemCount(), skey
            )
            self.grid_wordlist.SetItem(index, 1, typestr[self.wlist.content[skey][0]])
            self.grid_wordlist.SetItem(index, 2, str(self.wlist.content[skey][1] - 2))
            # Number of entries (excluding the two control entries)
            count = max(0, len(self.wlist.content[skey]) - 2)
            self.grid_wordlist.SetItem(index, 3, str(count))
        self.grid_wordlist.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.grid_wordlist.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.grid_wordlist.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.grid_wordlist.SetColumnWidth(3, wx.LIST_AUTOSIZE_USEHEADER)
        self.grid_wordlist.resize_columns()

        # Try to restore previous selection if possible
        if prev_selected:
            try:
                for idx in range(self.grid_wordlist.GetItemCount()):
                    if (
                        self.get_column_text(self.grid_wordlist, idx, 0).lower()
                        == prev_selected
                    ):
                        self.grid_wordlist.Select(idx, True)
                        self.grid_wordlist.SetFocus()
                        break
            except Exception:
                pass

    def get_column_text(self, grid, index, col):
        item = grid.GetItem(index, col)
        return item.GetText()

    def set_column_text(self, grid, index, col, value):
        # item = grid.GetItem(index)
        grid.SetItem(index, col, value)

    def refresh_grid_content(self, skey, current):
        import time

        self.cbo_index_single.Clear()
        choices = []
        selidx = 0
        # For virtual list, clear columns and set a single Content column
        self.grid_content.ClearAll()
        self.grid_content.InsertColumn(0, _("Content"))
        key_lower = skey.lower() if skey is not None else None
        self.cur_skey = key_lower
        self.cur_index = None

        # If the key does not exist, leave the content empty and avoid KeyError
        if key_lower is None or key_lower not in self.wlist.content:
            self.cbo_index_single.Set(choices)
            # ensure grid shows no rows
            self.grid_content.set_key(None, self.wlist, None)
            return

        total_items = max(0, len(self.wlist.content[key_lower]) - 2)
        # Prepare a small immediate-choice placeholder and arrange for lazy full population
        placeholder_limit = min(10, total_items)
        for idx in range(2, 2 + placeholder_limit):
            myidx = idx - 2
            s_entry = str(self.wlist.content[key_lower][idx])
            choices.append(f"{myidx:3d} - {s_entry[:10]}")
        if total_items > placeholder_limit:
            choices.append("...")
        # Record count for lazy population when the user opens the dropdown
        self._cbo_index_single_count = total_items
        # Bind the dropdown event for lazy expansion if not already bound
        if not hasattr(self, "_cbo_single_bound") or not self._cbo_single_bound:
            try:
                self.cbo_index_single.Bind(
                    wx.EVT_COMBOBOX_DROPDOWN, self.on_cbo_index_single_dropdown
                )
                self._cbo_single_bound = True
            except Exception:
                try:
                    self.cbo_index_single.Bind(
                        wx.EVT_DROPDOWN, self.on_cbo_index_single_dropdown
                    )
                    self._cbo_single_bound = True
                except Exception:
                    # fallback: will keep the placeholder list
                    pass

        # Freeze UI updates to batch expensive operations
        try:
            self.Freeze()
        except Exception:
            pass
        try:
            self.grid_content.Freeze()
        except Exception:
            pass
        try:
            self.cbo_index_single.Freeze()
        except Exception:
            pass

        # Set the virtual list's key and highlight the current index
        self.grid_content.set_key(key_lower, self.wlist, current)
        # Set item count to total items (virtual mode will fetch content on demand)
        self.grid_content.SetItemCount(total_items)
        # If a current index was provided, ensure it is selected and visible
        if current is not None and 0 <= current < total_items:
            try:
                self.grid_content.Select(current, True)
                self.grid_content.Focus()
                try:
                    self.grid_content.EnsureVisible(current)
                except Exception:
                    pass
            except Exception:
                pass
        # Populate combo and adjust column width
        self.cbo_index_single.Set(choices)
        if selidx >= 0 and selidx < len(choices):
            self.cbo_index_single.SetSelection(selidx)
        wsize = self.grid_content.GetSize()
        self.grid_content.SetColumnWidth(0, wsize[0] - 10)
        self.grid_content.resize_columns()

        # Thaw UI updates
        try:
            self.cbo_index_single.Thaw()
        except Exception:
            pass
        try:
            self.grid_content.Thaw()
        except Exception:
            pass
        try:
            self.Thaw()
        except Exception:
            pass

    def on_cbo_index_single_dropdown(self, event):
        # Lazily populate the single-index combo with the full list when opened
        try:
            count = getattr(self, "_cbo_index_single_count", 0)
            if count and (
                not self.cbo_index_single.GetItems()
                or len(self.cbo_index_single.GetItems()) < count
            ):
                try:
                    items = [
                        f"{i:3d} - {str(self.wlist.content[self.cur_skey][i + 2])[:10]}"
                        for i in range(count)
                    ]
                except Exception:
                    items = [str(i) for i in range(count)]
                try:
                    self.cbo_index_single.Freeze()
                except Exception:
                    pass
                self.cbo_index_single.Set(items)
                try:
                    self.cbo_index_single.Thaw()
                except Exception:
                    pass
        finally:
            event.Skip()

    def on_jump_index(self, event):
        """Prompt the user for an index and jump the grid to that index."""
        if self.cur_skey is None:
            self.edit_message(_("No variable selected"))
            return
        total_items = max(0, len(self.wlist.content[self.cur_skey]) - 2)
        if total_items == 0:
            self.edit_message(_("Selected variable has no entries"))
            return
        # Ask user for number
        try:
            value = wx.GetNumberFromUser(
                _("Index:"),
                _("Enter the zero-based index to jump to:"),
                _("Jump to index"),
                0,
                0,
                total_items - 1,
                self,
            )
        except Exception:
            value = None
        # wx.GetNumberFromUser returns -1 on cancel in some versions
        if value is None or (isinstance(value, int) and value < 0):
            return
        try:
            value = int(value)
        except Exception:
            # invalid input
            self.edit_message(_("Invalid index"))
            return
        # Bound-check the value
        if value < 0 or value >= total_items:
            self.edit_message(
                _("Index out of range (0..{max})").format(max=total_items - 1)
            )
            return
        # Commit index and refresh
        try:
            self.wlist.set_index(self.cur_skey, value)
            self.refresh_grid_content(self.cur_skey, value)
            # Ensure selection in virtual grid (only if within bounds)
            try:
                self.grid_content.Select(value, True)
                self.grid_content.Focus()
                try:
                    self.grid_content.EnsureVisible(value)
                except Exception:
                    # Some wx versions or controls may not implement EnsureVisible
                    pass
            except Exception:
                # Selection may fail on some wx versions or if control not ready
                pass
        except Exception as e:
            # Catch any unexpected error and report it instead of crashing
            self.edit_message(_("Jump failed: {err}").format(err=str(e)))
            return
        # Autosave if enabled
        self.autosave()
        wsize = self.grid_content.GetSize()
        self.grid_content.SetColumnWidth(0, wsize[0] - 10)
        self.grid_content.resize_columns()

        # Ensure the single-index combo reflects the current selection.
        try:
            items = self.cbo_index_single.GetItems()
            seltext = (
                f"{value:3d} - {str(self.wlist.content[self.cur_skey][value + 2])[:10]}"
            )
            if seltext in items:
                self.cbo_index_single.SetStringSelection(seltext)
            else:
                # If placeholder present or item missing, force full population then select
                try:
                    # Call the dropdown handler to populate the list lazily
                    class DummyEvent:
                        def Skip(self):
                            pass

                    self.on_cbo_index_single_dropdown(DummyEvent())
                    items = self.cbo_index_single.GetItems()
                    if seltext in items:
                        self.cbo_index_single.SetStringSelection(seltext)
                except Exception:
                    # Never raise on UI update failures
                    pass
        except Exception:
            # Be robust to missing controls or unexpected states
            pass

    def on_single_index(self, event):
        skey = self.cur_skey
        idx = self.cbo_index_single.GetSelection()
        if skey is None or idx < 0:
            return
        self.wlist.set_index(skey, idx)
        self.refresh_grid_content(skey, idx)
        # We need to refresh the main_index_column as well
        self.set_column_text(self.grid_wordlist, self.current_entry, 2, str(idx))
        # Ensure the content grid selects and scrolls to the chosen index
        try:
            self.grid_content.Select(idx, True)
            self.grid_content.Focus()
            try:
                self.grid_content.EnsureVisible(idx)
            except Exception:
                pass
        except Exception:
            pass

    def on_grid_wordlist(self, event):
        current_item = event.Index
        if current_item >= 0:
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

    def on_filter_change(self, event):
        self.filter_text = self.txt_filter.GetValue()
        self.refresh_grid_wordlist()

    def on_preview(self, event):
        pattern = self.txt_pattern.GetValue()
        if pattern is None:
            pattern = ""
        try:
            out = self.wlist.translate(pattern)
            self.edit_message("Preview: " + str(out))
        except Exception as e:
            self.edit_message("Preview failed: " + str(e))

    def on_grid_content(self, event):
        # Single Click
        event.Skip()

    def on_context_wordlist(self, event):
        """Context menu for the wordlist names (add / edit / remove)"""
        sel = self.grid_wordlist.GetFirstSelected()

        # Build the base menu
        menu = wx.Menu()
        mi_add = menu.Append(wx.ID_ANY, _("Add..."))
        mi_edit = menu.Append(wx.ID_ANY, _("Edit..."))
        mi_del = menu.Append(wx.ID_ANY, _("Delete"))

        # Set icons (best-effort)
        try:
            icon_size = max(16, int(get_default_icon_size(self.context) * 0.5))
            mi_add.SetBitmap(icon_add_new.GetBitmap(resize=icon_size, buffer=1))
            mi_edit.SetBitmap(icon_edit.GetBitmap(resize=icon_size, buffer=1))
            mi_del.SetBitmap(icon_trash.GetBitmap(resize=icon_size, buffer=1))
        except Exception:
            pass

        def on_add(evt):
            # Ask for a new variable name
            name = wx.GetTextFromUser(
                _("New variable name:"), _("Add Wordlist Variable"), parent=self
            )
            if name is None or name.strip() == "":
                return
            name = name.strip().lower()
            if name in self.wlist.content:
                self.edit_message(_("Variable '%s' already exists") % name)
                return
            self.wlist.add_value(name, "---", 0)
            self.autosave()
            self.populate_gui()
            # select the new key
            for idx in range(self.grid_wordlist.GetItemCount()):
                if self.get_column_text(self.grid_wordlist, idx, 0).lower() == name:
                    self.grid_wordlist.Select(idx, True)
                    self.grid_wordlist.SetFocus()
                    self.refresh_grid_content(name, 0)
                    break

        def on_edit(evt):
            idx = self.grid_wordlist.GetFirstSelected()
            if idx >= 0:
                self.grid_wordlist.EditLabel(idx)

        def on_delete(evt):
            idx = self.grid_wordlist.GetFirstSelected()
            if idx < 0:
                return
            key = self.get_column_text(self.grid_wordlist, idx, 0)
            if key in self.wlist.prohibited:
                self.edit_message(
                    _("Can't delete internal variable {key}").format(key=key)
                )
                return
            # Confirm deletion
            dlg = wx.MessageDialog(
                self,
                _("Delete variable '{key}'?").format(key=key),
                _("Confirm Delete"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            if dlg.ShowModal() == wx.ID_YES:
                self.wlist.delete(key)
                self.autosave()
                self.populate_gui()
            dlg.Destroy()

        # Offer a bulk-delete CSV option when the selected key is CSV
        try:
            sel_key = None
            if sel >= 0:
                try:
                    sel_key = self.get_column_text(self.grid_wordlist, sel, 0).lower()
                except Exception:
                    sel_key = None
            if sel_key and sel_key in self.wlist.content and self.wlist.content[sel_key][0] == TYPE_CSV:
                mi_delcsv = menu.Append(wx.ID_ANY, _("Delete CSV File..."))
                try:
                    icon_size = max(16, int(get_default_icon_size(self.context) * 0.5))
                    mi_delcsv.SetBitmap(icon_trash.GetBitmap(resize=icon_size, buffer=1))
                except Exception:
                    pass

                def _del_csv_handler(evt, key=sel_key):
                    try:
                        self.delete_csv_file(key, confirm=True)
                    except Exception:
                        pass

                self.Bind(wx.EVT_MENU, _del_csv_handler, mi_delcsv)
        except Exception:
            pass

        # If no selection, disable edit/delete options
        if sel < 0:
            mi_edit.Enable(False)
            mi_del.Enable(False)

        # Bind menu actions
        self.Bind(wx.EVT_MENU, on_add, mi_add)
        self.Bind(wx.EVT_MENU, on_edit, mi_edit)
        self.Bind(wx.EVT_MENU, on_delete, mi_del)

        # Show the menu at the mouse location
        pos = event.GetPosition()
        if not pos:
            pos = self.grid_wordlist.ScreenToClient(wx.GetMousePosition())
        self.PopupMenu(menu)
        menu.Destroy()

    def delete_csv_file(self, skey, confirm=True):
        """Delete all CSV-style keys (the entire CSV import) related to a CSV selection.

        Args:
            skey (str): The selected key name (case-insensitive)
            confirm (bool): If true, ask user for confirmation via dialog. Set False in tests.
        Returns:
            bool: True if deletion occurred, False otherwise.
        """
        if skey is None:
            self.edit_message(_("No variable selected"))
            return False
        sk = skey.lower()
        if sk not in self.wlist.content:
            self.edit_message(_("Variable not found"))
            return False
        try:
            if self.wlist.content[sk][0] != TYPE_CSV:
                self.edit_message(_("Selected variable is not CSV-based"))
                return False
        except Exception:
            self.edit_message(_("Selected variable is not CSV-based"))
            return False

        if confirm:
            dlg = wx.MessageDialog(
                self,
                _("Delete this entry and all other related CSV entries?"),
                _("Confirm Delete"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            if dlg.ShowModal() != wx.ID_YES:
                dlg.Destroy()
                return False
            dlg.Destroy()

        # Remove all CSV entries
        self.wlist.empty_csv()
        self.autosave()
        # Refresh UI
        try:
            self.populate_gui()
        except Exception:
            try:
                self.refresh_grid_wordlist()
            except Exception:
                pass
        self.edit_message(_("Deleted CSV file entries"))
        return True

    def on_context_content(self, event):
        """Context menu for the content list (add / edit / remove / paste)"""
        sel = self.grid_content.GetFirstSelected()
        # Allow Add/Paste when a variable is selected (even if no item selected)
        if self.cur_skey is None and sel < 0:
            return

        menu = wx.Menu()
        mi_add = menu.Append(wx.ID_ANY, _("Add Entry..."))
        mi_paste = menu.Append(wx.ID_ANY, _("Paste Entries"))
        mi_edit = None
        mi_del = None
        if sel >= 0:
            mi_edit = menu.Append(wx.ID_ANY, _("Edit Entry..."))
            mi_del = menu.Append(wx.ID_ANY, _("Delete Entry"))
        # Set icons (best-effort)
        try:
            icon_size = max(16, int(get_default_icon_size(self.context) * 0.5))
            mi_add.SetBitmap(icon_add_new.GetBitmap(resize=icon_size, buffer=1))
            mi_paste.SetBitmap(icons8_paste.GetBitmap(resize=icon_size, buffer=1))
            if mi_edit is not None:
                mi_edit.SetBitmap(icon_edit.GetBitmap(resize=icon_size, buffer=1))
            if mi_del is not None:
                mi_del.SetBitmap(icon_trash.GetBitmap(resize=icon_size, buffer=1))
        except Exception:
            pass

        def on_add_entry(evt):
            if self.cur_skey is None:
                self.edit_message(_("No variable selected"))
                return
            entry = wx.GetTextFromUser(
                _("New entry value:"), _("Add Entry"), parent=self
            )
            if entry is None or entry.strip() == "":
                self.edit_message(_("Invalid entry"))
                return
            # prevent duplicates and add atomically
            added, reason = self.wlist.add_value_unique(self.cur_skey, entry, 0)
            if not added:
                if reason == "duplicate":
                    self.edit_message(_("Entry already exists"))
                elif reason == "empty":
                    self.edit_message(_("Invalid entry"))
                else:
                    self.edit_message(_("Failed to add entry"))
                return
            self.autosave()
            self.refresh_grid_content(self.cur_skey, 0)
            try:
                self.refresh_grid_wordlist()
            except Exception:
                pass

        def on_edit_entry(evt):
            idx = self.grid_content.GetFirstSelected()
            if idx >= 0:
                self.grid_content.EditLabel(idx)

        def on_delete_entry(evt):
            idx = self.grid_content.GetFirstSelected()
            if idx < 0:
                return
            entry_text = self.get_column_text(self.grid_content, idx, 0)
            dlg = wx.MessageDialog(
                self,
                _("Delete entry '{entry}'?").format(entry=entry_text),
                _("Confirm Delete"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            if dlg.ShowModal() == wx.ID_YES:
                self.wlist.delete_value(self.cur_skey, idx)
                self.autosave()
                self.refresh_grid_content(self.cur_skey, 0)
                try:
                    self.refresh_grid_wordlist()
                except Exception:
                    pass
            dlg.Destroy()

        def on_paste_entries(evt):
            # Paste and report adds/skips
            if self.cur_skey is None:
                self.edit_message(_("No variable selected"))
                return
            text_data = wx.TextDataObject()
            success = False
            if wx.TheClipboard.Open():
                success = wx.TheClipboard.GetData(text_data)
                wx.TheClipboard.Close()
            if not success:
                self.edit_message(_("Clipboard empty or unavailable"))
                return
            msg = text_data.GetText()
            if msg is None or len(msg) == 0:
                self.edit_message(_("Clipboard empty"))
                return
            lines = msg.splitlines()
            added = 0
            skipped = 0
            invalid = 0
            for entry in lines:
                added_flag, reason = self.wlist.add_value_unique(
                    self.cur_skey, entry, 0
                )
                if added_flag:
                    added += 1
                else:
                    if reason == "duplicate":
                        skipped += 1
                    else:
                        invalid += 1
            self.autosave()
            self.refresh_grid_content(self.cur_skey, 0)
            # Provide clearer summary including invalid entries
            if invalid == 0:
                self.edit_message(
                    _("Pasted {a} entries, skipped {s} duplicates").format(
                        a=added, s=skipped
                    )
                )
            else:
                self.edit_message(
                    _("Pasted {a} entries, skipped {s} duplicates, {i} invalid").format(
                        a=added, s=skipped, i=invalid
                    )
                )

        self.Bind(wx.EVT_MENU, on_add_entry, mi_add)
        self.Bind(wx.EVT_MENU, on_paste_entries, mi_paste)
        if mi_edit is not None:
            self.Bind(wx.EVT_MENU, on_edit_entry, mi_edit)
        if mi_del is not None:
            self.Bind(wx.EVT_MENU, on_delete_entry, mi_del)

        pos = event.GetPosition()
        if not pos:
            pos = self.grid_content.ScreenToClient(wx.GetMousePosition())
        self.PopupMenu(menu)
        menu.Destroy()

    def on_begin_edit_wordlist(self, event):
        index = self.grid_wordlist.GetFirstSelected()
        if index >= 0:
            # Is this a prevented value?
            skey = self.get_column_text(self.grid_wordlist, index, 0)
            skey_lower = skey.lower()
            # Store lowercased key to avoid case-related mismatches
            self.to_save_wordlist = (skey_lower, 0)
            if skey_lower in self.wlist.prohibited:
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
            old_skey = self.to_save_wordlist[0]
            new_skey = event.GetText().strip().lower()
            # Validate new name
            if new_skey == "":
                self.edit_message(_("Invalid name"))
                if old_skey in self.wlist.content:
                    self.cur_skey = old_skey
                    self.refresh_grid_content(old_skey, 0)
                    self.txt_pattern.SetValue(old_skey)
            elif new_skey in self.wlist.prohibited:
                self.edit_message(_("Can't rename to internal variable name"))
                if old_skey in self.wlist.content:
                    self.cur_skey = old_skey
                    self.refresh_grid_content(old_skey, 0)
                    self.txt_pattern.SetValue(old_skey)
            elif new_skey in self.wlist.content and new_skey != old_skey:
                self.edit_message(_("A variable with that name already exists"))
                if old_skey in self.wlist.content:
                    self.cur_skey = old_skey
                    self.refresh_grid_content(old_skey, 0)
                    self.txt_pattern.SetValue(old_skey)
            else:
                # Attempt rename and handle failures gracefully
                if not self.wlist.rename_key(old_skey, new_skey):
                    # Rename failed - show message and keep previous selection if possible
                    self.edit_message(_("Rename failed"))
                    if old_skey in self.wlist.content:
                        self.cur_skey = old_skey
                        self.refresh_grid_content(old_skey, 0)
                        self.txt_pattern.SetValue(old_skey)
                else:
                    self.autosave()
                    self.cur_skey = new_skey
                    self.refresh_grid_content(new_skey, 0)
                    try:
                        self.refresh_grid_wordlist()
                    except Exception:
                        pass

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
            try:
                self.refresh_grid_wordlist()
            except Exception:
                pass
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
        # Store index range for lazy population on dropdown to keep UI snappy
        if maxidx >= 0:
            self._cbo_index_count = maxidx
            # show a default 0 value; full population occurs when user opens the dropdown
            self.cbo_Index.Clear()
            self.cbo_Index.SetValue("0")
            # Bind dropdown event the first time
            if not hasattr(self, "_cbo_index_bound") or not self._cbo_index_bound:
                try:
                    self.cbo_Index.Bind(
                        wx.EVT_COMBOBOX_DROPDOWN, self.on_cbo_index_dropdown
                    )
                    self._cbo_index_bound = True
                except Exception:
                    # Some wx versions use EVT_DROPDOWN
                    try:
                        self.cbo_Index.Bind(wx.EVT_DROPDOWN, self.on_cbo_index_dropdown)
                        self._cbo_index_bound = True
                    except Exception:
                        # Fallback: populate now
                        items = [str(i) for i in range(maxidx)]
                        self.cbo_Index.Set(items)
                        self.cbo_Index.SetValue("0")
        self.cbo_Index.Enable(True)
        # Let's refresh the scene to acknowledge new changes
        self.context.signal("refresh_scene", "Scene")

    def on_cbo_index_dropdown(self, event):
        # Populate the index combobox lazily when the user opens the dropdown
        try:
            count = getattr(self, "_cbo_index_count", 0)
            if count and (
                not self.cbo_Index.GetItems() or len(self.cbo_Index.GetItems()) < count
            ):
                items = [str(i) for i in range(count)]
                try:
                    self.cbo_Index.Freeze()
                except Exception:
                    pass
                self.cbo_Index.Set(items)
                try:
                    self.cbo_Index.Thaw()
                except Exception:
                    pass
        finally:
            # Let the event proceed so dropdown opens
            event.Skip()

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
        if skey is None or len(skey.strip()) == 0:
            self.edit_message(_("Invalid variable name"))
            return
        skey = skey.strip().lower()
        if skey in self.wlist.content:
            self.edit_message(_("Variable '%s' already exists") % skey)
            return
        if skey in self.wlist.prohibited:
            self.edit_message(
                _("Can't create internal variable {key}").format(key=skey)
            )
            return
        self.wlist.add_value(skey, "---", 0)
        self.autosave()
        self.populate_gui()
        event.Skip()

    def on_patterntext_change(self, event):
        enab1 = False
        enab2 = False
        newname = self.txt_pattern.GetValue().strip()
        if len(newname) > 0:
            enab2 = True
            enab1 = True
            if newname.lower() in self.wlist.content:
                enab1 = False
        self.btn_add.Enable(enab1)
        self.btn_add_counter.Enable(enab1)
        self.btn_delete.Enable(enab2)

    def on_add_counter(self, event):  # wxGlade: editWordlist.<event_handler>
        skey = self.txt_pattern.GetValue()
        if skey is None or len(skey.strip()) == 0:
            self.edit_message(_("Invalid variable name"))
            return
        skey = skey.strip().lower()
        if skey in self.wlist.content:
            self.edit_message(_("Variable '%s' already exists") % skey)
            self.populate_gui()
            return
        if skey in self.wlist.prohibited:
            self.edit_message(
                _("Can't create internal variable {key}").format(key=skey)
            )
            return
        self.wlist.add_value(skey, 1, 2)
        self.autosave()
        self.populate_gui()
        event.Skip()

    def on_btn_delete(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey) > 0:
            dlg = wx.MessageDialog(
                self,
                _("Delete variable '{key}'?").format(key=skey),
                _("Confirm Delete"),
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            if dlg.ShowModal() == wx.ID_YES:
                self.wlist.delete(skey)
                self.autosave()
                self.populate_gui()
            dlg.Destroy()
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
            if self.wlist.has_warnings():
                msg = _("Restored with warnings from ") + self.wlist.default_filename
                channel = self.context.kernel.root.channel("console")
                channel(msg)
                for warning in self.wlist.get_warnings():
                    channel("  " + warning)

            else:
                msg = _("Restored from ") + self.wlist.default_filename
            self.edit_message(msg)
            self.populate_gui()
        event.Skip()

    @signal_listener("wordlist")
    def signal_wordlist(self, origin, *args):
        self.autosave()
        self.refresh_grid_wordlist()

    @signal_listener("wordlist_modified")
    def signal_wordlist_modified(self, origin, *args):
        self.refresh_grid_wordlist()

class ImportPanel(wx.Panel):
    """ImportPanel - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for import functionality. Features button controls for user interaction. Integrates with wordlist, refresh_scene for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for import functionality. Key controls include "Edit" (button), "Next" (button), "Prev" (button)."""

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
            if self.wlist.has_warnings():
                msg = _("Imported file with warnings, {col} fields, {row} rows").format(
                    col=colcount, row=ct
                )
                channel = self.context.kernel.root.channel("console")
                channel(msg)
                for warning in self.wlist.get_warnings():
                    channel("  " + warning)
            else:
                msg = _("Imported file, {col} fields, {row} rows").format(
                    col=colcount, row=ct
                )
            if self.parent_panel is not None:
                self.parent_panel.edit_message(msg)
                self.parent_panel.populate_gui()
                self.parent_panel.show_panel("editor")
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
            if self.wlist.has_warnings():
                msg = _("Imported file with warnings, {col} fields, {row} rows").format(
                    col=colcount, row=ct
                )
                channel = self.context.kernel.root.channel("console")
                channel(msg)
                for warning in self.wlist.get_warnings():
                    channel("  " + warning)
            else:
                msg = _("Imported file, {col} fields, {row} rows").format(
                    col=colcount, row=ct
                )
            if self.parent_panel is not None:
                self.parent_panel.edit_message(msg)
                self.parent_panel.populate_gui()
                try:
                    self.parent_panel.show_panel("editor")
                except Exception:
                    pass

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
    """AboutPanel - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for about functionality. Features button controls for user interaction. Integrates with wordlist, refresh_scene for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for about functionality. Key controls include "Edit" (button), "Next" (button), "Prev" (button)."""

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
    """WordlistEditor - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for wordlisteditor functionality. Features button controls for user interaction. Integrates with wordlist, refresh_scene for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for wordlisteditor functionality. Key controls include "Edit" (button), "Next" (button), "Prev" (button)."""

    def __init__(self, *args, **kwds):
        super().__init__(500, 530, *args, **kwds)

        # Create panels with resilience - if a panel fails to initialize, create a fallback panel
        try:
            self.panel_editor = WordlistPanel(self, wx.ID_ANY, context=self.context)
        except Exception as e:
            import traceback

            traceback.print_exc()
            self.panel_editor = wx.Panel(self)
            st = wx.StaticText(
                self.panel_editor, wx.ID_ANY, _("Wordlist editor failed to initialize")
            )

        try:
            self.panel_import = ImportPanel(self, wx.ID_ANY, context=self.context)
        except Exception:
            import traceback

            traceback.print_exc()
            self.panel_import = wx.Panel(self)
            wx.StaticText(
                self.panel_import, wx.ID_ANY, _("CSV Import panel failed to initialize")
            )

        try:
            self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)
        except Exception:
            import traceback

            traceback.print_exc()
            self.panel_about = wx.Panel(self)
            wx.StaticText(
                self.panel_about, wx.ID_ANY, _("About panel failed to initialize")
            )

        # Give panels a chance to set parent if they implement it
        try:
            self.panel_editor.set_parent(self)
        except Exception:
            pass
        try:
            self.panel_import.set_parent(self)
        except Exception:
            pass
        try:
            self.panel_about.set_parent(self)
        except Exception:
            pass

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

    def show_panel(self, name):
        """
        Show a specific panel by name: 'editor', 'import', 'about'
        """
        name = name.lower()
        if name == "editor":
            self.notebook_main.SetSelection(0)
        elif name == "import":
            self.notebook_main.SetSelection(1)
        elif name == "about":
            self.notebook_main.SetSelection(2)
    @staticmethod
    def submenu():
        # Suppress to avoid double menu-appearance
        return "Editing", "Variables + Wordlists", True

    @staticmethod
    def helptext():
        return _("Configure the wordlist (text variable) entries")
