import wx


class CircleBrush:
    """
    Circular Brush to be drawn for area-based tools.
    """

    def __init__(self):
        self.tool_size = 100
        self.pos = 0 + 0j
        self.scale = 1.0
        self.range = self.tool_size * self.scale
        self.brush_fill = wx.Brush(wx.Colour(alpha=64, red=0, green=255, blue=0))
        self.using = False

    def set_location(self, x: float, y: float):
        self.pos = complex(x, y)

    def contains(self, x: float, y: float) -> bool:
        c = complex(x, y)
        return abs(self.pos - c) < self.range

    def draw(self, gc: wx.GraphicsContext):
        if self.using:
            self.draw_brush(gc)

    def draw_brush(self, gc: wx.GraphicsContext):
        gc.SetBrush(self.brush_fill)
        gc.DrawEllipse(
            self.pos.real - self.tool_size / 2.0,
            self.pos.imag - self.tool_size / 2.0,
            self.tool_size,
            self.tool_size,
        )
