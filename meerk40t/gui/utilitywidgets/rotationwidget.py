import math

import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CONSUME
from meerk40t.gui.utilitywidgets.handlewidget import HandleWidget
from meerk40t.tools.geomstr import Geomstr


class RotationWidget(HandleWidget):

    def __init__(self, scene, left, top, right, bottom, bitmap, apply_delta):
        super().__init__(scene, left, top, right, bottom, bitmap)
        self.tool = None
        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.RED)
        self.tool_pen.SetWidth(1000)
        self.apply_delta = apply_delta

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):

        if event_type == "leftup":
            self.tool = None
        if event_type == "move":
            cx = (self.left + self.right) / 2.0
            cy = (self.top + self.bottom) / 2.0
            angle_previous = Geomstr.angle(None, complex(cx, cy), complex(*space_pos[2:3]))
            if math.isnan(angle_previous):
                return RESPONSE_CONSUME
            angle_current = Geomstr.angle(None, complex(cx, cy), complex(*space_pos[0:2]))

            delta_theta = angle_current - angle_previous
            if delta_theta > math.tau / 2:
                delta_theta -= math.tau
            if delta_theta < -math.tau / 2:
                delta_theta += math.tau
            if not math.isnan(delta_theta):
                self.apply_delta(delta_theta)
            self.tool = list(space_pos[0:2])
        return RESPONSE_CONSUME

    def draw(self, gc):
        super().draw(gc)
        if self.tool is not None:
            cx = (self.left + self.right) / 2.0
            cy = (self.top + self.bottom) / 2.0
            gc.SetPen(self.tool_pen)
            gc.DrawLine((cx, cy), self.tool)

