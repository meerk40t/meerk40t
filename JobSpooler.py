import wx

from Kernel import *
from icons import icons8_connected_50, icons8_play_50

_ = wx.GetTranslation


class JobSpooler(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobSpooler.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((668, 448))
        self.list_job_spool = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.panel_controller = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.gauge_controller = wx.Gauge(self.panel_controller, wx.ID_ANY, 100)
        self.checkbox_limit_buffer = wx.CheckBox(self.panel_controller, wx.ID_ANY, _("Limit Write Buffer"))
        self.text_packet_buffer = wx.TextCtrl(self.panel_controller, wx.ID_ANY, "")
        self.spin_packet_buffer_max = wx.SpinCtrl(self.panel_controller, wx.ID_ANY, "1500", min=1, max=100000)
        self.button_spooler_control = wx.Button(self, wx.ID_ANY, _("Start Job"))
        self.button_controller = wx.BitmapButton(self, wx.ID_ANY, icons8_connected_50.GetBitmap())

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_list_drag, self.list_job_spool)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_item_rightclick, self.list_job_spool)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_limit_packet_buffer, self.checkbox_limit_buffer)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_TEXT, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_BUTTON, self.on_button_start_job, self.button_spooler_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_controller, self.button_controller)
        # end wxGlade
        self.kernel = None
        self.dirty = False
        self.update_buffer_size = False
        self.update_spooler_state = False
        self.update_spooler = False

        self.device = None
        self.elements_progress = 0
        self.elements_progress_total = 0
        self.command_index = 0
        self.listener_list = None
        self.list_lookup = {}
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def set_kernel(self, project):
        self.kernel = project
        self.device = project.device
        if self.device is None:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("You do not have a selected device."),
                                   _("No Device Selected."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        self.device.setting(int, "buffer_max", 600)
        self.device.setting(bool, "buffer_limit", True)
        self.device.listen("spooler;queue", self.on_spooler_update)
        self.device.listen("pipe;buffer", self.on_buffer_update)
        self.device.listen("interpreter;state", self.on_spooler_state)

        self.set_spooler_button_by_state()
        self.checkbox_limit_buffer.SetValue(self.kernel.buffer_limit)
        self.spin_packet_buffer_max.SetValue(self.kernel.buffer_max)
        self.refresh_spooler_list()

    def on_close(self, event):
        if self.device is not None:
            self.device.unlisten("spooler;queue", self.on_spooler_update)
            self.device.unlisten("pipe;buffer", self.on_buffer_update)
            self.device.unlisten("interpreter;state", self.on_spooler_state)
        self.kernel.mark_window_closed("JobSpooler")
        self.kernel = None
        self.device = None
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobSpooler.__set_properties
        self.SetTitle("Spooler")
        self.list_job_spool.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=29)
        self.list_job_spool.AppendColumn(_("Name"), format=wx.LIST_FORMAT_LEFT, width=90)
        self.list_job_spool.AppendColumn(_("Status"), format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn(_("Device"), format=wx.LIST_FORMAT_LEFT, width=53)
        self.list_job_spool.AppendColumn(_("Type"), format=wx.LIST_FORMAT_LEFT, width=50)
        self.list_job_spool.AppendColumn(_("Speed"), format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn(_("Settings"), format=wx.LIST_FORMAT_LEFT, width=82)
        self.list_job_spool.AppendColumn(_("Submitted"), format=wx.LIST_FORMAT_LEFT, width=70)
        self.list_job_spool.AppendColumn(_("Time Estimate"), format=wx.LIST_FORMAT_LEFT, width=92)
        self.checkbox_limit_buffer.SetValue(1)
        self.panel_controller.SetBackgroundColour(wx.Colour(204, 204, 204))
        self.button_spooler_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_spooler_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_spooler_control.SetBitmap(icons8_play_50.GetBitmap())
        self.button_controller.SetSize(self.button_controller.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobSpooler.__do_layout
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.VERTICAL)
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.list_job_spool, 8, wx.EXPAND, 0)
        sizer_11.Add(self.gauge_controller, 0, wx.EXPAND, 0)
        sizer_12.Add(self.checkbox_limit_buffer, 1, 0, 0)
        sizer_12.Add(self.text_packet_buffer, 5, 0, 0)
        label_4 = wx.StaticText(self.panel_controller, wx.ID_ANY, "/")
        sizer_12.Add(label_4, 0, 0, 0)
        sizer_12.Add(self.spin_packet_buffer_max, 0, 0, 0)
        sizer_11.Add(sizer_12, 1, wx.EXPAND, 0)
        self.panel_controller.SetSizer(sizer_11)
        sizer_2.Add(self.panel_controller, 0, wx.EXPAND, 0)
        sizer_3.Add(self.button_spooler_control, 1, 0, 0)
        sizer_3.Add(self.button_controller, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def refresh_spooler_list(self):
        self.list_job_spool.DeleteAllItems()
        if len(self.device.spooler.queue) > 0:
            # This should actually process and update the queue items.
            i = 0
            for e in self.device.spooler.queue:
                m = self.list_job_spool.InsertItem(i, "#%d" % i)
                if m != -1:
                    try:
                        t = e.type
                    except AttributeError:
                        t = "function"
                    self.list_job_spool.SetItem(m, 1, str(e))
                    if m == 0:
                        self.list_job_spool.SetItem(m, 2, _("Executing"))
                    else:
                        self.list_job_spool.SetItem(m, 2, _("Queued"))
                    self.list_job_spool.SetItem(m, 3, self.kernel.board)
                    settings = []
                    if t == 'path':
                        self.list_job_spool.SetItem(m, 4, _("Path"))
                        settings.append(_("power=%.0f" % (e.power)))
                    elif t == 'image':
                        self.list_job_spool.SetItem(m, 4, _("Raster"))
                        settings.append(_("step=%d" % (e.raster_step)))
                        if e['overscan'] is not None:
                            try:
                                settings.append(_("overscan=%d" % int(e['overscan'])))
                            except ValueError:
                                pass
                    if t in ('image', 'path', 'text'):
                        self.list_job_spool.SetItem(m, 5, _("%.1fmm/s" % (e.speed)))
                    settings = " ".join(settings)
                    self.list_job_spool.SetItem(m, 6, settings)
                    self.list_job_spool.SetItem(m, 7, _("n/a"))
                    self.list_job_spool.SetItem(m, 8, _("unknown")) # time estimate
                i += 1

    def on_list_drag(self, event):  # wxGlade: JobSpooler.<event_handler>
        event.Skip()

    def on_item_rightclick(self, event):  # wxGlade: JobSpooler.<event_handler>
        index = event.Index
        if index == 0:
            event.Skip()
            return  # We can't delete the running element.
        try:
            element = self.kernel.spooler.queue[index]
        except IndexError:
            return
        menu = wx.Menu()
        convert = menu.Append(wx.ID_ANY, _("Remove %s" % str(element)[:16]), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_delete(element), convert)
        convert = menu.Append(wx.ID_ANY, _("Clear All"), "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_tree_popup_clear(element), convert)
        self.PopupMenu(menu)
        menu.Destroy()

    def on_tree_popup_clear(self, element):
        def delete(event):
            self.kernel.spooler.queue = []
            self.refresh_spooler_list()

        return delete

    def on_tree_popup_delete(self, element):
        def delete(event):
            self.kernel.spooler.queue.remove(element)
            self.refresh_spooler_list()

        return delete

    def on_check_limit_packet_buffer(self, event):  # wxGlade: JobInfo.<event_handler>
        self.kernel.buffer_limit = not self.kernel.buffer_limit

    def on_spin_packet_buffer_max(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.kernel is not None:
            self.kernel.buffer_max = self.spin_packet_buffer_max.GetValue()

    def on_check_auto_start_controller(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.kernel is not None:
            self.kernel.autostart = not self.kernel.autostart

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.kernel is not None:
            self.kernel.autohome = not self.kernel.autohome

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.kernel is not None:
            self.kernel.autobeep = not self.kernel.autobeep

    def on_button_controller(self, event):  # wxGlade: JobSpooler.<event_handler>
        self.kernel.open_window("Controller")

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        spooler = self.device.spooler
        state = spooler.thread.state
        if state == THREAD_STATE_STARTED:
            spooler.thread.pause()
            self.set_spooler_button_by_state()
        elif state == THREAD_STATE_PAUSED:
            spooler.thread.resume()
            self.set_spooler_button_by_state()
        elif state == THREAD_STATE_UNSTARTED or state == THREAD_STATE_FINISHED:
            spooler.start_queue_consumer()
            self.set_spooler_button_by_state()
        elif state == THREAD_STATE_ABORT:
            spooler.reset_thread()

    def set_spooler_button_by_state(self):
        state = self.device.spooler.thread.state
        if state == THREAD_STATE_FINISHED or state == THREAD_STATE_UNSTARTED:
            self.button_spooler_control.SetBackgroundColour("#009900")
            self.button_spooler_control.SetLabel(_("Start Job"))
        elif state == THREAD_STATE_PAUSED:
            self.button_spooler_control.SetBackgroundColour("#00dd00")
            self.button_spooler_control.SetLabel(_("Resume Job"))
        elif state == THREAD_STATE_STARTED:
            self.button_spooler_control.SetBackgroundColour("#00ff00")
            self.button_spooler_control.SetLabel(_("Pause Job"))
        elif state == THREAD_STATE_ABORT:
            self.button_spooler_control.SetBackgroundColour("#00ffff")
            self.button_spooler_control.SetLabel(_("Manual Reset"))

    def post_update(self):
        if not self.dirty:
            self.dirty = True
            wx.CallAfter(self.post_update_on_gui_thread)

    def post_update_on_gui_thread(self):
        if self.kernel is None:
            return  # left over update on closed window

        if self.update_buffer_size:
            self.update_buffer_size = False
            buffer_size = len(self.device.pipe)
            self.text_packet_buffer.SetValue(str(buffer_size))
            self.gauge_controller.SetRange(self.spin_packet_buffer_max.GetValue())
            max = self.gauge_controller.GetRange()
            value = min(buffer_size, max)
            self.gauge_controller.SetValue(value)

        if self.update_spooler_state:
            self.update_spooler_state = False
            self.set_spooler_button_by_state()

        if self.update_spooler:
            self.update_spooler = False
            self.refresh_spooler_list()

        self.dirty = False

    def on_spooler_update(self, value):
        self.update_spooler = True
        self.post_update()

    def on_buffer_update(self, value):
        self.update_buffer_size = True
        self.post_update()

    def on_spooler_state(self, state):
        self.update_spooler_state = True
        self.post_update()
