import wx

from icons import icons8_laser_beam_52, icons8_route_50


class JobInfo(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobInfo.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((500, 584))
        self.elements_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.checkbox_autostart = wx.CheckBox(self, wx.ID_ANY, "Automatically Start")
        self.checkbox_autohome = wx.CheckBox(self, wx.ID_ANY, "Home After")
        self.checkbox_autobeep = wx.CheckBox(self, wx.ID_ANY, "Beep After")
        self.button_writer_control = wx.Button(self, wx.ID_ANY, "Start Job")
        self.button_job_spooler = wx.BitmapButton(self, wx.ID_ANY, icons8_route_50.GetBitmap())

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LISTBOX, self.on_listbox_click, self.elements_listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_dclick, self.elements_listbox)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_auto_start_controller, self.checkbox_autostart)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_home_after, self.checkbox_autohome)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_beep_after, self.checkbox_autobeep)
        self.Bind(wx.EVT_BUTTON, self.on_button_start_job, self.button_writer_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_job_spooler, self.button_job_spooler)
        # end wxGlade
        self.project = None

        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.elements = None

    def set_project(self, project, elements):
        self.project = project
        self.elements = elements
        self.checkbox_autobeep.SetValue(self.project.writer.autobeep)
        self.checkbox_autohome.SetValue(self.project.writer.autohome)
        self.checkbox_autostart.SetValue(self.project.writer.autostart)
        if elements is not None and len(elements) != 0:
            self.elements_listbox.InsertItems([str(e) for e in self.elements], 0)

    def on_close(self, event):
        try:
            del self.project.windows["jobinfo"]
        except KeyError:
            pass
        self.project = None
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobInfo.__set_properties
        self.SetTitle("Job")
        self.elements_listbox.Enable(False)
        self.checkbox_autostart.SetValue(1)
        self.checkbox_autobeep.SetValue(1)
        self.button_writer_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.button_writer_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_writer_control.SetBitmap(icons8_laser_beam_52.GetBitmap())
        self.button_job_spooler.SetSize(self.button_job_spooler.GetBestSize())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobInfo.__do_layout
        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.elements_listbox, 10, wx.EXPAND, 0)
        sizer_4.Add(self.checkbox_autostart, 0, 0, 0)
        sizer_4.Add(self.checkbox_autohome, 0, 0, 0)
        sizer_4.Add(self.checkbox_autobeep, 0, 0, 0)
        sizer_2.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_3.Add(self.button_writer_control, 1, 0, 0)
        sizer_3.Add(self.button_job_spooler, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def on_check_limit_packet_buffer(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.thread.limit_buffer = not self.project.writer.thread.limit_buffer

    def on_check_auto_start_controller(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.autostart = not self.project.writer.autostart

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.autohome = not self.project.writer.autohome

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.autobeep = not self.project.writer.autobeep

    def on_button_job_spooler(self, event=None):  # wxGlade: JobInfo.<event_handler>
        self.project.close_old_window("jobspooler")
        from JobSpooler import JobSpooler
        window = JobSpooler(None, wx.ID_ANY, "")
        window.set_project(self.project)
        window.Show()
        self.project.windows["jobspooler"] = window

    def on_listbox_click(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_click' not implemented!")
        event.Skip()

    def on_listbox_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_dclick' not implemented!")
        event.Skip()

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        self.project.writer.add_queue(self.elements)
        self.on_button_job_spooler()
        self.Close()
