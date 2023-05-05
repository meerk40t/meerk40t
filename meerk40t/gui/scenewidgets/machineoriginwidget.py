import wx

from meerk40t.gui.laserrender import DRAW_MODE_ORIGIN
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
        """ """
        return RESPONSE_CHAIN

    def process_draw(self, gc):
        """
        Draws the background on the scene.
        """
        if self.scene.context.draw_mode & DRAW_MODE_ORIGIN != 0:
            return
        gcmat = gc.GetTransform()
        mat_param = gcmat.Get()
        if mat_param[0] == 1 and mat_param[3] == 1:
            # We were called without a matrix applied, that's plain wrong
            return
        margin = 5000
        space = self.scene.context.space
        x, y = space.display.iposition(0, 0)
        x_dx, x_dy = space.display.iposition(50000, 0)
        xa1_dx, xa1_dy = space.display.iposition(45000, 5000)
        xa2_dx, xa2_dy = space.display.iposition(45000, -5000)
        y_dx, y_dy = space.display.iposition(0, 50000)
        ya1_dx, ya1_dy = space.display.iposition(5000, 45000)
        ya2_dx, ya2_dy = space.display.iposition(-5000, 45000)
        dev0x, dev0y = self.scene.context.device.device_to_scene_position(0, 0)
        gc.SetBrush(self.brush)
        gc.DrawRectangle(dev0x - margin, dev0y - margin, margin * 2, margin * 2)

        gc.SetBrush(wx.NullBrush)
        gc.SetPen(self.x_axis_pen)
        gc.DrawLines(
            [(x, y), (x_dx, x_dy), (xa1_dx, xa1_dy), (x_dx, x_dy), (xa2_dx, xa2_dy)]
        )
        gc.SetPen(self.y_axis_pen)
        gc.DrawLines(
            [(x, y), (y_dx, y_dy), (ya1_dx, ya1_dy), (y_dx, y_dy), (ya2_dx, ya2_dy)]
        )
