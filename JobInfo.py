import wx

from ThreadConstants import *


class JobInfo(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobInfo.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((595, 638))
        self.panel_writer = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.gauge_writer = wx.Gauge(self.panel_writer, wx.ID_ANY, 100)
        self.text_job_progress = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.text_job_total = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.text_command_index = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.elements_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.panel_controller = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.checkbox_limit_buffer = wx.CheckBox(self.panel_controller, wx.ID_ANY, "Limit Write Buffer")
        self.gauge_controller = wx.Gauge(self.panel_controller, wx.ID_ANY, 100)
        self.text_packet_buffer = wx.TextCtrl(self.panel_controller, wx.ID_ANY, "")
        self.spin_packet_buffer_max = wx.SpinCtrl(self.panel_controller, wx.ID_ANY, "1500", min=1, max=100000)
        self.checkbox_autostart = wx.CheckBox(self, wx.ID_ANY, "Automatically Start Controller")
        self.checkbox_autohome = wx.CheckBox(self, wx.ID_ANY, "Home After")
        self.checkbox_autobeep = wx.CheckBox(self, wx.ID_ANY, "Beep After")
        self.button_writer_control = wx.ToggleButton(self, wx.ID_ANY, "Start Job")
        self.button_delete_job = wx.BitmapButton(self, wx.ID_ANY,
                                                 wx.Bitmap("icons/icons8-trash-50.png", wx.BITMAP_TYPE_ANY))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LISTBOX, self.on_listbox_click, self.elements_listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_dclick, self.elements_listbox)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_limit_packet_buffer, self.checkbox_limit_buffer)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_auto_start_controller, self.checkbox_autostart)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_after, self.checkbox_autohome)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_beep_after, self.checkbox_autobeep)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_start_job, self.button_writer_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_delete_job, self.button_delete_job)
        # end wxGlade

        self.project = None
        self.dirty = False
        self.dirty_usb = False
        self.buffer_size = 0
        self.usb_status = ""
        self.progress_total = 0
        self.progress_update = 0
        self.command_progress = 0
        self.listener_list = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def set_project(self, project):
        self.project = project
        project["buffer", self.on_buffer_update] = self
        project["progress", self.on_progress] = self
        project["command", self.on_command_progress] = self
        self.set_writer_button_by_state()
        self.checkbox_autobeep.SetValue(self.project.writer.thread.autobeep)
        self.checkbox_autohome.SetValue(self.project.writer.thread.autohome)
        self.checkbox_autostart.SetValue(self.project.controller.autostart)
        self.checkbox_limit_buffer.SetValue(self.project.writer.thread.limit_buffer)
        self.spin_packet_buffer_max.SetValue(self.project.writer.thread.buffer_max)
        if len(self.project.writer.thread.element_list) > 0:
            self.elements_listbox.InsertItems([str(e) for e in self.project.writer.thread.element_list], 0)

    def on_close(self, event):
        self.project["buffer", self.on_buffer_update] = None
        self.project["progress", self.on_progress] = None
        self.project["command", self.on_command_progress] = None
        self.project = None
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobInfo.__set_properties
        self.SetTitle("Job")
        self.panel_writer.SetBackgroundColour(wx.Colour(238, 238, 238))
        self.elements_listbox.Enable(False)
        self.checkbox_limit_buffer.SetValue(1)
        self.panel_controller.SetBackgroundColour(wx.Colour(204, 204, 204))
        self.checkbox_autostart.SetValue(1)
        self.checkbox_autobeep.SetValue(1)
        self.button_writer_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_writer_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_writer_control.SetBitmap(wx.Bitmap("icons/icons8-play-50.png", wx.BITMAP_TYPE_ANY))
        self.button_writer_control.SetBitmapPressed(wx.Bitmap("icons/icons8-play-50.png", wx.BITMAP_TYPE_ANY))
        self.button_delete_job.SetSize(self.button_delete_job.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobInfo.__do_layout
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.VERTICAL)
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9 = wx.BoxSizer(wx.VERTICAL)
        sizer_14 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_9.Add(self.gauge_writer, 0, wx.EXPAND, 0)
        label_1 = wx.StaticText(self.panel_writer, wx.ID_ANY, "Job Elements: ")
        sizer_10.Add(label_1, 4, 0, 0)
        sizer_10.Add(self.text_job_progress, 5, 0, 0)
        label_2 = wx.StaticText(self.panel_writer, wx.ID_ANY, "/")
        sizer_10.Add(label_2, 0, 0, 0)
        sizer_10.Add(self.text_job_total, 5, 0, 0)
        sizer_9.Add(sizer_10, 1, wx.EXPAND, 0)
        label_6 = wx.StaticText(self.panel_writer, wx.ID_ANY, "Command Index: ")
        sizer_14.Add(label_6, 4, 0, 0)
        sizer_14.Add(self.text_command_index, 10, 0, 0)
        sizer_9.Add(sizer_14, 1, wx.EXPAND, 0)
        self.panel_writer.SetSizer(sizer_9)
        sizer_2.Add(self.panel_writer, 0, wx.EXPAND, 0)
        sizer_2.Add(self.elements_listbox, 10, wx.EXPAND, 0)
        sizer_11.Add(self.checkbox_limit_buffer, 1, 0, 0)
        sizer_11.Add(self.gauge_controller, 0, wx.EXPAND, 0)
        label_7 = wx.StaticText(self.panel_controller, wx.ID_ANY, "Packet Buffer")
        sizer_12.Add(label_7, 4, 0, 0)
        sizer_12.Add(self.text_packet_buffer, 5, 0, 0)
        label_4 = wx.StaticText(self.panel_controller, wx.ID_ANY, "/")
        sizer_12.Add(label_4, 0, 0, 0)
        sizer_12.Add(self.spin_packet_buffer_max, 0, 0, 0)
        sizer_11.Add(sizer_12, 1, wx.EXPAND, 0)
        self.panel_controller.SetSizer(sizer_11)
        sizer_2.Add(self.panel_controller, 0, wx.EXPAND, 0)
        sizer_4.Add(self.checkbox_autostart, 0, 0, 0)
        sizer_4.Add(self.checkbox_autohome, 0, 0, 0)
        sizer_4.Add(self.checkbox_autobeep, 0, 0, 0)
        sizer_2.Add(sizer_4, 0, wx.EXPAND, 0)
        sizer_3.Add(self.button_writer_control, 1, 0, 0)
        sizer_3.Add(self.button_delete_job, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

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

    def on_listbox_click(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_click' not implemented!")
        event.Skip()

    def on_listbox_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_dclick' not implemented!")
        event.Skip()

    def on_button_delete_job(self, event):  # wxGlade: JobInfo.<event_handler>
        from LhymicroWriter import LaserThread
        self.project.writer.thread = LaserThread(self.project)
        self.project.writer.thread.refresh_element_list()

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        state = self.project.writer.thread.state
        if state == THREAD_STATE_STARTED:
            self.project.writer.thread.state = THREAD_STATE_PAUSED
            self.set_writer_button_by_state()
        elif state == THREAD_STATE_PAUSED:
            self.project.writer.thread.state = THREAD_STATE_STARTED
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
            self.button_writer_control.SetValue(False)
        elif state == THREAD_STATE_PAUSED:
            self.button_writer_control.SetBackgroundColour("#00ff00")
            self.button_writer_control.SetLabel("Resume Job")
            self.button_writer_control.SetValue(False)
        elif state == THREAD_STATE_UNSTARTED:
            self.button_writer_control.SetBackgroundColour("#00ff00")
            self.button_writer_control.SetLabel("Start Job")
            self.button_writer_control.SetValue(True)
        elif state == THREAD_STATE_STARTED:
            self.button_writer_control.SetBackgroundColour("#ffff00")
            self.button_writer_control.SetLabel("Pause Job")
            self.button_writer_control.SetValue(True)
        elif state == THREAD_STATE_ABORT:
            self.button_writer_control.SetBackgroundColour("#ff0000")
            self.button_writer_control.SetLabel("Close Aborted Job")
            self.button_writer_control.SetValue(False)

    def on_combo_select_writer(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_combo_select_writer' not implemented!")
        event.Skip()

    def post_update(self):
        if not self.dirty:
            self.dirty = True
            wx.CallAfter(self.post_update_on_gui_thread)

    def post_update_on_gui_thread(self):
        if self.project is None:
            return  # left over update on closed window
        self.text_packet_buffer.SetValue(str(self.buffer_size))
        self.gauge_controller.SetValue(self.buffer_size)
        self.gauge_controller.SetRange(self.spin_packet_buffer_max.GetValue())

        self.text_job_progress.SetValue(str(self.progress_update))
        self.text_job_total.SetValue(str(self.progress_total))
        self.gauge_writer.SetValue(self.progress_update)
        self.gauge_writer.SetRange(self.progress_total)

        self.set_writer_button_by_state()
        self.dirty = False

    def on_buffer_update(self, value):
        self.buffer_size = value
        self.post_update()

    def on_command_progress(self, command_progress):
        self.command_progress = command_progress
        self.post_update()

    def on_progress(self, progress):
        last, limit = progress
        self.progress_total = limit
        self.progress_update = last
        self.post_update()
