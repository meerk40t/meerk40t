import math

import wx

from meerk40t.core.element_types import *
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
from meerk40t.gui.wxutils import StaticBoxSizer, create_menu_for_node
from meerk40t.svgelements import Point

NEARLY_ZERO = 1.0e-6


def process_event(
    widget,
    widget_identifier=None,
    window_pos=None,
    space_pos=None,
    event_type=None,
    nearest_snap=None,
    modifiers=None,
    helptext="",
    optimize_drawing=True,
):

    if widget_identifier is None:
        widget_identifier = "none"
    try:
        inside = widget.contains(space_pos[0], space_pos[1])
    except TypeError:
        # Widget already destroyed ?!
        return RESPONSE_CHAIN
    # if event_type in ("move", "leftdown", "leftup"):
    #     print(f"Event for {widget_identifier}: {event_type}, {nearest_snap}")

    # Not during an edit !
    if widget.scene.pane.active_tool.startswith("edit"):
        return RESPONSE_CHAIN

    # Now all Mouse-Hover-Events
    _ = widget.scene.context._
    if event_type == "hover" and widget.hovering and not inside:
        widget.hovering = False
        widget.scene.cursor("arrow")
        widget.scene.context.signal("statusmsg", "")
        return RESPONSE_CHAIN

    if event_type == "hover_start":
        if inside:
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
    # print (f"Event={event_type}, tool={widget.scene.tool_active}, modif={widget.scene.pane.modif_active}, snap={nearest_snap}")
    if widget.scene.pane.tool_active:
        # print ("ignore")
        return RESPONSE_CHAIN

    if event_type == "leftdown":
        # We want to establish that we don't have a singular Shift key or a singular ctrl-key
        # as these will extend / reduce the selection
        if widget_identifier == "move" or (
            not (len(modifiers) == 1 and ("shift" in modifiers or "ctrl" in modifiers))
        ):
            cx = (widget.left + widget.right) / 2
            cy = (widget.top + widget.bottom) / 2
            # print(f"Start: x={space_pos[0]}, y={space_pos[1]}, dx={space_pos[4]}, dy={space_pos[5]}")
            # print(f"Widget: cx={cx}, cy={cy}")
            # Set them to the center of the widget
            widget.master.offset_x = cx - space_pos[0]
            widget.master.offset_y = cy - space_pos[1]
            widget.was_lb_raised = True
            widget.save_width = widget.master.width
            widget.save_height = widget.master.height
            widget.uniform = not widget.master.key_alt_pressed
            widget.master.total_delta_y = dy
            widget.master.total_delta_x = dx
            widget.master.total_delta_y = dy
            widget.master.tool_running = optimize_drawing
            widget.master.invalidate_rot_center()
            widget.master.check_rot_center()
            widget.tool(space_pos, nearest_snap, dx, dy, -1, modifiers)
            return RESPONSE_CONSUME
    elif event_type == "middledown":
        # Hmm, I think this is never called due to the consumption of this event by scene pane...
        widget.was_lb_raised = False
        widget.save_width = widget.master.width
        widget.save_height = widget.master.height
        widget.uniform = False
        widget.master.total_delta_x = dx
        widget.master.total_delta_y = dy
        widget.master.tool_running = optimize_drawing
        widget.tool(space_pos, nearest_snap, dx, dy, -1, modifiers)
        return RESPONSE_CONSUME
    elif event_type == "leftup":
        if widget.was_lb_raised:
            widget.tool(space_pos, nearest_snap, dx, dy, 1, modifiers)
            widget.scene.context.elements.ensure_positive_bounds()
            widget.was_lb_raised = False
            widget.master.show_border = True
            widget.master.tool_running = False
            return RESPONSE_CONSUME
    elif event_type in ("middleup", "lost"):
        if widget.was_lb_raised:
            widget.tool(space_pos, nearest_snap, dx, dy, 1, modifiers)
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
            widget.tool(space_pos, nearest_snap, dx, dy, 0, modifiers)
            return RESPONSE_CONSUME
    elif event_type == "leftclick":
        if widget.was_lb_raised:
            widget.tool(space_pos, nearest_snap, dx, dy, 1, modifiers)
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

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        **kwargs,
    ):
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
        # Won't be display when rotating...
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
                font = wx.Font(
                    self.master.font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            except TypeError:
                font = wx.Font(
                    int(self.master.font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            gc.SetFont(font, self.scene.colors.color_manipulation)
            # Show Y-Value
            s_txt = str(Length(amount=self.top, digits=2, preferred_units=units))
            (t_width, t_height) = gc.GetTextExtent(s_txt)
            distance = 0.25 * t_height
            pos = self.top / 2.0 - t_height / 2
            if pos + t_height + distance >= self.top:
                pos = self.top - t_height - distance
            gc.DrawText(s_txt, center_x - t_width / 2, pos)

            # Display X-Coordinate
            s_txt = str(Length(amount=self.left, digits=2, preferred_units=units))
            (t_width, t_height) = gc.GetTextExtent(s_txt)
            pos = self.left / 2.0 - t_width / 2
            if pos + t_width + distance >= self.left:
                pos = self.left - t_width - distance
            gc.DrawText(s_txt, pos, center_y)
            # Display height
            s_txt = str(
                Length(amount=(self.bottom - self.top), digits=2, preferred_units=units)
            )
            (t_width, t_height) = gc.GetTextExtent(s_txt)
            gc.DrawText(
                s_txt,
                self.right + 0.5 * t_height,
                center_y + 0.5 * t_width,
                math.tau / 4,
            )

            # Display width
            s_txt = str(
                Length(amount=(self.right - self.left), digits=2, preferred_units=units)
            )
            (t_width, t_height) = gc.GetTextExtent(s_txt)
            gc.DrawText(s_txt, center_x - 0.5 * t_width, self.bottom + 0.5 * t_height)
        # But show the angle
        if abs(self.master.rotated_angle) > 0.001:
            try:
                font = wx.Font(
                    0.75 * self.master.font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            except TypeError:
                font = wx.Font(
                    int(0.75 * self.master.font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            gc.SetFont(font, self.scene.colors.color_manipulation)
            symbol = f"{360 * self.master.rotated_angle / math.tau:.0f}°"
            pen = wx.Pen()
            pen.SetColour(self.scene.colors.color_manipulation)
            pen.SetStyle(wx.PENSTYLE_SOLID)
            gc.SetPen(pen)
            brush = wx.Brush(wx.WHITE, wx.BRUSHSTYLE_SOLID)
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
        mid_x = (self.master.right + self.master.left) / 2
        mid_y = (self.master.bottom + self.master.top) / 2
        # Selection very small ? Relocate Handle
        inner_wd_half = (self.master.right - self.master.left) / 2
        inner_ht_half = (self.master.bottom - self.master.top) / 2
        dx = abs(min(0, inner_wd_half - self.inner))
        dy = abs(min(0, inner_ht_half - self.inner))
        if self.master.handle_outside:
            offset_x = self.inner / 2
            offset_y = self.inner / 2
        else:
            offset_x = 0
            offset_y = 0

        if self.index == 0:
            pos_x = self.master.left - dx - offset_x
            pos_y = self.master.top - dy - offset_y
        elif self.index == 1:
            pos_x = self.master.right + dx + offset_x
            pos_y = self.master.top - dy - offset_y
        elif self.index == 2:
            pos_x = self.master.right + dx + offset_x
            pos_y = self.master.bottom + dy + offset_y
        else:
            pos_x = self.master.left - dx - offset_x
            pos_y = self.master.bottom + dy + offset_y
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return
        self.update()  # make sure coords are valid

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

        # Well, I would have liked to draw a proper arc via dc.DrawArc but the DeviceContext is not available here(?)
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

        # End-arrow at 90deg, cos = 0, sin = 1
        # End-Arrow
        x = cx + signx * 0 * self.half
        y = cy + signy * 1 * self.half
        segment += [
            (x + signx * 1 / 2 * self.inner, y + 2 / 3 * signy * 1 / 2 * self.inner)
        ]
        segment += [(x, y)]
        segment += [(x + signx * 1 / 2 * self.inner, y - signy * 1 / 2 * self.inner)]
        gc.SetPen(self.master.handle_pen)
        gc.StrokeLines(segment)

    def tool(self, position, nearest_snap, dx, dy, event=0, modifiers=None):
        """
        Change the rotation of the selected elements.
        """
        # Nearest snap makes not a lot of sense imho, so no dealing with it...
        nearest_snap = None
        if nearest_snap is not None:
            # Position is space_pos:
            # 0, 1: current x, y
            # 2, 3: last pos x, y
            # 4, 5: current - last
            position = list(position)
            position[0] = nearest_snap[0]
            position[1] = nearest_snap[1]
            position[4] = position[0] - position[2]
            position[5] = position[1] - position[3]
            dx = position[4]
            dy = position[5]

        rot_angle = 0
        elements = self.scene.context.elements
        if event == 1:
            images = []
            for e in elements.flat(types=elem_group_nodes, emphasized=True):
                e.modified()
                if hasattr(e, "update"):
                    images.append(e)
            for e in images:
                e.update(None)
            self.master.last_angle = None
            self.master.start_angle = None
            self.master.rotated_angle = 0
            self.scene.context.signal("tool_modified")
        elif event == -1:
            self.scene.pane.modif_active = True
            # Normally this would happen automagically in the background, but as we are going
            # to suppress undo during the execution of this tool (to allow to go back to the
            # very starting point) we need to set the recovery point ourselves.
            elements.prepare_undo()
            return
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

            if self.master.last_angle is None:
                self.master.start_angle = current_angle
                self.master.last_angle = current_angle

            # Update Rotation angle...
            if self.master.key_shift_pressed:
                # Only steps of 5 deg
                desired_step = 5 * (math.tau / 360)
                old_angle = current_angle - self.master.start_angle
                new_angle = round(old_angle / desired_step) * desired_step
                current_angle += new_angle - old_angle
            elif self.master.key_control_pressed:
                # Only steps of 15 deg
                desired_step = 15 * (math.tau / 360)
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
            with elements.undofree():
                for e in elements.flat(types=elem_nodes, emphasized=True):
                    try:
                        if e.lock:
                            continue
                    except AttributeError:
                        pass
                    e.matrix.post_rotate(delta_angle, self.rotate_cx, self.rotate_cy)
            # elements.update_bounds([b[0], b[1], b[2], b[3]])

        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def _contains(self, x, y=None):
        # result: 0 = No Hit, 1 = outer, 2 = Inner
        value = 0
        if y is None:
            y = x.y
            x = x.x
        mid_x = (self.left + self.right) / 2
        mid_y = (self.top + self.bottom) / 2
        if self.index in (0, 3):  # left
            tx1 = self.left
            tx2 = mid_x + self.inner / 2
            bx1 = mid_x
            bx2 = self.right
        else:
            tx1 = mid_x - self.inner / 2
            tx2 = self.right
            bx1 = self.left
            bx2 = mid_x

        if self.index in (0, 1):  # top
            ty1 = self.top
            ty2 = mid_y + self.inner / 2
            by1 = mid_y
            by2 = self.bottom
        else:
            ty1 = mid_y - self.inner / 2
            ty2 = self.bottom
            by1 = self.top
            by2 = mid_y
        if tx1 <= x <= tx2 and ty1 <= y <= ty2:  # outer part
            value = 1
        elif bx1 <= x <= bx2 and by1 <= y <= by2:  # inner  part
            value = 2
        if (
            mid_x - self.inner / 2 <= x <= mid_x + self.inner / 2
            and mid_y - self.inner / 2 <= y <= mid_y + self.inner / 2
        ):
            # Corner-Handle
            value = 0

        return value

    def contains(self, x, y=None):
        # Slightly more complex than usual due to the inner exclusion...
        value = self._contains(x, y)
        return value != 0

    def inner_contains(self, x, y=None):
        # Slightly more complex than usual due to the inner exclusion...
        value = self._contains(x, y)
        return value == 2

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "rotation"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            nearest_snap=nearest_snap,
            modifiers=modifiers,
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
        mid_x = (self.master.right + self.master.left) / 2
        mid_y = (self.master.bottom + self.master.top) / 2
        # Selection very small ? Relocate Handle
        inner_wd_half = (self.master.right - self.master.left) / 2
        inner_ht_half = (self.master.bottom - self.master.top) / 2
        if self.master.handle_outside:
            offset_x = self.half
            offset_y = self.half
        else:
            offset_x = 0
            offset_y = 0
        dx = abs(min(0, inner_wd_half - 2 * self.half))
        dy = abs(min(0, inner_ht_half - 2 * self.half))

        if self.index == 0:
            pos_x = self.master.left - dx - offset_x
            pos_y = self.master.top - dy - offset_y
        elif self.index == 1:
            pos_x = self.master.right + dx + offset_x
            pos_y = self.master.top - dy - offset_y
        elif self.index == 2:
            pos_x = self.master.right + dx + offset_x
            pos_y = self.master.bottom + dy + offset_y
        else:
            pos_x = self.master.left - dx - offset_x
            pos_y = self.master.bottom + dy + offset_y
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        brush = wx.Brush(
            self.scene.colors.color_manipulation_handle, wx.BRUSHSTYLE_SOLID
        )
        gc.SetPen(self.master.handle_pen)
        gc.SetBrush(brush)
        gc.DrawRectangle(self.left, self.top, self.width, self.height)

    def tool(self, position, nearest_snap, dx, dy, event=0, modifiers=None):
        elements = self.scene.context.elements
        if nearest_snap is None:
            # print ("Took last snap instead...")
            nearest_snap = self.scene.pane.last_snap
        if nearest_snap is not None:
            # Position is space_pos:
            # 0, 1: current x, y
            # 2, 3: last pos x, y
            # 4, 5: current - last
            position = list(position)
            position[0] = nearest_snap[0]
            position[1] = nearest_snap[1]
            position[4] = position[0] - position[2]
            position[5] = position[1] - position[3]
            dx = position[4]
            dy = position[5]

        if event == 1:
            images = []
            for e in elements.flat(types=elem_group_nodes, emphasized=True):
                # modified no longer relevant
                # try:
                #     e.modified()
                # except AttributeError:
                #     pass
                if hasattr(e, "update"):
                    images.append(e)
            for e in images:
                e.update(None)
            self.scene.pane.modif_active = False
            self.scene.context.signal("tool_modified")
        elif event == -1:
            self.scene.pane.modif_active = True
            # Normally this would happen automagically in the background, but as we are going
            # to suppress undo during the execution of this tool (to allow to go back to the
            # very starting point) we need to set the recovery point ourselves.
            elements.prepare_undo()
            return
        elif event == 0:
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
                try:
                    scaley = (self.master.bottom - position[1]) / self.save_height
                except ZeroDivisionError:
                    scaley = 1
            elif "s" in self.method:
                try:
                    scaley = (position[1] - self.master.top) / self.save_height
                except ZeroDivisionError:
                    scaley = 1

            if "w" in self.method:
                try:
                    scalex = (self.master.right - position[0]) / self.save_width
                except ZeroDivisionError:
                    scalex = 1
            elif "e" in self.method:
                try:
                    scalex = (position[0] - self.master.left) / self.save_width
                except ZeroDivisionError:
                    scalex = 1
            free = bool("alt" in modifiers)
            if len(self.method) > 1 and self.uniform and not free:  # from corner
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale
            if abs(scalex) < NEARLY_ZERO or abs(scaley) <= NEARLY_ZERO:
                return

            b = elements._emphasized_bounds
            if "n" in self.method:
                orgy = self.master.bottom
            else:
                orgy = self.master.top

            if "w" in self.method:
                orgx = self.master.right
            else:
                orgx = self.master.left

            grow = 1
            # If the crtl+shift-Keys are pressed then size equally on both opposing sides at the same time
            if self.master.key_shift_pressed and self.master.key_control_pressed:
                orgy = (self.master.bottom + self.master.top) / 2
                orgx = (self.master.left + self.master.right) / 2
                grow = 0.5

            oldvalue = self.save_width
            self.save_width *= scalex
            deltax = self.save_width - oldvalue
            oldvalue = self.save_height
            self.save_height *= scaley
            deltay = self.save_height - oldvalue

            if "n" in self.method:
                b[1] -= grow * deltay
                b[3] += (1 - grow) * deltay
            elif "s" in self.method:
                b[3] += grow * deltay
                b[1] -= (1 - grow) * deltay

            if "e" in self.method:
                b[2] += grow * deltax
                b[0] -= (1 - grow) * deltax
            elif "w" in self.method:
                b[0] -= grow * deltax
                b[2] += (1 - grow) * deltax

            # No undo of interim steps
            with elements.undofree():
                for node in elements.elems(emphasized=True):
                    try:
                        if node.lock:
                            continue
                    except AttributeError:
                        pass
                    node.matrix.post_scale(scalex, scaley, orgx, orgy)
                    node.scaled(sx=scalex, sy=scaley, ox=orgx, oy=orgy)
            elements.update_bounds([b[0], b[1], b[2], b[3]])

        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "corner"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            nearest_snap=nearest_snap,
            modifiers=modifiers,
            helptext="Size element (with Alt-Key freely, with Ctrl+shift from center)",
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
        mid_x = (self.master.right + self.master.left) / 2
        mid_y = (self.master.bottom + self.master.top) / 2
        # Selection very small ? Relocate Handle
        inner_wd_half = (self.master.right - self.master.left) / 2
        inner_ht_half = (self.master.bottom - self.master.top) / 2
        dx = abs(min(0, inner_wd_half - 2 * self.half))
        dy = abs(min(0, inner_ht_half - 2 * self.half))

        if self.master.handle_outside:
            offset_x = self.half
            offset_y = self.half
        else:
            offset_x = 0
            offset_y = 0

        if self.index == 0:
            pos_x = mid_x
            pos_y = self.master.top - dy - offset_y
        elif self.index == 1:
            pos_x = self.master.right + dx + offset_x
            pos_y = mid_y
        elif self.index == 2:
            pos_x = mid_x
            pos_y = self.master.bottom + dy + offset_y
        else:
            pos_x = self.master.left - dx - offset_x
            pos_y = mid_y
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        brush = wx.Brush(
            self.scene.colors.color_manipulation_handle, wx.BRUSHSTYLE_SOLID
        )
        gc.SetPen(self.master.handle_pen)
        gc.SetBrush(brush)
        gc.DrawRectangle(self.left, self.top, self.width, self.height)

    def tool(self, position, nearest_snap, dx, dy, event=0, modifiers=None):
        elements = self.scene.context.elements
        if nearest_snap is None:
            # print ("Took last snap instead...")
            nearest_snap = self.scene.pane.last_snap
        if nearest_snap is not None:
            # Position is space_pos:
            # 0, 1: current x, y
            # 2, 3: last pos x, y
            # 4, 5: current - last
            position = list(position)
            # print(
            #     f"Side: pos={position[0]:.2f}, {position[1]:.2f}, "
            #     + f"old={position[2]:.2f}, {position[3]:.2f}, "
            #     + f"dx={position[4]:.2f}, dy={position[5]:.2f}"
            # )
            # print(
            #     f"snap: pos={nearest_snap[0]:.2f}, {nearest_snap[1]:.2f}, "
            #     + f"old={nearest_snap[2]:.2f}, {nearest_snap[3]:.2f}"
            # )
            position[0] = nearest_snap[0]
            position[1] = nearest_snap[1]
            position[4] = position[0] - position[2]
            position[5] = position[1] - position[3]
            dx = position[4]
            dy = position[5]

        if event == 1:
            images = []
            for e in elements.flat(types=elem_group_nodes, emphasized=True):
                # No longer needed
                # try:
                #     e.modified()
                # except AttributeError:
                #     pass
                if hasattr(e, "update"):
                    images.append(e)
            for e in images:
                e.update(None)
            self.scene.pane.modif_active = False
            self.scene.context.signal("tool_modified")
        elif event == -1:
            self.scene.pane.modif_active = True
            # Normally this would happen automagically in the background, but as we are going
            # to suppress undo during the execution of this tool (to allow to go back to the
            # very starting point) we need to set the recovery point ourselves.
            elements.prepare_undo()
            return
        elif event == 0:
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
            deltax = 0
            deltay = 0
            if "n" in self.method:
                try:
                    scaley = (self.master.bottom - position[1]) / self.save_height
                except ZeroDivisionError:
                    scaley = 1
            elif "s" in self.method:
                try:
                    scaley = (position[1] - self.master.top) / self.save_height
                except ZeroDivisionError:
                    scaley = 1
            if "w" in self.method:
                try:
                    scalex = (self.master.right - position[0]) / self.save_width
                except ZeroDivisionError:
                    scalex = 1
            elif "e" in self.method:
                try:
                    scalex = (position[0] - self.master.left) / self.save_width
                except ZeroDivisionError:
                    scaley = 1

            if len(self.method) > 1 and self.uniform:  # from corner
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale
            if abs(scalex) < NEARLY_ZERO or abs(scaley) <= NEARLY_ZERO:
                return
            # Correct, but slow...
            b = elements._emphasized_bounds
            if b is None:
                b = elements.selected_area()
                if b is None:
                    return
            if "n" in self.method:
                orgy = self.master.bottom
            else:
                orgy = self.master.top

            if "w" in self.method:
                orgx = self.master.right
            else:
                orgx = self.master.left
            grow = 1
            # If the Ctr+Shift-Keys are pressed then size equally on both opposing sides at the same time
            if self.master.key_shift_pressed and self.master.key_control_pressed:
                orgy = (self.master.bottom + self.master.top) / 2
                orgx = (self.master.left + self.master.right) / 2
                grow = 0.5

            oldvalue = self.save_width
            self.save_width *= scalex
            deltax = self.save_width - oldvalue
            oldvalue = self.save_height
            self.save_height *= scaley
            deltay = self.save_height - oldvalue

            if "n" in self.method:
                b[1] -= grow * deltay
                b[3] += (1 - grow) * deltay
            elif "s" in self.method:
                b[3] += grow * deltay
                b[1] -= (1 - grow) * deltay

            if "e" in self.method:
                b[2] += grow * deltax
                b[0] -= (1 - grow) * deltax
            elif "w" in self.method:
                b[0] -= grow * deltax
                b[2] += (1 - grow) * deltax
            # print ("Side-Tool #%d called, method=%s - dx=%.1f, dy=%.1f" % (self.index, self.method, dx, dy))
            # print (f"New width: {b[2] - b[0]:.4f}, New height: {b[3] - b[1]:.4f}")
            # print (f"Applied: scalex={scalex:.4f}, scaley={scaley:.4f}, orgx={orgx:.4f}, orgy={orgx:.4f}")

            # No undo of interim steps
            with elements.undofree():
                for node in elements.elems(emphasized=True):
                    try:
                        if node.lock:
                            continue
                    except AttributeError:
                        pass
                    node.matrix.post_scale(scalex, scaley, orgx, orgy)
                    node.scaled(sx=scalex, sy=scaley, ox=orgx, oy=orgy)

            elements.update_bounds([b[0], b[1], b[2], b[3]])

        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "side"
        s_coord = "Y" if self.index in (0, 2) else "X"
        s_help = f"Size element in {s_coord}-direction (with Ctrl+shift from center)"

        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            nearest_snap=nearest_snap,
            modifiers=modifiers,
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
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "skew_x" if is_x else "skew_y"
        self.update()

    def update(self):
        if self.master.handle_outside:
            offset_x = self.half
            offset_y = self.half
        else:
            offset_x = 0
            offset_y = 0

        if self.is_x:
            pos_x = self.master.left + 3 / 4 * (self.master.right - self.master.left)
            pos_y = self.master.bottom + offset_y
        else:
            pos_x = self.master.right + offset_x
            pos_y = self.master.top + 1 / 4 * (self.master.bottom - self.master.top)
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        gc.SetPen(self.master.handle_pen)
        brush = wx.Brush(
            self.scene.colors.color_manipulation_handle, wx.BRUSHSTYLE_SOLID
        )
        gc.SetBrush(brush)
        gc.DrawRectangle(self.left, self.top, self.width, self.height)

    def hit(self):
        return HITCHAIN_HIT

    def tool(self, position, nearest_snap, dx, dy, event=0, modifiers=None):
        """
        Change the skew of the selected elements.
        """
        elements = self.scene.context.elements
        # Skew makes not a lot of sense to listen to nearest_snap, so we ignore it...
        nearest_snap = None
        if nearest_snap is not None:
            # Position is space_pos:
            # 0, 1: current x, y
            # 2, 3: last pos x, y
            # 4, 5: current - last
            position = list(position)
            position[0] = nearest_snap[0]
            position[1] = nearest_snap[1]
            position[4] = position[0] - position[2]
            position[5] = position[1] - position[3]
            dx = position[4]
            dy = position[5]

        if event == 1:  # end
            self.last_skew = 0

            self.master.rotated_angle = self.last_skew
            images = []
            for e in elements.flat(types=elem_nodes, emphasized=True):
                try:
                    e.modified()
                except AttributeError:
                    pass
                if hasattr(e, "update"):
                    images.append(e)
            for e in images:
                e.update(None)
            self.scene.context.signal("tool_modified")
        elif event == -1:
            self.scene.pane.modif_active = True
            # Normally this would happen automagically in the background, but as we are going
            # to suppress undo during the execution of this tool (to allow to go back to the
            # very starting point) we need to set the recovery point ourselves.
            elements.prepare_undo()
            return
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

            # No undo of interim steps
            with elements.undofree():
                for e in elements.flat(types=elem_nodes, emphasized=True):
                    try:
                        if e.lock:
                            continue
                    except AttributeError:
                        pass
                    if self.is_x:
                        e.matrix.post_skew_x(
                            delta_angle,
                            (self.master.right + self.master.left) / 2,
                            (self.master.top + self.master.bottom) / 2,
                        )
                    else:
                        e.matrix.post_skew_y(
                            delta_angle,
                            (self.master.right + self.master.left) / 2,
                            (self.master.top + self.master.bottom) / 2,
                        )

            # elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "skew"
        s_help = f"Skew element in {'X' if self.is_x else 'Y'}-direction"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            nearest_snap=nearest_snap,
            modifiers=modifiers,
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
        self.action_size = size
        self.half_x = size / 2
        self.half_y = size / 2
        self.drawhalf = drawsize / 2
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        self.start_x = None
        self.start_y = None
        self.last_x = None
        self.last_y = None
        Widget.__init__(
            self, scene, -self.half_x, -self.half_y, self.half_x, self.half_y
        )
        self.cursor = "sizing"
        self.total_dx = 0
        self.total_dy = 0
        self.update()

    def update(self):
        # Let's take into account small selections
        pos_x = (self.master.right + self.master.left) / 2
        pos_y = (self.master.bottom + self.master.top) / 2
        inner_wd = (self.master.right - self.master.left) - (
            0.5 + 0.5
        ) * 2 * self.drawhalf
        self.half_x = max(self.drawhalf, min(self.action_size, inner_wd) / 2)
        inner_ht = (self.master.bottom - self.master.top) - (
            0.5 + 0.5
        ) * 2 * self.drawhalf
        self.half_y = max(self.drawhalf, min(self.action_size, inner_ht) / 2)
        self.right = self.left + 2 * self.half_x
        self.bottom = self.top + 2 * self.half_y
        self.set_position(pos_x - self.half_x, pos_y - self.half_y)

    def create_duplicate(self):
        from copy import copy

        self.duplicated_elements = True
        # Iterate through list of selected elements, duplicate them
        context = self.scene.context
        elements = context.elements
        copy_nodes = list()
        changed_nodes = list()
        delta_wordlist = 1
        # The alt-drag will leave a copy in the original location.
        # This copy will lose all hierarchy attributes,
        # so let's do something basic at least
        to_be_copied = []
        emph_list = list(elements.elems(emphasized=True))
        for e in emph_list:
            if e.type in ("file", "group"):
                for f in e.children:
                    if not f.emphasized:
                        f.emphasized = True
                        emph_list.append(f)
        for e in emph_list:
            new_parent = None
            org_parent = e.parent
            # First make sure we have all child elements as well
            if e.type in ("file", "group"):
                for f in e.children:
                    if not f.emphasized:
                        f.emphasized = True

            if org_parent is elements.elem_branch:
                new_parent = elements.elem_branch
            else:
                # Are all other elements of this group selected as well?
                # If yes create another group...
                # (that would actually need to travel down?!)
                all_selected = True
                if not org_parent.emphasized:
                    for sibling in org_parent.children:
                        if not sibling.emphasized:
                            all_selected = False
                            break
                if not all_selected:
                    new_parent = org_parent
            to_be_copied.append([e, org_parent, new_parent])

        for entry in to_be_copied:
            e = entry[0]
            oldparent = entry[1]
            newparent = entry[2]
            if newparent is None:
                # Add a new group...
                if oldparent.label is None:
                    newlabel = "Copy"
                else:
                    newlabel = f"Copy of {oldparent.label}"
                if oldparent.id is None:
                    newid = "Copy"
                else:
                    newid = f"Copy of {oldparent.id}"
                newparent = oldparent.parent.add(
                    type="group",
                    label=newlabel,
                    id=newid,
                )
                # and amend all other entries
                for others in to_be_copied:
                    if others[1] is oldparent and others[2] is None:
                        others[2] = newparent

            copy_node = copy(e)
            copy_node.emphasized = False
            copy_node.selected = False
            had_optional = False
            # Need to add stroke and fill, as copy will take the
            # default values for these attributes
            for optional in ("fill", "stroke"):
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))

            for optional in ("wxfont", "mktext", "mkfont", "mkfontsize"):
                if hasattr(e, optional):
                    setattr(copy_node, optional, getattr(e, optional))
                    had_optional = True
            newparent.add_node(copy_node)
            copy_nodes.append(copy_node)
            # The copy remains at the same place, we are moving the originals,
            # to provide the impression we are doing the right thing, we amend
            # consequently the original.
            if elements.copy_increases_wordlist_references and hasattr(e, "text"):
                e.text = elements.wordlist_delta(copy_node.text, delta_wordlist)
                e.altered()
                changed_nodes.append(e)
            elif elements.copy_increases_wordlist_references and hasattr(e, "mktext"):
                e.mktext = elements.wordlist_delta(e.mktext, delta_wordlist)
                e.altered()
                changed_nodes.append(e)
            delta_wordlist = 1
            if had_optional:
                for property_op in self.scene.context.kernel.lookup_all(
                    "path_updater/.*"
                ):
                    property_op(self.scene.context, e)

        if len(changed_nodes) > 0:
            self.scene.context.signal("element_property_update", changed_nodes)
        elements.classify(copy_nodes)

    def process_draw(self, gc):
        if self.master.tool_running:  # We don't need that overhead
            return

        self.update()  # make sure coords are valid
        gc.SetPen(self.master.handle_pen)
        brush = wx.Brush(
            self.scene.colors.color_manipulation_handle, wx.BRUSHSTYLE_SOLID
        )
        gc.SetBrush(brush)
        gc.DrawRectangle(
            self.left + self.half_x - self.drawhalf,
            self.top + self.half_y - self.drawhalf,
            2 * self.drawhalf,
            2 * self.drawhalf,
        )

    def hit(self):
        return HITCHAIN_HIT

    def check_for_magnets(self):
        if (
            not self.master.key_shift_pressed
        ):  # if Shift-Key pressed then ignore Magnets...
            elements = self.scene.context.elements
            b = elements._emphasized_bounds
            allowlockmove = elements.lock_allows_move
            dx, dy = self.scene.pane.revised_magnet_bound(b)
            self.total_dx += dx
            self.total_dy += dy
            if dx != 0 or dy != 0:
                with elements.undofree():
                    for e in elements.flat(types=elem_nodes, emphasized=True):
                        if hasattr(e, "lock") and e.lock and not allowlockmove:
                            continue
                        e.matrix.post_translate(dx, dy)
                        # We would normally not adjust the node properties,
                        # but the pure adjustment of the bbox is hopefully not hurting
                        e.translated(dx, dy)
                    self.translate(dx, dy)

                elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])

    def tool(self, position, nearest_snap, dx, dy, event=0, modifiers=None):
        """
        Change the position of the selected elements.
        """

        def move_to(dx, dy):
            if dx == 0 and dy == 0:
                return
            self.total_dx += dx
            self.total_dy += dy
            b = elements._emphasized_bounds
            if b is None:
                b = elements.selected_area()
                if b is None:
                    # There is no emphasized bounds or selected area.
                    return
            allowlockmove = elements.lock_allows_move
            with elements.undofree():
                for e in elements.flat(types=elem_nodes, emphasized=True):
                    if hasattr(e, "lock") and e.lock and not allowlockmove:
                        continue
                    e.matrix.post_translate(dx, dy)
                    # We would normally not adjust the node properties,
                    # but the pure adjustment of the bbox is hopefully not hurting
                    e.translated(dx, dy)
            self.translate(dx, dy)
            elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])

        elements = self.scene.context.elements
        lastdx = 0
        lastdy = 0
        if nearest_snap is None:
            # print ("Took last snap instead...")
            nearest_snap = self.scene.pane.last_snap
        # sweeping it under the rug for now until we have figured out a way
        # to move a defined reference and not an arbitrary point on the
        # Widget area.
        # nearest_snap = None
        if nearest_snap is not None and event != -1:
            # Position is space_pos:
            # 0, 1: current x, y
            # 2, 3: last pos x, y
            # 4, 5: current - last
            position = list(position)
            # print(
            #     f"Move: pos={position[0]:.2f}, {position[1]:.2f}, "
            #     + f"old={position[2]:.2f}, {position[3]:.2f}, "
            #     + f"dx={position[4]:.2f}, dy={position[5]:.2f}"
            # )
            # print(
            #     f"snap: pos={nearest_snap[0]:.2f}, {nearest_snap[1]:.2f}, "
            #     + f"screen={nearest_snap[2]:.2f}, {nearest_snap[3]:.2f}"
            # )
            lastdx = nearest_snap[0] - position[0]
            lastdy = nearest_snap[1] - position[1]
            position[0] = nearest_snap[0]
            position[1] = nearest_snap[1]
            position[4] = position[0] - position[2]
            position[5] = position[1] - position[3]
            # print(
            #     f"New: pos={position[0]:.2f}, {position[1]:.2f}, "
            #     + f"dx={position[4]:.2f}, dy={position[5]:.2f}"
            # )

        if event == 1:  # end
            if nearest_snap is None:
                move_to(lastdx, lastdy)
            else:
                move_to(lastdx - self.master.offset_x, lastdy - self.master.offset_y)
            self.check_for_magnets()
            # if abs(self.total_dx) + abs(self.total_dy) > 1e-3:
            #     # Did we actually move?
            #     # Remember this, it is still okay
            #     bx0, by0, bx1, by1 = elements._emphasized_bounds
            #     for e in elements.flat(types=elem_group_nodes, emphasized=True):
            #         try:
            #             # e.modified()
            #             e.translated(self.total_dx, self.total_dy)
            #         except AttributeError:
            #             pass
            #     # .translated will set the scene emphasized bounds dirty, that's not needed, so...
            #     elements.update_bounds([bx0, by0, bx1, by1])

            self.scene.context.signal("tool_modified")
            self.scene.pane.modif_active = False
        elif event == -1:  # start
            if "alt" in modifiers:
                self.create_duplicate()
            self.scene.pane.modif_active = True
            # Normally this would happen automagically in the background, but as we are going
            # to suppress undo during the execution of this tool (to allow to go back to the
            # very starting point) we need to set the recovery point ourselves.
            elements.prepare_undo()
            self.total_dx = 0
            self.total_dy = 0
        elif event == 0:  # move
            # b = elements.selected_area()  # correct, but slow...
            move_to(dx, dy)
        self.scene.request_refresh()

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "move"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            nearest_snap=nearest_snap,
            modifiers=modifiers,
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
        gc.SetPen(self.master.handle_pen)
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

    def tool(self, position, nearest_snap, dx, dy, event=0, modifiers=None):
        """
        Change the rotation-center of the selected elements.
        """
        lastdx = 0
        lastdy = 0
        if nearest_snap is None:
            # print ("Took last snap instead...")
            nearest_snap = self.scene.pane.last_snap
        elements = self.scene.context.elements
        if nearest_snap is not None:
            # Position is space_pos:
            # 0, 1: current x, y
            # 2, 3: last pos x, y
            # 4, 5: current - last
            position = list(position)
            lastdx = nearest_snap[0] - position[0]
            lastdy = nearest_snap[1] - position[1]
            position[0] = nearest_snap[0]
            position[1] = nearest_snap[1]
            position[4] = position[0] - position[2]
            position[5] = position[1] - position[3]

        if event == 1:  # end
            self.master.rotation_cx += lastdx - self.master.offset_x
            self.master.rotation_cy += lastdy - self.master.offset_y
            self.master.invalidate_rot_center()
            self.scene.pane.modif_active = False
        elif event == -1:  # start
            self.scene.pane.modif_active = True
            return
        elif event == 0:  # move
            self.master.rotation_cx += dx
            self.master.rotation_cy += dy
            self.master.invalidate_rot_center()
        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "rotcenter"
        if event_type == "doubleclick":
            self.master.rotation_cx = None
            self.master.rotation_cy = None
            self.master.invalidate_rot_center()
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        else:
            response = process_event(
                widget=self,
                widget_identifier=s_me,
                window_pos=window_pos,
                space_pos=space_pos,
                event_type=event_type,
                nearest_snap=nearest_snap,
                modifiers=modifiers,
                helptext="Move rotation center",
            )
        return response


