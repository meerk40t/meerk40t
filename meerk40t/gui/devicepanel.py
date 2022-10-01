import wx
from wx import aui

from meerk40t.gui.icons import icons8_manager_50
from meerk40t.gui.mwindow import MWindow
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

    window.on_pane_create(pane)
    context.register("pane/devices", pane)


class DevicePanel(wx.Panel):
    def __init__(self, *args, context=None, pane=False, **kwds):
        # begin wxGlade: DevicesPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_1 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Your Devices")), wx.VERTICAL
        )

        self.devices_list = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_REPORT
            | wx.LC_EDIT_LABELS
            | wx.LC_HRULES
            | wx.LC_SINGLE_SEL
            | wx.LC_SORT_ASCENDING,
        )
        self.devices_list.InsertColumn(0, _("Device"))
        self.devices_list.InsertColumn(1, _("Type"))
        sizer_1.Add(self.devices_list, 7, wx.EXPAND, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)
        # All devices
        self.devices = []
        # Active item in list
        self.current_item = 0

        self.button_create_device = wx.Button(self, wx.ID_ANY, _("Create New Device"))
        sizer_3.Add(self.button_create_device, 0, 0, 0)

        self.button_remove_device = wx.Button(self, wx.ID_ANY, _("Remove"))
        sizer_3.Add(self.button_remove_device, 0, 0, 0)

        self.button_rename_device = wx.Button(self, wx.ID_ANY, _("Rename"))
        sizer_3.Add(self.button_rename_device, 0, 0, 0)

        self.button_activate_device = wx.Button(self, wx.ID_ANY, _("Activate"))
        sizer_3.Add(self.button_activate_device, 0, 0, 0)

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
            wx.EVT_BUTTON, self.on_button_remove_device, self.button_remove_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_rename_device, self.button_rename_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_activate_device, self.button_activate_device
        )
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_edit, self.devices_list)
        self.Parent.Bind(wx.EVT_SIZE, self.on_resize)
        # end wxGlade

    def pane_show(self, *args):
        self.refresh_device_tree()
        if len(self.devices) > 0:
            self.devices_list.Select(0, 1)
        else:
            self.current_item = -1
        self.on_resize(None)
        self.enable_controls()

    def pane_hide(self, *args):
        pass

    def on_resize(self, event):
        if event is not None:
            event.Skip()
        size = self.devices_list.GetSize()
        if size[0] == 0 or size[1] == 0:
            return
        self.devices_list.SetColumnWidth(0, int(0.45 * size[0]))
        self.devices_list.SetColumnWidth(1, int(0.45 * size[0]))

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
            # self.refresh_device_tree()
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

    @signal_listener("activate;device")
    @lookup_listener("service/device/available")
    def refresh_device_tree(self, *args):
        self.devices = []
        names = []
        for obj, name, sname in self.context.find("provider", "device"):
            names.append(sname.lower())
        self.devices_list.DeleteAllItems()
        # root = self.devices_list.AddRoot("Devices")
        for i, device in enumerate(self.context.kernel.services("device")):
            self.devices.append(device)
            dev_index = len(self.devices) - 1
            lbl = device.label
            dev_name = ""
            for sname in names:
                if sname in device.path.lower():
                    dev_name = sname
                    break
            index = self.devices_list.InsertItem(self.devices_list.GetItemCount(), lbl)
            self.devices_list.SetItem(index, 1, dev_name)
            self.devices_list.SetItemData(index, dev_index)
            if self.context.device is device:
                self.devices_list.SetItemTextColour(index, wx.RED)

        self.devices_list.SetFocus()

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
        self.current_item = event.Index
        self.enable_controls()
        event.Skip()

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

    def on_tree_device_activated(self, event):  # wxGlade: DevicePanel.<event_handler>
        dev_index = event.GetItem().GetData()
        if 0 <= dev_index < len(self.devices):
            device = self.devices[dev_index]
            if device is not None:
                device.kernel.activate_service_path("device", device.path)
                self.recolor_device_items()

    def on_tree_device_right_click(self, event):
        index = self.current_item
        dev_index = self.devices_list.GetItemData(index)
        if 0 <= dev_index < len(self.devices):
            data = self.devices[dev_index]
            menu = wx.Menu()
            item1 = menu.Append(wx.ID_ANY, _("Rename"), "", wx.ITEM_NORMAL)
            self.Bind(wx.EVT_MENU, self.on_tree_popup_rename(data), item1)
            if self.context.device is not data:
                item2 = menu.Append(wx.ID_ANY, _("Remove"), "", wx.ITEM_NORMAL)
                self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(data), item2)
                item3 = menu.Append(wx.ID_ANY, _("Activate"), "", wx.ITEM_NORMAL)
                self.Bind(wx.EVT_MENU, self.on_tree_popup_activate(data), item3)
            self.PopupMenu(menu)
            menu.Destroy()

    def on_tree_popup_rename(self, service):
        def renameit(event=None):
            with wx.TextEntryDialog(
                None, _("What do you call this device?"), _("Device Label"), ""
            ) as dlg:
                dlg.SetValue(service.label)
                if dlg.ShowModal() == wx.ID_OK:
                    service.label = dlg.GetValue()
            self.refresh_device_tree()
            self.context.signal("device;renamed")

        return renameit

    def on_tree_popup_delete(self, service):
        def deleteit(event=None):
            if self.context.device is service:
                wx.MessageDialog(
                    None, _("Cannot remove the currently active device."), _("Error")
                ).ShowModal()
                return
            try:
                service.destroy()
                self.context.signal("device;modified")
            except AttributeError:
                pass
            self.refresh_device_tree()

        return deleteit

    def on_tree_popup_activate(self, service):
        def activateit(event=None):
            if service is not None:
                service.kernel.activate_service_path("device", service.path)
                self.recolor_device_items()

        return activateit

    def on_button_create_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        names = []
        for obj, name, sname in self.context.find("provider", "device"):
            names.append(sname)
        with wx.SingleChoiceDialog(
            None, _("What type of driver is being added?"), _("Device Type"), names
        ) as dlg:
            dlg.SetSelection(0)
            if dlg.ShowModal() == wx.ID_OK:
                device_type = names[dlg.GetSelection()]
                # Let's establish how many devices of this type
                # we already have and name it accordingly
                label = self.get_new_label_for_device(device_type)
                if label != "":
                    label = ' -l "' + label + '"'
                self.context(f"service device start -i {device_type}{label}\n")
        self.refresh_device_tree()
        self.context.signal("device;modified")

    def on_button_remove_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        if service is not None:
            if self.context.device is service:
                wx.MessageDialog(
                    None, _("Cannot remove the currently active device."), _("Error")
                ).ShowModal()
                return
            try:
                service.destroy()
                self.context.signal("device;modified")
            except AttributeError:
                pass
            self.refresh_device_tree()

    def on_button_activate_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        if service is not None:
            service.kernel.activate_service_path("device", service.path)
            self.recolor_device_items()

    def on_button_rename_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        service = self.get_selected_device()
        if service is not None:
            with wx.TextEntryDialog(
                None, _("What do you call this device?"), _("Device Label"), ""
            ) as dlg:
                dlg.SetValue(service.label)
                if dlg.ShowModal() == wx.ID_OK:
                    service.label = dlg.GetValue()
            self.refresh_device_tree()
            self.context.signal("device;renamed")

    def get_selected_device(self):
        service = None
        idx = self.current_item
        if idx >= 0:
            item = self.devices_list.GetItem(idx)
            dev_index = item.GetData()
            service = self.devices[dev_index]
        return service


class DeviceManager(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(653, 332, *args, **kwds)
        self.panel = DevicePanel(self, wx.ID_ANY, context=self.context)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_manager_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Devices"))

    @staticmethod
    def sub_register(kernel):
        kernel.register("wxpane/Devices", register_panel)
        kernel.register(
            "button/config/DeviceManager",
            {
                "label": _("Devices"),
                "icon": icons8_manager_50,
                "tip": _("Opens Devices Window"),
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
        return ("Device-Settings", "Device Manager")
