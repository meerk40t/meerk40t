import math

import wx

from ..core.elements import LaserOperation
from ..svgelements import Length
from .icons import icons8_laser_beam_52
from .mwindow import MWindow

_ = wx.GetTranslation

MILS_PER_MM = 39.3701


class ExecuteJob(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(496, 573, *args, **kwds)
        if len(args) >= 4:
            plan_name = args[3]
        else:
            plan_name = 0
        self.plan_name = plan_name

        # ==========
        # MENU BAR
        # ==========
        self.preview_menu = wx.MenuBar()
        self.create_menu(self.preview_menu.Append)
        self.SetMenuBar(self.preview_menu)
        # ==========
        # MENUBAR END
        # ==========

        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        selected_spooler = self.context.root.active
        spools = [str(i) for i in self.context.match("device", suffix=True)]
        try:
            index = spools.index(selected_spooler)
        except ValueError:
            index = 0
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

        self.panel_operation = wx.Panel(self, wx.ID_ANY)

        self.check_rapid_moves_between = wx.CheckBox(
            self, wx.ID_ANY, _("Rapid Moves Between Objects")
        )
        self.check_reduce_travel_time = wx.CheckBox(
            self, wx.ID_ANY, _("Reduce Travel Time")
        )

        self.check_merge_passes = wx.CheckBox(self, wx.ID_ANY, _("Merge Passes"))
        self.check_merge_ops = wx.CheckBox(self, wx.ID_ANY, _("Merge Operations"))
        self.check_cut_inner_first = wx.CheckBox(self, wx.ID_ANY, _("Cut Inner First"))
        # self.check_reduce_direction_changes = wx.CheckBox(
        #     self, wx.ID_ANY, _("Reduce Direction Changes")
        # )
        # self.check_remove_overlap_cuts = wx.CheckBox(
        #     self, wx.ID_ANY, _("Remove Overlap Cuts")
        # )
        self.button_start = wx.Button(self, wx.ID_ANY, _("Start"))

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
        self.Bind(wx.EVT_CHECKBOX, self.on_check_merge_passes, self.check_merge_passes)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_merge_ops, self.check_merge_ops)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_rapid_between, self.check_rapid_moves_between
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_reduce_travel, self.check_reduce_travel_time
        )
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_inner_first, self.check_cut_inner_first
        )
        # self.Bind(
        #     wx.EVT_CHECKBOX,
        #     self.on_check_reduce_directions,
        #     self.check_reduce_direction_changes,
        # )
        # self.Bind(
        #     wx.EVT_CHECKBOX,
        #     self.on_check_remove_overlap,
        #     self.check_remove_overlap_cuts,
        # )
        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)
        self.stage = 0

    def __set_properties(self):
        # begin wxGlade: Preview.__set_properties
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Execute Job"))
        self.combo_device.SetToolTip(
            _("Select the device to which to send the current job")
        )
        self.list_operations.SetToolTip(_("Operations being added to the current job"))
        self.list_command.SetToolTip(_("Commands being applied to the current job"))
        # self.slider_progress.SetToolTip(_("Preview slider to set progress position"))
        # self.text_operation_name.SetToolTip(_("Current Operation Being Processed"))
        # self.gauge_operation.SetToolTip(_("Gauge of Operation Progress"))
        # self.text_time_laser.SetToolTip(_("Time Estimate: Lasering Time"))
        # self.text_time_travel.SetToolTip(_("Time Estimate: Traveling Time"))
        # self.text_time_total.SetToolTip(_("Time Estimate: Total Time"))
        self.check_merge_passes.SetToolTip(
            _("Combine passes into the same optimization")
        )
        self.check_merge_ops.SetToolTip(
            _("Combine operations into the same optimization")
        )
        self.check_rapid_moves_between.SetToolTip(
            _(
                "Travel between objects (laser off) at the default/rapid speed rather than at the current laser-on speed"
            )
        )
        self.check_reduce_travel_time.SetToolTip(
            _("Reduce the travel time by optimizing the order of the elements")
        )
        self.check_cut_inner_first.SetToolTip(
            _(
                "Ensure that inside burns are done before an outside cut which might result in the cut piece shifting or dropping out of the material, while still requiring additonal cuts."
            )
        )
        # self.check_reduce_direction_changes.SetToolTip(
        #     _("Reorder to reduce the number of sharp directional changes")
        # )
        # self.check_reduce_direction_changes.Hide()
        # self.check_remove_overlap_cuts.SetToolTip(
        #     _("Remove elements of overlapped cuts")
        # )
        # self.check_remove_overlap_cuts.Hide()
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
        self.button_start.SetBitmap(icons8_laser_beam_52.GetBitmap())
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Preview.__do_layout
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_optimizations = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Optimizations")), wx.VERTICAL
        )
        # sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        # sizer_total_time = wx.StaticBoxSizer(
        #     wx.StaticBox(self, wx.ID_ANY, "Total Time"), wx.VERTICAL
        # )
        # sizer_travel_time = wx.StaticBoxSizer(
        #     wx.StaticBox(self, wx.ID_ANY, "Travel Time"), wx.VERTICAL
        # )
        # sizer_laser_time = wx.StaticBoxSizer(
        #     wx.StaticBox(self, wx.ID_ANY, "Laser Time"), wx.VERTICAL
        # )
        # sizer_operation = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_frame.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_main.Add(self.list_operations, 2, wx.EXPAND, 0)
        sizer_main.Add(self.list_command, 2, wx.EXPAND, 0)
        sizer_frame.Add(sizer_main, 1, wx.EXPAND, 0)
        # sizer_frame.Add(self.slider_progress, 0, wx.EXPAND, 0)
        # sizer_operation.Add(self.text_operation_name, 2, 0, 0)
        # sizer_operation.Add(self.gauge_operation, 7, wx.EXPAND, 0)
        # self.panel_operation.SetSizer(sizer_operation)
        sizer_frame.Add(self.panel_operation, 0, wx.EXPAND, 0)
        # sizer_laser_time.Add(self.text_time_laser, 0, wx.EXPAND, 0)
        # sizer_time.Add(sizer_laser_time, 1, wx.EXPAND, 0)
        # sizer_travel_time.Add(self.text_time_travel, 0, wx.EXPAND, 0)
        # sizer_time.Add(sizer_travel_time, 1, wx.EXPAND, 0)
        # sizer_total_time.Add(self.text_time_total, 0, wx.EXPAND, 0)
        # sizer_time.Add(sizer_total_time, 1, wx.EXPAND, 0)
        # sizer_frame.Add(sizer_time, 0, wx.EXPAND, 0)
        sizer_optimizations.Add(self.check_rapid_moves_between, 0, 0, 0)
        sizer_optimizations.Add(self.check_reduce_travel_time, 0, 0, 0)
        sizer_optimizations.Add(self.check_merge_ops, 0, 0, 0)
        sizer_optimizations.Add(self.check_merge_passes, 0, 0, 0)
        sizer_optimizations.Add(self.check_cut_inner_first, 0, 0, 0)
        # sizer_optimizations.Add(self.check_reduce_direction_changes, 0, 0, 0)
        # sizer_optimizations.Add(self.check_remove_overlap_cuts, 0, 0, 0)
        sizer_options.Add(sizer_optimizations, 2, wx.EXPAND, 0)
        sizer_options.Add(self.button_start, 3, wx.EXPAND, 0)
        sizer_frame.Add(sizer_options, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_frame)
        self.Layout()
        # end wxGlade


    def create_menu(self, append):
        from .wxutils import create_menu_for_choices
        wx_menu = create_menu_for_choices(self, self.context.registered["choices/planner"])
        append(wx_menu, _("Automatic"))

        # ==========
        # ADD MENU
        # ==========
        wx_menu = wx.Menu()
        append(wx_menu, _("Add"))

        self.Bind(
            wx.EVT_MENU, self.jobadd_home, wx_menu.Append(
            wx.ID_ANY, _("Home"), _("Add a home")
        )
        )
        self.Bind(
            wx.EVT_MENU,
            self.jobadd_physicalhome,
            wx_menu.Append(
                wx.ID_ANY, _("Physical Home"), _("Add a physicalhome")
            )
        )
        self.Bind(
            wx.EVT_MENU, self.jobadd_wait, wx_menu.Append(
            wx.ID_ANY, _("Wait"), _("Add a wait")
        )
        )
        self.Bind(
            wx.EVT_MENU, self.jobadd_beep, wx_menu.Append(
            wx.ID_ANY, _("Beep"), _("Add a beep")
        )
        )
        self.Bind(
            wx.EVT_MENU,
            self.jobadd_interrupt,
            wx_menu.Append(
                wx.ID_ANY, _("Interrupt"), _("Add an interrupt")
            )
        )


        # ==========
        # Tools Menu
        # ==========
        wx_menu = wx.Menu()
        append(wx_menu, _("Tools"))

        self.context.setting(bool, "developer_mode", False)
        if self.context.developer_mode:
            self.Bind(
                wx.EVT_MENU,
                self.jobchange_return_to_operations,
                wx_menu.Append(
                    wx.ID_ANY,
                    _("Return to Operations"),
                    _("Return the current Plan to Operations"),
                )
            )

        self.Bind(
            wx.EVT_MENU,
            self.jobchange_step_repeat,
            wx_menu.Append(
                wx.ID_ANY, _("Step Repeat"), _("Execute Step Repeat")
            )
        )

    def on_check_reduce_travel(self, event=None):  # wxGlade: Preview.<event_handler>
        self.context.opt_reduce_travel = self.check_reduce_travel_time.IsChecked()
        self.check_merge_ops.Enable(self.context.opt_reduce_travel)
        self.check_merge_passes.Enable(self.context.opt_reduce_travel)

    def on_check_inner_first(self, event=None):  # wxGlade: Preview.<event_handler>
        self.context.opt_inner_first = self.check_cut_inner_first.IsChecked()

    # def on_check_reduce_directions(
    #     self, event=None
    # ):  # wxGlade: Preview.<event_handler>
    #     self.context.opt_reduce_directions = (
    #         self.check_reduce_direction_changes.IsChecked()
    #     )
    #
    # def on_check_remove_overlap(self, event=None):  # wxGlade: Preview.<event_handler>
    #     self.context.opt_remove_overlap = self.check_remove_overlap_cuts.IsChecked()

    def on_check_merge_ops(self, event=None):
        self.context.opt_merge_ops = self.check_merge_ops.IsChecked()

    def on_check_merge_passes(self, event=None):
        self.context.opt_merge_passes = self.check_merge_passes.IsChecked()

    def on_check_rapid_between(self, event=None):  # wxGlade: Preview.<event_handler>
        self.context.opt_rapid_between = self.check_rapid_moves_between.IsChecked()

    def jobchange_return_to_operations(self, event=None):
        self.context("plan%s return clear\n" % (self.plan_name))

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
        try:
            bounds = self.context.elements._emphasized_bounds
            width = math.ceil(bounds[2] - bounds[0])
            height = math.ceil(bounds[3] - bounds[1])
        except Exception:
            width = None
            height = None

        dlg = wx.TextEntryDialog(
            self,
            _("How far apart are these copies width-wise? eg. 2in, 3cm, 50mm, 10%"),
            _("Enter X Gap"),
            "",
        )
        dlg.SetValue(str(width) if width is not None else "%f%%" % (100.0 / cols))
        bed_dim = self.context.root
        bed_dim.setting(int, "bed_width", 310)
        bed_dim.setting(int, "bed_height", 210)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                x_distance = Length(dlg.GetValue()).value(
                    ppi=1000.0,
                    relative_length=width
                    if width is not None
                    else bed_dim.bed_width * MILS_PER_MM,
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
        dlg.SetValue(str(height) if height is not None else "%f%%" % (100.0 / rows))
        if dlg.ShowModal() == wx.ID_OK:
            try:
                y_distance = Length(dlg.GetValue()).value(
                    ppi=1000.0,
                    relative_length=height
                    if height is not None
                    else bed_dim.bed_height * MILS_PER_MM,
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
            "plan%s step_repeat %s %s %s %s\n"
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

    def on_combo_device(self, event=None):  # wxGlade: Preview.<event_handler>
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
        cutplan = self.context.default_plan()
        obj = cutplan.plan[node_index]
        if isinstance(obj, LaserOperation):
            self.context.open("window/OperationProperty", self, node=obj)
        event.Skip()

    def on_listbox_commands_click(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_listbox_commands_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_button_start(self, event=None):  # wxGlade: Preview.<event_handler>
        if self.stage == 0:
            with wx.BusyInfo(_("Preprocessing...")):
                self.context("plan%s copy preprocess\n" % self.plan_name)
                cutplan = self.context.default_plan()
                if len(cutplan.commands) == 0:
                    self.context("plan%s validate\n" % self.plan_name)
        elif self.stage == 1:
            with wx.BusyInfo(_("Determining validity of operations...")):
                self.context("plan%s preprocess\n" % self.plan_name)
                cutplan = self.context.default_plan()
                if len(cutplan.commands) == 0:
                    self.context("plan%s validate\n" % self.plan_name)
        elif self.stage == 2:
            with wx.BusyInfo(_("Validating operation data...")):
                self.context("plan%s validate\n" % self.plan_name)
        elif self.stage == 3:
            with wx.BusyInfo(_("Compiling cuts...")):
                self.context("plan%s blob preopt\n" % self.plan_name)
        elif self.stage == 4:
            with wx.BusyInfo(_("Determining optimizations to perform...")):
                self.context("plan%s preopt\n" % self.plan_name)
        elif self.stage == 5:
            with wx.BusyInfo(_("Performing Optimizations...")):
                self.context("plan%s optimize\n" % self.plan_name)
        elif self.stage == 6:
            with wx.BusyInfo(_("Sending data to laser...")):
                self.context("plan%s spool%s\n" % (self.plan_name, self.connected_name))
                if self.context.auto_spooler:
                    self.context("window open JobSpooler\n")
                self.Close()
        self.update_gui()

    def window_open(self):
        rotary_context = self.context.get_context("rotary/1")
        rotary_context.setting(bool, "rotary", False)
        rotary_context.setting(float, "scale_x", 1.0)
        rotary_context.setting(float, "scale_y", 1.0)
        self.context.setting(int, "opt_closed_distance", 15)
        self.context.setting(bool, "opt_merge_passes", False)
        self.context.setting(bool, "opt_merge_ops", False)
        self.context.setting(bool, "opt_reduce_travel", True)
        self.context.setting(bool, "opt_inner_first", True)
        self.context.setting(bool, "opt_reduce_directions", False)
        self.context.setting(bool, "opt_remove_overlap", False)
        self.context.setting(bool, "opt_rapid_between", True)
        self.context.setting(int, "opt_jog_minimum", 256)
        self.context.setting(int, "opt_jog_mode", 0)

        self.context.listen("element_property_reload", self.on_element_property_update)
        self.context.listen("plan", self.plan_update)

        self.check_rapid_moves_between.SetValue(self.context.opt_rapid_between)
        self.check_reduce_travel_time.SetValue(self.context.opt_reduce_travel)
        self.check_merge_passes.SetValue(self.context.opt_merge_passes)
        self.check_merge_ops.SetValue(self.context.opt_merge_ops)
        self.check_merge_ops.Enable(self.context.opt_reduce_travel)
        self.check_merge_passes.Enable(self.context.opt_reduce_travel)
        self.check_cut_inner_first.SetValue(self.context.opt_inner_first)
        # self.check_reduce_direction_changes.SetValue(self.context.opt_reduce_directions)
        # self.check_remove_overlap_cuts.SetValue(self.context.opt_remove_overlap)

        cutplan = self.context.default_plan()
        if len(cutplan.plan) == 0 and len(cutplan.commands) == 0:
            self.context("plan%s copy preprocess\n" % self.plan_name)

        self.update_gui()

    def window_close(self):
        self.context("plan%s clear\n" % self.plan_name)

        self.context.unlisten(
            "element_property_reload", self.on_element_property_update
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
        cutplan = self.context.default_plan()
        if cutplan.plan is not None and len(cutplan.plan) != 0:
            self.list_operations.InsertItems([name_str(e) for e in cutplan.plan], 0)
        if cutplan.commands is not None and len(cutplan.commands) != 0:
            self.list_command.InsertItems([name_str(e) for e in cutplan.commands], 0)
        if self.stage == 0:
            self.button_start.SetLabelText(_("Copy"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 255, 102))
            self.button_start.SetToolTip(_("Copy Operations from Tree Operations"))
        elif self.stage == 1:
            self.button_start.SetLabelText(_("Preprocess Operations"))
            self.button_start.SetBackgroundColour(wx.Colour(102, 255, 255))
            self.button_start.SetToolTip(
                _("Determine what needs to be done validate these operations.")
            )
        elif self.stage == 2:
            self.button_start.SetLabelText(_("Validate"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 102, 255))
            self.button_start.SetToolTip(
                _("Run the commands to make these operations valid.")
            )
        elif self.stage == 3:
            self.button_start.SetLabelText(_("Blob"))
            self.button_start.SetBackgroundColour(wx.Colour(102, 102, 255))
            self.button_start.SetToolTip(_("Turn this set of operations into Cutcode"))
        elif self.stage == 4:
            self.button_start.SetLabelText(_("Preprocess Optimizations"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 102, 102))
            self.button_start.SetToolTip(
                _("Determine what needs to be done to optimize this cutcode.")
            )
        elif self.stage == 5:
            self.button_start.SetLabelText(_("Optimize"))
            self.button_start.SetBackgroundColour(wx.Colour(102, 255, 102))
            self.button_start.SetToolTip(_("Run the commands to optimize this cutcode"))
        elif self.stage == 6:
            self.button_start.SetLabelText(_("Spool"))
            self.button_start.SetBackgroundColour(wx.Colour(255, 255, 255))
            self.button_start.SetToolTip(_("Send this data to the spooler"))
        self.Refresh()
