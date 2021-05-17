import wx

from .icons import icons8_route_50
from .mwindow import MWindow

_ = wx.GetTranslation


class JobSpooler(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(673, 456, *args, **kwds)

        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        selected_spooler = self.context.root.active
        spools = [str(i) for i in self.context.match("device", suffix=True)]
        index = spools.index(selected_spooler)
        self.connected_name = spools[index]
        self.connected_spooler, self.connected_driver, self.connected_output = (
            None,
            None,
            None,
        )
        try:
            (
                self.connected_spooler,
                self.connected_driver,
                self.connected_output,
            ) = self.available_devices[index]
        except IndexError:
            for m in self.Children:
                if isinstance(m, wx.Window):
                    m.Disable()
        spools = [" -> ".join(map(repr, ad)) for ad in self.available_devices]
        self.combo_device = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(index)
        self.text_time_laser = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_travel = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_total = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_total_copy = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.list_job_spool = wx.ListCtrl(
            self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.list_job_spool)
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_job_spool
        )
        # end wxGlade
        self.dirty = False
        self.update_buffer_size = False
        self.update_spooler_state = False
        self.update_spooler = True

        self.elements_progress = 0
        self.elements_progress_total = 0
        self.command_index = 0
        self.listener_list = None
        self.list_lookup = {}

    def __set_properties(self):
        # begin wxGlade: Spooler.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_route_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle("Job Spooler")
        self.combo_device.SetToolTip("Select the device")
        self.text_time_laser.SetToolTip("Time Estimate: Lasering Time")
        self.text_time_travel.SetToolTip("Time Estimate: Traveling Time")
        self.text_time_total.SetToolTip("Time Estimate: Total Time")
        self.text_time_total_copy.SetToolTip("Time Estimate: Total Time")
        self.list_job_spool.SetToolTip("List and modify the queued operations")
        self.list_job_spool.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=78)
        self.list_job_spool.AppendColumn("Name", format=wx.LIST_FORMAT_LEFT, width=143)
        self.list_job_spool.AppendColumn("Status", format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=53)
        self.list_job_spool.AppendColumn("Speed", format=wx.LIST_FORMAT_LEFT, width=83)
        self.list_job_spool.AppendColumn(
            "Settings", format=wx.LIST_FORMAT_LEFT, width=223
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Spooler.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_remaining = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Time Remaining"), wx.VERTICAL
        )
        sizer_total_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Total Time"), wx.VERTICAL
        )
        sizer_travel_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Travel Time"), wx.VERTICAL
        )
        sizer_laser_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Laser Time"), wx.VERTICAL
        )
        sizer_frame.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_laser_time.Add(self.text_time_laser, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_laser_time, 1, wx.EXPAND, 0)
        sizer_travel_time.Add(self.text_time_travel, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_travel_time, 1, wx.EXPAND, 0)
        sizer_total_time.Add(self.text_time_total, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_total_time, 1, wx.EXPAND, 0)
        sizer_total_remaining.Add(self.text_time_total_copy, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_total_remaining, 1, wx.EXPAND, 0)
        sizer_frame.Add(sizer_time, 0, wx.EXPAND, 0)
        sizer_frame.Add(self.list_job_spool, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        self.Layout()
        # end wxGlade

    def on_combo_device(self, event):  # wxGlade: Spooler.<event_handler>
        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        index = self.combo_device.GetSelection()
        (
            self.connected_spooler,
            self.connected_driver,
            self.connected_output,
        ) = self.available_devices[index]
        self.update_spooler = True
        self.refresh_spooler_list()

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        event.Skip()

    def on_item_rightclick(self, event):  # wxGlade: JobSpooler.<event_handler>
        index = event.Index
        spooler = self.connected_spooler
        try:
            element = spooler._queue[index]
        except IndexError:
            return
        menu = wx.Menu()
        convert = menu.Append(
            wx.ID_ANY, _("Remove %s") % str(element)[:16], "", wx.ITEM_NORMAL
        )
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(element), convert)
        convert = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def window_open(self):
        self.context.listen("spooler;queue", self.on_spooler_update)
        self.refresh_spooler_list()

    def window_close(self):
        self.context.unlisten("spooler;queue", self.on_spooler_update)

    def refresh_spooler_list(self):
        if not self.update_spooler:
            return
        if not self.connected_spooler:
            return

        def name_str(e):
            try:
                return e.__name__
            except AttributeError:
                return str(e)

        try:
            self.list_job_spool.DeleteAllItems()
        except RuntimeError:
            return

        spooler = self.connected_spooler
        if len(spooler._queue) > 0:
            # This should actually process and update the queue items.
            for i, e in enumerate(spooler._queue):
                m = self.list_job_spool.InsertItem(i, "#%d" % i)
                if m != -1:
                    self.list_job_spool.SetItem(m, 1, name_str(e))
                    try:
                        self.list_job_spool.SetItem(m, 2, e._status_value)
                    except AttributeError:
                        pass
                    try:
                        self.list_job_spool.SetItem(m, 3, e.operation)
                    except AttributeError:
                        pass
                    try:
                        self.list_job_spool.SetItem(m, 4, _("%.1fmm/s") % (e.speed))
                    except AttributeError:
                        pass
                    settings = list()
                    try:
                        settings.append(_("power=%g") % (e.power))
                    except AttributeError:
                        pass
                    try:
                        settings.append(_("step=%d") % (e.raster_step))
                    except AttributeError:
                        pass
                    try:
                        settings.append(_("overscan=%d") % (e.overscan))
                    except AttributeError:
                        pass
                    self.list_job_spool.SetItem(m, 5, " ".join(settings))

    def on_tree_popup_clear(self, element):
        def delete(event):
            spooler = self.connected_spooler
            spooler.clear_queue()
            self.refresh_spooler_list()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event):
            spooler = self.connected_spooler
            spooler.remove(element)
            self.refresh_spooler_list()

        return delete

    def on_spooler_update(self, origin, value, *args, **kwargs):
        self.update_spooler = True
        self.refresh_spooler_list()
