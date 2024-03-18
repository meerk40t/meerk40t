
import wx

from meerk40t.gui.choicepropertypanel import ChoicePropertyPanel
from meerk40t.gui.icons import icon_barrel_distortion
from meerk40t.gui.mwindow import MWindow

_ = wx.GetTranslation


class CylinderSettings(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(700, 350, *args, **kwds)
        self.panel = ChoicePropertyPanel(
            self, wx.ID_ANY, context=self.context.device, choices="cylinder"
        )
        self.sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.add_module_delegate(self.panel)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_barrel_distortion.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("Cylinder-Correction"))
        self.restore_aspect(honor_initial_values=True)

    def window_open(self):
        self.panel.pane_show()

    def window_close(self):
        self.panel.pane_hide()

    @staticmethod
    def submenu():
        return "Device-Settings", "Cylinder-Correction"
