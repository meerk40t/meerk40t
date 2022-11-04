import wx

from meerk40t.kernel import signal_listener

from .choicepropertypanel import ChoicePropertyPanel
from .icons import STD_ICON_SIZE, icons8_laser_beam_52
from .mwindow import MWindow
from .wxutils import disable_window

_ = wx.GetTranslation


class PlannerPanel(wx.Panel):
    def __init__(self, *args, context=None, plan_name=None, **kwargs):
        # begin wxGlade: ConsolePanel.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context

        self.plan_name = plan_name
        self.available_devices = list(self.context.kernel.services("device"))
        self.selected_device = self.context.device
        index = -1
        for i, s in enumerate(self.available_devices):
            if s is self.selected_device:
                index = i
                break
        spools = [s.label for s in self.available_devices]

        self.combo_device = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN
        )
        self.combo_device.SetSelection(index)
        self.list_operations = wx.ListBox(self, wx.ID_ANY, choices=[])
        self.list_command = wx.ListBox(self, wx.ID_ANY, choices=[])

        choices = self.context.lookup("choices/optimize") # [:7]
        self.panel_optimize = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling=False
        )
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
        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)
        self.stage = 0
        if index == -1:
            disable_window(self)

    def delegates(self):
        yield self.panel_optimize

    def __set_properties(self):
        # begin wxGlade: Preview.__set_properties

        self.combo_device.SetToolTip(
            _("Select the device to which to send the current job")
        )
        self.list_operations.SetToolTip(_("Operations being added to the current job"))
        self.list_command.SetToolTip(_("Commands being applied to the current job"))
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
        # sizer_optimizations = wx.StaticBoxSizer(
        #     wx.StaticBox(self, wx.ID_ANY, _("Optimizations")), wx.VERTICAL
        # )
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(self.list_operations, 2, wx.EXPAND, 0)
        sizer_main.Add(self.list_command, 2, wx.EXPAND, 0)

        sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_options.Add(self.panel_optimize, 1, 2, wx.EXPAND, 0)
        sizer_options.Add(self.button_start, 1, wx.EXPAND, 0)

        sizer_frame.Add(self.combo_device, 0, wx.EXPAND, 0)
        sizer_frame.Add(sizer_main, 1, wx.EXPAND, 0)
        sizer_frame.Add(sizer_options, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_frame)
        self.Layout()
        # end wxGlade

    def on_combo_device(self, event=None):  # wxGlade: Preview.<event_handler>
        index = self.combo_device.GetSelection()
        self.selected_device = self.available_devices[index]

    def on_listbox_operation_click(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_listbox_operation_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        node_index = self.list_operations.GetSelection()
        if node_index == -1:
            return
        cutplan = self.context.planner.default_plan
        obj = cutplan.plan[node_index]
        self.context.open("window/Properties", self)
        # self.context.kernel.activate_instance(obj)
        event.Skip()

    def on_listbox_commands_click(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_listbox_commands_dclick(self, event):  # wxGlade: JobInfo.<event_handler>
        event.Skip()

    def on_button_start(self, event=None):  # wxGlade: Preview.<event_handler>
        if self.stage == 0:
            with wx.BusyInfo(_("Preprocessing...")):
                self.context(f"plan{self.plan_name} copy preprocess\n")
                cutplan = self.context.planner.default_plan
                if len(cutplan.commands) == 0:
                    self.context(f"plan{self.plan_name} validate\n")
        elif self.stage == 1:
            with wx.BusyInfo(_("Determining validity of operations...")):
                self.context(f"plan{self.plan_name} preprocess\n")
                cutplan = self.context.planner.default_plan
                if len(cutplan.commands) == 0:
                    self.context(f"plan{self.plan_name} validate\n")
        elif self.stage == 2:
            with wx.BusyInfo(_("Validating operation data...")):
                self.context(f"plan{self.plan_name} validate\n")
        elif self.stage == 3:
            with wx.BusyInfo(_("Compiling cuts...")):
                self.context(f"plan{self.plan_name} blob preopt\n")
        elif self.stage == 4:
            with wx.BusyInfo(_("Determining optimizations to perform...")):
                self.context(f"plan{self.plan_name} preopt\n")
        elif self.stage == 5:
            with wx.BusyInfo(_("Performing Optimizations...")):
                self.context(f"plan{self.plan_name} optimize\n")
        elif self.stage == 6:
            with wx.BusyInfo(_("Sending data to laser...")):
                self.context(f"plan{self.plan_name} spool\n")
                if self.context.auto_spooler:
                    self.context("window open JobSpooler\n")
                try:
                    self.GetParent().Close()
                except (TypeError, AttributeError):
                    pass
        self.update_gui()

    def pane_show(self):
        # self.context.setting(bool, "opt_rasters_split", True)
        # TODO: OPT_RASTER_SPLIT
        cutplan = self.context.planner.default_plan
        self.Children[0].SetFocus()
        if len(cutplan.plan) == 0 and len(cutplan.commands) == 0:
            self.context(f"plan{self.plan_name} copy preprocess\n")

        self.update_gui()

    def pane_hide(self):
        self.context(f"plan{self.plan_name} clear\n")

    @signal_listener("plan")
    def plan_update(self, origin, *message):
        plan_name, stage = message[0], message[1]
        if stage is not None:
            self.stage = stage
        self.plan_name = plan_name
        self.update_gui()

    @signal_listener("element_property_reload")
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
        cutplan = self.context.planner.default_plan
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


class ExecuteJob(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(496, 573, *args, **kwds)

        if len(args) > 3:
            plan_name = args[3]
        else:
            plan_name = 0
        self.panel = PlannerPanel(
            self, wx.ID_ANY, context=self.context, plan_name=plan_name
        )
        # self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Execute Job"))

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/jobstart/ExecuteJob",
            {
                "label": _("Execute Job"),
                "icon": icons8_laser_beam_52,
                "tip": _("Execute the current laser project"),
                "action": lambda v: kernel.console("window toggle ExecuteJob 0\n"),
                "size": STD_ICON_SIZE,
                "priority": 2,
            },
        )

    def delegates(self):
        yield self.panel

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return ("Burning", "Execute Job")
