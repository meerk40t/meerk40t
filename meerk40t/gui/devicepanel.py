import wx
from wx import aui

from meerk40t.gui.icons import icons8_manager
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    StaticBoxSizer,
    dip_size,
    wxButton,
    wxListCtrl,
    wxStaticText,
    wxTreeCtrl,
    TextCtrl,
)
from meerk40t.kernel import lookup_listener, signal_listener

_ = wx.GetTranslation


def register_panel(window, context):
    panel = DevicePanel(window, wx.ID_ANY, context=context, pane=True)
    pane = (
        aui.AuiPaneInfo()
        .Bottom()
        .Layer(2)
        .MinSize(600, 100)
        .FloatingSize(600, 230)
        .Caption(_("Devices"))
        .Name("devices")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 600
    pane.control = panel
    pane.helptext = _("Manage and add devices to be used by MeerK40t")

    window.on_pane_create(pane)
    context.register("pane/devices", pane)


class SelectDevice(wx.Dialog):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: SelectDevice.__init__
        kwds["style"] = (
            kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        wx.Dialog.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetTitle(_("Select Device"))

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_3 = StaticBoxSizer(self, wx.ID_ANY, _("Filter"), wx.HORIZONTAL)
        sizer_main.Add(sizer_3, 0, wx.EXPAND, 0)

        label_filter = wxStaticText(self, wx.ID_ANY, _("Device:"))
        sizer_3.Add(label_filter, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.text_filter = TextCtrl(self, wx.ID_ANY, "")
        sizer_3.Add(self.text_filter, 1, wx.EXPAND, 0)

        self.tree_devices = wxTreeCtrl(
            self,
            wx.ID_ANY,
            style=wx.BORDER_SUNKEN
            | wx.TR_HAS_BUTTONS
            | wx.TR_HIDE_ROOT
            | wx.TR_LINES_AT_ROOT
            | wx.TR_SINGLE,
        )
        # Used for proper sorting in the device add menu.
        self.sort_family_name = {
        _("K-Series CO2-Laser"): 99,
        _("Ortur Diode-Laser"): 98,
        _("Longer Diode-Laser"): 97,
        _("Newly CO2-Laser"): 96,
        _("Generic UV-Laser"): 95,
        _("Generic CO2-Laser"): 94,
        _("Generic Fibre-Laser"): 93,
        _("Generic Diode-Laser"): 92,
        _("Generic"): 91,
        }
        sizer_main.Add(self.tree_devices, 3, wx.EXPAND, 0)
        self.no_msg = (
            _("Click on a device to see more details about it.")
            + "\n"
            + _("You can as well search for your device at the top of this screen.")
        )
        self.label_info = wxStaticText(
            self,
            wx.ID_ANY,
            self.no_msg,
        )
        sizer_main.Add(self.label_info, 1, wx.EXPAND, 0)

        sizer_2 = wx.StdDialogButtonSizer()
        sizer_main.Add(sizer_2, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.button_OK = wxButton(self, wx.ID_OK, "")
        self.button_OK.SetDefault()
        sizer_2.AddButton(self.button_OK)

        self.button_CANCEL = wxButton(self, wx.ID_CANCEL, "")
        sizer_2.AddButton(self.button_CANCEL)

        sizer_2.Realize()

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        self.SetAffirmativeId(self.button_OK.GetId())
        self.SetEscapeId(self.button_CANCEL.GetId())
        self.device_type = ""
        self.device_info = ""
        self.filter = ""

        self.text_filter.SetToolTip(_("Quicksearch for device-entry"))
        self.tree_devices.SetToolTip(_("Select a matching entry for your new device"))

        self.text_filter.Bind(wx.EVT_TEXT, self.on_text_filter)
        self.tree_devices.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_selection)
        self.tree_devices.Bind(wx.EVT_LEFT_DCLICK, self.on_dclick)
        self.SetSize(dip_size(self, 350, 450))
        self.Layout()
        self.populate_tree()


    def populate_tree(self):
        tree = self.tree_devices
        tree.DeleteAllItems()
        tree_root = tree.AddRoot(_("Devices"))
        self.dev_infos = []
        for obj, name, sname in self.context.find("dev_info"):
            fam = obj.get("family", "")
            famnum = self.sort_family_name[fam] if fam in self.sort_family_name else 0
            key = f"{famnum}_{obj.get('priority', 0)}"
            self.dev_infos.append((obj, name, sname, key))
        # self.dev_infos = list(self.context.find("dev_info"))
        # self.dev_infos.sort(
        #     key=lambda e: str(self.sort_family_name[e[0].get("family", 0)])
        #     + "_"
        #     + str(e[0].get("priority", 0)),
        #     reverse=True,
        # )
        self.dev_infos.sort(key=lambda e: e[3], reverse=True)
        last_family = ""
        parent_item = tree_root
        index = -1
        for obj, name, sname, key in self.dev_infos:
            index += 1
            family = obj.get("family", "")
            info = obj.get("friendly_name", "")
            if self.filter and self.filter.lower() not in info.lower():
                continue
            if family != last_family:
                last_family = family
                parent_item = tree.AppendItem(tree_root, family)
            device_item = tree.AppendItem(parent_item, info)
            tree.SetItemData(device_item, index)
        # tree.ExpandAll()

    def on_text_filter(self, event):
        self.filter = self.text_filter.GetValue()
        self.populate_tree()

    def on_selection(self, event):
        tree = self.tree_devices
        self.device_type = ""
        self.device_info = ""
        info = ""
        item = event.GetItem()
        if item:
            try:
                if not tree.IsExpanded(item):
                    tree.ExpandAllChildren(item)
                index = tree.GetItemData(item)
                if index is not None and 0 <= index < len(self.dev_infos):
                    obj = self.dev_infos[index][0]
                    info = obj.get("extended_info", "")
                    self.device_type = obj.get("provider", "")
                    self.device_info = self.dev_infos[index][2]
            except RuntimeError:
                # Dialog has already been destroyed...
                return
        if info == "":
            info = self.no_msg
        self.label_info.SetLabel(info)
        self.button_OK.Enable(bool(self.device_type != ""))
        self.Layout()

    def on_dclick(self, event):
        if self.device_type:
            self.EndModal(self.GetAffirmativeId())
        else:
            item = self.tree_devices.GetFocusedItem()
            if not item:
                return
            if self.tree_devices.ItemHasChildren(item):
                if self.tree_devices.IsExpanded(item):
                    self.tree_devices.CollapseAllChildren(item)
                else:
                    self.tree_devices.ExpandAllChildren(item)


class DevicePanel(wx.Panel):
    def __init__(self, *args, context=None, pane=False, **kwds):
        # begin wxGlade: DevicesPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("devices")

        sizer_1 = StaticBoxSizer(self, wx.ID_ANY, _("Your Devices"), wx.VERTICAL)

        self.devices_list = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_REPORT
            | wx.LC_EDIT_LABELS
            | wx.LC_HRULES
            | wx.LC_SINGLE_SEL
            | wx.LC_SORT_ASCENDING,
            context=self.context,
            list_name="list_devices"
        )
        self.list_columns = {
            "device": 0,
            "driver": 1,
            "family": 2,
            "status": 3,
        }
        self.devices_list.InsertColumn(self.list_columns["device"], _("Device"))
        self.devices_list.InsertColumn(self.list_columns["driver"], _("Driver"))
        self.devices_list.InsertColumn(self.list_columns["family"], _("Type"))
        self.devices_list.InsertColumn(self.list_columns["status"], _("Status"))
        self.devices_list.resize_columns()
        sizer_1.Add(self.devices_list, 7, wx.EXPAND, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)
        # All devices
        self.devices = []
        # Active item in list
        self.current_item = 0

        self.button_create_device = wxButton(self, wx.ID_ANY, _("Create New Device"))
        sizer_3.Add(self.button_create_device, 0, 0, 0)

        self.button_copy_device = wxButton(self, wx.ID_ANY, _("Duplicate"))
        sizer_3.Add(self.button_copy_device, 0, 0, 0)

        self.button_rename_device = wxButton(self, wx.ID_ANY, _("Rename"))
        sizer_3.Add(self.button_rename_device, 0, 0, 0)

        self.button_remove_device = wxButton(self, wx.ID_ANY, _("Remove"))
        sizer_3.Add(self.button_remove_device, 0, 0, 0)

        self.button_activate_device = wxButton(self, wx.ID_ANY, _("Activate"))
        sizer_3.Add(self.button_activate_device, 0, 0, 0)
        sizer_3.AddStretchSpacer()
        self.button_config_device = wxButton(self, wx.ID_ANY, _("Config"))
        self.button_config_device.SetToolTip(
            _("Open the configuration window for the active device")
        )
        sizer_3.Add(self.button_config_device, 0, 0, 0)

        self.SetSizer(sizer_1)

        self.Layout()

        self.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.on_tree_device_activated, self.devices_list
        )
        # for wxMSW
        self.devices_list.Bind(
            wx.EVT_COMMAND_RIGHT_CLICK, self.on_tree_device_right_click
        )
        # for wxGTK
        self.devices_list.Bind(wx.EVT_RIGHT_UP, self.on_tree_device_right_click)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected, self.devices_list)
        self.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.on_item_deselected, self.devices_list
        )

        self.Bind(
            wx.EVT_BUTTON, self.on_button_create_device, self.button_create_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_copy_device, self.button_copy_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_remove_device, self.button_remove_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_rename_device, self.button_rename_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_activate_device, self.button_activate_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_config_device, self.button_config_device
        )
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_start_edit, self.devices_list)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_edit, self.devices_list)
        # end wxGlade

    def pane_show(self, *args):
        self.refresh_device_tree()
        if len(self.devices) > 0:
            self.devices_list.Select(0, 1)
        else:
            self.current_item = -1
        self.enable_controls()

    def pane_hide(self, *args):
        pass


    def on_start_edit(self, event):
        event.Allow()

    def on_end_edit(self, event):
        prohibited = "'" + '"' + "/"
        if event.IsEditCancelled():
            return
        label = event.GetLabel()

        # Certain-Characters are not allowed...
        for test in prohibited:
            if test in label:
                wx.Bell()
                event.Veto()
                return
        service = self.get_selected_device()
        if service is not None:
            service.label = label
            self.context.signal("label", label, service)
            self.context.signal("device;renamed")
        event.Skip()

    def recolor_device_items(self):
        # As we might be in darkmode, we can't just use wx.BLACK
        stdcol = self.button_create_device.GetForegroundColour()
        for idx in range(self.devices_list.GetItemCount()):
            item = self.devices_list.GetItem(idx)
            dev_index = item.GetData()
            service = self.devices[dev_index]
            if self.context.device is service:
                self.devices_list.SetItemTextColour(idx, wx.RED)
            else:
                self.devices_list.SetItemTextColour(idx, stdcol)

    @signal_listener("pause")
    @signal_listener("pipe;running")
    @signal_listener("activate;device")
    @signal_listener("device;renamed")
    @lookup_listener("service/device/available")
    def refresh_device_tree(self, *args):
        self.devices = []
        names = []
        for obj, name, sname in self.context.find("dev_info"):
            if obj is not None:
                try:
                    names.append(obj.get("friendly_name", sname.lower()))
                except AttributeError:
                    names.append(sname.lower())
        self.devices_list.DeleteAllItems()
        # root = self.devices_list.AddRoot("Devices")
        for i, device in enumerate(self.context.kernel.services("device")):
            self.devices.append(device)
            dev_index = len(self.devices) - 1
            label = device.label
            index = self.devices_list.InsertItem(
                self.devices_list.GetItemCount(), label
            )
            type_info = getattr(device, "name", device.path)
            dev_infos = list(self.context.find("dev_info"))
            dev_infos.sort(key=lambda e: e[0].get("priority", 0), reverse=True)
            family_default = ""
            for obj, name, sname in dev_infos:
                if device.registered_path == obj.get("provider", ""):
                    if "choices" in obj:
                        for prop in obj["choices"]:
                            if (
                                "attr" in prop
                                and "default" in prop
                                and prop["attr"] == "source"
                            ):
                                family_default = prop["default"]
                                break
                if family_default:
                    break

            family_info = device.setting(str, "source", family_default)
            if family_info:
                family_info = family_info.capitalize()
            active_status = ""
            try:
                if hasattr(device, "laser_status"):
                    active_status = device.laser_status
            except AttributeError:
                active_status = "??"

            try:
                if hasattr(device, "driver") and hasattr(device.driver, "paused"):
                    if device.driver.paused:
                        active_status = "paused"
            except AttributeError:
                pass

            self.devices_list.SetItem(index, self.list_columns["driver"], type_info)
            self.devices_list.SetItem(index, self.list_columns["family"], family_info)
            self.devices_list.SetItem(
                index, self.list_columns["status"], _(active_status)
            )
            self.devices_list.SetItemData(index, dev_index)
            if self.context.device is device:
                self.devices_list.SetItemTextColour(index, wx.RED)
        self.on_item_selected(None)

    def get_new_label_for_device(self, device_type):
        ct = 0
        maxid = 1
        label = ""
        device_type = device_type.lower()
        for i, device in enumerate(self.context.kernel.services("device")):
            # print (dir(device))
            # print ("checking %s vs %s (label=%s)" % (device_type, device.name, device.label))
            # print ("alias=%s, path=%s" % (device.alias, device.path))
            if device_type in device.path.lower():
                ct += 1
                if label == "":
                    label = device.label
                idx = device.label.find("#")
                if idx > 0:  # Needs to be after first character
                    idx_str = device.label[idx + 1 :]
                    if len(idx_str) > 0:
                        try:
                            num = int(idx_str)
                        except ValueError:
                            num = 0
                        maxid = max(maxid, num)
        if ct > 0:
            # There is already one...
            label += " #" + str(maxid + 1)
        # print ("Found: %d -> label=%s" % (ct, label))
        return label

    def on_item_selected(self, event):
        if event is None:
            self.current_item = self.devices_list.GetFirstSelected()
        else:
            self.current_item = event.Index
            event.Skip()
        self.enable_controls()

    def on_item_deselected(self, event):
        self.current_item = -1
        self.enable_controls()
        event.Skip()

    def enable_controls(self):
        if self.current_item < 0:
            flag1 = False
            flag2 = False
        else:
            flag1 = True
            flag2 = True
            dev_index = self.devices_list.GetItemData(self.current_item)
            if 0 <= dev_index < len(self.devices):
                data = self.devices[dev_index]
                if self.context.device is data:
                    flag2 = False
        self.button_activate_device.Enable(flag2)
        self.button_remove_device.Enable(flag2)
        self.button_rename_device.Enable(flag1)
        self.button_copy_device.Enable(flag1)

    def on_tree_device_activated(self, event):  # wxGlade: DevicePanel.<event_handler>
        dev_index = event.GetItem().GetData()
        if 0 <= dev_index < len(self.devices):
            device = self.devices[dev_index]
            if device is not None:
                device.kernel.activate_service_path("device", device.path)
                self.recolor_device_items()

    def on_tree_device_right_click(self, event):
        index = self.current_item
        if index < 0:
            event.Skip()
            return
        dev_index = self.devices_list.GetItemData(index)
        if 0 <= dev_index < len(self.devices):
            data = self.devices[dev_index]
            menu = wx.Menu()
            item0 = menu.Append(wx.ID_ANY, _("Duplicate"), "", wx.ITEM_NORMAL)
            self.Bind(wx.EVT_MENU, self.on_tree_popup_duplicate(data), item0)
            item1 = menu.Append(wx.ID_ANY, _("Rename"), "", wx.ITEM_NORMAL)
            self.Bind(wx.EVT_MENU, self.on_tree_popup_rename(data), item1)
            if self.context.device is not data:
                item2 = menu.Append(wx.ID_ANY, _("Remove"), "", wx.ITEM_NORMAL)
                self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(data), item2)
                item3 = menu.Append(wx.ID_ANY, _("Activate"), "", wx.ITEM_NORMAL)
                self.Bind(wx.EVT_MENU, self.on_tree_popup_activate(data), item3)
            else:
                item4 = menu.Append(wx.ID_ANY, _("Config"), "", wx.ITEM_NORMAL)
                self.Bind(wx.EVT_MENU, self.on_tree_popup_config(data), item4)
            self.PopupMenu(menu)
            menu.Destroy()

    def on_tree_popup_duplicate(self, service):
        def copyit(event=None):
            self.duplicate_device(service)

        return copyit

    def on_tree_popup_rename(self, service):
        def renameit(event=None):
            with wx.TextEntryDialog(
                None, _("What do you call this device?"), _("Device Label"), ""
            ) as dlg:
                dlg.SetValue(service.label)
                if dlg.ShowModal() == wx.ID_OK:
                    label = dlg.GetValue()
                    service.label = label
                    self.context.signal("label", label, service)
                    # self.refresh_device_tree()
                    self.context.signal("device;renamed")

        return renameit

    def on_tree_popup_delete(self, service):
        def deleteit(event=None):
            self.remove_device(service)

        return deleteit

    def on_tree_popup_activate(self, service):
        def activateit(event=None):
            if service is not None:
                service.kernel.activate_service_path("device", service.path)
                self.recolor_device_items()

        return activateit

    def on_tree_popup_config(self, service):
        def configit(event=None):
            if service is not None:
                service("window toggle Configuration\n")

        return configit

    def on_button_duplicate_device(self, event):
        service = self.get_selected_device()
        self.duplicate_device(service)

    def on_button_create_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        dlg = SelectDevice(None, wx.ID_ANY, context=self.context)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            device_type = dlg.device_type
            device_info = dlg.device_info
            label = self.get_new_label_for_device(device_type)
            if label:
                self.context(f'device add -i {device_info} -l "{label}"\n')
            else:
                self.context(f"device add -i {device_info}\n")
            self.refresh_device_tree()
            self.context.signal("device;modified")
        dlg.Destroy()

    def duplicate_device(self, service):
        if service is not None:
            self.context(f'device duplicate "{service.label}"\n')
            # We do it the simple way and copy the corresponding settings
            self.refresh_device_tree()
            self.context.signal("device;modified")

    def remove_device(self, service):
        if service is not None:
            if self.context.device is service:
                wx.MessageDialog(
                    None, _("Cannot remove the currently active device."), _("Error")
                ).ShowModal()
                return
            if self.context.kernel.yesno(
                _("Do you really want to remove this device?\nThis can not be undone!")
            ):
                try:
                    service.destroy()
                    self.context.signal("device;modified")
                except AttributeError:
                    pass
                self.refresh_device_tree()

    def on_button_remove_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        self.remove_device(service)

    def on_button_copy_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        self.duplicate_device(service)

    def on_button_activate_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        if service is not None:
            service.kernel.activate_service_path("device", service.path)
            self.recolor_device_items()

    def on_button_config_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        if service is not None:
            service("window toggle Configuration\n")

    def on_button_rename_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        if service is not None:
            with wx.TextEntryDialog(
                None, _("What do you call this device?"), _("Device Label"), ""
            ) as dlg:
                dlg.SetValue(service.label)
                if dlg.ShowModal() == wx.ID_OK:
                    label = dlg.GetValue()
                    service.label = label
                    self.context.signal("label", label, service)
                    self.context.signal("device;renamed")
            # self.refresh_device_tree()

    def get_selected_device(self):
        service = None
        idx = self.current_item
        if 0 <= idx < self.devices_list.GetItemCount():
            item = self.devices_list.GetItem(idx)
            dev_index = item.GetData()
            service = self.devices[dev_index]
        return service


class DeviceManager(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(653, 332, *args, **kwds)
        self.panel = DevicePanel(self, wx.ID_ANY, context=self.context)
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_manager.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Devices"))
        self.Layout()
        self.restore_aspect()

    @staticmethod
    def sub_register(kernel):
        if (
            hasattr(kernel.args, "lock_device_config")
            and kernel.args.lock_device_config
        ):
            return

        kernel.register("wxpane/Devices", register_panel)
        kernel.register(
            "button/device/DeviceManager",
            {
                "label": _("Devices"),
                "icon": icons8_manager,
                "tip": _("Opens Devices Window"),
                "help": "devices",
                "priority": -100,
                "action": lambda v: kernel.console("window toggle DeviceManager\n"),
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return "Device-Settings", "Device Manager"

    @staticmethod
    def helptext():
        return _("Manage and add devices to be used by MeerK40t")
