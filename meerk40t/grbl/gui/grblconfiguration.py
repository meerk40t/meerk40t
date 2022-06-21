import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class GRBLConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(374, 734, *args, **kwds)
        self.context = self.context.device
        _icon = wx.Icon()
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("GRBL-Configuration"))

        self.notebook_main = wx.lib.agw.aui.AuiNotebook(
            self,
            -1,
            style=wx.lib.agw.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.lib.agw.aui.AUI_NB_SCROLL_BUTTONS
            | wx.lib.agw.aui.AUI_NB_TAB_SPLIT
            | wx.lib.agw.aui.AUI_NB_TAB_MOVE,
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
        self.notebook_main.AddPage(self.panel_main, _("GRBL-connection"))
        self.notebook_main.AddPage(self.panel_dim, _("Bed Dim"))
        self.notebook_main.AddPage(self.panel_global, _("Global Settings"))
        self.Layout()
        self.add_module_delegate(self.panel_main)
        self.add_module_delegate(self.panel_global)

    def window_preserve(self):
        return False
