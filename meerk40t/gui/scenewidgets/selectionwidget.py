import math
import wx

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_SELECTION
from meerk40t.gui.scene.scene import (
    HITCHAIN_DELEGATE,
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
)
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT_AND_DELEGATE
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.wxutils import create_menu_for_node

from meerk40t.svgelements import Rect, Point

TEXT_COLOR = wx.Colour(0xA0, 0x7F, 0xA0)
LINE_COLOR = wx.Colour(0x7F, 0x7F, 0x7F)


def process_event(
    widget,
    widget_identifier=None,
    window_pos=None,
    space_pos=None,
    event_type=None,
    helptext="",
    optimize_drawing=True,
):
    if widget_identifier is None:
        widget_identifier = "none"
    # print("Its me - %s, event=%s, pos=%s" % (widget_identifier, event_type, space_pos))
    # Keyboard-Events...
    if event_type == "kb_shift_release":
        if widget.key_shift_pressed:
            widget.key_shift_pressed = False
            if widget.contains(space_pos[0], space_pos[1]):
                widget.scene.cursor(widget.cursor)
                widget.hovering = True
        return RESPONSE_CHAIN
    elif event_type == "kb_shift_press":
        if not widget.key_shift_pressed:
            widget.key_shift_pressed = True
        # Are we hovering ? If yes reset cursor
        if widget.hovering:
            widget.hovering = False
            widget.scene.cursor("arrow")
        return RESPONSE_CHAIN
    elif event_type == "kb_ctrl_release":
        if widget.key_control_pressed:
            widget.key_control_pressed = False
            if widget.contains(space_pos[0], space_pos[1]):
                widget.scene.cursor("sizing")
                widget.hovering = True
        return RESPONSE_CHAIN
    elif event_type == "kb_ctrl_press":
        if not widget.key_control_pressed:
            widget.key_control_pressed = True
        # Are we hovering ? If yes reset cursor
        if widget.hovering:
            widget.hovering = False
            widget.scene.cursor("arrow")
        return RESPONSE_CHAIN
    elif event_type == "kb_alt_release":
        if widget.key_alt_pressed:
            widget.key_alt_pressed = False
        return RESPONSE_CHAIN
    elif event_type == "kb_alt_press":
        if not widget.key_alt_pressed:
            widget.key_alt_pressed = True
        return RESPONSE_CHAIN
    try:
        inside = widget.contains(space_pos[0], space_pos[1])
    except TypeError:
        # Widget already destroyed ?!
        # print ("Something went wrong for %s" % widget_identifier)
        return RESPONSE_CHAIN

    # Now all Mouse-Hover-Events
    _ = widget.scene.context._
    if event_type == "hover" and widget.hovering and not inside:
        # print ("Hover %s, That was not for me ?!" % widget_identifier)
        widget.hovering = False
        widget.scene.cursor("arrow")
        widget.scene.context.signal("statusmsg", "")

        return RESPONSE_CHAIN

    if event_type == "hover_start":
        widget.scene.cursor(widget.cursor)
        widget.hovering = True
        widget.scene.context.signal("statusmsg", _(helptext))
        return RESPONSE_CONSUME
    elif event_type == "hover_end" or event_type == "lost":
        widget.scene.cursor("arrow")
        widget.hovering = False
        widget.scene.context.signal("statusmsg", "")
        return RESPONSE_CHAIN
    elif event_type == "hover":
        widget.hovering = True
        widget.scene.cursor(widget.cursor)
        widget.scene.context.signal("statusmsg", _(helptext))
        return RESPONSE_CONSUME

    # Now all Mouse-Click-Events
    elements = widget.scene.context.elements
    dx = space_pos[4]
    dy = space_pos[5]

    if event_type == "leftdown":
        if not (widget.key_control_pressed or widget.key_shift_pressed):
            widget.was_lb_raised = True
            widget.save_width = widget.master.width
            widget.save_height = widget.master.height
            widget.uniform = not widget.key_alt_pressed
            widget.master.total_delta_x = dx
            widget.master.total_delta_y = dy
            widget.master.tool_running = optimize_drawing
            widget.master.invalidate_rot_center()
            widget.master.check_rot_center()
            widget.tool(space_pos, dx, dy, -1)
            return RESPONSE_CONSUME
    elif event_type == "middledown":
        # Hmm, I think this is never called due to the consumption of this evennt by scene pane...
        widget.was_lb_raised = False
        widget.save_width = widget.master.width
        widget.save_height = widget.master.height
        widget.uniform = False
        widget.master.total_delta_x = dx
        widget.master.total_delta_y = dy
        widget.master.tool_running = optimize_drawing
        widget.tool(space_pos, dx, dy, -1)
        return RESPONSE_CONSUME
    elif event_type == "leftup":
        if widget.was_lb_raised:
            widget.tool(space_pos, dx, dy, 1)
            widget.scene.context.elements.ensure_positive_bounds()
            widget.was_lb_raised = False
            widget.master.show_border = True
            widget.master.tool_running = False
            return RESPONSE_CONSUME
    elif event_type in ("middleup", "lost"):
        if widget.was_lb_raised:
            widget.tool(space_pos, dx, dy, 1)
            widget.was_lb_raised = False
            widget.master.show_border = True
            widget.master.tool_running = False
            widget.scene.context.elements.ensure_positive_bounds()
            return RESPONSE_CONSUME
    elif event_type == "move":
        if widget.was_lb_raised:
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            if widget.save_width is None or widget.save_height is None:
                widget.save_width = widget.width
                widget.save_height = widget.height
            widget.master.total_delta_x += dx
            widget.master.total_delta_y += dy
            widget.tool(space_pos, dx, dy, 0)
            return RESPONSE_CONSUME
    elif event_type == "leftclick":
        if widget.was_lb_raised:
            widget.tool(space_pos, dx, dy, 1)
            widget.scene.context.elements.ensure_positive_bounds()
            widget.was_lb_raised = False
            widget.master.tool_running = False
            widget.master.show_border = True
            return RESPONSE_CONSUME
    else:
        return RESPONSE_CHAIN


