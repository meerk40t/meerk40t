import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.device.gui.effectspanel import EffectsPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import ScrolledPanel, StaticBoxSizer, TextCtrl, dip_size

_ = wx.GetTranslation


class ConfigurationUdp(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationTcp.__init__
        kwds["style"] = kwds.get("style", 0)
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        sizer_13 = StaticBoxSizer(self, wx.ID_ANY, _("UDP Settings"), wx.HORIZONTAL)

        h_sizer_y1 = StaticBoxSizer(self, wx.ID_ANY, _("Address"), wx.VERTICAL)
        sizer_13.Add(h_sizer_y1, 3, wx.EXPAND, 0)

        self.text_address = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER)
        self.text_address.SetMinSize(dip_size(self, 75, -1))
        self.text_address.SetToolTip(_("IP/hostname of the server computer"))
        h_sizer_y1.Add(self.text_address, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_13)

        self.Layout()

        self.text_address.SetActionRoutine(self.on_text_address)
        # end wxGlade
        self.text_address.SetValue(self.context.address)

    def pane_show(self):
        pass

    def pane_hide(self):
        pass

    def on_text_address(self):
        self.context.address = self.text_address.GetValue()


class ConfigurationInterfacePanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: ConfigurationInterfacePanel.__init__
        kwds["style"] = kwds.get("style", 0)
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

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

        self.radio_udp = wx.RadioButton(self, wx.ID_ANY, _("Networked"))
        self.radio_udp.SetToolTip(
            _(
                "Select this to connect this instance of Meerk40t to another instance of Meerk40t running as a remote server."
            )
        )
        sizer_interface_radio.Add(self.radio_udp, 1, wx.EXPAND, 0)

        self.radio_mock = wx.RadioButton(self, wx.ID_ANY, _("Mock"))
        self.radio_mock.SetToolTip(
            _(
                "Select this only for debugging without a physical laser available. Execute a burn as if there was an m2-nano controller physically connected by USB."
            )
        )
        sizer_interface_radio.Add(self.radio_mock, 1, wx.EXPAND, 0)

        self.panel_usb_settings = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="serial"
        )
        sizer_page_1.Add(self.panel_usb_settings, 5, wx.EXPAND, 1)

        self.panel_udp_config = ConfigurationUdp(self, wx.ID_ANY, context=self.context)
        sizer_page_1.Add(self.panel_udp_config, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_page_1)

        self.Layout()

        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_usb)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_udp)
        self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_interface, self.radio_mock)
        # end wxGlade
        if self.context.interface == "mock":
            self.panel_udp_config.Hide()
            self.panel_usb_settings.Hide()
            self.radio_mock.SetValue(True)
        elif self.context.interface == "udp":
            self.panel_usb_settings.Hide()
            self.radio_udp.SetValue(True)
        else:
            self.radio_usb.SetValue(True)
            self.panel_udp_config.Hide()
        self.SetupScrolling()

    def pane_show(self):
        self.panel_usb_settings.pane_show()
        self.panel_udp_config.pane_show()

    def pane_hide(self):
        self.panel_usb_settings.pane_hide()
        self.panel_udp_config.pane_hide()

    def on_radio_interface(
        self, event
    ):  # wxGlade: ConfigurationInterfacePanel.<event_handler>
        if self.radio_usb.GetValue():
            self.panel_udp_config.Hide()
            self.panel_usb_settings.Show()
            self.context.interface = "usb"
            self.context(".interface_update\n")
        if self.radio_udp.GetValue():
            self.panel_udp_config.Show()
            self.panel_usb_settings.Hide()
            self.context.interface = "udp"
            self.context(".interface_update\n")
        if self.radio_mock.GetValue():
            self.panel_udp_config.Hide()
            self.panel_usb_settings.Hide()
            self.context.interface = "mock"
            self.context(".interface_update\n")
        self.Layout()


class RuidaConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(420, 570, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Ruida-Configuration"))

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

        options = (("bed_dim", "Ruida"),)
        self.panels = []
        for item in options:
            section = item[0]
            pagetitle = _(item[1])
            addpanel = section
            if addpanel:
                newpanel = ChoicePropertyPanel(
                    self, wx.ID_ANY, context=self.context, choices=section
                )
                self.panels.append(newpanel)
                self.notebook_main.AddPage(newpanel, pagetitle)

        panel_interface = ConfigurationInterfacePanel(
            self.notebook_main, wx.ID_ANY, context=self.context
        )
        self.panels.append(panel_interface)
        self.notebook_main.AddPage(panel_interface, _("Interface"))

        panel_config = ChoicePropertyPanel(
            self.notebook_main,
            wx.ID_ANY,
            context=self.context,
            choices=("ruida-global", "ruida-magic"),
        )
        self.panels.append(panel_config)
        self.notebook_main.AddPage(panel_config, _("Configuration"))

        newpanel = EffectsPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Effects"))

        newpanel = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Warning"))

        newpanel = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Default Actions"))

        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Display Options"))

        self.Layout()
        for panel in self.panels:
            self.add_module_delegate(panel)

    def window_close(self):
        for panel in self.panels:
            panel.pane_hide()

    def window_open(self):
        for panel in self.panels:
            panel.pane_show()

    def window_preserve(self):
        return False

    @staticmethod
    def submenu():
        return "Device-Settings", "Configuration"

    @staticmethod
    def helptext():
        return _("Display the device configuration window")
