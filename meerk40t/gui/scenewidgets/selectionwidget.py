from msilib.schema import RadioButton
from pyparsing import line
import wx
import math
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

TEXT_COLOR = wx.Colour(0xA0, 0x7F, 0xA0)
LINE_COLOR = wx.Colour(0x7F, 0x7F, 0x7F)

def process_event(widget, widget_identifier=None, window_pos=None, space_pos=None, event_type=None, helptext=""):
    if widget_identifier is None:
        widget_identifier = "unknown"
    # print ("Its me - %s, event=%s, pos=%s" % (widget_identifier, event_type, space_pos ))
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
    except TypeError: # Widget already destroyed ?!
        # print ("Something went wrong for %s" % widget_identifier)
        return RESPONSE_CHAIN

    # Now all Mouse-Hover-Events
    _ = widget.scene.context._
    if event_type=="hover" and widget.hovering and not inside:
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
            widget.tool(space_pos, dx, dy, -1)
            return RESPONSE_CONSUME
    elif event_type == "middledown":
        # Hmm, I think this is never called due to the consumption of this evennt by scene pane...
        widget.was_lb_raised = False
        widget.save_width = widget.master.width
        widget.save_height = widget.master.height
        widget.uniform = False
        widget.tool(space_pos, dx, dy, -1)
        return RESPONSE_CONSUME
    elif event_type == "leftup":
        if widget.was_lb_raised:
            widget.tool(space_pos, dx, dy, 1)
            widget.scene.context.elements.ensure_positive_bounds()
            widget.was_lb_raised = False
            return RESPONSE_CONSUME
    elif event_type in ("middleup", "lost"):
        if widget.was_lb_raised:
            widget.was_lb_raised = False
            widget.tool(space_pos, dx, dy, 1)
            widget.scene.context.elements.ensure_positive_bounds()
            return RESPONSE_CONSUME
    elif event_type == "move":
        if widget.was_lb_raised:
            if not elements.has_emphasis():
                return RESPONSE_CONSUME
            if widget.save_width is None or widget.save_height is None:
                widget.save_width = widget.width
                widget.save_height = widget.height
            widget.tool(space_pos, dx, dy, 0)
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
        Widget.__init__(self, scene, self.master.left, self.master.top, self.master.right, self.master.bottom)
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
            "{distance:.2f}{units}".format(
                distance=context.device.length(self.top, 1, new_units=units, as_float=True),
                units=units,
            ),
            center_x,
            self.top / 2.0,
        )
        gc.DrawText(
            "{distance:.2f}{units}".format(
                distance=context.device.length(self.left, 0, new_units=units, as_float=True),
                units=units,
            ),
            self.left / 2.0,
            center_y,
        )
        gc.DrawText(
            "{distance:.2f}{units}".format(
                distance=context.device.length(
                    (self.bottom - self.top), 1, new_units=units, as_float=True
                ),
                units=units,
            ),
            self.right,
            center_y,
        )
        gc.DrawText(
            "{distance:.2f}{units}".format(
                distance=context.device.length(
                    (self.right - self.left), 0, new_units=units, as_float=True
                ),
                units=units,
            ),
            center_x,
            self.bottom,
        )
        if abs(self.master.rotated_angle)>0.001:
            gc.DrawText("%.0f°" % (360 * self.master.rotated_angle / math.tau), center_x, center_y)

