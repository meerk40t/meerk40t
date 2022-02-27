import math

import wx

from meerk40t.gui.laserrender import DRAW_MODE_GUIDES
from meerk40t.gui.scene.scene import Widget


class GuideWidget(Widget):
    """
    Interface Widget

    Guide lines drawn at along the scene edges.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.scene.context.setting(bool, "show_negative_guide", True)

    def process_draw(self, gc):
        """
        Draw the guide lines
        """
        if self.scene.context.draw_mode & DRAW_MODE_GUIDES != 0:
            return
        gc.SetPen(wx.BLACK_PEN)
        w, h = gc.Size
        p = self.scene.context
        scaled_conversion = (
            p.device.length(str(1) + p.units_name, as_float=True)
            * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
        if scaled_conversion == 0:
            return
        edge_gap = 5
        wpoints = w / 15.0
        hpoints = h / 15.0
        points = min(wpoints, hpoints)
        # tweak the scaled points into being useful.
        # points = scaled_conversion * round(points / scaled_conversion * 10.0) / 10.0
        points = scaled_conversion * float("{:.1g}".format(points / scaled_conversion))
        sx, sy = self.scene.convert_scene_to_window([0, 0])
        if points == 0:
            return
        offset_x = sx % points
        offset_y = sy % points

        starts = []
        ends = []
        x = offset_x
        length = 20
        font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.BLACK)
        gc.DrawText(p.units_name, edge_gap, edge_gap)
        while x < w:
            if x >= 45:
                mark_point = (x - sx) / scaled_conversion
                if round(mark_point * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                starts.append((x, edge_gap))
                ends.append((x, length + edge_gap))

                starts.append((x, h - edge_gap))
                ends.append((x, h - length - edge_gap))

                gc.DrawText("%g" % mark_point, x, edge_gap, -math.tau / 4)
            x += points

        y = offset_y
        while y < h:
            if y >= 20:
                mark_point = (y - sy) / scaled_conversion
                if round(mark_point * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if mark_point >= 0 or p.show_negative_guide:
                    starts.append((edge_gap, y))
                    ends.append((length + edge_gap, y))

                    starts.append((w - edge_gap, y))
                    ends.append((w - length - edge_gap, y))

                    # gc.DrawText("%g %s" % (mark_point + 0, p.units_name), 0, y + 0)
                    gc.DrawText("%g" % (mark_point + 0), edge_gap, y + 0)
            y += points
        if len(starts) > 0:
            gc.StrokeLineSegments(starts, ends)

    def signal(self, signal, *args, **kwargs):
        """
        Process guide signal to delete the current guide lines and force them to be recalculated.
        """
        if signal == "guide":
            pass
