import wx
from wx import aui

from meerk40t.gui.icons import *
from meerk40t.gui.wxmeerk40t import MeerK40t

MILS_IN_MM = 39.3701

_ = wx.GetTranslation


def register_panel(window: MeerK40t, context):
    panel = LaserPanel(window, wx.ID_ANY, context=context)
    panel2 = LaserPanel(window, wx.ID_ANY, context=context)
    panel3 = wx.Button(window, wx.ID_ANY, "Hello")
    notebook = wx.aui.AuiNotebook(
        window,
        -1,
        size=(200, 150),
        style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
        | wx.aui.AUI_NB_SCROLL_BUTTONS
        | wx.aui.AUI_NB_TAB_SPLIT
        | wx.aui.AUI_NB_TAB_MOVE
        | wx.aui.AUI_NB_BOTTOM,
    )
    pane = (
        aui.AuiPaneInfo()
        .Right()
        .Layer(1)
        .MinSize(350, 350)
        .FloatingSize(400, 400)
        .MaxSize(500, 500)
        .Caption(_("Laser"))
        .CaptionVisible(not context.pane_lock)
        .Name("laser")
    )
    pane.control = notebook
    pane.dock_proportion = 400
    notebook.AddPage(panel, "M2Nano")
    notebook.AddPage(panel2, "GRBL")
    notebook.AddPage(panel3, "M2-Networked")

    # notebook.SetPageSize((500,750))
    # notebook.Split(1, wx.BOTTOM)
    # notebook.SetSelection(1)
    window.on_pane_add(pane)
    window.context.register("pane/laser", pane)


class LaserPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_status = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_status, 0, wx.EXPAND, 0)

        self.text_status = wx.TextCtrl(
            self, wx.ID_ANY, "Disconnected", style=wx.TE_READONLY
        )
        self.text_status.SetToolTip("Status of selected device")
        sizer_status.Add(self.text_status, 1, 0, 0)

        self.button_initialize_laser = wx.Button(self, wx.ID_ANY, "Initialize Laser")
        self.button_initialize_laser.SetBitmap(
            icons8_center_of_gravity_50.GetBitmap(resize=20)
        )
        sizer_status.Add(self.button_initialize_laser, 0, 0, 0)

        sizer_control = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control, 0, wx.EXPAND, 0)

        self.button_start = wx.Button(self, wx.ID_ANY, "Start")
        self.button_start.SetToolTip("Execute the Job")
        self.button_start.SetBitmap(icons8_gas_industry_50.GetBitmap())
        sizer_control.Add(self.button_start, 1, 0, 0)

        self.button_pause = wx.Button(self, wx.ID_ANY, "Pause")
        self.button_pause.SetToolTip("Pause/Resume the laser")
        self.button_pause.SetBitmap(icons8_pause_50.GetBitmap())
        sizer_control.Add(self.button_pause, 1, 0, 0)

        self.button_stop = wx.Button(self, wx.ID_ANY, "Stop")
        self.button_stop.SetToolTip("Stop the laser")
        self.button_stop.SetBitmap(icons8_emergency_stop_button_50.GetBitmap())
        sizer_control.Add(self.button_stop, 1, 0, 0)

        sizer_control_misc = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_control_misc, 0, wx.EXPAND, 0)

        self.button_outline = wx.Button(self, wx.ID_ANY, "Outline")
        self.button_outline.SetToolTip("Outline the job")
        self.button_outline.SetBitmap(icons8_pentagon_50.GetBitmap())
        sizer_control_misc.Add(self.button_outline, 1, 0, 0)

        self.button_save_file = wx.Button(self, wx.ID_ANY, "Save")
        self.button_save_file.SetToolTip("Save the job")
        self.button_save_file.SetBitmap(icons8_save_50.GetBitmap())
        sizer_control_misc.Add(self.button_save_file, 1, 0, 0)

        self.button_load = wx.Button(self, wx.ID_ANY, "Load")
        self.button_load.SetToolTip("Load job")
        self.button_load.SetBitmap(icons8_opened_folder_50.GetBitmap())
        sizer_control_misc.Add(self.button_load, 1, 0, 0)

        sizer_start = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_start, 0, wx.EXPAND, 0)

        sizer_source = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Source"), wx.HORIZONTAL
        )
        sizer_start.Add(sizer_source, 1, wx.EXPAND, 0)

        self.combo_source = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["Operations", "Planner", "File"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_source.SetToolTip("Select the source for the sending data")
        self.combo_source.SetSelection(0)
        sizer_source.Add(self.combo_source, 0, 0, 0)

        sizer_position = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Start Position:"), wx.HORIZONTAL
        )
        sizer_start.Add(sizer_position, 1, wx.EXPAND, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, "")
        sizer_position.Add(label_1, 0, 0, 0)

        self.combo_start = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["Absolute Home", "Current Position", "User Origin"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_start.SetToolTip("Set the start position for the job")
        self.combo_start.SetSelection(0)
        sizer_position.Add(self.combo_start, 0, 0, 0)

        sizer_optimize = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Optimize"), wx.HORIZONTAL
        )
        sizer_main.Add(sizer_optimize, 0, wx.EXPAND, 0)

        self.checkbox_optimize = wx.CheckBox(self, wx.ID_ANY, "Optimize")
        self.checkbox_optimize.SetToolTip("Enable/Disable Optimize")
        self.checkbox_optimize.SetValue(1)
        sizer_optimize.Add(self.checkbox_optimize, 1, 0, 0)

        self.button_optimize_settings = wx.Button(
            self, wx.ID_ANY, "Optimization Settings"
        )
        self.button_optimize_settings.SetToolTip(
            "View and change optimization settings"
        )
        sizer_optimize.Add(self.button_optimize_settings, 3, 0, 0)

        self.button_simulate = wx.Button(self, wx.ID_ANY, "Simulate")
        self.button_simulate.SetToolTip("Simulate the Design")
        sizer_optimize.Add(self.button_simulate, 3, 0, 0)

        sizer_devices = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Device"), wx.HORIZONTAL
        )
        sizer_main.Add(sizer_devices, 0, wx.EXPAND, 0)

        self.button_devices = wx.Button(self, wx.ID_ANY, "Settings")
        self.button_devices.SetToolTip("Set and Define Devices")
        self.button_devices.SetBitmap(
            icons8_administrative_tools_50.GetBitmap(resize=20)
        )
        sizer_devices.Add(self.button_devices, 0, 0, 0)

        self.combo_devices = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_devices.SetToolTip("Select device from list of configured devices")
        sizer_devices.Add(self.combo_devices, 1, 0, 0)

        sizer_windows = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Associated Windows"), wx.HORIZONTAL
        )
        sizer_main.Add(sizer_windows, 0, wx.EXPAND, 0)

        self.button_controller = wx.Button(self, wx.ID_ANY, "Controller")
        self.button_controller.SetToolTip("Start the Controller for this device")
        self.button_controller.SetBitmap(icons8_connected_50.GetBitmap(resize=20))
        sizer_windows.Add(self.button_controller, 1, 0, 0)

        self.button_configuration = wx.Button(self, wx.ID_ANY, "Configuration")
        self.button_configuration.SetToolTip("Start the Configuration for this device")
        self.button_configuration.SetBitmap(icons8_system_task_20.GetBitmap(resize=20))
        sizer_windows.Add(self.button_configuration, 1, 0, 0)

        self.SetSizer(sizer_main)

        self.Layout()

        self.Bind(
            wx.EVT_BUTTON, self.on_button_initialize_laser, self.button_initialize_laser
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_start, self.button_start)
        self.Bind(wx.EVT_BUTTON, self.on_button_pause, self.button_pause)
        self.Bind(wx.EVT_BUTTON, self.on_button_stop, self.button_stop)
        self.Bind(wx.EVT_BUTTON, self.on_button_outline, self.button_outline)
        self.Bind(wx.EVT_BUTTON, self.on_button_save, self.button_save_file)
        self.Bind(wx.EVT_BUTTON, self.on_button_load, self.button_load)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_source, self.combo_source)
        self.Bind(wx.EVT_TEXT, self.on_combo_source, self.combo_source)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_combo_source, self.combo_source)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_start, self.combo_start)
        self.Bind(wx.EVT_TEXT, self.on_combo_start, self.combo_start)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_combo_start, self.combo_start)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_optimize, self.checkbox_optimize)
        self.Bind(
            wx.EVT_BUTTON,
            self.on_button_optimize_settings,
            self.button_optimize_settings,
        )
        self.Bind(wx.EVT_BUTTON, self.on_button_simulate, self.button_simulate)
        self.Bind(wx.EVT_BUTTON, self.on_button_devices, self.button_devices)
        self.Bind(wx.EVT_COMBOBOX, self.on_combo_devices, self.combo_devices)
        self.Bind(wx.EVT_TEXT, self.on_combo_devices, self.combo_devices)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_combo_devices, self.combo_devices)
        self.Bind(wx.EVT_BUTTON, self.on_button_controller, self.button_controller)
        self.Bind(
            wx.EVT_BUTTON, self.on_button_configuration, self.button_configuration
        )
        # end wxGlade

    def on_button_initialize_laser(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_initialize_laser' not implemented!")
        event.Skip()

    def on_button_start(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_start' not implemented!")
        event.Skip()

    def on_button_pause(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_pause' not implemented!")
        event.Skip()

    def on_button_stop(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_stop' not implemented!")
        event.Skip()

    def on_button_outline(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_outline' not implemented!")
        event.Skip()

    def on_button_save(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_save' not implemented!")
        event.Skip()

    def on_button_load(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_load' not implemented!")
        event.Skip()

    def on_combo_source(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_combo_source' not implemented!")
        event.Skip()

    def on_combo_start(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_combo_start' not implemented!")
        event.Skip()

    def on_check_optimize(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_check_optimize' not implemented!")
        event.Skip()

    def on_button_optimize_settings(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_optimize_settings' not implemented!")
        event.Skip()

    def on_button_simulate(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_simulate' not implemented!")
        event.Skip()

    def on_button_devices(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_devices' not implemented!")
        event.Skip()

    def on_combo_devices(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_combo_devices' not implemented!")
        event.Skip()

    def on_button_controller(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_controller' not implemented!")
        event.Skip()

    def on_button_configuration(self, event):  # wxGlade: LaserPanel.<event_handler>
        print("Event handler 'on_button_configuration' not implemented!")
        event.Skip()
