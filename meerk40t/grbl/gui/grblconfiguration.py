import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


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
        grbl_connection = self.context.lookup("choices/grbl-connection")

        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        grbl_connection[1]["choices"] = [x.device for x in ports]
        grbl_connection[1]["display"] = [str(x) for x in ports]

        panel_main = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices=grbl_connection
        )
        panel_global = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-global"
        )
        panel_dim = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="bed_dim"
        )
        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)
        self.panels.append(panel_main)
        self.panels.append(panel_global)
        self.panels.append(panel_dim)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(newpanel)
        self.notebook_main.AddPage(panel_main, _("Connection"))
        self.notebook_main.AddPage(panel_dim, _("Dimensions"))
        self.notebook_main.AddPage(panel_global, _("Global Settings"))
        self.notebook_main.AddPage(panel_warn, _("Warning"))
        self.notebook_main.AddPage(panel_actions, _("Default Actions"))
        self.notebook_main.AddPage(newpanel, _("Display Options"))
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
        return ("Device-Settings", "GRBL-Configuration")