class RotationWidget(Widget):
    """
    Rotation Widget it tasked with drawing the rotation box and managing the events
    dealing with rotating the selected object.
    """

    def __init__(self, master, scene, index, size, inner=0):
        self.master = master
        self.scene = scene
        self.index = index
        self.half = size/2
        self.inner = inner
        self.cursor = "rotate1"
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        self.rotate_cx = None
        self.rotate_cy = None

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
        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(0.75 * self.master.line_width)
        except TypeError:
            pen.SetWidth(0.75 * int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        self.update() # make sure coords are valid
        gc.SetPen(pen)

        cx = (self.left + self.right) / 2
        cy = (self.top + self.bottom) / 2
        if self.index==0: # tl
            signx = -1
            signy = -1
        elif self.index==1: # tr
            signx = +1
            signy = -1
        elif self.index==2: # br
            signx = +1
            signy = +1
        elif self.index==3: # bl
            signx = -1
            signy = +1

        # Well, I would have liked to draw a poper arc via dc.DrawArc but the DeviceContext is not available here(?)
        segment = []
        # Start arrow at 0deg, cos = 1, sin = 0
        x = cx + signx * 1 * self.half
        y = cy + signy * 0 * self.half
        segment += [(x - signx * 1/2 * self.inner, y + signy * 1/2 * self.inner)]
        segment += [(x, y)]
        segment += [(x + 2/3 * signx * 1/2 * self.inner, y + signy * 1/2 * self.inner)]
        segment += [(x, y)]

        # Arc-Segment
        numpts = 8
        for k in range(numpts+1):
            radi = k*math.pi/(2*numpts)
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
        segment += [(x + signx * 1/2 * self.inner, y + 2/3 * signy * 1/2 * self.inner)]
        segment += [(x, y)]
        segment += [(x + signx * 1/2 * self.inner, y - signy * 1/2 * self.inner)]
        gc.SetPen(pen)
        gc.StrokeLines(segment)

    def tool(self, position, dx, dy, event=0):
        """
        Change the rotation of the selected elements.
        """
        rot_angle = 0
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            self.master.rotated_angle = 0
        if event == 0:
            if self.rotate_cx is None:
                self.rotate_cx = self.master.rotation_cx
            if self.rotate_cy is None:
                self.rotate_cy = self.master.rotation_cy
            #if self.rotate_cx == self.master.rotation_cx and self.rotate_cy == self.master.rotation_cy:
            #    print ("Rotating around center")
            #else:
            #    print ("Rotating around special point")

            # Okay lets figure out whether the direction of travel was more CW or CCW
            # Lets focus on the bigger movement
            d_left = position[0] < self.rotate_cx
            d_top = position[1] < self.rotate_cy
            if abs(dx)>abs(dy):
                if d_left and d_top: # LT
                    cw = dx > 0
                elif d_left and not d_top: # LB
                    cw = dx < 0
                elif not d_left and not d_top: # RB
                    cw = dx < 0
                elif not d_left and d_top: # TR
                    cw = dx > 0
            else:
                if d_left and d_top: # LT
                    cw = dy < 0
                elif d_left and not d_top: # LB
                    cw = dy < 0
                elif not d_left and not d_top: # RB
                    cw = dy > 0
                elif not d_left and d_top: # TR
                    cw = dy > 0

            # print ("cw=%s, d_left=%s, d_top=%s, dx=%.1f, dy=%.1f, Pos=(%.1f, %.1f), Center=(%.1f, %.1f)" % ( cw, d_left, d_top, dx, dy, position[0], position[1], self.rotate_cx, self.rotate_cy))
            if self.key_alt_pressed:
                delta = 45
            else:
                delta = 1
                dd = abs(dx) if abs(dx)>abs(dy) else abs(dy)
                pxl = dd * self.master.parent.matrix.value_scale_x()
                # print ("Delta=%.1f, Pxl=%.1f" % ( dd, pxl))
                if 8 < pxl <= 15:
                    delta = 2
                elif 15 < pxl <= 25:
                    delta = 5
                elif pxl > 25:
                    delta = 10
            if cw:
                rot_angle = +1 * delta * math.tau / 360
            else:
                rot_angle = -1 * delta * math.tau / 360
            #Update Rotation angle...
            self.master.rotated_angle += rot_angle
            # Bring back to 'regular' radians
            while (self.master.rotated_angle >= 1 * math.tau):
                self.master.rotated_angle -= 1 * math.tau
            while (self.master.rotated_angle <= -1 * math.tau):
                self.master.rotated_angle += 1 * math.tau

            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                obj.transform.post_rotate(rot_angle, self.rotate_cx, self.rotate_cy)
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            for e in elements.flat(types=("group", "file")):
                try:
                    obj = e.object
                    obj.node.modified()
                except AttributeError:
                    pass
            # elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def contains(self, x, y=None):
        # Slightly more complex than usual due to the inner exclusion...
        valu = False
        if y is None:
            y = x.y
            x = x.x
        if self.left <= x <= self.right and self.top <= y <= self.bottom:
            # print ("rotation was queried:  x=%.1f, y=%.1f, left=%.1f, top=%.1f, right=%.1f, bottom=%.1f" % (x, y, self.left, self.top, self.right, self.bottom))
            valu = True
            if self.left + self.half - self.inner/2 <= x <= self.right - self.half + self.inner/2 and self.top + self.half - self.inner/2 <= y <= self.bottom - self.half + self.inner/2:
                # print("...but the inner part")
                valu = False
        return valu

    def inner_contains(self, x, y=None):
        # Slightly more complex than usual due to the inner exclusion...
        valu = False
        if y is None:
            y = x.y
            x = x.x
        x0 = self.left
        x1 = self.right
        y0 = self.top
        y1 = self.bottom
        if self.index == 0: # tl
            x0 += self.half
            y0 += self.half
        elif self.index == 1: # tr
            x1 -= self.half
            y0 += self.half
        elif self.index == 2: # br
            x1 -= self.half
            y1 -= self.half
        elif self.index == 3: # bl
            x0 += self.half
            y1 -= self.half

        if x0 <= x <= x1 and y0 <= y <= y1:
            valu = True
            if self.left + self.half - self.inner/2 <= x <= self.right - self.half + self.inner/2 and self.top + self.half - self.inner/2 <= y <= self.bottom - self.half + self.inner/2:
                # print("...but the inner part")
                valu = False
        return valu

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "rotation #" + str(self.index)
        response = process_event(widget=self, widget_identifier=s_me, window_pos=window_pos, space_pos=space_pos, event_type=event_type, helptext="Rotate element")
        if event_type == "leftdown":
            # Hit in the inner area?
            if self.inner_contains(space_pos[0], space_pos[1]):
                if self.index == 0: # tl
                    self.rotate_cx = self.master.right
                    self.rotate_cy = self.master.bottom
                elif self.index == 1: # tr
                    self.rotate_cx = self.master.left
                    self.rotate_cy = self.master.bottom
                elif self.index == 2: # br
                    self.rotate_cx = self.master.left
                    self.rotate_cy = self.master.top
                elif self.index == 3: # bl
                    self.rotate_cx = self.master.right
                    self.rotate_cy = self.master.top
            else:
                self.rotate_cx = None
                self.rotate_cy = None

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
        self.half = size/2
        self.allow_x = True
        self.allow_y = True
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        if (index==0):
            self.method = "nw"
        elif (index==1):
            self.method = "ne"
        elif (index==2):
            self.method = "se"
        if (index==3):
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
        self.update() # make sure coords are valid
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
            for e in elements.flat(types=("elem",), emphasized=True):
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

            rotation_unchanged = self.master.rotation_unchanged()

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

            if len(self.method)>1 and self.uniform: # from corner
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale

            self.save_width *= scalex
            self.save_height *= scaley

            b = elements.selected_area()
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
                try:
                    obj.node.modified()
                except AttributeError:
                    pass

            for e in elements.flat(types=("group", "file")):
                try:
                    obj = e.object
                    obj.node.modified()
                except AttributeError:
                    pass
            elements.update_bounds([b[0], b[1], b[2], b[3]])
            if rotation_unchanged:
                # Move rotation center as well
                self.master.keep_rotation_center()

            self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "corner #" + str(self.index)
        response = process_event(widget=self, widget_identifier=s_me, window_pos=window_pos, space_pos=space_pos, event_type=event_type, helptext="Size element (with Alt-Key freely)")
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
        self.half = size/2
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
        self.was_lb_raised = False
        self.hovering = False
        self.save_width = 0
        self.save_height = 0
        self.uniform = False
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        if index==0 or index ==2:
            self.allow_x = True
            self.allow_y = False
        else:
            self.allow_x = False
            self.allow_y = True
        if (index==0):
            self.method = "n"
        elif (index==1):
            self.method = "e"
        elif (index==2):
            self.method = "s"
        if (index==3):
            self.method = "w"
        self.cursor = "size_" + self.method
        self.update()

    def update(self):
        if self.index == 0:
            pos_x = (self.master.left + self.master.right)/2
            pos_y = self.master.top
        elif self.index == 1:
            pos_x = self.master.right
            pos_y = (self.master.bottom + self.master.top) / 2
        elif self.index == 2:
            pos_x = (self.master.left + self.master.right)/2
            pos_y = self.master.bottom
        else:
            pos_x = self.master.left
            pos_y = (self.master.bottom + self.master.top) / 2
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        self.update() # make sure coords are valid
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
            for e in elements.flat(types=("elem",), emphasized=True):
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

            rotation_unchanged = self.master.rotation_unchanged()

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

            if len(self.method)>1 and self.uniform: # from corner
                scale = (scaley + scalex) / 2.0
                scalex = scale
                scaley = scale

            self.save_width *= scalex
            self.save_height *= scaley

            b = elements.selected_area()
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
                try:
                    obj.node.modified()
                except AttributeError:
                    pass

            for e in elements.flat(types=("group", "file")):
                try:
                    obj = e.object
                    obj.node.modified()
                except AttributeError:
                    pass
            elements.update_bounds([b[0], b[1], b[2], b[3]])
            if rotation_unchanged:
                # Move rotation center as well
                self.master.keep_rotation_center()

            self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "side #" + str(self.index)
        s_help = "Size element in %s-direction" % ("Y" if self.index in (0, 2) else "X")
        response = process_event(widget=self, widget_identifier=s_me, window_pos=window_pos, space_pos=space_pos, event_type=event_type, helptext=s_help)
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
        self.half = size/2
        self.last_skew = 0
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
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
            pos_x = self.master.left + 3/4 * (self.master.right - self.master.left)
            pos_y = self.master.bottom
        else:
            pos_x = self.master.right
            pos_y = self.master.top + 1/4 * (self.master.bottom - self.master.top)
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        self.update() # make sure coords are valid
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
        if event == 1:
            self.last_skew = 0
            self.master.rotated_angle = self.last_skew
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        if event == 0:

            rotation_unchanged = self.master.rotation_unchanged()

            if self.is_x:
                dd = dx
            else:
                dd = dy
            if dd> 0 :
                self.last_skew += math.tau / 360
            else:
                self.last_skew -= math.tau / 360

            if self.last_skew <= -0.99 * math.pi / 2:
                self.last_skew = -0.99 * math.pi / 2
            if self.last_skew >= +0.99 * math.pi / 2:
                self.last_skew = +0.99 * math.pi / 2
            # valu = self.last_skew / math.tau * 360
            # print ("Skew-X, dx=%.1f, rad=%.2f, deg=%.2f, of Pi: %.3f" % (dx, self.last_skew, valu, self.last_skew / math.pi))
            self.master.rotated_angle = self.last_skew
            b = elements.selected_area()
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    if obj.lock:
                        continue
                except AttributeError:
                    pass
                mat = obj.transform
                if self.is_x:
                    mat[2] = math.tan(self.last_skew)
                else:
                    mat[1] = math.tan(self.last_skew)
                obj.transform = mat
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            for e in elements.flat(types=("group", "file")):
                try:
                    obj = e.object
                    obj.node.modified()
                except AttributeError:
                    pass

            if rotation_unchanged:
                # Move rotation center as well
                self.master.keep_rotation_center()

            # elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
        self.scene.request_refresh()


    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "skew-x" if self.is_x else "skew-y"
        s_help = "Skew element in %s-direction" % ("X" if self.is_x else "Y")
        response = process_event(widget=self, widget_identifier=s_me, window_pos=window_pos, space_pos=space_pos, event_type=event_type, helptext=s_help)
        return response

class MoveWidget(Widget):
    """
    Move Widget it tasked with drawing the skew box and managing the events
    dealing with moving the selected object
    """

    def __init__(self, master, scene, size, drawsize):
        self.master = master
        self.scene = scene
        self.half = size/2
        self.drawhalf = drawsize/2
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
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
        self.update() # make sure coords are valid
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
        gc.DrawRectangle(self.left+self.half-self.drawhalf, self.top+self.half-self.drawhalf, 2 * self.drawhalf, 2 * self.drawhalf)

    def hit(self):
        return HITCHAIN_HIT

    def tool(self, position, dx, dy, event=0):
        """
        Change the position of the selected elements.
        """
        elements = self.scene.context.elements
        if event == 1:
            for e in elements.flat(types=("elem",), emphasized=True):
                obj = e.object
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        if event == 0:
            rotation_unchanged = self.master.rotation_unchanged()

            b = elements.selected_area()
            for e in elements.flat(types=("elem",), emphasized=True):
                # Here we ignore the lock-status of an element
                obj = e.object
                obj.transform.post_translate(dx, dy)
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
            for e in elements.flat(types=("group", "file")):
                try:
                    obj = e.object
                    obj.node.modified()
                except AttributeError:
                    pass

            self.translate(dx, dy)

            elements.update_bounds([b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy])
            if rotation_unchanged:
                self.master.keep_rotation_center()

        self.scene.request_refresh()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "move"
        response = process_event(widget=self, widget_identifier=s_me, window_pos=window_pos, space_pos=space_pos, event_type=event_type, helptext="Move element")
        return response

class MoveRotationOriginWidget(Widget):
    """
    Move Rotation Origin Widget it tasked with drawing the rotation center indicator and managing the events
    dealing with moving the rotation center for the selected object
    """

    def __init__(self, master, scene, size):
        self.master = master
        self.scene = scene
        self.half = size/2
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
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
            #if 0 < abs(self.master.rotation_cx - (self.master.left + self.master.right)/2) <= 0.0001:
            #    print ("Difference for x too small")
            #    self.master.rotation_cx = (self.master.left + self.master.right)/2
            #if 0 < abs(self.master.rotation_cy - (self.master.top + self.master.bottom)/2) <= 0.0001:
            #    print ("Difference for y too small")
            #    self.master.rotation_cy = (self.master.top + self.master.bottom)/2
            pos_x = self.master.rotation_cx
            pos_y = self.master.rotation_cy
            self.set_position(pos_x - self.half, pos_y - self.half)
        except TypeError:
            # print ("There was nothing established as rotation center")
            pass

    def process_draw(self, gc):
        self.update() # make sure coords are valid
        pen = wx.Pen()
        # pen.SetColour(wx.RED)
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(0.75* self.master.line_width)
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
        self.scene.request_refresh()

    def hit(self):
        return HITCHAIN_HIT

    def event(self, window_pos=None, space_pos=None, event_type=None):
        s_me = "rotcenter"
        response = process_event(widget=self, widget_identifier=s_me, window_pos=window_pos, space_pos=space_pos, event_type=event_type, helptext="Move rotation center")
        return response

class ReferenceWidget(Widget):
    """
    Lock Widget it tasked with drawing the skew box and managing the events
    dealing with moving the selected object
    """

    def __init__(self, master, scene, size, is_reference_object):
        self.master = master
        self.scene = scene
        self.half = size/2
        if is_reference_object:
            self.half = self.half * 1.5
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
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
        pos_y = self.master.top + 1/4 * (self.master.bottom - self.master.top)
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        self.update() # make sure coords are valid
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
            font = wx.Font(0.75*self.master.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
        except TypeError:
            font = wx.Font(int(0.75*self.master.font_size), wx.SWISS, wx.NORMAL, wx.BOLD)
        gc.SetFont(font, fgcol)
        symbol ="r"
        (t_width, t_height) = gc.GetTextExtent(symbol)
        gc.DrawText(symbol, (self.left + self.right)/2 - t_width / 2, (self.top + self.bottom)/2 - t_height / 2)

    def hit(self):
        return HITCHAIN_HIT

    def tool(self, position=None, dx=None, dy=None, event=0): # Don't need all arguments, just for compatibility with pattern
        """
        Toggle the Reference Status of the selected elements
        """
        elements = self.scene.context.elements
        if event == 1:
            # Nothing to do...
            pass
        if event == -1: # leftdown
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
        s_me = "lock"
        response = process_event(widget=self, widget_identifier=s_me, window_pos=window_pos, space_pos=space_pos, event_type=event_type, helptext="Toggle reference status of element")
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

        label_1 = wx.StaticText(self, wx.ID_ANY, _("Move the selection into the reference object and scale the elements."))
        sizer_ref_align.Add(label_1, 0, wx.EXPAND, 0)

        sizer_options = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ref_align.Add(sizer_options, 0, wx.EXPAND, 0)

        sizer_pos = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _("Position")), wx.HORIZONTAL)
        sizer_options.Add(sizer_pos, 1, wx.EXPAND, 0)

        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        sizer_pos.Add(sizer_6, 1, wx.EXPAND, 0)

        self.radio_btn_1 = wx.RadioButton(self, wx.ID_ANY, "TL", style = wx.RB_GROUP)
        self.radio_btn_1.SetToolTip(_("Align the selection to the top left corner of the reference object"))
        sizer_6.Add(self.radio_btn_1, 0, 0, 0)

        self.radio_btn_4 = wx.RadioButton(self, wx.ID_ANY, "L")
        self.radio_btn_4.SetToolTip(_("Align the selection to the left side of the reference object"))
        sizer_6.Add(self.radio_btn_4, 0, 0, 0)

        self.radio_btn_7 = wx.RadioButton(self, wx.ID_ANY, "BL")
        self.radio_btn_7.SetToolTip(_("Align the selection to the bottom left corner of the reference object"))
        sizer_6.Add(self.radio_btn_7, 0, 0, 0)

        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_pos.Add(sizer_7, 1, wx.EXPAND, 0)

        self.radio_btn_2 = wx.RadioButton(self, wx.ID_ANY, "T")
        self.radio_btn_2.SetToolTip(_("Align the selection to the upper side of the reference object"))
        sizer_7.Add(self.radio_btn_2, 0, 0, 0)

        self.radio_btn_5 = wx.RadioButton(self, wx.ID_ANY, "C")
        sizer_7.Add(self.radio_btn_5, 0, 0, 0)

        self.radio_btn_8 = wx.RadioButton(self, wx.ID_ANY, "B")
        self.radio_btn_8.SetToolTip(_("Align the selection to the lower side of the reference object"))
        sizer_7.Add(self.radio_btn_8, 0, 0, 0)

        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_pos.Add(sizer_8, 1, wx.EXPAND, 0)

        self.radio_btn_3 = wx.RadioButton(self, wx.ID_ANY, "TR")
        self.radio_btn_3.SetToolTip(_("Align the selection to the top right corner of the reference object"))
        sizer_8.Add(self.radio_btn_3, 0, 0, 0)

        self.radio_btn_6 = wx.RadioButton(self, wx.ID_ANY, "R")
        sizer_8.Add(self.radio_btn_6, 0, 0, 0)

        self.radio_btn_9 = wx.RadioButton(self, wx.ID_ANY, "BR")
        self.radio_btn_9.SetToolTip(_("Align the selection to the bottom right corner of the reference object"))
        sizer_8.Add(self.radio_btn_9, 0, 0, 0)

        sizer_scale = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Scaling"), wx.VERTICAL)
        sizer_options.Add(sizer_scale, 1, wx.EXPAND, 0)

        self.radio_btn_10 = wx.RadioButton(self, wx.ID_ANY, "Unchanged", style = wx.RB_GROUP)
        self.radio_btn_10.SetToolTip(_("Don't change the size of the object(s)"))
        sizer_scale.Add(self.radio_btn_10, 0, 0, 0)

        self.radio_btn_11 = wx.RadioButton(self, wx.ID_ANY, "Fit")
        self.radio_btn_11.SetToolTip(_("Scale the object(s) while maintaining the aspect ratio"))
        sizer_scale.Add(self.radio_btn_11, 0, 0, 0)

        self.radio_btn_12 = wx.RadioButton(self, wx.ID_ANY, "Squeeze")
        self.radio_btn_11.SetToolTip(_("Scale the object(s) to make them fit the target"))
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

        self.radio_btn_10.SetValue(1) # Unchanged
        self.radio_btn_5.SetValue(1) # center

    def results(self):
        self.cancelled = False
        if self.radio_btn_10.GetValue():
            self.option_scale = "none"
        elif self.radio_btn_11.GetValue():
            self.option_scale = "fit"
        if self.radio_btn_12.GetValue():
            self.option_scale = "squeeze"
        for radio in (self.radio_btn_1, self.radio_btn_2, self.radio_btn_3,self.radio_btn_4, self.radio_btn_5, self.radio_btn_6,self.radio_btn_7, self.radio_btn_8, self.radio_btn_9,):
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
        self.save_width = None
        self.save_height = None
        self.cursor = "arrow"
        self.uniform = True
        self.rotation_cx = None
        self.rotation_cy = None
        self.rotated_angle = 0
        self.key_shift_pressed = False
        self.key_control_pressed = False
        self.key_alt_pressed = False
        self.was_lb_raised = False
        self.hovering = False
        self.use_handle_rotate = True
        self.use_handle_skew = True
        self.use_handle_size = True
        self.use_handle_move = True
        self.keep_rotation = True
        self.popupID1 = None

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
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")
            self.rotation_cx = None
            self.rotation_cy = None
            return HITCHAIN_DELEGATE

    def move_selection_to_ref(self, pos="c"):
        refob = self.scene.reference_object
        if refob is None:
            return
        bb = refob.bbox()

        cc = self.scene.context.elements.selected_area()
        if bb is None or cc is None:
            return
        if "l" in pos:
            tx = bb[0]
        elif "r" in pos:
            tx = bb[2] - (cc[2]-cc[0])
        else:
            tx = (bb[0] + bb[2])/2 - (cc[2] - cc[0]) / 2

        if "t" in pos:
            ty = bb[1]
        elif "b" in pos:
            ty = bb[3] - (cc[3]-cc[1])
        else:
            ty = (bb[1] + bb[3])/2 - (cc[3] - cc[1]) / 2

        dx = tx - cc[0]
        dy = ty - cc[1]
        #print ("Moving from (%.1f, %.1f) to (%.1f, %.1f) translate by (%.1f, %.1f)" % (cc[0], cc[1], tx, ty, dx, dy ))

        for e in self.scene.context.elements.flat(types=("elem",), emphasized=True):
            # Here we ignore the lock-status of an element, as this is just a move...
            obj = e.object
            if not obj is refob:
                obj.transform.post_translate(dx, dy)
                try:
                    obj.node.modified()
                except AttributeError:
                    pass
        for e in self.scene.context.elements.flat(types=("group", "file")):
            try:
                obj = e.object
                obj.node.modified()
            except AttributeError:
                pass


    def scale_selection_to_ref(self, method="none"):
        refob = self.scene.reference_object
        if refob is None:
            return
        bb = refob.bbox()

        cc = self.scene.context.elements.selected_area()
        if bb is None or cc is None:
            return
        try:
            b_ratio = (bb[2] - bb[0]) / (bb[3] - bb[1])
            c_ratio = (cc[2] - cc[0]) / (cc[3] - cc[1])
        except ZeroDivisionError:
            return
        if method=="fit":
            scalex = (bb[2] - bb[0]) / (cc[2] - cc[0])
            scaley = (bb[3] - bb[1]) / (cc[3] - cc[1])
            scalex = min(scalex, scaley)
            scaley = scalex
        elif method=="squeeze":
            scalex = (bb[2] - bb[0]) / (cc[2] - cc[0])
            scaley = (bb[3] - bb[1]) / (cc[3] - cc[1])
        else :
            return
        # print ("Scaling by x=%.1f, y=%.1f" % (scalex, scaley))
        for e in self.scene.context.elements.flat(types=("elem",), emphasized=True):
            # Here we acknowledge the lock-status of an element
            obj = e.object
            try:
                if obj.lock:
                    continue
            except AttributeError:
                pass
            if not obj is refob:
                obj.transform.post_scale(scalex, scaley, cc[0], cc[1])
                e._bounds_dirty = True
        for e in self.scene.context.elements.flat(types=("group", "file")):
            try:
                obj = e.object
                obj.node.modified()
            except AttributeError:
                pass


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
            self.scale_selection_to_ref(opt_scale)
            self.scene.request_refresh()
            self.move_selection_to_ref(opt_pos)
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

        # Add Manipulation menu
        if not obj is None:
            _ = self.scene.context._
            menu.AppendSeparator()
            if self.popupID1 is None:
                self.popupID1 = wx.NewId()
            gui.Bind(wx.EVT_MENU, self.show_reference_align_dialog, id=self.popupID1)
            menu.Append(self.popupID1, _("Align to reference object"))

        if menu.MenuItemCount != 0:
            gui.PopupMenu(menu)
            menu.Destroy()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        elements = self.scene.context.elements
        if event_type == "hover_start":
            self.hovering = True
            self.scene.context.signal("statusmsg", "")
        elif event_type == "hover_end" or event_type == "lost":
            self.scene.cursor(self.cursor)
            self.scene.context.signal
            self.hovering = False
            self.scene.context.signal("statusmsg", "")
        elif event_type == "hover":
            if self.hovering:
                self.scene.cursor(self.cursor)
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

    def rotation_unchanged(self):
        cx = (self.left + self.right)/2
        cy = (self.top + self.bottom)/2
        valu = abs(self.rotation_cx - cx) < 0.0001 and abs(self.rotation_cy - cy) < 0.0001
        #if valu:
        #    print ("RotHandle still in center")
        #else:
        #    print ("RotHandle (%.1f, %.1f) outside center (%.1f, %.1f)" % (self.rotation_cx, self.rotation_cy, cx, cy))
        return valu

    def keep_rotation_center(self):
        # Make sure rotation center remains centered...
        self.keep_rotation = True

    def process_draw(self, gc):
        """
        Draw routine for drawing the selection box.
        """
        if self.scene.context.draw_mode & DRAW_MODE_SELECTION != 0:
            return
        self.clear() # Clearing children as we are generating them in a bit...
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
            pass

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
            if self.keep_rotation: # Reset it to center....
                cx = (self.left + self.right)/2
                cy = (self.top + self.bottom)/2
                self.keep_rotation = False
                self.rotation_cx = cx
                self.rotation_cy = cy

            # Prep codoe for reference object - single object? And identical to reference?
            is_ref = False
            single_element = True
            if not self.scene.reference_object is None:

                for idx, e in enumerate(elements.flat(types=("elem",), emphasized=True)):
                    obj = e.object
                    if obj is self.scene.reference_object:
                        is_ref = True
                    if idx>0:
                        single_element =False
                        break

            if not single_element:
                is_ref = False

            # Add all subwidgets in Inverse Order
            msize = 5 * self.line_width
            rotsize = 3 * msize

            self.add_widget(-1, BorderWidget(master=self, scene=self.scene))
            if single_element and self.use_handle_skew:
                self.add_widget(-1, ReferenceWidget(master=self, scene=self.scene, size=msize, is_reference_object=is_ref))
            if self.use_handle_move:
                self.add_widget(-1, MoveWidget(master=self, scene=self.scene, size=rotsize, drawsize=msize))
            if self.use_handle_skew:
                self.add_widget(-1, SkewWidget(master=self, scene=self.scene, is_x=False, size=2/3*msize))
                self.add_widget(-1, SkewWidget(master=self, scene=self.scene, is_x=True, size=2/3*msize))
            if self.use_handle_rotate:
                for i in range(4):
                    self.add_widget(
                        -1, RotationWidget(master=self, scene=self.scene, index=i, size=rotsize, inner=msize)
                    )
                self.add_widget(-1, MoveRotationOriginWidget(master=self, scene=self.scene, size=msize))
            if self.use_handle_size:
                for i in range(4):
                    self.add_widget(
                        -1, CornerWidget(master=self, scene=self.scene, index=i, size=msize)
                    )
                for i in range(4):
                    self.add_widget(-1, SideWidget(master=self, scene=self.scene, index=i, size=msize))
