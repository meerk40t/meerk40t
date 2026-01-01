import platform

import wx
from wx import aui

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import (
    get_default_icon_size,
    icon_closed_door,
    icon_open_door,
    icon_update_plan,
    icons8_computer_support,
    icons8_delete,
    icons8_emergency_stop_button,
    icons8_gas_industry,
    icons8_laser_beam_hazard,
    icons8_pause,
    icons8_pentagon,
    icons8_save,
)
from meerk40t.gui.navigationpanels import Drag, Jog, JogDistancePanel, MovePanel
from meerk40t.gui.wxutils import (
    HoverButton,
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    disable_window,
    wxButton,
    wxCheckBox,
    wxComboBox,
    wxListCtrl,
    wxStaticText,
)
from meerk40t.kernel import lookup_listener, signal_listener

_ = wx.GetTranslation


def register_panel_laser(window, context):
    laser_panel = LaserPanel(window, wx.ID_ANY, context=context)
    plan_panel = JobPanel(window, wx.ID_ANY, context=context)

    optimize_panel = OptimizePanel(window, wx.ID_ANY, context=context)
    # jog_drag = wx.Panel(window, wx.ID_ANY)
    jog_drag = ScrolledPanel(window, wx.ID_ANY)
    jog_drag.SetupScrolling()
    jog_panel = Jog(jog_drag, wx.ID_ANY, context=context, suppress_z_controls=True)
    drag_panel = Drag(jog_drag, wx.ID_ANY, context=context)
    distance_panel = JogDistancePanel(jog_drag, wx.ID_ANY, context=context)
    main_sizer = wx.BoxSizer(wx.VERTICAL)
    sub_sizer = wx.BoxSizer(wx.HORIZONTAL)
    # main_sizer.AddStretchSpacer()
    sub_sizer.Add(jog_panel, 1, wx.ALIGN_CENTER_VERTICAL, 0)
    sub_sizer.Add(drag_panel, 1, wx.ALIGN_CENTER_VERTICAL, 0)
    main_sizer.Add(sub_sizer, 1, wx.EXPAND, 0)
    main_sizer.Add(distance_panel, 0, wx.EXPAND, 0)
    # main_sizer.AddStretchSpacer()
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
    # ARGGH, the color setting via the ArtProvider does only work
    # if you set the tabs to the bottom! wx.aui.AUI_NB_BOTTOM
    context.themes.set_window_colors(notebook)
    bg_std = context.themes.get("win_bg")
    bg_active = context.themes.get("highlight")
    notebook.GetArtProvider().SetColour(bg_std)
    notebook.GetArtProvider().SetActiveColour(bg_active)

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
    pane.helptext = _("Laser job control panel")
    pane.control = notebook
    pane.dock_proportion = 270
    notebook.AddPage(laser_panel, _("Laser"))
    notebook.AddPage(jog_drag, _("Jog"))
    notebook.AddPage(plan_panel, _("Plan"))
    notebook.AddPage(optimize_panel, _("Optimize"))
    notebook.AddPage(move_panel, _("Move"))

    def on_page_change(event):
        event.Skip()
        page = notebook.GetCurrentPage()
        if page is None:
            return
        pages = [jog_panel, drag_panel, distance_panel] if page is jog_drag else [page]
        for p in pages:
            if hasattr(p, "pane_show"):
                p.pane_show()

    notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, on_page_change)
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
            # Hint for translation _("General")
            "section": "General",
        },
    ]
    context.kernel.register_choices("preferences", choices)

    def on_resize(event):
        wb_size = jog_drag.ClientSize
        if platform.system() == "Linux":
            # They don't resize well
            panel_size = (max(20, wb_size[0] / 2 - 40), wb_size[1])
        else:
            panel_size = (wb_size[0] / 2, wb_size[1])

        for panel in (jog_panel, drag_panel, distance_panel):
            if hasattr(panel, "set_icons"):
                panel.set_icons(dimension=panel_size)

    jog_drag.Bind(wx.EVT_SIZE, on_resize)


