import wx
from wx import aui

from meerk40t.gui.icons import icons8_route_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import disable_window
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


def register_panel_spooler(window, context):
    panel = SpoolerPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Bottom()
        .Layer(1)
        .MinSize(600, 100)
        .FloatingSize(600, 230)
        .Caption(_("Spooler"))
        .Name("spooler")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 600
    pane.control = panel

    window.on_pane_add(pane)
    context.register("pane/spooler", pane)


class SpoolerPanel(wx.Panel):
    def __init__(self, *args, context=None, selected_device=None, **kwds):
        # begin wxGlade: SpoolerPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.available_devices = context.kernel.services("device")
        if selected_device is not None:
            self.selected_device = self.available_devices[selected_device]
        else:
            self.selected_device = self.context.device
        index = -1
        for i, s in enumerate(self.available_devices):
            if s is self.selected_device:
                index = i
                break
        spools = [s.label for s in self.available_devices]

        self.combo_device = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(index)

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
        if index == -1:
            disable_window(self)

    def __set_properties(self):
        # begin wxGlade: SpoolerPanel.__set_properties
        self.combo_device.SetToolTip(_("Select the device"))
        self.list_job_spool.SetToolTip(_("List and modify the queued operations"))
        self.list_job_spool.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=78)
        self.list_job_spool.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=143
        )
        self.list_job_spool.AppendColumn(
            _("Status"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_spool.AppendColumn(
            _("Type"), format=wx.LIST_FORMAT_LEFT, width=60
        )
        self.list_job_spool.AppendColumn(
            _("Speed"), format=wx.LIST_FORMAT_LEFT, width=83
        )
        self.list_job_spool.AppendColumn(
            _("Settings"), format=wx.LIST_FORMAT_LEFT, width=223
        )
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: SpoolerPanel.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_frame.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_frame.Add(self.list_job_spool, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        sizer_frame.Fit(self)
        self.Layout()
        # end wxGlade

    def on_combo_device(self, event=None):  # wxGlade: Spooler.<event_handler>
        index = self.combo_device.GetSelection()
        self.selected_device = self.available_devices[index]
        self.update_spooler = True
        self.refresh_spooler_list()

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        event.Skip()

    def on_item_rightclick(self, event):  # wxGlade: JobSpooler.<event_handler>
        index = event.Index
        spooler = self.selected_device.spooler
        try:
            element = spooler.queue[index]
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

    def pane_show(self, *args):
        self.refresh_spooler_list()

    def pane_hide(self, *args):
        pass

    @staticmethod
    def _name_str(named_obj):
        try:
            return named_obj.__name__
        except AttributeError:
            return str(named_obj)

    def set_spool_item(self, list_id, spool_obj, status=None):
        if list_id != -1:
            self.list_job_spool.SetItem(list_id, 1, SpoolerPanel._name_str(spool_obj))
            if status is not None:
                self.list_job_spool.SetItem(list_id, 2, status)

            try:
                self.list_job_spool.SetItem(list_id, 3, str(spool_obj))
            except AttributeError:
                pass
            try:
                self.list_job_spool.SetItem(list_id, 4, _("%.1fmm/s") % spool_obj.speed)
            except AttributeError:
                pass
            settings = list()
            try:
                settings.append(_("power=%g") % spool_obj.power)
            except AttributeError:
                pass
            try:
                settings.append(_("step=%d") % spool_obj.raster_step_x)
            except AttributeError:
                pass
            try:
                settings.append(_("overscan=%s") % str(spool_obj.overscan))
            except AttributeError:
                pass
            self.list_job_spool.SetItem(list_id, 5, " ".join(settings))

    def refresh_spooler_list(self):
        if not self.update_spooler:
            return

        try:
            self.list_job_spool.DeleteAllItems()
        except RuntimeError:
            return

        spooler = self.selected_device.spooler
        if spooler is None:
            return
        idx = 0
        if spooler.current is not None:
            m = self.list_job_spool.InsertItem(idx, _("Current"))
            self.set_spool_item(m, spooler.current, status=_("running"))
            idx += 1

        if len(spooler.realtime_queue) > 0:
            for e in spooler.queue:
                m = self.list_job_spool.InsertItem(idx, f"#{idx}")
                self.set_spool_item(m, e, status=_("realtime"))
                idx += 1

        if len(spooler.queue) > 0:
            for e in spooler.queue:
                m = self.list_job_spool.InsertItem(idx, f"#{idx}")
                self.set_spool_item(m, e, status=_("queued"))
                idx += 1

        if spooler.idle is not None:
            m = self.list_job_spool.InsertItem(idx, _("Idle"))
            self.set_spool_item(m, spooler.idle, status=_("idle"))
            idx += 1

    def on_tree_popup_clear(self, element=None):
        def delete(event=None):
            spooler = self.selected_device.spooler
            spooler.clear_queue()
            self.refresh_spooler_list()

        return delete

    def on_tree_popup_delete(self, element, index=None):
        def delete(event=None):
            spooler = self.selected_device.spooler
            spooler.remove(element, index)
            self.refresh_spooler_list()

        return delete

    @signal_listener("spooler;queue")
    @signal_listener("spooler;idle")
    @signal_listener("spooler;realtime")
    def on_spooler_update(self, origin, value, *args, **kwargs):
        self.update_spooler = True
        self.refresh_spooler_list()


class JobSpooler(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(673, 456, *args, **kwds)
        selected_device = None
        if len(args) >= 4 and args[3]:
            selected_device = args[3]
        self.panel = SpoolerPanel(
            self, wx.ID_ANY, context=self.context, selected_device=selected_device
        )
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_route_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Job Spooler"))
        self.Layout()

    @staticmethod
    def sub_register(kernel):
        kernel.register("wxpane/JobSpooler", register_panel_spooler)
        kernel.register(
            "button/control/Spooler",
            {
                "label": _("Spooler"),
                "icon": icons8_route_50,
                "tip": _("Opens Spooler Window"),
                "action": lambda v: kernel.console("window toggle JobSpooler\n"),
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
