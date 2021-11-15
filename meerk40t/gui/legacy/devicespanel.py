import wx
from wx import aui

from meerk40t.gui.icons import icons8_manager_50, icons8_plus_50, icons8_trash_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


def register_panel(window, context):
    panel = DevicesPanel(window, wx.ID_ANY, context=context, pane=True)
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


class DevicesPanel(wx.Panel):
    def __init__(self, *args, context=None, pane=False, **kwds):
        # begin wxGlade: DevicesPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.new_device_button = wx.BitmapButton(
            self, wx.ID_ANY, icons8_plus_50.GetBitmap()
        )
        self.remove_device_button = wx.BitmapButton(
            self, wx.ID_ANY, icons8_trash_50.GetBitmap()
        )
        self.devices_list = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
        )
        if pane:
            self.remove_device_button.Hide()
            self.new_device_button.Hide()

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
            _("Output"), format=wx.LIST_FORMAT_LEFT, width=220
        )
        self.devices_list.AppendColumn(
            _("Registered"), format=wx.LIST_FORMAT_LEFT, width=93
        )
        self.new_device_button.SetToolTip(_("Add a new device"))
        self.new_device_button.SetSize(self.new_device_button.GetBestSize())
        self.remove_device_button.SetToolTip(_("Remove selected device"))
        self.remove_device_button.SetSize(self.remove_device_button.GetBestSize())
        # end wxGlade
        # begin wxGlade: DeviceManager.__do_layout
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(self.devices_list, 1, wx.EXPAND, 0)
        if not pane:
            button_sizer = wx.BoxSizer(wx.VERTICAL)
            button_sizer.Add(self.new_device_button, 0, 0, 0)
            button_sizer.Add(self.remove_device_button, 0, 0, 0)
            main_sizer.Add(button_sizer, 0, wx.EXPAND, 0)
            self.new_device_button.Enable(False)
            self.remove_device_button.Enable(False)

        self.SetSizer(main_sizer)
        self.Layout()
        # end wxGlade

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
        self.Bind(wx.EVT_BUTTON, self.on_button_new, self.new_device_button)
        self.Bind(wx.EVT_BUTTON, self.on_button_remove, self.remove_device_button)
        # end wxGlade

    def __set_properties(self):
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
        self.new_device_button.SetToolTip(_("Add a new device"))
        self.new_device_button.SetSize(self.new_device_button.GetBestSize())
        self.remove_device_button.SetToolTip(_("Remove selected device"))
        self.remove_device_button.SetSize(self.remove_device_button.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: DeviceManager.__do_layout
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.devices_list, 0, wx.EXPAND, 0)
        button_sizer.Add(self.new_device_button, 0, 0, 0)
        button_sizer.Add(self.remove_device_button, 0, 0, 0)
        main_sizer.Add(button_sizer, 0, wx.EXPAND, 0)
        self.new_device_button.Enable(False)
        self.remove_device_button.Enable(False)
        self.SetSizer(main_sizer)
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
        select = None
        for i, find in enumerate(self.context.find("device")):
            device, dev, dev_suffix = find
            spooler, input_device, output = device
            device_context = self.context.get_context("devices")
            dev_string = "device_%s" % dev_suffix
            if hasattr(device_context, dev_string):
                line = getattr(device_context, dev_string)
                registered = len(line) > 0
            else:
                registered = False
            m = self.devices_list.InsertItem(i, str(i))
            if self.context.device.active == str(m):
                select = i
                from ..icons import DARKMODE

                if DARKMODE:
                    self.devices_list.SetItemBackgroundColour(m, wx.Colour(64, 64, 64))
                else:
                    self.devices_list.SetItemBackgroundColour(m, wx.LIGHT_GREY)
            if m != -1:
                spooler_name = spooler.name if spooler is not None else "None"
                self.devices_list.SetItem(m, 1, str(spooler_name))
                self.devices_list.SetItem(m, 2, str(input_device))
                self.devices_list.SetItem(m, 3, str(output))
                self.devices_list.SetItem(m, 4, str(registered))
            self.devices_list.SetFocus()
            if select is not None:
                self.devices_list.Select(select)

    def on_list_drag(self, event):  # wxGlade: DeviceManager.<event_handler>
        pass

    def on_list_right_click(self, event):  # wxGlade: DeviceManager.<event_handler>
        uid = event.GetLabel()
        self.refresh_device_list()

    def on_list_item_selected(self, event=None):
        item = self.devices_list.GetFirstSelected()
        self.new_device_button.Enable(item != -1)
        self.remove_device_button.Enable(item != -1)

    def on_list_item_activated(
        self, event=None
    ):  # wxGlade: DeviceManager.<event_handler>
        item = self.devices_list.GetFirstSelected()
        if item == -1:
            return
        uid = self.devices_list.GetItem(item).Text
        self.context("device activate %s\n" % uid)
        self.context("timer 1 0.2 window close DeviceManager\n")

    def on_button_new(self, event=None):  # wxGlade: DeviceManager.<event_handler>
        item = self.devices_list.GetFirstSelected()
        if item == -1:
            return
        spooler_input = self.devices_list.GetItem(item).Text
        # END SPOOLER

        names = list(self.context.match("driver", suffix=True))
        dlg = wx.SingleChoiceDialog(
            None, _("What type of driver is being added?"), _("Device Type"), names
        )
        dlg.SetSelection(0)
        if dlg.ShowModal() == wx.ID_OK:
            device_type = names[dlg.GetSelection()]
        else:
            dlg.Destroy()
            return
        dlg.Destroy()
        # END Driver

        names = list(self.context.match("output", suffix=True))
        dlg = wx.SingleChoiceDialog(
            None, _("Where does the device output data?"), _("Output Type"), names
        )
        dlg.SetSelection(0)
        if dlg.ShowModal() == wx.ID_OK:
            output_type = names[dlg.GetSelection()]
        else:
            dlg.Destroy()
            return
        dlg.Destroy()
        # END OUTPUT

        if output_type == "file":
            dlg = wx.TextEntryDialog(
                None,
                _("What filename does this device output to?"),
                _("Output"),
            )
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetValue()
            else:
                dlg.Destroy()
                return
            self.context("device delete %s\n" % spooler_input)
            self.context(
                "spool%s -r driver -n %s outfile %s\n"
                % (spooler_input, device_type, filename)
            )

            dlg.Destroy()
            self.refresh_device_list()
            return

        if output_type == "tcp":
            dlg = wx.TextEntryDialog(
                None,
                _("What network address does this device output to?"),
                _("Output"),
            )
            if dlg.ShowModal() == wx.ID_OK:
                address = dlg.GetValue()
            else:
                dlg.Destroy()
                return
            dlg.Destroy()

            port = None
            if ":" in address:
                port = address.split(":")[-1]
                try:
                    port = int(port)
                    address = address.split(":")[0]
                except ValueError:
                    port = None

            if port is None:
                dlg = wx.TextEntryDialog(
                    None,
                    _("What network port does this device output to?"),
                    _("Output"),
                )
                if dlg.ShowModal() == wx.ID_OK:
                    port = dlg.GetValue()
                else:
                    dlg.Destroy()
                    return
                dlg.Destroy()
            self.context("device delete %s\n" % spooler_input)
            self.context(
                "spool%s -r driver -n %s tcp %s %s\n"
                % (spooler_input, device_type, address, str(port))
            )

            self.refresh_device_list()
            return

        self.context("device delete %s\n" % spooler_input)
        self.context(
            "spool%s -r driver -n %s output -n %s\n"
            % (spooler_input, device_type, output_type)
        )
        self.refresh_device_list()
        self.context.get_context("devices").flush()

    def on_button_remove(self, event=None):  # wxGlade: DeviceManager.<event_handler>
        item = self.devices_list.GetFirstSelected()
        if item == -1:
            return
        uid = self.devices_list.GetItem(item).Text
        self.context("device delete %s\n" % uid)
        self.refresh_device_list()


class DeviceManager(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(653, 332, *args, **kwds)

        self.panel = DevicesPanel(self, wx.ID_ANY, context=self.context)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_manager_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Device Manager"))

    def window_open(self):
        self.panel.initialize()

    def window_close(self):
        self.panel.finalize()
