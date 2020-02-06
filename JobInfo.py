import wx

from LaserCommandConstants import *
from icons import icons8_laser_beam_52, icons8_route_50

_ = wx.GetTranslation


class JobInfo(wx.Frame):

    def __init__(self, *args, **kwds):
        # begin wxGlade: JobInfo.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)

        self.SetSize((659, 612))
        self.elements_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.operations_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.button_job_spooler = wx.BitmapButton(self, wx.ID_ANY, icons8_route_50.GetBitmap())
        self.button_writer_control = wx.Button(self, wx.ID_ANY, _("Start Job"))
        self.button_writer_control.SetBitmap(icons8_laser_beam_52.GetBitmap())
        self.button_writer_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))

        # Menu Bar
        self.JobInfo_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Trace Simple"), "")
        self.Bind(wx.EVT_MENU, self.spool_trace_simple, id=t.GetId())
        t.Enable(False)

        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Trace Hull"), "")
        self.Bind(wx.EVT_MENU, self.spool_trace_hull, id=t.GetId())
        t.Enable(False)
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Run"))

        wxglade_tmp_menu = wx.Menu()
        self.menu_autostart = wxglade_tmp_menu.Append(wx.ID_ANY, _("Start Spooler"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_auto_start_controller, id=self.menu_autostart.GetId())
        self.menu_autohome = wxglade_tmp_menu.Append(wx.ID_ANY, _("Home After"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_home_after, id=self.menu_autohome.GetId())
        self.menu_autobeep = wxglade_tmp_menu.Append(wx.ID_ANY, _("Beep After"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_beep_after, id=self.menu_autobeep.GetId())
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Automatic"))

        wxglade_tmp_menu = wx.Menu()
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Home"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_home, id=t.GetId())
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Wait"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_wait, id=t.GetId())
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Beep"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_beep, id=t.GetId())
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Add"))
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
        self.kernel = None

        self.Bind(wx.EVT_CLOSE, self.on_close, self)

        self.device = None
        self.job_items = None
        self.required_preprocessing_operations = None

    def spool_trace_simple(self, event):
        print("Spool Simple.")

    def spool_trace_hull(self, event):
        print("Spool Hull.")

    def jobadd_home(self, event):
        def home():
            yield COMMAND_WAIT_BUFFER_EMPTY
            yield COMMAND_HOME

        self.job_items.append(home)
        self.update_gui()

    def jobadd_wait(self, event):
        wait_amount = 5.0

        def wait():
            yield COMMAND_WAIT_BUFFER_EMPTY
            yield COMMAND_WAIT, wait_amount

        self.job_items.append(wait)
        self.update_gui()

    def jobadd_beep(self, event):
        def beep():
            yield COMMAND_WAIT_BUFFER_EMPTY
            yield COMMAND_BEEP

        self.job_items.append(beep)
        self.update_gui()

    def jobadd_remove_text(self):
        for e in self.job_items:
            try:
                t = e.type
            except AttributeError:
                t = 'function'
            if t == 'text':
                def remove_text():
                    self.job_items = [e for e in self.job_items if not hasattr(e, 'type') or e.type != 'text']
                    self.update_gui()

                self.required_preprocessing_operations.append(remove_text)
                break

    def jobadd_actualize_image(self):
        for e in self.job_items:
            try:
                t = e.type
            except AttributeError:
                t = 'function'
            try:
                if e.needs_actualization():
                    def actualize():
                        for e in self.job_items:
                            try:
                                if e.needs_actualization():
                                    e.make_actual()
                            except AttributeError:
                                pass

                    self.required_preprocessing_operations.append(actualize)
                    break
            except AttributeError:
                pass

    def jobadd_scale_rotary(self):
        if self.device.scale_x != 1.0 or self.device.scale_y != 1.0:
            def scale_project():
                p = self.device
                scale_str = 'scale(%f,%f,%f,%f)' % (p.scale_x, p.scale_y, p.current_x, p.current_y)
                for e in self.job_items:
                    try:
                        e.element *= scale_str
                    except AttributeError:
                        pass
                self.jobadd_actualize_image()

            self.required_preprocessing_operations.append(scale_project)

    def set_job_items(self, elements):
        self.job_items = elements
        self.jobadd_remove_text()
        self.jobadd_actualize_image()
        if self.device.rotary:
            self.jobadd_scale_rotary()

        if self.device.autobeep:
            self.jobadd_beep(None)

        if self.device.autohome:
            self.jobadd_home(None)

        self.update_gui()

    def set_device(self, device):
        self.device = device
        if self.device is None:
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("You do not have a selected device."),
                                   _("No Device Selected."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
        else:
            self.menu_autohome.Check(device.autohome)
            self.menu_autobeep.Check(device.autobeep)
            self.menu_autostart.Check(device.autostart)

    def set_kernel(self, kernel):
        self.kernel = kernel
        self.set_device(kernel.device)
        self.required_preprocessing_operations = []
        self.job_items = []
        self.set_job_items(kernel.operations[:])
        self.update_gui()

    def on_close(self, event):
        self.kernel.mark_window_closed("JobInfo")
        self.kernel = None
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobInfo.__set_properties
        self.SetTitle("Job")
        self.elements_listbox.SetToolTip(_("Element List"))
        self.operations_listbox.SetToolTip(_("Operation List"))
        self.button_writer_control.SetToolTip(_("Start the Job"))

        self.button_job_spooler.SetMinSize((50, 50))
        self.button_job_spooler.SetToolTip(_("View Spooler"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobInfo.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Elements and Operations")), wx.HORIZONTAL)
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

    def on_check_auto_start_controller(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.autostart = self.menu_autostart.IsChecked()

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.autohome = self.menu_autohome.IsChecked()

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.autobeep = self.menu_autobeep.IsChecked()

    def on_button_job_spooler(self, event=None):  # wxGlade: JobInfo.<event_handler>
        self.kernel.open_window("JobSpooler")

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        if len(self.required_preprocessing_operations) == 0:
            self.device.send_job(self.job_items)
            self.on_button_job_spooler()
            self.kernel.close_old_window("JobInfo")
        else:
            # copy of operations, so operations can add ops.
            ops = self.required_preprocessing_operations[:]
            self.required_preprocessing_operations = []
            for op in ops:
                op()
            # TODO: break the connection between elements in kernel and the elements here.
            self.kernel('elements', 0)
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
        elements = self.job_items
        operations = self.required_preprocessing_operations
        if elements is not None and len(elements) != 0:
            self.elements_listbox.InsertItems([name_str(e) for e in self.job_items], 0)
        if operations is not None and len(operations) != 0:
            self.operations_listbox.InsertItems([name_str(e) for e in self.required_preprocessing_operations], 0)

            self.button_writer_control.SetLabelText(_("Execute Operations"))
            self.button_writer_control.SetBackgroundColour(wx.Colour(255, 255, 102))
        else:
            self.button_writer_control.SetLabelText(_("Start Job"))
            self.button_writer_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.Refresh()
