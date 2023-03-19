import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools_50
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class RuidaConfiguration(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(420, 570, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools_50.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_(_("Ruida-Configuration")))

        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )

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
        return ("Device-Settings", "Configuration")
