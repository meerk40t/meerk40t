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
from meerk40t.gui.scene.widget import Widget
from meerk40t.gui.wxutils import create_menu

TEXT_COLOR = wx.Colour(0xA0, 0x7F, 0xA0)
LINE_COLOR = wx.Colour(0x7F, 0x7F, 0x7F)

class BorderWidget(Widget):
    """
    Border Widget it tasked with drawing the selection box
    """
    def __init__(self, master, scene):
        self.master = master
        self.scene = scene
        self.visible = True
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
        self.visible = True
        self.cursor = "rotate1"
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
        if not self.visible:
            return

        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
        pen.SetStyle(wx.PENSTYLE_SOLID)
        self.update() # make sure coords are valid
        gc.SetPen(pen)
        gc.StrokeLine(self.left, self.top, self.right, self.bottom)
        gc.StrokeLine(self.right, self.top, self.left, self.bottom)

        cx = (self.left + self.right) / 2
        cy = (self.top + self.bottom) / 2
        if self.index==0:
            signx = +1
            signy = +1
        elif self.index==1:
            signx = -1
            signy = +1
        elif self.index==2:
            signx = +1
            signy = +1
        elif self.index==3:
            signx = +1
            signy = -1

        # Well, I would have liked to draw a poper arc via dc.DrawArc but the DeviceContext is not available here(?)
        segment = []
        # Start arrow
        x = cx - signx * self.half
        y = cy
        #segment += [(x - signx * 1/2 * self.inner, y - signy * 1/2 * self.inner)]
        #segment += [(x, y)]
        #segment += [(x + signx * 1/2 * self.inner, y - signy * 1/2 * self.inner)]
        #segment += [(x, y)]

        # Arc-Segment
        numpts = 8
        for k in range(numpts+1):
            radi = k*math.pi/(2*numpts)
            sy = math.sin(radi)
            sx = math.cos(radi)
            x = cx + signx * self.half
            y = cx + signy * self.half
            # print ("Radian=%.1f (%.1f°), sx=%.1f, sy=%.1f, x=%.1f, y=%.1f" % (radi, (radi/math.pi*180), sy, sy, x, y))
            segment += [(x, y)]

        # End Arrow
        x = cx
        y = cx + signy * self.half
        #segment += [(x - signx * 1/2 * self.inner, y - signy * 1/2 * self.inner)]
        #segment += [(x, y)]
        #segment += [(x - signx * 1/2 * self.inner, y + signy * 1/2 * self.inner)]

        gc.SetPen(pen)
        gc.StrokeLines(segment)

    def hit(self):
        if self.visible:
            # todo
            return HITCHAIN_DELEGATE
        else:
            return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if self.visible:
            if event_type == "leftdown":
                return RESPONSE_CONSUME
            elif event_type == "move":
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        else:
            return RESPONSE_CHAIN

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
        self.visible = True
        if (index==0):
            self.cursor ="size_nw"
        elif (index==1):
            self.cursor ="size_ne"
        elif (index==2):
            self.cursor ="size_sw"
        if (index==3):
            self.cursor ="size_sw"

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
        if not self.visible:
            return

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

    def hit(self):
        if self.visible:
            # todo
            return HITCHAIN_DELEGATE
        else:
            return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if self.visible:
            if event_type == "leftdown":
                return RESPONSE_CONSUME
            elif event_type == "move":
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        else:
            return RESPONSE_CHAIN

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
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.visible = True
        if index==0 or index ==2:
            self.allow_x = True
            self.allow_y = False
        else:
            self.allow_x = False
            self.allow_y = True
        if (index==0):
            self.cursor ="size_w"
        elif (index==1):
            self.cursor ="size_n"
        elif (index==2):
            self.cursor ="size_e"
        if (index==3):
            self.cursor ="size_s"
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
        if not self.visible:
            return

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

    def hit(self):
        if self.visible:
            # todo
            return HITCHAIN_DELEGATE
        else:
            return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if self.visible:
            if event_type == "leftdown":
                return RESPONSE_CONSUME
            elif event_type == "move":
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        else:
            return RESPONSE_CHAIN

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
        self.visible = True
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
        if not self.visible:
            return

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
        if self.visible:
            # todo
            return HITCHAIN_DELEGATE
        else:
            return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if self.visible:
            if event_type == "leftdown":
                return RESPONSE_CONSUME
            elif event_type == "move":
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        else:
            return RESPONSE_CHAIN

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
        self.visible = True
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "sizing"
        self.update()

    def update(self):
        pos_x = (self.master.right + self.master.left) / 2
        pos_y = (self.master.bottom + self.master.top) / 2
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if not self.visible:
            return

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
        if self.visible:
            # todo
            return HITCHAIN_DELEGATE
        else:
            return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if self.visible:
            if event_type == "leftdown":
                return RESPONSE_CONSUME
            elif event_type == "move":
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        else:
            return RESPONSE_CHAIN

