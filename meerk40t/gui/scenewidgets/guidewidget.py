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
        self.primary_guides_pen = wx.Pen()
        self.secondary_guides_pen = wx.Pen()
        self.pen_magnets = wx.Pen()
        self.color_units = None
        self.primary_guides_color = None
        self.secondary_guides_color = None

        # Performance optimization caches
        self._text_extent_cache = {}
        self._formatted_text_cache = {}
        self._pen_cache = {}
        self._grid_cache = {
            "primary_starts": [],
            "primary_ends": [],
            "secondary_starts": [],
            "secondary_ends": [],
            "magnet_starts": [],
            "magnet_ends": [],
            "primary_text_data": [],
            "secondary_text_data": [],
            "cache_key": None,
        }
        self._viewport_cache = {}
        self._viewport_cache_max_size = (
            50  # Limit cache size to prevent unbounded growth
        )

        self.set_colors()
        self.font = wx.Font(
            10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )

    def _get_cache_key(self, w, h):
        """Generate cache key for current viewport and grid settings"""
        p = self.scene.context
        mat = self.scene.widget_root.scene_widget.matrix

        # Include full matrix transformation state to detect any changes
        # that would affect grid positioning and coordinate conversion
        return (
            w,
            h,
            self.scene.pane.grid.tick_distance,
            self.scene.pane.grid.draw_grid_primary,
            self.scene.pane.grid.draw_grid_secondary,
            # Matrix transformation components
            mat.a,
            mat.b,
            mat.c,
            mat.d,
            mat.e,
            mat.f,
            # Scene space settings
            p.space.right_positive,
            p.space.bottom_positive,
            p.space.origin_zero(),
            # Secondary grid scale factors
            getattr(self.scene.pane.grid, "grid_secondary_scale_x", None),
            getattr(self.scene.pane.grid, "grid_secondary_scale_y", None),
        )

    def _get_cached_text_extent(self, gc, text):
        """Get cached text extent or calculate and cache if not found"""
        if text not in self._text_extent_cache:
            self._text_extent_cache[text] = gc.GetTextExtent(text)
        return self._text_extent_cache[text]

    def _get_formatted_text(self, value, format_spec="g"):
        """Get cached formatted text or format and cache if not found"""
        cache_key = (value, format_spec)
        if cache_key not in self._formatted_text_cache:
            if format_spec == "g":
                self._formatted_text_cache[cache_key] = f"{value:g}"
            elif format_spec == ".0f":
                self._formatted_text_cache[cache_key] = f"{value:.0f}"
            elif format_spec == ".1f":
                self._formatted_text_cache[cache_key] = f"{value:.1f}"
            else:
                self._formatted_text_cache[cache_key] = f"{value:{format_spec}}"
        return self._formatted_text_cache[cache_key]

    def _calculate_viewport_bounds(self, w, h):
        """Calculate visible bounds more efficiently, accounting for coordinate system orientation"""
        cache_key = (w, h)
        if cache_key in self._viewport_cache:
            return self._viewport_cache[cache_key]

        # Calculate bounds for all four corners
        bounds = [
            self.scene.convert_window_to_scene([0, 0]),
            self.scene.convert_window_to_scene([w, 0]),
            self.scene.convert_window_to_scene([0, h]),
            self.scene.convert_window_to_scene([w, h]),
        ]

        # Get actual min/max regardless of coordinate system orientation
        min_x = min(bound[0] for bound in bounds)
        max_x = max(bound[0] for bound in bounds)
        min_y = min(bound[1] for bound in bounds)
        max_y = max(bound[1] for bound in bounds)

        # Clamp to device bounds - but be aware that in inverted coordinate systems,
        # the "logical" bounds might be different from the numerical bounds
        space = self.scene.context.space

        # For coordinate systems, we need to respect the actual coordinate space bounds
        if hasattr(space, "width") and hasattr(space, "height"):
            device_min_x = 0 if space.right_positive else -space.width
            device_max_x = space.width if space.right_positive else 0
            device_min_y = 0 if space.bottom_positive else -space.height
            device_max_y = space.height if space.bottom_positive else 0

            min_x = max(device_min_x, min_x)
            min_y = max(device_min_y, min_y)
            max_x = min(device_max_x, max_x)
            max_y = min(device_max_y, max_y)
        else:
            # Fallback to simple clamping if space properties not available
            min_x = max(0, min_x)
            min_y = max(0, min_y)
            max_x = min(getattr(space, "width", float("inf")), max_x)
            max_y = min(getattr(space, "height", float("inf")), max_y)

        result = (min_x, min_y, max_x, max_y)

        # Implement simple LRU eviction to prevent unbounded cache growth
        if len(self._viewport_cache) >= self._viewport_cache_max_size:
            # Remove oldest entry (first item) to make room for new one
            oldest_key = next(iter(self._viewport_cache))
            del self._viewport_cache[oldest_key]

        self._viewport_cache[cache_key] = result
        return result

    def set_colors(self):
        self.color_units = self.scene.colors.color_guide
        self.primary_guides_color = self.scene.colors.color_guide
        self.secondary_guides_color = self.scene.colors.color_guide2
        self.primary_guides_pen.SetColour(self.primary_guides_color)
        self.secondary_guides_pen.SetColour(self.secondary_guides_color)
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
            self.scene.pane.grid.auto_tick = True
        else:
            self.scene.pane.grid.auto_tick = False
            self.scene.pane.grid.tick_distance = value
        self.scene._signal_widget(self.scene.widget_root, "grid")
        self.scene.request_refresh()

    def change_tick_event(self, idx):
        value = self.options[idx]
        self.set_auto_tick(value)

    def attract_event(self, value):
        self.scene.pane.magnet_attraction = value
        self.scene.context.signal("magnet_options")

    def affect_event(self, value):
        if value == 0:
            self.scene.pane.magnet_attract_x = not self.scene.pane.magnet_attract_x
        elif value == 1:
            self.scene.pane.magnet_attract_y = not self.scene.pane.magnet_attract_y
        elif value == 2:
            self.scene.pane.magnet_attract_c = not self.scene.pane.magnet_attract_c
        self.scene.context.signal("magnet_options")

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
        if self.scene.pane.grid.draw_grid_primary:
            tlen = float(Length(f"{self.scene.pane.grid.tick_distance}{p.units_name}"))
            amount = (
                round(
                    (p.device.view.unit_width / tlen)
                    * (p.device.view.unit_height / tlen)
                    / 1000,
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
            while x <= p.device.view.unit_width:
                self.scene.pane.toggle_x_magnet(x)
                x += tlen

            y = 0
            while y <= p.device.view.unit_height:
                self.scene.pane.toggle_y_magnet(y)
                y += tlen
            self.scene.pane.save_magnets()
        elif self.scene.pane.grid.draw_grid_secondary:
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
                value=str(self.scene.pane.grid.tick_distance),
            )
            dlg.ShowModal()
            result = dlg.GetValue()
            dlg.Destroy()
            try:
                value = float(result)
            except:
                return
            self.scene.pane.grid.tick_distance = value
            self.scene.pane.grid.auto_tick = False
            self.scene._signal_widget(self.scene.widget_root, "grid")
            self.scene.request_refresh()

        def on_regular_option(option):
            def check(event):
                self.set_auto_tick(option)

            return check

        kind = wx.ITEM_CHECK if self.scene.pane.grid.auto_tick else wx.ITEM_NORMAL
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
                if self.scene.pane.grid.tick_distance == option
                and not self.scene.pane.grid.auto_tick
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
            _("User defined value: {value}").format(
                value=f"{self.scene.pane.grid.tick_distance}{units}"
            ),
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
        kind = (
            wx.ITEM_CHECK if self.scene.pane.magnet_attraction == 0 else wx.ITEM_NORMAL
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
            wx.ITEM_CHECK if self.scene.pane.magnet_attraction == 1 else wx.ITEM_NORMAL
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
            wx.ITEM_CHECK if self.scene.pane.magnet_attraction == 2 else wx.ITEM_NORMAL
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
            wx.ITEM_CHECK if self.scene.pane.magnet_attraction == 3 else wx.ITEM_NORMAL
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
            wx.ITEM_CHECK if self.scene.pane.magnet_attraction == 4 else wx.ITEM_NORMAL
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
            wx.ITEM_CHECK if self.scene.pane.magnet_attraction == 5 else wx.ITEM_NORMAL
        )
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
        kind = wx.ITEM_CHECK if self.scene.pane.magnet_attract_x else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Left/Right Side"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.affect_event(0),
            id=item.GetId(),
        )
        kind = wx.ITEM_CHECK if self.scene.pane.magnet_attract_y else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, _("Top/Bottom Side"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.affect_event(1),
            id=item.GetId(),
        )
        kind = wx.ITEM_CHECK if self.scene.pane.magnet_attract_c else wx.ITEM_NORMAL
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
        kind = (
            wx.ITEM_CHECK if self.scene.pane.grid.draw_grid_primary else wx.ITEM_NORMAL
        )
        item = menu.Append(wx.ID_ANY, _("Draw primary grid"), "", kind)
        if kind == wx.ITEM_CHECK:
            menu.Check(item.GetId(), True)
        self.scene.context.gui.Bind(
            wx.EVT_MENU,
            lambda e: self.toggle_rect(),
            id=item.GetId(),
        )
        kind = (
            wx.ITEM_CHECK
            if self.scene.pane.grid.draw_grid_secondary
            else wx.ITEM_NORMAL
        )
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

        kind = (
            wx.ITEM_CHECK if self.scene.pane.grid.draw_grid_circular else wx.ITEM_NORMAL
        )
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
            if self.scene.pane.grid.draw_grid_secondary:
                is_y = self.scale_x2_lower <= space_pos[0] <= self.scale_x2_upper
                secondary = True
        is_x = self.scale_y_lower <= space_pos[1] <= self.scale_y_upper
        if not is_x:
            if self.scene.pane.grid.draw_grid_secondary:
                is_x = self.scale_y2_lower <= space_pos[1] <= self.scale_y2_upper
                secondary = True
        # print ("is_x=%s, is_y=%s, secondary=%s" % (is_x, is_y, secondary))
        if not (is_x or is_y):
            return

        # value = 0
        if self.scaled_conversion_x == 0:
            return
        sx = 0
        sy = 0
        tick_distance_x = self.scene.pane.grid.tick_distance
        tick_distance_y = self.scene.pane.grid.tick_distance
        if secondary:
            if self.scene.pane.grid.grid_secondary_cx is not None:
                sx = self.scene.pane.grid.grid_secondary_cx
            if self.scene.pane.grid.grid_secondary_cy is not None:
                sy = self.scene.pane.grid.grid_secondary_cy
            if self.scene.pane.grid.grid_secondary_scale_x is not None:
                tick_distance_x *= self.scene.pane.grid.grid_secondary_scale_x
            if self.scene.pane.grid.grid_secondary_scale_y is not None:
                tick_distance_y *= self.scene.pane.grid.grid_secondary_scale_y
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
            if self.scene.pane.has_magnets():
                self.scene.pane.clear_magnets()
            else:
                self.fill_magnets()
            # No need to call save magnets here as both routines already do that
        elif is_x:
            # Get the X coordinate from space_pos [0]
            value = float(Length(f"{mark_point_x:.1f}{self.units}"))
            self.scene.pane.toggle_x_magnet(value)
            self.scene.pane.save_magnets()
        elif is_y:
            # Get the Y coordinate from space_pos [1]
            value = float(Length(f"{mark_point_y:.1f}{self.units}"))
            self.scene.pane.toggle_y_magnet(value)
        self.invalidate_cache()
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
            if self.scene.pane.has_magnets():
                item = menu.Append(wx.ID_ANY, _("Clear all magnets"), "")
                self.scene.context.gui.Bind(
                    wx.EVT_MENU,
                    lambda e: self.scene.pane.clear_magnets(),
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
        x, y = p.space.origin_zero()
        return self.scene.convert_scene_to_window([x, y])

    def _get_center_secondary(self):
        """
        Calculate center position for secondary grid
        """
        p = self.scene.context
        x, y = p.space.origin_zero()
        if self.scene.pane.grid.grid_secondary_cx is not None:
            x = self.scene.pane.grid.grid_secondary_cx

        if self.scene.pane.grid.grid_secondary_cy is not None:
            y = self.scene.pane.grid.grid_secondary_cy

        return self.scene.convert_scene_to_window([x, y])

    def _set_scaled_conversion(self):
        p = self.scene.context
        f = float(Length(f"1{p.units_name}"))
        m = self.scene.widget_root.scene_widget.matrix
        self.scaled_conversion_x = f * m.value_scale_x()
        self.scaled_conversion_y = f * m.value_scale_y()

    def _draw_primary_guides_optimized(self, gc):
        """Optimized primary guides drawing with caching and batching"""
        w, h = gc.Size
        cache_key = self._get_cache_key(w, h)

        # Check if we can use cached data
        if (
            self._grid_cache["cache_key"] == cache_key
            and self._grid_cache["primary_starts"] is not None
        ):
            starts = self._grid_cache["primary_starts"]
            ends = self._grid_cache["primary_ends"]
            text_data = self._grid_cache.get("primary_text_data", [])
        else:
            # Calculate grid data and cache it
            starts, ends, text_data = self._calculate_primary_grid_data(w, h, gc)
            self._grid_cache["primary_starts"] = starts
            self._grid_cache["primary_ends"] = ends
            self._grid_cache["primary_text_data"] = text_data
            self._grid_cache["cache_key"] = cache_key

        # Set drawing properties
        gc.SetPen(self.primary_guides_pen)
        gc.SetFont(self.font, self.primary_guides_color)

        # Draw all lines in a single batched operation
        if starts and ends:
            gc.StrokeLineSegments(starts, ends)

        # Draw all text labels
        for text, x, y, angle in text_data:
            gc.DrawText(text, x, y, angle)

    def _calculate_primary_grid_data(self, w, h, gc=None):
        """Calculate primary grid lines and text labels"""
        p = self.scene.context
        mat = self.scene.widget_root.scene_widget.matrix

        if mat.rotation != 0:
            return [], [], []

        sx_primary, sy_primary = self._get_center_primary()
        length = self.line_length
        edge_gap = self.edge_gap

        # Use cached text extent for "0" as reference
        if gc is not None:
            text_width, text_height = self._get_cached_text_extent(gc, "0")
        else:
            text_width, text_height = 8, 12  # fallback values

        starts = []
        ends = []
        text_data = []

        # Calculate X-axis guides with viewport culling
        points_x_primary = self.scene.pane.grid.tick_distance * self.scaled_conversion_x
        if points_x_primary > 0:
            offset_x_primary = float(sx_primary) % points_x_primary

            # Calculate visible range to avoid unnecessary iterations
            start_x = max(0, offset_x_primary)
            end_x = w
            x_range = end_x - start_x
            step_count = int(x_range / points_x_primary)
            if (x_range % points_x_primary) > 0:
                step_count += 1
            step_count = max(step_count, 1)

            x = start_x
            last_text_pos = x - 30

            for i in range(step_count):
                if x >= w:
                    break

                if x >= 45:
                    mark_point = (x - sx_primary) / self.scaled_conversion_x
                    if not p.space.right_positive:
                        mark_point *= -1
                    if round(float(mark_point) * 1000) == 0:
                        mark_point = 0.0

                    # Primary vertical lines
                    starts.extend([(x, edge_gap), (x, h - edge_gap)])
                    ends.extend([(x, length + edge_gap), (x, h - length - edge_gap)])

                    # Half-distance marks if there's room
                    if text_height < 0.5 * points_x_primary:
                        half_x = x - 0.5 * points_x_primary
                        starts.append((half_x, edge_gap))
                        ends.append((half_x, 0.25 * length + edge_gap))

                        if not self.scene.pane.grid.draw_grid_secondary:
                            starts.append((half_x, h - edge_gap))
                            ends.append((half_x, h - 0.25 * length - edge_gap))

                    # Text labels with spacing check
                    if (x - last_text_pos) >= text_height * 1.25:
                        formatted_text = self._get_formatted_text(mark_point, "g")
                        text_data.append((formatted_text, x, edge_gap, -math.tau / 4))
                        last_text_pos = x

                x += points_x_primary

        # Calculate Y-axis guides with viewport culling
        points_y_primary = self.scene.pane.grid.tick_distance * self.scaled_conversion_y
        if points_y_primary > 0:
            offset_y_primary = float(sy_primary) % points_y_primary

            # Calculate visible range with optimized step count
            start_y = max(0, offset_y_primary)
            end_y = h
            y_range = end_y - start_y
            step_count_y = int(y_range / points_y_primary)
            if y_range % points_y_primary != 0:
                step_count_y += 1
            step_count_y = max(step_count_y, 1)

            y = start_y
            last_text_pos = y - 30

            for i in range(step_count_y):
                if y >= h:
                    break

                if y >= 20:
                    mark_point = (y - sy_primary) / self.scaled_conversion_y
                    if not p.space.bottom_positive:
                        mark_point *= -1
                    if round(float(mark_point) * 1000) == 0:
                        mark_point = 0.0

                    # Primary horizontal lines
                    if not self.scene.pane.grid.draw_grid_secondary:
                        starts.extend([(edge_gap, y), (w - edge_gap, y)])
                        ends.extend(
                            [(length + edge_gap, y), (w - length - edge_gap, y)]
                        )
                    else:
                        starts.append((edge_gap, y))
                        ends.append((length + edge_gap, y))

                    # Half-distance marks
                    if text_height < 0.5 * points_y_primary:
                        half_y = y - 0.5 * points_y_primary
                        starts.append((edge_gap, half_y))
                        ends.append((0.25 * length + edge_gap, half_y))

                        if not self.scene.pane.grid.draw_grid_secondary:
                            starts.append((w - edge_gap, half_y))
                            ends.append((w - 0.25 * length - edge_gap, half_y))

                    # Text labels
                    if (y - last_text_pos) >= text_height * 1.25:
                        formatted_text = self._get_formatted_text(mark_point + 0, "g")
                        text_data.append((formatted_text, edge_gap, y + 0, 0))
                        last_text_pos = y

                y += points_y_primary

        return starts, ends, text_data

    def _draw_primary_guides(self, gc):
        """Legacy method - redirect to optimized version"""
        return self._draw_primary_guides_optimized(gc)

    def _draw_secondary_guides_optimized(self, gc):
        """Optimized secondary guide drawing with caching and viewport culling"""
        w, h = gc.Size
        cache_key = self._get_cache_key(w, h)

        # Check if we can use cached secondary guide data
        if (
            self._grid_cache["cache_key"] == cache_key
            and self._grid_cache["secondary_starts"]
        ):
            starts = self._grid_cache["secondary_starts"]
            ends = self._grid_cache["secondary_ends"]
            text_data = self._grid_cache["secondary_text"]
        else:
            # Calculate secondary guides with viewport culling
            starts, ends, text_data = self._calculate_secondary_guides(w, h)
            self._grid_cache["secondary_starts"] = starts
            self._grid_cache["secondary_ends"] = ends
            self._grid_cache["secondary_text"] = text_data

        # Set pen and font once
        gc.SetPen(self.secondary_guides_pen)
        gc.SetFont(self.font, self.secondary_guides_color)

        # Draw all lines in a single batch
        if starts and ends:
            gc.StrokeLineSegments(starts, ends)

        # Draw all text with proper positioning
        for formatted_text, x, y, rotation in text_data:
            # Calculate actual text dimensions for proper positioning
            text_width, text_height = self._get_cached_text_extent(gc, formatted_text)

            # Adjust position based on rotation
            if rotation == -math.tau / 4:  # Vertical text
                final_x = x
                final_y = y - text_width  # Adjust for rotated text
            else:  # Horizontal text
                final_x = x - text_width  # Right-align text
                final_y = y

            gc.DrawText(formatted_text, final_x, final_y, rotation)

    def _calculate_secondary_guides(self, w, h):
        """Calculate secondary guides with viewport culling"""
        p = self.scene.context
        mat = self.scene.widget_root.scene_widget.matrix
        if mat.rotation != 0:
            return [], [], []

        fx = 1.0
        if self.scene.pane.grid.grid_secondary_scale_x is not None:
            fx = self.scene.pane.grid.grid_secondary_scale_x
        points_x = fx * self.scene.pane.grid.tick_distance * self.scaled_conversion_x

        fy = 1.0
        if self.scene.pane.grid.grid_secondary_scale_y is not None:
            fy = self.scene.pane.grid.grid_secondary_scale_y
        points_y = fy * self.scene.pane.grid.tick_distance * self.scaled_conversion_y

        sx, sy = self._get_center_secondary()
        length = self.line_length
        edge_gap = self.edge_gap

        starts = []
        ends = []
        text_data = []

        # We'll cache text dimensions during rendering since we need gc context
        # For now, use approximate values for calculations
        t_height = 12  # Approximate text height

        # Process X axis (vertical lines) with viewport culling
        offset_x = float(sx) % points_x
        x = offset_x
        last_text_pos = x - 30

        while 0 <= x < w:
            if x >= 45:
                mark_point = (x - sx) / (fx * self.scaled_conversion_x)
                if not p.space.right_positive:
                    mark_point *= -1
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0

                # Main vertical lines
                starts.extend([(x, edge_gap), (x, h - edge_gap)])
                ends.extend([(x, length + edge_gap), (x, h - length - edge_gap)])

                # Half distance marks if there's room
                if t_height < 0.5 * points_x:
                    starts.append((x - 0.5 * points_x, h - edge_gap))
                    ends.append((x - 0.5 * points_x, h - 0.25 * length - edge_gap))

                # Text labels with spacing check
                if (x - last_text_pos) >= t_height * 1.25:
                    formatted_text = self._get_formatted_text(mark_point, "g")
                    text_data.append((formatted_text, x, h - edge_gap, -math.tau / 4))
                    last_text_pos = x
            x += points_x

        # Process Y axis (horizontal lines) with viewport culling
        offset_y = float(sy) % points_y
        y = offset_y
        last_text_pos = y - 30

        while 0 <= y < h:
            if y >= 20:
                mark_point = (y - sy) / (fy * self.scaled_conversion_y)
                if not p.space.bottom_positive:
                    mark_point *= -1
                if round(float(mark_point) * 1000) == 0:
                    mark_point = 0.0

                # Main horizontal lines
                starts.append((w - edge_gap, y))
                ends.append((w - length - edge_gap, y))

                # Half distance marks if there's room
                if t_height < 0.5 * points_y:
                    starts.append((w - edge_gap, y - 0.5 * points_y))
                    ends.append((w - 0.25 * length - edge_gap, y - 0.5 * points_y))

                # Text labels with spacing check
                if (y - last_text_pos) >= t_height * 1.25:
                    formatted_text = self._get_formatted_text(mark_point + 0, "g")
                    text_data.append((formatted_text, w - edge_gap, y + 0, 0))
                    last_text_pos = y
            y += points_y

        return starts, ends, text_data

    def _draw_secondary_guides(self, gc):
        """Legacy method - redirect to optimized version"""
        return self._draw_secondary_guides_optimized(gc)

    def _draw_magnet_lines_optimized(self, gc):
        """Optimized magnet line drawing with caching and viewport culling"""
        w, h = gc.Size
        cache_key = self._get_cache_key(w, h)

        # Check if we can use cached magnet data
        if (
            self._grid_cache["cache_key"] == cache_key
            and self._grid_cache["magnet_starts"]
        ):
            starts_hi = self._grid_cache["magnet_starts"]
            ends_hi = self._grid_cache["magnet_ends"]
        else:
            # Calculate magnet lines with viewport culling
            starts_hi, ends_hi = self._calculate_magnet_lines(w, h)
            self._grid_cache["magnet_starts"] = starts_hi
            self._grid_cache["magnet_ends"] = ends_hi

        gc.SetPen(self.pen_magnets)
        if starts_hi and ends_hi:
            gc.StrokeLineSegments(starts_hi, ends_hi)

    def _calculate_magnet_lines(self, w, h):
        """Calculate magnet lines with viewport culling"""
        length = self.line_length
        edge_gap = self.edge_gap
        starts_hi = []
        ends_hi = []
        epsilon = 1e-6  # Small epsilon for floating point precision

        # Process X magnets (vertical lines) with viewport culling
        for x in self.scene.pane.magnet_x:
            sx, sy = self.scene.convert_scene_to_window([x, 0])
            # Only add if line is visible in viewport with epsilon tolerance
            if -epsilon <= sx <= w + epsilon:
                starts_hi.append((sx, length + edge_gap))
                ends_hi.append((sx, h - length - edge_gap))

        # Process Y magnets (horizontal lines) with viewport culling
        for y in self.scene.pane.magnet_y:
            sx, sy = self.scene.convert_scene_to_window([0, y])
            # Only add if line is visible in viewport with epsilon tolerance
            if -epsilon <= sy <= h + epsilon:
                starts_hi.append((length + edge_gap, sy))
                ends_hi.append((w - length - edge_gap, sy))

        return starts_hi, ends_hi

    def invalidate_cache(self):
        """Invalidate all cached data to force recalculation"""
        self._grid_cache = {
            "cache_key": None,
            "primary_starts": [],
            "primary_ends": [],
            "primary_text_data": [],
            "secondary_starts": [],
            "secondary_ends": [],
            "secondary_text": [],
            "magnet_starts": [],
            "magnet_ends": [],
        }
        self._text_extent_cache.clear()
        self._formatted_text_cache.clear()
        self._viewport_cache.clear()  # Clear viewport cache as well

    def set_grid_changed(self):
        """Mark grid as changed and invalidate cache"""
        self.invalidate_cache()
        # Also send signal to notify other components
        self.scene._signal_widget(self.scene.widget_root, "grid")

    def set_matrix_changed(self):
        """Mark matrix as changed and invalidate cache"""
        self.invalidate_cache()
        # Force refresh on next draw since matrix affects all calculations
        if hasattr(self.scene, "request_refresh"):
            self.scene.request_refresh()

    def _check_matrix_change(self):
        """Check if matrix has changed since last cache and invalidate if needed"""
        if hasattr(self, "_last_matrix_state"):
            mat = self.scene.widget_root.scene_widget.matrix
            current_state = (
                mat.value_scale_x(),
                mat.value_scale_y(),
                mat.value_trans_x(),
                mat.value_trans_y(),
                mat.rotation,
            )
            if current_state != self._last_matrix_state:
                self.invalidate_cache()
                self._last_matrix_state = current_state
        else:
            # First time - store current matrix state
            mat = self.scene.widget_root.scene_widget.matrix
            self._last_matrix_state = (
                mat.value_scale_x(),
                mat.value_scale_y(),
                mat.value_trans_x(),
                mat.value_trans_y(),
                mat.rotation,
            )

    def _draw_magnet_lines(self, gc):
        """Legacy method - redirect to optimized version"""
        return self._draw_magnet_lines_optimized(gc)

    def _draw_units(self, gc):
        p = self.scene.context
        self.units = p.units_name
        gc.SetFont(self.font, self.color_units)
        gc.DrawText(self.units, self.edge_gap, self.edge_gap)

    def process_draw(self, gc):
        """
        Draw the guidelines
        """
        # Check for matrix changes that would invalidate cached calculations
        self._check_matrix_change()

        w, h = gc.Size
        self.scale_x2_lower = w - self.edge_gap - self.line_length
        self.scale_x2_upper = w
        self.scale_y2_lower = h - self.edge_gap - self.line_length
        self.scale_y2_upper = h
        if self.scene.context.draw_mode & DRAW_MODE_GUIDES != 0:
            return
        self._set_scaled_conversion()
        if self.scaled_conversion_x == 0 or self.scene.pane.grid.tick_distance == 0:
            # Cannot be drawn.
            return

        self._draw_units(gc)

        self._draw_primary_guides(gc)

        if self.scene.pane.grid.draw_grid_secondary:
            self._draw_secondary_guides(gc)
        self._draw_magnet_lines(gc)

    def signal(self, signal, *args, **kwargs):
        """
        Process guide signal to delete the current guidelines and force them to be recalculated.
        """
        if signal == "guide":
            # Legacy guide signal - invalidate cache
            self.invalidate_cache()
        elif signal == "grid":
            # Grid settings changed - invalidate cache to force recalculation
            self.invalidate_cache()
        elif signal == "theme":
            self.set_colors()
            # Theme change might affect text rendering - invalidate text caches
            self._text_extent_cache.clear()
