import wx

_ = wx.GetTranslation


class DevicesPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: DevicesPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.devices_list = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.devices_list)
        self.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.on_list_item_activated, self.devices_list
        )
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_list_right_click, self.devices_list
        )
        self.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.on_list_item_selected, self.devices_list
        )
        self.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.on_list_item_selected, self.devices_list
        )
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: DevicesPanel.__set_properties
        self.devices_list.SetFont(
            wx.Font(
                13,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.devices_list.AppendColumn(_("Index"), format=wx.LIST_FORMAT_LEFT, width=56)
        self.devices_list.AppendColumn(
            _("Spooler"), format=wx.LIST_FORMAT_LEFT, width=74
        )
        self.devices_list.AppendColumn(
            _("Driver/Input"), format=wx.LIST_FORMAT_LEFT, width=170
        )
        self.devices_list.AppendColumn(
            _("Output"), format=wx.LIST_FORMAT_LEFT, width=170
        )
        self.devices_list.AppendColumn(
            _("Registered"), format=wx.LIST_FORMAT_LEFT, width=93
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: DevicesPanel.__do_layout
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(self.devices_list, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.Layout()
        # end wxGlade

    def initialize(self, *args):
        self.refresh_device_list()

    def finalize(self, *args):
        item = self.devices_list.GetFirstSelected()
        if item != -1:
            uid = self.devices_list.GetItem(item).Text
            self.context.device_primary = uid

    def refresh_device_list(self):
        self.devices_list.DeleteAllItems()
        for i, dev in enumerate(self.context.match("device")):
            device = self.context.registered[dev]
            spooler, input_driver, output = device
            device_context = self.context.get_context("devices")
            dev_string = "device_%d" % i
            if hasattr(device_context, dev_string):
                line = getattr(device_context, dev_string)
                registered = len(line) > 0
            else:
                registered = False
            m = self.devices_list.InsertItem(i, str(i))
            if self.context.active == str(m):
                self.devices_list.SetItemBackgroundColour(m, wx.LIGHT_GREY)

            if m != -1:
                spooler_name = spooler.name if spooler is not None else "None"
                self.devices_list.SetItem(m, 1, str(spooler_name))
                self.devices_list.SetItem(m, 2, str(input_driver))
                self.devices_list.SetItem(m, 3, str(output))
                self.devices_list.SetItem(m, 4, str(registered))

    def on_list_drag(self, event):  # wxGlade: DeviceManager.<event_handler>
        pass

    def on_list_right_click(self, event):  # wxGlade: DeviceManager.<event_handler>
        uid = event.GetLabel()
        self.refresh_device_list()

    def on_list_item_selected(self, event=None):
        item = self.devices_list.GetFirstSelected()

    def on_list_item_activated(
        self, event=None
    ):  # wxGlade: DeviceManager.<event_handler>
        item = self.devices_list.GetFirstSelected()
        if item == -1:
            return
        uid = self.devices_list.GetItem(item).Text
        self.context("device activate %s\n" % uid)
        self.refresh_device_list()
