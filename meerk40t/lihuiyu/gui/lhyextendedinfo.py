import wx

from meerk40t.device.gui.defaultactions import DefaultActionPanel
from meerk40t.device.gui.formatterpanel import FormatterPanel
from meerk40t.device.gui.warningpanel import WarningPanel
from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icons8_administrative_tools
from meerk40t.gui.mwindow import MWindow
from meerk40t.gui.wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    TextCtrl,
    dip_size,
    wxCheckBox,
)
from meerk40t.kernel import signal_listener

_ = wx.GetTranslation


class LihuiyuBoardInformation(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(550, 700, *args, **kwds)
        self.context = self.context.device
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_administrative_tools.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Lihuiyu-Board Information"))

        # self.notebook_main = wx.Notebook(self, wx.ID_ANY)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)

        self.panels = []
        panel_info = ChoicePropertyPanel(
            self.notebook_main,
            wx.ID_ANY,
            context=self.context,
            choices=("lhy-information"),
        )

        panel_write = ChoicePropertyPanel(
            self,
            wx.ID_ANY,
            context=self.context,
            choices=("lhy-overwrite"),
        )

        self.panels.append(panel_info)
        self.panels.append(panel_write)

        self.notebook_main.AddPage(panel_info, _("Board Information"))
        self.notebook_main.AddPage(panel_write, _("Hardware Overwrite"))

        self.Layout()
        self.restore_aspect(honor_initial_values=True)

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
        return "Device-Info", "Board Information"