class BorderWidget(Widget):
    """
    Border Widget it tasked with drawing the selection box
    """

    def __init__(self, master, scene):
        self.master = master
        self.scene = scene
        self.cursor = None
        Widget.__init__(
            self,
            scene,
            self.master.left,
            self.master.top,
            self.master.right,
            self.master.bottom,
        )
        self.update()

    def update(self):
        self.left = self.master.left
        self.top = self.master.top
        self.right = self.master.right
        self.bottom = self.master.bottom

    def hit(self):
        return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        return RESPONSE_CHAIN

    def process_draw(self, gc):
        """
        Draw routine for drawing the selection box.
        """
        context = self.scene.context
        self.update()

        center_x = (self.left + self.right) / 2.0
        center_y = (self.top + self.bottom) / 2.0
        gc.SetPen(self.master.selection_pen)
        # Wont be display when rotating...
        if self.master.show_border:
            gc.StrokeLine(center_x, 0, center_x, self.top)
            gc.StrokeLine(0, center_y, self.left, center_y)
            gc.StrokeLine(self.left, self.top, self.right, self.top)
            gc.StrokeLine(self.right, self.top, self.right, self.bottom)
            gc.StrokeLine(self.right, self.bottom, self.left, self.bottom)
            gc.StrokeLine(self.left, self.bottom, self.left, self.top)
            # print ("Inner Drawmode=%d (logic=%s)" % ( draw_mode ,(draw_mode & DRAW_MODE_SELECTION) ))
            # if draw_mode & DRAW_MODE_SELECTION == 0:
            units = context.units_name
            try:
                font = wx.Font(self.master.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            except TypeError:
                font = wx.Font(int(self.master.font_size), wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, TEXT_COLOR)
            gc.DrawText(
                str(Length(amount=self.top, digits=3, preferred_units=units)),
                center_x,
                self.top / 2.0,
            )
            gc.DrawText(
                str(Length(amount=self.left, digits=3, preferred_units=units)),
                self.left / 2.0,
                center_y,
            )
            gc.DrawText(
                str(
                    Length(
                        amount=(self.bottom - self.top), digits=3, preferred_units=units
                    )
                ),
                self.right,
                center_y,
            )
            gc.DrawText(
                str(
                    Length(
                        amount=(self.right - self.left), digits=3, preferred_units=units
                    )
                ),
                center_x,
                self.bottom,
            )
        # But show the angle
        if abs(self.master.rotated_angle) > 0.001:
            try:
                font = wx.Font(
                    0.75 * self.master.font_size, wx.SWISS, wx.NORMAL, wx.BOLD
                )
            except TypeError:
                font = wx.Font(
                    int(0.75 * self.master.font_size), wx.SWISS, wx.NORMAL, wx.BOLD
                )
            gc.SetFont(font, LINE_COLOR)
            symbol = "%.0f°" % (360 * self.master.rotated_angle / math.tau)
            pen = wx.Pen()
            pen.SetColour(LINE_COLOR)
            pen.SetStyle(wx.PENSTYLE_SOLID)
            gc.SetPen(pen)
            brush = wx.Brush(wx.WHITE, wx.SOLID)
            gc.SetBrush(brush)
            (t_width, t_height) = gc.GetTextExtent(symbol)
            gc.DrawEllipse(
                center_x - 0.6 * t_width,
                center_y - 0.6 * t_height,
                1.2 * t_width,
                1.2 * t_height,
            )
            gc.DrawText(
                symbol,
                center_x - 0.5 * t_width,
                center_y - 0.5 * t_height,
            )


class RotationWidget(Widget):
    """
    Rotation Widget it tasked with drawing the rotation box and managing the events
    dealing with rotating the selected object.
    """

    def __init__(self, master, scene, index, size, inner=0):
        self.master = master
        self.scene = scene
        self.index = index
        self.half = size / 2
        self.inner = inner
        self.cursor = "rotate1"
        self.key_shift_pressed = master.key_shift_pressed
        self.key_control_pressed = master.key_control_pressed
        self.key_alt_pressed = master.key_alt_pressed
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        self.rotate_cx = None
        self.rotate_cy = None
        self.reference_rect = None

        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.update()

    def update(self):
        if self.index == 0:
            pos_x = self.master.left
            pos_y = self.master.top
        elif self.index == 1:
            pos_x = self.master.right
            pos_y = self.master.top
        elif self.index == 2:
            pos_x = self.master.right
            pos_y = self.master.bottom
        else:
            pos_x = self.master.left
            pos_y = self.master.bottom
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return
        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(0.75 * self.master.line_width)
        except TypeError:
            pen.SetWidth(0.75 * int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        self.update()  # make sure coords are valid
        gc.SetPen(pen)

        cx = (self.left + self.right) / 2
        cy = (self.top + self.bottom) / 2
        if self.index == 0:  # tl
            signx = -1
            signy = -1
        elif self.index == 1:  # tr
            signx = +1
            signy = -1
        elif self.index == 2:  # br
            signx = +1
            signy = +1
        elif self.index == 3:  # bl
            signx = -1
            signy = +1

        # Well, I would have liked to draw a poper arc via dc.DrawArc but the DeviceContext is not available here(?)
        segment = []
        # Start arrow at 0deg, cos = 1, sin = 0
        x = cx + signx * 1 * self.half
        y = cy + signy * 0 * self.half
        segment += [(x - signx * 1 / 2 * self.inner, y + signy * 1 / 2 * self.inner)]
        segment += [(x, y)]
        segment += [
            (x + 2 / 3 * signx * 1 / 2 * self.inner, y + signy * 1 / 2 * self.inner)
        ]
        segment += [(x, y)]

        # Arc-Segment
        numpts = 8
        for k in range(numpts + 1):
            radi = k * math.pi / (2 * numpts)
            sy = math.sin(radi)
            sx = math.cos(radi)
            x = cx + signx * sx * self.half
            y = cy + signy * sy * self.half
            # print ("Radian=%.1f (%.1f°), sx=%.1f, sy=%.1f, x=%.1f, y=%.1f" % (radi, (radi/math.pi*180), sy, sy, x, y))
            segment += [(x, y)]

        # End arrow at 90deg, cos = 0, sin = 1
        # End Arrow
        x = cx + signx * 0 * self.half
        y = cy + signy * 1 * self.half
        segment += [
            (x + signx * 1 / 2 * self.inner, y + 2 / 3 * signy * 1 / 2 * self.inner)
        ]
        segment += [(x, y)]
        segment += [(x + signx * 1 / 2 * self.inner, y - signy * 1 / 2 * self.inner)]
        gc.SetPen(pen)
        gc.StrokeLines(segment)

    def tool(self, position, dx, dy, event=0):
        """
        Change the rotation of the selected elements.
        """
        rot_angle = 0
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem", "group", "file"), emphasized=True):
                try:
                    obj = e.object
                    obj.node.modified()
                except AttributeError:
                    pass
            self.master.last_angle = None
            self.master.start_angle = None
            self.master.rotated_angle = 0
        elif event == 0:

            if self.rotate_cx is None:
                self.rotate_cx = self.master.rotation_cx
            if self.rotate_cy is None:
                self.rotate_cy = self.master.rotation_cy
            # if self.rotate_cx == self.master.rotation_cx and self.rotate_cy == self.master.rotation_cy:
            #    print ("Rotating around center")
            # else:
            #    print ("Rotating around special point")
            # Improved code by tatarize to establish rotation angle

            current_angle = Point.angle(position[:2], (self.rotate_cx, self.rotate_cy))
            # boost the angle to allow for simpler bigger movements
            if self.master.key_shift_pressed:
                current_angle *= 2
            elif self.master.key_control_pressed:
                current_angle *= 4
            # Bring back to 'regular' radians
            while current_angle > math.tau:
                current_angle -= 1 * math.tau
            while current_angle < math.tau:
                current_angle += 1 * math.tau

            if self.master.last_angle is None:
                self.master.start_angle = current_angle
                self.master.last_angle = current_angle

            # Update Rotation angle...
            if self.master.key_shift_pressed:
                # Only steps of 5 deg
                desired_step = math.pi / 36
                old_angle = current_angle - self.master.start_angle
                new_angle = round(old_angle / desired_step) * desired_step
                current_angle += new_angle - old_angle
            elif self.master.key_control_pressed:
                # Only steps of 15 deg
                desired_step = math.pi / 12
                old_angle = current_angle - self.master.start_angle
                new_angle = round(old_angle / desired_step) * desired_step
                current_angle += new_angle - old_angle

            delta_angle = current_angle - self.master.last_angle
            self.master.last_angle = current_angle
            # Update Rotation angle...
            self.master.rotated_angle = current_angle - self.master.start_angle
            # print(
            #    "Angle to Point=%.1f, last_angle=%.1f, total_angle=%.1f, delta=%.1f"
            #    % (
            #        current_angle / math.pi * 180,
            #        self.master.last_angle / math.pi * 180,
            #        self.master.rotated_angle / math.pi * 180,
            #        delta_angle / math.pi * 180,
            #    )
            # )
            # Bring back to 'regular' radians
            while self.master.rotated_angle > 0.5 * math.tau:
                self.master.rotated_angle -= 1.0 * math.tau
            while self.master.rotated_angle < -0.5 * math.tau:
                self.master.rotated_angle += 1.0 * math.tau
            # Take representation rectangle and rotate it
            # if self.reference_rect is None:
            #    b = elements._emphasized_bounds
            #    self.reference_rect = Rect(
            #        x=b[0], y=b[1], width=b[2] - b[0], height=b[3] - b[1]
            #    )
            # self.reference_rect.transform.post_rotate(
            #    rot_angle, self.rotate_cx, self.rotate_cy
            # )
            # b = self.reference_rect.bbox()

            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_rotate(delta_angle, self.rotate_cx, self.rotate_cy)
                try:
                    obj.node._bounds_dirty = True
                except AttributeError:
                    pass
            # elements.update_bounds([b[0], b[1], b[2], b[3]])

        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def contains(self, x, y=None):
        # Slightly more complex than usual due to the inner exclusion...
        value = False
        if y is None:
            y = x.y
            x = x.x
        if self.left <= x <= self.right and self.top <= y <= self.bottom:
            # print ("rotation was queried:  x=%.1f, y=%.1f, left=%.1f, top=%.1f, right=%.1f, bottom=%.1f" % (x, y, self.left, self.top, self.right, self.bottom))
            value = True
            if (
                self.left + self.half - self.inner / 2
                <= x
                <= self.right - self.half + self.inner / 2
                and self.top + self.half - self.inner / 2
                <= y
                <= self.bottom - self.half + self.inner / 2
            ):
                # print("...but the inner part")
                value = False
        return value

    def inner_contains(self, x, y=None):
        # Slightly more complex than usual due to the inner exclusion...
        value = False
        if y is None:
            y = x.y
            x = x.x
        x0 = self.left
        x1 = self.right
        y0 = self.top
        y1 = self.bottom
        if self.index == 0:  # tl
            x0 += self.half
            y0 += self.half
        elif self.index == 1:  # tr
            x1 -= self.half
            y0 += self.half
        elif self.index == 2:  # br
            x1 -= self.half
            y1 -= self.half
        elif self.index == 3:  # bl
            x0 += self.half
            y1 -= self.half

        if x0 <= x <= x1 and y0 <= y <= y1:
            value = True
            if (
                self.left + self.half - self.inner / 2
                <= x
                <= self.right - self.half + self.inner / 2
                and self.top + self.half - self.inner / 2
                <= y
                <= self.bottom - self.half + self.inner / 2
            ):
                # print("...but the inner part")
                value = False
        return value

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "rotation"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            helptext="Rotate element",
        )
        if event_type == "leftdown":
            self.master.show_border = False
            # Hit in the inner area?
            if self.inner_contains(space_pos[0], space_pos[1]):
                if self.index == 0:  # tl
                    self.rotate_cx = self.master.right
                    self.rotate_cy = self.master.bottom
                elif self.index == 1:  # tr
                    self.rotate_cx = self.master.left
                    self.rotate_cy = self.master.bottom
                elif self.index == 2:  # br
                    self.rotate_cx = self.master.left
                    self.rotate_cy = self.master.top
                elif self.index == 3:  # bl
                    self.rotate_cx = self.master.right
                    self.rotate_cy = self.master.top
            else:
                self.rotate_cx = None
                self.rotate_cy = None
        elif event_type in ("leftclick", "leftup"):
            self.master.show_border = True

        return response


class CornerWidget(Widget):
    """
    Corner Widget it tasked with drawing the corner box and managing the events
    dealing with sizing the selected object in both X- and Y-direction
    """

    def __init__(self, master, scene, index, size):
        self.master = master
        self.scene = scene
        self.index = index
        self.half = size / 2
        self.allow_x = True
        self.allow_y = True
        self.key_shift_pressed = master.key_shift_pressed
        self.key_control_pressed = master.key_control_pressed
        self.key_alt_pressed = master.key_alt_pressed
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        if index == 0:
            self.method = "nw"
        elif index == 1:
            self.method = "ne"
        elif index == 2:
            self.method = "se"
        if index == 3:
            self.method = "sw"
        self.cursor = "size_" + self.method

        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.update()

    def update(self):
        if self.index == 0:
            pos_x = self.master.left
            pos_y = self.master.top
        elif self.index == 1:
            pos_x = self.master.right
            pos_y = self.master.top
        elif self.index == 2:
            pos_x = self.master.right
            pos_y = self.master.bottom
        else:
            pos_x = self.master.left
            pos_y = self.master.bottom
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        brush = wx.Brush(LINE_COLOR, wx.SOLID)
        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        gc.SetBrush(brush)
        gc.DrawRectangle(self.left, self.top, self.width, self.height)

    def tool(self, position, dx, dy, event=0):
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem", "group", "file"), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        if event == 0:
            # Establish origin
            if "n" in self.method:
                orgy = self.master.bottom
            else:
                orgy = self.master.top

            if "e" in self.method:
                orgx = self.master.right
            else:
                orgx = self.master.left

            # Establish scales
            scalex = 1
            scaley = 1
            if "n" in self.method:
                scaley = (self.master.bottom - position[1]) / self.save_height
            elif "s" in self.method:
                scaley = (position[1] - self.master.top) / self.save_height

            if "w" in self.method:
                scalex = (self.master.right - position[0]) / self.save_width
            elif "e" in self.method:
                scalex = (position[0] - self.master.left) / self.save_width

            if len(self.method) > 1 and self.uniform:  # from corner
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale

            self.save_width *= scalex
            self.save_height *= scaley
            # Correct, but slow...
            # b = elements.selected_area()
            b = elements._emphasized_bounds
            if "n" in self.method:
                orgy = self.master.bottom
            else:
                orgy = self.master.top

            if "w" in self.method:
                orgx = self.master.right
            else:
                orgx = self.master.left

            if "n" in self.method:
                b[1] = b[3] - self.save_height
            elif "s" in self.method:
                b[3] = b[1] + self.save_height

            if "e" in self.method:
                b[2] = b[0] + self.save_width
            elif "w" in self.method:
                b[0] = b[2] - self.save_width

            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, orgx, orgy)

            elements.update_bounds([b[0], b[1], b[2], b[3]])

            self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "corner"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            helptext="Size element (with Alt-Key freely)",
        )
        return response


