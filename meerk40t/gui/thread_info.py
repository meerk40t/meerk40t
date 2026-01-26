import threading
import time

import wx
from wx import aui

from meerk40t.gui.icons import icons8_route
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    wxListCtrl,
    wxStaticText,
    dispatch_to_main_thread,
)
from meerk40t.kernel import Job, signal_listener

_ = wx.GetTranslation


def register_panel_thread_info(window, context):
    panel = ThreadPanel(window, wx.ID_ANY, context=context)
    pane = (
        aui.AuiPaneInfo()
        .Bottom()
        .Layer(1)
        .MinSize(600, 100)
        .FloatingSize(600, 230)
        .Caption(_("Tasks"))
        .Name("tasks")
        .CaptionVisible(not context.pane_lock)
        .Hide()
    )
    pane.dock_proportion = 600
    pane.control = panel
    pane.helptext = _("Opens the tasks window with all background task information")

    window.on_pane_create(pane)
    context.register("pane/tasks", pane)


class ThreadPanel(wx.Panel):
    """ThreadPanel - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for thread functionality. Features checkbox controls for user interaction. Integrates with thread_update, wxpane/ThreadInfo for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for thread functionality. Key controls include "Auto-show on new task" (checkbox)."""

    """ThreadPanel - User interface panel for laser cutting operations"""

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: SpoolerPanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("threadinfo")

        self.sizer_main = wx.BoxSizer(wx.VERTICAL)
        infomsg = _(
            "Background Tasks are preparatory jobs issued with the 'threaded' command,\nlike burn preparation and others."
        )
        self.info = wxStaticText(self, wx.ID_ANY, infomsg)

        self.list_job_threads = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
            context=self.context,
            list_name="list_threads",
        )
        self.list_job_threads.SetToolTip(_("List of background tasks"))
        self.list_job_threads.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=48)
        self.list_job_threads.AppendColumn(
            _("Task"), format=wx.LIST_FORMAT_LEFT, width=113
        )
        self.list_job_threads.AppendColumn(
            _("Status"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_threads.AppendColumn(
            _("Runtime"), format=wx.LIST_FORMAT_LEFT, width=73
        )
        self.list_job_threads.resize_columns()
        self.check_auto = wx.CheckBox(self, wx.ID_ANY, _("Auto-show on new task"))
        self.sizer_main.Add(self.info, 0, wx.EXPAND)
        self.sizer_main.Add(self.list_job_threads, 1, wx.EXPAND)
        self.sizer_main.Add(self.check_auto, 0, wx.EXPAND)
        self.check_auto.SetValue(
            self.context.setting(bool, "autoshow_task_window", True)
        )
        self.SetSizer(self.sizer_main)
        self.Layout()

        # We set a timer job that will periodically check the spooler queue
        # in case no signal was received
        self.show_system_tasks = False
        self._last_invokation = 0
        self.shown = False
        self.update_lock = threading.Lock()
        self.timerjob = Job(
            process=self.update_queue,
            job_name="spooler-update",
            interval=5,
            run_main=True,
        )
        self.list_job_threads.Bind(wx.EVT_RIGHT_DOWN, self.show_context_menu)
        self.check_auto.Bind(wx.EVT_CHECKBOX, self.on_check_auto)

    def on_show_system_tasks(self, event):
        self.show_system_tasks = not self.show_system_tasks
        self.refresh_thread_list()

    def on_check_auto(self, event):
        self.context.autoshow_task_window = self.check_auto.GetValue()

    def show_context_menu(self, event):
        menu = wx.Menu()
        item = menu.AppendCheckItem(wx.ID_ANY, _("Show System Tasks"))
        item.Check(self.show_system_tasks)
        menu.Bind(wx.EVT_MENU, self.on_show_system_tasks, id=item.GetId())
        self.PopupMenu(menu)
        menu.Destroy()

    def refresh_thread_list(self):
        try:
            self.list_job_threads.DeleteAllItems()
        except RuntimeError:
            return
        idx = 0
        with self.context.kernel.thread_lock:
            thread_items = list(self.context.kernel.threads.items())
        for thread_name, thread_info in thread_items:
            thread, message, user_type, info, started = thread_info
            # Skip system tasks when not showing them
            if not (user_type or self.show_system_tasks):
                continue
            if not info:
                info = thread_name
            idx += 1
            elapsed = time.time() - started
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime = f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
            m = self.list_job_threads.InsertItem(idx, f"#{idx}")
            self.list_job_threads.SetItem(m, 1, info)
            self.list_job_threads.SetItem(m, 2, message)
            self.list_job_threads.SetItem(m, 3, runtime)
            # print (idx, info, message, runtime)
        self.list_job_threads.resize_columns()
        self.list_job_threads.Refresh()

    @signal_listener("thread_update")
    @dispatch_to_main_thread
    def on_thread_signal(self, origin, *args):
        doit = True
        with self.update_lock:
            # Only update every 2 seconds or so
            dtime = time.time()
            if dtime - self._last_invokation < 2:
                doit = False
            else:
                self._last_invokation = dtime
        if not doit:
            return
        self.refresh_thread_list()

    def pane_show(self):
        self.shown = True
        self.list_job_threads.load_column_widths()
        self.context.schedule(self.timerjob)
        self.refresh_thread_list()

    def pane_hide(self):
        self.context.unschedule(self.timerjob)
        self.shown = False

        self.list_job_threads.save_column_widths()

    def update_queue(self):
        if self.shown:
            self.refresh_thread_list()


class ThreadInfo(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(600, 400, *args, **kwds)
        self.panel = ThreadPanel(
            self,
            wx.ID_ANY,
            context=self.context,
        )
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_route.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Background Tasks"))
        self.Layout()
        self.restore_aspect(honor_initial_values=True)

    @staticmethod
    def sub_register(kernel):
        kernel.register("wxpane/ThreadInfo", register_panel_thread_info)

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        # Hint for translation:  _("Tasks")
        return "", "Tasks"

    @staticmethod
    def helptext():
        return _("Opens the window with all background task information")
