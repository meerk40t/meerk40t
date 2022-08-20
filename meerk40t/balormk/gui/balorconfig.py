import wx

from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class BalorConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(420, 570, *args, **kwds)
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

        self.panel_main = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="balor"
        )
        self.panel_red = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="balor-redlight"
        )
        self.panel_global = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="balor-global"
        )
        self.panel_timing = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="balor-global-timing"
        )
        self.panel_extra = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context, choices="balor-extra"
        )
        self.panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)

        self.notebook_main.AddPage(self.panel_main, _("Balor"))
        self.notebook_main.AddPage(self.panel_red, _("Redlight"))
        self.notebook_main.AddPage(self.panel_global, _("Global"))
        self.notebook_main.AddPage(self.panel_timing, _("Timings"))
        self.notebook_main.AddPage(self.panel_extra, _("Extras"))
        self.notebook_main.AddPage(self.panel_warn, _("Warning"))

        self.Layout()

    def delegates(self):
        yield self.panel_main
        yield self.panel_red
        yield self.panel_global
        yield self.panel_timing
        yield self.panel_extra
        yield self.panel_warn

    @signal_listener("flip_x")
    @signal_listener("flip_y")
    def on_viewport_update(self, origin, *args):
        self.context("viewport_update\n")

    def window_preserve(self):
        return False

    def visible_choices(self, section):
        result = False
        devmode = self.context.root.developer_mode
        choices = self.context.lookup("choices", section)
        if choices is not None:
            for item in choices:
                try:
                    dummy = str(item["hidden"])
                    if dummy == "" or dummy=="0":
                        hidden = False
                    else:
                        hidden = False if devmode else True
                except KeyError:
                    hidden = False
                if not hidden:
                    result = True
                    break
        return result