class SideWidget(Widget):
    """
    Side Widget it tasked with drawing the corner box and managing the events
    dealing with sizing the selected object either in X- or Y-direction
    """

    def __init__(self, master, scene, index, size):
        self.master = master
        self.scene = scene
        self.index = index
        self.half = size / 2
        self.key_shift_pressed = master.key_shift_pressed
        self.key_control_pressed = master.key_control_pressed
        self.key_alt_pressed = master.key_alt_pressed
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        if index == 0 or index == 2:
            self.allow_x = True
            self.allow_y = False
        else:
            self.allow_x = False
            self.allow_y = True
        if index == 0:
            self.method = "n"
        elif index == 1:
            self.method = "e"
        elif index == 2:
            self.method = "s"
        if index == 3:
            self.method = "w"
        self.cursor = "size_" + self.method
        self.update()

    def update(self):
        if self.index == 0:
            pos_x = (self.master.left + self.master.right) / 2
            pos_y = self.master.top
        elif self.index == 1:
            pos_x = self.master.right
            pos_y = (self.master.bottom + self.master.top) / 2
        elif self.index == 2:
            pos_x = (self.master.left + self.master.right) / 2
            pos_y = self.master.bottom
        else:
            pos_x = self.master.left
            pos_y = (self.master.bottom + self.master.top) / 2
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        brush = wx.Brush(LINE_COLOR, wx.SOLID)
        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        gc.SetBrush(brush)
        gc.DrawRectangle(self.left, self.top, self.width, self.height)

    def tool(self, position, dx, dy, event=0):
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem", "group", "file"), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        if event == 0:
            # print ("Side-Tool #%d called, method=%s - dx=%.1f, dy=%.1f" % (self.index, self.method, dx, dy))
            # Establish origin
            if "n" in self.method:
                orgy = self.master.bottom
            else:
                orgy = self.master.top

            if "e" in self.method:
                orgx = self.master.right
            else:
                orgx = self.master.left

            # Establish scales
            scalex = 1
            scaley = 1
            if "n" in self.method:
                scaley = (self.master.bottom - position[1]) / self.save_height
            elif "s" in self.method:
                scaley = (position[1] - self.master.top) / self.save_height

            if "w" in self.method:
                scalex = (self.master.right - position[0]) / self.save_width
            elif "e" in self.method:
                scalex = (position[0] - self.master.left) / self.save_width

            if len(self.method) > 1 and self.uniform:  # from corner
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale

            self.save_width *= scalex
            self.save_height *= scaley

            # Correct, but slow...
            # b = elements.selected_area()
            b = elements._emphasized_bounds
            if "n" in self.method:
                orgy = self.master.bottom
            else:
                orgy = self.master.top

            if "w" in self.method:
                orgx = self.master.right
            else:
                orgx = self.master.left

            if "n" in self.method:
                b[1] = b[3] - self.save_height
            elif "s" in self.method:
                b[3] = b[1] + self.save_height

            if "e" in self.method:
                b[2] = b[0] + self.save_width
            elif "w" in self.method:
                b[0] = b[2] - self.save_width

            for obj in elements.elems(emphasized=True):
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_scale(scalex, scaley, orgx, orgy)
                # We leave that to the very end...
                # try:
                #    obj.node._bounds_dirty = True
                # except AttributeError:
                #    pass

            elements.update_bounds([b[0], b[1], b[2], b[3]])

            self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "side"
        s_help = "Size element in %s-direction" % ("Y" if self.index in (0, 2) else "X")
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            helptext=s_help,
        )
        return response


