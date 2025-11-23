import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.effectspanel import EffectsPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer, TextCtrl, dip_size
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class ConfigurationUsb(wx.Panel):
    '''Allow direct entry of serial port.

    On Linux this enables use of symlinks for devices to avoid having to
    re-enter the serial device when the cable has been pulled or the controller
    has been turned off. See the README for more information on how to
    configure UDEV to create the symlinks.
    '''
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationTcp.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        sizer_13 = StaticBoxSizer(self, wx.ID_ANY, _("USB Settings"), wx.HORIZONTAL)

        h_sizer_y1 = StaticBoxSizer(self, wx.ID_ANY, _("Serial Interface"), wx.VERTICAL)
        sizer_13.Add(h_sizer_y1, 3, wx.EXPAND, 0)

        self.text_serial_port = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_serial_port.SetMinSize(dip_size(self, 75, -1))
        self.text_serial_port.SetToolTip(_(
            'Serial port on the host.\n'
            'On Linux this is "/dev/<dev>"\n'
            'This allows use of symlinks using UDEV rules.\n'
            'On Windows this is "COM<n>"'))
        h_sizer_y1.Add(self.text_serial_port, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_13)

        self.Layout()

        self.text_serial_port.SetActionRoutine(self.on_text_serial_port)
        # end wxGlade
        self.text_serial_port.SetValue(self.context.serial_port)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_text_serial_port(self):
        self.context.serial_port = self.text_serial_port.GetValue()

