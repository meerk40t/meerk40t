import math

import wx

from meerk40t.kernel import signal_listener

from ..core.node.node import Node
from .choicepropertypanel import ChoicePropertyPanel
from .icons import STD_ICON_SIZE, icons8_laser_beam_52
from .mwindow import MWindow
from .wxutils import disable_window

_ = wx.GetTranslation

MILS_PER_MM = 39.3701


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

        choices = self.context.lookup("choices/optimize")[:7]
        self.panel_optimize = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=choices, scrolling = False
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

    def jobchange_return_to_operations(self, event=None):
        self.context("plan%s return clear\n" % (self.plan_name))

    def jobchange_step_repeat(self, event=None):
        elems = []
        cutplan = self.context.planner.default_plan
        for node in cutplan.plan:
            if node.type.startswith("op"):
                elems.extend(node.children)
        if len(elems) == 0:
            return

        dlg = wx.TextEntryDialog(
            self, _("How many copies wide?"), _("Enter Columns"), ""
        )

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
        if cols == 0:
            return

        dlg = wx.TextEntryDialog(self, _("How many copies high?"), _("Enter Rows"), "")
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
        if rows == 0:
            return

        bounds = Node.union_bounds(elems)

        try:
            width = math.ceil(bounds[2] - bounds[0])
            height = math.ceil(bounds[3] - bounds[1])
        except TypeError:
            width = None
            height = None
        if cols > 1 or width is None:
            dlg = wx.TextEntryDialog(
                self,
                _("How far apart are these copies width-wise? eg. 2in, 3cm, 50mm, 110%")
                + "\n\n"
                + _("This should be the item width + any gap."),
                _("Enter X Delta"),
                "",
            )

            name = self.context.units_name
            if width:
                width = self.context.device.length(
                    width,
                    unitless=self.context.device.native_scale_x,
                    new_units=name,
                    digits=3,
                )
            else:
                width = "%.2f%%" % (100.0 / rows)
            dlg.SetValue(str(width))
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    x_distance = self.context.device.length(
                        dlg.GetValue(),
                        0,
                        relative_length=width,
                        as_float=True,
                    )
                except ValueError:
                    dlg.Destroy()
                    return
            else:
                dlg.Destroy()
                return
            dlg.Destroy()
        else:
            x_distance = width

        if rows > 1:
            dlg = wx.TextEntryDialog(
                self,
                _(
                    "How far apart are these copies height-wise? eg. 2in, 3cm, 50mm, 110%"
                )
                + "\n\n"
                + _("This should be the item height + any gap."),
                _("Enter Y Delta"),
                "",
            )
            if height:
                height = self.context.device.length(
                    height,
                    unitless=self.context.device.native_scale_y,
                    new_units=name,
                    digits=3,
                )
            else:
                height = "%.2f%%" % (100.0 / cols)
            dlg.SetValue(str(height))
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    y_distance = self.context.device.length(
                        dlg.GetValue(),
                        1,
                        relative_length=height,
                        as_float=True,
                    )
                except ValueError:
                    dlg.Destroy()
                    return
            else:
                dlg.Destroy()
                return
            dlg.Destroy()
        else:
            y_distance = height

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
                self.context("plan%s copy preprocess\n" % self.plan_name)
                cutplan = self.context.planner.default_plan
                if len(cutplan.commands) == 0:
                    self.context("plan%s validate\n" % self.plan_name)
        elif self.stage == 1:
            with wx.BusyInfo(_("Determining validity of operations...")):
                self.context("plan%s preprocess\n" % self.plan_name)
                cutplan = self.context.planner.default_plan
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
                self.context("plan%s spool\n" % (self.plan_name))
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
            self.context("plan%s copy preprocess\n" % self.plan_name)

        self.update_gui()

    def pane_hide(self):
        self.context("plan%s clear\n" % self.plan_name)

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
        self.add_module_delegate(self.panel)
        self.panel.Bind(wx.EVT_RIGHT_DOWN, self.on_menu, self.panel)
        self.panel.list_operations.Bind(
            wx.EVT_RIGHT_DOWN, self.on_menu, self.panel.list_operations
        )
        self.panel.list_command.Bind(
            wx.EVT_RIGHT_DOWN, self.on_menu, self.panel.list_command
        )
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_laser_beam_52.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Execute Job"))

        # ==========
        # MENU BAR
        # ==========
        from platform import system as _sys

        if _sys() != "Darwin":
            self.preview_menu = wx.MenuBar()
            self.create_menu(self.preview_menu.Append)
            self.SetMenuBar(self.preview_menu)
        # ==========
        # MENUBAR END
        # ==========

    def on_menu(self, event):
        from .wxutils import create_menu_for_choices

        menu = create_menu_for_choices(self, self.context.lookup("choices/planner"))
        self.PopupMenu(menu)
        menu.Destroy()

    def create_menu(self, append):
        from .wxutils import create_menu_for_choices

        wx_menu = create_menu_for_choices(self, self.context.lookup("choices/planner"))
        append(wx_menu, _("Automatic"))

        # ==========
        # ADD MENU
        # ==========
        wx_menu = wx.Menu()
        append(wx_menu, _("Add"))

        self.Bind(
            wx.EVT_MENU,
            self.panel.jobadd_home,
            wx_menu.Append(wx.ID_ANY, _("Home"), _("Add a home")),
        )
        self.Bind(
            wx.EVT_MENU,
            self.panel.jobadd_physicalhome,
            wx_menu.Append(wx.ID_ANY, _("Physical Home"), _("Add a physicalhome")),
        )
        self.Bind(
            wx.EVT_MENU,
            self.panel.jobadd_beep,
            wx_menu.Append(wx.ID_ANY, _("Beep"), _("Add a beep")),
        )
        self.Bind(
            wx.EVT_MENU,
            self.panel.jobadd_interrupt,
            wx_menu.Append(wx.ID_ANY, _("Interrupt"), _("Add an interrupt")),
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
                self.panel.jobchange_return_to_operations,
                wx_menu.Append(
                    wx.ID_ANY,
                    _("Return to Operations"),
                    _("Return the current Plan to Operations"),
                ),
            )

        self.Bind(
            wx.EVT_MENU,
            self.panel.jobchange_step_repeat,
            wx_menu.Append(wx.ID_ANY, _("Step Repeat"), _("Execute Step Repeat")),
        )

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/project/ExecuteJob",
            {
                "label": _("Execute Job"),
                "icon": icons8_laser_beam_52,
                "tip": _("Execute the current laser project"),
                "action": lambda v: kernel.console("window toggle ExecuteJob 0\n"),
                "size": STD_ICON_SIZE,
            },
        )

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()
