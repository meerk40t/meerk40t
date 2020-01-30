import wx
from PIL import Image

from LaserNode import *
from ZMatrix import ZMatrix
from LaserCommandConstants import *

"""
Laser Render provides GUI relevant methods of displaying the given project nodes.
"""


def swizzlecolor(c):
    if c is None:
        return None
    if isinstance(c, int):
        c = Color(c)
    return c.blue << 16 | c.green << 8 | c.red


class LaserRender:
    def __init__(self, project):
        self.project = project
        self.cache = None
        self.pen = wx.Pen()
        self.brush = wx.Brush()
        self.color = wx.Colour()

    def render(self, dc, draw_mode):
        if draw_mode & 0x1C00 == 0:
            types = ('image', 'path', 'text')
        else:
            types = []
            if draw_mode & 0x0400 == 0:
                types.append('path')
            if draw_mode & 0x0800 == 0:
                types.append('image')
            if draw_mode & 0x1000 == 0:
                types.append('text')
            types = tuple(types)
        for element in self.project.elements.flat_elements(types=types, passes=False):
            try:
                element.draw(element, dc, draw_mode)
            except AttributeError:
                if isinstance(element.element, Path):
                    element.draw = self.draw_path
                elif isinstance(element.element, SVGImage):
                    element.draw = self.draw_image
                elif isinstance(element.element, SVGText):
                    element.draw = self.draw_text
                else:
                    element.draw = self.draw_path
            try:
                element.draw(element, dc, draw_mode)
            except AttributeError:
                pass  # This should not have happened.

    def generate_path(self, path):
        object_path = abs(path)
        plot = object_path
        first_point = plot.first_point
        if first_point is None:
            return
        yield COMMAND_RAPID_MOVE, first_point
        yield COMMAND_PLOT, plot

    def make_path(self, gc, element):
        p = gc.CreatePath()
        parse = LaserCommandPathParser(p)
        path = element.element

        for event in self.generate_path(path):
            parse.command(event)
        return p

    def make_raster(self, group, width=None, height=None, bitmap=False, types=('path', 'text', 'image')):
        flat_elements = list(group.flat_elements(types=types, passes=False))
        bounds = group.scene_bounds
        if bounds is None:
            self.validate()
            bounds = group.scene_bounds
        if bounds is None:
            return None
        xmin, ymin, xmax, ymax = bounds
        image_width = int(xmax - xmin)
        if image_width == 0:
            image_width = 1
        image_height = int(ymax - ymin)
        if image_height == 0:
            image_height = 1
        if width is None:
            width = image_width
        else:
            width = int(width)
        if height is None:
            height = image_height
        else:
            height = int(height)
        bmp = wx.Bitmap(width, height, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        for e in flat_elements:
            element = e.element
            matrix = element.transform
            old_matrix = Matrix(matrix)

            matrix.post_translate(-xmin, -ymin)
            scale_x = width / float(image_width)
            scale_y = height / float(image_height)
            scale = min(scale_x, scale_y)
            matrix.post_scale(scale)
            if e.type == 'path':
                p = self.make_path(gc, e)
                self.set_brush(gc, e.fill)
                self.set_pen(gc, e.stroke, width=e.stroke_width * scale)
                gc.FillPath(p)
                gc.StrokePath(p)
                del p
            # TODO: There is a need to raster a fragment of scene, including images.
            # Such that make_raster and actualize are two sides of the same coin.
            element.transform = old_matrix

        img = bmp.ConvertToImage()
        buf = img.GetData()
        image = Image.frombuffer("RGB", tuple(bmp.GetSize()), bytes(buf), "raw", "RGB", 0, 1)
        gc.Destroy()
        del dc
        if bitmap:
            return bmp
        return image

    def set_pen(self, gc, stroke, width=1.0):
        c = swizzlecolor(stroke)
        if c is None:
            self.pen.SetColour(None)
        else:
            self.color.SetRGB(c)
            self.pen.SetColour(self.color)

        self.pen.SetWidth(width)
        gc.SetPen(self.pen)

    def set_brush(self, gc, fill):
        c = fill
        if c is not None and c != 'none':
            swizzle_color = swizzlecolor(c)
            self.color.SetRGB(swizzle_color)  # wx has BBGGRR
            self.brush.SetColour(self.color)
            gc.SetBrush(self.brush)
        else:
            gc.SetBrush(wx.TRANSPARENT_BRUSH)

    def draw_path(self, node, dc, draw_mode):
        """Default draw routine for the laser element.
        If the generate is defined this will draw the
        element as a series of lines, as defined by generate."""
        try:
            matrix = node.element.transform
        except AttributeError:
            matrix = Matrix()
        drawfills = draw_mode & 1 == 0
        drawstrokes = draw_mode & 64 == 0
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        self.set_pen(gc, node.stroke, width=node.stroke_width)
        self.set_brush(gc, node.fill)
        cache = None
        try:
            cache = node.cache
        except AttributeError:
            pass
        if cache is None:
            node.cache = self.make_path(gc, node)
        if drawfills and node.fill is not None:
            gc.FillPath(node.cache)
        if drawstrokes and node.stroke is not None:
            gc.StrokePath(node.cache)

    def draw_text(self, node, dc, draw_mode):
        try:
            matrix = node.element.transform
        except AttributeError:
            matrix = Matrix()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if node.element.text is not None:
            dc.DrawText(node.element.text, matrix.value_trans_x(), matrix.value_trans_y())

    def make_thumbnail(self, node, maximum=None, width=None, height=None):
        pil_data = node.element.image
        image_width, image_height = pil_data.size
        if width is not None and height is None:
            height = width * image_height / float(image_width)
        if width is None and height is not None:
            width = height * image_width / float(image_height)
        if width is None and height is None:
            width = image_width
            height = image_height
        if maximum is not None and (width > maximum or height > maximum):
            scale_x = maximum / width
            scale_y = maximum / height
            scale = min(scale_x, scale_y)
            width = int(round(width * scale))
            height = int(round(height * scale))
        if image_width != width or image_height != height:
            pil_data = pil_data.copy().resize((width, height))
        else:
            pil_data = pil_data.copy()
        if pil_data.mode != "RGBA":
            pil_data = pil_data.convert('RGBA')
        pil_bytes = pil_data.tobytes()
        return wx.Bitmap.FromBufferRGBA(width, height, pil_bytes)

    def draw_image(self, node, dc, draw_mode):
        try:
            matrix = node.element.transform
        except AttributeError:
            matrix = Matrix()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        cache = None
        try:
            cache = node.cache
        except AttributeError:
            pass
        if cache is None:
            try:
                max_allowed = node.max_allowed
            except AttributeError:
                max_allowed = 2048
            node.c_width, node.c_height = node.element.image.size
            node.cache = self.make_thumbnail(node, maximum=max_allowed)
        gc.DrawBitmap(node.cache, 0, 0, node.c_width, node.c_height)

    def set_selected_by_position(self, position):
        self.project.set_selected(None)
        self.validate()
        for e in reversed(list(self.project.elements.flat_elements(types=('image', 'path', 'text'), passes=False))):
            bounds = e.scene_bounds
            if bounds is None:
                continue
            if e.contains(position):
                if e.parent is not None:
                    e = e.parent
                self.project.set_selected(e)
                break

    def validate(self, node=None):
        if node is None:
            # Default call.
            node = self.project.elements

        node.scene_bound = None  # delete bounds
        for element in node:
            self.validate(element)  # validate all subelements.
        if len(node) == 0:  # Leaf Node.
            try:
                node.scene_bounds = node.element.bbox()
            except AttributeError:
                pass
            return
        # Group node.
        xvals = []
        yvals = []
        for e in node:
            bounds = e.scene_bounds
            if bounds is None:
                continue
            xvals.append(bounds[0])
            xvals.append(bounds[2])
            yvals.append(bounds[1])
            yvals.append(bounds[3])
        if len(xvals) == 0:
            return
        node.scene_bounds = [min(xvals), min(yvals), max(xvals), max(yvals)]

    def bbox(self, elements):
        boundary_points = []
        for e in elements.flat_elements(types=('image', 'path', 'text'), passes=False):
            box = e.scene_bounds
            if box is None:
                continue
            top_left = e.transform.point_in_matrix_space([box[0], box[1]])
            top_right = e.transform.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)
        if len(boundary_points) == 0:
            return None
        xmin = min([e[0] for e in boundary_points])
        ymin = min([e[1] for e in boundary_points])
        xmax = max([e[0] for e in boundary_points])
        ymax = max([e[1] for e in boundary_points])
        return xmin, ymin, xmax, ymax


