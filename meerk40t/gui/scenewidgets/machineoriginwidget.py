import wx

from meerk40t.gui.laserrender import DRAW_MODE_BACKGROUND, swizzlecolor
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN
from meerk40t.gui.scene.widget import Widget


class MachineOriginWidget(Widget):
    """
    Machine Origin Interface Widget
    """

    def __init__(self, scene, name=None):
        Widget.__init__(self, scene, all=True)
        self.name = name
        self.brush = wx.Brush(
            colour=wx.Colour(255, 0, 0, alpha=127), style=wx.BRUSHSTYLE_SOLID
        )
        self.x_axis_pen = wx.Pen(colour=wx.Colour(255, 0, 0))
        self.x_axis_pen.SetWidth(1000)
        self.y_axis_pen = wx.Pen(colour=wx.Colour(0, 255, 0))
        self.y_axis_pen.SetWidth(1000)

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        """
        """
        return RESPONSE_CHAIN

    def process_draw(self, gc):
        """
        Draws the background on the scene.
        """
        if self.scene.context.draw_mode & DRAW_MODE_BACKGROUND == 0:
            margin = 5000
            context = self.scene.context
            x, y = context.device.device_to_scene_position(0, 0)
            x_dx, x_dy = context.device.device_to_scene_position(500, 0)
            y_dx, y_dy = context.device.device_to_scene_position(0, 500)
            gc.SetBrush(self.brush)
            gc.DrawRectangle(x - margin, y - margin, margin * 2, margin * 2)
            gc.SetPen(self.x_axis_pen)
            gc.DrawLines([(x, y), (x_dx, x_dy)])
            gc.SetPen(self.y_axis_pen)
            gc.DrawLines([(x, y), (y_dx, y_dy)])