class MoveRotationOriginWidget(Widget):
    """
    Move Rotation Origin Widget it tasked with drawing the rotation center indicator and managing the events
    dealing with moving the rotation center for the selected object
    """

    def __init__(self, master, scene, size):
        self.master = master
        self.scene = scene
        self.half = size/2
        self.visible = True
        Widget.__init__(self, scene, -self.half, -self.half, self.half, self.half)
        self.cursor = "rotmove"
        self.update()

    def update(self):
        pos_x = (self.master.right + self.master.left) / 2
        pos_y = (self.master.bottom + self.master.top) / 2
        self.set_position(pos_x - self.half, pos_y - self.half)

    def process_draw(self, gc):
        if not self.visible:
            return

        self.update() # make sure coords are valid
        pen = wx.Pen()
        pen.SetColour(LINE_COLOR)
        try:
            pen.SetWidth(self.master.line_width)
        except TypeError:
            pen.SetWidth(int(self.master.line_width))
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

    def hit(self):
        if self.visible:
            # todo
            return HITCHAIN_DELEGATE
        else:
            return HITCHAIN_DELEGATE

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if self.visible:
            if event_type == "leftdown":
                return RESPONSE_CONSUME
            elif event_type == "move":
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        else:
            return RESPONSE_CHAIN

