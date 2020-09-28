import wx

from Kernel import Module
from LaserOperation import *
from icons import icons8_laser_beam_52
from OperationPreprocessor import OperationPreprocessor

_ = wx.GetTranslation


class JobPreview(wx.Frame, Module):
    def __init__(self, context, path, parent, ops, *args, **kwds):
        # begin wxGlade: Preview.__init__
        wx.Frame.__init__(self, parent, -1, "",
                          style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.TAB_TRAVERSAL)
        Module.__init__(self, context, path)
        self.SetSize((711, 629))
        self.spooler = context._kernel.active.spooler
        self.combo_device = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.list_operations = wx.ListBox(self, wx.ID_ANY, choices=[])
        self.panel_simulation = wx.Panel(self, wx.ID_ANY)
        self.slider_progress = wx.Slider(self, wx.ID_ANY, 10000, 0, 10000)
        self.panel_operation = wx.Panel(self, wx.ID_ANY)
        self.text_operation_name = wx.TextCtrl(self.panel_operation, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.gauge_operation = wx.Gauge(self.panel_operation, wx.ID_ANY, 10)
        self.text_time_laser = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_travel = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_total = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.check_reduce_travel_time = wx.CheckBox(self, wx.ID_ANY, "Reduce Travel Time")
        self.check_cut_inner_first = wx.CheckBox(self, wx.ID_ANY, "Cut Inner First")
        self.check_reduce_direction_changes = wx.CheckBox(self, wx.ID_ANY, "Reduce Direction Changes")
        self.check_remove_overlap_cuts = wx.CheckBox(self, wx.ID_ANY, "Remove Overlap Cuts")
        self.check_start_from_position = wx.CheckBox(self, wx.ID_ANY, "Start At Set Progress")
        self.button_move_to_position = wx.Button(self, wx.ID_ANY, "Move Laser To Set Position")
        self.check_rapid_moves_between = wx.CheckBox(self, wx.ID_ANY, "Rapid Moves Between Objects")
        self.button_start = wx.Button(self, wx.ID_ANY, "Start")

        # Menu Bar
        self.preview_menu = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu_sub = wx.Menu()
        self.preview_menu.menu_prehome = wxglade_tmp_menu_sub.Append(wx.ID_ANY, "Home",
                                                                      "Automatically add a home command before all jobs",
                                                                     wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_home_before, id=self.preview_menu.menu_prehome.GetId())
        wxglade_tmp_menu.Append(wx.ID_ANY, "Before", wxglade_tmp_menu_sub, "")
        wxglade_tmp_menu_sub = wx.Menu()
        self.preview_menu.menu_autohome = wxglade_tmp_menu_sub.Append(wx.ID_ANY, "Home",
                                                                       "Automatically add a home command after all jobs",
                                                                      wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_home_after, id=self.preview_menu.menu_autohome.GetId())
        self.preview_menu.menu_autoorigin = wxglade_tmp_menu_sub.Append(wx.ID_ANY, "Return to Origin",
                                                                         "Automatically return to origin after a job",
                                                                        wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_origin_after, id=self.preview_menu.menu_autoorigin.GetId())
        self.preview_menu.menu_autobeep = wxglade_tmp_menu_sub.Append(wx.ID_ANY, "Beep",
                                                                       "Automatically add a beep after all jobs",
                                                                      wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.on_check_beep_after, id=self.preview_menu.menu_autobeep.GetId())
        wxglade_tmp_menu.Append(wx.ID_ANY, "After", wxglade_tmp_menu_sub, "")
        self.preview_menu.Append(wxglade_tmp_menu, "Automatic")
        wxglade_tmp_menu = wx.Menu()
        self.preview_menu.menu_jobadd_home = wxglade_tmp_menu.Append(wx.ID_ANY, "Home", "Add a home")
        self.Bind(wx.EVT_MENU, self.jobadd_home, id=self.preview_menu.menu_jobadd_home.GetId())
        self.preview_menu.menu_jobadd_wait = wxglade_tmp_menu.Append(wx.ID_ANY, "Wait", "Add a wait")
        self.Bind(wx.EVT_MENU, self.jobadd_wait, id=self.preview_menu.menu_jobadd_wait.GetId())
        self.preview_menu.menu_jobadd_beep = wxglade_tmp_menu.Append(wx.ID_ANY, "Beep", "Add a beep")
        self.Bind(wx.EVT_MENU, self.jobadd_beep, id=self.preview_menu.menu_jobadd_beep.GetId())
        self.preview_menu.menu_jobadd_interrupt = wxglade_tmp_menu.Append(wx.ID_ANY, "Interrupt", "Add an interrupt")
        self.Bind(wx.EVT_MENU, self.jobadd_interrupt, id=self.preview_menu.menu_jobadd_interrupt.GetId())
        self.preview_menu.menu_jobadd_command = wxglade_tmp_menu.Append(wx.ID_ANY, "System Command",
                                                                         "Add a system command")
        self.Bind(wx.EVT_MENU, self.jobadd_command, id=self.preview_menu.menu_jobadd_command.GetId())
        self.preview_menu.Append(wxglade_tmp_menu, "Add")
        self.SetMenuBar(self.preview_menu)
        # Menu Bar end

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_reduce_travel, self.check_reduce_travel_time)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_inner_first, self.check_cut_inner_first)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_reduce_directions, self.check_reduce_direction_changes)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_remove_overlap, self.check_remove_overlap_cuts)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_start_from_position, self.check_start_from_position)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_rapid_between, self.check_rapid_moves_between)
        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)

        self.Bind(wx.EVT_LISTBOX, self.on_listbox_operation_click, self.list_operations)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_listbox_operation_dclick, self.list_operations)
        # end wxGlade
        self.preprocessor = OperationPreprocessor()
        if not isinstance(ops, list):
            ops = [ops]
        self.operations = ops

    def __set_properties(self):
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle("Preview Job")
        self.combo_device.SetToolTip("Select the device to which to send the current job")
        self.list_operations.SetToolTip("Operations being added to the current job")
        self.panel_simulation.SetToolTip("Job Simulation")
        self.slider_progress.SetToolTip("Preview slider to set progress position")
        self.text_operation_name.SetToolTip("Current Operation Being Processed")
        self.gauge_operation.SetToolTip("Gauge of Operation Progress")
        self.text_time_laser.SetToolTip("Time Estimate: Lasering Time")
        self.text_time_travel.SetToolTip("Time Estimate: Traveling Time")
        self.text_time_total.SetToolTip("Time Estimate: Total Time")
        self.check_reduce_travel_time.SetToolTip("Reduce the travel time by optimizing the order of the elements")
        self.check_reduce_travel_time.SetValue(1)
        self.check_cut_inner_first.SetToolTip("Reorder elements to cut the inner elements first")
        self.check_cut_inner_first.SetValue(1)
        self.check_reduce_direction_changes.SetToolTip("Reorder to reduce the number of sharp directional changes")
        self.check_reduce_direction_changes.Enable(False)
        self.check_remove_overlap_cuts.SetToolTip("Remove elements of overlapped cuts")
        self.check_remove_overlap_cuts.Enable(False)
        self.check_start_from_position.SetToolTip("Start the job at the set amount of progress")
        self.button_move_to_position.SetToolTip("Move the laser to the current position selected within this job")
        self.check_rapid_moves_between.SetToolTip("Perform rapid moves between the objects")
        self.button_start.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_start.SetFont(
            wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, "Segoe UI"))
        self.button_start.SetToolTip("Start the Laser Job")
        self.button_start.SetBitmap(icons8_laser_beam_52.GetBitmap())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Preview.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_advanced = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Advanced"), wx.VERTICAL)
        sizer_optimizations = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Optimizations"), wx.VERTICAL)
        sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_time = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Total Time"), wx.VERTICAL)
        sizer_travel_time = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Travel Time"), wx.VERTICAL)
        sizer_laser_time = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Laser Time"), wx.VERTICAL)
        sizer_operation = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_1.Add(self.list_operations, 2, wx.EXPAND, 0)
        sizer_main.Add(sizer_1, 2, wx.EXPAND, 0)
        sizer_main.Add(self.panel_simulation, 7, wx.EXPAND, 0)
        sizer_frame.Add(sizer_main, 1, wx.EXPAND, 0)
        sizer_frame.Add(self.slider_progress, 0, wx.EXPAND, 0)
        sizer_operation.Add(self.text_operation_name, 2, 0, 0)
        sizer_operation.Add(self.gauge_operation, 7, wx.EXPAND, 0)
        self.panel_operation.SetSizer(sizer_operation)
        sizer_frame.Add(self.panel_operation, 0, wx.EXPAND, 0)
        sizer_laser_time.Add(self.text_time_laser, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_laser_time, 1, wx.EXPAND, 0)
        sizer_travel_time.Add(self.text_time_travel, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_travel_time, 1, wx.EXPAND, 0)
        sizer_total_time.Add(self.text_time_total, 0, wx.EXPAND, 0)
        sizer_time.Add(sizer_total_time, 1, wx.EXPAND, 0)
        sizer_frame.Add(sizer_time, 0, wx.EXPAND, 0)
        sizer_optimizations.Add(self.check_reduce_travel_time, 0, 0, 0)
        sizer_optimizations.Add(self.check_cut_inner_first, 0, 0, 0)
        sizer_optimizations.Add(self.check_reduce_direction_changes, 0, 0, 0)
        sizer_optimizations.Add(self.check_remove_overlap_cuts, 0, 0, 0)
        sizer_options.Add(sizer_optimizations, 5, wx.EXPAND, 0)
        sizer_advanced.Add(self.check_start_from_position, 0, 0, 0)
        sizer_advanced.Add(self.button_move_to_position, 0, 0, 0)
        sizer_advanced.Add(self.check_rapid_moves_between, 0, 0, 0)
        sizer_options.Add(sizer_advanced, 5, 0, 0)
        sizer_options.Add(self.button_start, 3, wx.EXPAND, 0)
        sizer_frame.Add(sizer_options, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        self.Layout()
        # end wxGlade

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

    def jobadd_command(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'jobadd_command' not implemented!")
        event.Skip()

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
            self.context.close(self.name)
            event.Skip()  # Call destroy as regular.

    def initialize(self, channel=None):
        self.context.close(self.name)
        self.Show()
        self.context.setting(bool, "rotary", False)
        self.context.setting(float, "scale_x", 1.0)
        self.context.setting(float, "scale_y", 1.0)
        self.context.setting(bool, "prehome", False)
        self.context.setting(bool, "autohome", False)
        self.context.setting(bool, "autoorigin", False)
        self.context.setting(bool, "autobeep", True)
        self.context.listen('element_property_update', self.on_element_property_update)

        self.preview_menu.menu_prehome.Check(self.context.prehome)
        self.preview_menu.menu_autohome.Check(self.context.autohome)
        self.preview_menu.menu_autoorigin.Check(self.context.autoorigin)
        self.preview_menu.menu_autobeep.Check(self.context.autobeep)
        self.preprocessor.device = self.context
        operations = list(self.operations)
        self.operations.clear()
        if self.context.prehome:
            if not self.context.rotary:
                self.jobadd_home()
            else:
                self.operations.append(_("Home Before: Disabled (Rotary On)"))
        for op in operations:
            if len(op) == 0:
                continue
            if not op.output:
                continue
            self.operations.append(copy(op))
        if self.context.autobeep:
            self.jobadd_beep()

        if self.context.autohome:
            if not self.context.rotary:
                self.jobadd_home()
            else:
                self.operations.append(_("Home After: Disabled (Rotary On)"))
        if self.context.autoorigin:
            self.jobadd_origin()

        self.preprocessor.process(self.operations)
        self.update_gui()

    def finalize(self, channel=None):
        self.context.unlisten('element_property_update', self.on_element_property_update)
        try:
            self.Close()
        except RuntimeError:
            pass

    def shutdown(self, channel=None):
        try:
            self.Close()
        except RuntimeError:
            pass

    def on_combo_device(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'on_combo_device' not implemented!")
        event.Skip()

    def on_check_home_before(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.prehome = self.preview_menu.menu_prehome.IsChecked()

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.autohome = self.preview_menu.menu_autohome.IsChecked()

    def on_check_origin_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.autoorigin = self.preview_menu.menu_autoorigin.IsChecked()

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.autobeep = self.preview_menu.menu_autobeep.IsChecked()

    def on_button_start(self, event):  # wxGlade: Preview.<event_handler>
        if len(self.preprocessor.commands) == 0:
            self.spooler.jobs(self.operations)
            self.context.close(self.name)
        else:
            self.preprocessor.execute()
            self.update_gui()

    def on_listbox_operation_click(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_listbox_operation_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        node_index = self.list_operations.GetSelection()
        if node_index == -1:
            return
        obj = self.operations[node_index]
        if isinstance(obj, LaserOperation):
            self.context.open('window/OperationProperty', self, obj)
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

        self.list_operations.Clear()
        operations = self.operations
        commands = self.preprocessor.commands
        if operations is not None and len(operations) != 0:
            self.list_operations.InsertItems([name_str(e) for e in self.operations], 0)
        if commands is not None and len(commands) != 0:
            # self.commands_listbox.InsertItems([name_str(e) for e in self.preprocessor.commands], 0)
            self.button_start.SetLabelText(_("Execute Commands"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 255, 102))
        else:
            self.button_start.SetLabelText(_("Start Job"))
            self.button_start.SetBackgroundColour(wx.Colour(102, 255, 102))
        self.Refresh()

    def on_check_reduce_travel(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'on_check_reduce_travel' not implemented!")
        event.Skip()

    def on_check_inner_first(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'on_check_inner_first' not implemented!")
        event.Skip()

    def on_check_reduce_directions(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'on_check_reduce_directions' not implemented!")
        event.Skip()

    def on_check_remove_overlap(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'on_check_remove_overlap' not implemented!")
        event.Skip()

    def on_check_start_from_position(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'on_check_start_from_position' not implemented!")
        event.Skip()

    def on_check_rapid_between(self, event):  # wxGlade: Preview.<event_handler>
        print("Event handler 'on_check_rapid_between' not implemented!")
        event.Skip()
