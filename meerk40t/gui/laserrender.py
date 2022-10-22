import platform
from math import ceil, isnan, sqrt

import wx
from PIL import Image

from meerk40t.core.cutcode import (
    CubicCut,
    CutCode,
    DwellCut,
    GotoCut,
    HomeCut,
    InputCut,
    LineCut,
    OutputCut,
    PlotCut,
    QuadCut,
    RasterCut,
    RawCut,
    SetOriginCut,
    WaitCut,
)
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
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
from .fonts import wxfont_to_svg
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


def as_wx_color(c):
    if c is None:
        return None
    if isinstance(c, int):
        c = Color(argb=c)
    return wx.Colour(red=c.red, green=c.green, blue=c.blue, alpha=c.alpha)


def svgfont_to_wx(textnode):
    """
    Translates all svg-text-properties to their wxfont-equivalents
    @param textnode:
    @return:
    """
    if not hasattr(textnode, "wxfont"):
        textnode.wxfont = wx.Font()
    wxfont = textnode.wxfont

    try:
        wxfont.SetNumericWeight(textnode.weight)  # Gets numeric weight.
    except AttributeError:
        # Running version wx4.0. No set Numeric Weight, can only set bold or normal.
        weight = textnode.weight
        wxfont.SetWeight(
            wx.FONTWEIGHT_BOLD if weight > 600 else wx.FONTWEIGHT_NORMAL
        )  # Gets numeric weight.
    # if the font_list is empty, then we do have a not properly initialised textnode,
    # that needs to be resolved...
    if textnode.font_family is None:
        wxfont_to_svg(textnode)

    svg_to_wx_family(textnode, wxfont)
    svg_to_wx_fontstyle(textnode, wxfont)
    font_size = textnode.font_size
    try:
        wxfont.SetFractionalPointSize(font_size)
    except AttributeError:
        # If we cannot set the fractional point size, we scale up to adjust to fractional levels.
        integer_font_size = int(round(font_size))
        scale = font_size / integer_font_size
        if scale != 1.0:
            textnode.matrix.pre_scale(scale, scale)
            textnode.font_size = integer_font_size
        wxfont.SetPointSize(integer_font_size)
    wxfont.SetUnderlined(textnode.underline)
    wxfont.SetStrikethrough(textnode.strikethrough)


def svg_to_wx_family(textnode, wxfont):
    font_list = textnode.font_list
    # if font_list is None:
    #     print("Fontlist is empty...")
    # else:
    #     print ("Fontlist was: ", font_list)
    for ff in font_list:
        if ff == "fantasy":
            family = wx.FONTFAMILY_DECORATIVE
            wxfont.SetFamily(family)
            return
        elif ff == "serif":
            family = wx.FONTFAMILY_ROMAN
            wxfont.SetFamily(family)
            return
        elif ff == "cursive":
            family = wx.FONTFAMILY_SCRIPT
            wxfont.SetFamily(family)
            return
        elif ff == "sans-serif":
            family = wx.FONTFAMILY_SWISS
            wxfont.SetFamily(family)
            return
        elif ff == "monospace":
            family = wx.FONTFAMILY_TELETYPE
            wxfont.SetFamily(family)
            return
        if wxfont.SetFaceName(ff):
            # We found a correct face name.
            return


def svg_to_wx_fontstyle(textnode, wxfont):
    ff = textnode.font_style
    if ff == "normal":
        fontstyle = wx.FONTSTYLE_NORMAL
    elif ff == "italic":
        fontstyle = wx.FONTSTYLE_ITALIC
    elif ff == "oblique":
        fontstyle = wx.FONTSTYLE_SLANT
    else:
        fontstyle = wx.FONTSTYLE_NORMAL
    wxfont.SetStyle(fontstyle)