class SkewWidget(Widget):
    """
    Skew Widget it tasked with drawing the skew box and managing the events
    dealing with skewing the selected object either in X- or Y-direction
    """

    def __init__(self, master, scene, is_x, size):
        self.master = master
        self.scene = scene
        self.is_x = is_x
        self.half = size / 2
        self.last_skew = 0
        self.key_shift_pressed = master.key_shift_pressed
        self.key_control_pressed = master.key_control_pressed
        self.key_alt_pressed = master.key_alt_pressed
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "skew_x" if is_x else "skew_y"
        self.update()

    def update(self):
        if self.is_x:
            pos_x = self.master.left + 3 / 4 * (self.master.right - self.master.left)
            pos_y = self.master.bottom
        else:
            pos_x = self.master.right
            pos_y = self.master.top + 1 / 4 * (self.master.bottom - self.master.top)
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        brush = wx.Brush(LINE_COLOR, wx.SOLID)
        gc.SetBrush(brush)
        gc.DrawRectangle(self.left, self.top, self.width, self.height)

    def hit(self):
        return HITCHAIN_HIT

    def tool(self, position, dx, dy, event=0):
        """
        Change the skew of the selected elements.
        """
        elements = self.scene.context.elements
        if event == 1:  # end
            self.last_skew = 0

            self.master.rotated_angle = self.last_skew
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass

        elif event == 0:  # move

            if self.is_x:
                dd = dx
                this_side = self.master.total_delta_x
                other_side = self.master.height
            else:
                dd = dy
                this_side = self.master.total_delta_y
                other_side = self.master.width

            skew_tan = this_side / other_side
            current_angle = math.atan(skew_tan)
            delta_angle = current_angle - self.master.rotated_angle
            self.master.rotated_angle = current_angle

            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                if self.is_x:
                    obj.transform.post_skew_x(
                        delta_angle,
                        (self.master.right + self.master.left) / 2,
                        (self.master.top + self.master.bottom) / 2,
                    )
                else:
                    obj.transform.post_skew_y(
                        delta_angle,
                        (self.master.right + self.master.left) / 2,
                        (self.master.top + self.master.bottom) / 2,
                    )
                try:
                    obj.node._bounds_dirty = True
                except AttributeError:
                    pass

            # elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "skew"
        s_help = "Skew element in %s-direction" % ("X" if self.is_x else "Y")
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            helptext=s_help,
        )
        if event_type == "leftdown":
            self.master.show_border = False
        elif event_type in ("leftclick", "leftup"):
            self.master.show_border = True

        return response


