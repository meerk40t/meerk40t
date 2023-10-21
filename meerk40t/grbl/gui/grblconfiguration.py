import re

import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation

DOLLAR_INFO = re.compile(r"\$([0-9]+)=(.*)")


class ConfigurationInterfacePanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationInterfacePanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context

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

        self.radio_mock = wx.RadioButton(self, wx.ID_ANY, _("Mock"))
        self.radio_mock.SetToolTip(
            _("Select this only for debugging without a physical laser available.")
        )
        sizer_interface_radio.Add(self.radio_mock, 1, wx.EXPAND, 0)

        self.panel_serial_settings = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="serial"
        )
        sizer_interface.Add(self.panel_serial_settings, 1, wx.EXPAND, 0)

        self.panel_tcp_config = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="tcp"
        )
        sizer_interface.Add(self.panel_tcp_config, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_page_1)

        self.Layout()

        if self.context.permit_serial:
            self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_serial)
        if self.context.permit_tcp:
            self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_tcp)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_mock)
        # end wxGlade
        if self.context.permit_serial and self.context.interface == "serial":
            self.radio_serial.SetValue(True)
            self.panel_tcp_config.Hide()
        elif self.context.permit_tcp and self.context.interface == "tcp":
            self.panel_serial_settings.Hide()
            self.radio_tcp.SetValue(True)
        else:
            # Mock
            self.panel_tcp_config.Hide()
            self.panel_serial_settings.Hide()
            self.radio_mock.SetValue(True)

        self.SetupScrolling()

    def pane_show(self):
        self.panel_serial_settings.pane_show()
        self.panel_tcp_config.pane_show()

    def pane_hide(self):
        self.panel_serial_settings.pane_hide()
        self.panel_tcp_config.pane_hide()

    def on_radio_interface(
        self, event
    ):  # wxGlade: ConfigurationInterfacePanel.<event_handler>
        try:
            if self.radio_serial.GetValue():
                self.context.interface = "serial"
                self.context.signal("update_interface")
                self.panel_serial_settings.Show()
                self.panel_tcp_config.Hide()
        except AttributeError:
            pass
        try:
            if self.radio_tcp.GetValue():
                self.context.interface = "tcp"
                self.context.signal("update_interface")
                self.panel_serial_settings.Hide()
                self.panel_tcp_config.Show()
        except AttributeError:
            pass
        if self.radio_mock.GetValue():
            self.panel_tcp_config.Hide()
            self.panel_serial_settings.Hide()
            self.context.interface = "mock"
            self.context.signal("update_interface")
        self.Layout()


class GRBLConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(345, 415, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
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
        self.panels = []
        self._requested_status = False

        inject_choices = [
            {
                "attr": "aquire_properties",
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
        ]

        panel_main = ChoicePropertyPanel(
            self,
            wx.ID_ANY,
            context=self.context,
            choices="grbl-connection",
            injector=inject_choices,
        )
        panel_global = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-advanced"
        )
        panel_interface = ConfigurationInterfacePanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )
        panel_dim = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="bed_dim"
        )
        panel_rotary = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="rotary"
        )
        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        panel_formatter = FormatterPanel(self, id=wx.ID_ANY, context=self.context)

        self.panels.append(panel_main)
        self.panels.append(panel_interface)
        self.panels.append(panel_global)
        self.panels.append(panel_dim)
        self.panels.append(panel_rotary)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(panel_formatter)

        self.notebook_main.AddPage(panel_main, _("Connection"))
        self.notebook_main.AddPage(panel_interface, _("Interface"))
        self.notebook_main.AddPage(panel_dim, _("Dimensions"))
        self.notebook_main.AddPage(panel_global, _("Advanced"))
        self.notebook_main.AddPage(panel_rotary, _("Rotary"))
        self.notebook_main.AddPage(panel_warn, _("Warning"))
        self.notebook_main.AddPage(panel_actions, _("Default Actions"))
        self.notebook_main.AddPage(panel_formatter, _("Display Options"))
        self.Layout()
        for panel in self.panels:
            self.add_module_delegate(panel)

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
        return "Device-Settings", "GRBL-Configuration"

    @property
    def aquire_properties(self):
        # Not relevant
        return False

    @aquire_properties.setter
    def aquire_properties(self, value):
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
        # Workaround for newly introduced bug, normally we would
        # have a clear connection between the command and
        # the result of this command. With 0.8.4 that is broken
        if cmd_issued == "$$":
            flag = True
        elif len(responses) > 0 and responses[0].startswith("$0"):
            flag = True
        if flag:
            # Right command
            if self._requested_status:
                # coming from myself
                changes = False
                for resp in responses:
                    index = -1
                    value = None
                    match = DOLLAR_INFO.match(resp)
                    if match:
                        # $xx=yy
                        index = int(match.group(1))
                        value = match.group(2)
                    if index >= 0 and value is not None:
                        self.context.controller.grbl_settings[index] = value
                    if index == 21:
                        flag = bool(int(value) == 1)
                        self.context.has_endstops = flag
                        self.context.signal("has_endstops", flag, self.context)
                    elif index == 130:
                        self.context.bedwidth = f"{value}mm"
                        self.context.signal(
                            "bedwidth", self.context.bedwidth, self.context
                        )
                        changes = True
                    elif index == 131:
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
