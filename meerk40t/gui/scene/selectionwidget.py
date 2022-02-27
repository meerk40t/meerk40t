
import wx

from meerk40t.gui.laserrender import DRAW_MODE_SELECTION
from meerk40t.gui.scene.scene import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    Widget,
)
from meerk40t.gui.wxutils import create_menu


class SelectionWidget(Widget):
    """
    Selection Widget it tasked with drawing the selection box and managing the events
    dealing with moving, resizing and altering the selected object.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(wx.Colour(0xA0, 0x7F, 0xA0))
        self.selection_pen.SetStyle(wx.PENSTYLE_DOT)
        self.save_width = None
        self.save_height = None
        self.tool = self.tool_translate
        self.cursor = None
        self.uniform = True

    def hit(self):
        elements = self.scene.context.elements
        try:
            bounds = elements.selected_area()
        except AttributeError:
            bounds = None
        if bounds is not None:
            self.left = bounds[0]
            self.top = bounds[1]
            self.right = bounds[2]
            self.bottom = bounds[3]

            # Adjust boundaries to ensure a minimum height / width so that
            # dots and horizontal / vertical lines get a move icon
            width = self.right - self.left
            height = self.bottom - self.top
            matrix = self.parent.matrix
            # Twice size of equivalent in event:hover
            try:
                xmin = 10 / matrix.value_scale_x()
                ymin = 10 / matrix.value_scale_y()
            except ZeroDivisionError:
                matrix.reset()
                ymin = 10
                xmin = 10
            if width < xmin:
                width = (xmin - width) / 2
                self.left -= width
                self.right += width
            if height < ymin:
                height = (ymin - height) / 2
                self.top -= height
                self.bottom += height

            self.clear()
            return HITCHAIN_HIT
        else:
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")
            self.clear()
            return HITCHAIN_DELEGATE

    key_shift_pressed = False
    key_control_pressed = False
    key_alt_pressed = False
    was_lb_raised = False
    hovering = False
    # debug_msg = ""

    def stillinside(self, space_pos=None):
        res = False
        matrix = self.parent.matrix
        if not space_pos is None:
            sx = space_pos[0]
            sy = space_pos[1]
            # print ("left=%f, right=%f, top=%f, bottom=%f, x=%f, y=%f" % (self.left, self.right, self.top, self.bottom, sx, sy))

            if (self.left <= sx <= self.right) and (self.top <= sy <= self.bottom):
                # print ("inside")
                res = True
        return res

    def event(self, window_pos=None, space_pos=None, event_type=None):

        elements = self.scene.context.elements

        # sdbg = event_type
        # if sdbg in ("hover_start", "hover_end", "hover"):
        #    sdbg = "hover"
        # if sdbg != self.debug_msg:
        #    self.debug_msg = sdbg
        #    print(
        #        "Selection-Event: %s (current state: %s)"
        #        % (event_type, self.was_lb_raised)
        #    )

        if event_type == "kb_shift_release":
            if self.key_shift_pressed:
                self.key_shift_pressed = False
                if self.stillinside(space_pos):
                    self.scene.cursor("sizing")
                    self.hovering = True
                    self.tool = self.tool_translate
            return RESPONSE_CHAIN
        elif event_type == "kb_shift_press":
            if not self.key_shift_pressed:
                self.key_shift_pressed = True
            # Are we hovering ? If yes reset cursor
            if self.hovering:
                self.hovering = False
                self.scene.cursor("arrow")
            return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_release":
            if self.key_control_pressed:
                self.key_control_pressed = False
                if self.stillinside(space_pos):
                    self.scene.cursor("sizing")
                    self.hovering = True
                    self.tool = self.tool_translate
            return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_press":
            if not self.key_control_pressed:
                self.key_control_pressed = True
            # Are we hovering ? If yes reset cursor
            if self.hovering:
                self.hovering = False
                self.scene.cursor("arrow")
            return RESPONSE_CHAIN
        elif event_type == "kb_alt_release":
            if self.key_alt_pressed:
                self.key_alt_pressed = False
            return RESPONSE_CHAIN
        elif event_type == "kb_alt_press":
            if not self.key_alt_pressed:
                self.key_alt_pressed = True
            return RESPONSE_CHAIN
        elif event_type == "hover_start":
            self.scene.cursor("sizing")
            self.hovering = True
            return RESPONSE_CHAIN
        elif event_type == "hover_end" or event_type == "lost":
            self.scene.cursor("arrow")
            self.hovering = False
            return RESPONSE_CHAIN
        elif event_type == "hover":
            if self.hovering:
                matrix = self.parent.matrix
                xin = space_pos[0] - self.left
                yin = space_pos[1] - self.top
                # Half size of equivalent in hit
                xmin = 5 / matrix.value_scale_x()
                ymin = 5 / matrix.value_scale_y()
                # Adjust sizing of hover border as follows:
                # 1. If object is very small so move area is smaller than 1/2 or even non-existent, prefer move to size by setting border to zero
                # 2. Otherwise try to expand by up to 2 (to make it easier to hover) but never less than xmin and never expanded
                #    to be more than 1/4 of the width or height
                xmin = (
                    min(xmin * 2.0, max(self.width / 4.0, xmin))
                    if xmin <= self.width / 4.0
                    else 0.0
                )
                ymin = (
                    min(ymin * 2.0, max(self.height / 4.0, ymin))
                    if ymin <= self.height / 4.0
                    else 0.0
                )
                xmax = self.width - xmin
                ymax = self.height - ymin
                for e in elements.elems(emphasized=True):
                    try:
                        if e.lock:
                            self.scene.cursor("sizing")
                            self.tool = self.tool_translate
                            return RESPONSE_CHAIN
                    except (ValueError, AttributeError):
                        pass
                if xin >= xmax and yin >= ymax:
                    self.scene.cursor("size_se")
                    self.tool = self.tool_scalexy_se
                elif xin <= xmin and yin <= ymin:
                    self.scene.cursor("size_nw")
                    self.tool = self.tool_scalexy_nw
                elif xin >= xmax and yin <= ymin:
                    self.scene.cursor("size_ne")
                    self.tool = self.tool_scalexy_ne
                elif xin <= xmin and yin >= ymax:
                    self.scene.cursor("size_sw")
                    self.tool = self.tool_scalexy_sw
                elif xin <= xmin:
                    self.scene.cursor("size_w")
                    self.tool = self.tool_scalex_w
                elif yin <= ymin:
                    self.scene.cursor("size_n")
                    self.tool = self.tool_scaley_n
                elif xin >= xmax:
                    self.scene.cursor("size_e")
                    self.tool = self.tool_scalex_e
                elif yin >= ymax:
                    self.scene.cursor("size_s")
                    self.tool = self.tool_scaley_s
                else:
                    self.scene.cursor("sizing")
                    self.tool = self.tool_translate
            return RESPONSE_CHAIN
        dx = space_pos[4]
        dy = space_pos[5]

        if event_type == "rightdown":
            elements.set_emphasized_by_position(space_pos)
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            create_menu(
                self.scene.context.gui, elements.top_element(emphasized=True), elements
            )
            return RESPONSE_CONSUME
        elif event_type == "doubleclick":
            elements.set_emphasized_by_position(space_pos)
            elements.signal("activate_selected_nodes", 0)
            return RESPONSE_CONSUME
        elif event_type == "leftdown":
            # Lets'check if the Ctrl or Shift Keys are pressed, if yes ignore the event, as they belong to the selection rectangle
            if not (self.key_control_pressed or self.key_shift_pressed):
                self.was_lb_raised = True
                self.save_width = self.width
                self.save_height = self.height
                self.uniform = True
                if (
                    self.key_alt_pressed
                ):  # Duplicate the selection in the background and start moving
                    self.create_duplicate()
                self.tool(space_pos, dx, dy, -1)
                return RESPONSE_CONSUME
        elif event_type == "middledown":
            self.was_lb_raised = False
            self.save_width = self.width
            self.save_height = self.height
            self.uniform = False
            self.tool(space_pos, dx, dy, -1)
            return RESPONSE_CONSUME
        elif event_type == "leftup":
            if self.was_lb_raised:
                self.tool(space_pos, dx, dy, 1)
                self.scene.context.elements.ensure_positive_bounds()
                self.was_lb_raised = False
                return RESPONSE_CONSUME
        elif event_type in ("middleup", "lost"):
            if self.was_lb_raised:
                self.was_lb_raised = False
                self.tool(space_pos, dx, dy, 1)
                self.scene.context.elements.ensure_positive_bounds()
                return RESPONSE_CONSUME
        elif event_type == "move":
            if self.was_lb_raised:
                if not elements.has_emphasis():
                    return RESPONSE_CONSUME
                if self.save_width is None or self.save_height is None:
                    self.save_width = self.width
                    self.save_height = self.height
                self.tool(space_pos, dx, dy, 0)
                return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def tool_scalexy(self, position, dx, dy, event=0):
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scalex = (position[0] - self.left) / self.save_width
            scaley = (position[1] - self.top) / self.save_height
            self.save_width *= scalex
            self.save_height *= scaley
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, self.left, self.top)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds([b[0], b[1], position[0], position[1]])
            self.scene.request_refresh()

    def tool_scalexy_se(self, position, dx, dy, event=0):
        """
        Change scale vs the bottom right corner.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scalex = (position[0] - self.left) / self.save_width
            scaley = (position[1] - self.top) / self.save_height
            if self.uniform:
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale
            self.save_width *= scalex
            self.save_height *= scaley
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, self.left, self.top)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds(
                [b[0], b[1], b[0] + self.save_width, b[1] + self.save_height]
            )
            self.scene.request_refresh()

    def tool_scalexy_nw(self, position, dx, dy, event=0):
        """
        Change scale from the top left corner.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scalex = (self.right - position[0]) / self.save_width
            scaley = (self.bottom - position[1]) / self.save_height
            if self.uniform:
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale
            self.save_width *= scalex
            self.save_height *= scaley
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, self.right, self.bottom)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds(
                [b[2] - self.save_width, b[3] - self.save_height, b[2], b[3]]
            )
            self.scene.request_refresh()

    def tool_scalexy_ne(self, position, dx, dy, event=0):
        """
        Change scale from the top right corner.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scalex = (position[0] - self.left) / self.save_width
            scaley = (self.bottom - position[1]) / self.save_height
            if self.uniform:
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale
            self.save_width *= scalex
            self.save_height *= scaley
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, self.left, self.bottom)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds(
                [b[0], b[3] - self.save_height, b[0] + self.save_width, b[3]]
            )
            self.scene.request_refresh()

    def tool_scalexy_sw(self, position, dx, dy, event=0):
        """
        Change scale from the bottom left corner.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scalex = (self.right - position[0]) / self.save_width
            scaley = (position[1] - self.top) / self.save_height
            if self.uniform:
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale
            self.save_width *= scalex
            self.save_height *= scaley
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, self.right, self.top)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds(
                [b[2] - self.save_width, b[1], b[2], b[1] + self.save_height]
            )
            self.scene.request_refresh()

    def tool_scalex_e(self, position, dx, dy, event=0):
        """
        Change scale from the right side.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scalex = (position[0] - self.left) / self.save_width
            self.save_width *= scalex
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, 1, self.left, self.top)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds([b[0], b[1], position[0], b[3]])
            self.scene.request_refresh()

    def tool_scalex_w(self, position, dx, dy, event=0):
        """
        Change scale from the left side.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scalex = (self.right - position[0]) / self.save_width
            self.save_width *= scalex
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, 1, self.right, self.top)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds([position[0], b[1], b[2], b[3]])
            self.scene.request_refresh()

    def tool_scaley_s(self, position, dx, dy, event=0):
        """
        Change scale from the bottom side.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scaley = (position[1] - self.top) / self.save_height
            self.save_height *= scaley
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(1, scaley, self.left, self.top)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds([b[0], b[1], b[2], position[1]])
            self.scene.request_refresh()

    def tool_scaley_n(self, position, dx, dy, event=0):
        """
        Change scale from the top side.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            scaley = (self.bottom - position[1]) / self.save_height
            self.save_height *= scaley
            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(1, scaley, self.left, self.bottom)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            elements.update_bounds([b[0], position[1], b[2], b[3]])
            self.scene.request_refresh()

    def tool_translate(self, position, dx, dy, event=0):
        """
        Change the position of the selected elements.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.node.modified()
        if event == 0:
            b = elements.selected_area()
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                obj.transform.post_translate(dx, dy)
            for e in elements.flat(types=("group", "file")):
                e._bounds_dirty = True
            self.translate(dx, dy)
            elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def process_draw(self, gc):
        """
        Draw routine for drawing the selection box.
        """
        if self.scene.context.draw_mode & DRAW_MODE_SELECTION != 0:
            return
        context = self.scene.context
        draw_mode = context.draw_mode
        elements = self.scene.context.elements
        bounds = elements.selected_area()
        matrix = self.parent.matrix
        if bounds is not None:
            try:
                linewidth = 2.0 / matrix.value_scale_x()
                font_size = 14.0 / matrix.value_scale_x()
            except ZeroDivisionError:
                matrix.reset()
                return
            try:
                self.selection_pen.SetWidth(linewidth)
            except TypeError:
                self.selection_pen.SetWidth(int(linewidth))
            if font_size < 1.0:
                font_size = 1.0  # Mac does not allow values lower than 1.
            try:
                font = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            except TypeError:
                font = wx.Font(int(font_size), wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, wx.Colour(0x7F, 0x7F, 0x7F))
            gc.SetPen(self.selection_pen)
            x0, y0, x1, y1 = bounds
            center_x = (x0 + x1) / 2.0
            center_y = (y0 + y1) / 2.0
            gc.StrokeLine(center_x, 0, center_x, y0)
            gc.StrokeLine(0, center_y, x0, center_y)
            gc.StrokeLine(x0, y0, x1, y0)
            gc.StrokeLine(x1, y0, x1, y1)
            gc.StrokeLine(x1, y1, x0, y1)
            gc.StrokeLine(x0, y1, x0, y0)
            if draw_mode & DRAW_MODE_SELECTION == 0:
                p = self.scene.context
                units = p.units_name
                # scale(%.13f,%.13f)
                gc.DrawText(
                    "{distance:.2f}{units}".format(
                        distance=p.device.length(y0, 1, new_units=units, as_float=True),
                        units=units,
                    ),
                    center_x,
                    y0 / 2.0,
                )
                gc.DrawText(
                    "{distance:.2f}{units}".format(
                        distance=p.device.length(x0, 0, new_units=units, as_float=True),
                        units=units,
                    ),
                    x0 / 2.0,
                    center_y,
                )
                gc.DrawText(
                    "{distance:.2f}{units}".format(
                        distance=p.device.length(
                            (y1 - y0), 1, new_units=units, as_float=True
                        ),
                        units=units,
                    ),
                    x1,
                    center_y,
                )
                gc.DrawText(
                    "{distance:.2f}{units}".format(
                        distance=p.device.length(
                            (x1 - x0), 0, new_units=units, as_float=True
                        ),
                        units=units,
                    ),
                    center_x,
                    y1,
                )

    def create_duplicate(self):
        from copy import copy

        self.duplicated_elements = True
        # Iterate through list of selected elements, duplicate them

        context = self.scene.context
        elements = context.elements
        adding_elements = [copy(e) for e in list(elements.elems(emphasized=True))]
        elements.add_elems(adding_elements)
        elements.classify(adding_elements)
