import time
from math import isinf

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

        self.info_label = wx.StaticText(self, wx.ID_ANY, _("Completed jobs:"))
        self.btn_clear = wx.Button(self, wx.ID_ANY, _("Clear History"))
        self.list_job_history = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_btn_clear, self.btn_clear)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.list_job_spool)
        self.Bind(
            wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_job_spool
        )
        # end wxGlade
        self._last_invokation = 0
        self.dirty = False
        self.update_buffer_size = False
        self.update_spooler_state = False
        self.update_spooler = True

        self.elements_progress = 0
        self.elements_progress_total = 0
        self.command_index = 0
        self.history = []
        self.listener_list = None
        self.list_lookup = {}
        if index == -1:
            disable_window(self)

    def __set_properties(self):
        # begin wxGlade: SpoolerPanel.__set_properties
        self.combo_device.SetToolTip(_("Select the device"))
        self.list_job_spool.SetToolTip(_("List and modify the queued operations"))
        self.list_job_spool.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
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
            _("Passes"), format=wx.LIST_FORMAT_LEFT, width=83
        )
        self.list_job_spool.AppendColumn(
            _("Priority"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_spool.AppendColumn(
            _("Runtime"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_spool.AppendColumn(
            _("Estimate"), format=wx.LIST_FORMAT_LEFT, width=73
        )

        self.list_job_history.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)

        self.list_job_history.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=143
        )
        self.list_job_history.AppendColumn(
            _("Start"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("End"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Runtime"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Device"), format=wx.LIST_FORMAT_LEFT, width=143
        )

        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: SpoolerPanel.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_frame.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_frame.Add(self.list_job_spool, 4, wx.EXPAND, 0)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.info_label, 1, wx.EXPAND, 0)
        hsizer.Add(self.btn_clear, 0, wx.EXPAND, 0)
        sizer_frame.Add(hsizer, 0, wx.EXPAND, 0)
        sizer_frame.Add(self.list_job_history, 2, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        sizer_frame.Fit(self)
        self.Layout()
        # end wxGlade

    def on_btn_clear(self, event):
        self.history = []
        self.list_job_history.DeleteAllItems()

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
        item = menu.Append(
            wx.ID_ANY,
            _("Remove {name}").format(name=str(element)[:16]),
            "",
            wx.ITEM_NORMAL,
        )
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(element), item)

        item = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), item)

        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_clear(self, element=None):
        def clear(event=None):
            spooler = self.selected_device.spooler
            spooler.clear_queue()
            self.refresh_spooler_list()

        return clear

    def on_tree_popup_delete(self, element, index=None):
        def delete(event=None):
            spooler = self.selected_device.spooler
            spooler.remove(element, index)
            self.refresh_spooler_list()

        return delete

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

        for idx, e in enumerate(spooler.queue):
            # Idx, Status, Type, Passes, Priority, Runtime, Estimate
            m = self.list_job_spool.InsertItem(idx, f"#{idx}")
            list_id = m
            spool_obj = e

            if list_id != -1:
                # IDX
                try:
                    self.list_job_spool.SetItem(list_id, 1, spool_obj.label)
                except AttributeError:
                    self.list_job_spool.SetItem(
                        list_id, 1, SpoolerPanel._name_str(spool_obj)
                    )

                # STATUS
                try:
                    status = spool_obj.status
                except AttributeError:
                    status = _("Queued")
                self.list_job_spool.SetItem(list_id, 2, status)

                # TYPE
                try:
                    self.list_job_spool.SetItem(
                        list_id, 3, str(spool_obj.__class__.__name__)
                    )
                except AttributeError:
                    pass

                # PASSES
                try:
                    loop = spool_obj.loops_executed
                    total = spool_obj.loops

                    if isinf(total):
                        total = "∞"
                    self.list_job_spool.SetItem(list_id, 4, f"{loop}/{total}")
                except AttributeError:
                    self.list_job_spool.SetItem(list_id, 4, "-")

                # Priority
                try:
                    self.list_job_spool.SetItem(list_id, 5, f"{spool_obj.priority}")
                except AttributeError:
                    self.list_job_spool.SetItem(list_id, 5, "-")

                # Runtime
                try:
                    t = spool_obj.elapsed_time()
                    hours, remainder = divmod(t, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                    self.list_job_spool.SetItem(list_id, 6, runtime)
                except AttributeError:
                    self.list_job_spool.SetItem(list_id, 6, "-")

                # Estimate Time
                try:
                    t = spool_obj.estimate_time()
                    hours, remainder = divmod(t, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                    self.list_job_spool.SetItem(list_id, 7, runtime)
                except AttributeError:
                    self.list_job_spool.SetItem(list_id, 7, "-")
        self._last_invokation = time.time()

    def refresh_history(self, newestinfo):
        def timestr(t, oneday):
            hours, remainder = divmod(t, 3600)
            if oneday:
                hours = hours % 24
            minutes, seconds = divmod(remainder, 60)
            result = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
            return result

        self.history.insert(0, newestinfo)
        self.list_job_history.DeleteAllItems()
        for idx, info in enumerate(self.history):
            list_id = self.list_job_history.InsertItem(
                self.list_job_history.GetItemCount(), f"#{idx}"
            )
            self.list_job_history.SetItem(list_id, 1, info[0])
            starttime = timestr(info[1], True)
            self.list_job_history.SetItem(list_id, 2, starttime)
            starttime = timestr(info[1] + info[2], True)
            self.list_job_history.SetItem(list_id, 3, starttime)
            runtime = timestr(info[2], False)
            self.list_job_history.SetItem(list_id, 4, runtime)
            self.list_job_history.SetItem(list_id, 5, info[3])

    @signal_listener("spooler;completed")
    def on_spooler_completed(self, origin, info, *args):
        # Info is just a tuple with the label and the runtime
        # print ("Signalled...", type(origin).__name__, type(info).__name__)
        # print(origin)
        # print(info)
        if info is None:
            return
        self.refresh_history(info)

    @signal_listener("spooler;queue")
    @signal_listener("spooler;idle")
    @signal_listener("spooler;realtime")
    def on_spooler_update(self, origin, value, *args, **kwargs):
        self.update_spooler = True
        self.refresh_spooler_list()

    @signal_listener("driver;position")
    @signal_listener("emulator;position")
    def on_device_update(self, origin, pos):
        # Only update every 2 seconds or so
        dtime = time.time()
        if dtime - self._last_invokation < 2:
            return
        spooler = self.selected_device.spooler
        if spooler is None:
            return
        if len(spooler.queue) != self.list_job_spool.GetItemCount():
            # Mismatch
            return
        self._last_invokation = dtime
        for idx, spool_obj in enumerate(spooler.queue):
            list_id = idx
            # Runtime
            try:
                t = spool_obj.elapsed_time()
                hours, remainder = divmod(t, 3600)
                minutes, seconds = divmod(remainder, 60)
                runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                self.list_job_spool.SetItem(list_id, 6, runtime)
            except AttributeError:
                self.list_job_spool.SetItem(list_id, 6, "-")

            # Estimate Time
            try:
                t = spool_obj.estimate_time()
                hours, remainder = divmod(t, 3600)
                minutes, seconds = divmod(remainder, 60)
                runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                self.list_job_spool.SetItem(list_id, 7, runtime)
            except AttributeError:
                self.list_job_spool.SetItem(list_id, 7, "-")


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
