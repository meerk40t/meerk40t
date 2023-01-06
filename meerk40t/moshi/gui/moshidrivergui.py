import wx

from meerk40t.core.units import Length
from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import ScrolledPanel, TextCtrl
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class MoshiConfigurationPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.parent = args[0]
        self.choices = self.context.lookup("choices", "bed_dim")
        self.panel_pref1 = ChoicePropertyPanel(
            self,
            id=wx.ID_ANY,
            context=context,
            choices=self.choices,
        )
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.panel_pref1, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        self.SetupScrolling()
        self.parent.add_module_delegate(self.panel_pref1)

        # end wxGlade

    def delegates(self):
        yield self.panel_pref1

    def pane_show(self):
        return

    def pane_hide(self):
        return

    @signal_listener("active")
    def on_active_change(self, origin, active):
        # self.Close()
        pass


class MoshiDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(305, 410, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Moshiboard-Configuration"))

        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.panels = []

        panel_config = MoshiConfigurationPanel(self, wx.ID_ANY, context=self.context)

        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)

        self.panels.append(panel_config)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(newpanel)

        self.notebook_main.AddPage(panel_config, _("Configuration"))
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
        return ("Device-Settings", "Configuration")