class MoveWidget(Widget):
    """
    Move Widget it tasked with drawing the skew box and managing the events
    dealing with moving the selected object
    """

    def __init__(self, master, scene, size, drawsize):
        self.master = master
        self.scene = scene
        self.half = size / 2
        self.drawhalf = drawsize / 2
        self.key_shift_pressed = self.master.key_shift_pressed
        self.key_control_pressed = self.master.key_control_pressed
        self.key_alt_pressed = self.master.key_alt_pressed
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "sizing"
        self.update()

    def update(self):
        pos_x = (self.master.right + self.master.left) / 2
        pos_y = (self.master.bottom + self.master.top) / 2
        self.set_position(pos_x - self.half, pos_y - self.half)

    def create_duplicate(self):
        from copy import copy

        self.duplicated_elements = True
        # Iterate through list of selected elements, duplicate them

        context = self.scene.context
        elements = context.elements
        adding_elements = [copy(e) for e in list(elements.elems(emphasized=True))]
        elements.add_elems(adding_elements)
        elements.classify(adding_elements)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        brush = wx.Brush(LINE_COLOR, wx.SOLID)
        gc.SetBrush(brush)
        gc.DrawRectangle(
            self.left + self.half - self.drawhalf,
            self.top + self.half - self.drawhalf,
            2 * self.drawhalf,
            2 * self.drawhalf,
        )

    def hit(self):
        return HITCHAIN_HIT

    def check_for_magnets(self):
        # print ("Shift-key-Status: self=%g, master=%g" % (self.key_shift_pressed, self.master.key_shift_pressed))
        if (
            not self.master.key_shift_pressed
        ):  # if Shift-Key pressed then ignore Magnets...
            elements = self.scene.context.elements
            b = elements._emphasized_bounds
            dx, dy = self.scene.revised_magnet_bound(b)
            if dx != 0 or dy != 0:
                for e in elements.flat(types=("elem",), emphasized=True):
                    obj = e.object
                    obj.transform.post_translate(dx, dy)

                self.translate(dx, dy)

                elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])

    def tool(self, position, dx, dy, event=0):
        """
        Change the position of the selected elements.
        """
        elements = self.scene.context.elements
        if event == 1:  # end
            self.check_for_magnets()
            for e in elements.flat(types=("elem", "group", "file"), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        elif event == -1:  # start
            if self.key_alt_pressed:
                self.create_duplicate()
        elif event == 0:  # move

            # b = elements.selected_area()  # correct, but slow...
            b = elements._emphasized_bounds
            for e in elements.flat(types=("elem",), emphasized=True):
                # Here we ignore the lock-status of an element
                obj = e.object
                obj.transform.post_translate(dx, dy)

            self.translate(dx, dy)

            elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])

        self.scene.request_refresh()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "move"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            helptext="Move element",
        )
        return response