class ReferenceWidget(Widget):
    """
    Reference Widget is tasked with drawing the reference box and managing the events
    dealing with assigning / revoking the reference status
    """

    def __init__(self, master, scene, size, is_reference_object, show_if_not_active):
        self.master = master
        self.scene = scene
        self.half = size / 2
        if is_reference_object:
            self.half = self.half * 1.5
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.show_if_not_active = show_if_not_active
        if self.show_if_not_active is None:
            self.show_if_not_active = False
        self.is_reference_object = is_reference_object
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "reference"
        self.update()

    def update(self):
        if self.master.handle_outside:
            offset_x = self.half
            offset_y = self.half
        else:
            offset_x = 0
            offset_y = 0
        pos_x = self.master.left - offset_x
        pos_y = self.master.top + 1 / 4 * (self.master.bottom - self.master.top)
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:
            # We don't need that overhead
            return
        if not (self.show_if_not_active or self.is_reference_object):
            return
        self.update()  # make sure coords are valid
        pen = wx.Pen()
        if self.is_reference_object:
            bgcol = wx.YELLOW
            fgcol = wx.RED
        else:
            bgcol = self.scene.colors.color_manipulation_handle
            fgcol = wx.BLACK
        pen.SetColour(bgcol)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        brush = wx.Brush(bgcol, wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        gc.DrawEllipse(self.left, self.top, self.width, self.height)
        # gc.DrawRectangle(self.left, self.top, self.width, self.height)
        try:
            font = wx.Font(
                0.75 * self.master.font_size,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        except TypeError:
            font = wx.Font(
                int(0.75 * self.master.font_size),
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
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
        self,
        position=None,
        nearest_snap=None,
        dx=None,
        dy=None,
        event=0,
        modifiers=None,
    ):  # Don't need all arguments, just for compatibility with pattern
        """
        Toggle the Reference Status of the selected elements
        """
        elements = self.scene.context.elements
        if event == -1:  # leftdown
            # Nothing to do...
            return
        elif event == 1:  # leftup, leftclick
            if self.is_reference_object:
                self.scene.pane.reference_object = None
            else:
                for e in elements.flat(types=elem_nodes, emphasized=True):
                    try:
                        # First object
                        self.scene.pane.reference_object = e
                        break
                    except AttributeError:
                        pass
            self.scene.context.signal("reference")
        self.scene.request_refresh()

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "reference"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            nearest_snap=nearest_snap,
            modifiers=modifiers,
            helptext="Toggle reference status of element",
            optimize_drawing=False,
        )
        return response


class LockWidget(Widget):
    """
    Lock Widget is tasked with drawing the lock box and managing the events
    dealing with revoking the lock status by clicking it
    """

    def __init__(self, master, scene, size):
        self.master = master
        self.scene = scene
        # Slightly bigger to be clearly seen
        self.half = size / 2
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "arrow"
        self.update()

    def update(self):
        if self.master.handle_outside:
            offset_x = self.half
            offset_y = self.half
        else:
            offset_x = 0
            offset_y = 0
        pos_x = self.master.right - offset_x
        pos_y = self.master.top + 1 / 4 * (self.master.bottom - self.master.top)
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if self.master.tool_running:
            # We don't need that overhead
            return
        self.update()  # make sure coords are valid
        pen = wx.Pen()
        bgcol = wx.YELLOW
        fgcol = wx.RED
        pen.SetColour(bgcol)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        gc.SetPen(pen)
        brush = wx.Brush(bgcol, wx.BRUSHSTYLE_SOLID)
        gc.SetBrush(brush)
        gc.DrawEllipse(self.left, self.top, self.width, self.height)
        # gc.DrawRectangle(self.left, self.top, self.width, self.height)
        try:
            font = wx.Font(
                0.75 * self.master.font_size,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        except TypeError:
            font = wx.Font(
                int(0.75 * self.master.font_size),
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        gc.SetFont(font, fgcol)
        symbol = "L"
        (t_width, t_height) = gc.GetTextExtent(symbol)
        gc.DrawText(
            symbol,
            (self.left + self.right) / 2 - t_width / 2,
            (self.top + self.bottom) / 2 - t_height / 2,
        )

    def hit(self):
        return HITCHAIN_HIT

    def tool(
        self,
        position=None,
        nearest_snap=None,
        dx=None,
        dy=None,
        event=0,
        modifiers=None,
    ):  # Don't need all arguments, just for compatibility with pattern
        """
        Toggle the Reference Status of the selected elements
        """
        elements = self.scene.context.elements
        if event == -1:  # leftdown
            # Nothing to do...
            return
        elif event == 1:  # leftup, leftclick
            data = list(elements.flat(types=elem_nodes, emphasized=True))
            for e in data:
                e.lock = False
            self.scene.context.signal("element_property_update", data)
        self.scene.request_refresh()

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        s_me = "lock"
        response = process_event(
            widget=self,
            widget_identifier=s_me,
            window_pos=window_pos,
            space_pos=space_pos,
            event_type=event_type,
            nearest_snap=None,
            modifiers=modifiers,
            helptext="Remove the 'locked' status of the element",
            optimize_drawing=False,
        )
        return response


class RefAlign(wx.Dialog):
    """
    RefAlign provides a dialog how to align the selection in respect to the reference object
    """

    def __init__(self, context, *args, **kwds):
        self.cancelled = False
        self.option_pos = ""
        self.option_scale = ""
        self.option_rotate = False
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

        sizer_pos = StaticBoxSizer(self, wx.ID_ANY, _("Position"), wx.HORIZONTAL)
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

        sizer_scale = StaticBoxSizer(self, wx.ID_ANY, _("Scaling"), wx.VERTICAL)
        sizer_options.Add(sizer_scale, 1, wx.EXPAND, 0)

        self.radio_btn_10 = wx.RadioButton(
            self, wx.ID_ANY, _("Unchanged"), style=wx.RB_GROUP
        )
        self.radio_btn_10.SetToolTip(_("Don't change the size of the object(s)"))
        sizer_scale.Add(self.radio_btn_10, 0, 0, 0)

        self.radio_btn_11 = wx.RadioButton(self, wx.ID_ANY, _("Fit"))
        self.radio_btn_11.SetToolTip(
            _("Scale the object(s) while maintaining the aspect ratio")
        )
        sizer_scale.Add(self.radio_btn_11, 0, 0, 0)

        self.radio_btn_12 = wx.RadioButton(self, wx.ID_ANY, _("Squeeze"))
        self.radio_btn_11.SetToolTip(
            _("Scale the object(s) to make them fit the target")
        )
        sizer_scale.Add(self.radio_btn_12, 0, 0, 0)

        self.chk_auto_rotate = wx.CheckBox(self, wx.ID_ANY, _("Autorotate"))
        self.chk_auto_rotate.SetToolTip(
            _("Rotate the object(s) if they would fit better")
        )
        sizer_scale.Add(self.chk_auto_rotate, 0, 0, 0)

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
        self.option_rotate = self.chk_auto_rotate.GetValue()
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
        return self.option_pos, self.option_scale, self.option_rotate


class SelectionWidget(Widget):
    """
    Selection Widget it tasked with drawing the selection box and managing the events
    dealing with moving, resizing and altering the selected object.
    """

    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(self.scene.colors.color_manipulation)
        self.selection_pen.SetStyle(wx.PENSTYLE_DOT)
        # want to have sharp edges
        self.selection_pen.SetJoin(wx.JOIN_MITER)

        self.handle_pen = wx.Pen()
        self.handle_pen.SetColour(self.scene.colors.color_manipulation_handle)
        self.handle_pen.SetStyle(wx.PENSTYLE_SOLID)
        # want to have sharp edges
        self.handle_pen.SetJoin(wx.JOIN_MITER)

        self.gc = None
        self.reset_variables()
        self.modifiers = []

    def init(self, context):
        context.listen("ext-modified", self.external_modification)
        # Option to draw selection Handle outside of box to allow for better visibility

    def final(self, context):
        context.unlisten("ext-modified", self.external_modification)

    @property
    def key_shift_pressed(self):
        return "shift" in self.modifiers

    @property
    def key_control_pressed(self):
        return "ctrl" in self.modifiers

    @property
    def key_alt_pressed(self):
        return "alt" in self.modifiers

    def reset_variables(self):
        self.modifiers = []
        self.save_width = None
        self.save_height = None
        self.cursor = "arrow"
        self.uniform = True
        self.rotation_cx = None
        self.rotation_cy = None
        self.rotated_angle = 0
        self.total_delta_x = 0
        self.total_delta_y = 0
        self.offset_x = 0
        self.offset_y = 0

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

    @property
    def handle_outside(self):
        return self.scene.context.outer_handles

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
        refob = self.scene.pane.reference_object

        elements = self.scene.context.elements
        if refob is None:
            return
        alignbounds = refob.bounds
        posx = ""
        posy = ""
        if "l" in pos:
            posx = "min"
        elif "r" in pos:
            posx = "max"
        else:
            posx = "center"
        if "t" in pos:
            posy = "min"
        elif "b" in pos:
            posy = "max"
        else:
            posy = "center"

        data = [
            e for e in elements.flat(types=elem_nodes, emphasized=True) if e != refob
        ]

        elements.align_elements(data, alignbounds, posx, posy, False)
        for q in data:
            q.invalidated_node()

    def rotate_elements_if_needed(self, doit):
        if not doit:
            return
        refob = self.scene.pane.reference_object
        if refob is None:
            return
        bb = refob.bounds
        elements = self.scene.context.elements
        cc = elements.selected_area()

        ratio_ref = (bb[3] - bb[1]) > (bb[2] - bb[0])
        ratio_sel = (cc[3] - cc[1]) > (cc[2] - cc[0])
        if ratio_ref != ratio_sel:
            angle = math.tau / 4
            cx = (cc[0] + cc[2]) / 2
            cy = (cc[1] + cc[3]) / 2
            dx = cc[2] - cc[0]
            dy = cc[3] - cc[1]
            for e in elements.flat(types=elem_nodes, emphasized=True):
                if e.lock:
                    continue
                e.matrix.post_rotate(angle, cx, cy)
            # Update bbox
            cc[0] = cx - dy / 2
            cc[2] = cc[0] + dy
            cc[1] = cy - dx / 2
            cc[3] = cc[1] + dx
            elements.update_bounds([cc[0], cc[1], cc[2], cc[3]])

    def scale_selection_to_ref(self, method="none"):
        refob = self.scene.pane.reference_object
        if refob is None:
            return
        bb = refob.bounds
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

        if abs(scalex) < NEARLY_ZERO or abs(scaley) <= NEARLY_ZERO:
            return
        # No undo of interim steps
        with elements.undofree():
            for e in elements.flat(types=elem_nodes, emphasized=True):
                if e.lock:
                    continue
                if e is not refob:
                    e.matrix.post_scale(scalex, scaley, cc[0], cc[1])
                    e.scaled(sx=scalex, sy=scaley, ox=cc[0], oy=cc[1])

        elements.update_bounds([cc[0], cc[1], cc[2] + dx, cc[3] + dy])

    def show_reference_align_dialog(self, event):
        opt_pos = None
        opt_scale = None
        opt_rotate = False
        dlgRefAlign = RefAlign(self.scene.context, None, wx.ID_ANY, "")
        # SetTopWindow(self.dlgRefAlign)
        if dlgRefAlign.ShowModal() == wx.ID_OK:
            opt_pos, opt_scale, opt_rotate = dlgRefAlign.results()
            # print ("I would need to align to: %s and scale to: %s" % (opt_pos, opt_scale))
        dlgRefAlign.Destroy()
        if opt_pos is not None:
            elements = self.scene.context.elements
            self.rotate_elements_if_needed(opt_rotate)
            self.scale_selection_to_ref(opt_scale)
            self.move_selection_to_ref(opt_pos)
            self.scene.context.elements.validate_selected_area()
            self.scene.request_refresh()

    def become_reference(self, event):
        for e in self.scene.context.elements.flat(types=elem_nodes, emphasized=True):
            try:
                # First object
                self.scene.pane.reference_object = e
                break
            except AttributeError:
                pass
        # print("set...")
        self.scene.context.signal("reference")
        self.scene.request_refresh()

    def delete_reference(self, event):
        self.scene.pane.reference_object = None
        self.scene.context.signal("reference")
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
        reference_object = self.scene.pane.reference_object
        if reference_object is not None:
            # Okay, just lets make sure we are not doing this on the refobject itself...
            for e in self.scene.context.elements.flat(
                types=elem_nodes, emphasized=True
            ):
                # Here we acknowledge the lock-status of an element
                if reference_object is e:
                    reference_object = None
                    break

        _ = self.scene.context._
        submenu = None
        # Add Manipulation menu
        if reference_object is not None:
            submenu = wx.Menu()
            item1 = submenu.Append(wx.ID_ANY, _("Align to reference object"))
            gui.Bind(wx.EVT_MENU, self.show_reference_align_dialog, id=item1.GetId())

        if self.single_element and not self.is_ref:
            if submenu is None:
                submenu = wx.Menu()
            item2 = submenu.Append(wx.ID_ANY, _("Become reference object"))
            gui.Bind(wx.EVT_MENU, self.become_reference, id=item2.GetId())
        if self.scene.pane.reference_object is not None:
            if submenu is None:
                submenu = wx.Menu()
            item3 = submenu.Append(wx.ID_ANY, _("Clear reference object"))
            gui.Bind(wx.EVT_MENU, self.delete_reference, id=item3.GetId())

        if submenu is not None:
            menu.AppendSubMenu(submenu, _("Reference Object"))

        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        self.modifiers = modifiers
        elements = self.scene.context.elements
        if event_type == "hover_start":
            if space_pos is not None:
                if self.contains(space_pos[0], space_pos[1]):
                    self.hovering = True
                    self.scene.context.signal("statusmsg", "")
                    self.tool_running = False

        elif event_type == "hover_end" or event_type == "lost":
            self.scene.cursor(self.cursor)
            self.hovering = False
            if space_pos is not None:
                for subwidget in self:
                    if (
                        hasattr(subwidget, "hovering")
                        and subwidget.hovering
                        and not subwidget.contains(space_pos[0], space_pos[1])
                    ):
                        subwidget.hovering = False
            self.scene.cursor("arrow")
            self.scene.context.signal("statusmsg", "")
        elif event_type == "hover":
            if self.hovering:
                self.scene.cursor(self.cursor)
            # self.tool_running = False
            self.scene.context.signal("statusmsg", "")
            if space_pos is not None:
                for subwidget in self:
                    if (
                        hasattr(subwidget, "hovering")
                        and subwidget.hovering
                        and not subwidget.contains(space_pos[0], space_pos[1])
                    ):
                        subwidget.hovering = False
                        self.scene.cursor("arrow")
                        self.scene.context.signal("statusmsg", "")

        elif event_type in ("leftdown", "leftup", "leftclick", "move"):
            # self.scene.tool_active = False
            pass
        elif event_type == "rightdown":
            self.scene.pane.tool_active = False
            self.scene.pane.modif_active = False
            smallest = bool(self.scene.context.select_smallest) != bool(
                "ctrl" in modifiers
            )
            elements.set_emphasized_by_position(
                space_pos,
                keep_old_selection=False,
                use_smallest=smallest,
                exit_over_selection=True,
            )
            # Check if reference is still existing
            self.scene.pane.validate_reference()
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            self.create_menu(
                self.scene.context.gui, elements.top_element(emphasized=True), elements
            )
            return RESPONSE_CONSUME
        elif event_type == "doubleclick":
            self.scene.pane.tool_active = False
            self.scene.pane.modif_active = False
            smallest = bool(self.scene.context.select_smallest) != bool(
                "ctrl" in modifiers
            )
            elements.set_emphasized_by_position(
                space_pos,
                keep_old_selection=False,
                use_smallest=smallest,
                exit_over_selection=True,
            )
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
        # Don't interfere during node editing
        if self.scene.pane.active_tool.startswith("edit"):
            return
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
            self.selection_pen.SetColour(self.scene.colors.color_manipulation)
            self.handle_pen.SetColour(self.scene.colors.color_manipulation_handle)
            try:
                self.selection_pen.SetWidth(self.line_width)
                self.handle_pen.SetWidth(0.75 * self.line_width)
            except TypeError:
                self.selection_pen.SetWidth(int(self.line_width))
                self.handle_pen.SetWidth(int(0.75 * self.line_width))
            if self.font_size < 1.0:
                self.font_size = 1.0  # Mac does not allow values lower than 1.
            try:
                font = wx.Font(
                    self.font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            except TypeError:
                font = wx.Font(
                    int(self.font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_BOLD,
                )
            gc.SetFont(font, self.scene.colors.color_manipulation)
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
            is_locked = True
            for idx, e in enumerate(elements.flat(types=elem_nodes, emphasized=True)):
                if e is self.scene.pane.reference_object:
                    self.is_ref = True
                # Is one of the elements locked?
                is_locked = is_locked and e.lock
                if idx > 0:
                    self.single_element = False

            if not self.single_element:
                self.is_ref = False

            # Add all subwidgets in Inverse Order
            msize = 5 * self.line_width
            rotsize = 3 * msize
            show_skew_x = self.use_handle_skew
            show_skew_y = self.use_handle_skew
            # Let's check whether there is enough room...
            # Top and bottom handle are overlapping by 1/2, middle 1, skew 2/3
            if (self.bottom - self.top) < (0.5 + 1 + 0.5 + 1) * msize:
                show_skew_y = False
            if (self.right - self.left) < (0.5 + 1 + 0.5 + 1) * msize:
                show_skew_x = False

            self.add_widget(-1, BorderWidget(master=self, scene=self.scene))
            if self.single_element and self.use_handle_size:
                self.add_widget(
                    -1,
                    ReferenceWidget(
                        master=self,
                        scene=self.scene,
                        size=msize,
                        is_reference_object=self.is_ref,
                        show_if_not_active=False,
                    ),
                )

            allowlockmove = elements.lock_allows_move
            maymove = True
            if is_locked and not allowlockmove:
                maymove = False
            if self.use_handle_move and maymove:
                self.add_widget(
                    -1,
                    MoveWidget(
                        master=self, scene=self.scene, size=rotsize, drawsize=msize
                    ),
                )
            if show_skew_y and not is_locked:
                self.add_widget(
                    -1,
                    SkewWidget(
                        master=self, scene=self.scene, is_x=False, size=2 / 3 * msize
                    ),
                )
            if show_skew_x and not is_locked:
                self.add_widget(
                    -1,
                    SkewWidget(
                        master=self, scene=self.scene, is_x=True, size=2 / 3 * msize
                    ),
                )
            if self.use_handle_rotate and not is_locked:
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
            if self.use_handle_size and not is_locked:
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
            if is_locked:
                self.add_widget(
                    -1,
                    LockWidget(
                        master=self,
                        scene=self.scene,
                        size=1.5 * msize,
                    ),
                )
