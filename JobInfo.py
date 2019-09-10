import wx


class JobInfo(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobInfo.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((388, 402))
        self.panel_writer = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.gauge_writer = wx.Gauge(self.panel_writer, wx.ID_ANY, 100)
        self.text_job_progress = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.text_job_total = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.checkbox_queue_packets = wx.CheckBox(self.panel_writer, wx.ID_ANY, "Queue Packet Building")
        self.spin_packet_queue_size = wx.SpinCtrl(self.panel_writer, wx.ID_ANY, "50", min=1, max=10000)
        self.button_writer_control = wx.ToggleButton(self.panel_writer, wx.ID_ANY, "")
        self.text_writer_status = wx.TextCtrl(self.panel_writer, wx.ID_ANY, "")
        self.panel_time = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.text_time_run = wx.TextCtrl(self.panel_time, wx.ID_ANY, "")
        self.text_time_estimate = wx.TextCtrl(self.panel_time, wx.ID_ANY, "")
        self.text_time_remaining = wx.TextCtrl(self.panel_time, wx.ID_ANY, "")
        self.panel_controller = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.gauge_controller = wx.Gauge(self.panel_controller, wx.ID_ANY, 100)
        self.text_controller_progress = wx.TextCtrl(self.panel_controller, wx.ID_ANY, "")
        self.text_controller_total = wx.TextCtrl(self.panel_controller, wx.ID_ANY, "")
        self.panel_usb = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_RAISED)
        self.text_usb_status = wx.TextCtrl(self.panel_usb, wx.ID_ANY, "")
        self.button_stop = wx.BitmapButton(self, wx.ID_ANY,
                                           wx.Bitmap("icons/icons8-stop-sign-50.png", wx.BITMAP_TYPE_ANY))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_writer_control, self.button_writer_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        # end wxGlade
        self.project = None
        self.Bind(wx.EVT_CLOSE, self.on_close, self)

    def set_project(self, project):
        self.project = project
        self.project.thread.queue_listener = self.on_queue
        self.project.thread.progress_listener = self.on_progress
        if self.project.controller.state == 2:
            self.button_stop.SetBackgroundColour("#00ff00")
        elif self.project.controller.state == 1:
            self.button_stop.SetBackgroundColour("#ff0000")

    def on_close(self, event):
        if self.project.thread is not None:
            self.project.thread.progress_listener = None
            self.project.thread.queue_listener = None
        self.project = None
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobInfo.__set_properties
        self.SetTitle("Job")
        self.checkbox_queue_packets.SetValue(1)
        self.button_writer_control.SetBackgroundColour(wx.Colour(255, 255, 0))
        self.button_writer_control.SetBitmap(wx.Bitmap("icons/icons8-play-50.png", wx.BITMAP_TYPE_ANY))
        self.button_writer_control.SetBitmapPressed(wx.Bitmap("icons/icons8-pause-50.png", wx.BITMAP_TYPE_ANY))
        self.panel_writer.SetBackgroundColour(wx.Colour(238, 238, 238))
        self.panel_time.SetBackgroundColour(wx.Colour(221, 221, 221))
        self.panel_controller.SetBackgroundColour(wx.Colour(204, 204, 204))
        self.panel_usb.SetBackgroundColour(wx.Colour(187, 187, 187))
        self.button_stop.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.button_stop.SetSize(self.button_stop.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobInfo.__do_layout
        sizer_8 = wx.GridBagSizer(0, 0)
        sizer_13 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.VERTICAL)
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_15 = wx.GridBagSizer(0, 0)
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
        sizer_14.Add(self.checkbox_queue_packets, 0, 0, 0)
        sizer_14.Add(self.spin_packet_queue_size, 0, 0, 0)
        sizer_14.Add(self.button_writer_control, 0, 0, 0)
        sizer_9.Add(sizer_14, 1, wx.EXPAND, 0)
        sizer_9.Add(self.text_writer_status, 0, wx.EXPAND, 0)
        self.panel_writer.SetSizer(sizer_9)
        sizer_8.Add(self.panel_writer, (0, 0), (1, 2), wx.EXPAND, 0)
        label_6 = wx.StaticText(self.panel_time, wx.ID_ANY, "Time Running:")
        sizer_15.Add(label_6, (0, 0), (1, 1), wx.ALIGN_RIGHT, 0)
        sizer_15.Add(self.text_time_run, (0, 1), (1, 1), 0, 0)
        label_7 = wx.StaticText(self.panel_time, wx.ID_ANY, "Estimate:")
        sizer_15.Add(label_7, (1, 0), (1, 1), wx.ALIGN_RIGHT, 0)
        sizer_15.Add(self.text_time_estimate, (1, 1), (1, 1), 0, 0)
        label_8 = wx.StaticText(self.panel_time, wx.ID_ANY, "Estimate Remaining:")
        sizer_15.Add(label_8, (2, 0), (1, 1), wx.ALIGN_RIGHT, 0)
        sizer_15.Add(self.text_time_remaining, (2, 1), (1, 1), 0, 0)
        self.panel_time.SetSizer(sizer_15)
        sizer_8.Add(self.panel_time, (1, 0), (1, 2), wx.EXPAND, 0)
        sizer_11.Add(self.gauge_controller, 0, wx.EXPAND, 0)
        label_3 = wx.StaticText(self.panel_controller, wx.ID_ANY, "Sending Packets: ")
        sizer_12.Add(label_3, 4, 0, 0)
        sizer_12.Add(self.text_controller_progress, 5, 0, 0)
        label_4 = wx.StaticText(self.panel_controller, wx.ID_ANY, "/")
        sizer_12.Add(label_4, 0, 0, 0)
        sizer_12.Add(self.text_controller_total, 5, 0, 0)
        sizer_11.Add(sizer_12, 1, wx.EXPAND, 0)
        self.panel_controller.SetSizer(sizer_11)
        sizer_8.Add(self.panel_controller, (2, 0), (1, 2), wx.EXPAND, 0)
        label_5 = wx.StaticText(self.panel_usb, wx.ID_ANY, "Usb Status")
        sizer_13.Add(label_5, 0, 0, 0)
        sizer_13.Add(self.text_usb_status, 1, 0, 0)
        self.panel_usb.SetSizer(sizer_13)
        sizer_8.Add(self.panel_usb, (3, 0), (1, 2), wx.EXPAND, 0)
        sizer_8.Add(self.button_stop, (4, 0), (1, 2), wx.EXPAND, 0)
        self.SetSizer(sizer_8)
        sizer_8.AddGrowableCol(0)
        self.Layout()
        # end wxGlade

    def on_button_writer_control(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.project is not None:
            if self.project.thread is not None:
                if self.button_writer_control.GetValue():
                    self.project.thread.state = 3
                else:
                    self.project.thread.state = 0

    def on_button_stop(self, event):  # wxGlade: JobInfo.<event_handler>
        if self.project is not None:
            if self.project.thread is not None:
                if self.project.controller.state == 1:
                    self.project.controller.state = 2
                    self.button_stop.SetBackgroundColour("#00ff00")
                else:
                    self.project.controller.state = 1
                    self.button_stop.SetBackgroundColour("#ff0000")

    def on_queue(self, last, limit):
        self.text_controller_progress.SetValue(str(last))
        self.text_controller_total.SetValue(str(limit))
        self.gauge_controller.SetValue(last)
        self.gauge_controller.SetRange(limit)

    def on_progress(self, last, limit):
        self.text_job_progress.SetValue(str(last))
        self.text_job_total.SetValue(str(limit))
        self.gauge_writer.SetValue(last)
        self.gauge_writer.SetRange(limit)
