import wx
from LaserCommandConstants import *
from icons import icons8_laser_beam_52, icons8_route_50


class JobInfo(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: JobInfo.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((500, 584))

        self.SetSize((659, 612))
        self.elements_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.operations_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.button_job_spooler = wx.BitmapButton(self, wx.ID_ANY, icons8_route_50.GetBitmap())
        self.button_writer_control = wx.Button(self, wx.ID_ANY, "Start Job")
        self.button_writer_control.SetBitmap(icons8_laser_beam_52.GetBitmap())
        self.button_writer_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))

        # Menu Bar
        self.JobInfo_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(wx.ID_ANY, "Trace Simple", "")
        wxglade_tmp_menu.Append(wx.ID_ANY, "Trace Hull", "")
        self.JobInfo_menubar.Append(wxglade_tmp_menu, "Run")
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(wx.ID_ANY, "Start Spooler", "", wx.ITEM_CHECK)
        wxglade_tmp_menu.Append(wx.ID_ANY, "Home After", "", wx.ITEM_CHECK)
        wxglade_tmp_menu.Append(wx.ID_ANY, "Beep After", "", wx.ITEM_CHECK)
        self.JobInfo_menubar.Append(wxglade_tmp_menu, "Automatic")
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu.Append(wx.ID_ANY, "Home", "")
        wxglade_tmp_menu.Append(wx.ID_ANY, "Wait", "")
        wxglade_tmp_menu.Append(wx.ID_ANY, "Beep", "")
        self.JobInfo_menubar.Append(wxglade_tmp_menu, "Add")
        self.SetMenuBar(self.JobInfo_menubar)
        # Menu Bar end

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LISTBOX, self.on_listbox_element_click, self.elements_listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_element_dclick, self.elements_listbox)
        self.Bind(wx.EVT_LISTBOX, self.on_listbox_operations_click, self.operations_listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_operations_dclick, self.operations_listbox)
        self.Bind(wx.EVT_BUTTON, self.on_button_start_job, self.button_writer_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_job_spooler, self.button_job_spooler)
        # end wxGlade
        self.project = None

        self.Bind(wx.EVT_CLOSE, self.on_close, self)
        self.elements = None
        self.operations = None

    def set_project(self, project, elements=None, operations=None):
        self.project = project
        self.elements = elements
        self.operations = operations
        if self.elements is None:
            self.elements = []
        if self.operations is None:
            self.operations = []

        if self.project.writer.autobeep:
            def beep():
                yield COMMAND_WAIT_BUFFER_EMPTY
                yield COMMAND_BEEP
            self.elements.append(beep)

        if self.project.writer.autohome:
            def home():
                yield COMMAND_HOME
            self.elements.append(home)

        for e in self.elements:
            try:
                if e.needs_actualization():
                    def actualize():
                        for e in self.elements:
                            try:
                                if e.needs_actualization():
                                    e.make_actual()
                            except AttributeError:
                                pass
                    self.operations.append(actualize)
                    break
            except AttributeError:
                pass
        self.update_gui()

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
        self.elements_listbox.SetToolTip("Element List")
        self.operations_listbox.SetToolTip("Operation List")
        self.button_writer_control.SetToolTip("Start the Job")

        self.button_job_spooler.SetMinSize((50, 50))
        self.button_job_spooler.SetToolTip("View Spooler")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobInfo.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Elements and Operations"), wx.HORIZONTAL)
        sizer_1.Add(self.elements_listbox, 10, wx.EXPAND, 0)
        sizer_1.Add(self.operations_listbox, 3, wx.EXPAND, 0)
        sizer_2.Add(sizer_1, 10, wx.EXPAND, 0)
        sizer_3.Add(self.button_writer_control, 1, wx.EXPAND, 0)
        sizer_3.Add(self.button_job_spooler, 0, 0, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
        self.Centre()
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

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        if len(self.operations) == 0:
            self.project.writer.add_queue(self.elements)
            self.on_button_job_spooler()
            self.Close()
        else:
            for op in self.operations:
                op()
            self.operations = []
            self.project('elements',0)
            self.update_gui()

    def on_listbox_element_click(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_element_click' not implemented!")
        event.Skip()

    def on_listbox_element_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_element_dclick' not implemented!")
        event.Skip()

    def on_listbox_operations_click(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_operations_click' not implemented!")
        event.Skip()

    def on_listbox_operations_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_operations_dclick' not implemented!")
        event.Skip()

    def update_gui(self):

        def name_str(e):
            try:
                return e.__name__
            except AttributeError:
                return str(e)

        self.operations_listbox.Clear()
        self.elements_listbox.Clear()
        elements = self.elements
        operations = self.operations
        if elements is not None and len(elements) != 0:
            self.elements_listbox.InsertItems([name_str(e) for e in self.elements], 0)
        if operations is not None and len(operations) != 0:
            self.operations_listbox.InsertItems([name_str(e) for e in self.operations], 0)

            self.button_writer_control.SetLabelText("Execute Operations")
            self.button_writer_control.SetBackgroundColour(wx.Colour(255, 255, 102))
        else:
            self.button_writer_control.SetLabelText("Start Job")
            self.button_writer_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.Refresh()
