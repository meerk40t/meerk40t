import wx

from Kernel import Module
from LaserOperation import *
from icons import icons8_laser_beam_52, icons8_route_50
from OperationPreprocessor import OperationPreprocessor

_ = wx.GetTranslation


class JobInfo(wx.Frame, Module):

    def __init__(self, *args, **kwds):
        # begin wxGlade: JobInfo.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP
        wx.Frame.__init__(self, *args, **kwds)
        Module.__init__(self)
        self.SetSize((659, 612))
        self.operations_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.commands_listbox = wx.ListBox(self, wx.ID_ANY, choices=[], style=wx.LB_ALWAYS_SB | wx.LB_SINGLE)
        self.button_job_spooler = wx.BitmapButton(self, wx.ID_ANY, icons8_route_50.GetBitmap())
        self.button_writer_control = wx.Button(self, wx.ID_ANY, _("Start Job"))
        self.button_writer_control.SetBitmap(icons8_laser_beam_52.GetBitmap())
        self.button_writer_control.SetFont(
            wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))

        # Menu Bar
        self.JobInfo_menubar = wx.MenuBar()
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
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Interrupt"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_interrupt, id=t.GetId())
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Add"))
        self.SetMenuBar(self.JobInfo_menubar)
        # Menu Bar end

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_LISTBOX, self.on_listbox_operation_click, self.operations_listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_operation_dclick, self.operations_listbox)
        self.Bind(wx.EVT_LISTBOX, self.on_listbox_commands_click, self.commands_listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_commands_dclick, self.commands_listbox)
        self.Bind(wx.EVT_BUTTON, self.on_button_start_job, self.button_writer_control)
        self.Bind(wx.EVT_BUTTON, self.on_button_job_spooler, self.button_job_spooler)
        # end wxGlade

        self.Bind(wx.EVT_CLOSE, self.on_close, self)

        self.preprocessor = OperationPreprocessor()
        self.operations = []

    def jobadd_home(self, event):
        self.operations.append(OperationPreprocessor.home)
        self.update_gui()

    def jobadd_wait(self, event):
        self.operations.append(OperationPreprocessor.wait)
        self.update_gui()

    def jobadd_beep(self, event):
        self.operations.append(OperationPreprocessor.beep)
        self.update_gui()

    def jobadd_interrupt(self, event):
        self.operations.append(self.interrupt)
        self.update_gui()

    def interrupt(self):
        yield COMMAND_WAIT_FINISH
        yield COMMAND_FUNCTION, self.interrupt_popup

    def interrupt_popup(self):
        dlg = wx.MessageDialog(None, _("Spooling Interrupted. Press OK to Continue."),
                               _("Interrupt"), wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def set_operations(self, operations):
        self.preprocessor.device = self.device

        if not isinstance(operations, list):
            operations = [operations]
        self.operations.clear()
        for op in operations:
            self.operations.append(copy(op))
        if self.device.autobeep:
            self.jobadd_beep(None)

        if self.device.autohome:
            self.jobadd_home(None)

        self.preprocessor.process(self.operations)
        self.update_gui()

    def initialize(self):
        self.device.close('module', self.name)
        self.Show()
        self.operations = []
        self.device.setting(bool, "rotary", False)
        self.device.setting(float, "scale_x", 1.0)
        self.device.setting(float, "scale_y", 1.0)
        self.device.setting(bool, "autohome", False)
        self.device.setting(bool, "autobeep", True)
        self.device.setting(bool, "autostart", True)
        self.device.listen("element_property_update", self.on_element_property_update)

        if self.device.is_root():
            for attr in dir(self):
                value = getattr(self, attr)
                if isinstance(value, wx.Control):
                    value.Enable(False)
            dlg = wx.MessageDialog(None, _("You do not have a selected device."),
                                   _("No Device Selected."), wx.OK | wx.ICON_WARNING)
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        self.menu_autohome.Check(self.device.autohome)
        self.menu_autobeep.Check(self.device.autobeep)
        self.menu_autostart.Check(self.device.autostart)

    def shutdown(self, channel):
        self.Close()

    def on_close(self, event):
        self.device.unlisten("element_property_update", self.on_element_property_update)
        self.device.module_instance_remove(self.name)
        event.Skip()  # Call destroy as regular.

    def __set_properties(self):
        # begin wxGlade: JobInfo.__set_properties
        self.SetTitle("Job")
        self.operations_listbox.SetToolTip(_("operation List"))
        self.commands_listbox.SetToolTip(_("Command List"))
        self.button_writer_control.SetToolTip(_("Start the Job"))

        self.button_job_spooler.SetMinSize((50, 50))
        self.button_job_spooler.SetToolTip(_("View Spooler"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: JobInfo.__do_layout
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Operations and Commands")), wx.HORIZONTAL)
        sizer_1.Add(self.operations_listbox, 10, wx.EXPAND, 0)
        sizer_1.Add(self.commands_listbox, 3, wx.EXPAND, 0)
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
        self.device.module_instance_open("JobSpooler", None, -1, "")

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        if len(self.preprocessor.commands) == 0:
            self.device.spooler.send_job(self.operations)
            self.on_button_job_spooler()
            self.device.module_instance_close("JobInfo")
        else:
            self.preprocessor.execute()
            self.update_gui()

    def on_listbox_operation_click(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_listbox_operation_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        node_index = self.operations_listbox.GetSelection()
        if node_index == -1:
            return
        obj = self.operations[node_index]

        if isinstance(obj, RasterOperation):
            self.device.module_instance_open("RasterProperty", None, -1, "").set_operation(obj)
        elif isinstance(obj, (CutOperation, EngraveOperation)):
            self.device.module_instance_open("EngraveProperty", None, -1, "").set_operation(obj)
        event.Skip()

    def on_listbox_commands_click(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_commands_click' not implemented!")
        event.Skip()

    def on_listbox_commands_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        print("Event handler 'on_listbox_commands_dclick' not implemented!")
        event.Skip()

    def on_element_property_update(self, *args):
        self.update_gui()

    def update_gui(self):
        def name_str(e):
            try:
                return e.__name__
            except AttributeError:
                return str(e)

        self.commands_listbox.Clear()
        self.operations_listbox.Clear()
        operations = self.operations
        commands = self.preprocessor.commands
        if operations is not None and len(operations) != 0:
            self.operations_listbox.InsertItems([name_str(e) for e in self.operations], 0)
        if commands is not None and len(commands) != 0:
            self.commands_listbox.InsertItems([name_str(e) for e in self.preprocessor.commands], 0)

            self.button_writer_control.SetLabelText(_("Execute Commands"))
            self.button_writer_control.SetBackgroundColour(wx.Colour(255, 255, 102))
        else:
            self.button_writer_control.SetLabelText(_("Start Job"))
            self.button_writer_control.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.Refresh()
