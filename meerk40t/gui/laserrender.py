from copy import copy
from math import ceil, isnan, sqrt

import wx
from PIL import Image

from meerk40t.core.elements.element_types import place_nodes
from meerk40t.core.node.node import Fillrule, Linecap, Linejoin, Node
from meerk40t.svgelements import (
    Arc,
    Close,
    Color,
    CubicBezier,
    Line,
    Matrix,
    Move,
    QuadraticBezier,
)

from ..core.cutcode.cubiccut import CubicCut
from ..core.cutcode.cutcode import CutCode
from ..core.cutcode.dwellcut import DwellCut
from ..core.cutcode.gotocut import GotoCut
from ..core.cutcode.homecut import HomeCut
from ..core.cutcode.inputcut import InputCut
from ..core.cutcode.linecut import LineCut
from ..core.cutcode.outputcut import OutputCut
from ..core.cutcode.plotcut import PlotCut
from ..core.cutcode.quadcut import QuadCut
from ..core.cutcode.rastercut import RasterCut
from ..core.cutcode.waitcut import WaitCut
from ..tools.geomstr import (  # , TYPE_RAMP
    TYPE_ARC,
    TYPE_CUBIC,
    TYPE_LINE,
    TYPE_QUAD,
    Geomstr,
)
from .fonts import wxfont_to_svg
from .icons import icons8_image
from .zmatrix import ZMatrix
from meerk40t.gui.wxutils import get_gc_scale

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
DRAW_MODE_ORIGIN = 0x4000000
DRAW_MODE_EDIT = 0x8000000


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
    if textnode.font_weight is not None:
        try:
            fw = float(textnode.font_weight)
            if fw > 1000:
                textnode.font_weight = 1000
        except ValueError:
            pass
    wxfont = textnode.wxfont
    # if the font_list is empty, then we do have a not properly initialised textnode,
    # that needs to be resolved...
    if textnode.font_family is None:
        wxfont_to_svg(textnode)

    svg_to_wx_family(textnode, wxfont)
    svg_to_wx_fontstyle(textnode, wxfont)
    try:
        wxfont.SetNumericWeight(textnode.weight)  # Gets numeric weight.
    except AttributeError:
        # Running version wx4.0. No set Numeric Weight, can only set bold or normal.
        weight = textnode.weight
        wxfont.SetWeight(
            wx.FONTWEIGHT_BOLD if weight > 600 else wx.FONTWEIGHT_NORMAL
        )  # Gets numeric weight.

    try:
        font_size = float(textnode.font_size)
    except ValueError:
        font_size = 10
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
        self.caches_generated = 0
        self.nodes_rendered = 0
        self.nodes_skipped = 0
        self._visible_area = None
        self.suppress_it = False

    def set_visible_area(self, box):
        self._visible_area = box

    def render_tree(self, node, gc, draw_mode=None, zoomscale=1.0, alpha=255):
        if not self.render_node(
            node, gc, draw_mode=draw_mode, zoomscale=zoomscale, alpha=alpha
        ):
            for c in node.children:
                self.render_tree(
                    c, gc, draw_mode=draw_mode, zoomscale=zoomscale, alpha=alpha
                )

    def render(self, nodes, gc, draw_mode=None, zoomscale=1.0, alpha=255, msg="unknown"):
        """
        Render scene information.

        @param nodes: Node types to render.
        @param gc: graphics context
        @param draw_mode: draw mode flags for rendering
        @param zoomscale: zoomscale at which to render nodes
        @param alpha: render transparency
        @return:
        """
        # gc_win = gc.GetWindow()
        # gc_mat = gc.GetTransform().Get()
        # print (f"Window handle: {gc_win}, matrix: {gc_mat}")
        self.suppress_it = self.context.setting(bool, "supress_non_visible", True)
        self.context.elements.set_start_time(f"renderscene_{msg}")
        self.caches_generated = 0
        self.nodes_rendered = 0
        self.nodes_skipped = 0
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
                    "effect hatch",
                    "effect wobble",
                    "effect warp",
                )
                nodes = [e for e in nodes if e.type not in path_elements]
            if draw_mode & DRAW_MODE_IMAGE:  # Do not draw images.
                nodes = [e for e in nodes if hasattr(e, "as_image")]
            if draw_mode & DRAW_MODE_TEXT:  # Do not draw text.
                nodes = [e for e in nodes if e.type != "elem text"]
            if draw_mode & DRAW_MODE_REGMARKS:  # Do not draw regmarked items.
                nodes = [e for e in nodes if e._parent.type != "branch reg"]
                nodes = [e for e in nodes if e.type not in place_nodes]
        _nodes = list(nodes)
        variable_translation = draw_mode & DRAW_MODE_VARIABLES
        nodecopy = list(_nodes)
        self.validate_text_nodes(nodecopy, variable_translation)

        for node in _nodes:
            if node.type == "reference":
                # Reference nodes should be drawn per-usual, recurse.
                self.render_node(
                    node.node, gc, draw_mode=draw_mode, zoomscale=zoomscale, alpha=alpha
                )
                continue
            self.render_node(
                node, gc, draw_mode=draw_mode, zoomscale=zoomscale, alpha=alpha
            )
        self.context.elements.set_end_time(f"renderscene_{msg}", message=f"Rendered: {self.nodes_rendered}, skipped: {self.nodes_skipped}, caches created: {self.caches_generated}")

    def render_node(self, node, gc, draw_mode=None, zoomscale=1.0, alpha=255):
        """
        Renders the specific node.
        @param node:
        @param gc:
        @param draw_mode:
        @param zoomscale:
        @param alpha:
        @return: True if rendering was done, False if rendering could not be done.
        """
        node_bb = node.bounds if hasattr(node, "bounds") else None
        vis_bb = self._visible_area
        if self.suppress_it and vis_bb is not None and node_bb is not None and (
            node_bb[0] > vis_bb[2] or
            node_bb[1] > vis_bb[3] or
            node_bb[2] < vis_bb[0] or
            node_bb[3] < vis_bb[1] 
        ):
            self.nodes_skipped += 1
            return False
        if hasattr(node, "hidden") and node.hidden:
            self.nodes_skipped += 1
            return False
        if hasattr(node, "is_visible") and not node.is_visible:
            self.nodes_skipped += 1
            return False
        if hasattr(node, "output") and not node.output:
            self.nodes_skipped += 1
            return False
        self.nodes_rendered += 1
        if not hasattr(node, "draw"): # or not hasattr(node, "_make_cache"):
            # No known render method, we must define the function to draw nodes.
            if node.type in (
                "elem path",
                "elem ellipse",
                "elem rect",
                "elem line",
                "elem polyline",
                "effect hatch",
                "effect wobble",
                "effect warp",
            ):
                node.draw = self.draw_vector
                # node._make_cache = self.cache_geomstr
            elif node.type == "elem point":
                node.draw = self.draw_point_node
            elif node.type in place_nodes:
                node.draw = self.draw_placement_node
            elif hasattr(node, "as_image"):
                node.draw = self.draw_image_node
            elif node.type == "elem text":
                node.draw = self.draw_text_node
            elif node.type == "cutcode":
                node.draw = self.draw_cutcode_node
            elif node.type == "group":
                node.draw = self.draw_nothing
            else:
                # print (f"This node has no method: {node.type}")
                return False
        # We have now defined that function, draw it.
        node.draw(node, gc, draw_mode, zoomscale=zoomscale, alpha=alpha)
        if getattr(node, "label_display", False) and node.label:
            # Display label
            col = self.context.root.setting(str, "label_display_color", "#ff0000ff")
            self.display_label(
                node, gc, draw_mode, zoomscale=zoomscale, alpha=alpha, color=col
            )
        return True

    def make_path(self, gc, path):
        """
        Takes a svgelements.Path and converts it to a GraphicsContext.Graphics Path
        """
        p = gc.CreatePath()
        init = False
        for e in path.segments(transformed=True):
            if isinstance(e, Move):
                p.MoveToPoint(e.end[0], e.end[1])
                init = True
            elif isinstance(e, Line):
                if not init:
                    init = True
                    p.MoveToPoint(e.start[0], e.start[1])
                p.AddLineToPoint(e.end[0], e.end[1])
            elif isinstance(e, Close):
                if not init:
                    init = True
                    p.MoveToPoint(e.start[0], e.start[1])
                p.CloseSubpath()
            elif isinstance(e, QuadraticBezier):
                if not init:
                    init = True
                    p.MoveToPoint(e.start[0], e.start[1])
                p.AddQuadCurveToPoint(e.control[0], e.control[1], e.end[0], e.end[1])
            elif isinstance(e, CubicBezier):
                if not init:
                    init = True
                    p.MoveToPoint(e.start[0], e.start[1])
                p.AddCurveToPoint(
                    e.control1[0],
                    e.control1[1],
                    e.control2[0],
                    e.control2[1],
                    e.end[0],
                    e.end[1],
                )
            elif isinstance(e, Arc):
                if not init:
                    init = True
                    p.MoveToPoint(e.start[0], e.start[1])
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

    def make_geomstr(self, gc, path, node=None, settings=None):
        """
        Takes a Geomstr path and converts it to a GraphicsContext.Graphics path

        This also creates a point list of the relevant nodes and creates a ._cache_edit value to be used by node
        editing view.
        """
        p = gc.CreatePath()
        pts = list()
        for subpath in path.as_subpaths():
            if len(subpath) == 0:
                continue
            end = None
            for e in subpath.segments:
                seg_type = int(e[2].real)
                if settings is not None and settings != int(e[2].imag):
                    continue
                start = e[0]
                if end != start:
                    # Start point does not equal previous end point.
                    p.MoveToPoint(start.real, start.imag)
                c0 = e[1]
                c1 = e[3]
                end = e[4]

                if seg_type == TYPE_LINE:
                    p.AddLineToPoint(end.real, end.imag)
                    pts.extend((start, end))
                elif seg_type == TYPE_QUAD:
                    p.AddQuadCurveToPoint(c0.real, c0.imag, end.real, end.imag)
                    pts.append(c0)
                    pts.extend((start, end))
                elif seg_type == TYPE_ARC:
                    radius = Geomstr.arc_radius(None, line=e)
                    center = Geomstr.arc_center(None, line=e)
                    start_t = Geomstr.angle(None, center, start)
                    end_t = Geomstr.angle(None, center, end)
                    p.AddArc(
                        center.real,
                        center.imag,
                        radius,
                        start_t,
                        end_t,
                        clockwise=Geomstr.orientation(None, start, c0, end) != "ccw",
                    )
                    pts.append(c0)
                    pts.extend((start, end))
                elif seg_type == TYPE_CUBIC:
                    p.AddCurveToPoint(
                        c0.real, c0.imag, c1.real, c1.imag, end.real, end.imag
                    )
                    pts.extend((c0, c1, start, end))
                else:
                    print(f"Unknown seg_type: {seg_type}")
            if subpath.first_point == end:
                p.CloseSubpath()
        if node is not None:
            graphics_path_2 = gc.CreatePath()
            for pt in pts:
                graphics_path_2.AddCircle(pt.real, pt.imag, 5000)
            node._cache_edit = graphics_path_2

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
        if not hasattr(node, "linejoin"):
            self.pen.SetJoin(wx.JOIN_BEVEL)
        elif node.linejoin is None:
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
        if node.fillrule == Fillrule.FILLRULE_EVENODD:
            return wx.ODDEVEN_RULE
        else:
            return wx.WINDING_RULE

    @staticmethod
    def _penwidth(pen, width):
        try:
            if isnan(width):
                width = 1.0
            try:
                pen.SetWidth(width)
            except TypeError:
                pen.SetWidth(int(width))
        except OverflowError:
            pass  # Exceeds 32 bit signed integer.

    def _set_penwidth(self, width):
        self._penwidth(self.pen, width)

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

    def draw_nothing(
        self,
        node: Node,
        gc: wx.GraphicsContext,
        draw_mode,
        zoomscale=1.0,
        alpha=255,
        x: int = 0,
        y: int = 0,
    ):
        # We don't do anything, just a placeholder
        return

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
        self,
        cutcode: CutCode,
        gc: wx.GraphicsContext,
        x: int = 0, y: int = 0,
        raster_as_image: bool = True,
        residual = None,
        laserspot_width = None,
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

        def establish_linewidth(scale, spot_width):
            default_pix = 1 / scale
            # print (gcscale, laserspot_width, 1/gcscale)
            pixelwidth = spot_width if spot_width is not None else default_pix
            # How many pixels should the laserspotwidth be like,
            # in any case at least 1 pixel, as otherwise it
            # wouldn't show up under Linux/Darwin
            return max(default_pix, pixelwidth)

        def process_cut(cut, p, last_point):

            def process_as_image():
                image = cut.image
                gc.PushState()
                matrix = Matrix.scale(cut.step_x, cut.step_y)
                matrix.post_translate(
                    cut.offset_x + x, cut.offset_y + y
                )  # Adjust image xy
                gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
                _gcscale = get_gc_scale(gc)
                try:
                    cache = cut._cache
                except AttributeError:
                    cache = None
                if cache is None:
                    # No valid cache. Generate.
                    cut._cache_width, cut._cache_height = image.size
                    try:
                        cut._cache = self.make_thumbnail(image, maximum=5000)
                    except (MemoryError, RuntimeError):
                        cut._cache = None
                    cut._cache_id = id(image)
                if cut._cache is not None:
                    # Cache exists and is valid.
                    gc.DrawBitmap(cut._cache, 0, 0, cut._cache_width, cut._cache_height)
                    if cut.highlighted:
                        # gc.SetBrush(wx.RED_BRUSH)
                        self._penwidth(highlight_pen, 3 / gcscale)
                        gc.SetPen(highlight_pen)
                        gc.DrawRectangle(0, 0, cut._cache_width, cut._cache_height)
                else:
                    # Image was too large to cache, draw a red rectangle instead.
                    gc.SetBrush(wx.RED_BRUSH)
                    gc.DrawRectangle(0, 0, cut._cache_width, cut._cache_height)
                    gc.DrawBitmap(
                        icons8_image.GetBitmap(),
                        0,
                        0,
                        cut._cache_width,
                        cut._cache_height,
                    )
                gc.PopState()

            def process_as_raster():
                try:
                    cache = cut._plotcache
                except AttributeError:
                    cache = None
                if cache is None:
                    process_as_image()
                    return
                p.MoveToPoint(start[0] + x, start[1] + y)
                todraw = cache
                if residual is None:
                    maxcount = -1
                else:
                    maxcount = int(len(todraw) * residual)
                count = 0
                for px, py, pon in todraw:
                    if px is None or py is None:
                        # Passthrough
                        continue
                    if pon == 0:
                        p.MoveToPoint(px + x, py + y)
                    else:
                        p.AddLineToPoint(px + x, py + y)
                    count += 1
                    if 0 < maxcount < count:
                        break

            def process_as_plot():
                p.MoveToPoint(start[0] + x, start[1] + y)
                try:
                    cache = cut._plotcache
                except AttributeError:
                    cache = None
                if cache is None:
                    return
                todraw = cache
                if residual is None:
                    maxcount = -1
                else:
                    maxcount = int(len(todraw) * residual)
                count = 0
                for ox, oy, pon, px, py in todraw:
                    if pon == 0:
                        p.MoveToPoint(px + x, py + y)
                    else:
                        p.AddLineToPoint(px + x, py + y)
                    count += 1
                    if 0 < maxcount < count:
                        break

            start = cut.start
            end = cut.end
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
                if raster_as_image:
                    process_as_image()
                else:
                    process_as_raster()

            elif isinstance(cut, PlotCut):
                process_as_plot()
            elif isinstance(cut, DwellCut):
                pass
            elif isinstance(cut, WaitCut):
                pass
            elif isinstance(cut, HomeCut):
                p.MoveToPoint(0, 0)
            elif isinstance(cut, GotoCut):
                p.MoveToPoint(start[0] + x, start[1] + y)
            elif isinstance(cut, InputCut):
                pass
            elif isinstance(cut, OutputCut):
                pass
            return end

        gcscale = get_gc_scale(gc)
        pixelwidth = establish_linewidth(gcscale, laserspot_width)
        defaultwidth = 1 / gcscale
        if defaultwidth > 0.25 * pixelwidth:
            defaultwidth = 0
        # print (f"Scale: {gcscale} - {mat_param}")
        highlight_color = Color("magenta")
        wx_color = wx.Colour(swizzlecolor(highlight_color))
        highlight_pen = wx.Pen(wx_color)
        highlight_pen.SetStyle(wx.PENSTYLE_SHORT_DASH)
        p = None
        last_point = None
        color = None
        for cut in cutcode:
            if hasattr(cut, "visible") and getattr(cut, "visible") is False:
                continue
            c = highlight_color if cut.highlighted else cut.color
            if c is None:
                c = 0
            try:
                if c.value is None:
                    c = 0
            except AttributeError:
                pass
            if c is not color:
                if p is not None:
                    gc.StrokePath(p)
                    if defaultwidth:
                        self._penwidth(self.pen, defaultwidth)
                        self.set_pen(gc, color, 192)
                        gc.StrokePath(p)
                    del p
                color = c
                last_point = None
                p = gc.CreatePath()
                self._penwidth(self.pen, pixelwidth)
                alphavalue = 192 if laserspot_width is None else 64
                self.set_pen(gc, c, alpha=alphavalue)
            if p is None:
                p = gc.CreatePath()
            last_point = process_cut(cut, p, last_point)
        if p is not None:
            gc.StrokePath(p)
            if defaultwidth:
                self._penwidth(self.pen, defaultwidth)
                self.set_pen(gc, c, 192)
                gc.StrokePath(p)
            del p

    def cache_geomstr(self, node, gc):
        self.caches_generated += 1

        try:
            matrix = node.matrix
            node._cache_matrix = copy(matrix)
        except AttributeError:
            node._cache_matrix = Matrix()
        if hasattr(node, "final_geometry"):
            geom = node.final_geometry()
        else:
            geom = node.as_geometry()
        cache = self.make_geomstr(gc, geom, node=node)
        node._cache = cache

    def draw_vector(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """
        Draw routine for vector objects.

        Vector objects are expected to have a _make_cache routine which attaches a `_cache_matrix` and a `_cache`
        attribute to them which can be drawn as a GraphicsPath.
        """
        if hasattr(node, "mktext"):
            newtext = self.context.elements.wordlist_translate(
                node.mktext, elemnode=node, increment=False
            )
            oldtext = getattr(node, "_translated_text", "")
            if newtext != oldtext:
                node._translated_text = newtext
                kernel = self.context.elements.kernel
                for property_op in kernel.lookup_all("path_updater/.*"):
                    property_op(kernel.root, node)
                if hasattr(node, "_cache"):
                    node._cache = None
        try:
            matrix = node.matrix
        except AttributeError:
            matrix = Matrix()
        gc.PushState()
        try:
            cache = node._cache
        except AttributeError:
            cache = None
        if cache is None:
            self.cache_geomstr(node, gc)

        try:
            cache_matrix = node._cache_matrix
        except AttributeError:
            cache_matrix = None

        stroke_factor = 1
        if matrix != cache_matrix and cache_matrix is not None:
            # Calculate the relative change matrix and apply it to this shape.
            q = ~cache_matrix * matrix
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(q)))
            # Applying the matrix will scale our stroke, so we scale the stroke back down.
            stroke_factor = 1.0 if q.determinant == 0 else 1.0 / sqrt(abs(q.determinant))
        self._set_linecap_by_node(node)
        self._set_linejoin_by_node(node)
        sw = node.implied_stroke_width * stroke_factor
        if draw_mode & DRAW_MODE_LINEWIDTH:
            # No stroke rendering.
            sw = 1000
        self._set_penwidth(sw)
        self.set_pen(
            gc,
            node.stroke,
            alpha=alpha,
        )
        self.set_brush(gc, node.fill, alpha=alpha)
        if draw_mode & DRAW_MODE_FILLS == 0 and node.fill is not None:
            gc.FillPath(node._cache, fillStyle=self._get_fillstyle(node))
        if draw_mode & DRAW_MODE_STROKES == 0 and node.stroke is not None:
            gc.StrokePath(node._cache)

        if node.emphasized and draw_mode & DRAW_MODE_EDIT:
            try:
                edit = node._cache_edit
                gc.StrokePath(edit)
            except AttributeError:
                pass
        gc.PopState()

    def draw_placement_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """Default draw routine for the placement operation."""
        if node.type == "place current":
            # no idea how to draw yet...
            return
        gc.PushState()
        matrix = Matrix()
        if node.rotation is not None and node.rotation != 0:
            matrix.post_rotate(node.rotation, node.x, node.y)
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        # First x
        dif = 20 * zoomscale
        x_from = node.x
        y_from = node.y
        if node.corner == 0:
            # Top Left
            x_to = x_from + dif
            y_to = y_from + dif
            x_sign = 1
            y_sign = 1
        elif node.corner == 1:
            # Top Right
            x_to = x_from - dif
            y_to = y_from + dif
            x_sign = -1
            y_sign = 1
        elif node.corner == 2:
            # Bottom Right
            x_to = x_from - dif
            y_to = y_from - dif
            x_sign = -1
            y_sign = -1
        elif node.corner == 3:
            # Bottom Left
            x_to = x_from + dif
            y_to = y_from - dif
            x_sign = 1
            y_sign = -1
        else:
            # Center
            x_from -= dif
            y_from -= dif
            x_to = x_from + 2 * dif
            y_to = y_from + 2 * dif
            x_sign = 1
            y_sign = 1
        width = 1.0 * zoomscale
        rpen = wx.Pen(wx.Colour(red=255, green=0, blue=0, alpha=alpha))
        self._penwidth(rpen, width)

        gpen = wx.Pen(wx.Colour(red=0, green=255, blue=0, alpha=alpha))
        self._penwidth(gpen, width)
        gc.SetPen(rpen)
        dif = 5 * zoomscale
        gc.StrokeLine(x_from, node.y, x_to, node.y)
        gc.StrokeLine(x_to - x_sign * dif, node.y - y_sign * dif, x_to, node.y)
        gc.StrokeLine(x_to - x_sign * dif, node.y + y_sign * dif, x_to, node.y)
        gc.SetPen(gpen)
        gc.StrokeLine(node.x, y_from, node.x, y_to)
        gc.StrokeLine(node.x - x_sign * dif, y_to - y_sign * dif, node.x, y_to)
        gc.StrokeLine(node.x + x_sign * dif, y_to - y_sign * dif, node.x, y_to)

        loops = 1
        if hasattr(node, "loops") and node.loops is not None:
            # No zero or negative values please
            try:
                loops = int(node.loops)
            except ValueError:
                loops = 1
            if loops < 1:
                loops = 1
        if loops > 1:
            symbol = f"{loops}x"
            font_size = 10 * zoomscale
            if font_size < 1.0:
                font_size = 1.0
            try:
                font = wx.Font(
                    font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            except TypeError:
                font = wx.Font(
                    int(font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            gc.SetFont(font, wx.Colour(red=255, green=0, blue=0, alpha=alpha))
            (t_width, t_height) = gc.GetTextExtent(symbol)
            x = (x_from + x_to) / 2 - t_width / 2
            y = (y_from + y_to) / 2 - t_height / 2
            # is corner center then shift it a bit more
            if node.corner == 4:
                x += 0.25 * (x_to - x_from)
                y += 0.25 * (y_to - y_from)
            gc.DrawText(symbol, x, y)
        symbol = ""
        if hasattr(node, "nx") and hasattr(node, "ny"):
            nx = node.nx
            if nx is None:
                nx = 1
            ny = node.ny
            if ny is None:
                ny = 1
            if nx != 1 or ny != 1:
                symbol = f"{nx},{ny}"
        if symbol:
            font_size = 10 * zoomscale
            if font_size < 1.0:
                font_size = 1.0
            try:
                font = wx.Font(
                    font_size,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            except TypeError:
                font = wx.Font(
                    int(font_size),
                    wx.FONTFAMILY_SWISS,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                )
            gc.SetFont(font, wx.Colour(red=255, green=0, blue=0, alpha=alpha))
            (t_width, t_height) = gc.GetTextExtent(symbol)
            x = x_from + (x_from - (x_from + x_to) / 2) - t_width / 2
            y = y_from + (y_from - (y_from + y_to) / 2) - t_height / 2
            # is corner center then shift it a bit more
            if node.corner == 4:
                x += 0.75 * abs(x_to - x_from)
                y += 0.75 * abs(y_to - y_from)
            gc.DrawText(symbol, x, y)

        gc.PopState()

    def draw_point_node(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """Default draw routine for the laser path element."""
        if draw_mode & DRAW_MODE_POINTS:
            return
        point = node.point
        gc.PushState()
        mypen = wx.Pen(wx.BLACK)
        try:
            mypen.SetWidth(zoomscale)
        except TypeError:
            mypen.SetWidth(int(zoomscale))
        gc.SetPen(mypen)
        dif = 5 * zoomscale
        gc.StrokeLine(point.x - dif, point.y, point.x + dif, point.y)
        gc.StrokeLine(point.x, point.y - dif, point.x, point.y + dif)
        gc.PopState()

    def display_label(
        self, node, gc, draw_mode=0, zoomscale=1.0, alpha=255, color="#ff0000ff"
    ):
        if node is None:
            return
        if not node.label:
            return
        try:
            bbox = node.bbox_group() if node.type == "group" else node.bbox()
            # print (f"{node.type}: {bbox}")
        except AttributeError:
            # print (f"This node has no bbox: {self.node.type}")
            return
        gc.PushState()
        cx = bbox[0] + 0.5 * (bbox[2] - bbox[0])
        cy = bbox[1] + 0.25 * (bbox[3] - bbox[1])
        symbol = node.display_label()
        font_size = 10 * zoomscale
        if font_size < 1.0:
            font_size = 1.0
        try:
            font = wx.Font(
                font_size,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        except TypeError:
            font = wx.Font(
                int(font_size),
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        c = Color(color)
        gc.SetFont(font, wx.Colour(red=c.red, green=c.green, blue=c.blue, alpha=alpha))
        (t_width, t_height) = gc.GetTextExtent(symbol)
        x = cx - t_width / 2
        y = cy - t_height / 2
        gc.DrawText(symbol, x, y)

        gc.PopState()

    def draw_text_node(self, node, gc, draw_mode=0, zoomscale=1.0, alpha=255):
        if node is None:
            return
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
        #
        # sw = node.implied_stroke_width
        # if draw_mode & DRAW_MODE_LINEWIDTH:
        #     # No stroke rendering.
        #     sw = 1000
        # self._set_penwidth(sw)
        # self.set_pen(
        #     gc,
        #     node.stroke,
        #     alpha=alpha,
        # )
        # self.set_brush(gc, node.fill, alpha=255)

        if node.fill is None or node.fill == "none":
            fill_color = wx.BLACK
        else:
            fill_color = as_wx_color(node.fill)
        gc.SetFont(font, fill_color)

        if draw_mode & DRAW_MODE_VARIABLES:
            # Only if flag show the translated values
            text = self.context.elements.wordlist_translate(
                text, elemnode=node, increment=False
            )
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
        gc.PushState()

        cache = None
        bounds = node.bbox()
        try:
            cache = node._cache
        except AttributeError:
            pass
        if cache is None:
            # We need to establish the cache
            try:
                image = node.active_image
                matrix = node.active_matrix
                bounds = 0, 0, image.width, image.height
                if matrix is not None and not matrix.is_identity():
                    gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
            except AttributeError:
                pass

            try:
                max_allowed = node.max_allowed
            except AttributeError:
                max_allowed = 2048
            try:
                cache = self.make_thumbnail(
                    image,
                    maximum=max_allowed,
                    alphablack=draw_mode & DRAW_MODE_ALPHABLACK == 0,
                )
                node._cache_width, node._cache_height = image.size
                node._cache = cache
            except Exception:
                pass

        min_x, min_y, max_x, max_y = bounds
        gc.DrawBitmap(cache, min_x, min_y, max_x - min_x, max_y - min_y)

        gc.PopState()
        if hasattr(node, "message"):
            txt = node.message
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
        dimension_x = 1000
        dimension_y = 500
        scaling = 1
        bmp = wx.Bitmap(dimension_x, dimension_y, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)

        draw_mode = self.context.draw_mode
        if draw_mode & DRAW_MODE_VARIABLES:
            # Only if flag show the translated values
            text = self.context.elements.wordlist_translate(
                node.text, elemnode=node, increment=False
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
        use_font = node.wxfont
        gc.SetFont(use_font, wx.WHITE)
        f_width, f_height, f_descent, f_external_leading = gc.GetFullTextExtent(text)
        needs_revision = False
        revision_factor = 3
        if revision_factor * f_width >= dimension_x:
            dimension_x = revision_factor * f_width
            needs_revision = True
        if revision_factor * f_height > dimension_y:
            dimension_y = revision_factor * f_height
            needs_revision = True
        if needs_revision:
            # We need to create an independent instance of the font
            # as we may to need to change the font_size temporarily
            fontdesc = node.wxfont.GetNativeFontInfoDesc()
            use_font = wx.Font(fontdesc)
            while True:
                try:
                    fsize = use_font.GetFractionalPointSize()
                except AttributeError:
                    fsize = use_font.GetPointSize()
                # print (f"Revised bounds: {dimension_x} x {dimension_y}, font_size={fsize} (original={fsize_org}")
                if fsize < 100 or dimension_x < 2000 or dimension_y < 1000:
                    break
                # We consume an enormous amount of time and memory to create insanely big
                # temporary canvasses, so we intentionally reduce the resolution and accept
                # smaller deviations...
                scaling *= 10
                fsize /= 10
                dimension_x /= 10
                dimension_y /= 10
                try:
                    use_font.SetFractionalPointSize(fsize)
                except AttributeError:
                    use_font.SetPointSize(int(fsize))

            gc.Destroy()
            dc.SelectObject(wx.NullBitmap)
            dc.Destroy()
            del dc
            bmp = wx.Bitmap(int(dimension_x), int(dimension_y), 32)
            dc = wx.MemoryDC()
            dc.SelectObject(bmp)
            dc.SetBackground(wx.BLACK_BRUSH)
            dc.Clear()
            gc = wx.GraphicsContext.Create(dc)
            gc.SetFont(use_font, wx.WHITE)

        gc.DrawText(text, 0, 0)
        try:
            img = bmp.ConvertToImage()
            buf = img.GetData()
            image = Image.frombuffer(
                "RGB", tuple(bmp.GetSize()), bytes(buf), "raw", "RGB", 0, 1
            )
            node.text_cache = image
            img_bb = image.getbbox()
            if img_bb is None:
                node.raw_bbox = None
            else:
                newbb = (
                    scaling * img_bb[0],
                    scaling * img_bb[1],
                    scaling * img_bb[2],
                    scaling * img_bb[3],
                )
                node.raw_bbox = newbb
        except Exception:
            node.text_cache = None
            node.raw_bbox = None
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
        self.context.elements.set_start_time("validate_text_nodes")
        for item in nodes:
            if item.type == "elem text" and (
                item._bounds_dirty
                or item._paint_bounds_dirty
                or item.bounds_with_variables_translated != translate_variables
            ):
                # We never drew this cleanly; our initial bounds calculations will be off if we don't premeasure
                self.measure_text(item)
                item.set_dirty_bounds()
                dummy = item.bounds
        self.context.elements.set_end_time("validate_text_nodes")

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
        nodecopy = list(_nodes)
        self.validate_text_nodes(nodecopy, variable_translation)

        for item in _nodes:
            # bb = item.bounds
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
        self.render(_nodes, gc, draw_mode=DRAW_MODE_CACHE | DRAW_MODE_VARIABLES, msg="make_raster")
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
        return bmp if bitmap else image

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
