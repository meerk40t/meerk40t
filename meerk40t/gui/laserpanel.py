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
from meerk40t.gui.navigationpanels import Drag, Jog, MovePanel
from meerk40t.gui.wxutils import StaticBoxSizer, disable_window
from meerk40t.kernel import lookup_listener, signal_listener

_ = wx.GetTranslation


def register_panel_laser(window, context):
    laser_panel = LaserPanel(window, wx.ID_ANY, context=context)
    plan_panel = JobPanel(window, wx.ID_ANY, context=context)

    optimize_panel = OptimizePanel(window, wx.ID_ANY, context=context)
    jog_drag = wx.Panel(window, wx.ID_ANY)
    jog_panel = Jog(jog_drag, wx.ID_ANY, context=context, icon_size=25)
    drag_panel = Drag(jog_drag, wx.ID_ANY, context=context, icon_size=25)
    main_sizer = wx.BoxSizer(wx.HORIZONTAL)
    main_sizer.AddStretchSpacer()
    main_sizer.Add(jog_panel, 0, wx.ALIGN_CENTER_VERTICAL, 0)
    main_sizer.AddSpacer(25)
    main_sizer.Add(drag_panel, 0, wx.ALIGN_CENTER_VERTICAL, 0)
    main_sizer.AddStretchSpacer()
    jog_drag.SetSizer(main_sizer)
    jog_drag.Layout()
    move_panel = MovePanel(window, wx.ID_ANY, context=context)
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
        .Right()
        .MinSize(200, 180)
        .BestSize(300, 270)
        .FloatingSize(300, 270)
        .Caption(_("Laser-Control"))
        .CaptionVisible(not context.pane_lock)
        .Name("laser")
    )
    pane.submenu = "_10_" + _("Laser")
    pane.control = notebook
    pane.dock_proportion = 270
    notebook.AddPage(laser_panel, _("Laser"))
    notebook.AddPage(plan_panel, _("Plan"))
    notebook.AddPage(optimize_panel, _("Optimize"))
    notebook.AddPage(jog_drag, _("Jog"))
    notebook.AddPage(move_panel, _("Move"))

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
    """
    Contains all elements to control the execution of the job
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_devices = StaticBoxSizer(self, wx.ID_ANY, _("Device"), wx.HORIZONTAL)
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
        self.btn_config_laser = wx.Button(self, wx.ID_ANY, "*")
        self.btn_config_laser.SetToolTip(
            _("Opens device-specific configuration window")
        )

        sizer_devices.Add(self.combo_devices, 1, wx.EXPAND, 0)
        self.btn_config_laser.SetMinSize(wx.Size(20, -1))
        sizer_devices.Add(self.btn_config_laser, 0, wx.EXPAND, 0)

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

        sizer_source = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_source, 0, wx.EXPAND, 0)

        self._optimize = True
        self.checkbox_optimize = wx.CheckBox(self, wx.ID_ANY, _("Optimize"))
        self.checkbox_optimize.SetToolTip(_("Enable/Disable Optimize"))
        self.checkbox_optimize.SetValue(self._optimize)
        self.checkbox_adjust = wx.CheckBox(self, wx.ID_ANY, _("Override"))
        self.checkbox_adjust.SetToolTip(
            _("Allow ad-hoc adjustment of speed and power.")
            + "\n"
            + _("This affects running jobs, so use with care!")
        )

        sizer_source.Add(self.checkbox_optimize, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_source.Add(self.checkbox_adjust, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_manipulate = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(sizer_manipulate, 0, wx.EXPAND, 0)

        self.sizer_power = wx.BoxSizer(wx.HORIZONTAL)
        sizer_manipulate.Add(self.sizer_power, 0, wx.EXPAND, 0)
        lb_power = wx.StaticText(self, wx.ID_ANY, _("Power"))
        self.label_power = wx.StaticText(self, wx.ID_ANY, "0%")
        self.slider_power = wx.Slider(
            self, wx.ID_ANY, value=10, minValue=1, maxValue=20
        )
        self.sizer_power.Add(lb_power, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_power.Add(self.slider_power, 3, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_power.Add(self.label_power, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.slider_power.SetToolTip(
            _("Increases/decreases the regular laser power by this amount.")
            + "\n"
            + _("This affects running jobs, so use with care!")
        )

        self.sizer_speed = wx.BoxSizer(wx.HORIZONTAL)
        sizer_manipulate.Add(self.sizer_speed, 0, wx.EXPAND, 0)
        lb_speed = wx.StaticText(self, wx.ID_ANY, _("Speed"))
        self.label_speed = wx.StaticText(self, wx.ID_ANY, "0%")
        self.slider_size = 20
        self.slider_speed = wx.Slider(
            self, wx.ID_ANY, value=10, minValue=1, maxValue=20
        )
        self.sizer_speed.Add(lb_speed, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_speed.Add(self.slider_speed, 3, wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_speed.Add(self.label_speed, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        self.slider_speed.SetToolTip(
            _("Increases/decreases the regular speed by this amount.")
            + "\n"
            + _("This affects running jobs, so use with care!")
        )

        self.SetSizer(sizer_main)
        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)
        self.button_start.Bind(wx.EVT_LEFT_DOWN, self.on_start_left)
        self.Bind(wx.EVT_BUTTON, self.on_button_pause, self.button_pause)
        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_check_arm, self.arm_toggle)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu_arm, self)
        self.Bind(wx.EVT_BUTTON, self.on_button_outline, self.button_outline)
        self.button_outline.Bind(wx.EVT_RIGHT_DOWN, self.on_button_outline_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_simulate, self.button_simulate)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_devices, self.combo_devices)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_adjust, self.checkbox_adjust)
        self.Bind(wx.EVT_SLIDER, self.on_slider_speed, self.slider_speed)
        self.Bind(wx.EVT_SLIDER, self.on_slider_power, self.slider_power)
        self.Bind(wx.EVT_CHECKBOX, self.on_optimize, self.checkbox_optimize)
        self.Bind(wx.EVT_BUTTON, self.on_config_button, self.btn_config_laser)
        # end wxGlade
        if index == -1:
            disable_window(self)
        self.checkbox_adjust.SetValue(False)
        self.on_check_adjust(None)
        self.update_override_controls()
        # Check for a real click of the execute button
        self.button_start_was_clicked = False

    def update_override_controls(self):
        flag_power = False
        override = False
        if hasattr(self.context.device.driver, "has_adjustable_power"):
            if self.context.device.driver.has_adjustable_power:
                flag_power = True
                # Let's establish the value and update the slider...
                value = self.context.device.driver.power_scale
                if value != 1:
                    override = True
                half = self.slider_size / 2
                sliderval = int(value * half)
                sliderval = max(1, min(self.slider_size, sliderval))
                self.slider_power.SetValue(sliderval)
                self.on_slider_speed(None)
        flag_speed = False
        if hasattr(self.context.device.driver, "has_adjustable_speed"):
            if self.context.device.driver.has_adjustable_speed:
                flag_speed = True
                # Let's establish the value and update the slider...
                value = self.context.device.driver.speed_scale
                if value != 1:
                    override = True
                half = self.slider_size / 2
                sliderval = int(value * half)
                sliderval = max(1, min(self.slider_size, sliderval))
                self.slider_speed.SetValue(sliderval)
                self.on_slider_speed(None)

        self.sizer_power.Show(flag_power)
        self.sizer_power.ShowItems(flag_power)
        self.sizer_power.Layout()
        self.sizer_speed.Show(flag_speed)
        self.sizer_speed.ShowItems(flag_speed)
        self.sizer_speed.Layout()
        self.checkbox_adjust.Show(bool(flag_power or flag_speed))
        self.checkbox_adjust.SetValue(override)
        self.slider_power.Enable(override)
        self.slider_speed.Enable(override)
        self.Layout()

    def on_check_adjust(self, event):
        if self.checkbox_adjust.GetValue():
            self.slider_power.Enable(True)
            self.slider_speed.Enable(True)
        else:
            self.slider_power.Enable(False)
            self.slider_speed.Enable(False)
            if hasattr(self.context.device.driver, "has_adjustable_power"):
                if self.context.device.driver.has_adjustable_power:
                    if event is not None:
                        self.context.device.driver.set_power_scale(1.0)
                    self.slider_power.SetValue(10)
                    self.on_slider_power(None)
            if hasattr(self.context.device.driver, "has_adjustable_speed"):
                if self.context.device.driver.has_adjustable_speed:
                    if event is not None:
                        self.context.device.driver.set_speed_scale(1.0)
                    self.slider_speed.SetValue(10)
                    self.on_slider_speed(None)

    def on_slider_speed(self, event):
        sliderval = self.slider_speed.GetValue()
        half = self.slider_size / 2
        newvalue = sliderval - half  # -> -9 to +10
        factor = 1 + newvalue / half
        if event is not None:
            self.context.device.driver.set_speed_scale(factor)
        msg = f"{'+' if factor > 1 else ''}{100 * (factor - 1.0):.0f}%"
        self.label_speed.SetLabel(msg)

    def on_slider_power(self, event):
        sliderval = self.slider_power.GetValue()
        half = self.slider_size / 2
        newvalue = sliderval - half  # -> -9 to +10
        factor = 1 + newvalue / half
        if event is not None:
            self.context.device.driver.set_power_scale(factor)
        msg = f"{'+' if factor > 1 else ''}{100 * (factor - 1.0):.0f}%"
        self.label_power.SetLabel(msg)

    def on_optimize(self, event):
        newval = bool(self.checkbox_optimize.GetValue())
        if newval != self._optimize:
            self.context.signal("optimize", newval)

    @signal_listener("optimize")
    def optimize_update(self, origin, *message):
        try:
            newvalue = bool(message[0])
        except ValueError:
            # You never know
            return
        if self._optimize != newvalue:
            self._optimize = newvalue
            self.checkbox_optimize.SetValue(newvalue)

    @signal_listener("device;modified")
    @signal_listener("device;renamed")
    @lookup_listener("service/device/active")
    @lookup_listener("service/device/available")
    def spooler_lookup(self, *args):
        # Devices Initialize.
        self.available_devices = self.context.kernel.services("device")
        self.selected_device = self.context.device
        index = -1
        self.combo_devices.Clear()
        for i, spool in enumerate(self.available_devices):
            if index < 0 and spool is self.selected_device:
                index = i
            self.combo_devices.Append(spool.label)
        self.combo_devices.SetSelection(index)
        self.set_pause_color()
        self.update_override_controls()

    @signal_listener("device;connected")
    def on_connectivity(self, *args):
        # There's no signal yet, but there should be one...
        self.update_override_controls()

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

    def on_start_left(self, event):
        self.button_start_was_clicked = True
        event.Skip()

    def on_button_start(self, event):  # wxGlade: LaserPanel.<event_handler>
        # We don't want this button to be executed if it has focus and
        # the user presses the space bar or the return key.
        # Cats can do wondrous things when they walk over a keyboard
        if not self.button_start_was_clicked:
            channel = self.context.kernel.channel("console")
            channel(
                _(
                    "We intentionally ignored a request to start a job via the keyboard.\n"
                    + "You need to make your intent clear by a deliberate mouse-click"
                )
            )
            return

        busy = self.context.kernel.busyinfo
        busy.start(msg=_("Preparing Laserjob..."))
        plan = self.context.planner.get_or_make_plan("z")
        self.context.setting(bool, "laserpane_hold", False)
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
        busy.end()
        self.button_start_was_clicked = False

    def on_button_pause(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("pause\n")

    def on_button_stop(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("estop\n")

    def on_button_outline(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("element* trace hull\n")

    def on_button_outline_right(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("element* trace complex\n")

    def on_button_simulate(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context.kernel.busyinfo.start(msg=_("Preparing simulation..."))

        plan = self.context.planner.get_or_make_plan("z")
        param = "0"
        if not plan.plan or not self.context.laserpane_hold:
            if self.checkbox_optimize.GetValue():
                self.context(
                    "planz clear copy preprocess validate blob preopt optimize\n"
                )
                param = "1"
            else:
                self.context("planz clear copy preprocess validate blob\n")
        self.context(f"window open Simulation z 0 {param}\n")
        self.context.kernel.busyinfo.end()

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

    def on_config_button(self, event):
        self.context.device("window toggle Configuration\n")


class JobPanel(wx.Panel):
    """
    Contains all elements to plan and save the job
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self._optimize = True

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

        self.SetSizer(sizer_main)
        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_check_hold, self.checkbox_hold)
        self.Bind(wx.EVT_BUTTON, self.on_button_save, self.button_save_file)
        # self.Bind(wx.EVT_BUTTON, self.on_button_load, self.button_load)
        self.Bind(wx.EVT_BUTTON, self.on_button_clear, self.button_clear)
        self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)

    @signal_listener("plan")
    def plan_update(self, origin, *message):
        plan_name, stage = message[0], message[1]
        if plan_name == "z":
            plan = self.context.planner.get_or_make_plan("z")
            if not len(plan.plan):
                self.text_plan.SetValue(_("--- Empty ---"))
            else:
                self.text_plan.SetValue(f"{str(stage)}: {str(plan)}")

    @signal_listener("optimize")
    def optimize_update(self, origin, *message):
        try:
            newvalue = bool(message[0])
        except ValueError:
            # You never know
            return
        self._optimize = newvalue

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
        self.context.kernel.busyinfo.start(msg=_("Updating Plan..."))
        if self._optimize:
            self.context("planz clear copy preprocess validate blob preopt optimize\n")
        else:
            self.context("planz clear copy preprocess validate blob\n")
        self.context.kernel.busyinfo.end()

    def on_check_hold(self, event):
        self.context.laserpane_hold = self.checkbox_hold.GetValue()

    def pane_show(self, *args):
        self.button_save_file.Enable(hasattr(self.context.device, "extension"))

    def pane_hide(self, *args):
        pass