class MoveRotationOriginWidget(Widget):
    """
    Move Rotation Origin Widget it tasked with drawing the rotation center indicator and managing the events
    dealing with moving the rotation center for the selected object
    """

    def __init__(self, master, scene, size):
        self.master = master
        self.scene = scene
        self.half = size / 2
        self.key_shift_pressed = master.key_shift_pressed
        self.key_control_pressed = master.key_control_pressed
        self.key_alt_pressed = master.key_alt_pressed
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        self.at_center = True
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "rotmove"
        self.update()

    def update(self):
        try:
            # if 0 < abs(self.master.rotation_cx - (self.master.left + self.master.right)/2) <= 0.0001:
            #    print ("Difference for x too small")
            #    self.master.rotation_cx = (self.master.left + self.master.right)/2
            # if 0 < abs(self.master.rotation_cy - (self.master.top + self.master.bottom)/2) <= 0.0001:
            #    print ("Difference for y too small")
            #    self.master.rotation_cy = (self.master.top + self.master.bottom)/2
            pos_x = self.master.rotation_cx
            pos_y = self.master.rotation_cy
            self.set_position(pos_x - self.half, pos_y - self.half)
        except TypeError:
            # print ("There was nothing established as rotation center")
            pass

    def process_draw(self, gc):
        # This one gets painted always.

        self.update()  # make sure coords are valid
        pen = wx.Pen()
        # pen.SetColour(wx.RED)
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(0.75 * self.master.line_width)
        except TypeError:
            pen.SetWidth(int(0.75 * self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.StrokeLine(
            self.left,
            self.top + self.height / 2.0,
            self.right,
            self.bottom - self.height / 2.0,
        )
        gc.StrokeLine(
            self.left + self.width / 2.0,
            self.top,
            self.right - self.width / 2.0,
            self.bottom,
        )
        gc.DrawEllipse(self.left, self.top, self.width, self.height)

    def tool(self, position, dx, dy, event=0):
        """
        Change the rotation-center of the selected elements.
        """
        self.master.rotation_cx += dx
        self.master.rotation_cy += dy
        self.master.invalidate_rot_center()
        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "rotcenter"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            helptext="Move rotation center",
        )
        return response


class ReferenceWidget(Widget):
    """
    Lock Widget it tasked with drawing the skew box and managing the events
    dealing with moving the selected object
    """

    def __init__(self, master, scene, size, is_reference_object):
        self.master = master
        self.scene = scene
        self.half = size / 2
        if is_reference_object:
            self.half = self.half * 1.5
        self.key_shift_pressed = master.key_shift_pressed
        self.key_control_pressed = master.key_control_pressed
        self.key_alt_pressed = master.key_alt_pressed
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.is_reference_object = is_reference_object
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "reference"
        self.update()

    def update(self):
        pos_x = self.master.left
        pos_y = self.master.top + 1 / 4 * (self.master.bottom - self.master.top)
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:
            # We don't need that overhead
            return
        self.update()  # make sure coords are valid
        pen = wx.Pen()
        if self.is_reference_object:
            bgcol = wx.YELLOW
            fgcol = wx.RED
        else:
            bgcol = LINE_COLOR
            fgcol = wx.BLACK
        pen.SetColour(bgcol)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        brush = wx.Brush(bgcol, wx.SOLID)
        gc.SetBrush(brush)
        gc.DrawEllipse(self.left, self.top, self.width, self.height)
        # gc.DrawRectangle(self.left, self.top, self.width, self.height)
        try:
            font = wx.Font(0.75 * self.master.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
        except TypeError:
            font = wx.Font(
                int(0.75 * self.master.font_size), wx.SWISS, wx.NORMAL, wx.BOLD
            )
        gc.SetFont(font, fgcol)
        symbol = "r"
        (t_width, t_height) = gc.GetTextExtent(symbol)
        gc.DrawText(
            symbol,
            (self.left + self.right) / 2 - t_width / 2,
            (self.top + self.bottom) / 2 - t_height / 2,
        )

    def hit(self):
        return HITCHAIN_HIT

    def tool(
        self, position=None, dx=None, dy=None, event=0
    ):  # Don't need all arguments, just for compatibility with pattern
        """
        Toggle the Reference Status of the selected elements
        """
        elements = self.scene.context.elements
        if event == -1:  # leftdown
            # Nothing to do...
            pass
        elif event == 1:  # leftup, leftclick
            if self.is_reference_object:
                self.scene.reference_object = None
            else:
                for e in elements.flat(types=("elem",), emphasized=True):
                    try:
                        # First object
                        obj = e.object
                        self.scene.reference_object = obj
                        break
                    except AttributeError:
                        pass

        self.scene.request_refresh()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "reference"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            helptext="Toggle reference status of element",
            optimize_drawing=False,
        )
        return response


class RefAlign(wx.Dialog):
    """
    RefAlign provides a dialog how to aligbn the selection in respect to the reference object
    """

    def __init__(self, context, *args, **kwds):
        self.cancelled = False
        self.option_pos = ""
        self.option_scale = ""
        self.context = context
        _ = context._
        # begin wxGlade: RefAlign.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetTitle("Align Selection")

        sizer_ref_align = wx.BoxSizer(wx.VERTICAL)

        label_1 = wx.StaticText(
            self,
            wx.ID_ANY,
            _("Move the selection into the reference object and scale the elements."),
        )
        sizer_ref_align.Add(label_1, 0, wx.EXPAND, 0)

        sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ref_align.Add(sizer_options, 0, wx.EXPAND, 0)

        sizer_pos = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Position")), wx.HORIZONTAL
        )
        sizer_options.Add(sizer_pos, 1, wx.EXPAND, 0)

        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_pos.Add(sizer_6, 1, wx.EXPAND, 0)

        self.radio_btn_1 = wx.RadioButton(self, wx.ID_ANY, "TL", style=wx.RB_GROUP)
        self.radio_btn_1.SetToolTip(
            _("Align the selection to the top left corner of the reference object")
        )
        sizer_6.Add(self.radio_btn_1, 0, 0, 0)

        self.radio_btn_4 = wx.RadioButton(self, wx.ID_ANY, "L")
        self.radio_btn_4.SetToolTip(
            _("Align the selection to the left side of the reference object")
        )
        sizer_6.Add(self.radio_btn_4, 0, 0, 0)

        self.radio_btn_7 = wx.RadioButton(self, wx.ID_ANY, "BL")
        self.radio_btn_7.SetToolTip(
            _("Align the selection to the bottom left corner of the reference object")
        )
        sizer_6.Add(self.radio_btn_7, 0, 0, 0)

        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_pos.Add(sizer_7, 1, wx.EXPAND, 0)

        self.radio_btn_2 = wx.RadioButton(self, wx.ID_ANY, "T")
        self.radio_btn_2.SetToolTip(
            _("Align the selection to the upper side of the reference object")
        )
        sizer_7.Add(self.radio_btn_2, 0, 0, 0)

        self.radio_btn_5 = wx.RadioButton(self, wx.ID_ANY, "C")
        sizer_7.Add(self.radio_btn_5, 0, 0, 0)

        self.radio_btn_8 = wx.RadioButton(self, wx.ID_ANY, "B")
        self.radio_btn_8.SetToolTip(
            _("Align the selection to the lower side of the reference object")
        )
        sizer_7.Add(self.radio_btn_8, 0, 0, 0)

        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_pos.Add(sizer_8, 1, wx.EXPAND, 0)

        self.radio_btn_3 = wx.RadioButton(self, wx.ID_ANY, "TR")
        self.radio_btn_3.SetToolTip(
            _("Align the selection to the top right corner of the reference object")
        )
        sizer_8.Add(self.radio_btn_3, 0, 0, 0)

        self.radio_btn_6 = wx.RadioButton(self, wx.ID_ANY, "R")
        sizer_8.Add(self.radio_btn_6, 0, 0, 0)

        self.radio_btn_9 = wx.RadioButton(self, wx.ID_ANY, "BR")
        self.radio_btn_9.SetToolTip(
            _("Align the selection to the bottom right corner of the reference object")
        )
        sizer_8.Add(self.radio_btn_9, 0, 0, 0)

        sizer_scale = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Scaling"), wx.VERTICAL
        )
        sizer_options.Add(sizer_scale, 1, wx.EXPAND, 0)

        self.radio_btn_10 = wx.RadioButton(
            self, wx.ID_ANY, "Unchanged", style=wx.RB_GROUP
        )
        self.radio_btn_10.SetToolTip(_("Don't change the size of the object(s)"))
        sizer_scale.Add(self.radio_btn_10, 0, 0, 0)

        self.radio_btn_11 = wx.RadioButton(self, wx.ID_ANY, "Fit")
        self.radio_btn_11.SetToolTip(
            _("Scale the object(s) while maintaining the aspect ratio")
        )
        sizer_scale.Add(self.radio_btn_11, 0, 0, 0)

        self.radio_btn_12 = wx.RadioButton(self, wx.ID_ANY, "Squeeze")
        self.radio_btn_11.SetToolTip(
            _("Scale the object(s) to make them fit the target")
        )
        sizer_scale.Add(self.radio_btn_12, 0, 0, 0)

        sizer_buttons = wx.StdDialogButtonSizer()
        sizer_ref_align.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.button_OK = wx.Button(self, wx.ID_OK, "")
        self.button_OK.SetToolTip(_("Align and scale the elements"))
        self.button_OK.SetDefault()
        sizer_buttons.AddButton(self.button_OK)

        self.button_CANCEL = wx.Button(self, wx.ID_CANCEL, "")
        self.button_CANCEL.SetToolTip(_("Close without applying any changes"))
        sizer_buttons.AddButton(self.button_CANCEL)

        sizer_buttons.Realize()

        self.SetSizer(sizer_ref_align)
        sizer_ref_align.Fit(self)

        self.SetAffirmativeId(self.button_OK.GetId())
        self.SetEscapeId(self.button_CANCEL.GetId())

        self.Layout()

        self.radio_btn_10.SetValue(1)  # Unchanged
        self.radio_btn_5.SetValue(1)  # center

    def results(self):
        self.cancelled = False
        if self.radio_btn_10.GetValue():
            self.option_scale = "none"
        elif self.radio_btn_11.GetValue():
            self.option_scale = "fit"
        if self.radio_btn_12.GetValue():
            self.option_scale = "squeeze"
        for radio in (
            self.radio_btn_1,
            self.radio_btn_2,
            self.radio_btn_3,
            self.radio_btn_4,
            self.radio_btn_5,
            self.radio_btn_6,
            self.radio_btn_7,
            self.radio_btn_8,
            self.radio_btn_9,
        ):
            if radio.GetValue():
                s = radio.GetLabel()
                self.option_pos = s.lower()
                break
        return self.option_pos, self.option_scale


