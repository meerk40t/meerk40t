import math

import wx

from meerk40t.gui.laserrender import DRAW_MODE_GUIDES
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.core.units import Length


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
        self.scaled_conversion = 0
        self.units = None
        self.options = []

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

    def set_auto_tick(self, value):
        if value == 0:
            self.scene.auto_tick = True
        else:
            self.scene.auto_tick = False
            self.scene.tick_distance = value

    def menu_event(self, idx):
        value = self.options[idx]
        self.set_auto_tick(value)

    def fill_magnets(self):
        # Lets set the full grid
        p = self.scene.context
        tlen= float(Length("{value}{units}".format(value=self.scene.tick_distance, units=p.units_name)))

        x = 0
        while x <= p.device.unit_width:
            self.scene.toggle_x_magnet(x)
            x += tlen

        y = 0
        while y <= p.device.unit_height:
            self.scene.toggle_y_magnet(y)
            y += tlen


    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Capture and deal with the doubleclick event.

        Doubleclick in the grid loads a menu to remove the background.
        """
        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "rightdown":
            menu = wx.Menu()
            _ = self.scene.context._
            item = menu.Append(wx.ID_ANY, _("Auto-Scale"), "")
            self.scene.context.gui.Bind(wx.EVT_MENU, lambda e: self.set_auto_tick(0), id=item.GetId(),)
            menu.AppendSeparator()

            units = self.scene.context.units_name
            if units=="mm":
                self.options = [1, 5, 10, 25]
            elif units=="cm":
                self.options = [0.1, 0.5, 1, 5]
            elif units=="inch":
                self.options = [0.1, 0.25, 0.5, 1]
            else: # mils
                self.options = [100, 250, 500, 1000]
            # Not elegant but if used with a loop lambda would take the last value of the loop for all...
            item = menu.Append(wx.ID_ANY, "{amount:.2f}{units}".format(amount=self.options[0], units=units), "")
            self.scene.context.gui.Bind(wx.EVT_MENU, lambda e: self.menu_event(0), id=item.GetId(),)
            item = menu.Append(wx.ID_ANY, "{amount:.2f}{units}".format(amount=self.options[1], units=units), "")
            self.scene.context.gui.Bind(wx.EVT_MENU, lambda e: self.menu_event(1), id=item.GetId(),)
            item = menu.Append(wx.ID_ANY, "{amount:.2f}{units}".format(amount=self.options[2], units=units), "")
            self.scene.context.gui.Bind(wx.EVT_MENU, lambda e: self.menu_event(2), id=item.GetId(),)
            item = menu.Append(wx.ID_ANY, "{amount:.2f}{units}".format(amount=self.options[3], units=units), "")
            self.scene.context.gui.Bind(wx.EVT_MENU, lambda e: self.menu_event(3), id=item.GetId(),)
            menu.AppendSeparator()
            if self.scene.has_magnets():
                item = menu.Append(wx.ID_ANY, _("Clear all magnets"), "")
                self.scene.context.gui.Bind(wx.EVT_MENU, lambda e: self.scene.clear_magnets(), id=item.GetId(),)
            else:
                item = menu.Append(wx.ID_ANY, _("Create magnets along grid"), "")
                self.scene.context.gui.Bind(wx.EVT_MENU, lambda e: self.fill_magnets(), id=item.GetId(),)

            self.scene.context.gui.PopupMenu(menu)
            menu.Destroy()
            self.scene.request_refresh()

            return RESPONSE_CONSUME
        elif event_type == "doubleclick":

            is_y = self.scale_x_lower <= space_pos[0] <= self.scale_x_upper
            is_x = self.scale_y_lower <= space_pos[1] <= self.scale_y_upper
            value = 0
            p = self.scene.context
            if self.scaled_conversion == 0:
                return
            p = self.scene.context
            sx, sy = self.scene.convert_scene_to_window(
                [
                    p.device.unit_width * p.device.origin_x,
                    p.device.unit_height * p.device.origin_y,
                ]
            )
            mark_point_x = (window_pos[0] - sx) / self.scaled_conversion
            mark_point_y = (window_pos[1] - sy) / self.scaled_conversion
            # Make positions stick on ticks (or exactly inbetween)
            mark_point_x = round(2.0 * mark_point_x / self.scene.tick_distance) * 0.5 * self.scene.tick_distance
            mark_point_y = round(2.0 * mark_point_y / self.scene.tick_distance) * 0.5 * self.scene.tick_distance
            #print(
            #    "Coordinates: x=%.1f, y=%.1f, sx=%.1f, sy=%.1f, mark-x=%.1f, y=%.1f"
            #    % (window_pos[0], window_pos[1], sx, sy, mark_point_x, mark_point_y)
            #)
            if is_x and is_y:
                if self.scene.has_magnets():
                    self.scene.clear_magnets()
                else:
                    self.fill_magnets()
            elif is_x:
                # Get the X coordinate from space_pos [0]
                value = float(Length("%.1f%s"%(mark_point_x, self.units)))
                self.scene.toggle_x_magnet(value)
            elif is_y:
                # Get the Y coordinate form space_pos [1]
                value = float(Length("%.1f%s"%(mark_point_y, self.units)))
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
        # print ("GuideWidget Draw")
        gc.SetPen(wx.BLACK_PEN)
        w, h = gc.Size
        p = self.scene.context
        self.scaled_conversion = (
            p.device.length(str(1) + p.units_name, as_float=True)
            * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
        if self.scaled_conversion == 0:
            return
        # Establish the delta for about 15 ticks
        # print ("set scene_tick_distance to %f" % delta)
        points = self.scene.tick_distance * self.scaled_conversion
        self.units = p.units_name

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

        # print ("The intended scale is in {units} with a tick every {delta} {units}]".format(delta=self.scene.tick_distance, units=self.units))

        starts = []
        ends = []
        x = offset_x
        length = self.line_length
        edge_gap = self.edge_gap
        font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, wx.BLACK)
        gc.DrawText(self.units, edge_gap, edge_gap)
        while x < w:
            if x >= 45:
                mark_point = (x - sx) / self.scaled_conversion
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if p.device.flip_x:
                    mark_point *= -1
                starts.append((x, edge_gap))
                ends.append((x, length + edge_gap))

                starts.append((x, h - edge_gap))
                ends.append((x, h - length - edge_gap))
                # Show half distance as well
                starts.append((x-0.5*points, edge_gap))
                ends.append((x-0.5*points, 0.25 * length + edge_gap))

                starts.append((x, h - edge_gap))
                ends.append((x, h - length - edge_gap))
                starts.append((x-0.5*points, h - edge_gap))
                ends.append((x-0.5*points, h - 0.25*length - edge_gap))

                gc.DrawText("%g" % mark_point, x, edge_gap, -math.tau / 4)
            x += points

        y = offset_y
        while y < h:
            if y >= 20:
                mark_point = (y - sy) / self.scaled_conversion
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if p.device.flip_y:
                    mark_point *= -1
                if mark_point >= 0 or p.show_negative_guide:
                    starts.append((edge_gap, y))
                    ends.append((length + edge_gap, y))
                    starts.append((edge_gap, y-0.5*points))
                    ends.append((0.25*length + edge_gap, y-0.5*points))

                    starts.append((w - edge_gap, y))
                    ends.append((w - length - edge_gap, y))
                    starts.append((w - edge_gap, y-0.5*points))
                    ends.append((w - 0.25* length - edge_gap, y-0.5*points))

                    # gc.DrawText("%g %s" % (mark_point + 0, p.units_name), 0, y + 0)
                    gc.DrawText("%g" % (mark_point + 0), edge_gap, y + 0)
            y += points
        if len(starts) > 0:
            gc.StrokeLineSegments(starts, ends)

        starts_hi = []
        ends_hi = []

        for x in self.scene.magnet_x:
            sx, sy = self.scene.convert_scene_to_window([x, 0])
            starts_hi.append((sx, length + edge_gap))
            ends_hi.append((sx, h - length - edge_gap))

        for y in self.scene.magnet_y:
            sx, sy = self.scene.convert_scene_to_window([0, y])
            starts_hi.append((length + edge_gap, sy))
            ends_hi.append((w- length - edge_gap, sy))

        grid_line_high_pen = wx.Pen()
        grid_line_high_pen.SetColour(wx.Colour(0xFF, 0xA0, 0xA0))
        grid_line_high_pen.SetWidth(2)

        gc.SetPen(grid_line_high_pen)
        if starts_hi and ends_hi:
            gc.StrokeLineSegments(starts_hi, ends_hi)

    def signal(self, signal, *args, **kwargs):
        """
        Process guide signal to delete the current guidelines and force them to be recalculated.
        """
        if signal == "guide":
            pass
