import json
import os
import time
from math import isinf

import wx
from wx import aui

from meerk40t.gui.icons import (
    icons8_emergency_stop_button_50,
    icons8_pause_50,
    icons8_route_50,
)
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

    window.on_pane_create(pane)
    context.register("pane/spooler", pane)


class SpoolerPanel(wx.Panel):
    def __init__(self, *args, context=None, selected_device=None, **kwds):
        # begin wxGlade: SpoolerPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.available_devices = context.kernel.services("device")
        self.filter_device = None
        spools = [s.label for s in self.available_devices]
        spools.insert(0, _("-- All available devices --"))
        self.queue_entries = []

        self.splitter = wx.SplitterWindow(self, id=wx.ID_ANY, style = wx.SP_LIVE_UPDATE)
        sty = wx.BORDER_SUNKEN

        self.win_top = wx.Window(self.splitter, style=sty)
        self.win_bottom = wx.Window(self.splitter, style=sty)
        self.splitter.SetMinimumPaneSize(50)
        self.splitter.SplitHorizontally(self.win_top, self.win_bottom, -100)
        self.context.setting(int, "spooler_sash_position", 0)
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

        self.info_label = wx.StaticText(self.win_bottom, wx.ID_ANY, _("Completed jobs:"))
        self.btn_clear = wx.Button(self.win_bottom, wx.ID_ANY, _("Clear History"))
        self.list_job_history = wx.ListCtrl(
            self.win_bottom,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )

        self.__set_properties()
        self.__do_layout()
        self.current_item = None
        self.Bind(wx.EVT_BUTTON, self.on_btn_clear, self.btn_clear)
        self.Bind(wx.EVT_BUTTON, self.on_button_pause, self.button_pause)
        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.list_job_spool)

        self.splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.on_sash_changed)
        self.splitter.Bind(wx.EVT_SPLITTER_DOUBLECLICKED, self.on_sash_double)

        self.list_job_spool.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.list_job_spool.Bind(wx.EVT_LEFT_DCLICK, self.on_item_doubleclick)
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
            "passes": 6,
            "priority": 7,
            "runtime": 8,
            "estimate": 9,
        }

        self.column_history = {
            "idx": 0,
            "device": 1,
            "jobname": 2,
            "start": 3,
            "end": 4,
            "runtime": 5,
            "passes": 6,
        }

        self.reload_history()

        # if index == -1:
        #     disable_window(self)

    def __set_properties(self):
        # begin wxGlade: SpoolerPanel.__set_properties
        self.combo_device.SetToolTip(_("Select the device"))
        self.list_job_spool.SetToolTip(_("List and modify the queued operations"))
        self.list_job_spool.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=58)
        self.list_job_spool.AppendColumn(
            _("Device"), format=wx.LIST_FORMAT_LEFT, width=95,
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
            _("Device"), format=wx.LIST_FORMAT_LEFT, width=95
        )
        self.list_job_history.AppendColumn(
            _("Name"), format=wx.LIST_FORMAT_LEFT, width=95
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
            _("Passes"), format=wx.LIST_FORMAT_LEFT, width=73
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

    def on_btn_clear(self, event):
        if self.filter_device is None:
            self.history = []
        else:
            idx = 0
            while idx<len(self.history):
                if self.history[idx][3] == self.filter_device:
                    self.history.pop(idx)
                else:
                    idx += 1
        self.save_history()
        self.refresh_history()

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

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        # Todo: Drag to reprioritise jobs
        event.Skip()

    def on_item_doubleclick(self, event):
        def item_info(item):
            result = ""
            count = 0
            if isinstance(item, tuple):
                attr = item[0]
                result = f"function(tuple): {attr}"
                count += 1
            elif isinstance(item, str):
                attr = item
                result = f"function(str): {attr}"
                count += 1
            if hasattr(item, "generate"):
                item = getattr(item, "generate")
                result = "Generator:"
                # Generator item
                for p in item():
                    dummy, subct = item_info(p)
                    count += subct
                    result += "\n" + dummy
                    count += 1

            return result, count

        index = self.current_item
        spooler = self.selected_device.spooler
        try:
            element = spooler.queue[index]
        except IndexError:
            return
        msgstr = f"{element.label}: \n"
        for idx, item in enumerate(element.items):
            info, ct = item_info(item)
            msgstr += f"{idx:2d}: {info}\n Steps: {ct}"
        print(msgstr)

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
        else:
            action = _("Remove")
        item = menu.Append(
            wx.ID_ANY,
            "{action} {name} [{label}]".format(
                action=action,
                name=str(element)[:30],
                label=spooler.context.label
            ),
            "",
            wx.ITEM_NORMAL,
        )
        info_tuple = [spooler, element]
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
                if self.filter_device is not None and device.label != self.filter_device:
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
            spooler.remove(element[1])
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
                    self.list_job_spool.SetItem(list_id, self.column_job["device"], device.label)
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

                    self.list_job_spool.SetItem(list_id, self.column_job["jobname"], to_display)
                    # Entries
                    joblen = 1
                    try:
                        if hasattr(spool_obj, "items"):
                            joblen = len(spool_obj.items)
                        elif hasattr(spool_obj, "elements"):
                            joblen = len(spool_obj.elements)
                    except AttributeError:
                        joblen = 1
                    self.list_job_spool.SetItem(list_id, self.column_job["entries"], str(joblen))
                    # STATUS
                    # try:
                    status = spool_obj.status
                    # except AttributeError:
                    # status = _("Queued")
                    self.list_job_spool.SetItem(list_id, self.column_job["status"], status)

                    # TYPE
                    try:
                        self.list_job_spool.SetItem(
                            list_id, self.column_job["type"], str(spool_obj.__class__.__name__)
                        )
                    except AttributeError:
                        pass

                    # PASSES
                    try:
                        loop = spool_obj.loops_executed
                        total = spool_obj.loops

                        if isinf(total):
                            total = "∞"
                        pass_str = f"{loop}/{total}"
                        pass_str += f" ({spool_obj.steps_done}/{spool_obj.steps_total})"
                        self.list_job_spool.SetItem(list_id, self.column_job["passes"], pass_str)
                    except AttributeError:
                        self.list_job_spool.SetItem(list_id, self.column_job["passes"], "-")

                    # Priority
                    try:
                        self.list_job_spool.SetItem(list_id, self.column_job["priority"], f"{spool_obj.priority}")
                    except AttributeError:
                        self.list_job_spool.SetItem(list_id, self.column_job["priority"], "-")

                    # Runtime
                    try:
                        t = spool_obj.elapsed_time()
                        hours, remainder = divmod(t, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                        self.list_job_spool.SetItem(list_id, self.column_job["runtime"], runtime)
                    except AttributeError:
                        self.list_job_spool.SetItem(list_id, self.column_job["runtime"], "-")

                    # Estimate Time
                    try:
                        t = spool_obj.estimate_time()
                        if isinf(t):
                            runtime = "∞"
                        else:
                            hours, remainder = divmod(t, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
                        self.list_job_spool.SetItem(list_id, self.column_job["estimate"], runtime)
                    except AttributeError:
                        self.list_job_spool.SetItem(list_id, self.column_job["estimate"], "-")
        self._last_invokation = time.time()

    def refresh_history(self, newestinfo=None):
        def timestr(t, oneday):
            if oneday:
                localt = time.localtime(t)
                hours = localt[3]
                minutes = localt[4]
                seconds = localt[5]
            else:
                hours, remainder = divmod(t, 3600)
                minutes, seconds = divmod(remainder, 60)
            result = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
            return result

        if newestinfo is not None:
            self.history.insert(0, newestinfo)
        self.list_job_history.DeleteAllItems()
        idx = 0
        for info in self.history:
            addit = True
            if self.filter_device is not None:
                if info[3] != self.filter_device:
                    addit = False
            if not addit:
                continue
            idx += 1
            list_id = self.list_job_history.InsertItem(
                self.list_job_history.GetItemCount(), f"#{idx}"
            )
            if info[1] is None:
                continue
            self.list_job_history.SetItem(list_id, self.column_history["jobname"], info[0])
            starttime = timestr(info[1], True)
            self.list_job_history.SetItem(list_id, self.column_history["start"], starttime)
            starttime = timestr(info[1] + info[2], True)
            self.list_job_history.SetItem(list_id, self.column_history["end"], starttime)
            runtime = timestr(info[2], False)
            self.list_job_history.SetItem(list_id, self.column_history["runtime"], runtime)
            # First passes then device
            if len(info) >= 5:
                self.list_job_history.SetItem(list_id, self.column_history["passes"], info[4])
            else:
                self.list_job_history.SetItem(list_id, self.column_history["passes"], "???")
            self.list_job_history.SetItem(list_id, self.column_history["device"], info[3])

    def reload_history(self):
        self.history = []
        directory = os.path.dirname(self.context.elements.op_data._config_file)
        filename = os.path.join(directory, "history.json")
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    self.history = json.load(f)
            except (json.JSONDecodeError, PermissionError, OSError, FileNotFoundError):
                pass
        if len(self.history) > 0:
            if len(self.history[0]) < 5:
                # Incompatible
                self.history = []
        self.refresh_history()

    def save_history(self):
        directory = os.path.dirname(self.context.elements.op_data._config_file)
        filename = os.path.join(directory, "history.json")
        try:
            with open(filename, "w") as f:
                json.dump(self.history, f)
        except (json.JSONDecodeError, PermissionError, OSError, FileNotFoundError):
            pass

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

    @signal_listener("spooler;completed")
    def on_spooler_completed(self, origin, info, *args):
        # Info is just a tuple with the label and the runtime
        # print ("Signalled...", type(origin).__name__, type(info).__name__)
        if info is None:
            return
        self.refresh_history(newestinfo=info)
        self.save_history()

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
                    self.list_job_spool.SetItem(list_id, self.column_job["runtime"], runtime)
            except (AttributeError, AssertionError):
                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(list_id, self.column_job["runtime"], "-")
                else:
                    refresh_needed = True

            try:
                loop = spool_obj.loops_executed
                total = spool_obj.loops

                if isinf(total):
                    total = "∞"
                pass_str = f"{loop}/{total}"
                pass_str += f" ({spool_obj.steps_done}/{spool_obj.steps_total})"

                self.list_job_spool.SetItem(list_id, self.column_job["passes"], pass_str)
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
                    self.list_job_spool.SetItem(list_id, self.column_job["estimate"], runtime)
            except (AttributeError, AssertionError):
                if list_id < self.list_job_spool.GetItemCount():
                    self.list_job_spool.SetItem(list_id, self.column_job["estimate"], "-")
                else:
                    refresh_needed = True
        if refresh_needed:
            self.refresh_spooler_list()
            self.reload_history()

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
