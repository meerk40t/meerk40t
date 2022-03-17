import wx

from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.propertiespanel import PropertiesPanel

_ = wx.GetTranslation


class BalorConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(374, 734, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_(_("Balor-Configuration")))

        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )

        self.panel_main = PropertiesPanel(
            self, wx.ID_ANY, context=self.context, choices="balor"
        )
        self.panel_global = PropertiesPanel(
            self, wx.ID_ANY, context=self.context, choices="balor-global"
        )
        self.panel_extra = PropertiesPanel(
            self, wx.ID_ANY, context=self.context, choices="balor-extra"
        )
        self.notebook_main.AddPage(self.panel_main, _("Balor"))
        self.notebook_main.AddPage(self.panel_global, _("Global Settings"))
        self.notebook_main.AddPage(self.panel_extra, _("Extras"))
        self.Layout()

        self.add_module_delegate(self.panel_main)
        self.add_module_delegate(self.panel_global)

    def window_preserve(self):
        return False
