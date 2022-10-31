import wx
from wx import aui

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import (
    icons8_delete_50,
    icons8_emergency_stop_button_50,
    icons8_gas_industry_50,
    icons8_goal_50,
    icons8_laser_beam_hazard2_50,
    icons8_pause_50,
    icons8_pentagon_50,
    icons8_save_50,
)
from meerk40t.gui.wxutils import disable_window
from meerk40t.kernel import lookup_listener, signal_listener

_ = wx.GetTranslation


def register_panel_laser(window, context):
    laser_panel = LaserPanel(window, wx.ID_ANY, context=context)
    optimize_panel = ChoicePropertyPanel(
        window, wx.ID_ANY, context=context, choices="optimize"
    )
    notebook = wx.aui.AuiNotebook(
        window,
        -1,
        style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
        | wx.aui.AUI_NB_SCROLL_BUTTONS
        | wx.aui.AUI_NB_TAB_SPLIT
        | wx.aui.AUI_NB_TAB_MOVE
        | wx.aui.AUI_NB_BOTTOM,
    )
    pane = (
        aui.AuiPaneInfo()
        .Left()
        .MinSize(245, 210)
        .FloatingSize(255, 270)
        .MaxSize(500, 300)
        .Caption(_("Laser-Control"))
        .CaptionVisible(not context.pane_lock)
        .Name("laser")
    )
    pane.submenu = "_10_" + _("Laser")
    pane.control = notebook
    pane.dock_proportion = 150
    notebook.AddPage(laser_panel, _("Laser"))
    notebook.AddPage(optimize_panel, _("Optimize"))

    window.on_pane_create(pane)
    window.context.register("pane/laser", pane)
    choices = [
        {
            "attr": "laserpane_arm",
            "object": context.root,
            "default": False,
            "type": bool,
            "label": _("Enable Laser Arm"),
            "tip": _("Enable Laser Panel Arm/Disarm feature."),
            "page": "Laser",
            "section": "General",
        },
    ]
    context.kernel.register_choices("preferences", choices)


class LaserPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_devices = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Device")), wx.HORIZONTAL
        )
        sizer_main.Add(sizer_devices, 0, wx.EXPAND, 0)

        # Devices Initialize.
        self.available_devices = self.context.kernel.services("device")

        self.selected_device = self.context.device
        index = -1
        for i, s in enumerate(self.available_devices):
            if s is self.selected_device:
                index = i
                break
        spools = [s.label for s in self.available_devices]

        self.combo_devices = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_devices.SetToolTip(
            _("Select device from list of configured devices")
        )
        self.combo_devices.SetSelection(index)

        sizer_devices.Add(self.combo_devices, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_control = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control, 0, wx.EXPAND, 0)

        self.button_start = wx.Button(self, wx.ID_ANY, _("Start"))
        self.button_start.SetToolTip(_("Execute the Job"))
        self.button_start.SetBitmap(icons8_gas_industry_50.GetBitmap(resize=25))
        self.button_start.SetBackgroundColour(wx.Colour(0, 127, 0))
        sizer_control.Add(self.button_start, 1, 0, 0)

        self.button_pause = wx.Button(self, wx.ID_ANY, _("Pause"))
        self.button_pause.SetForegroundColour(wx.BLACK)  # Dark Mode correction.
        self.button_pause.SetToolTip(_("Pause/Resume the laser"))
        self.button_pause.SetBitmap(
            icons8_pause_50.GetBitmap(resize=25, use_theme=False)
        )
        self.button_pause.SetBackgroundColour(wx.Colour(255, 255, 0))
        sizer_control.Add(self.button_pause, 1, 0, 0)

        self.button_stop = wx.Button(self, wx.ID_ANY, _("Stop"))
        self.button_stop.SetToolTip(_("Stop the laser"))
        self.button_stop.SetBitmap(icons8_emergency_stop_button_50.GetBitmap(resize=25))
        self.button_stop.SetBackgroundColour(wx.Colour(127, 0, 0))
        sizer_control.Add(self.button_stop, 1, 0, 0)

        sizer_control_misc = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control_misc, 0, wx.EXPAND, 0)

        self.arm_toggle = wx.ToggleButton(self, wx.ID_ANY, _("Arm"))
        self.arm_toggle.SetToolTip(_("Arm the job for execution"))
        sizer_control_misc.Add(self.arm_toggle, 1, wx.ALIGN_CENTER, 0)

        self.check_laser_arm()

        self.button_outline = wx.Button(self, wx.ID_ANY, _("Outline"))
        self.button_outline.SetToolTip(_("Trace the outline the job"))
        self.button_outline.SetBitmap(icons8_pentagon_50.GetBitmap(resize=25))
        sizer_control_misc.Add(self.button_outline, 1, 0, 0)

        self.button_simulate = wx.Button(self, wx.ID_ANY, _("Simulate"))
        self.button_simulate.SetToolTip(_("Simulate the Design"))
        self.button_simulate.SetBitmap(
            icons8_laser_beam_hazard2_50.GetBitmap(resize=25)
        )
        sizer_control_misc.Add(self.button_simulate, 1, 0, 0)

        sizer_control_update = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control_update, 0, wx.EXPAND, 0)

        self.button_clear = wx.Button(self, wx.ID_ANY, _("Clear"))
        self.button_clear.SetToolTip(_("Clear locally defined plan"))
        self.button_clear.SetBitmap(icons8_delete_50.GetBitmap(resize=25))
        sizer_control_update.Add(self.button_clear, 1, 0, 0)

        self.button_update = wx.Button(self, wx.ID_ANY, _("Update"))
        self.button_update.SetToolTip(_("Update the Plan"))
        self.button_update.SetBitmap(icons8_goal_50.GetBitmap(resize=25))
        sizer_control_update.Add(self.button_update, 1, 0, 0)

        self.button_save_file = wx.Button(self, wx.ID_ANY, _("Save"))
        self.button_save_file.SetToolTip(_("Save the job"))
        self.button_save_file.SetBitmap(icons8_save_50.GetBitmap(resize=25))
        sizer_control_update.Add(self.button_save_file, 1, 0, 0)

        sizer_source = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_source, 0, wx.EXPAND, 0)

        self.text_plan = wx.TextCtrl(
            self, wx.ID_ANY, _(_("--- Empty ---")), style=wx.TE_READONLY
        )
        sizer_source.Add(self.text_plan, 2, 0, 0)

        self.context.setting(bool, "laserpane_hold", False)
        self.checkbox_hold = wx.CheckBox(self, wx.ID_ANY, _("Hold"))
        self.checkbox_hold.SetToolTip(
            _("Preserve the job between running, rerunning, and execution")
        )
        self.checkbox_hold.SetValue(self.context.laserpane_hold)
        sizer_source.Add(self.checkbox_hold, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.checkbox_optimize = wx.CheckBox(self, wx.ID_ANY, _("Optimize"))
        self.checkbox_optimize.SetToolTip(_("Enable/Disable Optimize"))
        self.checkbox_optimize.SetValue(1)
        sizer_source.Add(self.checkbox_optimize, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.SetSizer(sizer_main)
        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_hold, self.checkbox_hold)
        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)
        self.Bind(wx.EVT_BUTTON, self.on_button_pause, self.button_pause)
        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_check_arm, self.arm_toggle)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu_arm, self)
        self.Bind(wx.EVT_BUTTON, self.on_button_outline, self.button_outline)
        self.button_outline.Bind(wx.EVT_RIGHT_DOWN, self.on_button_outline_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_save, self.button_save_file)
        # self.Bind(wx.EVT_BUTTON, self.on_button_load, self.button_load)
        self.Bind(wx.EVT_BUTTON, self.on_button_clear, self.button_clear)
        self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)
        self.Bind(wx.EVT_BUTTON, self.on_button_simulate, self.button_simulate)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_devices, self.combo_devices)
        # self.Bind(wx.EVT_TEXT, self.on_combo_devices, self.combo_devices)
        # self.Bind(wx.EVT_TEXT_ENTER, self.on_combo_devices, self.combo_devices)
        # end wxGlade
        if index == -1:
            disable_window(self)

    @signal_listener("device;modified")
    @lookup_listener("service/device/active")
    @lookup_listener("service/device/available")
    def spooler_lookup(self, *args):
        # Devices Initialize.
        self.available_devices = self.context.kernel.services("device")
        self.selected_device = self.context.device
        index = -1
        for i, s in enumerate(self.available_devices):
            if s is self.selected_device:
                index = i
                break
        self.combo_devices.Clear()
        spools = [s.label for s in self.available_devices]
        for i in range(len(spools)):
            self.combo_devices.Append(spools[i])
        self.combo_devices.SetSelection(index)
        self.button_save_file.Enable(hasattr(self.context.device, "extension"))
        self.set_pause_color()

    def set_pause_color(self):
        new_color = None
        new_caption = _("Pause")
        try:
            if self.context.device.driver.paused:
                new_color = wx.YELLOW
                new_caption = _("Resume")
        except AttributeError:
            pass
        self.button_pause.SetBackgroundColour(new_color)
        self.button_pause.SetLabelText(new_caption)

    @signal_listener("pause")
    def on_device_pause_toggle(self, origin, *args):
        self.set_pause_color()

    @signal_listener("plan")
    def plan_update(self, origin, *message):
        plan_name, stage = message[0], message[1]
        if plan_name == "z":
            plan = self.context.planner.get_or_make_plan("z")
            if not len(plan.plan):
                self.text_plan.SetValue(_("--- Empty ---"))
            else:
                self.text_plan.SetValue(f"{str(stage)}: {str(plan)}")

    @signal_listener("laserpane_arm")
    def check_laser_arm(self, *args):
        self.context.setting(bool, "laserpane_arm", True)
        if self.context.laserpane_arm:
            if not self.arm_toggle.Shown:
                self.arm_toggle.Show(True)
                self.Layout()
            if self.arm_toggle.GetValue():
                self.arm_toggle.SetBackgroundColour(wx.RED)
                self.button_start.Enable(True)
            else:
                self.arm_toggle.SetBackgroundColour(wx.GREEN)
                self.button_start.Enable(False)
        else:
            if self.arm_toggle.Shown:
                self.arm_toggle.Show(False)
                self.Layout()
            self.button_start.Enable(True)

    def on_check_arm(self, event):
        self.check_laser_arm()

    def on_menu_arm_enable(self, event):
        self.context.laserpane_arm = True
        self.check_laser_arm()

    def on_menu_arm_disable(self, event):
        self.context.laserpane_arm = False
        self.check_laser_arm()

    def on_menu_arm(self, event):
        menu = wx.Menu()
        if not self.context.laserpane_arm:
            self.Bind(
                wx.EVT_MENU,
                self.on_menu_arm_enable,
                menu.Append(wx.ID_ANY, _("Enable Arm Requirement"), _("Enable Arm")),
            )
        else:
            self.Bind(
                wx.EVT_MENU,
                self.on_menu_arm_disable,
                menu.Append(wx.ID_ANY, _("Disable Arm Requirement"), _("Disable Arm")),
            )
        self.PopupMenu(menu)
        menu.Destroy()

    def on_button_start(self, event):  # wxGlade: LaserPanel.<event_handler>
        plan = self.context.planner.get_or_make_plan("z")
        if plan.plan and self.context.laserpane_hold:
            self.context("planz spool\n")
        else:
            if self.checkbox_optimize.GetValue():
                self.context(
                    "planz clear copy preprocess validate blob preopt optimize spool\n"
                )
            else:
                self.context("planz clear copy preprocess validate blob spool\n")
        self.arm_toggle.SetValue(False)
        self.check_laser_arm()
        if self.context.auto_spooler:
            self.context("window open JobSpooler\n")

    def on_button_pause(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("pause\n")

    def on_button_stop(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("estop\n")

    def on_button_outline(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("element* trace hull\n")

    def on_button_outline_right(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("element* trace complex\n")

    def on_button_save(self, event):  # wxGlade: LaserPanel.<event_handler>
        gui = self.context.gui
        extension = "txt"
        if hasattr(self.context.device, "extension"):
            extension = self.context.device.extension
        filetype = f"*.{extension}"
        with wx.FileDialog(
            gui,
            _("Save Project"),
            wildcard=filetype,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()

            if not pathname.lower().endswith(f".{extension}"):
                pathname += f".{extension}"
            self.context(
                f'planz clear copy preprocess validate blob preopt optimize save_job "{pathname}"\n'
            )

    def on_button_load(self, event):  # wxGlade: LaserPanel.<event_handler>
        pass

    def on_button_clear(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("planz clear\n")

    def on_button_update(self, event):  # wxGlade: LaserPanel.<event_handler>
        with wx.BusyInfo(_("Updating Plan...")):
            if self.checkbox_optimize.GetValue():
                self.context(
                    "planz clear copy preprocess validate blob preopt optimize\n"
                )
            else:
                self.context("planz clear copy preprocess validate blob\n")

    def on_button_simulate(self, event):  # wxGlade: LaserPanel.<event_handler>
        with wx.BusyInfo(_("Preparing simulation...")):
            plan = self.context.planner.get_or_make_plan("z")
            if not plan.plan or not self.context.laserpane_hold:
                if self.checkbox_optimize.GetValue():
                    self.context(
                        "planz clear copy preprocess validate blob preopt optimize\n"
                    )
                else:
                    self.context("planz clear copy preprocess validate blob\n")

            self.context("window toggle Simulation z 0\n")

    def on_check_hold(self, event):
        self.context.laserpane_hold = self.checkbox_hold.GetValue()

    def on_button_devices(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("window toggle DeviceManager\n")

    def on_combo_devices(self, event):  # wxGlade: LaserPanel.<event_handler>
        index = self.combo_devices.GetSelection()
        self.selected_device = self.available_devices[index]
        self.selected_device.kernel.activate_service_path(
            "device", self.selected_device.path
        )
        # Device change, so let's focus properly...
        zl = self.context.zoom_margin
        self.context(f"scene focus -{zl}% -{zl}% {100 + zl}% {100 + zl}%\n")
        self.set_pause_color()
