"""
ScaleWidget provides scaling functionality to the parent that includes this widget. We assume this parent has an
attribute called .scale. This is changed by dragging the scaled widget which should draw a rectangle indicating the
scale amount. The starting point is 1:1 scaling. And moving further to the left can cause a scale-down effect.
"""

import wx
from meerk40t.gui.scene.sceneconst import  RESPONSE_CONSUME
from meerk40t.gui.utilitywidgets.handlewidget import HandleWidget

from meerk40t.gui import icons


class ScaleWidget(HandleWidget):
    def __init__(self, scene, left, top, right, bottom):
        super().__init__(scene, left, top, right, bottom, icons.icons8_resize_horizontal_50.GetBitmap(use_theme=False))
        self.scale = 1.0
        self.current_scale = 1.0
        self.scale_one_distance = (right - left) * 5
        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.RED)
        self.tool_pen.SetWidth(1000)
        self.rect = None

    def draw(self, gc: wx.GraphicsContext):
        super().draw(gc)
        if not self.rect:
            return
        gc.SetPen(self.tool_pen)
        if self.rect:
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.DrawRectangle(*self.rect)

    def apply_scale(self, scale):
        try:
            self.parent.scale = scale
        except AttributeError:
            pass

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type in ("hover", "hover_start", "hover_end"):
            return RESPONSE_CONSUME
        if event_type == "leftup":
            self.rect = None
            self.scale = 1.0
        elif event_type == "leftclick":
            self.scale = self.current_scale
            self.rect = None
        elif event_type == "move":
            dx = space_pos[0] - (self.left + self.right) / 2
            dy = space_pos[1] - (self.top + self.bottom) / 2
            d = max(dx, dy)
            scale_distance = self.scale_one_distance * self.scale
            self.current_scale = (d + scale_distance) / scale_distance
            self.current_scale *= self.scale
            self.apply_scale(self.current_scale * self.current_scale)
            cx = (self.left + self.right) / 2.0
            cy = (self.top + self.bottom) / 2.0
            left, top, right, bottom = cx - scale_distance, cy - scale_distance, cx + d, cy + d
            self.rect = left, top, right - left, bottom - top
        self.scene.toast(f"scale {self.current_scale:02f}")

        return RESPONSE_CONSUME
