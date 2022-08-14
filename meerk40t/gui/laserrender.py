import platform
from math import ceil, floor, sqrt, isnan

import wx
from PIL import Image

from meerk40t.core.cutcode import (
    CubicCut,
    CutCode,
    DwellCut,
    InputCut,
    LineCut,
    OutputCut,
    PlotCut,
    QuadCut,
    RasterCut,
    RawCut,
    WaitCut,
)
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.gui.fonts import svgfont_to_wx
from meerk40t.svgelements import (
    Arc,
    Close,
    Color,
    CubicBezier,
    Line,
    Matrix,
    Move,
    Path,
    QuadraticBezier,
)

from ..numpath import TYPE_CUBIC, TYPE_LINE, TYPE_QUAD, TYPE_RAMP
from .icons import icons8_image_50
from .zmatrix import ZMatrix

DRAW_MODE_FILLS = 0x000001
DRAW_MODE_GUIDES = 0x000002
DRAW_MODE_GRID = 0x000004
DRAW_MODE_LASERPATH = 0x000008
DRAW_MODE_RETICLE = 0x000010
DRAW_MODE_SELECTION = 0x000020
DRAW_MODE_STROKES = 0x000040
DRAW_MODE_CACHE = 0x000080  # Set means do not cache.
DRAW_MODE_REFRESH = 0x000100
DRAW_MODE_ANIMATE = 0x000200
DRAW_MODE_PATH = 0x000400
DRAW_MODE_IMAGE = 0x000800
DRAW_MODE_TEXT = 0x001000
DRAW_MODE_BACKGROUND = 0x002000
DRAW_MODE_POINTS = 0x004000
DRAW_MODE_REGMARKS = 0x008000
DRAW_MODE_VARIABLES = 0x010000

DRAW_MODE_ICONS = 0x0040000
DRAW_MODE_INVERT = 0x400000
DRAW_MODE_FLIPXY = 0x800000
DRAW_MODE_LINEWIDTH = 0x1000000
DRAW_MODE_ALPHABLACK = 0x2000000  # Set means do not alphablack images


def swizzlecolor(c):
    if c is None:
        return None
    if isinstance(c, int):
        c = Color(argb=c)
    try:
        return c.blue << 16 | c.green << 8 | c.red
    except (ValueError, TypeError):
        return None


