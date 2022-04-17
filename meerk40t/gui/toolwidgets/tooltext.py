import wx

from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import SVGText

from ...core.units import UNITS_PER_PIXEL
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME


class TextTool(ToolWidget):
    """
    Text Drawing Tool

    Adds Text at set location.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.x = None
        self.y = None
        self.text = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.text is not None:
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawText(self.text.text, self.x, self.y)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.p1 = complex(space_pos[0], space_pos[1])
            _ = self.scene.context._
            self.text = SVGText("")
            x = space_pos[0]
            y = space_pos[1]
            self.x = x
            self.y = y
            self.text *= "translate({x}, {y}) scale({scale})".format(
                x=x, y=y, scale=UNITS_PER_PIXEL
            )
            dlg = wx.TextEntryDialog(
                self.scene.gui, _("What text message"), _("Text"), ""
            )
            dlg.SetValue("")
            if dlg.ShowModal() == wx.ID_OK:
                self.text.text = dlg.GetValue()
                self.scene.context.elements.add_elem(self.text, classify=True)
                self.text = None
            dlg.Destroy()
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        return response
