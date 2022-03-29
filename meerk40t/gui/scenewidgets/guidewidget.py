import math

import wx

from meerk40t.gui.laserrender import DRAW_MODE_GUIDES
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.core.units import PX_PER_UNIT, UNITS_PER_PIXEL, Length


class GuideWidget(Widget):
    """
    Interface Widget

    Guidelines drawn at along the scene edges.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.scene.context.setting(bool, "show_negative_guide", True)
        self.edge_gap = 5
        self.line_length = 20
        self.scale_x_lower = self.edge_gap
        self.scale_x_upper = self.scale_x_lower + self.line_length
        self.scale_y_lower = self.edge_gap
        self.scale_y_upper = self.scale_y_lower + self.line_length

    def hit(self):
        return HITCHAIN_HIT

    def contains(self, x, y=None):
        # Slightly more complex than usual due to left, top area
        value = False
        if y is None:
            y = x.y
            x = x.x

        if (
            self.scale_x_lower <= x <= self.scale_x_upper
            or self.scale_y_lower <= y <= self.scale_y_upper
        ):
            value = True
        return value

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Capture and deal with the doubleclick event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "doubleclick":
            value = 0
            p = self.scene.context
            scaled_conversion = (
                p.device.length(str(1) + p.units_name, as_float=True)
                * self.scene.widget_root.scene_widget.matrix.value_scale_x()
            )
            sx, sy = self.scene.convert_scene_to_window(
                [
                    p.device.unit_width * p.device.origin_x,
                    p.device.unit_height * p.device.origin_y,
                ]
            )
            mark_point_x = (window_pos[0] - sx) / scaled_conversion
            mark_point_y = (window_pos[0] - sx) / scaled_conversion
            print(
                "Coordinates: x=%.1f, y=%.1f, sx=%.1f, sy=%.1f, mark-x=%.1f, y=%.1f"
                % (window_pos[0], window_pos[1], sx, sy, mark_point_x, mark_point_y)
            )

            cx, cy = p.device.physical_to_scene_position(
                window_pos[0] - sx, window_pos[1] - sy, UNITS_PER_PIXEL
            )
            print("cx=%.1f, cy=%.1f" % (cx, cy))
            is_y = self.scale_x_lower <= space_pos[0] <= self.scale_x_upper
            is_x = self.scale_y_lower <= space_pos[1] <= self.scale_y_upper
            if is_x and is_y:
                self.scene.clear_magnets()
            elif is_x:
                # Get the X coordinate from space_pos [0]
                value = cx
                self.scene.toggle_x_magnet(value)
            elif is_y:
                # Get the Y coordinate form space_pos [1]
                value = cy
                self.scene.toggle_y_magnet(value)

            self.scene.request_refresh()
            return RESPONSE_CONSUME
        else:
            return RESPONSE_CHAIN

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
        wpoints = w / 15.0
        hpoints = h / 15.0
        points = min(wpoints, hpoints)
        # tweak the scaled points into being useful.
        # points = scaled_conversion * round(points / scaled_conversion * 10.0) / 10.0
        points = scaled_conversion * float("{:.1g}".format(points / scaled_conversion))
        sx, sy = self.scene.convert_scene_to_window(
            [
                p.device.unit_width * p.device.origin_x,
                p.device.unit_height * p.device.origin_y,
            ]
        )
        if points == 0:
            return
        offset_x = float(sx) % points
        offset_y = float(sy) % points

        starts = []
        ends = []
        x = offset_x
        length = self.line_length
        edge_gap = self.edge_gap
        font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.BLACK)
        gc.DrawText(p.units_name, edge_gap, edge_gap)
        while x < w:
            if x >= 45:
                mark_point = (x - sx) / scaled_conversion
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if p.device.flip_x:
                    mark_point *= -1
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
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if p.device.flip_y:
                    mark_point *= -1
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
        Process guide signal to delete the current guidelines and force them to be recalculated.
        """
        if signal == "guide":
            pass
