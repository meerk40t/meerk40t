import time
from math import isinf, isnan

import wx
import wx.lib.mixins.listctrl as listmix
from wx import aui

from meerk40t.gui.icons import (
    icons8_emergency_stop_button_50,
    icons8_pause_50,
    icons8_route_50,
)
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation

# History Indices
IDX_HISTORY_JOBNAME = 0
IDX_HISTORY_START = 1
IDX_HISTORY_DURATION = 2
IDX_HISTORY_DEVICE = 3
IDX_HISTORY_PASSES = 4
IDX_HISTORY_STATUS = 5
IDX_HISTORY_INFO = 6
IDX_HISTORY_ESTIMATE = 7
IDX_HISTORY_STEPS_DONE = 8
IDX_HISTORY_STEPS_TOTAL = 9
IDX_HISTORY_LOOPS_DONE = 10
# Amount of columns...
IDX_HISTORY_MAX_FIELDS = IDX_HISTORY_LOOPS_DONE + 1


HC_INDEX = 0
HC_DEVICE = 1
HC_JOBNAME = 2
HC_START = 3
HC_END = 4
HC_RUNTIME = 5
HC_ESTIMATE = 6
HC_STEPS = 7
HC_PASSES = 8
HC_STATUS = 9
HC_JOBINFO = 10


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

    window.on_pane_create(pane)
    context.register("pane/spooler", pane)


class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    """TextEditMixin allows any column to be edited."""

    # ----------------------------------------------------------------------
    def __init__(
        self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0
    ):
        """Constructor"""
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)