class LaserRender:
    """
    Laser Render provides GUI relevant methods of displaying the given elements.
    """

    def __init__(self, context):
        self.context = context
        self.pen = wx.Pen()
        self.brush = wx.Brush()
        self.color = wx.Colour()
        (
            self.fontdescent_factor,
            self.fontdescent_delta,
        ) = self._calc_font_descent_by_os()

    def _calc_font_descent_by_os(self):
        system = platform.system()
        if system == "Darwin":
            # to be verified
            return 2.0, 0.5
        elif system == "Windows":
            return 2.0, 0.5
        elif system == "Linux":
            # Don't ask me why it's not 2.0...
            # Might be just my GTK...
            return 1.75, 0.45
        else:
            return 2.0, 0.5

    def render(self, nodes, gc, draw_mode=None, zoomscale=1.0, alpha=255):
        """
        Render scene information.

        @param nodes: Node types to render.
        @param gc: graphics context
        @param draw_mode: draw_mode set
        @param zoomscale: set zoomscale at which this is drawn at
        @return:
        """
        if draw_mode is None:
            draw_mode = self.context.draw_mode

        if draw_mode & (DRAW_MODE_TEXT | DRAW_MODE_IMAGE | DRAW_MODE_PATH) != 0:
            if draw_mode & DRAW_MODE_PATH:  # Do not draw paths.
                nodes = [e for e in nodes if e.type != "elem path"]
            if draw_mode & DRAW_MODE_IMAGE:  # Do not draw images.
                nodes = [e for e in nodes if e.type != "elem image"]
            if draw_mode & DRAW_MODE_TEXT:  # Do not draw text.
                nodes = [e for e in nodes if e.type != "elem text"]
            if draw_mode & DRAW_MODE_REGMARKS:  # Do not draw regmarked items.
                nodes = [e for e in nodes if e._parent.type != "branch reg"]

        for node in nodes:
            if node.type == "reference":
                self.render(
                    [node.node],
                    gc,
                    draw_mode=draw_mode,
                    zoomscale=zoomscale,
                    alpha=alpha,
                )
                continue

            try:
                node.draw(node, gc, draw_mode, zoomscale=zoomscale, alpha=alpha)
            except AttributeError:
                if node.type == "elem path":
                    node.draw = self.draw_path_node
                elif node.type == "elem numpath":
                    node.draw = self.draw_numpath_node
                elif node.type == "elem point":
                    node.draw = self.draw_point_node
                elif node.type in (
                    "elem rect",
                    "elem line",
                    "elem polyline",
                    "elem ellipse",
                ):
                    node.draw = self.draw_shape_node
                elif node.type == "elem image":
                    node.draw = self.draw_image_node
                elif node.type == "elem text":
                    node.draw = self.draw_text_node
                elif node.type == "cutcode":
                    node.draw = self.draw_cutcode_node
                else:
                    continue
                node.draw(node, gc, draw_mode, zoomscale=zoomscale, alpha=alpha)

    def make_path(self, gc, path):
        """
        Takes a svgelements.Path and converts it to a GraphicsContext.Graphics Path
        """
        p = gc.CreatePath()
        first_point = path.first_point
        if first_point is not None:
            p.MoveToPoint(first_point[0], first_point[1])
        for e in path:
            if isinstance(e, Move):
                p.MoveToPoint(e.end[0], e.end[1])
            elif isinstance(e, Line):
                p.AddLineToPoint(e.end[0], e.end[1])
            elif isinstance(e, Close):
                p.CloseSubpath()
            elif isinstance(e, QuadraticBezier):
                p.AddQuadCurveToPoint(e.control[0], e.control[1], e.end[0], e.end[1])
            elif isinstance(e, CubicBezier):
                p.AddCurveToPoint(
                    e.control1[0],
                    e.control1[1],
                    e.control2[0],
                    e.control2[1],
                    e.end[0],
                    e.end[1],
                )
            elif isinstance(e, Arc):
                for curve in e.as_cubic_curves():
                    p.AddCurveToPoint(
                        curve.control1[0],
                        curve.control1[1],
                        curve.control2[0],
                        curve.control2[1],
                        curve.end[0],
                        curve.end[1],
                    )
        return p

    def make_numpath(self, gc, path):
        """
        Takes a svgelements.Path and converts it to a GraphicsContext.Graphics Path
        """
        p = gc.CreatePath()
        for subpath in path.as_subpaths():
            if len(subpath) == 0:
                continue
            end = None
            for e in subpath.segments:
                seg_type = int(e[2].real)
                start = e[0]
                if end != start:
                    # Start point does not equal previous end point.
                    p.MoveToPoint(start.real, start.imag)
                c0 = e[1]
                c1 = e[3]
                end = e[4]

                if seg_type in (TYPE_LINE, TYPE_RAMP):
                    p.AddLineToPoint(end.real, end.imag)
                elif seg_type == TYPE_QUAD:
                    p.AddQuadCurveToPoint(c0.real, c0.imag, end.real, end.imag)
                elif seg_type == TYPE_CUBIC:
                    p.AddCurveToPoint(
                        c0.real, c0.imag, c1.real, c1.imag, end.real, end.imag
                    )
                else:
                    print(seg_type)
            if subpath.first_point == end:
                p.CloseSubpath()

        return p

    def _set_linecap_by_node(self, node):
        if not hasattr(node, "linecap") or node.linecap is None:
            self.pen.SetCap(wx.CAP_ROUND)
        else:
            if node.linecap == Linecap.CAP_BUTT:

                self.pen.SetCap(wx.CAP_BUTT)
            elif node.linecap == Linecap.CAP_ROUND:
                self.pen.SetCap(wx.CAP_ROUND)
            elif node.linecap == Linecap.CAP_SQUARE:
                self.pen.SetCap(wx.CAP_PROJECTING)
            else:
                self.pen.SetCap(wx.CAP_ROUND)

    def _set_linejoin_by_node(self, node):
        if not hasattr(node, "linejoin") or node.linejoin is None:
            self.pen.SetJoin(wx.JOIN_MITER)
        else:
            if node.linejoin == Linejoin.JOIN_ARCS:
                self.pen.SetJoin(wx.JOIN_ROUND)
            elif node.linejoin == Linejoin.JOIN_BEVEL:
                self.pen.SetJoin(wx.JOIN_BEVEL)
            elif node.linejoin == Linejoin.JOIN_MITER:
                self.pen.SetJoin(wx.JOIN_MITER)
            elif node.linejoin == Linejoin.JOIN_MITER_CLIP:
                self.pen.SetJoin(wx.JOIN_MITER)
            else:
                self.pen.SetJoin(wx.JOIN_ROUND)

    def _get_fillstyle(self, node):
        if not hasattr(node, "fillrule") or node.fillrule is None:
            return wx.WINDING_RULE
        else:
            if node.fillrule == Fillrule.FILLRULE_EVENODD:
                return wx.ODDEVEN_RULE
            else:
                return wx.WINDING_RULE

    def _set_penwidth(self, width):
        try:
            if isnan(width):
                width = 1.0
            try:
                self.pen.SetWidth(width)
            except TypeError:
                self.pen.SetWidth(int(width))
        except OverflowError:
            pass  # Exceeds 32 bit signed integer.

    def set_pen(self, gc, stroke, alpha=None):
        c = stroke
        if c is not None and c != "none":
            swizzle_color = swizzlecolor(c)
            if alpha is None:
                alpha = c.alpha
            self.color.SetRGBA(swizzle_color | alpha << 24)  # wx has BBGGRR
            self.pen.SetColour(self.color)
            gc.SetPen(self.pen)
        else:
            gc.SetPen(wx.TRANSPARENT_PEN)

    def set_brush(self, gc, fill, alpha=None):
        c = fill
        if c is not None and c != "none":
            swizzle_color = swizzlecolor(c)
            if alpha is None:
                alpha = c.alpha
            self.color.SetRGBA(swizzle_color | alpha << 24)  # wx has BBGGRR
            self.brush.SetColour(self.color)
            gc.SetBrush(self.brush)
        else:
            gc.SetBrush(wx.TRANSPARENT_BRUSH)

    def draw_cutcode_node(
        self,
        node: Node,
        gc: wx.GraphicsContext,
        draw_mode,
        zoomscale=1.0,
        alpha=255,
        x: int = 0,
        y: int = 0,
    ):
        cutcode = node.cutcode
        self.draw_cutcode(cutcode, gc, x, y)

    def draw_cutcode(
        self, cutcode: CutCode, gc: wx.GraphicsContext, x: int = 0, y: int = 0
    ):
        """
        Draw cutcode object into wxPython graphics code.

        This code accepts x,y offset values. The cutcode laser offset can be set with a
        command with the rest of the cutcode remaining the same. So drawing the cutcode
        requires knowing what, if any offset is currently being applied.

        @param cutcode: flat cutcode object to draw.
        @param gc: wx.graphics context
        @param x: offset in x direction
        @param y: offset in y direction
        @return:
        """
        p = None
        last_point = None
        color = None
        for cut in cutcode:
            c = cut.line_color
            if c is not color:
                color = c
                last_point = None
                if p is not None:
                    gc.StrokePath(p)
                    del p
                p = gc.CreatePath()
                self._set_penwidth(7.0)
                self.set_pen(gc, c, alpha=127)
            start = cut.start
            end = cut.end
            if p is None:
                p = gc.CreatePath()
            if last_point != start:
                p.MoveToPoint(start[0] + x, start[1] + y)
            if isinstance(cut, LineCut):
                # Standard line cut. Applies to path object.
                p.AddLineToPoint(end[0] + x, end[1] + y)
            elif isinstance(cut, QuadCut):
                # Standard quadratic bezier cut
                p.AddQuadCurveToPoint(
                    cut.c()[0] + x, cut.c()[1] + y, end[0] + x, end[1] + y
                )
            elif isinstance(cut, CubicCut):
                # Standard cubic bezier cut
                p.AddCurveToPoint(
                    cut.c1()[0] + x,
                    cut.c1()[1] + y,
                    cut.c2()[0] + x,
                    cut.c2()[1] + y,
                    end[0] + x,
                    end[1] + y,
                )
            elif isinstance(cut, RasterCut):
                # Rastercut object.
                image = cut.image
                gc.PushState()
                matrix = Matrix.scale(cut.step_x, cut.step_y)
                matrix.post_translate(
                    cut.offset_x + x, cut.offset_y + y
                )  # Adjust image xy
                gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
                try:
                    cache = cut.cache
                    cache_id = cut.cache_id
                except AttributeError:
                    cache = None
                    cache_id = -1
                if cache_id != id(image):
                    # Cached image is invalid.
                    cache = None
                if cache is None:
                    # No valid cache. Generate.
                    cut.c_width, cut.c_height = image.size
                    try:
                        cut.cache = self.make_thumbnail(image, maximum=5000)
                    except (MemoryError, RuntimeError):
                        cut.cache = None
                    cut.cache_id = id(image)
                if cut.cache is not None:
                    # Cache exists and is valid.
                    gc.DrawBitmap(cut.cache, 0, 0, cut.c_width, cut.c_height)
                else:
                    # Image was too large to cache, draw a red rectangle instead.
                    gc.SetBrush(wx.RED_BRUSH)
                    gc.DrawRectangle(0, 0, cut.c_width, cut.c_height)
                    gc.DrawBitmap(
                        icons8_image_50.GetBitmap(), 0, 0, cut.c_width, cut.c_height
                    )
                gc.PopState()
            elif isinstance(cut, RawCut):
                pass
            elif isinstance(cut, PlotCut):
                p.MoveToPoint(start[0] + x, start[1] + y)
                for px, py, pon in cut.plot:
                    if pon == 0:
                        p.MoveToPoint(px + x, py + y)
                    else:
                        p.AddLineToPoint(px + x, py + y)
            elif isinstance(cut, DwellCut):
                pass
            elif isinstance(cut, WaitCut):
                pass
            elif isinstance(cut, InputCut):
                pass
            elif isinstance(cut, OutputCut):
                pass
            last_point = end
        if p is not None:
            gc.StrokePath(p)
            del p

    def draw_shape_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """Default draw routine for the shape element."""
        try:
            matrix = node.matrix
        except AttributeError:
            matrix = None
        if not hasattr(node, "cache") or node.cache is None:
            cache = self.make_path(gc, Path(node.shape))
            node.cache = cache
        self._set_linecap_by_node(node)
        self._set_linejoin_by_node(node)

        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if draw_mode & DRAW_MODE_LINEWIDTH:
            self._set_penwidth(1000)
        else:
            self._set_penwidth(node.implied_stroke_width(zoomscale))
        self.set_pen(
            gc,
            node.stroke,
            alpha=alpha,
        )
        self.set_brush(gc, node.fill, alpha=alpha)
        if draw_mode & DRAW_MODE_FILLS == 0 and node.fill is not None:
            gc.FillPath(node.cache, fillStyle=self._get_fillstyle(node))
        if draw_mode & DRAW_MODE_STROKES == 0 and node.stroke is not None:
            gc.StrokePath(node.cache)
        gc.PopState()

    def draw_path_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """Default draw routine for the laser path element."""
        try:
            matrix = node.matrix
        except AttributeError:
            matrix = None
        if not hasattr(node, "cache") or node.cache is None:
            cache = self.make_path(gc, node.path)
            node.cache = cache
        self._set_linecap_by_node(node)
        self._set_linejoin_by_node(node)

        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if draw_mode & DRAW_MODE_LINEWIDTH:
            self._set_penwidth(1000)
        else:
            self._set_penwidth(node.implied_stroke_width(zoomscale))
        self.set_pen(
            gc,
            node.stroke,
            alpha=alpha,
        )
        self.set_brush(gc, node.fill, alpha=alpha)
        if draw_mode & DRAW_MODE_FILLS == 0 and node.fill is not None:
            gc.FillPath(node.cache, fillStyle=self._get_fillstyle(node))
        if draw_mode & DRAW_MODE_STROKES == 0 and node.stroke is not None:
            gc.StrokePath(node.cache)
        gc.PopState()

    def draw_numpath_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """Default draw routine for the laser path element."""
        try:
            matrix = node.matrix
        except AttributeError:
            matrix = None
        if not hasattr(node, "cache") or node.cache is None:
            cache = self.make_numpath(gc, node.path)
            node.cache = cache
        self._set_linecap_by_node(node)
        self._set_linejoin_by_node(node)

        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if draw_mode & DRAW_MODE_LINEWIDTH:
            self._set_penwidth(1000)
        else:
            self._set_penwidth(node.implied_stroke_width(zoomscale))
        self.set_pen(
            gc,
            node.stroke,
            alpha=alpha,
        )
        self.set_brush(gc, node.fill, alpha=alpha)
        if draw_mode & DRAW_MODE_FILLS == 0 and node.fill is not None:
            gc.FillPath(node.cache, fillStyle=self._get_fillstyle(node))
        if draw_mode & DRAW_MODE_STROKES == 0 and node.stroke is not None:
            gc.StrokePath(node.cache)
        gc.PopState()

    def draw_point_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """Default draw routine for the laser path element."""
        if draw_mode & DRAW_MODE_POINTS:
            return
        point = node.point
        if point is None:
            return
        try:
            matrix = node.matrix
        except AttributeError:
            matrix = None
        if matrix is None:
            return
        gc.PushState()
        gc.SetPen(wx.BLACK_PEN)
        point = matrix.point_in_matrix_space(point)
        node.point = point
        matrix.reset()
        dif = 5 * zoomscale
        gc.StrokeLine(point.x - dif, point.y, point.x + dif, point.y)
        gc.StrokeLine(point.x, point.y - dif, point.x, point.y + dif)
        gc.PopState()

    def draw_text_node(self, node, gc, draw_mode=0, zoomscale=1.0, alpha=255):
        text = node.text
        if text.text is None or text.text == "":
            return

        try:
            matrix = node.matrix
        except AttributeError:
            matrix = None

        svgfont_to_wx(node)
        font = node.wxfont

        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if draw_mode & DRAW_MODE_LINEWIDTH:
            self._set_penwidth(1000)
        else:
            self._set_penwidth(node.implied_stroke_width(zoomscale))
        self.set_pen(
            gc,
            node.stroke,
            alpha=alpha,
        )
        self.set_brush(gc, node.fill, alpha=255)

        if node.fill is None or node.fill == "none":
            gc.SetFont(font, wx.BLACK)
        else:
            gc.SetFont(font, wx.Colour(swizzlecolor(node.fill)))

        x = text.x
        y = text.y
        text_string = text.text
        if draw_mode & DRAW_MODE_VARIABLES:
            # Only if flag show the translated values
            text_string = self.context.elements.mywordlist.translate(text_string)
        if node.texttransform is not None:
            ttf = node.texttransform.lower()
            if ttf == "capitalize":
                text_string = text_string.capitalize()
            elif ttf == "uppercase":
                text_string = text_string.upper()
            if ttf == "lowercase":
                text_string = text_string.lower()
        # There's a fundamental flaw in wxPython to get the right fontsize
        # Both GetTextExtent and GetFullTextextent provide the fontmetric-size
        # as result for the font-height and don't take the real glyphs into account
        # That means that ".", "a", "g" and "T" all have the same height...
        # Consequently, the size is always off... This can be somewhat compensated by taking
        # the descent from the font-metric into account.
        # A 'real' height routine would most probably need to draw the string on an
        # empty canvas and find the first and last dots on a line...
        f_width, f_height, f_descent, f_external_leading = gc.GetFullTextExtent(text_string)

        # That stuff drives my crazy...
        # If you have characters with an underline, like p, y, g, j, q then you need to subtract 1x descent otherwise 2x
        has_underscore = any(
            substring in text_string for substring in ("g", "j", "p", "q", "y", ",", ";")
        )
        delta = self.fontdescent_factor * f_descent
        if has_underscore:
            delta /= 2.0
        delta -= f_external_leading
        f_height -= delta
        text.width = f_width
        text.height = f_height
        y -= text.height + self.fontdescent_factor * self.fontdescent_delta * f_descent

        anchor = "start"
        if hasattr(text, "anchor"):
            if text.anchor is not None:
                anchor = text.anchor
        if anchor == "middle":
            x -= text.width / 2
        elif anchor == "end":
            x -= text.width
        gc.DrawText(text_string, x, y)
        gc.PopState()

    def draw_image_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        image = node.active_image
        matrix = node.active_matrix
        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if node.process_image_failed:
            image_width, image_height = image.size
            gc.SetBrush(wx.RED_BRUSH)
            gc.SetPen(wx.RED_PEN)
            gc.DrawRectangle(0, 0, image_width, image_height)
            gc.DrawBitmap(icons8_image_50.GetBitmap(), 0, 0, image_width, image_height)
        else:
            if draw_mode & DRAW_MODE_CACHE == 0:
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
                    node.c_width, node.c_height = image.size
                    node.cache = self.make_thumbnail(
                        image,
                        maximum=max_allowed,
                        alphablack=draw_mode & DRAW_MODE_ALPHABLACK == 0,
                    )
                gc.DrawBitmap(node.cache, 0, 0, node.c_width, node.c_height)
            else:
                node.c_width, node.c_height = image.size
                try:
                    cache = self.make_thumbnail(
                        image, alphablack=draw_mode & DRAW_MODE_ALPHABLACK == 0
                    )
                    gc.DrawBitmap(cache, 0, 0, node.c_width, node.c_height)
                except MemoryError:
                    pass
        gc.PopState()
        txt = node.text
        if txt is not None:
            gc.PushState()
            gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(None)))
            font = wx.Font()
            font.SetFractionalPointSize(20)
            gc.SetFont(font, wx.BLACK)
            gc.DrawText(txt, 30, 30)
            gc.PopState()

    def make_raster(
        self,
        nodes,
        bounds,
        width=None,
        height=None,
        bitmap=False,
        step_x=1,
        step_y=1,
        keep_ratio=False,
        recursion=0,
    ):
        """
        Make Raster turns an iterable of elements and a bounds into an image of the designated size, taking into account
        the step size. The physical pixels in the image is reduced by the step size then the matrix for the element is
        scaled up by the same amount. This makes step size work like inverse dpi and correctly sets the image scale to
        the step scale for 1:1 sizes independent of the scale.

        This function requires both wxPython and Pillow.

        @param nodes: elements to render.
        @param bounds: bounds of those elements for the viewport.
        @param width: desired width of the resulting raster
        @param height: desired height of the resulting raster
        @param bitmap: bitmap to use rather than provisioning
        @param step_x: raster step rate, int scale rate of the image.
        @param step_y: raster step rate, int scale rate of the image.
        @param keep_ratio: get a picture with the same height / width
               ratio as the original
        @param recursion: prevent text from happening more than once.
        @return:
        """
        if bounds is None:
            return None
        xxmin = float("inf")
        yymin = float("inf")
        xxmax = -float("inf")
        yymax = -float("inf")
        # print ("Recursion=%d" % recursion)
        if not isinstance(nodes, (tuple, list)):
            mynodes = [nodes]
        else:
            mynodes = nodes
        if recursion == 0:
            # Do it only once...
            textnodes = []
            for item in mynodes:
                if item.type == "elem text":
                    if item.text.width == 0 or item.text.height == 0:
                        textnodes.append(item)
            if len(textnodes) > 0:
                # print ("Invalid textnodes found, call me again...")
                self.make_raster(
                    nodes=textnodes,
                    bounds=bounds,
                    width=width,
                    height=height,
                    bitmap=bitmap,
                    step_x=step_x,
                    step_y=step_y,
                    keep_ratio=keep_ratio,
                    recursion=1,
                )

        for item in mynodes:
            bb = item.bounds
            # if item.type == "elem text":
            #     print ("Bounds for text: %.1f, %.1f, %.1f, %.1f, w=%.1f, h=%.1f)" % (bb[0], bb[1], bb[2], bb[3], item.text.width, item.text.height))
            if bb[0] < xxmin:
                xxmin = bb[0]
            if bb[1] < yymin:
                yymin = bb[1]
            if bb[2] > xxmax:
                xxmax = bb[2]
            if bb[3] > yymax:
                yymax = bb[3]

        xmin = xxmin
        ymin = yymin
        xmax = xxmax
        ymax = yymax
        xmax = ceil(xmax)
        ymax = ceil(ymax)
        xmin = floor(xmin)
        ymin = floor(ymin)
        # print ("Bounds: %.1f, %.1f, %.1f, %.1f, Mine: %.1f, %.1f, %.1f, %.1f)" % (xmin, ymin, xmax, ymax, xxmin, yymin, xxmax, yymax))

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
        # Scale physical image down by step amount.
        width /= float(step_x)
        height /= float(step_y)
        width = int(ceil(abs(width)))
        height = int(ceil(abs(height)))
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        bmp = wx.Bitmap(width, height, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()

        matrix = Matrix()
        matrix.post_translate(-xmin, -ymin)

        # Scale affine matrix up by step amount scaled down.
        scale_x = width / float(image_width)
        scale_y = height / float(image_height)
        if keep_ratio:
            scale_x = min(scale_x, scale_y)
            scale_y = scale_x
        matrix.post_scale(scale_x, scale_y)

        gc = wx.GraphicsContext.Create(dc)
        gc.SetInterpolationQuality(wx.INTERPOLATION_BEST)
        gc.PushState()
        if not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if not isinstance(nodes, (list, tuple)):
            nodes = [nodes]
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawRectangle(xmin - 1, ymin - 1, xmax + 1, ymax + 1)
        self.render(nodes, gc, draw_mode=DRAW_MODE_CACHE | DRAW_MODE_VARIABLES)
        img = bmp.ConvertToImage()
        buf = img.GetData()
        image = Image.frombuffer(
            "RGB", tuple(bmp.GetSize()), bytes(buf), "raw", "RGB", 0, 1
        )
        gc.PopState()
        dc.SelectObject(wx.NullBitmap)
        gc.Destroy()
        del dc
        if bitmap:
            return bmp

        # for item in mynodes:
        #     bb = item.bounds
        #     if item.type == "elem text":
        #         print ("Afterwards Bounds for text: %.1f, %.1f, %.1f, %.1f, w=%.1f, h=%.1f)" % (bb[0], bb[1], bb[2], bb[3], item.text.width, item.text.height))

        return image

    def make_thumbnail(
        self, pil_data, maximum=None, width=None, height=None, alphablack=True
    ):
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
            pil_data = pil_data.resize((width, height))
        else:
            pil_data = pil_data.copy()
        if not alphablack:
            return wx.Bitmap.FromBufferRGBA(
                width, height, pil_data.convert("RGBA").tobytes()
            )
        if "transparency" in pil_data.info:
            pil_data = pil_data.convert("RGBA")
        try:
            # If transparent we paste 0 into the pil_data
            mask = pil_data.getchannel("A").point(lambda e: 255 - e)
            pil_data.paste(mask, None, mask)
        except ValueError:
            pass
        if pil_data.mode != "L":
            pil_data = pil_data.convert("L")
        black = Image.new("RGBA", pil_data.size, "black")
        black.putalpha(pil_data.point(lambda e: 255 - e))
        return wx.Bitmap.FromBufferRGBA(width, height, black.tobytes())
