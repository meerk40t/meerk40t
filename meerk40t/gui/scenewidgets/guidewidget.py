import math

import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_GUIDES
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.scene.widget import Widget

_ = wx.GetTranslation


class GuideWidget(Widget):
    """
    Interface Widget

    Guidelines drawn at along the scene edges.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.edge_gap = 5
        self.line_length = 20
        self.scale_x_lower = 0
        self.scale_x_upper = self.edge_gap + self.line_length
        self.scale_y_lower = 0
        self.scale_y_upper = self.edge_gap + self.line_length
        # Set secondary to primary initially
        self.scale_x2_lower = self.scale_x_lower
        self.scale_x2_upper = self.scale_x_upper
        self.scale_y2_lower = self.scale_y_lower
        self.scale_y2_upper = self.scale_y_upper
        self.scaled_conversion_x = 0
        self.scaled_conversion_y = 0
        self.units = None
        self.options = []
        self.pen_guide1 = wx.Pen()
        self.pen_guide2 = wx.Pen()
        self.pen_magnets = wx.Pen()
        self.color_units = None
        self.color_guide1 = None
        self.color_guide2 = None
        self.set_colors()
        self.font = wx.Font(
            10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )

    def set_colors(self):
        self.color_units = self.scene.colors.color_guide
        self.color_guide1 = self.scene.colors.color_guide
        self.color_guide2 = self.scene.colors.color_guide2
        self.pen_guide1.SetColour(self.color_guide1)
        self.pen_guide2.SetColour(self.color_guide2)
        self.pen_magnets.SetColour(self.scene.colors.color_magnetline)
        self.pen_magnets.SetWidth(2)

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
            tlen = float(Length(f"{self.scene.tick_distance}{p.units_name}"))
            amount = (
                round(
                    (p.device.unit_width / tlen) * (p.device.unit_height / tlen) / 1000,
                    0,
                )
                * 1000
            )
            if amount >= 2000:
                dlg = wx.MessageDialog(
                    None,
                    _(
                        "You will create more than {:,.0f} magnet-lines! Are you really, really sure?"
                    ).format(amount),
                    _("Huge amount of magnet lines"),
                    wx.YES_NO | wx.ICON_QUESTION,
                )
                result = dlg.ShowModal()
                dlg.Destroy()
                if result == wx.ID_NO:
                    return

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

    def _add_scale_options(self, menu):
        def on_user_option(event):
            dlg = wx.TextEntryDialog(
                self.scene.context.gui,
                message=_("Please provide the grid-size in {units}").format(
                    units=self.scene.context.units_name
                ),
                caption=_("User-defined grid-size"),
                value=str(self.scene.tick_distance),
            )
            dlg.ShowModal()
            result = dlg.GetValue()
            dlg.Destroy()
            try:
                value = float(result)
            except:
                return
            self.scene.tick_distance = value
            self.scene.auto_tick = False
            self.scene._signal_widget(self.scene.widget_root, "grid")
            self.scene.request_refresh()

        def on_regular_option(option):
            def check(event):
                self.set_auto_tick(option)

            return check

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
            self.options = [0.1, 0.5, 1, 5, 10, 25]
        elif units == "cm":
            self.options = [0.1, 0.5, 1, 5]
        elif units == "inch":
            self.options = [0.1, 0.25, 0.5, 1]
        else:  # mils
            self.options = [10, 25, 50, 100, 250, 500, 1000]

        for option in self.options:
            kind = (
                wx.ITEM_CHECK
                if self.scene.tick_distance == option and not self.scene.auto_tick
                else wx.ITEM_NORMAL
            )
            item = menu.Append(
                wx.ID_ANY,
                f"{option:.2f}{units}",
                "",
                kind,
            )
            if kind == wx.ITEM_CHECK:
                menu.Check(item.GetId(), True)
            self.scene.context.gui.Bind(
                wx.EVT_MENU,
                on_regular_option(option),
                id=item.GetId(),
            )

        menu.AppendSeparator()
        item = menu.Append(
            wx.ID_ANY,
            f"User defined value: {self.scene.tick_distance}{units}",
            "",
            wx.ITEM_NORMAL,
        )
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            on_user_option,
            id=item.GetId(),
        )

    def _add_attraction_strength_menu(self, menu):
        item = menu.Append(wx.ID_ANY, _("Attraction strength..."), "", wx.ITEM_NORMAL)
        menu.Enable(item.GetId(), False)
        kind = wx.ITEM_CHECK if self.scene.magnet_attraction == 0 else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Off"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.attract_event(0),
            id=item.GetId(),
        )
        kind = wx.ITEM_CHECK if self.scene.magnet_attraction == 1 else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Weak"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.attract_event(1),
            id=item.GetId(),
        )
        kind = wx.ITEM_CHECK if self.scene.magnet_attraction == 2 else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Normal"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.attract_event(2),
            id=item.GetId(),
        )
        kind = wx.ITEM_CHECK if self.scene.magnet_attraction == 3 else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Strong"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.attract_event(3),
            id=item.GetId(),
        )
        kind = wx.ITEM_CHECK if self.scene.magnet_attraction == 4 else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Very Strong"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.attract_event(4),
            id=item.GetId(),
        )
        kind = wx.ITEM_CHECK if self.scene.magnet_attraction == 5 else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Enormous"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.attract_event(5),
            id=item.GetId(),
        )

    def _add_attraction_options_menu(self, menu):
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

    def _add_grid_draw_options(self, menu):
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

    def _process_doubleclick(self, window_pos=None, space_pos=None):
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
            if self.scene.grid_secondary_cx is not None:
                sx = self.scene.grid_secondary_cx
            if self.scene.grid_secondary_cy is not None:
                sy = self.scene.grid_secondary_cy
            if self.scene.grid_secondary_scale_x is not None:
                tick_distance_x *= self.scene.grid_secondary_scale_x
            if self.scene.grid_secondary_scale_y is not None:
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
            value = float(Length(f"{mark_point_x:.1f}{self.units}"))
            self.scene.toggle_x_magnet(value)
        elif is_y:
            # Get the Y coordinate from space_pos [1]
            value = float(Length(f"{mark_point_y:.1f}{self.units}"))
            self.scene.toggle_y_magnet(value)

        self.scene.request_refresh()

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        """
        Capture and deal with the double click event.
        Double-click in the grid loads a menu to remove the background.
        """

        if event_type == "hover":
            return RESPONSE_CHAIN
        elif event_type == "rightdown":
            menu = wx.Menu()
            self._add_scale_options(menu)
            menu.AppendSeparator()
            if self.scene.has_magnets():
                item = menu.Append(wx.ID_ANY, _("Clear all magnets"), "")
                self.scene.context.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.scene.clear_magnets(),
                    id=item.GetId(),
                )
                menu.AppendSeparator()
                self._add_attraction_strength_menu(menu)
                menu.AppendSeparator()
                self._add_attraction_options_menu(menu)

            else:
                item = menu.Append(wx.ID_ANY, _("Create magnets along grid"), "")
                self.scene.context.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.fill_magnets(),
                    id=item.GetId(),
                )
            self._add_grid_draw_options(menu)
            self.scene.context.gui.PopupMenu(menu)
            menu.Destroy()
            self.scene.request_refresh()

            return RESPONSE_CONSUME
        elif event_type == "doubleclick":
            self._process_doubleclick(window_pos, space_pos)
            return RESPONSE_CONSUME
        else:
            return RESPONSE_CHAIN

    def _get_center_primary(self):
        """
        Calculate center position for primary grid
        """
        p = self.scene.context
        x = p.device.unit_width * p.device.show_origin_x
        y = p.device.unit_height * p.device.show_origin_y
        return self.scene.convert_scene_to_window([x, y])

    def _get_center_secondary(self):
        """
        Calculate center position for secondary grid
        """
        p = self.scene.context
        x = p.device.unit_width * p.device.show_origin_x
        y = p.device.unit_height * p.device.show_origin_y
        if self.scene.grid_secondary_cx is not None:
            x = self.scene.grid_secondary_cx

        if self.scene.grid_secondary_cy is not None:
            y = self.scene.grid_secondary_cy

        return self.scene.convert_scene_to_window([x, y])

    def _set_scaled_conversion(self):
        p = self.scene.context
        f = p.device.length(f"1{p.units_name}", as_float=True)
        m = self.scene.widget_root.scene_widget.matrix
        self.scaled_conversion_x = f * m.value_scale_x()
        self.scaled_conversion_y = f * m.value_scale_y()

    def _draw_primary_guides(self, gc):
        w, h = gc.Size
        p = self.scene.context
        sx_primary, sy_primary = self._get_center_primary()
        length = self.line_length
        edge_gap = self.edge_gap
        gc.SetPen(self.pen_guide1)
        gc.SetFont(self.font, self.color_guide1)

        (t_width, t_height) = gc.GetTextExtent("0")

        starts = []
        ends = []
        points_x_primary = self.scene.tick_distance * self.scaled_conversion_x
        offset_x_primary = float(sx_primary) % points_x_primary
        x = offset_x_primary
        last_text_pos = x - 30  # Arbitrary
        while x < w:
            if x >= 45:
                mark_point = (x - sx_primary) / self.scaled_conversion_x
                if p.device.show_flip_x:
                    mark_point *= -1
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                starts.append((x, edge_gap))
                ends.append((x, length + edge_gap))

                starts.append((x, h - edge_gap))
                ends.append((x, h - length - edge_gap))
                # Show half distance as well if there's enough room
                if t_height < 0.5 * points_x_primary:
                    starts.append((x - 0.5 * points_x_primary, edge_gap))
                    ends.append((x - 0.5 * points_x_primary, 0.25 * length + edge_gap))

                if not self.scene.draw_grid_secondary:
                    starts.append((x, h - edge_gap))
                    ends.append((x, h - length - edge_gap))
                    starts.append((x - 0.5 * points_x_primary, h - edge_gap))
                    ends.append(
                        (x - 0.5 * points_x_primary, h - 0.25 * length - edge_gap)
                    )
                if (x - last_text_pos) >= t_height * 1.25:
                    gc.DrawText(f"{mark_point:g}", x, edge_gap, -math.tau / 4)
                    last_text_pos = x
            x += points_x_primary

        points_y_primary = self.scene.tick_distance * self.scaled_conversion_y
        offset_y_primary = float(sy_primary) % points_y_primary
        y = offset_y_primary
        last_text_pos = y - 30  # arbitrary
        while y < h:
            if y >= 20:
                mark_point = (y - sy_primary) / self.scaled_conversion_y
                if p.device.show_flip_y:
                    mark_point *= -1
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                starts.append((edge_gap, y))
                ends.append((length + edge_gap, y))
                # if there is enough room for a mid-distance stroke...
                if t_height < 0.5 * points_y_primary:
                    starts.append((edge_gap, y - 0.5 * points_y_primary))
                    ends.append((0.25 * length + edge_gap, y - 0.5 * points_y_primary))

                if not self.scene.draw_grid_secondary:
                    starts.append((w - edge_gap, y))
                    ends.append((w - length - edge_gap, y))
                    starts.append((w - edge_gap, y - 0.5 * points_y_primary))
                    ends.append(
                        (w - 0.25 * length - edge_gap, y - 0.5 * points_y_primary)
                    )

                if (y - last_text_pos) >= t_height * 1.25:
                    # Adding zero makes -0 into positive 0
                    gc.DrawText(f"{mark_point + 0:g}", edge_gap, y + 0)
                    last_text_pos = y
            y += points_y_primary
        if len(starts) > 0:
            gc.StrokeLineSegments(starts, ends)

    def _draw_secondary_guides(self, gc):
        w, h = gc.Size
        p = self.scene.context

        fx = 1.0
        if self.scene.grid_secondary_scale_x is not None:
            fx = self.scene.grid_secondary_scale_x
        points_x = fx * self.scene.tick_distance * self.scaled_conversion_x

        fy = 1.0
        if self.scene.grid_secondary_scale_y is not None:
            fy = self.scene.grid_secondary_scale_y
        points_y = fy * self.scene.tick_distance * self.scaled_conversion_y
        self.units = p.units_name

        sx, sy = self._get_center_secondary()

        length = self.line_length
        edge_gap = self.edge_gap

        gc.SetPen(self.pen_guide2)
        gc.SetFont(self.font, self.color_guide2)
        (t_width, t_height) = gc.GetTextExtent("0")

        starts = []
        ends = []
        offset_x = float(sx) % points_x
        x = offset_x
        last_text_pos = x - 30
        while x < w:
            if x >= 45:
                mark_point = (x - sx) / (fx * self.scaled_conversion_x)
                if p.device.show_flip_x:
                    mark_point *= -1
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                starts.append((x, edge_gap))
                ends.append((x, length + edge_gap))

                starts.append((x, h - edge_gap))
                ends.append((x, h - length - edge_gap))
                # Show half distance as well if there's enough room
                if t_height < 0.5 * points_x:
                    starts.append((x - 0.5 * points_x, h - edge_gap))
                    ends.append(
                        (
                            x - 0.5 * points_x,
                            h - 0.25 * length - edge_gap,
                        )
                    )
                info = f"{mark_point:g}"
                (t_w, t_h) = gc.GetTextExtent(info)
                if (x - last_text_pos) >= t_h * 1.25:
                    gc.DrawText(info, x, h - edge_gap - t_w, -math.tau / 4)
                    last_text_pos = x
            x += points_x

        offset_y = float(sy) % points_y
        y = offset_y
        last_text_pos = y - 30
        while y < h:
            if y >= 20:
                mark_point = (y - sy) / (fy * self.scaled_conversion_y)
                if p.device.show_flip_y:
                    mark_point *= -1
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0  # prevents -0
                starts.append((w - edge_gap, y))
                ends.append((w - length - edge_gap, y))
                # if there is enough room for a mid-distance stroke...
                if t_height < 0.5 * points_y:
                    starts.append((w - edge_gap, y - 0.5 * points_y))
                    ends.append(
                        (
                            w - 0.25 * length - edge_gap,
                            y - 0.5 * points_y,
                        )
                    )

                info = f"{mark_point + 0:g}"  # -0.0 + 0 == 0
                (t_w, t_h) = gc.GetTextExtent(info)
                if (y - last_text_pos) >= t_h * 1.25:
                    gc.DrawText(info, w - edge_gap - t_w, y + 0)
                    last_text_pos = y
            y += points_y

        gc.StrokeLineSegments(starts, ends)

    def _draw_magnet_lines(self, gc):
        w, h = gc.Size
        length = self.line_length
        edge_gap = self.edge_gap

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

    def _draw_units(self, gc):
        p = self.scene.context
        self.units = p.units_name
        gc.SetFont(self.font, self.color_units)
        gc.DrawText(self.units, self.edge_gap, self.edge_gap)

    def process_draw(self, gc):
        """
        Draw the guidelines
        """
        w, h = gc.Size
        self.scale_x2_lower = w - self.edge_gap - self.line_length
        self.scale_x2_upper = w
        self.scale_y2_lower = h - self.edge_gap - self.line_length
        self.scale_y2_upper = h
        if self.scene.context.draw_mode & DRAW_MODE_GUIDES != 0:
            return
        self._set_scaled_conversion()
        if self.scaled_conversion_x == 0 or self.scene.tick_distance == 0:
            # Cannot be drawn.
            return

        self._draw_units(gc)

        self._draw_primary_guides(gc)

        if self.scene.draw_grid_secondary:
            self._draw_secondary_guides(gc)
        self._draw_magnet_lines(gc)

    def signal(self, signal, *args, **kwargs):
        """
        Process guide signal to delete the current guidelines and force them to be recalculated.
        """
        if signal == "guide":
            pass
        elif signal == "theme":
            self.set_colors()
