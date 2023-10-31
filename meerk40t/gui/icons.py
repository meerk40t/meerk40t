import wx
from wx.lib.embeddedimage import PyEmbeddedImage as py_embedded_image

from meerk40t.tools.geomstr import TYPE_ARC, TYPE_CUBIC, TYPE_LINE, TYPE_QUAD, Geomstr

"""
icons serves as a central repository for icons and other assets. These are all processed as PyEmbeddedImages which is
extended from the wx.lib utility of the same name. We allow several additional modifications to these assets. For
example we allow resizing and inverting this allows us to easily reuse the icons and to use the icons for dark themed
guis. We permit rotation of the icons, so as to permit reusing these icons and coloring the icons to match a particular
colored object, for example the icons in the tree for operations using color specific matching.

----
The icons are from Icon8 and typically IOS Glyph, IOS or Windows Metro in style.

https://icons8.com/icons

Find the desired icon and download in 50x50. We use the free license.

Put the icon file in the Pycharm working directory.
Using Local Terminal, with wxPython installed.

img2py -a icons8-icon-name-50.png icons.py

Paste the icon8_icon_name PyEmbeddedImage() block into icons.py
"""

DARKMODE = False

STD_ICON_SIZE = 50

_MIN_ICON_SIZE = 0
_GLOBAL_FACTOR = 1.0


def set_icon_appearance(factor, min_size):
    global _MIN_ICON_SIZE
    global _GLOBAL_FACTOR
    _MIN_ICON_SIZE = min_size
    _GLOBAL_FACTOR = factor


def get_default_icon_size():
    return int(_GLOBAL_FACTOR * STD_ICON_SIZE)


def get_default_scale_factor():
    return _GLOBAL_FACTOR


def write_png(buf, width, height):
    import struct
    import zlib

    width_byte_3 = width * 3
    raw_data = b"".join(
        b"\x00" + buf[span : span + width_byte_3]
        for span in range(0, height * width * 3, width_byte_3)
    )

    def png_pack(png_tag, data):
        chunk_head = png_tag + data
        return (
            struct.pack("!I", len(data))
            + chunk_head
            + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))
        )

    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_pack(b"IHDR", struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0)),
            png_pack(b"IDAT", zlib.compress(raw_data, 9)),
            png_pack(b"IEND", b""),
        ]
    )


class PyEmbeddedImage(py_embedded_image):
    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def message_icon(cls, msg, size=50, color=None, ptsize=48):
        import base64

        _icon_hatch = EmptyIcon(size=size, color=color, ptsize=ptsize, msg=msg)
        bm = _icon_hatch.GetBitmap()
        wxim = bm.ConvertToImage()

        w = wxim.GetWidth()
        h = wxim.GetHeight()
        data = wxim.GetData()

        png_b = write_png(data, width=w, height=h)

        b64 = base64.b64encode(png_b)
        return cls(b64)

    def GetBitmap(
        self,
        use_theme=True,
        resize=None,
        color=None,
        rotate=None,
        noadjustment=False,
        keepalpha=False,
        force_darkmode=False,
    ):
        """
        Assumes greyscale icon black on transparent background using alpha for shading
        Ready for Dark Theme
        If color is provided, the black is changed to this
        If color is close to background, alpha is removed and negative background added
        so, we don't get black icon on black background or white on white background.

        @param use_theme:
        @param resize:
        @param color:
        @param rotate:
        @param noadjustment: Disables size adjustment based on global factor
        @param keepalpha: maintain the alpha from the original asset
        @return:
        """

        def color_distance(color1, color2: str):
            from math import sqrt

            if hasattr(color1, "distance_to"):
                return color1.distance_to(color2)
            # That's wx stuff
            c1 = color1
            coldb = wx.ColourDatabase()
            c2 = coldb.Find(color2.upper())
            if not c2.IsOk():
                return 0
            red_mean = int((c1.red + c2.red) / 2.0)
            r = c1.red - c2.red
            g = c1.green - c2.green
            b = c1.blue - c2.blue
            distance_sq = (
                (((512 + red_mean) * r * r) >> 8)
                + (4 * g * g)
                + (((767 - red_mean) * b * b) >> 8)
            )
            return sqrt(distance_sq)

        image = py_embedded_image.GetImage(self)
        if not noadjustment and _GLOBAL_FACTOR != 1.0:
            oldresize = resize
            wd, ht = image.GetSize()
            if resize is not None:
                if isinstance(resize, int) or isinstance(resize, float):
                    resize *= _GLOBAL_FACTOR
                    if 0 < _MIN_ICON_SIZE < oldresize:
                        if resize < _MIN_ICON_SIZE:
                            resize = _MIN_ICON_SIZE
                elif isinstance(resize, tuple):  # (tuple wd ht)
                    resize = [oldresize[0], oldresize[1]]
                    for i in range(2):
                        resize[i] *= _GLOBAL_FACTOR
                        if 0 < _MIN_ICON_SIZE < oldresize[i]:
                            if resize[i] < _MIN_ICON_SIZE:
                                resize[i] = _MIN_ICON_SIZE
            else:
                resize = [wd, ht]
                oldresize = (wd, ht)
                for i in range(2):
                    resize[i] *= _GLOBAL_FACTOR
                    if 0 < _MIN_ICON_SIZE < oldresize[i]:
                        if resize[i] < _MIN_ICON_SIZE:
                            resize[i] = _MIN_ICON_SIZE
            # print ("Will adjust from %s to %s (was: %s)" % ((wd, ht), resize, oldresize))

        if resize is not None:
            if isinstance(resize, int) or isinstance(resize, float):
                image = image.Scale(int(resize), int(resize))
            else:
                image = image.Scale(int(resize[0]), int(resize[1]))
        if rotate is not None:
            if rotate == 1:
                image = image.Rotate90()
            elif rotate == 2:
                image = image.Rotate180()
            elif rotate == 3:
                image = image.Rotate90(False)
        if (
            color is not None
            and color.red is not None
            and color.green is not None
            and color.blue is not None
        ):
            image.Replace(0, 0, 0, color.red, color.green, color.blue)
            if force_darkmode or (DARKMODE and use_theme):
                dist = color_distance(color, "black")
                reverse = dist <= 200
                black_bg = False
            else:
                dist = color_distance(color, "white")
                reverse = dist <= 200
                black_bg = True
            if reverse and not keepalpha:
                self.RemoveAlpha(image, black_bg=black_bg)
        elif force_darkmode or (DARKMODE and use_theme):
            for x in range(image.GetWidth()):
                for y in range(image.GetHeight()):
                    r = int(255 - image.GetRed(x, y))
                    g = int(255 - image.GetGreen(x, y))
                    b = int(255 - image.GetBlue(x, y))
                    image.SetRGB(x, y, r, g, b)
            # image.Replace(0, 0, 0, 255, 255, 255)
        return wx.Bitmap(image)

    def RemoveAlpha(self, image, black_bg=False):
        if not image.HasAlpha():
            return
        bg_rgb = 0 if black_bg else 255
        for x in range(image.GetWidth()):
            for y in range(image.GetHeight()):
                a = image.GetAlpha(x, y)
                bg = int((255 - a) * bg_rgb / 255)
                r = int(image.GetRed(x, y) * a / 255) + bg
                g = int(image.GetGreen(x, y) * a / 255) + bg
                b = int(image.GetBlue(x, y) * a / 255) + bg
                image.SetRGB(x, y, r, g, b)
                image.SetAlpha(x, y, wx.IMAGE_ALPHA_OPAQUE)
        image.ClearAlpha()


class EmptyIcon:
    def __init__(self, size, color, msg=None, ptsize=None, **args):
        if isinstance(size, (list, tuple)):
            self._size_x = int(size[0])
            self._size_y = int(size[1])
        else:
            self._size_x = int(size)
            self._size_y = int(size)
        if self._size_x <= 0:
            self._size_x = 50
        if self._size_y <= 0:
            self._size_y = 50
        self._color = color
        bmp = self.populate_image(msg, ptsize)
        self._image = bmp.ConvertToImage()
        # self._image = wx.Image(width=size, height=size, clear=True)
        # for x in range(size):
        #     for y in range(size):
        #         self._image.SetRGB(x, y, color.red, color.green, color.blue)

    def populate_image(self, msg=None, ptsize=None):
        imgBit = wx.Bitmap(self._size_x, self._size_y)
        dc = wx.MemoryDC()
        dc.SelectObject(imgBit)
        if self._color is not None:
            brush = wx.Brush(self._color, wx.BRUSHSTYLE_SOLID)
            dc.SetBackground(brush)
        dc.Clear()
        if msg is not None and msg != "":
            # We only take the very first letter for
            pattern = {
                "[red]": wx.RED,
                "[green]": wx.GREEN,
                "[blue]": wx.BLUE,
                "[white]": wx.WHITE,
                "[black]": wx.BLACK,
            }
            txt_color = wx.BLACK
            autocolor = True
            for pat in pattern:
                if msg.startswith(pat):
                    txt_color = pattern[pat]
                    autocolor = False
                    msg = msg[len(pat) :]
            if autocolor and self._color is not None:
                c1 = self._color
                c2 = txt_color
                red_mean = int((c1.red + c2.red) / 2.0)
                r = c1.red - c2.red
                g = c1.green - c2.green
                b = c1.blue - c2.blue
                distance = (
                    (((512 + red_mean) * r * r) >> 8)
                    + (4 * g * g)
                    + (((767 - red_mean) * b * b) >> 8)
                )
                # print(c1.red, c1.blue, c1.green, c1.blue + c1.red)
                if distance < 200 * 200:
                    txt_color = wx.WHITE
            if ptsize is None:
                ptsize = 12
            font = wx.Font(
                ptsize,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
            dc.SetTextForeground(txt_color)
            dc.SetFont(font)
            (t_w, t_h) = dc.GetTextExtent(msg)
            x = (self._size_x - t_w) / 2
            y = (self._size_y - t_h) / 2
            pt = wx.Point(int(x), int(y))
            dc.DrawText(msg, pt)
        # Now release dc
        dc.SelectObject(wx.NullBitmap)
        dc.Destroy()
        return imgBit

    def GetBitmap(
        self,
        use_theme=True,
        resize=None,
        color=None,
        rotate=None,
        noadjustment=False,
        keepalpha=False,
    ):
        """
        Assumes greyscale icon black on transparent background using alpha for shading
        Ready for Dark Theme
        If color is provided, the black is changed to this
        If color is close to background, alpha is removed and negative background added
        so, we don't get black icon on black background or white on white background.

        @param use_theme:
        @param resize:
        @param color:
        @param rotate:
        @param noadjustment: Disables size adjustment based on global factor
        @param keepalpha: maintain the alpha from the original asset
        @return:
        """

        image = self._image
        if not noadjustment and _GLOBAL_FACTOR != 1.0:
            oldresize = resize
            wd, ht = image.GetSize()
            if resize is not None:
                if isinstance(resize, int) or isinstance(resize, float):
                    resize *= _GLOBAL_FACTOR
                    if 0 < _MIN_ICON_SIZE < oldresize:
                        if resize < _MIN_ICON_SIZE:
                            resize = _MIN_ICON_SIZE
                elif isinstance(resize, tuple):  # (tuple wd ht)
                    resize = [oldresize[0], oldresize[1]]
                    for i in range(2):
                        resize[i] *= _GLOBAL_FACTOR
                        if 0 < _MIN_ICON_SIZE < oldresize[i]:
                            if resize[i] < _MIN_ICON_SIZE:
                                resize[i] = _MIN_ICON_SIZE
            else:
                resize = [wd, ht]
                oldresize = (wd, ht)
                for i in range(2):
                    resize[i] *= _GLOBAL_FACTOR
                    if 0 < _MIN_ICON_SIZE < oldresize[i]:
                        if resize[i] < _MIN_ICON_SIZE:
                            resize[i] = _MIN_ICON_SIZE
            # print ("Will adjust from %s to %s (was: %s)" % ((wd, ht), resize, oldresize))

        if resize is not None:
            if isinstance(resize, int) or isinstance(resize, float):
                image = image.Scale(int(resize), int(resize))
            else:
                image = image.Scale(int(resize[0]), int(resize[1]))
        if rotate is not None:
            if rotate == 1:
                image = image.Rotate90()
            elif rotate == 2:
                image = image.Rotate180()
            elif rotate == 3:
                image = image.Rotate90(False)
        if (
            color is not None
            and color.red is not None
            and color.green is not None
            and color.blue is not None
        ):
            #            image.Replace(0, 0, 0, color.red, color.green, color.blue)
            image.Replace(
                self._color.red,
                self._color.green,
                self._color.blue,
                color.red,
                color.green,
                color.blue,
            )
            if DARKMODE and use_theme:
                reverse = color.distance_to("black") <= 200
                black_bg = False
            else:
                reverse = color.distance_to("white") <= 200
                black_bg = True
            if reverse and not keepalpha:
                self.RemoveAlpha(image, black_bg=black_bg)
        elif DARKMODE and use_theme:
            for x in range(image.GetWidth()):
                for y in range(image.GetHeight()):
                    r = int(255 - image.GetRed(x, y))
                    g = int(255 - image.GetGreen(x, y))
                    b = int(255 - image.GetBlue(x, y))
                    image.SetRGB(x, y, r, g, b)
            # image.Replace(0, 0, 0, 255, 255, 255)
        return wx.Bitmap(image)

    def RemoveAlpha(self, image, black_bg=False):
        if not image.HasAlpha():
            return
        bg_rgb = 0 if black_bg else 255
        for x in range(image.GetWidth()):
            for y in range(image.GetHeight()):
                a = image.GetAlpha(x, y)
                bg = int((255 - a) * bg_rgb / 255)
                r = int(image.GetRed(x, y) * a / 255) + bg
                g = int(image.GetGreen(x, y) * a / 255) + bg
                b = int(image.GetBlue(x, y) * a / 255) + bg
                image.SetRGB(x, y, r, g, b)
                image.SetAlpha(x, y, wx.IMAGE_ALPHA_OPAQUE)
        image.ClearAlpha()


class VectorIcon:
    def __init__(self, fill, stroke=None):
        self.list_fill = []
        self.list_stroke = []
        if not fill:
            pass
        elif isinstance(fill, str):
            self.list_fill.append(fill)
        elif isinstance(fill, (list, tuple)):
            for e in fill:
                self.list_fill.append(e)
        if not stroke:
            pass
        elif isinstance(stroke, str):
            self.list_stroke.append(stroke)
        elif isinstance(stroke, (list, tuple)):
            for e in stroke:
                self.list_stroke.append(e)
        self._pen = wx.Pen()
        self._brush = wx.Brush()
        self._background = wx.Brush()

    def light_mode(self, color):
        if color is None:
            target = wx.BLACK
        elif hasattr(color, "red"):
            target = wx.Colour(color.red, color.green, color.blue)
        else:
            target = color
        self._pen.SetColour(target)
        self._brush.SetColour(target)
        self._background.SetColour(wx.WHITE)
        self._pen.SetWidth(2)

    def dark_mode(self, color):
        if color is None:
            target = wx.WHITE
        elif hasattr(color, "red"):
            target = wx.Colour(color.red, color.green, color.blue)
        else:
            target = color
        self._pen.SetColour(target)
        self._brush.SetColour(target)
        self._background.SetColour(wx.BLACK)
        self._pen.SetWidth(2)

    def GetBitmap(
        self,
        use_theme=True,
        resize=None,
        color=None,
        rotate=None,
        noadjustment=False,
        keepalpha=False,
        force_darkmode=False,
        buffer=5,
        **kwargs,
    ):
        # if debug:
        #     print (f"Color: {color}, dark={force_darkmode}")
        if force_darkmode:
            self.dark_mode(color)
        else:
            self.light_mode(color)

        from meerk40t.tools.geomstr import Geomstr

        if resize is None:
            resize = get_default_icon_size()

        if isinstance(resize, tuple):
            final_icon_width, final_icon_height = resize
        else:
            final_icon_width = resize
            final_icon_height = resize
        bmp = wx.Bitmap(int(final_icon_width), int(final_icon_height), 32)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(self._background)
        # dc.SetBackground(wx.RED_BRUSH)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.dc = dc
        stroke_paths = []
        fill_paths = []
        # Establish the box...
        min_x = min_y = max_x = max_y = None
        for e in self.list_fill:
            geom = Geomstr.svg(e)
            gp = self.make_geomstr(gc, geom)
            fill_paths.append(gp)
            m_x, m_y, p_w, p_h = gp.Box
            if min_x is None:
                min_x = m_x
                min_y = m_y
                max_x = m_x + p_w
                max_y = m_y + p_h
            else:
                min_x = min(min_x, m_x)
                min_y = min(min_y, m_y)
                max_x = max(max_x, m_x + p_w)
                max_y = max(max_y, m_y + p_h)
        for e in self.list_stroke:
            geom = Geomstr.svg(e)
            gp = self.make_geomstr(gc, geom)
            stroke_paths.append(gp)
            m_x, m_y, p_w, p_h = gp.Box
            if min_x is None:
                min_x = m_x
                min_y = m_y
                max_x = m_x + p_w
                max_y = m_y + p_h
            else:
                min_x = min(min_x, m_x)
                min_y = min(min_y, m_y)
                max_x = max(max_x, m_x + p_w)
                max_y = max(max_y, m_y + p_h)

        path_width = max_x - min_x
        path_height = max_y - min_y

        scale_x = (final_icon_width - 2 * buffer) / path_width
        scale_y = (final_icon_height - 2 * buffer) / path_height

        scale = min(scale_x, scale_y)
        width_scaled = int(round(path_width * scale))
        height_scaled = int(round(path_height * scale))

        # print (f"W: {final_icon_width} vs {width_scaled}, {final_icon_height} vs {height_scaled}")
        keep_ratio = True

        if keep_ratio:
            scale_x = min(scale_x, scale_y)
            scale_y = scale_x

        from meerk40t.gui.zmatrix import ZMatrix
        from meerk40t.svgelements import Matrix

        matrix = Matrix()
        matrix.post_translate(
            -min_x + (final_icon_width - width_scaled) / 2 / scale_x,
            -min_y + (final_icon_height - height_scaled) / 2 / scale_x,
        )
        matrix.post_scale(scale_x, scale_y)
        if scale_y < 0:
            matrix.pre_translate(0, -height_scaled)
        if scale_x < 0:
            matrix.pre_translate(-width_scaled, 0)

        gc = wx.GraphicsContext.Create(dc)
        gc.dc = dc
        gc.SetInterpolationQuality(wx.INTERPOLATION_BEST)
        gc.PushState()
        if not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))

        gc.SetBrush(self._brush)
        for gp in fill_paths:
            gc.FillPath(gp)
        gc.SetPen(self._pen)
        for gp in stroke_paths:
            gc.StrokePath(gp)
        dc.SelectObject(wx.NullBitmap)
        gc.Destroy()
        del gc.dc
        del dc

        # That has no effect...
        # if force_darkmode:
        #     mask = wx.Mask(bmp, wx.BLACK)
        #     bmp.SetMask(mask)
        #     bmp.SetMaskColour("black")
        # else:
        #     mask = wx.Mask(bmp, wx.WHITE)
        #     effort = bmp.SetMask(mask)
        #     bmp.SetMaskColour("white")
        image = bmp.ConvertToImage()
        if image.HasAlpha():
            image.ClearAlpha()
        image.InitAlpha()
        if force_darkmode:
            bgcol = 0
        else:
            bgcol = 255
        for x in range(image.GetWidth()):
            for y in range(image.GetHeight()):
                r = image.GetRed(x, y)
                g = image.GetGreen(x, y)
                b = image.GetBlue(x, y)
                if r == g == b == bgcol:
                    # image.SetRGB(x, y, 255, 0, 0)
                    image.SetAlpha(x, y, wx.IMAGE_ALPHA_TRANSPARENT)
        bmp = wx.Bitmap(image)
        return bmp

    def make_geomstr(self, gc, path):
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
                start = e[0]
                if end != start:
                    # Start point does not equal previous end point.
                    p.MoveToPoint(start.real, start.imag)
                c0 = e[1]
                c1 = e[3]
                end = e[4]

                if seg_type == TYPE_LINE:
                    p.AddLineToPoint(end.real, end.imag)
                    pts.append(start)
                    pts.append(end)
                elif seg_type == TYPE_QUAD:
                    p.AddQuadCurveToPoint(c0.real, c0.imag, end.real, end.imag)
                    pts.append(c0)
                    pts.append(start)
                    pts.append(end)
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
                        clockwise="ccw" != Geomstr.orientation(None, start, c0, end),
                    )
                    pts.append(c0)
                    pts.append(start)
                    pts.append(end)
                elif seg_type == TYPE_CUBIC:
                    p.AddCurveToPoint(
                        c0.real, c0.imag, c1.real, c1.imag, end.real, end.imag
                    )
                    pts.append(c0)
                    pts.append(c1)
                    pts.append(start)
                    pts.append(end)
                else:
                    print(f"Unknown seg_type: {seg_type}")
            if subpath.first_point == end:
                p.CloseSubpath()
        return p




# ----------------------------------------------------------------------
icons8_opened_folder_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAK9SURBVGhD7Zk7aBRRFIYXLIKCEQux"
    b"ExEhYhcFCxEFUSsxCJFgAqJ2goWIdiJaiIrgI50kjRoLEdJpumApsfIBFpKg4AvxBYqF7/87"
    b"zFnuzowxu8p41P3gY+bc7C7nz+7cO49amzZtfspsOShfy29N+FSul2E4LWnsiyTMTHwrec87"
    b"uVSG4LmkqeVWzZwLkvfdlLMY+NPQDDbLPPlQ8t6jcn4Fdsof0moQWCc/S/+MKnwk+2QBf0Gr"
    b"9MoHsuxY+t36sck/b5Vs4FeDVM0xSb+nrEr424L0S/q9bFXCfxFkjlwSzH2Sfq/KBsqCMM1d"
    b"kZ+k/z2iL+QOafhgynnJGCv3ZFCZhr/K+gyWD8Iq/VLybSxkIDDHJb0zkxWCLJPU96yKzRFJ"
    b"r4co8kFYNakLs0JARiW9bqHIB/Gv66BVsZmS9LqIIh/kuqTeZFVcOGnlYH9llcgHeSKpox/o"
    b"ayV9jlsl0iALJPvPrIrNXkmvZ6wSaZCNkv0xq2IzLOl1p1UiDXJAsn/CqtjckvTabZVIg1yS"
    b"7G+3Ki4s2h/kR9nBAKRB7kj2m71+rxr6o8/bVmV4EJJxWkLSEDcTpoFfDD1ftCrDg6zIthMy"
    b"Oiclve63KsOD7Mq2QzI6zKr0usGqDA9yNtsyP0eHdY5eWffqeJAb2XaNjAxnHPT52KoED/JG"
    b"cu4yV0bGF+1rViV4EOTKKzqcldOrXUylpEE4v4/OiKTXwt3GNMhhBoLDlSu9dlmVkAbpYSAw"
    b"vmi/l4VFOw2ymIHArJT0yaOMAh6CWSs6uyW9cruqgAdhHYmOL9p7rMrhQc5ZFRtftFdblcOD"
    b"8LVFh58/zzpLF20PwoEUGSYi+uShUikk5AU8po7MVkmfhbvwzl3JC7gbsS2oA5LrJPrksUIp"
    b"m2XVDzRb9b6c9skudyK46mJ+jip3eKKfmbf516jVvgPWjL2OHf8X/wAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icon_meerk40t = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAAAA3NCSVQICAjb4U/gAAAgAElE"
    b"QVR4nGy8Wawk6XUmdv4l9oiM3Je7L9W31q7u6m51s7mIpJqkRGqGoiBpJHkkeTDSAB6PBvCD"
    b"AdlPnmcvAwMW4AfDDza8YCCNOCPKlEVSHKopsnrvWrq6uqpu3f3mvbkvsUf8ix/+qmSxx/lQ"
    b"yJuVGcv5v/Od75z/nEDr6+sYYwDgnEsp1XshBEKIUooQ4pxzzgEAISQR5EgihDQmdaoB44AR"
    b"lxJpRAghAIgEhBBCSH0OgInAOiYsLzARiGDOC4qJAJlhCQAak0iCoFRgJEAKITSEJRfqIEII"
    b"dV71rxBCCKHruhCiKApKqUTABBANC5lTAD1DGAjW9DBNbNtOi1RKpC5bIoEwY0Jgjp98KKU6"
    b"IMYYY8wYk1IihAgh6lyMMWUHAJBSAgApl8vqZ+pv9ZJSEkLUe4SQsiAASJCUUiQBpAQhAWMJ"
    b"gAiWAAghgjFGCANCT48uQSKEEEGSc4RBIiSRxIgIQIAJwqBLTAAJLBHCUgICoITA0ytRB1lc"
    b"rroT9V7dIRccA8YEIySxBCoxSMRAAiUCCca5kAIkAimRlAKE4IIzjhBeGEtKqd4oGy3O9SmD"
    b"qBdVOFKXog6xuMQFvtRXOecYEAHEJSBCOOeYYs45wlhKqcyJASGQUkoCICQABka5wBJ0gSUQ"
    b"hCUiTCKJkESIAiIgAAksJRdAEQFE0NNLRE9fGGN19eq9ulpCiBAChBSyIFgDhDgTBQgBwFhh"
    b"OFbOc4Y4IEASUYFBIikJCAAQ6l6Uu6iDK5wqUywsqK5BfU29SLlcVmhfOKAy3OIbyoKLqxec"
    b"gwSCMcJP8akWREokASOEF79FCBEMkmEMCEAiKTESAiSigLGUgIQkgiMpJQaJEEiEAEuQi5Vb"
    b"vACAUso5V+u/WEuMMQhJCQFAAEhKAISoqSOKcpaBFAQwRkC4RBJxRCRIjFFRFFJKTdMAIE1T"
    b"hJDneerDTxnrU+CiylKfMoqy9xOoP+UyjDFCSDCOMZZcYIIFFwRjkIAAhFT+hzkCqT5CCIOk"
    b"HLDkktAcSQZSYkSEpIhIJEEKgQCBxBIAhJRUgAT0M7/7FN6FEIt1XiwnIiARCC4wxgUvEMGG"
    b"pcdZCgXHAAi4BMwkSAAOmAGCgum6LqVcmAkAoih61jEXFvi5EyFEnyXRBXwU2pV11CEW31Fw"
    b"ZYwRhEBISgnnXN2hotKn7KbWRS0RRghhCUhyJCkSEhDGSCBEOGYIEAAgQBxAIkBP6ekJNAlZ"
    b"ELCClbqHJysnBEKY8wKAAmApJcFYSpllmQYYScCApJSFlBIjKSVIpOl6UWRCCMMwCCGc86Io"
    b"1M0+60AL3198KKUkpVJp4YOfWrT/308QJU+4XNkAQGIiAQmMACOk/GHBlIAKQrmKEFxgACKR"
    b"5AgRxIUQIJHkkiCBEJcIECCElZ0XR1BXyRhbfLKIVuq/EEGMM10zMCCCkWEYrMg5YxJrIDER"
    b"ABIYlpIQggmA5KzQKDEMAyGUZVmWZcolnyWfxZsFup+44bNm+tQ3FObV2iobC5BCIJ1SQ9dY"
    b"ngshcsawpguCpFo4CRgQlgAAAiGBAAGRIIVkUgIBwCBBChWZEQJBkAAAEBIBAVC4WLieECLP"
    b"c855nueGYShCME2TMRbHMaUUY2w5dpExkwrJJKaYYhIEGSEESSKlQBwJxAUCjCSAQIJblqFk"
    b"gdIKykwLbaQs8KxieHbZniipxXIplC0ihfrep8JlkmWC8HK5PJ+HAiAVhUZ1xrlBKJYSOHds"
    b"K4oiamiIGEUOCOM0LWzLgDStlEtJmnvlGjWteqt5795dJtl5/8w0TRPrmkWLgjHGiqIwDGN5"
    b"eRkhdOXKlRdffJExtrW11Ww2syxbW1t78803Hz16ZBjGn//5n8uCT4cjy7I8s8SLQiMUOBCE"
    b"kCQcOAKiYcw4I0i4JTdJc7UAC7aBpzHxUyypgLLgdABAKysrCy36rGhYWGrxSwAAjKSUlNIi"
    b"yzVNo5oBGgmTGGGsUSqTnHJpG3qR5abnzKJQN5w0yDXD2rm6Vam6lzbXl5vtPM/DKLFLFUGQ"
    b"4diO587n08P9gwd373W7XcuxNU2rVqvf+MY3Op1Oq9UKw7Ber0dRZFnW7u7uxsbG/fv3x+Nx"
    b"rVaTUh4cHL3+2me+8+2/GIyGf//WzSRJHMvNotjAFGMc5SlQwhG3DN3AKEmSjAv5hD+eCIhF"
    b"+HrW6Z6lqp8Za3l5eeGJi7jzrHUXOISnYrVQq4cRY8K0LKJrcRxTQJhLkxJCSFrkYR479crW"
    b"9sVf/+VvCc5Hs3E4n1y5dIGlyf7uY79UGQ6HS5ubkyTe3nmuYrnT0RADHB0dbF3YYYJfvHix"
    b"3+8XReG6ruu60+mUUvqjH/1I07T19fXbt29fvXp1fX19Pp9rujkcDos8bnXaN299+O/+4tvZ"
    b"NCCcszzVTD3IUoRxqVTO4gQXeRRFuu0yQM/qA3iqcp+1y7OAWngoKZVKC1g9+0b+vDj82e+E"
    b"pIQQQgTnBBNWFFiCTXWDUFnkjLGc56P5ZGVz/Ytv/NKXv/zF6XRUb1bvfXxvZWn59u27hmkl"
    b"afJ4f7fRbHV73Wsv3tg/PEBcTsYjKUS57DMutra3dnd3m80mxng6nU6n06Ojo+FwKKW8f//+"
    b"1taWpmm+7xdFkSTZxUtX0jRptOqVemU8m3/tq181Nf3ezbdWudw0TFenjm0OZnPGhRBcNwyB"
    b"McDPMKEY+T/mdfj5/OGJHZaXlwkh6sfqDef8P/794k+CsHJ4KaWmGTwvdEwIwppGqK4NZ5NG"
    b"p/mf//G/sCzD87w0i6I8jKKo4Xf2dg8P9o6TNF3bXn304P6039+8sO1W6n6lWi1XKEiKiWub"
    b"luMxwTVNs2371q1b0+m0Wq2qdAQAXnrppQcPHmiaZpqm4zgPH+4udVYQls1WOY5j2yrZrvPw"
    b"4ScrQdL9n/63Vcv+SM7/rzvvDRuNKSUYYykEy5hGqGKrZ9X5p8z0rIhf/C/xff9TCFr44Kcx"
    b"9TQBzPOcGBoimHNBELY0I01TwJBK/vqXP3/l2tVrly/NBsPzT3bXbdcaDcb7h5mQh+f905N+"
    b"tVp3S6VWu/X5L3wWpBRc1KrVw6NjXaeC8ZW1FUyopmmz2YwxVi6XK5XKeDwmhBiGMR6PhRBh"
    b"GNZqtdlsVq1Wi4K1Wm3fL2kaTtOkUa4fPHpccexNJvl3vr+ZMdvSj8eDY8nmOiVUL1KuaxQj"
    b"/Kw54OeV+qfM9GljPctw8DQ0fEp0LCzIBdctkyMoOKeaDgCcMaJrYNKrL7344msvv/baa3sf"
    b"ffzKxsUvbl+bvPlu7//4t5vEYJ2mqFV9u7a6vP797/3NpUs7w2l/bX0lmYdxELZXlh/v7Ukh"
    b"HNtqtztBEIzH40qlIqUslUpCiHa77bouQmh7e/vhw4eMsRs3bpydndVqdQy43qgVkHc67f5J"
    b"b7XapPNo+NZb1aNDn6WYiPM87dVKY4RsaeoSU0qF5IyxRUCEZ9TSs5b6j/UmUVezkAgL6z4b"
    b"FDDGSqhIAE2naZEJCZRSzgQGIBhyzr71W7/5m//J7wwns7Nu98bly/FR91q986P/4V+/hmj/"
    b"8OD1P/z9292ua5QIpl/8wufffvcmYHnvo7ufe/X18+75jZdeoZRolCAsR8OJRHD9+efH43GR"
    b"5aZhcCFs2xYgJ9PJxYuXz7pnb7zxS75XajbrIGSj0bBse2WlAxKSJDt7uPtyo3n0ve9Xe+du"
    b"nmgI7OXOXSFDy4GCZ0nMBONCPF179FSiP+txQoW6Z3J59BRZlRLBSEoghHABCBMhJMFEiUKE"
    b"gXOGKeYgEEYCBKFY1zVWFBrGlm6wPA+i+R//yz9eWl1+tPt4qb36pS98Waf0pfVV/N67wTtv"
    b"11maAHNvvPDKG2+89MINx7ZXVtcKXrzw/DXHsdvNzqWLV0XBKMa1ur9/sK9Z5qVLVziTQsg8"
    b"ibM05YJZtpMJrhnW5SvXoiDyXU8jMOydEQLNzpKUosjyOIp119lptWrD8Z3/8/9eFtjlQmPF"
    b"MGdf+S/+yx/evUc0cH27YFkSx6ZpcS4p1gQXmGqMc0KxFBwjIBiElIAlRkgIrkymPI+U/ZKU"
    b"EkCldQghBFICCKnUGkGEEELJk0KVBMaFrhtIIBAAjF+5fPlf/vG/WF7prKwsv/LSLxCpGZph"
    b"2+YSQt1/+2384JMygYygAaGXv/Tl3ngcA+KSb13YPjs/QRhZlvfchR3OmOs5Kxury6vLB4dH"
    b"UoDve+PRpCjyleVlTTdKvjcPQr9cmk4mRZYVec6KIpgF+weHzaXOZDLTAbfbnVSwDsWj7343"
    b"vfWBR/JOp57OZplp3+wNv/67v7t1aft8PJiPp0TTDMMUEhREWFHohg4g5RPHQgghhDWQSJVU"
    b"Fh5G/JInhOAIcSEoQlIKJKUUkhACWCo640wCl6gQRGJCDYRpyfYd2y3ZpRdeeGHQ79Vq1Uql"
    b"IgsZjkPHMGv1isfzv/2T//qaYcqiYFR7dHq2cmGnK8T+dFKI4qR70D3rttudOI1n8znWtOFk"
    b"GqT5rTt3r1x47uz0tOSVoigsuBAgEIAoimg2ESznLIvC8LR7pulOEIiNjYs3336rXq83a/Uo"
    b"jgTBDSlGf/Zn+tnjGPrtr7x2/tGuMEpzhJ16fenyxa1r1yp+9bx7XggI4sg0jSQLkeAIAWec"
    b"EKpjigQRknAGSFBdsyQSUoqnxvJLQghJiJCCIgziichCBBTKCCFCAiWEYqzrpl+tzCbTql/b"
    b"WNnY2NwqV8qf+8LnZrPJ+trqdDwydCucTgyeJe+9h376Tj3P3KYX8oxIkgAe1+t7cVCrlQtW"
    b"TGbTw8OTyXjywvXrURTuXLy0t7+/tbnx+NGjWrV63uvnrNjZuZjlBSU0TZI0TmrVChN8NJ4M"
    b"J7PJZNpsdPqD/t987/tUI2XPK3m2LIpKGL/z3/3rNk60Fq9cWkHjOIxFwuTqxYsf9Lr17e16"
    b"vTmeTGfhdB7Mmcw1QnSNSsERpRKgyAspJNV1QnTOQYDACCH0RIESv1yRKihIoBgAJCYYYRBC"
    b"YIQoopTqEhFJiACQGP3CKy+ur608f+X5X/u1X3dLVSah3q6H8dwmmu+7VsWxKFyteJ98+9+5"
    b"e0daPq987eWTh3cb0n10cvYusN08vrix8c7Nt8u1xnAw3FrflJzv7+3pGt59+IlGSLfb9cqV"
    b"w5OTLM9ty07i2DXtQX84nMxXNzYf7O7vHh19cOv9IJyF4ShJw/FsrlFiWebbP/67O3//95Ob"
    b"79Z2T1wZV58vG1VNi0XvbKhrTiDRrFXtCb66upYV+d/+6AccCss2MEFJGDqOm+QFooRijDBC"
    b"QjLOBBJUIwAcIXjCWaVSCRBSFc4npI8RICSFxAhhwIAQA5AIABEE8uR4/1/9q//mF155RQCK"
    b"stS0zFk0vXrl4g9/8IPW0tI8T808XbWdv/tv//tlxqoVzXx5JTo9cOeEU+cHk/O84nUPDpFE"
    b"pyfHWZq06i3bdqbjked6nBVCSp0amJJ5EDElRCUYVNM0bWll6fH+/sHx0Y/e/DsheDCfLq90"
    b"Dg8e3/vo3mAwvHX7/cHB4fjOx87J+SWJZNpf+sIGaAkut84+euSCLUx7z6A9ySqVmq7rN9/+"
    b"aaVaDsPAtmwNEwC15yIl4xghTSOYoAKxQuQYAQKkMmXilcoYsBQCSyRBYgJSCgCJJCCEKKYc"
    b"EKYapZqlG5TgS5cufv1Xv/7RJ/dSXmBK7tz+sFaxe4Oe1PSVzQt2qdIGknznr4u7t8s4X36u"
    b"DlXu6iTZmzHNuxWP9ieD8TzIeD4fDSb9Xnu58+prr08mgeOWwiTZ292PJ/PXXnn1//3bH25s"
    b"P5dkuWFow+EZRlw3affs+M7tWwd7+zwvLMt8/Hj39q0P8yxxXXPQO+/e+4QeHX11daOeh2Vf"
    b"uld9SKZADd6fknEyS4twa91c37h//97Ozk610njwYNcy3DzJ/FLJMPQ0zQCQoRka1aTghcwK"
    b"PReaoEAJerJ3Q8p+GSEEQmACEoBQLAEQAEaYYI3oBhcCUwpcABdFkv5Xf/InJ92upmvd89Nq"
    b"pXqw/7jZrJ2enEqgo9n84YMHm0QLv/s9f3DOxKT5+kVwYmJqwzsnulvtY/4f7j4YRQkn+nQ0"
    b"Ou+dJ1mRZGkcpcPR6OrVa0mS3rj2/AcffHDtxRdnsxkI0W63bFM3Te2TB58cHhzevfPR8eFx"
    b"xff75/1HD+6HQTAezYe900lv6GfZr5Tbr5ZLNBmtXyijFgKNg8RGgYrzNANrUq0Ulsm4sFzv"
    b"0pUrr7z8C7pGXccenp9zxoVEIAAjSjABISUWEgsQ0iAmhifJH6lVahghEJxLjhDCBCEhDaIh"
    b"TCQgjpBpWyXbRnmhMXl5+8Jrr36m014aD3vT2SRLYtdzBIfJeJoF0d7DR8FsGH18v3nn4RJL"
    b"9KbwrzaFHCLXjQ+HScbcav39k7NhVOwP5+eDcSFks9W88vyVF156XgjePz3znZKUwnTM4bDv"
    b"ulbJcygBznkUp17J/+jOxycHp7PxPE/S6WhEERYFIwQIB0NAG+Afmv5lCknaa33uEpAp4Bw0"
    b"Qr3O4Z0BojVwTd209ruDytLKJJiWq/4Lz1/97X/0W0SSx7v7wJBumIZlFoxRRCiihGGbOhiw"
    b"quRgjInruAghTdcQBsAyyzJbN6REBROIEialX/LLbilLIkLkf/bP//na2vp0Pvvg7m0hRffs"
    b"lGV5MBilvZEdJUdvv50fHqwH8Y0MzHzmXbKNNuY4x1nuYm/YnxvYHZ/3QhCEgUU0wYokiRzX"
    b"Wl5fnc7nL11/YTaeSIIn8+k8mF65cnE6GZ2dn21ubecFm8/Tj+8/GI0nWRzprKhpOoqCioS6"
    b"gE0JVzT7myubX213cNAzG7h0sQ44BFxIAIRsPuTxPOdpLMPYN2yYzzumUSLQsKxkHrz62mfa"
    b"yyuzeSgxns1nUvI8SUBKHRlCCAlIwpMtCFKt1BzHSbJE7Z6US36aF1TXDdtiAkq2wws2HY9e"
    b"evWlf/jbv75z/fJHd++MZqMHp8flVh1TEvSH5iyOPn5AHz541TQ/i61LEWswmeFZ64tLwgyQ"
    b"TpHQkVU/uvXYFd6l5taSptdkYeQxKXIOvEBo48qVSThvVqqEoqRgTIjnnts+PjlcXl7WdT3L"
    b"JNHNB7t79x5+0hucFvFsydK08XgN4CvY/KONjT987vIbldYOoXg2CcV06aWO1sBAMzAIAgGF"
    b"oFEaDsZWgmqxqPb75uN98+zUGk0263VT09/96GNarRDHfv/ubQ2BZRBdQ4TIKAmFEIBhkWRT"
    b"XdeTLDYsk1KchEGapkAw0vSciUqlIvJiudP+w3/2T2vtmkBcR7IM+MO33t3yrXJvmPb6mwKC"
    b"h0fXNKtWq/h54sShAyJmKa4DOCCpLNLMBB20wu/YydnAMcVnGs7VpfKE6OeA3+92Ucr4W++9"
    b"cOVKIwgnYaJR3XLc27duCeB+uWLqRqdU6x0cf23n4vDv3wxOumu+e7lc3llZv6DZjSytZDN9"
    b"uBfEEejYbPidrQ3juQrIIZMcFYxIAXphXW9eMLTRfjw+2q3oZt2wZr1gPDj5uw/fE0vLsL65"
    b"H0V73ZNv7ly4d+/+JEmmQs7z1HBtVggmuEoPOedoe/s5x7MHo5FOsUGJlJJTygH5dsm3SyXb"
    b"+vwXPvsPfuub773/9vWdC+Fet7h/Jk/OR4/umMGkKbg2T6p6mScJpmkuxrkWI4OtrK1Ury6B"
    b"PU5FZFIXMglAICOzR7PjR/08k5TbpixRahcaTSmJJNB2Z/P11xtvfAlMfaTh79/+cOXSDhNQ"
    b"081sb3+Fw0ff/e7ko3ulvGgZOkojW8N5FAOOmBg5FbS2s6RvdoAwQAVABhpiIKTkGnCZc0RM"
    b"EBogC5gePjwORln3cEKl7WjlrACgeka1IRFzzeLl+g8P9z8Q6USnUZRgjDGgRS8IWl/fJBo2"
    b"bZsXWTge11vteZaZjqtx3KrUXnzh+RduXMceXW/U63G+9703szt7tNttyrSUhk0E+WyONZqI"
    b"qL7V0Fs63a5BiUCeACRgFIAlSzjVDRA55AKQB7QMCS52e7yfn++embqdZ8I0y3OinQE+B6hf"
    b"u2i/eG3lV79+dzySmtECNPj+D+c//Wml19skxCsKnGcIi1E4qq03aleWYdMFPAcxB40VLKGU"
    b"Ss5BIqbpvGAWxSBFDhIRTAEhSQC5kGCgLdjth7v96eHQKrBuOnNKI9MZYuvEL/37ZPxhPEs5"
    b"IlTP0nhRkkFrK+tUJxln5ZJbc0qTyQQ5NkJkudxcbnfcshtl8atf+IXnyzXr7Qe7f/btZRnX"
    b"QehFriGpG7iyUYe6gK0KFGPwNJmnUhYYBCQBuI7kDBEKRQEYA0GAAPICkAXUhVwDrQJ7YxgV"
    b"4/1xEjCGdKQZWVY8NLD3T/8x3HghYNLsD8Nv/5X/8OG2KOw0JoSEedDeXKZffRVkH9gQcAyU"
    b"ySIHzBElAAKQAEAcU8aEzgFhIoFJyTGinDFMCZIaZBpACUgFaB1+8O7wYIBNl4OWMTJo1L7r"
    b"sL/YezgTmjQsLtmiUkia1YaUglCSZaksWKVSo4ZuaAYwUWT53uF+xvLllfbF1kqn0B/evFky"
    b"pCxiHVOQkPIijCdMBroIcbsOWYI0EzEBLAOdqu4H4BwoBZDAJRQMqAmCAtLB8JKHB5OTwfhs"
    b"Mo8TTnSwrCAtcgnnUq7/yldTz6202h7VnCCcnJ7wLBUaiQhI05gk0/13f4rCgU0AV1oAGkIE"
    b"CQKIABcghQTJOdI1AwQgDAgw4gSoi7mGwADiAC3BUf/83v6DH97MMpRTOzasKdGgVDqj8v35"
    b"cIwQo0bKOKE/6yZCWxubVNcYY6qXiDHm+SXf9yt+lXMexyFg9K1vfdNCaLvUSI+O5g/vuKMp"
    b"OerVcuaLXM9jInJARZAHpWZpeasNDRuaFqAAaAqSgYQnzTWcgKhAgOTxqHswnJxFruZaGKcA"
    b"c4OMid7l9MJnP9+4ek1bX3u7f5aWXLtaF2nKzs+dMIx2H0X7e36SNHjhhoHPUr2IRBoxIFbN"
    b"ru1U9K0GGBggApJIYAhrknOOGQIgoIOwQPoQAds7TwbBYK9nEpsQJyd25pbHun5E4P3zk1tH"
    b"h1NTsy5s5oYlMI2SbBbMf1YuvnDhAmNM07SiKAghtm1rmlYul13XPTg4yPNc07TXX3/96tWr"
    b"jUZj1jubHezVMrYljEc/+tFGpWQkicvBkgCS6TKDZJrxOfbh4mtbpI0lzSQXmBrAaXoaHr59"
    b"DJGOtFIBjqaVC4k54SFlSdkuX7n88rd+FzrLc5C3jx5LakzSpFSrPz7Yv3vrdtP3YD7f9ku7"
    b"b/74zve/9+X17XXbqiNcxhTSAkMRij6DoN1wa8uudbUJOAPGQSMMZzIHjTaCj3u9x8N4xDXk"
    b"YmRhpEcFLwwzNOyf7O99Ek0fABsD4Go5odir1k3bIQhPp1PTNLMsy/NcCEHUVqVpmpqmua5b"
    b"LpfVjnSv1xsOh2oz6uDg4OzsrNPpHJ10Hx6fbL14Y67RUcn+zsHjm3HwTjTbJaKngd3soESr"
    b"GzU9Fr3Tk/qNbYQSZCAACqL08Id37dQBXB2YpXG1eRfkD2aDv44Gh8v1pW98XT536bAQqWnd"
    b"O3qMdOqUnN6gV69Wfc+plksHBwd7B0fDKG5fvPThSXdPwj0hPqL0bp6zqi9tx9J9l1l0nM3O"
    b"+46NacUCTDgwIFwTRnEvObh54uY+luWBcM6t0kPHWPmdX7+/XP0fb//0A5TvUplaNvHL8zRH"
    b"1BAAhOiGYVq2kyTxz/bNqtWqpmmqP6IoCsaYaZqc836/H4bhaDRSOxqGYezt7Tmu+8prn3Vr"
    b"9ZVLzx2FQez5XcH6kp9k0cOz0/3+kCEbC9xEBk7D8oYHWpaxlAoNztBwdyZRdWL6b4fxj0fj"
    b"PUqGNf+0ZLY+8xlvY4vUW8LyRnHcn4zOhwPLcRqNxmg0jKOoyPNyuTKeTVc2NkZJWtvaetAf"
    b"ZH41rdSO4uAsnI/S9HQUmnqpabkyTVMRl9ZXAXLVl4VxtfvmMU7LM80bl+rX/9Fvb/yDb1z9"
    b"zW9NllpvTfpBrfJwMpkDFpqZMSiXq6ZpYUxynumWgSlmjKkWIQAgjUYDAPI8d123VCppmoYx"
    b"Ho1GSZLkeU4pnc/nRVHYtj0ej3cuPPeNr3x1Nh6vry+7rldvLBFs7h3sVZuNUTiv7Vw4MpBW"
    b"Ka1loiSSWA6dCy1KAbiTPkiGA5j59ffy9C0pxu1ml2Wd5y+vXr529fpLnukNeyPOeZzGQPV6"
    b"s3N21g+jmGg0jkJN09IkJhidnB63Wq3Nza3NrQvzIHy0+/iLX/3KBw/vh7b9kIvDYFahxDf1"
    b"cDZvX9gCGiGcITBQ5sw+HOZG48FyZ/Of/ZPJxc1Jpz7VdbPR8MqN/+V//l9Lpn/98vPzSbC+"
    b"tjrsDxBCUjIJwnRMQJAlWZ5laZoyxki5XEYI6bqOMVbIYoxhjLMswxgrFiuVSnmet9vtLE2/"
    b"+IVf9H1PgqSGYdpep70UxoHtWmAY/SwtXdh+7cZL8MljX+YBn9a2l4GnQMuHf7uHtdaeY/40"
    b"nHf9kr667DXqO1evXXz+xc7SSjKLmo3GSfc4L3LbcYfD4eHB/tHR4dl5dzIeI4QGg9777793"
    b"enpCKOksL13YviCkHI6GJ2dnIcunUswojdO0VBQb1borkAcp6WhABCL+6G43Py4GYOFfeWO0"
    b"vXGKud5qSE2PM/bOzXe//Iu/1Oks/eW//w5nLMtSSggrMgm8EHmpWpZS8IKpxliMMWk0Gmq/"
    b"VwihaZpySc65pmlCCMdxbNtO09S27SiK3vjKG612u9ps2iWXmobtOH6lRAkreaWdS1edUvnF"
    b"ay9fX93Co+Fs2IU86bRbYBEYZ/NbY+K230HFe3Hw/Be/7FSqrUr9heevbz93kTGm69p0Oj7v"
    b"nyZR+PGdO+fdk/PuaZYkvfMuINTtdo9PTgnFtmMDkpZtv/LKS4atDUc9xzVNy9p7fNCs13XG"
    b"o97o+a0L+mSmy8S5Uoc8BVYe3TomsXGOjJXf/e0TnVx4bns+mZiE6ongM3UAACAASURBVFRb"
    b"31h/9Hj33/zZv8EUu54DSEwmY0SBaJqma6VKmVIKXBq6YVmWbdtPdqQRQpRS13U1TQvDcD6f"
    b"c85brZZlWfP5/MaNG5Zl7ezsjEaji5cu1hr1QkohIYkjnYiy62JCbM/vtFeno2lw3qtiPD/r"
    b"eoWoCElXmpN7+2RsTWjpr+bDZGM5wrjZbOlEf/mlV9I8FYIHwXw6GX388b1gPndMXfBC14ht"
    b"WZZtTydzLmSW5VLINM+/9ItfqtaqGCHLNpuNuqZRIUQSx/v7e2XXmc7nLdfbQaQYndQu1YAQ"
    b"mOmnt04FdqyLV40vfc65cKF3fOzquqkbmOKyX7l05VKeZ8fHRwAySZJavW47rm7qpml5Ja/I"
    b"eR7nWZYlSZIkCanX6xhjSqmu65qmcc4ppXmel8vl2WzmOA4hJEmSV1999Rvf+Mbv/d7vAWAk"
    b"iUTY0nSRxHkSaxSDxK5XSeOs0WwZQtYM6/z+w04BcjItPX/t5OYdkXvTcuN/P3xELj33wssv"
    b"UU2/dPGSaZhEoxTDw0/u3frwA5CIIGLahpDCsm0B4Nje8vKqaThFzoN5bFue53qmaTuWHYZh"
    b"uVQ2DN2yzCCYBrMpR5LWaslg8EXPL+czzeW01oZjNjpLR4J6L72Ybm08HvaXq7UiTommhXEk"
    b"EZrP5+fdXpFkLCsQwkEYMS7iOM3S3NEdWUjBuZBSgYnU63XVzLboDVFtlgghTdMIIbquU0rf"
    b"e++9Vqu1trZWq9WlBMu0JBcsT8p+yXU9ADSfB5VaxXHc8XBYFBmN4kpvaEeJR0jvbEL9pb/v"
    b"9Xd939za8sulC9ubJc/XdT2Lw363W+TpbD7vdFYkoCxLbcdeWlop+RUJOI6zTx48wBiblkUp"
    b"DYJwdXUlzZJ+v8cYG49HVNOuXr3y8e07WZ73o8hI0i9XK24eh3zmb1wM3j8OM+MQ0e2vf/3M"
    b"MVYuX6ZA8qLIBa/UGrppdM+6gonpfDYYjSeTaZJkSZwgQLpueJaTpUlWZFmeq+1+rFJqVZAv"
    b"igIAVOPdfD4fDAbT6fTw8HA4HH7zm9/87Gc/6ziO69q2ZyAETBQSkUkQ9MdjhsTa5lK5Yhcs"
    b"Bs8I6s68YkksHETHD8+wUTkhcMRz07bf+MwXlipVDbDkYu/RLioKi+IP336nXilvX7hwcHLa"
    b"7Y80zS35DcaRJDQuMmxocZFgg8RFZJXM0Ww8nU9qjfp4OllaWz8bj2fz6PrFq1XbK7ueWfZO"
    b"eDHR9WE/Ba0xOhzlHNs7O42XX75w5bqmm9zUccm1fD9J8+k8bLQ6DMO1l168+Pzlcq0czKe6"
    b"RgydOrapO4Zm6/zppiHGmNTr9QVnqR5eAIjjmBBiWZbjOJ7nra2tua7red7q6moQhQAQRRHG"
    b"2PNKlGqO45mmLiUvlUogZLVWn/HEzlPjk4fVgnMGoWYc2NrfHO197Q/+iV2rIMw1SqbTWckt"
    b"9c5OBeOWaz/c3bt17+OHj3alhCIrPvjgg5s3b773zttHx0dxOOsP+oah3/3otgRx4bntLM9z"
    b"VkiA8WS21FkJJvPVerPVbHzxK1+90GktgyhGI09q1X5YBHyENf9rX2Pb24MsC1nBJDdsazSa"
    b"zII5pbTbPQGM/+r/+c5Z9/T2rQ8dy6IYFXkmQRJKclYQ/KSszBgjvu+rXVXTNJVWQAjN53OE"
    b"UKlUStPUNM0XX3yx2+3W6/Xl5eVGvQ5AOEjb8YjALBcYE8aY49hxGBVBdt7tSYocxsrjIO33"
    b"LayFGrrva5/9oz/wN9cH0QwIcjzXc73JdOr5/sHJySSIjk7PPrp7P0+zfu9s99HD/b1HRZbq"
    b"Ou6fd+PZNArn4Ww6HU8Nqi0tLY1GU9fxdMOkWPMMz6YGwmJrZ9v2SpuNxhsv3bj9H95sCYsP"
    b"Io2QEyKXfue3dwm4tZpt24TiKAjyLHVsy7Gtkuf86Z/+6Ucf3cmSuFmvIyTjNNZNfX19DYHE"
    b"CBUFWzQik3q9TilV6SGl1DRN3/c1TTMMQzUFn5+f//jHP97Z2fmDP/iDVquFMS3yPMtilhdI"
    b"Ytu2mRCaRhkrXNczsSEQEEvb7nQuN5c++PFbDkLngj3/R/9p63OfyYCeDYau75uWNeoPszRP"
    b"s0Ji7HjenTt3DM0YjfpBEAjBNEIRllmcrK2snpx0CQLG5fbWVpqmrVZHCFHyvCxjrXrj44/u"
    b"hUFgOGZ7dRljUnbcoN8fPz5szLjL8RyJdLW99fv/mC91wiicTCd5lrKC1ao1goll6pZp/uLn"
    b"Pz+fTAkmnPP+YCCEMEyTFUW5XC7yPE2zRd8pdV1X13X0dEaHcx7HcZZlURSFYZjn+cbGxu//"
    b"/u/HcXx2dmYYhqlbjOWTYU8y7ji+Wyr3p2MhhEXIgDEEmsTCccxZEATNVrdSteZRbGqXP/eV"
    b"t2bjPJV1vxGmLIwmRZQEs7njlbrdbrPVqpRdkDzPK4Peua6bUZ50Oi0w4PC0SwxjHmc05zsX"
    b"Lx8fHo2HI9u2j/cPpZQyy278wvN3792PJWJIH45PvEZj5fLl6vPX04MfCoyGlK5+5vWzyehh"
    b"7yQYT8vlcqVSI4Scnp5mSVpyXdu2b9+9++jB7s233zIs07As3TYAaeVKYz4Oi6LwvVKcJqrB"
    b"mahuZc55EARxHOd5rpxRSlmr1UqlUlEUN2/e9H1/e3t7eXk5DKLxeJRG4crKSpqmx93TNM8q"
    b"lTJFVKc60WmYRnEaGZrOJa53lhjA0quvPkAotZ2D/f0giFrtJcZ4kWWWacZJsr+/f3p2Yhp6"
    b"tVq+fv36/t7hdDbzfd80LcaFphuAsK4bW1vbCOHReNJstAAkL4ovf+lLEoAQbDmOZtmaYXiW"
    b"aVp6iuSF9vKjv/5b07QfUbTxja/1LIOZemepwzkDjCjRhBCu49RrtTiOf/zmm7bjNFsdKYFx"
    b"keeFY9uu6yZhAiCDKMjyDAAopcSyrCRJlLyyLKtSqViWpcxnGEa/3zdNc3l5uV6vX7t2bXV1"
    b"1S+XHNcVUmZ5YVluuVLWNA2k1DSKCQYMpmGYpompbpcrncsXL37jlxuv3pC1MifIMM00T7ng"
    b"o+FwdWVpOpuenp4MBn3TMNvtzrvvvbe5tX3x0qVavVav1waDvq5RKcX29tbW1mYQzI+PjzBG"
    b"tXotimPP8wrGoihqVBonRycbm+umTpuNSl7ksUhcaozvHR9P4/zS5s6v/so5iFEUTCYThCnF"
    b"WhzHYRhatiWlNEyz3emc9c6Pj48eP96dTif1WtXUdQApAbhkiOBFdyBpt9uqhrVool8MTU2n"
    b"00ajUa1Wf/mXf/nXfu3XNjY2pJRZlgFApVKlmq7pehiGWZphhOM4xoQoSBY5G0+mw9lslCbD"
    b"PH086BPT4JzrhqHpmm1b1Ur5/Pw8y7LV1VVK6enpqaZpP/nJT09OTh8/fjwej8/Pz9UEhK7r"
    b"8/l8PB5zzofD4erqaqfT8X0/y7Nev6dRjRfywnM7aZGF0azsl+IsSXjGM7axtFna3nReufrB"
    b"4HTKC4mg4lcFF3GcEEIcx9E0rVavlXx//+BgNBqpWQQEKAyCer3u+/48mBWMPdsuSlZWVlRo"
    b"zPM8iiLOuZLys9lM1/VKpaLr+ttvv/3jH//4+vXrtm0r751Op8PhsNfrEUJc11XATJJE1X10"
    b"XXccx3XdoijiOAaALMsYY2EYAoDjOKPR6PDwEADeeeedIAg8z1NYPjg4IITMZjM1fCSlDIJA"
    b"6eTJZNJqta5cuXL//v0wDMMw3NjYyPKcUD3Js73Tw6TI4zi2bHM8GMdZNtNk1+BRxZSuIwDC"
    b"IA5noed4ruthQlRxhTGWpmmj0fje97734Ycffvzxx7PZzHVdy7LSNFWIYYz9XE8pxjjPc8aY"
    b"ZVkKXKZpUkrTNA3D8Pj4uFarfe5zn7Msa2trSwgRx/F4PC6VSrVaDWOsxmgAIE3ToiiCIFDo"
    b"U3rN87w0TdUNh2H4+PFjjHGapg8fPtzf3280Gufn5wcHB1LKpaUlKWWv11MiRhVCSqWSwtfa"
    b"2lqz2ZxMJs1mU9d1VXQzDKOz1CGE2o6taTQOw0/u3w9ngW5ZmUmFZ4VFESWJbTr1agOkZELM"
    b"ZjMJUrW/Z1mmadrdu3fTNJ1MJgihWq3m+76u62q0SjH4YtiEVKvVPM9VWiOfJkGq3jAajdSY"
    b"tBDi7t27v/Ebv6Fa0sMwrFarUso4joMgUJSXpqmaPAIA13WllPP5XEo5HA51Xe/3+/fu3ZvP"
    b"58p80+lUdf33+33DMNbX1x89eqQMoUq1jUZDpaXNZlOhO89zz/MYY5PJRPnBfD6v1+v1RvO9"
    b"d98ZnffTILZN0zQMyeVsNk/i9HD3gEpcccrn/X6cZtMokhgLzpTCFEKowsHt27fff//9oigm"
    b"k4myjm3bi0kV1ZSsckGq1k0BUplJeVaWZSqFbrVa1Wr19ddf933fsiwhRLVaDcNQCKEQVK/X"
    b"z87OGGNZlqmkUvmRmiEpiuL+/ftCiE6nk2XZeDx+//33v/nNb969e1fB1rbt2Wym6rHD4VBl"
    b"pmpaUhXX4jhWTi2edhnrug4AYRj2+30BstvtxtO567q9s/rSygo1ddd1TWpe2Nie9Id3T+9Y"
    b"Xqk/GDWXO6PJuOaX5vM5IcT3fc55kiS6rne7XXW/lUqFMTYej4uisCwLPZ2qf5I412o1xTiL"
    b"koNlWQBg27aatJVSXrp0aWlpaXt7O03TNE3H4/FkMpnP52maJklyenqqBoAwxp7nWZY1m82C"
    b"IJhOp2EYquXinN+8efP8/Pztt9/WNM2yrF6v1+/3Fagnk4kaAKzX6wgh27abzWZRFItJCiWg"
    b"B4NBGIaWZYVhOJvNGo3Gzs7OWfdsOh5vbWz4rut7pZW11VKtrulGOJ7lcUqp5pZKpmFU67Xu"
    b"8FyAoIAE54ZhnJ+fLwZ2Dw8PGWOq1V4lLZRSVVZQ/qgolVSrVcUviyZ4NY7HObcsq1QqGYYx"
    b"Go1ms5mmaZubm1LK2Ww2GAxGo1GapgDged7Z2Zm6k+l02uv1Tk5OkiQJwxAhpNbq7t27juMw"
    b"xjzPQwj1er2dnZ0oivb395MkKYqi1+sp3TsYDBhj/X5fYUpK2e12kySJoijLnkygmqa5urqq"
    b"qpIYQ7PZiKIQABm67pQ8apqnZ12CMOM8jKMsz9M0dUvO8upKrVKdTaaNel3BQoWmv/zLv5zN"
    b"ZnEcL/TAsx3KCkYqCySKpBe1B0KIqm0tAl8cx7qur66ufulLX1I7Y0EQqHinaVqaplmWKYKP"
    b"okjF4NlsRildXl42TVONaE+nU3g6xut5HsZYzVCoK1N7S1mWVatV1YKheKBarWZZFoah53nK"
    b"E1utlmEYQgjP8zRNsywjTqPRaNjptC3X8cuVZrvdH40azWZS5HGe5UXRPT8bjgaT8Xg0Gk7H"
    b"I0MzZrOZEKLRaBiGcXJysre3N51OF9M8alwTANQDJBaDJ4SQJ8ha2FLdmyIgFQXa7bYK7Zqm"
    b"qRnhfr8/GAyiKJrP55qmNRqNs7MzBb0gCKSUlNK1tTWlnhzHCYJge3tb+X+pVGq324r7VM6g"
    b"VphS6jiOikcA0G630zRVgQlj7Pt+tao2fePV1VUVyxBClmUapnH9xeu+77c7bb9cNi2bEu38"
    b"/DwMgrOzs0G/v7zUXl1ZNU0TI+nYDsbk/Pw8iqI0TZvN5vHx8U9+8hPHcVShZQEXdfzFuMCT"
    b"aFipVJ4dUlmMRT1pskFoPB4rvbO/v6/reqlUUnJRHfHRo0d3795V2dInn3xyfn5+cnKibnsR"
    b"UFRwYYwdHh7u7OxUq9UoigzDsG273W4rfacCU61WGw6H5XJZ7chVKhWM8dra2mAwaLfbnU7H"
    b"sqyiKJaXl1utlu/7g0HfcR3bsggis+lsZX19Np9RSj3bNhDaXl0rOU6eZUEYbj+3xRjTKN3d"
    b"fbyysqKWZ29v7/Dw0PO80WiktvsWpSv0zDz24kVqtdqz4ylPepifFk4VLIMgYIypyNhsNlUN"
    b"59GjR0dHR6VSqV6vq+1YSulwOGy3261WS5HiaDQCABVDms3m2tpaEATdblcRZ6lUiqJIsdjW"
    b"1pZyvaIoqtWqrusK0a1Wq9FoKHKsVCqNRkOxr+/7CKH19TVCyXgyqddqtUadFzwviul05rme"
    b"QahtmIBRtVbLWXb//v2XX355PB6vrKxOp9OTkxPLslZXV2/fvn12dqbcbfGQFPj5ocsFxIgK"
    b"QPDzY2QLga+uUkqZ5/nm5uZ8Pvd9X7Fvq9VyHOfZ2wiCYGlpyfd9Qsjx8bESrq1WixAyHA7z"
    b"PB8MBnmeD4dD9VsAmM1m7XZ7PB6vr6+bpmnbdqfTUS5frVbV4wmUWRUclGqp1+tHR0dra2tB"
    b"EJZ8H2OSpJlhWsE0rFZrgCBjBcJIUjyNAst1KKJLneUPP7hl2Y5lWdVqtV6v53muqGM6nSZJ"
    b"smDtReandrwUyp5gSHHqsy9lKcVziqFVCB8MBlevXg2CoFqtViqVXq+XZZkqEHqe98knn6g4"
    b"pUjH9/1araYEEcY4DMOVlZUoinRdPz4+NgwjDMNer1epVKbTqaJCZaM8z3Vdj+NYSRPHcZRX"
    b"Kk0zmUwwxlEUOY5zeHhommaSpo5jO47nOZ6lG4eHR2EcAUKU0uls5vn+Bx9+uNRqM8bqzcb+"
    b"4YFtWSqAFEWh7KV24590uhOiRIOy2sITn0DsueeeU5ZTllr0IinGKZVKi50Ly7IajcbLL79s"
    b"WdbZ2Vm9Xp/NZkmSdDqdjz76qFwur66ujsdjTdNGo5HKxpWORQgZhkEpnUwm5+fnhBClAzqd"
    b"zmLdVOeFWhtFiOqlpK8iFCWvDcOYz+e2bUspx+Nxq9P2PM+kZpHE8/k848wuuVlRGJqmU02d"
    b"KE8Lx3PjPPN9//GjB75XUrJjd3dX0bE6/oKIVKBT+aOiXfUJaTQaCoELTKn/wxgrfl3MHgZB"
    b"oGmaitkXLlxQK2Db9vHxseM4lmVFUTQejz3PU5SHMR4MBiqGqiMYhqFqjSpdN01TeZlpmkEQ"
    b"cM6jKJpOp0VRJEmiYm4YhowxFbIV7tQBsyxTjgyA8yyP5wFnnOqUCyERSCHSOInjmOUFJWQ0"
    b"mXilEiKYUurYFsH49PS0KIrZbKbAruS3EkAKXGrN1E6zcklCCGk0GiopWayw2q9XV7ao1SdJ"
    b"opg4TdPr16/neR6GYaVSUeO3lUrF9/3pdKqSYaUD0jR1XTfP8yzLer2egqGqPbiuqyJmEAR5"
    b"ni9g5ft+EASqJqNpmoqMS0tLKu9ROohSqpIhdT+z2dQ0DSF4kiWMc6prSZxQQvI8T9NUSBnF"
    b"kWkaR4cHnuemSSy5ME2zXq8fHx8XRaHKG8p1CCF5nluWpWxnWZbqZPiZ5125cmUxt28YRqPR"
    b"iOM4iiIVGtQlWpal63q1WnUcR22IBUFQqVT6/b66PWXiyWSiqgvqSR9qs1aRmm3b8/lcSXBF"
    b"nJZlqTRQ1S1M01Rqg1KqHg6iwqsSvVJKVVwLgmAhhbrdrlISUsp6va48oCgKx3Fms5nSAepP"
    b"FdMVgaqd43K5fHx8vLu7a5pmHMeGYSh+VHBRBS+EkCod/ywaNptNIUS5XK5Wq5TS0WikXENZ"
    b"SjmaZVlxHE+nU3WmZrNZrVaPj49VOqkKHUdHR57nTSaTNE3zPFdlFrUVUhTF/v5+EASmaary"
    b"ofLEJEkWD0ATQsznc1W9efz4saIqFXYnk4mq9qh0fTqdEkKerXwRQkajkRKAYRgqF1MBrlar"
    b"WZalkj5VLKjX651OZzAY7O/vA0Cv16vVaooKFBepjRvlUiqZWTyHijQajfX19aIoVJIMAMol"
    b"VVqknpg0nU4Nw1hdXVXj8OVyWS2Uunld14MgsG1boUOdWGVzioy73a6q5auWExXsFKyklGEY"
    b"KuJTGY9qN5xMJqrIo7IoFeMHg4G6QlURjKJInahWq5mmqaSTWl2lzlTT3nw+V+5v23a5XHYc"
    b"h1J6eHjY7/c557VabTweqxtRiZRyKVUsU6nozzTqzs7OeDwGAOU4KllTjwZwXTcMQ5V22Lat"
    b"bhVjvL6+7nme67pJkiwWwfd9RW2apqnTCyFUgqlkmqpzxXGsCoSqfq1yoF6vp+u6gqSqvVSr"
    b"1b29vVqt9ujRIwUZ5R0KeipmqZYxlWk6jqOYUSFauZ6iP8U+qo6odFySJOPxeFGzVA/yU6v4"
    b"rCJVt6acTFVKSKVSUX6nmGIREXRdV25i27YiQl3XDcNYWlq6cePGIteVUp6dnSlmUXZZ1DQU"
    b"JG3bZk8r2WEYLtghSRL1uC9lPuXyKpBPp1PFDOfn59VqNQgCdQPK5dXmJkJoMBj8f22dyXPi"
    b"VhfFNWAkhEBiFFMDjt0e4+rOwulKUtlkl002+Z9d2XWlk1TKTrttYzCTQExitMW3+LVe6NTn"
    b"RaqbuAFd3Xfuuefc92Tb9nq9dhyH1C6VStRKiunLywsYAhLl8/lCoeD7PjIGgLANDzpCXwQN"
    b"Sa7NZsMHiVNFFExDOTys5+XlhYPtkCwAYyxYwzCwNn777TdQ3DRNSZKSyWS5XOYjx+MxMhAf"
    b"kE6n+Vrr9Zq2ebFYoEzxVbrdLqIzfb/v+7e3t6QA92w4HFIouHIGXyEQ9AaVSoX+yTRNFgQS"
    b"ueM4ME8oTrFYRAqm9H8eqFXV5+dn3/e5E7sSja7rREZoVpvNRi0Wi0IMpOHgekA1FDgOMVsu"
    b"l77vdzqdX3/9FcKJ0kLuULlgkoiZ/AGyPhgMTNOEFrNIFUVB6vF9X9CCdrvtOA60i8k64kIz"
    b"CNzA1GCMtm0vl0vbtlkHnufBQtFagyBwHAeEJh8pLI+Pj09PT7CE9Xodj8dhDxRQcToW+chV"
    b"fNaXyuWyFA6GcIIRwLQNjxBkxXLHKD30iXCCdDpN7Scugr8xxsR7Qu2AGPQpDgzjxjCxEwTB"
    b"YrGgPvDpICbORSQSwSe3LKvb7RqGEY1Gs9ks6qBhGJ8+faLHIiiMJdCBcyPJrNFo1G63//rr"
    b"L/xQaguJAkIBVf9GR1VFECRJUl+9ehUEAfcKHoSEJFokZDAwy7IsbjUIiv4XiUTANWQvVEfe"
    b"Z7lcsloBEaIZi8V0XWe8iYVGaQMyCFYkEkFBlGUZvgJpCIKgVCp5nhePxz3PI8uE1UTd4BAb"
    b"cJYifnBwAAqbptlsNgEy0genTg619l31ih9A/DPP4gTcbXiwKdEhxcRQDasdjvfq1SucCNM0"
    b"U6mUJEnIhC8vL8PhEImVCUwwfrPZPD4+CiID2fN93/d9bCFqkOhgqdbYB3BdWZYZna5UKjga"
    b"3BXK4mw2A9RZudyJSCSSy+Wy2axhGLlcjroxmUwGgwEMi09nYlbEQg6PvxXKzOfD+4IAzV2t"
    b"VqtKeG6dAC+gB7oRjUaF+F0sFp+fn8vlsu/7pVKJegwisi/D87zZbBaJRMAp+kHwKBqN2rZN"
    b"qs9mM3gDtZk2O51ODwYD13WTyeRwOEQOoctFU/Y8jyuHWBcKhfF4TJ9I4kiSxNQnUqJlWZVK"
    b"JRaLDYdDyIeu6zc3N/P5HMkTzBFE4T+6HsFinbEe1VqtJlzo3dNOqYDkGvLIZrMZDodYOJeX"
    b"l5vNhiacJPI8r91uJ5NJ27Z7vV4QHlhL6GErcNFGowE802ACQJ7n4c7yhuIAZTwFnGHhfUJi"
    b"1ut1KpWiCMKt0um053mxWIyhDdyzyWQCL0ELQw5iIePgkonIWOJHeKC7iaZWq9V/eUT4Q+0U"
    b"fRw3Qdf1RCIxnU7j8fj79+/fvXvHOCA3J5lMplIpJit1Xedi4PHgApnseR60G46O8kPIQCtB"
    b"cBaLRb1eJ7N837csa7FY8MuJRILc/3zDVRVUHY1GjPXT4pim+fT01Ol0yBdFUVar1d3dHdY8"
    b"vFLXdapNJDwV+T/IJTJOlmW1VqsJRYKUY6WIcTcpPH0TiMXuPzg4aDabx8fHmM+KoqB4CIAD"
    b"FGhWBDOAxENfc7mcLMu8m9ipQDGh6u3t7fV6vUKhIMsy7k6xWJzP5/gd0Wg0FovBS6LRKFWF"
    b"1YfSLcvy3d2dZVnFYhHddTQa3d3dYe1UKhWKFV46mb4Nz74V6h7BEhqyymwMN4pluFsHISC8"
    b"TjQ5hliSpMvLSwwSuK8cjsPNZjNkqVgsRvu+XC4VRaFZm8/nUFO+32KxgMTJ4WABVRWnM5FI"
    b"tFotyBQqBZmu6zo3qd/v826yLNdqNQoLXudkMmE/xHw+Z9BD07TNZkNBazabT09PQO1256w1"
    b"UdOE0qDsnOOqIuO9hKeakhf8SzACcgCWQe6Xy2WlUsGAAPjpctBCWZWLxWK1WrmuGwQB5sJk"
    b"Mmm327hn4vdJNNQFposURaHNpNF5/fr19fV1KpVC7TFNk4/j4ESyidixpqrVqrhUSDJ8hfx1"
    b"Xff6+vrx8TEIgkwmw20AUgkKiw41RRRHkTfq/v6+FB4XLKJLFZPCA175MIiloiivX7++v78/"
    b"Pz8HU3nT6XTabDbBBdFkGIZBK4OJj+AZiURs2wbLOW4UwELwgk+Tv8/Pz/F4/OLiotfrGYZh"
    b"WRbyA5ioqqrjOOVyGfXx6OgIOxI2EI/HwSNEyslkcn9/32g0rq+v1+t1qVTi4xik4GLJD+Hx"
    b"cAkC3RVFUff398UKQg4mnAx9CPDjRQqK53nHx8eKohwdHSmKous6C01RFM/zRqMRRRcPjTmk"
    b"VCrFv5VC31vTNF5kzQrGzFBYu91erVb5fH42m3U6nWKxCGWlpFA3aPvpHCErONiNRsP3fVj0"
    b"crlMpVKbzabRaLTbbWQJaBf7cJjMISegAbyt6BZhJERN/eqrr+TwBH9RNUQmEzuAn71OXHy/"
    b"33ddl5UIxArODYJgf7HAE4nEer0m77BUUayg/oyHgFaLxSKbzWLcs4uoUChks1m4eK/XIyjU"
    b"+0wmw5wPmZXL5XzfZ+FXKpV4PO44DuCIV9Rut5Gk6RlZ1+QHCQVeswa56pedvSeKoqiHh4cs"
    b"MZFWUnjCPk4yHEdRlEKh0Gq1eF/WyJs3b9LpNMlPiJnwe3p6AuCBDLrFUqm0Wq2y2Szq5eHh"
    b"YSaTabVa+K/sQgDy6ZCQNHhPSjYzeTRbtMq4cPl8Xtf14XBIW7pkkQAACCNJREFUIti2rWna"
    b"3t4e6uPz8/OHDx/6/X42m221WuPxuFqtappGZnHJ4M8ufwbjgFfBGVWsMK52l1jJ4QHVTJHJ"
    b"stzr9Wq1GurS5eXlarXq9/tff/31Njy0Eo1lPp8zYkn/RdVDn2FQDUBZrVY3Nze0/pybfHNz"
    b"8/btWyosF1ksFpHrOp0OWhidFu23YRjVajWTyWBtUM01TePmocQye8UYi+u6kG16cngMBA2c"
    b"ETqf6E+DnbP0FUVRj46OpB2HWhAz+B7ojspuWZbneQcHB8PhcDQaXV5evn37FvrKtyTi9Ia7"
    b"vbHgAdwMdB7XdXFAUA7++eefQqEwm83Ozs5UVSUEsND7+3tWOu2qZVmWZeVyuVwul0gkqDmm"
    b"aTIJQNZDxIRUx0A/SrFt24RGSDGGYQRBAPyRaPwCq0rQriAI1OPjY7H61C8Na0LO54Eg3Fsa"
    b"WkmSGo3Gjz/+aFkWg4CUAqGgJ5NJGn1gDlUE5R6Ioaej5FM0j46OVFXl+lGTJ5MJAjf9VrFY"
    b"nEwmvEkmk8lkMqPRaDKZrNdr4judTm3bliQJFoIixCgZy61YLBJ6AFQQi90GebtztnIQPmtG"
    b"VVWVukbxovPiAoguRQGyC87xCwcHB4PB4PT0lA5DiEEQAk3Tut1uIpFIp9P9fp9mjZbb9326"
    b"MFEZuQDGub/99ttYLDYajYgvDTBpkkwm0+k0pME0TRDn4eGB1o8JL9d1gcjtdptIJBCwBoMB"
    b"XJqTrT9+/AippgMVfZiQaERlEzGSw1kQ9fDwEEijKBCml53navA6ZqQUjk64rvvDDz8MBoNy"
    b"uYwzTM7jOOzt7eXzeeYQX15e+v0+SA9f7/f7vV4vmUwyC6lp2tXVFYZgpVLpdDosltFoxPRa"
    b"EARsisTgUVWVm9fpdJANkM/W6zUrlM4xGo22220qEj/NZpNOazAYPD8/01ERCJRbeWfkXQll"
    b"K9EzSpKknp6eyrLMvArTqGL6TTQBcvjMCCkUpDOZzPv374vFYrlcRmslEAK5+v1+LpdD3np4"
    b"ePA8r9vtSuHeO6SCRqNh2zZfnQHyDx8+VKtVij1rdjqd0j9Cl6iSmIO4JHSOaNDJZJIVjfm4"
    b"Wq0qlQrTqovFAjkkkUikUilmX03TNAxD0zRwcxe7hbD1RbBOTk5Qbcgp4U6r4WNJgvDRKOCa"
    b"rus446VSSdf1Wq1G80iJ4X2WyyUMo9frNZvNer1umiZRQMB4fHxE9vrjjz8SicSnT5+goD//"
    b"/HMmk8FQYKKbBMTRApXhlo7jwO/j8TiTXPBV1GpMOSZ/GNskyplM5vb2FpyhSjI8QGVAlhGs"
    b"nTUkumhZltWzszPiF+w8ikGINvKXQ24EDp1fUZRut1upVAg3JRmBQZIkXNVsNus4DrnpeR5a"
    b"HdVqPB7jj2CsXlxcHB8fM+qWzWaZzEOr4VuRO4iLpmnSJyPV4tBg/eq6PhgMer1eKpUCyLm6"
    b"fr/fbre32+3Z2Znv+4eHh8PhEANNkiRu8zacuN1lBbsZp56enlL4IBpgHlqPCNZuMxmJRFar"
    b"FYpluVz++++/f/rpJ9Eesih0XZ9MJkA1jJmqj+UBJOOtQcdB6Pl8nk6nsdpVVUVWlyTp+vqa"
    b"eH38+BFDiDLKTAYpwwhcp9PhIimaOD1CL7Esy7bt33//PZFI3N/fHx8fM6uCOURZkEP7XlTD"
    b"XVIl//LLL/yFEo4PJkqmWK6KeJpMEPBrjuO8efPGcZx6vR6Px2m7ABEAmNCwUUAJn3qEY8hQ"
    b"xXg8brVaUOdYLOY4DoCNFSp01FgsRsf78PBAEKHXpVKpXC4bhtFsNiFlp6enqM+NRgPbAs2a"
    b"lGRIwjAMZGVRpgeDAdyYgXaCK1j78+7enYuLC1RNdeexKcRLrER+eH0vfFCNqqq6rufz+Vqt"
    b"BuHu9Xqr1co0TT4VBGEASpZlTdNAdFVVJ5OJ67oPDw/pdPr+/j6VSjmOg79bKpWorWAWky2d"
    b"Tmc6nQLJbIlhfnm5XE4mE3gDIe50OrSQpVIJ+Yg6zk4IgUSPj483NzeapjENu91uB4OB0FcE"
    b"SZLDJy58xqzT09Ng54F1Ii4EdbfHVsJJcfrYer3O1KzjOJIkMVfEbATfbLszqIWSqapqv99H"
    b"5zUM4+rqinkAWZbj8Xgmk2GYy3XdzWbz9PS0XC7n8zllFHFN1/XRaIQsQxZDwdGz6B+KxSL3"
    b"ibZ5PB7PZjMSNpvNTqdTz/PwgYIgoPFCO/lM01X1JXxIh1hSn3vB8/Pz/4TpXzwLx83F/5LD"
    b"kUlJklzX/f7777/55htZlukVEPagPMlkkqYHekny9no9sH84HLI6ttttoVCwbTuTySDLBEGQ"
    b"TqfZDEOBkySp1WrJslypVKLR6Lt376gS6DwvO89T4q5ATZj+SCaTpVKpUChsNhsYrOM4BwcH"
    b"V1dXZ2dnf/75J1QjCOfZuGqhU5Fo4v3/T7D4r3CGg/CpXOIPmqadn58fHR1ZliWm1TFfdxsU"
    b"dsNQkjqdDujALoy9vb12u12v129vbxkta7fbWKT5fJ7vHY/Hh8Mhc1hsHpJl+eTkpNlsdrtd"
    b"ODotFFwUvZS9ZAhk2Wx2sViMx2M01f39/XK5zMTdyckJHe52uwWtIuFGAQFEcvggI8yhLzJL"
    b"5JQUOrREnbJFjdA0DYGl1+t99913hUKhXq+vVivEP2GasoPFtm120VGMWq1WEASu6+ZyuYeH"
    b"h1gsxow3l5TNZg8PDxHIZVkGzvv9PtuQQatMJgNyw9GRD2VZxqdYLBaM21H4qEJcAsAHPGFc"
    b"c/6VGL8CKwRqb8On6kg7QrOqqv8DjxomFsSpzQwAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_play_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAFKSURBVGhD7dm/KsVxGMfxX4pBNjLJ"
    b"qpTNYDqDhUuQO1DcgMEVWIwGC5egcwVyATLLjAUpSf68H3zrk4iDzu/7PJ53veo426fw/Z3v"
    b"abIsy7KspbYx/vrSd5e4wPLLT46zIU9vupiEy3SIucYqBuCq90OKQ0zDTTrkRl6bO2xgCNWn"
    b"QzrYwaO8Z44xh6rTITP2Bs3jBDrmAVsYQZV9NMQaxibuoYNOsYjq+mxIaRZH0DFmD2Oopq+G"
    b"WINYxy10zDmqOUi/M6Q0hQPoGFPFQdrLEMsOyhVcQcfYQbqG1g7SXoeUJrAPHWNaO0h/OqS0"
    b"hDPomFYO0t8OsUaxCx1j+nqQ/sWQ0gLsnNExfTtIc4gU4lfL/R+7+3+/IQ5E948oIR4a3T/G"
    b"h/hg5f6jbpjLhzDXQcr1BZ0JcWXq/hI7xNcKYb7oybIsy/57TfMMeVT4gW4EYDcAAAAASUVO"
    b"RK5CYII="
)


# ----------------------------------------------------------------------
icons8_move_32 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADiSURBVFhH7ZUBDsIgEAT5hH/U6HP9"
    b"T+1GNtlcSuEKHIlxkoukhduxVkh/OrnlWgKC37nCJRi+5QqVsOGhEhpun0CIxGsvDaKAimHO"
    b"VB578VtSAOAa7oWiAkuYKoBHev8Oi7QIoAd/smb0pXriwkWwFj1c/w4Ndy08wN1rZDhp7qkT"
    b"a1XiaK6tosRyAaASpxMduHuOlLjcSxee7e24jyphzw4XWFDb22sCQM+O4bQITGWJgO7tKoBr"
    b"tbOjG7u3UwBjvrQ9Z0cVDeKnjik2FZXQCgknViI0nFBiSThB8LLwXyClD9l3kJtafbLiAAAA"
    b"AElFTkSuQmCC"
)

icons8_move_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"zUlEQVRoge2Z7U7CMBSGnxhN9I8OZEPh/u8AE2OiIVFQgciHIsLN4I+2aZ0BaffRzfRJmmwj"
    b"63lfoO1pDwQCtSWSrdZEwCvwBlx61uJMBIyArWxTamimAYzRJkwzLY+6rGgBM4TwL7QJdT2j"
    b"BmZiYI4W3kEbaQMf8voTuPKk8SDU32mJFqqMIJ8t5f2odHUWvAATIDGemUaQn02A5xJ15ULa"
    b"SCEcFR2gLIKRqhGMVI1/Y+S4hBhPlDD9HkIMPAI9D7F7iAwgztpRC507DbN25sBQxl6QIdGM"
    b"EKmESgCvc5FmRwy8Sw1zHMxE6ARwjR8TigSdNc+w2JxdoHd2a0Qq7ps2OmueAs2/XkhvT22a"
    b"y2Rw4xhrTOpAI72OnABnDoIAzkt6B+AUoXUvmQdYAThPPM4DrAAyTzwJlgOsAMyJZ0OGiaeD"
    b"+Ba2QD8PZZb0ycGEoov4ZQZZO3JgIGN3PcT+xR1w61tEHoTDBxuCkaoRjFSNYGQHPeABUejZ"
    b"RQO4p+Jri9rfT9C5mbmONNFZ7KJ0dRaY9Q9VZlNGzHLchoqkHfvo8LPMtk1dq0pWLTDLbGar"
    b"lQlFgt5pboEVNTShSBCDeoXfI6VciMnhyDMQ8MQ3mEmjvi1225cAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_route_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAHQSURBVGhD7dZJTgMxFIThHIIlK2Zu"
    b"wIYdO7ZwAeZZnDV7FszcATFUCT/JMk7Hr+12/KT+pRJR6LjzKSCYjI3Z7cjNdAR8uZnFCOLH"
    b"zSQmRJjEhIgPN1OYGGLbzQxmFkIygZmHkJrGpCKkJjFahNQUpi9CagKTi5AWiimFkPjad6wq"
    b"pjRCqoophTh0X8OqYEp+Eo/Y/d/Dfw2KKYlghPCcqpjSCCYQrgpGg1jGVhL3ismZ3KAY7Scx"
    b"xeTaPhsEo0WwXMgntobF6oXpg2A5ECIOsK7UmBKQfT7Rkf/LnoJgW1j2p8IDND9aqZBBERIv"
    b"/MbkxTyIB85KC9Eg3jA5m+8pGSFpMBrIA5aC2MSyEdIx5mN4MG8QpoHsuq9dxRB8L1mlYDSQ"
    b"efFs/49mEYR0gvkY3sjH7GB7bkt8omcbWIjgvYt2ioUY3rhUMQTvOUhDYXjGC1YFIZ1hPoZv"
    b"IAezjoUI3qNK51iI4RvSFkPw7KqFmGdMg+G1fM1CEdIFFmJm/Rfrx2tCBM9aaJeYBhND8Iwm"
    b"imFWsTA+1yxCusK6MDEEX9Nk15iPecII4PjYR/DapothzCGkG8zH+Ah+z1S3mI/hYz5nMsGY"
    b"Rkh3bmNj9ppMfgF/kbj+SZ89mgAAAABJRU5ErkJggg=="
)

icons8_resize_horizontal_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAECSURBVGhD7dhZDoJAEIRhzuNyKJcH"
    b"vYnn8VjewaWbUMkEDRGmu2lI/UmFt2G+RF9oGGOMMcbaNt3TMo8zB7vInt3TKo8zB9MXvWTv"
    b"7nmU1XaWlWe6Y0qE7iHbymrbyfQsnOuK8UKgEIw3ArliohDIBRONQKaYuRDIBPMLoQdHV4XJ"
    b"gkCTMNkQaBQmKwL9hbnKSoTuLrslm96pvKPeWe/edpD1EUua3l0N64Foq/hpoT5mCX/2LwTK"
    b"ihmFQNkwkxAoC6YKgebGmCDQXJi9zAyBojEuCBSFcUUgb0wIAnlhQhGoxOjT4gPdSVae6Y5A"
    b"+iLrz5s4MwyBVvERmzHGGGP5apoPcwpl40zo9wQAAAAASUVORK5CYII="
)

icons8_resize_vertical_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAFSSURBVGhD7doxTsNAEIVhi3NwmECB"
    b"aJLj5VQUUHOOFFTJPMlPWq1md8aRbM+Y/aUnnBRxvm4NTKNR3j7mpe4i+5uH65QRcZ+XElMj"
    b"UmLOMg3BpcBYCC40pkbcZF/Fa1zjPb4OidEQb7Jr8R6u8V5YTAuBaggKidEQJxnTICgUxkKg"
    b"FgSFwHgQqAdBu2K8CGRB0C4YHP68COSBIA3zKVutV9mvzINAXggqMbgH7rVquMGPzEKgJRAE"
    b"zLdsdQR7mX9aLYUg72dv2jOQkA1ItAYkWgMSrQGJVnjIIY4oPDTigGe1FPIuw2dvcvItj/EW"
    b"ZgkEiM2O8dqDVQ/jhZTPItjqD1ao9+ufOg9EQ+z63K5hLMiuCObB9CAhEMzCtCChEKyH0SAh"
    b"EayFqSGhEUzDpPuzAqsxrYVGMAuTAsHwRTVMKgSrMSkRjJjUCHaIf+EY/dOm6QETlEg8SIvm"
    b"sQAAAABJRU5ErkJggg=="
)

icons8_save_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"XElEQVRoge2YS1ICMRBAn5aFx9E1eD0/HEV3bLwAehOHjZ5BXBBKoDLm051Jl/SrSg1Uejp5"
    b"hGSgwXGcUmbAEtgA207tOcxDxFNHgcO2ksoMIdF8pH8/UAv2ub9QkElNdAqRG+AzvH4FriXJ"
    b"avtTvHP8FVqP5L5FuDKtRWL7YSy3aGWmEonliuWulrEmApUyFkXgeM+8lA5U01+Sv0QEdjJb"
    b"4Lt0oJr+kvylIqMxl4IJSVF9FvUQeTt5v45GKWDhyV4cU7Mim3BdVNz7F3fhOmglTH0qjwcx"
    b"Ldq9cH7ZgbMgM6Ar8BEkUr+p1ER6Y+74VcVFrHHWIi2rLAO7E1FcQYH0qTVFleVBML/swFSV"
    b"RcKC35UZQ02k9XOmavyz3uwmcRFruIg1XMQaLmKNHJHef32zxv83K3KVEXPRfBYK48dWpFUB"
    b"ToOiIl7rApxGSxXxgHYFOI2WW8RzHOeEH/58jcLJRDukAAAAAElFTkSuQmCC"
)

icons8_plus_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"yElEQVRoge3az29VRRQH8E+18h4Bhb5aYCnxJ2gqe4I/FmoRF2iiiYo7DG74EXSr/g8mTfxH"
    b"DBGjCKKxiigbawHdqCSaYOOvCkHzWMxM5tb0te++N30tCd/k5iR3Zs6PO3POnDlzuYnVhaGC"
    b"vFp4BDuxHXdjE9bF9r/xC37AtziNU5gtqEPPaOIVHMd/aNd8/sX72IfGgHUHa/E6LlWUuoKP"
    b"8Cb2YhtGcFt8RuK7vXgLJ+KYNP5nHBU+zkCwB99XFPgS+7GhB14b8SrOVPhdxO4imnZAE+9W"
    b"BH6FJwvyn8DXFf6TlmF2tgiKtwWnPYhbSwuJPA9jTp7tzaWYbxWmu41pPFSK8SIYx0yUeSHq"
    b"0BfGKgy/wJ39MqyBESFEtwWf3NIro6a8nD6T94NBYh0+l5dZTz6THHta2OxWCqPyqpisO3iP"
    b"7NiD8ImlMC4HgIluB62V94mDBZRI4bRfHJGdv6sl9oa8T5QIsaUMGcY3kdeRpTo3hFShjScK"
    b"CKecIfB05HXJErOyT44QpVDSkCE5kr60WMcPYqf9hQRT1hA4EPkd69ShJaTVV/SWAHZCaUNG"
    b"cBXXVPS8pdLhUcG5P8XvBQWXxqywSQ4LBznMN2RnpB8PTqeecSLSXelF1ZBtkZ4bmDq9I+n4"
    b"QHpRNeTeSC8MTJ3ecT7S+xZqvCw4Zem8qrSzE7LwNn5dqPFqbFzTBaO6RYa6z1JoyHUCzF9a"
    b"NzSqhvwV6fouxg3VePoZ0wl3RPrHQoZcjrTYGXkZsSnS39KLqiEpWi0YCVYZ7o80Ra95hkxH"
    b"+vDA1Okd45F+l15UDTkd6WOD0qYPPB7pqYUaR+SkcWNBoaX3kZacNCannzcjs/hQiNHPFxRc"
    b"Gi8Ie91xlaj1f7wsfL0zBQWXPlidjfxeXKxjAz/Fjk8VEl7SkGcirx91cQ1xNHY+a/UVH85F"
    b"Xoe6GdCUa72HCyhQypD0gWfUuBTaHQfNyTF7JbED/wg61b7KmJS/wGhZvWphTMg62ninFwZN"
    b"oSzUFs7IK1HEXo+pqMOUPu4Zx4Q0IF0rjJXQrku0hEJIuo7rO5ndKk/tjMHkYjsqMs/jrlKM"
    b"N8vLbE6ovQ6XYl7BsBCdkmNPySl7MTTlANAWCsqlbl+HhKuMtE8kx17Wu/cJedpT1f6AkHTW"
    b"RQuvyWlHWkolb4sXRVNYXimdaQsZ6Um8jWfxoBC218RnVLg0ei72OSkXPFLaccgK/QHREKri"
    b"x4QjQN1qyTW8JySAfRlQ8qeaDUItdpdQtbxHCNe3x/Y/hTrURSGkfyLMSsdU/CZuZFwHvZQq"
    b"HNfefn4AAAAASUVORK5CYII="
)

icons8_trash_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAFwSURBVGhD7ZmtSgVRFIVHBDEIahMU"
    b"X0AFg8EgWHwEQRCsPoAWq8Fg1SCCVYuCJvEHk8VkEGwWX8AsFl0L9oaDHPHOZZ87w2V98JXF"
    b"MPssmDn3cqYSQggBpuEBvIH3Ge/gMZyFrWUSfsDvDvyE87CV7MHcov/yDLaSS+iLPIWbGQ+h"
    b"X/MMe8oAHO/AW+iL3Lbst2vQr3m17D8HYQij0Ic34RwMQUWCDCvi78gu9JufWxZtbkbYO+Ls"
    b"QB/CXakEvZihInVotMgYXDGXGCR4TocZGAvQ8wkGRqNFuHjP3xkkeE75h9J5hJ6vMzBUpA4q"
    b"YqpINCpiqkg0KmKqSDQqYqpINCpitr7IIuSZL31hkOA5nWJgXEPPVxkYjRaJREXq0DdFeDDt"
    b"Qx4YFOAE+gye3BdhGfoQegRznw66dR9+Qb//BiwCj06fYFqmlG8wPT4Kh1sot9jc8Cj5WzQD"
    b"izME+ShcwNwHz269gltwBAohRF9SVT/YcCJDemJ9EwAAAABJRU5ErkJggg=="
)


icons8_goal_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"vElEQVRoge2a329URRTHP7ttY+VXy4PUmhCNNj4QoCXRBLUSrZBY22CKMaGAkb+gShA1URIF"
    b"bE1DouEPsGhgK30ioomJTXyAqqE8+SNqVaS/7LZoKNQHpNr6cO5lz5yd3Xv3R996kknm3u/M"
    b"mfneOefMmdmFZVmWJZFEmfUlgU3ARuBB4G5gVYD9DUwDI8D3wLfAQpnHL0kqgXagH/gTWIxZ"
    b"/gLOADuBqqWa3EvALPA5UBu86wcuA1tN200FEvCVSeAAsLLcRK6pQS4GZBaC5+seMltMn3lg"
    b"HBgGPgPOAoOIWc3nITQOPF9OIp+YAS6a5+vAI6ZPK3ACMZU1eXTfAWwDjiEr7CM0EKEjttR6"
    b"Jm+Lj0yhkkA+wJBH/wjQUKJ+IB6Zq8C6cgwGdAJpoz8NNJWiNEXGJ6LKYdUvCbQA3cB54Dck"
    b"7N5CQu/XwHHgcaDCM24d4kuWTNErk8t2faXfEInbbxp4Fag2Y1cCfabtCEX6zFbEB+JMaMD0"
    b"jbuSYRkDdhkdCQ+Zj4shAuLIcchYIl3AFHAKeA14EdgPvAF8gKyE1bEAHMXNNCrJNrPnlpLM"
    b"j2Q2zThSgfjRBY+uFGKeodThBoAxYEUpZK5GkBkukEwou4E5o+uoabPH4C/HVV6JpB1a1iHR"
    b"KYWY0gCyElFkksDTwDNIIpkkWzYjX1qbWYfCE8BXCp8gZm7WjuROWyLa1QaTjyLTRSYA/AH0"
    b"AGs9ZPTKjOJGszYzTnscIv1B42vI1yw3mTD0Nps2nUbPKwpLAFcUlooikcTNZE8YzHd+KZbM"
    b"TQ8ZnaqkcU2xR2FX8ZvpbWk0E9qpsBYyNtxVJjJp02a70fGYwp4w2OZ8RPaqhvO4u2m3wqY8"
    b"feOSOWTadCusAphRWK/CqoF/FbY3H5EjquGYwc4r7FSO/nHJnFP4JK7JnlTYkOn3q8Le1oC1"
    b"s7tUfcZg96j6d6quk79ZYAdwSb17CPgCqFHv3jN6N6jnX1T9ATOH8RxzzSKyWtUtkTpVn1b1"
    b"7bg+k4vM6+p52Oher+rabO1K3lB1J4nM5/m3zLPehBKm/j7RZCrzjFWyWOVzqr7aYLNkDlH1"
    b"6v0EGTKQCdmzyGodQhz1HdXnYaNbm4w24VnTTq/CDfKIdvYRg+k0oU+9TyI7dq7Q7JNPye3s"
    b"Hyrsgumnnf2tfAPsUw3nkYuCUI4rbBrXyfVmtYCsQi55Ezeq6ZUqJPzuyUekyQyyTWHNBntK"
    b"YWvJPmecQzbRVUFpwV2JcD/S0WyHwR9V2JMGs4mtI0nkBjBsfExhFWaydtmbkbRjMWa5aSZq"
    b"s9wp3GD0rsJmiHHde0Z1uGw62F15t4eMvQnxlSnc9APcrGIROKiwJG7SeDqKBEh+pRW2Kqwa"
    b"SbFDbI7snKcWSTsmPQQmEZ+oMX0akduWsN3vuP7ZbvS0xSFSZSZh04QO3MRvzEMGZCU3IB+i"
    b"Naj7zKERCb86WDxr9Hyj8HEK2JMO4H6BToMfMficp02UJBBz0ivhC6v7DB4nvN+WlbhfKY2b"
    b"oiSQw401nSEkmvku30KpQKKTdmxt+3rV6nEDzChwZyFEQG7F9SCDuEuaQFbGd481g2yah5Gr"
    b"oP1B/ST+i4wFJJvVJKqAL007fZYvSAaMoj6y7bwDNwAUWq7g+gTBGB+ZdpHH23xSg6Qqlox1"
    b"tmrkjB0n9OoQfBA3OoGshCXxE9m5X8HS4JngIK7PhJJE9odexF/SwD9BSQfveoM2vsy7nmxz"
    b"mgLuL5VEKE0eMmki8p0CJAG8QHaaM0XE2bwYaSDbzBaR6NNGcb8QJ5HNTu8T2pzKthJW1iC3"
    b"4rmcthu57bA/FWipRhLAHnIHiRQF+kSxv7PvQg5S63Pg/yHERpENDyQDvhe4j9z7zBjyi/LZ"
    b"IudVlKxALpQnKD706rSjiyI2u3JK+IeBFNG39nbTPI34V8nn+aX4C8dG/H/hmEOi0s/AD8iV"
    b"0mKZx1+WZSm3/A9x0g4/FKsS0gAAAABJRU5ErkJggg=="
)

icons8_file_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"R0lEQVRoge3asU7CQBjA8b/GTiZOjq2Y6DsQnsVBjAuPwOAD6FM4uTj5BCjREN6C0Jm1mwaG"
    b"c7gO9E76nfcN3z9pQqFc75emoWkBy0rSUeR2BXAPDIFTgf1ugEegFhgrugL4ArbCSw1c/aOD"
    b"SQKEOOY4YpuhxI681t7rCnhHABMDkTgn/KbAi7deAR/AdZ9BYyDS/QC3tDEl7sgcjMkBgQSY"
    b"XBAQxuSEgCAmNwSEMBogIIDRAgGHGQOv3nslMAMuQl/OAbns+OwbuKGNqXC/PZ2d9JvTQT3g"
    b"LlZXHdu84a4oBr/r56FBc0DOgCfpQTWdI70yiLYMoi2DaMsg2jKItgyiLYNoyyDaMoi2DKIt"
    b"g2jLINqKgTTJZxEuOIcYyFJgIn1bSAxSAJ+ke9YeWuZE3KP+y1847oAR8o+r99XgjsQz7nGD"
    b"ZeVoB0LBdk/cOVz+AAAAAElFTkSuQmCC"
)

icons8_file_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"qElEQVQ4je3VMQ4BQRSA4Y+o6NxBsfXWWyhU7uFOtA6gYhOtwhEUSoWKQkKt2Y2xwSw68SeT"
    b"vJc3+eclLzPTcKONRJwtTs+KrSBOMMXqhSxBBwMcYyenGEf2jDDDGt1Yh3XJscMCQxy+FZZS"
    b"mFelnwizIN5jib5iUM03ZSv3Q8txRu/TDjfFCknD5N0Oo/yFf+FPCqtXLxN/E6tkmJRJIyjU"
    b"/QIescEFrkM5GgOS//FxAAAAAElFTkSuQmCC"
)

icons8_vector_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"yklEQVRoge2YS0oDQRCGv4TgCURBAxp3egdd6BkiIngCEQSXwYXiYiKeQpc+Alm5EK/gKYwS"
    b"Nz52URMXXWPCMEPPo2cSQn3QTDJ0/39Vd9e8QFEURVHSU3KsNxiXf9mV0Lip5KRrm+mkK2el"
    b"DMwATaADvAHn5JegCyrABSbWZ8DD5ICHmaHR5qU08ce76hdGk5B4S5isFlKKRlH01upMTbGX"
    b"gauQ8x5mVm1tGWg7iKMNLMX0bIaMvwRTKB5mi3WlY5xirwNfmG3yCZyQvEZOZexAtOoxxlYw"
    b"F6QugWJPwzHQlwBugNlAgDZG+80Bd/K/L9qF0BDTH2A/IsC4bZQD4FfON3KK/Z9tMfqW30Gy"
    b"JAKwg5mgQYS+E2rAu5gc5mUCHInHB7CSh0GLYU3kjV8zLdfCGwxnadG1eAhVhlfEdZfCtyJ6"
    b"5lLUgv/odO1KcB5T3D2KWQ2fqnj2MJfozOxhZubBhVhCHsV719YxzrPWphzvs0SUEt9zy9Yx"
    b"TiJrcnxKHU56fM9VF2KvmOWtuRBLyIp4v9g6Bt8bxvbxIKv/1LyPRD2uF/7xIKv/1KyIJjJp"
    b"aCKThiYyaUTdR/K+T9hI7D81K6IoiqIoCvAH9xeE5oCkha8AAAAASUVORK5CYII="
)

icons8_vector_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"JElEQVQ4je3SvUpDQRCG4ScmNooK/tQBCzsbTWOhtSAiURCsLIR4D2qrhZdgITbiNVgrCBIr"
    b"i4AIxkYQgiEIaQSxcENO1kMSsBNfOLDz7Tezs7OHfyKKKEdfsVtCFmvYxA0+o/0l3GEXJ0Eb"
    b"DlqSQRxgLIMGRvGA98g4iaNEsRL2UIt8I5hBI4djFLCDt2CYxhnqKbeqo4ltPAVtHKe4TfHL"
    b"4x5zoaOq9vyqQZsPnnxagZjrkNCLQvB2kI3iZUxoz6wbL1jABx5b4kBkWsV5H8VaXGAlrcN1"
    b"LGILr5j189eIKfme4UboMo9KJmyWdV5zX++BP+MwOqDQCsqROY7TSM2JZ/hrcol1KbGe6iN3"
    b"KspB+1FqGEroV3o/SjOKL1Hpo5G/xhdkBjoJ6swePgAAAABJRU5ErkJggg=="
)

icons8_system_task_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"TElEQVQ4ja3UzStEURjH8c9goWyxY1jITkrs8AewoPgLSLKztLJR/gEpxcbWwsbWhrLwlh3K"
    b"S40lKYlmIxbnjJm57ryU+dXt3OeeX9/znOc852bQiS6N0VMG1zhqEHCsCR9YRf4foHxkfLTE"
    b"DxN4x26KeQD3ceFKmo4MBWAzcrhIMW9iXfWyDEWGpiomyKIPwzV8v6oFnI3ZNQw4hR101OFF"
    b"sYbQja2SuBlveMWtsPUnrKEtwXkWzqAM+IL9hDEXxzOMYBkPOEz4RtMy/JR+ynCKDdxhMWV+"
    b"qPBSV11wiW8s1DIWMvxCb+lKKZpDT3yS6sYjZHCOSaygtb6E/ygvtNeBCPyPloRDg/OWas46"
    b"dSLUF2HL2xisYG6P40uFOKmrTIWJcfQr9tdxHEvjGyk/jDRgFntC5tU0jxnF5kd5YxfULrRQ"
    b"rZ7LCne8DPgDBhc9y356EnYAAAAASUVORK5CYII="
)

icons8_direction_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"yUlEQVQ4jc3UQUqCURDA8V/5RVAtwqBw0TmkGyhoeA33LTtHuGihtIs2FXoCpWu4EFwpHcGF"
    b"84ELKV7fo/pv5r1h5s/AYx7/iBM0cws/0MkpPccUt2XiIOIlVlFQw3WCtI5H9DEpItnCGDc4"
    b"insKxzHlJLFvL3d4RvFd4a/LrvCQS/Z3FBig8VPB4c65hiEWWFYaK2RPuK8qKjdlgB5eE/vf"
    b"wzFDF6Pyyd/QxgvWCcJ5xE97tqRl+3tcJE75JZ2QnuWUNnGaU1iJDUKqGvOJPKhrAAAAAElF"
    b"TkSuQmCC"
)

icons8_scatter_plot_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAGYktHRAD/AP8A/6C9p5MAAADtSURB"
    b"VDhPzZS9EsFAFIUXjU5FT6FEpVFTKAyFFzKeAk+g1niJtLwFJYbhnLtZk2wiNkuRb+ab7Nlk"
    b"bvYnG1V4SuHV0IVt3XTmBvfwIilCBz7gM6dX2IcJ5pAP/EQ5vP6NrIIreIYzSY5kFeQS1OBY"
    b"kgf2Gk4gR9mU5DHib5tygry/luSAXbABR7AiKT5i9g0hn/mIXfAAmZeS4iwg7x0lRcjaFFM8"
    b"+hJDWl8Ce4R1yGmZKU8h168FvaZsYzZlI0nDs0/f5DkpW8jPZidJFwpCe+yw4fd1100nWJA/"
    b"ExobpaEKB7rpDP9QqcWKilIvu2w5UIty+GoAAAAASUVORK5CYII="
)

icons8_bold_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"t0lEQVRoge3ZS2icVRQH8J/axCrUPrQ+qlB1UaGCSuqLilAUEbTUggtBpRVR0o0ggqBkZTfi"
    b"RisKVUGh4ANd+IAspCqoGBdVWkUqVtCurFip9RFN0gTHxbnjTGK+b+4kXzKDzB8+zsA9c+45"
    b"37nndT966KGHMpyUwXMedmFVRXv+htFED6VnH/6oSH4h7kNtgZ8JvIftOGUuSuZ4ZAd2YxhP"
    b"z2WTGViO03AWLsF6XIv+tP41BvFJBXtNww7x1nZXLbgJy7EN36a9xnB71ZsshiF19OHJtN8k"
    b"rsj948kLpdEcMYmH8AyW4MVEWyKLKQNLsaYFzyiOZsp7FFswgFvxztxVayDnaI3Iy04n8B2e"
    b"E4Fehp3pP3vmofs05BhyPPEcForO9hw13agx3FEi8+rE99X81G+gHUNWtJDVh43iLdeNKfLM"
    b"2YnnpxwlFzvYJ/GpKHx7RGwNFvAew984U4aencxa9bN/ZcF6TaNg11oJ66QhxxJdXrC+Rhjy"
    b"sy43ZG2iPxasX5folznCOmVIvyh88EEBz/2JDucIrKog1rFCcSPaJ7wwIIxYJ7zxwiy823Gj"
    b"OH4v52xctSGH2+S9TcwlzdgmjKvhQfyaI6wqQ97EVuVjwRR+EYPUsHjTY03ra/EsNgsjHpHp"
    b"jVwsRve7UhhZE7WjrOLPim7pfsfELEJ49THc3I6AbjFkXEyJG/CqSATvilOQNfpWFSMX4qoM"
    b"vnER3Ac1CmIz9uMuvITXxbGewgNVKJkTI/URtZ1nH+5UnCAG8GfivaGVklV5ZHWib4vGsAhL"
    b"RRN4mfDgK2KAulu8+WbsxxCewhPyPF6KKtv4Ok7FvRqZaqiArw9HEs/lZQI7FewTIg62CiUf"
    b"FkrPxCTeSL83lwnsdNb6GF+IDrjo6IwkWtTuo/OGEBdyNLrhmfg+0QvKhHSDIfUg7y9Y/z3R"
    b"0vjrBkPWJVo0l6xMdKJMSKcN2YhrRL0YKeCp35eVXkJ0ypBl4pZ/OOmwSxgzG9YnerBMYNXz"
    b"yFv+W9iasQzn4xyNdPuaaBKLUL/Mfn++yuUUxEPaa0+m8GFSsmyG2ZL4jyhOBqjOI9eLtqMV"
    b"RvGDOO8nWvCuxvPp984M/pZYzM8KdZyLz9O+e2V8kOp01poNN4nbyA1irr9Hl99rNWMJbhFZ"
    b"bC8uEq3LJhEfWQJycQYubk+/WXG6qNKrcKmYOzaJb4pEJX9cpOTxCvb7F4MW/qtuTdSJIZGa"
    b"20aORz7CAcV3tO3iLzG/HBffTQ7gM3xTkfweeujh/4x/ALbGH+I/qO5zAAAAAElFTkSuQmCC"
)

icons8_italic_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"LElEQVRoge2ZTSuFQRTHf14LKZHIRpSFknKFFSI7G0ufga/mI9goG9d12SgLShaKiPKW12tx"
    b"ZrrjGlceZ+bpqedXT3Pvv+495zTnzJmZB3JycurREMnOOrDi0c+ANeA5kh//ohV4Aio/PKPp"
    b"ufY3JhGHT4El86wa7QFo1jCi8ie/MGPGbWDTfF42Yxl40zDSqPEnvzBlxl2PVtQyEiOQaTP6"
    b"AtklI3QC78AL0OboF0iNDKfhVBIWEIf3HG3YaNcoLv+hU8umVdGj7SABqRA6kCiFDvFmJNOF"
    b"3o+kzj3VftVkvleAPk1jIWfEzkaJatMbAzqQLn+haSxkIL5a8BW/CjECyXR9NABXSC0MOvqB"
    b"0ebTcCoJI4jDl47WDrwinb5T22Co1LIptONoBWT1OgTutA2GDsStBV9PUSNUIL7VKXOF3gI8"
    b"Ah9Aj6OfIHVTSMOpJEwgDh87WjcS2BMSqDohUsuXVjPIkryPrFzqhAikXqGrd3RLrBnJXKHb"
    b"pveKbA4t9mg7koZTSZhDHC472pDRbgh4s6mdWvUOUkUUj7a1aAcS7WhbS6hAfGeQzBR6L9/v"
    b"c5uQDWIFGEjJrz+zjDi85WjjRjsLbVwztVKrD4gXSGbqA6pNb8jRykZbTMWjBNj7XPdo24Zc"
    b"Xn8AXaEd0EotXy0UkC37EXCrZOdHtAOJuuN10Xr1ZgM5p/rOY9aMJSUbUbBNz/dM1/mdGloz"
    b"soHsfGsp8fUlT05OTs7/+ATr8IVDpqnfoQAAAABJRU5ErkJggg=="
)

icons8_underline_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"dElEQVRoge2aQWtTQRDHfxWqBatIRWirRSu29KJIVTz10LNKToJ+BUX6CRS8KPgBBMWTB1u8"
    b"txdFQakerEhPCmqFinq1NoKxvsTDzLrlJZV5ySZdZX+wTHbe25n9Lzv7Ql4gkUgk/kceAbVc"
    b"e9qGPPPN5ukyJqi1ON5K03m2FEzUZQkagMJ5igqJliQkNpKQ2EhCYiMJiY0kJDaSkNhIQmIj"
    b"CYmNJCQ2rEJ+qu1VW871Q7BT7bdcv2IZbBXigg+q/ax2wDjeQr/aL7nYK5bBViFLueCuP24c"
    b"b+GY2vdq3aItNbi3DquQRbUTamfVlozjLbhYLrbLtdjg3qY5h/x49kL7Q8Av4AewP0D8YY21"
    b"BuxT30vNeTZA/D/sAL4DVeCQ+u5oonsB4t/XWLe0P6q5yoQ9UAA/8Wnt7wVW1XephbhTGmMF"
    b"X4NO2O0W4m7ICHIMV4Hj6isBGbIlmhEzhWzRDDijvpOaowIcbGG+f+UGslJvgb51k8nUPwMc"
    b"MMQZxq96hl+E3cA79V8PNelG9ADPNdEDoFv9JeRZU0OKdho5IMaA7drGgPOI2Ap+O53WGN34"
    b"1xfzwLZ2CgF5cC1rwifAHvUPIsW6Rv07jnzLgLv4mugDHuq1T0j9dYQjwEf8Njux7toQcBGY"
    b"A14jB8Kqfp4FLuCPWJCacNtpGTjc5rnXMYDfZlVky4wUGD+K1ElVYzzDf03pOD3AVeS8d4IW"
    b"gMvAJPU1MglcQR52TkAFuEYHasJCP3ATL8jSykhNBTliQ79G6wVOISt/FDlmd+m1r8AH4BXw"
    b"GKmhcoMYicS/yFbgDfZCDtXMf0oo8uPDRi/z28lm5NxcfgObzr2fydjmggAAAABJRU5ErkJg"
    b"gg=="
)

icons8_camera_50 = VectorIcon(
    "M 19.09375 5 C 18.011719 5 17.105469 5.625 16.5625 6.4375 C 16.5625 6.449219 16.5625 6.457031 16.5625 6.46875 L 14.96875 9 L 6 9 C 3.253906 9 1 11.253906 1 14 L 1 38 C 1 40.746094 3.253906 43 6 43 L 44 43 C 46.746094 43 49 40.746094 49 38 L 49 14 C 49 11.253906 46.746094 9 44 9 L 34.9375 9 L 33.34375 6.46875 C 33.34375 6.457031 33.34375 6.449219 33.34375 6.4375 C 32.800781 5.625 31.894531 5 30.8125 5 Z M 19.09375 7 L 30.8125 7 C 31.132813 7 31.398438 7.175781 31.65625 7.5625 L 33.5625 10.53125 C 33.746094 10.820313 34.0625 11 34.40625 11 L 44 11 C 45.65625 11 47 12.34375 47 14 L 47 38 C 47 39.65625 45.65625 41 44 41 L 6 41 C 4.34375 41 3 39.65625 3 38 L 3 14 C 3 12.34375 4.34375 11 6 11 L 15.5 11 C 15.84375 11 16.160156 10.820313 16.34375 10.53125 L 18.21875 7.5625 L 18.25 7.53125 C 18.5 7.179688 18.789063 7 19.09375 7 Z M 10 13 C 8.355469 13 7 14.355469 7 16 C 7 17.644531 8.355469 19 10 19 C 11.644531 19 13 17.644531 13 16 C 13 14.355469 11.644531 13 10 13 Z M 10 15 C 10.554688 15 11 15.445313 11 16 C 11 16.554688 10.554688 17 10 17 C 9.445313 17 9 16.554688 9 16 C 9 15.445313 9.445313 15 10 15 Z M 25 15 C 18.9375 15 14 19.9375 14 26 C 14 32.0625 18.9375 37 25 37 C 31.0625 37 36 32.0625 36 26 C 36 19.9375 31.0625 15 25 15 Z M 25 17 C 29.980469 17 34 21.019531 34 26 C 34 30.980469 29.980469 35 25 35 C 20.019531 35 16 30.980469 16 26 C 16 21.019531 20.019531 17 25 17 Z"
)


icons8_picture_in_picture_alternative_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"qUlEQVRoge3YUQqDMBCE4bF4/0tpz2WfIgmY4sNunMj/QZ+EsrMxsKsEAHjYV9Ix2W8rxS9V"
    b"kCOmH8MtkrT2HkygafznqSqiEcQNQdwQxA1B3BDEDUFuil4NNnVcjfGR02/GalDqa+q9GuMz"
    b"RDTnb1O4I24I4oYgbgjihiBuCOJm1NCY/oE8+0T24P/r7iO1srzMoqn31XdkplM51ScS/T6P"
    b"cOvOAADS/AAtmFEkt1mw4AAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icon_corner1 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAIJ3pUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VlXdiM3EPzvU/gISI1wHKR+zzfw8V0NDMNQFC2R+2lypaFATKeqDpil"
    b"+c/fQn/h5Yt1FDjlWGI0eIUSiqv4kM1+7as1Yf1eL++O7+x5na5fOCx53bn/jPPYX7HOtxtS"
    b"ONbbeZ1SP+TkQ9DxxUWgV82q7NiXw9WytW6Pv6kc99Vw587x08axxvvy+HdICMZgyPOO3PTW"
    b"G/zOqsXrj/VV1/Db+YJNula9vnTdPY8dXT8+BO/66SF2ph7r/hwKMvHYEB9idKxbfh67FaF7"
    b"i+xN8+kLBHma+9dd7ERGFpnbuxoiIhXpcOriyvqEjQ2h9Ou2iHfCD+NzWu+Cd4aLHYgNoNnw"
    b"7mTBSkRWbLDDVit2rmu3HSYGN13C1bkODHQt++SK6wDA+qBvKy754gf5DEw6UPNYdldb7NJb"
    b"lr5uMzQPi53OQhiQ+/qmZ4vvvK+CRJS61pp8jRXscsoamKHI6W/sAiBWjpjyiu960x1vzB2w"
    b"HgjyCnOGg9W0LaKxvXHLL5w99rEJZHZq2DQOAQgRdDOMsR4ImGg922hNci5Zizhm4FNhufPB"
    b"NSBgmd2wJMDG+whwslPduCfZtdex28soLQCCffQJ0BRfAVYIDP6kkMGhyp4DMXPkxJkL1+hj"
    b"iBxjTFFrVE0+hcQpppRyKqlmn0PmHHPKOZdciyseJYxLLIlKLqXUCqUVoivurthRa3PNt9C4"
    b"xZZabqXVDvr00LnHnnrupdfhhh9I/xFHopFHGXXaCSrNMHnGmWaeZVYB18RLEJYoSbIUqVfU"
    b"DlTPqNkH5F6jZg/UFLGw9qUbalhO6SLCajlhxQyIuWCBeFIEQGinmJlsQ3CKnGJmikNSsANq"
    b"lhWcYRUxIBimdSz2it0NuZe4EYdf4ea+Q44Uuj+BHCl0B3JfcXuC2qiro/gFkGahxtR4QWHD"
    b"puoy/qEev3+lTwX8L+j51fco03XpXEZq3aTpKjUeTkJrYfgYs+PmQssxtprHKNnblLgbcAPd"
    b"OqPRtBFbDiJg5BSbkwwDznpR+JtYn0TsqF70aykup5q0C4Kigvo8bHMjZdxkUjNJug9gevcy"
    b"s21oYTIkU2m6Nc9h9Yp7xkSXk4oBCfoEVkc0Vd94gpv8nSS0bAhTWYekixydFbYkY7YsY15L"
    b"o23Y53bRNuxzu+g+YJ/YRfcB+8Qu+grke3bRVyDfs4u+I9jVLlRZMaUhJWaDzC5o0QNltWot"
    b"LTr0WNb5qLvGtcdZO2df3TRzomdAapljFhbvWG2fHarFsRH8k2Y4lGUlmj1KptREU9Ow6sD+"
    b"s6sgAXcmGXPJJYQj00qnazIt5QiLfqnqkZ74pAZgP9Sz9t9DbKtBDE4ycMmJpRkbhhG4zF0i"
    b"Rj2EoDXu6HnDN1cLm14bQsecZ0J7aKlq7iLl+QDeZzkI6XgHWI3dIR68oUdgDuhLXNDLXNBz"
    b"MHbBdZNFG6wtS6GXBf2WdJGj0G9JsGXJUujP0uhi2qeW0Z2bH1lG8hC0dy2jx6C9axndOxoK"
    b"/gI3YuVp/IjRojGAw3O4WCa3xC1zbJhOIpvKpeBkkkCRPtkQBoRQMTdos5FoZJQOJaHauW2K"
    b"phZQNsTOmqA8u5UGy6WXgDEE5nfLDqjNPHJFq5rlt6OEn6q3+rb00lzJB1tqXukA1e2mGlVh"
    b"q15tSZXDTOgusfV08oLeceOZF/SOG8+8oHfceOYFvePGsyu948YzL+gdN555Qa/d8NiOSUbC"
    b"FDNjFj/rqKh7aZTZoxltRoxEtkikCUeqzzhNlBmy7abOHWybIrKvr8yyO69cWF9icsJpvKmx"
    b"xcyGXIxTlmsVR5WBARzneIupWmOCczd6UkKAwk5T3ARD9BM6Fny46tlaHIXDAqhZorTZjXWD"
    b"mNYSzl86lXW/uwYnPR8jM2EXjyZGtFZEuya2XlzTJxQ+sTgcZg+zcOPNrPUsQORi1oNR6jw9"
    b"en8yS4vZ2azDKChZZsGTwzA6LDvM0tJ5M2wWBLViePXVp9xax8EJxKkYBxLm0xHBn+FsTOIK"
    b"Clv3ubjgQgRkfiB0M+Fgg0KnT73u+vVumWwuLbOslulWywT8L2mn4Qrow4fQV1e6LVjxl359"
    b"dGsgd3TrNS7wofxpAtE5g37jzNkXeuWMgnWmsD6fXDZcOcxKlR4HbaIFX9eGobtnCWFDp48Z"
    b"ebHhP690S2Gl5tdSpNWgDZ2JNn/WTKRnEJwvwhqI7GIdefmpzuOa+mM5XVVo16NLIdqq/+tg"
    b"Y595Qe+4cfVC0xCBXi3720AfNeCx7jyUnSsJCRPFj5j7C2Z/xnB63iN+z3D6Sbr+hOF0ofgP"
    b"GZ6w8SnB6BdZ8JKh9Lrj3xh6PjCczwvKUXrZ888MfeDnYvuVoXSjqBZ0HT6PQI0d1AeGfhty"
    b"+kLRNxlKP9h4x9Dvz0z0pAhvRq3clhNDMR5gTLF1XsbnONiHlh3GZ1rzc8Q/xvnrmJ+5OR+b"
    b"W/MzQOU1PteVAU8er+ynK3R5vDItjOpxMTyYMbRBSw/LnZ722KSyQhYbwGDc7FbT9CUltExC"
    b"osTCkDVG7ANjUGBnEg56gzEAlYLzcYUKTqWNMw/PHKdPOG0fBX0tw084PnG6yc3r0Z0RpJly"
    b"rSNxGG5OCYNyNLlihBi4YVZwL7pux9BwVw+K2r7DbTWMKBcrjMG6sccvZMTQpEenNX7F8UAE"
    b"qbARCe2CiKznXbXeS9L/GHAbEAVj7EEr1pM0zDyP8lY6+F3DzxKvttHNuM9so5txn9lGzwL3"
    b"zvGN/shj0f8F/WFB2jYKiPcvpWoLVpagByQAAAAGYktHRAD/AP8A/6C9p5MAAAAJcEhZcwAA"
    b"DsQAAA7EAZUrDhsAAAAHdElNRQflCh0GIQzjOpIIAAAAc0lEQVRo3u3ZQQrAIAwEQFP6/y9v"
    b"v1AqxiKTs5eBXQ1YScYJc41DBgQEBAQEZGbutwerassKkKRECwSksewzRey4UEQLBGRh2f+0"
    b"AYgWCEhz2Ts2ANECAQEBAQFZ8bLvWtlFCwTkQ1/9s4OAgICAgBwEeQBF4hNpcTofVwAAAABJ"
    b"RU5ErkJggg=="
)

# ----------------------------------------------------------------------
icon_corner2 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAIFHpUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VlZluq6Dv3XKO4Q3MnNcNxprTeDN/y7ZQcIFFSdgvN5SUHAcWRZe6tL"
    b"0fz//4T+wcsXkylwyrHEaPAKJRRX8SWb/dpna8L6XC/vjmv2fpyuFxyGvM7cP+M85leM8+2G"
    b"FI7xdj9OqR9y8iHouHAR6HVlXeyYl8NVszVuj99UjvtqOG3neLdxjPE+Pf4OCcYYDHnekZve"
    b"eoPPrKt4fVtfdQyfzhdM0rHqvY/4ZJ+e246uXx+Md/32YDtTj3F/bwoy8ZgQH2x0jFt+brtl"
    b"obNG9rby3QU3zDTn18l2IiOLzL27GiIsFenY1GUr6xsmNpjSr9sijoQ343taR8GRscUOxAbQ"
    b"bDg62WIdLCs22GGrFTvXudsOFYObLuHsXAcGOpZ9csV1AGB90MOKS774QT4Dkw7UPIbdVRe7"
    b"1i1rvW4zVh4WM52FMIs7vhz0bPCd4ypIRKlrrclXW0Evp5yGGoqcfmIWALFy2JSXfddBJ96Y"
    b"E7AeCPIyc8YGq2lbRGN745ZfOHvMYxPIbNewaRwCYCKszVDGeiBgovVsozXJuWQt7JiBT4Xm"
    b"zgfXgIBldsOSABuwH+Bkp2vjnmTXXMduDyO0AAiGiyRAU3wFWCEw+JNCBocqew7EzJETZy5c"
    b"o48hcowxRY1RNfkUEqeYUsqppJp9DplzzCnnXHItrniEMC6xJCq5lFIrFq0QXXF3xYxam2u+"
    b"hcYtttRyK6120KeHzj321HMvvQ43/ID7jzgSjTzKqNNOUGmGyTPONPMsswq4Jl6CsERJkqVI"
    b"vaJ2oHqPmn1A7nvU7IGaIhbWvHRDDcMpXURYDSesmAExFywQT4oACO0UM5NtCE6RU8xMcXAK"
    b"dkDNsoIzrCIGBMO0jsVesbsh9y1uxOFXuLlXyJFC9zeQI4XuQO4rbk9QG3VlFL8AUi9Umxov"
    b"CGyYVF3GH+Lx+2f6VMB/gp6ffY8yXZfOZaTWTZquUuPhJLQWho8xO24utBxjq3mMkr1NibsB"
    b"N5DFMxJNG7HlIAJGTrE5yTDgrBeFv4n1ScSO6kUvS3E51aRZEBQVxOdhmxsp4yaTmknSfQDT"
    b"u5eZbUMKkyGZStOpeQ6rZ9wzJrKcVBRIWE+gdURS9Y0nuMmvJCFlQ5jKOiRd5GitsCUZs2UZ"
    b"87002op9rhdtxT7Xi84G+0QvOhvsE73oK5Dv6UVfgXxPL3pFsKteiLJiSoNLzAaZXZCiB8Jq"
    b"1VhatOixrPVRd41rj7N2zr66aeZEzoDUMscsLN6x6j47lhbHRvAnzXAoS0ske4RMqYmmumHV"
    b"gv3PzgIH3J5kzMWXYI5My52uzrQWh1n0oi4P98Q3VQDzsTxr/j3EthrEoJPBlpxYmrGhGMGW"
    b"uUtEqQcTtMYdOW/45mph02uD6ZjzTEgPLVX1Xbg8H8D7LAchHW8Dq7LbxIM39DDMAX2JC3qZ"
    b"C3oOxi64brJog7VlKfSyoN+SLnIU+i0JuixZCv29NLqo9qlmdNrmR5qRPBjtXc3o0Wjvakbn"
    b"jYaCX+BGrDyNHzFaJAZweA4Xy+SWuGWODdVJZFO5FHQmCRTpkw2hQAgVdYMmG4lGRulYJFQ7"
    b"t07R1ALKhthZHZRnt9KgufQSUIZA/W7ZAbWZR65IVbP8tpTwU9etvq11aS7ngy41L3fA0u22"
    b"NKLCXnqlJV0camLtEltPd7ugd7bxbBf0zjae7YLe2cazXdA723h2pne28WwX9HIbASx3ZbqC"
    b"qIeOdnrXekPoQ4E6O+YpR8XUJiWIi0y9F1tQpKJTQNRN4qr4tBVbfiaZRxMj6jhxWaUX17Rb"
    b"1xJc0A0jU6QicNrtPRNFd1/eg0QixewAXdd2pk0RntiXl9ntYw7+4NULV9JqjRIaIy2Xut/h"
    b"nJM2rnG2GcxVMY0A94odamkY2YrRoZmsJh0KH4o9qIXPm1pbqUMlDTKqlD6JaO2s1qEUbPGg"
    b"1vf2Ih4oB0tFMhzT+WGnGdxCweUWOHdpwKqk6F2cA0kUGaijqe9ojYtFyMmcxrIZ+jXlSzEz"
    b"syCkrHUqemzN5xXNdsAfWkb/U74jTXjyyMBN/WVMuTAQDeJ3yZtW9r5Ku3Okw40WmzWMQo+x"
    b"NbxoejrT0wt/sJXHndC3W3m5/sMZBl++9tLg6BIBDS+grVNqBF8tiNLUBCWgnUXiyCqPVrnV"
    b"f45HbTwvZy7VDF16A/t9RLrJUrYuSdqIQE7YTQY1qyoNzWtWtbNvnunVhdRvQ8tMy0i6rUcz"
    b"sTiYmzbBP+c3PWfF7/lNp+r0I36T/Q3x7As/wFc6kRPLnk2Fjamx7pn50uR0peZzZh68BEG/"
    b"MvOuZaWHnvXES41/PzHzYDm4SQc5IeszZtKPE78w87kD05Wa3xr7BS8PVoJnKI9XrFpMesHL"
    b"Z5n/npfKc9rU3EQvK/q9YuZdIfaFmcR/gZFXQYuaV2bWkDI3LZRz8VqH2N7CQKRzONfi9GEa"
    b"9pS0UjGtjI79JQdjZ5M4+gGGjLlSNDb19SHK/TOUaWHFvrNtMGMYeP+UHlZg6GkXR5A1oUpU"
    b"pUbAUKm9+1pjLYZr8L4zkjma1xZr7mhtg/7zhcKcMfqCvDzBBu5jHJT5JcPpIfy+zXD6Y1fY"
    b"DH/ZSdEn7edZFn3Sfp6l0d9ojFUWfdQYn5IqPavzl2YK62ZkaMrIpa/fdW+tE2QBP7uLxwNE"
    b"crXVof+PaO36ADGhV+TGxe4HiHBSOEJeDxD9kKFF5SgPzzrojx+K/HD+T9DfEIRYPQq8+1+q"
    b"fwBcjQsW6gAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1F"
    b"B+UKHQYkOcj+om4AAAB3SURBVGje7dlBCsAwCATAWPr/L9svlJoakPGcy8BuiCQyc02Yaw0Z"
    b"EBAQEBCQytxvD0bEkSdAZoZogYA0lr1SxI4LRbRAQH4se6Wcuy8K0QIB2VT2Sjk7VgDRAgEB"
    b"AQEBqT7jT60AogUC8qFz/tlBQEBAQEAGQR5Dnxdpa7PYOgAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icon_corner3 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAH/3pUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VlZtiOpDvzXKnoJySAEy2E85+3gLb9DgOfh3rLrs+26ThuTQlKEJhf1"
    b"//9v0D94uHR48iwxpBAOPHzyyWa8icd6rKs5/HydD2f3d+Z2nc5fWCw53bk+hr73Z6zz5Qbx"
    b"e73crpPULSduQfuLk0CnJ+the1/0Z83mutmfKe37sr8yZ/+Vttd4Xe4/e4EzGkOes2S7M+7A"
    b"a9RTnP4Zl3UNr9YlbNK17JwLeGXnn/uOzm/vnHd+d+e7I+91d+sKOsLeEO58tNcNP/fd9NC1"
    b"RuZy8s0XoEE/rh9XvhujxTH6si77AE8F2kadTJnvsLHAlW7eFvAU/DHey3wmPCNMrECsAc2C"
    b"ZyWTjIVnh/GmmWyG6fNaTYWK3nYruFpbgYGuRSc22QoAjPP6NMOKS66Ri8CkAjWHZXvWxcxz"
    b"0zyvmoiTm8FOayDM4I6HJz1b/OR5FjSGUteYI559Bb2schpqKHL6il0AxIztU57+nU+64s1x"
    b"BawDgjzdHGFgPsoSUdhcuOUmzg77GNF/rNAw0rYAuAhnM5QxDggcwTg2wRxirRgDP0bgk6G5"
    b"dd4WIGCYbTM0gA3YD3Ci1bNxj5i517Jdy0gtAIIRIgJokssAy3sGf8RHcCizY0/MHFg4cuIc"
    b"XPCBQwgSNEdlceKFJYhIlCQ5uugjxxAlxphiTjY5pDBOIQmlmFLKGYdmiM64O2NHzsUWV3zh"
    b"EoqUWFLJFfSpvnINVWqsqeZmm2sI/xaaUIsttdxNB5W679xDlx576nmAa8MNP3iEISOONPIZ"
    b"tY3qLWrmDrn3qJmNmiLm5z65oIZlkZMIo+mEFTMgZr0B4qIIgNBWMTui8d4qcorZkSyCgi1Q"
    b"M6zgNKOIAUHfjeVhzthdkHuLG7H/I9zsK+RIofsbyJFCt5F7xO0Jai3PiuImQBqF6tPDDSQ2"
    b"bMo24h/y8edX+lbAf4K+FOR6QElCLQqxDxNltAPEdGOUYZzoN6ZlN7rJrtSA/IuyRG3e0hGS"
    b"DXEpoVSQCFwZKutBEsJ2ybqThEoLYSprSwLX7mT9Vi9ain2vFy3FvtSr90EdHyunJrgxdZsL"
    b"wnCwL765YKK1xSJeORSOrXEsaP24mlZ7dZDqWmm29ODzIJzXUpXRfTYdtR8K5DTV96GyR1r1"
    b"oxnP2uLxmyv9tOHJVQvt9ZJkL5G49CNLTK5y66bCJEHrMcTn2FvoRXr1qXM6XIQvakRzoomR"
    b"2bUOxlW8ZnUjARMx24vwzMZkTEzyxASGb654YxckCscCJWSVBlgodygTVK3mSz0k1+oyd/ip"
    b"ZTi8FtUKXwaoU7Pxxdl+9A6NkB5Nbz1xBeJo/bhXM4pDL1eTR9aEEtWwhftji1lJUFp0Q/Ue"
    b"yUZkYSgfbfaqUUMlQa8szdFQp7E23t9d6X4Bk8B5iZGuRzVWz06oVNlAmaJcSR6FY9iDpU1S"
    b"okAWMCgdPeKWMKZLM1oalZgvcLtDejPTvfgKzJqQHOwhJbvAKO80JniImbI4meYmsDLqdYCV"
    b"hTtqCSgj4HWv+DBUGv4NlZXm4Y6C1W5hSfuG4Z8w+ynDaXnLX7kKhqmzpqtQTn9wOeT1uDSa"
    b"UCmXvMjiEixSLk3Xg00pXNiEXLLYJGOyyW02WWoSERzHFS9B/B+ZqbrdcLPRmZpfMpNebnhg"
    b"JjRVR71g5g/OfsHLzUrwbLMSIbKJ+YSXM10rLxeXnvBy8ZxnTqdNTsh7xczJc+XmW2bSe8a9"
    b"M+bWFvqNMb8hOk2r/wK7KV7g/ordpPT+G+wmpffH7L6ygj4N0pMVEMk9GbTHjBkbRJRY0Jyw"
    b"pGAy6iG4ifqIM1oP7IcDgNVFzB04io/oMHOPLurlADOAFk3Qj+wLJi0tkmVm5uSKuqFiDEFb"
    b"wxhODvTuAHQVx9SK/hThFC8NNKBKPFlTMbUMTBuTQSjYIEJvVattndXWJ8HsMGlopMzgkKBR"
    b"Evt0VTTkF4vG/AnpWq2tlPZKduJ4p9hWC6ZOxWhrNkk4LordqAWf3iq21NpK4Yiu+ehM3Jf5"
    b"BqH1znT0XN4jQ2LSG0cPcRxBJ7pWEPy9BvSCnSuXlkboPVj0cxgLE4LI1YSOsN300i3TD4Vx"
    b"kf194GiD/lPrd5H1OnBUqTToD6eFbcijHfSZIY920GeGPOpLnxnyaAd9ZsijHfSZIY9X+syQ"
    b"RzvowRBtl5GrHJ/b5ZZzSHLwqV1GH1+L+LjaZVuCDy3Q7JcxYPWi/bIWMz1xIAu27mYNzUfo"
    b"cYaudBtWvBeNPwe1YtVsYErWea2NmMqK4plAL9KOs7yTtCXriSRaRXnLepD0e71oKfa9XuTO"
    b"kr7Ti64d9o1e5O4kPdOrWYkNs1bJCUuOUxT2je1RPIa0mFsLmPs5NDaJMeiFEJDRa63iEsbV"
    b"gXE1FSUrasZPE5IQDn07GgT9H5eRdeJeIl9c6X5hpFOl3k3CdO2u1udajT5BhgmCGT0UeK4O"
    b"DH6cMS9mRrJP+iO44WS54IbmY8+VoyszCDymd1TtFQNWgUKsL+9azivWtByqe5tWTXUwL6Bg"
    b"7hn2FDbso2/Y2V9LoylOYVdTFvD38o6zxJO8Je1GFp1U+1YzujH0C83o3mmfakb3TvtUM7p3"
    b"2qea0Ss4/1QzegXnO82ejTW05vfTWPOLH1VKKSP6NqAnGjf0kDFnkJ00HfThW1Jza+pN00Hw"
    b"EsJRWWNLxNoIyfrjsJ8/lfmf6tpX1/8EfSdIU2KifwH3mgchYlIp/wAAAAZiS0dEAP8A/wD/"
    b"oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+UKHQYkNlhBv/8AAABzSURBVGje"
    b"7dkBCoAwCADAGf3/y/aEVkKknB8Yhzodi8xcE+JYQwIEBAQEBKQS5xeHRMTr9SEzQ2mBgDRp"
    b"9t0mrlwKSgsEBAQEBOTJZK9MXRkBAWm+xu++p2UEBKR5s/9p2istEJCbfvXPDgICAgICMghy"
    b"ATE+E2lGp11pAAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icon_corner4 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAIC3pUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VhZlisrDvzXKnoJiEmwHCad0zvo5XeITI9l173lep/PWWXSJCkkRSAh"
    b"aP3vv0r/wSdU7ygmKbnm7PCJNVbfcFPc8TladnF/70/w5zN+7KfrA4+uYCOPn3md4xv60+0F"
    b"iWd/f+wnGaeccgo6H1wEBpvZJjvHlXjVbPfz+Zvq+V6Ld+ac/32efelonn9HgTNmgrzgya/A"
    b"weG72CzB/jk068O3NzfuvhZCyPhO4Y3v6Hr75Lzr3ZPvXDv7w6MryOVzQH7y0dnP6bXvtofu"
    b"NeLbzA8PQnPL3X/ufKc6i+o6rGsxw1OZTqMupuw7DOxwZdivZVyC/4R72VfFVWDiAGITaHZc"
    b"g7iyh2eVI09urLx2O3hAxeiXF7TeD2BgfSWIr34AAA7RLlYvoYZJoQCTAdQCuv1VF97z1j3f"
    b"4IKZJ2OkZwhjvPHloledn1xXQapGXWZXrr6CXt44DTUMOfvGKADCevo0bf/ui+544+6ADUAw"
    b"bTcXGNhcP0T0xDduhY1zwLjkIrljabDMUwBchLkTlOEABFzmkDizE++FGX4swKdBcx+i70CA"
    b"U/KTSYEN2A9wire58Y7wHuuTP7oRWgBEwhIRQFNDA1gxJvBHYgGHWgopUkopJ0kl1dRyyDGn"
    b"nLNki1FNgkRJkkWkSJVWQokllVyklFJLq74GhLBUcxWqpdbaGiZtEN3wdsOI1rrvoceeeu7S"
    b"S6+9DdBnxJFGHjLKqKNNP8PE8p95Cs0y62yLF6i04korL1ll1dUUXNOgUZNmFS1atV1RO1F9"
    b"RI2fkPseNT5RM8TiHic31NAtchHBFk6SYQbEfGQgLoYACO0NM1c4Rm/IGWaueiyK5IEaJwNn"
    b"siEGBONin5Sv2N2Q+xY3SvFHuPl3yJFB908gRwbdidxX3F6gNtvOKGEDZKvQfOqCIrBhUPMF"
    b"f4jHn7f0WwH/CnrdhpF1+aEj1Sl9OFm+UU/Ta+w9zpBz8an72EvOvZU5awkskoYDN5DFCxJN"
    b"n7mXqApGLuUiOh04G9Tg78pBVHm2oPZYqy/SxLIgKKqIz5O7n1LwkpPuREeIYPoIugp3pDCd"
    b"Wqh2G1rWZGvxzlzIctqwQcJ8Cq0zkmroaYGb6Z0kpGwIM1mnpIsc2ysckpw7ZDn3vTQ6FPu9"
    b"XnQo9pleU9Gy3TKC/3nz2/YUJGOwdmiqo8YwN1ZrIDjCIISG3IesPssJq3MXYGHLAe2kG7Im"
    b"HaSS4jtEtIrekGpFQJp+SY8lS2nTEkVtq86aYis5bZa1IRSqbJqBrwhcfk+LoYhbeXsvsp9w"
    b"19ZjzP2dW9nQZOGTk7FHglobsbAV5Ya4hTxkErHbSUFdQkisi5GCVpqrV1HpLUWYm3sP0jDT"
    b"KGnQWpIiNkDZtrHdLUWEVGSWtP2IFIYZj9tL1+uW/jTga8saQAZQRNUnh1AMS7STS3Eb1UJO"
    b"llybZofAHLqu2HjVPSw7c4t5LI+DRhBrpFxjbYR9IqdpU69DIt6CPH+TB58f8g7aQl7Fe5CW"
    b"TLF4MZqXKCl3G1zd6tvpeeOjDbl5IuNwQhLRkefBnhjafj5t8KoRSU+9VRTw0cnIe7p/0tL7"
    b"AT9jO72i+x3b0zJpAa7e0hALTZYXk1XaTZZYGNmSjKGQE8+IyNvccDFX6sHpaaMPR83DpxdH"
    b"AX6ZFmi/d/mfGUr8c0a+ZCgdFDVKbZKejJLNqDcMPRi1F65eGUoPFDVpxs+TnZvv7/h5snOz"
    b"HfykJ4JaBLh3lznLBD7w85Xb6eZ3d8+hbe5PGEk/oPBXhp78hDKFvlD0uzx7x0+Y98BQ+kJR"
    b"vgb3G0dfM/RhKdOLtbwZ+genf2ETfUO3H9GC3vHijhZ/xXB6DMKfM5xeBuEPGE4vTPk7hgtw"
    b"FpQqdS4fUIouQZZOqBFAtVSGdtCuoGLwec2Gil+AP4r94qSEBE10oMDRYvBHrzbVmtZtoXZY"
    b"dq0OG02rEYynHKug6Ng6sOwI5SWb0WVtKrfYlyk+XT+4FKgbA4fYXnVFbFv76ltYSSi2nNou"
    b"Ki0LtLOXY39UAcFNLbhmK0anZk9q4f6m1qHUqZLt64719agWaQ39WBbPakHYk1q2vrZiz2pB"
    b"Kbq569FbsWiZsjhjnQ0fVrDazU0kJKxSLHTAtWoIXiqqsYzdyKgejvTAeRWsdrAFWxX49k9L"
    b"2MLBffanC/ces79lEFR/VjLYyeJftLSN+XMs2pM/b2XudzK0if+BKc+W0KemPFtCn5rybAl9"
    b"asqzJfSpKc+W0I9Ngc4IXSBr8oqI00PIrbZEg3MNUT0SQOqQiu118Fgao83KPdW4sHIQFtu0"
    b"4423Bdukf6LEMkn0aYn1LI0uNelv9aJLTfpbveixVv5cL3qslT/TCyEoUFJuq6FvzJx52tlk"
    b"8dNzXb5Lwl/qKaK+841RBHqREHisNBCnY1t5nUcUSt9v6WzS91uZYydj8Rmr/6fHIutN4qaH"
    b"vWnSOO3oREucTa2ohVK5t5ariLQ8AraDGdXjGjDao1Lk7NayNYAqu6B4XMcicJaosNyvLq75"
    b"dLGu08WW3beTT8Bg8saLik8H9BZODvDnmbcuEi/yDmlvZJGBf8gy8HWDf0j6mWZ0Ue23mtGd"
    b"mb/SjJ6d9qlm9AKAjzSjd3D+VDPS99T4kWb05LTva9gXhyuXsxW6Hq6shb1VkOHz9Wyxtx0N"
    b"er8eLcoRDiofR4tYWnWOYkeLhGl12mqc1f8wZX/ZjfxKwL+Cvt9UgK+V/g9jXwgHtfXQsQAA"
    b"AAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+UKHQYkMl8s"
    b"e+YAAAB2SURBVGje7dlBDsAgCARAafz/l+kXjKS1JcPZy0RWJUZmjg51jSYFAgICAgJSqbm6"
    b"MCK2nwCZGXYEBOQnYV8NceVQsCMgICAgICAnb/YvjQBaCwTk5bBX5vPKoaC1QEAeDPup+Vxr"
    b"gYBs5NU/OwgICAgISCPIDbaDF2kDKN/uAAAAAElFTkSuQmCC"
)


# ----------------------------------------------------------------------
icons8_pentagon_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"HUlEQVRoge2ZSU8UQRTHfwPjAi5xwT2SqBeXxMSDJ/VAMNGRGAQOIiae5WTCJ/ArGL6BJt7g"
    b"YEIMaozbQbxoPKAHLjBAxC1KQFDU8fCq0j2dmV6ruoc4v6Qz0+nX7/27q+rVq2qoU2dV0gFM"
    b"A0WgkLGWRBSBkjqmMtYSixwwgPMQ+hhQ11YFO4ARHPGf1KHPR5RNTdMGzCCCvwNXXdd6gK/q"
    b"2hxwPnV1IcgDN4HfiNBXwKEKdq3AC2XzF7gFrElHYjCtwHPKxa31sfc+9Bhw0K7EYLqAL4ig"
    b"D8C5CPe2IalZd8Ne4+pCsB5583oAjwK7Y/hpAe65/NwGmg1pDOQw8EYFXgZukDylXgMWlc9x"
    b"4HhCf6ECLqiA74ATBn0fA94q30vICzLOZuAu5V1gg4U4TZR32WFgqynnJ4EJnEHZZ8qxD904"
    b"c84kcCqJsxzSvD9x0mSlucEW7rS+gqTshqhOdgL3yX7i8s45j4G9QTfpknsGKSFK6rzNlsoI"
    b"uOecOURj1aWBu+QuIfm9JRWZ4fDOOVWXBtMeg1ost3OUv/CivuAePP3AR/X/jjKsNXTqB9F6"
    b"vZphlzJ+loKouOhMdsnPqAmZuf8Ae1IQFZVdSAZbxFOTefPyEpJ2G4DOVKRFoxtoRFaZP4KM"
    b"e5Gme2hZVBweIdouhzHeiLTMCrWVfrcjmpaR2q+MSlP+AtIaeeCiVWnR6EQ0jQLz3ovVapdh"
    b"9dttSVQctJZhXysPW5BisWIzZsAmpLv/ArZFvfkBMrCuGBYVhz6cJXVF/MriIfXbY1JRTLSG"
    b"IV+rKrgnHxurwbA040zScTY4AHiKNGmWg75HaXjiZxS04tJNmeWD6NixupVmH7JCnEf2stJm"
    b"HfBNadif1NkY0rQXkjqKQYeK/TLIMMxiPsvslShbeTmAvJXPSImQFnmc7yrGdm/0Fmm7KYch"
    b"OKtivg5jHHafKIvuZbRbaY7ifDpoNOm4Cg3ArIp5xLTzceX4tGnHFTijYr234XxQOZ/F7ve/"
    b"Ak5rDNoI4N3AS+OYDCsu8qZwyljZJCwgrTKB3TTcrmJMUaOfsOv8V/wD9srxvK1koPwAAAAA"
    b"SUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_pentagon_square_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"xElEQVRoge3ZTYsUVxTG8V+LiBJBcBQdiLpRBFEEFcWAm+gsXPqyUYkvn8ClGwVB0J3iQj+A"
    b"KzejgbgRXWnIqLNSFzMKAyIYlYRAENHEl3Zxb9s97VR3163qHpD6Q9FQVeec51Tde+651VRU"
    b"VFRUzAK1LtfrA1HRO930ZlI0kSPRRx2/FPRVSEsR42UY10xkPJ6bDS3JxiN4iU+4GY9P8dzI"
    b"gLUkGc/FaUH0a+xuufYzXuAzLmJen7UkG6/C79HmFoZnuGcpftMcaqv7pCXZeC/+wf/CG5nT"
    b"4d4ajuM9/sXBkrUkGc8Xhkkdk9iUw/d6PI62V/BDQS3JxuvwqEXIwgT/CzQfxAQ2JmrpSpbx"
    b"YbwVhsahIgEi+4Sh+U4YdjMtfKUmsghX4/kH8k3WbrQWi+tY3EVLLlqNt2JKevnshdby/Rw7"
    b"MrTkpo4TOIMP+BM7izjskZ0x1ocY+4QCiQxpthd13BDWgUGxNMZs1TCU4mi4xcETBTrPAtTw"
    b"tEXH8qwbOy1cL+PvfxgzOy19HX9EDfCqiKMb+FuYiINmLv7SbGuSqeNY/B3EJG9nV4x9VAmJ"
    b"DAnV41JhWfm5HGMvUdI6cluYM53mVNnMEUrwrTYtmTf3wqhQMban68rNT0LlHC3DWeMpLMNH"
    b"nC/DaY9cEFb4xr6mtBblrtA2DGI9qeEZ7mRo+YY8Y34UK7A5t6z8bBGayFKGFdOfwo9Cw3i2"
    b"LOcdOBdjrczQkpt24wdCy9BvJnG/i5Zp5C2n17BG2Kb2iw1YG2P1TN5EGmN2X067PDR8/1qm"
    b"05le56N49IvHeNijlq+krNSjmq+/bBrDNne1Sk0E9iTYdmN/W4zSyHqdE0IFK5txYROXR0tP"
    b"ZBmfF+r8ySLO2zgVfWa1QX1J5J7pe+kyj7GURFJ3fVPYhjea37mKUMMB4WvlVKqDTnw3f71V"
    b"VFRUVPSFL5FE0S7qGwl3AAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_square_border_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"7klEQVRoge3Z4Q6CIBQF4GNrPlQ9X1nvGb1G/UA2t+wKFxCB821tzTa5cBSRACKSDCvHPgnO"
    b"oRHV7ilREcWdhd+2Rjp0BH2p2u0iESfXyIe2JybVVSJOqtkp9PxeV0QzibAjRyPdI3vPVlvE"
    b"eppJhIiInBHAE8AbgAEwzceq84B9iC0/96IVKRnY4i8ArvN3k6uxPZ7sy+X50ZY9Xib8Xlq3"
    b"ohUpjbCdMQBesJ2o8mYnIkovZDc+977WP171NPPOLnVkQLkU1oj1dJFIVZrpSMhufO7ZLGqJ"
    b"31UiUf9bKKgS7iKRUq+lqnabSYSIZF/o3CVWfRkALAAAAABJRU5ErkJggg=="
)


icons8_compress_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAHKSURBVGhD7ZpNSgQxEEZnpd7DlUtd"
    b"ewPXHsITeCfx/xe8kzcQtR5OQ1GkeyZRqC9DHnww0yjUo7rpJDWrwWAAB5aj3495HFrO1znl"
    b"QiX7ljfLh+WEC1lcWL7XeeZCBUi8Wqb/RyatM60iexYvQegMt1kKLSJIvFiiBB1Ko1akJEFn"
    b"UiWgRgSJJ0uU4Ho624qUJPh7CQnYRoRiHy2yErBJhGIfLF4CKSkJWBKh2HuLvATMiVDsncVL"
    b"0BlJCSiJUOytxUvQGVkJiCIUe+OuETojLQFe5N1y7b4TOiMvAV7ky30mdKYLCfAiPnSmGwko"
    b"iXxaeC6uKiOzH/lrzixp7IzIseXyn8K2edAdtK3UzpZwO6XBg1R6wFrCA57Gzojwsim9hJbC"
    b"S42Xm5RILSwv4gKwOxEk4lLcLwi7EEEiboroDEv0bkSQiNvTaSnOpqkLEYqNBwV+U9SFCMXG"
    b"I5u4PZUXodh4eFY6KJAWKUnMHdnIilCsL44sHZ5JipQkOGCekwA5EYqNkyKKXJIAKZE4syMM"
    b"XTZJgIzIND1tkQAJEQaMUaJ2UiQhwsiX0a+XqJ3Zydxa7EeQaZ2e8mOA6YcB6acddCZtjj0Y"
    b"yLBa/QCFElub65nNHQAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_enlarge_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAEVSURBVGhD7dldCoJQEIZhr4r2EBHd"
    b"d9Xi21VELaDOCwki/hznTMcZmRe+i4SEB8JEmyiKomhL7dJuyjukVe+U9lHeNa16m4Ec0x7C"
    b"vdLMQKTt0+5priFTCOYCMoTg87vz2TxkDMHxZ+eYacgUglxA5hBkHpKDINOQXASZhSxBkEnI"
    b"UgSpQbiLvfx25oAwCYLUIHy5PREnlSRFkBlICYJMQEoRtDpEA0GrQrQQtBpEE0GrQLQRxCW/"
    b"vfzzVyAuF/IPhGo5EPMImoO4QNAUxA2CxiCuEDQEcYegPsQlgroQHs24RFAX0p8bBI1BXCFo"
    b"DMKD5qEH0DnjAXf1pn5a0vHKoXqbgfC6a+g1WMmK7mKjKIoiQzXNF/nEYloeaSPOAAAAAElF"
    b"TkSuQmCC"
)


icons8_choose_font_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"RElEQVRoge3ZvWsUQRiA8d8lQYyIH6CHBCsV/ACtLMQqEBQrMYpGxcpSELT1T7BSBFsbKytR"
    b"o1ZCCkXETtRgEwlpVBANKDGJOYtNuFxmL3u37N5eZB/YZvZl5nl3bvbemaWkpKRkLVHJqJ8N"
    b"OIgq1sfc78FCBuNMYwwzGfTVwDGMYha1Dl2jWSawCfc7KL/8+plVElWMF5jEtSyS6MfbFZ1P"
    b"4QYOYfOy2G34uyJ2YfFBFM5NjWLPsLVJ7BnhE33fAcdEdmFOXeqNaIaacUeYyN2cHVvitrrQ"
    b"H+xNiH8nTORcnoKtMqUudC8hdrtoPaxcHzvyFGyVCXWpowmxZ4Wz8TFPub42YodxBS/xKiF2"
    b"MKZtrI2xuoYPwhk5X6hRCqrC9VHDQJFSaRgRJjGe96A9OfQ5GNOW+/poZ7GvxgCOoBfHY+7X"
    b"RG+yZuRWnrfDTnzXZeV5Gk7osvI8Lf14hHldUJ5nQR++CSWHipRKw5AwiR9Y14nBs3z9nopp"
    b"W9rPrxkqmBTOyEiRUmk4LExiFls6JZDVT2s4pm1MtEbWDH0aN11L19UipdIwLExiTpfsBtvh"
    b"uTCRx4UapWCf8OyqhtNFSqXhqTCJz7KrqjPhgGh7uqfJ/Yvi66brHbFrkcvqReCcxvOoiuiP"
    b"bkaYxKTVD+06zleNgr/wRHREOiF+Jmq4UIRsMyr4rf1S/EERsknc0l4Sr7GxENMEekXHoq0k"
    b"8VD04aeruYRPQvl5vMDJ4tQaafVj6H7sXoz/Ijqnms5LqqSkpOT/5x8uy2K2p2FyYgAAAABJ"
    b"RU5ErkJggg=="
)

icons8_level_1_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"mklEQVRoge2aO2sUURSAP6OFidkNG2MSBOu0EUERhdjbyZLSTiWFhSCWoiDoT/CFjb1/QAQf"
    b"6xIbFWOTgCDEN2wUjYXIZi3ODutOzszunXPnUcwHp8jd7LnnS2buawZKSkri2OE53xSwABwE"
    b"5oB9wHj3s03gG7AGvASeAC3P/ZuoAktAE2gDnSGjDTwHznVz5MYEcA34zvDFR8UGcJUchBaB"
    b"T4bCo+IjUM9CYAy4l4JAOO4Ao2lJ1JBrOm2JIF4gg4dX9gJvM5QIYgWY9CUxBiznIBFEE0+X"
    b"WRb3xKC4bZVYLIBEEIlHsyoyHOYtEMRnZO5SGYkRuQTsd1KP5h1wBbhoyDELXHD90gT2GfsH"
    b"cm0fp7emO2nMuYHj7L+UsKM28BA4DexR8lpFOsjabGiaCTs5MyCvD5GGlli7R6aAI4NdVf6G"
    b"fq4lzBPHUZRJUhM5EdE+LAeA88Aj4L0hTxQjSI197FJ+cd7QyXVght7N/duQK4554MH/DZrI"
    b"nKGDWcN3XdhWo3YJzWRQiJXpcIMmMq60FY1tc4nlpi4Umshm5lW48zPcoIl8yaAQK1/DDZrI"
    b"WgaFWFkNN2girzIoxMrrcIMm8hjYSr2U5Gwhp5R9aCItZI9eVJrIcr6PqOH3frq1mHCqrYpY"
    b"W5fc4aHcuoxvARWt4J0RIn+QY6CFodV1OsgJ/KFuHAMOG/LdQDZuTlSAD9j/K75iHcPyqV4A"
    b"gSBOJZUIuFsAiZtWCZDjyqR7eB/RAHb7EAHZI6/kIPEGj4fYATXkr5OVxDIpPFYIGEUewqQt"
    b"cQuPl1McddIZmtfxMDq5UkHOc32sAFrAZXLeZleRY8wG7o+nnwFniVh2uOD7hYFJ+l8YmKZX"
    b"5C9kubKKvDDwFGUVW1JSkg7/AOZX0ILb/Rs6AAAAAElFTkSuQmCC"
)

icons8_keyboard_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"nUlEQVRoge3YMU8UQRjG8d+dFDQqNXcUJkhICPYUFvYW9tR8D/wMFNpbGUKFFlDpJyCBykQb"
    b"a0/uiLHCLMXsHRdzkNu93M0smX/yZu4mO7vPs7P77puXTFo8ii1gAm08w1P0I2uZiS4K/Kyy"
    b"qD0fLTOxUo6XVRalaGS7HH9UWZSikdfl+DWqihl5iWv8xWpkLbVYxz7+CC/626hqpmQTezjA"
    b"F+GlLsbiHVqxxE3DlvDcFxPiN47wqu7JF+V8Byd4jAFOcYYLnKv4zYjFMr4Ld/4DnsSVU59d"
    b"wcSZOZZEi/iOvCnH9/i3gOvNjW/CjrxYxMW6OMSVyVklxbgSMt3zcRO9BITVjR46yp0ocDyc"
    b"aAgdfBK0f+T2cWqSiSFrgvZ+q/xB4mXBPRSkWcbXYumO+eK//61E50c8mB3JRlIjZ63UmDZr"
    b"jRMrU006ZsSD2ZFsJDVy1kqNedVaVcm11pBsJDVy1kqNttB8ILSFmsZaOQ4ITa5CaK00yUwX"
    b"nwXth7CBX+I32mZp0K0P3XWEJtcgAWHTxqDciZGJTCaTaQ43WK8NPKELVSYAAAAASUVORK5C"
    b"YII="
)

icons8_roll_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"60lEQVRogd3a3Y9dUxgG8B89M1PpHKLtuBEqqSolbXzFx4UIE8y0IxE30vi64kJk2rpF8R+4"
    b"J5qQ+A+4QLSIdlAXbWZ8lUjRb0GHpF8xLtbaWVv17Dnn7HXO4El21snJ2s/7vHuvtd53v2vx"
    b"P8F5Gbkuwl24HWuwEiMYxhyO4xd8g734FO/G/xcci7ER7+CMILiT62S89yEMtGFvCjtzOnAB"
    b"NuHgWaK243k8ILyVpRjEkPB2rsGDeCH2PV26/6fIOVhht+ibBWP4vkT6GZ4UhlanWIonhKFW"
    b"8H2N+1r0z+LIYrxSItuN8bqkJYxjOnL/iZejzTJqO3KpMDnn8Ae2YFEdwhZo4BmciLamhCFZ"
    b"oJYjK/BtJNiHtV3LbB/XR1tz+CpqoIYjgyXCXbi4vsa2cYkw/wpnlqvhyFAkeQ8XZhLYCZrS"
    b"kN4l86rVb4wIK1k5/vyr8aH2A+k/0MgsZh3uxq1YjcuEFAV+x37h6e4UhuuezPZroSksxzM6"
    b"T1GmsVlydkHQiCJ+loQdEILmI7gBy4QcakBYdW7Eo3jV39ObY5iUf4TMi9X4vCTkfazXWZBs"
    b"YAN2lHh2Y1VWpRWYEFLvIi+6JwPnmBSvjgsPpad4WMpYt2FJRu5hvB65TwufBz3BhOTEc70y"
    b"gq3Rxil5k1KEcftbNPBsbvJzoHBmVpiPWdCQJva2XKRt4A3peydLpr1Zmtg558R8GJYWgKfr"
    b"kjWlOHFvXbIuMB5tH1XzIW6R4sRC4YOoYVMdkiLt6Pm6XoGJqGFvtwTrpLSj76lDCQ0cilqu"
    b"bdXp/AqC0di+JdSsFgpn8Hb8PdqqU5Ujt8R2Ry5FNbA9tre16lDlyNWxnc6lpgZmYttVcDwm"
    b"jMtl2eR0jxFpGe4YJ+PNVSXMfmFI0HKiVYeqofWfQpUjs7Ft9kPIPChKUbOtOlQ5ciC2Kyr6"
    b"9AtXxPbHVh2qHPkittflUlMDRSD8slWHKkemYntHNjnd487YdrXJs1ZYKQ5a2BRlAIejljXd"
    b"khT7FRsyieoG90cNtYp5xUfVQqYpH0UNk3VIhqUIP5ZBVKcoUvgjMnydTkqbPP0sbTbxXbT9"
    b"VA7ChlABnBPqTv3Cm9HmJzJu810plYO25iKtwEtS1TFbOajAeqlA10tnXpQKdK22qWtjYzQw"
    b"J9Sdcs6ZpjScTgmnIXqKcWmY7ZOnrDkhTexf9fBNnI1V0o7rnFCymdBZBjAgBLsiThQTe2VW"
    b"pW1gkVABPFoScgiv4THcJGzuDMZrOW7G40Lp9XDpviPCEtuLQwhtY4lQPCufJ2n32iPEqdrB"
    b"Lud5LUK6PSqc2boKl0sLwix+EPbtPxbOas2cg6Mr/AVMUjVunZJoRgAAAABJRU5ErkJggg=="
)

icons8_console_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"ZklEQVRoge2ZQUoDQRBFXzS4iIKCEoILA15Br+LZ1Ft4A0UlCyEuxGBUBPealTsXaRdd0UEM"
    b"2tPlTE2oBwUNSVf+o6fTMwk4zr+xBhwBEyA0rCaSfRXg2ECg3DqksBJ78xfNLPvE7K8tGQC0"
    b"6suTRQBYqjuFFi5ijeIeaTQLsyLtwti/tSzgItZwEWu4CLAsZYbZPX0qZ8A9sKuaJp3P/GVF"
    b"TmTeM9BXi5VOtkgHOKV+mWwRiM/K5zL/AdhWiZaGigjAOnAlPcZALztaGmoiABvAUPrcAFuZ"
    b"/VJQFQHoAiPpNSTKVUEAguaBOAXeZdyRqhSNFekSL6kA3FHtple7tHrArfQY0dDNvgM8yvxr"
    b"qt3kM7JF+sATX5t7Uy1aGlkiK8TTPAAD4lny/fVxoXdKXZQRaf/6tp+ZAi8S9gB4m/MBZSg1"
    b"z3/7tYaLWMNFrOEi1nARayyMyEL99XZZdwgFUu+YHeevfADs2tPOHBgeRwAAAABJRU5ErkJg"
    b"gg=="
)

icons8_text_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"3UlEQVRoge2ZWwqDMBBFr6WLq922O6nuo/0xICGayftS74EggsnkYDIfM4AQQvwjbwAbgG/n"
    b"sQKYa4qMkHDjU1PELdobc9xH4410I1dkge1YLIVzzEzG79zvnbz3lBglc6L7fCYsfhUwxNnG"
    b"c+ZEud0d2fbnMYtUTYu94sz7gsfc/orM8VOnJZXmxGlOjkg2t7sj9EiEDYmwIRE2JMKGRNiQ"
    b"CBsSYUMibEiEDYkE8HsoZzTrfdQi1EOJFbFbFPmKSa1bVa1z6Y4E8Ou2sQGQHi2/bmvpDQ6v"
    b"6wohxBh+1Qai3Sp+mhwAAAAASUVORK5CYII="
)


icons8_laser_beam_hazard_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"tklEQVRoge3ZT2hdRRTH8U9erEltqjFtasVKg1i1GEQSja1VidQuRFCx+Kc0CCpmY6UWq6iI"
    b"IqKNGmiLLYhQXUjRTV0ItouCiEihLvwDQguCqFijdVNcCF3pYs7z3b7c/LkvuUmE94VL5s09"
    b"c+Y3c8+cmXtDkyZNmjSZB1pK9n8B7ovyx/i7rI7KHEgLPsNf8XspNuKfEvssha04jkpcx6Pu"
    b"f8US/IL16IprfdQtmUddhXkFB6P8OnZF+WDcm3XKWCOr8A36sRzXSqF1AqfwLW7AzyX0Pat8"
    b"hJekSdqjtkb2Rt3L+HDe1E2T7DrYglvr7j2Exfip7t6CooKv1MTuyrF5S22QX0ebBcejOCaF"
    b"z7NYnWOzCjvD5gs8MmfqpslS/IoBXIZnJrF9ThpkH37DhaWrK8AI3ovyGybfK7Jh9778EJwX"
    b"rsCfuBTrpPifiq24BZdE2zWlqSvAIbwgxX01xWZZhw11dVXbSrQ9VLLGKbkdP6IdD0trpJ7B"
    b"uOrpxxDOxw/YVIrCadAq7dKb0WF8rFcHNag2kBvrbEai7ebw1dqomJnk8cdwRgqLbdgnxX5n"
    b"3G+p81/J/O4M27fxZPg4Ez7nlIswhuvRg6czAvfF3x4Mqz2R4ajL2oi2PeFrLHzPGaN4N8pv"
    b"Sim1Sif2S/vEYSl8RqLcF/c6M/aLpR1f+BwtTXUda3AaK3AbHoj6fmld9EiCD0hJoEp71PWF"
    b"zUC0gfvD14rwPSfp+BPpmFGRTrfZdNsihdBhtOW0bcORsKlvVz0p74w+ClH0fWSTFBq90mL9"
    b"Dn9gbZ3dRjw/gY9RaROspxef4wN8jydwdLrCimSt87BbmrF2XCmdYIvSgotzrlPSRLVHH7uj"
    b"z1knO0PDWJljUzF5aLWrhVbeJK7Ei1E+Gn3OKl34XXr8EzEgbXjVk+0B5w6mTW2xrw7bvJPA"
    b"U9LT7o0+u2ao/Rz2SmsDXp3Ctmj6radNLQXvj75nhbXSgl4mzeI9k9g2siHmca+UMJbJTyYN"
    b"cQTbpXNQXihkGcoIvElaB4NxVaJO2AxN4WtP9Lk9NMyIu6TPOIvQjasKtM07NE41EVmuw+PR"
    b"94nQ0hCLcBJ3NuogGJR/jJ8Or0nhdYd01M/LhFOyA582KCDLBuNfrKZLt/SNTGjZUdTBcunM"
    b"c02DAmaTbbha0nJa0jaOiXbOLVK6PImbcXcJAovQjS8lTQ+qbQX/MdFAxqRvUB3St6pjJQks"
    b"QgcuV/BA2Sq9G5yV/jGzEK6zeMcMXoebNGnSpEmTifgXBxu98dH6sbAAAAAASUVORK5CYII="
)

icons8_laser_beam_hazard2_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"WUlEQVRoge3YWYjVdRQH8I9LLrhNmaZCIGUGFUVE0EMPLVBSYqmUlLb4UBhKaRYYvlgYVE8+"
    b"RDRWPggVGi0+FEVFRdIuiuWSLRCVuaSR6Tg5zkwP59zu9XqvznJnRuF+4XAv5/f9nd85v+X8"
    b"zu9PHXXUUUcdfYB+PWz/fCzI/8/ipx4er0dwLprQntKUutMO60UAL6W0p+60wtVoxV+4Htfl"
    b"/9ZsOy3QHzvRhrloTpmbup3JqSkG1NogHsDt+AGDcYlIKs0YhInYg697YOyaYQQO4SimixV4"
    b"DEvy//RsO4RRfeRjh/CiONRvYCP24QwMzP+b8HpyVvWRjyfFeWjBYdwpnL2ppP2G1M1JTgsu"
    b"6GUfO4SvhKNPiNnfXIGzOdseT+43tRq8VtnjWlyB/TiCM3FbBd6MbGsRAV2OG2vkQ7cxALvF"
    b"YZ4jAnn1BPxXknOvuFf2iDPU51gkgtiCNfgXDSXtE1MKaEjOa/hObLHFveLpCdAgaqgWzBQB"
    b"lTv1BT4v0y1O7szs2+TY4HsdL4sZXSNm90/Hb5NNKaUYgL3YLrZhe9rqE0xWnM2705lbs20s"
    b"vsUYxUDGpG5scqZln3sUV3VyL/l+DDalI0tFQbghHVqJYdglDn8hkDtSNwyNyd2QfZemrfKV"
    b"63FMERlnr7gT2jBJHPx2EcwqHMTPKQdTtzI5i7JPW9rYmzan9FYQA8VZaMVssSVWYQLGlQTz"
    b"a/62pZTqFiV3QvZtEavXqvI56xEsSWc24k1R1Y7E+/gH72FbOjUfQ1LmZ0Db8G5yP8i+zXgr"
    b"bbbnGD2KsxTrpBk56PxsG4prxDlox8MV+j+SbbvFY2to6hekvpCOD+dYPYa1OeBqfJ9OP4Nf"
    b"SqQQyOgK/UeLVWmuIK1pc3X2X9sZxzpTa10kVuEwPhKpsvCA+rFEfk/+oAo2BotHVquY+VJp"
    b"Spuf5BgzcsyaY4uYzYVi5spv6/GYJ2a3HSsq2FiRbc3iJTm+rP0z/I1HFcuemmJaGt6FW8RK"
    b"DC7jrM/25diaDjfiwpTnU7cVTyb30zIbE8VqPZXtbTl2TTBIlOetmCW2wdMVeEPEa7BwT3yp"
    b"+E2rvUy3MrmVtt9zOcasHHN/FV6nsazEieXiYhtehduoeE+sFm+O7Sn7Ule4Zxqr2Bguzss7"
    b"ioEv624QY8R+bhFbqgVXVuH2E2+Lh0QlewBTFUuUqWISRiVnj+qfbO93bDpuTl+6jHVp8AVc"
    b"KlJiR74XN4jLcoRiICNS15FyvR9+E6VN4YPGuk76/j8uVvx0M7KrRlQu4zuCq0QA94mVPIrL"
    b"uuLADpE15nWlcwk+FKVIV/CxCGJh+rKjGrFacTZVVKZ/iBWp9EWkoyhknK7YGJZyTvoyCTfj"
    b"7XJitZt9ttinD+r+Z9UjKV3BIfEY2yYSRD/xrjkO1Q7uHJEqD4qL6VTAOJGa79KJZ3F/UY4f"
    b"EZfSqSBHRPlfcRedLJWerXsZq5Y4IB5dddRRRx11nDr4D2aAfaSIazOLAAAAAElFTkSuQmCC"
)


icons8_about_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"cElEQVRogd3aaahVVRQH8N+7ms/qORSvjMih8EkWFWI2SoVlUERBaBEFCpFgZUESBRVaRBF9"
    b"qQ8OfcuywqCiAQoqo5kmQiuTnLCQcMjZetXT24e1r+e+x5vuved6n/3hsM85d5+1/vvsfdaw"
    b"1+V/gqac5AzBZFyMc3EGxqEFw1KffdiLzdiAVfgS3+PfnHhUhWbMxApBsljlsRvLcQMGV0um"
    b"mhlpxb24A6PSvSJ+wBf4DuuxUQxwX+ozDMPFbI3HBbgEZ5XJ/g1LsEjMXl1wLB7GHtnb/Abz"
    b"cFoNcsdhvngRJbnbcLcaZqgnXIq1ZYrewkV5K8E0fFim52ucnYfgJjyIjiR4FabmIbgPXCsM"
    b"QhF/YXYtwo7BS0lYBx5N944Ujsdi2ew8rYpvulksnyJ24ZocCVaK2WhPXBarYDBNeDU9uBXn"
    b"1YFcpbgKBwSnp/r70GPpgZ1y+tBywpX4W3Cb1VfnK3AQ/6QHBxpuFwM5gLaeOh2HTanjIzkp"
    b"PkmELpPTeR5YJjh+qofv5aHU4Vv5OaJyq7MoJ5kjsSXJvLnrjyfIPPblOSkkwo3SQJbkKLe0"
    b"xNZhEBTSD7NEHPQ+Ps5RYbGH81rxvBjEeOE8D2NNUnR9jsro/I205iz7PsH5ndKNCenGdmma"
    b"jhK0ioijHS0Fmdd+T5jeowU78JWIQqYVxLTDJw2jVD1WpnZKQea9f6yDorkiQtiJBXWQX+J8"
    b"9mCcmi421UHRKGHa4ZQ6yN+Q2jEFjEgXe+qgqN7YndoRBZkX72gQmVrQntqhBZ03B442lFbT"
    b"3oIwY3Byg8jUgpKT3VXAz+liIOUe/UWJ89qC2FCAKQ0iUwsmpfanAj5IF43My6vF1aldWRD7"
    b"r3+IPdsJDaNUOS7EGJGbrC4Is7ss/Xhno1hVgbmpXa4sRWgTA9orX+u1UH0SqzFi4+6g2Es+"
    b"nFitw4vClyzMUWG98DiG4hWxWd4Jo7FfzExe26IL5D8j03FIzMjYnjrNTUo3yYK9WjAWc9Ix"
    b"qY++/UErfhUcH+itYxPeTh0/EknLQEGzyJmK+Ew/stnhIs4v4jVRVms0huB1wWmzClKC0aLq"
    b"VBQpcCMDyhbZKtmBcyoVMFo4yiLuypVa/zFeVsnaJpx2xWgTdrpDbaW1atAkDESpyLoWZ1Yr"
    b"bIUu+0ZHCNNFbbJktpeJ5VUVbk1C2h2Z8L4Zt4i4rzSAzbiuFqHTZRWiXm11Nzixgr6n4za8"
    b"LHLv8orufOG5+42u2/IzRajSjKWywKw3tIi3OQfnC8uyRoQO+0Utg6gJjhSxUZvOZYZSqfu5"
    b"NLB2VaJJxFiHktBnZXFYdyjgMhF2lNfd/yw77+vYijdwj15CjUoGMFhUb28SFup+PNNN30GJ"
    b"/AzcKHNKRbHjtxRvihmaKJbOCJkPOiCs0MZ0bKmVfFc8IStBzyi7P0Kkv/NEcXSbzm90PZ40"
    b"gJKxz2XkOgTh7bpfDr+IgecRAOaOqXhXhMXlpA9gNV4Qf6CZ2CiC/UG51RoiLMtwUdX9vSGM"
    b"qsR/ME41xQZApAYAAAAASUVORK5CYII="
)


icons8_type_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"m0lEQVRoge3ZTQ5AMBRF4cvqsP8VqH0wEBPx8yJt3XC+pDPhnURHTwKALxokJUlz5ZMk9TlD"
    b"3ojYzhgZsAmGzMHnSrmds60xRQ3RkKnoFNdSzpf1Wv/VN+5HFxkwekeeOLtXRb75uztijxA3"
    b"hLghxA0hbghxQ4gbQtwQ4oYQN4S4IcQNIW4IcUNIwNFOJeuuo5b9TiW86wCA71sAsWpmQWld"
    b"O0QAAAAASUVORK5CYII="
)

icons8_fantasy_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"70lEQVRogc3Za4hVVRQH8N/MpIVRoVZkDTUfggqLHn4ow6BQw0J6IPYCbUhTZ3ylidHLHtS3"
    b"oj5UUlAgRUlKlJEaFdHL6kNZJFlRaQ8ijfxQpviYuX3Y+3DO3HvPnfuc8Q+He+7ea++z/mev"
    b"vdba63BkYOZwK9AMHIu/MaaRSdqbo0tDmCmQuGa4FWkUH6KAt4ZbkXI4BUdVIXcm+gUiBzC6"
    b"3ge2yrRG4hvcqjKhbrRlxlw7yLzHYC5Oa1C/mvCS8KZ/wCx0FPW349co84LK5nUSHsAuvN0K"
    b"ZSvhfKnZFLAdN0ut4Eop0bE4qNS8zsaz2JeZ55Ih0L0EmzMKJNc2wVOtjf/vibIb4/9uXI43"
    b"0Vc0dtgcwuSowG4swM9Fih1GZ5Ttjm37M/378Xq878eEoVO9FF9EReZiRPzdGds2Z+RGC6ZV"
    b"wB+4T9gbj8e214ZM4xzcJN0jyf4YKazQ1UWyT2B27IdThf3Rh/Narukg6MCPApnB3Gsxnonj"
    b"Xmm2UrWiA1dgi6DQxzWM7ZKa2sVN16wKdAibfLXg97Ob+zuMw3S8j++xRrrhs3gyM25flLus"
    b"xbobIcSF5/CXUnf7IM6Nso8W9RewB5eWmfN6weUezshuxwqc3GwS47G1jHJbcWGR7COx7xDm"
    b"4Sy8Edv2CrlXOXRildTbJbnZOlylNGuoG+2YKmzKbBzYg6cEQg9JY8eNmbEdeDH2rcmZfxx6"
    b"8J6BL6sPH2FGs4hkMQaL8ZXSVTqMW8qMGR/7v860nYFlgoPIRvhDeBe9gnseEkzAT9K3NytH"
    b"7u4osyHTlqxSEuE3CNF/bIt0rYj7pSS6c2R6hPSjz0CvdEEce9AQp+3FuFdKYk6OTK9Aol8g"
    b"VHw+SvbEshbpOCgSU+kXvFM5LDSQxIlCUrkIR0eZ6XGeHao7cTYVy6UkFubIzJOSSGSWSffE"
    b"LtyFUfg2tg1pyWiFlMTiHJnF0gPX1kz7ttj2i5TQ7/gk3m9pjcqlSFaigE+Vrwcska7Ewfh7"
    b"uhDVC/hNMKEZgisudt8TW8oA8w10lQU8byCZLIkerI9yy6Vn9ocz8m1CipKNR6+2ksRtgmfq"
    b"x1JMwr8GkllaRIIQ3ZMguDfO0VVm/jZchy+FYFhOpmHMyZDoybRnyXymlAShVPqf9G1nT4vl"
    b"0CacZ2Y3Q/Es8kgkmCQ1szyZdVIiw1LIHowEwZwqkSAonxQnRubItAxzDU4iSTsquWFCnNiL"
    b"x5qpYDWolcQdVcy5Fuc0RbsqcbvaSCytct68w1SCTuWPwnUhuyfy0o4s0TwSx+GGGp+9Ssii"
    b"G0Y2L2p0JXrweQ3PbheOtzs1+OWgVhJLKsw1UaiiFOKYUVU8f5rUPU+rTuVSNIvEKLysNG/a"
    b"IRyeKiFJYwrxvmbMVxuJSi42Qa0r0iVUSvridUCN6UnWxVazsSuZUzF6hZQlD+2YIiSHSZVx"
    b"IzZJixfvCIG04kFrgdpWYlG1DCKOF4raxShXt+qLBC6K1yYDqyk745hOBnqCBULRmLASq3NI"
    b"PB3vlwg1q1rwjxAAW4bJaluJPJNrFO2Cd1ovNa1NUtM6EPumyXHHybfuFTkPGAoSxehSx2bf"
    b"LRA5oUxflkRvk5SsFjW73+T7xcqi9uEkQR0BcapU4ZXC97w7Db5vWo26UpQkfmSjbz0uttmo"
    b"K2mcjA/wp1AFn9JkpepBU9P4Ix7/A6+u1m3fs0SBAAAAAElFTkSuQmCC"
)


icons8_end_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"YElEQVRoge3ZPUvDUBiG4asqCCIiguAiFAQHwR8guDmKi+BfcHV0cHV1cHR1FFcHJ8HBwV1w"
    b"cRJxERFBEfFraIIZtLbmaJPDuaGEvsm5m4c0yckbEolEIpH4PzYx2OudCME7zjAX2Nnu8yfk"
    b"8jfsYDigsydBnrPlBRYCOTutByGXz+LU59HZxVhJZ6f1IBTlA1jDQ1a7xnJJZyf1IHwln8JR"
    b"Yd0exks629WD8J28gVXcZ+tvs+9lnD0JktPEYWG7A0z+0tnTIDkruMm2vdM6Oo0unZUIAhPY"
    b"L4w5xnQXzsoEyVnCVTbuEevo78BZuSAwqjUTyMefYOYHZyWD5CziMnM8YaONs9JBYATbeC34"
    b"ahkkZx7nbZy1CQJD2MJL2d/qC7VHdSP9tQpEcbLX/vIbxQ2x9lOUKCaNtZ/GN9X8wSqKR93a"
    b"Nx+iaAdF06CLpmUaRRM7itcK0bzoSSQSiUSiyAcoKiORfFCb+AAAAABJRU5ErkJggg=="
)


# ----------------------------------------------------------------------
icons8_group_objects_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"0ElEQVQ4jcWUIRLCMBBFHwwOzxmKJRo8shrNAdBYqvHV9dwhvrVgexNEN9MtkzZNp8CfyXRn"
    b"tvvz/24S+BIKoJSVRtSlqq4AWEliC+wkvgDHkYSJqkMTaljgEaFw35ewwE12HYtEaiyeVuWA"
    b"kVj3VC/fZkZqAb9l6PZUYx2SvAz9EIs+hUNw9mogm4PwLN/KR/gzyyf8A3hOJXypOKe1GcRf"
    b"plzTDOATg/Znu3oLSZS0NyMj7nG4SlwBxmf5AGwiFHbgCHU/7pEK3fEKHqlJeAOCaiebx3Kk"
    b"lAAAAABJRU5ErkJggg=="
)


icons8_group_objects_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"pElEQVRoge2ZQQ6AIAwE0fj/L+NJDx5A1NbNMnMj4dDJhjakpQCEsFzOdfB+NLfrWYMLScNG"
    b"ZBu834v6N6ZNRO2xn9gkYiPSohatx92sxyaR0cd+8CapkIZhkwgiaiCiBiJqPJ0jX9CaRcOz"
    b"xiYRRNRARA0bkaftN/vv3mX6RHqkf5FtEkFEDUTUsBGJar/pA9MmEXaIatiIsENUgx2iGjYi"
    b"AEHsbs4PYp2OHEMAAAAASUVORK5CYII="
)

icons8_ungroup_objects_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"rElEQVRoge2Z0Q6AIAgArfX/v2xPvTQrRSTEu7dWsOFJLEsJAGAmtpd7WRBTi3ruXRrojUMQ"
    b"87Sav7K0kZE9IiaMkRpyGtcXarnDGAlTiKTZrWgamhhRprvhMaJMad83WcKIAZelfLsuEsYI"
    b"hXiDQrxBId6Y4ThorTnCcZA3tI6DqvZx4Xk1ljCi8XYyyx3GSJhCehV7GZpxjIz61DUfmhj5"
    b"wPwfShgjAABzcQJJkRZZ1xWWJgAAAABJRU5ErkJggg=="
)

icons_centerize = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAd0lEQVRo3u3a0QmAMAwFwETc"
    b"f+U4gSBSbRsuA5QeSXn5aEZERZPqAKmjSzdAQEBA9qpzk6zJUZBHh80MbG8EBAQEZOlA/DI0"
    b"czXIm0uV0QIBAQEBAQGxNP6/O82EpNECAQEBEYgrht1ISBotEBAQEJCbfGjx8ewCQdYKbRHZ"
    b"jdYAAAAASUVORK5CYII="
)


icons_evenspace_horiz = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAeElEQVRo3u3aQQqAMAwEwI34"
    b"/y/rWVBREY0yey902BZSaHI8U67nrbXfS62o6yN7X+y5NqqrnWqrGSJJMvzlaIGAgICAgICA"
    b"NMz48HBXGrmhkXJHQEBAQEBAQEAMjV1z6gmgkYMpdwQEBAQEBAQEBKRNfvOpJtIsM9/aDGBS"
    b"7NmKAAAAAElFTkSuQmCC"
)

icons_evenspace_vert = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAaElEQVRo3u3aMQrAIAwFUOP9"
    b"75zOUnCSqul7k5MkYPQPRhtlu0u8Fhc2MfTQWxFlGokqMwKFz1iuqN/1e5jsRgQA4PiMkrtr"
    b"EePFeDEeAPhvjM/F+0m/YrwYD59cv9vq96nGO2JG5vU/iNoMJLKY0+4AAAAASUVORK5CYII="
)

icons8_computer_support_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"iUlEQVRoge3ZT28NURjH8U9VQtJa2mixJ3RnodJYYYE0kbbBzkJCuhPSF9ClxCsQUQsLkSAk"
    b"pDQEb0DEjpWKSIgWCa2UxTmTGdN7zRVtZyaZXzLJnec55znPd87fmUujRo0aNWq0stqJ25jH"
    b"r4pd8zG3HZ1AzFUg4aJrrgjmdix4C1uKqEvQFn/m2FbJcKoiRKI+aa+0VdJ1VdeyPNeVlMiK"
    b"qwGpmhqQqqkBqZoakKqpriB3FJxA6nJEgV1/c1YFpBfjeIhZLOIDpnEe24sCVAFkDO+1fxf5"
    b"iN1FQcoGmcBSzOExRoVj+xXp0X1PJ4HKBBkTIBZwOmO/JOT0DUOdBisLpFc6nLIQk9H2HQfa"
    b"1B3AtryxLJBx6XBKNBFtixhuU28PPgkLwB8qC2Q6tjsa7zfiR7SdalNnSPpqPp13lgUya/m3"
    b"gploG2lR/qAwZ5J8P+QLlAXyPba7IWO7EG2Xc2WHM+WT1exHPmBZIG9iu/0Z2+5o+yrAjAjD"
    b"bDHaL8Xyv/A2H/BTdPStZtYtdC22eyJj68IrrTfFyVjmeLx/kA94IzruWDuYbtyM7d5t4R8Q"
    b"htmMMIQmMr6nsd4ZeG5tP3cuSfeKbmlvzGOwAHpj5vfZWO8deuBLTSCyOivMlSUcS4zJMnfu"
    b"HwL9r4og9uEeTmKrsJr1C3PimfShXMhWOhwdCwLM5lVLP6gTiKJR8k6mJ7KaLKi4VsMpC3ET"
    b"U3gt7BuzuC9M7J6/PanDeNTB01hNiOTIMRXLV07duCrd4Pbn/HulENexfk2z61DrhCdc654g"
    b"PTPVGgJeCokeydlrBUH652pvxlY7CNLz0EVswlE1hIBD+Gn50nxVjSASDeIJPuOFsLd0rWQD"
    b"vwGZX5eIvM3txQAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_smartphone_ram_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"5UlEQVRoge2YQQ7CIBBFX3tDvYj0jMZLVL1K6wIaF1ogJoUB/0smDWEW88N8SAeEECKwhrC6"
    b"D8CYSmiFboR0ywhMwIN3b1qLO+CAISZkMlBobriYkO0kTrGkypzxNc6xpCUkRY+tMgO+xiWW"
    b"lHVnG+Cjzpzr9wZcDa2/kiNkazcr6yy6bq0m+MUjpTnMI6WRR5pEHimIPNIk8khB5JEmkUcK"
    b"Io80if7ZK66z6MYj26b1AR0khDzD1+rIdMCPTMGPd3dx1B9O58YlpdjhB8S1C92LOYiw3P7H"
    b"krrJau8Df/ayCyGEHV4Hpj6QuXY7DQAAAABJRU5ErkJggg=="
)

icons8_image_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"lklEQVRoge2YP0oDQRSHv2ghiFqZwl5whWgluYAgnsXGzhS5g72HUJEk4BFSiYJXMGJKBQMW"
    b"iUVmyBB23Jnd2cyA74MfYZd9w3w7b/9kQRCEf0EDmMWeRAjWYk8gFCKSGiKSGiKSGiJSE32g"
    b"DWyp34FP8SyR9Czzu3esjy6gc2IRabvUp/SutQN85ezfBj6Lin2ukTHw4nG8LweW/YeuA7gs"
    b"+xg4AjLg27HGN33L/AaO9YUHfAAtY+CrmkS0zPJdy7XWWWIfWFcZ1ihTNoXtBPOWelerobfr"
    b"arGgIuZKtNT2DJiwuPg6ltqfVERsEjpDFi3WA+6ALnAONC01KxfJa6e8og5/kwGjWCJFK2FG"
    b"t1hTrUQXuAWePcaoRcRHwpTJ219mrCAiru3kE3NMGxnwFFKkrrO3/CDNYwO4BqYhRPTZCbES"
    b"rpkAl8w/EAKcAm9VRVYtYeYR2FMyu8BDFZEY93wzI+BMyTSAC8q9NUSV0JkCN8AmFYgtYeYV"
    b"OC4jkdI/xEqk9hWlNCKSGiKSGiKSGiIiCIIQhV9aqvtgADl99gAAAABJRU5ErkJggg=="
)

icons8_cursor_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"CElEQVRoge3ZT8hUVRzG8c+bovYS0cI0IsgMw4VRFEJERIskUVpFhKvMpKRFi8CEFkok9HcT"
    b"FES1aOGmIhe2UHFhRNRCJCIysDAI1LKgIq0UdVqc3+VeX+Z9Z+bMvXPnhfnCZeY899zD88zM"
    b"e87vnJcJEyZM6MFRfI0b2jYyLJ24fsCKlr0MRadyncLt7drJpwhxIF5/w9pWHWVSBFmED+P9"
    b"Waxr01QORRBYgHej/R8eactUDtUgMIXXQruILW2YymFmkIIdoV/GcyN1lMlsQWAbLsX9V0bm"
    b"KJO5gsAmXIg+b+GqUZjKoVcQ2Ih/ot8eLGzaVA79BIH78Vf03YermzSVQ79B4G6cif6HcW1T"
    b"pnIYJAisxs/xzBEsbcJUDoMGgZtxPJ47hpvqNpVDThBYLpX/HfyEVXWayiE3CFyHL+L5X3BH"
    b"XaZyGCYITGN/jPEH7q3DVA7DBiFVzh8pK+eHhjWVQx1BSJXzezHWeTxaw5gDUVcQUuX8urJy"
    b"3lrTuH1RZ5CCauW8veaxZ6WuINO4BffgYXxeGXtnv4NMDWGgCNHvGLdJ+5Mbcb20niyXgszG"
    b"3/osZ0ZZjW7G013089LBxa9x/R7t09Ja0zi9flpP4lNlTXWn9Nu/iA3SNzQWxeNcQXZU7u+u"
    b"6AdDe75Za4PRLcgUXg292OqewZK4/2BoJ6XFcCzodorypisXtiPRrp6oHA3tidHY7M3Mc60P"
    b"on0O60N/PLRvlbPbptC+Nyb7+CLIYuyN93/ivkqfxdLs08EDoS3Aj6FtHJXZuSiCHFb+LdzV"
    b"pd+LcX9vRXs2tM8a9tgXM0/j18zSb5l0jHoJK0ObltaKjrSit0oR4gRu7dF3T/R9o6K9FNrH"
    b"jbgbgEP4Sn//sVqr3EBdE9oy/CstkL0+iLHiSynMMxXtndDebsVRJo9Jpo8rp92V0jdyTiok"
    b"5wULleda6yv6J6HtasNULi9IpvdHexFeVk7fY3k23I2l0qH2ZakmO6mc/b4zj4LA+65cg77B"
    b"U1IVMK9YLS2Gh6Tjn2F2qRMmNM3/zsPl3mj86SEAAAAASUVORK5CYII="
)

icons8_pencil_drawing_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"f0lEQVRoge3aP2gUQRTH8U+CSY50Aa20sBVMjKaTdCrYiFZa+ae20i6FRXoVES0iWoiIlWIU"
    b"jVpo5R9UUAwWighRhKAmSkALIeEsZo5L4t3lcu7eJsf+4Li92Xdv3vdm38yb3SNXrmrqxUec"
    b"auTLa5KNpWH14iHWoTvjWBrWJkyiiDF0ZRtOY2oJiD58l0Nkr5aEKGQbTmPaosUg7skhstN8"
    b"iDuSS+xOXMJ1tCXks6rShLgd/X5Be0J+Kyqty6kTo9HvN6FGS005RA21DMQtOUT96leGuC89"
    b"iL6E/FZUP6akC/EDAwn5ragcooZyiOWq5SAeWKUQ2zAdO3stOYgu3I1+p4T1KDWtVR6JIn6j"
    b"JwG/iyH6E/BZU8djZ4/xPB7v/U+fTYeA8djhPozE43M4K2xsRrBjGf66hD17UyEGlEuEDuH+"
    b"bLHK62Qd/jKBgPOx0zPxcynh3+AEDmAIv2J7rZEpyAiiSznw0myyU8iPxfvkoWg3UsVXZhCw"
    b"P3b8ahm2oxXOFYTSvgSxNakA56vWxv1IfL9ch58N8X1yUXsBN7FbWOx2CetQ07Qes/gjrCNL"
    b"6anwix8ToNosHIlpKY3EUipd8zfqsB307wz2CS9lDNGGdzGIPXXY9wn3l54J68pbZaBpobzJ"
    b"RNtjEJOW94yxQ5jRnlgBEHAxBnK1TvvNOI2vyiMxJWOIbszEYOZwuIpdD47ihYW5MS7UZvVM"
    b"EKnqoIWBzeFQPNcuJPYFoQIu2fyMbYPNDraWKtVSs8Kd78+L2saEhXDFPTrbKIxAtaKwiPcY"
    b"jrYrVsMqBz+DK0KdlfqziCT0wcLceCTkzKr4S8X8dWJCgLgm1FcTmUSUq0X0F8OGEKWXtluf"
    b"AAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_light_automation_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"oElEQVRogc2af2iWVRTHP++23OrdkoLSXFsoo9FoC40CyWFulGWLLUiWEkQa+yPKgn6Q/wlJ"
    b"aoQQBEX4RwX9oYsosR8EpVikC3JulT/ISjfLpbasWU1x79Mf5zzeu2fPj/u8e9+3vnB5n+ee"
    b"85x7znPvPfec87wZkpEBFgCdQCtwDXCt0oaBEWA38D6wz0FeyZEBuoHDgOfYDgPL9dn/BRqA"
    b"rzAKHgVeBu4EGoGstkZgqdKOWvx7gXkl1zqAVuAkotAw0AOUOzxXhszGj/rsb0BbkXRMRBtw"
    b"XhXZBlyWh4ws8I7KOA/cXjDtHNGAvEUPeJHprfMM8JLKOk0Jl1kGsye2UZjNmsHMzJ4CyUxE"
    b"tw54jPyWUxSywJDKvr+AckORwbjYh4og/2GVfZAiz8rNGBdbVgT55chMe8D8IsgHRPEuvX4P"
    b"yBVhjAlgu153FkE+IIYs0uuPInj2AYPA7Bg5s4EBoC+C/qH+tqZVMA38/XF9BH0As8bDjJmt"
    b"NA/oj5DRqPRD09I0AWM6SHUE/WrgW0wsNceizbJohwI0G9XKM1YAfSNxTgepieEJM8bVCICZ"
    b"yvdPAfSNxIgOckMCn72EDgau4/YPQJPy/jwtTROwWwe524HXNsbVCIAO5d+Zp46JKEMMATdD"
    b"RoAl1v0S7UtCh/7uclctPRZgQnbXA9GfERdUYJZvc2rtUiADHNGBuh2fSWPIKuX9Lr1q6bEa"
    b"430qHPhdDanChCcr8tYuBSqA73XA5xz4XQ3ZqHwDFCeOC8VSJNYaB25M4HUxZCFwQdvCaWuX"
    b"Eq9j1nM2hi/JkCuAnzDZZslRjRjhAW/F8MUZkkEiaQ/JOmckjJkBepGZC5aX/kKKH3mhCTir"
    b"glZH8MQZ8oTSRoG5juPF1cqOuSoehgcwb+S6EHqUIfX6TA64z3GsZSpre6C/ApmlCdw8aSS2"
    b"6gBvhNCiDHlb+9+MkLkIeBAJIn3458yWEP4TSqu1+uYBjwItMbpPgp9DjIbQogz5XfsbQmgr"
    b"ref+ADYDjyARhQesD3nma6X1IefQu8gM+SlBvasxUQqn7a9GIl8PyThzFu8EUgAPC1+WA8eZ"
    b"vGf+Bg7o9dZSG7JB+79AvFQLsmSHSC6rVgObkGW2DrgKyX38hHBxkhFxiqXhb0AO2QmkYmPD"
    b"P+2rEG/Xh3jMs0ghfA1QGeD1sVbH2o9DbTrOLcY1G71Eb2aAOqS4ESVrP+Z7jI1KTLDbU4r4"
    b"x186p5j6VquAD5D9MYjkLTXaOoBvgJuAHZiZ8ZFF9g841MsKsbSewniaz5jsSp/EBJVhxY8a"
    b"4Afledzqb8c4gVHglnwUy4f/DuAXpdlZol84vydGZpfy7NX7uZgXsxNZmnkrlg9/HSZa8JFU"
    b"igKZFQ/4U++zej+OtVRLliMg58g5pNofF1kHEVf4vhi6JBlyUn9vcxjQL73+GkKrAz5FNmwO"
    b"qZOBHGwQ/1WrXX/9VHkWMiOVSGXTRbeLGV6atjEg41ZkQ3rIBm23aGu0f5DwAuHlmG+Sj1n9"
    b"bZiMdgJ4JsmQcuB54IyDAWeQEzwYqb6K2eRXBmiVyDnhId6pE+N+uywj+pma11wKvKL000mG"
    b"+LgXs8GeRlxoLfAssu5zRIcKPfrsEaaeBSCHnW9MWOtnssu28Zry9LoaAvBCxEA54qe23FJ0"
    b"bYDm79FK5JzYg3iyMeBLZDnNCPD6mI/kK+OER9uxWAZ8gkzlKeBj3L6lL8aE3nOQwG8dEghu"
    b"It79guyrISTQbEE82ecqc0NaI6YLP1E7gITi9qweR0L2IJqRzNEO+3NIKuAhLj3pJRQc9ZgD"
    b"cAJJklYgEa+HJFFBrFfaMJKEbUaSMt+olUXXOgLNSJpq/4GgFlHqRAj/FqWtsvpmIumy0/lR"
    b"SthFhksCtB2IIXeVWql84deHo1rTf6daOvRgaml2u4DjX0r+BXGoAPepC/FyAAAAAElFTkSu"
    b"QmCC"
)

# ----------------------------------------------------------------------
icons8_light_off_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"AklEQVRoge2YvWsUQRiHn7vEC+qBIJfjEL/SJCgKEsHCaNRKLVTQiDYWIljaKQp+RFTURuGI"
    b"xMbGziKIf4CKhqCNIvgVsRBzEWIiAbkqCXgW8y6ry87t7O3M5Yp9YFnY993f+5vdnXnnDlJS"
    b"UlJSUlLIONDsBQ4B/UAJWCPXK8AU8BJ4Arx1UDsxGWAAGAdqhsc4cAQ3D7MhuoBX+Aa/A2Vg"
    b"L9ADLJejR66VgYl/8seA9U13HaAP+IkyVAFOA20G92WBo8A3ufcXsMeRx0j6gTkxMoJ66nHJ"
    b"A49FY040m0oXMCMG7pDsO88Cd0VrWrSbQgZ/ToyIkaRk8d/MGE1aAAak4ASNfU468sCkaB+2"
    b"qBtKBn+JPRkSLwIX5KyjEzgDFEJip0T7UzKb0fTiL7Fhq9N5iX9GNcMgJYnVgLMh8TbU6lcD"
    b"tljwq+WqFClr4kV8o8HBlAKxTo3GkORcseBXy3Mpsq9OTtBwSXNNx37Je2rBr5YvUqQ7Ii9o"
    b"3HQQoHYA3hbGGVUpkjfILQIf+H9vtcrgvrzkV+MYi9sDcnKeN8gN9gLT3rAg5yWG+Q0xjXpa"
    b"9ZZXSPZplSR3KpHTCLyOviPCSJLJvhO/wzvjnhS5rInHWX51b/WS5AxZ8KvloBT5qImfI1lD"
    b"BHgv8QOJnEbQgT9PtoXECyiD9eZQUXLCtihbRXtGajnlohQbxf4u1Wu4Tru6x1LUXqsGnLCo"
    b"exz/l+Yyi7p18bbyVWCjBb1u4LdoHrOgF4th/I69MoHOCvwdwAMLvmLTAbwWAy9obHLmgGei"
    b"8Qb12S4KBeCrGHlEvC1PBngo904Cq627i8kGYBZlaDDGfYNyzyx25pkVdqE2e/PAJoP8zZK/"
    b"AOx26KshbqOe8LBB7n3JveXUUYOsw/x/X+9Ya6u47c5cW6z67baEAkQZjDvgSGz8S9gSuBrI"
    b"qGi/I3xuWMfVQDyzfxzpO+cHahDb6+T04XfzluUm5kvvjUXyaEQONRjvzYQdk6hB5DQaLUc7"
    b"cB31Q6kCXMPdcp/ScvwFg4D0wSiNpC4AAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_light_on_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"P0lEQVRoge2aT0hUQRzHP09Fq02CYNmlDkJYUuShJLwkhVHdrIOhp6JLl07dO1h5MezQyS4d"
    b"K5ACCdJbEgXZv9X+oR5aTMmif5R1sj/bYX6PN26+3Te7My8TPzCMvPf7fX+/mXnz3syssEJk"
    b"7gCP/nUSNshJcUqF6wBxsdKQpUZVDDHuEcMcicop4CaQjDFmErgBnLQpOoDq1edAyqZwCCmJ"
    b"lQOu2xROasIvgXSInQc0AWeBYWAC+C5lXK6dAXYWiJWWGH7HWX8KUlqAsbx7HtABTBJ8N4qV"
    b"SeCI+Oo8JegwZ6OfRjViRLtWDzzUEpwCLgIHgAYgIaUBOCj3pjT7EWCTpvcAGCV81J3QAryX"
    b"hGaAE0BlBL8K1GhkxfcT0Ooox6K0AvOSSD+wpgSNBGoy50Rrr7XsIlKP6sUccJ6/n3MTPKBX"
    b"tD6y8DFzikcwJ/oprxG6pj8y9y1pFqVDAr6mtMcpjAQwLdrtFnUXxSN4xR5zoH9ctMdxPCpN"
    b"BK9YFwvOStRI54AdJo6myRyWegD4begbhV+oNR3AIRNH04bslnrI0M+EQalbTJxMG7JR6leG"
    b"fiZk82IZs5aFSwe/3NVs5uRabalBIlArMeYM8oo0IvqmqFrq+XIyLYKvXV3QqszNmr+ucrkn"
    b"SUuMdyZOpnPEnxubDf1M8LWzBa3yMG1IRup9hn4m+AvHUYcxaCPY9LjC34m2OYxBDcE8aXag"
    b"768cPkgsp5wmeP3ZXg8Ni3aXZd1FWU2wHjpqUbeTYKeZsKhbkHYJ+g3YZkFvC/BVNDst6BnR"
    b"J4EngPVl6KwDXojWZQt5GVODOgHJoX4DKWVyVgO3ReMJ6rGNhTTwGLUdBfWF909CrmE2+T3g"
    b"ivhOAxvkegZ4hsPjIP2ALkOQ9FbgM+Zvmy7x+QI0atfHcHhAV+zIdA/wA7Xg2x5Br1HsfwL7"
    b"8+45PTId0oTDeqlHbPoi6F0S296Q+/oh9mCITUl0A7co3Dt1RD/39UtdAb2kxDwXJUHbX2bT"
    b"PYK1+Mvmp7dl0xDb6L+pN8vfu4rYWcHliHh59X/FW6K/sd7YDGx7RK46so2dVcAFYJbwkZhF"
    b"fQid7wBtUYX6kM5I6Saef1BYYUnwB/Bb9Q/vjd5CAAAAAElFTkSuQmCC"
)

icon_cag_union_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABHRJREFUaIHF2muI1FUY"
    b"x/HPzrqabpqSlrds1cjAKDaTrSiiIMWsXhVZRFYvKqgMKqQLhCXUKkkSalFBN6jEjKJeBFJQ"
    b"2T260GUrs5tvDOlmmqtu2otnZl23mdn//ufM+IVhhpn/+Z3n/P/POed5njNNGssJWFh8n4zj"
    b"cAT24Vd8V3y9hRewO6twU2pLy9CMBViOiegWRm7GDvyBw8Rgjse84vu/eBTL8EsD7KzK1egS"
    b"d/ZpnIlChnZjsRTfFts+hNY62ViVFryG/ViLKTl1CuJm7MJfOC2JdRkZjQ/FnbwikeY48WS7"
    b"MTeRZlVGYCM2oS2xdgGrxA2ak1j7IJqFT2/D1Dr28zD24JR6dbBarDTt9eqgSLN44r9heGrx"
    b"NjEhO1MLV2Ai/sG9qYXX4WMMSS1chRuwE0enEpyGHlyQSjAjLdgiXDoJ67Bd+G6jWS2W5CR9"
    b"78BjKYRyMEVsuufXKjSuKHR2rUI1sBn3ZYl7qjFbDOTT2u3JzQY5lvwjcSdexldiye3G9yLI"
    b"K3E6xtRuYyZuw49ZLz4Jz4tQuwcf4C6xyz4u0oG+0Wkpcr0nkbHVuBl7B7polAi/94oYaqHI"
    b"HUpci8UV2jaJOVT6PD2vpQNwlbjBFZknXGenSIzKMQMzM3Q2AV9iUXb7MrNIeElZ5gvff0+k"
    b"oikYKVxxfCK9EivEFvA/LhautFK2bO6QZG59eARv9v+yQzym5RlFCiISHewyPlu6gK8LS/p+"
    b"0SrSyW8Mbst/qWjYYBiCt9W+I08V+9hB/XfidwdWmqycJZbnwdIm3LgWVoi53OsR4/A3rqtR"
    b"uJEME5P8xb5fPiNC4qE5RZtwYs62s+TL9G4UUXevBxVEDrwspyHE/OrCsTnarlR5n6rEeGzV"
    b"b8GYKyZMWw4j+jIfr+Ro16GfewxAQdy0n0XVppelYqVKwegcbZoNbrFYK4ocs/r/8LooSaZk"
    b"pvR15VJday+uL3fBVtySuNNV4s6NzHj9JNWX/TF4VaysFYtzPaIikZpFuDTjtUuUL682FXV2"
    b"iUGcWk1knwjP60k7zlHZ3RaLlKDECFwm8p4e8TSqxnQFMdqq8XwibsLXDuxVo4TLNIsDn3Y8"
    b"KBKy7XhSLEIni1LTzoE6+EFkWY3g8D6frxRFvU3C8G5xWvWuSF8HvQJuwBO125ib0cIjLqxV"
    b"aK2ooB8qzhUDGVur0EViZ59Uq1BO1kh0RjgEf+L2FGI5+t6BZ1MJ3o+fRGG4kSwQbpUn2CzL"
    b"BLEM351KMAMt+EwUwZPylAjnJ6YWrsAdIrWenFp4uEh1P1f/I4IOEcHeWq8O2kVMs6ZeHYh/"
    b"NewSteNai+hVmSOOgNfXoaPp4hjgC3U4yCzHJeLRd+GoRJrXiDmxUbrqZSY6xJzZVjQi77yZ"
    b"Jv7tsx/PaeyBaS+tYo/ZLf6G1ClbKNGMM8SR3J5i28vrZCOyp6PHiBrrHGHkR3hfRATbiu+j"
    b"xFHxeSKfHopPxODXq1+q0CLHXB4motQVeEOEFz3F1xYxuHfwgHCpejNJbKgz/gM/suiaaJQA"
    b"JgAAAABJRU5ErkJggg=="
)

icon_cag_subtract_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABAlJREFUaIHd2luIVVUc"
    b"x/HPmZlKzckGNMuBYlQoTNIw04qmq1j5IFQiRRBFD90ZzKKiol6GLk6BlVIZ9BBCUFEkWhRB"
    b"lF0pqYfCbhZ2o6ws7WLWTA//M3mc5pyzz95rzlBfGJizZu/f+u+z1/rf1pQ0ly4swtG4Dt+X"
    b"x2eiBy34E33Y3GTbMtONXhyL1hrXjcH+FZ9LI2lUM5mHh3DIaBlwBc5NpNWJR3FGIr1MlLAC"
    b"FyTWbcGpiTVrsgBnNXPC/zoHjrYBqViLialFWzR5I2IqVlYakIJz0JFIKyufYgcOTym6Vu0g"
    b"N1KMG5y3LYHYVLyHvxJoNcqvozDnyPJ/yGNKWFhkaR2Mw3AQnkliUj4GsKSRB2kVEfsynIAD"
    b"yuM/YwKW48iy8Du4L5mp9RnIclELLsEW9Is6oRcn4kF8N8w9nYkMzMoD9S44ChuxC3eLpVTJ"
    b"KmzNMFEfzm7UugborRUQe7AJuzEby/D5kGu2i0KoHstFOrHa3kVTKqqmKivEuutV27NdJKJr"
    b"Vu83U8Sd1Dw83OBNIrhdnkFgvnjgQxMalYfVQwcWiIe4OKPAGPyG83NMPla6XG+vFdGJb1V5"
    b"TTV4EU/mmPxkXJ/jvro8hQ/FN9UIV+EPe+JKI6zEtBz3VWW6iBF5lkg7fsdtOe6dKEMMqMFc"
    b"EYT/4Vl8If+avV9konlqkiJV3loV7rxdxIpLCwiOx1dYU0CjUZbiwsqBJSJyTygovEgsz6UF"
    b"dbKyzBBvdS9eSSR+h1hi3Q3eN1uCUvll3FNUpEwLNggv1kgz4jycXnTybcKFpqIN60RgvVW2"
    b"9GWOKA9qMUMkrlXZLZ/brUUJt5S1N+KYOtd34YYqf2sT+2GVcCpV6RftnJFghoj8A3hOOJbh"
    b"suXJuKaKxjSROtWkTXxr7bnMrM/7ovF8Cm7GY2LJbcZL+AA7MUUc/szBLJFhDDqgT8o/ddmi"
    b"+mtNzSRRbW7AG6K++UF8mV+Lo4iTsF8e8XV4JIWVBdgq9kBuWvCmaCaMFuPFadTTRYWOF5sx"
    b"aQ+1ARaLA9DCnfWSqL2b2b6pZL0Eb2OQPpFajEslmJEu4f7PTCXYIRLH21MJZuR50RdLVfIi"
    b"/PwvoshqBovF3lyYWngfvI63ZOtVFWGK6A+sH6kJusSrfsLIHdx0iPOUdxWvgWpynEjDX5Az"
    b"wtZgEl4VKUdT/pOhWzQUPvLvfm8Rze0iiiftnAxl7pAJpotcaIfo3eZ9O5NFr6xfpPR52kYN"
    b"MUsUQjdWjO1b/rwTXwrPlqU9WhI1SJ/whNtwdUJbh52wGmNxLe4SaX4Priz//o1Is18T3meX"
    b"OLnqEkcR88vXfSzK6DVi340a8/C4PZVZK04TS+VtfIafRBr+o3jATbgTRzTT0L8BzGe6xLiL"
    b"7tsAAAAASUVORK5CYII="
)

icon_cag_common_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAA3BJREFUaIHV2luopWMc"
    b"x/HPXttsRtu2t7bDjjBrmDFm2pHaacpEkmHQNqGYFEPulDQolMNcuJDD5BSGCxkuKE1N5Nhc"
    b"SE0aUhSJMkoOaUqOMwYX/zXTsqy93tPzrr18a13s533/v///eZ/3eZ7/89/vsP6yFKvwaevv"
    b"O7EeR2Fnq+1+jGEX9vY5vlxcibtwWsZ947gUM7VHVIBVmK6ocS42YaJ6OOW4HXfj4ARay3BL"
    b"Ap1STNakO1ST7r9YgDNr9rEea2v2YRNW1uxjCI9jRV0OjsG1dYl3MILhPvnqC8k7U9swZ7AR"
    b"x6cSG8WzqcQKcoLIBJKwDuenEivB6amEDjIAE68vm0vNDGGm6pOcxho0xFzZiz0VNctwb1GD"
    b"IZG93iw2vjfxd8fvJ7wl9pSxVJFm8EyRmyfxIjaIzizADhF0E8uxWiyJ2/Fr6/cETkwU8Fwc"
    b"XlVgu0hLujGGG/A5/sTD0mTC3bis18UmbsoQeBVPZdwzjDvE3PlSPaPz9FwXVmKL7MPMVryb"
    b"09lifIXvVD9sdfJgt8ZjsVnMgTwCPxRwOIo3WjZLC9iVJu/+ciH+UuwQtVCM4hfifD4QHIY/"
    b"cFVBu0nsxtsJYpgVOdcBTioptBXbStitFvvOxSX97ud5bSnSkXrM/Axmxeu1pITtO/hG+VTp"
    b"EFzX3nAPTi0p1hAr0eslbE/BPtVHBTEsz1XUWCtG5ewStq/hlRJ2TXHkPUADUyWEOnlJ7BNH"
    b"FLS7WiwYowVsxvGyjo6kYgLf4mPFUpGjxWheUMBmg/KLUy6W43eRTB5awO5HCY6si6sKdHAG"
    b"vsf7WJTTZqfY8XsxISP325zTWRGaIrhfcKvso/A2fNjj+sliTvR86HV0hJgnj4kU/mux3s81"
    b"obfgky7tC9u0MnO/ujqyn2bLx29ihHaItP48sYlOidfqgzabK/ACrini6KLqseZiHDfiPfzs"
    b"v0fkXW33TvkfFUbGxSo3g0fUX8XvC0sMQG1sYGjg0fkOoioNkR7swXHzFMOylGKL8EBKwZxM"
    b"iyNEUmZTC2YwJAp+lYtr8806XD7fQaSg9uV2ArfV7SQ1jS5tu0WS95D4J05KzhEFwL5ylnQr"
    b"2Yj4oGaj9A+nrzwpPrAZCEbEFwdr9C4UpCpmFKLIyrFP1GxX4HrxinzWdv0+URG5pKX7UaIY"
    b"c/EPAZKIlZ2aclcAAAAASUVORK5CYII="
)

icon_cag_xor_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABMpJREFUaIHF2nmoVVUU"
    b"x/HPe0+zEbMyNZyygUqxScOKrKw0oiIjgooiqH/CimzwD0mbw0yEgtRACiJIqGiAaJ7IAm3O"
    b"Jk2bJ23UrMyh+uP3lKe9e9+59577+sL5556z195n733W+q21b4vuZW+cghMxEAPQFxuwGsvw"
    b"Dl7As1hX1HBL2SPthFacgykYiR9lkJ9gVfsF/bAfjsAorMX9mIUvumGcVTkVH+IvzMMYebGu"
    b"2A2T8DHWYyZ2atIYq9ITs7EJ8zG4TjutuBArsRQHlzG4ouyK1/ALzijJ5h54UrbbhJJsVmVH"
    b"LMRy+bDLpBVzZJuOL9n2VrTJrH2DYU3sZy7WYHizOpiM3zGiWR2004bn8D62L9v4UNm/15Rt"
    b"uAID8DOuL9vwQ3gLPco2XIVJ+AP9yzI4UCLzaWUZLEhPCZQzyjJ4Az6XvdvdTMF3ZfW9AtPK"
    b"MFQHA/E3jm/UUJ92Q0c3aqgBluCmIrqnGofgH9mr2zU8pPp4FaNr9TK743Qch8MxRCLuV+33"
    b"f8ZHIlGexkuit5rJMpxUdEVG4gH5sO4UdboAiyV/GCsaaEr7b+PwjKzUVPQuc+TbsFK0WFV2"
    b"ERW7QWb5bOzQ4f49eKRC28G4Dj+0XxdpTv4zERurPTAGX8sqnFvhmbtEX1VjJ9wqYu8xWc0y"
    b"ORe/Vbp5iuimBapvi5vwesEOR4mr/hCDCrYpwhX4rLMbZ0lWdoeus7kL8KviW2ZPvCEyv1/B"
    b"Nl0xV1LnrThIlum2gkZGiPs9qIaO+4hyXawcl73UNuJxZ3wgb1c05LeI17iixs6HiqueVWO7"
    b"bdlXJvKIjj/OwLey/LUwR/HvpCPniLdpJA+/UiZyyyfQV7bUJXUYGyWzclQdbV+UwFkP20sg"
    b"3kr93i7Bq1edRp/TyQdXgLEyCYfW0fYySXm3BMM2CViT6zC2mcNkm5xdR9s3RS3UQn/ZUjd3"
    b"/HGMzEqjBYPZ8gEPqbHd1VKwKOrC22RLLpGqzRZulCDVKL3EpS6R2lZRRspEHljw+VnyPR+w"
    b"7Y3nRWqUQT8Jdq+LAylCa/vAzu/iuTYZ53qc2dkDX+Dygp0WYZCs8AqR+kV4S1LmSvTBw/LC"
    b"FSuNa8Wnl8lueFyE4i26LkA/pfNd0SIrtVImfHQ1IxtFCpdNCy7GT3J0ME3lYvajkhJsZkec"
    b"h0VqqMavUVmml0FvXCueaZO429nykhNwDN6Wb3U6nhDlvQ73qaE0+qnGYkhR2uSkaiZekQOf"
    b"fzpca/Ae7pXtVIvnQyTC3SUNtlZ6iHPYhGMbMdQqrvLIEgZVDxslELdI7l83rbI3h0ux6/9g"
    b"nMSe1Y0aapO8fEqjhuqghyjY6WUZvBVfSmG4O5koFZq9yjLYX0r0k8oyWICeeFcKHKVyvajX"
    b"AWUbrsBUcbllVlSQwtv7asvZ6+VQ/IlLm9XBCJmlec3qQAoG34sWa7SIXpXxIvbmKn9l9hFV"
    b"/LKtS69NY4Ko4qfVXlWpxFlSzFuouUXt/zBSjgh+EIFX7+oME/H3txQ5utvFI3J6cwF6uSRg"
    b"RTK/NjnFmi8yfAlObtIYUTzhH4SrRJX2loxukRyyrBL1umf7dQBOkOTqbSm/Pigr0jRqPa/o"
    b"JYMcJy50f5Hb28kLfSOS43k5bui2/1n9C7S9B8+2VLKzAAAAAElFTkSuQmCC"
)

# icons8_grid = PyEmbeddedImage(
#    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
#    b"AUlEQVRoge2WOQ7CMBBFn2gjsdwEOrYTstwuULLcgQYaKDJRLCumQBQf9J9kWRl/FxmNrAfG"
#    b"mE+YAHvgCjyAC7ADxqLZXkbAAXj2rEOcK2WL7OLCEZgDFbCI7yewFcsWqSO8yurrqNdi2SK3"
#    b"CFdZvYr6TSwLwKDnRy6xT7P6LPazWLbIlm4+lzRdWNLN50YsW2REN6P5qoGhWPYtY5qunIE7"
#    b"cKLpQt+zp5A1P4OCdlhRWhS0w4qSoqAdVpQUBe2wouQoaIcV5S9R0A4rSouCdlhRUhS0w4qS"
#    b"oqAdVpQcBe2wovwlCtphRWlR0A4rSoqCdlhRUhS0w4qSo6AdVhRjvsgL9TqhhyhVQOwAAAAA"
#    b"SUVORK5CYII="
# )

# icons8_snap_grid_32 = PyEmbeddedImage(
#    b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAABnRSTlMAAAAAAABupgeRAAAA'
#    b'CXBIWXMAABYlAAAWJQFJUiTwAAABb0lEQVRIidWVMY6CQBSGH5sNdoMHIB7AU1gZGjrEhopA'
#    b'4Q3stLO0IVbewgtQYWzmAlAJBVhSDQ1vCxIzWUZ2Z1kS+Ssmb/i/efMzjIKIMKQ+BnV/P0BZ'
#    b'llmWDQg4Ho+6rg8FoJTKLh8AAH+t3W5HCPE8rxnGcbxarQghmqbZtp0kifAtCQAimqZ5Op0Q'
#    b'MYoiQgi/UE3ThAw5gOM4vLthGI/HoyiK5XIJAOv1uheAMUYp5d0ZY00pz3MAmE6nfTsQuiNi'
#    b'URQSAAAIOfEfwnw+b7vXdS23RWEYvhre73fP83h3xphpmnIhdwDasiyrcb9er8IJvQA/uvcC'
#    b'uK7LuwdB4Pt+U0rT9Dnts322F4tFk+2rISICwH6/v91u5/NZVVXbtququlwudV3PZrPNZtP1'
#    b'q+juoN3QM/Ptdksp/VYVdCCryWTSPBwOh3b1zS6cP0jB1qWvKEp3yMLMX6pnyN3HEBHHn8H4'
#    b'QxYA/lfjz2D8gC9KdCT3eJBRHwAAAABJRU5ErkJggg==')

# icons8_snap_points_32 = PyEmbeddedImage(
#    b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAABnRSTlMAAAAAAABupgeRAAAA'
#    b'CXBIWXMAABYlAAAWJQFJUiTwAAABa0lEQVRIidVVO66CQBSdeXmhHFyAYQEsxNjQKTRUBgp2'
#    b'YAc7sDFU7MI9SGxmA1CBhVBSDQ33FZPoRJCfkPBOBTlzzzlzLzdgAEBz4mdW9eUZFEVxv99n'
#    b'NDidTuv1ei4DSunQ+AghBL3hui4hxLIs/hpF0X6/J4TIsqzrehzHjVUDDABA0zTf9wHger0S'
#    b'QsSgsiw3egwzME1TVN9ut3meZ1m22WwQQoZhfGXAGKOUiuqMMU49Hg+E0Gq1+vYGjeoAkGXZ'
#    b'NAaqqtbVq6qapkUAkCSJZVmiOmNM07TJhlzHbrfj6mEYNh74yqBT/WXQsn2fqMPhIKqfz2fb'
#    b'tjmVpunz2K9YyR8wxnXROuV53u12C4JAkiRd18uyvFwuVVUpiuI4TkPxp8hvVL0Jz5kfj0dK'
#    b'6RuLeRnGWIwp2rRQffBqUb0zfahO9E00IjvHwn6ZSzTo7uzbhMd/RS1o2cFO/P8Z9GrRohdt'
#    b'ZFl/zD6DP/5/oSKa1PBRAAAAAElFTkSuQmCC')

instruction_circle = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAAG4AAABsCAIAAAAE8RCnAAAABnRSTlMAAAAAAABupgeRAAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAAReElEQVR4nO1deVBT1xo/ZGEJCYaASUHD/oQoIgYoFRda"
    b"1LpUHlCsgKjTjhu0irbjWBCt1mFQUUapiPOs1nEEwQVE34Bin+ADl+FFEYUgaAgEA7IYFhNC"
    b"cpOQ98e14RJDSEICieX3D/cs3y/f/bjnfPfcs3xAjoBIJNI82dzcrLPsR0mFAUYMCIL4fD6P"
    b"x5PJZDgcDo/HEwiEiVZqRBiLKdva2hobG1ksVlNTE4/HGxgY4PP5YrEYADA4OIhCoRQ1MRgM"
    b"kUjE4/FEItHV1dXZ2dnLy8vBwcHMzGzi1AdgAk0JQVBtbS2TyXz58uXz58/lcrmNjY2rq6ub"
    b"m5uPj4+dnR3hL5ibm9va2sLGhR9SsVjM5/N7enqam5vLysp6e3vxeLybm5ubm5udnR2FQrG0"
    b"tBz/OzITiUTI2zM3N9cwyeVyp0+frq2sVCp98eJFWVnZ06dPBwcHaTSai4uLjY2Nv78/mUzW"
    b"QQ0IgoRCYXNzM5vNZrPZT548wWKxdDr9888/nzVrllwu14pqLDeIsbCwAAhonsRgtJN9+fJl"
    b"RUVFZWWlWCyePXv2zp0758yZA9fhcDhUKlU3NQAABAKBQqEEBgYCAFgslkAguHv3bkZGBhqN"
    b"9vPzW7x48ezZs8fhBsejgTMYjIsXL75588bHx2fLli1z585Fo9FKeugLWCzW19fX19d3YGCg"
    b"urr69u3bBw8enD59elRUFGxrw8GwpmQwGLm5uVwuNyQk5MCBAyQSCc6H/YlBYWVlNW/ePDqd"
    b"LhQKCwsLjx8/TqFQwsPDg4OD0Wi0IX7RUKZ8/Phxfn5+S0vLkiVLkpKSbGxsDPQYjgpbW9vv"
    b"vvsuPDy8sLAwKyuroKAgMjIyODgY+VagBm1t4L//BQAACwuLf/4TYEY2GAb5gEAQhCxTn5RK"
    b"pSple3p6fv/998ePHy9atGjHjh2ffPKJzlR61AqHw61duzYkJOTWrVtZWVlFRUUJCQm2trbq"
    b"qaRSaVsbhkwGixcDNhvk54PVq2VSqVS1GvodDJSXl69fvz4hIaG+vt5w44oxUnV0dCQlJUVH"
    b"R+fn549KxWDI//MfuVwub2yUl5aqY9ZbA+/r68vJyamoqIiMjPzmm2/kcrm+mPUOMpmcmppa"
    b"WFiYk5NTXV2dkJBgb2+vpn5lJejsBDwecHBQR6tRfzEqqqurd+3a1djYmJaWFhsbi3zhMlqE"
    b"h4enpaWJxeKdO3fevXtXTc3AQBATA7ZulTc3qyPUw1NZUlJy5syZlStXxsbGTsgwQ2c4Ojoe"
    b"OnTo+vXrmZmZ7e3tq1evVlO5t9eMQlHHNla3AzeTjRs3hoSEmJmZKdj04ivGh2rVqlUkEunU"
    b"qVPt7e3btm1DUkkkEkdH7KtXIDcXWFiAqCg5BEngvkvPbuf06dMxMTHPnj1TWbmjo+PAgQOX"
    b"L1/WhEpnNfRFxWazY2Ji9uzZIxQKVVJJJBL1VDr2lRAEHT58mMFgpKWl+fj4qKyTnp6enJzs"
    b"4eHR2dlpoLdiPcLV1TUlJeXt27e7d+/u7u6uqqpiMpnICjKZTD2DLqaEIOjnn3+GIOjo0aPI"
    b"AT8SHR0dDg4OGAyGTqeTyeTBwUEdfmicMW3atPT0dBQK5e+/JiHhdWoqtHTpFh6Pp6G4LqY8"
    b"ePCgUCjctWuXYiD4IbBYbG9v79DPaDa0mHDg8Xgbm088Pa+QSGEkUjgGczgj44yGshgOh6NI"
    b"SKVSDGJkpDJ54cKF2traxMRECILUyNrb21Op1L1798pkss2bN2MwGDniTVOpMtLoGqphOKqa"
    b"mj4s9v0jgsWSnj/vg29zdFlnZ2dFWiwWI0fKHyZzcnLq6upOnDjh4uLC4XDUy27cuFFDZgCA"
    b"VmoYlMrHZwqD0Q1bUyLpDgiYAhOOKqtFuysoKCgqKkpMTHRxcdFcyuSwY8cWqTSxu/sGj1dY"
    b"X/+Nu7ujhoKavqLX1tbm5OT8+OOPvr6+uippGrCzs/vzzzNVVVXt7e0EwoGjR4/6+fl5e3uP"
    b"KqjRU9nf35+RkbFq1arFixePWVXTAJ1OnzVr1sKFC8PDwzMyMvr7+0cV0Wi0k52dLZFIwsPD"
    b"kZUndogyblQREREPHz7Mzs5eu3btKLKjDgZqampCQ0OfPn1qhEOU8aGqr68PDw+vqqpSLztK"
    b"A4eb9ooVKz76LlINPD09IyMjT548qb6Zj2LKvLw8mUy2bt06vepmelizZo2lpWVeXp6aOupM"
    b"2draWlxcvGXLFmNeXjI+MDc3//7774uLi9va2kaqo87tXLlyhUqlzp07F65jQr7CEFTOzs6z"
    b"Zs3Ky8v74YcfVMuO1JW2traGhYU9efJkPDt4I6eqr6//+uuvW1tbVcqO2MCvXr3q4eFBp9NH"
    b"qvA3hKenp7e399WrV1WWqjZlW1tbeXl5dHS0IRUzSURFRZWXl6vsMVWb8urVq56ensilNpOA"
    b"MXPmTBqNpvLBVOF2BgYGOjo6YmKSq6osPv30/Qw6ME1fYQiqVatWpaenR0VFIVckqF7J9vjx"
    b"4y+++KKy0rq7G8yZg8bh0MhSxbW2C730uGZsYqn8/PxwOFxtbe2SJUuQpSoa+LNnz1xd6RAE"
    b"/PxAXd2H5X93YLHYefPmlZaWKuUrm7K/vx+FQtXXkxYsAAEBoLx8vBQ0KQQHBzOZzK6uLmSm"
    b"simrq6s/+yyopsaMyQRFRaCnBwz/wj8JAACg0WhTp069f/8+MlPZ7bBYLH//NY6OYM0amVQq"
    b"/cc/LEpLQViYTCqVmrSv0DtVQEDAvXv3Vq5cqSgd1rOKRKKmpiZ/f8ulSwEajZZKpd7eQCQC"
    b"aDQansg2XV+hd6rg4OCioqKuri7F9PWwBt7U1NTQ0DBzJnD8az7D0hIsWAAm8SGcnZ0JBAKb"
    b"zVbkDJny7du3t27dcnR0nPANMCYBFArl6ura0NAwlAP/OXv23LJlZ4uKAu7cmXL27LkJUs/E"
    b"MGPGDBaLpUhiOBxOX19fVlbn9OlJAAASaUlW1qFPP30+ZcoUQ0/emzqVtbV1XV1dU1MTCoV6"
    b"v6SgoqLC2npoI4a1dWBfX5+Pj48JrQOYECobG5sLFy6gUChnZ+f3SwpoNJpQ+D9FJaHwfzQa"
    b"DUxiNEydOtXW1raxsRFOogAA9vb28fFTW1pSeLw/W1sPx8dPVb82exIKODk5KT64vW/8mzZt"
    b"tLLK+fe/z2VmZk7aUXPgcDihUAhfD412hEKhh4cHgUDQcBG0KQ5R9E5lbm4Ob7YeNtoRiURE"
    b"ItEIxxXGTEUgEHg8Hpw/9IrO5/MnJ2m1BQ6HGxgYgK8nTTkmIPvKIVMKBAI8Hj9BKpkqkE/l"
    b"kNsRi8VyuVzzPtt0fYUeqWQyGQRBym6HSCSKRCKj7eCNk0oikRAIBGW3QyAQ+Hw+mIQ2GBgY"
    b"sLKygq+HmVIgEEyQSqYKoVCIw+Hg6yFT4vH4yadSWwiFQsVTOeR2LC0te3t7J92OVlTwG6Sy"
    b"2yGRSEKh0Gg7eOOkgiBIcSzIUAMnk8mdnZ1yIz5dwAjR3t6u+PozZEoPDw+xWKxmVesklCAQ"
    b"CNra2tzd3eHkkCmJRKK9vX1TU9MEKWZ6ePXqFQaDcXNzg5PDlhQ4OTk1NDQEBATASaPq4I2Q"
    b"6sWLFw4ODvAQUXlJATyFhswxng7eCKnYbPaMGTMUmcOWFHh4eCD3JU9CPZqampCTYMNM6erq"
    b"yuPxOjs7x10r00NnZ2dXV5erq6siZ5gpiUSip6dnZWXluCtmeqisrCSTyQr3DT48pcDd3b24"
    b"uBg+WcR4Ju+NkOrOnTuenp6vX79WlCrv22lvbw8LC+NyuRO7Q8bIqbhc7ldffdXY2IgsVV6q"
    b"SqFQvLy8KioqwCRGRkVFBXwsMTJTxVr0hQsXKq1nnYQS7t+/v+CDxZIqTBkYGNja2opcozUJ"
    b"JFgsFpfLDQoKUspXsW+HQCB4eXkVFhZu3boVWfXjGKKMnermzZs0Go1IJCqXquxZa2pqIiIi"
    b"WCzWhHfwxkb15s2byMjImpoaTbeLent702i0a9euqSz9O6OgoADeNPph0Yg7b2NiYh48eNDc"
    b"3GxAvUwNXV1dZWVlMTExKktHNKW3t7eXl1dubq7BFDM9FBYWzpgxY6Qzh9SdUhAREZGamlpf"
    b"Xw+PNE3aV4ydqr29vaSkJCkpSeWZDaq3iyqu6XS6r6/vH3/8cfjwYfiov4/gy5jOVNnZ2TQa"
    b"zc/PbyTZUU502b59O5fLvXHjhvpqHz1KS0ufP3++fft2NXVGMSWZTI6Jibl8+fKbN2/0qpsp"
    b"gcfjnT9/Pjo6WhF7RSVGP5MtNDTU3d39t99+k/9dJyMzMzOdnJwU2xlHgkZnssXFxe3atevm"
    b"zZthYWGKUpPwFWOnun37dl1d3bFjx0aV1aiTplKp69aty87ODgoKUuyONAlfMUYqHo93+fLl"
    b"devWUanUD3f1aOd2FAgNDaXT6fv27evo6NBQxNTR09Ozf//+wMDA0NBQTeprcapqfHw8hULZ"
    b"t29fT0+PruqZDMRicXp6up2dXXx8vIYiWpjSwsIiOTkZg8H8+uuvEolEJw2NC8gJBiWkpaVh"
    b"sdi9e/dqHg9Du8AH5ubme/bsSU5OTklJ2bBhg9H6CvWVUSjUu3fYGzeAlRW6txcsXw6oVCm8"
    b"FBqudu7cuZcvX/70009YLFaLUA46fIPicrmxsbH79+836Ocsg1JlZsr7+uSDg4P9/fKSkmGl"
    b"58+fj4iIYLPZ2mqly8nv06ZNS01NZTKZSUlJyNiFpgL4ebKxARAE4XDgyy/f58tksiNHjhQV"
    b"FaWkpCAnuDWEjofoOzk5JScnC4VCOOKCbiRGhZ6enqSkJCaTmZaWNnPmTB0YdI9HYGtre+TI"
    b"ESKRuHv37tbWVp15xh+wI3n3DmAwGJEIHD0K+Pz+xMREoVCYlpamw/MIwwz5cVfbGXcikSiT"
    b"yS5evPjs2bNvv/12zpw5Y6HSTVYHKgsLCwyGcuWKma0t6O0FS5cOFhdnMpnMuLg4ZFQMbbXS"
    b"T5i33Nzc0NDQU6dOvXv3boxU2sqOhWpwcJDL5Z44ceLMmTMQBI1RK/2EeYuOjqbRaFlZWU+e"
    b"PNm+fbtJHFfd2Nh47NixgYGBuLi4zz77DIw5UKfeIuZ5eXkdP3780qVLv/zyS2hoaGRkpNIQ"
    b"dWLB4/EyMs40NAx4elrFx39bVlaWn58fEBAQFxeHbMVjgT6ji+JwuE2bNvn7+588efLRo0fr"
    b"169ftGiRkcR/iorag8UewmJJDEb3pUsx8+aRt23bFhQUpMf/t/6ji9JotCNHjuTl5WVlZV25"
    b"cgWO26s4T1QrKn1p9fTpU5FoBQ5HAgBgsSR7+80bNkwJCgrS7xjMIEGtLSwsNm/eHBsbW1hY"
    b"ePr06evXr69evXrhwoU6UOlFKxaLJZFYIupg7ezs4Gp6/F5nwEjMyLi9GRkZBQUFwcHBQUFB"
    b"6j/r6xE8Hq+srOzBgwdtbW1S6aBEEoLFkiSSbkvLYjr9X3r/OYPHB4cNunz58nv37t29e/fC"
    b"hQs0Gi0oKGjBggX66u+VIBAIGAxGaWkpk8mkUCiLFi1atmyZXC7PyPhXQ8OAr6/Vjh2phvhd"
    b"Mzlixkarw6FGDailMslmsx8+fFhRUfH27dvZs2cHBgY6OTmh0WgvLy/d1ICTYrGYw+FwOJyS"
    b"kpKWlhYikTh//vz58+dTqVRtqXS+QTPk9wj4M5qGSS6Xi4w8qJUsBEEcDufRo0d1dXUtLS19"
    b"fX0uLi7w4k8XFxc8Hk8ikfB4PBz2VUmWz+dDECQQCHp7ezkcDovFev36dWtrKxqNplKpFApl"
    b"xYoVNBoNPu9QW63GcoMGcTuaJL29veEVI1Kp9MGDBxAEvXr1isFgXLt2TSwWwysYsFisjY0N"
    b"DocjEAhCoZDP5/P5fJFIpCh1cXFxdnaOiIhwd3enUqlYLFbpUdJWKyN1OxoCg8HAFlm6dCkA"
    b"QC6X83g8iUTC5/MFAgGfz+/u7pZIJLBBCQSCubm5nZ0dgUCwtraGo+wayVhg4k2pBDMzM/g0"
    b"Coe/onGPep6fkeD/A46FUNM4FbsAAAAASUVORK5CYII="
)

instruction_rectangle = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAAGQAAABKCAYAAABNRPESAAAACXBIWXMAAAoSAAAKEgF1aB9/"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAACLZJREFUeJztnW1MW9cZ"
    b"x38xFzAGG2xSsFnAGEzJ28gK7UgatkbTXrqXtJumbV0UbV+2oWra0JZvmSol/dRNm9pu+7Bo"
    b"66QuXZdpnbZoWaYoSOlIIUlDULKkeSEjUJZ2NGM4GNwBtvE+PDYYxy/XxL6AfX8SwvY9vvdw"
    b"nnuec57nnPtnHTqZxAi0AY8CHwY2Ag8Ds2pPsC479cob7MAjiBE+CBQBF4A3gD7gu0BP+LUq"
    b"dIOopwC549uAnUANMAH0hn+uAqGY7zyG9JCfqL2IbpDEmIFtSON/CCgD3kIavw/4r4pzlAAv"
    b"AXvUXlRJu5q5SwPQgfSABsAHnEEM8Dwwt4xz/g8xpGry1SAmoBVp/HbACgwi/v95YCSD13ob"
    b"cIZ/pyRfXFYNi76/CfH1V5DBtxe5k7PFHmAeOKKmcC4aRAGakcbfAawHPCw2frzBN5vUA98D"
    b"utQUzgWXZUHm/B3IIFwKDCCNvw+ZCa0kI4jLUsVaNEhk8N0Zfj2BzHr+AjyLuIfVxiwybr2f"
    b"quBqN0gp8BDS+O3h99cR9/MMcGflqpYW/cgYdjpVwdU2htQgjd8Rfm0A3kTcTz8ws3JVuy8i"
    b"f9MPUxVcSYMoiM+P+P5q4DbS+BeQICxXKAZ+A3wlVUEtXVY1Mvi2AS3haw8gjf8ycFfDumjN"
    b"LBK1pyRbBkmU9xlgdQ++2WQIaAz/TkimXFYZku/ZiQzCJmAYGXxPAeMZus5a5stINviVZIWW"
    b"a5DowbcBCLKY9zlPGvn/POIDwH7g28kKqXFZhYjP70Cmng4k79MLvID0BJ3UvAPUpioUzyAO"
    b"JIe/E1l0mWdx0eWXqAhudBLiQ9z7dKICCotLjpGs520k8v010hN0Msc5ZIXxVLJCbwKPA+Va"
    b"1CjPaQd+kKrQYaRn6GSfQuAPyQoYgLNIN9LJPn4kak84uzUg09UdWtVIhxvAg4kOGoB/ILMp"
    b"HW1I2gEMQADxbQatapTn9JLCICCZ1U2aVEfnPSTWi0vEIGeQWEQNW0ljSVInLl5ShBkO4K9I"
    b"enzJDKCoqGhLZWXlfmBdRUXFLqvVOulyuX6WtarmB98BPhHvgALUud3u7r1797rm5ua2Hzly"
    b"ZPjWrVsfQ6yI0+ncf/PmzT01NTV3vV7vFZPJdH1+fn6XdnXPSfqAzwIn7znS1NTUPTIyEorQ"
    b"3d0ddDqdC3tR3W73OaPR+K7JZHofqFIU5VNGo3GG1b8ev5pRgNfiHmltbX0rFMX8/HzI7XYv"
    b"7NZ2OBy3gZDBYAjW1dV12+32HwEhRVGmkCBHZ3kcJc7M1jA1NXV7eHgxg37ixImg3+/vjbz3"
    b"eDyVwFOKomybnJxsnJmZMVqt1qcDgcAjLG+/q45wFVlVvYfapqamawcPHvR0dXXNulyuM8h2"
    b"G4DiioqKHwM2rWqZRzwBfCPRwQJk/eN19LFBK9YDv4r9MOLDgkgE2QNs0bBS+cw48EDsh7GD"
    b"SjoBos79c5eY4SCeQdo1q47OWWLaO9Ygd9EXq7Skj5hEY7wM7ziyy1An+1whZsyOZxDdbWlH"
    b"ELFBQeSDeAa5pxvpZJUlvSSeQa6RIILUyQpLZrbxDBIK/xRqVaM8Z8kQkWjZ9iKyfVQn+3iI"
    b"ikUSGUQPELVlIWpPZJBzyOqhjjacBbZDYoOkXPPVySgLM9tkW3/+jTzToJN9FtZGkhlEDxC1"
    b"I6IsoaQyiB4gascloCWZQQYRoRYdbTgD7EhmkBCSa9E3MmjDWaA91X7eAeTp2ngUEp47u1yu"
    b"F81ms7e6unoYPX2/HMqRuC9pyspUV1fX09LSMr558+artbW1S1QINmzYcNxkMk0D66uqqv5U"
    b"XFz8RElJyQzw+ezVO2d4EPg6cAjZMfoKspuxLeE3Ghsbj/b09PhDoVAoEAiEdu/e/R5R6ZTa"
    b"2trhgoICv9Pp/BtAeXn5JxVF8aNPlWMpRBq6C3gVeb7wEPA1wKX6LO3t7SPRG+guXrwYamho"
    b"+HnkuNlsnjKZTB4gZLFYvlpeXj5eVlb2T7vdfgqVMhI5igPYDTyH3P3HgAPAx1HRLgm3/MzM"
    b"zASj309MTIQCgUBEibNkenq6zG63/8JsNlfeuXPnt8XFxbMOh+OdQCAwgCgWZFM2b7UQkRCJ"
    b"iChYWZSOPUwm1etcLtcz+/bt84yNjYUGBgZCW7duvQVUhQ9vKi0tHUUkNEqQBZZ8eODHgtzp"
    b"B4DfIXf/c0iPyMhmwqTSGjab7YtWq/Vpn89XNTY29mlEjSCfSCQdewFJwPozfUG1WidHgScz"
    b"ffFVRkS9LiIda0Me0LyA7Ogc1aISareNziGuKVPjQlVBQcF2i8WywePxHAamMnTedIiWjnWH"
    b"P4tIxx5ihdTr1BqkHxEe7k1VUA02m63f7/dbgXWNjY0PDQ0NfTMT501CrHTsA8jg+waZHnzv"
    b"E7UG6UMiyYwYpLKy8tL4+PhHZmdnSyYnJ3ch6ZlMSjqVI2IIHUjsVMaidOz3kWXTNU0JKpWZ"
    b"1WC1WjuNRuMs8GSGovsGJNA6hDwm9nskEGtjjc3+0hEwOwZ8LkPXbQaum0ymaUVRZr1e7xbk"
    b"cWE1RKvXtYffX0Pcz+vAfzJUxxUhnWdBhhDZ7JFlXsuB3ADvAoM2m+3ZiYmJvyNatsmmj9Hq"
    b"dQ4kGItIx75AjqnXpdNDnkK6/6tpXqOkoaHhWGtr6yZFUTh//vzQ0NDQZ4g/s4qVjrUD/yI3"
    b"pWPvGyeQ9vPp9fX1Lx4/ftwfyYmdPn06WF9f/1L4sB2Jcg8Af0QUSw8g0bApI7XOcf6c7hc2"
    b"btzYH4qhubl5HGn8l4FvIamX1aayvSKk+zzhDCk0A6MwA9t8Pl/RjRs3aG5uBmB0dJRgMHgJ"
    b"6Rk6MRSkLrKEiMZJvP8WU4NIBXYiUqiPA0Gv13v05MmTD5eVlZVevnyZzs7OtwcHB79EDsQC"
    b"2SBdN/Eo8FHgpyT+l0E93DsTM1ksli8Eg0HF5/O9hiTpdOKQrkGKkTTKdWTq2YcYYa3+14JV"
    b"x/8BanhVJKRKjdcAAAAASUVORK5CYII="
)

instruction_frame = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADwAAAAxCAYAAACGYsqsAAAACXBIWXMAAAcoAAAHKAGcLxde"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAA9BJREFUaIHtml9IKlkA"
    b"xj/nGpkRQw/e/tFC9meDkKU2kUFCIlq4lDQ99Q/Chy1qKeohDJaFfVpC9m3Zh95TwfVSS8Qt"
    b"ig3SaKg2xPugrawaRF7B1IFlVbKafbh0t61Gu4tT18Hf25zzHfm++cYzoEeC9xB6vd6o0Whe"
    b"KRSK6ouLi/Tp6ekfDMP87HQ6f4PIeGEwGF5Ho9Er7g4OhyPS19f3zXMbzCk0TX/Psuz13bA3"
    b"LC8vnzU1NSmf22euILRa7VckSUr4BP39/dVqtVo0LUtJkqzKJqqoqPh6YmLi1VMYyiUMw8Dt"
    b"drfcHpOmUqm/si1sb28nh4aGSOGsCcPs7Kzf7Xb/Z4xwu92/cxzHu8jj8UCpFM1XGMT29va3"
    b"JpPp7UOTLMtid3cXGo3mw5jVaoVCoUAgEHgyk7nkBcuyf4fD4TfHx8cNEonkZVlZWUkkEsHm"
    b"5iZ8Ph9GR0chkfy7p83NzaG3txderxc6ne4ZrWdnY2Mjvr+//xOvQC6XV3d1de3v7e1xyWTy"
    b"3isqFApxnZ2dXCwW41paWvjeZJ8MMzMzf97NSNy+SCQSIZlM9o6iKMhksns3xGq1YnBwEOXl"
    b"5aivr8fh4WEuinhSpB8jttlsKC0thd1uRzQaxdLSEtRqtVDeBOHRgT0eDyorK7G6ugoASKVS"
    b"UKlUSKfTKCoqEsxgriGyS97j8/kwNTX14Vomk2FsbAx+v18QY0Lx6IZpmr43ZjQac2rmKXh0"
    b"w2KhEFjsFAKLnUJgsVMILHYKgcVOIbDYKQQWO4XAYqcQOJ8wm81QKpXo7u5Ga2sr5ufns67J"
    b"68AAMDIygq2tLRwdHcFiseD6+jqj/qN+l/4U8Xg8sNvt8Hq9GBgYAEFk7jDvG06lUojH45DL"
    b"5djZ2QHDMBn1ed9wW1sbxsfHAQBVVVWw2+2gKIpXn/cNx+NxBAIBuFwuWCwWaLXajPq8brix"
    b"sRFOpxMmkwnFxcWYnJyEXq9HMpmEy+VCNBotlcvl1YlEIsT7IT09Pb8+99+c/5fLy0vObDZz"
    b"NpuNCwaDXDgc5tbX12PT09OrSqXyM9EFXlxc5FiWfXBuYWHhbV1dXUVeP9K3YRgGOp0OJPnw"
    b"2Ruj0ajy+/0/5P2mdcPJyQmam5t55wmCgEql+vLBhtPptGDGhILLcBLphpKSEvJe4GAw+Jqi"
    b"qHeCuBKQmpoaanh4+ItMmng8zr9b5xsNDQ31KysrZ3wbWiwWu6Jp+rvn9plTaJqedDgckbth"
    b"z8/PrwwGwy8ACN5DpflKR0dHF0VRU7W1tZ9LpdKiSCRydnBw8GZtbe1HANw/8RXUX0uyBW8A"
    b"AAAASUVORK5CYII="
)


icons8_expansion_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"cElEQVRoge2ZXYiVRRjHf+dkyEYf9mGbbtb6QZS0VlteFJWbGLFebNCFya5ppnSREhhhiXbV"
    b"hUJURCsGrUZFbhvWhUllH0ZJQUkabVRGQVYGaUfb3FoX3T1dPM/0zpkz8+6c3dc9LvSHl/PO"
    b"xzvz/GeeeT7mwP+oCGdUW4As8ARwDGittiAjwXqgqM9J4J7qijM82CTGLJmnEcF7gc/1/UNg"
    b"ECHTVj3R4rGYhMQcYKOWFwMrSchcmeWk+SwHU+wHdgPNwEdOWztwv9YXspx0XESfCcB9wJme"
    b"ti+BnU7dZ8CtKeN16OMiBywBaj1tR4DNyG4OG6soP7TmORbxva1aaWhImacI3Jj2ccyOjLfe"
    b"B4CnSNTiq4jvY/E1sAyYqOUGSo3C+LIvLMQQMRhEPPTtwDwy1nFk1bfo+yzgYWveIc9yJYf9"
    b"GeRMXAu8D1w4RP8cUA9M0vJ04OKIeWYBHwAXAZ3AuxXImIpHkdVahwi/T8v7KCeTA1qAV4G/"
    b"8Ov6QcR6zQ6QOKz9tiIa8KaWm7IkQgqZJqu+CJwAvgN+1vI3wE8Oqe3IToVIkCWROxDr1GzV"
    b"uWTWI4bACLzcIuharanAWuCQ1vcAqwMkAB7TvnUjJRKCTaYI9CGe2z13IfN7trYNWmO4JKIx"
    b"Es9eAN6xyj+oILFOqxd4DjlLBl3Izo4qmnTSPqAbWdG9wAVOv9CONJCo1x79PUxi5UYFORK1"
    b"WokIvxc/GRMJL7DqbBKvIOq0Vcubshb2buD6QFsLycE2Ou2SqdH6KUiYY8ozKCcBcpj7gH7C"
    b"B7sFccbRMKu4K9Deqe3LnXpDZoDErLpopZyEwRZte9DzXQ74hwryGTspusXTnkcO6An83r2G"
    b"hMQ4YCHig+ZafWaqYC6ade6QN19Bks+k3gHYJOYE+lyufb5NGwghsYtSB7hhiG/O136/pfSx"
    b"k7P/yNir8iTwkL5/oY8PlyC6+ivwltPWp+P8guxEJ0L4ZeAR4FxgGuLhbwIWUa5eS5Hcp4Ow"
    b"KZ8PXIqocBtitgFZveOk5wOxzyodc52W12h5u5bNYe3KaL7dULojrcBLukKfAi8GVmMqEn/t"
    b"R3ITG38DbyA7MxeJYntIUt/jiGoWkJ2dT3kq0a4yPKCCusgji1SHZI7zEFdQgjZE9wYRXfSh"
    b"Vic4EGi3sYEkBOlFTHoa6rTvj4H2PLLARWQxGtMGs8m45tXgoA42zdNW7whcj6yasXBnIZng"
    b"hMDcRWBbYN4OIknYA55EEigf2nXAtU697bFD1z1LCYczO7TN5yeM2Y8mYTCTJH92MVsnPIRE"
    b"sVAedpjzdzPwOjBZy+fhD2caES0oAOcE5p3BKQjnjRXaiD92MjC7t8iqc8OZWpIbyTWMMqYj"
    b"FmkQ+JNw2BGKfm0yR/W3myQmG1WsJrHne/AnRWn3WrUkJIr4Q6LMkAOupjw2snNsO8NzdThE"
    b"pJFEnczju9CoAa4YEQPFvTrJMqvOvSi40yr3IVFsMxI72UTqEIu0g8S/dCNXrKHbmQ4kFLlq"
    b"pETcW5TQbcckJCnqp3SV+51f8xSQg23OROh25pRcB4VI2KhD8omdSBRrBB9APPY2ZFd8JtZH"
    b"JnMiXREkfNik3yyJ7O+S+YQIIpXc/Zqc+zVE32NvO0wo7gsAfSgAtwHvATfEClcJESPMROBt"
    b"LX8MPF7hGCHUIM7zMi37MsggYoj8Yb3nkNUyuIbsiExBLKTvrq3oyFGGGCKbkSzP53GHSncr"
    b"wfdIqDPZ0/Y78v/JqOIuJIFaoWXbj+SB55G75NAty7BQ6RmJQY+O+yylep4HXkAIHUEc52kP"
    b"Ozk7gOyI+Uuh4nyi2liA3H3Z3vwo/j94TnvYZMYsCYOFyC3KddUWZEzgX8c29Ub7B663AAAA"
    b"AElFTkSuQmCC"
)

icons8_timer_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"t0lEQVRoge2ZSWgUQRSGP8eoKG5R4xK3oAmCCwqK4nbQg0FBAkH0YED0JIpXNXeXg6gRE0+5"
    b"iholihJEEBE9CerB5RARjGsWiWISjZiQ8fCmyOue7pmumk7mMj80FF1v+6eqq957AwUUUEAB"
    b"MaAJSAL/gB/AG+AWUAtsABL5C80OhkjY8xk4A8zPV4BRkY2Ief4CDcCM/ISZHZrIN+A1MEA4"
    b"oe/A3rxEmgWaSFPq3URgI1AHdBNMqB4oGu1gMyGIiMYE4ADwlXQydxHSsSIB7AOqgDEWetmI"
    b"GEwFLgGDpJOJdWUuKOOHLfSiEjGoAv7gJXPZKtIMqASGlOGLFrqNSq8xos5m0r+dPRY+AzEL"
    b"OW2MwV5giYX+GqAt9ay20NuG93TrAoot9NNwBe8vc9A3/xa4CpTk4iQEx4lpiy1GUgtj6E6A"
    b"zFWGz/8aV0chGAM8Vv7/AqUuhs4qI0PAqgCZEoSEkWsBFrk4C8EWvKty2tZAAu/Zfi+D7H6f"
    b"sx7gKPElhPeV7Y+2djf5gtuVRb7FJ58EngIVViEHY7fP7nob5Vq8e3NSFvmFyEr4yfwGjmF3"
    b"ifoxHjktjc0TNsrNSvFhRJ0jpBMxzyMcP9QUHihbN20UXyvF8xF1EsATwsl0IMWUC84pO6/C"
    b"nAdBFzpdEZ0NAYeQ7RSEOcB13BLBD2o8L0ggjMhkNe6wcPgeOJlhvgxYa2HPoEeNpwQJhBFJ"
    b"qvGgpdMG5JsIQzLDnLNOGJE+NQ78BbI4rQE6A+bagJeW9gCmqXFvkEAYkXY1LnNw3I6k5G3q"
    b"XRtS0/Q72NMxtAcJhBUtrcCK1Hilg2OAZ8Byhr+JF7iR8MfQaqOoL8Rf5Ld+Hof3srW6EDfg"
    b"vQN2xB2dBXb6Yllno5xAmmdG+Vrc0VnghorDOmkE6QAaAwPA0jiji4gKvA2JUy5GFiAJo1OO"
    b"ExNuK//OhRXI5ab3Z1Uc0UVEtc/3pVyMzcRbAXZj13xwRTnwU/ntJMfmA0gvVv8y75AEcKQw"
    b"F8nZtM/quIzXk05mJFamnHQSdXE6KELal9pBN/F+M9V4t5Pp3IyN0QcgdYSfTBL5ByqXo7kC"
    b"7+mkScTexDYoQhplfqeDSNFUSbR0pgi5sW+Q3rg2J5TVSrg2BfYgR/PsgLlepIPyFsl4f6Xe"
    b"T0Oy2JXAVrzFm0EnUvs3O8blhGJkdfSl6fr0I6swfTQJ+FGKdAA/YU/gI5J2BNbhNsil3+RH"
    b"AslMtyM1yDKkiWG2UB/wBTm6nyPl8AukaVFAAQUUEA3/AQrUfmUtuKGSAAAAAElFTkSuQmCC"
)

icons8_timer_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"NElEQVQ4jd3TuUpDQRgF4C9Bg+BraGOigqWFhW+hIi5v4EMIaVwweQofwEYrawsxbo2FWNq4"
    b"N2piMSPcJDNEO/HAwMy/nHvuv/BfsI8XnGMXtVxg+RektzjBIk7RQGVQ0gjmMwr3472CDbzh"
    b"aBBpE/co9dh3sdNjmxXKsJcjq6GNhfg+yKgtYh0fqKacDVwU1M3H4CZGM4RlXGM75bzEZo+t"
    b"iQ5uMJchraOVcrxgpcc2Gsk6+MR0Im8NT0XJ32jrH6PXmNCO706CsKuBQ4X7HcYSCceYiWRn"
    b"Cf+4MKN92NHdlJ+gjCtspZxVoasLKWcGyzFnIhfQwAMmf0A2hUdh6LOoCOv0gCXp3y9FZY84"
    b"xPCgL1eEdfoQZrOO1XjqQs3eo7KBZEVUhQ1o4TmeltCAbM3+Pr4AHQRErwawCkIAAAAASUVO"
    b"RK5CYII="
)

icons8_vga_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"yUlEQVQ4je3SPU5CURDF8d+TaNyMGG1dDZYGG2qN1BhrE1fhIuyAwqAU2OEm/Ag8C+clI8FH"
    b"oKLgn5zcmznJuTOTy46to4hzDxc4Q2PNjBmecI95VbxEiWmoRB8foX6NX4baVWdwEudDCFp4"
    b"wQjnNX7FaW67m17aVDe5w9cUPsV13B9DcIX3Gn+cA8cpsLCcYoWfM+zjc80Rs75wkDv8xluM"
    b"Uo1zhCEGaEZtmQ+TCP3Drc2/TW9xL3CIDo79v6dFSjzjzu/KdmwjPz1gX51NjwzGAAAAAElF"
    b"TkSuQmCC"
)

icons8_input_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"20lEQVQ4jdXRvU0DQRAF4E8WGdJFUAmJzxJluASIfW3gCkCuwBWQkhBQAkSkICGRG0wy4s7n"
    b"Xd/aCCGetNH7mbcz/Cc8YZbh5rjKcLPwJolPNAluGa+PJjy5It+Ci4LAyx0FNjDHS0Hga2g3"
    b"MEoEPuB0aCpOQjsY+CP8amCFhXbJS+mFN9p9NuGpcgPO8IY17jvC7lGOcRead4yHWte47U3t"
    b"X7kKTT0UtqtxcaPS0L3DHjHJcLX8987xnCLWmO7TIDANLzjqEB8O2884vFu4wUp7gNK3wvUB"
    b"Rf4IXzjbQCQgdD/qAAAAAElFTkSuQmCC"
)


icons8_diagonal_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"90lEQVQ4jdXUr0pEQRiG8Z/4B9wii3obglXWZBItIhhEi02jImxc9BIMYrAZxPUStAsKYjUI"
    b"2r0DYQ3nC8M6Z2EOBn3bPDDPfO934PDXM55hW1hHG68J38UqpvEWbAIHmMJH7oFjDPCC+YSf"
    b"Bn/ATCK7Dn6Uk203lN3E+Ud6IZtL2ElcelKtgGpNV8H7mMzJYHNI1niyXEpkLayMkpXUbOFO"
    b"ta5fmew++H5OttdQdoaxnLA3ouZtpuYAF3UyWKuZrF862XBKZbPYqJOV1mzjUc1XbjLZc/Cd"
    b"nPCwoaybStKldrCIc3wFW8YSPnEZAqrf2ALeo9U/yjfm22E9jSsxrQAAAABJRU5ErkJggg=="
)

laser_cut_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAALKAAACygH/GNH1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABKtJREFUaIHd2muIVVUU"
    b"wPHfjM6kmY5OYllJakSJmaWmmRVGUvQurOhTZJh9slAq/RAVFERfLEEoiCwKKkEqKqKHkRBF"
    b"WFBRVNCbssyw1CzzMdqHdQ5z5859nHPmnrH6w+Fyzl57n7X22Xvttde+5GM9luWsU5S1eDar"
    b"8NCcjc/BnznrFGUyOrIKt+ds/ACG5KxTlHb05BHOQ0+BOkVpFx2XWTgPg/1FSjNkML/IEP+j"
    b"L5J5juT1Wj04CXdgOw4mvwewo+r3C+yu0cYsjMVI0SmjEqW70IbRidxEbMupX2ZW4gf8hr3C"
    b"kHrXwzXqj65Tb0dy9WAzPsIHuLwsQyq5OFHiTozB0cL3T8FM0cO16EJ3Uicd2u14Fz/r/SKD"
    b"yjP4GycPsJ2lolOuHrBGBRmLrdgoxncRxuN3vNIinQpzg+jNGwvWf06EPZNapdBAeF14r2Ny"
    b"1kvn2fKWa1SQidiFdTnqjMC3+FiO4HAwuF307hUZ5R8U7vbM0jQqyBDh+zdr7kKnYx8eKlup"
    b"okwXC96aBjKpwT+pv9b8K3hADJmz65QvE0PwykHTqCDD8aWItYZVlU3AH8Ll/ieYLwLHu6ue"
    b"v4CdOG6wFRoIj2MPpib3C8WQuuWQaVSQbmwRsVgP9mOTkvYzZW6SdmOD2HdsE6mkpWLhbMYw"
    b"YXipLMRXosfLYBr+EvOsVCaLIO+JEtpO9yXf4YgS2u/HcjFxL8wgOw5fiw1XM27L0W5LaMc7"
    b"oudGNpGdJpRb0ERukpg/aweqXF6mCI+0uoncdGHI+Q1k2vCG2OqWNfcaco/G4QicJgw5r4HM"
    b"kkRmYcs0y0knPlE7HEmZIZScX6d8vMjKvNhq5fIyW/j8e+uUzxSGnFun/Hmxuzy29arlZ5XY"
    b"X5xeo2yWMOScGmXXJWWLylMtH4eLRfJD/bets4Wy1fPoSBHCvKl4BiY3zVwsMZkPiC1vJXOE"
    b"IWdVPX9KLKwnNGm3A8dneH9Txohd38si79uIx0R4cWLFs7nCkLkVzy5Knt3apL1LhSPZrkVf"
    b"bZEYBnvFPntMHbku/Khvwi6dIzOS+xH4Bu+pH7ROxWtJvU36dsKAGSHWjd0iml0h3G81lyUK"
    b"3Jzct4lhlRq2Rt99SiXdYoHdJ5IYS5QYoU/Ak3qPDi6pIbNepEGrz1/GiQX0rqrnHULpX4WR"
    b"q8Vxw6AwX3ipgyK8OKWirBtXNahX2csL8GnSzksGkDrtEGO+2VUrV9WOxXrnT/U2dp7IJO7D"
    b"Z/rHW48mBryvdpjTKRbU6mue6ID0mgrfa3xgU3nV22+Pwn165wUcJRIN+5O6+8X8qnSlN+F6"
    b"9Y8AH8mo19Y2kUhulNVIj9JWCU+yuIFsJdeqnQteLNx0Fl4VRxcrxVett03+Zajs5xL3i4mY"
    b"lS05n9dij1B+QzPBPKe6h8lnyNtiEaU3kbBR9HJW9ibvbUqeU928hqSZ+Wtwqpjs6+Q4ck7e"
    b"d8gNIebWOvnOTSrJbEiZQ6sV7FE7euhHni/SIXz9iuS+Ot4arW9g1yU6argYWjvxeUX5LuGJ"
    b"apH+EeEM9XeefchqSBveEq76ApFRT+lJlExJ//2Q0inWmU6RE6umQ+Mc1tNZFPwH6RsguE5X"
    b"XQUAAAAASUVORK5CYII="
)

laser_engrave_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAALKAAACygH/GNH1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAA0RJREFUaIHt2UmIHGUU"
    b"wPHf9IwzLmRmnIzBuGA0ByMiEWISBdeDiCIqqPdgjjEJERRFQfCkF/UgBBEUBHFFclJwAVFQ"
    b"3HBFoyIeQozbqEmUUWMnHl41PRZTM/1VV/W00n8oiqp67/vet73ve69I4znsSNQpy6N4qlPh"
    b"kcTCN+L3RJ2ynIGjOhVuJBZ+GMOJOmVpoJkinEKzhE5ZGqLjOhZOodcjUltDejkiw/5HI9Lx"
    b"Gkn1Wk2cidvwK45k98PYn7vvxuw8ZZyHaSwTnTKeGT2BIUxmcqswk2hfx9yOPfgZf4mGFF07"
    b"59GfLNDbn11N7MWHeA/X1NWQuVyVGXEXjseJwvefhXWih+djAlOZTmtqN/Am9mmPSE95En9g"
    b"TZflbBWdckPXFpVkGj/gNTG/y7ASv+CFimwqzSbRmzeV1H9eHHtOr8qgbnhJeK+TEvVa6+yW"
    b"yi0qySr8hqcTdI7DN/hIwuGwF9wqevfaDuUfEO72/NosKsmw8P17Le5C1+IQHqzbqLKsFRve"
    b"QwvItBr8reK9pi+4T0yZCwu+7xBT8LqeWVSSY/CVOGsdnft2Kg4Kl/uf4FJxcLw7934XDuCU"
    b"XhvUDY/hT5ydPV8vptS2JbOoJFP4TpzFmvgb76gpnqkzSJrFKyLumBGppK1i4xyw1KxeagOq"
    b"4ssFvo1VUUFVGZHleFfx4a9oLR4rdvmuo8KqGjIjFvYdiXr34AkRAvQNY/hAe9+Yy9fzvFuP"
    b"9/XZEb7FBSKJkJ9K+YaMiKm4rqqKq84aviVSOTcvIncnXhYj0reM43P/drlzR2QNPhaHy77n"
    b"SryqnVlpNaSB13FR1RV2O7W2ixB3Re79iyLZtil7fju7b8MneCMnPypC5C1d2lOaE0Qe+FM8"
    b"g8u1O2daTLHWwh/N5Maz5wYuxsNixB7Bhp5YvQBDuEzsCZ+J/WRYBFbrcT8uEa52FPfiCzwr"
    b"IsVKdveqWY7Nwugp/CTikBmclr2/UZ/H63lOFpn7I9n9nLoqqvunzUExEivFb4ZddVVUNvG8"
    b"GCMioFqMCcWec0wcKouY1LZ/3xAex9U5oWXS/2YtJT8O4Qqc20UhsyIu75RDFg53Dyj+d1ik"
    b"+31C/QMGDBgwoDr+AWj/qA3v5WpJAAAAAElFTkSuQmCC"
)

icons8_small_beam_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"O0lEQVQ4jb3UzSuEURQG8B8mX1OTJqTUJE1s7EwpSdn4lyxY+q8oH8VCiLJRFpqkECUsEGNx"
    b"72R6vWPuhqduve/5eM655zxd0jCA/sTYJGxiIyWwkEg4llq5OzXwrwm7MIuZVMJlzMXEPLJ5"
    b"TKEvlfARk6jl+GqooI7jrLPdUg7wiUaOr4ELHLbxd0QJd/GUOgUX0INF9GZ857jEGoajbRUr"
    b"mMB0Jv4Nu80ZZlsfQvWXRqoxphWNZocf2M44lzCCItZbCq5HWxm32MpWypMFjAtjuMceXqK9"
    b"iIVIuIPrFMKmzirx/wMP8bsszJwgm32ZcfX4iZqgwTpOhJdmFIPCNY8E/VaErV91IiwLwj7A"
    b"k7DpCl6FF+cpkpSivRs3zeQ8YZ/l2LJoCNd99j2OtoR5eG9DepqY/wPFeP4fX8KRO0UnWEma"
    b"AAAAAElFTkSuQmCC"
)

icons8_image_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"KklEQVQ4jdXUPS8EURTG8d8KCdsJuxHbrGwh2S1UElFRSUjotQqNSqNWKhGN2gcQQU/DVxAS"
    b"LwmFCI23QkIxs8k1uXbXVjzNZM45z39O7txz+OvKZd5LmEFvi/4nHOA2BpzELu5x1SJwCAXM"
    b"4iibvMB6pOtGymEDZ9lEEZ+o/gJWVzX1FqEjDebT52sbwLonHwJj6mwDHgWO4xLPWGkHCmXJ"
    b"OSzhDdtYwDtWM7X9qES85RjwA8tBfDoDncdLWruDnp+Aw2lwMdJ9HXoYfHAM1zjFaKMOvwUD"
    b"zaX5/SA2gBPctQOEKcn5rgWxbuyl3lpY3OrFjkFrqbeQLT6XjFGz0QuhOWwKRi80T0iWw4Pk"
    b"HjZSH0bwiC7JcjjOAmFQsr4qmquEG2xJfsw/0ReGG0QBJgJxVAAAAABJRU5ErkJggg=="
)

icons8_stop_gesture_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"N0lEQVQ4jcXTzytEYRTG8c/4FTJZoSwUGxspGytlYWdvz0LJSrJhJayVhfJHKGLFwoKVslSU"
    b"IiJDQolSDIt7J9cwM3emkafeuu957/me855zXv5BPVjHIqpLhTRiDUe4wyYucYgTjBYLnMEp"
    b"FvCBLixHbG/oQ0u2Y0UOYCsOsBTuP8KVsVViD2fojwOMo0FsYaRcwAtcob4QsBaJUqNkA6fx"
    b"hPFyAOswh0nshrYX3OIRN0gJmgPp34BVke+GcL+DTjTj2ddozEf+HRLMY15gMVrNdRAFZq6S"
    b"wAaSpUSKAu/xiiZsx/SvkVXLaFPSOEZvEQl1C+Yxp8ZwjbYYsAG8F0qgUlC/FCbQ4eeQJzEs"
    b"KNFKjMCqMIVzQaPSoXNmvQvmczZM4JvyPbFEmGF7mFWmgQ/YF7yov9cn1P5B23nSvF4AAAAA"
    b"SUVORK5CYII="
)

icons8_return_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"8ElEQVQ4jdXUPUpDQRSG4SdyEcGAiEXAJoWdO0ghWNoIWllJGgu7LCCFdZp0QgKCiL1iFhCx"
    b"cBcWigTBPyyNaGIxEW4R9V6dQt9qmDnn5YM5M/xHFrAWS7aMexzHkG2hjzaSn0oKmEATNTyg"
    b"m6HvFmc4wUv6IMEAl3jDcLQefCGbQhl7aGAT5+MKV/CEI0xnSDmDFp6x9FnRIi5wmkH4wS6u"
    b"hORjmUMlh7AoTEY1R8+3HOKAcMMxuEYpprAkjFwUJtHDdizhDu6EMfoVCep4xXp608ieJ/I8"
    b"VjGLDanPpJAq6GSUDXEjvOV9POYI8gd4B8NqKf/2uJJfAAAAAElFTkSuQmCC"
)

icons8_home_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"cElEQVQ4jdXUvUodURQF4O9qGvUWEpEENKBYGQiBgBKjXUrzAqJPIIrY21v7CEljFRGE1Aop"
    b"JCGSgLYGwQSCEP+9jX/F2RfGuaPo1cYFw8zZZ+21zz57MTwwGm/BKeE9XmITF/cp+AZfUcEB"
    b"fmKoHqGnmMMpltCNtoidRezFbYQaMYn/WJdazeMd1rCPaTy5TqyMZexi6iZiFB6PwiuRW4NZ"
    b"bKPn5iauoCdyZos2v2PmDmJVzEQuaMhsPMdWHYLbaC8SbMZJHYLHkYurF3+q1ugl9KMvvn9g"
    b"FecZTkN2nT3hnuS/LBYkY49hVJroYo7TJjmjRvAvOnPkV5jA23gm0JvjdOJPkeBGCFRRQod0"
    b"6dmiHQVFN4oEVzGIllhfhOhRhnOUyyljAN+KBD/jEJ/QFLEdyU5VPIuY4HyUfhoLVUJ2yhV8"
    b"wBf8lsxaxgi6gjMQsSVp+hUMx5toKY+WEOnH6zhVa+zt4R9+RZvzkg8fES4Bd6xJfI6CFB4A"
    b"AAAASUVORK5CYII="
)

icons8_bell_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"KUlEQVQ4ja3SvS5EQRQA4E8kCg9Asp1sRLb0k/jrJYRIKIQn8LuFxiNIqLyBqBQK22lEFLZV"
    b"iDdALxHE3ypmbnKzcZndONWdOSffzJx7+OfobKG2hAn04QOP7R46jAt84RlPaOAKq7jFXiq2"
    b"hFccYzC3X8YBPiN+k4Kt4B3bv9QsRnTzL2w5YtWEgw9w/VtBtQUM+oVnl5sT86jH5GkilsUT"
    b"pvMbkxE6xDresJOIdeAFU/nNXjyghi4stICOCCNVak4MtIme4Lwo2Sq6LczpUBE4KzT4MwHN"
    b"pmGpCOvAPXZRid9F6FbEVoow6BaaOxbXlYKb1lKwLOo4wzj2hefne7ohjNdaCkaY9nq86R1m"
    b"hB+VPf8Il6lYPrqb1hnawFw74E/Rg9H/wpLjGzFeVCqYlPuEAAAAAElFTkSuQmCC"
)

icons8_output_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"PUlEQVQ4ja3SOUpDURTG8d9zaATBJgtwaMQhQgoHsNPCDQhuIBsQrHQDWYGN0c4NCA5LULEV"
    b"RCsLbdQuTSSx8IS8PK4Dxg8O3HuG/zl34HcaCPsXDeAIxxjsF5ZhH+2wQ31MmqEeoFZYO3zZ"
    b"X4ATOcBNWKfB+F+nnIxprsOy8H2poR+AD4V9O+HrUfGC51D+oUleZcx+FVxDA6eJ2B52E/6z"
    b"qFkrBtYj0EINmyh9M1kpcmpR0wgGGMad7l/r2CuWE7CViBXz74IFpvAY3XawgWdcJoBXeIqc"
    b"nah5DEaPOtDz2NfRTACbOIj1RRGW/zb3mNd9+ab0txrCe6y3YsK3FFA+oHs3ReX9L4m4UZxg"
    b"puBfwnYifxuLBd+Cz+OPQSU6VlPdfqlqMCr5I6/2Aeyp7Uz4H1bJMILpPqbL6/YDkzdghLDo"
    b"+mMAAAAASUVORK5CYII="
)

icons8_close_window_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"3ElEQVQ4jb3UQU4CMQAF0KdxA3sdbkCMGy/BIWThci7hbUzAeAXOoUFvAB5Alrpo0QJ1Jm0m"
    b"/qRJ+2f6+/ubfAbGWTKfYIZRocYOK2xTcoIPfFWOLRo4j4IzXBY6S3EVNX4ES6+ZwzgVHAxd"
    b"gg9YZ/h1/FYseI85XhPuPXLzjn2glX+9N9zi5Wie+7eFi56DpljiLq6fcN214V8fhd/MFnh2"
    b"mumfyGWYy6wrx7bP4aOQ303C7TNd1jgsHb0Oq7AX3A2g9ZkuGqGCaq+7ERrnoGAboYLGFc5W"
    b"Qp8Oj2+JXWSupLCkIQAAAABJRU5ErkJggg=="
)


icons8_next_page_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"HElEQVQ4jcXUMU5CQRDG8R92UgoeQKDEO1iLKOrVtFQ8gYqFEsMJRHuDxxCJVFjsEsnLewto"
    b"jF+yzZeZf2ZmZ5d/UjWeX+kQPUwwi2cSvfa61QzwiQt00IynE70pHlepehtveMJOIq6GIUao"
    b"pICDCCsveJso5cSW8Yx+EawttJmtrI/zAmhdaL+VB7wT5pPVHj4S0C5us2YpJh3l1p6GHmOc"
    b"9avCWjQLgIvQs0zybsytwEY0ZwnQjzRvubOkuryWT/Ce4+vhck0YXOEmr4oDYQVqGT+1No2Y"
    b"s58HJDynodUX+wX3RTDCbY+EF1BPxDVizCu2UkDC9feFVrrC0Oefw6kwsykeVoEtqiUMe+z7"
    b"+xrjWmJmq6piya/yZ/oCgl5ESq9WShMAAAAASUVORK5CYII="
)

cap_butt_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABwAAAAPCAYAAAD3T6+hAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAAZdEVYdFNvZnR3YXJlAHd3dy5pbmtz"
    b"Y2FwZS5vcmeb7jwaAAAAfklEQVQ4T+2TMQ5AERBE59MpVe5/A5XEGSSuwAWUOtnPRqlE5SUj"
    b"bCSTXQbUcc4RgCsSfbnKM9wOG0opoZTiwmlEzhlaa1hrYYyZ5XN8MUZqrfGhlIJaK++PkVKi"
    b"EAJ576l3uMzOVo3gD7P+husLm8WfZoz0+CgnL/jbuWwI/AHZfOz8osNGAAAAAElFTkSuQmCC"
)

cap_round_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAACEAAAAPCAYAAABqQqYpAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAAZdEVYdFNvZnR3YXJlAHd3dy5pbmtz"
    b"Y2FwZS5vcmeb7jwaAAAAzElEQVRIS81VywmEMBCdKGoDindvnkwbYoXmKiL2YgNJAxYh8tZZ"
    b"XHbB2ZtRHzzI5A1kmF8IP1iWBV3Xoa5rZFkGpRSIyD/392GtRVVVspNvcgDOOaRpKjtcQS6B"
    b"1loWr2Lf97JwJZumEYU4jlEUBcIwFPVTmef54TJJEozjiGmaYIxBEAQHnzOpoiji0dzOX5Rl"
    b"Sduo7hbRPM+0rutueYCUCS7FMAzvTLRt6z0Tf3uCM8Q94T0A5iOm4xF74hEbk4Ng3P53fHDP"
    b"L0p4AczxLpvGSdCBAAAAAElFTkSuQmCC"
)

cap_square_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAACEAAAAPCAYAAABqQqYpAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAAZdEVYdFNvZnR3YXJlAHd3dy5pbmtz"
    b"Y2FwZS5vcmeb7jwaAAAAh0lEQVRIS+2UOw6AIBBERwhwDzqODC0F4S7cg1OQFRULI6WoBS+Z"
    b"kN1QTPa3AKCqT2Ht/ZRp4uTfJqSU0FqDc94yY9m24yKlFMUYKaVEzjlijN3+PKnuihpj4L1v"
    b"EZBzRimlRWO4OautoBDCXglr7fBKVHWTJISgOhNvGOi3423mnTiZJg6AFWbye0A3zNrCAAAA"
    b"AElFTkSuQmCC"
)

fill_nonzero = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAATCAYAAACQjC21AAAACXBIWXMAAAMpAAADKQG9Lnl1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAQ5JREFUOI2t07FKA0EU"
    b"RuHPkAQUEdTSSrCIoHZ2KvgCgiiYwkILIfggljY2voB2PoKItvZaK8QqChIVRDAWO8IaspOJ"
    b"5MAtZuafM7uzd0ljOVRfyonCTXRwOyzhamIuiXm84wML/cKlBOEOxjCK7WEI86+7kpCPMou2"
    b"7IN08Ia52IYRHGIL3z3WZ2R3mOcezR7ZEi5+B/t4zD3JoNVEo/uEGq7/IbvBYtEVlHGE1wRR"
    b"G6eoFMnybKAVkbVCJpkpPEeEL5jutbGoD3eDtIhJ1AcRrnWN70LlWY8c+IdxWRt08IUzTMh+"
    b"vxN8hrWnMN+XhkhvYQ8PIXOQIjzHFZYimRouQzZKFcfSeqsSstX85A/ci1xqR7HjbwAAAABJ"
    b"RU5ErkJggg=="
)

fill_evenodd = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAATCAYAAACQjC21AAAACXBIWXMAAAMpAAADKQG9Lnl1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAASdJREFUOI2t088qRGEY"
    b"x/EPmQlhwRUoi1FYsdHMLShRtizURLkMC8rGhtWsWGhcgkQkyUVQFDv5EyljMe9wTMeZV/nV"
    b"szi/5/v+es95nkOcJkK1VEdk4DRquPivwFIkF6VhPOMFI63g9ojAOXSjC7P/EZh83WIEn6lB"
    b"PKoPpIYnDGUdaMMSZvCR0n/FSZNXRGcK2479xsMCrhM3adRaysH1FO4G5WawgKME9C59XUqh"
    b"1+COMZrCob6Xq3jA5W9Q6D1iC7kM7ktTqGT0K4GJVj/usIfehN+Fbdxj4C+BK76/0TkmMY6z"
    b"hL/8l8Cqn1M8DZX0qrFhPepr0Jj0DvrUf79NvIXebfBbqixjtzCPq8AsxgTu4hBjGUwBB4HN"
    b"VB4b4nYrF9h80vwExRFNC/by8doAAAAASUVORK5CYII="
)

join_miter = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAIAAABLixI0AAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAACL0lEQVQ4jZ3SMWgaURzH8a+aE2tEUZAuBWkIuik4VCmF"
    b"gENKIZ0KDhbMVDN0KAmFop3sGnRwKEiHQkgyGLqUQoeQIUuwUCuUGkICtk6lDjVWmju1eh1s"
    b"Lnrxqpcft9zx/314791D7vf1PttbW5zHC7/gKZgAWWeq1arD4RhAZvgI78F4BavT6YTDYWVR"
    b"GfgO14ErWMlkUoHuwR+4e/6qzyoWi4IgDJouqEGei+iwTk9P5+bmBjUDvIEvYB2yZs3maa1Y"
    b"LKbUVkAEPyN5mclMZeXzF7sJgAiPRiG73X4nHJ5sVSoVq/XfbmbhEApgQJ3J5yWKYiAQUAqv"
    b"4Bs4L0FTWYlEQpl+CG0IjYMmWzs7O8roPDThmQZ0A1b+Y9VqNZfLNRgV4APsgnGob4Rb8AI+"
    b"QQ9qWla/319aWlJqz6EBN8/dBViHQ+jDIazDAlzTsnK5nALdhg48hhhsw0+QYBeewPzE8yqX"
    b"yxaLZTBhg6/Qgw78gNfwABwaZz+j+tRqtaLRqCRJg9ff8Bbq8A4+g6xx9j6f7/7ionpdy8vL"
    b"GvPqmM3mSCSSzWaPj49lWZbPzkaszc3NiYTb7Y7H44VCodFojKxi2Do6OrLZbGP7JpMpFAql"
    b"0+lSqdTr9cZfIsWSJCkYDKoIp9MZjUY3Njbq9fr4/lhrdXVVIbxe79ra2t7eXrvdnkyorP39"
    b"fUEQ/H5/KpU6ODjodrs6iCFrBmg2mycnJx6PZ8o/qBWDLGtdGp0Rxb+5WqWcYv6HwAAAAABJ"
    b"RU5ErkJggg=="
)


join_bevel = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAIAAABLixI0AAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAAB0UlEQVQ4jc3TMWsTcRjH8e9dkxvSTImC24lQ2sFGhcIt"
    b"IZopQ4YGg7h1Kg4e6isQgmQIeQMam1cggRKXgGPokuDY6wvokamSEiqn0v/d3+HsvylNcrlM"
    b"/raD5/lw/J47ZMwIIfL5PFd5Bx48hDUgrlWr1RT0GH7Ba2AFq9/vJxKJEFqHEzgEbQVrPB6b"
    b"pqle6jO4cOfqMYYVBEG1WlXQS7iEp1wnhtVqtdTafTiHD9zI1sbGUpbjOKlUKtxJwBEcQXIK"
    b"Mgzj+2AQbXmel8vl1FodxmDefCnLsnbL5WjLtm218wwu4QUzEt1Xt9vVtPDoZOEUDmZB0Zbr"
    b"utlsNhzVoAvHkFrBEkIUi0U1aoMHj+ZAOlgLrHq9rka3wYM3t4h12IUDGIFcYJVKJbXgTP0r"
    b"wAN4C9/gN/yEr/AqvGxkWZ/AhXuQhwYcQwCn8BHKU/VFdN/pdJ5DACdwBj4M4D08AT3uHaWU"
    b"P/b3z+EL7MHdOcUDuq5bOzsR1p+Li+3NzXlEOp2uVCrtdns0Gkkhor/74XBoGMY0YZqmbdu9"
    b"Xs/zvOu5ZSwpZaPRSCaThUKh2Ww6jjN7SAhNSjm/h3/xfX8ymWQymcVDS1lLxfdvH3f1/K/W"
    b"X6GtRkLtoYR+AAAAAElFTkSuQmCC"
)


join_round = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAIAAABLixI0AAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAACBUlEQVQ4jb3SP4iScQDG8a/vnffaayloKEQ4ZDQJ4iGI"
    b"29EfqFGnhqQtBG1saUi4IohuaGhwcSiCNqVQ2hpEL9ShQYe6ITDRFukuSSR4/zTI/S659+29"
    b"t6GHd3lffs8H3ud9MZzn4fb2Giyvc/ANXoAbcAo1m0232w0AEryDT3Aa1pxa0+k0EolwmHuw"
    b"gATg1NJ1PZPJCCgFv+Du4a0zq1wuC+gMfIYGSP9g9ft9RVGE9RLGEOIoJ7Xm83ksFhO126DC"
    b"FVayGY+fyCoUCqJzEX7Ak1XI6/V2dnftrWq16nK5lh0ZuvABNlYtv9+vyLKNNRwOg8Gg6OzA"
    b"PlzAJDZ7LRaLRCIhTt8EFW6YQfZWsVgUR6NwAE8tIBurVquJmTagA51jMy3jgk14YGWNx+NQ"
    b"6OjveQwzuLRKnILr8By+gAFfraxcLic6V0EFcX8e7sAb+AkqtOE+xGHd1JrNZrIsL5thmMAr"
    b"SMMj+Ag6fIfXcAvO2u41GAzEEG/BgH0wYA+ewTXwWGy/fvxpIBCQJEnXdQMO4D00oAF7YJgp"
    b"gKIol7e2zPdKp9MWrZVEIpF8Pl+v1+fzuWEY5la73fZ4TF8FSZKSyWSpVOp2u6qq/tmy/L9a"
    b"rVY0GhWEz+fLZrOVSmUymVhVXIZhNQKapvV6vdFoFA6HU6mU+LhW+ZvlNJL9kf9saZoG/Aa3"
    b"/yM6a1FRBwAAAABJRU5ErkJggg=="
)

icons8_menu_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"zklEQVRoge3YvQ3CMBCG4RdEyRLAAgRahoFBkJCggxUyDTVMkGQLOqSkgMJY+XGExDnoe6Qr"
    b"bLn4fI1PBhEREZHojGr21sD810F6KoBb24EdUA6ktm7wsXeRTVA/4tCaNQEy7LvdVRmw/KoN"
    b"IiIiDn/WmgJ7YGaQpY8COAKPpgMX7F/t0Dq7wf1ZqwxtSWwm3voAPIGFQZY+cuBkHUJERP5X"
    b"wuuxsR4/uip/Z22URhAytFI3uD9rXdtuGZmPrHVfpiuGMWvdrUOIiIiIdKgAK0vhhB7uSF4A"
    b"AAAASUVORK5CYII="
)

icons8_reference = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAIAAACRXR/mAAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAADI0lEQVRYhe2Zv08iQRSA35qLQCLNhcqYmBAIgWZXQ2F2"
    b"/QdAIVdZ2FxosITmOsvrroHS7WwsLhQUnvwD7la7EQrYGGhIdmzoFgjGAq4YRG528JadJWDi"
    b"V20mL2++zI83zMBNJhPYPLbWLUDnU2sZPohWLpf7auPo6Kjf77N3ZlkWz/P2/Llcjgyd/Eso"
    b"FKJmrNfrE2bq9To1eSgUIiLpkzgajWYRkiQxDBAFSZJmyUejETXmi8Nc5+fngUCAUWiRhB2n"
    b"Wq1Wy62MG5xq3d7exuNxxs4Mwzg9PXUSSdcSRXFra7rsHh8fAWBvby8cDjNq4e3caDSSySRu"
    b"GY/H9FBiCwiCYI/x+/1PT0/sOxEh5PP57PkPDw+JSFLLsixN0zRNw1NWqVQ0TUMIsTthTNPU"
    b"NK1SqQBAPB7HfVmW9R+tGXicDcPwSmgewzAAIJlMLgr4IIfPhuBWq1OWOBqSdFGudTrr0mq3"
    b"VGq7qsrFdDQqXdSY1FgnMX/XfuPurpQXsZ2c/l5mEGNfW5E3UqnCldIuTc2Kv2pr1CKJFC7z"
    b"+EuuuvZaxU6MJkTWFKvQet0OYiLqNsUKtGpVGQAAxLOTiNscnmp1OrWyxKWxVf6y4NrK8e+t"
    b"RchpTrY1ivnS9RWDFLuWHbHUVpiUALwsp6+lVC1GJZZK6onWWzmdK6VqMXrhvpR6ozVPpHA9"
    b"rfHyT6YR87pAzGq8+vvPWs9EktS3qddmnYmQ+vE6kZt1JkZOzlgX2Ep+NM+8XC8wUqvf7+u6"
    b"ruv6cDgEgGazqes6QmhJr4ULHyGk63qz2QSA4XCI+6K8UhE3Ier11efzeXJVRAhtb2/b8wuC"
    b"QESSh49pmgBwcHAwf9kfDAa9Xm93d3e5MbPR6/VeXl52dnZisRhuGY/HDw8PuNN56Geiqqp+"
    b"vx9/Hx8fK4pimmYwGGTUwt3zPH9/f49bnp+fqe9TTo9qhy8tXuFUK5FIePLs5vCdzKnWzc0N"
    b"z/MMSgAAjUaDuqXs0LXYB+YdFEXhOO79GFIrk8lUq1WicX9/n/3NDQDC4bAgCN1ul2jPZrNE"
    b"Czf5/CvKOZ9ay7ChWn8BFZpXh9qFrO8AAAAASUVORK5CYII="
)



icons8_centerh_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyAQMAAAAk8RryAAAABlBMVEX///8AAABVwtN+AAAA"
    b"AnRSTlMA/1uRIrUAAABbSURBVBiVY2BgYDjAAAaMDwaSZgbRBgwM7A1AuoKBgf8A4wPGP0D6"
    b"A+MDdhD9h/GBPIi2Z3xQbwOk+Rsf/AHRzAcffkCmYeIwdTB9MHOg5sLsgdk70P5ngMQDAOj0"
    b"Q7lGJdVSAAAAAElFTkSuQmCC"
)

icons8_centerv_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyAQMAAAAk8RryAAAABlBMVEX///8AAABVwtN+AAAA"
    b"AnRSTlMA/1uRIrUAAABmSURBVBiVY2AgCOT/QWj7/xC6/n8DCm3DDxGX4YPQcnIQmk8GQvPb"
    b"QGh2Cyj9A0Izf0ClGR9ALTxA2E0g20GggQFM/T8Ap2HiJIADqPajuwvubigN8xeMhvkbFg7o"
    b"4QMLN1g44gUAbSsw0GOTYp0AAAAASUVORK5CYII="
)

icons8_split_table_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"f0lEQVRoge2Zv2sUQRTHPxcVjPEKSaMSSBQUvNPexh+IWMfGwp+n2Ci2IlY25iL4LwiCguLP"
    b"EBTUIMRgY+2PM1pIrNRCBYlGuBMtZg/fbm5m3+waWHPzgYXZ2TffeW95tzM3DwKBQOB/oqS0"
    b"qwCHgSqw3GLTBGaAG8BUit5OYB+wDlhqsfkJvAKuAA2ln1Z6gFGgBfz2uO4A5Q56ZWDMU6sF"
    b"1CNfMjPqOam8HiYm7wEmcuiNuBx1pVYFeA4sie7fAJeBrxb7FcAwsEP0HQCuRe1DmDRp8wQY"
    b"B35Y9FYBx4CN0f0vYAvw2uFzRy7w921MR46mUQLuinET4tlj0X8b3e+zD/MC2+PqSt9j3BcC"
    b"ZzzG7RbjPor+T6J/l4feWTHuns3I9QPqSzih5YNor1xAvRi5vgRFIgRSNBZNILbtQZIK5muk"
    b"YVBhsxVY4zF3LibJvgq3r1mhN/sP9CZtznZdas0An5W2vaSnQwOYU+r1A0NK247I1Kp5jKuS"
    b"nlpVD70a3ZRaIZCiEQIpGiGQoqFdEM8Bp5S2vQqbm/gtiKloAxki5+qaIPdGMEnXpdZF4ici"
    b"LgaBSyk2x4H3Sr09wOk0I20gDcxxjgbNPuoZ5jhUw4DGaNGkVgikaHRFIPJP0WoPzbWi/W0B"
    b"9WK4Ankp2jXiR542SsAJi4Zsn0R/iH3EojFvYhvJssJbTFnhi2PSvcA20bcfuB61DwJXxbMp"
    b"TFnhu0WvHzgKbIjuW5iywrTDZyt1sh/dPGB+oedRDr3zWQKQk4/gX3q7ReeT8zKmLOej1YyC"
    b"cH6YtMXQTZiK02bsu9sm8A5TDH2aorcdUwxdDyyz2MwBLzDpmCmdAoFAoLj8AayZ/luTovAF"
    b"AAAAAElFTkSuQmCC"
)

icons8_keyhole_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"jklEQVRoge2Zz0sVURTHP6XhIqSflNEPXQjVzkCKCkJBK7BF4b6df0MQbSIX0aJNENHCla2C"
    b"liHqwiDxRyISlBRRIEkuxIdRZGHvtbjn8obXzH1vpnOn4TlfGOZw7jn3e79zf8y9M5AjR44t"
    b"gW0R/gG5tqfYllpQBB4BQ7UmzACljF4zYQ1ujBBie+pWVOJ/wBlgkIhRFCXEYgEY125RQjS5"
    b"CrM2BxIjF5I11I2QapP9X7ADOA+cxCybi8AksOmDzJeQ68Bd4FCFfxm4ATzRJvQh5A7m/QPw"
    b"BdML34AuoA0YBtqB2x64/8IsZjj0xcy7InlF4CZmeFk0iq8o16WYdfdJ3bNxkpIKeSV59xwx"
    b"DyRmOmbdqQlpkZxfwF5H3BHKvXIwRv1OIZrLb7vcl4A1R9xnoIDZM7VpkWsKKcnd1Rtg9ky7"
    b"xF7XItcU8hbYAPYAFxxx14AG4CvwSYtcU0gBeCr2Q2B3SEwrcF/sYeCnIn8okq5aBzDvjhLm"
    b"aZ8OlF0GVqVsiepDsBKpLr9gtiQfJX8k4J8W3wfgeIJ6U1u1LBaBebFfB/zWfg680yb1IaQB"
    b"6BZ7LOC3dq8HTi9COjHjfwN4GfCPA7+BE8AxbVIfQuwTfwH8CPgLwFxFjBp8ChkNKRutiFGD"
    b"tpBm4KzYYULsPOnR5tYW0oXZuq8Ab0LKpzDbkn3AKU1ibSF2yIxQ3nsFsQlMiH1Rk9iXkDFH"
    b"jJdlWPOoexSztII5s1+NiNsv93PATuC7BrmmkNaAXcsxtgk4DLzXINcUMgn0U37i1bCMkgjQ"
    b"FVICninWFwt186UxF5I11I2QapO9gxTO1TWiw1UYJcRuLwZ126KCYpgzSshjzAe0rA09+3s6"
    b"R44cWxV/AAHro5qkVYvkAAAAAElFTkSuQmCC"
)

icons8_add_new_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"7klEQVRIie2VOwrCQBCGP8Vr2FkE8VHFVgTPIVZ23kNSewCxFlSwU7AXbFQkhWDhPYyFE1gX"
    b"E3fXRyH5IPzM7jA/sztLIMOCnBYXgSFQeaPmHugDl6SEORB94JuqRQuaSVW0AxwduigDY6Ce"
    b"ZhIfXwhsHUzyWp2HRVN6wFLU2tmUEtAW/ZqJEz8x0S9epwt4StxUdKCsh8DI1PTMfc59iReY"
    b"vYuF5PsSn206mQAHJW4BDWADrLVOjNE70QlkP0jYf9rJ/0yXrckJWIk68+pOXmE0XZGoB1wd"
    b"TOI3FaUlzfjB/6QvSTWHLmJ2UifDjRsEWFa4krvEMAAAAABJRU5ErkJggg=="
)

icons8_edit_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"y0lEQVRIie3UP0oDQRTH8Q9uzmAqu9zBM6TI2qbRKrdKIygKKfQO9skJAoJewhVMUuwbMkqa"
    b"ZTaN7A8ezPxm3vsyfxn0WxWW2GByLsAD9hGffYMqPEXxBtu+QRWeo+g3alxmoHWaeFEAeMQ8"
    b"+iOMcY2r8NYn8joB0goavEZ7p13RPsarvgB1+C+OB18MSLeowU34U3yFv9Ju3QAYAP8VAPcZ"
    b"YBbeLPrFDy3pPYrdnQuQQ24jegfkkDyKz+Bv8of2N016wwI/JZBBnXQAlthpgy5S6SYAAAAA"
    b"SUVORK5CYII="
)

icons8_paste_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"3UlEQVRIie3VvU0DQRDF8R+IOoAMJ44IoBl3APVAARSAnfMlJyREJCcZXAAOccwRMEjWaHUL"
    b"J5Ac3JNGqx29e/+dDfbYMp3iAW+4x8lfAw6xRrtR79H/tQ4ww2uqVQTfYoy72K8K3in2uyCz"
    b"dNpcF+G7rPimXZBlmCY4xrwQ0BR68/BPYr/cDN1NkJ1YGzzhpXCQo0JvEf4m5YC9rrFwjqv8"
    b"UVKLx66QGmSNm4qnqnxd/6IBMkAGyJZA8rPSxjrCR4+8UcopqvY/+Wldd01yFhOMe0zxrWdf"
    b"r/egfvoE8sJYB3CAY3oAAAAASUVORK5CYII="
)

icons8_remove_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"g0lEQVRIie3Vu08UURTH8c+SjQGWVhOkIT4KqLUwsQBChQ3RoK2N/gPWkNBSUFGgiZaGREOl"
    b"nYEE46Mh8gf4qLR0YyBxeQQo5m7cHe/sXsKEil9yM/fOOXO+M+fce4YzUCXBpwdTGAlz+I23"
    b"+FXWi7zEUWTUcb0MwFAI+AJXcSWMcRxgISVINbeeQq1lPRyuG/jWcv87tnETM7kYH/GzE/SH"
    b"eGoeRnzrBb7TnQBwG3PB+Qkmw7gc8R1rsX/FVphf7AYR3uQoBEnVF6wXGXuKDGUqBXLD/1u1"
    b"ggfSzllXyAW8lqWiCapgGSu4XwZkD/fQj/cYxRIe4zlepUBiihX+Fv7gb7A91Z6qUgr/Ge/Q"
    b"iwYWAyxJKZBmDe5iVZbCNSfoW90gFe01mMEE+vyr0akhVQziGR7hEJu4g13ZhuiqfIPMa192"
    b"Hg601+CTLF17ZUCaoJiSAMTT1Xy4FrEVaaATNPYlm9iR1eFDAuASrsl+bFEV9Z4JzIu3+Lwa"
    b"eINZJ0jhuQp1DEu0WE60jG9UAAAAAElFTkSuQmCC"
)
# ----------------------------------------------------------------------
icons8_visit_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"iUlEQVQ4ja3UsUvVURQH8M/LtDIQyfJRDS0ZDoKQW2QQtgQVDfontNRiVGMIDjXlEG2Cow29"
    b"h4pNDWFGa7RUg7a4JErBWyOw4Xce7/bj/d57Zl84cO6553zv93fu79yS1jiNmxiO9VesYruo"
    b"4FBB/DCeooqjWA7rxRKeRE5H6IqiBygViHgUhxUJ+gsPMZOQ35N95iruJiSzuN+OrBuf0BPq"
    b"qngs6+WZOKgSuUcitzsl6MoRXsZxvMYtDGIOL/Abz3El6r5gBDVs1QnyjT2Hb+FfwgqmMYlR"
    b"jQu6Fi3YiJr3dYJ8U3dQDv8nBqIIhvALJ/EjYmXsaoFBrCcEH2S/ykRYb8TOR846TqUEzRTW"
    b"cCGUzWEN42Hv8AybkVNrpxCuYz5ZD+BG2IkkPh+5HeGtxrg1w1Co7RjjWGyx/xJX90MIb2S/"
    b"Sh6jsbdvjMkuJJ3nUsTGioryk5LiOy7iLD5G7A72sPAvCqEPn2WzXA6/v1VBs+cpjyncDn9J"
    b"43E4ECp49T+I6jgW1hZ/AFlFRTnCbQ/nAAAAAElFTkSuQmCC"
)

icons8_circled_left_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"M0lEQVRogc3az28VVRQH8A9NocSSFpAfblWskZQm2hZsBfe6cKFRDAsTQogJEUGwMbo3RNQ/"
    b"gBAX/gEKCaRUiYludCHEnfFHDFVJqAbQlh8JaKiLO5M7fby2bzp3Hn6Tybw39845586558c9"
    b"9y6TFsuxGX14GKvRm7VN42/8gh/xPf5NzL8SNuAAxnENsy1e17J39mN926UuYBQn8Y+7hbyD"
    b"iziHr7LrXPbsTpP+t3ECI+0cwAC+aCLIOA5hCPct8H43hnEYZ7J3i7TOYktNsoOV+MBcDVwQ"
    b"plWVqbEeBzFp7oc5iq4KdJuiD98VGF3CbsG4U2E59mCqwOc8NqVisAN/FYgfE7xRXViN4wV+"
    b"V/FUVaLP4mZGcBovViVYAjsxk/G+mcmyJIzgekZoCk+kkK4kBvGHOJgdZQk8Ik6nKcFG7hX6"
    b"xMFcVcJmVoqGPY3H65CuJAbFaXZei97sQ9HQ2mkTi+FlUa73Fus8IMaJY/XKtSTk3uw2+hfq"
    b"mEfsS+p1sUvFGtFePp+v06iout3tkWtJ2CvKua1Zh5Ni2pEyYqfGcjGd+bSxcYOYvB2oSYAe"
    b"ISH8GQ9UpPWGaCtz8rzX52tIhB58LU6Jqi69+OFfKzacyR6OV2TQDI2DeDMR3YmM3un8QacY"
    b"bA4lYpKjW1hU5YN4OyHtsYzmjMymBwqMhhIyqksTOYYLtPvhJXF5utDKrgzq1ESRR75sfkHG"
    b"ZBa/JWJQtyaK+D3j8VaHGMEvJyDcjVNiEeEdYXlcF65k995OrMr+XE9A+GM8nf0eU+8gCIYO"
    b"vR2JCS9LTK9ldIiaWLVQxxbximDk8L4wtepET3af7hBWgrAuAeEbeA7fZP/fVa+x35/dpwmL"
    b"p9z9ptAKwei/FD1XHZoput/nmRsQhxMyqtsNb9UQEIspyuHEzOrUzF0pCiFZnBWSx9SoSzOf"
    b"ZfROFR/uF9P4DYkYFdE4mKo1so1ibWFfsaGY3x+syGQ+9Ahf8SfVP9YhQdZbmnjbE1njpP/3"
    b"UncFfhVk/aRZhxFR9XvaJ1dpvCrKuXW+TmfFMuma9shVCmvxpyDjxEIdt4i2crx+uUrjI9Ep"
    b"bV6s81FRdTvrlasUdolyHWnlhS6hUJwHm8HaRGsdQ+KO8beCwbeETUIJf1YoUd7LbYVHRbu4"
    b"gofKEtgmbvRcxpMppWsRQ+Zu9GxfKqHi1tuMUNpvF3aJ0+kGnqlKcLs4zXJvVqdrXit6p3w6"
    b"jaYivkl0ALnd7JU2A1ghBLvcHnLDLm0Ti6FL2CkqnlSYFArKVXKnjULulKcdeZw4ooR3Wgr6"
    b"hU2WxiMcE0KKPiysQ+ZDt5BajAlJZONZlgktBLuU2CbsTzSeJcmvi8J0zA/VnM+eNet7S0gA"
    b"582d2oF1Qmn/tLjSbOWaFhZF+yQofKSuQ3XiMSGIPShUOfKSzYwQjy4IB89+kPDg2X+tZHt/"
    b"EvF7AgAAAABJRU5ErkJggg=="
)

icons8_circled_right_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"IklEQVRoge3a249fUxQH8I+2w3S06t4ZSnqhD4KmtH8AQvDihVSjaTUVvAmmkWgrGi8eRI0X"
    b"nqR4FRLCi4SkBtGExCVFlXhwqSra6fSSlt/Pw97HPjP5za/n9ht96DeZnMk5a3/X2r99WWuv"
    b"tTmNUwtnNMw3A1fjKlyJi9Afvx3FfnyHXfgKrYb118IAVuMN/IV2wb8/8Trujhy1UGdELsFD"
    b"eADzJn07gR/xE47Fd7NxKRaib5L8QbyIEfxaw6ZS6McWHJZ+3RY+xKNY0cHQPPqwEsOxTSvH"
    b"cxibpOnYMyzHNznF48KvuLgG5xI8H7ky3q+xrJalXbBBmCbZCGzHYIP8Q3hZGqGjWN8gP3gs"
    b"p+A33Na0ghxuxM/S6DzdFPGWHOknuLgp4i6Yj505vZvrEt6fI3sXc+oSlsCcqDPTv6Eq0fXS"
    b"mthpejuRYQAfRRuORZtKE+yJBL+Ynuk0FQYF39IWooLZZRo/Je1ONzVuWnncLG02W4s2ukya"
    b"Ui/1xq5K2C5tywuKNHguNjjk/51SkzFfiia2nUz4HMnDPttbuyoh+5HHMbeb4L3S2ljYe7tK"
    b"Y5G0VtZ2E3wnCu1o2IB5+B6fC1FzHXwg2PjWVAJ9wrpo45GayibjchyP3N+q15nhyHMQszoJ"
    b"rJS8aGnHUwCrhHNK3c6scBI718WPJ3Q/T9TBnVJndgsHrbI4M8exJns5IyewJD5/iIK9wGtR"
    b"+d/Cmf495UfmuHD6hCuyl/k5dkF87q1g4PnCjlIEewQ/sBFL8T5uEEKhotgrdOLC7EW+I1lQ"
    b"OF6CkJAp2SP4oCpYKuxAZdblofj8z5fMmEJwulE7LZQfkWwkyobrvwvOs8y5fZUwtQiL/o6S"
    b"OrORyEZmQkf+iM+hkqSEfNanBWVX4eH4/27l1wcpV7C/08e1er/93qXZ7feeTgJ5R7Oikpnd"
    b"0ZRDzDvu6zoJzMJYFBiuqGQqNBmibIw8BzBzKqG3o9BoDUWdcK6wRTcRNI4KNr7ZTSgLU1rq"
    b"ZQ97hcVSGL+mm+Bc6WA10nu7SmNEsG1MATexTUooN5kSrYsh6aj7TJEGC4QDfhuv9s6u0nhF"
    b"sOmIEutsq7RWbu2NXaVwi7Q2nijTcLbgsNrYp5rjagpDQrTbFkoapWsn10pT7Auc16R1BTGA"
    b"j6V81vKqRPdJXnSH6qF6FeST2C0hw1MLm6XOfKa+QyuCyWWFTU0R5ws9+3B7U8QdkC/0tPBk"
    b"0wrWS2umJZTJqoT8U2FQyO/mS2/rGuSfgGVCobLJYugiIRWaL4buEjabnqJfmLN5xVl5elgI"
    b"s4uWp0dNLE+P43GcVdaoOhcGhoQLAw/qfmHgSHw3IEQNnS4MjOEFYWSqZHEaQdUrHAdim9U4"
    b"u64RTV+qmYlrpEs18yUjDws73m5hDXyJfxrWfxqnDP4FKSVCfzhVg0gAAAAASUVORK5CYII="
)

icons8_hinges_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"XklEQVRoge3ZXYjVRRjH8Y9ZgS8lgeiSQpGllBDWTbQpWBfe9K500UZJlGVGRYQoEYFeWBhE"
    b"ZO/pRRt1GVjQRUQ3vUgXuhZRZBsFZkpQK0saVL5cPH85x+V4/jO7c9iC/xcGZmfnP/P85uWZ"
    b"mefQ0NDQ8H9iSo/bn4rzq/wojvW4v55wuzD+RJVGcdukWjROdmE9LqjSevyNPzLSN7grpbOz"
    b"E426Hk+gL7E+XIFnMVL9vQ8/486MNhbhTXyJ4W4VU4TMx/t4Bj9kGPFch7K/sDujjd14DFcr"
    b"IOQafI8tGQbAUzX/X4lLxYiPdKl3TDiNrpyVYNC5Ym3X1blDjFwKN2E7VuGtxG+6kiIkhR3Y"
    b"ik+xNKH+fBzAZ1V+wpQSchVexbdVvo5B7MW1eKSEAaleq46n8bLYkO8k1D+Kuwv1jXJC3qvS"
    b"pFFqaZViGYbwgThEk8kVMg0vidG/PPPbFLbiE8zFfTkf5gpZg+U4IvZEaYaxApepOQDHkrtH"
    b"RjEL86p8HfcIz0QYV8eDwgnsx4c5huUKGcRM4fufT6g/Q2utz0iofxSvZ9qEfCHHxR5J5Ysq"
    b"Qb84yU8xV1xCv8q0oSOl3C8x8n/in7ayh7C6yk/Hb1X+SiFwCrZh40Q7L+V+H8fv4pp+cVv5"
    b"Wiyo0tq28huwBw/j1hIGlBLyAO7Fj9IM2ynE7RBXmwlTamntxCviyr2urfw1LafQvrR+wkXC"
    b"cRwuYUApIRvxLg5pGUuM9pk2+78KiaDsZv+6Q1m/OHOIGaijT+y3X8SBezy18/EIuVkYNyj8"
    b"fjeOaL3+Zie0/YY4bwbEgZv86MoVsko8TQ/gOvVX8UGxfwgnsLmm/nliNvqqfDK5XusSEYD4"
    b"SHid0qwTTuFj8RROJndGtour9nI8mvltCt853SEkkytkBLeMp6NeM1kPq9n4HAeNcwbGUkrI"
    b"MhEifVus8ToGcA5ewKYSBpQS8qIY4SXSggpDWCzuXzmRxzNS6kDcL2ZlXpWv41T8a4GWe54Q"
    b"pYSsxv3CNae+7IaqVEdKpDNJSErsdUTnoPVYZonQaiqLqrSrrmKKkD1iPQ+IYHYq0zqUzcGG"
    b"jDYO4kb8WlcxRciweG88iQszjJiJhVpv9oUiTNqf0cZ/gpVO/+ntsB4eps2PoQ0NDQ2Twkmp"
    b"+6gCcP0/FwAAAABJRU5ErkJggg=="
)

icons8_copy_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAA/klEQVR4nO3XUQrCQAwE0FxipXhRfz1jEYunGb+EUlLb3U6ypczA4l/JM9NFzbgB6Uxm"
    b"NpBn6wJBb8xvCMYz0BPDhIyzz0Kar3oIxjPKDJO+GSbEemIeZEhXzDNgq2XPO8O6Lt+kbwsr"
    b"W93EMO/+j5ndgyCbNWPf/Ucx2JhnFcOETISXEjvmcWvGhAwEDBrOGHH338zsdaBmaDx0CANT"
    b"k1BIJgbRkCwMMiAZGGRBojHIhERiEAGp/W12CQjOCKmNIE60EUZULSeqFiOqlhNVixFVy4mq"
    b"xYiq5UTVYkTVcqJqRVSr9a8yzraRy0AogSDt0Ub+RdU6a7XQ4Qhii3wBuJ0AhigWdm0AAAAA"
    b"SUVORK5CYII="
)


icons8_paste_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAABHElEQVR4nO2ZTQrCMBBGv50IvZQLvZzgQj2Pi/YirgTtIT4pVNAiJplk0qTOg9nlZ14m"
    b"iSkCci4AKIwOBcHIUGUN4ASgV0zId9x+zGXIKZhzhpUNHf8oEXmMnbcBCYXi2283thtyUpsk"
    b"tG3uOTDtONfWemEiDFgRjeuX2hX5Rhch0ZYkogFNZIJVJBFcytZKhlQk5kmv8ilAoUhuCbry"
    b"ihXJBU3EgVVECG1r/fPWagBclX4zWKtIO6eIJjQRB1YRIazhsHdLEWlLE9GEJuLAKiKENRx2"
    b"2lvrDbu1YNdv3sPOH+E1cM0iTUlvLV+Ke2vdxgYbbwXPgRND13x7wQp6DZwYuuZbATgAuNcu"
    b"IsVESq0IMwdSE/OfuzQ+ruknDkHnlfedtfwAAAAASUVORK5CYII="
)


icons8_replicate_rows_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAABzUlEQVR4nO2XTU4CQRBGXxDjQon3UI+hLmXDDXRJRNAz4D0U1+IZiDcQMRzAxK26kYVt"
    b"KqlJWhyYyfxkeky9pJMZuqepr7uquhoMwzAMw/jDI+ACaRNy4AJrmck9QUE4E6LYjhSMM9dK"
    b"uRK1Sc8uQUht0rNLKaRqnAlRbEcKxplrKeZaBePMterqWq6sC09BuCQ7Jv9FSBKhCDkD3kIW"
    b"sgl0gBEwAz6BD30eaZ+MEXZDFdIG5inceq5jCU1IA7j25n4CLoB9YFubPPeBqY75Bob6bTBC"
    b"IhFfQBfYWDNW+s6BhX4jYjJR1IXoVOdr6+qKiMOY/3sAxjG/H6kY+fYki5C06XldewW2NGij"
    b"mOgmLFwcPS9mogRQCR0vJjYyCGkCz9ovc1XGnRohK5s1Jgfaf0uFvKgRezmEHGi/zFUZ72pE"
    b"ywtsl7JFCaCl7zJXMELEuLRC7kMSErmWHHa1dq2RGiEndlYhV9p/QwDpd5oj/c5CSL/+gShl"
    b"RxzrhPRDORD9EmWhZccyYy+wfY7zlihlMNSVFcN66jKraOpO5C4ay6ChBsnqRjEz0Iy0o02e"
    b"L72SJHcZXybiImkvVsG40yqWr7pyzZUmOyH1lH/V/cUPISq8buey9gMAAAAASUVORK5CYII="
)



icons8_canvas_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAAzElEQVR4nO3UsUpDMRjF8Z84+hYVLLj1CYoggsXVQR+gg5OTvkOhFHGQUjCla5+gKHbt"
    b"Y5VAlEva3kZux/7hQPLl5HxJhlBGH08OwCUmGGKUxrG2l0cEjDOtMMBr0iDVcl/AQzVwtqPR"
    b"GVqZYm0bs+okdmhKOAY2JuycHANLCb+DNha4bqgFLmLgHF8H0jwGdnBf0fIfActsb8zaIB77"
    b"Gz+42XK120rYecnj3uEZHzWeT7zgqiRwmv6+bo2nV9D0j2h6x0mN5zT53vKVNTsZRvouCNVM"
    b"AAAAAElFTkSuQmCC"
)

icons8_prototype_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAAV0lEQVR4nGNgGPHgCAMDwwMS8RF8oQZSMIeBgSGBSDwHqod+Bh6htpepDo4Q6Zoj1IiU"
    b"OUjhBVM3h5hIAWnGBhLQDIRZ9GDUQNqH4RxqxvIRaqdDhuEPAFGfZAHJHImuAAAAAElFTkSu"
    b"QmCC"
)

icons8_rectangular_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAATklEQVR4nGNgGNEgmYGBYTkDA8MqEvFyBgaGRHTDTBkYGP5TiE2QDQyFCoJoUkEoNr2j"
    b"BpIEQkfDcIgkGxMqZD1jdJsSKSgcEsjw2XABAJi8Vfblja28AAAAAElFTkSuQmCC"
)


icons8_oval_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAA8klEQVR4nO3UO0oEQRSF4Q80EVQM1QXoknwGGjrbUCMZFbMxM/eRmOkOZlB34iMaHwxy"
    b"4SqttDPdjZH4Q0Fz6txbXdSp4p8C81hHGyc52qnNqcEiLvCGZ3RxmaOb2ivO0zuUTfRxgyVM"
    b"lHhCW05PP2tKWcEA2xgzmvDsZE0s8IUZPGBffQ6zNnp80sIjJhs0nMITtoriMa405xqdotD5"
    b"7Yat3HL8fl2my7b8cSgHDRoe4f77ocijH2QUqsRmHLtZE5kdGuzbzOVPwY65u/RujFp5AWd5"
    b"vV7QK1y9Xmoxd5reysQDsIa9wuMQ36uYrd7GX+cdqXM6cP80NrIAAAAASUVORK5CYII="
)

icons8_line_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAAUElEQVR4nO2UsQkAIAwEj+jOruAiFuKQ2qSyEMQvLHJNuuMJ+cCHmFKWgAZUhSwDHZg+"
    b"TZFsAsPlITsTO7snxZ1dY1vRn7qJUxRF35E+SwkL3b0jER3TDbgAAAAASUVORK5CYII="
)

icons8_journey_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAA1klEQVR4nNWUOQ7CMBBFH1TQEDgNHAE4BwQ4QiSWK7AcBVFGIGhzgwS6cI2gkaZwgbEV"
    b"LCS+NI31/TTzvcC/KQJiYA70QsDuQKVV6FptxQbMhGaWugBroBUKWKonBZq2kQsDljtGbgB7"
    b"9Q5tJgFMgRnQ9YhpoMCEAJIODwoc2UwS8EYDzxz1VNjRBpNgz2oqPYBXYAm0bcCxwrY6ztdK"
    b"FNj38MorWugBRq4Od44O5fQfvi/q5JGheVcrLen0rSTgFXALBazzieRAx2vnB0mO8sVNQsB+"
    b"qxdgAGI6yhzqowAAAABJRU5ErkJggg=="
)

icons8_node_edit_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"k0lEQVRogc2Ze4hVVRTGf3e8jWXiNDmmoc1MM6RDChoYOVpj6oCSWVkJvYweJkn2oAcKJYn0"
    b"wlTsn6ISx1QKFXprhDWTRmnZwwGRokzKMslq1LTCbG5/fOt0zz1zzn3sc2bqg8M9Z529v7XW"
    b"2Wuvvfa+KaASqCOLb4AO4qMf8ARwtT1vAOYDvyXAHWYz+4GM79qfgCKAt4zvY2CH3W9MiLuL"
    b"zWngTOAL4DXgcqABmBdTUQUwBVgJ3GqylcDNwGPA4Zj8YTaTAdZbg/Xkehr3muVTPith7hyb"
    b"UybsQHFWh+JvdJFfJgVcCdwN9DHZXuAd9PXbgStM/iowEmgBmoGzTf47sBx4uUidAJ+E2EyL"
    b"vfCulUWSNQAfog9xFFgCDPW9vwfoJPsFO03mYRiw1PpmgA8C/fPB1eYuuAFlnxPmQFVEu0nA"
    b"c3ZNimgzAFgG/A0cAa5zNapUPIC+4HfA+AR5JwD7jPuhBHlD8aAp+hTo3w38VcDnpmN+N/AD"
    b"MA3FeTvd44SHSvShOoHpSZPXoSzxIzAwafIQDAQOAL+SzW6J4E30haYmSVoAU0zn60kRNqOY"
    b"XZEUYQSqgbkoI5abbJXpnpCEgq3AX0BtEmQRaEBli7fmtAG9gHqU4lvjKhiKhndNXKICeAo5"
    b"cC2w1u7H2bsXzYb6fARlBRTMRGVId4dVPTL+JVTKeDKA582GmXEUvI9W8PJCDWNgKArdNnse"
    b"AvyBSv8U0BuVMVtcFZSjgu6NGEbWArPtqolo41XcjT7ZMpPNsOeNwDHgJBcjGoxssUtn4CpT"
    b"7k3gY6hS9mM0in8vnOahDFWFJv+XQBp40jiGuRhyoXW+z6FvBXAI1WNTgUvtvgNtgT1sRllp"
    b"uD13AuvsfoHpnw3cT24CKAmXWWeXSTbJ+s7xyeaYbKI9e+tTi6+Nf8PUF63u3yNnMmZTKPJl"
    b"rUwJhgdxyH6rfbIa37sU8DjwJ/BwBMdR4BFgMNkP0ulizHjkzFyHvmlU+J0AXgBW2/0OtNDN"
    b"MO6lgX7+EQElnD1k59lFDrZQY52Xu3S2/q0+I95FI5RGk/gwXTdkQUcArvdxDHExpAzt2N5z"
    b"6exDpV0evHgPbp4qTP52iB077d1gVyM2oTjuU6hhkTgFTd4DaDJ7qAC2k/3yiwL9LjH5s66K"
    b"7zSCa1wJAphnfHf4ZH4nFgMfEe7MFlQBFHtAkYMBwHF0vBMXlWij9DXZkqcPWSc8w/2OLfD1"
    b"byR8DhWN1UYwxpXAMJGumWqMyX5ADnjwQulbnyyFFtWfXQ1oQEO6jcLVcj6k0YHaAeBkn3wR"
    b"Mno7cmYcSjJHgLG+dpMJT9klYYmR3BuHBLjLeG4LyD1ndpJ1IliObEZhXk0MnArsNqKmGDx9"
    b"gV/QAXRwdD1nwpwYZe/WxtD9L4aj8qIDOC8Gz6NE101Rk3mNvRsVQ28OLkabnkOo6HPBILQ2"
    b"bQ15F+bIWSgSNjvqi0QTGpUTwELcNjsrkNEXBORhjnjzc7KDnoI4B/jMFOxGYZIqof+5qJLd"
    b"EJAHHalANVl7ifwloTc6C/Z2gbvQBijvaYcZNAL4Co3qTaga9iribb7np012YyFjkvByENpF"
    b"3gKcbrJ9yLG96PCiF6oSzkDb2wEl8P9Edp5EIsnhKkfHnJNR+hxG7sIHGr12VFHvA55B4RUM"
    b"MQ9LUToekaCdJaMMjUAd2psEK+jhKGwW5uHYZdf/Es0ohZf65+ce8mwn0t1qcjimo5B7BU32"
    b"YlALnI/SdVuBtj2GdlTtloKx9NBfcsWiHxqFdYUaBtAbheOmqAY9HVqNKBU3ob+VS0HK+pcR"
    b"ciwUZ3/hAq+qPejQ9yBwGtlTyf8UrejgzSUSpqF5cnuiFjkgjVZ51/1/f/L86dSTc2Qk2ljV"
    b"4n6AcJyIg+yedCSDMk89hQvLfDgaJvwHFoGnkXE7UcMAAAAASUVORK5CYII="
)

icons8_warning_shield_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAACV0lEQVR4nJ2Tz2sTQRTHV9GDB/8GQXoT9eAf4KXszk6CoFj1VpqCVmNOVRSDRnvyB14k"
    b"1GZnZheMBxGkhogmMxu0ojm0SWixgQpaE9M0UE0PWjTJJhmZQNLWTZsmX/jCY997n2Xem5Gk"
    b"LRR/OLCPBZR+iuV7JnEsMgKXGFI0isHAS3xiv7QTRZDcxzTgMXWVUQzKDKvVmcnBUmbay4UT"
    b"k4MVhtUaxaBiGo6YqI0guc8GokgeNQnMUgT4u+DJP2nzcm0lfZdXfxicrwY3WXwTubTpqU89"
    b"PVUSPabuyFEMrrSA4m+psIuvZf02QKlAeH7uQcMi/j+/lvVz0WsSaLaAjMBQmrltxcICNH6j"
    b"v2ERt6uZZ27OsPpiHYgULRV21XoFJsOuahSBxxtmCLzx5+dKvQI/PjtbYghcXwdqypmY4Szz"
    b"1SddA+vFIDcNZyWqgdMbZug4KLb1O+PvGvhr8REXvTEMD7SAnEu7GIHFXOJW18DvMzc5w3DF"
    b"dhcZUo1UeNjqFpgMDVkUqaQNUAYUq7XSsrbje/g3PyGOW49iINuAPp9vN8Mw9zV+rb5pRt8m"
    b"+PSr0YZFvDH35cNVznRHRvS2fctRpFyIGc5KuYA7Hrlc0JrbHZa2UiJwbC/T4cI8dVudgJ+i"
    b"I1Wmw/Rb3/E90nZ6oymHKFKtfOpO20ssvDw7xkUNC6iHt4W1FqQBDyPQKn62b/Xnwn3xbqsM"
    b"gYtSN6IY+kRjYW6sBVtK3W7AKIHermBNRQPgEsWqNfv6vJUMDVVETDVlpCdYUxEiH2XE+Z7p"
    b"jikTgSOdGv4BIclJf+4n3KEAAAAASUVORK5CYII="
)

icons8_ghost_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAABSklEQVR4nMXTsUtVYRjH8U/dIIcM57i6qTgXRg6h4CQ25J+ggoqbS0FLg9CQf4Agru5B"
    b"oSiIQwQ2tSnSIKLhqIEhCRUXfsZB495zFewHLxye5/t+n/Ny3sN/SDuGsqrXEVWxjN+F9Qvv"
    b"8aBZWRu+RvIOoxjHamo7uN+M8E02zl2o38JCerPNCHfwA2PYzdts4kWOe4btsrLb+IlP6MFb"
    b"VCLrD7MZptJINoD5HGmpDrcUZrEw5FKmCl/zOx7XEfbiuMBPXgTuBliOqLXRUXAPfdjAURx/"
    b"05dJHzCofEawkr1Pio1HWMdJms9LyKbDHud+PvwX1IFTrJUQboStNgI/Yw936jCVMF9KDPYq"
    b"RznAR3QWep2pHYR5XUZYm/4SW9k0UeiNp7aVwRVNpDt/wyFmctf2U+tyxTzDt8IFrj0PX1V2"
    b"nhY8zao932z+APy3U8fp28sCAAAAAElFTkSuQmCC"
)

icons8_circled_play_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAACGUlEQVR4nO2ZuUpDQRSGP+NSqKC4VCpY+gJulU8hiva+gpJKUIy9ShQ7S0UtXBp7tRMl"
    b"9m6VW6mJhVcGTkACQma9g9wPDgRumMkHc2f+OYGMjIwMTRqBcSAP7AO3wDvwJaU+l+SZ+s4Y"
    b"kCMiBoBV4AlINOsRKAD9aQr0AltAxUCgttQYRaAntMQM8OZAoLZegekQAs3AtgeB2tqUubzQ"
    b"CpwGkEikTmROpzQHlkikzoAWlyIhltNfpTYBJ8ymKJFITdlKdAMvEYi82W7NWxFIJFIbNid2"
    b"xfAs+PYgUjZNAKuGE3YAw8C5B5mCrkROcpDJZFUagEngzqHIk4TTuhm3mKyWNmAJ+HAkM6Ij"
    b"kncoUmUQ2HUgsqAjcuBBpMoocGkx/p6OSMmjCLLO54Bng/FvdERsIroO7cCibK31jq8O6Lqx"
    b"uSyZMKSxS5ZjF6n3qlyOcWl1ysHrbWmV/svLfuBRZAK4CrX95j2IqMC34yBQzuuIjDmOKMvA"
    b"p6VAIqUCqVZofIgwNN6bdCcLFjFeBbsLhwKJ1AoG9BueJ+8eBBLZovswpOjpR5nUGhZ0RdJ8"
    b"eHXRF56OQGQSR2ymKLGOQ1SkOExB4hhowjGt0lgOJXHko4n9u5ldDLScmgjAlKfd7Nnli63T"
    b"F97QvEv8VWU5J7pIkT6JMybZ7EFih/GJ7YOcZKwFuTPcyE2zIqU+X8uzeUmxUf09nZGRQfz8"
    b"ACGaYcKeMXOQAAAAAElFTkSuQmCC"
)

icons8_circled_stop_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAB/klEQVR4nO2ZO07DQBCGP0KgoORR8bwECA6CEsFBgnIAkh5QQNwABBQ8GtoUhI4oHIBA"
    b"BQllSGiMFk0RRULyrNf2KviXfsmSszv6nPXO7BgyZcqUSalJYAsoAxfAM/AJfIvNdUvumd9s"
    b"Ajk80jJQBd6AQOlXoAIspQmwAJwAAwuAUZs5asB80hA7QNcBwKg7QDEJgCngNAaAUR9LrFg0"
    b"A9wlABGIbyWmU00lDBGI74FplyBJLKe/bDYBJ9pNESIQF6JCzAEfHoB0o27NJx5ABOKjKBlb"
    b"k+x6QB04C+m6jAk7f9+2AqgqgjwAKxYxVoGGIk7FpgAMWzv1LCGGYb5CxmprC80txVMySySq"
    b"6op4G5qJy4qJzXofVthxE0NjzhTj9jQglx6DnGtAWh6DNDUgXY9BPjQgA49B+v8SpDsuS6s1"
    b"Li/75bhsv2WPQUoakE2PS5R1zcQ5aZ6FLRpN4WerNUXR+GLTnawonlLDEsZAPCri7FvE+D3E"
    b"aPLJl8XBKuw/EUj+WMRSNUWguH1ABM160nzouOgLFz0A2caRjlOEOMShzBn+KgWIGyCPY81I"
    b"YzkpiOs4mtjDzexaQsspTwIqxLSbvbt8sTV94SNJVFEB+pInZklRi1LOtC0A2lJ2WGfsOJST"
    b"5tmenBmactIciM31k9wrSRXr1efpTJky4b9+ABFcO8ADWuYXAAAAAElFTkSuQmCC"
)

icons8_checkmark_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAERUlEQVR4nO2aXYhVVRTHf6ONM4aaNuo4CRn4kmkiJqLgixSW4RdG0KQ9WKQpaToYgoKj"
    b"+KLpQ5LYk2D05IM+mJZipBhSlIipqY2DD+YH2hcY6ExWIwv/J5Zzz/Wer3vOEP7hMGfO3nvt"
    b"tfdee63/2vvCQ/x/MQiYA2wG9gPngd+BTuAvvbcBnwNbVLeBHoI6YB5wEPgb6Ir53AEOAPOB"
    b"PkUMoC/QAlxxSnUAh4G1mu1RWqVaPfb+jMrWA0e0UkF7k9WS54CmA+1OgRPAQmBgAllmWu8A"
    b"Z5y8duAlqoh6YLvr8KQGVZOBbJMxCzgn2f8CH6vPTNEIHFcnt4EVwCNZd8I9E1wtB2F9fQMM"
    b"c+VJVv0/PAVckGD7O47q4zngkp4mfXsbuAZMTLoSwSC+A4aQH5qA0Xp/3jmGBXEF1TtzskH0"
    b"pxg8rRhkemxMIiDY2BdyXgmPwc5D7gZ6ERPT3cbOY0+UC7ZHpYdZxqP6PjxOsAtmwQJUEagB"
    b"PpEOPwNP6PtbwI9RPWaLixPVcLFRsEY6/NnNIk7ru3mwissZ0A4zryLwqgLiPwqSHs2OzljM"
    b"KYt5jnZkEbHjYiJw6wFm3cvRme6DvA8HVcm4U96wTXxZ/e+IYPp7ylUYJCrekZYKJIDFqB+k"
    b"4KEKZtMkPS1APhZWYY4EfUW+6A3sU9/nIk5i4JanhRVuUaHlE3niQ/X7CzAyYpsP1KY1rDCY"
    b"ldnkh8UuKZsS07N1KaUuQZsKLbPLAy8q1TVX+0bMtmNdrCvBbyp8PIZt7wLeJD5ssv5QfxsS"
    b"erguRf0SBMlM1Jz5FZfNLY2hxFDgotruShiv+qq9xZzUAzG8qwgclWJbanAshAjGRZ3bW6lN"
    b"K8B82bq13fYAqm0z/6nqXY7DYkMwRHJuhBX+lGKzz9XsWPudZchmq8pvAs+SDqNd3CnB/pTu"
    b"d6qUNBl7u52ABETQIvJM0mOu66cEmzMIiJNcWvol0A+YrATNvi0jG6yXvE1hhbNVaKeFaWBm"
    b"c9Xl+tfd/skKRyVzRljhQEcajUCmwUjnYu35IsMkrUGE0Z4B5SodUMeLMuhwmBjt2YzZ9BLp"
    b"aJSqLF7POLGy2XuS7FAjWmI6vlYp0ATJzcv0PMxy1KRi4F6uyqcKPHwIQ61LcyNRonp3TLqS"
    b"noNV0um8LCcyxQ64zHiKxwTpYkH1hbiNt7mLF2OsRaHRufKtSQTUKaCZgO8LOsQe4A7Sv01z"
    b"LTdYNhnQ7jxXptENol3/k/aip80JHJ/TnrioPo2Vj8hK8FBnZrbp3q90ZJkQtfJOHc6cMr/S"
    b"sD3zkeNPp0TasrwMPePS563Vvqqe5kwtOMlYnCCzDCjMEkc7urQnY7vYNKvznqhCoECn6HWr"
    b"Ep8xUrSPngZ9s7J1wNfdfjBgF59L4wS7rAfUrOzyTsKfcOwTASzkJxzlfP5MHWd+pnz6V61U"
    b"p97PKj3dpP1V1AXrQ1Bt3AVSX1y/4Zx+TQAAAABJRU5ErkJggg=="
)

icons8_home_location_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAABYElEQVR4nKXVsUtWYRTH8Y+aEURDKAitTvISQUaakkNDIJi7+Ac4ODY4hFA4uIUO0tSg"
    b"III0pLQ2OEjkUkMQEoFjUIiVKAR55cIhHl7ufbv39QcHLuc59/uc53eey6W1buErltCR5K9r"
    b"Q7fxA1nES3RiBn/QVwc2GLATTOB1QDewEM+NqrARHOEYDyJ3OYEe1QGO4VfE/aa1brxKLGhU"
    b"gf2ODu6V1HRhLYBvcKUM9jD8OsTd/2ycQueLCsZxGkPIJ1tF+bRncbNo8Xvs9gHL0cGFtI6/"
    b"idkDFd7pxwu8xw4eF/n5tOL0hvEzaSCLeIerdYG5HV+i7gxvsZ9AF+sCh5KX82PmuoTdyB2o"
    b"CXyUANO7+jxy+dX7pyeRzD0qUyMBbqEXd/Atcp/S4tHwJSuIvaTuc0lNhmfNHUxiFZtNMZfU"
    b"TJXADtHT4nQttV0AnG4XlutafFmF16Vd3cBHrKS/h3MOR3bOP+nOwAAAAABJRU5ErkJggg=="
)

icons8_user_location_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAIAAACRXR/mAAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAAHOElEQVRYhc1Zb0ySaxQ/3JS0SHHiIGmVjchWUxdry2pI"
    b"5bS+uAwzxYbVCifJzNj60FYzbatWc/3b+tD8ogtdNvqfW25l2sDUNcEN5jCD1FLxPxCOgOd+"
    b"eHbfywVe4MXu3T2fzjnP75zn9/I+z3nO80JDCMH/T2KWEzw2Nvb06dO+vj6DwbCwsLBixQou"
    b"l7t9+/YDBw7k5+evXLky6sy0KH6t+fn5K1euNDY22my25OTkzMzMzZs3r1mzxuPxTExMmEym"
    b"/v5+AMjKylIqlcePH4+GF6IidrtdLpcDwLp1627cuGG328mQer0eE1q9enVbWxulWRBCFGh9"
    b"/foVP0lra2uEIVarVSaTAUBJSQklWpG+xLt371ZXV9fU1DQ0NPj65+bmdDrdyMiIw+GIiYlh"
    b"sVh8Pj8zM9MXY7PZ2Gy2y+UaHR1du3ZtJNNFROv+/fsKhaKhoaGmpoZw6nS6a9eueb1egUDA"
    b"4/EYDIbb7Z6amjIajb29vQUFBVKplMViYbDb7RYKhVqt1mazMRiM8LzC/p5v374FgObmZsIz"
    b"OjpaUFAgl8u/f/9OFtXa2qpQKPyc2dnZTCbT5XKFnTQMreHhYQC4efMm4VGr1fn5+ZOTk2FT"
    b"I4QWFxclEsn09DThYTKZ+/btWy4tgUCwceNGwmxubpZIJJEQIkSj0WRkZBDmwMAAALx+/Tp6"
    b"Wo8fPwaA8fFxbHZ3d4vF4qDIrq6ulpaWtra2kZGRwNHp6em9e/cS766uri7s4gk1nJ6eLpVK"
    b"sb64uCgSiQIxGo1mw4YNf+8gGu3IkSOBMIvF4vF4sO52u/0WKwVaFosFAGZmZrB5+fLlFy9e"
    b"+GE6OjoAoKioiFhq7e3tKSkpSUlJgQmHhoaGh4exfv78+bS0tGhoyWSyrKwsrM/MzBw+fNgP"
    b"4PF4AKC2tjYwNikp6cSJE37OgYGBiooKrJtMJlxiKNPatGnTpUuXsH7v3r1nz575ARobG8mW"
    b"iFqtptPpgbu1oKDg74kBHj58SI2WxWKJj4/XaDTYPH36tNVq9cPs37+/vLycNC9AZ2cn2ShC"
    b"SCwW5+bmko3+EbTGWq1Wp9OZnp6OTYfDwWQy/TCzs7OJiYkhCvXS0lKIUYFAoNPpyEaD05qf"
    b"nweApKQkbDqdzpgY/84sJiYGLy8yWbVqVYjRLVu2WK1WarT8HhRvaV8xGo39/f3btm0jy5ua"
    b"mlpVVRXoN5vNWAn9SwenFRcX52uigON8YmICACorK8ny1tbW6vX6QH9FRQVWFhYWKNPCK2lq"
    b"aiooSwDYsWMHg8F48uQJWd7bt2+Xl5f7OS0WC4/Hw/rg4CCbzaZGa/369QwGo6enB5vx8fF2"
    b"u90XkJiYWFRUdPToUa/XGxiuUqkMBgNuAH3l06dPO3fuxHp7e7tQKCSjRVq30tPT5XI51qur"
    b"qw0GQ9Aq0NPTE+jPzc0tLi4O9BcXF8/PzxOxIbpcUlrXr1+Pi4vDeldX18WLFwMxUqmUzWYv"
    b"LS35OnF/Njg46AdeXFwkTvqXL1/SaDSz2UyZFq4RQ0ND2MzLy/v586cfxuVyMRgMNps9OzuL"
    b"Pbj0BzaACCGVStXQ0ID10tJS326HAi2E0O7du4mWTavVlpWVBYXR6XRiCAAqKysDMXNzc0QD"
    b"4nA48NqKkhbeaEQLderUqXfv3hGj3759UygUKSkpAPDlyxfsVCgUAJCRkdHU1OT7csVisVar"
    b"xXp9fX2INR2eFkIoNjZWJpMR5q5du/BBKZFIAIDH49XX1//48cM3pLOzkygN3d3dCKGqqqoH"
    b"Dx7g0aWlJTqdXldXtyxajx49AgCn00kkLSkpOXToEJ1O7+/vDx179epVACgrK7t16xbhxK2p"
    b"1+tdFi2v15ucnHz27Flfp1Qq5fP5oQMRQvgkfvXq1T/mI2nRqNFCCH348AEATCaTr9NoNIpE"
    b"ojNnzqjVamJhIYTsdvvnz5/v3Llz8OBBoukjRC6XM5lMt9sddtKIrq98Pp/L5b5//97Pr9Pp"
    b"uru79Xq92WzG+4vD4aSlpWVnZ+fk5BB3VyyTk5McDqelpaWkpCTsjBF9g8CH7vPnzyMBk4lI"
    b"JOJyuRGCI/00gnd+tJSQSqUKWvrJJNKZXC4XjUZTKpXR0SIrs6T4yKH4Qvzx40eqnI4dO8Zm"
    b"symFUHsveXl5qamplEJwd9Tb20spihoth8NBo9HOnTsXeUh8fHzQe3ZoobyKcZkgDrjQUlhY"
    b"yOFwfv369a/TQgiVlpYymcywMPwAYc+ooBLlnk9ISBAKhSEAY2NjAEA0WFQlSlp9fX0A0NTU"
    b"RAbYunUrj8eLLjmKmhb6qxH1PRAJUSqVAOD7EfC/o4UQKiwsZLFYQXv5KMrbb6OFEIqNjc3J"
    b"ySHMmZkZAKiqqlpm2uXSGh8fBwDiXgQAe/bsWWZOtHxaCKE3b94AQEdHh1QqTUhImJub+1/Q"
    b"QghduHABt0mBn8Gik99DCyF08uRJtVr9u7JF88fdfyB/AsROR8G6/EH9AAAAAElFTkSuQmCC"
)

icon_kerf_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAIAAACRXR/mAAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAAAsTAAALEwEAmpwYAAAHxElEQVRYhe2Ya0xTaRrHT1s4p6cXqFAsbimFKlM6yaCQ"
    b"xRGF4GUSAXHMYhaYkLhdLGZHB8jQLNcEGQaclQWBgUYmURFB4hKVqVFqVkgTyzUCiojERG5C"
    b"y62EFmgLvZyzH0pYppT2tLD7YbP/T708z3N+ffue5/m/B0AxyGQyXblyhUgkSiQSLPEWKisr"
    b"JRKhhoZ67CkAxjij0Xj58mUymdzS0oK9OoIglZWVMAzfvVuLPcsBLDNZSkoKjebe3i7DmFJV"
    b"9TMEQbW1dxxiQlHUBcAsAoFw8+ZNHA539uzZlpaWI0fCAAAoLi56//691XitVvv8+XORqJrP"
    b"/zP2q5iFdyiaQCBUVVVRKNShoaH1fDwB3EZDQ+/PnIlNTr7oKBMAAA6s1nqCiwsIuhIIBPPb"
    b"nJyc7SKTk5MBAMXhcE5gObZa/zX9H8sR/Q9hEQguEsnz1VWdjRiFQvHmzRsCweFbal2ONjoU"
    b"Rdva2ry9vcPDjykUcqsB3d1dHI7/oUOHRkZGnKiPOtTl3717t7S0ZH49MvLx8OFQJpPZ2dmx"
    b"OQZBkLq6OiqVGh8fvxE8OflpYmJi97H0en1+fj4EgU1N/9j4cHl5KSkpCYbh+vp7a2trq6ur"
    b"Wq02OzsLgqCCggKj0bgRmZHxvYfHnvr6egRBdg1rbm4uMTEBhuHCwh/0ev3mrzQazaVLlyAI"
    b"YrPZvr6+LBaLSCSWl5ebTKbNYUqlks//EwSBubk5a2tru4AlkUhYLBaPx+vq6rQagCDIo0cP"
    b"U1NTcTjcjz8Wtre3b1eqoaHBy8srNPT3Q0NDzmNpNJrMzExXV9eLFy+q1WrbVXp6uvF4vN2w"
    b"8fHxkydPUqmUmpqbFiuKCWtg4E1QUNDevXvFYjGWDYERC0VRg8FQUnIdhuGvvz4rl1u/ka1g"
    b"GQyGiooKEokUExMzNTVp9zKOYpnV19cXFPQFk8nc7mf/Bksul0dHR5HJ5MrKCoPBgPEaTmCh"
    b"KLq8vPzdd1dAEExLS11eXraOZTKZfvmlhkqlnjhxYmJi3CIIQZC0tLT79xu2Y7WNpVKprl27"
    b"VlZWZi2xJyAgwMfHp7X1hSXWzMz0uXPnYBi+fv365n6zGSszM9PNzY3HC6ypqdFoNBix5ufn"
    b"i4qKPDw8GAzG7du3rEKr1eqUlBQQBIVC4crKyjqWWCxmMn8XFPRFX1+v1bQNTU1NCoVCNzc3"
    b"Pz8/kUik0azYwFIq5/Pz8+l0ure3d0lJyeLioo3KCII8fvxo3759wcGHXr9+jaIoAIJgenra"
    b"xqCwK4VCnp2d7e7uzuFwNpbWAmtsbNTDw4PD4ZSWlmKvPDk5GRMTQ6FQSkv/Djx9+hT7TNjQ"
    b"7OxMS8uzjbcWWGtrq8+ePdVqtY6WNRqNFRUVFArFGQexVW/fvqVSKU5wWNXg4CAORVEnLdFv"
    b"pdfrQRAEAGBwcLCgoMBkMm2NMf+teLx9k7dr7hQEQQRB7t2ri4yMnJiYgK2JSqViPAjZcY9S"
    b"qTQvLw8Atl3RyMjIn376GwAAKtViampaU1NTdnZ2Xl6eeeWclh0sNpsdHR299Y/W6XR1dXfn"
    b"5uajoqIBAJDJXiYnJ6Mo0NraGhERsROgdTmxJUdGRsLCwuh0+pMnT1ZXdQUFV0EQTEpKUqls"
    b"NSfsWlhYALbOI9sSi3+l0+lHjx4dHR39+PFjRES4p6dnQ0ODbaOCXS9e/NPf3x84fvz4+PgY"
    b"lgQEQaqrq0kkUlzcH5RK5cuXL/38/Ljczzo6trV+DslkMolE1WQy+auvTgFhYUc8PT2bmx/b"
    b"bqoLCwvffJNIJpMqKyu0Wm1eXi4EgXw+3yHXYEMKhSI2NhaG4Rs3yoxGI6DVaoVCoaura0bG"
    b"9zqd9X746tUrHi+Qw/Hv7u768OHDsWNH6XR6Y2OjE+NhqxAEaW5uNg/E/v4+84frW14sFjMY"
    b"jC+/PDw8PLw5x2QyiUQiEol0/nycUqm8c+f2nj00c2faORCKomq1+ttv/wJBUHp6+mZj8u87"
    b"cWxs7NSpUzQabePkpFKpEhISYBguL78xPT0dH/9HEolUXFyE8fRiVz09PVwul8VibR6vllgo"
    b"iur1+qtX811cXAQCQXu7jMvl7t+/v7OzQyqV+vr6HjhwoLu7a1eADAZDcXExkUg8fz5ubm5u"
    b"a4CVvtXb2xsYGIjH4wUCgVwuT0kRQBCUlZW11f05p/7+/oMHD3p5eYnFv263O623U7VaLZPJ"
    b"RkdHAwIOMJnMtrbWXQHS6/VlZWUkEik2NnZmZsZGpK0uPzw8zGaz2Wx2a+suYH369On06dNk"
    b"Mrm6usru+cXO8FlYWODz+Wajjd1nWghBkAcPHtDp9JCQECxHavtY5qJisdjHx4fH4znR0FWq"
    b"xQsXLoAgmJubg90nYh3V09OK+Ph4EASzsrJ0Oh3GLJlMxuVy/f39Hd0GDjgIvV5fVFQEw3BU"
    b"1Gm77RRBkNraO+7u7uHh4U48fHPY2AwMDISGhtJotFu3bm3nGmZnZxMS4iEIKiwstHj29J/C"
    b"QlFUp9MVFv5AJBLj4uIsnlMiCCKRSHx9fT//nNfV5Xzvdf7k09vbGxwczGAwGhvvm7viysqK"
    b"UJgBgqBAIFha2pGz2NGBTKvVZmb+FYKgxMREqVQaEhLMYDAePny4c2exC+fEjo4OLvczAADO"
    b"nImZmpraeUEURf8FcaHqfSGVp/MAAAAASUVORK5CYII="
)

icons8_finger_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAACLklEQVR4nO2ZTUtXQRjFf2Ybo7+FhlDoIlAkEBcJQQujPkDQoqXlN2jZIgJXgR9A1IXg"
    b"QtKKRANzY5Av7VoUiGFtFIIwLcgX0N3IwBGGi/69969znaF74IHLYe4zz+HMnbcLBQoEhxbg"
    b"DbAO/NZzM5GhHdgCTCIs10ZEmFbhb4FrinFx74gI2yq6weGuitskIhhFWj5YmEJIYDCFI4HB"
    b"FI4EBlM4EhjM/+LICPAH+Au8ApqIVIhJxE+gE5jQPs2KHARKZ1B7JiFTQKPifRmBC8B5AhbS"
    b"6HBNDt8HXAFuyCXLPdURwB7O7FAcS7x/pkKO4usc7kkZp1YTbYMRMgt8THCtTvteoF5ufRL3"
    b"3FPtqQrOgpKTp9bh74n7Qg7wuV5cVG47u3mH74XP5LWwFkJCceQc8Dh2Ry4AM04nH2IV8lrJ"
    b"14CHQFWZtnPA5wo5r0LuKvE/3fkeh8MKSct5FTKsxM9Stg9WyA8ltpu9qIXsKLH94KMWsnXI"
    b"nihKIYtKfDt2If1K/CJ2IXecA091zEKqnJmrK2YhFt1KvpzCFXupMF8h511ItUSkdaVS1Obx"
    b"C+9RBlcqxU318Q2PsMV/9+xKj/IP4Bld6mjFw03hZd1CGm1U8e3KwQI5dMx2PuuhbVJ57bkn"
    b"F9wC9tTpS6DmFJw4ELEBXCdHPHDE/NKFWgdwKeX7JbXvcYbTRoZt0KnPMF+def8kYYdTrk4k"
    b"Ycf2fWBUE8BuysLtBdySfi+c+MPeB/5NUJYk4pDZAAAAAElFTkSuQmCC"
)

icon_regular_star = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAAD5klEQVR4nO2ZaahNaxjHf8c5uAfXlEPGpMzDByGzW265fCDXUPcDMuSTWfKB4pshlClj"
    b"XVxdRd2MR9dMXeEDkumQFNec46Acw3G2Hv1Xve32OXvtY6119opfrdq969nP87zvWut9hhd+"
    b"4IsawFngjH7Hll+BhK6hxJg9zkT+JqY0BkqBMl2lGosds/QkCoGj+j2TGHJFzo8Bxur3NWJG"
    b"bzn+AqgN1AKeaawXMWKznF7ljK3W2CZiQj7wSk53ccY7aawEqEMMmCSH/0tx77zuTSQGnJOz"
    b"U1Lcm6p7Fu2zmg5AOfAW+DnF/XrAG03GXrWsZbmc3FaJzHbJLCNLyQMey8m+lcj1k8xToCZZ"
    b"yCg5eMuH7A3JjiQLOSjn5vmQnS/ZA1RDbCgA2gE9gcHAcGAcMB1YAHwCPkguHQWS/aT/Tpeu"
    b"4dLdU7YKZNsXE4A/gX3AceACcB24DxQrc034vPZmsDh7M9BbJl/uy7cL8nWffLc58NyHolLl"
    b"TfeAy4oVhXJmK7AGWAI0z2AiLfSfNdJhugql+7JsvZDtdP7ZHPhNaUNCe/x4oBvQFmgE5FL9"
    b"5MqXtvJtvBOPSjSHr7QHbjoZ6y9kL/2BJ/L1blI+95X6zs5jH+EMso9p2iTMx3/1lCp8hF50"
    b"tmtLlgStvBR+2Vha/gDe6U/28TWl+mgMnJAv74HJmSqwvfyBFNzTRxY1HYHb8uFxmtQn7RZ5"
    b"UYosox1NdIxwdlPbjtt8q0KruXdIYbne1TC7hjnAQuCzbO4JuqKc7UR5C151CZ6fgL+cRVuq"
    b"iYX6uK3d0zpA3abLayGVyFaoWGVXJIOW5wSF9/oWRVk9rpdRy5WCwl4j07mOCPHSmQEB6hwo"
    b"nVZ0RUILJ8EMMupbpH4t3a2IsG91KATdh6Pse+2SsTkh6J4r3TuJgIcyFkbK0l26HxEynWXo"
    b"ic9A1UlnI0d9bqk5Tq1htkJjpoxY9E334S5MKlM/Kr2xI4bK2C35UOuh/TJSWSrdRwc6Xpqx"
    b"XVe5c9hjMhUxWXJmKxRyneOCVKlJvla8zEn97VTXY5CadwklhFvUC06mlZOm+CqeMsVrdVp9"
    b"kMwQ4I5TJq+tIKnMVwT3ylVr7wxLIVfko/VaZRZL+QZnrKFW1nttrurYLR09gEtJ/bAmzv2N"
    b"Gl8Uwjw4LeVecTXOORd8p5XOJNLnqTR4Kx0v1XE0ftfYqaAnUUf1sr3/XYF/nNU8p5K0qlhr"
    b"9Jij74ieWJlewUDrnmHOynuNsWKdSgVR+ORIV7GTx3nNj1TfUJVZmdSitDyrJcHTzEmBvGtF"
    b"kAZOSun/OgcJm1GylZDtwBiiXasB0dFANs3298MXw0hXuTS4jKMAAAAASUVORK5CYII="
)

icon_crossing_star = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAIAAACRXR/mAAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAACbUlEQVRYhd2YO08CQRDHZw/LCw0tHb3PgoJeOv08+gV8"
    b"ND4a/QAajYaHET8CCT0JoaAlAZUooiWsxSXruXc7O8tsjLkJ1e3M3H/3tzO7h5BSwv+zwFsi"
    b"kQtEzls2X4n8WqZlKXy+OGZ6tQBgIecLOfeVzYMsDZwXjpmGqPD54siVlYqMzzG7EDVwXjiy"
    b"ZCGwmBwzCjEVGZ/j8rJywQrTAbHlZVnvj5wLJgtiuVw2DVUqFU5mIf7nrpdSCggEBCcnp5Js"
    b"UQjfJ25HR8cqBOIp6FkEBLs7u7hPdbvqlDAuANRAvd4gKqNPwClhrVb/eSJ/14vqzkjviXwo"
    b"zcnqaXqdvt/VMH56FAoFqyYAyOfzyCiyBCllqK6/gcj1ej1t9ObmFgBeXp8pst6nbwDQaj1p"
    b"z7vdrlrI1LXUIf6SnDYbOkGTP2mfIBlNQEulElETABSLxaRKXBMAgLE8EpVyd3c/HA6dWpEK"
    b"n0wmV1fXDiWMQEydpX2iPmKpJ89Czi8uL5zUaHZ2fuYwHzqLfr+verFTO41+g8GA/i4qRIjV"
    b"FHHbxt2c65foF7d4YxuPx0mH0WiEtyW7EVe13W4nwaUCNVEWEHQ6Hc8QTRQ0oNh54sJx+eu2"
    b"pobaJ2lG2luPjy3++5zCSRDx9Y9G9/f3pJQHB4dWT4o+lizkLEf8SRc1qwf+juQQcmPz2beQ"
    b"v4qaD03TV3Wj2cBjcbND1FbeqeKSzkSOJIha0jAMiTgWch6GYao+liyVbm11XU30YzalpI7s"
    b"YzZVvW1zY0tLazILRC2e07qcUlEr8fNrxm+nn18zorPzJwbfuJ8Y1uDlzFuX/3v7BikOKD82"
    b"lTxEAAAAAElFTkSuQmCC"
)

icon_polygon = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAACZUlEQVR4nO2aT0sVURjGf7qo0EVIEUUYiYFCFLRIsEViGXTzC1hgfYeSbFVt0o1pu3Kj"
    b"req61BbZoqCWldEHUFKvtJBKKPpH6Y0DT3AW/rn3zJxzz8j9wV3NnOd5z9yZOe/7noEqVaKh"
    b"G1gCZoGzKeoaLaNZAHIEwBgVPf8WQ0xkLsBEZn1PYjewbJmleWt1WRdpWV7eGJTRS48ez+Ux"
    b"4MvgIPAdWAPafZkAJ+XxEzjkw+ChrtQj/PNYXuNpCx8HVoHfQDP+OQz8kueJNIWf6QoNEY67"
    b"8pxOS7BTgl+APYSjAfgk73NJxWqBGYldJTzX5P1esThzRUIfgJ2EZ4fWKxPDZVeRXcCCRHqo"
    b"HBcVg8nv6lwEbkjgXdK/NSE1wGvF0u/yoH3W4DNUntOKZQXYW87Aexo4STxMKaaRUgc0aTH6"
    b"CxwlHlqAP1qUj5QyYEIzv098PFBs+a1ObFPC9g3YT3zsA74qxlObnfhCM75JvNxSjK/WO3hB"
    b"72lzwkegnnipV4zF9er7Quh6OSGFjeLN8kQW7AM562DWbq3zm9XL5oGKldul9A3s1+8B4n79"
    b"tm91cl4zNotPbIwqNlPTZzZFaS03RUGJWVGJWiw8UUzDrml8mt1EVzqsNL7svkF/RIXVG8Vy"
    b"3bXUnZeAKTcrxSVrzXAqdVHBH0vzoTeJkLml3krItGZC05dWO8hu0Dk9aAlosF44iRt0/5mW"
    b"oGljhmJYnk/TFD2mBTJUE7vJVxMbtfhLTg8SkpfXWJY3etrk8QNo9GUyEHDr7U6ozdC5LG+G"
    b"bpvt6W31wUBOk/H1CcfiRnV4lSqE5x+0Tyg887i34gAAAABJRU5ErkJggg=="
)

node_break = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABcAAAAZAQMAAADg7ieTAAAABlBMVEUAAAD///+l2Z/dAAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAOElEQVQImWP4//8fw39GIK6FYIYaBjgbLA6Sf4+EGaG4"
    b"GYiPQ8Qa/jEx7Pv3C4zt/v2As0HiQP0AnIQ8UXzwP+sAAAAASUVORK5CYII="
)

node_curve = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAAARklEQVQImWP4//9/AwOUOAgi7gKJP7JA4iGIdR4kJg+U"
    b"/VcPIkDq/oCInyDiN4j4DCK+w4nnIOI9iGgGEbtRiWYk2/43AADobVHMAT+avQAAAABJRU5E"
    b"rkJggg=="
)

node_delete = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAKUlEQVQImWP4//9/AwM24g+DPDKBUx0SMakeSOyvh3FB"
    b"LDBAE4OoA3IBbltJOc3s08cAAAAASUVORK5CYII="
)

node_join = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAPklEQVQImWP4//9/A8OD/80NDO/+74YSff93IHPBsv+/"
    b"/0chGkDEQRDxGC72H04wgIg6GNFQx4DMhcgC1QEARo5M+gzPuwgAAAAASUVORK5CYII="
)

node_line = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAAARElEQVQImWP4//9/A8P//wdAxD0sRAOIsAcS/+qBxB+Q"
    b"4p8g4jOIeA4izoOI+SDCHkj8qwcSf0CGNoKIvViIRoiV/xsA49JQrrbQItQAAAAASUVORK5C"
    b"YII="
)

node_symmetric = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZAQMAAAD+JxcgAAAABlBMVEUAAAD///+l2Z/dAAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAAAV0lEQVQImV3NqxGAMBRE0R2qQoXS2ApICVDJowRKQEYi"
    b"YsIAWX6DIObIeyGJeGgllDTKwKjMl147MesgJq3Eoo0IjES0QCTzROdqYnAV4S1dZbvz/B5/"
    b"TrOwSVb5BTbFAAAAAElFTkSuQmCC"
)

node_smooth = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAIgSURBVEhLY/wPBAw0BkxQmqZg+FhC"
    b"VJx8+fyZ4fKVK1AeBEhKSDAoKCpCefgBUZZcvHCBITo6CsqDgJjYWIaKikooDz8gKrjevX8P"
    b"ZSHAh3fvGX7//g3l4Qc4ffLz50+G9evWMSxftpTh7r17UFFUwM3NzeDm6saQlJLMoKioBBXF"
    b"BFgtOX/+HENNdRXDw4ePwHwZGVmGJ08eg9kwICQkxPDj+3eGb0DMxMTEkJySwpCdncPAwsIC"
    b"VYEAGJZs3bqFoaaqiuH3nz8Mjg6ODHkFBWADFy1cCFUBAdo6Ogx2dnYMq1etYpg6dQrDly9f"
    b"GKysbRgmTpzIwMnJCVUFBSBLYODgwYP/dXV1/usB8do1a6CihMGLF8//h4YE/9fW0vyfmZn5"
    b"/++fP1AZCIBb8ubNm/8W5mb/dbS1/m/ftg0qSjz4/Pnz/4AAf7BF8+bOhYpCANyS2tpqsIKO"
    b"jnaoCOng/v37/40MDf4bGxmCHQ0DYEtAAoYG+mCfAMMWLEEu6O7qAjt22rSpUJH//8H55MD+"
    b"/Qy/fv1i8A8IACdLSkBkZCSY3rVzJ5gGAWZ+Pr6G7du3MgB9wyAsJMzwB5iq1DU0oNKkg/Xr"
    b"1zFcOHeO4dWrVwzfvn4DZofzDIwgr0HlwcDZ2Ylh4qQpUB7pwNfHh+H+fUTmBYXMaH1CEmA8"
    b"duwYSpyAihB1dXUoj3QAqhZA5RkMMDMzEVefUApGI54EwMAAANLW9DiEznjCAAAAAElFTkSu"
    b"QmCC"
)

node_smooth_all = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAACs0lEQVR4nO2YO2hUQRSGj4r4loh2Rldws3P+/+zdK2xhSB+idop2FqJgFUEt1FJERBtt"
    b"VKy0UvCBz0IR0UKsTBoRBEVREcEHiEh8JBrlZu+uIbmYx97sA+eDKbaY/86/c86cMyPi8Xg8"
    b"Ho/nP6RYLM404PDIETjnpJlob22dY8TvkQPAOmkmzCxMMkJq9yaRGdLIFAqFeaa606DPkkwM"
    b"Gx8NOBoE2VZpNACsJfR1ZbHQH0b8SjDxrbI70D5Sd4vIdGkESN1rxGApdPAmCp8gCBYRuEui"
    b"Z/gw0w1mroPE5coc4FImk5ldVxMG7Bm2C6edcwvGPddcF6HvYjM36pY7Zq6rEj7Agclp2Mpy"
    b"SJJ6UGpNsVicS+JFbOJMNVr5fK5A4iuh/aqal1pCanc5J7LZ7MIU9PbF4XkxnRWOEwJPSka4"
    b"Q1LaYSM+EDoQtrUtlVpAMhsfn/1hGLakp4sTkW4e2CpTjVEvEHgQn1Sfo9+q2l6tLum2EHhY"
    b"0tWnQ9+h7qpWN3DORVojhyS3HdxYvREcS2hnzlera+Y6ktbsjYyF35HJh9boxEkr2UsHifbF"
    b"CX81tWSH3owNDEZ1aijZpxoC14eOYNXOtDTzwOa4eD+SWkHq9rjtOZeaJnAv1jyUlubYHyXn"
    b"E/opqvCBc0G1ennVzrh4DwDISJ2uBr3R3X+yOrlcbolRX8Y16aTU5QWG6C0nfTabnTVRjTAM"
    b"WyodCPRVmq3UhDCzZUa8jRdy3zm3YrxzA+cCoz6O534huUrqCYA2As//LkiPRIai4jnqCg3s"
    b"V9WcAcfj94LolHoPYLU0Aqq62ICzw4pZdM///q9HDStdnW+RXC6NRqlC65Xyv53cvOKnUe+Q"
    b"XCMi06SRiR43DHotwURPtHvSTBj0VIKR29Js5FXXJzyQb6v3ujwej8fj8Uid+AMS4JbuhXD/"
    b"gAAAAABJRU5ErkJggg=="
)

node_close = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAsTAAALEwEAmpwY"
    b"AAACpklEQVR4nO2YSWsVQRRGjwlOcWM0YCDguFHzUKMrccClszEgiCKSgBiCYOJGI7qX4MYg"
    b"auLsD3DnhD5F/AGaxAHEZKFunDfqwiQ+KbgNl6K7051+TbpNHajV++7te19VV9dX4HA4HA7H"
    b"xDAFOA5cAGrJMTuBkoy3QB05Za1qJPfNHMtzM3OBrUCLvCOvIjSzAOgQfdhoAbbIM1KhEjgI"
    b"PAFGrML9xh0r/k2EGD2GgcfAAaCiXE1sAgZiFvLUyvExZnxJjT5gY9Imjsi/Yyd/DzwEbslS"
    b"0r99ApZbeVYD3UBPyDC5TM4PATPUNt4mTvkkuww0KM1ea6mZJgokpwG44rOMO+MmagL+qgTv"
    b"gBWWZpU1W6aJesrLSmBQPWMUaIwaPAf4oYL7A3aRfSk34VFjvaPfgGoicFYFfQUWBuhmAL3A"
    b"bWAp6bIY+K7q6horYBbwWwUcJTt0qLp+AVVh4t1K/BmYRnaYLivEq29XmLhXCa+RPW6o+i6F"
    b"CR8o4SGyx2FV3/0w4Usl3Eb22GHtpoH0K+F2su2B+ibF0upRwutkj5uqvotRt98vsuXlcvut"
    b"ko+NJ24nm270JzBzrIAu61yzKOUClwH3gPPA1ADNEuuIciZK4moraEAObmlQLwdO71l7fDQ1"
    b"1mfBLK/ZUR/QKEdmL3hQju1pNmEsQcHHlwxZx3izBcei0zI1xuRcFbeXlILVxIiYNO/ib40c"
    b"kWxjZS4oxkVbgNU1drQo9jTMvnZbjtJvJkpil02uYoC//wO0kpANwIsElwemMM2zmPHPgXWU"
    b"iQq5mikGzFDYeG3luhshZhh4BOwv53WQnxXeDDQDp2UrDBongPlWfJ3PzcuQ5GqW3JGsbBao"
    b"lZnSzZwkp/jNzHr+k2aayDHzgHPyjlROdDEOh8PhmJz8A+PVbUCLkfVDAAAAAElFTkSuQmCC"
)


icons8_centerh_50 = VectorIcon(
    "M 23.4815320307,48.8124690662 C 23.1957961233,48.0678532274 23.0830594543,36.8929321171 23.2310060995,23.9793110433 C 23.4611043587,3.89503184947 23.716895111,0.5 25,0.5 C 26.2923777019,0.5 26.5,3.87962962963 26.5,24.9166666667 C 26.5,43.5556297706 26.204337579,49.4318874737 25.2505259312,49.7498246896 C 24.5633151933,49.9788949356 23.7672679381,49.557084905 23.4815320307,48.8124690662 Z M 5.2,31.8 C 3.49433315332,30.0943331533 3.64738544542,19.537533519 5.3988551522,18.083942768 C 6.77561936461,16.9413299568 10.1467515776,18.574363024 16.5,23.4615237926 L 18.5,25 L 16.5,26.5384762074 C 14.2357722318,28.2802064821 7.04496406527,33 6.65559094272,33 C 6.51501592422,33 5.86,32.46 5.2,31.8 Z M 37,29.6214380251 C 33.975,27.8650464301 31.5,25.7884692723 31.5,25.0068221188 C 31.5,24.2251749654 34.1464588219,22.0977065982 37.3810196041,20.2791146362 C 44.7105737226,16.1581631062 46,16.8528197296 46,24.9224447154 C 46,29.8955171137 44.7797216097,33.19853933 43.05,32.9074386443 C 42.7475,32.8565298987 40.025,31.37782962 37,29.6214380251 Z M 11.4529469789,26.8394849797 C 12.8538261405,26.2012017185 14,25.3734334777 14,25 C 14,24.3913047117 9.57843532493,22 8.45294697887,22 C 8.20382614049,22 8,23.35 8,25 C 8,28.4092552194 8.00353888442,28.4111404857 11.4529469789,26.8394849797 Z M 42,25 C 42,21.5907447806 41.9964611156,21.5888595143 38.5470530211,23.1605150203 C 35.4123272686,24.5887916561 35.3474130241,25.3796404509 38.25,26.779505359 C 41.6491195451,28.4188388948 42,28.2523339214 42,25 Z"
)

icons8_cog_50 = VectorIcon(
    "M 40.25 0 C 39.902344 -0.0117188 39.566406 0.15625 39.375 0.46875 L 37.78125 3.0625 C 37.242188 3.019531 36.722656 3.015625 36.1875 3.0625 L 34.5625 0.5 C 34.300781 0.0859375 33.761719 -0.0625 33.3125 0.125 L 30.5 1.3125 C 30.054688 1.5 29.796875 1.996094 29.90625 2.46875 L 30.59375 5.4375 C 30.179688 5.792969 29.789063 6.175781 29.4375 6.59375 L 26.46875 5.90625 C 25.984375 5.796875 25.527344 6.078125 25.34375 6.53125 L 24.1875 9.375 C 24.003906 9.824219 24.152344 10.335938 24.5625 10.59375 L 27.125 12.1875 C 27.082031 12.730469 27.105469 13.300781 27.15625 13.84375 L 24.59375 15.4375 C 24.179688 15.699219 24.027344 16.238281 24.21875 16.6875 L 25.40625 19.5 C 25.59375 19.945313 26.058594 20.207031 26.53125 20.09375 L 29.5 19.4375 C 29.851563 19.847656 30.238281 20.214844 30.65625 20.5625 L 30 23.53125 C 29.894531 24.007813 30.140625 24.503906 30.59375 24.6875 L 33.4375 25.84375 C 33.558594 25.894531 33.6875 25.90625 33.8125 25.90625 C 34.148438 25.90625 34.46875 25.734375 34.65625 25.4375 L 36.3125 22.84375 C 36.855469 22.882813 37.402344 22.863281 37.9375 22.8125 L 39.59375 25.40625 C 39.859375 25.8125 40.367188 25.96875 40.8125 25.78125 L 43.65625 24.59375 C 44.109375 24.402344 44.332031 23.914063 44.21875 23.4375 L 43.5 20.46875 C 43.902344 20.121094 44.28125 19.722656 44.625 19.3125 L 47.625 19.96875 C 48.109375 20.074219 48.597656 19.824219 48.78125 19.375 L 49.9375 16.53125 C 50.121094 16.074219 49.949219 15.535156 49.53125 15.28125 L 46.90625 13.6875 C 46.945313 13.15625 46.953125 12.625 46.90625 12.09375 L 49.46875 10.40625 C 49.875 10.144531 50.0625 9.632813 49.875 9.1875 L 48.65625 6.375 C 48.46875 5.925781 47.984375 5.667969 47.5 5.78125 L 44.53125 6.5 C 44.179688 6.089844 43.820313 5.722656 43.40625 5.375 L 44.03125 2.375 C 44.132813 1.898438 43.886719 1.402344 43.4375 1.21875 L 40.59375 0.0625 C 40.480469 0.015625 40.367188 0.00390625 40.25 0 Z M 37 8.875 C 37.53125 8.867188 38.070313 8.945313 38.59375 9.15625 C 40.6875 10.007813 41.695313 12.40625 40.84375 14.5 C 39.992188 16.59375 37.59375 17.601563 35.5 16.75 C 33.40625 15.898438 32.398438 13.5 33.25 11.40625 C 33.890625 9.835938 35.40625 8.898438 37 8.875 Z M 14.53125 17 C 14.042969 17 13.609375 17.359375 13.53125 17.84375 L 12.90625 21.78125 C 12.164063 22.007813 11.429688 22.296875 10.75 22.65625 L 7.5 20.34375 C 7.101563 20.058594 6.566406 20.09375 6.21875 20.4375 L 3.46875 23.1875 C 3.125 23.53125 3.097656 24.070313 3.375 24.46875 L 5.65625 27.75 C 5.289063 28.4375 4.980469 29.160156 4.75 29.90625 L 0.84375 30.53125 C 0.359375 30.613281 0 31.042969 0 31.53125 L 0 35.40625 C 0 35.890625 0.335938 36.320313 0.8125 36.40625 L 4.75 37.09375 C 4.980469 37.839844 5.289063 38.5625 5.65625 39.25 L 3.34375 42.5 C 3.058594 42.898438 3.089844 43.433594 3.4375 43.78125 L 6.1875 46.53125 C 6.53125 46.875 7.070313 46.902344 7.46875 46.625 L 10.75 44.34375 C 11.433594 44.707031 12.132813 44.992188 12.875 45.21875 L 13.53125 49.15625 C 13.609375 49.636719 14.042969 50 14.53125 50 L 18.40625 50 C 18.890625 50 19.320313 49.664063 19.40625 49.1875 L 20.09375 45.1875 C 20.835938 44.957031 21.539063 44.675781 22.21875 44.3125 L 25.53125 46.625 C 25.929688 46.902344 26.46875 46.875 26.8125 46.53125 L 29.5625 43.78125 C 29.910156 43.433594 29.941406 42.867188 29.65625 42.46875 L 27.3125 39.21875 C 27.671875 38.539063 27.960938 37.824219 28.1875 37.09375 L 32.1875 36.40625 C 32.667969 36.320313 33 35.890625 33 35.40625 L 33 31.53125 C 33 31.042969 32.640625 30.640625 32.15625 30.5625 L 28.1875 29.90625 C 27.960938 29.175781 27.671875 28.460938 27.3125 27.78125 L 29.625 24.46875 C 29.902344 24.070313 29.875 23.53125 29.53125 23.1875 L 26.78125 20.4375 C 26.433594 20.089844 25.898438 20.058594 25.5 20.34375 L 22.21875 22.6875 C 21.535156 22.324219 20.832031 22.039063 20.09375 21.8125 L 19.40625 17.84375 C 19.324219 17.363281 18.890625 17 18.40625 17 Z M 16.5 28.34375 C 19.355469 28.34375 21.65625 30.644531 21.65625 33.5 C 21.65625 36.355469 19.351563 38.65625 16.5 38.65625 C 13.648438 38.65625 11.34375 36.355469 11.34375 33.5 C 11.34375 30.644531 13.644531 28.34375 16.5 28.34375 Z"
)

icons8_comments_50 = VectorIcon(
    "M 3 6 L 3 26 L 12.585938 26 L 16 29.414063 L 19.414063 26 L 29 26 L 29 6 Z M 5 8 L 27 8 L 27 24 L 18.585938 24 L 16 26.585938 L 13.414063 24 L 5 24 Z M 9 11 L 9 13 L 23 13 L 23 11 Z M 9 15 L 9 17 L 23 17 L 23 15 Z M 9 19 L 9 21 L 19 21 L 19 19 Z"
)

icons8_computer_support_50 = VectorIcon(
    "M 7 8 C 4.757 8 3 9.757 3 12 L 3 34 C 3 34.738 3.2050625 35.413 3.5390625 36 L 1 36 C 0.447 36 0 36.447 0 37 C 0 39.757 2.243 42 5 42 L 23.896484 42 L 25.896484 40 L 5 40 C 3.696 40 2.584875 39.164 2.171875 38 L 7 38 L 27.896484 38 L 29.896484 36 L 7 36 C 5.859 36 5 35.141 5 34 L 5 12 C 5 10.859 5.859 10 7 10 L 43 10 C 44.141 10 45 10.859 45 12 L 45 22.451172 C 45.705 22.701172 46.374 23.023156 47 23.410156 L 47 12 C 47 9.757 45.243 8 43 8 L 7 8 z M 41.5 24 C 36.81752 24 33 27.81752 33 32.5 C 33 33.484227 33.290881 34.378694 33.599609 35.255859 L 25.064453 43.789062 C 23.652066 45.20145 23.652066 47.521207 25.064453 48.933594 C 26.47684 50.345981 28.79855 50.345981 30.210938 48.933594 L 38.742188 40.400391 C 39.620086 40.709768 40.51563 41 41.5 41 C 46.18248 41 50 37.18248 50 32.5 C 50 31.568566 49.845983 30.67281 49.570312 29.837891 L 49.074219 28.335938 L 47.929688 29.429688 L 43.267578 33.882812 L 40.810547 33.189453 L 40.117188 30.732422 L 45.664062 24.923828 L 44.160156 24.429688 C 43.3262 24.155463 42.431434 24 41.5 24 z M 41.5 26 C 41.611788 26 41.710057 26.045071 41.820312 26.050781 L 37.882812 30.175781 L 39.189453 34.810547 L 43.822266 36.117188 L 47.947266 32.177734 C 47.95306 32.288755 48 32.387457 48 32.5 C 48 36.10152 45.10152 39 41.5 39 C 40.542813 39 39.642068 38.788477 38.818359 38.414062 L 38.1875 38.126953 L 28.794922 47.519531 C 28.147309 48.167144 27.126129 48.167144 26.478516 47.519531 C 25.830902 46.871918 25.830902 45.850738 26.478516 45.203125 L 35.871094 35.8125 L 35.583984 35.181641 C 35.21045 34.35882 35 33.457187 35 32.5 C 35 28.89848 37.89848 26 41.5 26 z"
)

icons8_connected_50 = VectorIcon(
    "M 42.470703 3.9863281 A 1.50015 1.50015 0 0 0 41.439453 4.4394531 L 36.541016 9.3359375 C 34.254638 7.6221223 31.461881 6.8744981 28.753906 7.234375 A 1.50015 1.50015 0 1 0 29.148438 10.207031 C 31.419618 9.9052025 33.783172 10.625916 35.546875 12.357422 A 1.50015 1.50015 0 0 0 35.650391 12.460938 C 38.608211 15.481642 38.60254 20.274411 35.605469 23.271484 L 32.5 26.378906 L 21.621094 15.5 L 24.728516 12.394531 A 1.5012209 1.5012209 0 0 0 22.605469 10.271484 L 19.5 13.378906 L 18.560547 12.439453 A 1.50015 1.50015 0 1 0 16.439453 14.560547 L 18.265625 16.386719 A 1.50015 1.50015 0 0 0 18.611328 16.732422 L 31.265625 29.386719 A 1.50015 1.50015 0 0 0 31.611328 29.732422 L 33.439453 31.560547 A 1.50015 1.50015 0 1 0 35.560547 29.439453 L 34.621094 28.5 L 37.728516 25.394531 C 41.515681 21.607366 41.677294 15.729393 38.574219 11.548828 L 43.560547 6.5605469 A 1.50015 1.50015 0 0 0 42.470703 3.9863281 z M 13.484375 15.984375 A 1.50015 1.50015 0 0 0 12.439453 18.560547 L 13.378906 19.5 L 10.271484 22.605469 C 6.4843192 26.392634 6.3227056 32.270607 9.4257812 36.451172 L 4.4394531 41.439453 A 1.50015 1.50015 0 1 0 6.5605469 43.560547 L 11.542969 38.580078 C 15.593418 41.589531 21.232231 41.53733 25.033203 38.070312 A 1.50015 1.50015 0 1 0 23.011719 35.855469 C 20.007171 38.596036 15.400503 38.522732 12.464844 35.654297 A 1.50015 1.50015 0 0 0 12.349609 35.539062 C 9.3917898 32.518358 9.3974578 27.725589 12.394531 24.728516 L 15.5 21.621094 L 29.439453 35.560547 A 1.50015 1.50015 0 1 0 31.560547 33.439453 L 16.734375 18.613281 A 1.50015 1.50015 0 0 0 16.388672 18.267578 L 14.560547 16.439453 A 1.50015 1.50015 0 0 0 13.484375 15.984375 z"
)

icons8_console_50 = VectorIcon(
    "M 2.84375 3 C 1.285156 3 0 4.285156 0 5.84375 L 0 10.8125 C -0.00390625 10.855469 -0.00390625 10.894531 0 10.9375 L 0 46 C 0 46.550781 0.449219 47 1 47 L 49 47 C 49.550781 47 50 46.550781 50 46 L 50 11 C 50 10.96875 50 10.9375 50 10.90625 L 50 5.84375 C 50 4.285156 48.714844 3 47.15625 3 Z M 2.84375 5 L 47.15625 5 C 47.636719 5 48 5.363281 48 5.84375 L 48 10 L 2 10 L 2 5.84375 C 2 5.363281 2.363281 5 2.84375 5 Z M 2 12 L 48 12 L 48 45 L 2 45 Z M 14.90625 19.9375 C 14.527344 19.996094 14.214844 20.265625 14.101563 20.628906 C 13.988281 20.996094 14.09375 21.394531 14.375 21.65625 L 19.59375 27.03125 L 14.21875 32.25 C 13.820313 32.636719 13.816406 33.273438 14.203125 33.671875 C 14.589844 34.070313 15.226563 34.074219 15.625 33.6875 L 21.6875 27.75 L 22.40625 27.0625 L 21.71875 26.34375 L 15.78125 20.25 C 15.601563 20.058594 15.355469 19.949219 15.09375 19.9375 C 15.03125 19.929688 14.96875 19.929688 14.90625 19.9375 Z M 22.8125 32 C 22.261719 32.050781 21.855469 32.542969 21.90625 33.09375 C 21.957031 33.644531 22.449219 34.050781 23 34 L 36 34 C 36.359375 34.003906 36.695313 33.816406 36.878906 33.503906 C 37.058594 33.191406 37.058594 32.808594 36.878906 32.496094 C 36.695313 32.183594 36.359375 31.996094 36 32 L 23 32 C 22.96875 32 22.9375 32 22.90625 32 C 22.875 32 22.84375 32 22.8125 32 Z"
)

icons8_curly_brackets_50 = VectorIcon(
    "M 9.5703125 4 C 5.9553125 4 4.4385 5.3040312 4.4375 8.4570312 L 4.4375 10.648438 C 4.4375 12.498437 3.9412656 13.115234 2.4472656 13.115234 L 2.4472656 16.398438 C 3.9402656 16.398437 4.4375 17.014563 4.4375 18.851562 L 4.4375 21.435547 C 4.4375 24.660547 5.9673125 26 9.5703125 26 L 10.816406 26 L 10.816406 23.404297 L 10.283203 23.404297 C 8.3622031 23.404297 7.7460938 22.835328 7.7460938 20.986328 L 7.7460938 17.904297 C 7.7460938 16.091297 6.8912969 15.024141 5.2792969 14.869141 L 5.2792969 14.65625 C 6.9632969 14.50225 7.7460938 13.578656 7.7460938 11.847656 L 7.7460938 9.0371094 C 7.7460938 7.1761094 8.3512031 6.6074219 10.283203 6.6074219 L 10.816406 6.6074219 L 10.816406 4 L 9.5703125 4 z M 19.183594 4 L 19.183594 6.6074219 L 19.716797 6.6074219 C 21.648797 6.6074219 22.253906 7.1761094 22.253906 9.0371094 L 22.253906 11.847656 C 22.253906 13.577656 23.037703 14.50225 24.720703 14.65625 L 24.720703 14.871094 C 23.107703 15.025094 22.253906 16.090297 22.253906 17.904297 L 22.253906 20.986328 C 22.253906 22.835328 21.636797 23.404297 19.716797 23.404297 L 19.183594 23.404297 L 19.183594 26.001953 L 20.429688 26.001953 C 24.033688 26.001953 25.5625 24.6615 25.5625 21.4375 L 25.5625 18.853516 C 25.5625 17.015516 26.058734 16.398438 27.552734 16.398438 L 27.552734 13.115234 C 26.059734 13.115234 25.5625 12.499391 25.5625 10.650391 L 25.5625 8.4570312 C 25.5625 5.3040312 24.044687 4 20.429688 4 L 19.183594 4 z"
)

icons8_emergency_stop_button_50 = VectorIcon(
    stroke="M33.1,40.2c-2.7,1.5-5.8,2.4-9.1,2.4C13.7,42.6,5.4,34.3,5.4,24c0-2.9,0.7-5.6,1.8-8.1 M13.7,8.5c2.9-2,6.5-3.1,10.3-3.1c10.3,0,18.6,8.3,18.6,18.6c0,2.8-0.6,5.4-1.7,7.7 M19.3,15.1c1.4-0.7,3-1.2,4.7-1.2c3.4,0,6.4,1.7,8.2,4.2 M18.4,32.5c-2.8-1.8-4.6-4.9-4.6-8.5c0-1.5,0.3-2.9,0.9-4.2 M34,25.7c-0.8,4.8-5,8.4-10,8.4",
    fill="M30.5,21.4l4.2,0.7c0.6,0.1,1.2-0.4,1.2-1v-4.2c0-0.8-1-1.3-1.6-0.8L30,19.7C29.3,20.2,29.6,21.3,30.5,21.4zM24.4,30.7l-2.7,3.2c-0.4,0.5-0.3,1.2,0.3,1.5l3.6,2.1c0.7,0.4,1.6-0.2,1.5-1l-0.9-5.3C26,30.4,25,30.1,24.4,30.7zM18.2,22L16.6,18c-0.2-0.6-0.9-0.8-1.4-0.5l-3.6,2.1c-0.7,0.4-0.6,1.5,0.2,1.8l5.1,1.8C17.7,23.6,18.5,22.8,18.2,22z",
)

icons8_laptop_settings_50 = VectorIcon(
    "M 37 0 L 36.400391 3.1992188 C 36.100391 3.2992188 35.700391 3.3996094 35.400391 3.5996094 L 32.699219 1.6992188 L 29.699219 4.6992188 L 31.5 7.1992188 C 31.4 7.5992188 31.199609 7.9007812 31.099609 8.3007812 L 28 8.8007812 L 28 13 L 31.099609 13.5 C 31.199609 13.8 31.3 14.2 31.5 14.5 L 29.699219 17.199219 L 32.699219 20.199219 L 35.400391 18.400391 C 35.800391 18.600391 36.1 18.700781 36.5 18.800781 L 37 22 L 41.099609 22 L 41.699219 18.900391 C 41.999219 18.800391 42.299219 18.7 42.699219 18.5 L 45.400391 20.300781 L 48.400391 17.300781 L 46.5 14.699219 C 46.7 14.299219 46.800391 13.899609 46.900391 13.599609 L 50 13 L 50 8.8007812 L 46.800781 8.3007812 C 46.700781 8.0007812 46.600391 7.6007812 46.400391 7.3007812 L 48.199219 4.5996094 L 45.300781 1.6992188 L 42.699219 3.5996094 C 42.399219 3.3996094 41.999219 3.2992188 41.699219 3.1992188 L 41.199219 0 L 37 0 z M 38.699219 2 L 39.5 2 L 39.900391 4.6992188 L 40.5 4.9003906 C 41.1 5.1003906 41.699219 5.2996094 42.199219 5.5996094 L 42.800781 6 L 45.099609 4.3007812 L 45.599609 4.8007812 L 44 7.0996094 L 44.300781 7.5996094 C 44.600781 8.1996094 44.8 8.8003906 45 9.4003906 L 45.199219 10 L 48 10.400391 L 48 11.199219 L 45.300781 11.800781 L 45.099609 12.400391 C 44.899609 13.000391 44.700391 13.599609 44.400391 14.099609 L 44 14.699219 L 45.699219 17 L 45.099609 17.599609 L 42.800781 16 L 42.300781 16.300781 C 41.700781 16.600781 41.1 16.8 40.5 17 L 39.900391 17.199219 L 39.400391 20 L 38.599609 20 L 38.199219 17.300781 L 37.599609 17.099609 C 36.999609 16.899609 36.400391 16.700391 35.900391 16.400391 L 35.300781 16 L 32.900391 17.599609 L 32.300781 17 L 33.900391 14.699219 L 33.599609 14.199219 C 33.299609 13.599219 33.100391 12.900391 32.900391 12.400391 L 32.699219 11.800781 L 30 11.300781 L 30 10.5 L 32.800781 10 L 32.900391 9.3007812 C 33.000391 8.8007812 33.2 8.1992188 33.5 7.6992188 L 33.900391 7.1992188 L 32.300781 4.9003906 L 32.900391 4.3007812 L 35.199219 5.9003906 L 35.699219 5.6992188 C 36.399219 5.3992188 36.999609 5.1003906 37.599609 4.9003906 L 38.199219 4.8007812 L 38.699219 2 z M 39 6.9003906 C 36.8 6.9003906 35 8.7003906 35 10.900391 C 35 13.100391 36.8 14.900391 39 14.900391 C 41.2 14.900391 43 13.200391 43 10.900391 C 43 8.7003906 41.2 6.9003906 39 6.9003906 z M 8 8 C 5.794 8 4 9.794 4 12 L 4 34 C 4 34.732221 4.2118795 35.409099 4.5566406 36 L 2 36 A 1.0001 1.0001 0 0 0 1 37 C 1 39.749516 3.2504839 42 6 42 L 44 42 C 46.749516 42 49 39.749516 49 37 A 1.0001 1.0001 0 0 0 48 36 L 45.443359 36 C 45.788121 35.409099 46 34.732221 46 34 L 46 21.943359 C 45.367 22.349359 44.702 22.708 44 23 L 44 34 C 44 35.103 43.103 36 42 36 L 8 36 C 6.897 36 6 35.103 6 34 L 6 12 C 6 10.897 6.897 10 8 10 L 26.050781 10 C 26.102781 9.317 26.208328 8.65 26.361328 8 L 8 8 z M 39 9 C 40.1 9 41 9.8 41 11 C 41 12.1 40.1 13 39 13 C 37.9 13 37 12.1 37 11 C 37 9.9 37.9 9 39 9 z M 3.4121094 38 L 8 38 L 42 38 L 46.587891 38 C 46.150803 39.112465 45.275852 40 44 40 L 6 40 C 4.7241482 40 3.8491966 39.112465 3.4121094 38 z"
)

icons8_laser_beam = VectorIcon(
    "M 24.90625 -0.03125 C 24.863281 -0.0234375 24.820313 -0.0117188 24.78125 0 C 24.316406 0.105469 23.988281 0.523438 24 1 L 24 27.9375 C 24 28.023438 24.011719 28.105469 24.03125 28.1875 C 22.859375 28.59375 22 29.6875 22 31 C 22 32.65625 23.34375 34 25 34 C 26.65625 34 28 32.65625 28 31 C 28 29.6875 27.140625 28.59375 25.96875 28.1875 C 25.988281 28.105469 26 28.023438 26 27.9375 L 26 1 C 26.011719 0.710938 25.894531 0.433594 25.6875 0.238281 C 25.476563 0.0390625 25.191406 -0.0585938 24.90625 -0.03125 Z M 35.125 12.15625 C 34.832031 12.210938 34.582031 12.394531 34.4375 12.65625 L 27.125 25.3125 C 26.898438 25.621094 26.867188 26.03125 27.042969 26.371094 C 27.222656 26.710938 27.578125 26.917969 27.960938 26.90625 C 28.347656 26.894531 28.6875 26.664063 28.84375 26.3125 L 36.15625 13.65625 C 36.34375 13.335938 36.335938 12.9375 36.140625 12.625 C 35.941406 12.308594 35.589844 12.128906 35.21875 12.15625 C 35.1875 12.15625 35.15625 12.15625 35.125 12.15625 Z M 17.78125 17.71875 C 17.75 17.726563 17.71875 17.738281 17.6875 17.75 C 17.375 17.824219 17.113281 18.042969 16.988281 18.339844 C 16.867188 18.636719 16.894531 18.976563 17.0625 19.25 L 21.125 26.3125 C 21.402344 26.796875 22.015625 26.964844 22.5 26.6875 C 22.984375 26.410156 23.152344 25.796875 22.875 25.3125 L 18.78125 18.25 C 18.605469 17.914063 18.253906 17.710938 17.875 17.71875 C 17.84375 17.71875 17.8125 17.71875 17.78125 17.71875 Z M 7 19.6875 C 6.566406 19.742188 6.222656 20.070313 6.140625 20.5 C 6.0625 20.929688 6.273438 21.359375 6.65625 21.5625 L 19.3125 28.875 C 19.796875 29.152344 20.410156 28.984375 20.6875 28.5 C 20.964844 28.015625 20.796875 27.402344 20.3125 27.125 L 7.65625 19.84375 C 7.488281 19.738281 7.292969 19.683594 7.09375 19.6875 C 7.0625 19.6875 7.03125 19.6875 7 19.6875 Z M 37.1875 22.90625 C 37.03125 22.921875 36.882813 22.976563 36.75 23.0625 L 29.6875 27.125 C 29.203125 27.402344 29.035156 28.015625 29.3125 28.5 C 29.589844 28.984375 30.203125 29.152344 30.6875 28.875 L 37.75 24.78125 C 38.164063 24.554688 38.367188 24.070313 38.230469 23.617188 C 38.09375 23.164063 37.660156 22.867188 37.1875 22.90625 Z M 0.71875 30 C 0.167969 30.078125 -0.21875 30.589844 -0.140625 31.140625 C -0.0625 31.691406 0.449219 32.078125 1 32 L 19 32 C 19.359375 32.003906 19.695313 31.816406 19.878906 31.503906 C 20.058594 31.191406 20.058594 30.808594 19.878906 30.496094 C 19.695313 30.183594 19.359375 29.996094 19 30 L 1 30 C 0.96875 30 0.9375 30 0.90625 30 C 0.875 30 0.84375 30 0.8125 30 C 0.78125 30 0.75 30 0.71875 30 Z M 30.71875 30 C 30.167969 30.078125 29.78125 30.589844 29.859375 31.140625 C 29.9375 31.691406 30.449219 32.078125 31 32 L 49 32 C 49.359375 32.003906 49.695313 31.816406 49.878906 31.503906 C 50.058594 31.191406 50.058594 30.808594 49.878906 30.496094 C 49.695313 30.183594 49.359375 29.996094 49 30 L 31 30 C 30.96875 30 30.9375 30 30.90625 30 C 30.875 30 30.84375 30 30.8125 30 C 30.78125 30 30.75 30 30.71875 30 Z M 19.75 32.96875 C 19.71875 32.976563 19.6875 32.988281 19.65625 33 C 19.535156 33.019531 19.417969 33.0625 19.3125 33.125 L 12.25 37.21875 C 11.898438 37.375 11.667969 37.714844 11.65625 38.101563 C 11.644531 38.484375 11.851563 38.839844 12.191406 39.019531 C 12.53125 39.195313 12.941406 39.164063 13.25 38.9375 L 20.3125 34.875 C 20.78125 34.675781 21.027344 34.160156 20.882813 33.671875 C 20.738281 33.183594 20.25 32.878906 19.75 32.96875 Z M 30.03125 33 C 29.597656 33.054688 29.253906 33.382813 29.171875 33.8125 C 29.09375 34.242188 29.304688 34.671875 29.6875 34.875 L 42.34375 42.15625 C 42.652344 42.382813 43.0625 42.414063 43.402344 42.238281 C 43.742188 42.058594 43.949219 41.703125 43.9375 41.320313 C 43.925781 40.933594 43.695313 40.59375 43.34375 40.4375 L 30.6875 33.125 C 30.488281 33.007813 30.257813 32.964844 30.03125 33 Z M 21.9375 35.15625 C 21.894531 35.164063 21.851563 35.175781 21.8125 35.1875 C 21.519531 35.242188 21.269531 35.425781 21.125 35.6875 L 13.84375 48.34375 C 13.617188 48.652344 13.585938 49.0625 13.761719 49.402344 C 13.941406 49.742188 14.296875 49.949219 14.679688 49.9375 C 15.066406 49.925781 15.40625 49.695313 15.5625 49.34375 L 22.875 36.6875 C 23.078125 36.367188 23.082031 35.957031 22.882813 35.628906 C 22.683594 35.304688 22.316406 35.121094 21.9375 35.15625 Z M 27.84375 35.1875 C 27.511719 35.234375 27.226563 35.445313 27.082031 35.746094 C 26.9375 36.046875 26.953125 36.398438 27.125 36.6875 L 31.21875 43.75 C 31.375 44.101563 31.714844 44.332031 32.101563 44.34375 C 32.484375 44.355469 32.839844 44.148438 33.019531 43.808594 C 33.195313 43.46875 33.164063 43.058594 32.9375 42.75 L 28.875 35.6875 C 28.671875 35.320313 28.257813 35.121094 27.84375 35.1875 Z M 24.90625 35.96875 C 24.863281 35.976563 24.820313 35.988281 24.78125 36 C 24.316406 36.105469 23.988281 36.523438 24 37 L 24 45.9375 C 23.996094 46.296875 24.183594 46.632813 24.496094 46.816406 C 24.808594 46.996094 25.191406 46.996094 25.503906 46.816406 C 25.816406 46.632813 26.003906 46.296875 26 45.9375 L 26 37 C 26.011719 36.710938 25.894531 36.433594 25.6875 36.238281 C 25.476563 36.039063 25.191406 35.941406 24.90625 35.96875 Z"
)

icons8_laser_beam = icons8_laser_beam

icons8_laser_beam_hazard_50 = VectorIcon(
    "M 50 15.033203 C 48.582898 15.033232 47.16668 15.72259 46.375 17.101562 L 11.564453 77.705078 C 9.9806522 80.462831 12.019116 84 15.197266 84 L 84.802734 84 C 87.98159 84 90.021301 80.462831 88.4375 77.705078 L 53.626953 17.101562 C 52.834735 15.72278 51.417102 15.033174 50 15.033203 z M 50 16.966797 C 50.729648 16.966826 51.459796 17.344439 51.892578 18.097656 L 86.703125 78.701172 C 87.569324 80.209419 86.535879 82 84.802734 82 L 15.197266 82 C 13.465416 82 12.432629 80.209419 13.298828 78.701172 L 48.109375 18.097656 C 48.541695 17.344629 49.270352 16.966768 50 16.966797 z M 49.976562 21.332031 A 0.50005 0.50005 0 0 0 49.554688 21.607422 L 49.558594 21.595703 L 26.78125 61.25 A 0.5005035 0.5005035 0 1 0 27.648438 61.75 L 50.001953 22.833984 L 69.625 57 L 57.931641 57 C 57.862711 56.450605 57.737333 55.919306 57.5625 55.410156 L 59.892578 54.443359 A 0.50005 0.50005 0 0 0 59.689453 53.478516 A 0.50005 0.50005 0 0 0 59.509766 53.519531 L 57.177734 54.486328 C 56.861179 53.842222 56.462551 53.247463 55.992188 52.714844 L 61.314453 47.392578 A 0.50005 0.50005 0 0 0 60.949219 46.535156 A 0.50005 0.50005 0 0 0 60.607422 46.685547 L 55.285156 52.007812 C 54.752537 51.537449 54.157778 51.138821 53.513672 50.822266 L 54.480469 48.490234 A 0.50005 0.50005 0 0 0 54.009766 47.791016 A 0.50005 0.50005 0 0 0 53.556641 48.107422 L 52.589844 50.4375 C 51.927783 50.21016 51.227119 50.070675 50.5 50.025391 L 50.5 40.5 A 0.50005 0.50005 0 0 0 49.992188 39.992188 A 0.50005 0.50005 0 0 0 49.5 40.5 L 49.5 50.025391 C 48.772881 50.070675 48.072217 50.21016 47.410156 50.4375 L 46.443359 48.107422 A 0.50005 0.50005 0 0 0 45.974609 47.791016 A 0.50005 0.50005 0 0 0 45.519531 48.490234 L 46.486328 50.822266 C 45.842222 51.138821 45.247463 51.537449 44.714844 52.007812 L 39.392578 46.685547 A 0.50005 0.50005 0 0 0 39.035156 46.535156 A 0.50005 0.50005 0 0 0 38.685547 47.392578 L 44.007812 52.714844 C 43.537449 53.247463 43.138821 53.842222 42.822266 54.486328 L 40.490234 53.519531 A 0.50005 0.50005 0 0 0 40.294922 53.478516 A 0.50005 0.50005 0 0 0 40.107422 54.443359 L 42.4375 55.410156 C 42.21016 56.072217 42.070675 56.772881 42.025391 57.5 L 33.5 57.5 A 0.50005 0.50005 0 1 0 33.5 58.5 L 42.025391 58.5 C 42.070675 59.227119 42.21016 59.927783 42.4375 60.589844 L 40.107422 61.556641 A 0.50005 0.50005 0 1 0 40.490234 62.480469 L 42.822266 61.513672 C 43.138821 62.157778 43.537449 62.752537 44.007812 63.285156 L 38.685547 68.607422 A 0.50005 0.50005 0 1 0 39.392578 69.314453 L 44.714844 63.992188 C 45.247463 64.462551 45.842222 64.861179 46.486328 65.177734 L 45.519531 67.509766 A 0.50005 0.50005 0 1 0 46.443359 67.892578 L 47.410156 65.5625 C 48.072217 65.78984 48.772881 65.929325 49.5 65.974609 L 49.5 75.5 A 0.50005 0.50005 0 1 0 50.5 75.5 L 50.5 65.974609 C 51.227119 65.929325 51.927783 65.78984 52.589844 65.5625 L 53.556641 67.892578 A 0.50005 0.50005 0 1 0 54.480469 67.509766 L 53.513672 65.177734 C 54.157778 64.861179 54.752537 64.462551 55.285156 63.992188 L 60.607422 69.314453 A 0.50005 0.50005 0 1 0 61.314453 68.607422 L 55.992188 63.285156 C 56.462551 62.752537 56.861179 62.157778 57.177734 61.513672 L 59.509766 62.480469 A 0.50005 0.50005 0 1 0 59.892578 61.556641 L 57.5625 60.589844 C 57.737333 60.080694 57.862711 59.549395 57.931641 59 L 70.773438 59 L 81.685547 78 L 17.451172 78 A 0.50005 0.50005 0 1 0 17.451172 79 L 82.550781 79 A 0.50005 0.50005 0 0 0 82.984375 78.25 L 50.435547 21.582031 A 0.50005 0.50005 0 0 0 49.976562 21.332031 z M 44.826172 45.019531 A 0.50005 0.50005 0 0 0 44.371094 45.71875 L 44.753906 46.642578 A 0.50005 0.50005 0 1 0 45.677734 46.259766 L 45.294922 45.335938 A 0.50005 0.50005 0 0 0 44.826172 45.019531 z M 55.158203 45.021484 A 0.50005 0.50005 0 0 0 54.705078 45.335938 L 54.322266 46.259766 A 0.50005 0.50005 0 1 0 55.246094 46.642578 L 55.628906 45.71875 A 0.50005 0.50005 0 0 0 55.158203 45.021484 z M 49.939453 51.003906 A 0.50005 0.50005 0 0 0 50.0625 51.003906 C 50.967657 51.011882 51.829666 51.190519 52.621094 51.509766 A 0.50005 0.50005 0 0 0 52.751953 51.560547 C 53.549716 51.901213 54.268672 52.388578 54.880859 52.984375 A 0.50005 0.50005 0 0 0 55.009766 53.113281 C 55.608206 53.726739 56.097688 54.447709 56.439453 55.248047 A 0.50005 0.50005 0 0 0 56.488281 55.375 C 56.815986 56.185939 57 57.070277 57 58 C 57 58.944364 56.812181 59.84279 56.474609 60.664062 A 0.50005 0.50005 0 0 0 56.447266 60.736328 C 56.102786 61.548676 55.606272 62.280088 54.998047 62.900391 A 0.50005 0.50005 0 0 0 54.902344 62.996094 C 54.287775 63.59917 53.563359 64.091195 52.759766 64.435547 A 0.50005 0.50005 0 0 0 52.617188 64.490234 C 51.82726 64.808392 50.967598 64.987888 50.064453 64.996094 A 0.50005 0.50005 0 0 0 49.992188 64.992188 A 0.50005 0.50005 0 0 0 49.935547 64.996094 C 49.032638 64.98789 48.17257 64.810189 47.382812 64.492188 A 0.50005 0.50005 0 0 0 47.242188 64.435547 C 46.438807 64.091527 45.714172 63.600645 45.099609 62.998047 A 0.50005 0.50005 0 0 0 45 62.898438 C 44.391656 62.277526 43.894973 61.545514 43.550781 60.732422 A 0.50005 0.50005 0 0 0 43.525391 60.662109 C 43.195567 59.859085 43.011772 58.981915 43.003906 58.060547 A 0.50005 0.50005 0 0 0 43.003906 57.9375 C 43.011882 57.032344 43.190519 56.170334 43.509766 55.378906 A 0.50005 0.50005 0 0 0 43.560547 55.248047 C 43.901213 54.450284 44.388579 53.731328 44.984375 53.119141 A 0.50005 0.50005 0 0 0 45.113281 52.990234 C 45.726739 52.391794 46.447709 51.902313 47.248047 51.560547 A 0.50005 0.50005 0 0 0 47.375 51.511719 C 48.168096 51.191224 49.032048 51.011653 49.939453 51.003906 z M 37.523438 52.330078 A 0.50005 0.50005 0 0 0 37.335938 53.294922 L 38.259766 53.677734 A 0.50005 0.50005 0 1 0 38.642578 52.753906 L 37.71875 52.371094 A 0.50005 0.50005 0 0 0 37.523438 52.330078 z M 62.460938 52.330078 A 0.50005 0.50005 0 0 0 62.28125 52.371094 L 61.357422 52.753906 A 0.50005 0.50005 0 1 0 61.740234 53.677734 L 62.664062 53.294922 A 0.50005 0.50005 0 0 0 62.460938 52.330078 z M 38.439453 62.28125 A 0.50005 0.50005 0 0 0 38.259766 62.322266 L 37.335938 62.705078 A 0.50005 0.50005 0 1 0 37.71875 63.628906 L 38.642578 63.246094 A 0.50005 0.50005 0 0 0 38.439453 62.28125 z M 61.546875 62.28125 A 0.50005 0.50005 0 0 0 61.357422 63.246094 L 62.28125 63.628906 A 0.50005 0.50005 0 1 0 62.664062 62.705078 L 61.740234 62.322266 A 0.50005 0.50005 0 0 0 61.546875 62.28125 z M 25.498047 63.994141 A 0.50005 0.50005 0 0 0 25.058594 64.251953 L 23.335938 67.251953 A 0.50005 0.50005 0 1 0 24.203125 67.748047 L 25.925781 64.748047 A 0.50005 0.50005 0 0 0 25.498047 63.994141 z M 22.626953 68.994141 A 0.50005 0.50005 0 0 0 22.185547 69.251953 L 21.613281 70.251953 A 0.50005 0.50005 0 1 0 22.480469 70.748047 L 23.052734 69.748047 A 0.50005 0.50005 0 0 0 22.626953 68.994141 z M 45.207031 69.042969 A 0.50005 0.50005 0 0 0 44.753906 69.357422 L 44.371094 70.28125 A 0.50005 0.50005 0 1 0 45.294922 70.664062 L 45.677734 69.740234 A 0.50005 0.50005 0 0 0 45.207031 69.042969 z M 54.777344 69.042969 A 0.50005 0.50005 0 0 0 54.322266 69.740234 L 54.705078 70.664062 A 0.50005 0.50005 0 1 0 55.628906 70.28125 L 55.246094 69.357422 A 0.50005 0.50005 0 0 0 54.777344 69.042969 z"
)

icons8_laser_beam_hazard2_50 = icons8_laser_beam_hazard_50

icons8_move_50 = VectorIcon(
    "M50.6,21.7L61,11.2v32.5c0,1.7,1.3,3,3,3s3-1.3,3-3V11.2l10.4,10.4c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9	c1.2-1.2,1.2-3.1,0-4.2L66.1,1.9c-1.2-1.2-3.1-1.2-4.2,0L46.3,17.4c-1.2,1.2-1.2,3.1,0,4.2C47.5,22.8,49.4,22.8,50.6,21.7z M61.9,126.1c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9l15.6-15.6c1.2-1.2,1.2-3.1,0-4.2c-1.2-1.2-3.1-1.2-4.2,0	L67,116.8V84.3c0-1.7-1.3-3-3-3s-3,1.3-3,3v32.5l-10.4-10.4c-1.2-1.2-3.1-1.2-4.2,0c-1.2,1.2-1.2,3.1,0,4.2L61.9,126.1z M17.4,81.7c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9c1.2-1.2,1.2-3.1,0-4.2L11.2,67h32.5c1.7,0,3-1.3,3-3	s-1.3-3-3-3H11.2l10.4-10.4c1.2-1.2,1.2-3.1,0-4.2c-1.2-1.2-3.1-1.2-4.2,0L1.9,61.9C1.3,62.4,1,63.2,1,64s0.3,1.6,0.9,2.1L17.4,81.7	z M126.1,61.9l-15.6-15.6c-1.2-1.2-3.1-1.2-4.2,0c-1.2,1.2-1.2,3.1,0,4.2L116.8,61H84.3c-1.7,0-3,1.3-3,3	s1.3,3,3,3h32.5l-10.4,10.4c-1.2,1.2-1.2,3.1,0,4.2c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9l15.6-15.6c0.6-0.6,0.9-1.3,0.9-2.1	S126.7,62.4,126.1,61.9z"
)

icons8_opened_folder_50 = VectorIcon(
    "M 3 4 C 1.355469 4 0 5.355469 0 7 L 0 43.90625 C -0.0625 44.136719 -0.0390625 44.378906 0.0625 44.59375 C 0.34375 45.957031 1.5625 47 3 47 L 42 47 C 43.492188 47 44.71875 45.875 44.9375 44.4375 C 44.945313 44.375 44.964844 44.3125 44.96875 44.25 C 44.96875 44.230469 44.96875 44.207031 44.96875 44.1875 L 45 44.03125 C 45 44.019531 45 44.011719 45 44 L 49.96875 17.1875 L 50 17.09375 L 50 17 C 50 15.355469 48.644531 14 47 14 L 47 11 C 47 9.355469 45.644531 8 44 8 L 18.03125 8 C 18.035156 8.003906 18.023438 8 18 8 C 17.96875 7.976563 17.878906 7.902344 17.71875 7.71875 C 17.472656 7.4375 17.1875 6.96875 16.875 6.46875 C 16.5625 5.96875 16.226563 5.4375 15.8125 4.96875 C 15.398438 4.5 14.820313 4 14 4 Z M 3 6 L 14 6 C 13.9375 6 14.066406 6 14.3125 6.28125 C 14.558594 6.5625 14.84375 7.03125 15.15625 7.53125 C 15.46875 8.03125 15.8125 8.5625 16.21875 9.03125 C 16.625 9.5 17.179688 10 18 10 L 44 10 C 44.5625 10 45 10.4375 45 11 L 45 14 L 8 14 C 6.425781 14 5.171875 15.265625 5.0625 16.8125 L 5.03125 16.8125 L 5 17 L 2 33.1875 L 2 7 C 2 6.4375 2.4375 6 3 6 Z M 8 16 L 47 16 C 47.5625 16 48 16.4375 48 17 L 43.09375 43.53125 L 43.0625 43.59375 C 43.050781 43.632813 43.039063 43.675781 43.03125 43.71875 C 43.019531 43.757813 43.007813 43.800781 43 43.84375 C 43 43.863281 43 43.886719 43 43.90625 C 43 43.917969 43 43.925781 43 43.9375 C 42.984375 43.988281 42.976563 44.039063 42.96875 44.09375 C 42.964844 44.125 42.972656 44.15625 42.96875 44.1875 C 42.964844 44.230469 42.964844 44.269531 42.96875 44.3125 C 42.84375 44.71875 42.457031 45 42 45 L 3 45 C 2.4375 45 2 44.5625 2 44 L 6.96875 17.1875 L 7 17.09375 L 7 17 C 7 16.4375 7.4375 16 8 16 Z"
)

icons8_pause_50 = VectorIcon(
    "M 12 8 L 12 42 L 22 42 L 22 8 Z M 28 8 L 28 42 L 38 42 L 38 8 Z"
)

icons8_save_50 = VectorIcon(
    "M 7 4 C 5.3545455 4 4 5.3545455 4 7 L 4 43 C 4 44.645455 5.3545455 46 7 46 L 43 46 C 44.645455 46 46 44.645455 46 43 L 46 13.199219 A 1.0001 1.0001 0 0 0 45.707031 12.492188 L 37.507812 4.2929688 A 1.0001 1.0001 0 0 0 36.800781 4 L 7 4 z M 7 6 L 12 6 L 12 18 C 12 19.645455 13.354545 21 15 21 L 34 21 C 35.645455 21 37 19.645455 37 18 L 37 6.6132812 L 44 13.613281 L 44 43 C 44 43.554545 43.554545 44 43 44 L 38 44 L 38 29 C 38 27.354545 36.645455 26 35 26 L 15 26 C 13.354545 26 12 27.354545 12 29 L 12 44 L 7 44 C 6.4454545 44 6 43.554545 6 43 L 6 7 C 6 6.4454545 6.4454545 6 7 6 z M 14 6 L 35 6 L 35 18 C 35 18.554545 34.554545 19 34 19 L 15 19 C 14.445455 19 14 18.554545 14 18 L 14 6 z M 29 8 A 1.0001 1.0001 0 0 0 28 9 L 28 16 A 1.0001 1.0001 0 0 0 29 17 L 32 17 A 1.0001 1.0001 0 0 0 33 16 L 33 9 A 1.0001 1.0001 0 0 0 32 8 L 29 8 z M 30 10 L 31 10 L 31 15 L 30 15 L 30 10 z M 15 28 L 35 28 C 35.554545 28 36 28.445455 36 29 L 36 44 L 14 44 L 14 29 C 14 28.445455 14.445455 28 15 28 z M 8 40 L 8 42 L 10 42 L 10 40 L 8 40 z M 40 40 L 40 42 L 42 42 L 42 40 L 40 40 z"
)

icons8_separate_for_every_new_imported_file = VectorIcon(
    "M 16 4 L 16 8 L 10 8 L 10 12 L 4 12 L 4 28 L 7 28 L 12 28 L 12 26 L 7 26 L 6 26 L 6 14 L 14 14 L 14 19 L 16 19 L 16 12 L 12 12 L 12 10 L 20 10 L 20 24 L 22 24 L 22 20 L 24 20 L 24 18 L 22 18 L 22 8 L 18 8 L 18 6 L 26 6 L 26 11 L 28 11 L 28 4 L 16 4 z M 27 13 L 24 16 L 26 16 L 26 20 L 28 20 L 28 16 L 30 16 L 27 13 z M 15 21 L 12 24 L 14 24 L 14 28 L 16 28 L 16 24 L 18 24 L 15 21 z"
)

# The following icons were designed by the mk-Team themselves...
icon_fractal = VectorIcon(
    fill="",
    stroke="M 0,0 L 4095,0 L 6143,-3547 L 4095,-7094 L 6143,-10641 L 10239,-10641 L 12287,-7094 M 12287,-7094 L 10239,-3547 L 12287,0 L 16383,0 M 16383,0 L 18431,-3547 L 22527,-3547 L 24575,0 L 28671,0 L 30719,-3547 L 28671,-7094 L 24575,-7094 L 22527,-10641 L 24575,-14188 M 24575,-14188 L 22527,-17735 L 18431,-17735 L 16383,-14188 M 16383,-14188 L 12287,-14188 L 10239,-17735 L 12287,-21283 L 16383,-21283 L 18431,-24830 L 16383,-28377 M 16383,-28377 L 18431,-31924 L 22527,-31924 L 24575,-28377 L 28671,-28377 L 30719,-31924 L 28671,-35471 L 24575,-35471 L 22527,-39019 L 24575,-42566 L 28671,-42566 L 30719,-46113 L 28671,-49660 L 30719,-53207 L 34815,-53207 L 36863,-49660 L 34815,-46113 L 36863,-42566 L 40959,-42566 L 43007,-39019 L 40959,-35471 L 36863,-35471 L 34815,-31924 L 36863,-28377 L 40959,-28377 L 43007,-31924 L 47103,-31924 L 49151,-28377 L 47103,-24830 L 49151,-21283 L 53247,-21283 L 55295,-17735 L 53247,-14188 L 49151,-14188 L 47103,-17735 L 43007,-17735 L 40959,-14188 L 43007,-10641 L 40959,-7094 L 36863,-7094 L 34815,-3547 L 36863,0 L 40959,0 M 40959,0 L 43007,-3547 L 47103,-3547 L 49151,0 M 49151,0 L 53247,0 L 55295,-3547 L 53247,-7094 L 55295,-10641 L 59391,-10641 L 61439,-7094 L 59391,-3547 L 61439,0 L 65535,0",
)

icon_mk_circle = VectorIcon(fill="", stroke="M 15, 15 a 15,15 0 1,0 1,0 z")

icon_mk_ellipse = VectorIcon(fill="", stroke="M 15, 7.5 a 15,7.5 0 1,0 1,0 z")

icon_mk_rectangular = VectorIcon(
    fill=(
        "M 5 0 a 5 5, 0 1,0 1,0",
        "M 50 0 a 5 5, 0 1,0 1,0",
        "M 50 30 a 5 5, 0 1,0 1,0",
        "M 5 30 a 5 5, 0 1,0 1,0",
    ),
    stroke=("M 5 5 h45 v30 h-45 v-30",),
)

icon_mk_polyline = VectorIcon(
    fill=(
        "M 5,45 a 5,5, 0 1,0 1,0",
        "M 20,15 a 5,5, 0 1,0 1,0",
        "M 40,35 a 5,5, 0 1,0 1,0",
        "M 60,5 a 5,5, 0 1,0 1,0",
    ),
    stroke=("M 5,50 L 20 20 L 40 40 L 60 10",),
)

icon_mk_point = VectorIcon(
    fill="M 15, 12 a 3,3 0 1,0 1,0 z",
    stroke=(
        "M 15, 0 a 15,15 0 1,0 1,0 z",
        "M 15, 5 a 10,10 0 1,0 1,0 z",
    ),
)

icon_mk_align_right = VectorIcon(
    fill="M 20,5 h20 v10 h-20 z",
    stroke=(
        "M 10,20 h30 v10 h-30 z",
        "M 20,5 h20 v10 h-20 z",
        "M 45,0 v35",
    ),
)

icon_mk_align_left = VectorIcon(
    fill="M 5,5 h20 v10 h-20 z",
    stroke=(
        "M 5,20 h30 v10 h-30 z",
        "M 5,5 h20 v10 h-20 z",
        "M 0,0 v35",
    ),
)

icon_mk_align_top = VectorIcon(
    fill="M 20,5 v20 h10 v-20 z",
    stroke=(
        "M 5,5 v30 h10 v-30 z",
        "M 20,5 v20 h10 v-20 z",
        "M 0,0 h35",
    ),
)

icon_mk_align_bottom = VectorIcon(
    fill="M 20,15 v20 h10 v-20 z",
    stroke=(
        "M 5,5 v30 h10 v-30 z",
        "M 20,15 v20 h10 v-20 z",
        "M 0,40 h35",
    ),
)

icon_mk_polygon = VectorIcon(
    fill=(
        "M 20,50 a 5,5, 0 1,0 1,0",
        "M 40,50 a 5,5, 0 1,0 1,0",
        "M 20,0 a 5,5, 0 1,0 1,0",
        "M 40,0 a 5,5, 0 1,0 1,0",
        "M 55,25 a 5,5, 0 1,0 1,0",
        "M 5,25 a 5,5, 0 1,0 1,0",
    ),
    stroke="M 20,55 L 40,55 L 55,30 L 40,5 L 20,5 L 5,30 z",
)

node_add = VectorIcon(
    fill="",
    stroke=(
        "M 35, 15 h 30",
        "M 50, 0 v 30",
        "M 35,70 h 30 v 30 h -30 z",
        "M 0,85 h 100",
    ),
)

node_append = VectorIcon(
    fill="",
    stroke=(
        "M 35, 15 h 30",
        "M 50, 0 v 30",
        "M 0,70 h 15 v 30 h -15",
        "M 70,70 h 30 v 30 h -30 z",
        "M 0,85 h 85",
    ),
)


def savage_consumer():
    import argparse
    import os.path
    import sys
    from xml.etree.ElementTree import iterparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-V", "--version", action="store_true", help="icon consumer version"
    )
    parser.add_argument("input", nargs="?", type=str, help="input file")
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    if args.version:
        print("Version 1: SaVaGe Consumer")
        return

    if not args.input:
        print("Input not specified.")
        return

    only_filename = os.path.split(args.input)[-1]
    ext_split = os.path.splitext(only_filename)
    assert ext_split[-1] == ".svg"
    filename = ext_split[0]
    filename = filename.replace("-", "_")

    fills = []
    strokes = []
    with open(args.input, "r") as f:
        for event, elem in iterparse(f, events=("end",)):
            if not elem.tag.endswith("path"):
                continue
            path_d = elem.attrib.get("d")
            if "stroke-width" in elem.attrib:
                strokes.append(path_d)
            else:
                fills.append(path_d)

    if not fills and not strokes:
        print("Parsing error, blank.")
        return

    with open(__file__, "a") as f:
        f.write(
            f"\n{filename} = VectorIcon(fill={str(tuple(fills))}, stroke={str(tuple(strokes))})\n"
        )

    print(f"{filename} was added as a vector icon.")


if __name__ == "__main__":
    savage_consumer()

# The following icons were added with SaVaGe consumer.

icons8_info_50 = VectorIcon(fill=('M 25 2 C 12.309295 2 2 12.309295 2 25 C 2 37.690705 12.309295 48 25 48 C 37.690705 48 48 37.690705 48 25 C 48 12.309295 37.690705 2 25 2 z M 25 4 C 36.609824 4 46 13.390176 46 25 C 46 36.609824 36.609824 46 25 46 C 13.390176 46 4 36.609824 4 25 C 4 13.390176 13.390176 4 25 4 z M 25 11 A 3 3 0 0 0 22 14 A 3 3 0 0 0 25 17 A 3 3 0 0 0 28 14 A 3 3 0 0 0 25 11 z M 21 21 L 21 23 L 22 23 L 23 23 L 23 36 L 22 36 L 21 36 L 21 38 L 22 38 L 23 38 L 27 38 L 28 38 L 29 38 L 29 36 L 28 36 L 27 36 L 27 21 L 26 21 L 22 21 L 21 21 z',), stroke=())

icons8_scissors_50 = VectorIcon(fill=('M 30.015625 1.085938 C 29.976563 1.085938 29.9375 1.089844 29.902344 1.09375 C 27.160156 1.367188 25.386719 3.105469 24.378906 4.679688 C 23.371094 6.257813 23.027344 7.773438 23.027344 7.773438 C 23.019531 7.796875 23.015625 7.820313 23.011719 7.84375 L 20.609375 23.0625 C 20.320313 23.128906 16.007813 24.121094 14.285156 24.65625 C 13.828125 24.800781 13.90625 24.777344 13.855469 24.78125 C 13.476563 21.554688 10.824219 19 7.5 19 C 3.921875 19 1 21.921875 1 25.5 C 1 29.078125 3.921875 32 7.5 32 L 7.984375 32 C 10.027344 32.035156 11.660156 31.195313 13.550781 30.453125 C 15.328125 29.761719 17.386719 29.097656 20.398438 29.015625 C 20.710938 31.277344 20.320313 33.261719 19.75 35.152344 C 19.039063 37.511719 18 39.679688 18 42 L 18 42.5 C 18 46.078125 20.921875 49 24.5 49 C 28.078125 49 31 46.078125 31 42.5 C 31 39.058594 28.277344 36.292969 24.890625 36.078125 C 25.300781 34.714844 26.578125 30.433594 26.917969 29.292969 L 42.152344 26.988281 C 42.175781 26.984375 42.199219 26.980469 42.222656 26.972656 C 42.222656 26.972656 43.757813 26.628906 45.355469 25.625 C 46.953125 24.621094 48.71875 22.84375 48.996094 20.097656 C 49.023438 19.8125 48.925781 19.527344 48.730469 19.316406 C 48.535156 19.109375 48.257813 18.992188 47.96875 19 C 47.933594 19 47.894531 19.003906 47.859375 19.011719 L 28.152344 21.824219 L 30.988281 2.230469 C 31.03125 1.945313 30.949219 1.65625 30.761719 1.4375 C 30.574219 1.21875 30.300781 1.089844 30.015625 1.085938 Z M 28.769531 3.589844 L 25.25 27.890625 C 25.25 27.890625 25.195313 28.070313 25.191406 28.082031 C 25.191406 28.085938 25.191406 28.089844 25.1875 28.09375 C 25.0625 28.511719 23.292969 34.449219 22.910156 35.714844 C 22.78125 36.144531 22.722656 36.539063 22.832031 36.964844 C 22.945313 37.386719 23.316406 37.777344 23.652344 37.917969 C 24.117188 38.109375 24.410156 38.0625 24.59375 38.011719 C 27.046875 38.058594 29 40.035156 29 42.5 C 29 44.996094 26.996094 47 24.5 47 C 22.003906 47 20 44.996094 20 42.5 L 20 42 C 20 40.328125 20.90625 38.25 21.664063 35.730469 C 22.394531 33.308594 22.863281 30.40625 22 27.085938 L 24.980469 8.214844 C 24.980469 8.207031 25.261719 7.019531 26.0625 5.757813 C 26.65625 4.835938 27.59375 4.082031 28.769531 3.589844 Z M 7.5 21 C 9.996094 21 12 23.003906 12 25.5 L 12.003906 25.402344 C 12.003906 25.402344 11.984375 25.699219 12.082031 25.953125 C 12.183594 26.210938 12.433594 26.5 12.738281 26.648438 C 13.347656 26.945313 13.949219 26.859375 14.878906 26.566406 C 16.117188 26.183594 19.050781 25.488281 20.269531 25.203125 L 20.011719 26.84375 C 20.003906 26.90625 20 26.964844 20 27.027344 C 16.882813 27.160156 14.617188 27.890625 12.824219 28.59375 C 10.839844 29.367188 9.472656 30.027344 8.015625 30 C 8.011719 30 8.003906 30 8 30 L 7.5 30 C 5.003906 30 3 27.996094 3 25.5 C 3 23.003906 5.003906 21 7.5 21 Z M 46.496094 21.222656 C 45.996094 22.398438 45.226563 23.339844 44.289063 23.933594 C 43.007813 24.738281 41.796875 25.019531 41.785156 25.019531 L 27.371094 27.203125 L 27.851563 23.890625 Z M 7.5 22 C 5.578125 22 4 23.578125 4 25.5 C 4 27.421875 5.578125 29 7.5 29 C 9.421875 29 11 27.421875 11 25.5 C 11 23.578125 9.421875 22 7.5 22 Z M 7.5 24 C 8.339844 24 9 24.660156 9 25.5 C 9 26.339844 8.339844 27 7.5 27 C 6.660156 27 6 26.339844 6 25.5 C 6 24.660156 6.660156 24 7.5 24 Z M 24 24 C 23.449219 24 23 24.449219 23 25 C 23 25.550781 23.449219 26 24 26 C 24.550781 26 25 25.550781 25 25 C 25 24.449219 24.550781 24 24 24 Z M 13.941406 25.21875 C 13.945313 25.222656 13.945313 25.222656 13.949219 25.222656 C 13.953125 25.242188 13.949219 25.246094 13.953125 25.265625 C 13.953125 25.25 13.945313 25.234375 13.941406 25.21875 Z M 24.5 39 C 22.578125 39 21 40.578125 21 42.5 C 21 44.421875 22.578125 46 24.5 46 C 26.421875 46 28 44.421875 28 42.5 C 28 40.578125 26.421875 39 24.5 39 Z M 24.5 41 C 25.339844 41 26 41.660156 26 42.5 C 26 43.339844 25.339844 44 24.5 44 C 23.660156 44 23 43.339844 23 42.5 C 23 41.660156 23.660156 41 24.5 41 Z',), stroke=())

icon_mk_undo = VectorIcon(fill=('M 16.8125 3.09375 C 16.59375 3.132813 16.398438 3.242188 16.25 3.40625 L 5.34375 14.28125 L 4.65625 15 L 5.34375 15.71875 L 16.25 26.59375 C 16.492188 26.890625 16.878906 27.027344 17.253906 26.941406 C 17.625 26.855469 17.917969 26.5625 18.003906 26.191406 C 18.089844 25.816406 17.953125 25.429688 17.65625 25.1875 L 8.46875 16 L 24 16 C 30.007813 16 34.242188 17.519531 36.96875 19.96875 C 39.695313 22.417969 41 25.835938 41 30 C 41 38.347656 37.15625 44.46875 37.15625 44.46875 C 36.933594 44.769531 36.894531 45.171875 37.0625 45.507813 C 37.230469 45.847656 37.570313 46.0625 37.945313 46.066406 C 38.320313 46.070313 38.667969 45.863281 38.84375 45.53125 C 38.84375 45.53125 43 38.964844 43 30 C 43 25.40625 41.5 21.332031 38.3125 18.46875 C 35.125 15.605469 30.347656 14 24 14 L 8.46875 14 L 17.65625 4.8125 C 17.980469 4.511719 18.066406 4.035156 17.871094 3.640625 C 17.679688 3.242188 17.246094 3.023438 16.8125 3.09375 Z',), stroke=())

icon_mk_redo = VectorIcon(fill=('M 32.84375 3.09375 C 32.46875 3.160156 32.167969 3.433594 32.0625 3.796875 C 31.957031 4.164063 32.066406 4.554688 32.34375 4.8125 L 41.53125 14 L 26 14 C 19.652344 14 14.875 15.605469 11.6875 18.46875 C 8.5 21.332031 7 25.40625 7 30 C 7 38.964844 11.15625 45.53125 11.15625 45.53125 C 11.332031 45.863281 11.679688 46.070313 12.054688 46.066406 C 12.429688 46.0625 12.769531 45.847656 12.9375 45.507813 C 13.105469 45.171875 13.066406 44.769531 12.84375 44.46875 C 12.84375 44.46875 9 38.347656 9 30 C 9 25.835938 10.304688 22.417969 13.03125 19.96875 C 15.757813 17.519531 19.992188 16 26 16 L 41.53125 16 L 32.34375 25.1875 C 32.046875 25.429688 31.910156 25.816406 31.996094 26.191406 C 32.082031 26.5625 32.375 26.855469 32.746094 26.941406 C 33.121094 27.027344 33.507813 26.890625 33.75 26.59375 L 44.65625 15.71875 L 45.34375 15 L 44.65625 14.28125 L 33.75 3.40625 C 33.542969 3.183594 33.242188 3.070313 32.9375 3.09375 C 32.90625 3.09375 32.875 3.09375 32.84375 3.09375 Z',), stroke=())

icons8_left_50 = VectorIcon(fill=('M 19.8125 13.09375 C 19.59375 13.132813 19.398438 13.242188 19.25 13.40625 L 8.34375 24.28125 L 7.65625 25 L 8.34375 25.71875 L 19.25 36.59375 C 19.492188 36.890625 19.878906 37.027344 20.253906 36.941406 C 20.625 36.855469 20.917969 36.5625 21.003906 36.191406 C 21.089844 35.816406 20.953125 35.429688 20.65625 35.1875 L 11.46875 26 L 41 26 C 41.359375 26.003906 41.695313 25.816406 41.878906 25.503906 C 42.058594 25.191406 42.058594 24.808594 41.878906 24.496094 C 41.695313 24.183594 41.359375 23.996094 41 24 L 11.46875 24 L 20.65625 14.8125 C 20.980469 14.511719 21.066406 14.035156 20.871094 13.640625 C 20.679688 13.242188 20.246094 13.023438 19.8125 13.09375 Z',), stroke=())

icons8_right_50 = VectorIcon(fill=('M 38.035156 13.988281 C 37.628906 13.980469 37.257813 14.222656 37.09375 14.59375 C 36.933594 14.96875 37.015625 15.402344 37.300781 15.691406 L 45.277344 24 L 2.023438 24 C 1.664063 23.996094 1.328125 24.183594 1.148438 24.496094 C 0.964844 24.808594 0.964844 25.191406 1.148438 25.503906 C 1.328125 25.816406 1.664063 26.003906 2.023438 26 L 45.277344 26 L 37.300781 34.308594 C 36.917969 34.707031 36.933594 35.339844 37.332031 35.722656 C 37.730469 36.105469 38.363281 36.09375 38.746094 35.691406 L 49.011719 25 L 38.746094 14.308594 C 38.5625 14.109375 38.304688 13.996094 38.035156 13.988281 Z',), stroke=())

icons8_up_50 = VectorIcon(fill=('M 25 7.65625 L 24.28125 8.34375 L 13.40625 19.25 C 13.109375 19.492188 12.972656 19.878906 13.058594 20.253906 C 13.144531 20.625 13.4375 20.917969 13.808594 21.003906 C 14.183594 21.089844 14.570313 20.953125 14.8125 20.65625 L 24 11.46875 L 24 41 C 23.996094 41.359375 24.183594 41.695313 24.496094 41.878906 C 24.808594 42.058594 25.191406 42.058594 25.503906 41.878906 C 25.816406 41.695313 26.003906 41.359375 26 41 L 26 11.46875 L 35.1875 20.65625 C 35.429688 20.953125 35.816406 21.089844 36.191406 21.003906 C 36.5625 20.917969 36.855469 20.625 36.941406 20.253906 C 37.027344 19.878906 36.890625 19.492188 36.59375 19.25 L 25.71875 8.34375 Z',), stroke=())

icons8_down_50 = VectorIcon(fill=('M 24.90625 7.96875 C 24.863281 7.976563 24.820313 7.988281 24.78125 8 C 24.316406 8.105469 23.988281 8.523438 24 9 L 24 38.53125 L 14.8125 29.34375 C 14.625 29.144531 14.367188 29.035156 14.09375 29.03125 C 13.6875 29.035156 13.324219 29.28125 13.171875 29.660156 C 13.023438 30.035156 13.113281 30.46875 13.40625 30.75 L 24.28125 41.65625 L 25 42.34375 L 25.71875 41.65625 L 36.59375 30.75 C 36.890625 30.507813 37.027344 30.121094 36.941406 29.746094 C 36.855469 29.375 36.5625 29.082031 36.191406 28.996094 C 35.816406 28.910156 35.429688 29.046875 35.1875 29.34375 L 26 38.53125 L 26 9 C 26.011719 8.710938 25.894531 8.433594 25.6875 8.238281 C 25.476563 8.039063 25.191406 7.941406 24.90625 7.96875 Z',), stroke=())

icons8_down_left_50 = VectorIcon(fill=('M 42.980469 5.992188 C 42.71875 5.996094 42.472656 6.105469 42.292969 6.292969 L 8 40.585938 L 8 27 C 8.003906 26.730469 7.898438 26.46875 7.707031 26.277344 C 7.515625 26.085938 7.253906 25.980469 6.984375 25.984375 C 6.433594 25.996094 5.992188 26.449219 6 27 L 6 42.847656 C 5.980469 42.957031 5.980469 43.070313 6 43.179688 L 6 44 L 6.824219 44 C 6.933594 44.019531 7.042969 44.019531 7.152344 44 L 23 44 C 23.359375 44.003906 23.695313 43.816406 23.878906 43.503906 C 24.058594 43.191406 24.058594 42.808594 23.878906 42.496094 C 23.695313 42.183594 23.359375 41.996094 23 42 L 9.414063 42 L 43.707031 7.707031 C 44.003906 7.417969 44.089844 6.980469 43.929688 6.601563 C 43.769531 6.21875 43.394531 5.976563 42.980469 5.992188 Z',), stroke=())

icons8_down_right_50 = VectorIcon(fill=('M 6.992188 5.992188 C 6.582031 5.992188 6.21875 6.238281 6.0625 6.613281 C 5.910156 6.992188 6 7.421875 6.292969 7.707031 L 40.585938 42 L 27 42 C 26.640625 41.996094 26.304688 42.183594 26.121094 42.496094 C 25.941406 42.808594 25.941406 43.191406 26.121094 43.503906 C 26.304688 43.816406 26.640625 44.003906 27 44 L 42.847656 44 C 42.957031 44.019531 43.070313 44.019531 43.179688 44 L 44 44 L 44 43.175781 C 44.019531 43.066406 44.019531 42.957031 44 42.847656 L 44 27 C 44.003906 26.730469 43.898438 26.46875 43.707031 26.277344 C 43.515625 26.085938 43.253906 25.980469 42.984375 25.984375 C 42.433594 25.996094 41.992188 26.449219 42 27 L 42 40.585938 L 7.707031 6.292969 C 7.519531 6.097656 7.261719 5.992188 6.992188 5.992188 Z',), stroke=())

icons8_up_left_50 = VectorIcon(fill=('M 6.992188 5.992188 C 6.945313 5.992188 6.902344 5.992188 6.859375 6 L 6 6 L 6 6.863281 C 5.988281 6.953125 5.988281 7.039063 6 7.128906 L 6 23 C 5.996094 23.359375 6.183594 23.695313 6.496094 23.878906 C 6.808594 24.058594 7.191406 24.058594 7.503906 23.878906 C 7.816406 23.695313 8.003906 23.359375 8 23 L 8 9.414063 L 42.292969 43.707031 C 42.542969 43.96875 42.917969 44.074219 43.265625 43.980469 C 43.617188 43.890625 43.890625 43.617188 43.980469 43.265625 C 44.074219 42.917969 43.96875 42.542969 43.707031 42.292969 L 9.414063 8 L 23 8 C 23.359375 8.003906 23.695313 7.816406 23.878906 7.503906 C 24.058594 7.191406 24.058594 6.808594 23.878906 6.496094 C 23.695313 6.183594 23.359375 5.996094 23 6 L 7.117188 6 C 7.074219 5.992188 7.03125 5.992188 6.992188 5.992188 Z',), stroke=())

icons8_up_right_50 = VectorIcon(fill=('M 42.980469 5.992188 C 42.941406 5.992188 42.90625 5.996094 42.871094 6 L 27 6 C 26.640625 5.996094 26.304688 6.183594 26.121094 6.496094 C 25.941406 6.808594 25.941406 7.191406 26.121094 7.503906 C 26.304688 7.816406 26.640625 8.003906 27 8 L 40.585938 8 L 6.292969 42.292969 C 6.03125 42.542969 5.925781 42.917969 6.019531 43.265625 C 6.109375 43.617188 6.382813 43.890625 6.734375 43.980469 C 7.082031 44.074219 7.457031 43.96875 7.707031 43.707031 L 42 9.414063 L 42 23 C 41.996094 23.359375 42.183594 23.695313 42.496094 23.878906 C 42.808594 24.058594 43.191406 24.058594 43.503906 23.878906 C 43.816406 23.695313 44.003906 23.359375 44 23 L 44 7.125 C 44.011719 7.035156 44.011719 6.941406 44 6.851563 L 44 6 L 43.144531 6 C 43.089844 5.992188 43.035156 5.988281 42.980469 5.992188 Z',), stroke=())

icons8_administrative_tools_50 = VectorIcon(fill=('M 20.09375 0 C 19.644531 0.0507813 19.285156 0.398438 19.21875 0.84375 L 18.25 6.8125 C 17.082031 7.152344 15.957031 7.585938 14.90625 8.15625 L 10 4.65625 C 9.605469 4.371094 9.066406 4.414063 8.71875 4.75 L 4.8125 8.65625 C 4.476563 9.003906 4.433594 9.542969 4.71875 9.9375 L 8.15625 14.875 C 7.574219 15.941406 7.097656 17.058594 6.75 18.25 L 0.84375 19.21875 C 0.351563 19.296875 -0.0078125 19.722656 0 20.21875 L 0 25.71875 C 0.0078125 26.195313 0.347656 26.597656 0.8125 26.6875 L 6.78125 27.75 C 7.128906 28.925781 7.578125 30.039063 8.15625 31.09375 L 4.65625 36 C 4.371094 36.394531 4.414063 36.933594 4.75 37.28125 L 8.65625 41.1875 C 9.003906 41.523438 9.542969 41.566406 9.9375 41.28125 L 14.84375 37.8125 C 15.90625 38.394531 17.035156 38.839844 18.21875 39.1875 L 19.21875 45.15625 C 19.296875 45.648438 19.722656 46.007813 20.21875 46 L 25.71875 46 C 25.816406 45.992188 25.910156 45.972656 26 45.9375 L 26 49 C 26 49.550781 26.449219 50 27 50 L 49 50 C 49.550781 50 50 49.550781 50 49 L 50 33 C 50 32.96875 50 32.9375 50 32.90625 L 50 31.84375 C 50 30.285156 48.714844 29 47.15625 29 L 38.78125 29 C 38.933594 28.585938 39.089844 28.152344 39.21875 27.75 L 45.15625 26.6875 C 45.636719 26.613281 45.992188 26.203125 46 25.71875 L 46 20.21875 C 46.007813 19.722656 45.648438 19.296875 45.15625 19.21875 L 39.15625 18.25 C 38.8125 17.09375 38.347656 15.980469 37.78125 14.9375 L 41.28125 9.9375 C 41.566406 9.542969 41.523438 9.003906 41.1875 8.65625 L 37.28125 4.75 C 36.933594 4.414063 36.394531 4.371094 36 4.65625 L 31.09375 8.1875 C 30.042969 7.609375 28.925781 7.160156 27.75 6.8125 L 26.6875 0.8125 C 26.597656 0.347656 26.195313 0.0078125 25.71875 0 L 20.21875 0 C 20.175781 -0.00390625 20.136719 -0.00390625 20.09375 0 Z M 21.0625 2 L 24.875 2 L 25.875 7.6875 C 25.945313 8.0625 26.222656 8.367188 26.59375 8.46875 C 28.054688 8.832031 29.433594 9.429688 30.6875 10.1875 C 31.027344 10.394531 31.457031 10.382813 31.78125 10.15625 L 36.46875 6.78125 L 39.15625 9.46875 L 35.84375 14.21875 C 35.605469 14.539063 35.582031 14.96875 35.78125 15.3125 C 36.53125 16.5625 37.105469 17.917969 37.46875 19.375 C 37.5625 19.765625 37.882813 20.0625 38.28125 20.125 L 44 21.0625 L 44 24.875 L 38.28125 25.875 C 37.882813 25.9375 37.5625 26.234375 37.46875 26.625 C 37.351563 27.101563 36.96875 28.160156 36.65625 29 L 28.84375 29 C 28.824219 29 28.800781 29 28.78125 29 C 30.359375 27.480469 31.34375 25.351563 31.34375 23 C 31.34375 18.410156 27.589844 14.65625 23 14.65625 C 18.410156 14.65625 14.65625 18.410156 14.65625 23 C 14.65625 27.589844 18.410156 31.34375 23 31.34375 C 24.148438 31.34375 25.253906 31.109375 26.25 30.6875 C 26.089844 31.042969 26 31.429688 26 31.84375 L 26 32.8125 C 25.996094 32.855469 25.996094 32.894531 26 32.9375 L 26 38.46875 L 24.875 44 L 21.0625 44 L 20.125 38.34375 C 20.0625 37.945313 19.765625 37.625 19.375 37.53125 C 17.910156 37.171875 16.511719 36.601563 15.25 35.84375 C 14.910156 35.636719 14.480469 35.648438 14.15625 35.875 L 9.46875 39.15625 L 6.78125 36.46875 L 10.09375 31.8125 C 10.320313 31.488281 10.332031 31.058594 10.125 30.71875 C 9.359375 29.453125 8.800781 28.09375 8.4375 26.625 C 8.34375 26.234375 8.023438 25.9375 7.625 25.875 L 2 24.875 L 2 21.0625 L 7.625 20.125 C 8.023438 20.0625 8.34375 19.765625 8.4375 19.375 C 8.804688 17.898438 9.394531 16.515625 10.15625 15.25 C 10.363281 14.910156 10.351563 14.480469 10.125 14.15625 L 6.8125 9.46875 L 9.53125 6.78125 L 14.1875 10.09375 C 14.507813 10.332031 14.9375 10.355469 15.28125 10.15625 C 16.535156 9.402344 17.910156 8.828125 19.375 8.46875 C 19.765625 8.375 20.0625 8.054688 20.125 7.65625 Z M 23 16.65625 C 26.507813 16.65625 29.34375 19.492188 29.34375 23 C 29.34375 26.507813 26.507813 29.34375 23 29.34375 C 19.492188 29.34375 16.65625 26.507813 16.65625 23 C 16.65625 19.492188 19.492188 16.65625 23 16.65625 Z M 28.84375 31 L 37.0625 31 C 37.253906 31.058594 37.464844 31.058594 37.65625 31 L 47.15625 31 C 47.636719 31 48 31.363281 48 31.84375 L 48 32 L 28 32 L 28 31.84375 C 28 31.363281 28.363281 31 28.84375 31 Z M 28 34 L 48 34 L 48 48 L 28 48 L 28 38.59375 C 28.042969 38.429688 28.042969 38.257813 28 38.09375 Z M 37 34.59375 L 36.28125 35.28125 L 32.9375 38.625 L 31.65625 37.53125 L 30.90625 36.875 L 29.59375 38.40625 L 30.34375 39.03125 L 32.34375 40.75 L 33.0625 41.375 L 37.71875 36.71875 L 38.40625 36 Z M 37 39.59375 L 36.28125 40.28125 L 32.9375 43.625 L 31.65625 42.53125 L 30.90625 41.875 L 29.59375 43.40625 L 30.34375 44.03125 L 32.34375 45.75 L 33.0625 46.375 L 37.71875 41.71875 L 38.40625 41 Z',), stroke=())

icons8_rotate_left_50 = VectorIcon(fill=('M 15 3 L 15 5 L 16 5 L 16 3 Z M 12.84375 3.4375 L 12 3.65625 L 11.96875 3.6875 L 11.9375 3.6875 L 11.09375 4 L 11.0625 4 L 11.03125 4.03125 L 10.9375 4.0625 L 11.78125 5.875 L 11.8125 5.875 L 11.875 5.84375 L 12.5625 5.59375 L 12.625 5.5625 L 13.40625 5.34375 Z M 20 4 L 20 12 L 22 12 L 22 6.78125 C 25.03125 8.761719 27 12.0625 27 16 C 27 22.054688 22.054688 27 16 27 C 9.945313 27 5 22.054688 5 16 L 5 15 L 3 15 L 3 16 C 3 23.144531 8.855469 29 16 29 C 23.144531 29 29 23.144531 29 16 C 29 11.941406 27.203125 8.386719 24.34375 6 L 28 6 L 28 4 Z M 9.15625 5 L 8.625 5.34375 L 8.59375 5.375 L 8.5625 5.375 L 7.875 5.90625 L 7.84375 5.9375 L 7.8125 5.9375 L 7.53125 6.1875 L 8.84375 7.6875 L 9.0625 7.5 L 9.125 7.46875 L 9.6875 7.03125 L 9.75 7 L 10.21875 6.6875 Z M 6.09375 7.59375 L 5.875 7.875 L 5.8125 7.9375 L 5.28125 8.625 L 5.28125 8.65625 L 5.25 8.6875 L 4.90625 9.21875 L 6.59375 10.3125 L 6.875 9.84375 L 6.9375 9.78125 L 7.375 9.1875 L 7.40625 9.15625 L 7.625 8.90625 Z M 3.96875 11 L 3.9375 11.125 L 3.90625 11.15625 L 3.90625 11.1875 L 3.59375 12 L 3.59375 12.03125 L 3.5625 12.09375 L 3.34375 12.9375 L 5.25 13.46875 L 5.46875 12.6875 L 5.5 12.625 L 5.75 11.9375 L 5.78125 11.875 L 5.78125 11.84375 Z',), stroke=())

icons8_rotate_right_50 = VectorIcon(fill=('M 16 3 L 16 5 L 17 5 L 17 3 Z M 19.15625 3.4375 L 18.59375 5.34375 L 19.375 5.5625 L 19.4375 5.59375 L 20.125 5.84375 L 20.1875 5.875 L 20.21875 5.875 L 21.0625 4.0625 L 20.96875 4.03125 L 20.9375 4 L 20.90625 4 L 20.0625 3.6875 L 20.03125 3.6875 L 20 3.65625 Z M 4 4 L 4 6 L 7.65625 6 C 4.796875 8.386719 3 11.941406 3 16 C 3 23.144531 8.855469 29 16 29 C 23.144531 29 29 23.144531 29 16 L 29 15 L 27 15 L 27 16 C 27 22.054688 22.054688 27 16 27 C 9.945313 27 5 22.054688 5 16 C 5 12.0625 6.96875 8.761719 10 6.78125 L 10 12 L 12 12 L 12 4 Z M 22.84375 5 L 21.78125 6.6875 L 22.25 7 L 22.3125 7.03125 L 22.875 7.46875 L 22.9375 7.5 L 23.15625 7.6875 L 24.46875 6.1875 L 24.1875 5.9375 L 24.15625 5.9375 L 24.125 5.90625 L 23.4375 5.375 L 23.40625 5.375 L 23.375 5.34375 Z M 25.90625 7.59375 L 24.375 8.90625 L 24.59375 9.15625 L 24.625 9.1875 L 25.0625 9.78125 L 25.125 9.84375 L 25.40625 10.3125 L 27.09375 9.21875 L 26.75 8.6875 L 26.71875 8.65625 L 26.71875 8.625 L 26.1875 7.9375 L 26.125 7.875 Z M 28.03125 11 L 26.21875 11.84375 L 26.21875 11.875 L 26.25 11.9375 L 26.5 12.625 L 26.53125 12.6875 L 26.75 13.46875 L 28.65625 12.9375 L 28.4375 12.09375 L 28.40625 12.03125 L 28.40625 12 L 28.09375 11.1875 L 28.09375 11.15625 L 28.0625 11.125 Z',), stroke=())

icons8_home_filled_50 = VectorIcon(fill=('M 25 1.0507812 C 24.7825 1.0507812 24.565859 1.1197656 24.380859 1.2597656 L 1.3808594 19.210938 C 0.95085938 19.550938 0.8709375 20.179141 1.2109375 20.619141 C 1.5509375 21.049141 2.1791406 21.129062 2.6191406 20.789062 L 4 19.710938 L 4 46 C 4 46.55 4.45 47 5 47 L 19 47 L 19 29 L 31 29 L 31 47 L 45 47 C 45.55 47 46 46.55 46 46 L 46 19.710938 L 47.380859 20.789062 C 47.570859 20.929063 47.78 21 48 21 C 48.3 21 48.589063 20.869141 48.789062 20.619141 C 49.129063 20.179141 49.049141 19.550938 48.619141 19.210938 L 25.619141 1.2597656 C 25.434141 1.1197656 25.2175 1.0507812 25 1.0507812 z M 35 5 L 35 6.0507812 L 41 10.730469 L 41 5 L 35 5 z',), stroke=())

icons8_copy_50 = VectorIcon(fill=('M 19 0 L 19 6 L 21 8 L 21 2 L 36 2 L 36 14 L 48 14 L 48 40 L 33 40 L 33 42 L 50 42 L 50 12.59375 L 37.40625 0 Z M 38 3.40625 L 46.59375 12 L 38 12 Z M 0 8 L 0 50 L 31 50 L 31 20.59375 L 30.71875 20.28125 L 18.71875 8.28125 L 18.40625 8 Z M 2 10 L 17 10 L 17 22 L 29 22 L 29 48 L 2 48 Z M 19 11.4375 L 27.5625 20 L 19 20 Z',), stroke=())

icons8_paste_50 = VectorIcon(fill=('M 14.8125 0 C 14.335938 0.0898438 13.992188 0.511719 14 1 L 14 2 L 5.90625 2 C 4.304688 2 3 3.304688 3 4.90625 L 3 43 C 3 44.644531 4.304688 46 5.90625 46 L 16 46 L 16 44 L 5.90625 44 C 5.507813 44 5 43.554688 5 43 L 5 4.90625 C 5 4.507813 5.507813 4 5.90625 4 L 14 4 L 14 6 L 7 6 L 7 42 L 16 42 L 16 40 L 9 40 L 9 8 L 14 8 L 14 9 C 14 9.550781 14.449219 10 15 10 L 29 10 C 29.550781 10 30 9.550781 30 9 L 30 8 L 35 8 L 35 14 L 37 14 L 37 6 L 30 6 L 30 4 L 38.09375 4 C 38.492188 4 39 4.507813 39 4.90625 L 39 14 L 41 14 L 41 4.90625 C 41 3.304688 39.695313 2 38.09375 2 L 30 2 L 30 1 C 30 0.449219 29.550781 0 29 0 L 15 0 C 14.96875 0 14.9375 0 14.90625 0 C 14.875 0 14.84375 0 14.8125 0 Z M 16 2 L 28 2 L 28 8 L 16 8 Z M 17.8125 15 C 17.335938 15.089844 16.992188 15.511719 17 16 L 17 49 C 17 49.550781 17.449219 50 18 50 L 46 50 C 46.550781 50 47 49.550781 47 49 L 47 16 C 47 15.449219 46.550781 15 46 15 L 18 15 C 17.96875 15 17.9375 15 17.90625 15 C 17.875 15 17.84375 15 17.8125 15 Z M 19 17 L 45 17 L 45 48 L 19 48 Z M 23.71875 23 C 23.167969 23.078125 22.78125 23.589844 22.859375 24.140625 C 22.9375 24.691406 23.449219 25.078125 24 25 L 41 25 C 41.359375 25.003906 41.695313 24.816406 41.878906 24.503906 C 42.058594 24.191406 42.058594 23.808594 41.878906 23.496094 C 41.695313 23.183594 41.359375 22.996094 41 23 L 24 23 C 23.96875 23 23.9375 23 23.90625 23 C 23.875 23 23.84375 23 23.8125 23 C 23.78125 23 23.75 23 23.71875 23 Z M 23.71875 29 C 23.167969 29.078125 22.78125 29.589844 22.859375 30.140625 C 22.9375 30.691406 23.449219 31.078125 24 31 L 36 31 C 36.359375 31.003906 36.695313 30.816406 36.878906 30.503906 C 37.058594 30.191406 37.058594 29.808594 36.878906 29.496094 C 36.695313 29.183594 36.359375 28.996094 36 29 L 24 29 C 23.96875 29 23.9375 29 23.90625 29 C 23.875 29 23.84375 29 23.8125 29 C 23.78125 29 23.75 29 23.71875 29 Z M 23.71875 35 C 23.167969 35.078125 22.78125 35.589844 22.859375 36.140625 C 22.9375 36.691406 23.449219 37.078125 24 37 L 41 37 C 41.359375 37.003906 41.695313 36.816406 41.878906 36.503906 C 42.058594 36.191406 42.058594 35.808594 41.878906 35.496094 C 41.695313 35.183594 41.359375 34.996094 41 35 L 24 35 C 23.96875 35 23.9375 35 23.90625 35 C 23.875 35 23.84375 35 23.8125 35 C 23.78125 35 23.75 35 23.71875 35 Z M 23.71875 41 C 23.167969 41.078125 22.78125 41.589844 22.859375 42.140625 C 22.9375 42.691406 23.449219 43.078125 24 43 L 36 43 C 36.359375 43.003906 36.695313 42.816406 36.878906 42.503906 C 37.058594 42.191406 37.058594 41.808594 36.878906 41.496094 C 36.695313 41.183594 36.359375 40.996094 36 41 L 24 41 C 23.96875 41 23.9375 41 23.90625 41 C 23.875 41 23.84375 41 23.8125 41 C 23.78125 41 23.75 41 23.71875 41 Z',), stroke=())

icons8_fence = VectorIcon(fill=('M14.3,86c-1.7,0-3,1.3-3,3s1.3,3,3,3h5.3v14.7c0,1.7,1.3,3,3,3h17.8c1.7,0,3-1.3,3-3V92h8.2v14.7c0,1.7,1.3,3,3,3h17.8 c1.7,0,3-1.3,3-3V92h8.2v14.7c0,1.7,1.3,3,3,3h17.8c1.7,0,3-1.3,3-3V92h5.2c1.7,0,3-1.3,3-3s-1.3-3-3-3h-5.2V53.3h5.2 c1.7,0,3-1.3,3-3s-1.3-3-3-3h-5.2V30.2c0-0.8-0.3-1.6-0.9-2.1l-8.9-8.9c-1.1-1.1-3.1-1.1-4.2,0l-8.9,8.9c-0.6,0.6-0.9,1.3-0.9,2.1 v17.1h-8.2V30.2c0-0.8-0.3-1.6-0.9-2.1l-8.9-8.9c-1.1-1.1-3.1-1.1-4.2,0l-8.9,8.9c-0.6,0.6-0.9,1.3-0.9,2.1v17.1h-8.2V30.2 c0-0.8-0.3-1.6-0.9-2.1l-8.9-8.9c-1.1-1.1-3.1-1.1-4.2,0l-8.9,8.9c-0.6,0.6-0.9,1.3-0.9,2.1v17.1h-5.3c-1.7,0-3,1.3-3,3s1.3,3,3,3 h5.3V86H14.3z M89.6,31.4l5.9-5.9l5.9,5.9v72.3H89.6V31.4z M75.3,53.3h8.2V86h-8.2V53.3z M57.6,31.4l5.9-5.9l5.9,5.9v72.3H57.6 V31.4z M43.4,53.3h8.2V86h-8.2V53.3z M25.6,31.4l5.9-5.9l5.9,5.9v72.3H25.6V31.4z',), stroke=())

icons8_center_of_gravity_50 = VectorIcon(fill=('M 24.90625 -0.03125 C 24.863281 -0.0234375 24.820313 -0.0117188 24.78125 0 C 24.316406 0.105469 23.988281 0.523438 24 1 L 24 10.03125 C 21.808594 10.175781 19.65625 10.800781 17.71875 11.875 C 17.160156 12.1875 16.75 12.546875 16.375 12.8125 C 15.917969 13.132813 15.804688 13.761719 16.125 14.21875 C 16.445313 14.675781 17.074219 14.789063 17.53125 14.46875 C 17.992188 14.144531 18.339844 13.816406 18.6875 13.625 C 20.328125 12.714844 22.148438 12.171875 24 12.03125 L 24 24 L 12.03125 24 C 12.097656 23.144531 12.257813 22.285156 12.5 21.4375 C 12.90625 20.015625 13.585938 18.703125 14.4375 17.5 C 14.675781 17.179688 14.703125 16.753906 14.507813 16.40625 C 14.308594 16.0625 13.925781 15.863281 13.53125 15.90625 C 13.238281 15.9375 12.976563 16.097656 12.8125 16.34375 C 11.855469 17.695313 11.074219 19.199219 10.59375 20.875 C 10.300781 21.90625 10.132813 22.949219 10.0625 24 L 1 24 C 0.96875 24 0.9375 24 0.90625 24 C 0.355469 24.027344 -0.0742188 24.496094 -0.046875 25.046875 C -0.0195313 25.597656 0.449219 26.027344 1 26 L 10.0625 26 C 10.207031 28.179688 10.816406 30.320313 11.90625 32.28125 C 12.1875 32.792969 12.476563 33.261719 12.78125 33.6875 C 13.101563 34.144531 13.730469 34.257813 14.1875 33.9375 C 14.644531 33.617188 14.757813 32.988281 14.4375 32.53125 C 14.148438 32.121094 13.878906 31.714844 13.65625 31.3125 C 12.730469 29.640625 12.207031 27.839844 12.0625 26 L 24 26 L 24 37.96875 C 21.632813 37.777344 19.398438 36.910156 17.5 35.5625 C 17.042969 35.242188 16.414063 35.355469 16.09375 35.8125 C 15.773438 36.269531 15.886719 36.898438 16.34375 37.21875 C 18.566406 38.796875 21.203125 39.746094 24 39.9375 L 24 49 C 23.996094 49.359375 24.183594 49.695313 24.496094 49.878906 C 24.808594 50.058594 25.191406 50.058594 25.503906 49.878906 C 25.816406 49.695313 26.003906 49.359375 26 49 L 26 39.96875 C 28.191406 39.824219 30.34375 39.199219 32.28125 38.125 C 32.839844 37.8125 33.246094 37.453125 33.625 37.1875 C 34.019531 36.941406 34.191406 36.457031 34.042969 36.019531 C 33.894531 35.578125 33.460938 35.300781 33 35.34375 C 32.808594 35.355469 32.625 35.417969 32.46875 35.53125 C 32.011719 35.855469 31.664063 36.179688 31.3125 36.375 C 29.671875 37.285156 27.851563 37.828125 26 37.96875 L 26 26 L 37.96875 26 C 37.902344 26.855469 37.742188 27.714844 37.5 28.5625 C 37.09375 29.984375 36.414063 31.296875 35.5625 32.5 C 35.320313 32.789063 35.261719 33.1875 35.410156 33.53125 C 35.558594 33.878906 35.886719 34.113281 36.261719 34.136719 C 36.636719 34.164063 36.992188 33.976563 37.1875 33.65625 C 38.144531 32.304688 38.925781 30.800781 39.40625 29.125 C 39.699219 28.09375 39.867188 27.050781 39.9375 26 L 49 26 C 49.359375 26.003906 49.695313 25.816406 49.878906 25.503906 C 50.058594 25.191406 50.058594 24.808594 49.878906 24.496094 C 49.695313 24.183594 49.359375 23.996094 49 24 L 39.9375 24 C 39.792969 21.820313 39.183594 19.679688 38.09375 17.71875 C 37.8125 17.207031 37.523438 16.738281 37.21875 16.3125 C 36.984375 15.96875 36.558594 15.808594 36.15625 15.90625 C 35.828125 15.980469 35.558594 16.210938 35.4375 16.527344 C 35.316406 16.84375 35.363281 17.195313 35.5625 17.46875 C 35.851563 17.878906 36.121094 18.285156 36.34375 18.6875 C 37.269531 20.359375 37.792969 22.160156 37.9375 24 L 26 24 L 26 12.03125 C 28.367188 12.222656 30.601563 13.089844 32.5 14.4375 C 32.957031 14.757813 33.585938 14.644531 33.90625 14.1875 C 34.226563 13.730469 34.113281 13.101563 33.65625 12.78125 C 31.433594 11.203125 28.796875 10.253906 26 10.0625 L 26 1 C 26.011719 0.710938 25.894531 0.433594 25.6875 0.238281 C 25.476563 0.0390625 25.191406 -0.0585938 24.90625 -0.03125 Z',), stroke=())

icons8_lock = VectorIcon(fill=('M 16 3 C 12.15625 3 9 6.15625 9 10 L 9 13 L 6 13 L 6 29 L 26 29 L 26 13 L 23 13 L 23 10 C 23 6.15625 19.84375 3 16 3 Z M 16 5 C 18.753906 5 21 7.246094 21 10 L 21 13 L 11 13 L 11 10 C 11 7.246094 13.246094 5 16 5 Z M 8 15 L 24 15 L 24 27 L 8 27 Z',), stroke=())

icons8_ungroup_objects_50 = VectorIcon(fill=('M 6 6 L 6 12 L 8 12 L 8 29 L 6 29 L 6 35 L 12 35 L 12 33 L 17 33 L 17 38 L 15 38 L 15 44 L 21 44 L 21 42 L 38 42 L 38 44 L 44 44 L 44 38 L 42 38 L 42 21 L 44 21 L 44 15 L 38 15 L 38 17 L 33 17 L 33 12 L 35 12 L 35 6 L 29 6 L 29 8 L 12 8 L 12 6 Z M 8 8 L 10 8 L 10 10 L 8 10 Z M 31 8 L 33 8 L 33 10 L 31 10 Z M 12 10 L 29 10 L 29 12 L 31 12 L 31 29 L 29 29 L 29 31 L 12 31 L 12 29 L 10 29 L 10 12 L 12 12 Z M 40 17 L 42 17 L 42 19 L 40 19 Z M 33 19 L 38 19 L 38 21 L 40 21 L 40 38 L 38 38 L 38 40 L 21 40 L 21 38 L 19 38 L 19 33 L 29 33 L 29 35 L 35 35 L 35 29 L 33 29 Z M 8 31 L 10 31 L 10 33 L 8 33 Z M 31 31 L 33 31 L 33 33 L 31 33 Z M 17 40 L 19 40 L 19 42 L 17 42 Z M 40 40 L 42 40 L 42 42 L 40 42 Z',), stroke=())

icons8_group_objects_50 = VectorIcon(fill=('M 3 3 L 3 4 L 3 11 L 6 11 L 6 39 L 3 39 L 3 47 L 11 47 L 11 46 L 11 44 L 39 44 L 39 47 L 47 47 L 47 46 L 47 39 L 44 39 L 44 11 L 47 11 L 47 10 L 47 3 L 39 3 L 39 6 L 11 6 L 11 3 L 3 3 z M 5 5 L 9 5 L 9 9 L 5 9 L 5 5 z M 41 5 L 45 5 L 45 9 L 43 9 L 41 9 L 41 7 L 41 5 z M 11 8 L 39 8 L 39 11 L 42 11 L 42 39 L 39 39 L 39 42 L 11 42 L 11 39 L 8 39 L 8 11 L 11 11 L 11 8 z M 13 13 L 13 14 L 13 29 L 21 29 L 21 37 L 37 37 L 37 21 L 29 21 L 29 13 L 13 13 z M 15 15 L 27 15 L 27 27 L 15 27 L 15 15 z M 29 23 L 35 23 L 35 35 L 23 35 L 23 29 L 29 29 L 29 23 z M 5 41 L 7 41 L 9 41 L 9 43 L 9 45 L 5 45 L 5 41 z M 41 41 L 43 41 L 45 41 L 45 45 L 41 45 L 41 43 L 41 41 z',), stroke=())

icons_evenspace_vert = VectorIcon(fill=('M6,13.5A1.50164,1.50164,0,0,0,4.5,15v2A1.50164,1.50164,0,0,0,6,18.5H18A1.50164,1.50164,0,0,0,19.5,17V15A1.50164,1.50164,0,0,0,18,13.5ZM18.5,15v2a.50065.50065,0,0,1-.5.5H6a.50065.50065,0,0,1-.5-.5V15a.50065.50065,0,0,1,.5-.5H18A.50065.50065,0,0,1,18.5,15ZM15,6.5A1.50164,1.50164,0,0,0,16.5,5V3A1.50164,1.50164,0,0,0,15,1.5H9A1.50164,1.50164,0,0,0,7.5,3V5A1.50164,1.50164,0,0,0,9,6.5ZM8.5,5V3A.50065.50065,0,0,1,9,2.5h6a.50065.50065,0,0,1,.5.5V5a.50065.50065,0,0,1-.5.5H9A.50065.50065,0,0,1,8.5,5Zm-6,17a.49971.49971,0,0,1,.5-.5H21a.5.5,0,0,1,0,1H3A.49971.49971,0,0,1,2.5,22ZM3,9.5H21a.5.5,0,0,1,0,1H3a.5.5,0,0,1,0-1Z',), stroke=())

icons_evenspace_horiz = VectorIcon(fill=('M7,4.5A1.50164,1.50164,0,0,0,5.5,6V18A1.50164,1.50164,0,0,0,7,19.5H9A1.50164,1.50164,0,0,0,10.5,18V6A1.50164,1.50164,0,0,0,9,4.5ZM9.5,6V18a.50065.50065,0,0,1-.5.5H7a.50065.50065,0,0,1-.5-.5V6A.50065.50065,0,0,1,7,5.5H9A.50065.50065,0,0,1,9.5,6ZM21,7.5H19A1.50164,1.50164,0,0,0,17.5,9v6A1.50164,1.50164,0,0,0,19,16.5h2A1.50164,1.50164,0,0,0,22.5,15V9A1.50164,1.50164,0,0,0,21,7.5Zm.5,7.5a.50065.50065,0,0,1-.5.5H19a.50065.50065,0,0,1-.5-.5V9a.50065.50065,0,0,1,.5-.5h2a.50065.50065,0,0,1,.5.5ZM2.5,3V21a.5.5,0,0,1-1,0V3a.5.5,0,0,1,1,0ZM14,2.5a.49971.49971,0,0,1,.5.5V21a.5.5,0,0,1-1,0V3A.49971.49971,0,0,1,14,2.5Z',), stroke=())

icons8_measure_50 = VectorIcon(fill=('M 35.0625 1.5 C 34.835938 1.53125 34.625 1.644531 34.46875 1.8125 L 1.875 34.40625 C 1.488281 34.796875 1.488281 35.421875 1.875 35.8125 L 14.09375 48.03125 C 14.28125 48.226563 14.542969 48.335938 14.8125 48.335938 C 15.082031 48.335938 15.34375 48.226563 15.53125 48.03125 L 48.125 15.4375 C 48.511719 15.046875 48.511719 14.421875 48.125 14.03125 L 35.90625 1.8125 C 35.859375 1.753906 35.808594 1.703125 35.75 1.65625 C 35.574219 1.542969 35.367188 1.488281 35.15625 1.5 C 35.125 1.5 35.09375 1.5 35.0625 1.5 Z M 35.1875 3.9375 L 46 14.75 L 14.8125 45.90625 L 4 35.125 L 6.84375 32.28125 L 9.28125 34.71875 L 10.71875 33.28125 L 8.28125 30.84375 L 10.84375 28.28125 L 16.28125 33.71875 L 17.71875 32.28125 L 12.28125 26.84375 L 14.84375 24.28125 L 17.28125 26.71875 L 18.71875 25.28125 L 16.28125 22.84375 L 18.84375 20.28125 L 24.28125 25.71875 L 25.71875 24.28125 L 20.28125 18.84375 L 22.84375 16.28125 L 25.28125 18.71875 L 26.71875 17.28125 L 24.28125 14.84375 L 26.84375 12.28125 L 32.28125 17.71875 L 33.71875 16.28125 L 28.28125 10.84375 L 30.84375 8.28125 L 33.28125 10.71875 L 34.71875 9.28125 L 32.28125 6.84375 Z',), stroke=())

icons8_unlock = VectorIcon(fill=('M 16 3 C 12.964844 3 10.414063 4.964844 9.375 7.625 L 11.21875 8.375 C 11.976563 6.433594 13.835938 5 16 5 C 18.753906 5 21 7.246094 21 10 L 21 13 L 6 13 L 6 29 L 26 29 L 26 13 L 23 13 L 23 10 C 23 6.15625 19.84375 3 16 3 Z M 8 15 L 24 15 L 24 27 L 8 27 Z',), stroke=())

icons8_keyboard_50 = VectorIcon(fill=('M 36.9375 2.84375 C 36.9375 5.9375 36.214844 7.304688 35.28125 8.0625 C 34.347656 8.820313 32.925781 9.058594 31.3125 9.28125 C 29.699219 9.503906 27.898438 9.710938 26.40625 10.90625 C 25.167969 11.898438 24.3125 13.539063 24.0625 16 L 4 16 C 1.800781 16 0 17.800781 0 20 L 0 40 C 0 42.199219 1.800781 44 4 44 L 46 44 C 48.199219 44 50 42.199219 50 40 L 50 20 C 50 17.800781 48.199219 16 46 16 L 26.09375 16 C 26.308594 14.0625 26.910156 13.066406 27.65625 12.46875 C 28.585938 11.722656 29.976563 11.503906 31.59375 11.28125 C 33.210938 11.058594 35.039063 10.839844 36.53125 9.625 C 38.023438 8.410156 38.9375 6.269531 38.9375 2.84375 Z M 4 18 L 46 18 C 47.117188 18 48 18.882813 48 20 L 48 40 C 48 41.117188 47.117188 42 46 42 L 4 42 C 2.882813 42 2 41.117188 2 40 L 2 20 C 2 18.882813 2.882813 18 4 18 Z M 5 22 L 5 26 L 9 26 L 9 22 Z M 11 22 L 11 26 L 15 26 L 15 22 Z M 17 22 L 17 26 L 21 26 L 21 22 Z M 23 22 L 23 26 L 27 26 L 27 22 Z M 29 22 L 29 26 L 33 26 L 33 22 Z M 35 22 L 35 26 L 39 26 L 39 22 Z M 41 22 L 41 26 L 45 26 L 45 22 Z M 5 28 L 5 32 L 12 32 L 12 28 Z M 14 28 L 14 32 L 18 32 L 18 28 Z M 20 28 L 20 32 L 24 32 L 24 28 Z M 26 28 L 26 32 L 30 32 L 30 28 Z M 32 28 L 32 32 L 36 32 L 36 28 Z M 38 28 L 38 32 L 45 32 L 45 28 Z M 5 34 L 5 38 L 9 38 L 9 34 Z M 11 34 L 11 38 L 15 38 L 15 34 Z M 17 34 L 17 38 L 33 38 L 33 34 Z M 35 34 L 35 38 L 39 38 L 39 34 Z M 41 34 L 41 38 L 45 38 L 45 34 Z',), stroke=())

icons8_caret_up = VectorIcon(fill=('M 24.96875 13 C 24.449219 13.007813 23.953125 13.21875 23.585938 13.585938 L 3.585938 33.585938 C 3.0625 34.085938 2.851563 34.832031 3.035156 35.535156 C 3.21875 36.234375 3.765625 36.78125 4.464844 36.964844 C 5.167969 37.148438 5.914063 36.9375 6.414063 36.414063 L 25 17.828125 L 43.585938 36.414063 C 44.085938 36.9375 44.832031 37.148438 45.535156 36.964844 C 46.234375 36.78125 46.78125 36.234375 46.964844 35.535156 C 47.148438 34.832031 46.9375 34.085938 46.414063 33.585938 L 26.414063 13.585938 C 26.03125 13.203125 25.511719 12.992188 24.96875 13 Z',), stroke=())

icons8_caret_down = VectorIcon(fill=('M 44.984375 12.96875 C 44.453125 12.984375 43.953125 13.203125 43.585938 13.585938 L 25 32.171875 L 6.414063 13.585938 C 6.035156 13.199219 5.519531 12.980469 4.976563 12.980469 C 4.164063 12.980469 3.433594 13.476563 3.128906 14.230469 C 2.820313 14.984375 3.003906 15.847656 3.585938 16.414063 L 23.585938 36.414063 C 24.367188 37.195313 25.632813 37.195313 26.414063 36.414063 L 46.414063 16.414063 C 47.007813 15.84375 47.195313 14.964844 46.875 14.203125 C 46.558594 13.441406 45.808594 12.953125 44.984375 12.96875 Z',), stroke=())

icons8_caret_left = VectorIcon(fill=('M 34.960938 2.980469 C 34.441406 2.996094 33.949219 3.214844 33.585938 3.585938 L 13.585938 23.585938 C 12.804688 24.367188 12.804688 25.632813 13.585938 26.414063 L 33.585938 46.414063 C 34.085938 46.9375 34.832031 47.148438 35.535156 46.964844 C 36.234375 46.78125 36.78125 46.234375 36.964844 45.535156 C 37.148438 44.832031 36.9375 44.085938 36.414063 43.585938 L 17.828125 25 L 36.414063 6.414063 C 37.003906 5.839844 37.183594 4.960938 36.863281 4.199219 C 36.539063 3.441406 35.785156 2.957031 34.960938 2.980469 Z',), stroke=())

icons8_caret_right = VectorIcon(fill=('M 14.980469 2.980469 C 14.164063 2.980469 13.433594 3.476563 13.128906 4.230469 C 12.820313 4.984375 13.003906 5.847656 13.585938 6.414063 L 32.171875 25 L 13.585938 43.585938 C 13.0625 44.085938 12.851563 44.832031 13.035156 45.535156 C 13.21875 46.234375 13.765625 46.78125 14.464844 46.964844 C 15.167969 47.148438 15.914063 46.9375 16.414063 46.414063 L 36.414063 26.414063 C 37.195313 25.632813 37.195313 24.367188 36.414063 23.585938 L 16.414063 3.585938 C 16.035156 3.199219 15.519531 2.980469 14.980469 2.980469 Z',), stroke=())

icons8_delete_50 = VectorIcon(fill=('M 7.71875 6.28125 L 6.28125 7.71875 L 23.5625 25 L 6.28125 42.28125 L 7.71875 43.71875 L 25 26.4375 L 42.28125 43.71875 L 43.71875 42.28125 L 26.4375 25 L 43.71875 7.71875 L 42.28125 6.28125 L 25 23.5625 Z',), stroke=())

icons8_constraint_50 = VectorIcon(fill=('M14.3,86c-1.7,0-3,1.3-3,3s1.3,3,3,3h5.3v14.7c0,1.7,1.3,3,3,3h17.8c1.7,0,3-1.3,3-3V92h8.2v14.7c0,1.7,1.3,3,3,3h17.8 c1.7,0,3-1.3,3-3V92h8.2v14.7c0,1.7,1.3,3,3,3h17.8c1.7,0,3-1.3,3-3V92h5.2c1.7,0,3-1.3,3-3s-1.3-3-3-3h-5.2V53.3h5.2 c1.7,0,3-1.3,3-3s-1.3-3-3-3h-5.2V30.2c0-0.8-0.3-1.6-0.9-2.1l-8.9-8.9c-1.1-1.1-3.1-1.1-4.2,0l-8.9,8.9c-0.6,0.6-0.9,1.3-0.9,2.1 v17.1h-8.2V30.2c0-0.8-0.3-1.6-0.9-2.1l-8.9-8.9c-1.1-1.1-3.1-1.1-4.2,0l-8.9,8.9c-0.6,0.6-0.9,1.3-0.9,2.1v17.1h-8.2V30.2 c0-0.8-0.3-1.6-0.9-2.1l-8.9-8.9c-1.1-1.1-3.1-1.1-4.2,0l-8.9,8.9c-0.6,0.6-0.9,1.3-0.9,2.1v17.1h-5.3c-1.7,0-3,1.3-3,3s1.3,3,3,3 h5.3V86H14.3z M89.6,31.4l5.9-5.9l5.9,5.9v72.3H89.6V31.4z M75.3,53.3h8.2V86h-8.2V53.3z M57.6,31.4l5.9-5.9l5.9,5.9v72.3H57.6 V31.4z M43.4,53.3h8.2V86h-8.2V53.3z M25.6,31.4l5.9-5.9l5.9,5.9v72.3H25.6V31.4z',), stroke=())

icons8_disconnected_50 = VectorIcon(fill=('M 43.28125 2.28125 L 38.5625 7 L 36.3125 4.75 C 35.144531 3.582031 33.601563 3 32.0625 3 C 30.523438 3 29.011719 3.582031 27.84375 4.75 L 23 9.5625 L 21.71875 8.28125 C 21.476563 8.03125 21.121094 7.925781 20.78125 8 C 20.40625 8.066406 20.105469 8.339844 20 8.703125 C 19.894531 9.070313 20.003906 9.460938 20.28125 9.71875 L 25.0625 14.5 L 18.9375 20.65625 L 20.34375 22.0625 L 26.5 15.9375 L 34.0625 23.5 L 27.9375 29.65625 L 29.34375 31.0625 L 35.5 24.9375 L 40.28125 29.71875 C 40.679688 30.117188 41.320313 30.117188 41.71875 29.71875 C 42.117188 29.320313 42.117188 28.679688 41.71875 28.28125 L 40.4375 27 L 45.21875 22.15625 C 47.554688 19.820313 47.554688 15.992188 45.21875 13.65625 L 43 11.4375 L 47.71875 6.71875 L 46.28125 5.28125 L 41.5625 10 L 40 8.4375 L 44.71875 3.71875 Z M 32.0625 4.96875 C 33.085938 4.96875 34.121094 5.371094 34.90625 6.15625 L 43.8125 15.0625 C 45.382813 16.632813 45.382813 19.148438 43.8125 20.71875 L 43.8125 20.75 L 39 25.5625 L 24.4375 11 L 29.25 6.15625 C 30.035156 5.371094 31.039063 4.96875 32.0625 4.96875 Z M 8.90625 19.96875 C 8.863281 19.976563 8.820313 19.988281 8.78125 20 C 8.40625 20.066406 8.105469 20.339844 8 20.703125 C 7.894531 21.070313 8.003906 21.460938 8.28125 21.71875 L 9.5625 23 L 4.75 27.84375 C 2.414063 30.179688 2.414063 33.976563 4.75 36.3125 L 7 38.5625 L 2.28125 43.28125 L 3.71875 44.71875 L 8.4375 40 L 10 41.5625 L 5.28125 46.28125 L 6.71875 47.71875 L 11.4375 43 L 13.6875 45.25 C 16.023438 47.585938 19.820313 47.585938 22.15625 45.25 L 27 40.4375 L 28.28125 41.71875 C 28.679688 42.117188 29.320313 42.117188 29.71875 41.71875 C 30.117188 41.320313 30.117188 40.679688 29.71875 40.28125 L 9.71875 20.28125 C 9.511719 20.058594 9.210938 19.945313 8.90625 19.96875 Z M 11 24.4375 L 25.5625 39 L 20.75 43.84375 C 19.179688 45.414063 16.664063 45.414063 15.09375 43.84375 L 6.15625 34.90625 C 4.585938 33.335938 4.585938 30.820313 6.15625 29.25 Z',), stroke=())

icons8_usb_connector_50 = VectorIcon(fill=('M 32 1 L 25 12 L 30 12 L 29.261719 41.533203 L 20.814453 37.634766 L 20.060547 32.626953 A 6 6 0 0 0 18 21 A 6 6 0 0 0 16.693359 32.851562 L 17.009766 39.199219 L 17.064453 40.310547 L 18.162109 40.816406 L 29.152344 45.888672 L 29.003906 51.806641 A 6 6 0 0 0 32 63 A 6 6 0 0 0 34.996094 51.806641 L 34.673828 38.96875 L 45.837891 33.816406 L 46.935547 33.310547 L 46.990234 32.199219 L 47.300781 26 L 51 26 L 51 16 L 41 16 L 41 26 L 43.882812 26 L 43.185547 30.634766 L 34.564453 34.613281 L 34 12 L 39 12 L 32 1 z',), stroke=())

icons8_user_location_50 = VectorIcon(fill=('M 25 2 C 16.175781 2 9 9.175781 9 18 C 9 24.34375 12.863281 31.664063 16.65625 37.5 C 20.449219 43.335938 24.25 47.65625 24.25 47.65625 C 24.441406 47.871094 24.714844 47.996094 25 47.996094 C 25.285156 47.996094 25.558594 47.871094 25.75 47.65625 C 25.75 47.65625 29.550781 43.328125 33.34375 37.5 C 37.136719 31.671875 41 24.375 41 18 C 41 9.175781 33.824219 2 25 2 Z M 25 4 C 32.742188 4 39 10.257813 39 18 C 39 23.539063 35.363281 30.742188 31.65625 36.4375 C 28.546875 41.210938 25.921875 44.355469 25 45.4375 C 24.082031 44.355469 21.457031 41.195313 18.34375 36.40625 C 14.636719 30.703125 11 23.5 11 18 C 11 10.257813 17.257813 4 25 4 Z M 25 11.84375 L 24.5 12.15625 L 17 16.65625 L 18 18.34375 L 18 26 L 32 26 L 32 18.34375 L 33 16.65625 L 25.5 12.15625 Z M 25 14.15625 L 30 17.15625 L 30 24 L 27 24 L 27 19 L 23 19 L 23 24 L 20 24 L 20 17.15625 Z',), stroke=())

icons8_choose_font_50 = VectorIcon(fill=('M 15.529297 3.9785156 A 1.50015 1.50015 0 0 0 15.259766 4 L 12 4 C 9.6666667 4 8.0772187 5.229724 7.1992188 6.4003906 C 6.3212187 7.5710573 6.0292969 8.7578125 6.0292969 8.7578125 A 1.0004595 1.0004595 0 0 0 7.9707031 9.2421875 C 7.9707031 9.2421875 8.1787814 8.4289427 8.8007812 7.5996094 C 9.4227812 6.770276 10.333333 6 12 6 L 13.833984 6 C 13.179241 8.7555904 12.600708 11.027355 12.068359 13 L 11 13 A 1.0001 1.0001 0 1 0 11 15 L 11.529297 15 C 10.768676 17.643284 10.114342 19.505472 9.5195312 20.710938 C 8.9399105 21.885618 8.4532978 22.411041 8.0644531 22.662109 C 7.6756085 22.913178 7.2720618 23 6.5 23 C 5.7812349 23 5.7988281 22.75 5.7988281 22.75 A 1.50015 1.50015 0 1 0 3.2011719 24.25 C 3.2011719 24.25 4.3747651 26 6.5 26 C 7.5469382 26 8.6766885 25.836822 9.6914062 25.181641 C 10.706124 24.526459 11.493355 23.489383 12.208984 22.039062 C 13.008367 20.419007 13.782949 18.114834 14.650391 15 L 20 15 A 1.0001 1.0001 0 1 0 20 13 L 15.1875 13 C 15.716881 10.979191 16.278508 8.7389756 16.923828 6 L 26 6 A 1.0001 1.0001 0 1 0 26 4 L 15.75 4 A 1.50015 1.50015 0 0 0 15.529297 3.9785156 z',), stroke=())

icons8_finger_50 = VectorIcon(fill=('M 17 3 C 16.0625 3 15.117188 3.3125 14.34375 3.96875 C 13.570313 4.625 13 5.675781 13 6.90625 L 13 28.4375 C 12.558594 28.597656 12.15625 28.644531 11.34375 29.34375 C 10.167969 30.359375 9 32.183594 9 34.90625 C 9 36.878906 9.785156 38.683594 10.09375 39.40625 C 10.09375 39.417969 10.09375 39.425781 10.09375 39.4375 L 12.90625 45.03125 C 12.910156 45.039063 12.902344 45.054688 12.90625 45.0625 C 14.382813 48.105469 17.539063 50 20.90625 50 L 30 50 C 34.945313 50 39 45.945313 39 41 L 39 25 C 39 24.179688 38.871094 23.050781 38.3125 22 C 37.753906 20.949219 36.597656 20 35 20 C 33.90625 20 33.09375 20.375 32.4375 20.875 C 32.328125 20.574219 32.273438 20.238281 32.125 19.96875 C 31.503906 18.847656 30.367188 18 29 18 C 27.882813 18 27.007813 18.40625 26.34375 18.96875 C 25.679688 17.871094 24.558594 17 23 17 C 22.21875 17 21.574219 17.246094 21 17.59375 L 21 7 C 21 5.734375 20.460938 4.675781 19.6875 4 C 18.914063 3.324219 17.9375 3 17 3 Z M 17 5 C 17.460938 5 18 5.175781 18.375 5.5 C 18.75 5.824219 19 6.265625 19 7 L 19 23 L 21 23 L 21 21 C 21 20.125 21.660156 19 23 19 C 24.339844 19 25 20.125 25 21 L 25 22 C 25.007813 22.546875 25.453125 22.984375 26 22.984375 C 26.546875 22.984375 26.992188 22.546875 27 22 C 27 21.464844 27.132813 20.933594 27.40625 20.59375 C 27.679688 20.253906 28.082031 20 29 20 C 29.632813 20 29.996094 20.257813 30.375 20.9375 C 30.753906 21.617188 31 22.71875 31 24 L 33 24 C 33 23.417969 33.105469 22.910156 33.34375 22.59375 C 33.582031 22.277344 33.964844 22 35 22 C 35.902344 22 36.246094 22.339844 36.5625 22.9375 C 36.878906 23.535156 37 24.417969 37 25 L 37 41 C 37 44.855469 33.855469 48 30 48 L 20.90625 48 C 18.285156 48 15.816406 46.5 14.6875 44.15625 L 11.90625 38.59375 C 11.902344 38.585938 11.910156 38.570313 11.90625 38.5625 C 11.613281 37.875 11 36.320313 11 34.90625 C 11 32.726563 11.832031 31.585938 12.65625 30.875 C 13.480469 30.164063 14.25 29.96875 14.25 29.96875 C 14.691406 29.855469 15 29.457031 15 29 L 15 6.90625 C 15 6.238281 15.25 5.820313 15.625 5.5 C 16 5.179688 16.539063 5 17 5 Z M 21.90625 29.96875 C 21.863281 29.976563 21.820313 29.988281 21.78125 30 C 21.316406 30.105469 20.988281 30.523438 21 31 L 21 40 C 20.996094 40.359375 21.183594 40.695313 21.496094 40.878906 C 21.808594 41.058594 22.191406 41.058594 22.503906 40.878906 C 22.816406 40.695313 23.003906 40.359375 23 40 L 23 31 C 23.011719 30.710938 22.894531 30.433594 22.6875 30.238281 C 22.476563 30.039063 22.191406 29.941406 21.90625 29.96875 Z M 26.90625 29.96875 C 26.863281 29.976563 26.820313 29.988281 26.78125 30 C 26.316406 30.105469 25.988281 30.523438 26 31 L 26 40 C 25.996094 40.359375 26.183594 40.695313 26.496094 40.878906 C 26.808594 41.058594 27.191406 41.058594 27.503906 40.878906 C 27.816406 40.695313 28.003906 40.359375 28 40 L 28 31 C 28.011719 30.710938 27.894531 30.433594 27.6875 30.238281 C 27.476563 30.039063 27.191406 29.941406 26.90625 29.96875 Z M 31.90625 29.96875 C 31.863281 29.976563 31.820313 29.988281 31.78125 30 C 31.316406 30.105469 30.988281 30.523438 31 31 L 31 40 C 30.996094 40.359375 31.183594 40.695313 31.496094 40.878906 C 31.808594 41.058594 32.191406 41.058594 32.503906 40.878906 C 32.816406 40.695313 33.003906 40.359375 33 40 L 33 31 C 33.011719 30.710938 32.894531 30.433594 32.6875 30.238281 C 32.476563 30.039063 32.191406 29.941406 31.90625 29.96875 Z',), stroke=())

icons8_place_marker_50 = VectorIcon(fill=('M 25 0.0625 C 17.316406 0.0625 11.0625 6.316406 11.0625 14 C 11.0625 20.367188 14.402344 27.667969 17.6875 33.46875 C 20.972656 39.269531 24.25 43.5625 24.25 43.5625 C 24.425781 43.800781 24.703125 43.945313 25 43.945313 C 25.296875 43.945313 25.574219 43.800781 25.75 43.5625 C 25.75 43.5625 29.03125 39.210938 32.3125 33.375 C 35.59375 27.539063 38.9375 20.234375 38.9375 14 C 38.9375 6.316406 32.683594 0.0625 25 0.0625 Z M 25 1.9375 C 31.679688 1.9375 37.0625 7.320313 37.0625 14 C 37.0625 19.554688 33.90625 26.75 30.6875 32.46875 C 28.058594 37.144531 25.871094 40.210938 25 41.40625 C 24.125 40.226563 21.9375 37.199219 19.3125 32.5625 C 16.097656 26.882813 12.9375 19.703125 12.9375 14 C 12.9375 7.320313 18.320313 1.9375 25 1.9375 Z M 25 8.03125 C 21.164063 8.03125 18.03125 11.164063 18.03125 15 C 18.03125 18.835938 21.164063 21.96875 25 21.96875 C 28.835938 21.96875 31.96875 18.835938 31.96875 15 C 31.96875 11.164063 28.835938 8.03125 25 8.03125 Z M 25 9.96875 C 27.792969 9.96875 30.03125 12.207031 30.03125 15 C 30.03125 17.792969 27.792969 20.03125 25 20.03125 C 22.207031 20.03125 19.96875 17.792969 19.96875 15 C 19.96875 12.207031 22.207031 9.96875 25 9.96875 Z M 15.15625 34.15625 C 11.15625 34.742188 7.773438 35.667969 5.28125 36.875 C 4.035156 37.476563 3.003906 38.148438 2.25 38.9375 C 1.496094 39.726563 1 40.707031 1 41.75 C 1 43.179688 1.914063 44.402344 3.21875 45.375 C 4.523438 46.347656 6.285156 47.132813 8.4375 47.8125 C 12.738281 49.171875 18.5625 50 25 50 C 31.4375 50 37.261719 49.171875 41.5625 47.8125 C 43.714844 47.132813 45.476563 46.347656 46.78125 45.375 C 48.085938 44.402344 49 43.179688 49 41.75 C 49 40.710938 48.503906 39.726563 47.75 38.9375 C 46.996094 38.148438 45.964844 37.476563 44.71875 36.875 C 42.226563 35.667969 38.84375 34.742188 34.84375 34.15625 C 34.292969 34.070313 33.773438 34.449219 33.6875 35 C 33.601563 35.550781 33.980469 36.070313 34.53125 36.15625 C 38.390625 36.722656 41.640625 37.621094 43.84375 38.6875 C 44.945313 39.222656 45.796875 39.804688 46.3125 40.34375 C 46.828125 40.882813 47 41.332031 47 41.75 C 47 42.324219 46.617188 42.984375 45.59375 43.75 C 44.570313 44.515625 42.980469 45.269531 40.96875 45.90625 C 36.945313 47.175781 31.265625 48 25 48 C 18.734375 48 13.054688 47.175781 9.03125 45.90625 C 7.019531 45.269531 5.429688 44.515625 4.40625 43.75 C 3.382813 42.984375 3 42.324219 3 41.75 C 3 41.332031 3.171875 40.882813 3.6875 40.34375 C 4.203125 39.804688 5.054688 39.222656 6.15625 38.6875 C 8.359375 37.621094 11.609375 36.722656 15.46875 36.15625 C 16.019531 36.070313 16.398438 35.550781 16.3125 35 C 16.226563 34.449219 15.707031 34.070313 15.15625 34.15625 Z',), stroke=())

icons8_cursor_50 = VectorIcon(fill=('M 14.78125 5 C 14.75 5.007813 14.71875 5.019531 14.6875 5.03125 C 14.644531 5.050781 14.601563 5.070313 14.5625 5.09375 C 14.550781 5.09375 14.542969 5.09375 14.53125 5.09375 C 14.511719 5.101563 14.488281 5.113281 14.46875 5.125 C 14.457031 5.136719 14.449219 5.144531 14.4375 5.15625 C 14.425781 5.167969 14.417969 5.175781 14.40625 5.1875 C 14.375 5.207031 14.34375 5.226563 14.3125 5.25 C 14.289063 5.269531 14.269531 5.289063 14.25 5.3125 C 14.238281 5.332031 14.226563 5.355469 14.21875 5.375 C 14.183594 5.414063 14.152344 5.457031 14.125 5.5 C 14.113281 5.511719 14.105469 5.519531 14.09375 5.53125 C 14.09375 5.542969 14.09375 5.550781 14.09375 5.5625 C 14.082031 5.582031 14.070313 5.605469 14.0625 5.625 C 14.050781 5.636719 14.042969 5.644531 14.03125 5.65625 C 14.03125 5.675781 14.03125 5.699219 14.03125 5.71875 C 14.019531 5.757813 14.007813 5.800781 14 5.84375 C 14 5.875 14 5.90625 14 5.9375 C 14 5.949219 14 5.957031 14 5.96875 C 14 5.980469 14 5.988281 14 6 C 13.996094 6.050781 13.996094 6.105469 14 6.15625 L 14 39 C 14.003906 39.398438 14.242188 39.757813 14.609375 39.914063 C 14.972656 40.070313 15.398438 39.992188 15.6875 39.71875 L 22.9375 32.90625 L 28.78125 46.40625 C 28.890625 46.652344 29.09375 46.847656 29.347656 46.941406 C 29.601563 47.035156 29.882813 47.023438 30.125 46.90625 L 34.5 44.90625 C 34.996094 44.679688 35.21875 44.09375 35 43.59375 L 28.90625 30.28125 L 39.09375 29.40625 C 39.496094 29.378906 39.84375 29.113281 39.976563 28.730469 C 40.105469 28.347656 39.992188 27.921875 39.6875 27.65625 L 15.84375 5.4375 C 15.796875 5.378906 15.746094 5.328125 15.6875 5.28125 C 15.648438 5.234375 15.609375 5.195313 15.5625 5.15625 C 15.550781 5.15625 15.542969 5.15625 15.53125 5.15625 C 15.511719 5.132813 15.492188 5.113281 15.46875 5.09375 C 15.457031 5.09375 15.449219 5.09375 15.4375 5.09375 C 15.386719 5.070313 15.335938 5.046875 15.28125 5.03125 C 15.269531 5.03125 15.261719 5.03125 15.25 5.03125 C 15.230469 5.019531 15.207031 5.007813 15.1875 5 C 15.175781 5 15.167969 5 15.15625 5 C 15.136719 5 15.113281 5 15.09375 5 C 15.082031 5 15.074219 5 15.0625 5 C 15.042969 5 15.019531 5 15 5 C 14.988281 5 14.980469 5 14.96875 5 C 14.9375 5 14.90625 5 14.875 5 C 14.84375 5 14.8125 5 14.78125 5 Z M 16 8.28125 L 36.6875 27.59375 L 27.3125 28.40625 C 26.992188 28.4375 26.707031 28.621094 26.546875 28.902344 C 26.382813 29.179688 26.367188 29.519531 26.5 29.8125 L 32.78125 43.5 L 30.21875 44.65625 L 24.21875 30.8125 C 24.089844 30.515625 23.828125 30.296875 23.511719 30.230469 C 23.195313 30.160156 22.863281 30.25 22.625 30.46875 L 16 36.6875 Z',), stroke=())

icons8_pencil_drawing_50 = VectorIcon(fill=('M 35.6875 2 C 35.460938 2.03125 35.25 2.144531 35.09375 2.3125 L 9.09375 28.28125 C 8.996094 28.390625 8.917969 28.515625 8.875 28.65625 L 2.0625 46.65625 C 1.929688 47.019531 2.019531 47.429688 2.296875 47.703125 C 2.570313 47.980469 2.980469 48.070313 3.34375 47.9375 L 21.34375 41.125 C 21.484375 41.082031 21.609375 41.003906 21.71875 40.90625 L 23 39.625 C 23.238281 39.523438 23.429688 39.332031 23.53125 39.09375 L 47.6875 14.90625 C 47.984375 14.664063 48.121094 14.277344 48.035156 13.902344 C 47.949219 13.53125 47.65625 13.238281 47.285156 13.152344 C 46.910156 13.066406 46.523438 13.203125 46.28125 13.5 L 22.34375 37.40625 C 21.625 37.074219 20.527344 36.703125 19.125 36.75 C 19.289063 36.304688 19.535156 36.039063 19.625 35.5 C 19.84375 34.199219 19.726563 32.601563 18.5625 31.4375 C 17.394531 30.269531 15.785156 30.160156 14.46875 30.40625 C 14.003906 30.492188 13.777344 30.730469 13.375 30.875 C 13.390625 30.734375 13.433594 30.710938 13.4375 30.5625 C 13.460938 29.695313 13.257813 28.621094 12.59375 27.65625 L 36.5 3.71875 C 36.796875 3.433594 36.886719 2.992188 36.726563 2.613281 C 36.570313 2.234375 36.191406 1.992188 35.78125 2 C 35.75 2 35.71875 2 35.6875 2 Z M 11.09375 29.15625 C 11.34375 29.613281 11.449219 30.058594 11.4375 30.5 C 11.421875 31.179688 11.203125 31.765625 11.0625 32.15625 C 10.910156 32.578125 11.054688 33.046875 11.417969 33.308594 C 11.78125 33.570313 12.273438 33.558594 12.625 33.28125 C 12.910156 33.058594 13.863281 32.550781 14.8125 32.375 C 15.761719 32.199219 16.605469 32.292969 17.15625 32.84375 C 17.710938 33.398438 17.816406 34.246094 17.65625 35.1875 C 17.496094 36.128906 17.003906 37.082031 16.8125 37.34375 C 16.535156 37.695313 16.523438 38.1875 16.785156 38.550781 C 17.046875 38.914063 17.515625 39.058594 17.9375 38.90625 C 19.207031 38.519531 20.195313 38.65625 20.875 38.875 L 20.40625 39.34375 L 9.375 43.53125 L 6.5 40.625 L 10.65625 29.59375 Z',), stroke=())

icons8_image = VectorIcon(fill=('M 11.5 6 C 8.4802259 6 6 8.4802259 6 11.5 L 6 36.5 C 6 39.519774 8.4802259 42 11.5 42 L 36.5 42 C 39.519774 42 42 39.519774 42 36.5 L 42 11.5 C 42 8.4802259 39.519774 6 36.5 6 L 11.5 6 z M 11.5 9 L 36.5 9 C 37.898226 9 39 10.101774 39 11.5 L 39 31.955078 L 32.988281 26.138672 A 1.50015 1.50015 0 0 0 32.986328 26.136719 C 32.208234 25.385403 31.18685 25 30.173828 25 C 29.16122 25 28.13988 25.385387 27.361328 26.138672 L 25.3125 28.121094 L 19.132812 22.142578 C 18.35636 21.389748 17.336076 21 16.318359 21 C 15.299078 21 14.280986 21.392173 13.505859 22.140625 A 1.50015 1.50015 0 0 0 13.503906 22.142578 L 9 26.5 L 9 11.5 C 9 10.101774 10.101774 9 11.5 9 z M 30.5 13 C 29.125 13 27.903815 13.569633 27.128906 14.441406 C 26.353997 15.313179 26 16.416667 26 17.5 C 26 18.583333 26.353997 19.686821 27.128906 20.558594 C 27.903815 21.430367 29.125 22 30.5 22 C 31.875 22 33.096185 21.430367 33.871094 20.558594 C 34.646003 19.686821 35 18.583333 35 17.5 C 35 16.416667 34.646003 15.313179 33.871094 14.441406 C 33.096185 13.569633 31.875 13 30.5 13 z M 30.5 16 C 31.124999 16 31.403816 16.180367 31.628906 16.433594 C 31.853997 16.686821 32 17.083333 32 17.5 C 32 17.916667 31.853997 18.313179 31.628906 18.566406 C 31.403816 18.819633 31.124999 19 30.5 19 C 29.875001 19 29.596184 18.819633 29.371094 18.566406 C 29.146003 18.313179 29 17.916667 29 17.5 C 29 17.083333 29.146003 16.686821 29.371094 16.433594 C 29.596184 16.180367 29.875001 16 30.5 16 z M 16.318359 24 C 16.578643 24 16.835328 24.09366 17.044922 24.296875 A 1.50015 1.50015 0 0 0 17.046875 24.298828 L 23.154297 30.207031 L 14.064453 39 L 11.5 39 C 10.101774 39 9 37.898226 9 36.5 L 9 30.673828 L 15.589844 24.298828 C 15.802764 24.093234 16.059641 24 16.318359 24 z M 30.173828 28 C 30.438806 28 30.692485 28.09229 30.902344 28.294922 L 39 36.128906 L 39 36.5 C 39 37.898226 37.898226 39 36.5 39 L 18.380859 39 L 29.447266 28.294922 C 29.654714 28.094207 29.910436 28 30.173828 28 z',), stroke=())

icons8_compress = VectorIcon(fill=('M 46.292969 2.292969 L 30 18.585938 L 30 9 L 28 9 L 28 22 L 41 22 L 41 20 L 31.414063 20 L 47.707031 3.707031 Z M 9 28 L 9 30 L 18.585938 30 L 2.292969 46.292969 L 3.707031 47.707031 L 20 31.414063 L 20 41 L 22 41 L 22 28 Z',), stroke=())

icons8_decompress = VectorIcon(fill=('M 33 4 L 33 6 L 42.585938 6 L 27.292969 21.292969 L 28.707031 22.707031 L 44 7.4140625 L 44 17 L 46 17 L 46 4 L 33 4 z M 21.292969 27.292969 L 6 42.585938 L 6 33 L 4 33 L 4 46 L 17 46 L 17 44 L 7.4140625 44 L 22.707031 28.707031 L 21.292969 27.292969 z',), stroke=())

icons8_r_white = VectorIcon(fill=('M 25 2 C 12.309295 2 2 12.309295 2 25 C 2 37.690705 12.309295 48 25 48 C 37.690705 48 48 37.690705 48 25 C 48 12.309295 37.690705 2 25 2 z M 25 4 C 36.609824 4 46 13.390176 46 25 C 46 36.609824 36.609824 46 25 46 C 13.390176 46 4 36.609824 4 25 C 4 13.390176 13.390176 4 25 4 z M 18.419922 16 L 18.419922 34 L 20.664062 34 L 20.666016 34 L 20.666016 26.876953 L 25.09375 26.876953 L 28.947266 34 L 31.580078 34 L 27.414062 26.527344 C 29.671062 25.816344 31.03125 23.870281 31.03125 21.363281 C 31.03125 18.120281 28.760969 16 25.292969 16 L 18.419922 16 z M 20.664062 17.994141 L 24.992188 17.994141 C 27.312187 17.994141 28.710938 19.2795 28.710938 21.4375 C 28.710938 23.6455 27.40175 24.880859 25.09375 24.880859 L 20.664062 24.880859 L 20.664062 17.994141 z',), stroke=())

icons8_light_off_50 = VectorIcon(fill=('M 25 9 C 17.28125 9 11 15.28125 11 23 C 11 27.890625 13.191406 31.175781 15.25 33.59375 C 16.28125 34.800781 17.277344 35.824219 17.96875 36.71875 C 18.660156 37.613281 19 38.328125 19 39 L 19 42.6875 C 18.941406 42.882813 18.941406 43.085938 19 43.28125 L 19 44 C 19 45.644531 20.355469 47 22 47 L 22.78125 47 C 23.332031 47.609375 24.117188 48 25 48 C 25.882813 48 26.667969 47.609375 27.21875 47 L 28 47 C 29.644531 47 31 45.644531 31 44 L 31 43.1875 C 31.027344 43.054688 31.027344 42.914063 31 42.78125 L 31 39 C 31 38.328125 31.339844 37.605469 32.03125 36.71875 C 32.722656 35.832031 33.71875 34.828125 34.75 33.625 C 36.808594 31.21875 39 27.933594 39 23 C 39 15.28125 32.71875 9 25 9 Z M 25 11 C 31.640625 11 37 16.359375 37 23 C 37 27.359375 35.191406 30.078125 33.25 32.34375 C 32.28125 33.476563 31.277344 34.464844 30.46875 35.5 C 29.875 36.261719 29.449219 37.09375 29.21875 38 L 20.78125 38 C 20.550781 37.09375 20.125 36.265625 19.53125 35.5 C 18.722656 34.457031 17.71875 33.453125 16.75 32.3125 C 14.808594 30.035156 13 27.3125 13 23 C 13 16.359375 18.359375 11 25 11 Z M 20.40625 17.46875 C 20.363281 17.476563 20.320313 17.488281 20.28125 17.5 C 19.90625 17.566406 19.605469 17.839844 19.5 18.203125 C 19.394531 18.570313 19.503906 18.960938 19.78125 19.21875 L 23.5625 23 L 19.78125 26.78125 C 19.382813 27.179688 19.382813 27.820313 19.78125 28.21875 C 20.179688 28.617188 20.820313 28.617188 21.21875 28.21875 L 25 24.4375 L 28.78125 28.21875 C 29.179688 28.617188 29.820313 28.617188 30.21875 28.21875 C 30.617188 27.820313 30.617188 27.179688 30.21875 26.78125 L 26.4375 23 L 30.21875 19.21875 C 30.542969 18.917969 30.628906 18.441406 30.433594 18.046875 C 30.242188 17.648438 29.808594 17.429688 29.375 17.5 C 29.152344 17.523438 28.941406 17.625 28.78125 17.78125 L 25 21.5625 L 21.21875 17.78125 C 21.011719 17.558594 20.710938 17.445313 20.40625 17.46875 Z M 21 40 L 29 40 L 29 42 L 24 42 C 23.96875 42 23.9375 42 23.90625 42 C 23.355469 42.027344 22.925781 42.496094 22.953125 43.046875 C 22.980469 43.597656 23.449219 44.027344 24 44 L 29 44 C 29 44.566406 28.566406 45 28 45 L 22 45 C 21.433594 45 21 44.566406 21 44 C 21.359375 44.003906 21.695313 43.816406 21.878906 43.503906 C 22.058594 43.191406 22.058594 42.808594 21.878906 42.496094 C 21.695313 42.183594 21.359375 41.996094 21 42 Z',), stroke=())

icons8_light_on_50 = VectorIcon(fill=('M 24.90625 0.96875 C 24.863281 0.976563 24.820313 0.988281 24.78125 1 C 24.316406 1.105469 23.988281 1.523438 24 2 L 24 6 C 23.996094 6.359375 24.183594 6.695313 24.496094 6.878906 C 24.808594 7.058594 25.191406 7.058594 25.503906 6.878906 C 25.816406 6.695313 26.003906 6.359375 26 6 L 26 2 C 26.011719 1.710938 25.894531 1.433594 25.6875 1.238281 C 25.476563 1.039063 25.191406 0.941406 24.90625 0.96875 Z M 10.03125 7.125 C 10 7.132813 9.96875 7.144531 9.9375 7.15625 C 9.578125 7.230469 9.289063 7.5 9.183594 7.851563 C 9.078125 8.203125 9.175781 8.585938 9.4375 8.84375 L 12.28125 11.6875 C 12.523438 11.984375 12.910156 12.121094 13.285156 12.035156 C 13.65625 11.949219 13.949219 11.65625 14.035156 11.285156 C 14.121094 10.910156 13.984375 10.523438 13.6875 10.28125 L 10.84375 7.4375 C 10.65625 7.238281 10.398438 7.128906 10.125 7.125 C 10.09375 7.125 10.0625 7.125 10.03125 7.125 Z M 39.75 7.125 C 39.707031 7.132813 39.664063 7.144531 39.625 7.15625 C 39.445313 7.203125 39.285156 7.300781 39.15625 7.4375 L 36.3125 10.28125 C 36.015625 10.523438 35.878906 10.910156 35.964844 11.285156 C 36.050781 11.65625 36.34375 11.949219 36.714844 12.035156 C 37.089844 12.121094 37.476563 11.984375 37.71875 11.6875 L 40.5625 8.84375 C 40.875 8.546875 40.964844 8.082031 40.78125 7.691406 C 40.59375 7.296875 40.179688 7.070313 39.75 7.125 Z M 25 9 C 17.28125 9 11 15.28125 11 23 C 11 27.890625 13.191406 31.175781 15.25 33.59375 C 16.28125 34.800781 17.277344 35.824219 17.96875 36.71875 C 18.660156 37.613281 19 38.328125 19 39 L 19 42.53125 C 18.867188 42.808594 18.867188 43.128906 19 43.40625 L 19 44 C 19 45.644531 20.355469 47 22 47 L 22.78125 47 C 23.332031 47.609375 24.117188 48 25 48 C 25.882813 48 26.667969 47.609375 27.21875 47 L 28 47 C 29.644531 47 31 45.644531 31 44 L 31 43.1875 C 31.027344 43.054688 31.027344 42.914063 31 42.78125 L 31 39 C 31 38.328125 31.339844 37.605469 32.03125 36.71875 C 32.722656 35.832031 33.71875 34.828125 34.75 33.625 C 36.808594 31.21875 39 27.933594 39 23 C 39 15.28125 32.71875 9 25 9 Z M 25 11 C 31.640625 11 37 16.359375 37 23 C 37 27.359375 35.191406 30.078125 33.25 32.34375 C 32.28125 33.476563 31.277344 34.464844 30.46875 35.5 C 29.875 36.261719 29.449219 37.09375 29.21875 38 L 20.78125 38 C 20.550781 37.09375 20.125 36.265625 19.53125 35.5 C 18.722656 34.457031 17.71875 33.453125 16.75 32.3125 C 14.808594 30.035156 13 27.3125 13 23 C 13 16.359375 18.359375 11 25 11 Z M 3.71875 22 C 3.167969 22.078125 2.78125 22.589844 2.859375 23.140625 C 2.9375 23.691406 3.449219 24.078125 4 24 L 8 24 C 8.359375 24.003906 8.695313 23.816406 8.878906 23.503906 C 9.058594 23.191406 9.058594 22.808594 8.878906 22.496094 C 8.695313 22.183594 8.359375 21.996094 8 22 L 4 22 C 3.96875 22 3.9375 22 3.90625 22 C 3.875 22 3.84375 22 3.8125 22 C 3.78125 22 3.75 22 3.71875 22 Z M 41.71875 22 C 41.167969 22.078125 40.78125 22.589844 40.859375 23.140625 C 40.9375 23.691406 41.449219 24.078125 42 24 L 46 24 C 46.359375 24.003906 46.695313 23.816406 46.878906 23.503906 C 47.058594 23.191406 47.058594 22.808594 46.878906 22.496094 C 46.695313 22.183594 46.359375 21.996094 46 22 L 42 22 C 41.96875 22 41.9375 22 41.90625 22 C 41.875 22 41.84375 22 41.8125 22 C 41.78125 22 41.75 22 41.71875 22 Z M 12.875 34 C 12.648438 34.03125 12.4375 34.144531 12.28125 34.3125 L 9.4375 37.15625 C 9.140625 37.398438 9.003906 37.785156 9.089844 38.160156 C 9.175781 38.53125 9.46875 38.824219 9.839844 38.910156 C 10.214844 38.996094 10.601563 38.859375 10.84375 38.5625 L 13.6875 35.71875 C 13.984375 35.433594 14.074219 34.992188 13.914063 34.613281 C 13.757813 34.234375 13.378906 33.992188 12.96875 34 C 12.9375 34 12.90625 34 12.875 34 Z M 36.8125 34 C 36.4375 34.066406 36.136719 34.339844 36.03125 34.703125 C 35.925781 35.070313 36.035156 35.460938 36.3125 35.71875 L 39.15625 38.5625 C 39.398438 38.859375 39.785156 38.996094 40.160156 38.910156 C 40.53125 38.824219 40.824219 38.53125 40.910156 38.160156 C 40.996094 37.785156 40.859375 37.398438 40.5625 37.15625 L 37.71875 34.3125 C 37.53125 34.113281 37.273438 34.003906 37 34 C 36.96875 34 36.9375 34 36.90625 34 C 36.875 34 36.84375 34 36.8125 34 Z M 21 40 L 29 40 L 29 42 L 24 42 C 23.96875 42 23.9375 42 23.90625 42 C 23.875 42 23.84375 42 23.8125 42 C 23.261719 42.050781 22.855469 42.542969 22.90625 43.09375 C 22.957031 43.644531 23.449219 44.050781 24 44 L 29 44 C 29 44.566406 28.566406 45 28 45 L 22 45 C 21.433594 45 21 44.566406 21 44 C 21.359375 44.003906 21.695313 43.816406 21.878906 43.503906 C 22.058594 43.191406 22.058594 42.808594 21.878906 42.496094 C 21.695313 42.183594 21.359375 41.996094 21 42 Z',), stroke=())

icons8_manager_50 = VectorIcon(fill=('M33.08 59.9c-.53 0-.97-.43-.97-.97V44.65c0-.53.43-.97.97-.97s.97.43.97.97v14.28C34.05 59.47 33.61 59.9 33.08 59.9zM22.44 21.42H43.72V24.590000000000003H22.44zM39.39 28.97L46.85 28.97 46.85 26.53 44.69 26.53 21.47 26.53 19.31 26.53 19.31 28.97 26.77 28.97zM19.31 17.04H46.849999999999994V19.49H19.31zM7.45 60.79v1.32c0 .49.4.89.89.89h19.83v-3.1H8.34C7.85 59.9 7.45 60.3 7.45 60.79zM22.44 11.94H43.72V15.11H22.44zM44.69 10h4.58c.53 0 .97-.43.97-.97V3.97C50.23 3.43 49.8 3 49.26 3h-2.52v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97-.53 0-.97-.43-.97-.97V3H16.9c-.53 0-.97.43-.97.97v5.07c0 .53.43.97.97.97h4.58H44.69zM27.74 30.91H38.43V33.8H27.74zM57.67 59.9H37.84V63h19.83c.49 0 .88-.4.88-.89v-1.32C58.55 60.3 58.16 59.9 57.67 59.9zM27.74 39.12L33.08 43.41 38.42 39.12 38.42 35.73 27.74 35.73zM40.14 51.81c-.25 0-.5-.09-.68-.28-.38-.38-.38-.99 0-1.37l2.63-2.63c.38-.38.99-.38 1.37 0 .38.38.38.99 0 1.37l-2.63 2.63C40.63 51.72 40.39 51.81 40.14 51.81zM42.11 55.52c-.45 0-.86-.32-.95-.78-.1-.52.24-1.03.76-1.14l3.65-.71c.53-.1 1.03.24 1.14.76.1.52-.24 1.03-.76 1.14L42.3 55.5C42.24 55.51 42.17 55.52 42.11 55.52zM26.02 51.81c-.25 0-.5-.09-.68-.28l-2.63-2.63c-.38-.38-.38-.99 0-1.37.38-.38.99-.38 1.37 0l2.63 2.63c.38.38.38.99 0 1.37C26.52 51.72 26.27 51.81 26.02 51.81zM24.05 55.52c-.06 0-.12-.01-.19-.02l-3.65-.71c-.52-.1-.87-.61-.76-1.14.1-.52.6-.87 1.14-.76l3.65.71c.52.1.87.61.76 1.14C24.91 55.2 24.5 55.52 24.05 55.52z',), stroke=())

icons8_gas_industry_50 = VectorIcon(fill=('M 28.53125 0 C 28.433594 0.015625 28.339844 0.046875 28.25 0.09375 C 28.25 0.09375 9 9.503906 9 26.1875 C 9 31.46875 12.070313 35.007813 15.03125 37.09375 C 17.992188 39.179688 20.9375 39.96875 20.9375 39.96875 C 21.359375 40.097656 21.816406 39.933594 22.0625 39.566406 C 22.304688 39.199219 22.28125 38.714844 22 38.375 C 22 38.375 18 33.230469 18 26.3125 C 18 20.390625 21.492188 16.382813 23.71875 14.375 C 23.15625 18.378906 23.355469 21.554688 24.03125 23.53125 C 24.445313 24.742188 24.953125 25.613281 25.375 26.1875 C 25.796875 26.761719 26.15625 27.0625 26.15625 27.0625 C 26.4375 27.292969 26.824219 27.351563 27.164063 27.214844 C 27.5 27.078125 27.738281 26.769531 27.78125 26.40625 C 27.78125 26.40625 27.882813 25.375 28.1875 24.125 C 28.269531 23.789063 28.476563 23.535156 28.59375 23.1875 C 28.929688 24.40625 29.328125 25.523438 29.71875 26.53125 C 30.417969 28.324219 31 29.902344 31 31.90625 C 31 33.214844 30.382813 34.882813 29.71875 36.1875 C 29.054688 37.492188 28.375 38.40625 28.375 38.40625 C 28.109375 38.761719 28.113281 39.25 28.378906 39.605469 C 28.648438 39.957031 29.117188 40.09375 29.53125 39.9375 C 35.179688 37.980469 39 32.214844 39 26.1875 C 39 20.617188 35.914063 16.425781 33.3125 12.59375 C 30.710938 8.761719 28.613281 5.421875 29.65625 1.25 C 29.738281 0.941406 29.664063 0.609375 29.460938 0.363281 C 29.253906 0.113281 28.945313 -0.0195313 28.625 0 C 28.59375 0 28.5625 0 28.53125 0 Z M 27.5625 2.84375 C 27.363281 6.921875 29.410156 10.410156 31.65625 13.71875 C 34.28125 17.585938 37 21.359375 37 26.1875 C 37 30.214844 34.933594 34.144531 31.78125 36.46875 C 32.417969 35.121094 33 33.554688 33 31.90625 C 33 29.507813 32.296875 27.617188 31.59375 25.8125 C 30.890625 24.007813 30.1875 22.246094 30 19.90625 C 29.960938 19.507813 29.691406 19.171875 29.308594 19.046875 C 28.929688 18.925781 28.511719 19.042969 28.25 19.34375 C 27.152344 20.5625 26.625 22.207031 26.28125 23.59375 C 26.15625 23.320313 26.023438 23.222656 25.90625 22.875 C 25.210938 20.847656 24.753906 17.472656 25.96875 12.21875 C 26.050781 11.828125 25.894531 11.425781 25.570313 11.191406 C 25.242188 10.960938 24.808594 10.949219 24.46875 11.15625 C 24.46875 11.15625 16 16.53125 16 26.3125 C 16 31.238281 17.542969 34.609375 18.84375 36.90625 C 18.007813 36.511719 17.152344 36.152344 16.1875 35.46875 C 13.546875 33.605469 11 30.707031 11 26.1875 C 11 13.195313 23.796875 5.007813 27.5625 2.84375 Z M 10.40625 42 C 9.105469 42 8 43.105469 8 44.40625 L 8 49 C 8 49.550781 8.449219 50 9 50 L 41 50 C 41.550781 50 42 49.550781 42 49 L 42 44.40625 C 42 43.105469 40.894531 42 39.59375 42 L 37 42 C 36.449219 42 36 42.449219 36 43 L 36 45 L 35 45 L 35 43 C 35 42.449219 34.550781 42 34 42 L 30 42 C 29.449219 42 29 42.449219 29 43 L 29 45 L 28 45 L 28 43 C 28 42.449219 27.550781 42 27 42 L 23 42 C 22.449219 42 22 42.449219 22 43 L 22 45 L 21 45 L 21 43 C 21 42.449219 20.550781 42 20 42 L 16 42 C 15.449219 42 15 42.449219 15 43 L 15 45 L 14 45 L 14 43 C 14 42.449219 13.550781 42 13 42 Z M 10.40625 44 L 12 44 L 12 46 C 12 46.550781 12.449219 47 13 47 L 16 47 C 16.550781 47 17 46.550781 17 46 L 17 44 L 19 44 L 19 46 C 19 46.550781 19.449219 47 20 47 L 23 47 C 23.550781 47 24 46.550781 24 46 L 24 44 L 26 44 L 26 46 C 26 46.550781 26.449219 47 27 47 L 30 47 C 30.550781 47 31 46.550781 31 46 L 31 44 L 33 44 L 33 46 C 33 46.550781 33.449219 47 34 47 L 37 47 C 37.550781 47 38 46.550781 38 46 L 38 44 L 39.59375 44 C 39.894531 44 40 44.105469 40 44.40625 L 40 48 L 10 48 L 10 44.40625 C 10 44.105469 10.105469 44 10.40625 44 Z',), stroke=())

icons8_laser_beam = VectorIcon(fill=('M 24.90625 -0.03125 C 24.863281 -0.0234375 24.820313 -0.0117188 24.78125 0 C 24.316406 0.105469 23.988281 0.523438 24 1 L 24 27.9375 C 24 28.023438 24.011719 28.105469 24.03125 28.1875 C 22.859375 28.59375 22 29.6875 22 31 C 22 32.65625 23.34375 34 25 34 C 26.65625 34 28 32.65625 28 31 C 28 29.6875 27.140625 28.59375 25.96875 28.1875 C 25.988281 28.105469 26 28.023438 26 27.9375 L 26 1 C 26.011719 0.710938 25.894531 0.433594 25.6875 0.238281 C 25.476563 0.0390625 25.191406 -0.0585938 24.90625 -0.03125 Z M 35.125 12.15625 C 34.832031 12.210938 34.582031 12.394531 34.4375 12.65625 L 27.125 25.3125 C 26.898438 25.621094 26.867188 26.03125 27.042969 26.371094 C 27.222656 26.710938 27.578125 26.917969 27.960938 26.90625 C 28.347656 26.894531 28.6875 26.664063 28.84375 26.3125 L 36.15625 13.65625 C 36.34375 13.335938 36.335938 12.9375 36.140625 12.625 C 35.941406 12.308594 35.589844 12.128906 35.21875 12.15625 C 35.1875 12.15625 35.15625 12.15625 35.125 12.15625 Z M 17.78125 17.71875 C 17.75 17.726563 17.71875 17.738281 17.6875 17.75 C 17.375 17.824219 17.113281 18.042969 16.988281 18.339844 C 16.867188 18.636719 16.894531 18.976563 17.0625 19.25 L 21.125 26.3125 C 21.402344 26.796875 22.015625 26.964844 22.5 26.6875 C 22.984375 26.410156 23.152344 25.796875 22.875 25.3125 L 18.78125 18.25 C 18.605469 17.914063 18.253906 17.710938 17.875 17.71875 C 17.84375 17.71875 17.8125 17.71875 17.78125 17.71875 Z M 7 19.6875 C 6.566406 19.742188 6.222656 20.070313 6.140625 20.5 C 6.0625 20.929688 6.273438 21.359375 6.65625 21.5625 L 19.3125 28.875 C 19.796875 29.152344 20.410156 28.984375 20.6875 28.5 C 20.964844 28.015625 20.796875 27.402344 20.3125 27.125 L 7.65625 19.84375 C 7.488281 19.738281 7.292969 19.683594 7.09375 19.6875 C 7.0625 19.6875 7.03125 19.6875 7 19.6875 Z M 37.1875 22.90625 C 37.03125 22.921875 36.882813 22.976563 36.75 23.0625 L 29.6875 27.125 C 29.203125 27.402344 29.035156 28.015625 29.3125 28.5 C 29.589844 28.984375 30.203125 29.152344 30.6875 28.875 L 37.75 24.78125 C 38.164063 24.554688 38.367188 24.070313 38.230469 23.617188 C 38.09375 23.164063 37.660156 22.867188 37.1875 22.90625 Z M 0.71875 30 C 0.167969 30.078125 -0.21875 30.589844 -0.140625 31.140625 C -0.0625 31.691406 0.449219 32.078125 1 32 L 19 32 C 19.359375 32.003906 19.695313 31.816406 19.878906 31.503906 C 20.058594 31.191406 20.058594 30.808594 19.878906 30.496094 C 19.695313 30.183594 19.359375 29.996094 19 30 L 1 30 C 0.96875 30 0.9375 30 0.90625 30 C 0.875 30 0.84375 30 0.8125 30 C 0.78125 30 0.75 30 0.71875 30 Z M 30.71875 30 C 30.167969 30.078125 29.78125 30.589844 29.859375 31.140625 C 29.9375 31.691406 30.449219 32.078125 31 32 L 49 32 C 49.359375 32.003906 49.695313 31.816406 49.878906 31.503906 C 50.058594 31.191406 50.058594 30.808594 49.878906 30.496094 C 49.695313 30.183594 49.359375 29.996094 49 30 L 31 30 C 30.96875 30 30.9375 30 30.90625 30 C 30.875 30 30.84375 30 30.8125 30 C 30.78125 30 30.75 30 30.71875 30 Z M 19.75 32.96875 C 19.71875 32.976563 19.6875 32.988281 19.65625 33 C 19.535156 33.019531 19.417969 33.0625 19.3125 33.125 L 12.25 37.21875 C 11.898438 37.375 11.667969 37.714844 11.65625 38.101563 C 11.644531 38.484375 11.851563 38.839844 12.191406 39.019531 C 12.53125 39.195313 12.941406 39.164063 13.25 38.9375 L 20.3125 34.875 C 20.78125 34.675781 21.027344 34.160156 20.882813 33.671875 C 20.738281 33.183594 20.25 32.878906 19.75 32.96875 Z M 30.03125 33 C 29.597656 33.054688 29.253906 33.382813 29.171875 33.8125 C 29.09375 34.242188 29.304688 34.671875 29.6875 34.875 L 42.34375 42.15625 C 42.652344 42.382813 43.0625 42.414063 43.402344 42.238281 C 43.742188 42.058594 43.949219 41.703125 43.9375 41.320313 C 43.925781 40.933594 43.695313 40.59375 43.34375 40.4375 L 30.6875 33.125 C 30.488281 33.007813 30.257813 32.964844 30.03125 33 Z M 21.9375 35.15625 C 21.894531 35.164063 21.851563 35.175781 21.8125 35.1875 C 21.519531 35.242188 21.269531 35.425781 21.125 35.6875 L 13.84375 48.34375 C 13.617188 48.652344 13.585938 49.0625 13.761719 49.402344 C 13.941406 49.742188 14.296875 49.949219 14.679688 49.9375 C 15.066406 49.925781 15.40625 49.695313 15.5625 49.34375 L 22.875 36.6875 C 23.078125 36.367188 23.082031 35.957031 22.882813 35.628906 C 22.683594 35.304688 22.316406 35.121094 21.9375 35.15625 Z M 27.84375 35.1875 C 27.511719 35.234375 27.226563 35.445313 27.082031 35.746094 C 26.9375 36.046875 26.953125 36.398438 27.125 36.6875 L 31.21875 43.75 C 31.375 44.101563 31.714844 44.332031 32.101563 44.34375 C 32.484375 44.355469 32.839844 44.148438 33.019531 43.808594 C 33.195313 43.46875 33.164063 43.058594 32.9375 42.75 L 28.875 35.6875 C 28.671875 35.320313 28.257813 35.121094 27.84375 35.1875 Z M 24.90625 35.96875 C 24.863281 35.976563 24.820313 35.988281 24.78125 36 C 24.316406 36.105469 23.988281 36.523438 24 37 L 24 45.9375 C 23.996094 46.296875 24.183594 46.632813 24.496094 46.816406 C 24.808594 46.996094 25.191406 46.996094 25.503906 46.816406 C 25.816406 46.632813 26.003906 46.296875 26 45.9375 L 26 37 C 26.011719 36.710938 25.894531 36.433594 25.6875 36.238281 C 25.476563 36.039063 25.191406 35.941406 24.90625 35.96875 Z',), stroke=())

icons8_detective_50 = VectorIcon(fill=('M 21 3 C 11.621094 3 4 10.621094 4 20 C 4 29.378906 11.621094 37 21 37 C 24.710938 37 28.140625 35.804688 30.9375 33.78125 L 44.09375 46.90625 L 46.90625 44.09375 L 33.90625 31.0625 C 36.460938 28.085938 38 24.222656 38 20 C 38 10.621094 30.378906 3 21 3 Z M 21 5 C 28.070313 5 33.96875 9.867188 35.5625 16.4375 C 31.863281 13.777344 26.761719 11.125 21 11.125 C 15.238281 11.125 10.136719 13.808594 6.4375 16.46875 C 8.023438 9.882813 13.921875 5 21 5 Z M 21 12.875 C 23.261719 12.875 25.460938 13.332031 27.5 14.0625 C 28.863281 15.597656 29.6875 17.59375 29.6875 19.8125 C 29.6875 24.628906 25.816406 28.53125 21 28.53125 C 16.183594 28.53125 12.3125 24.628906 12.3125 19.8125 C 12.3125 17.613281 13.101563 15.621094 14.4375 14.09375 C 16.503906 13.347656 18.707031 12.875 21 12.875 Z M 11.5625 15.34375 C 10.914063 16.695313 10.5625 18.210938 10.5625 19.8125 C 10.5625 25.566406 15.246094 30.25 21 30.25 C 26.753906 30.25 31.4375 25.566406 31.4375 19.8125 C 31.4375 18.226563 31.078125 16.722656 30.4375 15.375 C 32.460938 16.402344 34.28125 17.609375 35.78125 18.78125 C 35.839844 18.820313 35.902344 18.851563 35.96875 18.875 C 35.996094 19.25 36 19.621094 36 20 C 36 28.296875 29.296875 35 21 35 C 12.703125 35 6 28.296875 6 20 C 6 19.542969 6.023438 19.101563 6.0625 18.65625 C 6.296875 18.660156 6.519531 18.570313 6.6875 18.40625 C 8.089844 17.34375 9.742188 16.265625 11.5625 15.34375 Z M 21 15.46875 C 18.597656 15.46875 16.65625 17.410156 16.65625 19.8125 C 16.65625 22.214844 18.597656 24.1875 21 24.1875 C 23.402344 24.1875 25.34375 22.214844 25.34375 19.8125 C 25.34375 17.410156 23.402344 15.46875 21 15.46875 Z',), stroke=())

icons8_flip_vertical = VectorIcon(fill=('M 43.0625 4 C 42.894531 3.992188 42.71875 4.019531 42.5625 4.09375 L 5.5625 22.09375 C 5.144531 22.296875 4.925781 22.765625 5.03125 23.21875 C 5.136719 23.671875 5.535156 24 6 24 L 43 24 C 43.554688 24 44 23.550781 44 23 L 44 5 C 44 4.65625 43.824219 4.339844 43.53125 4.15625 C 43.386719 4.066406 43.230469 4.007813 43.0625 4 Z M 5.8125 26 C 5.371094 26.066406 5.027344 26.417969 4.96875 26.859375 C 4.910156 27.300781 5.152344 27.726563 5.5625 27.90625 L 42.5625 45.90625 C 42.875 46.058594 43.242188 46.039063 43.535156 45.851563 C 43.824219 45.667969 44.003906 45.347656 44 45 L 44 27 C 44 26.449219 43.550781 26 43 26 L 6 26 C 5.96875 26 5.9375 26 5.90625 26 C 5.875 26 5.84375 26 5.8125 26 Z M 10.34375 28 L 42 28 L 42 43.40625 Z',), stroke=())

icons8_flip_horizontal = VectorIcon(fill=('M 22.875 5 C 22.535156 5.042969 22.242188 5.253906 22.09375 5.5625 L 4.09375 42.5625 C 3.941406 42.875 3.960938 43.242188 4.148438 43.535156 C 4.332031 43.824219 4.652344 44.003906 5 44 L 23 44 C 23.550781 44 24 43.550781 24 43 L 24 6 C 24.003906 5.710938 23.878906 5.4375 23.664063 5.246094 C 23.449219 5.054688 23.160156 4.964844 22.875 5 Z M 27.125 5 C 27.015625 4.988281 26.894531 5.003906 26.78125 5.03125 C 26.328125 5.136719 26 5.535156 26 6 L 26 43 C 26 43.554688 26.445313 44 27 44 L 45 44 C 45.34375 44 45.660156 43.824219 45.84375 43.53125 C 46.027344 43.238281 46.054688 42.871094 45.90625 42.5625 L 27.90625 5.5625 C 27.753906 5.25 27.457031 5.039063 27.125 5 Z M 22 10.34375 L 22 42 L 6.59375 42 Z',), stroke=())

icons8_flash_on_50 = VectorIcon(fill=('M 31.1875 3.25 C 30.9375 3.292969 30.714844 3.425781 30.5625 3.625 L 11.5 27.375 C 11.257813 27.675781 11.210938 28.085938 11.378906 28.433594 C 11.546875 28.78125 11.898438 29 12.28125 29 L 22.75 29 L 17.75 45.4375 C 17.566406 45.910156 17.765625 46.441406 18.210938 46.679688 C 18.65625 46.917969 19.207031 46.789063 19.5 46.375 L 38.5 22.625 C 38.742188 22.324219 38.789063 21.914063 38.621094 21.566406 C 38.453125 21.21875 38.101563 21 37.71875 21 L 27.625 21 L 32.28125 4.53125 C 32.371094 4.222656 32.308594 3.886719 32.109375 3.632813 C 31.910156 3.378906 31.601563 3.238281 31.28125 3.25 C 31.25 3.25 31.21875 3.25 31.1875 3.25 Z M 29.03125 8.71875 L 25.3125 21.71875 C 25.222656 22.023438 25.285156 22.351563 25.472656 22.601563 C 25.664063 22.855469 25.964844 23.003906 26.28125 23 L 35.625 23 L 21.1875 41.09375 L 25.09375 28.28125 C 25.183594 27.976563 25.121094 27.648438 24.933594 27.398438 C 24.742188 27.144531 24.441406 26.996094 24.125 27 L 14.375 27 Z',), stroke=())

icons8_flash_off_50 = VectorIcon(fill=('M 11.919922 1.2539062 C 11.671859 1.280625 11.445125 1.4300625 11.328125 1.6640625 L 9.328125 5.6640625 C 9.143125 6.0340625 9.2930625 6.486875 9.6640625 6.671875 C 10.034062 6.856875 10.486875 6.7069375 10.671875 6.3359375 L 11.25 5.1777344 L 11.25 8 C 11.25 8.414 11.586 8.75 12 8.75 C 12.414 8.75 12.75 8.414 12.75 8 L 12.75 2 C 12.75 1.652 12.510875 1.3495312 12.171875 1.2695312 C 12.087375 1.2495312 12.002609 1.245 11.919922 1.2539062 z M 5 4.25 C 4.808 4.25 4.6167031 4.3242031 4.4707031 4.4707031 C 4.1777031 4.7627031 4.1777031 5.2372969 4.4707031 5.5292969 L 7.7539062 8.8144531 L 5.328125 13.664062 C 5.212125 13.896062 5.2243281 14.173531 5.3613281 14.394531 C 5.4983281 14.615531 5.74 14.75 6 14.75 L 11.25 14.75 L 11.25 22 C 11.25 22.348 11.489125 22.650469 11.828125 22.730469 C 12.166125 22.810469 12.515875 22.647938 12.671875 22.335938 L 15.539062 16.599609 L 18.480469 19.542969 C 18.773469 19.834969 19.249969 19.834969 19.542969 19.542969 C 19.834969 19.249969 19.834969 18.773469 19.542969 18.480469 L 15.996094 14.933594 C 15.92516 14.80669 15.827485 14.692851 15.6875 14.623047 C 15.686169 14.622381 15.684927 14.621751 15.683594 14.621094 L 5.5292969 4.4707031 C 5.3832969 4.3242031 5.192 4.25 5 4.25 z M 14 9.25 C 13.586 9.25 13.25 9.586 13.25 10 C 13.25 10.414 13.586 10.75 14 10.75 L 16.785156 10.75 L 15.828125 12.664062 C 15.643125 13.034062 15.793063 13.486875 16.164062 13.671875 C 16.534063 13.856875 16.986875 13.706938 17.171875 13.335938 L 18.671875 10.335938 C 18.787875 10.103938 18.775672 9.8264687 18.638672 9.6054688 C 18.501672 9.3844687 18.26 9.25 18 9.25 L 14 9.25 z M 8.8730469 9.9316406 L 12.236328 13.296875 C 12.160904 13.271364 12.084002 13.25 12 13.25 L 7.2148438 13.25 L 8.8730469 9.9316406 z M 12.703125 13.763672 L 14.419922 15.482422 L 12.75 18.822266 L 12.75 14 C 12.75 13.915998 12.728636 13.839096 12.703125 13.763672 z',), stroke=())

icons8_arrange_50 = VectorIcon(fill=('M 8.5 4 C 7.0833337 4 5.8935589 4.5672556 5.1269531 5.4296875 C 4.3603473 6.2921194 4 7.4027779 4 8.5 C 4 9.5972221 4.3603473 10.707881 5.1269531 11.570312 C 5.8935589 12.432745 7.0833337 13 8.5 13 C 9.9166663 13 11.106441 12.432744 11.873047 11.570312 C 12.639653 10.707882 13 9.5972221 13 8.5 C 13 7.4027779 12.639653 6.2921194 11.873047 5.4296875 C 11.106441 4.5672556 9.9166663 4 8.5 4 z M 19.5 4 C 18.083334 4 16.893559 4.5672556 16.126953 5.4296875 C 15.360347 6.2921194 15 7.4027779 15 8.5 C 15 9.5972221 15.360347 10.707881 16.126953 11.570312 C 16.893559 12.432745 18.083334 13 19.5 13 C 20.916666 13 22.106441 12.432744 22.873047 11.570312 C 23.639653 10.707882 24 9.5972221 24 8.5 C 24 7.4027779 23.639653 6.2921194 22.873047 5.4296875 C 22.106441 4.5672556 20.916666 4 19.5 4 z M 30.5 4 C 29.083334 4 27.893559 4.5672556 27.126953 5.4296875 C 26.360347 6.2921194 26 7.4027779 26 8.5 C 26 9.5972221 26.360347 10.707881 27.126953 11.570312 C 27.893559 12.432745 29.083334 13 30.5 13 C 31.916666 13 33.106441 12.432744 33.873047 11.570312 C 34.639653 10.707882 35 9.5972221 35 8.5 C 35 7.4027779 34.639653 6.2921194 33.873047 5.4296875 C 33.106441 4.5672556 31.916666 4 30.5 4 z M 41.5 4 C 40.083334 4 38.893559 4.5672556 38.126953 5.4296875 C 37.360347 6.2921194 37 7.4027779 37 8.5 C 37 9.5972221 37.360347 10.707881 38.126953 11.570312 C 38.893559 12.432745 40.083334 13 41.5 13 C 42.916666 13 44.106441 12.432744 44.873047 11.570312 C 45.639653 10.707882 46 9.5972221 46 8.5 C 46 7.4027779 45.639653 6.2921194 44.873047 5.4296875 C 44.106441 4.5672556 42.916666 4 41.5 4 z M 8.5 6 C 9.4166661 6 9.9768929 6.3077444 10.376953 6.7578125 C 10.777013 7.2078806 11 7.8472221 11 8.5 C 11 9.1527779 10.777013 9.7921189 10.376953 10.242188 C 9.9768929 10.692255 9.4166661 11 8.5 11 C 7.5833339 11 7.0231072 10.692256 6.6230469 10.242188 C 6.2229865 9.7921189 6 9.1527779 6 8.5 C 6 7.8472221 6.2229865 7.2078806 6.6230469 6.7578125 C 7.0231072 6.3077444 7.5833339 6 8.5 6 z M 19.5 6 C 20.416666 6 20.976893 6.3077444 21.376953 6.7578125 C 21.777013 7.2078806 22 7.8472221 22 8.5 C 22 9.1527779 21.777013 9.7921189 21.376953 10.242188 C 20.976893 10.692255 20.416666 11 19.5 11 C 18.583334 11 18.023107 10.692256 17.623047 10.242188 C 17.222987 9.7921189 17 9.1527779 17 8.5 C 17 7.8472221 17.222987 7.2078806 17.623047 6.7578125 C 18.023107 6.3077444 18.583334 6 19.5 6 z M 30.5 6 C 31.416666 6 31.976893 6.3077444 32.376953 6.7578125 C 32.777013 7.2078806 33 7.8472221 33 8.5 C 33 9.1527779 32.777013 9.7921189 32.376953 10.242188 C 31.976893 10.692255 31.416666 11 30.5 11 C 29.583334 11 29.023107 10.692256 28.623047 10.242188 C 28.222987 9.7921189 28 9.1527779 28 8.5 C 28 7.8472221 28.222987 7.2078806 28.623047 6.7578125 C 29.023107 6.3077444 29.583334 6 30.5 6 z M 41.5 6 C 42.416666 6 42.976893 6.3077444 43.376953 6.7578125 C 43.777013 7.2078806 44 7.8472221 44 8.5 C 44 9.1527779 43.777013 9.7921189 43.376953 10.242188 C 42.976893 10.692255 42.416666 11 41.5 11 C 40.583334 11 40.023107 10.692256 39.623047 10.242188 C 39.222987 9.7921189 39 9.1527779 39 8.5 C 39 7.8472221 39.222987 7.2078806 39.623047 6.7578125 C 40.023107 6.3077444 40.583334 6 41.5 6 z M 8.5 15 C 7.0833337 15 5.8935589 15.567256 5.1269531 16.429688 C 4.3603473 17.292119 4 18.402778 4 19.5 C 4 20.597222 4.3603473 21.707881 5.1269531 22.570312 C 5.8935589 23.432744 7.0833337 24 8.5 24 C 9.9166663 24 11.106441 23.432744 11.873047 22.570312 C 12.639653 21.707881 13 20.597222 13 19.5 C 13 18.402778 12.639653 17.292119 11.873047 16.429688 C 11.106441 15.567256 9.9166663 15 8.5 15 z M 19.5 15 C 18.083334 15 16.893559 15.567256 16.126953 16.429688 C 15.360347 17.292119 15 18.402778 15 19.5 C 15 20.597222 15.360347 21.707881 16.126953 22.570312 C 16.893559 23.432744 18.083334 24 19.5 24 C 20.916666 24 22.106441 23.432744 22.873047 22.570312 C 23.639653 21.707881 24 20.597222 24 19.5 C 24 18.402778 23.639653 17.292119 22.873047 16.429688 C 22.106441 15.567256 20.916666 15 19.5 15 z M 30.5 15 C 29.083334 15 27.893559 15.567256 27.126953 16.429688 C 26.360347 17.292119 26 18.402778 26 19.5 C 26 20.597222 26.360347 21.707881 27.126953 22.570312 C 27.893559 23.432744 29.083334 24 30.5 24 C 31.916666 24 33.106441 23.432744 33.873047 22.570312 C 34.639653 21.707881 35 20.597222 35 19.5 C 35 18.402778 34.639653 17.292119 33.873047 16.429688 C 33.106441 15.567256 31.916666 15 30.5 15 z M 41.5 15 C 40.083334 15 38.893559 15.567256 38.126953 16.429688 C 37.360347 17.292119 37 18.402778 37 19.5 C 37 20.597222 37.360347 21.707881 38.126953 22.570312 C 38.893559 23.432744 40.083334 24 41.5 24 C 42.916666 24 44.106441 23.432744 44.873047 22.570312 C 45.639653 21.707881 46 20.597222 46 19.5 C 46 18.402778 45.639653 17.292119 44.873047 16.429688 C 44.106441 15.567256 42.916666 15 41.5 15 z M 8.5 17 C 9.4166661 17 9.9768929 17.307744 10.376953 17.757812 C 10.777013 18.207881 11 18.847222 11 19.5 C 11 20.152778 10.777013 20.792119 10.376953 21.242188 C 9.9768929 21.692256 9.4166661 22 8.5 22 C 7.5833339 22 7.0231072 21.692256 6.6230469 21.242188 C 6.2229865 20.792119 6 20.152778 6 19.5 C 6 18.847222 6.2229865 18.207881 6.6230469 17.757812 C 7.0231072 17.307744 7.5833339 17 8.5 17 z M 19.5 17 C 20.416666 17 20.976893 17.307744 21.376953 17.757812 C 21.777013 18.207881 22 18.847222 22 19.5 C 22 20.152778 21.777013 20.792119 21.376953 21.242188 C 20.976893 21.692256 20.416666 22 19.5 22 C 18.583334 22 18.023107 21.692256 17.623047 21.242188 C 17.222987 20.792119 17 20.152778 17 19.5 C 17 18.847222 17.222987 18.207881 17.623047 17.757812 C 18.023107 17.307744 18.583334 17 19.5 17 z M 30.5 17 C 31.416666 17 31.976893 17.307744 32.376953 17.757812 C 32.777013 18.207881 33 18.847222 33 19.5 C 33 20.152778 32.777013 20.792119 32.376953 21.242188 C 31.976893 21.692256 31.416666 22 30.5 22 C 29.583334 22 29.023107 21.692256 28.623047 21.242188 C 28.222987 20.792119 28 20.152778 28 19.5 C 28 18.847222 28.222987 18.207881 28.623047 17.757812 C 29.023107 17.307744 29.583334 17 30.5 17 z M 41.5 17 C 42.416666 17 42.976893 17.307744 43.376953 17.757812 C 43.777013 18.207881 44 18.847222 44 19.5 C 44 20.152778 43.777013 20.792119 43.376953 21.242188 C 42.976893 21.692256 42.416666 22 41.5 22 C 40.583334 22 40.023107 21.692256 39.623047 21.242188 C 39.222987 20.792119 39 20.152778 39 19.5 C 39 18.847222 39.222987 18.207881 39.623047 17.757812 C 40.023107 17.307744 40.583334 17 41.5 17 z M 8.5 26 C 7.0833337 26 5.8935589 26.567256 5.1269531 27.429688 C 4.3603473 28.292119 4 29.402778 4 30.5 C 4 31.597222 4.3603473 32.707882 5.1269531 33.570312 C 5.8935589 34.432744 7.0833337 35 8.5 35 C 9.9166663 35 11.106441 34.432744 11.873047 33.570312 C 12.639653 32.707881 13 31.597222 13 30.5 C 13 29.402778 12.639653 28.292118 11.873047 27.429688 C 11.106441 26.567256 9.9166663 26 8.5 26 z M 19.5 26 C 18.083334 26 16.893559 26.567256 16.126953 27.429688 C 15.360347 28.292119 15 29.402778 15 30.5 C 15 31.597222 15.360347 32.707882 16.126953 33.570312 C 16.893559 34.432744 18.083334 35 19.5 35 C 20.916666 35 22.106441 34.432744 22.873047 33.570312 C 23.639653 32.707881 24 31.597222 24 30.5 C 24 29.402778 23.639653 28.292118 22.873047 27.429688 C 22.106441 26.567256 20.916666 26 19.5 26 z M 30.5 26 C 29.083334 26 27.893559 26.567256 27.126953 27.429688 C 26.360347 28.292119 26 29.402778 26 30.5 C 26 31.597222 26.360347 32.707882 27.126953 33.570312 C 27.893559 34.432744 29.083334 35 30.5 35 C 31.916666 35 33.106441 34.432744 33.873047 33.570312 C 34.639653 32.707881 35 31.597222 35 30.5 C 35 29.402778 34.639653 28.292118 33.873047 27.429688 C 33.106441 26.567256 31.916666 26 30.5 26 z M 41.5 26 C 40.083334 26 38.893559 26.567256 38.126953 27.429688 C 37.360347 28.292119 37 29.402778 37 30.5 C 37 31.597222 37.360347 32.707882 38.126953 33.570312 C 38.893559 34.432744 40.083334 35 41.5 35 C 42.916666 35 44.106441 34.432744 44.873047 33.570312 C 45.639653 32.707881 46 31.597222 46 30.5 C 46 29.402778 45.639653 28.292118 44.873047 27.429688 C 44.106441 26.567256 42.916666 26 41.5 26 z M 8.5 28 C 9.4166661 28 9.9768929 28.307744 10.376953 28.757812 C 10.777013 29.207881 11 29.847222 11 30.5 C 11 31.152778 10.777013 31.792118 10.376953 32.242188 C 9.9768929 32.692256 9.4166661 33 8.5 33 C 7.5833339 33 7.0231072 32.692256 6.6230469 32.242188 C 6.2229865 31.792119 6 31.152778 6 30.5 C 6 29.847222 6.2229865 29.207882 6.6230469 28.757812 C 7.0231072 28.307744 7.5833339 28 8.5 28 z M 19.5 28 C 20.416666 28 20.976893 28.307744 21.376953 28.757812 C 21.777013 29.207881 22 29.847222 22 30.5 C 22 31.152778 21.777013 31.792118 21.376953 32.242188 C 20.976893 32.692256 20.416666 33 19.5 33 C 18.583334 33 18.023107 32.692256 17.623047 32.242188 C 17.222987 31.792119 17 31.152778 17 30.5 C 17 29.847222 17.222987 29.207882 17.623047 28.757812 C 18.023107 28.307744 18.583334 28 19.5 28 z M 30.5 28 C 31.416666 28 31.976893 28.307744 32.376953 28.757812 C 32.777013 29.207881 33 29.847222 33 30.5 C 33 31.152778 32.777013 31.792118 32.376953 32.242188 C 31.976893 32.692256 31.416666 33 30.5 33 C 29.583334 33 29.023107 32.692256 28.623047 32.242188 C 28.222987 31.792119 28 31.152778 28 30.5 C 28 29.847222 28.222987 29.207882 28.623047 28.757812 C 29.023107 28.307744 29.583334 28 30.5 28 z M 41.5 28 C 42.416666 28 42.976893 28.307744 43.376953 28.757812 C 43.777013 29.207881 44 29.847222 44 30.5 C 44 31.152778 43.777013 31.792118 43.376953 32.242188 C 42.976893 32.692256 42.416666 33 41.5 33 C 40.583334 33 40.023107 32.692256 39.623047 32.242188 C 39.222987 31.792119 39 31.152778 39 30.5 C 39 29.847222 39.222987 29.207882 39.623047 28.757812 C 40.023107 28.307744 40.583334 28 41.5 28 z M 8.5 37 C 7.0833337 37 5.8935589 37.567256 5.1269531 38.429688 C 4.3603473 39.292119 4 40.402778 4 41.5 C 4 42.597222 4.3603473 43.707881 5.1269531 44.570312 C 5.8935589 45.432744 7.0833337 46 8.5 46 C 9.9166663 46 11.106441 45.432745 11.873047 44.570312 C 12.639653 43.707881 13 42.597222 13 41.5 C 13 40.402778 12.639653 39.292119 11.873047 38.429688 C 11.106441 37.567256 9.9166663 37 8.5 37 z M 19.5 37 C 18.083334 37 16.893559 37.567256 16.126953 38.429688 C 15.360347 39.292119 15 40.402778 15 41.5 C 15 42.597222 15.360347 43.707881 16.126953 44.570312 C 16.893559 45.432744 18.083334 46 19.5 46 C 20.916666 46 22.106441 45.432745 22.873047 44.570312 C 23.639653 43.707881 24 42.597222 24 41.5 C 24 40.402778 23.639653 39.292119 22.873047 38.429688 C 22.106441 37.567256 20.916666 37 19.5 37 z M 30.5 37 C 29.083334 37 27.893559 37.567256 27.126953 38.429688 C 26.360347 39.292119 26 40.402778 26 41.5 C 26 42.597222 26.360347 43.707881 27.126953 44.570312 C 27.893559 45.432744 29.083334 46 30.5 46 C 31.916666 46 33.106441 45.432745 33.873047 44.570312 C 34.639653 43.707881 35 42.597222 35 41.5 C 35 40.402778 34.639653 39.292119 33.873047 38.429688 C 33.106441 37.567256 31.916666 37 30.5 37 z M 41.5 37 C 40.083334 37 38.893559 37.567256 38.126953 38.429688 C 37.360347 39.292119 37 40.402778 37 41.5 C 37 42.597222 37.360347 43.707881 38.126953 44.570312 C 38.893559 45.432744 40.083334 46 41.5 46 C 42.916666 46 44.106441 45.432745 44.873047 44.570312 C 45.639653 43.707881 46 42.597222 46 41.5 C 46 40.402778 45.639653 39.292119 44.873047 38.429688 C 44.106441 37.567256 42.916666 37 41.5 37 z M 8.5 39 C 9.4166661 39 9.9768929 39.307744 10.376953 39.757812 C 10.777013 40.207881 11 40.847222 11 41.5 C 11 42.152778 10.777013 42.792119 10.376953 43.242188 C 9.9768929 43.692256 9.4166661 44 8.5 44 C 7.5833339 44 7.0231072 43.692255 6.6230469 43.242188 C 6.2229865 42.792119 6 42.152778 6 41.5 C 6 40.847222 6.2229865 40.207881 6.6230469 39.757812 C 7.0231072 39.307744 7.5833339 39 8.5 39 z M 19.5 39 C 20.416666 39 20.976893 39.307744 21.376953 39.757812 C 21.777013 40.207881 22 40.847222 22 41.5 C 22 42.152778 21.777013 42.792119 21.376953 43.242188 C 20.976893 43.692256 20.416666 44 19.5 44 C 18.583334 44 18.023107 43.692255 17.623047 43.242188 C 17.222987 42.792119 17 42.152778 17 41.5 C 17 40.847222 17.222987 40.207881 17.623047 39.757812 C 18.023107 39.307744 18.583334 39 19.5 39 z M 30.5 39 C 31.416666 39 31.976893 39.307744 32.376953 39.757812 C 32.777013 40.207881 33 40.847222 33 41.5 C 33 42.152778 32.777013 42.792119 32.376953 43.242188 C 31.976893 43.692256 31.416666 44 30.5 44 C 29.583334 44 29.023107 43.692255 28.623047 43.242188 C 28.222987 42.792119 28 42.152778 28 41.5 C 28 40.847222 28.222987 40.207881 28.623047 39.757812 C 29.023107 39.307744 29.583334 39 30.5 39 z M 41.5 39 C 42.416666 39 42.976893 39.307744 43.376953 39.757812 C 43.777013 40.207881 44 40.847222 44 41.5 C 44 42.152778 43.777013 42.792119 43.376953 43.242188 C 42.976893 43.692256 42.416666 44 41.5 44 C 40.583334 44 40.023107 43.692255 39.623047 43.242188 C 39.222987 42.792119 39 42.152778 39 41.5 C 39 40.847222 39.222987 40.207881 39.623047 39.757812 C 40.023107 39.307744 40.583334 39 41.5 39 z',), stroke=())

icons8_pentagon_50 = VectorIcon(fill=('M 25 3 C 23.894531 3 23 3.894531 23 5 C 23 5.0625 22.996094 5.125 23 5.1875 L 5.0625 18.3125 C 4.753906 18.121094 4.390625 18 4 18 C 2.894531 18 2 18.894531 2 20 C 2 20.933594 2.636719 21.714844 3.5 21.9375 L 10.53125 43.65625 C 10.207031 44.011719 10 44.480469 10 45 C 10 46.105469 10.894531 47 12 47 C 12.738281 47 13.371094 46.597656 13.71875 46 L 36.28125 46 C 36.628906 46.597656 37.261719 47 38 47 C 39.105469 47 40 46.105469 40 45 C 40 44.480469 39.792969 44.011719 39.46875 43.65625 L 46.5 21.9375 C 47.363281 21.714844 48 20.933594 48 20 C 48 18.894531 47.105469 18 46 18 C 45.609375 18 45.246094 18.121094 44.9375 18.3125 L 27 5.1875 C 27.003906 5.125 27 5.0625 27 5 C 27 3.894531 26.105469 3 25 3 Z M 24.1875 6.84375 C 24.195313 6.847656 24.210938 6.839844 24.21875 6.84375 C 24.457031 6.945313 24.722656 7 25 7 C 25.277344 7 25.542969 6.945313 25.78125 6.84375 L 25.8125 6.84375 L 44 20.0625 C 44.015625 20.589844 44.246094 21.058594 44.59375 21.40625 L 37.59375 43.03125 C 37.027344 43.148438 36.5625 43.515625 36.28125 44 L 13.71875 44 C 13.4375 43.515625 12.972656 43.148438 12.40625 43.03125 L 5.40625 21.40625 C 5.753906 21.058594 5.984375 20.589844 6 20.0625 Z',), stroke=())

