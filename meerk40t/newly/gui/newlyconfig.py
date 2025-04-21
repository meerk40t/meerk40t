import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.device.gui.effectspanel import EffectsPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class NewlyConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(420, 570, *args, **kwds)
        self.context = self.context.device
        self.SetHelpText("newlyconfig")
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Newly-Configuration"))

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

        options = (
            ("newly", _("Newly")),
            ("newly-specific", _("Device")),
            ("newly-global", _("Global")),
        )
        self.panels = []
        for item in options:
            section = item[0]
            pagetitle = _(item[1])
            addpanel = self.visible_choices(section)
            if addpanel:
                newpanel = ChoicePropertyPanel(
                    self, wx.ID_ANY, context=self.context, choices=section
                )
                self.panels.append(newpanel)
                self.notebook_main.AddPage(newpanel, pagetitle)
        newpanel = ChoicePropertyPanel(
            self, id=wx.ID_ANY, context=self.context, choices="newly-speedchart"
        )
        self.panels.append(newpanel)
        self.notebook_main.AddPage(newpanel, _("Raster Chart"))

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
        self.restore_aspect()

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

    def visible_choices(self, section):
        result = False
        devmode = self.context.root.setting(bool, "developer_mode", False)
        choices = self.context.lookup("choices", section)
        if choices is not None:
            for item in choices:
                try:
                    dummy = str(item["hidden"])
                    if dummy == "" or dummy == "0":
                        hidden = False
                    else:
                        hidden = False if devmode else True
                except KeyError:
                    hidden = False
                if not hidden:
                    result = True
                    break
        return result

    @staticmethod
    def submenu():
        return "Device-Settings", "Configuration"
