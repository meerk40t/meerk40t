import wx

from meerk40t.gui.toolwidgets.toolwidget import ToolWidget

from ...core.units import UNITS_PER_MM


class RelocateTool(ToolWidget):
    """
    Relocate laser Tool.

    Adds Circle with click and drag.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.p1 = None
        self.p2 = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.p1 is not None and self.p2 is not None:
            x0 = min(self.p1.real, self.p2.real)
            y0 = min(self.p1.imag, self.p2.imag)
            x1 = max(self.p1.real, self.p2.real)
            y1 = max(self.p1.imag, self.p2.imag)
            gc.SetPen(wx.BLUE_PEN)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawEllipse(x0, y0, x1 - x0, y1 - y0)

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftdown":
            bed_width = self.scene.context.device.unit_width
            bed_height = self.scene.context.device.unit_height
            x = space_pos[0]
            y = space_pos[1]
            if x > bed_width:
                x = bed_width
            if y > bed_height:
                y = bed_height
            if x < 0:
                x = 0
            if y < 0:
                y = 0
            x /= UNITS_PER_MM
            y /= UNITS_PER_MM
            self.scene.context("move_absolute {x}mm {y}mm\n".format(x=x, y=y))
