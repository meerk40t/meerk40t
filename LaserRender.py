import wx
from PIL import Image

from ProjectNodes import *
from ZMatrix import ZMatrix

"""
Laser Render provides GUI relevant methods of displaying the given project nodes.
"""

# TODO: Raw typically uses path, but could just use a 1 bit image to visualize it.


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
        for element in self.project.elements.flat_elements(types=('image', 'path', 'text')):
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
                element.draw(element, dc, draw_mode)

    def make_raster(self, group):
        flat_elements = list(group.flat_elements(types='path'))
        xmin, ymin, xmax, ymax = group.bounds
        width = int(xmax - xmin)
        height = int(ymax - ymin)
        bitmap = wx.Bitmap(width, height, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        for e in flat_elements:
            element = e.element
            matrix = element.transform
            fill_color = e.fill
            if fill_color is None:
                continue
            p = gc.CreatePath()
            parse = LaserCommandPathParser(p)

            matrix.post_translate(-xmin, -ymin)
            for event in e.generate():
                parse.command(event)
            matrix.post_translate(+xmin, +ymin)

            self.color.SetRGB(swizzlecolor(fill_color))
            self.brush.SetColour(self.color)
            gc.SetBrush(self.brush)
            gc.FillPath(p)
            del p
        img = bitmap.ConvertToImage()
        buf = img.GetData()
        image = Image.frombuffer("RGB", tuple(bitmap.GetSize()), bytes(buf), "raw", "RGB", 0, 1)
        gc.Destroy()
        del dc
        return image

    def draw_path(self, node, dc, draw_mode):
        """Default draw routine for the laser element.
        If the generate is defined this will draw the
        element as a series of lines, as defined by generate."""
        try:
            matrix = node.element.transform
        except AttributeError:
            matrix = Matrix()
        drawfills = draw_mode & 1 == 0
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        c = swizzlecolor(node.stroke)
        if c is None:
            self.pen.SetColour(None)
        else:
            self.color.SetRGB(c)
            self.pen.SetColour(self.color)
        gc.SetPen(self.pen)
        cache = None
        try:
            cache = node.cache
        except AttributeError:
            pass
        if cache is None:
            p = gc.CreatePath()
            parse = LaserCommandPathParser(p)
            for event in node.generate():
                parse.command(event)
            node.cache = p
        if drawfills and node.fill is not None:
            c = node.fill
            if c is not None and c != 'none':
                swizzle_color = swizzlecolor(c)
                self.color.SetRGB(swizzle_color)  # wx has BBGGRR
                self.brush.SetColour(self.color)
                gc.SetBrush(self.brush)
                gc.FillPath(node.cache)
        gc.StrokePath(node.cache)

    def draw_text(self, node, dc, draw_mode):
        try:
            matrix = node.element.transform
        except AttributeError:
            matrix = Matrix()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if node.text is not None:
            dc.DrawText(node.text, matrix.value_trans_x(), matrix.value_trans_y())

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
            pil_data = node.element.image
            node.c_width, node.c_height = pil_data.size
            width, height = pil_data.size
            dim = max(width, height)
            if dim > max_allowed or max_allowed == -1:
                width = int(round(width * max_allowed / float(dim)))
                height = int(round(height * max_allowed / float(dim)))
                pil_data = pil_data.copy().resize((width, height))
            else:
                pil_data = pil_data.copy()
            if pil_data.mode != "RGBA":
                pil_data = pil_data.convert('RGBA')
            pil_bytes = pil_data.tobytes()
            node.cache = wx.Bitmap.FromBufferRGBA(width, height, pil_bytes)
        gc.DrawBitmap(node.cache, 0, 0, node.c_width, node.c_height)


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