class LaserRender:
    """
    Laser Render provides GUI relevant methods of displaying the given elements.
    """

    def __init__(self, context):
        self.context = context
        self.context.setting(int, "draw_mode", 0)
        self.pen = wx.Pen()
        self.brush = wx.Brush()
        self.color = wx.Colour()

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
                path_elements = (
                    "elem ellipse",
                    "elem path",
                    "elem point",
                    "elem polyline",
                    "elem rect",
                    "elem line",
                )
                nodes = [e for e in nodes if e.type not in path_elements]
            if draw_mode & DRAW_MODE_IMAGE:  # Do not draw images.
                nodes = [e for e in nodes if e.type != "elem image"]
            if draw_mode & DRAW_MODE_TEXT:  # Do not draw text.
                nodes = [e for e in nodes if e.type != "elem text"]
            if draw_mode & DRAW_MODE_REGMARKS:  # Do not draw regmarked items.
                nodes = [e for e in nodes if e._parent.type != "branch reg"]
        _nodes = list(nodes)
        variable_translation = draw_mode & DRAW_MODE_VARIABLES
        nodecopy = [e for e in _nodes]
        self.validate_text_nodes(nodecopy, variable_translation)

        for node in _nodes:
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
                    print(f"Unknown seg_type: {seg_type}")
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
            if c is None:
                c = 0
            try:
                if c.value is None:
                    c = 0
            except AttributeError:
                pass
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
                    cut._cache_width, cut._cache_height = image.size
                    try:
                        cut.cache = self.make_thumbnail(image, maximum=5000)
                    except (MemoryError, RuntimeError):
                        cut.cache = None
                    cut.cache_id = id(image)
                if cut.cache is not None:
                    # Cache exists and is valid.
                    gc.DrawBitmap(cut.cache, 0, 0, cut._cache_width, cut._cache_height)
                    # gc.SetBrush(wx.RED_BRUSH)
                    # gc.DrawRectangle(0, 0, cut._cache_width, cut._cache_height)
                else:
                    # Image was too large to cache, draw a red rectangle instead.
                    gc.SetBrush(wx.RED_BRUSH)
                    gc.DrawRectangle(0, 0, cut._cache_width, cut._cache_height)
                    gc.DrawBitmap(
                        icons8_image_50.GetBitmap(),
                        0,
                        0,
                        cut._cache_width,
                        cut._cache_height,
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
            elif isinstance(cut, HomeCut):
                p.MoveToPoint(0, 0)
            elif isinstance(cut, SetOriginCut):
                # This may actually need to set a new draw location for loop cuts
                pass
            elif isinstance(cut, GotoCut):
                p.MoveToPoint(start[0] + x, start[1] + y)
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
            stroke_scale = sqrt(abs(matrix.determinant)) if matrix else 1.0
            self._set_penwidth(1000 / stroke_scale)
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
            stroke_scale = sqrt(abs(matrix.determinant)) if matrix else 1.0
            self._set_penwidth(1000 / stroke_scale)
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
            stroke_scale = sqrt(abs(matrix.determinant)) if matrix else 1.0
            self._set_penwidth(1000 / stroke_scale)
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
        if text is None or text == "":
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
            stroke_scale = sqrt(abs(matrix.determinant)) if matrix else 1.0
            self._set_penwidth(1000 / stroke_scale)
        else:
            self._set_penwidth(node.implied_stroke_width(zoomscale))
        self.set_pen(
            gc,
            node.stroke,
            alpha=alpha,
        )
        self.set_brush(gc, node.fill, alpha=255)

        if node.fill is None or node.fill == "none":
            fill_color = wx.BLACK
        else:
            fill_color = as_wx_color(node.fill)
        gc.SetFont(font, fill_color)

        if draw_mode & DRAW_MODE_VARIABLES:
            # Only if flag show the translated values
            text = self.context.elements.wordlist_translate(text, node)
        if node.texttransform is not None:
            ttf = node.texttransform.lower()
            if ttf == "capitalize":
                text = text.capitalize()
            elif ttf == "uppercase":
                text = text.upper()
            if ttf == "lowercase":
                text = text.lower()
        xmin, ymin, xmax, ymax = node.bbox(transformed=False)
        height = ymax - ymin
        width = xmax - xmin
        dy = 0
        dx = 0
        if node.anchor == "middle":
            dx -= width / 2
        elif node.anchor == "end":
            dx -= width
        gc.DrawText(text, dx, dy)
        gc.PopState()

    def draw_image_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        image = node.active_image
        matrix = node.active_matrix
        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        if node._process_image_failed:
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
                    node._cache_width, node._cache_height = image.size
                    node.cache = self.make_thumbnail(
                        image,
                        maximum=max_allowed,
                        alphablack=draw_mode & DRAW_MODE_ALPHABLACK == 0,
                    )
                gc.DrawBitmap(node.cache, 0, 0, node._cache_width, node._cache_height)
            else:
                node._cache_width, node._cache_height = image.size
                try:
                    cache = self.make_thumbnail(
                        image, alphablack=draw_mode & DRAW_MODE_ALPHABLACK == 0
                    )
                    gc.DrawBitmap(cache, 0, 0, node._cache_width, node._cache_height)
                except MemoryError:
                    pass
        gc.PopState()
        txt = node._processing_message
        if txt is not None:
            gc.PushState()
            gc.SetTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(None)))
            font = wx.Font()
            font.SetPointSize(20)
            gc.SetFont(font, wx.BLACK)
            gc.DrawText(txt, 30, 30)
            gc.PopState()

    def measure_text(self, node):
        """
        Use default measure text routines to calculate height etc.

        Use the real draw of the font to calculate actual size.
        A 'real' height routine needs to draw the string on an
        empty canvas and find the first and last dots on a line...
        We are creating a temporary bitmap and paint on it...

        @param node:
        @return:
        """

        bmp = wx.Bitmap(1000, 500, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        draw_mode = self.context.draw_mode
        if draw_mode & DRAW_MODE_VARIABLES:
            # Only if flag show the translated values
            text = self.context.elements.wordlist_translate(
                node.text, node, increment=False
            )
            node.bounds_with_variables_translated = True
        else:
            text = node.text
            node.bounds_with_variables_translated = False
        if node.texttransform:
            ttf = node.texttransform.lower()
            if ttf == "capitalize":
                text = text.capitalize()
            elif ttf == "uppercase":
                text = text.upper()
            if ttf == "lowercase":
                text = text.lower()
        svgfont_to_wx(node)
        gc.SetFont(node.wxfont, wx.WHITE)
        gc.DrawText(text, 0, 0)
        f_width, f_height, f_descent, f_external_leading = gc.GetFullTextExtent(text)
        try:
            img = bmp.ConvertToImage()
            buf = img.GetData()
            image = Image.frombuffer(
                "RGB", tuple(bmp.GetSize()), bytes(buf), "raw", "RGB", 0, 1
            )
            node.text_cache = image
            node.raw_bbox = image.getbbox()
            if node.raw_bbox is None:
                height = 0
            else:
                height = node.raw_bbox[3] - node.raw_bbox[1] + 1
        except MemoryError:
            node.text_cache = None
            node.raw_bbox = None
            height = f_height
        node.ascent = f_height - f_descent
        if node.baseline != "hanging":
            node.matrix.pre_translate(0, -node.ascent)
            if node.baseline == "middle":
                node.matrix.pre_translate(0, node.ascent / 2)
            node.baseline = "hanging"
        dc.SelectObject(wx.NullBitmap)
        dc.Destroy()
        del dc

    def validate_text_nodes(self, nodes, translate_variables):
        for item in nodes:
            if item.type == "elem text" and (
                item.width is None
                or item.height is None
                or item._bounds_dirty
                or item._paint_bounds_dirty
                or item.bounds_with_variables_translated != translate_variables
            ):
                # We never drew this cleanly; our initial bounds calculations will be off if we don't premeasure
                self.measure_text(item)
                item.set_dirty_bounds()

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
        @param step_x: raster step rate, scale rate of the image.
        @param step_y: raster step rate, scale rate of the image.
        @param keep_ratio: get a picture with the same height / width
               ratio as the original
        @return:
        """
        if bounds is None:
            return None
        x_min = float("inf")
        y_min = float("inf")
        x_max = -float("inf")
        y_max = -float("inf")
        if not isinstance(nodes, (tuple, list)):
            _nodes = [nodes]
        else:
            _nodes = nodes

        # if it's a raster we will always translate text variables...
        variable_translation = True
        nodecopy = [e for e in _nodes]
        self.validate_text_nodes(nodecopy, variable_translation)

        for item in _nodes:
            bb = item.paint_bounds
            if bb is None:
                # Fall back to bounds
                bb = item.bounds
            if bb is None:
                continue
            if bb[0] < x_min:
                x_min = bb[0]
            if bb[1] < y_min:
                y_min = bb[1]
            if bb[2] > x_max:
                x_max = bb[2]
            if bb[3] > y_max:
                y_max = bb[3]
        raster_width = max(x_max - x_min, 1)
        raster_height = max(y_max - y_min, 1)
        if width is None:
            width = raster_width / step_x
        if height is None:
            height = raster_height / step_y
        width = max(width, 1)
        height = max(height, 1)
        bmp = wx.Bitmap(int(ceil(abs(width))), int(ceil(abs(height))), 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()

        matrix = Matrix()

        # Scale affine matrix up by step amount scaled down.
        try:
            scale_x = width / raster_width
        except ZeroDivisionError:
            scale_x = 1

        try:
            scale_y = height / raster_height
        except ZeroDivisionError:
            scale_y = 1
        if keep_ratio:
            scale_x = min(scale_x, scale_y)
            scale_y = scale_x
        matrix.post_translate(-x_min, -y_min)
        matrix.post_scale(scale_x, scale_y)
        if scale_y < 0:
            matrix.pre_translate(0, -raster_height)
        if scale_x < 0:
            matrix.pre_translate(-raster_width, 0)

        gc = wx.GraphicsContext.Create(dc)
        gc.dc = dc
        gc.SetInterpolationQuality(wx.INTERPOLATION_BEST)
        gc.PushState()
        if not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawRectangle(x_min - 1, y_min - 1, x_max + 1, y_max + 1)
        self.render(_nodes, gc, draw_mode=DRAW_MODE_CACHE | DRAW_MODE_VARIABLES)
        img = bmp.ConvertToImage()
        buf = img.GetData()
        image = Image.frombuffer(
            "RGB", tuple(bmp.GetSize()), bytes(buf), "raw", "RGB", 0, 1
        )

        gc.PopState()
        dc.SelectObject(wx.NullBitmap)
        gc.Destroy()
        del gc.dc
        del dc
        if bitmap:
            return bmp
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
