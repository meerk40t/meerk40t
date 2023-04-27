import wx

from meerk40t.gui.scene.scene import (
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.scene.widget import Widget


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

    def hit(self):
        return HITCHAIN_HIT

    store_last_msg = ""

    def update_statusmsg(self, value):
        if value != self.store_last_msg:
            self.store_last_msg = value
            self.scene.context.signal("statusmsg", value)

    # debug_msg = ""

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        if modifiers is not None:
            self.modifiers = modifiers

        elements = self.scene.context.elements
        if event_type == "leftdown":
            self.start_location = space_pos
            self.end_location = space_pos
            # print ("RectSelect consumed leftdown")
            return RESPONSE_CONSUME
        elif event_type == "leftclick":
            # That's too fast
            # still chaining though
            self.scene.request_refresh()
            self.start_location = None
            self.end_location = None
            return RESPONSE_CHAIN
        elif event_type == "leftup":
            if self.start_location is None:
                return RESPONSE_CHAIN
            _ = self.scene.context._
            self.update_statusmsg(_("Status"))
            elements.validate_selected_area()
            sx = self.start_location[0]
            sy = self.start_location[1]
            ex = self.end_location[0]
            ey = self.end_location[1]
            if sx <= ex:
                if sy <= ey:
                    sector = 0
                else:
                    sector = 1
            else:
                if sy <= ey:
                    sector = 3
                else:
                    sector = 2

            sx = min(self.start_location[0], self.end_location[0])
            sy = min(self.start_location[1], self.end_location[1])
            ex = max(self.start_location[0], self.end_location[0])
            ey = max(self.start_location[1], self.end_location[1])
            for node in elements.elems():
                try:
                    q = node.bounds
                except AttributeError:
                    continue  # This element has no bounds.
                if q is None:
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
                elif "ctrl" in self.modifiers:
                    # Invert Selection
                    if cover >= self.selection_method[sector]:
                        node.emphasized = not node.emphasized
                        node.selected = node.emphasized
                else:
                    # Replace Selection
                    if cover >= self.selection_method[sector]:
                        node.emphasized = True
                        node.selected = True
                    else:
                        node.emphasized = False
                        node.selected = False

            self.scene.request_refresh()
            self.scene.context.signal("select_emphasized_tree", 0)

            self.start_location = None
            self.end_location = None

            return RESPONSE_CONSUME
        elif event_type == "move":
            self.scene.request_refresh()
            self.end_location = space_pos
            return RESPONSE_CONSUME
        elif event_type == "lost":
            self.start_location = None
            self.end_location = None
            return RESPONSE_CONSUME
        return RESPONSE_DROP

    def draw_rectangle(self, gc, x0, y0, x1, y1, tcolor, tstyle):
        matrix = self.parent.matrix
        self.selection_pen.SetColour(tcolor)
        self.selection_pen.SetStyle(tstyle)
        gc.SetPen(self.selection_pen)

        linewidth = 2.0 / matrix.value_scale_x()
        if linewidth < 1:
            linewidth = 1
        try:
            self.selection_pen.SetWidth(linewidth)
        except TypeError:
            self.selection_pen.SetWidth(int(linewidth))
        gc.SetPen(self.selection_pen)
        gc.StrokeLine(x0, y0, x1, y0)
        gc.StrokeLine(x1, y0, x1, y1)
        gc.StrokeLine(x1, y1, x0, y1)
        gc.StrokeLine(x0, y1, x0, y0)

    def draw_tiny_indicator(self, gc, symbol, x0, y0, x1, y1, tcolor, tstyle):
        matrix = self.parent.matrix
        self.selection_pen.SetColour(tcolor)
        self.selection_pen.SetStyle(tstyle)

        linewidth = 2.0 / matrix.value_scale_x()
        if linewidth < 1:
            linewidth = 1
        try:
            self.selection_pen.SetWidth(linewidth)
        except TypeError:
            self.selection_pen.SetWidth(int(linewidth))
        gc.SetPen(self.selection_pen)
        delta_X = 15.0 / matrix.value_scale_x()
        delta_Y = 15.0 / matrix.value_scale_y()
        if abs(x1 - x0) > delta_X and abs(y1 - y0) > delta_Y:  # Don't draw if too tiny
            # Draw tiny '+' in corner of pointer
            x_signum = +1 * delta_X if x0 < x1 else -1 * delta_X
            y_signum = +1 * delta_Y if y0 < y1 else -1 * delta_X
            ax1 = x1 - x_signum
            ay1 = y1 - y_signum

            gc.SetPen(self.selection_pen)
            gc.StrokeLine(ax1, y1, ax1, ay1)
            gc.StrokeLine(ax1, ay1, x1, ay1)
            font_size = 10.0 / matrix.value_scale_x()
            if font_size < 1.0:
                font_size = 1.0
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

    def process_draw(self, gc):
        """
        Draw the selection rectangle
        """
        if self.start_location is not None and self.end_location is not None:
            self.selection_style[0][0] = self.scene.colors.color_selection1
            self.selection_style[1][0] = self.scene.colors.color_selection2
            self.selection_style[2][0] = self.scene.colors.color_selection3
            x0 = self.start_location[0]
            y0 = self.start_location[1]
            x1 = self.end_location[0]
            y1 = self.end_location[1]
            if x0 <= x1:
                if y0 <= y1:
                    sector = 0
                else:
                    sector = 1
            else:
                if y0 <= y1:
                    sector = 3
                else:
                    sector = 2

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