class ConfigurationInterfacePanel(ScrolledPanel):
    """ConfigurationInterfacePanel - User interface panel for laser cutting operations
    **Technical Purpose:**
    Provides user interface controls for configurationinterface functionality. Features radio button controls for user interaction. Integrates with grid, bedwidth for enhanced functionality.
    **End-User Perspective:**
    This panel provides controls for configurationinterface functionality. Key controls include "Networked" (radio button), "WebSocket" (radio button), "Mock" (radio button)."""

    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationInterfacePanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.SetHelpText("grblconfig")

        sizer_page_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_interface = StaticBoxSizer(self, wx.ID_ANY, _("Interface"), wx.VERTICAL)
        sizer_page_1.Add(sizer_interface, 10, wx.EXPAND, 0)

        sizer_interface_radio = wx.BoxSizer(wx.HORIZONTAL)
        sizer_interface.Add(sizer_interface_radio, 0, wx.EXPAND, 0)

        if self.context.permit_serial:
            self.radio_serial = wx.RadioButton(
                self, wx.ID_ANY, _("Serial"), style=wx.RB_GROUP
            )
            self.radio_serial.SetValue(1)
            self.radio_serial.SetToolTip(
                _(
                    "Select this if you have a GRBL device running through a serial connection."
                )
            )
            sizer_interface_radio.Add(self.radio_serial, 1, wx.EXPAND, 0)

        if self.context.permit_tcp:
            self.radio_tcp = wx.RadioButton(self, wx.ID_ANY, _("Networked"))
            self.radio_tcp.SetToolTip(
                _("Select this if the GRBL device is contacted via TCP connection")
            )
            sizer_interface_radio.Add(self.radio_tcp, 1, wx.EXPAND, 0)

        if self.context.permit_ws:
            self.radio_ws = wx.RadioButton(self, wx.ID_ANY, _("WebSocket"))
            self.radio_ws.SetToolTip(
                _(
                    "Select this if the GRBL device is contacted via WebSocket connection"
                )
            )
            sizer_interface_radio.Add(self.radio_ws, 1, wx.EXPAND, 0)

        self.radio_mock = wx.RadioButton(self, wx.ID_ANY, _("Mock"))
        self.radio_mock.SetToolTip(
            _("Select this only for debugging without a physical laser available.")
        )
        sizer_interface_radio.Add(self.radio_mock, 1, wx.EXPAND, 0)

        #self.panel_serial_settings = ChoicePropertyPanel(
        #    self, wx.ID_ANY, context=self.context, choices="serial"
        #)
        self.panel_serial_settings = ConfigurationUsb(self, wx.ID_ANY, context=self.context)

        sizer_interface.Add(self.panel_serial_settings, 1, wx.EXPAND, 0)

        self.panel_tcp_config = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="tcp"
        )
        sizer_interface.Add(self.panel_tcp_config, 1, wx.EXPAND, 0)

        self.panel_ws_config = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="ws"
        )
        sizer_interface.Add(self.panel_ws_config, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_page_1)

        self.Layout()

        if self.context.permit_serial:
            self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_serial)
        if self.context.permit_tcp:
            self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_tcp)
        if self.context.permit_ws:
            self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_ws)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_mock)
        # end wxGlade
        if self.context.permit_serial and self.context.interface == "serial":
            self.radio_serial.SetValue(True)
            self.panel_tcp_config.Hide()
            self.panel_ws_config.Hide()
        elif self.context.permit_tcp and self.context.interface == "tcp":
            self.panel_serial_settings.Hide()
            self.radio_tcp.SetValue(True)
            self.panel_ws_config.Hide()
        elif self.context.permit_ws and self.context.interface == "ws":
            self.panel_serial_settings.Hide()
            self.panel_tcp_config.Hide()
            self.radio_ws.SetValue(True)
        else:
            # Mock
            self.panel_tcp_config.Hide()
            self.panel_serial_settings.Hide()
            self.panel_ws_config.Hide()
            self.radio_mock.SetValue(True)

        self.SetupScrolling()

    def pane_show(self):
        self.panel_serial_settings.pane_show()
        self.panel_tcp_config.pane_show()
        self.panel_ws_config.pane_show()

    def pane_hide(self):
        self.panel_serial_settings.pane_hide()
        self.panel_tcp_config.pane_hide()
        self.panel_ws_config.pane_hide()

    def on_radio_interface(
        self, event
    ):  # wxGlade: ConfigurationInterfacePanel.<event_handler>
        last = self.context.interface
        try:
            if self.radio_serial.GetValue():
                self.context.interface = "serial"
                self.context.signal("update_interface")
                self.panel_serial_settings.Show()
                self.panel_tcp_config.Hide()
                self.panel_ws_config.Hide()
        except AttributeError:
            pass
        try:
            if self.radio_tcp.GetValue():
                if self.context.port == 81:
                    self.context.port = 23
                    self.context.signal("port", self.context.port, self.context)
                self.context.interface = "tcp"
                self.context.signal("update_interface")
                self.panel_serial_settings.Hide()
                self.panel_tcp_config.Show()
                self.panel_ws_config.Hide()
        except AttributeError:
            pass

        try:
            if self.radio_ws.GetValue():
                if self.context.port == 23:
                    self.context.port = 81
                    self.context.signal("port", self.context.port, self.context)
                self.context.interface = "ws"
                self.context.signal("update_interface")
                self.panel_serial_settings.Hide()
                self.panel_tcp_config.Hide()
                self.panel_ws_config.Show()
        except AttributeError:
            pass
        if self.radio_mock.GetValue():
            self.panel_tcp_config.Hide()
            self.panel_serial_settings.Hide()
            self.panel_ws_config.Hide()
            self.context.interface = "mock"
            self.context.signal("update_interface")
        self.Layout()


class GRBLConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(550, 700, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("GRBL-Configuration"))

        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.window_context.themes.set_window_colors(self.notebook_main)
        bg_std = self.window_context.themes.get("win_bg")
        bg_active = self.window_context.themes.get("highlight")
        self.notebook_main.GetArtProvider().SetColour(bg_std)
        self.notebook_main.GetArtProvider().SetActiveColour(bg_active)

        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)
        self.panels = []
        self._requested_status = False

        inject_choices = [
            {
                "attr": "acquire_properties",
                "object": self,
                "default": False,
                "type": bool,
                "style": "button",
                "label": _("Query properties"),
                "tip": _("Connect to laser and try to establish some properties"),
                "section": "_ZZ_Auto-Configuration",
                "width": 250,
                "weight": 0,
            },
            {
                "attr": "hw_config",
                "object": self,
                "default": False,
                "type": bool,
                "style": "button",
                "label": _("Hardware properties"),
                "tip": _("Retrieve and change Laser properties"),
                "section": "_ZZ_Auto-Configuration",
                "width": 250,
                "weight": 0,
            },
        ]

        panel_global = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-advanced"
        )
        panel_interface = ConfigurationInterfacePanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )
        panel_dim = ChoicePropertyPanel(
            self,
            wx.ID_ANY,
            context=self.context,
            choices="bed_dim",
            injector=inject_choices,
        )
        panel_protocol = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="protocol"
        )

        panel_effects = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-effects"
        )
        panel_defaults = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-defaults"
        )
        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        panel_formatter = FormatterPanel(self, id=wx.ID_ANY, context=self.context)

        self.panels.append(panel_dim)
        self.panels.append(panel_interface)
        self.panels.append(panel_protocol)
        self.panels.append(panel_global)
        self.panels.append(panel_effects)
        self.panels.append(panel_defaults)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(panel_formatter)

        self.notebook_main.AddPage(panel_dim, _("Device"))
        self.notebook_main.AddPage(panel_interface, _("Interface"))
        self.notebook_main.AddPage(panel_protocol, _("Protocol"))
        self.notebook_main.AddPage(panel_global, _("Advanced"))
        self.notebook_main.AddPage(panel_effects, _("Effects"))
        self.notebook_main.AddPage(panel_defaults, _("Operation Defaults"))
        self.notebook_main.AddPage(panel_warn, _("Warning"))
        self.notebook_main.AddPage(panel_actions, _("Default Actions"))
        self.notebook_main.AddPage(panel_formatter, _("Display Options"))
        self.Layout()
        for panel in self.panels:
            self.add_module_delegate(panel)
        self.restore_aspect(honor_initial_values=True)

    def window_open(self):
        for panel in self.panels:
            panel.pane_show()

    def window_close(self):
        for panel in self.panels:
            panel.pane_hide()

    def window_preserve(self):
        return False

    @staticmethod
    def submenu():
        # Hint for translation: _("Device-Settings"), _("GRBL-Configuration")
        return "Device-Settings", "GRBL-Configuration"

    @staticmethod
    def helptext():
        return _("Edit device configuration")

    @property
    def hw_config(self):
        # Not relevant
        return False

    @hw_config.setter
    def hw_config(self, value):
        if not value:
            return
        try:
            self.context.driver(f"$${self.context.driver.line_end}")
            self.context("window open GrblHardwareConfig\n")
        except:
            wx.MessageBox(
                _("Could not query laser-data!"),
                _("Connect failed"),
                wx.OK | wx.ICON_ERROR,
            )

    @property
    def acquire_properties(self):
        # Not relevant
        return False

    @acquire_properties.setter
    def acquire_properties(self, value):
        if not value:
            return
        try:
            self.context.driver(f"$${self.context.driver.line_end}")
            self._requested_status = True
        except:
            wx.MessageBox(
                _("Could not query laser-data!"),
                _("Connect failed"),
                wx.OK | wx.ICON_ERROR,
            )

    @signal_listener("grbl;response")
    def on_serial_status(self, origin, cmd_issued, responses=None):
        if responses is None:
            return
        flag = False
        if cmd_issued.startswith("$$"):
            flag = True
        if flag:
            # Right command
            if self._requested_status and hasattr(
                self.context.device, "hardware_config"
            ):
                # coming from myself
                changes = False
                if 21 in self.context.device.hardware_config:
                    value = self.context.device.hardware_config[21]
                    # Some grbl controllers send something like "1 (hard limits,bool)"
                    flag = value is not None and str(value).startswith("1")
                    self.context.has_endstops = flag
                    self.context.signal("has_endstops", flag, self.context)
                if 130 in self.context.device.hardware_config:
                    value = self.context.device.hardware_config[130]
                    self.context.bedwidth = f"{value}mm"
                    self.context.signal("bedwidth", self.context.bedwidth, self.context)
                    changes = True
                if 131 in self.context.device.hardware_config:
                    value = self.context.device.hardware_config[131]
                    self.context.bedheight = f"{value}mm"
                    self.context.signal(
                        "bedheight", self.context.bedheight, self.context
                    )
                    changes = True
                if changes:
                    self.context("viewport_update\n")
                    self.context.signal("guide")
                    self.context.signal("grid")
                    self.context.signal("refresh_scene", "Scene")
                self._requested_status = False
                wx.MessageBox(
                    _("Successfully queried laser-data!"),
                    _("Connect succeeded"),
                    wx.OK | wx.ICON_INFORMATION,
                )

        else:
            # Different command
            pass

    @signal_listener("activate;device")
    def on_device_changes(self, *args):
        # Device activated, make sure we are still fine...
        if self.context.device.name != "GRBLDevice":
            wx.CallAfter(self.Close)
