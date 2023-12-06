import os

import wx
from wx import aui

from ..kernel import signal_listener
from .icons import (
    STD_ICON_SIZE,
    get_default_icon_size,
    icon_add_new,
    icon_edit,
    icon_trash,
    icons8_paste,
    icon_library,
)
from .mwindow import MWindow
from .wxutils import StaticBoxSizer, dip_size

_ = wx.GetTranslation


class MaterialPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.SetHelpText("materialmanager")
        self.parent_panel = None

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        filter_box = StaticBoxSizer(self, wx.ID_ANY, _("Filter Materials"), wx.HORIZONTAL)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Material"))
        filter_box.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_material = wx.TextCtrl(self, wx.ID_ANY, "")
        filter_box.Add(self.txt_material, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("Lasertype"))
        filter_box.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.laser_choices = [_("<All Lasertypes>"),]
        dev_infos = list(self.context.find("provider/friendly"))
        # Gets a list of tuples (description, key, path)
        dev_infos.sort(key=lambda e: e[0][1])
        for e in dev_infos:
            self.laser_choices.append(e[0][0])

        self.combo_lasertype = wx.ComboBox(self, wx.ID_ANY, choices=self.laser_choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        filter_box.Add(self.combo_lasertype, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_reset = wx.Button(self, wx.ID_ANY, _("Reset Filter"))
        filter_box.Add(self.btn_reset, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        main_sizer.Add(filter_box, 0, wx.EXPAND, 0)
        result_box = StaticBoxSizer(self, wx.ID_ANY, _("Matching library entries"), wx.VERTICAL)
        self.list_library_entries = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_library_entries.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_library_entries.AppendColumn(
            _("Material"),
            format=wx.LIST_FORMAT_LEFT,
            width=95,
        )
        self.list_library_entries.AppendColumn(
            _("Lasertype"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_library_entries.AppendColumn(
            _("Operations"), format=wx.LIST_FORMAT_LEFT, width=65
        )
        self.list_preview = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_preview.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_preview.AppendColumn(
            _("Operation"),
            format=wx.LIST_FORMAT_LEFT,
            width=95,
        )
        self.list_preview.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_preview.AppendColumn(
            _("Power"), format=wx.LIST_FORMAT_LEFT, width=65
        )
        self.list_preview.AppendColumn(
            _("Speed"), format=wx.LIST_FORMAT_LEFT, width=65
        )

        param_box = StaticBoxSizer(self, wx.ID_ANY, _("Information"), wx.HORIZONTAL)
        label_1 = wx.StaticText(self, wx.ID_ANY, _("Material"))
        param_box.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_entry_name = wx.TextCtrl(self, wx.ID_ANY, "")
        param_box.Add(self.txt_entry_name, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("Lasertype"))
        param_box.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        choices = self.laser_choices[1:]
        self.combo_entry_type = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        param_box.Add(self.combo_entry_type, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        result_box.Add(self.list_library_entries, 1, wx.EXPAND, 0)
        result_box.Add(param_box, 1, wx.EXPAND, 0)
        result_box.Add(self.list_preview, 1, wx.EXPAND, 0)

        button_box = wx.BoxSizer(wx.VERTICAL)

        self.btn_use_current = wx.Button(self, wx.ID_ANY, _("Use current"))
        self.btn_use_current.SetToolTip(_("Use the currently defined operations"))
        self.btn_apply = wx.Button(self, wx.ID_ANY, _("Apply"))
        self.btn_apply.SetToolTip(_("Apply the current library entry"))
        self.btn_delete = wx.Button(self, wx.ID_ANY, _("Delete"))
        self.btn_delete.SetToolTip(_("Delete the current library entry"))
        self.btn_duplicate = wx.Button(self, wx.ID_ANY, _("Duplicate"))
        self.btn_duplicate.SetToolTip(_("Duplicate the current library entry"))
        self.btn_import = wx.Button(self, wx.ID_ANY, _("Import"))
        self.btn_import.SetToolTip(_("Import a material library from ezcad or LightBurn"))
        self.btn_share = wx.Button(self, wx.ID_ANY, _("Share"))
        self.btn_share.SetToolTip(_("Share the current library entry with the MeerK40t community"))

        button_box.Add(self.btn_use_current, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_apply, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_delete, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_duplicate, 0, wx.EXPAND, 0)
        button_box.AddStretchSpacer(1)
        button_box.Add(self.btn_import, 0, wx.EXPAND, 0)
        button_box.Add(self.btn_share, 0, wx.EXPAND, 0)
        outer_box = wx.BoxSizer(wx.HORIZONTAL)
        outer_box.Add(result_box, 1, wx.EXPAND, 0)
        outer_box.Add(button_box, 0, wx.EXPAND, 0)
        main_sizer.Add(outer_box, 1, wx.EXPAND, 0)

        self.SetSizer(main_sizer)
        self.Layout()
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.combo_lasertype.Bind(wx.EVT_COMBOBOX, self.update_list)
        self.txt_material.Bind(wx.EVT_TEXT, self.update_list)
        self.btn_use_current.Bind(wx.EVT_BUTTON, self.on_use_current)
        self.btn_apply.Bind(wx.EVT_BUTTON, self.on_apply)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_duplicate.Bind(wx.EVT_BUTTON, self.on_duplicate)
        self.btn_share.Bind(wx.EVT_BUTTON, self.on_share)
        self.txt_entry_name.Bind(wx.EVT_TEXT, self.on_update_entry)
        self.combo_entry_type.Bind(wx.EVT_COMBOBOX, self.on_update_entry)
        self.on_reset(None)


    def on_share(self, event):
        print ("Sharing")

    def on_duplicate(self, event):
        print ("Duplicating")

    def on_delete(self, event):
        print ("Deleting")

    def on_apply(self, event):
        print ("Applying")

    def on_use_current(self, event):
        print ("Use current")

    def on_update_entry(self, event):
        entry_txt = self.txt_entry_name.GetValue()
        entry_type = self.combo_entry_type.GetSelection() + 1

    def on_reset(self, event):
        self.txt_material.SetValue("")
        self.combo_lasertype.SetSelection(0)
        self.update_list()

    def update_list(self, *args):
        filter_txt = self.txt_material.GetValue()
        filter_type = self.combo_lasertype.GetSelection()

    def set_parent(self, par_panel):
        self.parent_panel = par_panel

    def pane_show(self):
        pass

    def pane_hide(self):
        pass


class ImportPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.parent_panel = None
        self.context = context
        self.library_entries = []
        self.visible_list = []
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        filter_box = StaticBoxSizer(self, wx.ID_ANY, _("Import Materials"), wx.HORIZONTAL)

        label_1 = wx.StaticText(self, wx.ID_ANY, _("Material"))
        filter_box.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_material = wx.TextCtrl(self, wx.ID_ANY, "")
        filter_box.Add(self.txt_material, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("Lasertype"))
        filter_box.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.laser_choices = [_("<All Lasertypes>"),]
        dev_infos = list(self.context.find("provider/friendly"))
        # Gets a list of tuples (description, key, path)
        # description is a tuple itself containing description and index
        dev_infos.sort(key=lambda e: e[0][1])
        for e in dev_infos:
            self.laser_choices.append(e[0][0])
        self.combo_lasertype = wx.ComboBox(self, wx.ID_ANY, choices=self.laser_choices, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        filter_box.Add(self.combo_lasertype, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_reset = wx.Button(self, wx.ID_ANY, _("Reset Filter"))
        filter_box.Add(self.btn_reset, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_load = wx.Button(self, wx.ID_ANY, _("Load"))
        filter_box.Add(self.btn_load, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        main_sizer.Add(filter_box, 0, wx.EXPAND, 0)
        result_box = StaticBoxSizer(self, wx.ID_ANY, _("Matching library entries"), wx.VERTICAL)
        self.list_library_entries = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_library_entries.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_library_entries.AppendColumn(
            _("Material"),
            format=wx.LIST_FORMAT_LEFT,
            width=95,
        )
        self.list_library_entries.AppendColumn(
            _("Lasertype"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_library_entries.AppendColumn(
            _("Operations"), format=wx.LIST_FORMAT_LEFT, width=65
        )
        self.list_preview = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        self.list_preview.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_preview.AppendColumn(
            _("Operation"),
            format=wx.LIST_FORMAT_LEFT,
            width=95,
        )
        self.list_preview.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_preview.AppendColumn(
            _("Power"), format=wx.LIST_FORMAT_LEFT, width=65
        )
        self.list_preview.AppendColumn(
            _("Speed"), format=wx.LIST_FORMAT_LEFT, width=65
        )

        result_box.Add(self.list_library_entries, 1, wx.EXPAND, 0)
        result_box.Add(self.list_preview, 1, wx.EXPAND, 0)
        self.btn_import = wx.Button(self, wx.ID_ANY, _("Import"))
        result_box.Add(self.btn_import, 0, wx.ALIGN_RIGHT, 0)

        main_sizer.Add(result_box, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.btn_load.Bind(wx.EVT_BUTTON, self.on_load)
        self.combo_lasertype.Bind(wx.EVT_COMBOBOX, self.update_list)
        self.txt_material.Bind(wx.EVT_TEXT, self.update_list)
        self.list_library_entries.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection)
        ### TODO Look for locally cached entries...
        self.on_reset(None)
        self.enable_filter_controls()

    def on_import(self, event):
        idx = self.list_library_entries.GetFirstSelected()
        if idx >= 0:
            lib_idx = self.visible_list[idx]

    def on_reset(self, event):
        self.txt_material.SetValue("")
        self.combo_lasertype.SetSelection(0)
        self.update_list()

    def enable_filter_controls(self):
        flag = len(self.library_entries) > 0
        self.txt_material.Enable(flag)
        self.combo_lasertype.Enable(flag)
        self.btn_reset.Enable(flag)

    def on_load(self, event):
        self.library_entries.clear()
        ### TODO: Load material database from internet

        self.enable_filter_controls()
        self.update_list()

    def update_list(self, *args):
        filter_txt = self.txt_material.GetValue()
        filter_type = self.combo_lasertype.GetSelection()
        self.visible_list.clear()
        self.btn_import.Enable(False)
        self.list_library_entries.DeleteAllItems()
        for idx, entry in enumerate(self.library_entries):
            use_it = True
            if filter_txt and filter_txt not in entry[0]:
                use_it = False
            if filter_type > 0 and filter_type != entry[1]:
                use_it = False
            if use_it:
                try:
                    ltype = self.laser_choices(entry[1])
                except IndexError:
                    # Invalid...
                    continue
                self.visible_list.append(idx)
                list_id = self.list_library_entries.InsertItem(idx, f"#{idx}")
                self.list_library_entries.SetItem(list_id, 1, entry[0])
                self.list_library_entries.SetItem(list_id, 2, ltype)
                self.list_library_entries.SetItem(list_id, 3, len(entry[2]))

        if len(self.visible_list):
            self.list_library_entries.Select(0)
        self.on_selection(None)

    def on_selection(self, event):
        self.btn_import.Enable(False)
        idx = self.list_library_entries.GetFirstSelected()
        self.list_preview.DeleteAllItems()
        if idx >= 0:
            self.btn_import.Enable(True)
            lib_idx = self.visible_list[idx]
            entry = self.library_entries[lib_idx]
            for idx, op in enumerate(entry[2]):
                list_id = self.list_preview.InsertItem(idx, f"#{idx}")
                self.list_preview.SetItem(list_id, 1, op.type)
                self.list_preview.SetItem(list_id, 2, op.label)
                if hasattr(op, "power"):
                    self.list_preview.SetItem(list_id, 3, op.power)
                if hasattr(op, "speed"):
                    self.list_preview.SetItem(list_id, 4, op.speed)

    def set_parent(self, par_panel):
        self.parent_panel = par_panel


class AboutPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        info_box = StaticBoxSizer(self, wx.ID_ANY, _("How to use..."), wx.VERTICAL)
        self.parent_panel = None
        s = self.context.asset("material_howto")
        info_label = wx.TextCtrl(
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


class MaterialManager(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 530, *args, **kwds)

        self.panel_library = MaterialPanel(self, wx.ID_ANY, context=self.context)
        self.panel_import = ImportPanel(self, wx.ID_ANY, context=self.context)
        self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)

        self.panel_library.set_parent(self)
        self.panel_import.set_parent(self)
        self.panel_about.set_parent(self)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_library.GetBitmap())
        self.SetIcon(_icon)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.notebook_main.AddPage(self.panel_library, _("Library"))
        self.notebook_main.AddPage(self.panel_import, _("Import"))
        self.notebook_main.AddPage(self.panel_about, _("How to use"))
        # begin wxGlade: Keymap.__set_properties
        self.DragAcceptFiles(True)
        self.Bind(wx.EVT_DROP_FILES, self.on_drop_file)
        self.SetTitle(_("Material Library"))

    def on_drop_file(self, event):
        """
        Drop file handler
        Accepts only a single file drop.
        """
        for pathname in event.GetFiles():
            if self.panel_import.import_csv(pathname):
                break

    def delegates(self):
        yield self.panel_library
        yield self.panel_import
        yield self.panel_about

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/config/Material",
            {
                "label": _("Material Library"),
                "icon": icon_library,
                "tip": _("Manages Material Settings"),
                "help": "materialmanager",
                "action": lambda v: kernel.console("window toggle MatManager\n"),
            },
        )

    def window_open(self):
        pass

    def window_close(self):
        pass

    def edit_message(self, msg):
        self.panel_library.edit_message(msg)

    def populate_gui(self):
        self.panel_library.populate_gui()

    @staticmethod
    def submenu():
        # Suppress to avoid double menu-appearance
        return "", "Material Library", True