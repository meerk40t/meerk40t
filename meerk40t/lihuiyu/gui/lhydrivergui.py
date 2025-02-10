import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.device.gui.effectspanel import EffectsPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxCheckBox,
    wxStaticText,
)
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation

FIX_SPEEDS_RATIO = 0.9195


class ConfigurationUsb(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationUsb.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_usb_settings = StaticBoxSizer(
            self, wx.ID_ANY, _("USB Settings"), wx.VERTICAL
        )

        sizer_usb_restrict = StaticBoxSizer(
            self, wx.ID_ANY, _("Restrict Multiple Lasers"), wx.VERTICAL
        )
        sizer_usb_settings.Add(sizer_usb_restrict, 0, wx.EXPAND, 0)

        sizer_criteria = wx.BoxSizer(wx.HORIZONTAL)
        sizer_usb_restrict.Add(sizer_criteria, 1, wx.EXPAND, 0)

        sizer_chip_version = StaticBoxSizer(
            self, wx.ID_ANY, _("CH341 Version"), wx.HORIZONTAL
        )
        sizer_criteria.Add(sizer_chip_version, 0, wx.EXPAND, 0)

        self.text_device_version = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        sizer_chip_version.Add(self.text_device_version, 1, wx.EXPAND, 0)

        self.spin_device_version = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=100)
        self.spin_device_version.SetMinSize(dip_size(self, 40, -1))
        self.spin_device_version.SetToolTip(
            _(
                "Optional: Distinguish between different lasers using the match criteria below.\n-1 match anything. 0+ match exactly that value."
            )
        )
        sizer_chip_version.Add(self.spin_device_version, 0, wx.EXPAND, 0)

        sizer_device_index = StaticBoxSizer(
            self, wx.ID_ANY, _("Device Index:"), wx.HORIZONTAL
        )
        sizer_criteria.Add(sizer_device_index, 0, wx.EXPAND, 0)

        self.text_device_index = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        sizer_device_index.Add(self.text_device_index, 1, wx.EXPAND, 0)

        self.spin_device_index = wx.SpinCtrl(self, wx.ID_ANY, "-1", min=-1, max=5)
        self.spin_device_index.SetMinSize(dip_size(self, 40, -1))
        self.spin_device_index.SetToolTip(
            _(
                "Optional: Distinguish between different lasers using the match criteria below.\n-1 match anything. 0+ match exactly that value."
            )
        )
        sizer_device_index.Add(self.spin_device_index, 0, wx.EXPAND, 0)

        sizer_serial = StaticBoxSizer(
            self, wx.ID_ANY, _("Serial Number"), wx.HORIZONTAL
        )
        sizer_usb_restrict.Add(sizer_serial, 0, wx.EXPAND, 0)

        self.check_serial_number = wxCheckBox(self, wx.ID_ANY, _("Serial Number"))
        self.check_serial_number.SetToolTip(
            _("Require a serial number match for this board")
        )
        sizer_serial.Add(self.check_serial_number, 0, wx.EXPAND, 0)

        self.text_serial_number = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER
        )
        self.text_serial_number.SetMinSize(dip_size(self, 50, -1))
        self.text_serial_number.SetToolTip(
            _(
                "Board Serial Number to be used to identify a specific laser. If the device fails to match the serial number it will be disconnected."
            )
        )
        sizer_serial.Add(self.text_serial_number, 1, wx.EXPAND, 0)

        sizer_buffer = StaticBoxSizer(self, wx.ID_ANY, _("Write Buffer"), wx.HORIZONTAL)
        sizer_usb_settings.Add(sizer_buffer, 0, wx.EXPAND, 0)

        self.checkbox_limit_buffer = wxCheckBox(
            self, wx.ID_ANY, _("Limit Write Buffer")
        )
        self.checkbox_limit_buffer.SetToolTip(
            _(
                "Limit the write buffer to a certain amount. Permits on-the-fly command production."
            )
        )
        self.checkbox_limit_buffer.SetValue(1)
        sizer_buffer.Add(self.checkbox_limit_buffer, 0, 0, 0)

        self.text_buffer_length = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY, limited=True
        )
        self.text_buffer_length.SetToolTip(
            _("Current number of bytes in the write buffer.")
        )
        sizer_buffer.Add(self.text_buffer_length, 1, wx.EXPAND, 0)

        label_14 = wxStaticText(self, wx.ID_ANY, "/")
        sizer_buffer.Add(label_14, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.spin_packet_buffer_max = wx.SpinCtrl(
            self, wx.ID_ANY, "1500", min=1, max=1000000
        )
        self.spin_packet_buffer_max.SetToolTip(_("Current maximum write buffer limit."))
        self.spin_packet_buffer_max.SetMaxSize(dip_size(self, 100, -1))
        sizer_buffer.Add(self.spin_packet_buffer_max, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_usb_settings)

        self.Layout()

        self.Bind(
            wx.EVT_SPINCTRL, self.spin_on_device_version, self.spin_device_version
        )
        self.Bind(
            wx.EVT_TEXT_ENTER, self.spin_on_device_version, self.spin_device_version
        )
        self.Bind(wx.EVT_SPINCTRL, self.spin_on_device_index, self.spin_device_index)
        self.Bind(wx.EVT_TEXT_ENTER, self.spin_on_device_index, self.spin_device_index)
        self.Bind(
            wx.EVT_CHECKBOX, self.on_check_serial_number, self.check_serial_number
        )
        self.text_serial_number.SetActionRoutine(self.on_text_serial_number)
        self.Bind(
            wx.EVT_CHECKBOX,
            self.on_check_limit_packet_buffer,
            self.checkbox_limit_buffer,
        )
        self.Bind(
            wx.EVT_SPINCTRL, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max
        )
        self.Bind(
            wx.EVT_TEXT, self.on_spin_packet_buffer_max, self.spin_packet_buffer_max
        )
        self.Bind(
            wx.EVT_TEXT_ENTER,
            self.on_spin_packet_buffer_max,
            self.spin_packet_buffer_max,
        )
        # end wxGlade
        self.spin_device_index.SetValue(self.context.usb_index)
        self.spin_device_version.SetValue(self.context.usb_version)
        if self.context.serial is not None:
            self.text_serial_number.SetValue(self.context.serial)
        self.check_serial_number.SetValue(self.context.serial_enable)
        self.checkbox_limit_buffer.SetValue(self.context.buffer_limit)
        self.spin_packet_buffer_max.SetValue(self.context.buffer_max)

    def pane_show(self):
        # self.context.listen("pipe;buffer", self.on_buffer_update)
        pass

    def pane_hide(self):
        # self.context.unlisten("pipe;buffer", self.on_buffer_update)
        pass

    @signal_listener("pipe;buffer")
    def on_buffer_update(self, origin, value, *args):
        self.text_buffer_length.SetValue(str(value))

    @signal_listener("pipe;index")
    def on_update_pipe_index(self, origin, value):
        if origin != self.context.path:
            return
        self.text_device_index.SetValue(str(value))

    @signal_listener("pipe;chipv")
    def on_update_pipe_chipv(self, origin, value):
        if origin != self.context.path:
            return
        self.text_device_version.SetValue(str(value))

    def on_check_limit_packet_buffer(
        self, event=None
    ):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_limit = self.checkbox_limit_buffer.GetValue()

    def on_spin_packet_buffer_max(self, event=None):  # wxGlade: JobInfo.<event_handler>
        self.context.buffer_max = self.spin_packet_buffer_max.GetValue()

    def spin_on_device_index(self, event=None):
        self.context.usb_index = int(self.spin_device_index.GetValue())

    def spin_on_device_version(self, event=None):
        self.context.usb_version = int(self.spin_device_version.GetValue())

    def on_check_serial_number(
        self, event
    ):  # wxGlade: ConfigurationUsb.<event_handler>
        self.context.serial_enable = self.check_serial_number.GetValue()

    def on_text_serial_number(self):
        self.context.serial = self.text_serial_number.GetValue()


class ConfigurationTcp(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationTcp.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context

        sizer_13 = StaticBoxSizer(self, wx.ID_ANY, _("TCP Settings"), wx.HORIZONTAL)

        h_sizer_y1 = StaticBoxSizer(self, wx.ID_ANY, _("Address"), wx.VERTICAL)
        sizer_13.Add(h_sizer_y1, 3, wx.EXPAND, 0)

        self.text_address = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_address.SetMinSize(dip_size(self, 75, -1))
        self.text_address.SetToolTip(_("IP/hostname of the server computer"))
        h_sizer_y1.Add(self.text_address, 1, wx.EXPAND, 0)

        sizer_port = StaticBoxSizer(self, wx.ID_ANY, _("Port"), wx.VERTICAL)
        sizer_13.Add(sizer_port, 1, wx.EXPAND, 0)

        self.text_port = TextCtrl(
            self,
            wx.ID_ANY,
            "",
            limited=True,
            check="int",
            style=wx.TE_PROCESS_ENTER,
        )
        self.text_port.lower_limit = 0
        self.text_port.upper_limit = 65535
        self.text_port.lower_limit_err = 0
        self.text_port.upper_limit_err = 65535

        self.text_port.SetToolTip(_("Port for tcp connection on the server computer"))
        sizer_port.Add(self.text_port, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_13)

        self.Layout()

        self.text_address.SetActionRoutine(self.on_text_address)
        self.text_port.SetActionRoutine(self.on_text_port)
        # end wxGlade
        self.text_port.SetValue(str(self.context.port))
        self.text_address.SetValue(self.context.address)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_text_address(self):
        self.context.address = self.text_address.GetValue()

    def on_text_port(self):  # wxGlade: ConfigurationTcp.<event_handler>
        try:
            self.context.port = max(0, min(65535, int(self.text_port.GetValue())))
        except ValueError:
            pass


class ConfigurationInterfacePanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationInterfacePanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context

        sizer_page_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_interface = StaticBoxSizer(self, wx.ID_ANY, _("Interface"), wx.VERTICAL)
        sizer_page_1.Add(sizer_interface, 0, wx.EXPAND, 0)

        sizer_interface_radio = wx.BoxSizer(wx.HORIZONTAL)
        sizer_interface.Add(sizer_interface_radio, 0, wx.EXPAND, 0)

        self.radio_usb = wx.RadioButton(self, wx.ID_ANY, _("USB"), style=wx.RB_GROUP)
        self.radio_usb.SetValue(1)
        self.radio_usb.SetToolTip(
            _(
                "Select this if you have an m2-nano controller physically connected to this computer using a USB cable."
            )
        )
        sizer_interface_radio.Add(self.radio_usb, 1, wx.EXPAND, 0)

        self.radio_tcp = wx.RadioButton(self, wx.ID_ANY, _("Networked"))
        self.radio_tcp.SetToolTip(
            _(
                "Select this to connect this instance of Meerk40t to another instance of Meerk40t running as a remote server."
            )
        )
        sizer_interface_radio.Add(self.radio_tcp, 1, wx.EXPAND, 0)

        self.radio_mock = wx.RadioButton(self, wx.ID_ANY, _("Mock"))
        self.radio_mock.SetToolTip(
            _(
                "Select this only for debugging without a physical laser available. Execute a burn as if there was an m2-nano controller physically connected by USB."
            )
        )
        sizer_interface_radio.Add(self.radio_mock, 1, wx.EXPAND, 0)

        self.panel_usb_settings = ConfigurationUsb(
            self, wx.ID_ANY, context=self.context
        )
        sizer_interface.Add(self.panel_usb_settings, 0, wx.EXPAND, 0)

        self.panel_tcp_config = ConfigurationTcp(self, wx.ID_ANY, context=self.context)
        sizer_interface.Add(self.panel_tcp_config, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_page_1)

        self.Layout()

        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_usb)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_tcp)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_mock)
        # end wxGlade
        if self.context.mock:
            self.panel_tcp_config.Hide()
            self.panel_usb_settings.Hide()
            self.radio_mock.SetValue(True)
        elif self.context.networked:
            self.panel_usb_settings.Hide()
            self.radio_tcp.SetValue(True)
        else:
            self.radio_usb.SetValue(True)
            self.panel_tcp_config.Hide()
        self.SetupScrolling()

    def pane_show(self):
        self.panel_usb_settings.pane_show()
        self.panel_tcp_config.pane_show()

    def pane_hide(self):
        self.panel_usb_settings.pane_hide()
        self.panel_tcp_config.pane_hide()

    def on_radio_interface(
        self, event
    ):  # wxGlade: ConfigurationInterfacePanel.<event_handler>
        if self.radio_usb.GetValue():
            self.panel_tcp_config.Hide()
            self.panel_usb_settings.Show()
            self.context.networked = False
            self.context.mock = False
            self.context(".network_update\n")
        if self.radio_tcp.GetValue():
            self.panel_tcp_config.Show()
            self.panel_usb_settings.Hide()
            self.context.networked = True
            self.context.mock = False
            self.context(".network_update\n")
        if self.radio_mock.GetValue():
            self.panel_tcp_config.Hide()
            self.panel_usb_settings.Hide()
            self.context.networked = False
            self.context.mock = True
            self.context(".network_update\n")
        self.Layout()


class LihuiyuDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(550, 700, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Lihuiyu-Configuration"))

        # self.notebook_main = wx.Notebook(self, wx.ID_ANY)
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
        panel_config = ChoicePropertyPanel(
            self.notebook_main,
            wx.ID_ANY,
            context=self.context,
            choices=("bed_dim", "bed_orientation", "coolant"),
        )

        panel_interface = ConfigurationInterfacePanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )

        panel_setup = ChoicePropertyPanel(
            self,
            wx.ID_ANY,
            context=self.context,
            choices=("lhy-general", "lhy-jog", "lhy-rapid-override", "lhy-speed"),
        )

        panel_effects = EffectsPanel(self, id=wx.ID_ANY, context=self.context)
        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        panel_format = FormatterPanel(self, id=wx.ID_ANY, context=self.context)

        self.panels.append(panel_config)
        self.panels.append(panel_interface)
        self.panels.append(panel_setup)
        self.panels.append(panel_effects)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(panel_format)

        self.notebook_main.AddPage(panel_config, _("Configuration"))
        self.notebook_main.AddPage(panel_interface, _("Interface"))
        self.notebook_main.AddPage(panel_setup, _("Setup"))
        self.notebook_main.AddPage(panel_effects, _("Effects"))
        self.notebook_main.AddPage(panel_warn, _("Warning"))
        self.notebook_main.AddPage(panel_actions, _("Default Actions"))
        self.notebook_main.AddPage(panel_format, _("Display Options"))

        self.Layout()
        self.restore_aspect(honor_initial_values=True)

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
        return "Device-Settings", "Configuration"

    @staticmethod
    def helptext():
        return _("Display the device configuration window")
