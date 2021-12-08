import wx
from wx import aui

from meerk40t.gui.icons import icons8_manager_50
from meerk40t.gui.mwindow import MWindow

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

    window.on_pane_add(pane)
    context.register("pane/devices", pane)


class DevicePanel(wx.Panel):
    def __init__(self, *args, context=None, pane=False, **kwds):
        # begin wxGlade: DevicesPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_1 = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Your Devices"), wx.VERTICAL
        )

        self.devices_tree = wx.TreeCtrl(self, wx.ID_ANY)
        sizer_1.Add(self.devices_tree, 7, wx.EXPAND, 0)

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)

        self.button_create_device = wx.Button(self, wx.ID_ANY, "Create New Device")
        sizer_3.Add(self.button_create_device, 0, 0, 0)

        self.button_remove_device = wx.Button(self, wx.ID_ANY, "Remove")
        sizer_3.Add(self.button_remove_device, 0, 0, 0)

        self.SetSizer(sizer_1)

        self.Layout()

        self.Bind(
            wx.EVT_TREE_ITEM_ACTIVATED, self.on_tree_device_activated, self.devices_tree
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_create_device, self.button_create_device
        )
        self.Bind(
            wx.EVT_BUTTON, self.on_button_remove_device, self.button_remove_device
        )
        # end wxGlade

    def pane_show(self, *args):
        self.refresh_device_tree()

    def pane_hide(self, *args):
        pass

    def refresh_device_tree(self):
        self.devices_tree.DeleteAllItems()
        root = self.devices_tree.AddRoot("Devices")
        for i, device in enumerate(self.context.kernel.services("device")):
            self.devices_tree.AppendItem(root, str(device), data=device)
        self.devices_tree.SetFocus()
        self.devices_tree.ExpandAllChildren(root)

    def on_tree_device_activated(self, event):  # wxGlade: DevicePanel.<event_handler>
        device = self.devices_tree.GetItemData(event.GetItem())
        device.kernel.activate_service_path("device", device.path)

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
                self.context(
                    "service device start {device_type}\n".format(
                        device_type=device_type
                    )
                )
        self.refresh_device_tree()

    def on_button_remove_device(self, event):  # wxGlade: DevicePanel.<event_handler>
        s = self.devices_tree.GetSelection()
        data = self.devices_tree.GetItemData(s)
        if self.context.device is data:
            wx.MessageDialog(None, _("Cannot remove the currently active device."), _("Error")).ShowModal()
            return
        data.destroy()

        self.refresh_device_tree()


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
                "action": lambda v: kernel.console("window toggle DeviceManager\n"),
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
