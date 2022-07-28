import wx
from .statusbarwidget import StatusBarWidget

_ = wx.GetTranslation

class SBW_Information(StatusBarWidget):
    def __init__(self, parent, panelidx, identifier, context, **args):
        super().__init__(parent, panelidx, identifier, context, args)
        FONT_SIZE = 7
        self.info_text = wx.StaticText(self.parent, wx.ID_ANY, label="")
        self.info_text.SetFont(
            wx.Font(
                FONT_SIZE,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        self.PrependSpacer(5)
        self.Add(self.info_text, 1, wx.EXPAND, 0)

    def SetInformation(self, msg):
        self.StartPopulation()
        self.info_text.SetLabel(msg)
        self.EndPopulation()