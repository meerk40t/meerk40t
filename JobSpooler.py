import wx

from LaserProject import PathElement, ImageElement, RawElement, VARIABLE_NAME_SPEED, VARIABLE_NAME_RASTER_STEP, \
    VARIABLE_NAME_POWER
from ThreadConstants import *


class JobSpooler(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobSpooler.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((668, 448))
        self.list_job_spool = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.panel_controller = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.gauge_controller = wx.Gauge(self.panel_controller, wx.ID_ANY, 100)
        self.checkbox_limit_buffer = wx.CheckBox(self.panel_controller, wx.ID_ANY, "Limit Write Buffer")
        self.text_packet_buffer = wx.TextCtrl(self.panel_controller, wx.ID_ANY, "")
        self.spin_packet_buffer_max = wx.SpinCtrl(self.panel_controller, wx.ID_ANY, "1500", min=1, max=100000)
        self.button_writer_control = wx.Button(self, wx.ID_ANY, "Start Job")
        self.button_controller = wx.BitmapButton(self, wx.ID_ANY,
                                                 wx.Bitmap("icons/icons8-connected-50.png", wx.BITMAP_TYPE_ANY))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_limit_packet_buffer, self.checkbox_limit_buffer)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_BUTTON, self.on_button_start_job, self.button_writer_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_controller, self.button_controller)
        # end wxGlade
        self.project = None
        self.dirty = False
        self.update_buffer_size = False
        self.update_writer_state = False
        self.update_spooler = False

        self.buffer_size = 0
        self.elements_progress = 0
        self.elements_progress_total = 0
        self.command_index = 0
        self.listener_list = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def set_project(self, project):
        self.project = project
        project["spooler", self.on_spooler_update] = self
        project["buffer", self.on_buffer_update] = self
        project["writer", self.on_writer_state] = self
        self.set_writer_button_by_state()
        self.checkbox_limit_buffer.SetValue(self.project.writer.thread.limit_buffer)
        self.spin_packet_buffer_max.SetValue(self.project.writer.thread.buffer_max)
        self.refresh_spooler_list()

    def on_close(self, event):
        self.project["spooler", self.on_spooler_update] = None
        self.project["buffer", self.on_buffer_update] = None
        self.project["writer", self.on_writer_state] = None
        try:
            del self.project.windows["jobspooler"]
        except KeyError:
            pass
        self.project = None
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobSpooler.__set_properties
        self.SetTitle("Spooler")
        self.list_job_spool.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=29)
        self.list_job_spool.AppendColumn("Name", format=wx.LIST_FORMAT_LEFT, width=90)
        self.list_job_spool.AppendColumn("Status", format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn("Device", format=wx.LIST_FORMAT_LEFT, width=53)
        self.list_job_spool.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=50)
        self.list_job_spool.AppendColumn("Speed", format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_job_spool.AppendColumn("Settings", format=wx.LIST_FORMAT_LEFT, width=72)
        self.list_job_spool.AppendColumn("Submitted", format=wx.LIST_FORMAT_LEFT, width=70)
        self.list_job_spool.AppendColumn("Time Estimate", format=wx.LIST_FORMAT_LEFT, width=92)
        self.checkbox_limit_buffer.SetValue(1)
        self.panel_controller.SetBackgroundColour(wx.Colour(204, 204, 204))
        self.button_writer_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_writer_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_writer_control.SetBitmap(wx.Bitmap("icons/icons8-play-50.png", wx.BITMAP_TYPE_ANY))
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
        sizer_3.Add(self.button_writer_control, 1, 0, 0)
        sizer_3.Add(self.button_controller, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def refresh_spooler_list(self):
        self.list_job_spool.DeleteAllItems()
        if len(self.project.writer.queue) > 0:
            pass
            # This should actually process and update the queue items.
            for i, e in enumerate(self.project.writer.queue):
                m = self.list_job_spool.InsertItem(i, "#%d" % i)
                if m != -1:
                    self.list_job_spool.SetItem(m, 1, str(e))
                    settings = ""
                    if m == 0:
                        self.list_job_spool.SetItem(m, 2, "Executing")
                    else:
                        self.list_job_spool.SetItem(m, 2, "Queued")
                    self.list_job_spool.SetItem(m, 3, self.project.writer.board)
                    if isinstance(e, PathElement):
                        self.list_job_spool.SetItem(m, 4, "Path")
                        if VARIABLE_NAME_POWER in e.cut:
                            settings += " power=%.0f" % (e.cut[VARIABLE_NAME_POWER])
                    elif isinstance(e, ImageElement):
                        self.list_job_spool.SetItem(m, 4, "Raster")
                        if VARIABLE_NAME_RASTER_STEP in e.cut:
                            settings += " step=%d" % (e.cut[VARIABLE_NAME_RASTER_STEP])
                    elif isinstance(e, RawElement):
                        self.list_job_spool.SetItem(m, 4, "Raw")
                    if VARIABLE_NAME_SPEED in e.cut:
                        self.list_job_spool.SetItem(m, 5, "%.1fmm/s" % (e.cut[VARIABLE_NAME_SPEED]))
                    self.list_job_spool.SetItem(m, 6, settings)
                    self.list_job_spool.SetItem(m, 7, "n/a")
                    self.list_job_spool.SetItem(m, 8, "unknown")

    def on_check_limit_packet_buffer(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.thread.limit_buffer = not self.project.writer.thread.limit_buffer

    def on_spin_packet_buffer_max(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.thread.buffer_max = self.spin_packet_buffer_max.GetValue()

    def on_check_auto_start_controller(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.thread.autostart = not self.project.controller.autostart

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.thread.autohome = not self.project.writer.thread.autohome

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.thread.autobeep = not self.project.writer.thread.autobeep

    def on_button_controller(self, event):  # wxGlade: JobSpooler.<event_handler>
        self.project.close_old_window("controller")
        from Controller import Controller
        window = Controller(None, wx.ID_ANY, "")
        window.set_project(self.project)
        window.Show()
        self.project.windows["controller"] = window

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        state = self.project.writer.thread.state
        if state == THREAD_STATE_STARTED:
            self.project.writer.thread.pause()
            self.set_writer_button_by_state()
        elif state == THREAD_STATE_PAUSED:
            self.project.writer.thread.resume()
            self.set_writer_button_by_state()
        elif state == THREAD_STATE_UNSTARTED:
            self.project.writer.thread.state = THREAD_STATE_STARTED
            self.project.writer.thread.start()
            self.set_writer_button_by_state()
        elif state == THREAD_STATE_ABORT:
            self.Close()
        elif state == THREAD_STATE_FINISHED:
            self.Close()

    def set_writer_button_by_state(self):
        state = self.project.writer.thread.state
        if state == THREAD_STATE_FINISHED:
            self.button_writer_control.SetBackgroundColour("#0000ff")
            self.button_writer_control.SetLabel("Close Job")
            # self.button_writer_control.SetValue(False)
        elif state == THREAD_STATE_PAUSED:
            self.button_writer_control.SetBackgroundColour("#00ff00")
            self.button_writer_control.SetLabel("Resume Job")
            # self.button_writer_control.SetValue(False)
        elif state == THREAD_STATE_UNSTARTED:
            self.button_writer_control.SetBackgroundColour("#00ff00")
            self.button_writer_control.SetLabel("Start Job")
            # self.button_writer_control.SetValue(True)
        elif state == THREAD_STATE_STARTED:
            self.button_writer_control.SetBackgroundColour("#ffff00")
            self.button_writer_control.SetLabel("Pause Job")
            # self.button_writer_control.SetValue(True)
        elif state == THREAD_STATE_ABORT:
            self.button_writer_control.SetBackgroundColour("#ff0000")
            self.button_writer_control.SetLabel("Close Aborted Job")
            # self.button_writer_control.SetValue(False)

    def post_update(self):
        if not self.dirty:
            self.dirty = True
            wx.CallAfter(self.post_update_on_gui_thread)

    def post_update_on_gui_thread(self):
        if self.project is None:
            return  # left over update on closed window

        if self.update_buffer_size:
            self.update_buffer_size = False
            self.text_packet_buffer.SetValue(str(self.buffer_size))
            self.gauge_controller.SetValue(self.buffer_size)
            self.gauge_controller.SetRange(self.spin_packet_buffer_max.GetValue())

        if self.update_writer_state:
            self.update_writer_state = False
            self.set_writer_button_by_state()

        if self.update_spooler:
            self.update_spooler = False
            self.refresh_spooler_list()

        self.dirty = False

    def on_spooler_update(self, value):
        self.update_spooler = True
        self.post_update()

    def on_buffer_update(self, value):
        self.update_buffer_size = True
        self.buffer_size = value
        self.post_update()

    def on_writer_state(self, state):
        self.update_writer_state = True
        self.post_update()
