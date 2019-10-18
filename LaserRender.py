from PIL import Image
import wx
from ZMatrix import ZMatrix

from ProjectNodes import *


# TODO: Raw typically uses path, but could just use a 1 bit image to visualize it.

def swizzlecolor(c):
    swizzle_color = (c & 0xFF) << 16 | ((c >> 8) & 0xFF) << 8 | ((c >> 16) & 0xFF)
    return swizzle_color

class LaserRender:
    def __init__(self, project):
        self.project = project
        self.cache = None
        self.pen = wx.Pen()
        self.brush = wx.Brush()
        self.color = wx.Colour()

    def render(self, dc, draw_mode):
        for element in self.project.elements.flat_elements(LaserElement):
            try:
                element.draw(element, dc, draw_mode)
            except AttributeError:
                if isinstance(element, PathElement):
                    element.draw = self.draw
                elif isinstance(element, ImageElement):
                    element.draw = self.draw_image
                elif isinstance(element, TextElement):
                    element.draw = self.draw_text
                else:
                    element.draw = self.draw
                element.draw(element, dc, draw_mode)

    def make_raster(self, group):
        elems = list(group.flat_elements(types=(PathElement)))
        xmin, ymin, xmax, ymax = group.bounds
        width = int(xmax - xmin)
        height = int(ymax - ymin)
        bitmap = wx.Bitmap(width, height, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        for e in elems:
            fill_color = e.fill
            if fill_color is None:
                continue
            p = gc.CreatePath()
            parse = LaserCommandPathParser(p)

            e.matrix.post_translate(-xmin, -ymin)
            for event in e.generate():
                parse.command(event)
            e.matrix.post_translate(+xmin, +ymin)

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

    def draw(self, node, dc, draw_mode):
        """Default draw routine for the laser element.
        If the generate is defined this will draw the
        element as a series of lines, as defined by generate."""
        drawfills = draw_mode & 1 == 0
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(node.matrix)))

        self.color.SetRGB(swizzlecolor(node.properties[VARIABLE_NAME_COLOR]))
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
            for event in node.generate(path.Matrix()):
                parse.command(event)
            node.cache = p
        if drawfills and VARIABLE_NAME_FILL_COLOR in node.properties:
            c = node.properties[VARIABLE_NAME_FILL_COLOR]
            swizzle_color = (c & 0xFF) << 16 | ((c >> 8) & 0xFF) << 8 | ((c >> 16) & 0xFF)
            self.color.SetRGB(swizzle_color)  # wx has BBGGRR
            self.brush.SetColour(self.color)
            gc.SetBrush(self.brush)
            gc.FillPath(node.cache)
        gc.StrokePath(node.cache)

    def draw_text(self, node, dc, draw_mode):
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(node.matrix)))
        if node.text is not None:
            dc.DrawText(node.text, node.matrix.value_trans_x(), node.matrix.value_trans_y())

    def draw_image(self, node, dc, draw_mode):
        gc = wx.GraphicsContext.Create(dc)
        gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(node.matrix)))
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
            pil_data = node.image
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
                if isinstance(e, path.Move):
                    self.graphic_path.MoveToPoint(e.end[0], e.end[1])
                elif isinstance(e, path.Line):
                    self.graphic_path.AddLineToPoint(e.end[0], e.end[1])
                elif isinstance(e, path.Close):
                    self.graphic_path.CloseSubpath()
                elif isinstance(e, path.QuadraticBezier):
                    self.graphic_path.AddQuadCurveToPoint(e.control[0], e.control[1],
                                                          e.end[0], e.end[1])
                elif isinstance(e, path.CubicBezier):
                    self.graphic_path.AddCurveToPoint(e.control1[0], e.control1[1],
                                                      e.control2[0], e.control2[1],
                                                      e.end[0], e.end[1])
                elif isinstance(e, path.Arc):
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