class LaserCommandPathParser:
    """This class converts a set of laser commands into a
     graphical representation of those commands."""

    def __init__(self, graphic_path):
        self.graphic_path = graphic_path
        self.on = False
        self.relative = False
        self.x = 0
        self.y = 0

    def command(self, event):
        command, values = event
        if command == COMMAND_LASER_OFF:
            self.on = False
        elif command == COMMAND_LASER_ON:
            self.on = True
        elif command == COMMAND_RAPID_MOVE:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_SET_SPEED:
            pass
        elif command == COMMAND_SET_POWER:
            pass
        elif command == COMMAND_SET_STEP:
            pass
        elif command == COMMAND_SET_DIRECTION:
            pass
        elif command == COMMAND_MODE_COMPACT:
            pass
        elif command == COMMAND_MODE_DEFAULT:
            pass
        elif command == COMMAND_MODE_CONCAT:
            pass
        elif command == COMMAND_SET_ABSOLUTE:
            self.relative = False
        elif command == COMMAND_SET_INCREMENTAL:
            self.relative = True
        elif command == COMMAND_HSTEP:
            x = values
            y = self.y
            x += self.x
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_VSTEP:
            x = self.x
            y = values
            y += self.y
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_HOME:
            self.graphic_path.MoveToPoint(0, 0)
            self.x = 0
            self.y = 0
        elif command == COMMAND_LOCK:
            pass
        elif command == COMMAND_UNLOCK:
            pass
        elif command == COMMAND_PLOT:
            plot = values
            for e in plot:
                if isinstance(e, Move):
                    self.graphic_path.MoveToPoint(e.end[0], e.end[1])
                elif isinstance(e, Line):
                    self.graphic_path.AddLineToPoint(e.end[0], e.end[1])
                elif isinstance(e, Close):
                    self.graphic_path.CloseSubpath()
                elif isinstance(e, QuadraticBezier):
                    self.graphic_path.AddQuadCurveToPoint(e.control[0], e.control[1],
                                                          e.end[0], e.end[1])
                elif isinstance(e, CubicBezier):
                    self.graphic_path.AddCurveToPoint(e.control1[0], e.control1[1],
                                                      e.control2[0], e.control2[1],
                                                      e.end[0], e.end[1])
                elif isinstance(e, Arc):
                    for curve in e.as_cubic_curves():
                        self.graphic_path.AddCurveToPoint(curve.control1[0], curve.control1[1],
                                                          curve.control2[0], curve.control2[1],
                                                          curve.end[0], curve.end[1])

        elif command == COMMAND_SHIFT:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_MOVE:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            if self.on:
                self.graphic_path.MoveToPoint(x, y)
            else:
                self.graphic_path.AddLineToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_CUT:
            x, y = values
            if self.relative:
                x += self.x
                y += self.y
            self.graphic_path.AddLineToPoint(x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_CUT_QUAD:
            cx, cy, x, y = values
            if self.relative:
                x += self.x
                y += self.y
                cx += self.x
                cy += self.y

            self.graphic_path.AddQuadCurveToPoint(cx, cy, x, y)
            self.x = x
            self.y = y
        elif command == COMMAND_CUT_CUBIC:
            c1x, c1y, c2x, c2y, x, y = values
            if self.relative:
                x += self.x
                y += self.y
                c1x += self.x
                c1y += self.y
                c2x += self.x
                c2y += self.y
            self.graphic_path.AddCurveToPoint(c1x, c1y, c2x, c2y, x, y)
            self.x = x
            self.y = y
