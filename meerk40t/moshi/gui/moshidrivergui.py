import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.device.gui.effectspanel import EffectsPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class MoshiDriverGui(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(330, 630, *args, **kwds)
        self.context = self.context.device
        self.SetHelpText("moshiconfig")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
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
        self.window_context.themes.set_window_colors(self.notebook_main)
        bg_std = self.window_context.themes.get("win_bg")
        bg_active = self.window_context.themes.get("highlight")
        self.notebook_main.GetArtProvider().SetColour(bg_std)
        self.notebook_main.GetArtProvider().SetActiveColour(bg_active)
        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)

        self.panels = []

        panel_config = ChoicePropertyPanel(
            self,
            id=wx.ID_ANY,
            context=self.context,
            choices=("bed_dim", "coolant"),
        )
        panel_effects = EffectsPanel(self, id=wx.ID_ANY, context=self.context)
        panel_warn = WarningPanel(self, id=wx.ID_ANY, context=self.context)
        panel_actions = DefaultActionPanel(self, id=wx.ID_ANY, context=self.context)
        newpanel = FormatterPanel(self, id=wx.ID_ANY, context=self.context)

        self.panels.append(panel_config)
        self.panels.append(panel_effects)
        self.panels.append(panel_warn)
        self.panels.append(panel_actions)
        self.panels.append(newpanel)

        self.notebook_main.AddPage(panel_config, _("Configuration"))
        self.notebook_main.AddPage(panel_effects, _("Effects"))
        self.notebook_main.AddPage(panel_warn, _("Warning"))
        self.notebook_main.AddPage(panel_actions, _("Default Actions"))
        self.notebook_main.AddPage(newpanel, _("Display Options"))

        self.Layout()
        self.restore_aspect()

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
