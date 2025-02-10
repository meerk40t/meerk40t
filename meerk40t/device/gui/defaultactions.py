import wx

from meerk40t.gui.icons import (
    icon_air_off,
    icon_air_on,
    icon_bell,
    icon_close_window,
    icon_console,
    icon_external,
    icon_internal,
    icon_return,
    icon_round_stop,
    icon_timer,
    icon_trash,
    icons8_down,
    icons8_home_filled,
    icons8_up,
)
from meerk40t.gui.wxutils import StaticBoxSizer, TextCtrl, dip_size, wxButton, wxListCtrl, wxStaticBitmap

_ = wx.GetTranslation


class DefaultActionPanel(wx.Panel):
    """
    DefaultActions is a panel that should work for all devices (hence in its own directory)
    It allows to define operations that should be executed at the beginning and the end of a job
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: PassesPanel.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)

        self.context = context
        self.context.themes.set_window_colors(self)

        self.SetHelpText("defaultactions")

        self.standards = (
            ("Home", "util home", ""),
            ("Goto Origin", "util goto", "0,0"),
            ("Goto 0,0", "util goto", "0,0,True"),
            ("Beep", "util console", "beep"),
            ("Interrupt", "util console", 'interrupt "Spooling was interrupted"'),
            ("Console", "util console", ""),
            ("Coolant on", "util console", "coolant_on"),
            ("Coolant off", "util console", "coolant_off"),
        )
        self.default_images = [
            ["console home -f", icons8_home_filled],
            ["console move_abs", icon_return],
            ["console beep", icon_bell],
            ["console interrupt", icon_round_stop],
            ["console quit", icon_close_window],
            ["util wait", icon_timer],
            ["util home", icons8_home_filled],
            ["util goto", icon_return],  # icon_marker
            ["util output", icon_external],
            ["util input", icon_internal],
            ["util console", icon_console],
            ["console coolant_on", icon_air_on],
            ["console coolant_off", icon_air_off],
        ]
        self.prepend_ops = []
        self.append_ops = []

        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_before = StaticBoxSizer(self, wx.ID_ANY, _("At job start"), wx.VERTICAL)
        sizer_after = StaticBoxSizer(self, wx.ID_ANY, _("At job end"), wx.VERTICAL)
        sizer_middle = wx.BoxSizer(wx.VERTICAL)

        iconsize = dip_size(self, 30, 20)
        bmpsize = min(iconsize[0], iconsize[1]) * self.context.root.bitmap_correction_scale
        self.option_list = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_LIST,
        )

        self.text_param_option = TextCtrl(self, wx.ID_ANY)

        self.button_add_prepend = wxButton(self, wx.ID_ANY, _("Add to Job Start"))
        self.button_add_append = wxButton(self, wx.ID_ANY, _("Add to Job End"))

        self.prepend_list = wxListCtrl(
            self, wx.ID_ANY, style=wx.LC_LIST | wx.LC_SINGLE_SEL, context=self.context,
        )
        self.text_param_prepend = TextCtrl(self, wx.ID_ANY)

        self.append_list = wxListCtrl(
            self, wx.ID_ANY, style=wx.LC_LIST | wx.LC_SINGLE_SEL, context=self.context,
        )
        self.text_param_append = TextCtrl(self, wx.ID_ANY)
        self.button_del_prepend = wxStaticBitmap(self, wx.ID_ANY, size=iconsize)
        self.button_up_prepend = wxStaticBitmap(self, wx.ID_ANY, size=iconsize)
        self.button_down_prepend = wxStaticBitmap(self, wx.ID_ANY, size=iconsize)
        self.button_del_prepend.SetBitmap(
            icon_trash.GetBitmap(resize=bmpsize, buffer=1)
        )
        self.button_up_prepend.SetBitmap(icons8_up.GetBitmap(resize=bmpsize, buffer=1))
        self.button_down_prepend.SetBitmap(
            icons8_down.GetBitmap(resize=bmpsize, buffer=1)
        )

        self.button_del_append = wxStaticBitmap(self, wx.ID_ANY, size=iconsize)
        self.button_up_append = wxStaticBitmap(self, wx.ID_ANY, size=iconsize)
        self.button_down_append = wxStaticBitmap(self, wx.ID_ANY, size=iconsize)
        self.button_del_append.SetBitmap(icon_trash.GetBitmap(resize=bmpsize, buffer=1))
        self.button_up_append.SetBitmap(icons8_up.GetBitmap(resize=bmpsize, buffer=1))
        self.button_down_append.SetBitmap(
            icons8_down.GetBitmap(resize=bmpsize, buffer=1)
        )

        sizer_param = StaticBoxSizer(
            self, wx.ID_ANY, _("Operation parameter:"), wx.HORIZONTAL
        )
        sizer_param.Add(self.text_param_option, 1, wx.EXPAND, 0)
        sizer_button = wx.BoxSizer(wx.VERTICAL)
        sizer_button.Add(self.button_add_prepend, 1, wx.EXPAND, 0)
        sizer_button.Add(self.button_add_append, 1, wx.EXPAND, 0)

        sizer_middle.Add(self.option_list, 1, wx.EXPAND, 0)
        sizer_middle.Add(sizer_param, 0, wx.EXPAND, 0)
        sizer_middle.Add(sizer_button, 0, wx.EXPAND, 0)

        hsizer_prepend = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_prepend.Add(self.text_param_prepend, 1, wx.EXPAND, 0)
        hsizer_prepend.Add(self.button_del_prepend, 0, wx.EXPAND, 0)
        hsizer_prepend.Add(self.button_up_prepend, 0, wx.EXPAND, 0)
        hsizer_prepend.Add(self.button_down_prepend, 0, wx.EXPAND, 0)

        hsizer_append = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_append.Add(self.text_param_append, 1, wx.EXPAND, 0)
        hsizer_append.Add(self.button_del_append, 0, wx.EXPAND, 0)
        hsizer_append.Add(self.button_up_append, 0, wx.EXPAND, 0)
        hsizer_append.Add(self.button_down_append, 0, wx.EXPAND, 0)

        sizer_before.Add(self.prepend_list, 1, wx.EXPAND, 0)
        sizer_before.Add(hsizer_prepend, 0, wx.EXPAND, 0)

        sizer_after.Add(self.append_list, 1, wx.EXPAND, 0)
        sizer_after.Add(hsizer_append, 0, wx.EXPAND, 0)

        sizer_jobs = wx.BoxSizer(wx.VERTICAL)
        sizer_jobs.Add(sizer_before, 1, wx.EXPAND, 0)
        sizer_jobs.Add(sizer_after, 1, wx.EXPAND, 0)

        sizer_main.Add(sizer_jobs, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_middle, 1, wx.EXPAND, 0)

        # Explanatory tooltips
        self.button_add_prepend.SetToolTip(
            _("Add the selected operation to the default 'Job Start' list")
        )
        self.button_add_append.SetToolTip(
            _("Add the selected operation to the default 'Job End' list")
        )
        self.button_del_prepend.SetToolTip(
            _("Remove the selected operation from the list")
        )
        self.button_del_append.SetToolTip(
            _("Remove the selected operation from the list")
        )
        self.button_down_prepend.SetToolTip(
            _("Decrease the position of the selected operation")
        )
        self.button_up_prepend.SetToolTip(
            _("Increase the position of the selected operation")
        )
        self.button_down_append.SetToolTip(
            _("Decrease the position of the selected operation")
        )
        self.button_up_append.SetToolTip(
            _("Increase the position of the selected operation")
        )
        self.text_param_option.SetToolTip(
            _("Modify the default parameter of the operation to be added")
        )
        self.text_param_prepend.SetToolTip(
            _("Modify the parameter of the selected operation")
        )
        self.text_param_append.SetToolTip(
            _("Modify the parameter of the selected operation")
        )

        # Logic for manipulation of existing entries
        self.prepend_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.prepend_single_click)
        self.append_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.append_single_click)
        self.button_up_prepend.Bind(wx.EVT_LEFT_DOWN, self.prepend_move_up)
        self.button_up_append.Bind(wx.EVT_LEFT_DOWN, self.append_move_up)
        self.button_down_prepend.Bind(wx.EVT_LEFT_DOWN, self.prepend_move_down)
        self.button_down_append.Bind(wx.EVT_LEFT_DOWN, self.append_move_down)
        self.button_del_prepend.Bind(wx.EVT_LEFT_DOWN, self.prepend_delete)
        self.button_del_append.Bind(wx.EVT_LEFT_DOWN, self.append_delete)
        self.text_param_prepend.Bind(wx.EVT_TEXT, self.on_text_prepend)
        self.text_param_append.Bind(wx.EVT_TEXT, self.on_text_append)

        # Logic for addition of new entries
        self.option_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.option_single_click)
        self.button_add_prepend.Bind(wx.EVT_BUTTON, self.add_prepend_option)
        self.button_add_append.Bind(wx.EVT_BUTTON, self.add_append_option)

        # Fill template list
        self.setup_state_images()
        for entry in self.standards:
            item = self.option_list.InsertItem(
                self.option_list.GetItemCount(), _(entry[0])
            )
            state = self.establish_state(entry[1], entry[2])
            if state >= 0:
                # print(
                #     f"I would set image for {entry[0]}={entry[1]}.{entry[2]} to {state}"
                # )
                self.option_list.SetItemImage(item, state)
        # Set to all to disabled by default
        for ctrl in (
            self.button_del_append,
            self.button_del_prepend,
            self.button_down_append,
            self.button_down_prepend,
            self.button_up_append,
            self.button_up_prepend,
            self.button_add_append,
            self.button_add_prepend,
            self.text_param_append,
            self.text_param_prepend,
            self.text_param_option,
        ):
            ctrl.Enable(False)

        self.SetSizer(sizer_main)
        self.Layout()
        self.init_settings()
        self.update_widgets()

    ### Manipulation routines of existing entries

    def prepend_delete(self, event):
        idx = self.prepend_list.GetFirstSelected()
        if idx < 0 or idx >= len(self.prepend_ops):
            return
        self.prepend_ops.pop(idx)
        # print("Now", self.prepend_ops)
        # print("Deleted was", removed)
        self.save_data()
        self.fill_prepend_list()

    def append_delete(self, event):
        idx = self.append_list.GetFirstSelected()
        if idx < 0 or idx >= len(self.append_ops):
            return
        self.append_ops.pop(idx)
        self.save_data()
        self.fill_append_list()

    def on_text_prepend(self, event):
        idx = self.prepend_list.GetFirstSelected()
        if idx < 0 or idx >= len(self.prepend_ops):
            return
        content = self.text_param_prepend.GetValue()
        self.prepend_ops[idx][1] = content
        self.save_data()

    def on_text_append(self, event):
        idx = self.append_list.GetFirstSelected()
        if idx < 0 or idx >= len(self.append_ops):
            return
        content = self.text_param_append.GetValue()
        self.append_ops[idx][1] = content
        self.save_data()

    def prepend_move_up(self, event):
        idx2 = self.prepend_list.GetFirstSelected()
        # Either invalid or the first, so can't be moved up
        if idx2 <= 0 or idx2 >= len(self.prepend_ops):
            return
        # Previous Element
        idx1 = idx2 - 1
        swap = self.prepend_ops[idx1][0]
        self.prepend_ops[idx1][0] = self.prepend_ops[idx2][0]
        self.prepend_ops[idx2][0] = swap
        swap = self.prepend_ops[idx1][1]
        self.prepend_ops[idx1][1] = self.prepend_ops[idx2][1]
        self.prepend_ops[idx2][1] = swap
        self.save_data()
        self.fill_prepend_list()
        self.prepend_list.SetItemState(
            idx1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED
        )
        self.prepend_single_click(None)

    def prepend_move_down(self, event):
        idx2 = self.prepend_list.GetFirstSelected()
        # Either invalid or the last, so can't be moved down
        if idx2 < 0 or idx2 >= len(self.prepend_ops) - 1:
            return
        # Next element
        idx1 = idx2 + 1
        swap = self.prepend_ops[idx1][0]
        self.prepend_ops[idx1][0] = self.prepend_ops[idx2][0]
        self.prepend_ops[idx2][0] = swap
        swap = self.prepend_ops[idx1][1]
        self.prepend_ops[idx1][1] = self.prepend_ops[idx2][1]
        self.prepend_ops[idx2][1] = swap
        self.save_data()
        self.fill_prepend_list()
        self.prepend_list.SetItemState(
            idx1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED
        )
        self.prepend_single_click(None)

    def append_move_up(self, event):
        idx2 = self.append_list.GetFirstSelected()
        # Either invalid or the first, so can't be moved up
        if idx2 <= 0 or idx2 >= len(self.append_ops):
            return
        # Previous Element
        idx1 = idx2 - 1
        swap = self.append_ops[idx1][0]
        self.append_ops[idx1][0] = self.append_ops[idx2][0]
        self.append_ops[idx2][0] = swap
        swap = self.append_ops[idx1][1]
        self.append_ops[idx1][1] = self.append_ops[idx2][1]
        self.append_ops[idx2][1] = swap
        self.save_data()
        self.fill_append_list()
        self.append_list.SetItemState(
            idx1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED
        )
        self.append_single_click(None)

    def append_move_down(self, event):
        idx2 = self.append_list.GetFirstSelected()
        # Either invalid or the last, so can't be moved down
        if idx2 < 0 or idx2 >= len(self.append_ops) - 1:
            return
        # Next element
        idx1 = idx2 + 1
        if (
            idx1 < 0
            or idx2 < 0
            or idx1 >= len(self.append_ops)
            or idx2 >= len(self.append_ops)
        ):
            return
        swap = self.append_ops[idx1][0]
        self.append_ops[idx1][0] = self.append_ops[idx2][0]
        self.append_ops[idx2][0] = swap
        swap = self.append_ops[idx1][1]
        self.append_ops[idx1][1] = self.append_ops[idx2][1]
        self.append_ops[idx2][1] = swap
        self.save_data()
        self.fill_append_list()
        self.append_list.SetItemState(
            idx1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED
        )
        self.append_single_click(None)

    def prepend_single_click(self, event):
        active = True
        idx = self.prepend_list.GetFirstSelected()
        if idx > len(self.prepend_ops):
            idx = -1
        if idx < 0:
            active = False
        self.text_param_prepend.Enable(active)
        self.button_del_prepend.Enable(active)
        self.button_up_prepend.Enable(idx > 0)
        self.button_down_prepend.Enable(active and idx < len(self.prepend_ops) - 1)
        if idx < 0:
            self.text_param_prepend.Enable(False)
            self.text_param_prepend.SetValue("")
        else:
            self.text_param_prepend.Enable(True)
            self.text_param_prepend.SetValue(self.prepend_ops[idx][1])

    def append_single_click(self, event):
        idx = self.append_list.GetFirstSelected()
        active = True
        if idx > len(self.append_ops):
            idx = -1
        if idx < 0:
            active = False
        self.text_param_append.Enable(active)
        self.button_del_append.Enable(active)
        self.button_up_append.Enable(idx > 0)
        self.button_down_append.Enable(active and idx < len(self.append_ops) - 1)
        if idx < 0:
            self.text_param_append.Enable(False)
            self.text_param_append.SetValue("")
        else:
            self.text_param_append.Enable(True)
            self.text_param_append.SetValue(self.append_ops[idx][1])

    ### Routines for addition of new entries
    def add_prepend_option(self, event):
        ct = self.option_list.GetSelectedItemCount()
        if ct <= 0:
            return
        idx = self.option_list.GetFirstSelected()
        while 0 <= idx < len(self.standards):
            operation = self.standards[idx][1]
            if ct == 1:
                # Only one, so we take the displayed and potentially changed parameter
                content = self.text_param_option.GetValue()
            else:
                # More than one, so we take the default as parameter
                content = self.standards[idx][2]
            entry = [operation, content]
            self.prepend_ops.append(entry)
            idx = self.option_list.GetNextSelected(idx)
        self.save_data()
        self.fill_prepend_list()

    def add_append_option(self, event):
        ct = self.option_list.GetSelectedItemCount()
        if ct <= 0:
            return
        idx = self.option_list.GetFirstSelected()
        while 0 <= idx < len(self.standards):
            operation = self.standards[idx][1]
            if ct == 1:
                # Only one, so we take the displayed and potentially changed parameter
                content = self.text_param_option.GetValue()
            else:
                # More than one, so we take the default as parameter
                content = self.standards[idx][2]
            entry = [operation, content]
            self.append_ops.append(entry)
            idx = self.option_list.GetNextSelected(idx)
        self.save_data()
        self.fill_append_list()

    def option_single_click(self, event):
        idx = self.option_list.GetFirstSelected()
        if idx < 0 or idx >= len(self.standards):
            active = False
            self.text_param_option.SetValue("")
        else:
            active = True
            self.text_param_option.SetValue(self.standards[idx][2])
        for ctrl in (
            self.button_add_prepend,
            self.button_add_append,
            self.text_param_option,
        ):
            ctrl.Enable(active)

    ### Data storage / retrieval

    def save_data(self):
        prefix = "prepend"
        str_count = f"{prefix}_op_count"
        count = 0
        for idx, entry in enumerate(self.prepend_ops):
            if entry[1] is None:
                entry[1] = ""
            attr1 = f"{prefix}_op_{idx:02d}"
            attr2 = f"{prefix}_op_param_{idx:02d}"
            self.context.setting(str, attr1, entry[0])
            self.context.setting(str, attr2, entry[1])
            setattr(self.context, attr1, entry[0])
            setattr(self.context, attr2, entry[1])
            count += 1
        setattr(self.context, str_count, len(self.prepend_ops))

        prefix = "append"
        str_count = f"{prefix}_op_count"
        for idx, entry in enumerate(self.append_ops):
            if entry[1] is None:
                entry[1] = ""
            attr1 = f"{prefix}_op_{idx:02d}"
            attr2 = f"{prefix}_op_param_{idx:02d}"
            self.context.setting(str, attr1, entry[0])
            self.context.setting(str, attr2, entry[1])
            setattr(self.context, attr1, entry[0])
            setattr(self.context, attr2, entry[1])
        setattr(self.context, str_count, len(self.append_ops))

    def setup_state_images(self):
        testsize = dip_size(self, 20, 20)
        iconsize = testsize[1]

        self.options_images = wx.ImageList()
        self.options_images.Create(width=iconsize, height=iconsize)
        self.prepend_images = wx.ImageList()
        self.prepend_images.Create(width=iconsize, height=iconsize)
        self.append_images = wx.ImageList()
        self.append_images.Create(width=iconsize, height=iconsize)
        for entry in self.default_images:
            image = entry[1].GetBitmap(
                resize=(iconsize, iconsize), buffer=2, noadjustment=True
            )
            image_id1 = self.options_images.Add(bitmap=image)
            image_id2 = self.prepend_images.Add(bitmap=image)
            image_id3 = self.append_images.Add(bitmap=image)
        self.option_list.AssignImageList(self.options_images, wx.IMAGE_LIST_SMALL)
        self.prepend_list.AssignImageList(self.prepend_images, wx.IMAGE_LIST_SMALL)
        self.append_list.AssignImageList(self.append_images, wx.IMAGE_LIST_SMALL)

    def establish_state(self, opname, parameter):
        # Establish colors (and some images)
        stateidx = -1
        tofind = opname
        if parameter is None:
            parameter = ""
        if tofind == "util console":
            # Let's see whether we find the keyword...
            for idx, entry in enumerate(self.default_images):
                if entry[0].startswith("console "):
                    skey = entry[0][8:]
                    if parameter is not None and skey in parameter:
                        stateidx = idx
                        break
        if stateidx < 0:
            for idx, entry in enumerate(self.default_images):
                if entry[0] == tofind:
                    stateidx = idx
                    break
        # print(f"opname={opname}, parameter={parameter}, state={stateidx}")
        return stateidx

    def init_settings(self):
        for prefix in ("prepend", "append"):
            str_count = f"{prefix}_op_count"
            self.context.setting(int, str_count, 0)
            value = getattr(self.context, str_count, 0)
            if value > 0:
                for idx in range(value):
                    attr1 = f"{prefix}_op_{idx:02d}"
                    attr2 = f"{prefix}_op_param_{idx:02d}"
                    self.context.setting(str, attr1, "")
                    self.context.setting(str, attr2, "")

    def fill_prepend_list(self):
        self.prepend_list.DeleteAllItems()
        self.text_param_prepend.Enable(False)
        self.button_del_prepend.Enable(False)
        self.button_up_prepend.Enable(False)
        self.button_down_prepend.Enable(False)

        for idx, entry in enumerate(self.prepend_ops):
            if entry[1] is None:
                entry[1] = ""
            display_name = entry[0]
            for def_entry in self.standards:
                if def_entry[1] == entry[0] and def_entry[2] == entry[1]:
                    display_name = def_entry[0]
                    break
            item = self.prepend_list.InsertItem(
                self.prepend_list.GetItemCount(), f"{idx:02d}# - {display_name}"
            )
            state = self.establish_state(entry[0], entry[1])
            if state >= 0:
                # print (f"I would set image for {entry[0]}.{entry[1]} to {state}")
                self.prepend_list.SetItemImage(item, state)

        self.prepend_list.Refresh()

    def fill_append_list(self):
        self.append_list.DeleteAllItems()
        self.text_param_append.Enable(False)
        self.button_del_append.Enable(False)
        self.button_up_append.Enable(False)
        self.button_down_append.Enable(False)
        for idx, entry in enumerate(self.append_ops):
            if entry[1] is None:
                entry[1] = ""
            display_name = entry[0]
            for def_entry in self.standards:
                if def_entry[2] is None:
                    def_entry[2] = ""
                if def_entry[1] == entry[0] and def_entry[2] == entry[1]:
                    display_name = def_entry[0]
                    break
            item = self.append_list.InsertItem(
                self.append_list.GetItemCount(), f"{idx:02d}# - {display_name}"
            )
            state = self.establish_state(entry[0], entry[1])
            if state >= 0:
                self.append_list.SetItemImage(item, state)
        self.append_list.Refresh()

    def update_widgets(self):
        # Validate and set all choices
        self.prepend_ops = []
        self.append_ops = []

        prefix = "prepend"
        str_count = f"{prefix}_op_count"
        count = getattr(self.context, str_count, 0)
        for idx in range(count):
            entry = ["", ""]
            attr1 = f"{prefix}_op_{idx:02d}"
            attr2 = f"{prefix}_op_param_{idx:02d}"
            entry[0] = getattr(self.context, attr1, "")
            entry[1] = getattr(self.context, attr2, "")
            self.prepend_ops.append(entry)

        prefix = "append"
        str_count = f"{prefix}_op_count"
        count = getattr(self.context, str_count, 0)
        for idx in range(count):
            entry = ["", ""]
            attr1 = f"{prefix}_op_{idx:02d}"
            attr2 = f"{prefix}_op_param_{idx:02d}"
            entry[0] = getattr(self.context, attr1, "")
            entry[1] = getattr(self.context, attr2, "")
            self.append_ops.append(entry)
        self.fill_prepend_list()
        self.fill_append_list()

    def pane_hide(self):
        pass

    def pane_show(self):
        self.update_widgets()