class SelectionWidget(Widget):
    """
    Selection Widget it tasked with drawing the selection box and managing the events
    dealing with moving, resizing and altering the selected object.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(LINE_COLOR)
        self.selection_pen.SetStyle(wx.PENSTYLE_DOT)
        self.popupID1 = None
        self.popupID2 = None
        self.popupID3 = None
        self.gc = None
        self.reset_variables()

    def init(self, context):
        context.listen("ext-modified", self.external_modification)

    def final(self, context):
        context.unlisten("ext-modified", self.external_modification)

    def reset_variables(self):
        self.save_width = None
        self.save_height = None
        self.cursor = "arrow"
        self.uniform = True
        self.rotation_cx = None
        self.rotation_cy = None
        self.rotated_angle = 0
        self.total_delta_x = 0
        self.total_delta_y = 0
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
        self.was_lb_raised = False
        self.hovering = False
        self.use_handle_rotate = True
        self.use_handle_skew = True
        self.use_handle_size = True
        self.use_handle_move = True
        self.keep_rotation = None
        self.line_width = 0
        self.font_size = 0
        self.tool_running = False
        self.active_tool = "none"
        self.single_element = True
        self.is_ref = False
        self.show_border = True
        self.last_angle = None
        self.start_angle = None

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
            if self.rotation_cx is None:
                # print ("Update rot-center")
                self.rotation_cx = (self.left + self.right) / 2
                self.rotation_cy = (self.top + self.bottom) / 2

            # print ("Hit and delegate")
            return HITCHAIN_HIT_AND_DELEGATE
        else:
            self.reset_variables()
            return HITCHAIN_DELEGATE

    def move_selection_to_ref(self, pos="c"):
        refob = self.scene.reference_object
        elements = self.scene.context.elements
        if refob is None:
            return
        bb = refob.bbox()

        cc = elements.selected_area()

        if bb is None or cc is None:
            return
        if "l" in pos:
            tx = bb[0]
        elif "r" in pos:
            tx = bb[2] - (cc[2] - cc[0])
        else:
            tx = (bb[0] + bb[2]) / 2 - (cc[2] - cc[0]) / 2

        if "t" in pos:
            ty = bb[1]
        elif "b" in pos:
            ty = bb[3] - (cc[3] - cc[1])
        else:
            ty = (bb[1] + bb[3]) / 2 - (cc[3] - cc[1]) / 2

        dx = tx - cc[0]
        dy = ty - cc[1]
        # print ("Moving from (%.1f, %.1f) to (%.1f, %.1f) translate by (%.1f, %.1f)" % (cc[0], cc[1], tx, ty, dx, dy ))

        for e in elements.flat(types=("elem",), emphasized=True):
            # Here we ignore the lock-status of an element, as this is just a move...
            obj = e.object
            if not obj is refob:
                obj.transform.post_translate(dx, dy)
                try:
                    obj.node._bounds_dirty = True
                except AttributeError:
                    pass
        elements.update_bounds([cc[0] + dx, cc[1] + dy, cc[2] + dx, cc[3] + dy])

    def scale_selection_to_ref(self, method="none"):
        refob = self.scene.reference_object
        if refob is None:
            return
        bb = refob.bbox()
        elements = self.scene.context.elements
        cc = elements.selected_area()

        if bb is None or cc is None:
            return
        try:
            b_ratio = (bb[2] - bb[0]) / (bb[3] - bb[1])
            c_ratio = (cc[2] - cc[0]) / (cc[3] - cc[1])
        except ZeroDivisionError:
            return
        if method == "fit":
            scalex = (bb[2] - bb[0]) / (cc[2] - cc[0])
            scaley = (bb[3] - bb[1]) / (cc[3] - cc[1])
            scalex = min(scalex, scaley)
            scaley = scalex
        elif method == "squeeze":
            scalex = (bb[2] - bb[0]) / (cc[2] - cc[0])
            scaley = (bb[3] - bb[1]) / (cc[3] - cc[1])
        else:
            return
        dx = (scalex - 1) * (cc[2] - cc[0])
        dy = (scaley - 1) * (cc[3] - cc[1])

        for e in elements.flat(types=("elem",), emphasized=True):
            # Here we acknowledge the lock-status of an element
            obj = e.object
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            if not obj is refob:
                obj.transform.post_scale(scalex, scaley, cc[0], cc[1])
                try:
                    obj.node._bounds_dirty = True
                except AttributeError:
                    pass
        elements.update_bounds([cc[0], cc[1], cc[2] + dx, cc[3] + dy])

    def show_reference_align_dialog(self, event):
        opt_pos = None
        opt_scale = None
        dlgRefAlign = RefAlign(self.scene.context, None, wx.ID_ANY, "")
        # SetTopWindow(self.dlgRefAlign)
        if dlgRefAlign.ShowModal() == wx.ID_OK:
            opt_pos, opt_scale = dlgRefAlign.results()
            # print ("I would need to align to: %s and scale to: %s" % (opt_pos, opt_scale))
        dlgRefAlign.Destroy()
        if not opt_pos is None:
            elements = self.scene.context.elements
            self.scale_selection_to_ref(opt_scale)
            self.move_selection_to_ref(opt_pos)
            self.scene.request_refresh()

    def become_reference(self, event):
        for e in self.scene.context.elements.flat(types=("elem",), emphasized=True):
            try:
                # First object
                obj = e.object
                self.scene.reference_object = obj
                break
            except AttributeError:
                pass
        # print("set...")
        self.scene.request_refresh()

    def delete_reference(self, event):
        self.scene.reference_object = None
        # Simplify, no complete scene refresh required
        # print("unset...")
        self.scene.request_refresh()

    def create_menu(self, gui, node, elements):
        if node is None:
            return
        if hasattr(node, "node"):
            node = node.node
        menu = create_menu_for_node(gui, node, elements)
        # Now check whether we have a reference object
        obj = self.scene.reference_object
        if not obj is None:
            # Okay, just lets make sure we are not doing this on the refobject itself...
            for e in self.scene.context.elements.flat(types=("elem",), emphasized=True):
                # Here we acknowledge the lock-status of an element
                if obj == e.object:
                    obj = None
                    break

        _ = self.scene.context._
        submenu = None
        # Add Manipulation menu
        if not obj is None:
            submenu = wx.Menu()
            if self.popupID1 is None:
                self.popupID1 = wx.NewId()
            gui.Bind(wx.EVT_MENU, self.show_reference_align_dialog, id=self.popupID1)
            submenu.Append(self.popupID1, _("Align to reference object"))

        if self.single_element and not self.is_ref:
            if submenu is None:
                submenu = wx.Menu()
            if self.popupID3 is None:
                self.popupID3 = wx.NewId()
            gui.Bind(wx.EVT_MENU, self.become_reference, id=self.popupID3)
            submenu.Append(self.popupID3, _("Become reference object"))
        if not self.scene.reference_object is None:
            if submenu is None:
                submenu = wx.Menu()
            if self.popupID2 is None:
                self.popupID2 = wx.NewId()
            gui.Bind(wx.EVT_MENU, self.delete_reference, id=self.popupID2)
            submenu.Append(self.popupID2, _("Clear reference object"))

        if not submenu is None:
            menu.AppendSubMenu(submenu, _("Reference Object"))

        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        elements = self.scene.context.elements
        # mirror key-events to provide them to the widgets as they get deleted and created after every event...
        if event_type == "kb_shift_release":
            if self.key_shift_pressed:
                self.key_shift_pressed = False
            return RESPONSE_CHAIN
        elif event_type == "kb_shift_press":
            if not self.key_shift_pressed:
                self.key_shift_pressed = True
            return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_release":
            if self.key_control_pressed:
                self.key_control_pressed = False
            return RESPONSE_CHAIN
        elif event_type == "kb_ctrl_press":
            if not self.key_control_pressed:
                self.key_control_pressed = True
            return RESPONSE_CHAIN
        elif event_type == "kb_alt_release":
            if self.key_alt_pressed:
                self.key_alt_pressed = False
            return RESPONSE_CHAIN
        elif event_type == "kb_alt_press":
            if not self.key_alt_pressed:
                self.key_alt_pressed = True
            return RESPONSE_CHAIN

        # Now all hovering, there is some empty space in the selection widget that get these events
        # print("** MASTER, event=%s, pos=%s" % (event_type, space_pos))

        if event_type == "hover_start":
            self.hovering = True
            self.scene.context.signal("statusmsg", "")
            self.tool_running = False
        elif event_type == "hover_end" or event_type == "lost":
            self.scene.cursor(self.cursor)
            self.hovering = False
            self.scene.context.signal("statusmsg", "")
        elif event_type == "hover":
            if self.hovering:
                self.scene.cursor(self.cursor)
            # self.tool_running = False
            self.scene.context.signal("statusmsg", "")
        elif event_type == "rightdown":
            elements.set_emphasized_by_position(space_pos)
            # Check if reference is still existing
            self.scene.validate_reference()
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            self.create_menu(
                self.scene.context.gui, elements.top_element(emphasized=True), elements
            )
            return RESPONSE_CONSUME
        elif event_type == "doubleclick":
            elements.set_emphasized_by_position(space_pos)
            elements.signal("activate_selected_nodes", 0)
            return RESPONSE_CONSUME

        return RESPONSE_CHAIN

    def invalidate_rot_center(self):
        self.keep_rotation = None

    def check_rot_center(self):
        if self.keep_rotation is None:
            if self.rotation_cx is None:
                # print ("Update rot-center")
                self.rotation_cx = (self.left + self.right) / 2
                self.rotation_cy = (self.top + self.bottom) / 2
            cx = (self.left + self.right) / 2
            cy = (self.top + self.bottom) / 2
            value = (
                abs(self.rotation_cx - cx) < 0.0001
                and abs(self.rotation_cy - cy) < 0.0001
            )
            self.keep_rotation = value
            # if value:
            #    print ("RotHandle still in center")
            # else:
            #    print ("RotHandle (%.1f, %.1f) outside center (%.1f, %.1f)" % (self.rotation_cx, self.rotation_cy, cx, cy))

    def external_modification(self, origin, *args):
        # Reset rotation center...
        self.keep_rotation = True
        self.rotation_cx = None
        self.rotation_cy = None

    def process_draw(self, gc):
        """
        Draw routine for drawing the selection box.
        """
        self.gc = gc
        if self.scene.context.draw_mode & DRAW_MODE_SELECTION != 0:
            return
        self.clear()  # Clearing children as we are generating them in a bit...
        context = self.scene.context
        try:
            self.use_handle_rotate = context.enable_sel_rotate
            self.use_handle_skew = context.enable_sel_skew
            self.use_handle_size = context.enable_sel_size
            self.use_handle_move = context.enable_sel_move
        except AttributeError:
            # Stuff has not yet been defined...
            self.use_handle_rotate = True
            self.use_handle_skew = True
            self.use_handle_size = True
            self.use_handle_move = True

        draw_mode = context.draw_mode
        elements = self.scene.context.elements
        bounds = elements.selected_area()
        matrix = self.parent.matrix
        if bounds is not None:
            try:
                self.line_width = 2.0 / matrix.value_scale_x()
                self.font_size = 14.0 / matrix.value_scale_x()
            except ZeroDivisionError:
                matrix.reset()
                return
            try:
                self.selection_pen.SetWidth(self.line_width)
            except TypeError:
                self.selection_pen.SetWidth(int(self.line_width))
            if self.font_size < 1.0:
                self.font_size = 1.0  # Mac does not allow values lower than 1.
            try:
                font = wx.Font(self.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            except TypeError:
                font = wx.Font(int(self.font_size), wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(font, TEXT_COLOR)
            gc.SetPen(self.selection_pen)
            self.left = bounds[0]
            self.top = bounds[1]
            self.right = bounds[2]
            self.bottom = bounds[3]
            self.check_rot_center()
            if self.keep_rotation:  # Reset it to center....
                cx = (self.left + self.right) / 2
                cy = (self.top + self.bottom) / 2
                # self.keep_rotation = False
                self.rotation_cx = cx
                self.rotation_cy = cy

            # Code for reference object - single object? And identical to reference?
            self.is_ref = False
            self.single_element = True
            if not self.scene.reference_object is None:

                for idx, e in enumerate(
                    elements.flat(types=("elem",), emphasized=True)
                ):
                    obj = e.object
                    if obj is self.scene.reference_object:
                        self.is_ref = True
                    if idx > 0:
                        self.single_element = False
                        break

            if not self.single_element:
                self.is_ref = False

            # Add all subwidgets in Inverse Order
            msize = 5 * self.line_width
            rotsize = 3 * msize

            self.add_widget(-1, BorderWidget(master=self, scene=self.scene))
            if self.single_element and self.use_handle_skew:
                self.add_widget(
                    -1,
                    ReferenceWidget(
                        master=self,
                        scene=self.scene,
                        size=msize,
                        is_reference_object=self.is_ref,
                    ),
                )
            if self.use_handle_move:
                self.add_widget(
                    -1,
                    MoveWidget(
                        master=self, scene=self.scene, size=rotsize, drawsize=msize
                    ),
                )
            if self.use_handle_skew:
                self.add_widget(
                    -1,
                    SkewWidget(
                        master=self, scene=self.scene, is_x=False, size=2 / 3 * msize
                    ),
                )
                self.add_widget(
                    -1,
                    SkewWidget(
                        master=self, scene=self.scene, is_x=True, size=2 / 3 * msize
                    ),
                )
            if self.use_handle_rotate:
                for i in range(4):
                    self.add_widget(
                        -1,
                        RotationWidget(
                            master=self,
                            scene=self.scene,
                            index=i,
                            size=rotsize,
                            inner=msize,
                        ),
                    )
                self.add_widget(
                    -1,
                    MoveRotationOriginWidget(master=self, scene=self.scene, size=msize),
                )
            if self.use_handle_size:
                for i in range(4):
                    self.add_widget(
                        -1,
                        CornerWidget(
                            master=self, scene=self.scene, index=i, size=msize
                        ),
                    )
                for i in range(4):
                    self.add_widget(
                        -1,
                        SideWidget(master=self, scene=self.scene, index=i, size=msize),
                    )
