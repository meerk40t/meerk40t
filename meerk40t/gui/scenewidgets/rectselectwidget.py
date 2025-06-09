"""
Specifically draws the rectangle selection box and deals with emphasis of selected objects.
Special case: if the user did not move the mouse within the first 0.5 seconds after
the initial mouse press then we assume a drag move.
"""
from time import perf_counter

import numpy as np
import wx

from meerk40t.core.elements.element_types import elem_nodes
from meerk40t.gui.scene.scene import (
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.wxutils import dip_size, get_gc_full_scale, get_matrix_scale
from meerk40t.tools.geomstr import NON_GEOMETRY_TYPES


class RectSelectWidget(Widget):
    """
    SceneWidget

    Rectangle Selection Widget, draws the selection rectangle if left-clicked and dragged
    """

    # selection_method = 1 = hit, 2 = cross, 3 = enclose
    SELECTION_TOUCH = 1
    SELECTION_CROSS = 2
    SELECTION_ENCLOSE = 3
    selection_text_shift = " Previously selected remain selected!"
    selection_text_control = " Invert selection state of elements!"

    # 2 | 1        Define Selection method per sector, movement of mouse from point of origin into that sector...
    # - + -
    # 3 | 0
    #
    selection_method = [
        SELECTION_ENCLOSE,
        SELECTION_ENCLOSE,
        SELECTION_TOUCH,
        SELECTION_TOUCH,
    ]  # Selection rectangle to the right: enclose, to the left: touch

    was_lb_raised = False

    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        # Color for selection rectangle (hit, cross, enclose)
        self.selection_style = [
            [
                self.scene.colors.color_selection1,
                wx.PENSTYLE_DOT_DASH,
                "Select all elements the selection rectangle touches.",
            ],
            [
                self.scene.colors.color_selection2,
                wx.PENSTYLE_DOT,
                "Select all elements the selection rectangle crosses.",
            ],
            [
                self.scene.colors.color_selection3,
                wx.PENSTYLE_SHORT_DASH,
                "Select all elements the selection rectangle encloses.",
            ],
        ]
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(self.selection_style[0][0])
        self.selection_pen.SetWidth(25)
        self.selection_pen.SetStyle(self.selection_style[0][1])
        # want to have sharp edges
        self.selection_pen.SetJoin(wx.JOIN_MITER)
        self.start_location = None
        self.end_location = None
        self.modifiers = []
        self.mouse_down_time = 0
        self.scene.context.setting(bool, "delayed_move", True)
        self.mode = "select"
        self.can_drag_move = False
        self.magnification = dip_size(scene.gui, 100, 100)[1] / 100

    def hit(self):
        return HITCHAIN_HIT

    store_last_msg = ""

    @property
    def sector(self):
        sx = self.start_location[0]
        sy = self.start_location[1]
        ex = self.end_location[0]
        ey = self.end_location[1]
        if sx <= ex:
            return 0 if sy <= ey else 1
        else:
            return 3 if sy <= ey else 2

    def rect_select(self, elements, sx, sy, ex, ey):
        sector = self.sector
        selected = False
        # We don't want every single element to to issue a signal
        with elements.signalfree("emphasized"):
            for node in elements.elems():
                try:
                    q = node.bounds
                except AttributeError:
                    continue  # This element has no bounds.
                if q is None:
                    continue
                if hasattr(node, "hidden") and node.hidden:
                    continue
                if hasattr(node, "can_emphasize") and not node.can_emphasize:
                    continue
                xmin = q[0]
                ymin = q[1]
                xmax = q[2]
                ymax = q[3]
                # no hit
                cover = 0
                # Check Hit
                # The rectangles don't overlap if
                # one rectangle's minimum in some dimension
                # is greater than the other's maximum in
                # that dimension.
                if not ((sx > xmax) or (xmin > ex) or (sy > ymax) or (ymin > ey)):
                    cover = self.SELECTION_TOUCH
                    # If selection rect is fully inside an object then ignore
                    if sx > xmin and ex < xmax and sy > ymin and ey < ymax:
                        cover = 0

                # Check Cross
                if (
                    ((sx <= xmin) and (xmax <= ex))
                    and not ((sy > ymax) or (ey < ymin))
                    or ((sy <= ymin) and (ymax <= ey))
                    and not ((sx > xmax) or (ex < xmin))
                ):
                    cover = self.SELECTION_CROSS
                # Check contain
                if ((sx <= xmin) and (xmax <= ex)) and ((sy <= ymin) and (ymax <= ey)):
                    cover = self.SELECTION_ENCLOSE

                if "shift" in self.modifiers:
                    # Add Selection
                    if cover >= self.selection_method[sector]:
                        node.emphasized = True
                        node.selected = True
                        selected = True
                elif "ctrl" in self.modifiers:
                    # Invert Selection
                    if cover >= self.selection_method[sector]:
                        node.emphasized = not node.emphasized
                        node.selected = node.emphasized
                        selected = True
                else:
                    # Replace Selection
                    if cover >= self.selection_method[sector]:
                        node.emphasized = True
                        node.selected = True
                        selected = True
                    else:
                        node.emphasized = False
                        node.selected = False
        if selected:
            self.scene.context.signal("element_clicked")

    def update_statusmsg(self, value):
        if value != self.store_last_msg:
            self.store_last_msg = value
            self.scene.context.signal("statusmsg", value)

    # debug_msg = ""

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        def contains(box, x, y=None):
            if box is None:
                return False
            if y is None:
                y = x[1]
                x = x[0]
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]

        def shortest_distance(p1, p2, tuplemode):
            """
            Calculates the shortest distance between two arrays of 2-dimensional points.
            """
            try:
                # Calculate the Euclidean distance between each point in p1 and p2
                if tuplemode:
                    # For an array of tuples:
                    dist = np.sqrt(np.sum((p1[:, np.newaxis] - p2) ** 2, axis=2))
                else:
                    # For an array of complex numbers
                    dist = np.abs(p1[:, np.newaxis] - p2[np.newaxis, :])

                # Find the minimum distance and its corresponding indices
                min_dist = np.min(dist)
                if np.isnan(min_dist):
                    return None, 0, 0
                min_indices = np.argwhere(dist == min_dist)

                # Return the coordinates of the two points
                return min_dist, p1[min_indices[0][0]], p2[min_indices[0][1]]
            except Exception:  # out of memory eg
                return None, None, None

        def move_to(dx, dy):
            if dx == 0 and dy == 0:
                return
            # self.total_dx += dx
            # self.total_dy += dy
            b = self.scene.context.elements._emphasized_bounds
            if b is None:
                b = self.scene.context.elements.selected_area()
                if b is None:
                    # There is no emphasized bounds or selected area.
                    return
            allowlockmove = self.scene.context.elements.lock_allows_move
            with self.scene.context.elements.undofree():
                for e in self.scene.context.elements.flat(
                    types=elem_nodes, emphasized=True
                ):
                    if not e.can_move(allowlockmove):
                        continue
                    e.matrix.post_translate(dx, dy)
                    # We would normally not adjust the node properties,
                    # but the pure adjustment of the bbox is hopefully not hurting
                    e.translated(dx, dy)
            self.scene.context.elements.update_bounds(
                [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]
            )
            self.scene.request_refresh()

        def check_leftdown(space_pos):
            self.mouse_down_time = perf_counter()
            self.mode = "unclear"
            self.start_location = space_pos
            self.end_location = space_pos
            if contains(self.scene.context.elements._emphasized_bounds, space_pos):
                self.can_drag_move = True

        def check_click(space_pos):
            # That's too fast
            # still chaining though
            self.scene.request_refresh()
            self.reset()

        def check_move(space_pos):
            if self.mode == "unclear":
                current_time = perf_counter()
                # print (f"{current_time - self.mouse_down_time:.2f}sec.")
                if current_time - self.mouse_down_time > 0.5 and self.can_drag_move:
                    self.mode = "move"
                    self.scene.cursor("sizing")
                else:
                    self.mode = "select"
                    self.scene.cursor("arrow")

            if self.mode == "select":
                self.scene.request_refresh()
                self.end_location = space_pos
            elif self.mode == "move":
                dx = space_pos[4]
                dy = space_pos[5]
                move_to(dx, dy)

        def check_leftup_select(space_pos):
            _ = self.scene.context._
            self.update_statusmsg(_("Status"))
            elements.validate_selected_area()
            sx = min(self.start_location[0], self.end_location[0])
            sy = min(self.start_location[1], self.end_location[1])
            ex = max(self.start_location[0], self.end_location[0])
            ey = max(self.start_location[1], self.end_location[1])
            self.rect_select(elements, sx, sy, ex, ey)

            self.scene.request_refresh()
            self.scene.context.signal("select_emphasized_tree", 0)

        def check_leftup_move(space_pos):
            b = self.scene.context.elements._emphasized_bounds
            if b is None:
                b = self.scene.context.elements.selected_area()
            matrix = self.scene.widget_root.scene_widget.matrix
            did_snap_to_point = False
            if (
                self.scene.context.snap_points
                and "shift" not in modifiers
                and b is not None
            ):
                gap = self.scene.context.action_attract_len / get_matrix_scale(matrix)
                # We gather all points of non-selected elements,
                # but only those that lie within the boundaries
                # of the selected area
                # We compare every point of the selected elements
                # with the points of the non-selected elements (provided they
                # lie within the selection area plus boundary) and look for
                # the closest distance.

                # t1 = perf_counter()
                other_points = []
                selected_points = []
                for e in self.scene.context.elements.elems():
                    target = selected_points if e.emphasized else other_points
                    if not hasattr(e, "as_geometry"):
                        continue
                    geom = e.as_geometry()
                    last = None
                    for seg in geom.segments[: geom.index]:
                        start = seg[0]
                        seg_type = geom._segtype(seg)
                        end = seg[4]
                        if seg_type in NON_GEOMETRY_TYPES:
                            continue
                        if np.isnan(start) or np.isnan(end):
                            print(
                                f"Strange, encountered within rectselect a segment with type: {seg_type} and start={start}, end={end} - coming from element type {e.type}\nPlease inform the developers"
                            )
                            continue
                        if start != last:
                            xx = start.real
                            yy = start.imag
                            ignore = (
                                xx < b[0] - gap
                                or xx > b[2] + gap
                                or yy < b[1] - gap
                                or yy > b[3] + gap
                            )
                            if not ignore:
                                target.append(start)
                        xx = end.real
                        yy = end.imag
                        ignore = (
                            xx < b[0] - gap
                            or xx > b[2] + gap
                            or yy < b[1] - gap
                            or yy > b[3] + gap
                        )
                        if not ignore:
                            target.append(end)
                        last = end
                # t2 = perf_counter()
                if other_points and selected_points:
                    np_other = np.asarray(other_points)
                    np_selected = np.asarray(selected_points)
                    dist, pt1, pt2 = shortest_distance(np_other, np_selected, False)

                    if dist is not None and dist < gap:
                        did_snap_to_point = True
                        dx = pt1.real - pt2.real
                        dy = pt1.imag - pt2.imag
                        move_to(dx, dy)
                        # Get new value
                        b = self.scene.context.elements._emphasized_bounds
                        # t3 = perf_counter()
                        # print (f"Snap, compared {len(selected_points)} pts to {len(other_points)} pts. Total time: {t3-t1:.2f}sec, Generation: {t2-t1:.2f}sec, shortest: {t3-t2:.2f}sec")
            if (
                self.scene.context.snap_grid
                and "shift" not in modifiers
                and b is not None
                and not did_snap_to_point
            ):
                # t1 = perf_counter()
                gap = self.scene.context.grid_attract_len / get_matrix_scale(matrix)
                # Check for corner points + center:
                selected_points = (
                    (b[0], b[1]),
                    (b[2], b[1]),
                    (b[0], b[3]),
                    (b[2], b[3]),
                    ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2),
                )
                other_points = self.scene.pane.grid.grid_points
                if other_points and selected_points:
                    np_other = np.asarray(other_points)
                    np_selected = np.asarray(selected_points)
                    dist, pt1, pt2 = shortest_distance(np_other, np_selected, True)
                    if dist is not None and dist < gap:
                        # did_snap_to_point = True
                        dx = pt1[0] - pt2[0]
                        dy = pt1[1] - pt2[1]
                        move_to(dx, dy)
                        # Get new value
                        b = self.scene.context.elements._emphasized_bounds

                # t2 = perf_counter()
                # print (f"Corner-points, compared {len(selected_points)} pts to {len(other_points)} pts. Total time: {t2-t1:.2f}sec")
                # Even then magnets win!
                dx, dy = self.scene.pane.revised_magnet_bound(b)
                move_to(dx, dy)

        if modifiers is not None:
            self.modifiers = modifiers

        elements = self.scene.context.elements
        if event_type == "leftdown":
            check_leftdown(space_pos)
            # print ("RectSelect consumed leftdown")
            return RESPONSE_CONSUME
        elif event_type == "leftclick":
            check_click(space_pos)
            return RESPONSE_CHAIN
        elif event_type == "leftup":
            if self.mode == "select":
                if self.start_location is None:
                    return RESPONSE_CHAIN
                check_leftup_select(space_pos)
            else:
                check_leftup_move(space_pos)

            self.reset()

            return RESPONSE_CONSUME
        elif event_type == "move":
            check_move(space_pos)
            return RESPONSE_CONSUME
        elif event_type == "lost":
            self.reset()
            return RESPONSE_CONSUME
        return RESPONSE_DROP

    def reset(self):
        self.start_location = None
        self.end_location = None
        self.mode = "unclear"
        self.mouse_down_time = 0
        self.can_drag_move = False
        self.scene.cursor("arrow")

    def draw_rectangle(self, gc, x0, y0, x1, y1, tcolor, tstyle):
        # Linux / Darwin do not recognize the GraphicsContext TransformationMatrix
        # when drawing dashed/dotted lines, so they always appear to be solid
        # (even if they are dotted on a microscopic level)
        # To circumvent this issue, we scale the gc back
        gc.PushState()
        sx, sy = get_gc_full_scale(gc)
        gc.Scale(1 / sx, 1 / sy)
        self.selection_pen.SetColour(tcolor)
        self.selection_pen.SetStyle(tstyle)
        gc.SetPen(self.selection_pen)
        linewidth = 1
        try:
            self.selection_pen.SetWidth(linewidth)
        except TypeError:
            self.selection_pen.SetWidth(int(linewidth))
        gc.SetPen(self.selection_pen)
        gc.StrokeLine(x0 * sx, y0 * sy, x1 * sx, y0 * sy)
        gc.StrokeLine(x1 * sx, y0 * sy, x1 * sx, y1 * sy)
        gc.StrokeLine(x1 * sx, y1 * sy, x0 * sx, y1 * sy)
        gc.StrokeLine(x0 * sx, y1 * sy, x0 * sx, y0 * sy)
        gc.PopState()

    def draw_tiny_indicator(self, gc, symbol, x0, y0, x1, y1, tcolor, tstyle):
        # Linux / Darwin do not recognize the GraphicsContext TransformationMatrix
        # when drawing dashed/dotted lines, so they always appear to be solid
        # (even if they are dotted on a microscopic level)
        # To circumvent this issue, we scale the gc back
        gc.PushState()
        sx, sy = get_gc_full_scale(gc)
        # print (f"sx={sx}, sy={sy}")
        gc.Scale(1 / sx, 1 / sy)
        self.selection_pen.SetColour(tcolor)
        self.selection_pen.SetStyle(tstyle)

        linewidth = 1
        try:
            self.selection_pen.SetWidth(linewidth)
        except TypeError:
            self.selection_pen.SetWidth(int(linewidth))
        gc.SetPen(self.selection_pen)
        delta_X = 15.0 * self.magnification
        delta_Y = 15.0 * self.magnification
        x0 *= sx
        x1 *= sx
        y0 *= sx
        y1 *= sx
        if abs(x1 - x0) > delta_X and abs(y1 - y0) > delta_Y:  # Don't draw if too tiny
            # Draw tiny '+' in corner of pointer
            x_signum = +1 * delta_X if x0 < x1 else -1 * delta_X
            y_signum = +1 * delta_Y if y0 < y1 else -1 * delta_Y
            ax1 = x1 - x_signum
            ay1 = y1 - y_signum

            gc.SetPen(self.selection_pen)
            gc.StrokeLine(ax1, y1, ax1, ay1)
            gc.StrokeLine(ax1, ay1, x1, ay1)
            font_size = 10.0 * self.magnification
            font_size = max(
                font_size, 1.0
            )  # Darwin issues a TypeError if font size is smaller than 1
            try:
                font = wx.Font(
                    font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            except TypeError:
                font = wx.Font(
                    int(font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            gc.SetFont(font, tcolor)
            (t_width, t_height) = gc.GetTextExtent(symbol)
            gc.DrawText(
                symbol, (ax1 + x1) / 2 - t_width / 2, (ay1 + y1) / 2 - t_height / 2
            )
            if (
                abs(x1 - x0) > 2 * delta_X and abs(y1 - y0) > 2 * delta_Y
            ):  # Don't draw if too tiny
                # Draw second symbol at origin
                ax1 = x0 + x_signum
                ay1 = y0 + y_signum
                gc.StrokeLine(ax1, y0, ax1, ay1)
                gc.StrokeLine(ax1, ay1, x0, ay1)
                gc.DrawText(
                    symbol, (ax1 + x0) / 2 - t_width / 2, (ay1 + y0) / 2 - t_height / 2
                )
        gc.PopState()

    def process_draw(self, gc):
        """
        Draw the selection rectangle
        """
        if (
            self.mode == "select"
            and self.start_location is not None
            and self.end_location is not None
        ):
            self.selection_style[0][0] = self.scene.colors.color_selection1
            self.selection_style[1][0] = self.scene.colors.color_selection2
            self.selection_style[2][0] = self.scene.colors.color_selection3
            x0 = self.start_location[0]
            y0 = self.start_location[1]
            x1 = self.end_location[0]
            y1 = self.end_location[1]
            sector = self.sector

            _ = self.scene.context._
            statusmsg = _(self.selection_style[self.selection_method[sector] - 1][2])
            if "shift" in self.modifiers:
                statusmsg += _(self.selection_text_shift)
            elif "ctrl" in self.modifiers:
                statusmsg += _(self.selection_text_control)

            self.update_statusmsg(statusmsg)
            gcstyle = self.selection_style[self.selection_method[sector] - 1][0]
            gccolor = self.selection_style[self.selection_method[sector] - 1][1]
            self.draw_rectangle(
                gc,
                x0,
                y0,
                x1,
                y1,
                gcstyle,
                gccolor,
            )

            # Determine Colour on selection mode: standard (from left top to right bottom) = Blue, else Green
            # Draw indicator...
            if "shift" in self.modifiers:
                self.draw_tiny_indicator(
                    gc,
                    "+",
                    x0,
                    y0,
                    x1,
                    y1,
                    gcstyle,
                    gccolor,
                )

            elif "ctrl" in self.modifiers:
                self.draw_tiny_indicator(
                    gc,
                    "^",
                    x0,
                    y0,
                    x1,
                    y1,
                    self.selection_style[self.selection_method[sector] - 1][0],
                    self.selection_style[self.selection_method[sector] - 1][1],
                )