class LaserPanel(wx.Panel):
    """
    Main laser job execution and control interface providing comprehensive device management, job execution controls, safety systems, and real-time parameter adjustment.

    **Technical Details:**
    - Purpose: Central control panel for laser operations including device selection, job execution, safety arming, parameter adjustment, and optimization controls with real-time device state synchronization
    - Signals: Multiple listeners including "optimize", "pwm_mode_changed", "device;modified", "device;renamed", "device;connected", "pause", "laser_armed", "laserpane_arm", "plan" for comprehensive device and job state management
    - Help Section: laserpanel

    **User Interface:**
    - Device selection dropdown with configuration access button for multi-device management
    - Primary execution controls (Start/Pause/Stop) with safety arm/disarm system to prevent accidental firing
    - Secondary operation buttons (Outline/Simulate) for job preview and testing with background processing options
    - Real-time power and speed adjustment sliders with override controls for running jobs
    - Optimization toggle with dynamic enable/disable based on device capabilities
    - Rotary active status indicator for rotary engraving operations
    - Comprehensive tooltip system explaining all control functions and safety warnings
    - Settings persistence for control states and user preferences across sessions
    - Dynamic UI adaptation based on device capabilities and current job state
    """

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("laserpanel")
        self.context.root.setting(bool, "laserpane_arm", True)
        self.context.setting(bool, "laserpane_hold", False)
        self.context.setting(str, "laserpane_plan", "z")

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.icon_size = 0.5 * get_default_icon_size(self.context)

        self.sizer_devices = StaticBoxSizer(self, wx.ID_ANY, _("Device"), wx.HORIZONTAL)
        sizer_main.Add(self.sizer_devices, 0, wx.EXPAND, 0)

        # Devices Initialize.
        self.available_devices = self.context.kernel.services("device")

        self.combo_devices = wxComboBox(
            self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_devices.SetToolTip(
            _("Select device from list of configured devices")
        )
        ss = dip_size(self, 23, 23)
        bsize = ss[0] * self.context.root.bitmap_correction_scale
        self.btn_config_laser = wxButton(self, wx.ID_ANY, size=ss)
        self.btn_config_laser.SetBitmap(icons8_computer_support.GetBitmap(resize=bsize))
        self.btn_config_laser.SetToolTip(
            _("Opens device-specific configuration window")
        )
        kernel = self.context.kernel
        if (
            hasattr(kernel.args, "lock_device_config")
            and kernel.args.lock_device_config
        ):
            self.btn_config_laser.Enable(False)
        self.sizer_devices.Add(self.combo_devices, 1, wx.EXPAND, 0)
        minsize = 32
        self.btn_config_laser.SetMinSize(dip_size(self, minsize, -1))
        self.sizer_devices.Add(self.btn_config_laser, 0, wx.EXPAND, 0)

        sizer_control = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control, 0, wx.EXPAND, 0)

        self.button_start = HoverButton(self, wx.ID_ANY, _("Start"))
        self.button_start.SetToolTip(_("Execute the Job"))
        self.button_start.SetBitmap(
            icons8_gas_industry.GetBitmap(
                resize=self.icon_size,
                color=wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT),
                keepalpha=True,
                force_darkmode=True,
            )
        )
        self.button_start.SetBitmapFocus(
            icons8_gas_industry.GetBitmap(
                resize=self.icon_size,
            )
        )
        self.button_start.SetBackgroundColour(self.context.themes.get("start_bg"))
        self.button_start.SetForegroundColour(self.context.themes.get("start_fg"))
        self.button_start.SetFocusColour(self.context.themes.get("start_fg_focus"))

        sizer_control.Add(self.button_start, 1, wx.EXPAND, 0)

        self.button_pause = HoverButton(self, wx.ID_ANY, _("Pause"))
        self.button_pause.SetToolTip(_("Pause/Resume the laser"))
        self.button_pause.SetBitmap(
            icons8_pause.GetBitmap(
                resize=self.icon_size,
            )
        )
        sizer_control.Add(self.button_pause, 1, wx.EXPAND, 0)

        self.button_stop = HoverButton(self, wx.ID_ANY, _("Stop"))
        self.button_stop.SetToolTip(_("Stop the laser"))
        self.button_stop.SetBitmap(
            icons8_emergency_stop_button.GetBitmap(
                resize=self.icon_size,
                color=self.context.themes.get("stop_fg"),
                keepalpha=True,
                force_darkmode=True,
            )
        )
        self.button_stop.SetBitmapFocus(
            icons8_emergency_stop_button.GetBitmap(
                resize=self.icon_size,
            )
        )
        self.button_stop.SetBackgroundColour(self.context.themes.get("stop_bg"))
        self.button_stop.SetForegroundColour(self.context.themes.get("stop_fg"))
        self.button_stop.SetFocusColour(self.context.themes.get("stop_fg_focus"))
        sizer_control.Add(self.button_stop, 1, wx.EXPAND, 0)

        sizer_control_misc = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control_misc, 0, wx.EXPAND, 0)

        self.arm_toggle = HoverButton(self, wx.ID_ANY, _("Arm"))
        self.arm_toggle.SetToolTip(_("Arm the job for execution"))
        self.arm_toggle.SetBitmap(
            icon_closed_door.GetBitmap(
                resize=self.icon_size,
                color=self.context.themes.get("arm_fg"),
            )
        )
        self.arm_toggle.SetBitmapFocus(
            icon_closed_door.GetBitmap(
                resize=self.icon_size,
            )
        )
        self.arm_toggle.SetForegroundColour(self.context.themes.get("arm_fg"))
        self.arm_toggle.SetFocusColour(self.context.themes.get("stop_fg_focus"))
        self.armed = False
        sizer_control_misc.Add(self.arm_toggle, 1, wx.EXPAND, 0)

        self.check_laser_arm()

        self.button_outline = wxButton(self, wx.ID_ANY, _("Outline"))
        self.button_outline.SetToolTip(_("Trace the outline of the job"))
        self.button_outline.SetBitmap(
            icons8_pentagon.GetBitmap(
                resize=self.icon_size,
            )
        )
        sizer_control_misc.Add(self.button_outline, 1, wx.EXPAND, 0)

        self.button_simulate = wxButton(self, wx.ID_ANY, _("Simulate"))
        self.button_simulate.SetToolTip(_("Simulate the Design"))
        self.button_simulate.SetBitmap(
            icons8_laser_beam_hazard.GetBitmap(
                resize=self.icon_size,
            )
        )
        sizer_control_misc.Add(self.button_simulate, 1, wx.EXPAND, 0)

        sizer_control_update = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control_update, 0, wx.EXPAND, 0)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.rotary_indicator = wxStaticText(
            self, wx.ID_ANY, _("Rotary active"), style=wx.ALIGN_CENTRE_HORIZONTAL
        )
        bg_color = self.context.themes.get("pause_bg")
        fg_color = self.context.themes.get("pause_fg")
        self.rotary_indicator.SetBackgroundColour(bg_color)
        self.rotary_indicator.SetForegroundColour(fg_color)
        box.Add(self.rotary_indicator, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(box, 0, wx.EXPAND, 0)

        sizer_source = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_source, 0, wx.EXPAND, 0)

        self.checkbox_optimize = wxCheckBox(self, wx.ID_ANY, _("Optimize"))
        self.checkbox_optimize.SetToolTip(_("Enable/Disable Optimize"))
        self.checkbox_optimize.SetValue(self.context.planner.do_optimization)
        self.checkbox_adjust = wxCheckBox(self, wx.ID_ANY, _("Override"))
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
        lb_power = wxStaticText(self, wx.ID_ANY, _("Power"))
        self.label_power = wxStaticText(self, wx.ID_ANY, "0%")
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
        lb_speed = wxStaticText(self, wx.ID_ANY, _("Speed"))
        self.label_speed = wxStaticText(self, wx.ID_ANY, "0%")
        self.slider_size = 20
        self.power_mode = "relative"
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
        self.Bind(wx.EVT_BUTTON, self.on_check_arm, self.arm_toggle)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu_arm, self)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu_arm, self.button_start)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu_arm, self.button_outline)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_menu_arm, self.button_simulate)
        self.Bind(wx.EVT_BUTTON, self.on_button_outline, self.button_outline)
        self.button_outline.Bind(wx.EVT_RIGHT_DOWN, self.on_button_outline_right)
        self.Bind(wx.EVT_BUTTON, self.on_button_simulate, self.button_simulate)
        self.button_simulate.Bind(wx.EVT_RIGHT_DOWN, self.on_button_simulate_right)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_devices, self.combo_devices)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_adjust, self.checkbox_adjust)
        self.Bind(wx.EVT_SLIDER, self.on_slider_speed, self.slider_speed)
        self.Bind(wx.EVT_SLIDER, self.on_slider_power, self.slider_power)
        self.Bind(wx.EVT_CHECKBOX, self.on_optimize, self.checkbox_optimize)
        # self.btn_config_laser.Bind(wx.EVT_LEFT_DOWN, self.on_config_button)
        self.btn_config_laser.Bind(wx.EVT_BUTTON, self.on_config_button)
        self.combo_devices.Bind(wx.EVT_RIGHT_DOWN, self.on_control_right)
        self.btn_config_laser.Bind(wx.EVT_RIGHT_DOWN, self.on_control_right)
        # end wxGlade
        self.checkbox_adjust.SetValue(False)
        self.on_check_adjust(None)
        self.update_override_controls()
        self.on_device_changes()
        index = self.combo_devices.GetSelection()
        if index == -1:
            disable_window(self)
        # Check for a real click of the execute button
        self.button_start_was_clicked = False

    def update_override_controls(self):
        def set_boundaries(slider, current_value, min_value, max_value):
            slider.SetMin(min_value)
            slider.SetMax(max_value)
            slider.SetValue(current_value)

        flag_power = False
        override = False
        if (
            hasattr(self.context.device.driver, "has_adjustable_power")
            and self.context.device.driver.has_adjustable_power
        ):
            flag_power = True
            # Let's establish the value and update the slider...
            value = self.context.device.driver.power_scale
            if value != 1:
                override = True
            half = self.slider_size / 2
            sliderval = int(value * half)
            sliderval = max(1, min(self.slider_size, sliderval))
            set_boundaries(self.slider_power, sliderval, 1, self.slider_size)
            self.slider_power.SetToolTip(
                _("Increases/decreases the regular laser power by this amount.")
                + "\n"
                + _("This affects running jobs, so use with care!")
            )
            self.power_mode = "relative"
            self.on_slider_power(None)
        elif (
            hasattr(self.context.device.driver, "has_adjustable_maximum_power")
            and self.context.device.driver.has_adjustable_maximum_power
        ):
            flag_power = True
            override = True
            dev_mode = getattr(self.context.kernel.root, "developer_mode", False)
            # Let's establish the value and update the slider...
            min_value = 1
            max_value = 100 if dev_mode else 50
            sliderval = min(max_value, self.context.device.driver.max_power_scale)
            set_boundaries(self.slider_power, sliderval, min_value, max_value)
            self.slider_power.SetToolTip(
                _("Sets the maximum laser power level.")
                + "\n"
                + _("Setting this too high may cause damage to your laser tube!")
            )
            self.power_mode = "maximum"
            self.on_slider_power(None)
        flag_speed = False
        if (
            hasattr(self.context.device.driver, "has_adjustable_speed")
            and self.context.device.driver.has_adjustable_speed
        ):
            flag_speed = True
            # Let's establish the value and update the slider...
            value = self.context.device.driver.speed_scale
            if value != 1:
                override = True
            half = self.slider_size / 2
            sliderval = int(value * half)
            sliderval = max(1, min(self.slider_size, sliderval))
            set_boundaries(self.slider_speed, sliderval, 1, self.slider_size)
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
            if (
                hasattr(self.context.device.driver, "has_adjustable_power")
                and self.context.device.driver.has_adjustable_power
            ):
                if event is not None:
                    self.context.device.driver.set_power_scale(1.0)
                self.slider_power.SetValue(10)
                self.on_slider_power(None)
            if (
                hasattr(self.context.device.driver, "has_adjustable_speed")
                and self.context.device.driver.has_adjustable_speed
            ):
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
        if self.power_mode == "maximum":
            # Maximum power mode, so we just set the value.
            if event is not None:
                self.context.device.driver.max_power_scale = sliderval
            msg = f"{sliderval}%"
        else:
            half = self.slider_size / 2
            newvalue = sliderval - half  # -> -9 to +10
            factor = 1 + newvalue / half
            if event is not None:
                self.context.device.driver.set_power_scale(factor)
            msg = f"{'+' if factor > 1 else ''}{100 * (factor - 1.0):.0f}%"
        self.label_power.SetLabel(msg)

    def on_optimize(self, event):
        newval = bool(self.checkbox_optimize.GetValue())
        if newval != self.context.planner.do_optimization:
            self.context.planner.do_optimization = newval
            self.context.signal("optimize", newval)

    @signal_listener("optimize")
    def optimize_update(self, origin, *message):
        try:
            newvalue = bool(message[0])
        except ValueError:
            # You never know
            return
        if self.context.planner.do_optimization != newvalue:
            self.context.planner.do_optimization = newvalue
        if self.checkbox_optimize.GetValue() != newvalue:
            self.checkbox_optimize.SetValue(newvalue)

    @signal_listener("pwm_mode_changed")
    def on_pwm_mode_changed(self, origin, *message):
        """
        This is called when the power scale of the device changes.
        It updates the slider and label accordingly.
        """
        self.update_override_controls()

    @signal_listener("device;modified")
    @signal_listener("device;renamed")
    @lookup_listener("service/device/active")
    @lookup_listener("service/device/available")
    def on_device_changes(self, *args):
        # Devices Initialize.
        self.available_devices = self.context.kernel.services("device")
        self.selected_device = self.context.device
        index = -1
        count = 0
        self.combo_devices.Clear()
        for i, spool in enumerate(self.available_devices):
            if index < 0 and spool is self.selected_device:
                index = i
            self.combo_devices.Append(spool.label)
            count += 1
        self.combo_devices.SetSelection(index)
        self.set_pause_color()
        self.update_override_controls()
        showit = count > 1
        self.sizer_devices.ShowItems(showit)
        flag = False
        if hasattr(self.context.device, "rotary"):
            flag = self.context.device.rotary.active
        self.rotary_indicator.Show(flag)
        self.Layout()

    @signal_listener("device;connected")
    def on_connectivity(self, *args):
        # There's no signal yet, but there should be one...
        self.update_override_controls()

    def set_pause_color(self):
        new_bg_color = None
        new_fg_color = None
        new_caption = _("Pause")
        try:
            if self.context.device.driver.paused:
                new_bg_color = self.context.themes.get("pause_bg")
                new_fg_color = self.context.themes.get("pause_fg")
                new_caption = _("Resume")
        except AttributeError:
            pass
        self.button_pause.SetBackgroundColour(new_bg_color)
        self.button_pause.SetForegroundColour(new_fg_color)
        self.button_pause.SetLabelText(new_caption)

    @signal_listener("pause")
    def on_device_pause_toggle(self, origin, *args):
        self.set_pause_color()

    @signal_listener("laser_armed")
    def signal_laser_arm(self, origin, *message):
        try:
            newval = bool(message[0])
        except ValueError:
            # You never know
            newval = False
        if self.armed != newval:
            self.armed = newval
            self.check_laser_arm()

    @signal_listener("laserpane_arm")
    def check_laser_arm(self, *args):
        ctxt = self.context.kernel.root
        ctxt.setting(bool, "_laser_may_run", False)
        if self.context.root.laserpane_arm:
            if not self.arm_toggle.Shown:
                self.arm_toggle.Show(True)
                self.Layout()
            if self.armed:
                self.arm_toggle.SetBackgroundColour(self.context.themes.get("arm_bg"))
                self.button_start.SetBackgroundColour(
                    self.context.themes.get("start_bg")
                )
                self.arm_toggle.SetBitmap(
                    icon_open_door.GetBitmap(
                        resize=self.icon_size,
                        color=self.context.themes.get("arm_fg"),
                    )
                )
                self.arm_toggle.SetBitmapFocus(
                    icon_open_door.GetBitmap(
                        resize=self.icon_size,
                    )
                )
                self.arm_toggle.SetLabel(_("Disarm"))
                self.arm_toggle.SetToolTip(
                    _("Prevent the laser from accidentally executing")
                )
                self.button_start.Enable(True)
                ctxt._laser_may_run = True
            else:
                self.arm_toggle.SetBackgroundColour(
                    self.context.themes.get("arm_bg_inactive")
                )
                self.button_start.SetBackgroundColour(
                    self.context.themes.get("start_bg_inactive")
                )
                self.button_start.Enable(False)
                self.arm_toggle.SetBitmap(
                    icon_closed_door.GetBitmap(
                        resize=self.icon_size,
                        color=self.context.themes.get("arm_fg"),
                    )
                )
                self.arm_toggle.SetBitmapFocus(
                    icon_closed_door.GetBitmap(
                        resize=self.icon_size,
                    )
                )
                self.arm_toggle.SetLabel(_("Arm"))
                self.arm_toggle.SetToolTip(_("Arm the job for execution"))
                ctxt._laser_may_run = False
        else:
            if self.arm_toggle.Shown:
                self.arm_toggle.Show(False)
                self.Layout()
            self.button_start.SetBackgroundColour(self.context.themes.get("start_bg"))
            self.button_start.Enable(True)
            ctxt._laser_may_run = True
        self.context.signal("laser_armed", self.armed)
        self.context.signal("icons")

    def on_check_arm(self, event):
        self.armed = not self.armed
        self.check_laser_arm()

    def on_menu_arm_enable(self, event):
        self.context.root.laserpane_arm = True
        self.check_laser_arm()

    def on_menu_arm_disable(self, event):
        self.context.root.laserpane_arm = False
        self.check_laser_arm()

    def on_menu_arm(self, event):
        menu = wx.Menu()
        if not self.context.root.laserpane_arm:
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
        prefer_threaded = self.context.setting(bool, "prefer_threaded_mode", True)
        prefix = "threaded " if prefer_threaded else ""

        busy = self.context.kernel.busyinfo
        busy.start(msg=_("Preparing Laserjob..."))
        last_plan = self.context.laserpane_plan or self.context.planner.get_last_plan()
        if self.context.laserpane_hold and self.context.planner.has_content(last_plan):
            self.context(f"plan{last_plan} spool\n")
        elif self.checkbox_optimize.GetValue():
            new_plan = self.context.planner.get_free_plan()
            self.context(
                f"{prefix}plan{new_plan} clear copy preprocess validate blob preopt optimize spool\n"
            )
            if self.context.setting(bool, "autoshow_task_window", True):
                self.context("window open ThreadInfo\n")
        else:
            new_plan = self.context.planner.get_free_plan()
            self.context(
                f"{prefix}plan{new_plan} clear copy preprocess validate blob spool\n"
            )
        self.armed = False
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
        try:
            self.context.device.outline()
        except AttributeError:
            self.context("element* trace hull\n")

    def on_button_outline_right(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("element* trace quick\n")

    def simulate(self, in_background=False):
        if in_background:
            prefix = "threaded "
        else:
            prefix = ""
            self.context.kernel.busyinfo.start(msg=_("Preparing simulation..."))

        param = "0"
        last_plan = self.context.laserpane_plan or self.context.planner.get_last_plan()
        if self.context.laserpane_hold and self.context.planner.has_content(last_plan):
            plan = last_plan
        else:
            plan = self.context.planner.get_free_plan()
            if self.checkbox_optimize.GetValue():
                self.context(
                    f"{prefix}plan{plan} clear copy preprocess validate blob preopt optimize finish\n"
                )
                param = "1"
            else:
                self.context(
                    f"{prefix}plan{plan} clear copy preprocess validate blob finish\n"
                )
        self.context(f"window open Simulation {plan} 0 {param}\n")
        if not in_background:
            self.context.kernel.busyinfo.end()

    def on_button_simulate(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.simulate(in_background=False)

    def on_button_simulate_right(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.simulate(in_background=True)

    def on_control_right(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("window open DeviceManager\n")

    def on_combo_devices(self, event):  # wxGlade: LaserPanel.<event_handler>
        index = self.combo_devices.GetSelection()
        try:
            self.selected_device = self.available_devices[index]
        except IndexError:
            return
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
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.last_selected = None
        self.list_plan = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
            context=self.context,
            list_name="list_plan",
        )
        self.list_plan.SetToolTip(_("List of prepared cutplans"))
        self.list_plan.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=48)
        self.list_plan.AppendColumn(_("Plan"), format=wx.LIST_FORMAT_LEFT, width=113)
        self.list_plan.AppendColumn(_("Status"), format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_plan.AppendColumn(_("Content"), format=wx.LIST_FORMAT_LEFT, width=73)
        self.list_plan.resize_columns()
        # self.btn_clear = wx.Button(self, wx.ID_ANY, _("Clear"))
        # self.btn_clear.SetToolTip(_("Clear selected plan"))
        self.btn_update = wx.Button(self, wx.ID_ANY, _("Update"))
        self.btn_update.SetToolTip(_("Update selected plan"))
        self.btn_export = wx.Button(self, wx.ID_ANY, _("Export"))
        self.btn_export.SetToolTip(_("Export selected plan"))
        self.btn_spool = wx.Button(self, wx.ID_ANY, _("Spool"))
        self.btn_spool.SetToolTip(_("Spool selected plan"))
        self.context.setting(bool, "laserpane_hold", False)
        self.context.setting(str, "laserpane_plan", "z")
        self.checkbox_hold = wxCheckBox(self, wx.ID_ANY, _("Hold"))
        self.checkbox_hold.SetToolTip(
            _("Preserve the job between running, rerunning, and execution")
        )
        self.checkbox_hold.SetValue(self.context.laserpane_hold)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.list_plan, 1, wx.EXPAND, 0)
        hsizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        # hsizer.Add(self.btn_clear, 0, wx.EXPAND, 0)
        hsizer_buttons.Add(self.btn_update, 0, wx.EXPAND, 0)
        hsizer_buttons.Add(self.btn_export, 0, wx.EXPAND, 0)
        hsizer_buttons.Add(self.btn_spool, 0, wx.EXPAND, 0)
        hsizer_controls = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_controls.Add(self.checkbox_hold, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_main.Add(hsizer_buttons, 0, wx.EXPAND, 0)
        sizer_main.Add(hsizer_controls, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        self.shown = False
        self.list_plan.Bind(wx.EVT_RIGHT_DOWN, self.on_right_click)
        self.list_plan.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection)
        # self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear_plan)
        self.btn_update.Bind(wx.EVT_BUTTON, self.on_update_plan)
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_export_plan)
        self.btn_spool.Bind(wx.EVT_BUTTON, self.on_spool_plan)
        self.checkbox_hold.Bind(wx.EVT_CHECKBOX, self.on_hold)
        self.on_selection(None)

    def refresh_plan_list(self):
        self.list_plan.DeleteAllItems()
        idx = 0
        for plan_name in self.context.planner._plan:
            idx += 1
            cutplan = self.context.planner._plan[plan_name]
            state, description = self.context.planner.get_plan_stage(plan_name)
            item = self.list_plan.InsertItem(idx, f"{idx}")
            self.list_plan.SetItem(item, 1, plan_name)
            self.list_plan.SetItem(item, 2, description)
            itemcount = 0
            for layer in cutplan.plan:
                if isinstance(layer, (list, tuple)):
                    itemcount += len(layer)
                elif hasattr(layer, "children"):
                    itemcount += len(layer.children)
                else:
                    itemcount += 1

            info = _("{amount} items").format(amount=itemcount)
            self.list_plan.SetItem(item, 3, info)
        # Reselect previous selection if possible
        if self.last_selected is not None:
            for idx in range(self.list_plan.GetItemCount()):
                plan_name = self.list_plan.GetItemText(idx, 1)
                if plan_name == self.last_selected:
                    self.last_selected = None
                    self.list_plan.Select(idx)
                    self.on_selection(None)
                    break

    @signal_listener("plan")
    def plan_update(self, origin, *message):
        if self.shown:
            self.refresh_plan_list()

    def on_selection(self, event):
        can_update = self.list_plan.GetFirstSelected() != -1
        has_content = False
        if can_update:
            plan_name = self.list_plan.GetItemText(self.list_plan.GetFirstSelected(), 1)
            self.last_selected = plan_name
            try:
                has_content = self.context.planner.has_content(plan_name)
            except KeyError:
                can_update = False
        can_export = has_content and hasattr(self.context.device, "extension")
        self.btn_update.Enable(can_update)
        self.btn_export.Enable(can_export)
        self.btn_spool.Enable(has_content)

    def on_spool_plan(self, event):
        if self.list_plan.GetFirstSelected() == -1:
            return
        plan_name = self.list_plan.GetItemText(self.list_plan.GetFirstSelected(), 1)
        self.context.laserpane_plan = plan_name
        plan = self.context.planner._plan[plan_name]
        if len(plan.plan) == 0:
            wx.MessageBox(
                _("No items to spool"), _("Spool Plan"), wx.OK | wx.ICON_INFORMATION
            )
            return
        self.context(f"plan{plan_name} spool\n")

    def on_show_details(self, event):
        if self.list_plan.GetFirstSelected() == -1:
            return
        plan_name = self.list_plan.GetItemText(self.list_plan.GetFirstSelected(), 1)
        msgs = []
        msgs.append(_("Details of Plan '{plan}':").format(plan=plan_name))
        with self.context.planner._plan_lock:
            states = self.context.planner._states.get(plan_name, {})
        if states:
            ordered = sorted(states.items(), key=lambda kv: kv[1])
            start_time = ordered[0][1]
            previous_time = start_time
            total_time = ordered[-1][1] - start_time
            for stage, timestamp in ordered:
                stagename = self.context.planner.STAGE_DESCRIPTIONS[stage]
                if total_time > 0:
                    percent = (
                        f" ({100 * (timestamp - previous_time) / total_time:.1f}%)"
                    )
                else:
                    percent = ""
                msgs.append(
                    f"Stage '{stagename}': {timestamp - previous_time:.1f}s{percent}"
                )
                previous_time = timestamp
            msgs.append(f"Total time: {total_time:.1f}s")
        else:
            msgs.append(_("Empty"))
        # We look at the stages of the given plan.
        info = "\n".join(msgs)
        wx.MessageBox(info, _("Plan Details"), wx.OK | wx.ICON_INFORMATION)

    def on_clear_plan(self, event):
        if self.list_plan.GetFirstSelected() == -1:
            return
        plan_name = self.list_plan.GetItemText(self.list_plan.GetFirstSelected(), 1)
        self.context(f"plan{plan_name} clear finish\n")

    def _do_update_plan(self, background: bool = False):
        if self.list_plan.GetFirstSelected() == -1:
            return
        plan_name = self.list_plan.GetItemText(self.list_plan.GetFirstSelected(), 1)
        self.last_selected = plan_name
        if self.context.planner.do_optimization:
            cmd = f"plan{plan_name} clear copy preprocess validate blob preopt optimize finish\n"
        else:
            cmd = f"plan{plan_name} clear copy preprocess validate blob finish\n"
        if background:
            self.context(f"threaded {cmd}")
            if self.context.setting(bool, "autoshow_task_window", True):
                self.context("window open ThreadInfo\n")
        else:
            self.context.kernel.busyinfo.start(msg=_("Updating Plan..."))
            self.context(cmd)
            self.context.kernel.busyinfo.end()

    def on_update_plan(self, event):
        self._do_update_plan()

    def on_update_plan_background(self, event):
        self._do_update_plan(background=True)

    def on_export_plan(self, event):
        if self.list_plan.GetFirstSelected() == -1:
            return
        plan_name = self.list_plan.GetItemText(self.list_plan.GetFirstSelected(), 1)
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
            self.context(f'plan{plan_name} save_job "{pathname}"\n')

    def on_hold(self, event):
        self.context.laserpane_hold = self.checkbox_hold.GetValue()

    def on_right_click(self, event):
        # Select the item under the mouse cursor
        event.Skip()
        item, flags = self.list_plan.HitTest(event.GetPosition())
        if item >= 0:
            self.list_plan.Select(item)
        item = self.list_plan.GetFirstSelected()
        if item < 0:
            return
        menu = wx.Menu()
        item = menu.Append(wx.ID_ANY, _("Clear"))
        self.Bind(wx.EVT_MENU, self.on_clear_plan, item)
        item = menu.Append(wx.ID_ANY, _("Update"))
        self.Bind(wx.EVT_MENU, self.on_update_plan, item)
        item = menu.Append(wx.ID_ANY, _("Update (background)"))
        self.Bind(wx.EVT_MENU, self.on_update_plan_background, item)
        item = menu.Append(wx.ID_ANY, _("Export"))
        self.Bind(wx.EVT_MENU, self.on_export_plan, item)
        item = menu.Append(wx.ID_ANY, _("Spool"))
        self.Bind(wx.EVT_MENU, self.on_spool_plan, item)
        menu.AppendSeparator()
        item = menu.AppendCheckItem(wx.ID_ANY, _("Details"))
        self.Bind(wx.EVT_MENU, self.on_show_details, item)
        self.PopupMenu(menu)
        menu.Destroy()

    def pane_show(self):
        self.shown = True
        self.list_plan.load_column_widths()
        self.refresh_plan_list()

    def pane_hide(self):
        self.shown = False
        self.list_plan.save_column_widths()


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
        self.context.themes.set_window_colors(self)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.checkbox_optimize = wxCheckBox(self, wx.ID_ANY, _("Optimize"))
        self.checkbox_optimize.SetToolTip(_("Enable/Disable Optimize"))
        self.checkbox_optimize.SetValue(self.context.planner.do_optimization)
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
        if self.context.planner.do_optimization != newvalue:
            self.context.planner.do_optimization = newvalue
        if self.checkbox_optimize.GetValue() != newvalue:
            self.checkbox_optimize.SetValue(newvalue)
            self.optimize_panel.Enable(newvalue)

    def on_optimize(self, event):
        newvalue = bool(self.checkbox_optimize.GetValue())
        if newvalue != self.context.planner.do_optimization:
            self.context.planner.do_optimization = newvalue
            self.context.signal("optimize", newvalue)
            self.optimize_panel.Enable(newvalue)

    def pane_show(self, *args):
        pass

    def pane_hide(self, *args):
        pass
