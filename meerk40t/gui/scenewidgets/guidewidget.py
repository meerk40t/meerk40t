import math

import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_GUIDES
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.scene.widget import Widget


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
        self.calc_area(True, 0, 0)
        self.scaled_conversion_x = 0
        self.scaled_conversion_y = 0
        self.units = None
        self.options = []
        self.pen_guide1 = wx.Pen()
        self.pen_guide2 = wx.Pen()
        self.pen_magnets = wx.Pen()
        self.color_guide1 = None
        self.color_guide2 = None
        self.set_colors()

    def set_colors(self):
        self.color_guide1 = self.scene.colors.color_guide
        self.color_guide2 = self.scene.colors.color_guide2
        self.pen_guide1.SetColour(self.color_guide1)
        self.pen_guide2.SetColour(self.color_guide2)
        self.pen_magnets.SetColour(self.scene.colors.color_magnetline)
        self.pen_magnets.SetWidth(2)

    def hit(self):
        return HITCHAIN_HIT

    def calc_area(self, lower, w, h):
        if lower:
            self.scale_x_lower = 0
            self.scale_x_upper = self.edge_gap + self.line_length
            self.scale_y_lower = 0
            self.scale_y_upper = self.edge_gap + self.line_length
            # Set secondary to primary initially
            self.scale_x2_lower = self.scale_x_lower
            self.scale_x2_upper = self.scale_x_upper
            self.scale_y2_lower = self.scale_y_lower
            self.scale_y2_upper = self.scale_y_upper

        else:

            self.scale_x2_lower = w - self.edge_gap - self.line_length
            self.scale_x2_upper = w
            self.scale_y2_lower = h - self.edge_gap - self.line_length
            self.scale_y2_upper = h

    def contains(self, x, y=None):
        # Slightly more complex than usual due to left, top area
        value = False
        if y is None:
            y = x.y
            x = x.x

        if (
            self.scale_x_lower <= x <= self.scale_x_upper
            or self.scale_y_lower <= y <= self.scale_y_upper
            or self.scale_x2_lower <= x <= self.scale_x2_upper
            or self.scale_y2_lower <= y <= self.scale_y2_upper
        ):
            value = True
        return value

    def set_auto_tick(self, value):
        if value == 0:
            self.scene.auto_tick = True
        else:
            self.scene.auto_tick = False
            self.scene.tick_distance = value
        self.scene._signal_widget(self.scene.widget_root, "grid")
        self.scene.request_refresh()

    def change_tick_event(self, idx):
        value = self.options[idx]
        self.set_auto_tick(value)

    def attract_event(self, value):
        self.scene.magnet_attraction = value

    def affect_event(self, value):
        if value == 0:
            self.scene.magnet_attract_x = not self.scene.magnet_attract_x
        elif value == 1:
            self.scene.magnet_attract_y = not self.scene.magnet_attract_y
        elif value == 2:
            self.scene.magnet_attract_c = not self.scene.magnet_attract_c

    def toggle_circles(self):
        # toggle circular grid
        self.scene.context("scene grid circular\n")

    def toggle_rect(self):
        # toggle primary grid
        self.scene.context("scene grid primary\n")

    def toggle_secondary(self):
        # toggle secondary grid
        self.scene.context("scene grid secondary\n")

    def fill_magnets(self):
        # Let's set the full grid
        p = self.scene.context
        if self.scene.draw_grid_primary:
            tlen = float(
                Length(
                    "{value}{units}".format(
                        value=self.scene.tick_distance, units=p.units_name
                    )
                )
            )

            x = 0
            while x <= p.device.unit_width:
                self.scene.toggle_x_magnet(x)
                x += tlen

            y = 0
            while y <= p.device.unit_height:
                self.scene.toggle_y_magnet(y)
                y += tlen
        elif self.scene.draw_grid_secondary:
            # Placeholder for a use case, as you can define them manually...
            pass

    def event(self, window_pos=None, space_pos=None, event_type=None):
        """
        Capture and deal with the double click event.
        Doubleclick in the grid loads a menu to remove the background.
        """
        _ = self.scene.context._

        def add_scale_options(self, menu):
            kind = wx.ITEM_CHECK if self.scene.auto_tick else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, _("Auto-Scale"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.set_auto_tick(0),
                id=item.GetId(),
            )
            menu.AppendSeparator()
            units = self.scene.context.units_name
            if units == "mm":
                self.options = [1, 5, 10, 25]
            elif units == "cm":
                self.options = [0.1, 0.5, 1, 5]
            elif units == "inch":
                self.options = [0.1, 0.25, 0.5, 1]
            else:  # mils
                self.options = [100, 250, 500, 1000]

            # Not elegant but if used with a loop lambda would take the last value of the loop for all...
            kind = (
                wx.ITEM_CHECK
                if self.scene.tick_distance == self.options[0]
                and not self.scene.auto_tick
                else wx.ITEM_NORMAL
            )
            item = menu.Append(
                wx.ID_ANY,
                "{amount:.2f}{units}".format(amount=self.options[0], units=units),
                "",
                kind,
            )
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.change_tick_event(0),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK
                if self.scene.tick_distance == self.options[1]
                and not self.scene.auto_tick
                else wx.ITEM_NORMAL
            )
            item = menu.Append(
                wx.ID_ANY,
                "{amount:.2f}{units}".format(amount=self.options[1], units=units),
                "",
                kind,
            )
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.change_tick_event(1),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK
                if self.scene.tick_distance == self.options[2]
                and not self.scene.auto_tick
                else wx.ITEM_NORMAL
            )
            item = menu.Append(
                wx.ID_ANY,
                "{amount:.2f}{units}".format(amount=self.options[2], units=units),
                "",
                kind,
            )
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.change_tick_event(2),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK
                if self.scene.tick_distance == self.options[3]
                and not self.scene.auto_tick
                else wx.ITEM_NORMAL
            )
            item = menu.Append(
                wx.ID_ANY,
                "{amount:.2f}{units}".format(amount=self.options[3], units=units),
                "",
                kind,
            )
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.change_tick_event(3),
                id=item.GetId(),
            )

        def add_attraction_strength_menu(self, menu):
            item = menu.Append(
                wx.ID_ANY, _("Attraction strength..."), "", wx.ITEM_NORMAL
            )
            menu.Enable(item.GetId(), False)
            kind = (
                wx.ITEM_CHECK if self.scene.magnet_attraction == 0 else wx.ITEM_NORMAL
            )
            item = menu.Append(wx.ID_ANY, _("Off"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.attract_event(0),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK if self.scene.magnet_attraction == 1 else wx.ITEM_NORMAL
            )
            item = menu.Append(wx.ID_ANY, _("Weak"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.attract_event(1),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK if self.scene.magnet_attraction == 2 else wx.ITEM_NORMAL
            )
            item = menu.Append(wx.ID_ANY, _("Normal"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.attract_event(2),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK if self.scene.magnet_attraction == 3 else wx.ITEM_NORMAL
            )
            item = menu.Append(wx.ID_ANY, _("Strong"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.attract_event(3),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK if self.scene.magnet_attraction == 4 else wx.ITEM_NORMAL
            )
            item = menu.Append(wx.ID_ANY, _("Very Strong"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.attract_event(4),
                id=item.GetId(),
            )
            kind = (
                wx.ITEM_CHECK if self.scene.magnet_attraction == 5 else wx.ITEM_NORMAL
            )
            item = menu.Append(wx.ID_ANY, _("Enormous"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.attract_event(5),
                id=item.GetId(),
            )

        def add_attraction_options_menu(self, menu):
            item = menu.Append(wx.ID_ANY, _("Attraction areas..."), "", wx.ITEM_NORMAL)
            menu.Enable(item.GetId(), False)
            kind = wx.ITEM_CHECK if self.scene.magnet_attract_x else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, _("Left/Right Side"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.affect_event(0),
                id=item.GetId(),
            )
            kind = wx.ITEM_CHECK if self.scene.magnet_attract_y else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, _("Top/Bottom Side"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.affect_event(1),
                id=item.GetId(),
            )
            kind = wx.ITEM_CHECK if self.scene.magnet_attract_c else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, _("Center"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.affect_event(2),
                id=item.GetId(),
            )

        def add_grid_draw_options(self, menu):
            menu.AppendSeparator()
            kind = wx.ITEM_CHECK if self.scene.draw_grid_primary else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, _("Draw primary grid"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.toggle_rect(),
                id=item.GetId(),
            )
            kind = wx.ITEM_CHECK if self.scene.draw_grid_secondary else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, _("Draw secondary grid"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.toggle_secondary(),
                id=item.GetId(),
            )
            # DISABLE, AS NOT YET READY
            # menu.Enable(item.GetId(), False)

            kind = wx.ITEM_CHECK if self.scene.draw_grid_circular else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, _("Draw circular grid"), "", kind)
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                lambda e: self.toggle_circles(),
                id=item.GetId(),
            )

        def process_doubleclick(self):
            # Primary Guide
            secondary = False
            is_y = self.scale_x_lower <= space_pos[0] <= self.scale_x_upper
            if not is_y:
                if self.scene.draw_grid_secondary:
                    is_y = self.scale_x2_lower <= space_pos[0] <= self.scale_x2_upper
                    secondary = True
            is_x = self.scale_y_lower <= space_pos[1] <= self.scale_y_upper
            if not is_x:
                if self.scene.draw_grid_secondary:
                    is_x = self.scale_y2_lower <= space_pos[1] <= self.scale_y2_upper
                    secondary = True
            # print ("is_x=%s, is_y=%s, secondary=%s" % (is_x, is_y, secondary))
            if not (is_x or is_y):
                return

            value = 0
            p = self.scene.context
            if self.scaled_conversion_x == 0:
                return
            p = self.scene.context
            sx = 0
            sy = 0
            tick_distance_x = self.scene.tick_distance
            tick_distance_y = self.scene.tick_distance
            if secondary:
                if not self.scene.grid_secondary_cx is None:
                    sx = self.scene.grid_secondary_cx
                if not self.scene.grid_secondary_cy is None:
                    sy = self.scene.grid_secondary_cy
                if not self.scene.grid_secondary_scale_x is None:
                    tick_distance_x *= self.scene.grid_secondary_scale_x
                if not self.scene.grid_secondary_scale_y is None:
                    tick_distance_y *= self.scene.grid_secondary_scale_y
            ox, oy = self.scene.convert_scene_to_window([sx, sy])

            # print(
            #    "Device-origin=%.1f, %.1f \n ox, oy=%.1f, %.1f"
            #    % (p.device.origin_x, p.device.origin_y, ox, oy)
            # )
            mark_point_x = (window_pos[0] - ox) / self.scaled_conversion_x
            mark_point_y = (window_pos[1] - oy) / self.scaled_conversion_y

            # print(
            #    "OX=%.1f, Oy=%.1f, Mark before x=%.1f, y=%.1f"
            #    % (
            #        ox / self.scaled_conversion_x,
            #        oy / self.scaled_conversion_y,
            #        mark_point_x,
            #        mark_point_y,
            #    )
            # )

            # Make positions stick on ticks (or exactly inbetween)
            mark_point_x = (
                round(2.0 * mark_point_x / tick_distance_x) * 0.5 * tick_distance_x
            )
            mark_point_y = (
                round(2.0 * mark_point_y / tick_distance_y) * 0.5 * tick_distance_y
            )
            if is_x and is_y:
                if self.scene.has_magnets():
                    self.scene.clear_magnets()
                else:
                    self.fill_magnets()
            elif is_x:
                # Get the X coordinate from space_pos [0]
                value = float(Length("%.1f%s" % (mark_point_x, self.units)))
                self.scene.toggle_x_magnet(value)
            elif is_x:
                # Get the X coordinate from space_pos [0]
                value = float(Length("%.1f%s" % (mark_point_x, self.units)))
                self.scene.toggle_x_magnet(value)
            elif is_y:
                # Get the Y coordinate from space_pos [1]
                value = float(Length("%.1f%s" % (mark_point_y, self.units)))
                self.scene.toggle_y_magnet(value)

            self.scene.request_refresh()

        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "rightdown":
            menu = wx.Menu()
            add_scale_options(self, menu)
            menu.AppendSeparator()
            if self.scene.has_magnets():
                item = menu.Append(wx.ID_ANY, _("Clear all magnets"), "")
                self.scene.context.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.scene.clear_magnets(),
                    id=item.GetId(),
                )
                menu.AppendSeparator()
                add_attraction_strength_menu(self, menu)
                menu.AppendSeparator()
                add_attraction_options_menu(self, menu)

            else:
                item = menu.Append(wx.ID_ANY, _("Create magnets along grid"), "")
                self.scene.context.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.fill_magnets(),
                    id=item.GetId(),
                )
            add_grid_draw_options(self, menu)
            self.scene.context.gui.PopupMenu(menu)
            menu.Destroy()
            self.scene.request_refresh()

            return RESPONSE_CONSUME
        elif event_type == "doubleclick":
            process_doubleclick(self)
            return RESPONSE_CONSUME
        else:
            return RESPONSE_CHAIN

    def process_draw(self, gc):
        """
        Draw the guidelines
        """
        if self.scene.context.draw_mode & DRAW_MODE_GUIDES != 0:
            return
        # print ("GuideWidget Draw")
        w, h = gc.Size
        self.calc_area(False, w, h)
        p = self.scene.context
        self.scaled_conversion_x = (
            p.device.length(str(1) + p.units_name, as_float=True)
            * self.scene.widget_root.scene_widget.matrix.value_scale_x()
        )
        self.scaled_conversion_y = (
            p.device.length(str(1) + p.units_name, as_float=True)
            * self.scene.widget_root.scene_widget.matrix.value_scale_y()
        )
        if self.scaled_conversion_x == 0:
            return
        # Establish the delta for about 15 ticks
        # print ("set scene_tick_distance to %f" % delta)
        points_x_primary = self.scene.tick_distance * self.scaled_conversion_x
        points_y_primary = self.scene.tick_distance * self.scaled_conversion_y
        if self.scene.grid_secondary_scale_x is None:
            factor_x_secondary = 1.0
        else:
            factor_x_secondary = self.scene.grid_secondary_scale_x
        if self.scene.grid_secondary_scale_y is None:
            factor_y_secondary = 1.0
        else:
            factor_y_secondary = self.scene.grid_secondary_scale_y

        points_x_secondary = factor_x_secondary * points_x_primary
        points_y_secondary = factor_y_secondary * points_y_primary
        self.units = p.units_name
        # Calculate center position for primary grid
        x = p.device.unit_width * p.device.show_origin_x
        y = p.device.unit_height * p.device.show_origin_y
        sx_primary, sy_primary = self.scene.convert_scene_to_window([x, y])
        #  ... and now for secondary
        if not self.scene.grid_secondary_cx is None:
            x = self.scene.grid_secondary_cx
            relative_x = self.scene.grid_secondary_cx / p.device.unit_width
        else:
            relative_x = p.device.show_origin_x
        if not self.scene.grid_secondary_cy is None:
            y = self.scene.grid_secondary_cy
            relative_y = self.scene.grid_secondary_cy / p.device.unit_height
        else:
            relative_y = p.device.show_origin_y

        sx_secondary, sy_secondary = self.scene.convert_scene_to_window([x, y])

        # Do we need to show the guide regardless of the 'show negative guide' setting?
        show_x_primary = p.device.show_origin_x not in (0.0, 1.0)
        show_y_primary = p.device.show_origin_y not in (0.0, 1.0)

        show_x_secondary = relative_x not in (0.0, 1.0)
        show_y_secondary = relative_y not in (0.0, 1.0)
        if points_x_primary == 0:
            return
        offset_x_primary = float(sx_primary) % points_x_primary
        offset_y_primary = float(sy_primary) % points_y_primary
        offset_x_secondary = float(sx_secondary) % points_x_secondary
        offset_y_secondary = float(sy_secondary) % points_y_secondary

        # print ("The intended scale is in {units} with a tick every {delta} {units}]".format(delta=self.scene.tick_distance, units=self.units))
        # print("Ticks start for x at %.1f, for y at %.1f with a step-size of %.1f, %.1f" % (offset_x_primary, offset_y_primary, points_x_primary, points_y_primary))
        # print("Start-location is at %.1f, %.1f" % (sx_primary, sy_primary))
        length = self.line_length
        edge_gap = self.edge_gap

        gc.SetPen(self.pen_guide1)
        font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, self.color_guide1)
        gc.DrawText(self.units, edge_gap, edge_gap)
        (t_width, t_height) = gc.GetTextExtent("0")

        starts = []
        ends = []
        x = offset_x_primary
        while x < w:
            if x >= 45:
                mark_point = (x - sx_primary) / self.scaled_conversion_x
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if p.device.flip_x:
                    mark_point *= -1
                if mark_point >= 0 or p.show_negative_guide or show_x_primary:
                    starts.append((x, edge_gap))
                    ends.append((x, length + edge_gap))

                    starts.append((x, h - edge_gap))
                    ends.append((x, h - length - edge_gap))
                    # Show half distance as well if there's enough room
                    if t_height < 0.5 * points_x_primary:
                        starts.append((x - 0.5 * points_x_primary, edge_gap))
                        ends.append(
                            (x - 0.5 * points_x_primary, 0.25 * length + edge_gap)
                        )

                    if not self.scene.draw_grid_secondary:
                        starts.append((x, h - edge_gap))
                        ends.append((x, h - length - edge_gap))
                        starts.append((x - 0.5 * points_x_primary, h - edge_gap))
                        ends.append(
                            (x - 0.5 * points_x_primary, h - 0.25 * length - edge_gap)
                        )

                    gc.DrawText("%g" % mark_point, x, edge_gap, -math.tau / 4)
            x += points_x_primary

        y = offset_y_primary
        while y < h:
            if y >= 20:
                mark_point = (y - sy_primary) / self.scaled_conversion_y
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                if p.device.flip_y:
                    mark_point *= -1
                if mark_point >= 0 or p.show_negative_guide or show_y_primary:
                    starts.append((edge_gap, y))
                    ends.append((length + edge_gap, y))
                    # if there is enough room for a mid-distance stroke...
                    if t_height < 0.5 * points_y_primary:
                        starts.append((edge_gap, y - 0.5 * points_y_primary))
                        ends.append(
                            (0.25 * length + edge_gap, y - 0.5 * points_y_primary)
                        )

                    if not self.scene.draw_grid_secondary:
                        starts.append((w - edge_gap, y))
                        ends.append((w - length - edge_gap, y))
                        starts.append((w - edge_gap, y - 0.5 * points_y_primary))
                        ends.append(
                            (w - 0.25 * length - edge_gap, y - 0.5 * points_y_primary)
                        )

                    # gc.DrawText("%g %s" % (mark_point + 0, p.units_name), 0, y + 0)
                    gc.DrawText("%g" % (mark_point + 0), edge_gap, y + 0)
            y += points_y_primary
        if len(starts) > 0:
            gc.StrokeLineSegments(starts, ends)

        # Now the guide for the secondary grid...
        if self.scene.draw_grid_secondary:
            gc.SetPen(self.pen_guide2)
            gc.SetFont(font, self.color_guide2)

            starts = []
            ends = []
            x = offset_x_secondary
            while x < w:
                if x >= 45:
                    mark_point = (x - sx_secondary) / (
                        factor_x_secondary * self.scaled_conversion_x
                    )
                    if round(float(mark_point) * 1000) == 0:
                        mark_point = 0.0  # prevents -0
                    if p.device.flip_x:
                        mark_point *= -1
                    if mark_point >= 0 or p.show_negative_guide or show_x_secondary:
                        starts.append((x, edge_gap))
                        ends.append((x, length + edge_gap))

                        starts.append((x, h - edge_gap))
                        ends.append((x, h - length - edge_gap))
                        # Show half distance as well if there's enough room
                        if t_height < 0.5 * points_x_secondary:
                            starts.append((x - 0.5 * points_x_secondary, h - edge_gap))
                            ends.append(
                                (
                                    x - 0.5 * points_x_secondary,
                                    h - 0.25 * length - edge_gap,
                                )
                            )
                        info = "%g" % mark_point
                        (t_w, t_h) = gc.GetTextExtent(info)
                        gc.DrawText(info, x, h - edge_gap - t_w, -math.tau / 4)
                x += points_x_secondary

            y = offset_y_secondary
            while y < h:
                if y >= 20:
                    mark_point = (y - sy_secondary) / (
                        factor_y_secondary * self.scaled_conversion_y
                    )
                    if round(float(mark_point) * 1000) == 0:
                        mark_point = 0.0  # prevents -0
                    if p.device.flip_y:
                        mark_point *= -1
                    if mark_point >= 0 or p.show_negative_guide or show_y_secondary:
                        starts.append((w - edge_gap, y))
                        ends.append((w - length - edge_gap, y))
                        # if there is enough room for a mid-distance stroke...
                        if t_height < 0.5 * points_y_secondary:
                            starts.append((w - edge_gap, y - 0.5 * points_y_secondary))
                            ends.append(
                                (
                                    w - 0.25 * length - edge_gap,
                                    y - 0.5 * points_y_secondary,
                                )
                            )

                        info = "%g" % (mark_point + 0)
                        (t_w, t_h) = gc.GetTextExtent(info)
                        gc.DrawText(info, w - edge_gap - t_w, y + 0)
                y += points_y_secondary

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
            ends_hi.append((w - length - edge_gap, sy))

        gc.SetPen(self.pen_magnets)
        if starts_hi and ends_hi:
            gc.StrokeLineSegments(starts_hi, ends_hi)

    def signal(self, signal, *args, **kwargs):
        """
        Process guide signal to delete the current guidelines and force them to be recalculated.
        """
        if signal == "guide":
            pass
        elif signal == "theme":
            self.set_colors()
