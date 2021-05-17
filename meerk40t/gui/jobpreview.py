import wx

from ..core.elements import LaserOperation
from ..svgelements import Length
from .icons import icons8_laser_beam_52
from .mwindow import MWindow

_ = wx.GetTranslation


class JobPreview(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(496, 573, *args, **kwds)
        if len(args) >= 4:
            plan_name = args[3]
        else:
            plan_name = 0
        self.plan_name = plan_name

        # Menu Bar
        self.preview_menu = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        wxglade_tmp_menu_sub = wx.Menu()
        self.preview_menu.menu_prehome = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY,
            "Home",
            "Automatically add a home command before all jobs",
            wx.ITEM_CHECK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_home_before,
            id=self.preview_menu.menu_prehome.GetId(),
        )
        self.preview_menu.menu_prephysicalhome = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY,
            "Physical Home",
            "Automatically add a physical home command before all jobs",
            wx.ITEM_CHECK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_physicalhome_before,
            id=self.preview_menu.menu_prephysicalhome.GetId(),
        )

        wxglade_tmp_menu.Append(wx.ID_ANY, "Before", wxglade_tmp_menu_sub, "")
        wxglade_tmp_menu_sub = wx.Menu()

        self.preview_menu.menu_autohome = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY,
            "Home",
            "Automatically add a home command after all jobs",
            wx.ITEM_CHECK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_home_after,
            id=self.preview_menu.menu_autohome.GetId(),
        )
        self.preview_menu.menu_autophysicalhome = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY,
            "Physical Home",
            "Automatically add a physical home command after all jobs",
            wx.ITEM_CHECK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_physicalhome_after,
            id=self.preview_menu.menu_autophysicalhome.GetId(),
        )
        self.preview_menu.menu_autoorigin = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY,
            "Return to Origin",
            "Automatically return to origin after a job",
            wx.ITEM_CHECK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_origin_after,
            id=self.preview_menu.menu_autoorigin.GetId(),
        )
        self.preview_menu.menu_autobeep = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY, "Beep", "Automatically add a beep after all jobs", wx.ITEM_CHECK
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_beep_after,
            id=self.preview_menu.menu_autobeep.GetId(),
        )
        self.preview_menu.menu_autointerrupt = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY,
            "Interrupt",
            "Automatically add an interrupt after all jobs",
            wx.ITEM_CHECK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_interrupt_after,
            id=self.preview_menu.menu_autointerrupt.GetId(),
        )

        self.preview_menu.menu_autounlock = wxglade_tmp_menu_sub.Append(
            wx.ID_ANY,
            "Unlock",
            "Automatically unlock the rail after all jobs",
            wx.ITEM_CHECK,
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_check_unlock_after,
            id=self.preview_menu.menu_autounlock.GetId(),
        )

        wxglade_tmp_menu.Append(wx.ID_ANY, "After", wxglade_tmp_menu_sub, "")
        self.preview_menu.Append(wxglade_tmp_menu, "Automatic")
        wxglade_tmp_menu = wx.Menu()
        self.preview_menu.menu_jobadd_home = wxglade_tmp_menu.Append(
            wx.ID_ANY, "Home", "Add a home"
        )
        self.Bind(
            wx.EVT_MENU, self.jobadd_home, id=self.preview_menu.menu_jobadd_home.GetId()
        )
        self.preview_menu.menu_jobadd_autophysicalhome = wxglade_tmp_menu.Append(
            wx.ID_ANY, "Physical Home", "Add a physicalhome"
        )
        self.Bind(
            wx.EVT_MENU,
            self.jobadd_physicalhome,
            id=self.preview_menu.menu_jobadd_autophysicalhome.GetId(),
        )
        self.preview_menu.menu_jobadd_wait = wxglade_tmp_menu.Append(
            wx.ID_ANY, "Wait", "Add a wait"
        )
        self.Bind(
            wx.EVT_MENU, self.jobadd_wait, id=self.preview_menu.menu_jobadd_wait.GetId()
        )
        self.preview_menu.menu_jobadd_beep = wxglade_tmp_menu.Append(
            wx.ID_ANY, "Beep", "Add a beep"
        )
        self.Bind(
            wx.EVT_MENU, self.jobadd_beep, id=self.preview_menu.menu_jobadd_beep.GetId()
        )
        self.preview_menu.menu_jobadd_interrupt = wxglade_tmp_menu.Append(
            wx.ID_ANY, "Interrupt", "Add an interrupt"
        )
        self.Bind(
            wx.EVT_MENU,
            self.jobadd_interrupt,
            id=self.preview_menu.menu_jobadd_interrupt.GetId(),
        )
        # self.preview_menu.menu_jobadd_command = wxglade_tmp_menu.Append(
        #     wx.ID_ANY, "Command", "Add a command"
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     self.jobadd_command,
        #     id=self.preview_menu.menu_jobadd_command.GetId(),
        # )
        self.preview_menu.Append(wxglade_tmp_menu, "Add")

        wxglade_tmp_menu = wx.Menu()
        # self.preview_menu.menu_jobchange_step_repeat = wxglade_tmp_menu.Append(
        #     wx.ID_ANY, "Step and Repeat", "Perform Step and Repeat"
        # )
        # self.Bind(
        #     wx.EVT_MENU,
        #     self.jobchange_step_repeat,
        #     id=self.preview_menu.menu_jobchange_step_repeat.GetId(),
        # )
        self.preview_menu.Append(wxglade_tmp_menu, _("Tools"))

        self.SetMenuBar(self.preview_menu)
        # Menu Bar end

        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        selected_spooler = self.context.root.active
        spools = [str(i) for i in self.context.match("device", suffix=True)]
        index = spools.index(selected_spooler)
        self.connected_name = spools[index]
        self.connected_spooler, self.connected_driver, self.connected_output = (
            None,
            None,
            None,
        )
        try:
            (
                self.connected_spooler,
                self.connected_driver,
                self.connected_output,
            ) = self.available_devices[index]
        except IndexError:
            for m in self.Children:
                if isinstance(m, wx.Window):
                    m.Disable()
        spools = [" -> ".join(map(repr, ad)) for ad in self.available_devices]

        self.combo_device = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(index)
        self.list_operations = wx.ListBox(self, wx.ID_ANY, choices=[])
        self.list_command = wx.ListBox(self, wx.ID_ANY, choices=[])
        self.slider_progress = wx.Slider(self, wx.ID_ANY, 10000, 0, 10000)
        self.panel_operation = wx.Panel(self, wx.ID_ANY)
        self.text_operation_name = wx.TextCtrl(
            self.panel_operation, wx.ID_ANY, "", style=wx.TE_READONLY
        )
        self.gauge_operation = wx.Gauge(self.panel_operation, wx.ID_ANY, 10)
        self.text_time_laser = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_travel = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.text_time_total = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.check_rapid_moves_between = wx.CheckBox(
            self, wx.ID_ANY, "Rapid Moves Between Objects"
        )
        self.check_reduce_travel_time = wx.CheckBox(
            self, wx.ID_ANY, "Reduce Travel Time"
        )
        self.check_cut_inner_first = wx.CheckBox(self, wx.ID_ANY, "Cut Inner First")
        self.check_reduce_direction_changes = wx.CheckBox(
            self, wx.ID_ANY, "Reduce Direction Changes"
        )
        self.check_remove_overlap_cuts = wx.CheckBox(
            self, wx.ID_ANY, "Remove Overlap Cuts"
        )
        self.button_start = wx.Button(self, wx.ID_ANY, "Start")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_COMBOBOX, self.on_combo_device, self.combo_device)
        self.Bind(wx.EVT_LISTBOX, self.on_listbox_operation_click, self.list_operations)
        self.Bind(
            wx.EVT_LISTBOX_DCLICK,
            self.on_listbox_operation_dclick,
            self.list_operations,
        )
        self.Bind(wx.EVT_LISTBOX, self.on_listbox_commands_click, self.list_command)
        self.Bind(
            wx.EVT_LISTBOX_DCLICK, self.on_listbox_commands_dclick, self.list_command
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_rapid_between, self.check_rapid_moves_between
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_reduce_travel, self.check_reduce_travel_time
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_inner_first, self.check_cut_inner_first
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_check_reduce_directions,
            self.check_reduce_direction_changes,
        )
        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_check_remove_overlap,
            self.check_remove_overlap_cuts,
        )

        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)
        # end wxGlade
        self.stage = 0

    def __set_properties(self):
        # begin wxGlade: Preview.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle("Preview Job")
        self.combo_device.SetToolTip(
            "Select the device to which to send the current job"
        )
        self.list_operations.SetToolTip("Operations being added to the current job")
        self.list_command.SetToolTip("Commands being applied to the current job")
        self.slider_progress.SetToolTip("Preview slider to set progress position")
        self.text_operation_name.SetToolTip("Current Operation Being Processed")
        self.gauge_operation.SetToolTip("Gauge of Operation Progress")
        self.text_time_laser.SetToolTip("Time Estimate: Lasering Time")
        self.text_time_travel.SetToolTip("Time Estimate: Traveling Time")
        self.text_time_total.SetToolTip("Time Estimate: Total Time")
        self.check_rapid_moves_between.SetToolTip(
            "Perform rapid moves between the objects"
        )
        self.check_reduce_travel_time.SetToolTip(
            "Reduce the travel time by optimizing the order of the elements"
        )
        self.check_cut_inner_first.SetToolTip(
            "Reorder elements to cut the inner elements first"
        )
        self.check_cut_inner_first.Enable(False)
        self.check_reduce_direction_changes.SetToolTip(
            "Reorder to reduce the number of sharp directional changes"
        )
        self.check_reduce_direction_changes.Enable(False)
        self.check_remove_overlap_cuts.SetToolTip("Remove elements of overlapped cuts")
        self.check_remove_overlap_cuts.Enable(False)
        self.button_start.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.button_start.SetFont(
            wx.Font(
                14,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.button_start.SetForegroundColour(wx.BLACK)
        self.button_start.SetToolTip("Start the Laser Job")
        self.button_start.SetBitmap(icons8_laser_beam_52.GetBitmap())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Preview.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_optimizations = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Optimizations"), wx.VERTICAL
        )
        sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        sizer_total_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Total Time"), wx.VERTICAL
        )
        sizer_travel_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Travel Time"), wx.VERTICAL
        )
        sizer_laser_time = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Laser Time"), wx.VERTICAL
        )
        sizer_operation = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_frame.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_main.Add(self.list_operations, 2, wx.EXPAND, 0)
        sizer_main.Add(self.list_command, 2, wx.EXPAND, 0)
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
        sizer_optimizations.Add(self.check_rapid_moves_between, 0, 0, 0)
        sizer_optimizations.Add(self.check_reduce_travel_time, 0, 0, 0)
        sizer_optimizations.Add(self.check_cut_inner_first, 0, 0, 0)
        sizer_optimizations.Add(self.check_reduce_direction_changes, 0, 0, 0)
        sizer_optimizations.Add(self.check_remove_overlap_cuts, 0, 0, 0)
        sizer_options.Add(sizer_optimizations, 2, wx.EXPAND, 0)
        sizer_options.Add(self.button_start, 3, wx.EXPAND, 0)
        sizer_frame.Add(sizer_options, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        self.Layout()
        # end wxGlade

    def on_check_home_before(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.prehome = self.preview_menu.menu_prehome.IsChecked()

    def on_check_home_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.autohome = self.preview_menu.menu_autohome.IsChecked()

    def on_check_physicalhome_before(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.prephysicalhome = (
            self.preview_menu.menu_prephysicalhome.IsChecked()
        )

    def on_check_physicalhome_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.autophysicalhome = (
            self.preview_menu.menu_autophysicalhome.IsChecked()
        )

    def on_check_origin_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.autoorigin = self.preview_menu.menu_autoorigin.IsChecked()

    def on_check_beep_after(self, event):  # wxGlade: JobInfo.<event_handler>
        self.context.autobeep = self.preview_menu.menu_autobeep.IsChecked()

    def on_check_interrupt_after(self, event):  # wxGlade: Preview.<event_handler>
        self.context.autointerrupt = self.preview_menu.menu_autointerrupt.IsChecked()

    def on_check_unlock_after(self, event):  # wxGlade: Preview.<event_handler>
        self.context.postunlock = self.preview_menu.menu_autounlock.IsChecked()

    def on_check_reduce_travel(self, event):  # wxGlade: Preview.<event_handler>
        self.context.opt_reduce_travel = self.check_reduce_travel_time.IsChecked()

    def on_check_inner_first(self, event):  # wxGlade: Preview.<event_handler>
        self.context.opt_inner_first = self.check_cut_inner_first.IsChecked()

    def on_check_reduce_directions(self, event):  # wxGlade: Preview.<event_handler>
        self.context.opt_reduce_directions = (
            self.check_reduce_direction_changes.IsChecked()
        )

    def on_check_remove_overlap(self, event):  # wxGlade: Preview.<event_handler>
        self.context.opt_remove_overlap = self.check_remove_overlap_cuts.IsChecked()

    def on_check_rapid_between(self, event):  # wxGlade: Preview.<event_handler>
        self.context.opt_rapid_between = self.check_rapid_moves_between.IsChecked()

    def jobchange_step_repeat(self, event=None):
        dlg = wx.TextEntryDialog(
            self, _("How many copies wide?"), _("Enter Columns"), ""
        )
        dlg.SetValue("5")

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

        dlg = wx.TextEntryDialog(self, _("How many copies high?"), _("Enter Rows"), "")
        dlg.SetValue("5")
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

        dlg = wx.TextEntryDialog(
            self,
            _("How far apart are these copies width-wise? eg. 2in, 3cm, 50mm, 10%"),
            _("Enter X Gap"),
            "",
        )
        dlg.SetValue("")
        bed_dim = self.context.get_context("/")
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                x_distance = Length(dlg.GetValue()).value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
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

        dlg = wx.TextEntryDialog(
            self,
            _("How far apart are these copies height-wise? eg. 2in, 3cm, 50mm, 10%"),
            _("Enter Y Gap"),
            "",
        )
        dlg.SetValue("")
        if dlg.ShowModal() == wx.ID_OK:
            try:
                y_distance = Length(dlg.GetValue()).value(
                    ppi=1000.0, relative_length=bed_dim.bed_width * 39.3701
                )
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
        self.context(
            "plan%s step_repeat %s %s %s %s"
            % (self.plan_name, cols, rows, x_distance, y_distance)
        )

    def jobadd_physicalhome(self, event=None):
        self.context("plan%s command -o physicalhome\n" % self.plan_name)
        self.update_gui()

    def jobadd_home(self, event=None):
        self.context("plan%s command -o home\n" % self.plan_name)
        self.update_gui()

    def jobadd_origin(self, event=None):
        self.context("plan%s command -o origin\n" % self.plan_name)
        self.update_gui()

    def jobadd_wait(self, event=None):
        self.context("plan%s command -o wait\n" % self.plan_name)
        self.update_gui()

    def jobadd_beep(self, event=None):
        self.context("plan%s command -o beep\n" % self.plan_name)
        self.update_gui()

    def jobadd_interrupt(self, event=None):
        self.context("plan%s command -o interrupt\n" % self.plan_name)
        self.update_gui()

    def jobadd_command(self, event=None):  # wxGlade: Preview.<event_handler>
        self.context("plan%s command -o console\n" % self.plan_name)
        self.update_gui()

    def on_combo_device(self, event):  # wxGlade: Preview.<event_handler>
        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        index = self.combo_device.GetSelection()
        (
            self.connected_spooler,
            self.connected_driver,
            self.connected_output,
        ) = self.available_devices[index]
        self.connected_name = [
            str(i) for i in self.context.match("device", suffix=True)
        ][index]

    def on_listbox_operation_click(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_listbox_operation_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        node_index = self.list_operations.GetSelection()
        if node_index == -1:
            return
        operations, original, commands, name = self.context.default_plan()
        obj = operations[node_index]
        if isinstance(obj, LaserOperation):
            self.context.open("window/OperationProperty", self, node=obj)
        event.Skip()

    def on_listbox_commands_click(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_listbox_commands_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_button_start(self, event):  # wxGlade: Preview.<event_handler>
        if self.stage == 0:
            self.context("plan%s copy preprocess\n" % self.plan_name)
            operations, original, commands, name = self.context.default_plan()
            if len(commands) == 0:
                self.context("plan%s validate\n" % self.plan_name)
        elif self.stage == 1:
            self.context("plan%s preprocess\n" % self.plan_name)
            operations, original, commands, name = self.context.default_plan()
            if len(commands) == 0:
                self.context("plan%s validate\n" % self.plan_name)
        elif self.stage == 2:
            self.context("plan%s validate\n" % self.plan_name)
        elif self.stage == 3:
            self.context("plan%s blob preopt\n" % self.plan_name)
        elif self.stage == 4:
            self.context("plan%s preopt\n" % self.plan_name)
        elif self.stage == 5:
            self.context("plan%s optimize\n" % self.plan_name)
        elif self.stage == 6:
            self.context("plan%s spool%s\n" % (self.plan_name, self.connected_name))
            self.Close()
        self.update_gui()

    def window_open(self):
        rotary_context = self.context.get_context("rotary/1")
        rotary_context.setting(bool, "rotary", False)
        rotary_context.setting(float, "scale_x", 1.0)
        rotary_context.setting(float, "scale_y", 1.0)
        self.context.setting(bool, "prehome", False)
        self.context.setting(bool, "autohome", False)
        self.context.setting(bool, "prephysicalhome", False)
        self.context.setting(bool, "autophysicalhome", False)
        self.context.setting(bool, "autoorigin", False)
        self.context.setting(bool, "autobeep", True)
        self.context.setting(bool, "autointerrupt", False)
        self.context.setting(bool, "postunlock", False)
        self.context.setting(bool, "opt_reduce_travel", True)
        self.context.setting(bool, "opt_inner_first", True)
        self.context.setting(bool, "opt_reduce_directions", False)
        self.context.setting(bool, "opt_remove_overlap", False)
        self.context.setting(bool, "opt_rapid_between", True)
        self.context.setting(int, "opt_jog_minimum", 127)
        self.context.setting(int, "opt_jog_mode", 0)

        self.context.listen("element_property_update", self.on_element_property_update)
        self.context.listen("plan", self.plan_update)

        self.preview_menu.menu_prehome.Check(bool(self.context.prehome))
        self.preview_menu.menu_autohome.Check(bool(self.context.autohome))
        self.preview_menu.menu_prephysicalhome.Check(bool(self.context.prephysicalhome))
        self.preview_menu.menu_autophysicalhome.Check(
            bool(self.context.autophysicalhome)
        )

        self.preview_menu.menu_autoorigin.Check(bool(self.context.autoorigin))
        self.preview_menu.menu_autobeep.Check(bool(self.context.autobeep))
        self.preview_menu.menu_autointerrupt.Check(bool(self.context.autointerrupt))
        self.preview_menu.menu_autounlock.Check(bool(self.context.postunlock))

        self.check_reduce_travel_time.SetValue(self.context.opt_reduce_travel)
        self.check_cut_inner_first.SetValue(self.context.opt_inner_first)
        self.check_reduce_direction_changes.SetValue(self.context.opt_reduce_directions)
        self.check_remove_overlap_cuts.SetValue(self.context.opt_remove_overlap)
        self.check_rapid_moves_between.SetValue(self.context.opt_rapid_between)

        self.update_gui()

    def window_close(self):
        self.context("plan%s clear\n" % self.plan_name)

        self.context.unlisten(
            "element_property_update", self.on_element_property_update
        )
        self.context.unlisten("plan", self.plan_update)

    def plan_update(self, origin, *message):
        plan_name, stage = message[0], message[1]
        if stage is not None:
            self.stage = stage
        self.plan_name = plan_name
        self.update_gui()

    def on_element_property_update(self, origin, *args):
        self.update_gui()

    def update_gui(self):
        def name_str(e):
            try:
                return e.__name__
            except AttributeError:
                return str(e)

        self.list_operations.Clear()
        self.list_command.Clear()
        operations, original, commands, plan_name = self.context.default_plan()
        if operations is not None and len(operations) != 0:
            self.list_operations.InsertItems([name_str(e) for e in operations], 0)
        if commands is not None and len(commands) != 0:
            self.list_command.InsertItems([name_str(e) for e in commands], 0)
        if self.stage == 0:
            self.button_start.SetLabelText(_("Copy"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 255, 102))
        elif self.stage == 1:
            self.button_start.SetLabelText(_("Preprocess Operations"))
            self.button_start.SetBackgroundColour(wx.Colour(102, 255, 255))
        elif self.stage == 2:
            self.button_start.SetLabelText(_("Validate"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 102, 255))
        elif self.stage == 3:
            self.button_start.SetLabelText(_("Blob"))
            self.button_start.SetBackgroundColour(wx.Colour(102, 102, 255))
        elif self.stage == 4:
            self.button_start.SetLabelText(_("Preprocess Optimizations"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 102, 102))
        elif self.stage == 5:
            self.button_start.SetLabelText(_("Optimize"))
            self.button_start.SetBackgroundColour(wx.Colour(102, 255, 102))
        elif self.stage == 6:
            self.button_start.SetLabelText(_("Spool"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.Refresh()
