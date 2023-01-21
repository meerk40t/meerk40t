import wx
from meerk40t.gui.scene.sceneconst import  RESPONSE_CONSUME
from meerk40t.gui.utilitywidgets.handlewidget import HandleWidget

from meerk40t.gui import icons


class ScaleWidget(HandleWidget):
    """
    ButtonWidget serves as an onscreen button backed by a bitmap that when clicked calls the click() function.
    This is a general scene button widget.
    """

    def __init__(self, scene, left, top, right, bottom):
        super().__init__(scene, left, top, right, bottom, icons.icons8_resize_horizontal_50.GetBitmap(use_theme=False))
        self.scale = 1.0
        self.current_scale = 1.0
        self.scale_one_distance = (right - left) * 5
        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.RED)
        self.tool_pen.SetWidth(1000)
        self.tool = None

    def draw(self, gc: wx.GraphicsContext):
        super().draw(gc)
        if not self.tool:
            return
        gc.SetPen(self.tool_pen)
        gc.StrokeLine((self.left + self.right) / 2.0, (self.top + self.bottom) / 2.0, self.tool[0], self.tool[1])

    def apply_scale(self, scale):
        try:
            self.parent.scale = scale
        except AttributeError:
            pass

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type in ("hover", "hover_start", "hover_end"):
            return RESPONSE_CONSUME
        if event_type == "leftup":
            self.tool = None
            self.scale = 1.0
        elif event_type == "leftclick":
            self.scale = self.current_scale
            self.tool = None
        elif event_type == "move":
            dx = space_pos[0] - (self.left + self.right) / 2
            dy = space_pos[1] - (self.top + self.bottom) / 2
            d = max(dx, dy)
            scale_distance = self.scale_one_distance * self.scale
            self.current_scale = (d + scale_distance) / scale_distance
            self.current_scale *= self.scale
            self.apply_scale(self.current_scale * self.current_scale)
            self.tool = space_pos[:2]
        self.scene.toast(f"scale {self.current_scale:02f}")

        return RESPONSE_CONSUME
