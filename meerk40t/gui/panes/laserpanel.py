import wx
from wx import aui

from meerk40t.gui.icons import (
    icons8_gas_industry_50,
    icons8_pause_50,
    icons8_emergency_stop_button_50,
    icons8_pentagon_50,
    icons8_delete_50,
    icons8_goal_50,
    icons8_laser_beam_hazard2_50,
)
from meerk40t.gui.propertiespanel import PropertiesPanel

_ = wx.GetTranslation


def register_panel(window, context):
    laser_panel = LaserPanel(window, wx.ID_ANY, context=context)
    optimize_panel = PropertiesPanel(
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
        .MinSize(325, 235)
        .FloatingSize(400, 300)
        .MaxSize(500, 400)
        .Caption(_("Laser"))
        .CaptionVisible(not context.pane_lock)
        .Name("laser")
    )
    pane.control = notebook
    pane.dock_proportion = 235
    notebook.AddPage(laser_panel, _("Laser"))
    notebook.AddPage(optimize_panel, _("Optimize"))

    window.on_pane_add(pane)
    window.context.register("pane/laser", pane)


class LaserPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_devices = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Device"), wx.HORIZONTAL
        )
        sizer_main.Add(sizer_devices, 0, wx.EXPAND, 0)

        # Devices Initialize.
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

        self.combo_devices = wx.ComboBox(
            self, wx.ID_ANY, choices=spools, style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_devices.SetToolTip(
            _("Select device from list of configured devices")
        )
        self.combo_devices.SetSelection(index)

        sizer_devices.Add(self.combo_devices, 1, 0, 0)

        sizer_control = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control, 0, wx.EXPAND, 0)

        self.button_start = wx.Button(self, wx.ID_ANY, _("Start"))
        self.button_start.SetToolTip(_("Execute the Job"))
        self.button_start.SetBitmap(icons8_gas_industry_50.GetBitmap(resize=25))
        self.button_start.SetBackgroundColour(wx.Colour(0, 127, 0))
        sizer_control.Add(self.button_start, 1, 0, 0)

        self.button_pause = wx.Button(self, wx.ID_ANY, _("Pause"))
        self.button_pause.SetToolTip(_("Pause/Resume the laser"))
        self.button_pause.SetBitmap(icons8_pause_50.GetBitmap(resize=25))
        self.button_pause.SetBackgroundColour(wx.Colour(255, 255, 0))
        sizer_control.Add(self.button_pause, 1, 0, 0)

        self.button_stop = wx.Button(self, wx.ID_ANY, _("Stop"))
        self.button_stop.SetToolTip(_("Stop the laser"))
        self.button_stop.SetBitmap(icons8_emergency_stop_button_50.GetBitmap(resize=25))
        self.button_stop.SetBackgroundColour(wx.Colour(127, 0, 0))
        sizer_control.Add(self.button_stop, 1, 0, 0)

        sizer_control_misc = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control_misc, 0, wx.EXPAND, 0)

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

        # self.button_save_file = wx.Button(self, wx.ID_ANY, _("Save"))
        # self.button_save_file.SetToolTip(_("Save the job"))
        # self.button_save_file.SetBitmap(icons8_save_50.GetBitmap())
        # self.button_save_file.Enable(False)
        # sizer_control_misc.Add(self.button_save_file, 1, 0, 0)

        # self.button_load = wx.Button(self, wx.ID_ANY, _("Load"))
        # self.button_load.SetToolTip(_("Load job"))
        # self.button_load.SetBitmap(icons8_opened_folder_50.GetBitmap())
        # self.button_load.Enable(False)
        # sizer_control_misc.Add(self.button_load, 1, 0, 0)

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_1, 0, wx.EXPAND, 0)

        self.button_clear = wx.Button(self, wx.ID_ANY, _("Clear"))
        self.button_clear.SetToolTip(_("Clear locally defined plan"))
        self.button_clear.SetBitmap(icons8_delete_50.GetBitmap(resize=25))
        sizer_1.Add(self.button_clear, 1, 0, 0)

        self.button_update = wx.Button(self, wx.ID_ANY, _("Update"))
        self.button_update.SetToolTip(_("Update the Plan"))
        self.button_update.SetBitmap(icons8_goal_50.GetBitmap(resize=25))
        sizer_1.Add(self.button_update, 1, 0, 0)

        sizer_source = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_source, 0, wx.EXPAND, 0)

        self.text_plan = wx.TextCtrl(
            self, wx.ID_ANY, _(_("--- Empty ---")), style=wx.TE_READONLY
        )
        sizer_source.Add(self.text_plan, 3, 0, 0)

        self.checkbox_optimize = wx.CheckBox(self, wx.ID_ANY, _("Optimize"))
        self.checkbox_optimize.SetToolTip(_("Enable/Disable Optimize"))
        self.checkbox_optimize.SetValue(1)
        sizer_source.Add(self.checkbox_optimize, 1, 0, 0)

        self.SetSizer(sizer_main)
        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)
        self.Bind(wx.EVT_BUTTON, self.on_button_pause, self.button_pause)
        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_BUTTON, self.on_button_outline, self.button_outline)
        # self.Bind(wx.EVT_BUTTON, self.on_button_save, self.button_save_file)
        # self.Bind(wx.EVT_BUTTON, self.on_button_load, self.button_load)
        self.Bind(wx.EVT_BUTTON, self.on_button_clear, self.button_clear)
        self.Bind(wx.EVT_BUTTON, self.on_button_update, self.button_update)
        self.Bind(wx.EVT_BUTTON, self.on_button_simulate, self.button_simulate)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_devices, self.combo_devices)
        self.Bind(wx.EVT_TEXT, self.on_combo_devices, self.combo_devices)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_combo_devices, self.combo_devices)
        # end wxGlade
        self.context.listen("plan", self.plan_update)

    def plan_update(self, origin, *message):
        plan_name, stage = message[0], message[1]
        if plan_name == "z":
            plan = self.context.planner.get_or_make_plan("z")
            if not len(plan.plan):
                self.text_plan.SetLabel(_("--- Empty ---"))
            else:
                self.text_plan.SetLabel("%s: %s" % (str(stage), str(plan)))

    def on_button_start(self, event):  # wxGlade: LaserPanel.<event_handler>
        plan = self.context.planner.get_or_make_plan("z")
        s = self.connected_spooler.name
        if plan.plan:
            self.context("planz spool%s\n" % s)
        else:
            if self.checkbox_optimize.GetValue():
                self.context(
                    "planz copy preprocess validate blob preopt optimize spool%s\n" % s
                )
            else:
                self.context("planz copy preprocess validate blob spool%s\n % s")

    def on_button_pause(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("pause\n")

    def on_button_stop(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("estop\n")

    def on_button_outline(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("element* trace_hull\n")

    def on_button_save(self, event):  # wxGlade: LaserPanel.<event_handler>
        pass

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
            if not plan.plan:
                if self.checkbox_optimize.GetValue():
                    self.context(
                        "planz copy preprocess validate blob preopt optimize\n"
                    )
                else:
                    self.context("planz copy preprocess validate blob\n")

            self.context("window toggle Simulation z 0\n"),

    def on_button_devices(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.context("window toggle DeviceManager\n")

    def on_combo_devices(self, event):  # wxGlade: LaserPanel.<event_handler>
        self.available_devices = [
            self.context.registered[i] for i in self.context.match("device")
        ]
        index = self.combo_devices.GetSelection()
        (
            self.connected_spooler,
            self.connected_driver,
            self.connected_output,
        ) = self.available_devices[index]
        self.context("device activate %s\n" % str(index))
