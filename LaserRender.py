import wx
from PIL import Image

from svgelements import *
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
    def __init__(self, device):
        self.device = device
        self.cache = None
        self.pen = wx.Pen()
        self.brush = wx.Brush()
        self.color = wx.Colour()

    def render(self, gc, draw_mode=None):
        """
        Render scene information.

        :param gc:
        :param draw_mode:
        :return:
        """
        if draw_mode is None:
            draw_mode = self.device.draw_mode
        kernel = self.device.device_root
        elements = kernel.elements.elems()
        if draw_mode & 0x1C00 != 0:
            types = []
            if draw_mode & 0x0400 == 0:
                types.append(Path)
            if draw_mode & 0x0800 == 0:
                types.append(SVGImage)
            if draw_mode & 0x1000 == 0:
                types.append(SVGText)
            elements = [e for e in elements if type(e) in types]
        for element in elements:
            try:
                element.draw(element, gc, draw_mode)
            except AttributeError:
                if isinstance(element, Path):
                    element.draw = self.draw_path
                elif isinstance(element, SVGImage):
                    element.draw = self.draw_image
                elif isinstance(element, SVGText):
                    element.draw = self.draw_text
                elif isinstance(element, Group):
                    element.draw = self.draw_group
                else:
                    element.draw = self.draw_path
            element.draw(element, gc, draw_mode)

    def generate_path(self, path):
        # object_path = abs(path)
        plot = path
        first_point = plot.first_point
        if first_point is None:
            return
        yield COMMAND_LASER_OFF
        yield COMMAND_MODE_RAPID
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_MOVE, first_point
        yield COMMAND_PLOT, plot

    def make_path(self, gc, path):
        p = gc.CreatePath()

        parse = LaserCommandPathParser(p)

        for event in self.generate_path(path):
            parse.command(event)
        return p

    def set_pen(self, gc, stroke, width=1.0):
        c = stroke
        if c is not None and c != 'none':
            swizzle_color = swizzlecolor(c)
            self.color.SetRGB(swizzle_color)
            self.pen.SetColour(self.color)
            self.pen.SetWidth(width)
            gc.SetPen(self.pen)
        else:
            gc.SetPen(wx.TRANSPARENT_PEN)

    def set_brush(self, gc, fill):
        c = fill
        if c is not None and c != 'none':
            swizzle_color = swizzlecolor(c)
            self.color.SetRGB(swizzle_color)  # wx has BBGGRR
            self.brush.SetColour(self.color)
            gc.SetBrush(self.brush)
        else:
            gc.SetBrush(wx.TRANSPARENT_BRUSH)

    def draw_group(self, element, gc, draw_mode):
        pass

    def draw_path(self, element, gc, draw_mode):
        """Default draw routine for the laser element.
        If the generate is defined this will draw the
        element as a series of lines, as defined by generate."""
        try:
            matrix = element.transform
        except AttributeError:
            matrix = Matrix()
        drawfills = draw_mode & 1 == 0
        drawstrokes = draw_mode & 64 == 0
        if not hasattr(element, 'cache') or element.cache is None:
            cache = self.make_path(gc, element)
            element.cache = cache
        gc.PushState()
        gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        try:
            sw = Length(element.values['stroke-width']).value(ppi=96.0)
            if sw < 2:
                sw = 2
            self.set_pen(gc, element.stroke, width=sw)
        except KeyError:
            self.set_pen(gc, element.stroke)
        self.set_brush(gc, element.fill)
        if drawfills and element.fill is not None:
            gc.FillPath(element.cache)
        if drawstrokes and element.stroke is not None:
            gc.StrokePath(element.cache)
        gc.PopState()

    def draw_text(self, element, gc, draw_mode):
        try:
            matrix = element.transform
        except AttributeError:
            matrix = Matrix()

        gc.PushState()
        gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if hasattr(element, 'wxfont'):
            font = element.wxfont
        else:
            if element.font_size < 1:
                if element.font_size > 0:
                    element.transform.pre_scale(element.font_size,
                                                element.font_size,
                                                element.x,
                                                element.y)
                element.font_size = 1  # No zero sized fonts.
            font = wx.Font(element.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
            element.wxfont = font
        try:
            sw = Length(element.values['stroke-width']).value(ppi=96.0)
            if sw < 2:
                sw = 2
            self.set_pen(gc, element.stroke, width=sw)
        except KeyError:
            self.set_pen(gc, element.stroke)
        self.set_brush(gc, element.fill)
        if element.fill is None or element.fill == 'none':
            gc.SetFont(font, wx.BLACK)
        else:
            gc.SetFont(font, wx.Colour(swizzlecolor(element.fill)))
        if element.text is not None:
            if not hasattr(element, 'anchor') or element.anchor == 'start':
                element.width, element.height = gc.GetTextExtent(element.text)
                gc.DrawText(element.text, element.x, element.y-element.height)
            elif element.anchor == 'middle':
                element.width, element.height = gc.GetTextExtent(element.text)
                gc.DrawText(element.text, element.x-(element.width/2), element.y-element.height)
            elif element.anchor == 'end':
                element.width, element.height = gc.GetTextExtent(element.text)
                gc.DrawText(element.text, element.x-element.width, element.y-element.height)
        gc.PopState()

    def draw_image(self, node, gc, draw_mode):
        try:
            matrix = node.transform
        except AttributeError:
            matrix = Matrix()
        gc.PushState()
        gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
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
            node.c_width, node.c_height = node.image.size
            node.cache = self.make_thumbnail(node.image, maximum=max_allowed)
        gc.DrawBitmap(node.cache, 0, 0, node.c_width, node.c_height)
        gc.PopState()

    def make_raster(self, elements, bounds, width=None, height=None, bitmap=False, step=1):
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
        if height is None:
            height = image_height
        width /= float(step)
        height /= float(step)
        width = int(width)
        height = int(height)
        bmp = wx.Bitmap(width, height, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if not isinstance(elements, list):
            elements = [elements]

        for element in elements:
            matrix = element.transform
            old_matrix = Matrix(matrix)

            matrix.post_translate(-xmin, -ymin)
            scale_x = width / float(image_width)
            scale_y = height / float(image_height)
            scale = min(scale_x, scale_y)
            matrix.post_scale(scale)
            if isinstance(element, Path):
                p = self.make_path(gc, abs(element))
                self.set_brush(gc, element.fill)
                try:
                    stroke_width = Length(element.values[SVG_ATTR_STROKE_WIDTH]).value()
                except AttributeError:
                    stroke_width = 1.0
                except KeyError:
                    stroke_width = 1.0
                self.set_pen(gc, element.stroke, width=stroke_width * scale)
                gc.FillPath(p)
                gc.StrokePath(p)
                del p
            elif isinstance(element, SVGText):
                #TODO: FINISH THIS
                pass
            element.transform = old_matrix

        img = bmp.ConvertToImage()
        buf = img.GetData()
        image = Image.frombuffer("RGB", tuple(bmp.GetSize()), bytes(buf), "raw", "RGB", 0, 1)
        gc.Destroy()
        del dc
        if bitmap:
            return bmp
        return image

    def make_thumbnail(self, pil_data, maximum=None, width=None, height=None):
        """Resizes the given pil image into wx.Bitmap object that fits the constraints."""
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


class LaserCommandPathParser:
    """This class converts a set of laser commands into a
     graphical representation of those commands."""

    def __init__(self, graphic_path):
        self.graphic_path = graphic_path
        self.enable = True
        self.on = False
        self.relative = False
        self.x = 0
        self.y = 0

    def command(self, event):
        if isinstance(event, int):
            command = event
            values = None
        else:
            command, values = event
        if command == COMMAND_LASER_OFF:
            self.on = False
        elif command == COMMAND_LASER_ON:
            self.on = True
        elif command == COMMAND_LASER_ENABLE:
            self.enable = True
        elif command == COMMAND_LASER_DISABLE:
            self.enable = False
        elif command == COMMAND_SET_ABSOLUTE:
            self.relative = False
        elif command == COMMAND_SET_INCREMENTAL:
            self.relative = True
        elif command == COMMAND_HOME:
            self.graphic_path.MoveToPoint(0, 0)
            self.x = 0
            self.y = 0
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
                self.x, self.y = e.end
        elif command == COMMAND_MOVE:
            x = values[0]
            y = values[1]
            if self.relative:
                x += self.x
                y += self.y
            if self.on and self.enable:
                self.graphic_path.AddLineToPoint(x, y)
            else:
                self.graphic_path.MoveToPoint(x, y)
            self.x = x
            self.y = y