class SelectionWidgetNew(Widget):
    """
    Selection Widget it tasked with drawing the selection box and managing the events
    dealing with moving, resizing and altering the selected object.
    """
    def __init__(self, scene):
        Widget.__init__(self, scene, all=False)
        self.cursor = None
        self.uniform = True
        self.matrix = None
        self.selection_pen = wx.Pen()
        self.selection_pen.SetColour(LINE_COLOR)
        self.selection_pen.SetStyle(wx.PENSTYLE_DOT)
        self.selection_font = wx.Font()
        self.line_width = 0
        self.font_size = 0


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
            self.clear()
            return HITCHAIN_HIT
        else:
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")
            self.clear()
            return HITCHAIN_DELEGATE

    def update(self):
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
        else:
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")

    def event(self, window_pos=None, space_pos=None, event_type=None):
      return RESPONSE_CHAIN

    def process_draw(self, gc):
        """
        Draw routine for drawing the selection box.
        """
        self.matrix = self.parent.matrix
        context = self.scene.context
        draw_mode = context.draw_mode
        if draw_mode & DRAW_MODE_SELECTION != 0:
            print ("Wrong Drawmode")
            return
        elements = context.elements
        bounds = elements.selected_area()
        if bounds is not None:
            self.left = bounds[0]
            self.top = bounds[1]
            self.right = bounds[2]
            self.bottom = bounds[3]
            print ("Draw (%.1f, %.1f, %.1f, %.1f)" % ( self.left, self.top, self.right, self.bottom))
            self.matrix = self.parent.matrix
            try:
                self.line_width = 2.0 / self.matrix.value_scale_x()
                self.font_size = 14.0 / self.matrix.value_scale_x()
            except ZeroDivisionError:
                self.matrix.reset()
                return
            # This pen will be used by all subchildren
            try:
                self.selection_pen.SetWidth(self.line_width)
            except TypeError:
                self.selection_pen.SetWidth(int(self.line_width))
            if self.font_size < 1.0:
                self.font_size = 1.0  # Mac does not allow values lower than 1.

            try:
                self.selection_font = wx.Font(self.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            except TypeError:
                self.selection_font = wx.Font(int(self.font_size), wx.SWISS, wx.NORMAL, wx.BOLD)
            gc.SetFont(self.selection_font, TEXT_COLOR)
            gc.SetPen(self.selection_pen)
            print("Linewidth = %.1f, Fontsize=%.1f" % (self.line_width, self.font_size))
            gc.DrawText("Live" ,  -50 , -20)
            msize = 5 * self.line_width
            rotsize = 3 * msize

            center_x = (self.left + self.right) / 2.0
            center_y = (self.top + self.bottom) / 2.0
            gc.StrokeLine(center_x, 0, center_x, self.top)
            gc.StrokeLine(0, center_y, self.left, center_y)
            gc.StrokeLine(self.left, self.top, self.right, self.top)
            gc.StrokeLine(self.right, self.top, self.right, self.bottom)
            gc.StrokeLine(self.right, self.bottom, self.left, self.bottom)
            gc.StrokeLine(self.left, self.bottom, self.left, self.top)

            # Add all subwidgets in Inverse Order
            self.add_widget(-1, SkewWidget(master=self, scene=self.scene, is_x=False, size=2/3*msize))
            self.add_widget(-1, SkewWidget(master=self, scene=self.scene, is_x=True, size=2/3*msize))
            for i in range(4):
                self.add_widget(
                    -1, RotationWidget(master=self, scene=self.scene, index=i, size=rotsize, inner=msize)
                )
            for i in range(4):
                self.add_widget(
                    -1, CornerWidget(master=self, scene=self.scene, index=i, size=msize)
                )
            for i in range(4):
                self.add_widget(-1, SideWidget(master=self, scene=self.scene, index=i, size=msize))
            self.add_widget(-1, MoveRotationOriginWidget(master=self, scene=self.scene, size=msize))
            self.add_widget(-1, MoveWidget(master=self, scene=self.scene, size=2*msize, drawsize=msize))
            self.add_widget(-1, BorderWidget(master=self, scene=self.scene))



        else:
            self.clear()


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
            self.clear()
            return
        context = self.scene.context
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

            # Add all subwidgets in Inverse Order
            msize = 5 * self.line_width
            rotsize = 3 * msize
            self.add_widget(-1, SkewWidget(master=self, scene=self.scene, is_x=False, size=2/3*msize))
            self.add_widget(-1, SkewWidget(master=self, scene=self.scene, is_x=True, size=2/3*msize))
            for i in range(4):
                self.add_widget(
                    -1, RotationWidget(master=self, scene=self.scene, index=i, size=rotsize, inner=msize)
                )
            for i in range(4):
                self.add_widget(
                    -1, CornerWidget(master=self, scene=self.scene, index=i, size=msize)
                )
            for i in range(4):
                self.add_widget(-1, SideWidget(master=self, scene=self.scene, index=i, size=msize))
            self.add_widget(-1, MoveRotationOriginWidget(master=self, scene=self.scene, size=msize))
            self.add_widget(-1, MoveWidget(master=self, scene=self.scene, size=2*msize, drawsize=msize))
            self.add_widget(-1, BorderWidget(master=self, scene=self.scene))

        else:
            self.clear()

    def create_duplicate(self):
        from copy import copy

        self.duplicated_elements = True
        # Iterate through list of selected elements, duplicate them

        context = self.scene.context
        elements = context.elements
        adding_elements = [copy(e) for e in list(elements.elems(emphasized=True))]
        elements.add_elems(adding_elements)
        elements.classify(adding_elements)