class SpoolerPanel(wx.Panel):
    def __init__(self, *args, context=None, selected_device=None, **kwds):
        # begin wxGlade: SpoolerPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.selected_device = selected_device
        self.available_devices = context.kernel.services("device")
        self.filter_device = None
        spools = [s.label for s in self.available_devices]
        spools.insert(0, _("-- All available devices --"))
        self.queue_entries = []
        self.context.setting(int, "spooler_sash_position", 0)
        self.context.setting(bool, "spool_history_clear_on_start", False)
        self.clear_data = self.context.spool_history_clear_on_start
        self.context.setting(bool, "spool_ignore_helper_jobs", True)

        self.splitter = wx.SplitterWindow(self, id=wx.ID_ANY, style=wx.SP_LIVE_UPDATE)
        sty = wx.BORDER_SUNKEN

        self.win_top = wx.Window(self.splitter, style=sty)
        self.win_bottom = wx.Window(self.splitter, style=sty)
        self.splitter.SetMinimumPaneSize(50)
        self.splitter.SplitHorizontally(self.win_top, self.win_bottom, -100)
        self.splitter.SetSashPosition(self.context.spooler_sash_position)
        self.combo_device = wx.ComboBox(
            self.win_top, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(0)  # All by default...
        self.button_pause = wx.Button(self.win_top, wx.ID_ANY, _("Pause"))
        self.button_pause.SetToolTip(_("Pause/Resume the laser"))
        self.button_pause.SetBitmap(icons8_pause_50.GetBitmap(resize=25))
        self.button_stop = wx.Button(self.win_top, wx.ID_ANY, _("Abort"))
        self.button_stop.SetToolTip(_("Stop the laser"))
        self.button_stop.SetBitmap(icons8_emergency_stop_button_50.GetBitmap(resize=25))
        self.button_stop.SetBackgroundColour(wx.Colour(127, 0, 0))

        self.list_job_spool = wx.ListCtrl(
            self.win_top, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES
        )

        self.info_label = wx.StaticText(
            self.win_bottom, wx.ID_ANY, _("Completed jobs:")
        )
        self.btn_clear = wx.Button(self.win_bottom, wx.ID_ANY, _("Clear History"))
        self.list_job_history = EditableListCtrl(
            self.win_bottom,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )

        self.__set_properties()
        self.__do_layout()
        self.current_item = None
        self.Bind(wx.EVT_BUTTON, self.on_btn_clear, self.btn_clear)
        self.btn_clear.Bind(wx.EVT_RIGHT_DOWN, self.on_btn_clear_right)
        self.list_job_history.Bind(wx.EVT_RIGHT_DOWN, self.on_btn_clear_right)
        self.list_job_history.Bind(
            wx.EVT_LIST_BEGIN_LABEL_EDIT, self.before_history_update
        )
        self.list_job_history.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_history_update)
        self.Bind(wx.EVT_BUTTON, self.on_button_pause, self.button_pause)
        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.list_job_spool)

        self.splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.on_sash_changed)
        self.splitter.Bind(wx.EVT_SPLITTER_DOUBLECLICKED, self.on_sash_double)

        self.list_job_spool.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        # self.list_job_spool.Bind(wx.EVT_LEFT_DCLICK, self.on_item_doubleclick)
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
        self.column_job = {
            "idx": 0,
            "device": 1,
            "jobname": 2,
            "entries": 3,
            "status": 4,
            "type": 5,
            "steps": 6,
            "passes": 7,
            "priority": 8,
            "runtime": 9,
            "estimate": 10,
        }
        self.map_item_key = {}
        self.refresh_history()
        self.set_pause_color()

    def __set_properties(self):
        # begin wxGlade: SpoolerPanel.__set_properties
        self.combo_device.SetToolTip(_("Select the device"))
        self.list_job_spool.SetToolTip(_("List and modify the queued operations"))
        self.list_job_spool.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_job_spool.AppendColumn(
            _("Device"),
            format=wx.LIST_FORMAT_LEFT,
            width=95,
        )
        self.list_job_spool.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_job_spool.AppendColumn(
            _("Items"), format=wx.LIST_FORMAT_LEFT, width=45
        )
        self.list_job_spool.AppendColumn(
            _("Status"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_spool.AppendColumn(
            _("Type"), format=wx.LIST_FORMAT_LEFT, width=60
        )
        self.list_job_spool.AppendColumn(
            _("Steps"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_spool.AppendColumn(
            _("Passes"), format=wx.LIST_FORMAT_LEFT, width=73
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

        self.list_job_history.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=48)

        self.list_job_history.AppendColumn(
            _("Device"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_job_history.AppendColumn(
            _("Start"), format=wx.LIST_FORMAT_LEFT, width=113
        )
        self.list_job_history.AppendColumn(
            _("End"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Runtime"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Estimate"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Steps"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Passes"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Status"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_history.AppendColumn(
            _("Jobinfo"), format=wx.LIST_FORMAT_LEFT, width=wx.LIST_AUTOSIZE_USEHEADER
        )

        # end wxGlade

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_top = wx.BoxSizer(wx.VERTICAL)
        sizer_bottom = wx.BoxSizer(wx.VERTICAL)
        sizer_combo_cmds = wx.BoxSizer(wx.HORIZONTAL)
        sizer_combo_cmds.Add(self.combo_device, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_combo_cmds.Add(self.button_pause, 0, wx.EXPAND, 0)
        sizer_combo_cmds.Add(self.button_stop, 0, wx.EXPAND, 0)

        sizer_top.Add(sizer_combo_cmds, 0, wx.EXPAND, 0)
        sizer_top.Add(self.list_job_spool, 4, wx.EXPAND, 0)
        self.win_top.SetSizer(sizer_top)
        sizer_top.Fit(self.win_top)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.info_label, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        hsizer.Add(self.btn_clear, 0, wx.EXPAND, 0)
        sizer_bottom.Add(hsizer, 0, wx.EXPAND, 0)
        sizer_bottom.Add(self.list_job_history, 2, wx.EXPAND, 0)
        self.win_bottom.SetSizer(sizer_bottom)
        sizer_bottom.Fit(self.win_bottom)

        sizer_main.Add(self.splitter, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        sizer_main.Fit(self)
        self.Layout()
        # end wxGlade

    def on_sash_changed(self, event):
        position = self.splitter.GetSashPosition()
        self.context.spooler_sash_position = position

    def on_sash_double(self, event):
        self.splitter.SetSashPosition(0, True)
        self.context.spooler_sash_position = 0

    def on_item_selected(self, event):
        self.current_item = event.Index

    def clear_history(self, older_than=None):
        if self.filter_device:
            to_remove = list(self.context.logging.matching_events("job", device=self.context.device.label))
        else:
            to_remove = list(self.context.logging.matching_events("job"))
        for key, event in to_remove:
            del self.context.logging.logs[key]
        self.refresh_history()

    def on_btn_clear(self, event):
        self.clear_history(None)

    def on_btn_clear_right(self, event):
        def on_menu_index(idx_to_delete):
            def check(event):
                self.history.pop(idx_to_delete)
                self.refresh_history()

            return check

        def on_menu_time(cutoff):
            def check(event):
                self.clear_history(cutoff)

            return check

        def toggle_1(event):
            self.context.spool_history_clear_on_start = (
                not self.context.spool_history_clear_on_start
            )

        def toggle_2(event):
            self.context.spool_ignore_helper_jobs = (
                not self.context.spool_ignore_helper_jobs
            )

        now = time.time()
        week_seconds = 60 * 60 * 24 * 7
        options = [(_("All entries"), None)]
        for week in range(1, 5):
            cutoff_time = now - week * week_seconds
            options.append((_("Older than {week} week").format(week=week), cutoff_time))
        menu = wx.Menu()
        idx = -1
        listid = self.list_job_history.GetFirstSelected()
        if listid >= 0:
            idx = self.list_job_history.GetItemData(listid)
        if idx >= 0:
            menuitem = menu.Append(wx.ID_ANY, _("Delete this entry"), "")
            self.Bind(
                wx.EVT_MENU,
                on_menu_index(idx),
                id=menuitem.GetId(),
            )
            menu.AppendSeparator()

        menuitem = menu.Append(wx.ID_ANY, _("Delete..."))
        menu.Enable(menuitem.GetId(), False)

        for item in options:
            menuitem = menu.Append(wx.ID_ANY, item[0], "")
            self.Bind(
                wx.EVT_MENU,
                on_menu_time(item[1]),
                id=menuitem.GetId(),
            )

        menu.AppendSeparator()
        menuitem = menu.Append(
            wx.ID_ANY, _("Clear history on startup"), "", wx.ITEM_CHECK
        )
        menuitem.Check(self.context.spool_history_clear_on_start)
        self.Bind(
            wx.EVT_MENU,
            toggle_1,
            id=menuitem.GetId(),
        )
        menuitem = menu.Append(wx.ID_ANY, _("Ignore helper jobs"), "", wx.ITEM_CHECK)
        menuitem.Check(self.context.spool_ignore_helper_jobs)
        self.Bind(
            wx.EVT_MENU,
            toggle_2,
            id=menuitem.GetId(),
        )
        if menu.MenuItemCount != 0:
            self.PopupMenu(menu)
            menu.Destroy()

    def on_button_pause(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("pause\n")

    def on_button_stop(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("estop\n")

    def on_combo_device(self, event=None):  # wxGlade: Spooler.<event_handler>
        index = self.combo_device.GetSelection()
        if index == 0:
            self.filter_device = None
        else:
            self.filter_device = self.available_devices[index - 1].label
        self.update_spooler = True
        self.refresh_spooler_list()
        self.refresh_history()
        self.set_pause_color()

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        # Todo: Drag to reprioritise jobs
        event.Skip()

    def on_item_rightclick(self, event):  # wxGlade: JobSpooler.<event_handler>
        listindex = event.Index
        index = self.list_job_spool.GetItemData(listindex)
        try:
            spooler = self.queue_entries[index][0]
            qindex = self.queue_entries[index][1]
            element = spooler.queue[qindex]
        except IndexError:
            return

        menu = wx.Menu()
        if element.status.lower() == "running":
            action = _("Stop")
            remove_mode = "stop"
        else:
            action = _("Remove")
            remove_mode = "remove"
        item = menu.Append(
            wx.ID_ANY,
            f"{action} {str(element)[:30]} [{spooler.context.label}]",
            "",
            wx.ITEM_NORMAL,
        )
        info_tuple = [spooler, element, remove_mode]
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(info_tuple), item)

        item = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), item)

        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_clear(self, element=None):
        def clear(event=None):
            spoolers = []
            for device in self.available_devices:
                addit = True
                if (
                    self.filter_device is not None
                    and device.label != self.filter_device
                ):
                    addit = False
                if addit:
                    spoolers.append(device.spooler)
            for spooler in spoolers:
                spooler.clear_queue()
            self.refresh_spooler_list()

        return clear

    def on_tree_popup_delete(self, element):
        def delete(event=None):
            spooler = element[0]
            mode = element[2]
            job = element[1]
            spooler.remove(job)
            # That will remove the job but create a log entry if needed.
            if mode == "stop":
                # Force stop of laser.
                self.context("estop\n")
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
        self.queue_entries = []
        queue_idx = -1
        for device in self.available_devices:
            spooler = device.spooler
            if spooler is None:
                continue
            if self.filter_device is not None and self.filter_device != device.label:
                continue
            for idx, e in enumerate(spooler.queue):
                self.queue_entries.append([spooler, idx])
                queue_idx += 1
                # Idx, Status, Type, Passes, Priority, Runtime, Estimate
                m = self.list_job_spool.InsertItem(idx, f"#{idx}")
                list_id = m
                spool_obj = e

                if list_id != -1:
                    self.list_job_spool.SetItemData(list_id, queue_idx)
                    # DEVICE
                    self.list_job_spool.SetItem(
                        list_id, self.column_job["device"], device.label
                    )
                    # Jobname
                    to_display = ""
                    if hasattr(spool_obj, "label"):
                        to_display = spool_obj.label
                        if to_display is None:
                            to_display = ""
                    if to_display == "":
                        to_display = SpoolerPanel._name_str(spool_obj)
                    if to_display.endswith(" items"):
                        # Look for last ':' and remove everything from there
                        cpos = -1
                        lpos = -1
                        while True:
                            lpos = to_display.find(":", lpos + 1)
                            if lpos == -1:
                                break
                            cpos = lpos
                        if cpos > 0:
                            to_display = to_display[:cpos]

                    self.list_job_spool.SetItem(
                        list_id, self.column_job["jobname"], to_display
                    )
                    # Entries
                    joblen = 1
                    try:
                        if hasattr(spool_obj, "items"):
                            joblen = len(spool_obj.items)
                        elif hasattr(spool_obj, "elements"):
                            joblen = len(spool_obj.elements)
                    except AttributeError:
                        joblen = 1
                    self.list_job_spool.SetItem(
                        list_id, self.column_job["entries"], str(joblen)
                    )
                    # STATUS
                    # try:
                    status = spool_obj.status
                    # except AttributeError:
                    # status = _("Queued")
                    self.list_job_spool.SetItem(
                        list_id, self.column_job["status"], status
                    )

                    # TYPE
                    try:
                        self.list_job_spool.SetItem(
                            list_id,
                            self.column_job["type"],
                            str(spool_obj.__class__.__name__),
                        )
                    except AttributeError:
                        pass

                    # STEPS
                    try:
                        pass_str = f"{spool_obj.steps_done}/{spool_obj.steps_total}"
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["steps"], pass_str
                        )
                    except AttributeError:
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["steps"], "-"
                        )
                    # PASSES
                    try:
                        loop = spool_obj.loops_executed
                        total = spool_obj.loops

                        if isinf(total):
                            total = "∞"
                        pass_str = f"{loop}/{total}"
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["passes"], pass_str
                        )
                    except AttributeError:
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["passes"], "-"
                        )

                    # Priority
                    try:
                        self.list_job_spool.SetItem(
                            list_id,
                            self.column_job["priority"],
                            f"{spool_obj.priority}",
                        )
                    except AttributeError:
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["priority"], "-"
                        )

                    # Runtime
                    try:
                        t = spool_obj.elapsed_time()
                        hours, remainder = divmod(t, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["runtime"], runtime
                        )
                    except AttributeError:
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["runtime"], "-"
                        )

                    # Estimate Time
                    try:
                        t = spool_obj.estimate_time()
                        if isinf(t):
                            runtime = "∞"
                        else:
                            hours, remainder = divmod(t, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["estimate"], runtime
                        )
                    except AttributeError:
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["estimate"], "-"
                        )
        self._last_invokation = time.time()

    @staticmethod
    def timestr(t, oneday):
        if t is None:
            return ""
        if isinf(t) or isnan(t) or t < 0:
            return "∞"

        if oneday:
            localt = time.localtime(t)
            hours = localt[3]
            minutes = localt[4]
            seconds = localt[5]
        else:
            hours, remainder = divmod(t, 3600)
            minutes, seconds = divmod(remainder, 60)
        result = (
            f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
        )
        return result

    @staticmethod
    def datestr(t):
        if t is None:
            return ""
        localt = time.localtime(t)
        lyear = localt[0]
        lmonth = int(localt[1])
        lday = localt[2]
        lhour = localt[3]
        lminute = localt[4]
        lsecond = localt[5]
        # wx.DateTime has a bug: it does always provide the dateformat
        # string with a month representation one number too high, so
        # wx.DateTime(31,01,1999)
        # Arbitrary but with different figures
        # Alas this is the only simple method to get locale relevant dateformat...
        wxdt = wx.DateTime(31, 7, 2022)
        pattern = wxdt.FormatDate()
        pattern = pattern.replace("2022", "{yy}")
        pattern = pattern.replace("22", "{yy}")
        pattern = pattern.replace("31", "{dd}")
        # That would be the right thing, so if the bug is ever fixed, that will work
        pattern = pattern.replace("07", "{mm}")
        pattern = pattern.replace("7", "{mm}")
        # And this is needed to deal with the bug...
        pattern = pattern.replace("08", "{mm}")
        pattern = pattern.replace("8", "{mm}")
        result = pattern.format(
            dd=str(lday).zfill(2), mm=str(lmonth).zfill(2), yy=str(lyear).zfill(2)
        )
        # Just to show the bug...
        # result1 = f"{int(lday)}.{str(int(lmonth)).zfill(2)}.{str(int(lyear)).zfill(2)}"
        # wxdt = wx.DateTime(lday, lmonth, lyear, lhour, lminute, lsecond)
        # result2 = wxdt.FormatDate()
        # print(f"res={result}, wxd={result2}, manual={result1}, pattern={pattern}")
        return result

    def refresh_history(self):
        self.list_job_history.DeleteAllItems()
        self.map_item_key.clear()
        if self.filter_device:
            events = self.context.logging.matching_events(
                "job", device=self.context.device.label
            )
        else:
            events = self.context.logging.matching_events("job")
        for idx, event_and_key in enumerate(reversed(list(events))):
            key, info = event_and_key
            list_id = self.list_job_history.InsertItem(
                self.list_job_history.GetItemCount(), f"#{idx}"
            )
            self.map_item_key[list_id] = key
            self.list_job_history.SetItem(
                list_id, HC_JOBNAME, info.get("label")
            )
            self.list_job_history.SetItem(
                list_id,
                HC_START,
                f"{self.datestr(info.get('start_time'))} {self.timestr(info.get('start_time'), True)}",
            )
            self.list_job_history.SetItem(
                list_id,
                HC_END,
                self.timestr(info.get("start_time", 0) + info.get("duration", 0), True),
            )
            self.list_job_history.SetItem(
                list_id,
                HC_RUNTIME,
                self.timestr(info.get("duration"), False),
            )
            self.list_job_history.SetItem(
                list_id,
                HC_PASSES,
                str(info.get("loops_total")),
            )
            self.list_job_history.SetItem(
                list_id, HC_DEVICE, str(info.get("device"))
            )
            self.list_job_history.SetItem(
                list_id, HC_STATUS, info.get("status", "")
            )
            self.list_job_history.SetItem(
                list_id, HC_JOBINFO, info.get("info", "")
            )
            self.list_job_history.SetItem(
                list_id,
                HC_ESTIMATE,
                self.timestr(info.get("estimate", 0), False),
            )
            self.list_job_history.SetItem(
                list_id,
                HC_STEPS,
                f"{info.get('steps_done',0)}/{info.get('steps_total',0)}",
            )
            self.list_job_history.SetItemData(list_id, idx)

    def reload_history(self):
        self.refresh_history()

    def before_history_update(self, event):
        list_id = event.GetIndex()  # Get the current row
        col_id = event.GetColumn()  # Get the current column
        if col_id == HC_JOBINFO:
            event.Allow()
        else:
            event.Veto()

    def on_history_update(self, event):
        list_id = event.GetIndex()  # Get the current row
        col_id = event.GetColumn()  # Get the current column
        new_data = event.GetLabel()  # Get the changed data
        if list_id >= 0 and col_id == HC_JOBINFO:
            idx = self.list_job_history.GetItemData(list_id)
            key = self.map_item_key[idx]
            self.context.logging.logs[key]["info"] = new_data

            # Set the new data in the listctrl
            self.list_job_history.SetItem(list_id, col_id, new_data)

    def set_pause_color(self):
        new_color = None
        new_caption = _("Pause")
        try:
            if self.context.device.driver.paused:
                new_color = wx.YELLOW
                new_caption = _("Resume")
        except AttributeError:
            pass
        self.button_pause.SetBackgroundColour(new_color)
        self.button_pause.SetLabelText(new_caption)

    @signal_listener("pause")
    def on_device_pause_toggle(self, origin, *args):
        self.set_pause_color()

    @signal_listener("activate;device")
    def on_activate_device(self, origin, device):
        self.available_devices = self.context.kernel.services("device")
        self.selected_device = self.context.device
        spools = []
        index = -1
        for i, s in enumerate(self.available_devices):
            if s is self.selected_device:
                index = i + 1
                break
        spools = [s.label for s in self.available_devices]
        spools.insert(0, _("-- All available devices --"))
        # This might not be relevant if you have a stable device set, but there might always be
        # changes to add / rename devices etc.
        if self.combo_device.GetSelection() == 0:
            # all devices is a superset of any device, so we can leave it...
            index = 0
        self.combo_device.Clear()
        self.combo_device.SetItems(spools)
        self.combo_device.SetSelection(index)
        self.on_combo_device(None)
        self.set_pause_color()

    @signal_listener("spooler;completed")
    def on_spooler_completed(self, origin, *args):
        self.refresh_history()

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
        # Two things (at least) could go wrong:
        # 1) You are in the wrong queue, ie there's a job running in the background a
        #    that provides an update but the user has changed the device so a different
        #    queue is selected
        # 2) As this is a signal it may come later, ie the job has already finished
        #
        # The checks here are rather basic and need to be revisited
        refresh_needed = False
        try:
            listctrl = self.list_job_spool
        except RuntimeError:
            return
        self._last_invokation = dtime
        for list_id, entry in enumerate(self.queue_entries):
            spooler = entry[0]
            qindex = entry[1]
            if qindex >= len(spooler.queue):
                # This item is nowhere to be found
                refresh_needed = True
                continue
            spool_obj = spooler.queue[qindex]
            try:
                t = spool_obj.elapsed_time()
                hours, remainder = divmod(t, 3600)
                minutes, seconds = divmod(remainder, 60)
                runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(
                        list_id, self.column_job["runtime"], runtime
                    )
            except (AttributeError, AssertionError):
                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(
                        list_id, self.column_job["runtime"], "-"
                    )
                else:
                    refresh_needed = True

            try:
                pass_str = f"{spool_obj.steps_done}/{spool_obj.steps_total}"
                self.list_job_spool.SetItem(list_id, self.column_job["steps"], pass_str)
            except AttributeError:
                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(list_id, self.column_job["steps"], "-")
                else:
                    refresh_needed = True
            try:
                loop = spool_obj.loops_executed
                total = spool_obj.loops

                if isinf(total):
                    total = "∞"
                pass_str = f"{loop}/{total}"
                self.list_job_spool.SetItem(
                    list_id, self.column_job["passes"], pass_str
                )
            except AttributeError:
                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(list_id, self.column_job["passes"], "-")
                else:
                    refresh_needed = True

            # Estimate Time
            try:
                t = spool_obj.estimate_time()
                if isinf(t):
                    runtime = "∞"
                else:
                    hours, remainder = divmod(t, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"

                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(
                        list_id, self.column_job["estimate"], runtime
                    )
            except (AttributeError, AssertionError):
                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(
                        list_id, self.column_job["estimate"], "-"
                    )
                else:
                    refresh_needed = True
        if refresh_needed:
            self.refresh_spooler_list()
            self.refresh_history()


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
                "priority": -1,
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return ("Burning", "Spooler")
