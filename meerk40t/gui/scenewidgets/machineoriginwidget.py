"""
This widget draws the machine origin as well as the X and Y directions for the
coordinate system being used.

The machine origin is actually the position of the 0,0 location for the device
being used, whereas the coordinate system is the user display space.
"""

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

        # Get the actual machine origin coordinates
        origin_x, origin_y = space.origin_zero()

        # Determine arrow directions based on coordinate system orientation
        arrow_length = 50000  # Length of the arrow in device units

        # X-axis direction: positive X should point right if right_positive, left otherwise
        if space.right_positive:
            x_end_x, x_end_y = origin_x + arrow_length, origin_y + 0
            x_arrow1_x, x_arrow1_y = origin_x + arrow_length - 5000, origin_y + 5000
            x_arrow2_x, x_arrow2_y = origin_x + arrow_length - 5000, origin_y - 5000
        else:
            x_end_x, x_end_y = origin_x - arrow_length, origin_y + 0
            x_arrow1_x, x_arrow1_y = origin_x - arrow_length + 5000, origin_y + 5000
            x_arrow2_x, x_arrow2_y = origin_x - arrow_length + 5000, origin_y - 5000

        # Y-axis direction: positive Y should point down if bottom_positive, up otherwise
        if space.bottom_positive:
            y_end_x, y_end_y = origin_x + 0, origin_y + arrow_length
            y_arrow1_x, y_arrow1_y = origin_x + 5000, origin_y + arrow_length - 5000
            y_arrow2_x, y_arrow2_y = origin_x - 5000, origin_y + arrow_length - 5000
        else:
            y_end_x, y_end_y = origin_x + 0, origin_y - arrow_length
            y_arrow1_x, y_arrow1_y = origin_x + 5000, origin_y - arrow_length + 5000
            y_arrow2_x, y_arrow2_y = origin_x - 5000, origin_y - arrow_length + 5000

        # Convert device coordinates to scene coordinates using space.display.iposition
        origin_dx, origin_dy = space.display.iposition(origin_x, origin_y)
        x_end_dx, x_end_dy = space.display.iposition(x_end_x, x_end_y)
        x_arrow1_dx, x_arrow1_dy = space.display.iposition(x_arrow1_x, x_arrow1_y)
        x_arrow2_dx, x_arrow2_dy = space.display.iposition(x_arrow2_x, x_arrow2_y)
        y_end_dx, y_end_dy = space.display.iposition(y_end_x, y_end_y)
        y_arrow1_dx, y_arrow1_dy = space.display.iposition(y_arrow1_x, y_arrow1_y)
        y_arrow2_dx, y_arrow2_dy = space.display.iposition(y_arrow2_x, y_arrow2_y)

        gc.SetBrush(self.brush)
        try:
            dev0x, dev0y = space.device.view.iposition(0, 0)
            gc.DrawRectangle(dev0x - margin, dev0y - margin, margin * 2, margin * 2)
        except AttributeError:
            # device view does not exist, so we cannot draw the device machine origin widget
            pass

        gc.SetBrush(wx.NullBrush)
        gc.SetPen(self.x_axis_pen)
        # Draw X-axis arrow
        arrow1 = gc.CreatePath()
        arrow1.MoveToPoint((origin_dx, origin_dy))
        arrow1.AddLineToPoint((x_end_dx, x_end_dy))
        arrow1.AddLineToPoint((x_arrow1_dx, x_arrow1_dy))
        arrow1.MoveToPoint((x_end_dx, x_end_dy))
        arrow1.AddLineToPoint((x_arrow2_dx, x_arrow2_dy))
        gc.DrawPath(arrow1)

        gc.SetPen(self.y_axis_pen)
        # Draw Y-axis arrow
        arrow2 = gc.CreatePath()
        arrow2.MoveToPoint((origin_dx, origin_dy))
        arrow2.AddLineToPoint((y_end_dx, y_end_dy))
        arrow2.AddLineToPoint((y_arrow1_dx, y_arrow1_dy))
        arrow2.MoveToPoint((y_end_dx, y_end_dy))
        arrow2.AddLineToPoint((y_arrow2_dx, y_arrow2_dy))
        gc.DrawPath(arrow2)