class OptimizePanel(wx.Panel):
    """
    Contains all elements to adjust optimisation
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        from copy import copy

        self.parent = args[0]

        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self._optimize = True
        self.checkbox_optimize = wx.CheckBox(self, wx.ID_ANY, _("Optimize"))
        self.checkbox_optimize.SetToolTip(_("Enable/Disable Optimize"))
        self.checkbox_optimize.SetValue(self._optimize)
        prechoices = context.lookup("choices/optimize")
        choices = list(map(copy, prechoices))
        # Clear the page-entry
        for entry in choices:
            entry["page"] = ""
        self.optimize_panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=context, choices=choices
        )

        sizer_main.Add(self.checkbox_optimize, 0, 0, 0)
        sizer_main.Add(self.optimize_panel, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()

        self.Bind(wx.EVT_CHECKBOX, self.on_optimize, self.checkbox_optimize)
        self.parent.add_module_delegate(self.optimize_panel)

    @signal_listener("optimize")
    def optimize_update(self, origin, *message):
        try:
            newvalue = bool(message[0])
        except ValueError:
            # You never know
            return
        if self._optimize != newvalue:
            self._optimize = newvalue
            self.checkbox_optimize.SetValue(newvalue)
            self.optimize_panel.Enable(newvalue)

    def on_optimize(self, event):
        newvalue = bool(self.checkbox_optimize.GetValue())
        if newvalue != self._optimize:
            self._optimize = newvalue
            self.context.signal("optimize", newvalue)
            self.optimize_panel.Enable(newvalue)

    def pane_show(self, *args):
        pass

    def pane_hide(self, *args):
        pass
