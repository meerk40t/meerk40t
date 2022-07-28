import wx
from ...core.element_types import elem_nodes
from .statusbarwidget import StatusBarWidget
from ...core.units import UNITS_PER_INCH, Length

_ = wx.GetTranslation

class SBW_Information(StatusBarWidget):
    """
    Placeholder to accept any kind of information,
    if none is given externally it falls back to basic infos
    about the emphasized elements
    """
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
        self._externalinfo = None
        self.PrependSpacer(5)
        self.Add(self.info_text, 1, wx.EXPAND, 0)

    def SetInformation(self, msg):
        self._externalinfo = msg
        self.StartPopulation()
        self.info_text.SetLabel("" if msg is None else msg)
        self.EndPopulation()

    def Signal(self, signal, **args):
        if signal == "emphasized" and self._externalinfo is not None:
            elements = self.context.elements
            ct = 0
            total_area = 0
            total_length = 0
            _mm = float(Length("1{unit}".format(unit="mm")))
            msg = ""
            for e in elements.flat(types=elem_nodes, emphasized=True):
                ct += 1
                this_area, this_length = elements.get_information(e, fine=False)
                total_area += this_area
                total_length += this_length

            if ct > 0:
                total_area = total_area / (_mm * _mm)
                total_length = total_length / _mm
                msg = "# = %d, A = %.1f mm², D = %.1f mm" % (ct, total_area, total_length)
            self.StartPopulation()
            self.info_text.SetLabel(msg)
            self.EndPopulation()
