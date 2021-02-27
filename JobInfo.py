import wx

from Kernel import Module
from LaserOperation import *
from icons import icons8_laser_beam_52, icons8_route_50
from OperationPreprocessor import OperationPreprocessor
from svgelements import Length

_ = wx.GetTranslation


class JobInfo(wx.Frame, Module):

    def __init__(self, parent, ops, *args, **kwds):
        wx.Frame.__init__(self, parent, -1, "",
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL)
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
        self.menu_prehome = wxglade_tmp_menu.Append(wx.ID_ANY, _("Home Before"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_home_before, id=self.menu_prehome.GetId())
        self.menu_autohome = wxglade_tmp_menu.Append(wx.ID_ANY, _("Home After"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_home_after, id=self.menu_autohome.GetId())

        self.menu_prephysicalhome = wxglade_tmp_menu.Append(wx.ID_ANY, _("Physical Home Before"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_physicalhome_before, id=self.menu_prephysicalhome.GetId())
        self.menu_autophysicalhome = wxglade_tmp_menu.Append(wx.ID_ANY, _("Physical Home After"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_physicalhome_after, id=self.menu_autophysicalhome.GetId())

        self.menu_autoorigin = wxglade_tmp_menu.Append(wx.ID_ANY, _("Return to Origin After"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_origin_after, id=self.menu_autoorigin.GetId())

        self.menu_autobeep = wxglade_tmp_menu.Append(wx.ID_ANY, _("Beep After"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_beep_after, id=self.menu_autobeep.GetId())
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Automatic"))

        wxglade_tmp_menu = wx.Menu()
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Home"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_home, id=t.GetId())
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Physical Home"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_physicalhome, id=t.GetId())
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Wait"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_wait, id=t.GetId())
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Beep"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_beep, id=t.GetId())
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Interrupt"), "")
        self.Bind(wx.EVT_MENU, self.jobadd_interrupt, id=t.GetId())
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Add"))

        wxglade_tmp_menu = wx.Menu()
        self.menu_rapid = wxglade_tmp_menu.Append(wx.ID_ANY, _("Rapid Between"), "", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_rapid, id=self.menu_rapid.GetId())
        wxglade_tmp_menu.AppendSeparator()
        self.menu_jog = wxglade_tmp_menu.Append(wx.ID_ANY, _("Jog Standard"), "", wx.ITEM_RADIO)
        self.Bind(wx.EVT_MENU, self.on_check_jog, id=self.menu_jog.GetId())
        # self.menu_jog2 = wxglade_tmp_menu.Append(wx.ID_ANY, _("Jog Switch"), "", wx.ITEM_RADIO)
        # self.Bind(wx.EVT_MENU, self.on_check_jog2, id=self.menu_jog2.GetId())
        self.menu_jog3 = wxglade_tmp_menu.Append(wx.ID_ANY, _("Jog Finish"), "", wx.ITEM_RADIO)
        self.Bind(wx.EVT_MENU, self.on_check_jog3, id=self.menu_jog3.GetId())
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Settings"))

        wxglade_tmp_menu = wx.Menu()
        t = wxglade_tmp_menu.Append(wx.ID_ANY, _("Step and Repeat"))
        self.Bind(wx.EVT_MENU, self.jobchange_step_repeat, id=t.GetId())
        self.JobInfo_menubar.Append(wxglade_tmp_menu, _("Tools"))

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

        # OSX Window close
        def on_key_down(event):
            if event.GetKeyCode() == ord('W') and event.CmdDown():
                self.Close(False)
                return
            event.Skip()

        self.Bind(wx.EVT_KEY_DOWN, on_key_down)

        # Moved to elements in 0.7.0
        self.preprocessor = OperationPreprocessor()
        if not isinstance(ops, list):
            ops = [ops]
        self.operations = ops
        self._original_ops = list(ops)

    def jobchange_step_repeat(self, event=None):
        dlg = wx.TextEntryDialog(self, _("How many copies wide?"), _("Enter Columns"), '')
        dlg.SetValue('5')

        if dlg.ShowModal() == wx.ID_OK:
            try:
                cols = int(dlg.GetValue())
            except ValueError:
                dlg.Destroy()
                return
        else:
            dlg.Destroy()
            return
        dlg.Destroy()

        dlg = wx.TextEntryDialog(self, _("How many copies high?"), _("Enter Rows"), '')
        dlg.SetValue('5')
        if dlg.ShowModal() == wx.ID_OK:
            try:
                rows = int(dlg.GetValue())
            except ValueError:
                dlg.Destroy()
                return
        else:
            dlg.Destroy()
            return
        dlg.Destroy()

        dlg = wx.TextEntryDialog(self, _("How far apart are these copies width-wise? eg. 2in, 3cm, 50mm, 10%"), _("Enter X Gap"), '')
        dlg.SetValue('')
        if dlg.ShowModal() == wx.ID_OK:
            try:
                x_distance = Length(dlg.GetValue()).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            except ValueError:
                dlg.Destroy()
                return
            if isinstance(x_distance, Length):
                dlg.Destroy()
                return
        else:
            dlg.Destroy()
            return
        dlg.Destroy()

        dlg = wx.TextEntryDialog(self, _("How far apart are these copies height-wise? eg. 2in, 3cm, 50mm, 10%"), _("Enter Y Gap"), '')
        dlg.SetValue('')
        if dlg.ShowModal() == wx.ID_OK:
            try:
                y_distance = Length(dlg.GetValue()).value(ppi=1000.0, relative_length=self.device.bed_width * 39.3701)
            except ValueError:
                dlg.Destroy()
                return
            if isinstance(y_distance, Length):
                dlg.Destroy()
                return
        else:
            dlg.Destroy()
            return
        dlg.Destroy()
        self.operations.clear()
        self.preprocessor.commands = list()
        x_distance = int(x_distance)
        y_distance = int(y_distance)
        x_last = 0
        y_last = 0
        y_pos = 0
        x_pos = 0
        for j in range(rows):
            x_pos = 0
            for k in range(cols):
                x_offset = x_pos - x_last
                y_offset = y_pos - y_last
                self.operations.append(OperationPreprocessor.origin)
                if x_offset != 0 or y_offset != 0:
                    self.operations.append(OperationPreprocessor.offset(x_offset, y_offset))
                self.operations.extend(list(self._original_ops))
                x_last = x_pos
                y_last = y_pos
                x_pos += x_distance
            y_pos += y_distance
        if x_pos != 0 or y_pos != 0:
            self.operations.append(OperationPreprocessor.offset(-x_pos, -y_pos))
        self.refresh_lists()
        self.update_gui()

    def jobadd_physicalhome(self, event=None):
        self.operations.append(OperationPreprocessor.physicalhome)
        self.update_gui()

    def jobadd_home(self, event=None):
        self.operations.append(OperationPreprocessor.home)
        self.update_gui()

    def jobadd_origin(self, event=None):
        self.operations.append(OperationPreprocessor.origin)
        self.update_gui()

    def jobadd_wait(self, event=None):
        self.operations.append(OperationPreprocessor.wait)
        self.update_gui()

    def jobadd_beep(self, event=None):
        self.operations.append(OperationPreprocessor.beep)
        self.update_gui()

    def jobadd_interrupt(self, event=None):
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

    def on_close(self, event):
        if self.state == 5:
            event.Veto()
        else:
            self.state = 5
            self.device.close('window', self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, channel=None):
        self.device.close('window', self.name)
        self.Show()
        self.device.device_root.setting(bool, "auto_spooler", True)
        self.device.setting(bool, "rotary", False)
        self.device.setting(float, "scale_x", 1.0)
        self.device.setting(float, "scale_y", 1.0)
        self.device.setting(bool, "prehome", False)
        self.device.setting(bool, "autohome", False)
        self.device.setting(bool, "prephysicalhome", False)
        self.device.setting(bool, "autophysicalhome", False)
        self.device.setting(bool, "autoorigin", False)
        self.device.setting(bool, "autobeep", True)
        self.device.setting(bool, "autostart", True)
        self.device.setting(bool, "opt_rapid_between", True)
        self.device.setting(int, "opt_jog_mode", 0)
        self.device.listen('element_property_update', self.on_element_property_update)

        self.menu_prehome.Check(self.device.prehome)
        self.menu_autohome.Check(self.device.autohome)
        self.menu_prephysicalhome.Check(self.device.prephysicalhome)
        self.menu_autophysicalhome.Check(self.device.autophysicalhome)

        self.menu_autoorigin.Check(self.device.autoorigin)
        self.menu_autobeep.Check(self.device.autobeep)
        jog_mode = self.device.opt_jog_mode
        self.menu_jog.Check(False)
        # self.menu_jog2.Check(False)
        self.menu_jog3.Check(False)
        if jog_mode == 0:
            self.menu_jog.Check(True)
        elif jog_mode == 1:
            # self.menu_jog2.Check(True)
            pass
        else:
            self.menu_jog3.Check(True)
        self.menu_rapid.Check(self.device.opt_rapid_between)
        self.preprocessor.device = self.device
        self.refresh_lists()

    def refresh_lists(self):
        operations = list(self.operations)
        self.operations.clear()
        if self.device.prephysicalhome:
            if not self.device.rotary:
                self.jobadd_physicalhome()
            else:
                self.operations.append(_("Physical Home Before: Disabled (Rotary On)"))
        if self.device.prehome:
            if not self.device.rotary:
                self.jobadd_home()
            else:
                self.operations.append(_("Home Before: Disabled (Rotary On)"))
        for op in operations:
            try:
                if len(op) == 0:
                    continue
                if not op.output:
                    continue
                self.operations.append(copy(op))
            except TypeError:  # direct copy function
                self.operations.append(op)
        if self.device.autobeep:
            self.jobadd_beep()

        if self.device.autophysicalhome:
            if not self.device.rotary:
                self.jobadd_physicalhome()
            else:
                self.operations.append(_("Physical Home After: Disabled (Rotary On)"))
        if self.device.autohome:
            if not self.device.rotary:
                self.jobadd_home()
            else:
                self.operations.append(_("Home After: Disabled (Rotary On)"))
        if self.device.autoorigin:
            self.jobadd_origin()

        self.preprocessor.process(self.operations)
        self.update_gui()

    def finalize(self, channel=None):
        self.device.unlisten('element_property_update', self.on_element_property_update)
        try:
            self.Close()
        except RuntimeError:
            pass

    def shutdown(self, channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        # begin wxGlade: JobInfo.__set_properties
        self.SetTitle("Job")
        self.operations_listbox.SetToolTip(_("operation List"))
        self.commands_listbox.SetToolTip(_("Command List"))
        self.button_writer_control.SetToolTip(_("Start the Job"))
        self.button_writer_control.SetForegroundColour(wx.BLACK)

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
        sizer_3.Add(self.button_job_spooler, 0, wx.EXPAND, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_2)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_check_rapid(self, event):
        self.device.opt_rapid_between = self.menu_rapid.IsChecked()

    def on_check_jog(self, event):
        if self.menu_jog.IsChecked():
            self.device.opt_jog_mode = 0

    # def on_check_jog2(self, event):
    #     if self.menu_jog2.IsChecked():
    #         self.device.opt_jog_mode = 1

    def on_check_jog3(self, event):
        if self.menu_jog3.IsChecked():
            self.device.opt_jog_mode = 2

    def on_check_home_before(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.prehome = self.menu_prehome.IsChecked()
        self.operations = list(self._original_ops)
        self.preprocessor.commands = list()
        self.refresh_lists()

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.autohome = self.menu_autohome.IsChecked()
        self.operations = list(self._original_ops)
        self.preprocessor.commands = list()
        self.refresh_lists()

    def on_check_physicalhome_before(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.prephysicalhome = self.menu_prephysicalhome.IsChecked()
        self.operations = list(self._original_ops)
        self.preprocessor.commands = list()
        self.refresh_lists()

    def on_check_physicalhome_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.autophysicalhome = self.menu_autophysicalhome.IsChecked()
        self.operations = list(self._original_ops)
        self.preprocessor.commands = list()
        self.refresh_lists()

    def on_check_origin_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.autoorigin = self.menu_autoorigin.IsChecked()
        self.operations = list(self._original_ops)
        self.preprocessor.commands = list()
        self.refresh_lists()

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.device.autobeep = self.menu_autobeep.IsChecked()
        self.operations = list(self._original_ops)
        self.preprocessor.commands = list()
        self.refresh_lists()

    def on_button_job_spooler(self, event=None):  # wxGlade: JobInfo.<event_handler>
        if self.device.device_root.auto_spooler:
            self.device.open('window', "JobSpooler", self.GetParent())

    def on_button_start_job(self, event):  # wxGlade: JobInfo.<event_handler>
        if len(self.preprocessor.commands) == 0:
            self.device.spooler.jobs(self.operations)
            self.on_button_job_spooler()
            self.device.close('window', "JobInfo")
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
        if isinstance(obj, LaserOperation):
            self.device.open('window', "OperationProperty", self, obj)
        event.Skip()

    def on_listbox_commands_click(self, event):  # wxGlade: JobInfo.<event_handler>
        # print("Event handler 'on_listbox_commands_click' not implemented!")
        event.Skip()

    def on_listbox_commands_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        # print("Event handler 'on_listbox_commands_dclick' not implemented!")
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
