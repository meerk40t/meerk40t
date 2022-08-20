import wx

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

        self.panel_main = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-connection"
        )
        self.panel_global = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="grbl-global"
        )
        self.panel_dim = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="bed_dim"
        )
        self.panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        self.notebook_main.AddPage(self.panel_main, _("Connection"))
        self.notebook_main.AddPage(self.panel_dim, _("Dimensions"))
        self.notebook_main.AddPage(self.panel_global, _("Global Settings"))
        self.notebook_main.AddPage(self.panel_warn, _("Warning"))
        self.Layout()

    def delegates(self):
        yield self.panel_main
        yield self.panel_global
        yield self.panel_dim
        yield self.panel_warn

    def window_preserve(self):
        return False
