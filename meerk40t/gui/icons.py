import threading
from functools import lru_cache

import wx
from wx.lib.embeddedimage import PyEmbeddedImage as py_embedded_image

from meerk40t.tools.geomstr import TYPE_ARC, TYPE_CUBIC, TYPE_LINE, TYPE_QUAD, Geomstr

"""
icons serves as a central repository for icons and other assets. These come in two flavors:
A)  Bitmap based icons - they are processed as PyEmbeddedImages which is extended from
    the wx.lib utility of the same name.
B)  Vector icons - they are using the SVG syntax and are processed via the VectorIcon class.

We allow several additional modifications to these assets. For example we allow resizing
and inverting this allows us to easily reuse the icons and to use the icons for dark themed
guis. We permit rotation of the icons, so as to permit reusing these icons and coloring
the icons to match a particular colored object, for example the icons in the tree for operations
using color specific matching.

Origin of icons and addition of new ones
----------------------------------------
A)  The bitmapped icons are from Icon8 and typically IOS Glyph, IOS or Windows Metro in style.

    https://icons8.com/icons

    Find the desired icon and download in 50x50. We use the free license.

    Put the icon file in the Pycharm working directory.
    Using Local Terminal, with wxPython installed.

    img2py -a icons8-icon-name-50.png icons.py

    Paste the icon8_icon_name PyEmbeddedImage() block into icons.py
B)  VectorIcons may come as well from the Icon8 library, in this case we have named
    them icon8_xxxxx, but a lot of the other icons have been designed by the
    MeerK40t team, either by creating them from scratch or by vectorizing some other
    freely available images.
    You can add a VectorIcon by changing into meerk40t source directory and issiuing

    python ./meerk40t/gui/icons.py <fully qualified filename of a svg-file>

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


def get_default_icon_size(context=None):
    res = _GLOBAL_FACTOR * STD_ICON_SIZE
    c = context
    if c is not None:
        if hasattr(c, "root"):
            c = c.root
        if hasattr(c, "bitmap_correction_scale"):
            res *= c.bitmap_correction_scale
    return int(res)


def set_default_icon_size(default_size):
    global STD_ICON_SIZE
    STD_ICON_SIZE = default_size


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
    def message_icon(cls, msg, size=None, color=None, ptsize=48):
        import base64

        if size is None:
            size = STD_ICON_SIZE
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
        **kwargs,
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
        @param force_darkmode:
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
            _r = c1.red - c2.red
            _g = c1.green - c2.green
            _b = c1.blue - c2.blue
            distance_sq = (
                (((512 + red_mean) * _r * _r) >> 8)
                + (4 * _g * _g)
                + (((767 - red_mean) * _b * _b) >> 8)
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
            self._size_x = STD_ICON_SIZE
        if self._size_y <= 0:
            self._size_y = STD_ICON_SIZE
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
        **kwargs,
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
    def __init__(self, fill, stroke=None, edge=0, strokewidth=None):
        self.list_fill = []
        self.list_stroke = []
        # Intentional edge
        self.edge = edge
        if strokewidth is None:
            self.strokewidth = 2
        else:
            self.strokewidth = int(strokewidth)

        if not fill:
            pass
        elif isinstance(fill, str):
            color, bright, pathstr, attrib = self.investigate(fill)
            self.list_fill.append((color, bright, pathstr, attrib))
        elif isinstance(fill, (list, tuple)):
            for e in fill:
                color, bright, pathstr, attrib = self.investigate(e)
                self.list_fill.append((color, bright, pathstr, attrib))
        if not stroke:
            pass
        elif isinstance(stroke, str):
            color, bright, pathstr, attrib = self.investigate(stroke)
            self.list_stroke.append((color, bright, pathstr, attrib))
        elif isinstance(stroke, (list, tuple)):
            for e in stroke:
                color, bright, pathstr, attrib = self.investigate(e)
                self.list_stroke.append((color, bright, pathstr, attrib))
        self._pen = wx.Pen()
        self._brush = wx.Brush()
        self._background = wx.Brush()

        # res_fill = ""
        # for e in self.list_fill:
        #     res_fill += str(hash(e)) + ","
        # res_stroke = ""
        # for e in self.list_stroke:
        #     res_stroke += str(hash(e[2])) + ","
        #
        # self._prehash = res_fill + "|" + res_stroke
        self._lock = threading.Lock()

    def investigate(self, svgstr):
        color = None
        bright = None
        attribs = ""
        pathstr = svgstr
        if pathstr.startswith("["):
            idx = pathstr.find("]")
            pattern = pathstr[1:idx]
            subpattern = pattern.split(",")
            for p in subpattern:
                e = p.strip()
                if e.startswith("fill"):
                    attribs += e + ","
                elif e.startswith("join"):
                    attribs += e + ","
                elif e.startswith("cap"):
                    attribs += e + ","
                elif e.startswith("width"):
                    attribs += e + ","
                elif e.endswith("%"):
                    try:
                        bright = int(e[:-1])
                    except ValueError:
                        pass
                else:
                    if e.startswith("0x"):
                        try:
                            r = int(e[2:4], 16)
                            g = int(e[4:6], 16)
                            b = int(e[6:8], 16)
                            e = wx.Colour(r, g, b)
                            # print (f"Was: {was}, now: {now}, rgb={r}, {g}, {b}")
                        except ValueError:
                            pass
                    color = e
            pathstr = pathstr[idx + 1 :]
            # print (f"{pattern}: {color}, {bright}, {attribs} -> {pathstr[:20]}")
        return color, bright, pathstr, attribs

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
        self._pen.SetWidth(self.strokewidth)

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
        self._pen.SetWidth(self.strokewidth)

    def prepare_bitmap(
        self, final_icon_width, final_icon_height, buffer, forced_background=None
    ):
        # forced_background is a (r, g, b, a) tuple (needed so we can still hash it)
        wincol = self._background.GetColour()
        red, green, blue = wincol.red, wincol.green, wincol.blue

        bmp = wx.Bitmap.FromRGBA(
            final_icon_width,
            final_icon_height,
            red,
            green,
            blue,
            0,
        )
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        # dc.SetBackground(self._background)
        # dc.SetBackground(wx.RED_BRUSH)
        # dc.Clear()
        if forced_background:
            dc.SetBackground(
                wx.Brush(
                    wx.Colour(
                        forced_background[0],
                        forced_background[1],
                        forced_background[2],
                    )
                )
            )
            dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.dc = dc
        stroke_paths = []
        fill_paths = []
        # Establish the box...
        min_x = min_y = max_x = max_y = None

        def get_color(info_color, info_bright, default_color):
            wx_color = None
            if info_color is not None:
                try:
                    wx_color = wx.Colour(info_color)
                except AttributeError:
                    pass
            if info_bright is not None:
                if wx_color is None:
                    wx_color = default_color
                # brightness is a percentage values below 100 indicate darker
                # values beyond 100 indicate lighter
                # no change = 100
                # What about black? This is a special case, so we only consider
                ialpha = info_bright / 100.0
                if (
                    wx_color.red == wx_color.green == wx_color.blue == 0
                    and info_bright > 100
                ):
                    ialpha = (info_bright - 100) / 100.0
                    cr = int(255 * ialpha)
                    cg = int(255 * ialpha)
                    cb = int(255 * ialpha)
                else:
                    cr = int(wx_color.red * ialpha)
                    cg = int(wx_color.green * ialpha)
                    cb = int(wx_color.blue * ialpha)

                # Make sure the stay with 0..255
                cr = max(0, min(255, cr))
                cg = max(0, min(255, cg))
                cb = max(0, min(255, cb))
                wx_color = wx.Colour(cr, cg, cb)
            return wx_color

        def_col = self._brush.GetColour()
        for s_entry in self.list_fill:
            e = s_entry[2]
            attrib = s_entry[3]
            geom = Geomstr.svg(e)
            color = get_color(s_entry[0], s_entry[1], def_col)
            gp = self.make_geomstr(gc, geom)
            bb = geom.bbox()
            m_x, m_y, p_w, p_h = bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]
            fill_paths.append((gp, color, attrib))
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

        def_col = self._pen.GetColour()
        for s_entry in self.list_stroke:
            e = s_entry[2]
            attrib = s_entry[3]
            geom = Geomstr.svg(e)
            bb = geom.bbox()
            m_x, m_y, p_w, p_h = bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]
            color = get_color(s_entry[0], s_entry[1], def_col)
            gp = self.make_geomstr(gc, geom)
            stroke_paths.append((gp, color, attrib))
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

        path_width += 2 * self.edge
        path_height += 2 * self.edge

        stroke_buffer = self.strokewidth
        path_width += 2 * stroke_buffer
        path_height += 2 * stroke_buffer

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
        tx = (
            -min_x
            + self.edge
            + stroke_buffer
            + (final_icon_width - width_scaled) / 2 / scale_x
        )
        ty = (
            -min_y
            + self.edge
            + stroke_buffer
            + (final_icon_height - height_scaled) / 2 / scale_x
        )
        matrix.post_translate(tx, ty)
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

        for entry in fill_paths:
            fill_style = wx.WINDING_RULE
            gp = entry[0]
            colpat = entry[1]
            attrib = entry[2]
            if "fill_evenodd" in attrib:
                fill_style = wx.ODDEVEN_RULE
            if "fill_nonzero" in attrib:
                fill_style = wx.WINDING_RULE

            if colpat is None:
                sbrush = self._brush
            else:
                sbrush = wx.Brush()
                sbrush.SetColour(colpat)
            gc.SetBrush(sbrush)
            gc.FillPath(gp, fillStyle=fill_style)
        for entry in stroke_paths:
            gp = entry[0]
            attrib = entry[2]
            if entry[1] is None:
                spen = self._pen
            else:
                spen = wx.Pen()
                spen.SetColour(entry[1])

            spen.SetWidth(self.strokewidth)
            attributes = attrib.split(",")
            spen.SetCap(wx.CAP_ROUND)
            spen.SetJoin(wx.JOIN_ROUND)
            for attrib in attributes:
                # print (attrib)
                if attrib == "width_bold":
                    spen.SetWidth(int(2 * self.strokewidth))
                elif attrib == "width_narrow":
                    spen.SetWidth(int(0.5 * self.strokewidth))
                elif attrib.startswith("width="):
                    try:
                        s = attrib[6:]
                        lw = int(s)
                        spen.SetWidth(lw)
                    except ValueError:
                        pass
                if attrib == "cap_butt":
                    spen.SetCap(wx.CAP_BUTT)
                if attrib == "cap_round":
                    spen.SetCap(wx.CAP_BUTT)
                if attrib == "cap_square":
                    spen.SetCap(wx.CAP_PROJECTING)

                if attrib == "join_arcs":
                    spen.SetJoin(wx.JOIN_ROUND)
                if attrib == "join_bevel":
                    spen.SetJoin(wx.JOIN_BEVEL)
                if attrib == "join_miter":
                    spen.SetJoin(wx.JOIN_MITER)
                if attrib == "join_miterclip":
                    spen.SetJoin(wx.JOIN_MITER)
            gc.SetPen(spen)
            gc.StrokePath(gp)
        dc.SelectObject(wx.NullBitmap)
        gc.Destroy()
        del gc.dc
        del dc
        return bmp

    @lru_cache(maxsize=1024)
    def retrieve_bitmap(
        self,
        color_dark,
        final_icon_width,
        final_icon_height,
        buffer,
        forced_background=None,
    ):
        # Even if we don't use color_dark in this routine, it is needed
        # to create the proper function hash?!
        # forced_background is a (r, g, b, a) tuple (needed so we can still hash it)

        with self._lock:
            bmp = self.prepare_bitmap(
                final_icon_width,
                final_icon_height,
                buffer,
                forced_background=forced_background,
            )
        return bmp

    def GetBitmap(
        self,
        use_theme=True,
        resize=None,
        color=None,
        rotate=None,
        noadjustment=False,
        keepalpha=False,
        force_darkmode=False,
        force_lightmode=False,
        buffer=None,
        resolution=1,
        forced_background=None,
        **kwargs,
    ):
        # forced_background is a (r, g, b, a) tuple (needed so we can still hash it)
        if color is not None and hasattr(color, "red"):
            if color.red == color.green == color.blue == 255:
                # Color is white...
                force_darkmode = True

        if (force_darkmode or DARKMODE) and not force_lightmode:
            self.dark_mode(color)
            darkm = True
        else:
            self.light_mode(color)
            darkm = False

        if resize is None:
            resize = get_default_icon_size()

        if isinstance(resize, tuple):
            final_icon_width, final_icon_height = resize
        else:
            final_icon_width = resize
            final_icon_height = resize
        if resolution > 1:
            # We don't need to have a one pixel resolution=size
            # It's good enough to have one every resolution pixel
            final_icon_height = int(final_icon_height / resolution) * resolution
            final_icon_width = int(final_icon_width / resolution) * resolution

        final_icon_height = int(final_icon_height)
        final_icon_width = int(final_icon_width)
        if final_icon_height <= 0:
            final_icon_height = 1
        if final_icon_width <= 0:
            final_icon_width = 1
        if buffer is None:
            buffer = 5
            if min(final_icon_height, final_icon_width) < 0.5 * get_default_icon_size():
                buffer = 2
        # Dummy variable for proper hashing via lru_cache
        color_dark = f"{color}|{darkm}"
        return self.retrieve_bitmap(
            color_dark,
            final_icon_width,
            final_icon_height,
            buffer,
            forced_background=forced_background,
        )

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

icons8_camera = VectorIcon(
    "M 19.09375 5 C 18.011719 5 17.105469 5.625 16.5625 6.4375 C 16.5625 6.449219 16.5625 6.457031 16.5625 6.46875 L 14.96875 9 L 6 9 C 3.253906 9 1 11.253906 1 14 L 1 38 C 1 40.746094 3.253906 43 6 43 L 44 43 C 46.746094 43 49 40.746094 49 38 L 49 14 C 49 11.253906 46.746094 9 44 9 L 34.9375 9 L 33.34375 6.46875 C 33.34375 6.457031 33.34375 6.449219 33.34375 6.4375 C 32.800781 5.625 31.894531 5 30.8125 5 Z M 19.09375 7 L 30.8125 7 C 31.132813 7 31.398438 7.175781 31.65625 7.5625 L 33.5625 10.53125 C 33.746094 10.820313 34.0625 11 34.40625 11 L 44 11 C 45.65625 11 47 12.34375 47 14 L 47 38 C 47 39.65625 45.65625 41 44 41 L 6 41 C 4.34375 41 3 39.65625 3 38 L 3 14 C 3 12.34375 4.34375 11 6 11 L 15.5 11 C 15.84375 11 16.160156 10.820313 16.34375 10.53125 L 18.21875 7.5625 L 18.25 7.53125 C 18.5 7.179688 18.789063 7 19.09375 7 Z M 10 13 C 8.355469 13 7 14.355469 7 16 C 7 17.644531 8.355469 19 10 19 C 11.644531 19 13 17.644531 13 16 C 13 14.355469 11.644531 13 10 13 Z M 10 15 C 10.554688 15 11 15.445313 11 16 C 11 16.554688 10.554688 17 10 17 C 9.445313 17 9 16.554688 9 16 C 9 15.445313 9.445313 15 10 15 Z M 25 15 C 18.9375 15 14 19.9375 14 26 C 14 32.0625 18.9375 37 25 37 C 31.0625 37 36 32.0625 36 26 C 36 19.9375 31.0625 15 25 15 Z M 25 17 C 29.980469 17 34 21.019531 34 26 C 34 30.980469 29.980469 35 25 35 C 20.019531 35 16 30.980469 16 26 C 16 21.019531 20.019531 17 25 17 Z"
)

# icons8_cog = VectorIcon(
#     "M 40.25 0 C 39.902344 -0.0117188 39.566406 0.15625 39.375 0.46875 L 37.78125 3.0625 C 37.242188 3.019531 36.722656 3.015625 36.1875 3.0625 L 34.5625 0.5 C 34.300781 0.0859375 33.761719 -0.0625 33.3125 0.125 L 30.5 1.3125 C 30.054688 1.5 29.796875 1.996094 29.90625 2.46875 L 30.59375 5.4375 C 30.179688 5.792969 29.789063 6.175781 29.4375 6.59375 L 26.46875 5.90625 C 25.984375 5.796875 25.527344 6.078125 25.34375 6.53125 L 24.1875 9.375 C 24.003906 9.824219 24.152344 10.335938 24.5625 10.59375 L 27.125 12.1875 C 27.082031 12.730469 27.105469 13.300781 27.15625 13.84375 L 24.59375 15.4375 C 24.179688 15.699219 24.027344 16.238281 24.21875 16.6875 L 25.40625 19.5 C 25.59375 19.945313 26.058594 20.207031 26.53125 20.09375 L 29.5 19.4375 C 29.851563 19.847656 30.238281 20.214844 30.65625 20.5625 L 30 23.53125 C 29.894531 24.007813 30.140625 24.503906 30.59375 24.6875 L 33.4375 25.84375 C 33.558594 25.894531 33.6875 25.90625 33.8125 25.90625 C 34.148438 25.90625 34.46875 25.734375 34.65625 25.4375 L 36.3125 22.84375 C 36.855469 22.882813 37.402344 22.863281 37.9375 22.8125 L 39.59375 25.40625 C 39.859375 25.8125 40.367188 25.96875 40.8125 25.78125 L 43.65625 24.59375 C 44.109375 24.402344 44.332031 23.914063 44.21875 23.4375 L 43.5 20.46875 C 43.902344 20.121094 44.28125 19.722656 44.625 19.3125 L 47.625 19.96875 C 48.109375 20.074219 48.597656 19.824219 48.78125 19.375 L 49.9375 16.53125 C 50.121094 16.074219 49.949219 15.535156 49.53125 15.28125 L 46.90625 13.6875 C 46.945313 13.15625 46.953125 12.625 46.90625 12.09375 L 49.46875 10.40625 C 49.875 10.144531 50.0625 9.632813 49.875 9.1875 L 48.65625 6.375 C 48.46875 5.925781 47.984375 5.667969 47.5 5.78125 L 44.53125 6.5 C 44.179688 6.089844 43.820313 5.722656 43.40625 5.375 L 44.03125 2.375 C 44.132813 1.898438 43.886719 1.402344 43.4375 1.21875 L 40.59375 0.0625 C 40.480469 0.015625 40.367188 0.00390625 40.25 0 Z M 37 8.875 C 37.53125 8.867188 38.070313 8.945313 38.59375 9.15625 C 40.6875 10.007813 41.695313 12.40625 40.84375 14.5 C 39.992188 16.59375 37.59375 17.601563 35.5 16.75 C 33.40625 15.898438 32.398438 13.5 33.25 11.40625 C 33.890625 9.835938 35.40625 8.898438 37 8.875 Z M 14.53125 17 C 14.042969 17 13.609375 17.359375 13.53125 17.84375 L 12.90625 21.78125 C 12.164063 22.007813 11.429688 22.296875 10.75 22.65625 L 7.5 20.34375 C 7.101563 20.058594 6.566406 20.09375 6.21875 20.4375 L 3.46875 23.1875 C 3.125 23.53125 3.097656 24.070313 3.375 24.46875 L 5.65625 27.75 C 5.289063 28.4375 4.980469 29.160156 4.75 29.90625 L 0.84375 30.53125 C 0.359375 30.613281 0 31.042969 0 31.53125 L 0 35.40625 C 0 35.890625 0.335938 36.320313 0.8125 36.40625 L 4.75 37.09375 C 4.980469 37.839844 5.289063 38.5625 5.65625 39.25 L 3.34375 42.5 C 3.058594 42.898438 3.089844 43.433594 3.4375 43.78125 L 6.1875 46.53125 C 6.53125 46.875 7.070313 46.902344 7.46875 46.625 L 10.75 44.34375 C 11.433594 44.707031 12.132813 44.992188 12.875 45.21875 L 13.53125 49.15625 C 13.609375 49.636719 14.042969 50 14.53125 50 L 18.40625 50 C 18.890625 50 19.320313 49.664063 19.40625 49.1875 L 20.09375 45.1875 C 20.835938 44.957031 21.539063 44.675781 22.21875 44.3125 L 25.53125 46.625 C 25.929688 46.902344 26.46875 46.875 26.8125 46.53125 L 29.5625 43.78125 C 29.910156 43.433594 29.941406 42.867188 29.65625 42.46875 L 27.3125 39.21875 C 27.671875 38.539063 27.960938 37.824219 28.1875 37.09375 L 32.1875 36.40625 C 32.667969 36.320313 33 35.890625 33 35.40625 L 33 31.53125 C 33 31.042969 32.640625 30.640625 32.15625 30.5625 L 28.1875 29.90625 C 27.960938 29.175781 27.671875 28.460938 27.3125 27.78125 L 29.625 24.46875 C 29.902344 24.070313 29.875 23.53125 29.53125 23.1875 L 26.78125 20.4375 C 26.433594 20.089844 25.898438 20.058594 25.5 20.34375 L 22.21875 22.6875 C 21.535156 22.324219 20.832031 22.039063 20.09375 21.8125 L 19.40625 17.84375 C 19.324219 17.363281 18.890625 17 18.40625 17 Z M 16.5 28.34375 C 19.355469 28.34375 21.65625 30.644531 21.65625 33.5 C 21.65625 36.355469 19.351563 38.65625 16.5 38.65625 C 13.648438 38.65625 11.34375 36.355469 11.34375 33.5 C 11.34375 30.644531 13.644531 28.34375 16.5 28.34375 Z"
# )

icons8_comments = VectorIcon(
    "M 3 6 L 3 26 L 12.585938 26 L 16 29.414063 L 19.414063 26 L 29 26 L 29 6 Z M 5 8 L 27 8 L 27 24 L 18.585938 24 L 16 26.585938 L 13.414063 24 L 5 24 Z M 9 11 L 9 13 L 23 13 L 23 11 Z M 9 15 L 9 17 L 23 17 L 23 15 Z M 9 19 L 9 21 L 19 21 L 19 19 Z"
)

icons8_computer_support = VectorIcon(
    "M 7 8 C 4.757 8 3 9.757 3 12 L 3 34 C 3 34.738 3.2050625 35.413 3.5390625 36 L 1 36 C 0.447 36 0 36.447 0 37 C 0 39.757 2.243 42 5 42 L 23.896484 42 L 25.896484 40 L 5 40 C 3.696 40 2.584875 39.164 2.171875 38 L 7 38 L 27.896484 38 L 29.896484 36 L 7 36 C 5.859 36 5 35.141 5 34 L 5 12 C 5 10.859 5.859 10 7 10 L 43 10 C 44.141 10 45 10.859 45 12 L 45 22.451172 C 45.705 22.701172 46.374 23.023156 47 23.410156 L 47 12 C 47 9.757 45.243 8 43 8 L 7 8 z M 41.5 24 C 36.81752 24 33 27.81752 33 32.5 C 33 33.484227 33.290881 34.378694 33.599609 35.255859 L 25.064453 43.789062 C 23.652066 45.20145 23.652066 47.521207 25.064453 48.933594 C 26.47684 50.345981 28.79855 50.345981 30.210938 48.933594 L 38.742188 40.400391 C 39.620086 40.709768 40.51563 41 41.5 41 C 46.18248 41 50 37.18248 50 32.5 C 50 31.568566 49.845983 30.67281 49.570312 29.837891 L 49.074219 28.335938 L 47.929688 29.429688 L 43.267578 33.882812 L 40.810547 33.189453 L 40.117188 30.732422 L 45.664062 24.923828 L 44.160156 24.429688 C 43.3262 24.155463 42.431434 24 41.5 24 z M 41.5 26 C 41.611788 26 41.710057 26.045071 41.820312 26.050781 L 37.882812 30.175781 L 39.189453 34.810547 L 43.822266 36.117188 L 47.947266 32.177734 C 47.95306 32.288755 48 32.387457 48 32.5 C 48 36.10152 45.10152 39 41.5 39 C 40.542813 39 39.642068 38.788477 38.818359 38.414062 L 38.1875 38.126953 L 28.794922 47.519531 C 28.147309 48.167144 27.126129 48.167144 26.478516 47.519531 C 25.830902 46.871918 25.830902 45.850738 26.478516 45.203125 L 35.871094 35.8125 L 35.583984 35.181641 C 35.21045 34.35882 35 33.457187 35 32.5 C 35 28.89848 37.89848 26 41.5 26 z"
)

icons8_connected = VectorIcon(
    "M 42.470703 3.9863281 A 1.50015 1.50015 0 0 0 41.439453 4.4394531 L 36.541016 9.3359375 C 34.254638 7.6221223 31.461881 6.8744981 28.753906 7.234375 A 1.50015 1.50015 0 1 0 29.148438 10.207031 C 31.419618 9.9052025 33.783172 10.625916 35.546875 12.357422 A 1.50015 1.50015 0 0 0 35.650391 12.460938 C 38.608211 15.481642 38.60254 20.274411 35.605469 23.271484 L 32.5 26.378906 L 21.621094 15.5 L 24.728516 12.394531 A 1.5012209 1.5012209 0 0 0 22.605469 10.271484 L 19.5 13.378906 L 18.560547 12.439453 A 1.50015 1.50015 0 1 0 16.439453 14.560547 L 18.265625 16.386719 A 1.50015 1.50015 0 0 0 18.611328 16.732422 L 31.265625 29.386719 A 1.50015 1.50015 0 0 0 31.611328 29.732422 L 33.439453 31.560547 A 1.50015 1.50015 0 1 0 35.560547 29.439453 L 34.621094 28.5 L 37.728516 25.394531 C 41.515681 21.607366 41.677294 15.729393 38.574219 11.548828 L 43.560547 6.5605469 A 1.50015 1.50015 0 0 0 42.470703 3.9863281 z M 13.484375 15.984375 A 1.50015 1.50015 0 0 0 12.439453 18.560547 L 13.378906 19.5 L 10.271484 22.605469 C 6.4843192 26.392634 6.3227056 32.270607 9.4257812 36.451172 L 4.4394531 41.439453 A 1.50015 1.50015 0 1 0 6.5605469 43.560547 L 11.542969 38.580078 C 15.593418 41.589531 21.232231 41.53733 25.033203 38.070312 A 1.50015 1.50015 0 1 0 23.011719 35.855469 C 20.007171 38.596036 15.400503 38.522732 12.464844 35.654297 A 1.50015 1.50015 0 0 0 12.349609 35.539062 C 9.3917898 32.518358 9.3974578 27.725589 12.394531 24.728516 L 15.5 21.621094 L 29.439453 35.560547 A 1.50015 1.50015 0 1 0 31.560547 33.439453 L 16.734375 18.613281 A 1.50015 1.50015 0 0 0 16.388672 18.267578 L 14.560547 16.439453 A 1.50015 1.50015 0 0 0 13.484375 15.984375 z"
)

icons8_console = VectorIcon(
    "M 2.84375 3 C 1.285156 3 0 4.285156 0 5.84375 L 0 10.8125 C -0.00390625 10.855469 -0.00390625 10.894531 0 10.9375 L 0 46 C 0 46.550781 0.449219 47 1 47 L 49 47 C 49.550781 47 50 46.550781 50 46 L 50 11 C 50 10.96875 50 10.9375 50 10.90625 L 50 5.84375 C 50 4.285156 48.714844 3 47.15625 3 Z M 2.84375 5 L 47.15625 5 C 47.636719 5 48 5.363281 48 5.84375 L 48 10 L 2 10 L 2 5.84375 C 2 5.363281 2.363281 5 2.84375 5 Z M 2 12 L 48 12 L 48 45 L 2 45 Z M 14.90625 19.9375 C 14.527344 19.996094 14.214844 20.265625 14.101563 20.628906 C 13.988281 20.996094 14.09375 21.394531 14.375 21.65625 L 19.59375 27.03125 L 14.21875 32.25 C 13.820313 32.636719 13.816406 33.273438 14.203125 33.671875 C 14.589844 34.070313 15.226563 34.074219 15.625 33.6875 L 21.6875 27.75 L 22.40625 27.0625 L 21.71875 26.34375 L 15.78125 20.25 C 15.601563 20.058594 15.355469 19.949219 15.09375 19.9375 C 15.03125 19.929688 14.96875 19.929688 14.90625 19.9375 Z M 22.8125 32 C 22.261719 32.050781 21.855469 32.542969 21.90625 33.09375 C 21.957031 33.644531 22.449219 34.050781 23 34 L 36 34 C 36.359375 34.003906 36.695313 33.816406 36.878906 33.503906 C 37.058594 33.191406 37.058594 32.808594 36.878906 32.496094 C 36.695313 32.183594 36.359375 31.996094 36 32 L 23 32 C 22.96875 32 22.9375 32 22.90625 32 C 22.875 32 22.84375 32 22.8125 32 Z"
)

icons8_curly_brackets = VectorIcon(
    "M 9.5703125 4 C 5.9553125 4 4.4385 5.3040312 4.4375 8.4570312 L 4.4375 10.648438 C 4.4375 12.498437 3.9412656 13.115234 2.4472656 13.115234 L 2.4472656 16.398438 C 3.9402656 16.398437 4.4375 17.014563 4.4375 18.851562 L 4.4375 21.435547 C 4.4375 24.660547 5.9673125 26 9.5703125 26 L 10.816406 26 L 10.816406 23.404297 L 10.283203 23.404297 C 8.3622031 23.404297 7.7460938 22.835328 7.7460938 20.986328 L 7.7460938 17.904297 C 7.7460938 16.091297 6.8912969 15.024141 5.2792969 14.869141 L 5.2792969 14.65625 C 6.9632969 14.50225 7.7460938 13.578656 7.7460938 11.847656 L 7.7460938 9.0371094 C 7.7460938 7.1761094 8.3512031 6.6074219 10.283203 6.6074219 L 10.816406 6.6074219 L 10.816406 4 L 9.5703125 4 z M 19.183594 4 L 19.183594 6.6074219 L 19.716797 6.6074219 C 21.648797 6.6074219 22.253906 7.1761094 22.253906 9.0371094 L 22.253906 11.847656 C 22.253906 13.577656 23.037703 14.50225 24.720703 14.65625 L 24.720703 14.871094 C 23.107703 15.025094 22.253906 16.090297 22.253906 17.904297 L 22.253906 20.986328 C 22.253906 22.835328 21.636797 23.404297 19.716797 23.404297 L 19.183594 23.404297 L 19.183594 26.001953 L 20.429688 26.001953 C 24.033688 26.001953 25.5625 24.6615 25.5625 21.4375 L 25.5625 18.853516 C 25.5625 17.015516 26.058734 16.398438 27.552734 16.398438 L 27.552734 13.115234 C 26.059734 13.115234 25.5625 12.499391 25.5625 10.650391 L 25.5625 8.4570312 C 25.5625 5.3040312 24.044687 4 20.429688 4 L 19.183594 4 z"
)

icons8_emergency_stop_button = VectorIcon(
    stroke="M33.1,40.2c-2.7,1.5-5.8,2.4-9.1,2.4C13.7,42.6,5.4,34.3,5.4,24c0-2.9,0.7-5.6,1.8-8.1 M13.7,8.5c2.9-2,6.5-3.1,10.3-3.1c10.3,0,18.6,8.3,18.6,18.6c0,2.8-0.6,5.4-1.7,7.7 M19.3,15.1c1.4-0.7,3-1.2,4.7-1.2c3.4,0,6.4,1.7,8.2,4.2 M18.4,32.5c-2.8-1.8-4.6-4.9-4.6-8.5c0-1.5,0.3-2.9,0.9-4.2 M34,25.7c-0.8,4.8-5,8.4-10,8.4",
    fill="M30.5,21.4l4.2,0.7c0.6,0.1,1.2-0.4,1.2-1v-4.2c0-0.8-1-1.3-1.6-0.8L30,19.7C29.3,20.2,29.6,21.3,30.5,21.4zM24.4,30.7l-2.7,3.2c-0.4,0.5-0.3,1.2,0.3,1.5l3.6,2.1c0.7,0.4,1.6-0.2,1.5-1l-0.9-5.3C26,30.4,25,30.1,24.4,30.7zM18.2,22L16.6,18c-0.2-0.6-0.9-0.8-1.4-0.5l-3.6,2.1c-0.7,0.4-0.6,1.5,0.2,1.8l5.1,1.8C17.7,23.6,18.5,22.8,18.2,22z",
)

# icons8_laptop_settings = VectorIcon(
#     "M 37 0 L 36.400391 3.1992188 C 36.100391 3.2992188 35.700391 3.3996094 35.400391 3.5996094 L 32.699219 1.6992188 L 29.699219 4.6992188 L 31.5 7.1992188 C 31.4 7.5992188 31.199609 7.9007812 31.099609 8.3007812 L 28 8.8007812 L 28 13 L 31.099609 13.5 C 31.199609 13.8 31.3 14.2 31.5 14.5 L 29.699219 17.199219 L 32.699219 20.199219 L 35.400391 18.400391 C 35.800391 18.600391 36.1 18.700781 36.5 18.800781 L 37 22 L 41.099609 22 L 41.699219 18.900391 C 41.999219 18.800391 42.299219 18.7 42.699219 18.5 L 45.400391 20.300781 L 48.400391 17.300781 L 46.5 14.699219 C 46.7 14.299219 46.800391 13.899609 46.900391 13.599609 L 50 13 L 50 8.8007812 L 46.800781 8.3007812 C 46.700781 8.0007812 46.600391 7.6007812 46.400391 7.3007812 L 48.199219 4.5996094 L 45.300781 1.6992188 L 42.699219 3.5996094 C 42.399219 3.3996094 41.999219 3.2992188 41.699219 3.1992188 L 41.199219 0 L 37 0 z M 38.699219 2 L 39.5 2 L 39.900391 4.6992188 L 40.5 4.9003906 C 41.1 5.1003906 41.699219 5.2996094 42.199219 5.5996094 L 42.800781 6 L 45.099609 4.3007812 L 45.599609 4.8007812 L 44 7.0996094 L 44.300781 7.5996094 C 44.600781 8.1996094 44.8 8.8003906 45 9.4003906 L 45.199219 10 L 48 10.400391 L 48 11.199219 L 45.300781 11.800781 L 45.099609 12.400391 C 44.899609 13.000391 44.700391 13.599609 44.400391 14.099609 L 44 14.699219 L 45.699219 17 L 45.099609 17.599609 L 42.800781 16 L 42.300781 16.300781 C 41.700781 16.600781 41.1 16.8 40.5 17 L 39.900391 17.199219 L 39.400391 20 L 38.599609 20 L 38.199219 17.300781 L 37.599609 17.099609 C 36.999609 16.899609 36.400391 16.700391 35.900391 16.400391 L 35.300781 16 L 32.900391 17.599609 L 32.300781 17 L 33.900391 14.699219 L 33.599609 14.199219 C 33.299609 13.599219 33.100391 12.900391 32.900391 12.400391 L 32.699219 11.800781 L 30 11.300781 L 30 10.5 L 32.800781 10 L 32.900391 9.3007812 C 33.000391 8.8007812 33.2 8.1992188 33.5 7.6992188 L 33.900391 7.1992188 L 32.300781 4.9003906 L 32.900391 4.3007812 L 35.199219 5.9003906 L 35.699219 5.6992188 C 36.399219 5.3992188 36.999609 5.1003906 37.599609 4.9003906 L 38.199219 4.8007812 L 38.699219 2 z M 39 6.9003906 C 36.8 6.9003906 35 8.7003906 35 10.900391 C 35 13.100391 36.8 14.900391 39 14.900391 C 41.2 14.900391 43 13.200391 43 10.900391 C 43 8.7003906 41.2 6.9003906 39 6.9003906 z M 8 8 C 5.794 8 4 9.794 4 12 L 4 34 C 4 34.732221 4.2118795 35.409099 4.5566406 36 L 2 36 A 1.0001 1.0001 0 0 0 1 37 C 1 39.749516 3.2504839 42 6 42 L 44 42 C 46.749516 42 49 39.749516 49 37 A 1.0001 1.0001 0 0 0 48 36 L 45.443359 36 C 45.788121 35.409099 46 34.732221 46 34 L 46 21.943359 C 45.367 22.349359 44.702 22.708 44 23 L 44 34 C 44 35.103 43.103 36 42 36 L 8 36 C 6.897 36 6 35.103 6 34 L 6 12 C 6 10.897 6.897 10 8 10 L 26.050781 10 C 26.102781 9.317 26.208328 8.65 26.361328 8 L 8 8 z M 39 9 C 40.1 9 41 9.8 41 11 C 41 12.1 40.1 13 39 13 C 37.9 13 37 12.1 37 11 C 37 9.9 37.9 9 39 9 z M 3.4121094 38 L 8 38 L 42 38 L 46.587891 38 C 46.150803 39.112465 45.275852 40 44 40 L 6 40 C 4.7241482 40 3.8491966 39.112465 3.4121094 38 z"
# )

icons8_laser_beam = VectorIcon(
    fill=(
        "M 24.90625 -0.03125 C 24.863281 -0.0234375 24.820313 -0.0117188 24.78125 0 C 24.316406 0.105469 23.988281 0.523438 24 1 L 24 27.9375 C 24 28.023438 24.011719 28.105469 24.03125 28.1875 C 22.859375 28.59375 22 29.6875 22 31 C 22 32.65625 23.34375 34 25 34 C 26.65625 34 28 32.65625 28 31 C 28 29.6875 27.140625 28.59375 25.96875 28.1875 C 25.988281 28.105469 26 28.023438 26 27.9375 L 26 1 C 26.011719 0.710938 25.894531 0.433594 25.6875 0.238281 C 25.476563 0.0390625 25.191406 -0.0585938 24.90625 -0.03125 Z M 35.125 12.15625 C 34.832031 12.210938 34.582031 12.394531 34.4375 12.65625 L 27.125 25.3125 C 26.898438 25.621094 26.867188 26.03125 27.042969 26.371094 C 27.222656 26.710938 27.578125 26.917969 27.960938 26.90625 C 28.347656 26.894531 28.6875 26.664063 28.84375 26.3125 L 36.15625 13.65625 C 36.34375 13.335938 36.335938 12.9375 36.140625 12.625 C 35.941406 12.308594 35.589844 12.128906 35.21875 12.15625 C 35.1875 12.15625 35.15625 12.15625 35.125 12.15625 Z M 17.78125 17.71875 C 17.75 17.726563 17.71875 17.738281 17.6875 17.75 C 17.375 17.824219 17.113281 18.042969 16.988281 18.339844 C 16.867188 18.636719 16.894531 18.976563 17.0625 19.25 L 21.125 26.3125 C 21.402344 26.796875 22.015625 26.964844 22.5 26.6875 C 22.984375 26.410156 23.152344 25.796875 22.875 25.3125 L 18.78125 18.25 C 18.605469 17.914063 18.253906 17.710938 17.875 17.71875 C 17.84375 17.71875 17.8125 17.71875 17.78125 17.71875 Z M 7 19.6875 C 6.566406 19.742188 6.222656 20.070313 6.140625 20.5 C 6.0625 20.929688 6.273438 21.359375 6.65625 21.5625 L 19.3125 28.875 C 19.796875 29.152344 20.410156 28.984375 20.6875 28.5 C 20.964844 28.015625 20.796875 27.402344 20.3125 27.125 L 7.65625 19.84375 C 7.488281 19.738281 7.292969 19.683594 7.09375 19.6875 C 7.0625 19.6875 7.03125 19.6875 7 19.6875 Z M 37.1875 22.90625 C 37.03125 22.921875 36.882813 22.976563 36.75 23.0625 L 29.6875 27.125 C 29.203125 27.402344 29.035156 28.015625 29.3125 28.5 C 29.589844 28.984375 30.203125 29.152344 30.6875 28.875 L 37.75 24.78125 C 38.164063 24.554688 38.367188 24.070313 38.230469 23.617188 C 38.09375 23.164063 37.660156 22.867188 37.1875 22.90625 Z M 0.71875 30 C 0.167969 30.078125 -0.21875 30.589844 -0.140625 31.140625 C -0.0625 31.691406 0.449219 32.078125 1 32 L 19 32 C 19.359375 32.003906 19.695313 31.816406 19.878906 31.503906 C 20.058594 31.191406 20.058594 30.808594 19.878906 30.496094 C 19.695313 30.183594 19.359375 29.996094 19 30 L 1 30 C 0.96875 30 0.9375 30 0.90625 30 C 0.875 30 0.84375 30 0.8125 30 C 0.78125 30 0.75 30 0.71875 30 Z M 30.71875 30 C 30.167969 30.078125 29.78125 30.589844 29.859375 31.140625 C 29.9375 31.691406 30.449219 32.078125 31 32 L 49 32 C 49.359375 32.003906 49.695313 31.816406 49.878906 31.503906 C 50.058594 31.191406 50.058594 30.808594 49.878906 30.496094 C 49.695313 30.183594 49.359375 29.996094 49 30 L 31 30 C 30.96875 30 30.9375 30 30.90625 30 C 30.875 30 30.84375 30 30.8125 30 C 30.78125 30 30.75 30 30.71875 30 Z M 19.75 32.96875 C 19.71875 32.976563 19.6875 32.988281 19.65625 33 C 19.535156 33.019531 19.417969 33.0625 19.3125 33.125 L 12.25 37.21875 C 11.898438 37.375 11.667969 37.714844 11.65625 38.101563 C 11.644531 38.484375 11.851563 38.839844 12.191406 39.019531 C 12.53125 39.195313 12.941406 39.164063 13.25 38.9375 L 20.3125 34.875 C 20.78125 34.675781 21.027344 34.160156 20.882813 33.671875 C 20.738281 33.183594 20.25 32.878906 19.75 32.96875 Z M 30.03125 33 C 29.597656 33.054688 29.253906 33.382813 29.171875 33.8125 C 29.09375 34.242188 29.304688 34.671875 29.6875 34.875 L 42.34375 42.15625 C 42.652344 42.382813 43.0625 42.414063 43.402344 42.238281 C 43.742188 42.058594 43.949219 41.703125 43.9375 41.320313 C 43.925781 40.933594 43.695313 40.59375 43.34375 40.4375 L 30.6875 33.125 C 30.488281 33.007813 30.257813 32.964844 30.03125 33 Z M 21.9375 35.15625 C 21.894531 35.164063 21.851563 35.175781 21.8125 35.1875 C 21.519531 35.242188 21.269531 35.425781 21.125 35.6875 L 13.84375 48.34375 C 13.617188 48.652344 13.585938 49.0625 13.761719 49.402344 C 13.941406 49.742188 14.296875 49.949219 14.679688 49.9375 C 15.066406 49.925781 15.40625 49.695313 15.5625 49.34375 L 22.875 36.6875 C 23.078125 36.367188 23.082031 35.957031 22.882813 35.628906 C 22.683594 35.304688 22.316406 35.121094 21.9375 35.15625 Z M 27.84375 35.1875 C 27.511719 35.234375 27.226563 35.445313 27.082031 35.746094 C 26.9375 36.046875 26.953125 36.398438 27.125 36.6875 L 31.21875 43.75 C 31.375 44.101563 31.714844 44.332031 32.101563 44.34375 C 32.484375 44.355469 32.839844 44.148438 33.019531 43.808594 C 33.195313 43.46875 33.164063 43.058594 32.9375 42.75 L 28.875 35.6875 C 28.671875 35.320313 28.257813 35.121094 27.84375 35.1875 Z M 24.90625 35.96875 C 24.863281 35.976563 24.820313 35.988281 24.78125 36 C 24.316406 36.105469 23.988281 36.523438 24 37 L 24 45.9375 C 23.996094 46.296875 24.183594 46.632813 24.496094 46.816406 C 24.808594 46.996094 25.191406 46.996094 25.503906 46.816406 C 25.816406 46.632813 26.003906 46.296875 26 45.9375 L 26 37 C 26.011719 36.710938 25.894531 36.433594 25.6875 36.238281 C 25.476563 36.039063 25.191406 35.941406 24.90625 35.96875 Z"
    ),
)

icons8_laserbeam_weak = VectorIcon(
    fill=("M 50 45 a 5 5, 0 1,0 1,0",),
    stroke=(
        "M 50 20 v 30",
        "[150%]M 50 57.5 v 10",
        "[150%]M 42.5 50 h -15",
        "[150%]M 57.5 50 h 15",
        "[150%]M 45 45 L 40 40",
        "[150%]M 45 55 L 40 60",
        "[150%]M 55 45 L 60 40",
        "[150%]M 55 55 L 60 60",
    ),
)

icons8_laser_beam_hazard = VectorIcon(
    "M 50 15.033203 C 48.582898 15.033232 47.16668 15.72259 46.375 17.101562 L 11.564453 77.705078 C 9.9806522 80.462831 12.019116 84 15.197266 84 L 84.802734 84 C 87.98159 84 90.021301 80.462831 88.4375 77.705078 L 53.626953 17.101562 C 52.834735 15.72278 51.417102 15.033174 50 15.033203 z M 50 16.966797 C 50.729648 16.966826 51.459796 17.344439 51.892578 18.097656 L 86.703125 78.701172 C 87.569324 80.209419 86.535879 82 84.802734 82 L 15.197266 82 C 13.465416 82 12.432629 80.209419 13.298828 78.701172 L 48.109375 18.097656 C 48.541695 17.344629 49.270352 16.966768 50 16.966797 z M 49.976562 21.332031 A 0.50005 0.50005 0 0 0 49.554688 21.607422 L 49.558594 21.595703 L 26.78125 61.25 A 0.5005035 0.5005035 0 1 0 27.648438 61.75 L 50.001953 22.833984 L 69.625 57 L 57.931641 57 C 57.862711 56.450605 57.737333 55.919306 57.5625 55.410156 L 59.892578 54.443359 A 0.50005 0.50005 0 0 0 59.689453 53.478516 A 0.50005 0.50005 0 0 0 59.509766 53.519531 L 57.177734 54.486328 C 56.861179 53.842222 56.462551 53.247463 55.992188 52.714844 L 61.314453 47.392578 A 0.50005 0.50005 0 0 0 60.949219 46.535156 A 0.50005 0.50005 0 0 0 60.607422 46.685547 L 55.285156 52.007812 C 54.752537 51.537449 54.157778 51.138821 53.513672 50.822266 L 54.480469 48.490234 A 0.50005 0.50005 0 0 0 54.009766 47.791016 A 0.50005 0.50005 0 0 0 53.556641 48.107422 L 52.589844 50.4375 C 51.927783 50.21016 51.227119 50.070675 50.5 50.025391 L 50.5 40.5 A 0.50005 0.50005 0 0 0 49.992188 39.992188 A 0.50005 0.50005 0 0 0 49.5 40.5 L 49.5 50.025391 C 48.772881 50.070675 48.072217 50.21016 47.410156 50.4375 L 46.443359 48.107422 A 0.50005 0.50005 0 0 0 45.974609 47.791016 A 0.50005 0.50005 0 0 0 45.519531 48.490234 L 46.486328 50.822266 C 45.842222 51.138821 45.247463 51.537449 44.714844 52.007812 L 39.392578 46.685547 A 0.50005 0.50005 0 0 0 39.035156 46.535156 A 0.50005 0.50005 0 0 0 38.685547 47.392578 L 44.007812 52.714844 C 43.537449 53.247463 43.138821 53.842222 42.822266 54.486328 L 40.490234 53.519531 A 0.50005 0.50005 0 0 0 40.294922 53.478516 A 0.50005 0.50005 0 0 0 40.107422 54.443359 L 42.4375 55.410156 C 42.21016 56.072217 42.070675 56.772881 42.025391 57.5 L 33.5 57.5 A 0.50005 0.50005 0 1 0 33.5 58.5 L 42.025391 58.5 C 42.070675 59.227119 42.21016 59.927783 42.4375 60.589844 L 40.107422 61.556641 A 0.50005 0.50005 0 1 0 40.490234 62.480469 L 42.822266 61.513672 C 43.138821 62.157778 43.537449 62.752537 44.007812 63.285156 L 38.685547 68.607422 A 0.50005 0.50005 0 1 0 39.392578 69.314453 L 44.714844 63.992188 C 45.247463 64.462551 45.842222 64.861179 46.486328 65.177734 L 45.519531 67.509766 A 0.50005 0.50005 0 1 0 46.443359 67.892578 L 47.410156 65.5625 C 48.072217 65.78984 48.772881 65.929325 49.5 65.974609 L 49.5 75.5 A 0.50005 0.50005 0 1 0 50.5 75.5 L 50.5 65.974609 C 51.227119 65.929325 51.927783 65.78984 52.589844 65.5625 L 53.556641 67.892578 A 0.50005 0.50005 0 1 0 54.480469 67.509766 L 53.513672 65.177734 C 54.157778 64.861179 54.752537 64.462551 55.285156 63.992188 L 60.607422 69.314453 A 0.50005 0.50005 0 1 0 61.314453 68.607422 L 55.992188 63.285156 C 56.462551 62.752537 56.861179 62.157778 57.177734 61.513672 L 59.509766 62.480469 A 0.50005 0.50005 0 1 0 59.892578 61.556641 L 57.5625 60.589844 C 57.737333 60.080694 57.862711 59.549395 57.931641 59 L 70.773438 59 L 81.685547 78 L 17.451172 78 A 0.50005 0.50005 0 1 0 17.451172 79 L 82.550781 79 A 0.50005 0.50005 0 0 0 82.984375 78.25 L 50.435547 21.582031 A 0.50005 0.50005 0 0 0 49.976562 21.332031 z M 44.826172 45.019531 A 0.50005 0.50005 0 0 0 44.371094 45.71875 L 44.753906 46.642578 A 0.50005 0.50005 0 1 0 45.677734 46.259766 L 45.294922 45.335938 A 0.50005 0.50005 0 0 0 44.826172 45.019531 z M 55.158203 45.021484 A 0.50005 0.50005 0 0 0 54.705078 45.335938 L 54.322266 46.259766 A 0.50005 0.50005 0 1 0 55.246094 46.642578 L 55.628906 45.71875 A 0.50005 0.50005 0 0 0 55.158203 45.021484 z M 49.939453 51.003906 A 0.50005 0.50005 0 0 0 50.0625 51.003906 C 50.967657 51.011882 51.829666 51.190519 52.621094 51.509766 A 0.50005 0.50005 0 0 0 52.751953 51.560547 C 53.549716 51.901213 54.268672 52.388578 54.880859 52.984375 A 0.50005 0.50005 0 0 0 55.009766 53.113281 C 55.608206 53.726739 56.097688 54.447709 56.439453 55.248047 A 0.50005 0.50005 0 0 0 56.488281 55.375 C 56.815986 56.185939 57 57.070277 57 58 C 57 58.944364 56.812181 59.84279 56.474609 60.664062 A 0.50005 0.50005 0 0 0 56.447266 60.736328 C 56.102786 61.548676 55.606272 62.280088 54.998047 62.900391 A 0.50005 0.50005 0 0 0 54.902344 62.996094 C 54.287775 63.59917 53.563359 64.091195 52.759766 64.435547 A 0.50005 0.50005 0 0 0 52.617188 64.490234 C 51.82726 64.808392 50.967598 64.987888 50.064453 64.996094 A 0.50005 0.50005 0 0 0 49.992188 64.992188 A 0.50005 0.50005 0 0 0 49.935547 64.996094 C 49.032638 64.98789 48.17257 64.810189 47.382812 64.492188 A 0.50005 0.50005 0 0 0 47.242188 64.435547 C 46.438807 64.091527 45.714172 63.600645 45.099609 62.998047 A 0.50005 0.50005 0 0 0 45 62.898438 C 44.391656 62.277526 43.894973 61.545514 43.550781 60.732422 A 0.50005 0.50005 0 0 0 43.525391 60.662109 C 43.195567 59.859085 43.011772 58.981915 43.003906 58.060547 A 0.50005 0.50005 0 0 0 43.003906 57.9375 C 43.011882 57.032344 43.190519 56.170334 43.509766 55.378906 A 0.50005 0.50005 0 0 0 43.560547 55.248047 C 43.901213 54.450284 44.388579 53.731328 44.984375 53.119141 A 0.50005 0.50005 0 0 0 45.113281 52.990234 C 45.726739 52.391794 46.447709 51.902313 47.248047 51.560547 A 0.50005 0.50005 0 0 0 47.375 51.511719 C 48.168096 51.191224 49.032048 51.011653 49.939453 51.003906 z M 37.523438 52.330078 A 0.50005 0.50005 0 0 0 37.335938 53.294922 L 38.259766 53.677734 A 0.50005 0.50005 0 1 0 38.642578 52.753906 L 37.71875 52.371094 A 0.50005 0.50005 0 0 0 37.523438 52.330078 z M 62.460938 52.330078 A 0.50005 0.50005 0 0 0 62.28125 52.371094 L 61.357422 52.753906 A 0.50005 0.50005 0 1 0 61.740234 53.677734 L 62.664062 53.294922 A 0.50005 0.50005 0 0 0 62.460938 52.330078 z M 38.439453 62.28125 A 0.50005 0.50005 0 0 0 38.259766 62.322266 L 37.335938 62.705078 A 0.50005 0.50005 0 1 0 37.71875 63.628906 L 38.642578 63.246094 A 0.50005 0.50005 0 0 0 38.439453 62.28125 z M 61.546875 62.28125 A 0.50005 0.50005 0 0 0 61.357422 63.246094 L 62.28125 63.628906 A 0.50005 0.50005 0 1 0 62.664062 62.705078 L 61.740234 62.322266 A 0.50005 0.50005 0 0 0 61.546875 62.28125 z M 25.498047 63.994141 A 0.50005 0.50005 0 0 0 25.058594 64.251953 L 23.335938 67.251953 A 0.50005 0.50005 0 1 0 24.203125 67.748047 L 25.925781 64.748047 A 0.50005 0.50005 0 0 0 25.498047 63.994141 z M 22.626953 68.994141 A 0.50005 0.50005 0 0 0 22.185547 69.251953 L 21.613281 70.251953 A 0.50005 0.50005 0 1 0 22.480469 70.748047 L 23.052734 69.748047 A 0.50005 0.50005 0 0 0 22.626953 68.994141 z M 45.207031 69.042969 A 0.50005 0.50005 0 0 0 44.753906 69.357422 L 44.371094 70.28125 A 0.50005 0.50005 0 1 0 45.294922 70.664062 L 45.677734 69.740234 A 0.50005 0.50005 0 0 0 45.207031 69.042969 z M 54.777344 69.042969 A 0.50005 0.50005 0 0 0 54.322266 69.740234 L 54.705078 70.664062 A 0.50005 0.50005 0 1 0 55.628906 70.28125 L 55.246094 69.357422 A 0.50005 0.50005 0 0 0 54.777344 69.042969 z"
)

icons8_move = VectorIcon(
    "M50.6,21.7L61,11.2v32.5c0,1.7,1.3,3,3,3s3-1.3,3-3V11.2l10.4,10.4c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9	c1.2-1.2,1.2-3.1,0-4.2L66.1,1.9c-1.2-1.2-3.1-1.2-4.2,0L46.3,17.4c-1.2,1.2-1.2,3.1,0,4.2C47.5,22.8,49.4,22.8,50.6,21.7z M61.9,126.1c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9l15.6-15.6c1.2-1.2,1.2-3.1,0-4.2c-1.2-1.2-3.1-1.2-4.2,0	L67,116.8V84.3c0-1.7-1.3-3-3-3s-3,1.3-3,3v32.5l-10.4-10.4c-1.2-1.2-3.1-1.2-4.2,0c-1.2,1.2-1.2,3.1,0,4.2L61.9,126.1z M17.4,81.7c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9c1.2-1.2,1.2-3.1,0-4.2L11.2,67h32.5c1.7,0,3-1.3,3-3	s-1.3-3-3-3H11.2l10.4-10.4c1.2-1.2,1.2-3.1,0-4.2c-1.2-1.2-3.1-1.2-4.2,0L1.9,61.9C1.3,62.4,1,63.2,1,64s0.3,1.6,0.9,2.1L17.4,81.7	z M126.1,61.9l-15.6-15.6c-1.2-1.2-3.1-1.2-4.2,0c-1.2,1.2-1.2,3.1,0,4.2L116.8,61H84.3c-1.7,0-3,1.3-3,3	s1.3,3,3,3h32.5l-10.4,10.4c-1.2,1.2-1.2,3.1,0,4.2c0.6,0.6,1.4,0.9,2.1,0.9s1.5-0.3,2.1-0.9l15.6-15.6c0.6-0.6,0.9-1.3,0.9-2.1	S126.7,62.4,126.1,61.9z"
)

icons8_opened_folder = VectorIcon(
    "M 3 4 C 1.355469 4 0 5.355469 0 7 L 0 43.90625 C -0.0625 44.136719 -0.0390625 44.378906 0.0625 44.59375 C 0.34375 45.957031 1.5625 47 3 47 L 42 47 C 43.492188 47 44.71875 45.875 44.9375 44.4375 C 44.945313 44.375 44.964844 44.3125 44.96875 44.25 C 44.96875 44.230469 44.96875 44.207031 44.96875 44.1875 L 45 44.03125 C 45 44.019531 45 44.011719 45 44 L 49.96875 17.1875 L 50 17.09375 L 50 17 C 50 15.355469 48.644531 14 47 14 L 47 11 C 47 9.355469 45.644531 8 44 8 L 18.03125 8 C 18.035156 8.003906 18.023438 8 18 8 C 17.96875 7.976563 17.878906 7.902344 17.71875 7.71875 C 17.472656 7.4375 17.1875 6.96875 16.875 6.46875 C 16.5625 5.96875 16.226563 5.4375 15.8125 4.96875 C 15.398438 4.5 14.820313 4 14 4 Z M 3 6 L 14 6 C 13.9375 6 14.066406 6 14.3125 6.28125 C 14.558594 6.5625 14.84375 7.03125 15.15625 7.53125 C 15.46875 8.03125 15.8125 8.5625 16.21875 9.03125 C 16.625 9.5 17.179688 10 18 10 L 44 10 C 44.5625 10 45 10.4375 45 11 L 45 14 L 8 14 C 6.425781 14 5.171875 15.265625 5.0625 16.8125 L 5.03125 16.8125 L 5 17 L 2 33.1875 L 2 7 C 2 6.4375 2.4375 6 3 6 Z M 8 16 L 47 16 C 47.5625 16 48 16.4375 48 17 L 43.09375 43.53125 L 43.0625 43.59375 C 43.050781 43.632813 43.039063 43.675781 43.03125 43.71875 C 43.019531 43.757813 43.007813 43.800781 43 43.84375 C 43 43.863281 43 43.886719 43 43.90625 C 43 43.917969 43 43.925781 43 43.9375 C 42.984375 43.988281 42.976563 44.039063 42.96875 44.09375 C 42.964844 44.125 42.972656 44.15625 42.96875 44.1875 C 42.964844 44.230469 42.964844 44.269531 42.96875 44.3125 C 42.84375 44.71875 42.457031 45 42 45 L 3 45 C 2.4375 45 2 44.5625 2 44 L 6.96875 17.1875 L 7 17.09375 L 7 17 C 7 16.4375 7.4375 16 8 16 Z"
)

icons8_pause = VectorIcon(
    "M 12 8 L 12 42 L 22 42 L 22 8 Z M 28 8 L 28 42 L 38 42 L 38 8 Z"
)

icons8_save = VectorIcon(
    "M 7 4 C 5.3545455 4 4 5.3545455 4 7 L 4 43 C 4 44.645455 5.3545455 46 7 46 L 43 46 C 44.645455 46 46 44.645455 46 43 L 46 13.199219 A 1.0001 1.0001 0 0 0 45.707031 12.492188 L 37.507812 4.2929688 A 1.0001 1.0001 0 0 0 36.800781 4 L 7 4 z M 7 6 L 12 6 L 12 18 C 12 19.645455 13.354545 21 15 21 L 34 21 C 35.645455 21 37 19.645455 37 18 L 37 6.6132812 L 44 13.613281 L 44 43 C 44 43.554545 43.554545 44 43 44 L 38 44 L 38 29 C 38 27.354545 36.645455 26 35 26 L 15 26 C 13.354545 26 12 27.354545 12 29 L 12 44 L 7 44 C 6.4454545 44 6 43.554545 6 43 L 6 7 C 6 6.4454545 6.4454545 6 7 6 z M 14 6 L 35 6 L 35 18 C 35 18.554545 34.554545 19 34 19 L 15 19 C 14.445455 19 14 18.554545 14 18 L 14 6 z M 29 8 A 1.0001 1.0001 0 0 0 28 9 L 28 16 A 1.0001 1.0001 0 0 0 29 17 L 32 17 A 1.0001 1.0001 0 0 0 33 16 L 33 9 A 1.0001 1.0001 0 0 0 32 8 L 29 8 z M 30 10 L 31 10 L 31 15 L 30 15 L 30 10 z M 15 28 L 35 28 C 35.554545 28 36 28.445455 36 29 L 36 44 L 14 44 L 14 29 C 14 28.445455 14.445455 28 15 28 z M 8 40 L 8 42 L 10 42 L 10 40 L 8 40 z M 40 40 L 40 42 L 42 42 L 42 40 L 40 40 z"
)

# The following icons were designed by the mk-Team themselves...
icon_fractal = VectorIcon(
    fill="",
    stroke="M 0,0 L 4095,0 L 6143,-3547 L 4095,-7094 L 6143,-10641 L 10239,-10641 L 12287,-7094 M 12287,-7094 L 10239,-3547 L 12287,0 L 16383,0 M 16383,0 L 18431,-3547 L 22527,-3547 L 24575,0 L 28671,0 L 30719,-3547 L 28671,-7094 L 24575,-7094 L 22527,-10641 L 24575,-14188 M 24575,-14188 L 22527,-17735 L 18431,-17735 L 16383,-14188 M 16383,-14188 L 12287,-14188 L 10239,-17735 L 12287,-21283 L 16383,-21283 L 18431,-24830 L 16383,-28377 M 16383,-28377 L 18431,-31924 L 22527,-31924 L 24575,-28377 L 28671,-28377 L 30719,-31924 L 28671,-35471 L 24575,-35471 L 22527,-39019 L 24575,-42566 L 28671,-42566 L 30719,-46113 L 28671,-49660 L 30719,-53207 L 34815,-53207 L 36863,-49660 L 34815,-46113 L 36863,-42566 L 40959,-42566 L 43007,-39019 L 40959,-35471 L 36863,-35471 L 34815,-31924 L 36863,-28377 L 40959,-28377 L 43007,-31924 L 47103,-31924 L 49151,-28377 L 47103,-24830 L 49151,-21283 L 53247,-21283 L 55295,-17735 L 53247,-14188 L 49151,-14188 L 47103,-17735 L 43007,-17735 L 40959,-14188 L 43007,-10641 L 40959,-7094 L 36863,-7094 L 34815,-3547 L 36863,0 L 40959,0 M 40959,0 L 43007,-3547 L 47103,-3547 L 49151,0 M 49151,0 L 53247,0 L 55295,-3547 L 53247,-7094 L 55295,-10641 L 59391,-10641 L 61439,-7094 L 59391,-3547 L 61439,0 L 65535,0",
    strokewidth=100,
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

icon_node_add = VectorIcon(
    fill="",
    stroke=(
        "M 35, 15 h 30",
        "M 50, 0 v 30",
        "M 35,70 h 30 v 30 h -30 z",
        "M 0,85 h 100",
    ),
)

icon_node_delete = VectorIcon(
    fill="",
    stroke=(
        "M 35, 15 h 30",
        #        "M 50, 0 v 30",
        "M 35,70 h 30 v 30 h -30 z",
        "M 0,85 h 100",
    ),
)

icon_node_append = VectorIcon(
    fill="",
    stroke=(
        "M 35, 15 h 30",
        "M 50, 0 v 30",
        "M 0,70 h 15 v 30 h -15",
        "M 70,70 h 30 v 30 h -30 z",
        "M 0,85 h 85",
    ),
)

icon_node_line = VectorIcon(
    fill=(),
    stroke=(
        "M 40,70 L 70, 40",
        "M 10,70 h 30 v 30 h -30 z",
        "M 70,10 h 30 v 30 h -30 z",
    ),
)

icon_node_curve = VectorIcon(
    fill=(),
    stroke=(
        "M 25,70 Q 25,25 70,25",
        "M 10,70 h 30 v 30 h -30 z",
        "M 70,10 h 30 v 30 h -30 z",
    ),
)

icon_node_symmetric = VectorIcon(
    fill=(),
    stroke=(
        "M 0 0 Q 0,50 50,50 Q 100,50 100,0" "M 10 50 h 80" "M 35,35 h 30 v 30 h -30 z",
    ),
)

icon_node_break = VectorIcon(
    fill=("M 70,60 h 10 v 20 h 20 l -25,30 -25,-30 h 20 z",),
    stroke=(
        "M 55 5 h 40 v 40 h -40 z",
        "M 15 115 h 40 v 40 h -40 z",
        "M 95 115 h 40 v 40 h -40 z",
        "M 5, 25 h 140",
        "M 5, 135 h 20",
        "M 125,135 h 20",
    ),
)

icon_node_join = VectorIcon(
    fill=("M 70 60 h 10 v 20 h 20 l -25,30 -25,-30 h 20 z",),
    stroke=(
        "M 15 5 h 40 v 40 h -40 z",
        "M 95 5 h 40 v 40 h -40 z",
        "M 55 115 h 40 v 40 h -40 z",
        "M 5, 135 h 140",
        "M 5, 25 h 20",
        "M 125, 25 h 20",
    ),
)

icon_node_close = VectorIcon(
    fill=(),
    stroke=(
        "M 25 10 h -5 C 0 10 0 40 20 40 h 20",
        "M 40 0 L 30 10 L 40 20",
        "M 30 30 L 40 40 L 30 50",
        "M 45 40 h 5 C 70 40 70 10 50 10 h -20",
    ),
)

icon_node_smooth = VectorIcon(
    fill=(),
    stroke=(
        "M 0 30 h 10 v 10 h -10 z",
        "M 25 0 h 10 v 10 h -10 z",
        "M 50 30 h 10 v 10 h -10 z",
        "M 5 30 Q 5 5 25 5",
        "M 35 5 Q 55 5 55 30",
    ),
)

icon_node_smooth_all = VectorIcon(
    fill=(),
    stroke=(
        "M 0 30 h 10 v 10 h -10 z",
        "M 25 0 h 10 v 10 h -10 z",
        "M 50 30 h 10 v 10 h -10 z",
        "M 75 60 h 10 v 10 h -10 z",
        "M 100 30 h 10 v 10 h -10 z",
        "M 5 30 Q 5 5 30 5 Q 55 5 55 35 Q 55 65 80 65 Q 105 65 105 40",
    ),
)

icon_node_line_all = VectorIcon(
    fill=(),
    stroke=(
        "M 0 30 h 10 v 10 h -10 z",
        "M 25 0 h 10 v 10 h -10 z",
        "M 50 30 h 10 v 10 h -10 z",
        "M 75 60 h 10 v 10 h -10 z",
        "M 100 30 h 10 v 10 h -10 z",
        "M 5 30 L 30 5 55 35 80 65 105 40",
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
    if not filename.startswith("icon"):
        filename = "icon_" + filename

    fills = []
    strokes = []

    def splitted(org):
        s = org
        splits = list()
        flag = True
        while flag and len(s) > 0:
            idx = s.find("Z")
            if idx >= 0:
                # print(s[: idx + 1])
                splits.append(s[: idx + 1])
                s = s[idx + 1 :]
            else:
                flag = False
                splits.append(s)

        return splits

    with open(args.input, "r") as f:
        for event, elem in iterparse(f, events=("end",)):
            if not elem.tag.endswith("path"):
                continue
            path_d = elem.attrib.get("d")
            l_path = splitted(path_d)
            is_stroke = False
            if "stroke-width" in elem.attrib:
                is_stroke = True
            if "style" in elem.attrib:
                path_style = elem.attrib.get("style")
                if "fill:none" in path_style:
                    is_stroke = True
            if is_stroke:
                strokes.extend(l_path)
            else:
                fills.extend(l_path)

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

icons8_info = VectorIcon(
    fill=(
        "M 25 2 C 12.309295 2 2 12.309295 2 25 C 2 37.690705 12.309295 48 25 48 C 37.690705 48 48 37.690705 48 25 C 48 12.309295 37.690705 2 25 2 z M 25 4 C 36.609824 4 46 13.390176 46 25 C 46 36.609824 36.609824 46 25 46 C 13.390176 46 4 36.609824 4 25 C 4 13.390176 13.390176 4 25 4 z M 25 11 A 3 3 0 0 0 22 14 A 3 3 0 0 0 25 17 A 3 3 0 0 0 28 14 A 3 3 0 0 0 25 11 z M 21 21 L 21 23 L 22 23 L 23 23 L 23 36 L 22 36 L 21 36 L 21 38 L 22 38 L 23 38 L 27 38 L 28 38 L 29 38 L 29 36 L 28 36 L 27 36 L 27 21 L 26 21 L 22 21 L 21 21 z",
    ),
    stroke=(),
)

icons8_scissors = VectorIcon(
    fill=(
        "M 30.015625 1.085938 C 29.976563 1.085938 29.9375 1.089844 29.902344 1.09375 C 27.160156 1.367188 25.386719 3.105469 24.378906 4.679688 C 23.371094 6.257813 23.027344 7.773438 23.027344 7.773438 C 23.019531 7.796875 23.015625 7.820313 23.011719 7.84375 L 20.609375 23.0625 C 20.320313 23.128906 16.007813 24.121094 14.285156 24.65625 C 13.828125 24.800781 13.90625 24.777344 13.855469 24.78125 C 13.476563 21.554688 10.824219 19 7.5 19 C 3.921875 19 1 21.921875 1 25.5 C 1 29.078125 3.921875 32 7.5 32 L 7.984375 32 C 10.027344 32.035156 11.660156 31.195313 13.550781 30.453125 C 15.328125 29.761719 17.386719 29.097656 20.398438 29.015625 C 20.710938 31.277344 20.320313 33.261719 19.75 35.152344 C 19.039063 37.511719 18 39.679688 18 42 L 18 42.5 C 18 46.078125 20.921875 49 24.5 49 C 28.078125 49 31 46.078125 31 42.5 C 31 39.058594 28.277344 36.292969 24.890625 36.078125 C 25.300781 34.714844 26.578125 30.433594 26.917969 29.292969 L 42.152344 26.988281 C 42.175781 26.984375 42.199219 26.980469 42.222656 26.972656 C 42.222656 26.972656 43.757813 26.628906 45.355469 25.625 C 46.953125 24.621094 48.71875 22.84375 48.996094 20.097656 C 49.023438 19.8125 48.925781 19.527344 48.730469 19.316406 C 48.535156 19.109375 48.257813 18.992188 47.96875 19 C 47.933594 19 47.894531 19.003906 47.859375 19.011719 L 28.152344 21.824219 L 30.988281 2.230469 C 31.03125 1.945313 30.949219 1.65625 30.761719 1.4375 C 30.574219 1.21875 30.300781 1.089844 30.015625 1.085938 Z M 28.769531 3.589844 L 25.25 27.890625 C 25.25 27.890625 25.195313 28.070313 25.191406 28.082031 C 25.191406 28.085938 25.191406 28.089844 25.1875 28.09375 C 25.0625 28.511719 23.292969 34.449219 22.910156 35.714844 C 22.78125 36.144531 22.722656 36.539063 22.832031 36.964844 C 22.945313 37.386719 23.316406 37.777344 23.652344 37.917969 C 24.117188 38.109375 24.410156 38.0625 24.59375 38.011719 C 27.046875 38.058594 29 40.035156 29 42.5 C 29 44.996094 26.996094 47 24.5 47 C 22.003906 47 20 44.996094 20 42.5 L 20 42 C 20 40.328125 20.90625 38.25 21.664063 35.730469 C 22.394531 33.308594 22.863281 30.40625 22 27.085938 L 24.980469 8.214844 C 24.980469 8.207031 25.261719 7.019531 26.0625 5.757813 C 26.65625 4.835938 27.59375 4.082031 28.769531 3.589844 Z M 7.5 21 C 9.996094 21 12 23.003906 12 25.5 L 12.003906 25.402344 C 12.003906 25.402344 11.984375 25.699219 12.082031 25.953125 C 12.183594 26.210938 12.433594 26.5 12.738281 26.648438 C 13.347656 26.945313 13.949219 26.859375 14.878906 26.566406 C 16.117188 26.183594 19.050781 25.488281 20.269531 25.203125 L 20.011719 26.84375 C 20.003906 26.90625 20 26.964844 20 27.027344 C 16.882813 27.160156 14.617188 27.890625 12.824219 28.59375 C 10.839844 29.367188 9.472656 30.027344 8.015625 30 C 8.011719 30 8.003906 30 8 30 L 7.5 30 C 5.003906 30 3 27.996094 3 25.5 C 3 23.003906 5.003906 21 7.5 21 Z M 46.496094 21.222656 C 45.996094 22.398438 45.226563 23.339844 44.289063 23.933594 C 43.007813 24.738281 41.796875 25.019531 41.785156 25.019531 L 27.371094 27.203125 L 27.851563 23.890625 Z M 7.5 22 C 5.578125 22 4 23.578125 4 25.5 C 4 27.421875 5.578125 29 7.5 29 C 9.421875 29 11 27.421875 11 25.5 C 11 23.578125 9.421875 22 7.5 22 Z M 7.5 24 C 8.339844 24 9 24.660156 9 25.5 C 9 26.339844 8.339844 27 7.5 27 C 6.660156 27 6 26.339844 6 25.5 C 6 24.660156 6.660156 24 7.5 24 Z M 24 24 C 23.449219 24 23 24.449219 23 25 C 23 25.550781 23.449219 26 24 26 C 24.550781 26 25 25.550781 25 25 C 25 24.449219 24.550781 24 24 24 Z M 13.941406 25.21875 C 13.945313 25.222656 13.945313 25.222656 13.949219 25.222656 C 13.953125 25.242188 13.949219 25.246094 13.953125 25.265625 C 13.953125 25.25 13.945313 25.234375 13.941406 25.21875 Z M 24.5 39 C 22.578125 39 21 40.578125 21 42.5 C 21 44.421875 22.578125 46 24.5 46 C 26.421875 46 28 44.421875 28 42.5 C 28 40.578125 26.421875 39 24.5 39 Z M 24.5 41 C 25.339844 41 26 41.660156 26 42.5 C 26 43.339844 25.339844 44 24.5 44 C 23.660156 44 23 43.339844 23 42.5 C 23 41.660156 23.660156 41 24.5 41 Z",
    ),
    stroke=(),
)

icon_mk_undo = VectorIcon(
    fill=(
        "M 16.8125 3.09375 C 16.59375 3.132813 16.398438 3.242188 16.25 3.40625 L 5.34375 14.28125 L 4.65625 15 L 5.34375 15.71875 L 16.25 26.59375 C 16.492188 26.890625 16.878906 27.027344 17.253906 26.941406 C 17.625 26.855469 17.917969 26.5625 18.003906 26.191406 C 18.089844 25.816406 17.953125 25.429688 17.65625 25.1875 L 8.46875 16 L 24 16 C 30.007813 16 34.242188 17.519531 36.96875 19.96875 C 39.695313 22.417969 41 25.835938 41 30 C 41 38.347656 37.15625 44.46875 37.15625 44.46875 C 36.933594 44.769531 36.894531 45.171875 37.0625 45.507813 C 37.230469 45.847656 37.570313 46.0625 37.945313 46.066406 C 38.320313 46.070313 38.667969 45.863281 38.84375 45.53125 C 38.84375 45.53125 43 38.964844 43 30 C 43 25.40625 41.5 21.332031 38.3125 18.46875 C 35.125 15.605469 30.347656 14 24 14 L 8.46875 14 L 17.65625 4.8125 C 17.980469 4.511719 18.066406 4.035156 17.871094 3.640625 C 17.679688 3.242188 17.246094 3.023438 16.8125 3.09375 Z",
    ),
    stroke=(),
)

icon_mk_redo = VectorIcon(
    fill=(
        "M 32.84375 3.09375 C 32.46875 3.160156 32.167969 3.433594 32.0625 3.796875 C 31.957031 4.164063 32.066406 4.554688 32.34375 4.8125 L 41.53125 14 L 26 14 C 19.652344 14 14.875 15.605469 11.6875 18.46875 C 8.5 21.332031 7 25.40625 7 30 C 7 38.964844 11.15625 45.53125 11.15625 45.53125 C 11.332031 45.863281 11.679688 46.070313 12.054688 46.066406 C 12.429688 46.0625 12.769531 45.847656 12.9375 45.507813 C 13.105469 45.171875 13.066406 44.769531 12.84375 44.46875 C 12.84375 44.46875 9 38.347656 9 30 C 9 25.835938 10.304688 22.417969 13.03125 19.96875 C 15.757813 17.519531 19.992188 16 26 16 L 41.53125 16 L 32.34375 25.1875 C 32.046875 25.429688 31.910156 25.816406 31.996094 26.191406 C 32.082031 26.5625 32.375 26.855469 32.746094 26.941406 C 33.121094 27.027344 33.507813 26.890625 33.75 26.59375 L 44.65625 15.71875 L 45.34375 15 L 44.65625 14.28125 L 33.75 3.40625 C 33.542969 3.183594 33.242188 3.070313 32.9375 3.09375 C 32.90625 3.09375 32.875 3.09375 32.84375 3.09375 Z",
    ),
    stroke=(),
)

icons8_left = VectorIcon(
    fill=(
        "M 19.8125 13.09375 C 19.59375 13.132813 19.398438 13.242188 19.25 13.40625 L 8.34375 24.28125 L 7.65625 25 L 8.34375 25.71875 L 19.25 36.59375 C 19.492188 36.890625 19.878906 37.027344 20.253906 36.941406 C 20.625 36.855469 20.917969 36.5625 21.003906 36.191406 C 21.089844 35.816406 20.953125 35.429688 20.65625 35.1875 L 11.46875 26 L 41 26 C 41.359375 26.003906 41.695313 25.816406 41.878906 25.503906 C 42.058594 25.191406 42.058594 24.808594 41.878906 24.496094 C 41.695313 24.183594 41.359375 23.996094 41 24 L 11.46875 24 L 20.65625 14.8125 C 20.980469 14.511719 21.066406 14.035156 20.871094 13.640625 C 20.679688 13.242188 20.246094 13.023438 19.8125 13.09375 Z",
    ),
    stroke=(),
)

icons8_right = VectorIcon(
    fill=(
        "M 38.035156 13.988281 C 37.628906 13.980469 37.257813 14.222656 37.09375 14.59375 C 36.933594 14.96875 37.015625 15.402344 37.300781 15.691406 L 45.277344 24 L 2.023438 24 C 1.664063 23.996094 1.328125 24.183594 1.148438 24.496094 C 0.964844 24.808594 0.964844 25.191406 1.148438 25.503906 C 1.328125 25.816406 1.664063 26.003906 2.023438 26 L 45.277344 26 L 37.300781 34.308594 C 36.917969 34.707031 36.933594 35.339844 37.332031 35.722656 C 37.730469 36.105469 38.363281 36.09375 38.746094 35.691406 L 49.011719 25 L 38.746094 14.308594 C 38.5625 14.109375 38.304688 13.996094 38.035156 13.988281 Z",
    ),
    stroke=(),
)

icons8_up = VectorIcon(
    fill=(
        "M 25 7.65625 L 24.28125 8.34375 L 13.40625 19.25 C 13.109375 19.492188 12.972656 19.878906 13.058594 20.253906 C 13.144531 20.625 13.4375 20.917969 13.808594 21.003906 C 14.183594 21.089844 14.570313 20.953125 14.8125 20.65625 L 24 11.46875 L 24 41 C 23.996094 41.359375 24.183594 41.695313 24.496094 41.878906 C 24.808594 42.058594 25.191406 42.058594 25.503906 41.878906 C 25.816406 41.695313 26.003906 41.359375 26 41 L 26 11.46875 L 35.1875 20.65625 C 35.429688 20.953125 35.816406 21.089844 36.191406 21.003906 C 36.5625 20.917969 36.855469 20.625 36.941406 20.253906 C 37.027344 19.878906 36.890625 19.492188 36.59375 19.25 L 25.71875 8.34375 Z",
    ),
    stroke=(),
)

icons8_down = VectorIcon(
    fill=(
        "M 24.90625 7.96875 C 24.863281 7.976563 24.820313 7.988281 24.78125 8 C 24.316406 8.105469 23.988281 8.523438 24 9 L 24 38.53125 L 14.8125 29.34375 C 14.625 29.144531 14.367188 29.035156 14.09375 29.03125 C 13.6875 29.035156 13.324219 29.28125 13.171875 29.660156 C 13.023438 30.035156 13.113281 30.46875 13.40625 30.75 L 24.28125 41.65625 L 25 42.34375 L 25.71875 41.65625 L 36.59375 30.75 C 36.890625 30.507813 37.027344 30.121094 36.941406 29.746094 C 36.855469 29.375 36.5625 29.082031 36.191406 28.996094 C 35.816406 28.910156 35.429688 29.046875 35.1875 29.34375 L 26 38.53125 L 26 9 C 26.011719 8.710938 25.894531 8.433594 25.6875 8.238281 C 25.476563 8.039063 25.191406 7.941406 24.90625 7.96875 Z",
    ),
    stroke=(),
)

icons8_down_left = VectorIcon(
    fill=(
        "M 42.980469 5.992188 C 42.71875 5.996094 42.472656 6.105469 42.292969 6.292969 L 8 40.585938 L 8 27 C 8.003906 26.730469 7.898438 26.46875 7.707031 26.277344 C 7.515625 26.085938 7.253906 25.980469 6.984375 25.984375 C 6.433594 25.996094 5.992188 26.449219 6 27 L 6 42.847656 C 5.980469 42.957031 5.980469 43.070313 6 43.179688 L 6 44 L 6.824219 44 C 6.933594 44.019531 7.042969 44.019531 7.152344 44 L 23 44 C 23.359375 44.003906 23.695313 43.816406 23.878906 43.503906 C 24.058594 43.191406 24.058594 42.808594 23.878906 42.496094 C 23.695313 42.183594 23.359375 41.996094 23 42 L 9.414063 42 L 43.707031 7.707031 C 44.003906 7.417969 44.089844 6.980469 43.929688 6.601563 C 43.769531 6.21875 43.394531 5.976563 42.980469 5.992188 Z",
    ),
    stroke=(),
    edge=10,
)

icons8_down_right = VectorIcon(
    fill=(
        "M 6.992188 5.992188 C 6.582031 5.992188 6.21875 6.238281 6.0625 6.613281 C 5.910156 6.992188 6 7.421875 6.292969 7.707031 L 40.585938 42 L 27 42 C 26.640625 41.996094 26.304688 42.183594 26.121094 42.496094 C 25.941406 42.808594 25.941406 43.191406 26.121094 43.503906 C 26.304688 43.816406 26.640625 44.003906 27 44 L 42.847656 44 C 42.957031 44.019531 43.070313 44.019531 43.179688 44 L 44 44 L 44 43.175781 C 44.019531 43.066406 44.019531 42.957031 44 42.847656 L 44 27 C 44.003906 26.730469 43.898438 26.46875 43.707031 26.277344 C 43.515625 26.085938 43.253906 25.980469 42.984375 25.984375 C 42.433594 25.996094 41.992188 26.449219 42 27 L 42 40.585938 L 7.707031 6.292969 C 7.519531 6.097656 7.261719 5.992188 6.992188 5.992188 Z",
    ),
    stroke=(),
    edge=10,
)

icons8_up_left = VectorIcon(
    fill=(
        "M 6.992188 5.992188 C 6.945313 5.992188 6.902344 5.992188 6.859375 6 L 6 6 L 6 6.863281 C 5.988281 6.953125 5.988281 7.039063 6 7.128906 L 6 23 C 5.996094 23.359375 6.183594 23.695313 6.496094 23.878906 C 6.808594 24.058594 7.191406 24.058594 7.503906 23.878906 C 7.816406 23.695313 8.003906 23.359375 8 23 L 8 9.414063 L 42.292969 43.707031 C 42.542969 43.96875 42.917969 44.074219 43.265625 43.980469 C 43.617188 43.890625 43.890625 43.617188 43.980469 43.265625 C 44.074219 42.917969 43.96875 42.542969 43.707031 42.292969 L 9.414063 8 L 23 8 C 23.359375 8.003906 23.695313 7.816406 23.878906 7.503906 C 24.058594 7.191406 24.058594 6.808594 23.878906 6.496094 C 23.695313 6.183594 23.359375 5.996094 23 6 L 7.117188 6 C 7.074219 5.992188 7.03125 5.992188 6.992188 5.992188 Z",
    ),
    stroke=(),
    edge=10,
)

icons8_up_right = VectorIcon(
    fill=(
        "M 42.980469 5.992188 C 42.941406 5.992188 42.90625 5.996094 42.871094 6 L 27 6 C 26.640625 5.996094 26.304688 6.183594 26.121094 6.496094 C 25.941406 6.808594 25.941406 7.191406 26.121094 7.503906 C 26.304688 7.816406 26.640625 8.003906 27 8 L 40.585938 8 L 6.292969 42.292969 C 6.03125 42.542969 5.925781 42.917969 6.019531 43.265625 C 6.109375 43.617188 6.382813 43.890625 6.734375 43.980469 C 7.082031 44.074219 7.457031 43.96875 7.707031 43.707031 L 42 9.414063 L 42 23 C 41.996094 23.359375 42.183594 23.695313 42.496094 23.878906 C 42.808594 24.058594 43.191406 24.058594 43.503906 23.878906 C 43.816406 23.695313 44.003906 23.359375 44 23 L 44 7.125 C 44.011719 7.035156 44.011719 6.941406 44 6.851563 L 44 6 L 43.144531 6 C 43.089844 5.992188 43.035156 5.988281 42.980469 5.992188 Z",
    ),
    stroke=(),
    edge=10,
)

icons8_administrative_tools = VectorIcon(
    fill=(
        "M 20.09375 0 C 19.644531 0.0507813 19.285156 0.398438 19.21875 0.84375 L 18.25 6.8125 C 17.082031 7.152344 15.957031 7.585938 14.90625 8.15625 L 10 4.65625 C 9.605469 4.371094 9.066406 4.414063 8.71875 4.75 L 4.8125 8.65625 C 4.476563 9.003906 4.433594 9.542969 4.71875 9.9375 L 8.15625 14.875 C 7.574219 15.941406 7.097656 17.058594 6.75 18.25 L 0.84375 19.21875 C 0.351563 19.296875 -0.0078125 19.722656 0 20.21875 L 0 25.71875 C 0.0078125 26.195313 0.347656 26.597656 0.8125 26.6875 L 6.78125 27.75 C 7.128906 28.925781 7.578125 30.039063 8.15625 31.09375 L 4.65625 36 C 4.371094 36.394531 4.414063 36.933594 4.75 37.28125 L 8.65625 41.1875 C 9.003906 41.523438 9.542969 41.566406 9.9375 41.28125 L 14.84375 37.8125 C 15.90625 38.394531 17.035156 38.839844 18.21875 39.1875 L 19.21875 45.15625 C 19.296875 45.648438 19.722656 46.007813 20.21875 46 L 25.71875 46 C 25.816406 45.992188 25.910156 45.972656 26 45.9375 L 26 49 C 26 49.550781 26.449219 50 27 50 L 49 50 C 49.550781 50 50 49.550781 50 49 L 50 33 C 50 32.96875 50 32.9375 50 32.90625 L 50 31.84375 C 50 30.285156 48.714844 29 47.15625 29 L 38.78125 29 C 38.933594 28.585938 39.089844 28.152344 39.21875 27.75 L 45.15625 26.6875 C 45.636719 26.613281 45.992188 26.203125 46 25.71875 L 46 20.21875 C 46.007813 19.722656 45.648438 19.296875 45.15625 19.21875 L 39.15625 18.25 C 38.8125 17.09375 38.347656 15.980469 37.78125 14.9375 L 41.28125 9.9375 C 41.566406 9.542969 41.523438 9.003906 41.1875 8.65625 L 37.28125 4.75 C 36.933594 4.414063 36.394531 4.371094 36 4.65625 L 31.09375 8.1875 C 30.042969 7.609375 28.925781 7.160156 27.75 6.8125 L 26.6875 0.8125 C 26.597656 0.347656 26.195313 0.0078125 25.71875 0 L 20.21875 0 C 20.175781 -0.00390625 20.136719 -0.00390625 20.09375 0 Z M 21.0625 2 L 24.875 2 L 25.875 7.6875 C 25.945313 8.0625 26.222656 8.367188 26.59375 8.46875 C 28.054688 8.832031 29.433594 9.429688 30.6875 10.1875 C 31.027344 10.394531 31.457031 10.382813 31.78125 10.15625 L 36.46875 6.78125 L 39.15625 9.46875 L 35.84375 14.21875 C 35.605469 14.539063 35.582031 14.96875 35.78125 15.3125 C 36.53125 16.5625 37.105469 17.917969 37.46875 19.375 C 37.5625 19.765625 37.882813 20.0625 38.28125 20.125 L 44 21.0625 L 44 24.875 L 38.28125 25.875 C 37.882813 25.9375 37.5625 26.234375 37.46875 26.625 C 37.351563 27.101563 36.96875 28.160156 36.65625 29 L 28.84375 29 C 28.824219 29 28.800781 29 28.78125 29 C 30.359375 27.480469 31.34375 25.351563 31.34375 23 C 31.34375 18.410156 27.589844 14.65625 23 14.65625 C 18.410156 14.65625 14.65625 18.410156 14.65625 23 C 14.65625 27.589844 18.410156 31.34375 23 31.34375 C 24.148438 31.34375 25.253906 31.109375 26.25 30.6875 C 26.089844 31.042969 26 31.429688 26 31.84375 L 26 32.8125 C 25.996094 32.855469 25.996094 32.894531 26 32.9375 L 26 38.46875 L 24.875 44 L 21.0625 44 L 20.125 38.34375 C 20.0625 37.945313 19.765625 37.625 19.375 37.53125 C 17.910156 37.171875 16.511719 36.601563 15.25 35.84375 C 14.910156 35.636719 14.480469 35.648438 14.15625 35.875 L 9.46875 39.15625 L 6.78125 36.46875 L 10.09375 31.8125 C 10.320313 31.488281 10.332031 31.058594 10.125 30.71875 C 9.359375 29.453125 8.800781 28.09375 8.4375 26.625 C 8.34375 26.234375 8.023438 25.9375 7.625 25.875 L 2 24.875 L 2 21.0625 L 7.625 20.125 C 8.023438 20.0625 8.34375 19.765625 8.4375 19.375 C 8.804688 17.898438 9.394531 16.515625 10.15625 15.25 C 10.363281 14.910156 10.351563 14.480469 10.125 14.15625 L 6.8125 9.46875 L 9.53125 6.78125 L 14.1875 10.09375 C 14.507813 10.332031 14.9375 10.355469 15.28125 10.15625 C 16.535156 9.402344 17.910156 8.828125 19.375 8.46875 C 19.765625 8.375 20.0625 8.054688 20.125 7.65625 Z M 23 16.65625 C 26.507813 16.65625 29.34375 19.492188 29.34375 23 C 29.34375 26.507813 26.507813 29.34375 23 29.34375 C 19.492188 29.34375 16.65625 26.507813 16.65625 23 C 16.65625 19.492188 19.492188 16.65625 23 16.65625 Z M 28.84375 31 L 37.0625 31 C 37.253906 31.058594 37.464844 31.058594 37.65625 31 L 47.15625 31 C 47.636719 31 48 31.363281 48 31.84375 L 48 32 L 28 32 L 28 31.84375 C 28 31.363281 28.363281 31 28.84375 31 Z M 28 34 L 48 34 L 48 48 L 28 48 L 28 38.59375 C 28.042969 38.429688 28.042969 38.257813 28 38.09375 Z M 37 34.59375 L 36.28125 35.28125 L 32.9375 38.625 L 31.65625 37.53125 L 30.90625 36.875 L 29.59375 38.40625 L 30.34375 39.03125 L 32.34375 40.75 L 33.0625 41.375 L 37.71875 36.71875 L 38.40625 36 Z M 37 39.59375 L 36.28125 40.28125 L 32.9375 43.625 L 31.65625 42.53125 L 30.90625 41.875 L 29.59375 43.40625 L 30.34375 44.03125 L 32.34375 45.75 L 33.0625 46.375 L 37.71875 41.71875 L 38.40625 41 Z",
    ),
    stroke=(),
)

icons8_rotate_left = VectorIcon(
    fill=(
        "M 15 3 L 15 5 L 16 5 L 16 3 Z M 12.84375 3.4375 L 12 3.65625 L 11.96875 3.6875 L 11.9375 3.6875 L 11.09375 4 L 11.0625 4 L 11.03125 4.03125 L 10.9375 4.0625 L 11.78125 5.875 L 11.8125 5.875 L 11.875 5.84375 L 12.5625 5.59375 L 12.625 5.5625 L 13.40625 5.34375 Z M 20 4 L 20 12 L 22 12 L 22 6.78125 C 25.03125 8.761719 27 12.0625 27 16 C 27 22.054688 22.054688 27 16 27 C 9.945313 27 5 22.054688 5 16 L 5 15 L 3 15 L 3 16 C 3 23.144531 8.855469 29 16 29 C 23.144531 29 29 23.144531 29 16 C 29 11.941406 27.203125 8.386719 24.34375 6 L 28 6 L 28 4 Z M 9.15625 5 L 8.625 5.34375 L 8.59375 5.375 L 8.5625 5.375 L 7.875 5.90625 L 7.84375 5.9375 L 7.8125 5.9375 L 7.53125 6.1875 L 8.84375 7.6875 L 9.0625 7.5 L 9.125 7.46875 L 9.6875 7.03125 L 9.75 7 L 10.21875 6.6875 Z M 6.09375 7.59375 L 5.875 7.875 L 5.8125 7.9375 L 5.28125 8.625 L 5.28125 8.65625 L 5.25 8.6875 L 4.90625 9.21875 L 6.59375 10.3125 L 6.875 9.84375 L 6.9375 9.78125 L 7.375 9.1875 L 7.40625 9.15625 L 7.625 8.90625 Z M 3.96875 11 L 3.9375 11.125 L 3.90625 11.15625 L 3.90625 11.1875 L 3.59375 12 L 3.59375 12.03125 L 3.5625 12.09375 L 3.34375 12.9375 L 5.25 13.46875 L 5.46875 12.6875 L 5.5 12.625 L 5.75 11.9375 L 5.78125 11.875 L 5.78125 11.84375 Z",
    ),
    stroke=(),
)

icons8_rotate_right = VectorIcon(
    fill=(
        "M 16 3 L 16 5 L 17 5 L 17 3 Z M 19.15625 3.4375 L 18.59375 5.34375 L 19.375 5.5625 L 19.4375 5.59375 L 20.125 5.84375 L 20.1875 5.875 L 20.21875 5.875 L 21.0625 4.0625 L 20.96875 4.03125 L 20.9375 4 L 20.90625 4 L 20.0625 3.6875 L 20.03125 3.6875 L 20 3.65625 Z M 4 4 L 4 6 L 7.65625 6 C 4.796875 8.386719 3 11.941406 3 16 C 3 23.144531 8.855469 29 16 29 C 23.144531 29 29 23.144531 29 16 L 29 15 L 27 15 L 27 16 C 27 22.054688 22.054688 27 16 27 C 9.945313 27 5 22.054688 5 16 C 5 12.0625 6.96875 8.761719 10 6.78125 L 10 12 L 12 12 L 12 4 Z M 22.84375 5 L 21.78125 6.6875 L 22.25 7 L 22.3125 7.03125 L 22.875 7.46875 L 22.9375 7.5 L 23.15625 7.6875 L 24.46875 6.1875 L 24.1875 5.9375 L 24.15625 5.9375 L 24.125 5.90625 L 23.4375 5.375 L 23.40625 5.375 L 23.375 5.34375 Z M 25.90625 7.59375 L 24.375 8.90625 L 24.59375 9.15625 L 24.625 9.1875 L 25.0625 9.78125 L 25.125 9.84375 L 25.40625 10.3125 L 27.09375 9.21875 L 26.75 8.6875 L 26.71875 8.65625 L 26.71875 8.625 L 26.1875 7.9375 L 26.125 7.875 Z M 28.03125 11 L 26.21875 11.84375 L 26.21875 11.875 L 26.25 11.9375 L 26.5 12.625 L 26.53125 12.6875 L 26.75 13.46875 L 28.65625 12.9375 L 28.4375 12.09375 L 28.40625 12.03125 L 28.40625 12 L 28.09375 11.1875 L 28.09375 11.15625 L 28.0625 11.125 Z",
    ),
    stroke=(),
)

icons8_home_filled = VectorIcon(
    fill=(
        "M 25 1.0507812 C 24.7825 1.0507812 24.565859 1.1197656 24.380859 1.2597656 L 1.3808594 19.210938 C 0.95085938 19.550938 0.8709375 20.179141 1.2109375 20.619141 C 1.5509375 21.049141 2.1791406 21.129062 2.6191406 20.789062 L 4 19.710938 L 4 46 C 4 46.55 4.45 47 5 47 L 19 47 L 19 29 L 31 29 L 31 47 L 45 47 C 45.55 47 46 46.55 46 46 L 46 19.710938 L 47.380859 20.789062 C 47.570859 20.929063 47.78 21 48 21 C 48.3 21 48.589063 20.869141 48.789062 20.619141 C 49.129063 20.179141 49.049141 19.550938 48.619141 19.210938 L 25.619141 1.2597656 C 25.434141 1.1197656 25.2175 1.0507812 25 1.0507812 z M 35 5 L 35 6.0507812 L 41 10.730469 L 41 5 L 35 5 z",
    ),
    stroke=(),
)

icons8_copy = VectorIcon(
    fill=(
        "M 19 0 L 19 6 L 21 8 L 21 2 L 36 2 L 36 14 L 48 14 L 48 40 L 33 40 L 33 42 L 50 42 L 50 12.59375 L 37.40625 0 Z M 38 3.40625 L 46.59375 12 L 38 12 Z M 0 8 L 0 50 L 31 50 L 31 20.59375 L 30.71875 20.28125 L 18.71875 8.28125 L 18.40625 8 Z M 2 10 L 17 10 L 17 22 L 29 22 L 29 48 L 2 48 Z M 19 11.4375 L 27.5625 20 L 19 20 Z",
    ),
    stroke=(),
)

icons8_paste = VectorIcon(
    fill=(
        "M 14.8125 0 C 14.335938 0.0898438 13.992188 0.511719 14 1 L 14 2 L 5.90625 2 C 4.304688 2 3 3.304688 3 4.90625 L 3 43 C 3 44.644531 4.304688 46 5.90625 46 L 16 46 L 16 44 L 5.90625 44 C 5.507813 44 5 43.554688 5 43 L 5 4.90625 C 5 4.507813 5.507813 4 5.90625 4 L 14 4 L 14 6 L 7 6 L 7 42 L 16 42 L 16 40 L 9 40 L 9 8 L 14 8 L 14 9 C 14 9.550781 14.449219 10 15 10 L 29 10 C 29.550781 10 30 9.550781 30 9 L 30 8 L 35 8 L 35 14 L 37 14 L 37 6 L 30 6 L 30 4 L 38.09375 4 C 38.492188 4 39 4.507813 39 4.90625 L 39 14 L 41 14 L 41 4.90625 C 41 3.304688 39.695313 2 38.09375 2 L 30 2 L 30 1 C 30 0.449219 29.550781 0 29 0 L 15 0 C 14.96875 0 14.9375 0 14.90625 0 C 14.875 0 14.84375 0 14.8125 0 Z M 16 2 L 28 2 L 28 8 L 16 8 Z M 17.8125 15 C 17.335938 15.089844 16.992188 15.511719 17 16 L 17 49 C 17 49.550781 17.449219 50 18 50 L 46 50 C 46.550781 50 47 49.550781 47 49 L 47 16 C 47 15.449219 46.550781 15 46 15 L 18 15 C 17.96875 15 17.9375 15 17.90625 15 C 17.875 15 17.84375 15 17.8125 15 Z M 19 17 L 45 17 L 45 48 L 19 48 Z M 23.71875 23 C 23.167969 23.078125 22.78125 23.589844 22.859375 24.140625 C 22.9375 24.691406 23.449219 25.078125 24 25 L 41 25 C 41.359375 25.003906 41.695313 24.816406 41.878906 24.503906 C 42.058594 24.191406 42.058594 23.808594 41.878906 23.496094 C 41.695313 23.183594 41.359375 22.996094 41 23 L 24 23 C 23.96875 23 23.9375 23 23.90625 23 C 23.875 23 23.84375 23 23.8125 23 C 23.78125 23 23.75 23 23.71875 23 Z M 23.71875 29 C 23.167969 29.078125 22.78125 29.589844 22.859375 30.140625 C 22.9375 30.691406 23.449219 31.078125 24 31 L 36 31 C 36.359375 31.003906 36.695313 30.816406 36.878906 30.503906 C 37.058594 30.191406 37.058594 29.808594 36.878906 29.496094 C 36.695313 29.183594 36.359375 28.996094 36 29 L 24 29 C 23.96875 29 23.9375 29 23.90625 29 C 23.875 29 23.84375 29 23.8125 29 C 23.78125 29 23.75 29 23.71875 29 Z M 23.71875 35 C 23.167969 35.078125 22.78125 35.589844 22.859375 36.140625 C 22.9375 36.691406 23.449219 37.078125 24 37 L 41 37 C 41.359375 37.003906 41.695313 36.816406 41.878906 36.503906 C 42.058594 36.191406 42.058594 35.808594 41.878906 35.496094 C 41.695313 35.183594 41.359375 34.996094 41 35 L 24 35 C 23.96875 35 23.9375 35 23.90625 35 C 23.875 35 23.84375 35 23.8125 35 C 23.78125 35 23.75 35 23.71875 35 Z M 23.71875 41 C 23.167969 41.078125 22.78125 41.589844 22.859375 42.140625 C 22.9375 42.691406 23.449219 43.078125 24 43 L 36 43 C 36.359375 43.003906 36.695313 42.816406 36.878906 42.503906 C 37.058594 42.191406 37.058594 41.808594 36.878906 41.496094 C 36.695313 41.183594 36.359375 40.996094 36 41 L 24 41 C 23.96875 41 23.9375 41 23.90625 41 C 23.875 41 23.84375 41 23.8125 41 C 23.78125 41 23.75 41 23.71875 41 Z",
    ),
    stroke=(),
)


# icon_fence_closed = VectorIcon(
#     fill=(),
#     stroke=(
#         "M 10 10 L 10 80 L 20 80 L 20 10 L 15 0 z",
#         "M 30 10 L 30 80 L 40 80 L 40 10 L 35 0 z",
#         "M 50 10 L 50 80 L 60 80 L 60 10 L 55 0 z",
#         "M 70 10 L 70 80 L 80 80 L 80 10 L 75 0 z",
#         "M 0 30 h 10 M 20 30 h 10 M 40 30 h 10 M 60 30 h 10 M 80 30 h 10"
#         "M 0 70 h 10 M 20 70 h 10 M 40 70 h 10 M 60 70 h 10 M 80 70 h 10",
#     ),
# )
#
# icon_fence_open = VectorIcon(
#     fill=(),
#     stroke=(
#         "M 10 10 L 10 80 L 20 80 L 20 10 L 15 0 z",
#         "M 70 10 L 70 80 L 80 80 L 80 10 L 75 0 z",
#         "M 30 60 L 40 10",
#         "M 60 60 L 50 10",
#         "M 0 30 h 10 M 80 30 h 10" "M 0 70 h 10  M 80 70 h 10",
#     ),
# )

icon_fence_open = VectorIcon(
    fill=(),
    stroke=(
        "M 100 95 a 5,5, 0 1,0 1,0",
        "M 100 50 a 50,50, 0 1,0 1,0",
        "M 100 120 l 0 70 l -20 -20 m 20 20 l 20 -20",
        "M 100 80 l 0 -70 l -20 20 m 20 -20 l 20 20",
        "M 80 100 l -70 0 l 20 20 m -20 -20 l 20 -20",
        "M 120 100 l 70 0 l -20 20 m 20 -20 l -20 -20",
        "M 110 90 l 50 -50 l -10 0 m 10 0 l 0 10",
        "M 110 110 l 50 50 l -10 0 m 10 0 l 0 -10",
        "M 90 90 l -50 -50 l 10 0 m -10 0 l 0 10",
        "M 90 110 l -50 50 l 10 0 m -10 0 l 0 -10",
    ),
)

icon_fence_closed = VectorIcon(
    fill=(),
    stroke=(
        "M 0 0 h 200 v 200 h -200 z",
        "M 5 5 h 190 v 190 h -190 z",
        "M 100 95 a 5,5, 0 1,0 1,0",
        "M 100 50 a 50,50, 0 1,0 1,0",
        "M 100 120 l 0 70 l -20 -20 m 20 20 l 20 -20",
        "M 100 80 l 0 -70 l -20 20 m 20 -20 l 20 20",
        "M 80 100 l -70 0 l 20 20 m -20 -20 l 20 -20",
        "M 120 100 l 70 0 l -20 20 m 20 -20 l -20 -20",
        "M 110 90 l 50 -50 l -10 0 m 10 0 l 0 10",
        "M 110 110 l 50 50 l -10 0 m 10 0 l 0 -10",
        "M 90 90 l -50 -50 l 10 0 m -10 0 l 0 10",
        "M 90 110 l -50 50 l 10 0 m -10 0 l 0 -10",
    ),
)

icons8_center_of_gravity = VectorIcon(
    fill=(
        "M 24.90625 -0.03125 C 24.863281 -0.0234375 24.820313 -0.0117188 24.78125 0 C 24.316406 0.105469 23.988281 0.523438 24 1 L 24 10.03125 C 21.808594 10.175781 19.65625 10.800781 17.71875 11.875 C 17.160156 12.1875 16.75 12.546875 16.375 12.8125 C 15.917969 13.132813 15.804688 13.761719 16.125 14.21875 C 16.445313 14.675781 17.074219 14.789063 17.53125 14.46875 C 17.992188 14.144531 18.339844 13.816406 18.6875 13.625 C 20.328125 12.714844 22.148438 12.171875 24 12.03125 L 24 24 L 12.03125 24 C 12.097656 23.144531 12.257813 22.285156 12.5 21.4375 C 12.90625 20.015625 13.585938 18.703125 14.4375 17.5 C 14.675781 17.179688 14.703125 16.753906 14.507813 16.40625 C 14.308594 16.0625 13.925781 15.863281 13.53125 15.90625 C 13.238281 15.9375 12.976563 16.097656 12.8125 16.34375 C 11.855469 17.695313 11.074219 19.199219 10.59375 20.875 C 10.300781 21.90625 10.132813 22.949219 10.0625 24 L 1 24 C 0.96875 24 0.9375 24 0.90625 24 C 0.355469 24.027344 -0.0742188 24.496094 -0.046875 25.046875 C -0.0195313 25.597656 0.449219 26.027344 1 26 L 10.0625 26 C 10.207031 28.179688 10.816406 30.320313 11.90625 32.28125 C 12.1875 32.792969 12.476563 33.261719 12.78125 33.6875 C 13.101563 34.144531 13.730469 34.257813 14.1875 33.9375 C 14.644531 33.617188 14.757813 32.988281 14.4375 32.53125 C 14.148438 32.121094 13.878906 31.714844 13.65625 31.3125 C 12.730469 29.640625 12.207031 27.839844 12.0625 26 L 24 26 L 24 37.96875 C 21.632813 37.777344 19.398438 36.910156 17.5 35.5625 C 17.042969 35.242188 16.414063 35.355469 16.09375 35.8125 C 15.773438 36.269531 15.886719 36.898438 16.34375 37.21875 C 18.566406 38.796875 21.203125 39.746094 24 39.9375 L 24 49 C 23.996094 49.359375 24.183594 49.695313 24.496094 49.878906 C 24.808594 50.058594 25.191406 50.058594 25.503906 49.878906 C 25.816406 49.695313 26.003906 49.359375 26 49 L 26 39.96875 C 28.191406 39.824219 30.34375 39.199219 32.28125 38.125 C 32.839844 37.8125 33.246094 37.453125 33.625 37.1875 C 34.019531 36.941406 34.191406 36.457031 34.042969 36.019531 C 33.894531 35.578125 33.460938 35.300781 33 35.34375 C 32.808594 35.355469 32.625 35.417969 32.46875 35.53125 C 32.011719 35.855469 31.664063 36.179688 31.3125 36.375 C 29.671875 37.285156 27.851563 37.828125 26 37.96875 L 26 26 L 37.96875 26 C 37.902344 26.855469 37.742188 27.714844 37.5 28.5625 C 37.09375 29.984375 36.414063 31.296875 35.5625 32.5 C 35.320313 32.789063 35.261719 33.1875 35.410156 33.53125 C 35.558594 33.878906 35.886719 34.113281 36.261719 34.136719 C 36.636719 34.164063 36.992188 33.976563 37.1875 33.65625 C 38.144531 32.304688 38.925781 30.800781 39.40625 29.125 C 39.699219 28.09375 39.867188 27.050781 39.9375 26 L 49 26 C 49.359375 26.003906 49.695313 25.816406 49.878906 25.503906 C 50.058594 25.191406 50.058594 24.808594 49.878906 24.496094 C 49.695313 24.183594 49.359375 23.996094 49 24 L 39.9375 24 C 39.792969 21.820313 39.183594 19.679688 38.09375 17.71875 C 37.8125 17.207031 37.523438 16.738281 37.21875 16.3125 C 36.984375 15.96875 36.558594 15.808594 36.15625 15.90625 C 35.828125 15.980469 35.558594 16.210938 35.4375 16.527344 C 35.316406 16.84375 35.363281 17.195313 35.5625 17.46875 C 35.851563 17.878906 36.121094 18.285156 36.34375 18.6875 C 37.269531 20.359375 37.792969 22.160156 37.9375 24 L 26 24 L 26 12.03125 C 28.367188 12.222656 30.601563 13.089844 32.5 14.4375 C 32.957031 14.757813 33.585938 14.644531 33.90625 14.1875 C 34.226563 13.730469 34.113281 13.101563 33.65625 12.78125 C 31.433594 11.203125 28.796875 10.253906 26 10.0625 L 26 1 C 26.011719 0.710938 25.894531 0.433594 25.6875 0.238281 C 25.476563 0.0390625 25.191406 -0.0585938 24.90625 -0.03125 Z",
    ),
    stroke=(),
)

icons8_lock = VectorIcon(
    fill=(
        "M 16 3 C 12.15625 3 9 6.15625 9 10 L 9 13 L 6 13 L 6 29 L 26 29 L 26 13 L 23 13 L 23 10 C 23 6.15625 19.84375 3 16 3 Z M 16 5 C 18.753906 5 21 7.246094 21 10 L 21 13 L 11 13 L 11 10 C 11 7.246094 13.246094 5 16 5 Z M 8 15 L 24 15 L 24 27 L 8 27 Z",
    ),
    stroke=(),
)

icons8_ungroup_objects = VectorIcon(
    fill=(
        "M 6 6 L 6 12 L 8 12 L 8 29 L 6 29 L 6 35 L 12 35 L 12 33 L 17 33 L 17 38 L 15 38 L 15 44 L 21 44 L 21 42 L 38 42 L 38 44 L 44 44 L 44 38 L 42 38 L 42 21 L 44 21 L 44 15 L 38 15 L 38 17 L 33 17 L 33 12 L 35 12 L 35 6 L 29 6 L 29 8 L 12 8 L 12 6 Z M 8 8 L 10 8 L 10 10 L 8 10 Z M 31 8 L 33 8 L 33 10 L 31 10 Z M 12 10 L 29 10 L 29 12 L 31 12 L 31 29 L 29 29 L 29 31 L 12 31 L 12 29 L 10 29 L 10 12 L 12 12 Z M 40 17 L 42 17 L 42 19 L 40 19 Z M 33 19 L 38 19 L 38 21 L 40 21 L 40 38 L 38 38 L 38 40 L 21 40 L 21 38 L 19 38 L 19 33 L 29 33 L 29 35 L 35 35 L 35 29 L 33 29 Z M 8 31 L 10 31 L 10 33 L 8 33 Z M 31 31 L 33 31 L 33 33 L 31 33 Z M 17 40 L 19 40 L 19 42 L 17 42 Z M 40 40 L 42 40 L 42 42 L 40 42 Z",
    ),
    stroke=(),
)

icons8_group_objects = VectorIcon(
    fill=(
        "M 3 3 L 3 4 L 3 11 L 6 11 L 6 39 L 3 39 L 3 47 L 11 47 L 11 46 L 11 44 L 39 44 L 39 47 L 47 47 L 47 46 L 47 39 L 44 39 L 44 11 L 47 11 L 47 10 L 47 3 L 39 3 L 39 6 L 11 6 L 11 3 L 3 3 z M 5 5 L 9 5 L 9 9 L 5 9 L 5 5 z M 41 5 L 45 5 L 45 9 L 43 9 L 41 9 L 41 7 L 41 5 z M 11 8 L 39 8 L 39 11 L 42 11 L 42 39 L 39 39 L 39 42 L 11 42 L 11 39 L 8 39 L 8 11 L 11 11 L 11 8 z M 13 13 L 13 14 L 13 29 L 21 29 L 21 37 L 37 37 L 37 21 L 29 21 L 29 13 L 13 13 z M 15 15 L 27 15 L 27 27 L 15 27 L 15 15 z M 29 23 L 35 23 L 35 35 L 23 35 L 23 29 L 29 29 L 29 23 z M 5 41 L 7 41 L 9 41 L 9 43 L 9 45 L 5 45 L 5 41 z M 41 41 L 43 41 L 45 41 L 45 45 L 41 45 L 41 43 L 41 41 z",
    ),
    stroke=(),
)

icons_evenspace_vert = VectorIcon(
    fill=(
        "M6,13.5A1.50164,1.50164,0,0,0,4.5,15v2A1.50164,1.50164,0,0,0,6,18.5H18A1.50164,1.50164,0,0,0,19.5,17V15A1.50164,1.50164,0,0,0,18,13.5ZM18.5,15v2a.50065.50065,0,0,1-.5.5H6a.50065.50065,0,0,1-.5-.5V15a.50065.50065,0,0,1,.5-.5H18A.50065.50065,0,0,1,18.5,15ZM15,6.5A1.50164,1.50164,0,0,0,16.5,5V3A1.50164,1.50164,0,0,0,15,1.5H9A1.50164,1.50164,0,0,0,7.5,3V5A1.50164,1.50164,0,0,0,9,6.5ZM8.5,5V3A.50065.50065,0,0,1,9,2.5h6a.50065.50065,0,0,1,.5.5V5a.50065.50065,0,0,1-.5.5H9A.50065.50065,0,0,1,8.5,5Zm-6,17a.49971.49971,0,0,1,.5-.5H21a.5.5,0,0,1,0,1H3A.49971.49971,0,0,1,2.5,22ZM3,9.5H21a.5.5,0,0,1,0,1H3a.5.5,0,0,1,0-1Z",
    ),
    stroke=(),
)

icons_evenspace_horiz = VectorIcon(
    fill=(
        "M7,4.5A1.50164,1.50164,0,0,0,5.5,6V18A1.50164,1.50164,0,0,0,7,19.5H9A1.50164,1.50164,0,0,0,10.5,18V6A1.50164,1.50164,0,0,0,9,4.5ZM9.5,6V18a.50065.50065,0,0,1-.5.5H7a.50065.50065,0,0,1-.5-.5V6A.50065.50065,0,0,1,7,5.5H9A.50065.50065,0,0,1,9.5,6ZM21,7.5H19A1.50164,1.50164,0,0,0,17.5,9v6A1.50164,1.50164,0,0,0,19,16.5h2A1.50164,1.50164,0,0,0,22.5,15V9A1.50164,1.50164,0,0,0,21,7.5Zm.5,7.5a.50065.50065,0,0,1-.5.5H19a.50065.50065,0,0,1-.5-.5V9a.50065.50065,0,0,1,.5-.5h2a.50065.50065,0,0,1,.5.5ZM2.5,3V21a.5.5,0,0,1-1,0V3a.5.5,0,0,1,1,0ZM14,2.5a.49971.49971,0,0,1,.5.5V21a.5.5,0,0,1-1,0V3A.49971.49971,0,0,1,14,2.5Z",
    ),
    stroke=(),
)

icons8_measure = VectorIcon(
    fill=(
        "M 35.0625 1.5 C 34.835938 1.53125 34.625 1.644531 34.46875 1.8125 L 1.875 34.40625 C 1.488281 34.796875 1.488281 35.421875 1.875 35.8125 L 14.09375 48.03125 C 14.28125 48.226563 14.542969 48.335938 14.8125 48.335938 C 15.082031 48.335938 15.34375 48.226563 15.53125 48.03125 L 48.125 15.4375 C 48.511719 15.046875 48.511719 14.421875 48.125 14.03125 L 35.90625 1.8125 C 35.859375 1.753906 35.808594 1.703125 35.75 1.65625 C 35.574219 1.542969 35.367188 1.488281 35.15625 1.5 C 35.125 1.5 35.09375 1.5 35.0625 1.5 Z M 35.1875 3.9375 L 46 14.75 L 14.8125 45.90625 L 4 35.125 L 6.84375 32.28125 L 9.28125 34.71875 L 10.71875 33.28125 L 8.28125 30.84375 L 10.84375 28.28125 L 16.28125 33.71875 L 17.71875 32.28125 L 12.28125 26.84375 L 14.84375 24.28125 L 17.28125 26.71875 L 18.71875 25.28125 L 16.28125 22.84375 L 18.84375 20.28125 L 24.28125 25.71875 L 25.71875 24.28125 L 20.28125 18.84375 L 22.84375 16.28125 L 25.28125 18.71875 L 26.71875 17.28125 L 24.28125 14.84375 L 26.84375 12.28125 L 32.28125 17.71875 L 33.71875 16.28125 L 28.28125 10.84375 L 30.84375 8.28125 L 33.28125 10.71875 L 34.71875 9.28125 L 32.28125 6.84375 Z",
    ),
    stroke=(),
)

icons8_unlock = VectorIcon(
    fill=(
        "M 16 3 C 12.964844 3 10.414063 4.964844 9.375 7.625 L 11.21875 8.375 C 11.976563 6.433594 13.835938 5 16 5 C 18.753906 5 21 7.246094 21 10 L 21 13 L 6 13 L 6 29 L 26 29 L 26 13 L 23 13 L 23 10 C 23 6.15625 19.84375 3 16 3 Z M 8 15 L 24 15 L 24 27 L 8 27 Z",
    ),
    stroke=(),
)

icons8_keyboard = VectorIcon(
    fill=(
        "M 36.9375 2.84375 C 36.9375 5.9375 36.214844 7.304688 35.28125 8.0625 C 34.347656 8.820313 32.925781 9.058594 31.3125 9.28125 C 29.699219 9.503906 27.898438 9.710938 26.40625 10.90625 C 25.167969 11.898438 24.3125 13.539063 24.0625 16 L 4 16 C 1.800781 16 0 17.800781 0 20 L 0 40 C 0 42.199219 1.800781 44 4 44 L 46 44 C 48.199219 44 50 42.199219 50 40 L 50 20 C 50 17.800781 48.199219 16 46 16 L 26.09375 16 C 26.308594 14.0625 26.910156 13.066406 27.65625 12.46875 C 28.585938 11.722656 29.976563 11.503906 31.59375 11.28125 C 33.210938 11.058594 35.039063 10.839844 36.53125 9.625 C 38.023438 8.410156 38.9375 6.269531 38.9375 2.84375 Z M 4 18 L 46 18 C 47.117188 18 48 18.882813 48 20 L 48 40 C 48 41.117188 47.117188 42 46 42 L 4 42 C 2.882813 42 2 41.117188 2 40 L 2 20 C 2 18.882813 2.882813 18 4 18 Z M 5 22 L 5 26 L 9 26 L 9 22 Z M 11 22 L 11 26 L 15 26 L 15 22 Z M 17 22 L 17 26 L 21 26 L 21 22 Z M 23 22 L 23 26 L 27 26 L 27 22 Z M 29 22 L 29 26 L 33 26 L 33 22 Z M 35 22 L 35 26 L 39 26 L 39 22 Z M 41 22 L 41 26 L 45 26 L 45 22 Z M 5 28 L 5 32 L 12 32 L 12 28 Z M 14 28 L 14 32 L 18 32 L 18 28 Z M 20 28 L 20 32 L 24 32 L 24 28 Z M 26 28 L 26 32 L 30 32 L 30 28 Z M 32 28 L 32 32 L 36 32 L 36 28 Z M 38 28 L 38 32 L 45 32 L 45 28 Z M 5 34 L 5 38 L 9 38 L 9 34 Z M 11 34 L 11 38 L 15 38 L 15 34 Z M 17 34 L 17 38 L 33 38 L 33 34 Z M 35 34 L 35 38 L 39 38 L 39 34 Z M 41 34 L 41 38 L 45 38 L 45 34 Z",
    ),
    stroke=(),
)

icons8_caret_up = VectorIcon(
    fill=(
        "M 24.96875 13 C 24.449219 13.007813 23.953125 13.21875 23.585938 13.585938 L 3.585938 33.585938 C 3.0625 34.085938 2.851563 34.832031 3.035156 35.535156 C 3.21875 36.234375 3.765625 36.78125 4.464844 36.964844 C 5.167969 37.148438 5.914063 36.9375 6.414063 36.414063 L 25 17.828125 L 43.585938 36.414063 C 44.085938 36.9375 44.832031 37.148438 45.535156 36.964844 C 46.234375 36.78125 46.78125 36.234375 46.964844 35.535156 C 47.148438 34.832031 46.9375 34.085938 46.414063 33.585938 L 26.414063 13.585938 C 26.03125 13.203125 25.511719 12.992188 24.96875 13 Z",
    ),
    stroke=(),
)

icons8_caret_down = VectorIcon(
    fill=(
        "M 44.984375 12.96875 C 44.453125 12.984375 43.953125 13.203125 43.585938 13.585938 L 25 32.171875 L 6.414063 13.585938 C 6.035156 13.199219 5.519531 12.980469 4.976563 12.980469 C 4.164063 12.980469 3.433594 13.476563 3.128906 14.230469 C 2.820313 14.984375 3.003906 15.847656 3.585938 16.414063 L 23.585938 36.414063 C 24.367188 37.195313 25.632813 37.195313 26.414063 36.414063 L 46.414063 16.414063 C 47.007813 15.84375 47.195313 14.964844 46.875 14.203125 C 46.558594 13.441406 45.808594 12.953125 44.984375 12.96875 Z",
    ),
    stroke=(),
)

icons8_caret_left = VectorIcon(
    fill=(
        "M 34.960938 2.980469 C 34.441406 2.996094 33.949219 3.214844 33.585938 3.585938 L 13.585938 23.585938 C 12.804688 24.367188 12.804688 25.632813 13.585938 26.414063 L 33.585938 46.414063 C 34.085938 46.9375 34.832031 47.148438 35.535156 46.964844 C 36.234375 46.78125 36.78125 46.234375 36.964844 45.535156 C 37.148438 44.832031 36.9375 44.085938 36.414063 43.585938 L 17.828125 25 L 36.414063 6.414063 C 37.003906 5.839844 37.183594 4.960938 36.863281 4.199219 C 36.539063 3.441406 35.785156 2.957031 34.960938 2.980469 Z",
    ),
    stroke=(),
)

icons8_caret_right = VectorIcon(
    fill=(
        "M 14.980469 2.980469 C 14.164063 2.980469 13.433594 3.476563 13.128906 4.230469 C 12.820313 4.984375 13.003906 5.847656 13.585938 6.414063 L 32.171875 25 L 13.585938 43.585938 C 13.0625 44.085938 12.851563 44.832031 13.035156 45.535156 C 13.21875 46.234375 13.765625 46.78125 14.464844 46.964844 C 15.167969 47.148438 15.914063 46.9375 16.414063 46.414063 L 36.414063 26.414063 C 37.195313 25.632813 37.195313 24.367188 36.414063 23.585938 L 16.414063 3.585938 C 16.035156 3.199219 15.519531 2.980469 14.980469 2.980469 Z",
    ),
    stroke=(),
)

icons8_delete = VectorIcon(
    fill=(
        "M 7.71875 6.28125 L 6.28125 7.71875 L 23.5625 25 L 6.28125 42.28125 L 7.71875 43.71875 L 25 26.4375 L 42.28125 43.71875 L 43.71875 42.28125 L 26.4375 25 L 43.71875 7.71875 L 42.28125 6.28125 L 25 23.5625 Z",
    ),
    stroke=(),
)

icons8_disconnected = VectorIcon(
    fill=(
        "M 43.28125 2.28125 L 38.5625 7 L 36.3125 4.75 C 35.144531 3.582031 33.601563 3 32.0625 3 C 30.523438 3 29.011719 3.582031 27.84375 4.75 L 23 9.5625 L 21.71875 8.28125 C 21.476563 8.03125 21.121094 7.925781 20.78125 8 C 20.40625 8.066406 20.105469 8.339844 20 8.703125 C 19.894531 9.070313 20.003906 9.460938 20.28125 9.71875 L 25.0625 14.5 L 18.9375 20.65625 L 20.34375 22.0625 L 26.5 15.9375 L 34.0625 23.5 L 27.9375 29.65625 L 29.34375 31.0625 L 35.5 24.9375 L 40.28125 29.71875 C 40.679688 30.117188 41.320313 30.117188 41.71875 29.71875 C 42.117188 29.320313 42.117188 28.679688 41.71875 28.28125 L 40.4375 27 L 45.21875 22.15625 C 47.554688 19.820313 47.554688 15.992188 45.21875 13.65625 L 43 11.4375 L 47.71875 6.71875 L 46.28125 5.28125 L 41.5625 10 L 40 8.4375 L 44.71875 3.71875 Z M 32.0625 4.96875 C 33.085938 4.96875 34.121094 5.371094 34.90625 6.15625 L 43.8125 15.0625 C 45.382813 16.632813 45.382813 19.148438 43.8125 20.71875 L 43.8125 20.75 L 39 25.5625 L 24.4375 11 L 29.25 6.15625 C 30.035156 5.371094 31.039063 4.96875 32.0625 4.96875 Z M 8.90625 19.96875 C 8.863281 19.976563 8.820313 19.988281 8.78125 20 C 8.40625 20.066406 8.105469 20.339844 8 20.703125 C 7.894531 21.070313 8.003906 21.460938 8.28125 21.71875 L 9.5625 23 L 4.75 27.84375 C 2.414063 30.179688 2.414063 33.976563 4.75 36.3125 L 7 38.5625 L 2.28125 43.28125 L 3.71875 44.71875 L 8.4375 40 L 10 41.5625 L 5.28125 46.28125 L 6.71875 47.71875 L 11.4375 43 L 13.6875 45.25 C 16.023438 47.585938 19.820313 47.585938 22.15625 45.25 L 27 40.4375 L 28.28125 41.71875 C 28.679688 42.117188 29.320313 42.117188 29.71875 41.71875 C 30.117188 41.320313 30.117188 40.679688 29.71875 40.28125 L 9.71875 20.28125 C 9.511719 20.058594 9.210938 19.945313 8.90625 19.96875 Z M 11 24.4375 L 25.5625 39 L 20.75 43.84375 C 19.179688 45.414063 16.664063 45.414063 15.09375 43.84375 L 6.15625 34.90625 C 4.585938 33.335938 4.585938 30.820313 6.15625 29.25 Z",
    ),
    stroke=(),
)

icons8_usb_connector = VectorIcon(
    fill=(
        "M 32 1 L 25 12 L 30 12 L 29.261719 41.533203 L 20.814453 37.634766 L 20.060547 32.626953 A 6 6 0 0 0 18 21 A 6 6 0 0 0 16.693359 32.851562 L 17.009766 39.199219 L 17.064453 40.310547 L 18.162109 40.816406 L 29.152344 45.888672 L 29.003906 51.806641 A 6 6 0 0 0 32 63 A 6 6 0 0 0 34.996094 51.806641 L 34.673828 38.96875 L 45.837891 33.816406 L 46.935547 33.310547 L 46.990234 32.199219 L 47.300781 26 L 51 26 L 51 16 L 41 16 L 41 26 L 43.882812 26 L 43.185547 30.634766 L 34.564453 34.613281 L 34 12 L 39 12 L 32 1 z",
    ),
    stroke=(),
)

icons8_user_location = VectorIcon(
    fill=(
        "M 25 2 C 16.175781 2 9 9.175781 9 18 C 9 24.34375 12.863281 31.664063 16.65625 37.5 C 20.449219 43.335938 24.25 47.65625 24.25 47.65625 C 24.441406 47.871094 24.714844 47.996094 25 47.996094 C 25.285156 47.996094 25.558594 47.871094 25.75 47.65625 C 25.75 47.65625 29.550781 43.328125 33.34375 37.5 C 37.136719 31.671875 41 24.375 41 18 C 41 9.175781 33.824219 2 25 2 Z M 25 4 C 32.742188 4 39 10.257813 39 18 C 39 23.539063 35.363281 30.742188 31.65625 36.4375 C 28.546875 41.210938 25.921875 44.355469 25 45.4375 C 24.082031 44.355469 21.457031 41.195313 18.34375 36.40625 C 14.636719 30.703125 11 23.5 11 18 C 11 10.257813 17.257813 4 25 4 Z M 25 11.84375 L 24.5 12.15625 L 17 16.65625 L 18 18.34375 L 18 26 L 32 26 L 32 18.34375 L 33 16.65625 L 25.5 12.15625 Z M 25 14.15625 L 30 17.15625 L 30 24 L 27 24 L 27 19 L 23 19 L 23 24 L 20 24 L 20 17.15625 Z",
    ),
    stroke=(),
)

icons8_choose_font = VectorIcon(
    fill=(
        "M 15.529297 3.9785156 A 1.50015 1.50015 0 0 0 15.259766 4 L 12 4 C 9.6666667 4 8.0772187 5.229724 7.1992188 6.4003906 C 6.3212187 7.5710573 6.0292969 8.7578125 6.0292969 8.7578125 A 1.0004595 1.0004595 0 0 0 7.9707031 9.2421875 C 7.9707031 9.2421875 8.1787814 8.4289427 8.8007812 7.5996094 C 9.4227812 6.770276 10.333333 6 12 6 L 13.833984 6 C 13.179241 8.7555904 12.600708 11.027355 12.068359 13 L 11 13 A 1.0001 1.0001 0 1 0 11 15 L 11.529297 15 C 10.768676 17.643284 10.114342 19.505472 9.5195312 20.710938 C 8.9399105 21.885618 8.4532978 22.411041 8.0644531 22.662109 C 7.6756085 22.913178 7.2720618 23 6.5 23 C 5.7812349 23 5.7988281 22.75 5.7988281 22.75 A 1.50015 1.50015 0 1 0 3.2011719 24.25 C 3.2011719 24.25 4.3747651 26 6.5 26 C 7.5469382 26 8.6766885 25.836822 9.6914062 25.181641 C 10.706124 24.526459 11.493355 23.489383 12.208984 22.039062 C 13.008367 20.419007 13.782949 18.114834 14.650391 15 L 20 15 A 1.0001 1.0001 0 1 0 20 13 L 15.1875 13 C 15.716881 10.979191 16.278508 8.7389756 16.923828 6 L 26 6 A 1.0001 1.0001 0 1 0 26 4 L 15.75 4 A 1.50015 1.50015 0 0 0 15.529297 3.9785156 z",
    ),
    stroke=(),
)

icons8_finger = VectorIcon(
    fill=(
        "M 17 3 C 16.0625 3 15.117188 3.3125 14.34375 3.96875 C 13.570313 4.625 13 5.675781 13 6.90625 L 13 28.4375 C 12.558594 28.597656 12.15625 28.644531 11.34375 29.34375 C 10.167969 30.359375 9 32.183594 9 34.90625 C 9 36.878906 9.785156 38.683594 10.09375 39.40625 C 10.09375 39.417969 10.09375 39.425781 10.09375 39.4375 L 12.90625 45.03125 C 12.910156 45.039063 12.902344 45.054688 12.90625 45.0625 C 14.382813 48.105469 17.539063 50 20.90625 50 L 30 50 C 34.945313 50 39 45.945313 39 41 L 39 25 C 39 24.179688 38.871094 23.050781 38.3125 22 C 37.753906 20.949219 36.597656 20 35 20 C 33.90625 20 33.09375 20.375 32.4375 20.875 C 32.328125 20.574219 32.273438 20.238281 32.125 19.96875 C 31.503906 18.847656 30.367188 18 29 18 C 27.882813 18 27.007813 18.40625 26.34375 18.96875 C 25.679688 17.871094 24.558594 17 23 17 C 22.21875 17 21.574219 17.246094 21 17.59375 L 21 7 C 21 5.734375 20.460938 4.675781 19.6875 4 C 18.914063 3.324219 17.9375 3 17 3 Z M 17 5 C 17.460938 5 18 5.175781 18.375 5.5 C 18.75 5.824219 19 6.265625 19 7 L 19 23 L 21 23 L 21 21 C 21 20.125 21.660156 19 23 19 C 24.339844 19 25 20.125 25 21 L 25 22 C 25.007813 22.546875 25.453125 22.984375 26 22.984375 C 26.546875 22.984375 26.992188 22.546875 27 22 C 27 21.464844 27.132813 20.933594 27.40625 20.59375 C 27.679688 20.253906 28.082031 20 29 20 C 29.632813 20 29.996094 20.257813 30.375 20.9375 C 30.753906 21.617188 31 22.71875 31 24 L 33 24 C 33 23.417969 33.105469 22.910156 33.34375 22.59375 C 33.582031 22.277344 33.964844 22 35 22 C 35.902344 22 36.246094 22.339844 36.5625 22.9375 C 36.878906 23.535156 37 24.417969 37 25 L 37 41 C 37 44.855469 33.855469 48 30 48 L 20.90625 48 C 18.285156 48 15.816406 46.5 14.6875 44.15625 L 11.90625 38.59375 C 11.902344 38.585938 11.910156 38.570313 11.90625 38.5625 C 11.613281 37.875 11 36.320313 11 34.90625 C 11 32.726563 11.832031 31.585938 12.65625 30.875 C 13.480469 30.164063 14.25 29.96875 14.25 29.96875 C 14.691406 29.855469 15 29.457031 15 29 L 15 6.90625 C 15 6.238281 15.25 5.820313 15.625 5.5 C 16 5.179688 16.539063 5 17 5 Z M 21.90625 29.96875 C 21.863281 29.976563 21.820313 29.988281 21.78125 30 C 21.316406 30.105469 20.988281 30.523438 21 31 L 21 40 C 20.996094 40.359375 21.183594 40.695313 21.496094 40.878906 C 21.808594 41.058594 22.191406 41.058594 22.503906 40.878906 C 22.816406 40.695313 23.003906 40.359375 23 40 L 23 31 C 23.011719 30.710938 22.894531 30.433594 22.6875 30.238281 C 22.476563 30.039063 22.191406 29.941406 21.90625 29.96875 Z M 26.90625 29.96875 C 26.863281 29.976563 26.820313 29.988281 26.78125 30 C 26.316406 30.105469 25.988281 30.523438 26 31 L 26 40 C 25.996094 40.359375 26.183594 40.695313 26.496094 40.878906 C 26.808594 41.058594 27.191406 41.058594 27.503906 40.878906 C 27.816406 40.695313 28.003906 40.359375 28 40 L 28 31 C 28.011719 30.710938 27.894531 30.433594 27.6875 30.238281 C 27.476563 30.039063 27.191406 29.941406 26.90625 29.96875 Z M 31.90625 29.96875 C 31.863281 29.976563 31.820313 29.988281 31.78125 30 C 31.316406 30.105469 30.988281 30.523438 31 31 L 31 40 C 30.996094 40.359375 31.183594 40.695313 31.496094 40.878906 C 31.808594 41.058594 32.191406 41.058594 32.503906 40.878906 C 32.816406 40.695313 33.003906 40.359375 33 40 L 33 31 C 33.011719 30.710938 32.894531 30.433594 32.6875 30.238281 C 32.476563 30.039063 32.191406 29.941406 31.90625 29.96875 Z",
    ),
    stroke=(),
)

icons8_place_marker = VectorIcon(
    fill=(
        "M 25 0.0625 C 17.316406 0.0625 11.0625 6.316406 11.0625 14 C 11.0625 20.367188 14.402344 27.667969 17.6875 33.46875 C 20.972656 39.269531 24.25 43.5625 24.25 43.5625 C 24.425781 43.800781 24.703125 43.945313 25 43.945313 C 25.296875 43.945313 25.574219 43.800781 25.75 43.5625 C 25.75 43.5625 29.03125 39.210938 32.3125 33.375 C 35.59375 27.539063 38.9375 20.234375 38.9375 14 C 38.9375 6.316406 32.683594 0.0625 25 0.0625 Z M 25 1.9375 C 31.679688 1.9375 37.0625 7.320313 37.0625 14 C 37.0625 19.554688 33.90625 26.75 30.6875 32.46875 C 28.058594 37.144531 25.871094 40.210938 25 41.40625 C 24.125 40.226563 21.9375 37.199219 19.3125 32.5625 C 16.097656 26.882813 12.9375 19.703125 12.9375 14 C 12.9375 7.320313 18.320313 1.9375 25 1.9375 Z M 25 8.03125 C 21.164063 8.03125 18.03125 11.164063 18.03125 15 C 18.03125 18.835938 21.164063 21.96875 25 21.96875 C 28.835938 21.96875 31.96875 18.835938 31.96875 15 C 31.96875 11.164063 28.835938 8.03125 25 8.03125 Z M 25 9.96875 C 27.792969 9.96875 30.03125 12.207031 30.03125 15 C 30.03125 17.792969 27.792969 20.03125 25 20.03125 C 22.207031 20.03125 19.96875 17.792969 19.96875 15 C 19.96875 12.207031 22.207031 9.96875 25 9.96875 Z M 15.15625 34.15625 C 11.15625 34.742188 7.773438 35.667969 5.28125 36.875 C 4.035156 37.476563 3.003906 38.148438 2.25 38.9375 C 1.496094 39.726563 1 40.707031 1 41.75 C 1 43.179688 1.914063 44.402344 3.21875 45.375 C 4.523438 46.347656 6.285156 47.132813 8.4375 47.8125 C 12.738281 49.171875 18.5625 50 25 50 C 31.4375 50 37.261719 49.171875 41.5625 47.8125 C 43.714844 47.132813 45.476563 46.347656 46.78125 45.375 C 48.085938 44.402344 49 43.179688 49 41.75 C 49 40.710938 48.503906 39.726563 47.75 38.9375 C 46.996094 38.148438 45.964844 37.476563 44.71875 36.875 C 42.226563 35.667969 38.84375 34.742188 34.84375 34.15625 C 34.292969 34.070313 33.773438 34.449219 33.6875 35 C 33.601563 35.550781 33.980469 36.070313 34.53125 36.15625 C 38.390625 36.722656 41.640625 37.621094 43.84375 38.6875 C 44.945313 39.222656 45.796875 39.804688 46.3125 40.34375 C 46.828125 40.882813 47 41.332031 47 41.75 C 47 42.324219 46.617188 42.984375 45.59375 43.75 C 44.570313 44.515625 42.980469 45.269531 40.96875 45.90625 C 36.945313 47.175781 31.265625 48 25 48 C 18.734375 48 13.054688 47.175781 9.03125 45.90625 C 7.019531 45.269531 5.429688 44.515625 4.40625 43.75 C 3.382813 42.984375 3 42.324219 3 41.75 C 3 41.332031 3.171875 40.882813 3.6875 40.34375 C 4.203125 39.804688 5.054688 39.222656 6.15625 38.6875 C 8.359375 37.621094 11.609375 36.722656 15.46875 36.15625 C 16.019531 36.070313 16.398438 35.550781 16.3125 35 C 16.226563 34.449219 15.707031 34.070313 15.15625 34.15625 Z",
    ),
    stroke=(),
)

icons8_cursor = VectorIcon(
    fill=(
        "M 14.78125 5 C 14.75 5.007813 14.71875 5.019531 14.6875 5.03125 C 14.644531 5.050781 14.601563 5.070313 14.5625 5.09375 C 14.550781 5.09375 14.542969 5.09375 14.53125 5.09375 C 14.511719 5.101563 14.488281 5.113281 14.46875 5.125 C 14.457031 5.136719 14.449219 5.144531 14.4375 5.15625 C 14.425781 5.167969 14.417969 5.175781 14.40625 5.1875 C 14.375 5.207031 14.34375 5.226563 14.3125 5.25 C 14.289063 5.269531 14.269531 5.289063 14.25 5.3125 C 14.238281 5.332031 14.226563 5.355469 14.21875 5.375 C 14.183594 5.414063 14.152344 5.457031 14.125 5.5 C 14.113281 5.511719 14.105469 5.519531 14.09375 5.53125 C 14.09375 5.542969 14.09375 5.550781 14.09375 5.5625 C 14.082031 5.582031 14.070313 5.605469 14.0625 5.625 C 14.050781 5.636719 14.042969 5.644531 14.03125 5.65625 C 14.03125 5.675781 14.03125 5.699219 14.03125 5.71875 C 14.019531 5.757813 14.007813 5.800781 14 5.84375 C 14 5.875 14 5.90625 14 5.9375 C 14 5.949219 14 5.957031 14 5.96875 C 14 5.980469 14 5.988281 14 6 C 13.996094 6.050781 13.996094 6.105469 14 6.15625 L 14 39 C 14.003906 39.398438 14.242188 39.757813 14.609375 39.914063 C 14.972656 40.070313 15.398438 39.992188 15.6875 39.71875 L 22.9375 32.90625 L 28.78125 46.40625 C 28.890625 46.652344 29.09375 46.847656 29.347656 46.941406 C 29.601563 47.035156 29.882813 47.023438 30.125 46.90625 L 34.5 44.90625 C 34.996094 44.679688 35.21875 44.09375 35 43.59375 L 28.90625 30.28125 L 39.09375 29.40625 C 39.496094 29.378906 39.84375 29.113281 39.976563 28.730469 C 40.105469 28.347656 39.992188 27.921875 39.6875 27.65625 L 15.84375 5.4375 C 15.796875 5.378906 15.746094 5.328125 15.6875 5.28125 C 15.648438 5.234375 15.609375 5.195313 15.5625 5.15625 C 15.550781 5.15625 15.542969 5.15625 15.53125 5.15625 C 15.511719 5.132813 15.492188 5.113281 15.46875 5.09375 C 15.457031 5.09375 15.449219 5.09375 15.4375 5.09375 C 15.386719 5.070313 15.335938 5.046875 15.28125 5.03125 C 15.269531 5.03125 15.261719 5.03125 15.25 5.03125 C 15.230469 5.019531 15.207031 5.007813 15.1875 5 C 15.175781 5 15.167969 5 15.15625 5 C 15.136719 5 15.113281 5 15.09375 5 C 15.082031 5 15.074219 5 15.0625 5 C 15.042969 5 15.019531 5 15 5 C 14.988281 5 14.980469 5 14.96875 5 C 14.9375 5 14.90625 5 14.875 5 C 14.84375 5 14.8125 5 14.78125 5 Z M 16 8.28125 L 36.6875 27.59375 L 27.3125 28.40625 C 26.992188 28.4375 26.707031 28.621094 26.546875 28.902344 C 26.382813 29.179688 26.367188 29.519531 26.5 29.8125 L 32.78125 43.5 L 30.21875 44.65625 L 24.21875 30.8125 C 24.089844 30.515625 23.828125 30.296875 23.511719 30.230469 C 23.195313 30.160156 22.863281 30.25 22.625 30.46875 L 16 36.6875 Z",
    ),
    stroke=(),
)

icons8_pencil_drawing = VectorIcon(
    fill=(
        "M 35.6875 2 C 35.460938 2.03125 35.25 2.144531 35.09375 2.3125 L 9.09375 28.28125 C 8.996094 28.390625 8.917969 28.515625 8.875 28.65625 L 2.0625 46.65625 C 1.929688 47.019531 2.019531 47.429688 2.296875 47.703125 C 2.570313 47.980469 2.980469 48.070313 3.34375 47.9375 L 21.34375 41.125 C 21.484375 41.082031 21.609375 41.003906 21.71875 40.90625 L 23 39.625 C 23.238281 39.523438 23.429688 39.332031 23.53125 39.09375 L 47.6875 14.90625 C 47.984375 14.664063 48.121094 14.277344 48.035156 13.902344 C 47.949219 13.53125 47.65625 13.238281 47.285156 13.152344 C 46.910156 13.066406 46.523438 13.203125 46.28125 13.5 L 22.34375 37.40625 C 21.625 37.074219 20.527344 36.703125 19.125 36.75 C 19.289063 36.304688 19.535156 36.039063 19.625 35.5 C 19.84375 34.199219 19.726563 32.601563 18.5625 31.4375 C 17.394531 30.269531 15.785156 30.160156 14.46875 30.40625 C 14.003906 30.492188 13.777344 30.730469 13.375 30.875 C 13.390625 30.734375 13.433594 30.710938 13.4375 30.5625 C 13.460938 29.695313 13.257813 28.621094 12.59375 27.65625 L 36.5 3.71875 C 36.796875 3.433594 36.886719 2.992188 36.726563 2.613281 C 36.570313 2.234375 36.191406 1.992188 35.78125 2 C 35.75 2 35.71875 2 35.6875 2 Z M 11.09375 29.15625 C 11.34375 29.613281 11.449219 30.058594 11.4375 30.5 C 11.421875 31.179688 11.203125 31.765625 11.0625 32.15625 C 10.910156 32.578125 11.054688 33.046875 11.417969 33.308594 C 11.78125 33.570313 12.273438 33.558594 12.625 33.28125 C 12.910156 33.058594 13.863281 32.550781 14.8125 32.375 C 15.761719 32.199219 16.605469 32.292969 17.15625 32.84375 C 17.710938 33.398438 17.816406 34.246094 17.65625 35.1875 C 17.496094 36.128906 17.003906 37.082031 16.8125 37.34375 C 16.535156 37.695313 16.523438 38.1875 16.785156 38.550781 C 17.046875 38.914063 17.515625 39.058594 17.9375 38.90625 C 19.207031 38.519531 20.195313 38.65625 20.875 38.875 L 20.40625 39.34375 L 9.375 43.53125 L 6.5 40.625 L 10.65625 29.59375 Z",
    ),
    stroke=(),
)

icons8_image = VectorIcon(
    fill=(
        "M 11.5 6 C 8.4802259 6 6 8.4802259 6 11.5 L 6 36.5 C 6 39.519774 8.4802259 42 11.5 42 L 36.5 42 C 39.519774 42 42 39.519774 42 36.5 L 42 11.5 C 42 8.4802259 39.519774 6 36.5 6 L 11.5 6 z M 11.5 9 L 36.5 9 C 37.898226 9 39 10.101774 39 11.5 L 39 31.955078 L 32.988281 26.138672 A 1.50015 1.50015 0 0 0 32.986328 26.136719 C 32.208234 25.385403 31.18685 25 30.173828 25 C 29.16122 25 28.13988 25.385387 27.361328 26.138672 L 25.3125 28.121094 L 19.132812 22.142578 C 18.35636 21.389748 17.336076 21 16.318359 21 C 15.299078 21 14.280986 21.392173 13.505859 22.140625 A 1.50015 1.50015 0 0 0 13.503906 22.142578 L 9 26.5 L 9 11.5 C 9 10.101774 10.101774 9 11.5 9 z M 30.5 13 C 29.125 13 27.903815 13.569633 27.128906 14.441406 C 26.353997 15.313179 26 16.416667 26 17.5 C 26 18.583333 26.353997 19.686821 27.128906 20.558594 C 27.903815 21.430367 29.125 22 30.5 22 C 31.875 22 33.096185 21.430367 33.871094 20.558594 C 34.646003 19.686821 35 18.583333 35 17.5 C 35 16.416667 34.646003 15.313179 33.871094 14.441406 C 33.096185 13.569633 31.875 13 30.5 13 z M 30.5 16 C 31.124999 16 31.403816 16.180367 31.628906 16.433594 C 31.853997 16.686821 32 17.083333 32 17.5 C 32 17.916667 31.853997 18.313179 31.628906 18.566406 C 31.403816 18.819633 31.124999 19 30.5 19 C 29.875001 19 29.596184 18.819633 29.371094 18.566406 C 29.146003 18.313179 29 17.916667 29 17.5 C 29 17.083333 29.146003 16.686821 29.371094 16.433594 C 29.596184 16.180367 29.875001 16 30.5 16 z M 16.318359 24 C 16.578643 24 16.835328 24.09366 17.044922 24.296875 A 1.50015 1.50015 0 0 0 17.046875 24.298828 L 23.154297 30.207031 L 14.064453 39 L 11.5 39 C 10.101774 39 9 37.898226 9 36.5 L 9 30.673828 L 15.589844 24.298828 C 15.802764 24.093234 16.059641 24 16.318359 24 z M 30.173828 28 C 30.438806 28 30.692485 28.09229 30.902344 28.294922 L 39 36.128906 L 39 36.5 C 39 37.898226 37.898226 39 36.5 39 L 18.380859 39 L 29.447266 28.294922 C 29.654714 28.094207 29.910436 28 30.173828 28 z",
    ),
    stroke=(),
)

icon_image3d = VectorIcon(
    stroke=(),
    fill=(
        "M11.41 79.61L248.43.68c2.83-.96 5.79-.87 8.42.05V.68l240.14 82.26c5.92 2 9.5 7.75 8.96 13.7.04.29.04.63.04.96v279.29h-.04c0 4.83-2.67 9.5-7.29 11.83L260.22 509.88c-2 1.2-4.37 1.91-6.87 1.91-2.67 0-5.12-.79-7.21-2.12L7.16 385.02c-4.49-2.38-7.12-6.96-7.12-11.75H0V92.77c0-6.71 4.96-12.25 11.41-13.16z"
        + "m292.94 159.41c11.86-5.76 23.7-11.52 35.54-17.21 11.8-5.68 23.58-11.37 35.35-17.02 13.86-6.66 25.21-9.99 34.03-10.03 8.89-.04 16.47 2.31 22.84 7.02 6.39 4.73 11.39 11.32 15.08 19.83 3.68 8.51 6.23 18.11 7.58 28.97 2.1 16.92 1.81 31.03-1.02 42.41-2.83 11.36-7.48 22.1-13.97 32.18-6.53 10.14-13.89 18.45-22.08 25-11.22 8.96-21.58 15.95-30.95 20.89-13.13 6.91-26.27 13.82-39.42 20.76-13.18 6.96-26.38 13.97-39.6 20.94-.88-28.67-1.71-57.47-2.26-86.36-.55-29.02-.87-58.16-1.12-87.38z"
        + "m49.37 15.43c.7 15.42 1.43 30.84 2.23 46.21.8 15.34 1.68 30.64 2.58 45.91 4.24-2.17 8.49-4.36 12.72-6.55 10.82-5.61 18.44-10.75 22.82-15.47 4.34-4.66 7.53-10.59 9.57-17.74 2.05-7.16 2.44-17.24 1.31-30.32-1.5-17.39-5.21-27.89-11.18-31.68-5.94-3.75-15.2-2.62-27.84 3.6-4.09 2.01-8.14 4.02-12.21 6.04z"
        + "m-245.06-5.21c-8.59-4.23-17.16-8.42-25.75-12.59-8.56-4.17-17.13-8.29-25.72-12.42 4.97-11.86 13.69-19.5 26.26-22.88 6.28-1.69 13.77-2.15 22.49-1.3 8.72.85 18.67 2.99 29.85 6.51 12.85 4.03 23.88 8.61 33.06 13.67 9.2 5.06 16.61 10.68 22.16 16.82 11.15 12.33 16.47 25.05 15.97 37.99-.29 7.51-2.9 13.51-7.79 17.88-4.88 4.36-12.11 7.04-21.67 8.07 7.58 4.51 13.34 8.62 17.28 12.34 6.43 6.07 11.35 12.67 14.76 19.87 3.42 7.23 4.98 14.89 4.66 22.93-.4 10.1-3.74 18.54-10.19 25.17-6.39 6.59-15.4 9.84-26.99 9.79-5.8-.03-12.46-1.03-19.98-3.07-7.51-2.03-15.92-5.05-25.19-9-18.02-7.67-32.17-15.4-42.42-23.14-10.24-7.72-18.55-16.09-24.97-25.25-6.37-9.09-11.12-19.15-14.19-30.24 9.19 2.58 18.43 5.17 27.63 7.71 9.21 2.54 18.46 5.16 27.68 7.71 1.75 9.9 4.78 17.47 9.18 22.83 4.36 5.31 10.05 9.47 17.12 12.35 7.34 3 13.6 3.28 18.72.79 5.1-2.49 7.79-7.62 8.11-15.26.32-7.75-1.72-14.65-6.26-20.76-4.5-6.04-10.85-10.6-18.9-13.63-4.29-1.61-10.27-2.96-17.85-4.01 1.45-10.43 2.86-20.93 4.32-31.49 2.96 1.43 5.3 2.47 7.02 3.08 7.08 2.54 13.11 2.71 18 .53 4.9-2.19 7.49-5.95 7.72-11.29.23-5.17-1.41-9.89-4.83-14.12-3.45-4.26-8.3-7.44-14.5-9.5-6.44-2.14-11.7-2.26-15.9-.32-4.12 1.9-7.09 6.67-8.89 14.23z"
        + "m131.4 227.4V209.51L26.57 112.72v252.55l213.49 111.37z"
        + "m239.31-360.76l-212.74 93.75v267.26l212.74-108.12V115.88z"
        + "m-226.9-88.67L50.56 94.48l202.87 92L456.3 97.06 252.47 27.21z"
    ),
)

icons8_image_in_frame = VectorIcon(
    fill=(
        "M 11.5 6 C 8.4802259 6 6 8.4802259 6 11.5 L 6 36.5 C 6 39.519774 8.4802259 42 11.5 42 L 36.5 42 C 39.519774 42 42 39.519774 42 36.5 L 42 11.5 C 42 8.4802259 39.519774 6 36.5 6 L 11.5 6 z M 11.5 9 L 36.5 9 C 37.898226 9 39 10.101774 39 11.5 L 39 31.955078 L 32.988281 26.138672 A 1.50015 1.50015 0 0 0 32.986328 26.136719 C 32.208234 25.385403 31.18685 25 30.173828 25 C 29.16122 25 28.13988 25.385387 27.361328 26.138672 L 25.3125 28.121094 L 19.132812 22.142578 C 18.35636 21.389748 17.336076 21 16.318359 21 C 15.299078 21 14.280986 21.392173 13.505859 22.140625 A 1.50015 1.50015 0 0 0 13.503906 22.142578 L 9 26.5 L 9 11.5 C 9 10.101774 10.101774 9 11.5 9 z M 30.5 13 C 29.125 13 27.903815 13.569633 27.128906 14.441406 C 26.353997 15.313179 26 16.416667 26 17.5 C 26 18.583333 26.353997 19.686821 27.128906 20.558594 C 27.903815 21.430367 29.125 22 30.5 22 C 31.875 22 33.096185 21.430367 33.871094 20.558594 C 34.646003 19.686821 35 18.583333 35 17.5 C 35 16.416667 34.646003 15.313179 33.871094 14.441406 C 33.096185 13.569633 31.875 13 30.5 13 z M 30.5 16 C 31.124999 16 31.403816 16.180367 31.628906 16.433594 C 31.853997 16.686821 32 17.083333 32 17.5 C 32 17.916667 31.853997 18.313179 31.628906 18.566406 C 31.403816 18.819633 31.124999 19 30.5 19 C 29.875001 19 29.596184 18.819633 29.371094 18.566406 C 29.146003 18.313179 29 17.916667 29 17.5 C 29 17.083333 29.146003 16.686821 29.371094 16.433594 C 29.596184 16.180367 29.875001 16 30.5 16 z M 16.318359 24 C 16.578643 24 16.835328 24.09366 17.044922 24.296875 A 1.50015 1.50015 0 0 0 17.046875 24.298828 L 23.154297 30.207031 L 14.064453 39 L 11.5 39 C 10.101774 39 9 37.898226 9 36.5 L 9 30.673828 L 15.589844 24.298828 C 15.802764 24.093234 16.059641 24 16.318359 24 z M 30.173828 28 C 30.438806 28 30.692485 28.09229 30.902344 28.294922 L 39 36.128906 L 39 36.5 C 39 37.898226 37.898226 39 36.5 39 L 18.380859 39 L 29.447266 28.294922 C 29.654714 28.094207 29.910436 28 30.173828 28 z",
    ),
    stroke="M -40 -40 h 90 v 90 h -90 v -90",
)

icons8_decompress = VectorIcon(
    fill=(
        "M 33 4 L 33 6 L 42.585938 6 L 27.292969 21.292969 L 28.707031 22.707031 L 44 7.4140625 L 44 17 L 46 17 L 46 4 L 33 4 z M 21.292969 27.292969 L 6 42.585938 L 6 33 L 4 33 L 4 46 L 17 46 L 17 44 L 7.4140625 44 L 22.707031 28.707031 L 21.292969 27.292969 z",
    ),
    stroke=(),
)

icons8_r_white = VectorIcon(
    fill=(
        "M 25 2 C 12.309295 2 2 12.309295 2 25 C 2 37.690705 12.309295 48 25 48 C 37.690705 48 48 37.690705 48 25 C 48 12.309295 37.690705 2 25 2 z M 25 4 C 36.609824 4 46 13.390176 46 25 C 46 36.609824 36.609824 46 25 46 C 13.390176 46 4 36.609824 4 25 C 4 13.390176 13.390176 4 25 4 z M 18.419922 16 L 18.419922 34 L 20.664062 34 L 20.666016 34 L 20.666016 26.876953 L 25.09375 26.876953 L 28.947266 34 L 31.580078 34 L 27.414062 26.527344 C 29.671062 25.816344 31.03125 23.870281 31.03125 21.363281 C 31.03125 18.120281 28.760969 16 25.292969 16 L 18.419922 16 z M 20.664062 17.994141 L 24.992188 17.994141 C 27.312187 17.994141 28.710938 19.2795 28.710938 21.4375 C 28.710938 23.6455 27.40175 24.880859 25.09375 24.880859 L 20.664062 24.880859 L 20.664062 17.994141 z",
    ),
    stroke=(),
)

icons8_light_off = VectorIcon(
    fill=(
        "M 25 9 C 17.28125 9 11 15.28125 11 23 C 11 27.890625 13.191406 31.175781 15.25 33.59375 C 16.28125 34.800781 17.277344 35.824219 17.96875 36.71875 C 18.660156 37.613281 19 38.328125 19 39 L 19 42.6875 C 18.941406 42.882813 18.941406 43.085938 19 43.28125 L 19 44 C 19 45.644531 20.355469 47 22 47 L 22.78125 47 C 23.332031 47.609375 24.117188 48 25 48 C 25.882813 48 26.667969 47.609375 27.21875 47 L 28 47 C 29.644531 47 31 45.644531 31 44 L 31 43.1875 C 31.027344 43.054688 31.027344 42.914063 31 42.78125 L 31 39 C 31 38.328125 31.339844 37.605469 32.03125 36.71875 C 32.722656 35.832031 33.71875 34.828125 34.75 33.625 C 36.808594 31.21875 39 27.933594 39 23 C 39 15.28125 32.71875 9 25 9 Z M 25 11 C 31.640625 11 37 16.359375 37 23 C 37 27.359375 35.191406 30.078125 33.25 32.34375 C 32.28125 33.476563 31.277344 34.464844 30.46875 35.5 C 29.875 36.261719 29.449219 37.09375 29.21875 38 L 20.78125 38 C 20.550781 37.09375 20.125 36.265625 19.53125 35.5 C 18.722656 34.457031 17.71875 33.453125 16.75 32.3125 C 14.808594 30.035156 13 27.3125 13 23 C 13 16.359375 18.359375 11 25 11 Z M 20.40625 17.46875 C 20.363281 17.476563 20.320313 17.488281 20.28125 17.5 C 19.90625 17.566406 19.605469 17.839844 19.5 18.203125 C 19.394531 18.570313 19.503906 18.960938 19.78125 19.21875 L 23.5625 23 L 19.78125 26.78125 C 19.382813 27.179688 19.382813 27.820313 19.78125 28.21875 C 20.179688 28.617188 20.820313 28.617188 21.21875 28.21875 L 25 24.4375 L 28.78125 28.21875 C 29.179688 28.617188 29.820313 28.617188 30.21875 28.21875 C 30.617188 27.820313 30.617188 27.179688 30.21875 26.78125 L 26.4375 23 L 30.21875 19.21875 C 30.542969 18.917969 30.628906 18.441406 30.433594 18.046875 C 30.242188 17.648438 29.808594 17.429688 29.375 17.5 C 29.152344 17.523438 28.941406 17.625 28.78125 17.78125 L 25 21.5625 L 21.21875 17.78125 C 21.011719 17.558594 20.710938 17.445313 20.40625 17.46875 Z M 21 40 L 29 40 L 29 42 L 24 42 C 23.96875 42 23.9375 42 23.90625 42 C 23.355469 42.027344 22.925781 42.496094 22.953125 43.046875 C 22.980469 43.597656 23.449219 44.027344 24 44 L 29 44 C 29 44.566406 28.566406 45 28 45 L 22 45 C 21.433594 45 21 44.566406 21 44 C 21.359375 44.003906 21.695313 43.816406 21.878906 43.503906 C 22.058594 43.191406 22.058594 42.808594 21.878906 42.496094 C 21.695313 42.183594 21.359375 41.996094 21 42 Z",
    ),
    stroke=(),
)

icons8_light_on = VectorIcon(
    fill=(
        "M 24.90625 0.96875 C 24.863281 0.976563 24.820313 0.988281 24.78125 1 C 24.316406 1.105469 23.988281 1.523438 24 2 L 24 6 C 23.996094 6.359375 24.183594 6.695313 24.496094 6.878906 C 24.808594 7.058594 25.191406 7.058594 25.503906 6.878906 C 25.816406 6.695313 26.003906 6.359375 26 6 L 26 2 C 26.011719 1.710938 25.894531 1.433594 25.6875 1.238281 C 25.476563 1.039063 25.191406 0.941406 24.90625 0.96875 Z M 10.03125 7.125 C 10 7.132813 9.96875 7.144531 9.9375 7.15625 C 9.578125 7.230469 9.289063 7.5 9.183594 7.851563 C 9.078125 8.203125 9.175781 8.585938 9.4375 8.84375 L 12.28125 11.6875 C 12.523438 11.984375 12.910156 12.121094 13.285156 12.035156 C 13.65625 11.949219 13.949219 11.65625 14.035156 11.285156 C 14.121094 10.910156 13.984375 10.523438 13.6875 10.28125 L 10.84375 7.4375 C 10.65625 7.238281 10.398438 7.128906 10.125 7.125 C 10.09375 7.125 10.0625 7.125 10.03125 7.125 Z M 39.75 7.125 C 39.707031 7.132813 39.664063 7.144531 39.625 7.15625 C 39.445313 7.203125 39.285156 7.300781 39.15625 7.4375 L 36.3125 10.28125 C 36.015625 10.523438 35.878906 10.910156 35.964844 11.285156 C 36.050781 11.65625 36.34375 11.949219 36.714844 12.035156 C 37.089844 12.121094 37.476563 11.984375 37.71875 11.6875 L 40.5625 8.84375 C 40.875 8.546875 40.964844 8.082031 40.78125 7.691406 C 40.59375 7.296875 40.179688 7.070313 39.75 7.125 Z M 25 9 C 17.28125 9 11 15.28125 11 23 C 11 27.890625 13.191406 31.175781 15.25 33.59375 C 16.28125 34.800781 17.277344 35.824219 17.96875 36.71875 C 18.660156 37.613281 19 38.328125 19 39 L 19 42.53125 C 18.867188 42.808594 18.867188 43.128906 19 43.40625 L 19 44 C 19 45.644531 20.355469 47 22 47 L 22.78125 47 C 23.332031 47.609375 24.117188 48 25 48 C 25.882813 48 26.667969 47.609375 27.21875 47 L 28 47 C 29.644531 47 31 45.644531 31 44 L 31 43.1875 C 31.027344 43.054688 31.027344 42.914063 31 42.78125 L 31 39 C 31 38.328125 31.339844 37.605469 32.03125 36.71875 C 32.722656 35.832031 33.71875 34.828125 34.75 33.625 C 36.808594 31.21875 39 27.933594 39 23 C 39 15.28125 32.71875 9 25 9 Z M 25 11 C 31.640625 11 37 16.359375 37 23 C 37 27.359375 35.191406 30.078125 33.25 32.34375 C 32.28125 33.476563 31.277344 34.464844 30.46875 35.5 C 29.875 36.261719 29.449219 37.09375 29.21875 38 L 20.78125 38 C 20.550781 37.09375 20.125 36.265625 19.53125 35.5 C 18.722656 34.457031 17.71875 33.453125 16.75 32.3125 C 14.808594 30.035156 13 27.3125 13 23 C 13 16.359375 18.359375 11 25 11 Z M 3.71875 22 C 3.167969 22.078125 2.78125 22.589844 2.859375 23.140625 C 2.9375 23.691406 3.449219 24.078125 4 24 L 8 24 C 8.359375 24.003906 8.695313 23.816406 8.878906 23.503906 C 9.058594 23.191406 9.058594 22.808594 8.878906 22.496094 C 8.695313 22.183594 8.359375 21.996094 8 22 L 4 22 C 3.96875 22 3.9375 22 3.90625 22 C 3.875 22 3.84375 22 3.8125 22 C 3.78125 22 3.75 22 3.71875 22 Z M 41.71875 22 C 41.167969 22.078125 40.78125 22.589844 40.859375 23.140625 C 40.9375 23.691406 41.449219 24.078125 42 24 L 46 24 C 46.359375 24.003906 46.695313 23.816406 46.878906 23.503906 C 47.058594 23.191406 47.058594 22.808594 46.878906 22.496094 C 46.695313 22.183594 46.359375 21.996094 46 22 L 42 22 C 41.96875 22 41.9375 22 41.90625 22 C 41.875 22 41.84375 22 41.8125 22 C 41.78125 22 41.75 22 41.71875 22 Z M 12.875 34 C 12.648438 34.03125 12.4375 34.144531 12.28125 34.3125 L 9.4375 37.15625 C 9.140625 37.398438 9.003906 37.785156 9.089844 38.160156 C 9.175781 38.53125 9.46875 38.824219 9.839844 38.910156 C 10.214844 38.996094 10.601563 38.859375 10.84375 38.5625 L 13.6875 35.71875 C 13.984375 35.433594 14.074219 34.992188 13.914063 34.613281 C 13.757813 34.234375 13.378906 33.992188 12.96875 34 C 12.9375 34 12.90625 34 12.875 34 Z M 36.8125 34 C 36.4375 34.066406 36.136719 34.339844 36.03125 34.703125 C 35.925781 35.070313 36.035156 35.460938 36.3125 35.71875 L 39.15625 38.5625 C 39.398438 38.859375 39.785156 38.996094 40.160156 38.910156 C 40.53125 38.824219 40.824219 38.53125 40.910156 38.160156 C 40.996094 37.785156 40.859375 37.398438 40.5625 37.15625 L 37.71875 34.3125 C 37.53125 34.113281 37.273438 34.003906 37 34 C 36.96875 34 36.9375 34 36.90625 34 C 36.875 34 36.84375 34 36.8125 34 Z M 21 40 L 29 40 L 29 42 L 24 42 C 23.96875 42 23.9375 42 23.90625 42 C 23.875 42 23.84375 42 23.8125 42 C 23.261719 42.050781 22.855469 42.542969 22.90625 43.09375 C 22.957031 43.644531 23.449219 44.050781 24 44 L 29 44 C 29 44.566406 28.566406 45 28 45 L 22 45 C 21.433594 45 21 44.566406 21 44 C 21.359375 44.003906 21.695313 43.816406 21.878906 43.503906 C 22.058594 43.191406 22.058594 42.808594 21.878906 42.496094 C 21.695313 42.183594 21.359375 41.996094 21 42 Z",
    ),
    stroke=(),
)

icons8_manager = VectorIcon(
    fill=(
        "M33.08 59.9c-.53 0-.97-.43-.97-.97V44.65c0-.53.43-.97.97-.97s.97.43.97.97v14.28C34.05 59.47 33.61 59.9 33.08 59.9zM22.44 21.42H43.72V24.590000000000003H22.44zM39.39 28.97L46.85 28.97 46.85 26.53 44.69 26.53 21.47 26.53 19.31 26.53 19.31 28.97 26.77 28.97zM19.31 17.04H46.849999999999994V19.49H19.31zM7.45 60.79v1.32c0 .49.4.89.89.89h19.83v-3.1H8.34C7.85 59.9 7.45 60.3 7.45 60.79zM22.44 11.94H43.72V15.11H22.44zM44.69 10h4.58c.53 0 .97-.43.97-.97V3.97C50.23 3.43 49.8 3 49.26 3h-2.52v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97s-.97-.43-.97-.97V3h-3.14v2.85c0 .53-.43.97-.97.97-.53 0-.97-.43-.97-.97V3H16.9c-.53 0-.97.43-.97.97v5.07c0 .53.43.97.97.97h4.58H44.69zM27.74 30.91H38.43V33.8H27.74zM57.67 59.9H37.84V63h19.83c.49 0 .88-.4.88-.89v-1.32C58.55 60.3 58.16 59.9 57.67 59.9zM27.74 39.12L33.08 43.41 38.42 39.12 38.42 35.73 27.74 35.73zM40.14 51.81c-.25 0-.5-.09-.68-.28-.38-.38-.38-.99 0-1.37l2.63-2.63c.38-.38.99-.38 1.37 0 .38.38.38.99 0 1.37l-2.63 2.63C40.63 51.72 40.39 51.81 40.14 51.81zM42.11 55.52c-.45 0-.86-.32-.95-.78-.1-.52.24-1.03.76-1.14l3.65-.71c.53-.1 1.03.24 1.14.76.1.52-.24 1.03-.76 1.14L42.3 55.5C42.24 55.51 42.17 55.52 42.11 55.52zM26.02 51.81c-.25 0-.5-.09-.68-.28l-2.63-2.63c-.38-.38-.38-.99 0-1.37.38-.38.99-.38 1.37 0l2.63 2.63c.38.38.38.99 0 1.37C26.52 51.72 26.27 51.81 26.02 51.81zM24.05 55.52c-.06 0-.12-.01-.19-.02l-3.65-.71c-.52-.1-.87-.61-.76-1.14.1-.52.6-.87 1.14-.76l3.65.71c.52.1.87.61.76 1.14C24.91 55.2 24.5 55.52 24.05 55.52z",
    ),
    stroke=(),
)

icons8_gas_industry = VectorIcon(
    fill=(
        "M 28.53125 0 C 28.433594 0.015625 28.339844 0.046875 28.25 0.09375 C 28.25 0.09375 9 9.503906 9 26.1875 C 9 31.46875 12.070313 35.007813 15.03125 37.09375 C 17.992188 39.179688 20.9375 39.96875 20.9375 39.96875 C 21.359375 40.097656 21.816406 39.933594 22.0625 39.566406 C 22.304688 39.199219 22.28125 38.714844 22 38.375 C 22 38.375 18 33.230469 18 26.3125 C 18 20.390625 21.492188 16.382813 23.71875 14.375 C 23.15625 18.378906 23.355469 21.554688 24.03125 23.53125 C 24.445313 24.742188 24.953125 25.613281 25.375 26.1875 C 25.796875 26.761719 26.15625 27.0625 26.15625 27.0625 C 26.4375 27.292969 26.824219 27.351563 27.164063 27.214844 C 27.5 27.078125 27.738281 26.769531 27.78125 26.40625 C 27.78125 26.40625 27.882813 25.375 28.1875 24.125 C 28.269531 23.789063 28.476563 23.535156 28.59375 23.1875 C 28.929688 24.40625 29.328125 25.523438 29.71875 26.53125 C 30.417969 28.324219 31 29.902344 31 31.90625 C 31 33.214844 30.382813 34.882813 29.71875 36.1875 C 29.054688 37.492188 28.375 38.40625 28.375 38.40625 C 28.109375 38.761719 28.113281 39.25 28.378906 39.605469 C 28.648438 39.957031 29.117188 40.09375 29.53125 39.9375 C 35.179688 37.980469 39 32.214844 39 26.1875 C 39 20.617188 35.914063 16.425781 33.3125 12.59375 C 30.710938 8.761719 28.613281 5.421875 29.65625 1.25 C 29.738281 0.941406 29.664063 0.609375 29.460938 0.363281 C 29.253906 0.113281 28.945313 -0.0195313 28.625 0 C 28.59375 0 28.5625 0 28.53125 0 Z M 27.5625 2.84375 C 27.363281 6.921875 29.410156 10.410156 31.65625 13.71875 C 34.28125 17.585938 37 21.359375 37 26.1875 C 37 30.214844 34.933594 34.144531 31.78125 36.46875 C 32.417969 35.121094 33 33.554688 33 31.90625 C 33 29.507813 32.296875 27.617188 31.59375 25.8125 C 30.890625 24.007813 30.1875 22.246094 30 19.90625 C 29.960938 19.507813 29.691406 19.171875 29.308594 19.046875 C 28.929688 18.925781 28.511719 19.042969 28.25 19.34375 C 27.152344 20.5625 26.625 22.207031 26.28125 23.59375 C 26.15625 23.320313 26.023438 23.222656 25.90625 22.875 C 25.210938 20.847656 24.753906 17.472656 25.96875 12.21875 C 26.050781 11.828125 25.894531 11.425781 25.570313 11.191406 C 25.242188 10.960938 24.808594 10.949219 24.46875 11.15625 C 24.46875 11.15625 16 16.53125 16 26.3125 C 16 31.238281 17.542969 34.609375 18.84375 36.90625 C 18.007813 36.511719 17.152344 36.152344 16.1875 35.46875 C 13.546875 33.605469 11 30.707031 11 26.1875 C 11 13.195313 23.796875 5.007813 27.5625 2.84375 Z M 10.40625 42 C 9.105469 42 8 43.105469 8 44.40625 L 8 49 C 8 49.550781 8.449219 50 9 50 L 41 50 C 41.550781 50 42 49.550781 42 49 L 42 44.40625 C 42 43.105469 40.894531 42 39.59375 42 L 37 42 C 36.449219 42 36 42.449219 36 43 L 36 45 L 35 45 L 35 43 C 35 42.449219 34.550781 42 34 42 L 30 42 C 29.449219 42 29 42.449219 29 43 L 29 45 L 28 45 L 28 43 C 28 42.449219 27.550781 42 27 42 L 23 42 C 22.449219 42 22 42.449219 22 43 L 22 45 L 21 45 L 21 43 C 21 42.449219 20.550781 42 20 42 L 16 42 C 15.449219 42 15 42.449219 15 43 L 15 45 L 14 45 L 14 43 C 14 42.449219 13.550781 42 13 42 Z M 10.40625 44 L 12 44 L 12 46 C 12 46.550781 12.449219 47 13 47 L 16 47 C 16.550781 47 17 46.550781 17 46 L 17 44 L 19 44 L 19 46 C 19 46.550781 19.449219 47 20 47 L 23 47 C 23.550781 47 24 46.550781 24 46 L 24 44 L 26 44 L 26 46 C 26 46.550781 26.449219 47 27 47 L 30 47 C 30.550781 47 31 46.550781 31 46 L 31 44 L 33 44 L 33 46 C 33 46.550781 33.449219 47 34 47 L 37 47 C 37.550781 47 38 46.550781 38 46 L 38 44 L 39.59375 44 C 39.894531 44 40 44.105469 40 44.40625 L 40 48 L 10 48 L 10 44.40625 C 10 44.105469 10.105469 44 10.40625 44 Z",
    ),
    stroke=(),
)

icons8_laser_beam = VectorIcon(
    fill=(
        "M 24.90625 -0.03125 C 24.863281 -0.0234375 24.820313 -0.0117188 24.78125 0 C 24.316406 0.105469 23.988281 0.523438 24 1 L 24 27.9375 C 24 28.023438 24.011719 28.105469 24.03125 28.1875 C 22.859375 28.59375 22 29.6875 22 31 C 22 32.65625 23.34375 34 25 34 C 26.65625 34 28 32.65625 28 31 C 28 29.6875 27.140625 28.59375 25.96875 28.1875 C 25.988281 28.105469 26 28.023438 26 27.9375 L 26 1 C 26.011719 0.710938 25.894531 0.433594 25.6875 0.238281 C 25.476563 0.0390625 25.191406 -0.0585938 24.90625 -0.03125 Z M 35.125 12.15625 C 34.832031 12.210938 34.582031 12.394531 34.4375 12.65625 L 27.125 25.3125 C 26.898438 25.621094 26.867188 26.03125 27.042969 26.371094 C 27.222656 26.710938 27.578125 26.917969 27.960938 26.90625 C 28.347656 26.894531 28.6875 26.664063 28.84375 26.3125 L 36.15625 13.65625 C 36.34375 13.335938 36.335938 12.9375 36.140625 12.625 C 35.941406 12.308594 35.589844 12.128906 35.21875 12.15625 C 35.1875 12.15625 35.15625 12.15625 35.125 12.15625 Z M 17.78125 17.71875 C 17.75 17.726563 17.71875 17.738281 17.6875 17.75 C 17.375 17.824219 17.113281 18.042969 16.988281 18.339844 C 16.867188 18.636719 16.894531 18.976563 17.0625 19.25 L 21.125 26.3125 C 21.402344 26.796875 22.015625 26.964844 22.5 26.6875 C 22.984375 26.410156 23.152344 25.796875 22.875 25.3125 L 18.78125 18.25 C 18.605469 17.914063 18.253906 17.710938 17.875 17.71875 C 17.84375 17.71875 17.8125 17.71875 17.78125 17.71875 Z M 7 19.6875 C 6.566406 19.742188 6.222656 20.070313 6.140625 20.5 C 6.0625 20.929688 6.273438 21.359375 6.65625 21.5625 L 19.3125 28.875 C 19.796875 29.152344 20.410156 28.984375 20.6875 28.5 C 20.964844 28.015625 20.796875 27.402344 20.3125 27.125 L 7.65625 19.84375 C 7.488281 19.738281 7.292969 19.683594 7.09375 19.6875 C 7.0625 19.6875 7.03125 19.6875 7 19.6875 Z M 37.1875 22.90625 C 37.03125 22.921875 36.882813 22.976563 36.75 23.0625 L 29.6875 27.125 C 29.203125 27.402344 29.035156 28.015625 29.3125 28.5 C 29.589844 28.984375 30.203125 29.152344 30.6875 28.875 L 37.75 24.78125 C 38.164063 24.554688 38.367188 24.070313 38.230469 23.617188 C 38.09375 23.164063 37.660156 22.867188 37.1875 22.90625 Z M 0.71875 30 C 0.167969 30.078125 -0.21875 30.589844 -0.140625 31.140625 C -0.0625 31.691406 0.449219 32.078125 1 32 L 19 32 C 19.359375 32.003906 19.695313 31.816406 19.878906 31.503906 C 20.058594 31.191406 20.058594 30.808594 19.878906 30.496094 C 19.695313 30.183594 19.359375 29.996094 19 30 L 1 30 C 0.96875 30 0.9375 30 0.90625 30 C 0.875 30 0.84375 30 0.8125 30 C 0.78125 30 0.75 30 0.71875 30 Z M 30.71875 30 C 30.167969 30.078125 29.78125 30.589844 29.859375 31.140625 C 29.9375 31.691406 30.449219 32.078125 31 32 L 49 32 C 49.359375 32.003906 49.695313 31.816406 49.878906 31.503906 C 50.058594 31.191406 50.058594 30.808594 49.878906 30.496094 C 49.695313 30.183594 49.359375 29.996094 49 30 L 31 30 C 30.96875 30 30.9375 30 30.90625 30 C 30.875 30 30.84375 30 30.8125 30 C 30.78125 30 30.75 30 30.71875 30 Z M 19.75 32.96875 C 19.71875 32.976563 19.6875 32.988281 19.65625 33 C 19.535156 33.019531 19.417969 33.0625 19.3125 33.125 L 12.25 37.21875 C 11.898438 37.375 11.667969 37.714844 11.65625 38.101563 C 11.644531 38.484375 11.851563 38.839844 12.191406 39.019531 C 12.53125 39.195313 12.941406 39.164063 13.25 38.9375 L 20.3125 34.875 C 20.78125 34.675781 21.027344 34.160156 20.882813 33.671875 C 20.738281 33.183594 20.25 32.878906 19.75 32.96875 Z M 30.03125 33 C 29.597656 33.054688 29.253906 33.382813 29.171875 33.8125 C 29.09375 34.242188 29.304688 34.671875 29.6875 34.875 L 42.34375 42.15625 C 42.652344 42.382813 43.0625 42.414063 43.402344 42.238281 C 43.742188 42.058594 43.949219 41.703125 43.9375 41.320313 C 43.925781 40.933594 43.695313 40.59375 43.34375 40.4375 L 30.6875 33.125 C 30.488281 33.007813 30.257813 32.964844 30.03125 33 Z M 21.9375 35.15625 C 21.894531 35.164063 21.851563 35.175781 21.8125 35.1875 C 21.519531 35.242188 21.269531 35.425781 21.125 35.6875 L 13.84375 48.34375 C 13.617188 48.652344 13.585938 49.0625 13.761719 49.402344 C 13.941406 49.742188 14.296875 49.949219 14.679688 49.9375 C 15.066406 49.925781 15.40625 49.695313 15.5625 49.34375 L 22.875 36.6875 C 23.078125 36.367188 23.082031 35.957031 22.882813 35.628906 C 22.683594 35.304688 22.316406 35.121094 21.9375 35.15625 Z M 27.84375 35.1875 C 27.511719 35.234375 27.226563 35.445313 27.082031 35.746094 C 26.9375 36.046875 26.953125 36.398438 27.125 36.6875 L 31.21875 43.75 C 31.375 44.101563 31.714844 44.332031 32.101563 44.34375 C 32.484375 44.355469 32.839844 44.148438 33.019531 43.808594 C 33.195313 43.46875 33.164063 43.058594 32.9375 42.75 L 28.875 35.6875 C 28.671875 35.320313 28.257813 35.121094 27.84375 35.1875 Z M 24.90625 35.96875 C 24.863281 35.976563 24.820313 35.988281 24.78125 36 C 24.316406 36.105469 23.988281 36.523438 24 37 L 24 45.9375 C 23.996094 46.296875 24.183594 46.632813 24.496094 46.816406 C 24.808594 46.996094 25.191406 46.996094 25.503906 46.816406 C 25.816406 46.632813 26.003906 46.296875 26 45.9375 L 26 37 C 26.011719 36.710938 25.894531 36.433594 25.6875 36.238281 C 25.476563 36.039063 25.191406 35.941406 24.90625 35.96875 Z",
    ),
    stroke=(),
)

icons8_detective = VectorIcon(
    fill=(
        "M 21 3 C 11.621094 3 4 10.621094 4 20 C 4 29.378906 11.621094 37 21 37 C 24.710938 37 28.140625 35.804688 30.9375 33.78125 L 44.09375 46.90625 L 46.90625 44.09375 L 33.90625 31.0625 C 36.460938 28.085938 38 24.222656 38 20 C 38 10.621094 30.378906 3 21 3 Z M 21 5 C 28.070313 5 33.96875 9.867188 35.5625 16.4375 C 31.863281 13.777344 26.761719 11.125 21 11.125 C 15.238281 11.125 10.136719 13.808594 6.4375 16.46875 C 8.023438 9.882813 13.921875 5 21 5 Z M 21 12.875 C 23.261719 12.875 25.460938 13.332031 27.5 14.0625 C 28.863281 15.597656 29.6875 17.59375 29.6875 19.8125 C 29.6875 24.628906 25.816406 28.53125 21 28.53125 C 16.183594 28.53125 12.3125 24.628906 12.3125 19.8125 C 12.3125 17.613281 13.101563 15.621094 14.4375 14.09375 C 16.503906 13.347656 18.707031 12.875 21 12.875 Z M 11.5625 15.34375 C 10.914063 16.695313 10.5625 18.210938 10.5625 19.8125 C 10.5625 25.566406 15.246094 30.25 21 30.25 C 26.753906 30.25 31.4375 25.566406 31.4375 19.8125 C 31.4375 18.226563 31.078125 16.722656 30.4375 15.375 C 32.460938 16.402344 34.28125 17.609375 35.78125 18.78125 C 35.839844 18.820313 35.902344 18.851563 35.96875 18.875 C 35.996094 19.25 36 19.621094 36 20 C 36 28.296875 29.296875 35 21 35 C 12.703125 35 6 28.296875 6 20 C 6 19.542969 6.023438 19.101563 6.0625 18.65625 C 6.296875 18.660156 6.519531 18.570313 6.6875 18.40625 C 8.089844 17.34375 9.742188 16.265625 11.5625 15.34375 Z M 21 15.46875 C 18.597656 15.46875 16.65625 17.410156 16.65625 19.8125 C 16.65625 22.214844 18.597656 24.1875 21 24.1875 C 23.402344 24.1875 25.34375 22.214844 25.34375 19.8125 C 25.34375 17.410156 23.402344 15.46875 21 15.46875 Z",
    ),
    stroke=(),
)

icons8_flip_vertical = VectorIcon(
    fill=(
        "M 43.0625 4 C 42.894531 3.992188 42.71875 4.019531 42.5625 4.09375 L 5.5625 22.09375 C 5.144531 22.296875 4.925781 22.765625 5.03125 23.21875 C 5.136719 23.671875 5.535156 24 6 24 L 43 24 C 43.554688 24 44 23.550781 44 23 L 44 5 C 44 4.65625 43.824219 4.339844 43.53125 4.15625 C 43.386719 4.066406 43.230469 4.007813 43.0625 4 Z M 5.8125 26 C 5.371094 26.066406 5.027344 26.417969 4.96875 26.859375 C 4.910156 27.300781 5.152344 27.726563 5.5625 27.90625 L 42.5625 45.90625 C 42.875 46.058594 43.242188 46.039063 43.535156 45.851563 C 43.824219 45.667969 44.003906 45.347656 44 45 L 44 27 C 44 26.449219 43.550781 26 43 26 L 6 26 C 5.96875 26 5.9375 26 5.90625 26 C 5.875 26 5.84375 26 5.8125 26 Z M 10.34375 28 L 42 28 L 42 43.40625 Z",
    ),
    stroke=(),
)

icons8_flip_horizontal = VectorIcon(
    fill=(
        "M 22.875 5 C 22.535156 5.042969 22.242188 5.253906 22.09375 5.5625 L 4.09375 42.5625 C 3.941406 42.875 3.960938 43.242188 4.148438 43.535156 C 4.332031 43.824219 4.652344 44.003906 5 44 L 23 44 C 23.550781 44 24 43.550781 24 43 L 24 6 C 24.003906 5.710938 23.878906 5.4375 23.664063 5.246094 C 23.449219 5.054688 23.160156 4.964844 22.875 5 Z M 27.125 5 C 27.015625 4.988281 26.894531 5.003906 26.78125 5.03125 C 26.328125 5.136719 26 5.535156 26 6 L 26 43 C 26 43.554688 26.445313 44 27 44 L 45 44 C 45.34375 44 45.660156 43.824219 45.84375 43.53125 C 46.027344 43.238281 46.054688 42.871094 45.90625 42.5625 L 27.90625 5.5625 C 27.753906 5.25 27.457031 5.039063 27.125 5 Z M 22 10.34375 L 22 42 L 6.59375 42 Z",
    ),
    stroke=(),
)

icons8_flash_on = VectorIcon(
    fill=(
        "M 31.1875 3.25 C 30.9375 3.292969 30.714844 3.425781 30.5625 3.625 L 11.5 27.375 C 11.257813 27.675781 11.210938 28.085938 11.378906 28.433594 C 11.546875 28.78125 11.898438 29 12.28125 29 L 22.75 29 L 17.75 45.4375 C 17.566406 45.910156 17.765625 46.441406 18.210938 46.679688 C 18.65625 46.917969 19.207031 46.789063 19.5 46.375 L 38.5 22.625 C 38.742188 22.324219 38.789063 21.914063 38.621094 21.566406 C 38.453125 21.21875 38.101563 21 37.71875 21 L 27.625 21 L 32.28125 4.53125 C 32.371094 4.222656 32.308594 3.886719 32.109375 3.632813 C 31.910156 3.378906 31.601563 3.238281 31.28125 3.25 C 31.25 3.25 31.21875 3.25 31.1875 3.25 Z M 29.03125 8.71875 L 25.3125 21.71875 C 25.222656 22.023438 25.285156 22.351563 25.472656 22.601563 C 25.664063 22.855469 25.964844 23.003906 26.28125 23 L 35.625 23 L 21.1875 41.09375 L 25.09375 28.28125 C 25.183594 27.976563 25.121094 27.648438 24.933594 27.398438 C 24.742188 27.144531 24.441406 26.996094 24.125 27 L 14.375 27 Z",
    ),
    stroke=(),
)

icons8_flash_off = VectorIcon(
    fill=(
        "M 11.919922 1.2539062 C 11.671859 1.280625 11.445125 1.4300625 11.328125 1.6640625 L 9.328125 5.6640625 C 9.143125 6.0340625 9.2930625 6.486875 9.6640625 6.671875 C 10.034062 6.856875 10.486875 6.7069375 10.671875 6.3359375 L 11.25 5.1777344 L 11.25 8 C 11.25 8.414 11.586 8.75 12 8.75 C 12.414 8.75 12.75 8.414 12.75 8 L 12.75 2 C 12.75 1.652 12.510875 1.3495312 12.171875 1.2695312 C 12.087375 1.2495312 12.002609 1.245 11.919922 1.2539062 z M 5 4.25 C 4.808 4.25 4.6167031 4.3242031 4.4707031 4.4707031 C 4.1777031 4.7627031 4.1777031 5.2372969 4.4707031 5.5292969 L 7.7539062 8.8144531 L 5.328125 13.664062 C 5.212125 13.896062 5.2243281 14.173531 5.3613281 14.394531 C 5.4983281 14.615531 5.74 14.75 6 14.75 L 11.25 14.75 L 11.25 22 C 11.25 22.348 11.489125 22.650469 11.828125 22.730469 C 12.166125 22.810469 12.515875 22.647938 12.671875 22.335938 L 15.539062 16.599609 L 18.480469 19.542969 C 18.773469 19.834969 19.249969 19.834969 19.542969 19.542969 C 19.834969 19.249969 19.834969 18.773469 19.542969 18.480469 L 15.996094 14.933594 C 15.92516 14.80669 15.827485 14.692851 15.6875 14.623047 C 15.686169 14.622381 15.684927 14.621751 15.683594 14.621094 L 5.5292969 4.4707031 C 5.3832969 4.3242031 5.192 4.25 5 4.25 z M 14 9.25 C 13.586 9.25 13.25 9.586 13.25 10 C 13.25 10.414 13.586 10.75 14 10.75 L 16.785156 10.75 L 15.828125 12.664062 C 15.643125 13.034062 15.793063 13.486875 16.164062 13.671875 C 16.534063 13.856875 16.986875 13.706938 17.171875 13.335938 L 18.671875 10.335938 C 18.787875 10.103938 18.775672 9.8264687 18.638672 9.6054688 C 18.501672 9.3844687 18.26 9.25 18 9.25 L 14 9.25 z M 8.8730469 9.9316406 L 12.236328 13.296875 C 12.160904 13.271364 12.084002 13.25 12 13.25 L 7.2148438 13.25 L 8.8730469 9.9316406 z M 12.703125 13.763672 L 14.419922 15.482422 L 12.75 18.822266 L 12.75 14 C 12.75 13.915998 12.728636 13.839096 12.703125 13.763672 z",
    ),
    stroke=(),
)

icons8_arrange = VectorIcon(
    fill=(
        "M 8.5 4 C 7.0833337 4 5.8935589 4.5672556 5.1269531 5.4296875 C 4.3603473 6.2921194 4 7.4027779 4 8.5 C 4 9.5972221 4.3603473 10.707881 5.1269531 11.570312 C 5.8935589 12.432745 7.0833337 13 8.5 13 C 9.9166663 13 11.106441 12.432744 11.873047 11.570312 C 12.639653 10.707882 13 9.5972221 13 8.5 C 13 7.4027779 12.639653 6.2921194 11.873047 5.4296875 C 11.106441 4.5672556 9.9166663 4 8.5 4 z M 19.5 4 C 18.083334 4 16.893559 4.5672556 16.126953 5.4296875 C 15.360347 6.2921194 15 7.4027779 15 8.5 C 15 9.5972221 15.360347 10.707881 16.126953 11.570312 C 16.893559 12.432745 18.083334 13 19.5 13 C 20.916666 13 22.106441 12.432744 22.873047 11.570312 C 23.639653 10.707882 24 9.5972221 24 8.5 C 24 7.4027779 23.639653 6.2921194 22.873047 5.4296875 C 22.106441 4.5672556 20.916666 4 19.5 4 z M 30.5 4 C 29.083334 4 27.893559 4.5672556 27.126953 5.4296875 C 26.360347 6.2921194 26 7.4027779 26 8.5 C 26 9.5972221 26.360347 10.707881 27.126953 11.570312 C 27.893559 12.432745 29.083334 13 30.5 13 C 31.916666 13 33.106441 12.432744 33.873047 11.570312 C 34.639653 10.707882 35 9.5972221 35 8.5 C 35 7.4027779 34.639653 6.2921194 33.873047 5.4296875 C 33.106441 4.5672556 31.916666 4 30.5 4 z M 41.5 4 C 40.083334 4 38.893559 4.5672556 38.126953 5.4296875 C 37.360347 6.2921194 37 7.4027779 37 8.5 C 37 9.5972221 37.360347 10.707881 38.126953 11.570312 C 38.893559 12.432745 40.083334 13 41.5 13 C 42.916666 13 44.106441 12.432744 44.873047 11.570312 C 45.639653 10.707882 46 9.5972221 46 8.5 C 46 7.4027779 45.639653 6.2921194 44.873047 5.4296875 C 44.106441 4.5672556 42.916666 4 41.5 4 z M 8.5 6 C 9.4166661 6 9.9768929 6.3077444 10.376953 6.7578125 C 10.777013 7.2078806 11 7.8472221 11 8.5 C 11 9.1527779 10.777013 9.7921189 10.376953 10.242188 C 9.9768929 10.692255 9.4166661 11 8.5 11 C 7.5833339 11 7.0231072 10.692256 6.6230469 10.242188 C 6.2229865 9.7921189 6 9.1527779 6 8.5 C 6 7.8472221 6.2229865 7.2078806 6.6230469 6.7578125 C 7.0231072 6.3077444 7.5833339 6 8.5 6 z M 19.5 6 C 20.416666 6 20.976893 6.3077444 21.376953 6.7578125 C 21.777013 7.2078806 22 7.8472221 22 8.5 C 22 9.1527779 21.777013 9.7921189 21.376953 10.242188 C 20.976893 10.692255 20.416666 11 19.5 11 C 18.583334 11 18.023107 10.692256 17.623047 10.242188 C 17.222987 9.7921189 17 9.1527779 17 8.5 C 17 7.8472221 17.222987 7.2078806 17.623047 6.7578125 C 18.023107 6.3077444 18.583334 6 19.5 6 z M 30.5 6 C 31.416666 6 31.976893 6.3077444 32.376953 6.7578125 C 32.777013 7.2078806 33 7.8472221 33 8.5 C 33 9.1527779 32.777013 9.7921189 32.376953 10.242188 C 31.976893 10.692255 31.416666 11 30.5 11 C 29.583334 11 29.023107 10.692256 28.623047 10.242188 C 28.222987 9.7921189 28 9.1527779 28 8.5 C 28 7.8472221 28.222987 7.2078806 28.623047 6.7578125 C 29.023107 6.3077444 29.583334 6 30.5 6 z M 41.5 6 C 42.416666 6 42.976893 6.3077444 43.376953 6.7578125 C 43.777013 7.2078806 44 7.8472221 44 8.5 C 44 9.1527779 43.777013 9.7921189 43.376953 10.242188 C 42.976893 10.692255 42.416666 11 41.5 11 C 40.583334 11 40.023107 10.692256 39.623047 10.242188 C 39.222987 9.7921189 39 9.1527779 39 8.5 C 39 7.8472221 39.222987 7.2078806 39.623047 6.7578125 C 40.023107 6.3077444 40.583334 6 41.5 6 z M 8.5 15 C 7.0833337 15 5.8935589 15.567256 5.1269531 16.429688 C 4.3603473 17.292119 4 18.402778 4 19.5 C 4 20.597222 4.3603473 21.707881 5.1269531 22.570312 C 5.8935589 23.432744 7.0833337 24 8.5 24 C 9.9166663 24 11.106441 23.432744 11.873047 22.570312 C 12.639653 21.707881 13 20.597222 13 19.5 C 13 18.402778 12.639653 17.292119 11.873047 16.429688 C 11.106441 15.567256 9.9166663 15 8.5 15 z M 19.5 15 C 18.083334 15 16.893559 15.567256 16.126953 16.429688 C 15.360347 17.292119 15 18.402778 15 19.5 C 15 20.597222 15.360347 21.707881 16.126953 22.570312 C 16.893559 23.432744 18.083334 24 19.5 24 C 20.916666 24 22.106441 23.432744 22.873047 22.570312 C 23.639653 21.707881 24 20.597222 24 19.5 C 24 18.402778 23.639653 17.292119 22.873047 16.429688 C 22.106441 15.567256 20.916666 15 19.5 15 z M 30.5 15 C 29.083334 15 27.893559 15.567256 27.126953 16.429688 C 26.360347 17.292119 26 18.402778 26 19.5 C 26 20.597222 26.360347 21.707881 27.126953 22.570312 C 27.893559 23.432744 29.083334 24 30.5 24 C 31.916666 24 33.106441 23.432744 33.873047 22.570312 C 34.639653 21.707881 35 20.597222 35 19.5 C 35 18.402778 34.639653 17.292119 33.873047 16.429688 C 33.106441 15.567256 31.916666 15 30.5 15 z M 41.5 15 C 40.083334 15 38.893559 15.567256 38.126953 16.429688 C 37.360347 17.292119 37 18.402778 37 19.5 C 37 20.597222 37.360347 21.707881 38.126953 22.570312 C 38.893559 23.432744 40.083334 24 41.5 24 C 42.916666 24 44.106441 23.432744 44.873047 22.570312 C 45.639653 21.707881 46 20.597222 46 19.5 C 46 18.402778 45.639653 17.292119 44.873047 16.429688 C 44.106441 15.567256 42.916666 15 41.5 15 z M 8.5 17 C 9.4166661 17 9.9768929 17.307744 10.376953 17.757812 C 10.777013 18.207881 11 18.847222 11 19.5 C 11 20.152778 10.777013 20.792119 10.376953 21.242188 C 9.9768929 21.692256 9.4166661 22 8.5 22 C 7.5833339 22 7.0231072 21.692256 6.6230469 21.242188 C 6.2229865 20.792119 6 20.152778 6 19.5 C 6 18.847222 6.2229865 18.207881 6.6230469 17.757812 C 7.0231072 17.307744 7.5833339 17 8.5 17 z M 19.5 17 C 20.416666 17 20.976893 17.307744 21.376953 17.757812 C 21.777013 18.207881 22 18.847222 22 19.5 C 22 20.152778 21.777013 20.792119 21.376953 21.242188 C 20.976893 21.692256 20.416666 22 19.5 22 C 18.583334 22 18.023107 21.692256 17.623047 21.242188 C 17.222987 20.792119 17 20.152778 17 19.5 C 17 18.847222 17.222987 18.207881 17.623047 17.757812 C 18.023107 17.307744 18.583334 17 19.5 17 z M 30.5 17 C 31.416666 17 31.976893 17.307744 32.376953 17.757812 C 32.777013 18.207881 33 18.847222 33 19.5 C 33 20.152778 32.777013 20.792119 32.376953 21.242188 C 31.976893 21.692256 31.416666 22 30.5 22 C 29.583334 22 29.023107 21.692256 28.623047 21.242188 C 28.222987 20.792119 28 20.152778 28 19.5 C 28 18.847222 28.222987 18.207881 28.623047 17.757812 C 29.023107 17.307744 29.583334 17 30.5 17 z M 41.5 17 C 42.416666 17 42.976893 17.307744 43.376953 17.757812 C 43.777013 18.207881 44 18.847222 44 19.5 C 44 20.152778 43.777013 20.792119 43.376953 21.242188 C 42.976893 21.692256 42.416666 22 41.5 22 C 40.583334 22 40.023107 21.692256 39.623047 21.242188 C 39.222987 20.792119 39 20.152778 39 19.5 C 39 18.847222 39.222987 18.207881 39.623047 17.757812 C 40.023107 17.307744 40.583334 17 41.5 17 z M 8.5 26 C 7.0833337 26 5.8935589 26.567256 5.1269531 27.429688 C 4.3603473 28.292119 4 29.402778 4 30.5 C 4 31.597222 4.3603473 32.707882 5.1269531 33.570312 C 5.8935589 34.432744 7.0833337 35 8.5 35 C 9.9166663 35 11.106441 34.432744 11.873047 33.570312 C 12.639653 32.707881 13 31.597222 13 30.5 C 13 29.402778 12.639653 28.292118 11.873047 27.429688 C 11.106441 26.567256 9.9166663 26 8.5 26 z M 19.5 26 C 18.083334 26 16.893559 26.567256 16.126953 27.429688 C 15.360347 28.292119 15 29.402778 15 30.5 C 15 31.597222 15.360347 32.707882 16.126953 33.570312 C 16.893559 34.432744 18.083334 35 19.5 35 C 20.916666 35 22.106441 34.432744 22.873047 33.570312 C 23.639653 32.707881 24 31.597222 24 30.5 C 24 29.402778 23.639653 28.292118 22.873047 27.429688 C 22.106441 26.567256 20.916666 26 19.5 26 z M 30.5 26 C 29.083334 26 27.893559 26.567256 27.126953 27.429688 C 26.360347 28.292119 26 29.402778 26 30.5 C 26 31.597222 26.360347 32.707882 27.126953 33.570312 C 27.893559 34.432744 29.083334 35 30.5 35 C 31.916666 35 33.106441 34.432744 33.873047 33.570312 C 34.639653 32.707881 35 31.597222 35 30.5 C 35 29.402778 34.639653 28.292118 33.873047 27.429688 C 33.106441 26.567256 31.916666 26 30.5 26 z M 41.5 26 C 40.083334 26 38.893559 26.567256 38.126953 27.429688 C 37.360347 28.292119 37 29.402778 37 30.5 C 37 31.597222 37.360347 32.707882 38.126953 33.570312 C 38.893559 34.432744 40.083334 35 41.5 35 C 42.916666 35 44.106441 34.432744 44.873047 33.570312 C 45.639653 32.707881 46 31.597222 46 30.5 C 46 29.402778 45.639653 28.292118 44.873047 27.429688 C 44.106441 26.567256 42.916666 26 41.5 26 z M 8.5 28 C 9.4166661 28 9.9768929 28.307744 10.376953 28.757812 C 10.777013 29.207881 11 29.847222 11 30.5 C 11 31.152778 10.777013 31.792118 10.376953 32.242188 C 9.9768929 32.692256 9.4166661 33 8.5 33 C 7.5833339 33 7.0231072 32.692256 6.6230469 32.242188 C 6.2229865 31.792119 6 31.152778 6 30.5 C 6 29.847222 6.2229865 29.207882 6.6230469 28.757812 C 7.0231072 28.307744 7.5833339 28 8.5 28 z M 19.5 28 C 20.416666 28 20.976893 28.307744 21.376953 28.757812 C 21.777013 29.207881 22 29.847222 22 30.5 C 22 31.152778 21.777013 31.792118 21.376953 32.242188 C 20.976893 32.692256 20.416666 33 19.5 33 C 18.583334 33 18.023107 32.692256 17.623047 32.242188 C 17.222987 31.792119 17 31.152778 17 30.5 C 17 29.847222 17.222987 29.207882 17.623047 28.757812 C 18.023107 28.307744 18.583334 28 19.5 28 z M 30.5 28 C 31.416666 28 31.976893 28.307744 32.376953 28.757812 C 32.777013 29.207881 33 29.847222 33 30.5 C 33 31.152778 32.777013 31.792118 32.376953 32.242188 C 31.976893 32.692256 31.416666 33 30.5 33 C 29.583334 33 29.023107 32.692256 28.623047 32.242188 C 28.222987 31.792119 28 31.152778 28 30.5 C 28 29.847222 28.222987 29.207882 28.623047 28.757812 C 29.023107 28.307744 29.583334 28 30.5 28 z M 41.5 28 C 42.416666 28 42.976893 28.307744 43.376953 28.757812 C 43.777013 29.207881 44 29.847222 44 30.5 C 44 31.152778 43.777013 31.792118 43.376953 32.242188 C 42.976893 32.692256 42.416666 33 41.5 33 C 40.583334 33 40.023107 32.692256 39.623047 32.242188 C 39.222987 31.792119 39 31.152778 39 30.5 C 39 29.847222 39.222987 29.207882 39.623047 28.757812 C 40.023107 28.307744 40.583334 28 41.5 28 z M 8.5 37 C 7.0833337 37 5.8935589 37.567256 5.1269531 38.429688 C 4.3603473 39.292119 4 40.402778 4 41.5 C 4 42.597222 4.3603473 43.707881 5.1269531 44.570312 C 5.8935589 45.432744 7.0833337 46 8.5 46 C 9.9166663 46 11.106441 45.432745 11.873047 44.570312 C 12.639653 43.707881 13 42.597222 13 41.5 C 13 40.402778 12.639653 39.292119 11.873047 38.429688 C 11.106441 37.567256 9.9166663 37 8.5 37 z M 19.5 37 C 18.083334 37 16.893559 37.567256 16.126953 38.429688 C 15.360347 39.292119 15 40.402778 15 41.5 C 15 42.597222 15.360347 43.707881 16.126953 44.570312 C 16.893559 45.432744 18.083334 46 19.5 46 C 20.916666 46 22.106441 45.432745 22.873047 44.570312 C 23.639653 43.707881 24 42.597222 24 41.5 C 24 40.402778 23.639653 39.292119 22.873047 38.429688 C 22.106441 37.567256 20.916666 37 19.5 37 z M 30.5 37 C 29.083334 37 27.893559 37.567256 27.126953 38.429688 C 26.360347 39.292119 26 40.402778 26 41.5 C 26 42.597222 26.360347 43.707881 27.126953 44.570312 C 27.893559 45.432744 29.083334 46 30.5 46 C 31.916666 46 33.106441 45.432745 33.873047 44.570312 C 34.639653 43.707881 35 42.597222 35 41.5 C 35 40.402778 34.639653 39.292119 33.873047 38.429688 C 33.106441 37.567256 31.916666 37 30.5 37 z M 41.5 37 C 40.083334 37 38.893559 37.567256 38.126953 38.429688 C 37.360347 39.292119 37 40.402778 37 41.5 C 37 42.597222 37.360347 43.707881 38.126953 44.570312 C 38.893559 45.432744 40.083334 46 41.5 46 C 42.916666 46 44.106441 45.432745 44.873047 44.570312 C 45.639653 43.707881 46 42.597222 46 41.5 C 46 40.402778 45.639653 39.292119 44.873047 38.429688 C 44.106441 37.567256 42.916666 37 41.5 37 z M 8.5 39 C 9.4166661 39 9.9768929 39.307744 10.376953 39.757812 C 10.777013 40.207881 11 40.847222 11 41.5 C 11 42.152778 10.777013 42.792119 10.376953 43.242188 C 9.9768929 43.692256 9.4166661 44 8.5 44 C 7.5833339 44 7.0231072 43.692255 6.6230469 43.242188 C 6.2229865 42.792119 6 42.152778 6 41.5 C 6 40.847222 6.2229865 40.207881 6.6230469 39.757812 C 7.0231072 39.307744 7.5833339 39 8.5 39 z M 19.5 39 C 20.416666 39 20.976893 39.307744 21.376953 39.757812 C 21.777013 40.207881 22 40.847222 22 41.5 C 22 42.152778 21.777013 42.792119 21.376953 43.242188 C 20.976893 43.692256 20.416666 44 19.5 44 C 18.583334 44 18.023107 43.692255 17.623047 43.242188 C 17.222987 42.792119 17 42.152778 17 41.5 C 17 40.847222 17.222987 40.207881 17.623047 39.757812 C 18.023107 39.307744 18.583334 39 19.5 39 z M 30.5 39 C 31.416666 39 31.976893 39.307744 32.376953 39.757812 C 32.777013 40.207881 33 40.847222 33 41.5 C 33 42.152778 32.777013 42.792119 32.376953 43.242188 C 31.976893 43.692256 31.416666 44 30.5 44 C 29.583334 44 29.023107 43.692255 28.623047 43.242188 C 28.222987 42.792119 28 42.152778 28 41.5 C 28 40.847222 28.222987 40.207881 28.623047 39.757812 C 29.023107 39.307744 29.583334 39 30.5 39 z M 41.5 39 C 42.416666 39 42.976893 39.307744 43.376953 39.757812 C 43.777013 40.207881 44 40.847222 44 41.5 C 44 42.152778 43.777013 42.792119 43.376953 43.242188 C 42.976893 43.692256 42.416666 44 41.5 44 C 40.583334 44 40.023107 43.692255 39.623047 43.242188 C 39.222987 42.792119 39 42.152778 39 41.5 C 39 40.847222 39.222987 40.207881 39.623047 39.757812 C 40.023107 39.307744 40.583334 39 41.5 39 z",
    ),
    stroke=(),
)

icons8_pentagon = VectorIcon(
    fill=(
        "M 25 3 C 23.894531 3 23 3.894531 23 5 C 23 5.0625 22.996094 5.125 23 5.1875 L 5.0625 18.3125 C 4.753906 18.121094 4.390625 18 4 18 C 2.894531 18 2 18.894531 2 20 C 2 20.933594 2.636719 21.714844 3.5 21.9375 L 10.53125 43.65625 C 10.207031 44.011719 10 44.480469 10 45 C 10 46.105469 10.894531 47 12 47 C 12.738281 47 13.371094 46.597656 13.71875 46 L 36.28125 46 C 36.628906 46.597656 37.261719 47 38 47 C 39.105469 47 40 46.105469 40 45 C 40 44.480469 39.792969 44.011719 39.46875 43.65625 L 46.5 21.9375 C 47.363281 21.714844 48 20.933594 48 20 C 48 18.894531 47.105469 18 46 18 C 45.609375 18 45.246094 18.121094 44.9375 18.3125 L 27 5.1875 C 27.003906 5.125 27 5.0625 27 5 C 27 3.894531 26.105469 3 25 3 Z M 24.1875 6.84375 C 24.195313 6.847656 24.210938 6.839844 24.21875 6.84375 C 24.457031 6.945313 24.722656 7 25 7 C 25.277344 7 25.542969 6.945313 25.78125 6.84375 L 25.8125 6.84375 L 44 20.0625 C 44.015625 20.589844 44.246094 21.058594 44.59375 21.40625 L 37.59375 43.03125 C 37.027344 43.148438 36.5625 43.515625 36.28125 44 L 13.71875 44 C 13.4375 43.515625 12.972656 43.148438 12.40625 43.03125 L 5.40625 21.40625 C 5.753906 21.058594 5.984375 20.589844 6 20.0625 Z",
    ),
    stroke=(),
)
icons8_pentagon_squared = VectorIcon(
    fill=(
        "M 25 3 C 23.894531 3 23 3.894531 23 5 C 23 5.0625 22.996094 5.125 23 5.1875 L 5.0625 18.3125 C 4.753906 18.121094 4.390625 18 4 18 C 2.894531 18 2 18.894531 2 20 C 2 20.933594 2.636719 21.714844 3.5 21.9375 L 10.53125 43.65625 C 10.207031 44.011719 10 44.480469 10 45 C 10 46.105469 10.894531 47 12 47 C 12.738281 47 13.371094 46.597656 13.71875 46 L 36.28125 46 C 36.628906 46.597656 37.261719 47 38 47 C 39.105469 47 40 46.105469 40 45 C 40 44.480469 39.792969 44.011719 39.46875 43.65625 L 46.5 21.9375 C 47.363281 21.714844 48 20.933594 48 20 C 48 18.894531 47.105469 18 46 18 C 45.609375 18 45.246094 18.121094 44.9375 18.3125 L 27 5.1875 C 27.003906 5.125 27 5.0625 27 5 C 27 3.894531 26.105469 3 25 3 Z M 24.1875 6.84375 C 24.195313 6.847656 24.210938 6.839844 24.21875 6.84375 C 24.457031 6.945313 24.722656 7 25 7 C 25.277344 7 25.542969 6.945313 25.78125 6.84375 L 25.8125 6.84375 L 44 20.0625 C 44.015625 20.589844 44.246094 21.058594 44.59375 21.40625 L 37.59375 43.03125 C 37.027344 43.148438 36.5625 43.515625 36.28125 44 L 13.71875 44 C 13.4375 43.515625 12.972656 43.148438 12.40625 43.03125 L 5.40625 21.40625 C 5.753906 21.058594 5.984375 20.589844 6 20.0625 Z",
    ),
    stroke=("M 0 0 h 50 v50 h -50 v -50",),
)

icons8_compress = VectorIcon(
    fill=(
        "M 46.292969 2.292969 L 30 18.585938 L 30 9 L 28 9 L 28 22 L 41 22 L 41 20 L 31.414063 20 L 47.707031 3.707031 Z M 9 28 L 9 30 L 18.585938 30 L 2.292969 46.292969 L 3.707031 47.707031 L 20 31.414063 L 20 41 L 22 41 L 22 28 Z",
    ),
    stroke=(),
)

icons8_enlarge = VectorIcon(
    fill=(
        "M 33 4 L 33 6 L 42.585938 6 L 27.292969 21.292969 L 28.707031 22.707031 L 44 7.4140625 L 44 17 L 46 17 L 46 4 L 33 4 z M 21.292969 27.292969 L 6 42.585938 L 6 33 L 4 33 L 4 46 L 17 46 L 17 44 L 7.4140625 44 L 22.707031 28.707031 L 21.292969 27.292969 z",
    ),
    stroke=(),
)

icons8_centerh = VectorIcon(
    fill=(
        "M16,0c-0.553,0-1,0.448-1,1v30c0,0.552,0.447,1,1,1s1-0.448,1-1V1C17,0.448,16.553,0,16,0z",
        "M27.499,11.15c-0.271,0-0.536,0.074-0.77,0.214l-5.589,3.35c-0.456,0.273-0.728,0.754-0.728,1.286 s0.271,1.013,0.729,1.287l5.587,3.349c0.234,0.14,0.5,0.214,0.771,0.214c0.389,0,0.758-0.148,1.04-0.418 C28.836,20.147,29,19.763,29,19.349v-6.698C29,11.823,28.327,11.15,27.499,11.15z M27,18.466L22.885,16L27,13.534V18.466z",
        "M10.811,14.719l-5.537-3.333c-0.279-0.168-0.568-0.253-0.86-0.253C3.594,11.132,3,11.779,3,12.671v6.659 c0,0.891,0.595,1.538,1.413,1.538c0.291,0,0.58-0.084,0.859-0.252l5.536-3.326c0.455-0.273,0.728-0.753,0.728-1.284 C11.537,15.475,11.266,14.994,10.811,14.719z M5,18.447v-4.892l4.066,2.448L5,18.447z",
    ),
    stroke=(),
)

icons8_centerv = VectorIcon(
    fill=(
        "M31,15H1c-0.553,0-1,0.448-1,1s0.447,1,1,1h30c0.553,0,1-0.448,1-1S31.553,15,31,15z",
        "M17.259,21.168c-0.272-0.457-0.754-0.73-1.287-0.73c-0.531,0-1.013,0.272-1.286,0.728l-3.341,5.562 c-0.277,0.462-0.285,1.041-0.02,1.511S12.091,29,12.631,29h6.679c0.539,0,1.04-0.292,1.306-0.761 c0.266-0.469,0.258-1.048-0.02-1.511L17.259,21.168z M13.515,27l2.457-4.091L18.427,27H13.515z",
        "M14.682,10.834c0.273,0.456,0.755,0.728,1.286,0.728s1.013-0.272,1.286-0.728l3.342-5.562 c0.277-0.462,0.285-1.041,0.02-1.511S19.85,3,19.31,3h-6.679c-0.539,0-1.04,0.292-1.306,0.761c-0.266,0.469-0.258,1.048,0.02,1.511 L14.682,10.834z M18.426,5l-2.458,4.091L13.514,5H18.426z",
    ),
    stroke=(),
)

icon_corner1 = VectorIcon(
    fill=(
        "M3,3.5v17C3,20.7763672,3.2236328,21,3.5,21h1C4.7763672,21,5,20.7763672,5,20.5V5h15.5 C20.7763672,5,21,4.7763672,21,4.5v-1C21,3.2236328,20.7763672,3,20.5,3h-17C3.2236328,3,3,3.2236328,3,3.5z",
    ),
    stroke=(),
)

icon_corner2 = VectorIcon(
    fill=(
        "M20.5,3h-17C3.2236328,3,3,3.2236328,3,3.5v1C3,4.7763672,3.2236328,5,3.5,5H19v15.5 c0,0.2763672,0.2236328,0.5,0.5,0.5h1c0.2763672,0,0.5-0.2236328,0.5-0.5v-17C21,3.2236328,20.7763672,3,20.5,3z",
    ),
    stroke=(),
)

icon_corner3 = VectorIcon(
    fill=(
        "M21,20.5v-17C21,3.2236328,20.7763672,3,20.5,3h-1C19.2236328,3,19,3.2236328,19,3.5V19H3.5 C3.2236328,19,3,19.2236328,3,19.5v1C3,20.7763672,3.2236328,21,3.5,21h17C20.7763672,21,21,20.7763672,21,20.5z",
    ),
    stroke=(),
)

icon_corner4 = VectorIcon(
    fill=(
        "M3.5,21h17c0.2763672,0,0.5-0.2236328,0.5-0.5v-1c0-0.2763672-0.2236328-0.5-0.5-0.5H5V3.5 C5,3.2236328,4.7763672,3,4.5,3h-1C3.2236328,3,3,3.2236328,3,3.5v17C3,20.7763672,3.2236328,21,3.5,21z",
    ),
    stroke=(),
)

icons8_route = VectorIcon(
    fill=(
        "M 25 0.0078125 C 23.691406 0.0078125 22.382813 0.5 21.390625 1.492188 L 1.492188 21.390625 C -0.492188 23.375 -0.492188 26.625 1.492188 28.609375 L 21.390625 48.507813 C 23.375 50.492188 26.625 50.492188 28.609375 48.507813 L 48.507813 28.609375 C 50.492188 26.625 50.492188 23.375 48.507813 21.390625 L 28.609375 1.492188 C 27.617188 0.5 26.308594 0.0078125 25 0.0078125 Z M 25 1.992188 C 25.792969 1.992188 26.585938 2.296875 27.191406 2.90625 L 47.09375 22.808594 C 48.3125 24.023438 48.3125 25.976563 47.09375 27.191406 L 27.191406 47.09375 C 25.976563 48.3125 24.023438 48.3125 22.808594 47.09375 L 2.90625 27.191406 C 1.6875 25.976563 1.6875 24.023438 2.90625 22.808594 L 22.808594 2.90625 C 23.414063 2.296875 24.207031 1.992188 25 1.992188 Z M 29.988281 14.988281 C 29.582031 14.992188 29.21875 15.238281 29.0625 15.613281 C 28.910156 15.992188 29 16.421875 29.292969 16.707031 L 33.585938 21 L 23 21 C 20.25 21 18 23.25 18 26 L 18 35 C 17.996094 35.359375 18.183594 35.695313 18.496094 35.878906 C 18.808594 36.058594 19.191406 36.058594 19.503906 35.878906 C 19.816406 35.695313 20.003906 35.359375 20 35 L 20 26 C 20 24.332031 21.332031 23 23 23 L 33.585938 23 L 29.292969 27.292969 C 29.03125 27.542969 28.925781 27.917969 29.019531 28.265625 C 29.109375 28.617188 29.382813 28.890625 29.734375 28.980469 C 30.082031 29.074219 30.457031 28.96875 30.707031 28.707031 L 36.621094 22.796875 C 36.691406 22.738281 36.753906 22.675781 36.8125 22.605469 L 37.414063 22 L 36.808594 21.390625 C 36.753906 21.324219 36.691406 21.261719 36.625 21.207031 C 36.621094 21.207031 36.621094 21.203125 36.617188 21.203125 L 30.707031 15.292969 C 30.519531 15.097656 30.261719 14.992188 29.988281 14.988281 Z",
    ),
    stroke=(),
)

icons8_file = VectorIcon(
    fill=(
        "M 7 2 L 7 48 L 43 48 L 43 14.59375 L 42.71875 14.28125 L 30.71875 2.28125 L 30.40625 2 Z M 9 4 L 29 4 L 29 16 L 41 16 L 41 46 L 9 46 Z M 31 5.4375 L 39.5625 14 L 31 14 Z"
    ),
    stroke=(),
)

icons8_circled_play = VectorIcon(
    fill=(
        "M 25 2 C 12.309295 2 2 12.309295 2 25 C 2 37.690705 12.309295 48 25 48 C 37.690705 48 48 37.690705 48 25 C 48 12.309295 37.690705 2 25 2 z M 25 4 C 36.609824 4 46 13.390176 46 25 C 46 36.609824 36.609824 46 25 46 C 13.390176 46 4 36.609824 4 25 C 4 13.390176 13.390176 4 25 4 z M 17.958984 13.037109 A 1.0001 1.0001 0 0 0 16.958984 14.041016 L 16.958984 14.064453 A 1.0001 1.0001 0 0 0 16.958984 14.070312 L 17.042969 36.037109 A 1.0001 1.0001 0 0 0 18.546875 36.898438 L 37.503906 25.828125 A 1.0001 1.0001 0 0 0 37.498047 24.095703 L 18.457031 13.169922 L 18.457031 13.171875 A 1.0001 1.0001 0 0 0 17.958984 13.037109 z M 18.964844 15.769531 L 35.001953 24.972656 L 19.037109 34.294922 L 18.964844 15.769531 z"
    ),
    stroke=(),
)

icons8_circled_stop = VectorIcon(
    fill=(
        "M 25 2 C 12.309534 2 2 12.309534 2 25 C 2 37.690466 12.309534 48 25 48 C 37.690466 48 48 37.690466 48 25 C 48 12.309534 37.690466 2 25 2 z M 25 4 C 36.609534 4 46 13.390466 46 25 C 46 36.609534 36.609534 46 25 46 C 13.390466 46 4 36.609534 4 25 C 4 13.390466 13.390466 4 25 4 z M 16 16 L 16 17 L 16 34 L 34 34 L 34 16 L 16 16 z M 18 18 L 32 18 L 32 32 L 18 32 L 18 18 z"
    ),
    stroke=(),
)

icons8_checkmark = VectorIcon(
    fill=(
        "M 4 4 L 4 28 L 28 28 L 28 12.1875 L 26 14.1875 L 26 26 L 6 26 L 6 6 L 25.8125 6 L 27.8125 4 Z M 27.28125 7.28125 L 16 18.5625 L 11.71875 14.28125 L 10.28125 15.71875 L 15.28125 20.71875 L 16 21.40625 L 16.71875 20.71875 L 28.71875 8.71875 Z"
    ),
    stroke=(),
)

icons8_ghost = VectorIcon(
    fill=(
        "M 24 2.9980469 C 17.211539 2.9980469 11.727169 8.4404724 11.119141 15.269531 C 10.743358 15.063705 10.217761 14.902293 9.9960938 14.755859 C 8.3451022 13.653703 6.1477186 13.769365 4.6210938 15.039062 C 3.0941899 16.308742 2.5831438 18.448175 3.3632812 20.271484 C 3.6289337 20.890842 5.3057598 23.936762 9.875 26.677734 C 8.9952934 28.849142 7.7997276 30.892625 6.9082031 32.146484 C 5.594411 33.994139 5.7183656 36.534628 7.2382812 38.232422 C 9.0155881 40.216805 12.07121 42 16 42 L 16.041016 42 C 17.811223 43.941744 20.709941 45 24 45 C 27.290291 45 30.189414 43.942485 31.958984 42 L 32 42 C 35.92879 42 38.984412 40.216805 40.761719 38.232422 A 1.50015 1.50015 0 0 0 40.763672 38.230469 C 42.282264 36.532538 42.406135 33.994184 41.09375 32.146484 A 1.50015 1.50015 0 0 0 41.091797 32.146484 C 40.200272 30.892625 39.004707 28.849142 38.125 26.677734 C 42.69424 23.936762 44.371066 20.890842 44.636719 20.271484 C 45.416856 18.448175 44.90581 16.308742 43.378906 15.039062 C 41.852281 13.769365 39.654898 13.653703 38.003906 14.755859 C 37.782239 14.902293 37.256642 15.063705 36.880859 15.269531 C 36.272831 8.4405195 30.788461 2.9980469 24 2.9980469 z M 24 5.9980469 C 29.504991 5.9980469 34 10.64802 34 16.498047 L 34 17.498047 A 1.50015 1.50015 0 0 0 35.755859 18.976562 C 37.673914 18.644889 39.161537 17.584744 39.662109 17.253906 A 1.50015 1.50015 0 0 0 39.667969 17.25 C 40.224977 16.878156 40.941609 16.915404 41.458984 17.345703 C 41.973551 17.773585 42.141612 18.473617 41.878906 19.089844 C 41.813236 19.242956 40.518585 22.210816 35.546875 24.777344 A 1.50015 1.50015 0 0 0 34.810547 26.582031 C 35.818482 29.626406 37.504977 32.277169 38.646484 33.882812 C 39.1581 34.603113 39.108751 35.5804 38.527344 36.230469 C 37.300611 37.600083 35.01121 39 32 39 L 31.347656 39 A 1.50015 1.50015 0 0 0 30.113281 39.648438 C 29.318032 40.802684 26.924135 42 24 42 C 21.075865 42 18.683105 40.803392 17.886719 39.648438 A 1.50015 1.50015 0 0 0 16.650391 39 L 16 39 C 12.98879 39 10.699349 37.600086 9.4726562 36.230469 C 8.890572 35.580262 8.8393546 34.605111 9.3515625 33.884766 C 10.493088 32.279299 12.181149 29.62752 13.189453 26.582031 A 1.50015 1.50015 0 0 0 12.453125 24.777344 C 7.4831213 22.211697 6.187588 19.246787 6.1210938 19.091797 L 6.1210938 19.089844 C 5.8583882 18.473664 6.0264486 17.773585 6.5410156 17.345703 C 7.0583908 16.915401 7.7750229 16.878156 8.3320312 17.25 A 1.50015 1.50015 0 0 0 8.3378906 17.253906 C 8.8384626 17.584744 10.326086 18.644889 12.244141 18.976562 A 1.50015 1.50015 0 0 0 14 17.498047 L 14 16.498047 C 14 10.64802 18.495009 5.9980469 24 5.9980469 z M 20 14 A 2 2.5 0 0 0 20 19 A 2 2.5 0 0 0 20 14 z M 28 14 A 2 2.5 0 0 0 28 19 A 2 2.5 0 0 0 28 14 z M 24 21 C 22.246 21 20.664453 22.063484 20.064453 23.646484 C 19.948453 23.954484 19.989781 24.297359 20.175781 24.568359 C 20.363781 24.837359 20.672 25 21 25 L 27 25 C 27.328 25 27.635266 24.838359 27.822266 24.568359 C 28.009266 24.298359 28.051547 23.953484 27.935547 23.646484 C 27.335547 22.063484 25.754 21 24 21 z"
    ),
    stroke=(),
)

icons8_square_border = VectorIcon(
    fill=(
        "M 4 4 L 4 16 L 9 16 L 9 9 L 16 9 L 16 4 L 4 4 z M 34 4 L 34 9 L 41 9 L 41 16 L 46 16 L 46 4 L 34 4 z M 25 22 A 3 3 0 0 0 22 25 A 3 3 0 0 0 25 28 A 3 3 0 0 0 28 25 A 3 3 0 0 0 25 22 z M 4 34 L 4 46 L 16 46 L 16 41 L 9 41 L 9 34 L 4 34 z M 41 34 L 41 41 L 34 41 L 34 46 L 46 46 L 46 34 L 41 34 z",
    ),
    stroke=(),
)

icons8_circled_left = VectorIcon(
    fill=(
        "M 64 6.0507812 C 49.15 6.0507812 34.3 11.7 23 23 C 12 33.9 6 48.5 6 64 C 6 79.5 12 94.1 23 105 C 34.3 116.3 49.2 122 64 122 C 78.9 122 93.7 116.3 105 105 C 116 94 122 79.5 122 64 C 122 48.5 116 33.9 105 23 C 93.7 11.7 78.85 6.0507812 64 6.0507812 z M 64 12 C 77.3 12 90.600781 17.099219 100.80078 27.199219 C 110.60078 37.099219 116 50.1 116 64 C 116 77.9 110.60078 90.900781 100.80078 100.80078 C 80.500781 121.10078 47.500781 121.10078 27.300781 100.80078 C 17.400781 90.900781 12 77.9 12 64 C 12 50.1 17.399219 37.099219 27.199219 27.199219 C 37.399219 17.099219 50.7 12 64 12 z M 58.962891 46 C 58.200391 46 57.450391 46.300391 56.900391 46.900391 L 41.900391 61.900391 C 40.700391 63.100391 40.700391 64.999609 41.900391 66.099609 L 56.900391 81.099609 C 57.500391 81.699609 58.3 82 59 82 C 59.7 82 60.499609 81.699609 61.099609 81.099609 C 62.299609 79.899609 62.299609 78.000391 61.099609 76.900391 L 51.199219 67 L 82 67 C 83.7 67 85 65.7 85 64 C 85 62.3 83.7 61 82 61 L 51.199219 61 L 61.099609 51.099609 C 62.299609 49.899609 62.299609 48.000391 61.099609 46.900391 C 60.499609 46.300391 59.725391 46 58.962891 46 z"
    ),
    stroke=(),
)

icons8_circled_right = VectorIcon(
    fill=(
        "M 64 6.0507812 C 49.15 6.0507812 34.3 11.7 23 23 C 12 33.9 6 48.5 6 64 C 6 79.5 12 94.1 23 105 C 34.3 116.3 49.2 122 64 122 C 78.9 122 93.7 116.3 105 105 C 116 94 122 79.5 122 64 C 122 48.5 116 33.9 105 23 C 93.7 11.7 78.85 6.0507812 64 6.0507812 z M 64 12 C 77.3 12 90.600781 17.099219 100.80078 27.199219 C 110.60078 37.099219 116 50.1 116 64 C 116 77.9 110.60078 90.900781 100.80078 100.80078 C 80.500781 121.10078 47.500781 121.10078 27.300781 100.80078 C 17.400781 90.900781 12 77.9 12 64 C 12 50.1 17.399219 37.099219 27.199219 27.199219 C 37.399219 17.099219 50.7 12 64 12 z M 68.962891 46 C 68.200391 46 67.450391 46.300391 66.900391 46.900391 C 65.700391 48.100391 65.700391 49.999609 66.900391 51.099609 L 76.800781 61 L 46 61 C 44.3 61 43 62.3 43 64 C 43 65.7 44.3 67 46 67 L 76.800781 67 L 66.900391 76.900391 C 65.700391 78.100391 65.700391 79.999609 66.900391 81.099609 C 67.500391 81.699609 68.3 82 69 82 C 69.7 82 70.499609 81.699609 71.099609 81.099609 L 86.099609 66.099609 C 87.299609 64.899609 87.299609 63.000391 86.099609 61.900391 L 71.099609 46.900391 C 70.499609 46.300391 69.725391 46 68.962891 46 z",
    ),
    stroke=(),
)

icon_update_plan = VectorIcon(
    fill=(),
    stroke=(
        "M 0 20 L 5 25 L 10 10 M 30 20 h 50",
        "M 0 50 L 5 55 L 10 40 M 30 50 h 50",
        "M 0 80 L 5 85 L 10 70 M 30 80 h 50",
    ),
)

icons8_vector = VectorIcon(
    fill=(
        "M 19 8 L 19 13 L 5.8125 13 C 5.398438 11.839844 4.300781 11 3 11 C 1.34375 11 0 12.34375 0 14 C 0 15.65625 1.34375 17 3 17 C 4.300781 17 5.398438 16.160156 5.8125 15 L 17 15 C 11.921875 17.714844 8.386719 22.941406 8.03125 29 L 3 29 L 3 41 L 15 41 L 15 29 L 10.0625 29 C 10.441406 23.277344 13.992188 18.433594 19 16.25 L 19 20 L 31 20 L 31 16.25 C 36 18.441406 39.5625 23.277344 39.9375 29 L 35 29 L 35 41 L 47 41 L 47 29 L 41.96875 29 C 41.621094 22.929688 38.082031 17.714844 33 15 L 44.1875 15 C 44.601563 16.160156 45.699219 17 47 17 C 48.65625 17 50 15.65625 50 14 C 50 12.34375 48.65625 11 47 11 C 45.699219 11 44.601563 11.839844 44.1875 13 L 31 13 L 31 8 Z M 21 10 L 29 10 L 29 13.65625 C 28.941406 13.851563 28.941406 14.054688 29 14.25 L 29 18 L 21 18 L 21 14.1875 C 21.027344 14.054688 21.027344 13.914063 21 13.78125 Z M 5 31 L 13 31 L 13 39 L 5 39 Z M 37 31 L 45 31 L 45 39 L 37 39 Z",
    ),
    stroke=(),
)

icons8_node_edit = VectorIcon(
    fill=(
        "M 23.277344 3.8632812 L 17.285156 5.7539062 C 16.187933 6.0517442 15.311459 6.8795343 14.953125 7.953125 L 14.943359 7.9804688 L 11.580078 20.419922 L 13.261719 19.964844 L 24.029297 17.052734 L 24.054688 17.042969 C 25.122208 16.688075 25.944797 15.819008 26.240234 14.732422 L 26.230469 14.771484 L 28.136719 8.7226562 L 23.277344 3.8632812 z M 22.722656 6.1367188 L 25.863281 9.2773438 L 24.316406 14.189453 L 24.310547 14.208984 C 24.190243 14.651449 23.860868 14.996916 23.425781 15.142578 C 23.425781 15.142578 23.423828 15.144531 23.423828 15.144531 L 16.357422 17.056641 L 19.484375 13.929688 A 2 2 0 0 0 20 14 A 2 2 0 0 0 20 10 A 2 2 0 0 0 18.070312 12.515625 L 14.943359 15.642578 L 16.853516 8.5820312 C 17.004183 8.1365066 17.347717 7.8092274 17.810547 7.6835938 L 17.830078 7.6796875 L 22.722656 6.1367188 z M 6 7 A 2 2 0 0 0 5.0371094 10.75 C 5.4223625 19.526772 12.471528 26.576647 21.248047 26.962891 A 2 2 0 0 0 23 28 A 2 2 0 0 0 23 24 A 2 2 0 0 0 21.291016 24.964844 C 13.563991 24.604238 7.3957618 18.436009 7.0351562 10.708984 A 2 2 0 0 0 6 7 z",
    ),
    stroke=(),
)

icon_resize_horizontal = VectorIcon(
    fill=(),
    stroke=(
        "M 0 30 h 100 M 0 30 L 30 10 M 0 30 L 30 50",
        "M 100 70 h -100 M 100 70 L 70 50 M 100 70 L 70 90",
    ),
)

icon_open_door = VectorIcon(
    fill=(),
    stroke=(
        "M 0 20 L 60 0 L 60 120 L 0 100 L 0 20",
        "M 70 20 h 30 v 80 h -30",
        "M 45 60 a 3,5, 0 1,0 1,0",
    ),
    strokewidth=10,
)

icon_closed_door = VectorIcon(
    fill=(),
    stroke=(
        "M 0 0 h 100 v 120 h -100 v -120",
        "M 15 15 h 70 v 105 h -70 v -105",
        "M 70 60 a 5,5, 0 1,0 1,0",
    ),
    strokewidth=10,
)

icon_circled_1 = VectorIcon(
    fill=(),
    stroke=(
        "M 50 0 a 50,50, 0 1,0 1,0",
        "M 40,45 L 55 20 L 55 70 h -10 h 20",
    ),
)

icon_nohatch = VectorIcon(
    fill=(),
    stroke=("M 10 10 h 80 v 80 h -80 v -80",),
)

icon_hatch = VectorIcon(
    fill=(),
    stroke=(
        "M 10 10 h 80 v 80 h -80 v -80",
        "M 10 26 h 80",
        "M 10 42 h 80",
        "M 10 58 h 80",
        "M 10 74 h 80",
    ),
)

icon_hatch_bidir = VectorIcon(
    fill=(),
    stroke=(
        "M 10 10 h 80 v 80 h -80 v -80",
        "M 10 26 h 80 l -5 5 m 5 -5 l -5 -5",
        "M 10 42 l 5 5 m -5 -5 l 5 -5 m -5 5 h 80",
        "M 10 58 h 80 l -5 5 m 5 -5 l -5 -5",
        "M 10 74 l 5 5 m -5 -5 l 5 -5 m -5 5 h 80",
    ),
)

icon_hatch_diag = VectorIcon(
    fill=(),
    stroke=(
        "M 10 10 h 80 v 80 h -80 v -80",
        "M 10 30 L 30 10",
        "M 10 50 L 50 10",
        "M 10 70 L 70 10",
        "M 10 90 L 90 10",
        "M 30 90 L 90 30",
        "M 50 90 L 90 50",
        "M 70 90 L 90 70",
    ),
)

icon_hatch_diag_bidir = VectorIcon(
    fill=(),
    stroke=(
        "M 10 10 h 80 v 80 h -80 v -80",
        "M 10 30 L 30 10 l -10 5 m 10 -5 l -5 10",
        "M 10 70 l 5 -10 m -5 10 l 10 -5 m -10 5 L 70 10",
        "M 30 90 L 90 30 l -10 5 m 10 -5 l -5 10",
        "M 70 90 l 5 -10 m -5 10 l 10 -5 m -10 5 L 90 70",
    ),
)

icon_bmap_text = VectorIcon(fill=(), stroke="M 20 0 h 60 h -30 v80", edge=20)

icons8_text = VectorIcon(
    fill=(),
    stroke=(
        "M39,7H11 c-0.552,0-1,0.448-1,1v6c0,0.552,0.448,1,1,1h2c0.552,0,1-0.448,1-1v-3h9v28h-3c-0.552,0-1,0.448-1,1v2c0,0.552,0.448,1,1,1h10 c0.552,0,1-0.448,1-1v-2c0-0.552-0.448-1-1-1h-3V11h9v3c0,0.552,0.448,1,1,1h2c0.552,0,1-0.448,1-1V8C40,7.448,39.552,7,39,7z",
    ),
)

icon_regmarks = VectorIcon(
    fill=(),
    stroke=(
        "M 0 0 h 100 v 20 h -100 v -20",
        "M 0 30 h 60 v 60 h -60 v -60",
        "M 70 30 h 30 v 60 h -30 v -60",
    ),
)

icons8_direction = VectorIcon(
    fill=(
        "M 37.90625 3.96875 C 37.863281 3.976563 37.820313 3.988281 37.78125 4 C 37.40625 4.066406 37.105469 4.339844 37 4.703125 C 36.894531 5.070313 37.003906 5.460938 37.28125 5.71875 L 43.5625 12 L 12 12 C 11.96875 12 11.9375 12 11.90625 12 C 11.355469 12.027344 10.925781 12.496094 10.953125 13.046875 C 10.980469 13.597656 11.449219 14.027344 12 14 L 43.5625 14 L 37.28125 20.28125 C 36.882813 20.679688 36.882813 21.320313 37.28125 21.71875 C 37.679688 22.117188 38.320313 22.117188 38.71875 21.71875 L 46.5625 13.84375 C 46.617188 13.808594 46.671875 13.765625 46.71875 13.71875 C 46.742188 13.6875 46.761719 13.65625 46.78125 13.625 C 46.804688 13.605469 46.824219 13.585938 46.84375 13.5625 C 46.882813 13.503906 46.914063 13.441406 46.9375 13.375 C 46.949219 13.355469 46.960938 13.332031 46.96875 13.3125 C 46.96875 13.300781 46.96875 13.292969 46.96875 13.28125 C 46.980469 13.25 46.992188 13.21875 47 13.1875 C 47.015625 13.082031 47.015625 12.980469 47 12.875 C 47 12.855469 47 12.832031 47 12.8125 C 47 12.800781 47 12.792969 47 12.78125 C 46.992188 12.761719 46.980469 12.738281 46.96875 12.71875 C 46.96875 12.707031 46.96875 12.699219 46.96875 12.6875 C 46.960938 12.667969 46.949219 12.644531 46.9375 12.625 C 46.9375 12.613281 46.9375 12.605469 46.9375 12.59375 C 46.929688 12.574219 46.917969 12.550781 46.90625 12.53125 C 46.894531 12.519531 46.886719 12.511719 46.875 12.5 C 46.867188 12.480469 46.855469 12.457031 46.84375 12.4375 C 46.808594 12.382813 46.765625 12.328125 46.71875 12.28125 L 46.6875 12.28125 C 46.667969 12.257813 46.648438 12.238281 46.625 12.21875 L 38.71875 4.28125 C 38.511719 4.058594 38.210938 3.945313 37.90625 3.96875 Z M 4 12 C 3.449219 12 3 12.449219 3 13 C 3 13.550781 3.449219 14 4 14 C 4.550781 14 5 13.550781 5 13 C 5 12.449219 4.550781 12 4 12 Z M 8 12 C 7.449219 12 7 12.449219 7 13 C 7 13.550781 7.449219 14 8 14 C 8.550781 14 9 13.550781 9 13 C 9 12.449219 8.550781 12 8 12 Z M 11.875 28 C 11.652344 28.023438 11.441406 28.125 11.28125 28.28125 L 3.4375 36.15625 L 3.34375 36.1875 C 3.320313 36.207031 3.300781 36.226563 3.28125 36.25 L 3.28125 36.28125 C 3.257813 36.300781 3.238281 36.320313 3.21875 36.34375 C 3.195313 36.363281 3.175781 36.382813 3.15625 36.40625 C 3.15625 36.417969 3.15625 36.425781 3.15625 36.4375 C 3.132813 36.457031 3.113281 36.476563 3.09375 36.5 C 3.09375 36.511719 3.09375 36.519531 3.09375 36.53125 C 3.03125 36.636719 2.988281 36.753906 2.96875 36.875 C 2.96875 36.886719 2.96875 36.894531 2.96875 36.90625 C 2.96875 36.9375 2.96875 36.96875 2.96875 37 C 2.96875 37.019531 2.96875 37.042969 2.96875 37.0625 C 2.96875 37.074219 2.96875 37.082031 2.96875 37.09375 C 2.984375 37.226563 3.027344 37.351563 3.09375 37.46875 C 3.101563 37.488281 3.113281 37.511719 3.125 37.53125 C 3.136719 37.542969 3.144531 37.550781 3.15625 37.5625 C 3.164063 37.582031 3.175781 37.605469 3.1875 37.625 C 3.199219 37.636719 3.207031 37.644531 3.21875 37.65625 C 3.230469 37.667969 3.238281 37.675781 3.25 37.6875 C 3.261719 37.699219 3.269531 37.707031 3.28125 37.71875 C 3.335938 37.777344 3.398438 37.832031 3.46875 37.875 L 11.28125 45.71875 C 11.679688 46.117188 12.320313 46.117188 12.71875 45.71875 C 13.117188 45.320313 13.117188 44.679688 12.71875 44.28125 L 6.4375 38 L 38 38 C 38.359375 38.003906 38.695313 37.816406 38.878906 37.503906 C 39.058594 37.191406 39.058594 36.808594 38.878906 36.496094 C 38.695313 36.183594 38.359375 35.996094 38 36 L 6.4375 36 L 12.71875 29.71875 C 13.042969 29.417969 13.128906 28.941406 12.933594 28.546875 C 12.742188 28.148438 12.308594 27.929688 11.875 28 Z M 42 36 C 41.449219 36 41 36.449219 41 37 C 41 37.550781 41.449219 38 42 38 C 42.550781 38 43 37.550781 43 37 C 43 36.449219 42.550781 36 42 36 Z M 46 36 C 45.449219 36 45 36.449219 45 37 C 45 37.550781 45.449219 38 46 38 C 46.550781 38 47 37.550781 47 37 C 47 36.449219 46.550781 36 46 36 Z",
    ),
    stroke=(),
)

icon_effect_wobble = VectorIcon(
    fill=(),
    stroke=(
        "M 10 10 a 10,10, 0 1,0 1,0",
        "M 25 10 a 10,10, 0 1,0 1,0",
        "M 40 10 a 10,10, 0 1,0 1,0",
    ),
)

icon_effect_hatch = VectorIcon(
    fill=(),
    stroke=(
        "M 0 5 L 5 0",
        "M 0 17.5 L 17.5 0",
        "M 0 30 L 30 0",
        "M 12.5 30 L 30 12.5",
        "M 25 30 L 30 25",
    ),
)

icon_split_image = VectorIcon(
    fill=(),
    stroke=(
        "M 0 0 h 45 v90 h -45 v -90",
        "M 55 0 h 45 v90 h -45 v -90",
        "M 0 30 h 45 M 55 30 h 45",
        "M 0 60 h 45 M 55 60 h 45",
    ),
)

icon_keyhole = VectorIcon(
    fill=(
        "M 50 10 a 20,20, 0 1,0 1,0 z",
        "M 50 30 L 30 90 L 70 90 z",
    ),
    stroke="M 0 0 h 100 v 100 h -100 v -100",
)

icon_cag_union = VectorIcon(
    fill=(),
    stroke=(
        "M 20 20 v -20 h 30 v 30 h -20",  # First rectangle
        "M 20 20 h -20 v 30 h 30 v -20",  # Second rectangle
        "M 22.5 20 h 2 M 27.5 20 h 2",
        "M 30 20 v 2 M 30 25 v 2",
        "M 27.5 30 h -2 M 22.5 30 h -2",
        "M 20 30 v -2 M 20 25 v -2",
    ),
)

icon_cag_subtract = VectorIcon(
    fill=(),
    stroke=(
        "M 20 20 h -20 v 30 h 30 v -20 h -10 v -10",  # Main rectangle
        "M 22.5 20 h 2 M 27.5 20 h 2",
        "M 30 20 v 2 M 30 25 v 2",
        "M 20 17.5 v -2 M 20 12.5 v -2 M 20 7.5 v -2 M 20 2.5 v -2",
        "M 20 0 h 2 M 25 0 h 2 M 30 0 h 2 M 35 0 h 2 M 40 0 h 2 M 45 0 h 2",
        "M 50 0 v 2 M 50 5 v 2 M 50 10 v 2 M 50 15 v 2 M 50 20 v 2 M 50 25 v 2"
        "M 32.5 30 h 2 M 37.5 30 h 2 M 42.5 30 h 2 M 47.5 30 h 2",
    ),
)

icon_cag_common = VectorIcon(
    fill=(),
    stroke=(
        "M 20 20 h 10 v 10 h -10 v -10",  # Main rectangle
        "M 22.5 20 h 2 M 27.5 20 h 2",
        "M 30 20 v 2 M 30 25 v 2",
        "M 20 17.5 v -2 M 20 12.5 v -2 M 20 7.5 v -2 M 20 2.5 v -2",
        "M 20 0 h 2 M 25 0 h 2 M 30 0 h 2 M 35 0 h 2 M 40 0 h 2 M 45 0 h 2",
        "M 50 0 v 2 M 50 5 v 2 M 50 10 v 2 M 50 15 v 2 M 50 20 v 2 M 50 25 v 2",
        "M 32.5 30 h 2 M 37.5 30 h 2 M 42.5 30 h 2 M 47.5 30 h 2",
        "M 0 20 h 2 M 5 20 h 2 M 10 20 h 2 M 15 20 h 2",
        "M 0 20 v 2 M 0 25 v 2 M 0 30 v 2 M 0 35 v 2 M 0 40 v 2 M 0 45 v 2",
        "M 0 50 h 2 M 5 50 h 2 M 10 50 h 2 M 15 50 h 2 M 20 50 h 2 M 25 50 h 2",
        "M 30 32.5 v 2 M 30 37.5 v 2 M 30 42.5 v 2 M 30 47.5 v 2",
    ),
)

icon_cag_xor = VectorIcon(
    fill=(),
    stroke=(
        "M 20 0 h 30 v 30 h -30 v -30",
        "M 0 20 h 30 v 30 h -30 v -30",
    ),
)

icon_hinges = VectorIcon(
    fill=(),
    stroke=(
        "M 0 10 h 30 v 75 h -30 v -75",
        "M 40 10 h 30 v 75 h -30 v -75",
        "M 30 5 h 10 v 40 h -10 v -40",
        "M 30 50 h 10 v 40 h -10 v -40",
        "M 17.5 17.5 a 2.5,2.5, 0 1,0 1,0"
        "M 7.5 35 a 2.5,2.5, 0 1,0 1,0"
        "M 17.5 52.5 a 2.5,2.5, 0 1,0 1,0"
        "M 7.5 70 a 2.5,2.5, 0 1,0 1,0"
        "M 62.5 17.5 a 2.5,2.5, 0 1,0 1,0"
        "M 52.5 35 a 2.5,2.5, 0 1,0 1,0"
        "M 62.5 52.5 a 2.5,2.5, 0 1,0 1,0"
        "M 52.5 70 a 2.5,2.5, 0 1,0 1,0",
    ),
)

icon_canvas = VectorIcon(
    fill=(),
    stroke=(
        "M 60 5 h 40 v 60 h -100 v -60 h 40",
        "M 40 0 h 20 v 10 h -20 v -10",
        "M 30 65 v 5 h 40 v -5",
        "M 30 90 L 40 70",
        "M 70 90 L 60 70",
        "M 50 90 v -20",
    ),
)

icon_duplicate = VectorIcon(
    fill=(),
    stroke=(
        "M 0 20 h 60 v 80 h -60 v -80",
        "M 30 10 h 60 v 80 h -20" "M 20 60 h 20",
        "M 30 50 v 20",
    ),
)

icon_crossing_star = VectorIcon(
    fill=(),
    stroke=(
        "M 128.341,145.628 L 108.983,209.299 L 162.069,169.166 L 95.532,170.431 L 150.105,208.517 L 128.341,145.628"
    ),
)

icon_regular_star = VectorIcon(
    fill=(),
    stroke=(
        "M 232.999,128.821 L 240.176,162.177 L 269.387,144.547 L 250.876,173.208 L 283.998,181.397"
        " L 250.642,188.574 L 268.272,217.785 L 239.611,199.274 L 231.428,232.395 L 224.245,199.040"
        " L 195.034,216.669 L 213.545,188.009 L 180.424,179.819 L 213.779,172.643 L 196.150,143.432"
        " L 224.810,161.943 L 232.999,128.821"
    ),
)

icon_polygon = VectorIcon(
    fill=(),
    stroke=(
        "M 155.460,171.601 L 188.113,196.274 L 174.738,234.953 L 133.818,234.185 L 121.904,195.031 L 155.460,171.601",
    ),
)

icon_growing = VectorIcon(
    fill=(),
    stroke=(
        "M 50,50 h 10 v 15 h -20 v -25 h 30 v 35 h -40 v -45 h 50 v 55 h -60 v -65 h 70 v 75",
    ),
    edge=5,
)

icons8_menu = VectorIcon(
    fill=(
        "M 0 0 h 50 v2 h -50 z",
        "M 0 20 h 50 v2 h -50 z",
        "M 0 40 h 50 v2 h -50 z",
    ),
    stroke=(),
)

icon_instruct_circle = VectorIcon(
    fill=(
        "M 55 0 a 5,5, 0 1,0 1,0",
        "M 5 50 a 5,5, 0 1,0 1,0",
        "M 96 80 a 5,5, 0 1,0 1,0",
    ),
    stroke=(
        "M 55 5 a 50,50, 0 1,0 1,0",
        # A
        "M 55 15 L 50 25",
        "M 55 15 L 60 25",
        "M 53 21 h 6",
        # B
        "M 15 50 v 10",
        "M 15 50 C 22.5,50 22.5,55 15,55 C 25,55 25,60 15,60"
        # C
        "M 85 80 C 75,80 75,90 85,90",
    ),
)

icon_instruct_rect = VectorIcon(
    fill=(
        "M 5 0 a 5,5, 0 1,0 1,0",
        "M 100 75 a 5,5, 0 1,0 1,0",
    ),
    stroke=(
        "M 5 5 h 95 v 75 h -95 z",
        # A
        "M 15 15 L 10 25",
        "M 15 15 L 20 25",
        "M 13 21 h 6",
        # B
        "M 75 60 v 10",
        "M 75 60 C 82.5,60 82.5,65 75,65 C 85,65 85,70 75,70",
    ),
)

icon_instruct_square = VectorIcon(
    fill=(
        "M 15 70 a 5,5, 0 1,0 1,0",
        "M 50 80 a 5,5, 0 1,0 1,0",
        "M 77.5 60 a 5,5, 0 1,0 1,0",
    ),
    stroke=(
        "M 0 50 L 30 100 L 100 50 L 70 0 z",
        # B
        "M 20 60 v 10",
        "M 20 60 C 27.5,60 27.5,65 20,65 C 30,65 30,70 20,70"
        # A
        "M 50 65 L 45 75",
        "M 50 65 L 55 75",
        "M 48 71 h 6",
        # 1
        "M 60 75 L 60 65 L 57 68",
        # A
        "M 70 45 L 65 55",
        "M 70 45 L 75 55",
        "M 68 51 h 6",
        # 2
        "M 79 45 h 5 v 5 h -5 v 5 h 5",
    ),
)

icon_points = VectorIcon(
    fill=(
        "M 15 8 a 4,4, 0 1,0 1,0",
        "M 15 28 a 4,4, 0 1,0 1,0",
        "M 35 8 a 4,4 0 1,0 1,0",
        "M 50 28 a 4,4, 0 1,0 1,0",
        "M 30 48 a 4,4, 0 1,0 1,0",
        "M 50 48 a 4,4, 0 1,0 1,0",
    ),
    stroke=("M 0 60 v -60 h 60",),
)

icon_timer = VectorIcon(
    fill=(),
    stroke=(
        "M 4.51555 7 C 3.55827 8.4301 3 10.1499 3 12 C 3 16.9706 7.02944 21 12 21 C 16.9706 21 21 16.9706 21 12 C 21 7.02944 16.9706 3 12 3 V 6 M 12 12 L8 8",
    ),
)

icon_return = VectorIcon(
    fill=(),
    stroke=(
        "M 12.9998 8 L 6 14 L 12.9998 21",
        "M 6 14 H 28.9938 C 35.8768 14 41.7221 19.6204 41.9904 26.5 C 42.2739 33.7696 36.2671 40 28.9938 40 H 11.9984",
    ),
)

icon_console = VectorIcon(
    fill=(),
    stroke=(
        "M 4 26.016 q 0 0.832 0.576 1.408 t 1.44 0.576 h 20 q 0.8 0 1.408-0.576 t 0.576-1.408 v -20 q 0 -0.832 -0.576 -1.408 t -1.408 -0.608 h -20 q -0.832 0 -1.44 0.608 t -0.576 1.408 v 20z",
        "M 8 8 L 12 12 L 8 16",
        "M 13 18 h 8",
    ),
)

icon_external = VectorIcon(
    fill=(),
    stroke=(
        "M 20 10 h -20 v 40 h 40 v -20",
        "M 20 30 L 45 5",
        "M 35 5 h 10 v 10",
    ),
)

icon_internal = VectorIcon(
    fill=(),
    stroke=(
        "M 20 10 h -20 v 40 h 40 v -20",
        "M 20 30 L 45 5",
        "M 20 20 v 10 h 10",
    ),
)

icon_warning = VectorIcon(
    fill=(
        "[yellow]M 32, 9 l 23, 45 h -46 l 23, -45 Z",
        "[red]M32.427,7.987c2.183,0.124 4,1.165 5.096,3.281l17.936,36.208c1.739,3.66 -0.954,8.585 -5.373,8.656l-36.119,0c-4.022,-0.064 -7.322,-4.631 -5.352,-8.696l18.271,-36.207c0.342,-0.65 0.498,-0.838 0.793,-1.179c1.186,-1.375 2.483,-2.111 4.748,-2.063Zm-0.295,3.997c-0.687,0.034 -1.316,0.419 -1.659,1.017c-6.312,11.979 -12.397,24.081 -18.301,36.267c-0.546,1.225 0.391,2.797 1.762,2.863c12.06,0.195 24.125,0.195 36.185,0c1.325,-0.064 2.321,-1.584 1.769,-2.85c-5.793,-12.184 -11.765,-24.286 -17.966,-36.267c-0.366,-0.651 -0.903,-1.042 -1.79,-1.03Z",
        "[red]M33.631,40.581l-3.348,0l-0.368,-16.449l4.1,0l-0.384,16.449Zm-3.828,5.03c0,-0.609 0.197,-1.113 0.592,-1.514c0.396,-0.4 0.935,-0.601 1.618,-0.601c0.684,0 1.223,0.201 1.618,0.601c0.395,0.401 0.593,0.905 0.593,1.514c0,0.587 -0.193,1.078 -0.577,1.473c-0.385,0.395 -0.929,0.593 -1.634,0.593c-0.705,0 -1.249,-0.198 -1.634,-0.593c-0.384,-0.395 -0.576,-0.886 -0.576,-1.473Z",
    ),
    stroke=(),
)

icon_marker = VectorIcon(
    fill=(),
    stroke=(
        "M12 13C13.6569 13 15 11.6569 15 10C15 8.34315 13.6569 7 12 7C10.3431 7 9 8.34315 9 10C9 11.6569 10.3431 13 12 13Z",
        "M12 22C16 18 20 14.4183 20 10C20 5.58172 16.4183 2 12 2C7.58172 2 4 5.58172 4 10C4 14.4183 8 18 12 22Z",
    ),
)

icon_line = VectorIcon(
    fill=(
        "M 5 0 a 5,5, 0 1,0 1,0",
        "M 45 45 a 5,5, 0 1,0 1,0",
    ),
    stroke=("M 5 5 L 45 50",),
)

icon_path = VectorIcon(
    fill=(
        "M 5 0 a 5,5, 0 1,0 1,0",
        "M 30 40 a 5,5, 0 1,0 1,0",
    ),
    stroke="M 10 5 h 20 C 40 5 40 25 30 25 h -20 C 0 25 0 45 10 45 h 20",
)

icon_add_new = VectorIcon(
    fill=(),
    stroke=("M 0 0 h 40 v 40 h -40 z", "M 20 10 v 20 M 10 20 h 20"),
)

icon_trash = VectorIcon(
    fill=(),
    stroke=(
        "M 4 6 H 20",
        "M 16 6 L 15.7294 5.18807 C 15.4671 4.40125 15.3359 4.00784 15.0927 3.71698 C 14.8779 3.46013 14.6021 3.26132 14.2905 3.13878 C 13.9376 3 13.523 3 12.6936 3 H 11.3064 C 10.477 3 10.0624 3 9.70951 3.13878 C 9.39792 3.26132 9.12208 3.46013 8.90729 3.71698 C 8.66405 4.00784 8.53292 4.40125 8.27064 5.18807 L 8 6",
        "M 18 6 V 16.2 C 18 17.8802 18 18.7202 17.673 19.362 C 17.3854 19.9265 16.9265 20.3854 16.362 20.673 C 15.7202 21 14.8802 21 13.2 21 H 10.8 C 9.11984 21 8.27976 21 7.63803 20.673 C 7.07354 20.3854 6.6146 19.9265 6.32698 19.362 C 6 18.7202 6 17.8802 6 16.2 V 6",
        "M 14 10 V 17",
        "M 10 10 V 17",
    ),
)

icon_round_stop = VectorIcon(
    fill=("M 30 30 h 40 v 40 h -40 Z",),
    stroke=("M 50 0 a 50,50, 0 1,0 1,0",),
    strokewidth=5,
)

icon_bell = VectorIcon(
    fill=(),
    stroke=(
        "M9.00195 17H5.60636C4.34793 17 3.71872 17 3.58633 16.9023C3.4376 16.7925 3.40126 16.7277 3.38515 16.5436C3.37082 16.3797 3.75646 15.7486 4.52776 14.4866C5.32411 13.1835 6.00031 11.2862 6.00031 8.6C6.00031 7.11479 6.63245 5.69041 7.75766 4.6402C8.88288 3.59 10.409 3 12.0003 3C13.5916 3 15.1177 3.59 16.2429 4.6402C17.3682 5.69041 18.0003 7.11479 18.0003 8.6C18.0003 11.2862 18.6765 13.1835 19.4729 14.4866C20.2441 15.7486 20.6298 16.3797 20.6155 16.5436C20.5994 16.7277 20.563 16.7925 20.4143 16.9023C20.2819 17 19.6527 17 18.3943 17H15.0003",
        "M9.00195 17L9.00031 18C9.00031 19.6569 10.3435 21 12.0003 21C13.6572 21 15.0003 19.6569 15.0003 18V17",
        "M9.00195 17H15.0003",
    ),
)

icon_close_window = VectorIcon(
    fill=(),
    stroke=(
        "M 0 0 h 40 v 40 h -40 z",
        "M 10 10 L 30 30",
        "M 30 10 L 10 30",
    ),
)

icon_edit = VectorIcon(
    fill=(),
    stroke=(
        "M 18 10 L 21 7 L 17 3 L 14 6",
        "M 18 10 L 8 20 H 4 V 16 L 14 6",
        "M 18 10 L 14 6",
    ),
)

icon_tree = VectorIcon(
    fill=(),
    stroke=(
        "M 0 0 h 10 v 10 h -10 z",
        "M 30 20 h 10 v 10 h -10 z",
        "M 30 40 h 10 v 10 h -10 z",
        "M 5 10 v 35 h 25",
        "M 5 25 h 25",
    ),
)

icon_rotary = VectorIcon(
    fill=(),
    stroke=(
        "M 17.8 21 H 22 v 1 h -6 v -6 h 1 v 4.508 a 9.861 9.861 0 1 0-5 1.373 v .837 A 10.748 10.748 0 1 1 17.8 21z",
        "M 11 11 v 2 h 2 v -2 z",
    ),
)

icon_magic_wand = VectorIcon(
    fill=(),
    stroke=(
        "M31.891 13.418l-3.212-4.802 1.599-5.588c0.099-0.35 0.002-0.728-0.257-0.985-0.258-0.258-0.633-0.353-0.986-0.251l-5.578 1.629-4.822-3.247c-0.303-0.204-0.692-0.229-1.014-0.061-0.324 0.166-0.532 0.496-0.544 0.859l-0.173 5.811-4.578 3.581c-0.287 0.225-0.428 0.588-0.371 0.947s0.306 0.659 0.65 0.782l4.296 1.54c-0.029 0.023-0.059 0.044-0.087 0.071l-16.586 16.586c-0.391 0.39-0.391 1.023 0 1.414 0.196 0.195 0.451 0.293 0.707 0.293s0.511-0.098 0.707-0.293l16.586-16.586c0.064-0.065 0.114-0.137 0.157-0.213l1.681 4.611c0.125 0.342 0.426 0.589 0.786 0.645 0.051 0.008 0.102 0.012 0.154 0.012 0.306 0 0.599-0.142 0.791-0.389l3.555-4.599 5.747-0.205c0.364-0.012 0.692-0.223 0.858-0.548s0.139-0.714-0.066-1.015z",
    ),
    strokewidth=1,
)

icon_about = VectorIcon(
    fill=(
        "M26,52A26,26,0,0,1,22.88.19,25.78,25.78,0,0,1,34.73,1.5a2,2,0,1,1-1.35,3.77,22,22,0,0,0-21,38,22,22,0,0,0,35.41-20,2,2,0,1,1,4-.48A26,26,0,0,1,26,52Z"
        "M26,43.86a2,2,0,0,1-2-2V22.66a2,2,0,1,1,4,0v19.2A2,2,0,0,1,26,43.86Z",
        "M 26 13.44 a 2.57,2.57, 0 1,0 1,0",
    ),
)


icon_fill_evenodd = VectorIcon(
    fill=(
        "[fill_evenodd]M 1105,339 C 1115.397,339 1117.885,319 1111.421,319 1104.873,319 1094.578,335.0032 1105.037,335.0032 1115.363,335.0032 1105.127,319 1098.605,319 1092.082,319 1094.42,339 1105,339 Z",
    ),
    stroke=(),
)

icon_fill_nonzero = VectorIcon(
    fill=(
        "[fill_nonzero]M 1135,339 C 1145.397,339 1147.885,319 1141.421,319 1134.873,319 1124.578,335.0031 1135.037,335.0031 1145.363,335.0031 1135.127,319 1128.605,319 1122.082,319 1124.42,339 1135,339 Z",
    ),
    stroke=(),
)

icon_cap_butt = VectorIcon(
    fill=("m 3.5,24 0,-14.5 17,0 0,14.5",), stroke="[red,cap_butt]m 12,24 0,-14"
)

icon_cap_round = VectorIcon(
    fill=("m 3.5,24 0,-14.5 a 8.5,8.5 0 0 1 17,0 l 0,14.5",),
    stroke="[red,cap_butt]m 12,24 0,-14",
)

icon_cap_square = VectorIcon(
    fill=("m 3.5,24 0,-23.5 17,0 0,23.5",), stroke="[red,cap_butt]m 12,24 0,-14"
)

icon_join_bevel = VectorIcon(
    fill=("m 0.5,24 0,-13 10.5,-10.5 13,0   0,17 -6.5,0 0,6.5 z",),
    stroke=(
        "m 0.5,24 0,-13 10.5,-10.5 13,0 m 0,17 -6.5,0 0,6.5  ",
        "[red]m 9,24 0,-15 15,0",
    ),
)

icon_join_miter = VectorIcon(
    fill=("m 0.5,24 0,-23.5 23.5,0   0,17 -6.5,0 0,6.5 z",),
    stroke=("m 0.5,24 0,-23.5 23.5,0 m 0,17 -6.5,0 0,6.5", "[red]m 9,24 0,-15 15,0"),
)

icon_join_round = VectorIcon(
    fill=("m 0.5,24 0,-11 a 12.5,12.5 0 0 1 12.5,-12.5 l 11,0   0,17 -6.5,0 0,6.5 z",),
    stroke=(
        "m 0.5,24 0,-11 a 12.5,12.5 0 0 1 12.5,-12.5 l 11,0 m 0,17 -6.5,0 0,6.5",
        "[red]m 9,24 0,-15 15,0",
    ),
)

icon_kerf = VectorIcon(
    fill=(),
    stroke=(
        "m 41.079941,10.060393 0.209589,15.300182 27.875675,0.209591 0.209591,9.222029 -7.335704,-10e-7 -0.20959,26.198941 15.719363,-10e-7 10e-7,38.879228 -6.497338,0.419178 0.104795,9.74601 c 0,0 39.298407,0.52398 38.879227,-0.31439 -0.41918,-0.83836 -0.31439,-9.53641 -0.31439,-9.53641 l -5.76376,-0.209592 -0.20959,-27.456489",
        "M 140.42632,10.060393 V 25.570166 H 79.644781",
        "m 112.55065,25.150983 -0.20959,9.850801 7.75489,0.209593 v 25.150984 l -42.756676,0.628774",
        "M 62.248684,46.73891 H 119.88636",
        "m 68.955612,34.792195 43.490248,0.20959",
        "m 78.282435,110.24515 0.104798,8.80284 24.312617,0.20959 0.1048,-8.69805",
        "M 133.5098,113.38902 120.30554,128.6892",
        "m 128.47961,130.9947 14.881,-5.86856",
        "m 187.79401,142.73183 -86.98049,-0.41918 -0.62877,24.10302 88.65722,0.2096",
        "m -7.9644781,142.31265 88.0284411,0.20959 0.419185,22.84548 -87.1900769,0.62877",
        "M 68.326838,188.63238 82.159879,176.89525",
        "m 87.818851,176.89525 -3.982239,14.67141",
        "m 93.687412,176.68566 5.449382,14.881",
        "m 99.136794,174.79933 14.252226,13.41386",
        "M 91.381907,164.63414 91.172315,134.76735",
        "M 62.248684,129.31797 C 60.781543,128.06042 47.577277,113.59861 47.577277,113.59861",
        "M 53.865023,131.2043 38.355251,124.49737",
        "m 86.246914,119.46717 c 0,0 -0.368821,8.75297 -0.104797,11.52753 0.201722,2.11984 2.692579,4.11493 4.820605,4.19183 1.745456,0.0631 4.004355,-1.40737 4.191831,-3.14387 0.407704,-3.77637 0.209592,-12.3659 0.209592,-12.3659",
    ),
)

icon_power_button = VectorIcon(
    fill=(
        "[yellow]M262 -10 a 280,280, 0 1,0 1,0",
        "[red]M228.576 26.213v207.32h54.848V26.214h-54.848zm-28.518 45.744C108.44 96.58 41 180.215 41 279.605c0 118.74 96.258 215 215 215 118.74 0 215-96.26 215-215 0-99.39-67.44-183.025-159.057-207.647v50.47c64.6 22.994 110.85 84.684 110.85 157.177 0 92.117-74.676 166.794-166.793 166.794-92.118 0-166.794-74.678-166.794-166.795 0-72.494 46.25-134.183 110.852-157.178v-50.47z",
    ),
    stroke=(),
)

icon_youtube = VectorIcon(
    fill=(
        "[red]M27.9727 3.12324C27.6435 1.89323 26.6768 0.926623 25.4468 0.597366C23.2197 2.24288e-07 14.285 0 14.285 0C14.285 0 5.35042 2.24288e-07 3.12323 0.597366C1.89323 0.926623 0.926623 1.89323 0.597366 3.12324C2.24288e-07 5.35042 0 10 0 10C0 10 2.24288e-07 14.6496 0.597366 16.8768C0.926623 18.1068 1.89323 19.0734 3.12323 19.4026C5.35042 20 14.285 20 14.285 20C14.285 20 23.2197 20 25.4468 19.4026C26.6768 19.0734 27.6435 18.1068 27.9727 16.8768C28.5701 14.6496 28.5701 10 28.5701 10C28.5701 10 28.5677 5.35042 27.9727 3.12324Z",
        "[white]M11.4253 14.2854L18.8477 10.0004L11.4253 5.71533V14.2854Z",
        "M34.6024 13.0036L31.3945 1.41846H34.1932L35.3174 6.6701C35.6043 7.96361 35.8136 9.06662 35.95 9.97913H36.0323C36.1264 9.32532 36.3381 8.22937 36.665 6.68892L37.8291 1.41846H40.6278L37.3799 13.0036V18.561H34.6001V13.0036H34.6024Z",
        "M41.4697 18.1937C40.9053 17.8127 40.5031 17.22 40.2632 16.4157C40.0257 15.6114 39.9058 14.5437 39.9058 13.2078V11.3898C39.9058 10.0422 40.0422 8.95805 40.315 8.14196C40.5878 7.32588 41.0135 6.72851 41.592 6.35457C42.1706 5.98063 42.9302 5.79248 43.871 5.79248C44.7976 5.79248 45.5384 5.98298 46.0981 6.36398C46.6555 6.74497 47.0647 7.34234 47.3234 8.15137C47.5821 8.96275 47.7115 10.0422 47.7115 11.3898V13.2078C47.7115 14.5437 47.5845 15.6161 47.3329 16.4251C47.0812 17.2365 46.672 17.8292 46.1075 18.2031C45.5431 18.5771 44.7764 18.7652 43.8098 18.7652C42.8126 18.7675 42.0342 18.5747 41.4697 18.1937ZM44.6353 16.2323C44.7905 15.8231 44.8705 15.1575 44.8705 14.2309V10.3292C44.8705 9.43077 44.7929 8.77225 44.6353 8.35833C44.4777 7.94206 44.2026 7.7351 43.8074 7.7351C43.4265 7.7351 43.156 7.94206 43.0008 8.35833C42.8432 8.77461 42.7656 9.43077 42.7656 10.3292V14.2309C42.7656 15.1575 42.8408 15.8254 42.9914 16.2323C43.1419 16.6415 43.4123 16.8461 43.8074 16.8461C44.2026 16.8461 44.4777 16.6415 44.6353 16.2323Z",
        "M56.8154 18.5634H54.6094L54.3648 17.03H54.3037C53.7039 18.1871 52.8055 18.7656 51.6061 18.7656C50.7759 18.7656 50.1621 18.4928 49.767 17.9496C49.3719 17.4039 49.1743 16.5526 49.1743 15.3955V6.03751H51.9942V15.2308C51.9942 15.7906 52.0553 16.188 52.1776 16.4256C52.2999 16.6631 52.5045 16.783 52.7914 16.783C53.036 16.783 53.2712 16.7078 53.497 16.5573C53.7228 16.4067 53.8874 16.2162 53.9979 15.9858V6.03516H56.8154V18.5634Z",
        "M64.4755 3.68758H61.6768V18.5629H58.9181V3.68758H56.1194V1.42041H64.4755V3.68758Z",
        "M71.2768 18.5634H69.0708L68.8262 17.03H68.7651C68.1654 18.1871 67.267 18.7656 66.0675 18.7656C65.2373 18.7656 64.6235 18.4928 64.2284 17.9496C63.8333 17.4039 63.6357 16.5526 63.6357 15.3955V6.03751H66.4556V15.2308C66.4556 15.7906 66.5167 16.188 66.639 16.4256C66.7613 16.6631 66.9659 16.783 67.2529 16.783C67.4974 16.783 67.7326 16.7078 67.9584 16.5573C68.1842 16.4067 68.3488 16.2162 68.4593 15.9858V6.03516H71.2768V18.5634Z",
        "M80.609 8.0387C80.4373 7.24849 80.1621 6.67699 79.7812 6.32186C79.4002 5.96674 78.8757 5.79035 78.2078 5.79035C77.6904 5.79035 77.2059 5.93616 76.7567 6.23014C76.3075 6.52412 75.9594 6.90747 75.7148 7.38489H75.6937V0.785645H72.9773V18.5608H75.3056L75.5925 17.3755H75.6537C75.8724 17.7988 76.1993 18.1304 76.6344 18.3774C77.0695 18.622 77.554 18.7443 78.0855 18.7443C79.038 18.7443 79.7412 18.3045 80.1904 17.4272C80.6396 16.5476 80.8653 15.1765 80.8653 13.3092V11.3266C80.8653 9.92722 80.7783 8.82892 80.609 8.0387ZM78.0243 13.1492C78.0243 14.0617 77.9867 14.7767 77.9114 15.2941C77.8362 15.8115 77.7115 16.1808 77.5328 16.3971C77.3564 16.6158 77.1165 16.724 76.8178 16.724C76.585 16.724 76.371 16.6699 76.1734 16.5594C75.9759 16.4512 75.816 16.2866 75.6937 16.0702V8.96062C75.7877 8.6196 75.9524 8.34209 76.1852 8.12337C76.4157 7.90465 76.6697 7.79646 76.9401 7.79646C77.2271 7.79646 77.4481 7.90935 77.6034 8.13278C77.7609 8.35855 77.8691 8.73485 77.9303 9.26636C77.9914 9.79787 78.022 10.5528 78.022 11.5335V13.1492H78.0243Z",
        "M84.8657 13.8712C84.8657 14.6755 84.8892 15.2776 84.9363 15.6798C84.9833 16.0819 85.0821 16.3736 85.2326 16.5594C85.3831 16.7428 85.6136 16.8345 85.9264 16.8345C86.3474 16.8345 86.639 16.6699 86.7942 16.343C86.9518 16.0161 87.0365 15.4705 87.0506 14.7085L89.4824 14.8519C89.4965 14.9601 89.5035 15.1106 89.5035 15.3011C89.5035 16.4582 89.186 17.3237 88.5534 17.8952C87.9208 18.4667 87.0247 18.7536 85.8676 18.7536C84.4777 18.7536 83.504 18.3185 82.9466 17.446C82.3869 16.5735 82.1094 15.2259 82.1094 13.4008V11.2136C82.1094 9.33452 82.3987 7.96105 82.9772 7.09558C83.5558 6.2301 84.5459 5.79736 85.9499 5.79736C86.9165 5.79736 87.6597 5.97375 88.1771 6.32888C88.6945 6.684 89.059 7.23433 89.2707 7.98457C89.4824 8.7348 89.5882 9.76961 89.5882 11.0913V13.2362H84.8657V13.8712ZM85.2232 7.96811C85.0797 8.14449 84.9857 8.43377 84.9363 8.83593C84.8892 9.2381 84.8657 9.84722 84.8657 10.6657V11.5641H86.9283V10.6657C86.9283 9.86133 86.9001 9.25221 86.846 8.83593C86.7919 8.41966 86.6931 8.12803 86.5496 7.95635C86.4062 7.78702 86.1851 7.7 85.8864 7.7C85.5854 7.70235 85.3643 7.79172 85.2232 7.96811Z",
    ),
    stroke=(),
)

icon_balor_regmarks = VectorIcon(
    fill=(),
    stroke=(
        "[150%]M 10 70 L 70 10 L 120 60 L 60 120 L 10 70",
        "[150%]M 10 70 L 120 60 M 70 10 L 60 120",
        "[red,125%]M 10 70 l 10 -10 m 10 -10 l 10 -10 m 10 -10 l 10 -10 m 10 -10",
        "[red,125%]M 70 10 l 10 10 m 10 10 l 10 10 m 10 10 l 10 10",
        "[red,125%]M 60 120 l 10 -10 m 10 -10 l 10 -10 m 10 -10 l 10 -10 m 10 -10",
        "[red,125%]M 10 70 l 10 10 m 10 10 l 10 10 m 10 10 l 10 10",
        "[red,125%]M 10 70 m 22 -2 l 22 -2 m 22 -2 l 22 -2",
        "[red,125%]M 70 10 m -2 22 l -2 22 m -2 22 l -2 22",
        "[red,125%]M 100 90 v 30 M 100 90 C 120 90 120 105 100 105 M 105 105 L 115 120",
    ),
    edge=5,
)

icon_balor_full = VectorIcon(
    fill=(),
    stroke=(
        "[150%]M 10 70 L 70 10 L 120 60 L 60 120 L 10 70",
        "[150%]M 10 70 L 120 60 M 70 10 L 60 120",
        "[red,125%]M 10 70 l 10 -10 m 10 -10 l 10 -10 m 10 -10 l 10 -10 m 10 -10",
        "[red,125%]M 70 10 l 10 10 m 10 10 l 10 10 m 10 10 l 10 10",
        "[red,125%]M 60 120 l 10 -10 m 10 -10 l 10 -10 m 10 -10 l 10 -10 m 10 -10",
        "[red,125%]M 10 70 l 10 10 m 10 10 l 10 10 m 10 10 l 10 10",
        "[red,125%]M 10 70 m 22 -2 l 22 -2 m 22 -2 l 22 -2",
        "[red,125%]M 70 10 m -2 22 l -2 22 m -2 22 l -2 22",
    ),
    edge=5,
)

icon_balor_hull = VectorIcon(
    fill=(),
    stroke=(
        "[150%]M 10 70 L 70 10 L 120 60 L 60 120 L 10 70",
        "[150%]M 10 70 L 120 60 M 70 10 L 60 120",
        "[red,125%]M 10 70 l 10 -10 m 10 -10 l 10 -10 m 10 -10 l 10 -10 m 10 -10",
        "[red,125%]M 70 10 l 10 10 m 10 10 l 10 10 m 10 10 l 10 10",
        "[red,125%]M 60 120 l 10 -10 m 10 -10 l 10 -10 m 10 -10 l 10 -10 m 10 -10",
        "[red,125%]M 10 70 l 10 10 m 10 10 l 10 10 m 10 10 l 10 10",
    ),
    edge=5,
)

icon_balor_bounds = VectorIcon(
    fill=(),
    stroke=(
        "[150%]M 10 70 L 70 10 L 120 60 L 60 120 L 10 70",
        "[150%]M 10 70 L 120 60 M 70 10 L 60 120",
        "[red,125%]M 10 10 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0",
        "[red,125%]M 120 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10",
        "[red,125%]M 10 120 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0 l 10 0 m 10 0",
        "[red,125%]M 10 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10 l 0 10 m 0 10",
    ),
    edge=5,
)

icon_outline = VectorIcon(
    fill=(),
    stroke=(
        "M 258.011,154.807 h 51.602 v 51.602 h -51.602 z",
        "M 283.812,180.608 h 51.602 v 51.602 h -51.602 z",
        "[red]M 287.542,237.895 L 281.972,237.816 L 281.216,237.445 C 280.223,236.957 279.324,236.064 278.687,234.932 L 278.171,234.015 L 278.126,223.169 L 278.081,212.322 L 268.820,212.318"
        "C 258.062,212.312 256.450,212.241 255.342,211.716 C 254.389,211.266 253.517,210.400 252.897,209.291 L 252.416,208.431 L 252.418,180.722 L 252.421,153.013 L 252.849,152.184"
        "C 253.662,150.612 254.989,149.585 256.605,149.279 C 257.567,149.096 310.049,149.097 311.019,149.280 C 312.695,149.595 314.073,150.692 314.867,152.341"
        "L 315.329,153.303 L 315.329,164.049 L 315.329,174.794 L 325.913,174.874 C 336.003,174.950 336.536,174.966 337.338,175.216"
        "C 338.936,175.714 340.096,176.785 340.827,178.439 L 341.157,179.185 L 341.121,206.469 L 341.084,233.752"
        "L 340.790,234.473 C 340.181,235.967 338.996,237.116 337.519,237.644 C 336.763,237.914 336.647,237.916 314.936,237.945 C 302.933,237.962 290.606,237.939 287.542,237.895 L 287.542,237.895",
    ),
    edge=5,
)
icon_library = VectorIcon(
    stroke=(
        "M 0,0 h 36 v 36 h -36 Z",
        "M33.48,29.63,26.74,11.82a2,2,0,0,0-2.58-1.16L21,11.85V8.92A1.92,1.92,0,0,0,19.08,7H14V4.92A1.92,1.92,0,0,0,12.08,3H5A2,2,0,0,0,3,5V32a1,1,0,0,0,1,1H20a1,1,0,0,0,1-1V19.27l5,13.21a1,1,0,0,0,1.29.58l5.61-2.14a1,1,0,0,0,.58-1.29Z",
        "M12,8.83V31H5V5h7Z",
        "M19,31H14V9h5Zm8.51-.25L21.13,13.92l3.74-1.42,6.39,16.83Z",
    ),
    fill=(),
    strokewidth=1,
)

icon_paint_brush = VectorIcon(
    fill=(),
    stroke=(
        "M 223.754,317.144 L 295.271,245.627 L 233.971,184.326 L 285.055,133.243 L 468.956,317.144 L 417.873,368.228 L 356.572,306.927 L 285.055,378.445 L 244.188,378.445 L 223.754,358.011 L 223.754,317.144",
        "M 280.194,337.386 C 280.194,334.311 279.384,331.291 277.847,328.628 C 276.310,325.966 274.098,323.754 271.436,322.217 C 268.773,320.680 265.753,319.871 262.678,319.871 C 259.604,319.871 256.583,320.680 253.921,322.217 C 251.258,323.754 249.047,325.966 247.510,328.628 C 245.972,331.291 245.163,334.311 245.163,337.386 C 245.163,340.460 245.972,343.481 247.510,346.143 C 249.047,348.806 251.258,351.017 253.921,352.554 C 256.583,354.092 259.604,354.901 262.678,354.901 C 265.753,354.901 268.773,354.092 271.436,352.554 C 274.098,351.017 276.310,348.806 277.847,346.143 C 279.384,343.481 280.194,340.460 280.194,337.386",
        "M 305.488,153.676 L 407.656,51.509 L 478.575,122.823 L 433.996,193.918 L 525.230,168.520 L 550.690,194.543 L 448.523,296.711",
        "M 551.629,216.730 C 542.599,231.173 520.205,258.130 515.507,274.503 C 513.977,279.838 513.384,291.574 515.507,296.701 C 518.370,303.612 529.753,314.995 536.663,317.857 C 543.576,320.721 559.682,320.721 566.595,317.857 C 573.505,314.995 584.888,303.612 587.751,296.701 C 589.874,291.574 589.281,279.838 587.751,274.503 C 583.053,258.130 560.659,231.173 551.629,216.730",
        "M 525.230,168.520 L 450.372,247.589",
        "M 431.325,75.576 L 356.466,154.645",
        "M 457.526,102.244 L 382.667,181.313",
    ),
    strokewidth=10,
)

icon_paint_brush_green = VectorIcon(
    fill=(),
    stroke=(
        "[green]M 223.754,317.144 L 295.271,245.627 L 233.971,184.326 L 285.055,133.243 L 468.956,317.144 L 417.873,368.228 L 356.572,306.927 L 285.055,378.445 L 244.188,378.445 L 223.754,358.011 L 223.754,317.144",
        "[green]M 280.194,337.386 C 280.194,334.311 279.384,331.291 277.847,328.628 C 276.310,325.966 274.098,323.754 271.436,322.217 C 268.773,320.680 265.753,319.871 262.678,319.871 C 259.604,319.871 256.583,320.680 253.921,322.217 C 251.258,323.754 249.047,325.966 247.510,328.628 C 245.972,331.291 245.163,334.311 245.163,337.386 C 245.163,340.460 245.972,343.481 247.510,346.143 C 249.047,348.806 251.258,351.017 253.921,352.554 C 256.583,354.092 259.604,354.901 262.678,354.901 C 265.753,354.901 268.773,354.092 271.436,352.554 C 274.098,351.017 276.310,348.806 277.847,346.143 C 279.384,343.481 280.194,340.460 280.194,337.386",
        "[green]M 305.488,153.676 L 407.656,51.509 L 478.575,122.823 L 433.996,193.918 L 525.230,168.520 L 550.690,194.543 L 448.523,296.711",
        "[green]M 551.629,216.730 C 542.599,231.173 520.205,258.130 515.507,274.503 C 513.977,279.838 513.384,291.574 515.507,296.701 C 518.370,303.612 529.753,314.995 536.663,317.857 C 543.576,320.721 559.682,320.721 566.595,317.857 C 573.505,314.995 584.888,303.612 587.751,296.701 C 589.874,291.574 589.281,279.838 587.751,274.503 C 583.053,258.130 560.659,231.173 551.629,216.730",
        "[green]M 525.230,168.520 L 450.372,247.589",
        "[green]M 431.325,75.576 L 356.466,154.645",
        "[green]M 457.526,102.244 L 382.667,181.313",
    ),
    strokewidth=10,
)

icon_textsize_down = VectorIcon(
    stroke=(),
    fill=(
        "M 33.6585,44.381L 24.397,44.381L 22.0936,52.9919L 14.5596,52.9919L 24.397,21L 33.9944,21L 42.31,47.4041L 47.7438,29.9832L 54.7237,29.9832L 62.0513,53L 56.2942,53L 54.4794,46.7375L 47.7438,46.7375L 46.0686,53L 36.1538,52.9919L 33.6585,44.381 ZM 25.4527,39.1786L 32.6028,39.1786L 30.5873,32.3811L 29.7355,29.2915L 28.9557,26.2024L 28.8598,26.2024L 28.134,29.3193L 27.3722,32.4615L 25.4527,39.1786 ZM 48.5116,42.954L 53.7116,42.954L 52.2458,38.0104L 51.6264,35.7634L 51.0592,33.5168L 50.9894,33.5168L 50.4616,35.7836L 49.9075,38.0688L 48.5116,42.954 Z",
        "M 45,21L 57,21L 51,27L 45,21 Z",
    ),
)

icon_textsize_up = VectorIcon(
    stroke=(),
    fill=(
        "M 33.6585,44.381L 24.397,44.381L 22.0936,52.9919L 14.5596,52.9919L 24.397,21L 33.9944,21L 42.31,47.4041L 47.7438,29.9832L 54.7237,29.9832L 62.0513,53L 56.2942,53L 54.4794,46.7375L 47.7438,46.7375L 46.0686,53L 36.1538,52.9919L 33.6585,44.381 ZM 25.4527,39.1786L 32.6028,39.1786L 30.5873,32.3811L 29.7355,29.2915L 28.9557,26.2024L 28.8598,26.2024L 28.134,29.3193L 27.3722,32.4615L 25.4527,39.1786 ZM 48.5116,42.954L 53.7116,42.954L 52.2458,38.0104L 51.6264,35.7634L 51.0592,33.5168L 50.9894,33.5168L 50.4616,35.7836L 49.9075,38.0688L 48.5116,42.954 Z",
        "M 45,27L 51,21L 57,27L 45,27 Z",
    ),
)
icon_textalign_left = VectorIcon(
    fill=(),
    stroke=(
        "M 3 10 H 16",
        "M 3 14 H 21",
        "M 3 18 H 16",
        "M 3 6 H 21",
    ),
)

icon_textalign_center = VectorIcon(
    fill=(),
    stroke=(
        "M3 6 H 21",
        "M3 14 H 21",
        "M 17 10 H 7",
        "M 17 18 H 7",
    ),
)

icon_textalign_right = VectorIcon(
    fill=(),
    stroke=(
        "M 8 10 H 21",
        "M 3 14 H 21",
        "M 8 18 H 21",
        "M 3 6 H 21",
    ),
)

icon_kerning_bigger = VectorIcon(
    fill=(),
    stroke=(
        "[width_bold]M 5, 30 l 10,-20 l 10, 20 M 10, 20 l 10, 0 M 30, 10 l 7.5, 20 l 7.5, -20",
        "M 10, 35 l -5, 5 l 5, 5",
        "M 5, 40 h 15 m 10, 0 h 15",
        "M 40, 35 l 5, 5 l -5 5",
    ),
)

icon_kerning_smaller = VectorIcon(
    fill=(),
    stroke=(
        "[width_bold]M 7.5, 30 l 10,-20 l 10, 20 M 12.5, 20 l 10, 0 M 27.5, 10 l 7.5, 20 l 7.5, -20",
        "M 15, 35 l 5, 5 l -5, 5",
        "M 5, 40 h 15 m 10, 0 h 15",
        "M 35, 35 l -5, 5 l 5 5",
    ),
)

icon_linegap_bigger = VectorIcon(
    fill=(),
    stroke=(
        "[width_bold]M 10, 30 l 10, -20 l 10, 20 M 15, 20 l 10, 0",
        "[width_bold]M 12.5, 40 l 7.5, 20 l 7.5, -20",
        "M 35, 15 l 5, -5 l 5, 5",
        "M 40, 10 v 20 m 0, 10 v 20",
        "M 35, 55 l 5, 5 l 5, -5",
    ),
)

icon_linegap_smaller = VectorIcon(
    fill=(),
    stroke=(
        "[width_bold]M 10, 32.5 l 10, -20 l 10, 20 M 15, 22.5 l 10, 0",
        "[width_bold]M 12.5, 37.5 l 7.5, 20 l 7.5, -20",
        "M 35, 25 l 5, 5 l 5, -5",
        "M 40, 10 v 20 m 0, 10 v 20",
        "M 35, 45 l 5, -5 l 5, 5",
    ),
)

icon_air_on = VectorIcon(
    fill=(
        "M10.6 22q-1.275 0-1.937-.763T8 19.5q0-.65.288-1.263t.887-1.012q.55-.35.888-.9t.462-1.175l-.3-.15q-.15-.075-.275-.175l-2.3.825q-.425.15-.825.25T6 16q-1.575 0-2.788-1.375T2 10.6q0-1.275.763-1.937T4.475 8q.65 0 1.275.288t1.025.887q.35.55.9.887t1.175.463l.15-.3q.075-.15.175-.275l-.825-2.3q-.15-.425-.25-.825t-.1-.8q0-1.6 1.375-2.813T13.4 2q1.275 0 1.938.763T16 4.475q0 .65-.288 1.275t-.887 1.025q-.55.35-.887.9t-.463 1.175l.3.15q.15.075.275.175l2.3-.85q.425-.15.813-.237T17.975 8Q20 8 21 9.675t1 3.725q0 1.275-.8 1.938T19.425 16q-.625 0-1.213-.288t-.987-.887q-.35-.55-.9-.887t-1.175-.463l-.15.3q-.075.15-.175.275l.825 2.3q.15.4.25.763t.1.762q.025 1.625-1.35 2.875T10.6 22m1.4-8.5q.625 0 1.062-.437T13.5 12q0-.625-.437-1.062T12 10.5q-.625 0-1.062.438T10.5 12q0 .625.438 1.063T12 13.5",
    ),
    # stroke=(
    #     "M3 8H10C11.6569 8 13 6.65685 13 5C13 3.34315 11.6569 2 10 2C8.34315 2 7 3.34315 7 5",
    #     "M4 16H15C16.6569 16 18 17.3431 18 19C18 20.6569 16.6569 22 15 22C13.3431 22 12 20.6569 12 19",
    #     "M2 12H19C20.6569 12 22 10.6569 22 9C22 7.34315 20.6569 6 19 6C17.3431 6 16 7.34315 16 9",
    # ),
)

icon_air_off = VectorIcon(
    fill=(
        "M12.5 2C9.64 2 8.57 4.55 9.29 7.47L15 13.16c.87.21 1.81.65 2.28 1.57c1.18 2.37 4.75 2.27 4.75-2.23c0-3.58-3.98-4.37-7.68-2.37c-.32-.4-.74-.71-1.22-.91c.19-.93.63-1.98 1.62-2.47C17.11 5.57 17 2 12.5 2",
        "M3.28 4L2 5.27l2.47 2.46C3.22 7.74 2 8.87 2 11.5c0 3.57 3.96 4.35 7.65 2.37c.32.4.75.72 1.24.92c-.2.92-.64 1.96-1.62 2.45C6.91 18.42 7 22 11.5 22c2.3 0 3.44-1.64 3.44-3.79L18.73 22L20 20.72z",
    ),
    stroke=(),
)

icon_barrel_distortion = VectorIcon(
    fill=(),
    stroke=(
        "M 557,209 C 531,212 504,213 477,209",
        "M 517,151 L 517,232",
        "M 557,173 C 531,169 504,169 477,173",
        "M 499,231 C 496,205 496,178 499,151",
        "M 535,231 C 539,205 539,178 535,151",
        "M 558,191 L 477,191",
        "M 480,154 C 494,149 545,150 554,154 C 559,168 558,219 554,228 C 540,233 489,232 480,228 C 475,214 476,163 480,154 L 480,154",
    ),
)

icon_ignore = VectorIcon(
    fill=(
        "M511.675127 0C229.086213 0 0 229.084914 0 511.675127 0 794.26664 229.086213 1023.350254 511.675127 1023.350254S1023.350254 794.26534 1023.350254 511.675127C1023.350254 229.087513 794.264041 0 511.675127 0z"
        "m0 921.015228c-226.07269 0-409.338802-183.267411-409.338802-409.340101s183.267411-409.340102 409.338802-409.340102c226.07399 0 409.340102 183.267411 409.340101 409.340102s-183.267411 409.340102-409.340101 409.340101z"
        "M292.385787 438.57868h438.57868V584.771574H292.385787V438.57868z"
    ),
    stroke=(),
)

# Adding a couple of letters to go along with user-defined buttons
icon_letter_a = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M15.19,37.42L24.19,10.5 M32.81,37.5L24.19,10.5 M29.93,28.47L18.18,28.47",
    ),
    fill=(),
)

icon_letter_b = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M14.98,37.5L14.98,10.5",
        "M15,10.5H26.29A6.74,6.74,0,0,1,33,17.25h0A6.74,6.74,0,0,1,26.29,24H15",
        "M15,24H26.29A6.74,6.74,0,0,1,33,30.75h0a6.74,6.74,0,0,1-6.73,6.75H15",
    ),
    fill=(),
)
icon_letter_c = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M33,28.45a9,9,0,0,1-9,9.05h0a9,9,0,0,1-9-9v-8.9a9,9,0,0,1,9-9h0a9,9,0,0,1,9,9.05",
    ),
    fill=(),
)
icon_letter_d = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M15,37.5v-27h4.57A13.48,13.48,0,0,1,33,24h0A13.48,13.48,0,0,1,19.55,37.5Z",
    ),
    fill=(),
)
icon_letter_e = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M17.25,37.5 L30.75,37.5 M17.25,10.5 L30.75,10.5 M17.25,24 L26.05,24 M17.25,10.5 L17.25,37.5",
    ),
    fill=(),
)
icon_letter_f = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M17.26,10.5 L30.74,10.5 M17.26,24 L26.05,24 M17.26,10.5 L17.26,37.5",
    ),
    fill=(),
)
icon_letter_g = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M33,19.55a9,9,0,0,0-9.52-9c-4.88.26-8.54,4.65-8.54,9.55v8.39a9,9,0,0,0,9,9.05h0a9,9,0,0,0,9-9H24",
    ),
    fill=(),
)
icon_letter_h = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M14.95,10.5 L14.95,37.5",
        "M33.05,10.5 L33.05,37.5",
        "M14.95,23.95 L33.05,23.95",
    ),
    fill=(),
)
icon_letter_i = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M17.26,37.5 L30.74,37.5",
        "M17.26,10.5 L30.74,10.5",
        "M24,10.5 L24,37.5",
    ),
    fill=(),
)
icon_letter_j = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M17.26,10.5H30.74V30.75A6.75,6.75,0,0,1,24,37.5h0a6.75,6.75,0,0,1-6.74-6.75V28.51",
    ),
    fill=(),
)
icon_letter_k = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M17.31,10.54 L17.31,37.42",
        "M20.78,23.98 L30.69,10.63",
        "M20.78,23.98 L30.69,37.46",
        "M20.78,23.98 L17.31,23.98",
    ),
    fill=(),
)
icon_letter_l = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M17.27 10.5 L17.27 37.5 L 30.73 37.5",
    ),
    fill=(),
)
icon_letter_m = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M10.57 37.47 L10.57 10.5 L24 37.5 L37.43 10.54 L37.43 37.5",
    ),
    fill=(),
)
icon_letter_n = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M14.95,10.5 L14.95,37.5",
        "M33.05,37.5 L33.05,10.5",
        "M14.95,10.5 L33.05,37.5",
    ),
    fill=(),
)
icon_letter_o = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M33,19.55a9,9,0,0,0-9.52-9c-4.88.26-8.54,4.65-8.54,9.55v8.39a9,9,0,0,0,9,9.05h0a9,9,0,0,0,9-9v-8.9",
    ),
    fill=(),
)
icon_letter_p = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M15,37.5v-27H24a9.07,9.07,0,0,1,0,18.14H15",
    ),
    fill=(),
)
icon_letter_q = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M33,19.55a9,9,0,0,0-9.52-9c-4.88.26-8.54,4.65-8.54,9.55v8.39a9,9,0,0,0,9,9.05h0a9,9,0,0,0,9-9v-8.9",
        "M33.03,37.5 L24,28.58",
    ),
    fill=(),
)
icon_letter_r = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M15,37.4V10.5h9a9,9,0,0,1,0,18.07H15",
        "M24,28.57 L32.91,37.5",
    ),
    fill=(),
)
icon_letter_s = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M21.71,10.5A6.74,6.74,0,0,0,15,17.25h0A6.74,6.74,0,0,0,21.71,24H24",
        "M24,24h2.29A6.74,6.74,0,0,1,33,30.75h0a6.74,6.74,0,0,1-6.73,6.75",
        "M32.38,12.78C30.52,11.22,28.51,10.5,24,10.5H21.71",
        "M15.62,35.22c1.86,1.56,3.87,2.28,8.38,2.28h2.29",
    ),
    fill=(),
)
icon_letter_t = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M13.84,10.5 L34.16,10.5",
        "M24,37.5 L24,10.5",
    ),
    fill=(),
)
icon_letter_u = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M15,10.55V28.43a9,9,0,0,0,9,9h0a9,9,0,0,0,9-9V10.55",
    ),
    fill=(),
)
icon_letter_v = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M33.03 10.5 L24 37.5 L14.96 10.5",
    ),
    fill=(),
)
icon_letter_w = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M10.55,10.5 L17.27,37.5",
        "M24,10.5 L17.27,37.5",
        "M24,10.5 L30.73,37.5",
        "M37.45,10.5 L30.73,37.5",
    ),
    fill=(),
)
icon_letter_x = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M14.98 10.5 L24 24 L14.98 37.5",
        "M33.02 10.5 L24 24 L33.02 37.5",
    ),
    fill=(),
)
icon_letter_y = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M14.98,10.5 L24,24",
        "M33.02,10.5 L24,24",
        "M24,37.5 L24,24",
    ),
    fill=(),
)
icon_letter_z = VectorIcon(
    stroke=(
        "M40.5,5.5H7.5a2,2,0,0,0-2,2v33a2,2,0,0,0,2,2h33a2,2,0,0,0,2-2V7.5A2,2,0,0,0,40.5,5.5Z",
        "M15 10.5 L33 10.5 L15 37.5 L33 37.5",
    ),
    fill=(),
)

icon_tabs = VectorIcon(
    fill=(),
    stroke=(
        "M 154.807,154.807 L 283.183,154.807"
        + "M 154.807,154.807 L 154.807,180.609"
        + "M 154.807,206.410 L 154.807,283.813"
        + "M 283.813,154.807 L 283.813,180.609"
        + "M 283.813,206.410 L 283.813,283.813"
        + "M 154.807,283.813 L 206.409,283.813"
        + "M 283.813,283.813 L 232.210,283.813"
        + "M 161.257,193.508"
        + "C 161.257,192.376 160.959,191.264 160.393,190.283"
        + "C 159.827,189.303 159.012,188.488 158.032,187.922"
        + "C 157.051,187.356 155.939,187.058 154.807,187.058"
        + "C 153.674,187.058 152.562,187.356 151.581,187.922"
        + "C 150.601,188.488 149.787,189.303 149.220,190.283"
        + "C 148.654,191.264 148.356,192.376 148.356,193.508"
        + "C 148.356,194.641 148.654,195.753 149.220,196.734"
        + "C 149.787,197.714 150.601,198.528 151.581,199.094"
        + "C 152.562,199.661 153.674,199.959 154.807,199.959"
        + "C 155.939,199.959 157.051,199.661 158.032,199.094"
        + "C 159.012,198.528 159.827,197.714 160.393,196.734"
        + "C 160.959,195.753 161.257,194.641 161.257,193.508"
        + "M 290.263,193.508"
        + "C 290.263,192.376 289.965,191.264 289.399,190.283"
        + "C 288.833,189.303 288.018,188.488 287.038,187.922"
        + "C 286.057,187.356 284.945,187.058 283.812,187.058"
        + "C 282.680,187.058 281.568,187.356 280.587,187.922"
        + "C 279.607,188.488 278.792,189.303 278.226,190.283"
        + "C 277.660,191.264 277.362,192.376 277.362,193.508"
        + "C 277.362,194.641 277.660,195.753 278.226,196.734"
        + "C 278.792,197.714 279.607,198.528 280.587,199.094"
        + "C 281.568,199.661 282.680,199.959 283.812,199.959"
        + "C 284.945,199.959 286.057,199.661 287.038,199.094"
        + "C 288.018,198.528 288.833,197.714 289.399,196.734"
        + "C 289.965,195.753 290.263,194.641 290.263,193.508"
        + "M 225.760,283.812"
        + "C 225.760,282.680 225.462,281.568 224.896,280.587"
        + "C 224.330,279.607 223.515,278.792 222.535,278.226"
        + "C 221.554,277.660 220.442,277.362 219.310,277.362"
        + "C 218.177,277.362 217.065,277.660 216.084,278.226"
        + "C 215.104,278.792 214.290,279.607 213.723,280.587"
        + "C 213.157,281.568 212.859,282.680 212.859,283.812"
        + "C 212.859,284.945 213.157,286.057 213.723,287.038"
        + "C 214.290,288.018 215.104,288.833 216.084,289.399"
        + "C 217.065,289.965 218.177,290.263 219.310,290.263"
        + "C 220.442,290.263 221.554,289.965 222.535,289.399"
        + "C 223.515,288.833 224.330,288.018 224.896,287.038"
        + "C 225.462,286.057 225.760,284.945 225.760,283.812"
    ),
    edge=25,
)

icon_meerk40t = VectorIcon(
    fill=(
        # Grey outer circle
        "[0x999999]M 243146.39,109490.94 A 112235.34,112235.34 0 0 1 130911.05,221726.28 112235.34,112235.34 0 0 1 18675.708,109490.94 112235.34,112235.34 0 0 1 130911.05,-2744.4077 112235.34,112235.34 0 0 1 243146.39,109490.94 Z",
        # Yellow circle
        "[0xffeeaa]M 240693.07,109699.68 A 109654.96,109654.96 0 0 1 131038.11,219354.63 109654.96,109654.96 0 0 1 21383.148,109699.68 109654.96,109654.96 0 0 1 131038.11,44.722008 109654.96,109654.96 0 0 1 240693.07,109699.68 Z",
        # White background
        "[white]M 69563 -393 C 69086.9 -801.61 76038.3 7796.65 78298.6 10220.7 C 83432.9 18925.5 98947.7 26693.2 98478.3 35496.3 C 95246 40079.2 97540.8 43912.2 88826.5 44161.5 C 83025.7 45973.5 82123.4 50851.1 81411.9 55188 C 81239.9 60864 82258.1 64762 84229.2 66529.1 C 83432.2 66265.5 85578.4 71691.8 91201.1 73601 C 86105.3 71393.1 93925 75941.7 93554.4 74954.3 C 94243.8 76154.1 94647.3 77985.1 95109 77181 C 97785.8 82408.1 99327.2 82149.3 102013 85204.8 C 101960 82633.7 108533 91666.3 101350 89870.1 C 94838 96436.8 85241.2 96878.3 77929.3 103955 C 73187.1 111173 68944.8 117334 59916.2 119046 C 55197.8 121764 50417.9 124079 44816.5 123191 C 36639.2 126664 23596.1 138706 35084.6 145939 C 27663.2 157688 18333.7 168187 11483.7 180299 C 7237.17 188531 12108.6 184618 16332.6 180861 C 28346.4 171658 45881.4 164976 59374.9 175423 C 63776.1 189103 73510.7 179947 79616.1 174785 C 86614.2 178554 88037.9 188511 97787.6 189123 C 106930 192122 105278 198468 105829 206599 C 111630 222118 128836 209487 123483 197995 C 119164 186438 126892 193853 133413 192640 C 151602 183577 133710 210072 147606 214337 C 165714 213361 154931 196297 166147 190032 C 176687 191988 182731 172178 191049 179090 C 197373 192806 202541 175585 209139 172307 C 225090 165044 245753 174497 256513 187100 C 254942 175071 242355 162838 234891 152029 C 227522 146311 232252 143649 235384 138237 C 231851 126913 218835 120975 208105 120046 C 195564 117549 191577 107452 182483 100406 C 175683 94092.5 167637 91702.2 159796 88439.2 C 161012 85782.7 161192 87036 163335 85294 C 164821 84240.5 168778 79380.9 170251 78722.9 C 170648 75805 170916 76698.8 173332 74491 C 181712 69595.9 178882 67795.5 182421 64277.4 C 184044 59413.6 181563 51941.9 180418 49876.1 C 182122 46567.1 172442 44144.7 168602 40885.5 C 171686 42808.7 167643 37099.9 165402 34509.6 C 170773 29079.5 176080 23404.3 181540 17880.7 C 187427 11926.4 192518 6174.82 197528 408.3 L 188186 6103.85 C 183128 9708.98 172332 19926 166393 25833.8 C 162083 32901.2 158739 26477.7 157024 24734.5 C 150294 21488.7 141545 20138.8 132293 20505.4 C 122552 20891.4 120425 20961.8 108199 24819.7 C 109849 25154.6 102590 27358.6 106842 27096.3 C 100709 29616.7 106658 26379 103646 28628.4 C 95229.2 20222.2 87072.9 11905.9 78132.8 4050.73 C 75415.1 2500.65 73479.6 1374.78 71048.7 219.34 C 68895.7 -1960.23 69990.7 -25.83 69563 -393 Z M 87683.8 71550.4 L 87683.8 71550.4 Z",
        "",
        # Red laserbeams
        "[red]M 195960 1656.3 L 189248 8978.63 L 160220 38268 L 156907 42975.2 L 156123 49164.3 L 150892 50907.7 L 146795 48815.6 L 145292 47050.4 L 144442 45067.3 L 145335 41689.4 L 149890 38202.6 L 154052 37548.8 L 154423 39226.9 L 166845 27633.2 L 179528 14971.6 L 185935 8695.33 L 186829 7867.21 Z",
        "[red]M 71480 1046.1 L 78889.5 5578.98 L 112276 39052.5 L 112101 37134.8 L 115240 37134.8 L 120296 40708.8 L 120812 43486.3 L 120689 44441.8 L 120011 46167.6 L 118439 48725.7 L 116282 49742.7 L 113231 49280.4 L 108361 44873.2 L 109009 42407.7 L 111043 42962.4 L 92550.9 22683.2 Z",
        # Main shape
        "[black]M 115039 47557.4 C 121966 46863.5 114524 34342.1 119087 43454.5 C 121556 46784.9 111185 48744.3 115039 47557.4 Z",
        "[black]M 148680 47948.1 C 142540 44919.2 151777 35516.2 146842 44379.8 C 146184 47537.3 154587 49073.5 148680 47948.1 Z",
        "[black]M 148612 213878 C 134716 209613 152681 181937 134271 191959 C 127750 193172 118105 185020 122424 196577 C 127408 207921 112636 222101 106835 206581 C 106284 198451 107937 192104 98794.5 189106 C 89044.8 188493 86883.7 177356 79885.7 173587 C 73411.5 178307 64783.3 189085 60382 175406 C 47626.1 164295 28246.7 170608 16232.8 179812 C 12008.8 183569 8243.38 188513 12489.9 180282 C 19339.9 168169 28669.4 157671 36090.8 145921 C 24602.3 138689 37645.8 126646 45823.1 123174 C 51424.5 124061 56204.7 121747 60923.1 119029 C 69951.7 117317 74193.3 111157 78935.5 103939 C 86247.4 96861.9 95844.2 96419.8 102356 89853.1 C 109539 91649.3 102966 82617.1 103019 85188.2 C 100333 82132.7 98792.8 82391.1 96116 77164 C 95654.3 77968.1 95250.1 76137 94560.6 74937.3 C 94931.3 75924.6 87111.2 71376.2 92207.1 73584.1 C 86584.3 71674.9 84438.9 66247.9 85235.9 66511.5 C 83264.9 64744.4 82246 60847.2 82418 55171.2 C 83129.5 50834.3 84032.1 45957.1 89832.8 44145 C 98547.2 43895.7 96252.4 40062.8 99484.7 35479.9 C 99954.1 26676.9 84439.5 18908.3 79305.2 10203.5 C 76291.4 6971.47 65935.5 -4710.4 74547.3 4007.85 C 87383.2 17170.6 100695 29980.2 112481 44091.6 C 103165 38963.6 115694 56009.8 119587 46125.1 C 125418 39750.5 106669 34107.7 113964 40946.2 C 101316 29968.6 89789 17464.3 78389.1 5144.53 C 87329.2 12999.7 95571.2 21606.6 103988 30012.8 C 107000 27763.4 101871 29417.9 108004 26897.5 C 103752 27159.8 110934 25398 109283 25063.1 C 112873 23752.7 118264 22564.6 119705 21767.5 C 123153 21783.5 122253 20589.7 125899 20957 C 127685 20383.3 130138 21902.9 131800 20803.1 C 133197 21017.5 135089 21594.5 138327 20956.4 C 141909 20628.1 140336 21082.4 143184 21222 C 144200 22466 147218 22487.2 151750 23314.9 C 153618 24655.7 156790 24913.7 158030 26986.5 C 159745 28729.8 163089 32883.9 167400 25816.5 C 173338 19908.7 181892 11360.7 186950 7755.57 C 175543 19508.3 164291 31528.9 151884 42219.4 C 161030 32145.6 135946 43427.1 148424 49145 C 154281 52682.9 158977 40017.2 153714 44577.5 C 167110 29365.3 181772 15275.9 196397 1252.11 C 186377 12785.1 175586 23633 164844 34493.3 C 167085 37083.6 171128 42791.3 168043 40868.2 C 171884 44127.4 183129 46550 181425 49859 C 182570 51924.8 183649 58879.9 182026 63743.7 C 178487 67261.8 181759 68767.2 173379 73662.2 C 170963 75870 170400 74976.9 170003 77894.7 C 168531 78552.7 164795 83559.2 163309 84612.6 C 161535 86649.7 159215 85691.7 159253 88938.2 C 167095 92201.2 175878 95256.1 182678 101569 C 191772 108615 196571 118785 209111 121283 C 219841 122212 230350 126895 234547 137998 C 231415 143410 227274 147179 234643 152897 C 242107 163705 251524 173505 256192 185977 C 245432 173374 226097 165027 210146 172290 C 203547 175568 198380 192789 192056 179073 C 182853 168768 177545 191085 167006 189130 C 151217 192297 166720 212902 148612 213878 Z "
        "M 110663 208111 C 110754 203670 109303 186156 107693 199897 C 107356 207296 109172 206968 109176 200568 C 108929 198027 111151 216012 110663 208111 Z "
        "M 154809 209036 C 155844 202832 156497 197319 156516 207323 C 159726 203497 155806 187109 155162 199451 C 156412 199968 152411 215254 154809 209036 Z "
        "M 154767 197750 C 154239 191315 154277 208461 154767 197750 Z "
        "M 110957 195566 C 110460 200559 111593 203280 110957 195566 Z "
        "M 112147 199610 C 111722 199937 112525 201296 112147 199610 Z "
        "M 160363 191634 C 176300 184223 178394 162835 171258 148504 C 166603 158874 166774 170658 161138 180655 C 165042 178042 167627 161296 167861 165034 C 168609 170183 162179 182070 162369 182148 C 166754 179141 169186 163887 169406 164423 C 169890 170547 163791 183503 162347 184575 C 166560 179900 171656 174316 165569 182890 C 158548 192999 176417 169562 167826 182255 C 162858 189154 166757 185131 169757 180867 C 169206 186298 153759 193874 164541 188262 C 161414 193678 144638 190919 158141 192346 L 160363 191634 Z "
        "M 166255 182412 C 167366 180802 165710 184122 166255 182412 Z "
        "M 165950 179710 C 168925 174562 172036 159341 168866 173668 C 168216 175803 167508 178039 165950 179710 Z "
        "M 168053 161679 C 168259 160078 168259 163280 168053 161679 Z "
        "M 111469 192123 C 116292 192481 96755.9 189066 103275 189348 C 107050 191758 92137.3 181081 94573.4 176240 C 95348.8 182192 106299 191948 97671 181485 C 93527.1 170323 97358.3 181852 101674 184857 C 96454.5 182019 93413.7 157984 96575.9 172690 C 96520.1 178238 106995 189950 99485.1 178707 C 97043.6 172658 94458.9 157949 97984.9 171904 C 98475.1 177149 107968 188604 101107 178000 C 98252 174220 95957.1 155016 98870.5 168394 C 99620.5 173611 107886 187002 101688 174907 C 98697.2 167878 97585.2 151605 93591.2 149606 C 87234.2 163654 89895.6 183247 104361 191138 C 106483 192407 109092 192569 111469 192123 Z "
        "M 95656.1 162702 C 95861.8 161101 95861.8 164304 95656.1 162702 Z "
        "M 157948 191200 C 156934 190662 157710 191776 157948 191200 Z "
        "M 107237 190843 C 104629 189714 107936 191894 107237 190843 Z "
        "M 158971 190944 C 157958 190406 158733 191520 158971 190944 Z "
        "M 141773 183306 C 152563 179754 163022 171002 164657 159249 C 159590 168995 150009 175588 139889 179418 C 146796 178412 153877 172500 157782 169054 C 154375 174355 142952 179419 141161 180732 C 146135 179366 158188 172345 147547 178892 C 142276 181462 136166 184041 145455 180730 C 151498 178607 134514 185797 141773 183306 Z "
        "M 123976 183082 C 118125 180239 115495 177822 122859 181670 C 128429 184414 103222 170118 117269 177691 C 121102 179949 131336 182880 121760 179176 C 116962 178535 101616 163922 112135 172817 C 116058 176832 131564 181688 118664 176203 C 111630 174683 102505 160241 100958 161382 C 104487 172236 114350 180314 125016 183657 L 123976 183082 Z "
        "M 135889 172279 C 147256 163474 158147 153674 166281 141718 C 161020 136333 155793 130914 150521 125540 C 138721 126803 126771 126872 114971 125575 C 110427 132797 93053.4 140146 104105 148421 C 112660 158043 122147 167052 132689 174468 L 133788 173824 L 135889 172279 Z "
        "M 128995 170302 C 123445 167606 121350 163034 122458 157237 C 122693 150950 120929 135398 125457 149729 C 126945 153929 130700 166561 135720 159572 C 138370 154932 144095 134897 142996 149449 C 142544 154696 143679 160693 142406 165571 C 138132 167758 133359 176334 128995 170302 Z "
        "M 110138 153180 C 103031 147521 97952.7 140389 107786 134759 C 111909 129607 116099 124794 123204 127590 C 132124 127913 141081 127871 149959 126862 C 154684 132048 160530 136596 164380 142310 C 161610 145070 152327 159931 151637 154265 C 151632 146737 151626 139210 151621 131683 C 142824 130619 136533 133408 134835 142917 C 130765 154584 129664 133619 124274 132116 C 121078 133062 113756 129811 113754 134006 C 113713 141615 113672 149224 113632 156833 C 112467 155615 111303 154398 110138 153180 Z "
        "M 22943.5 171078 C 31178 164967 39296.6 158644 46607 151434 C 38253.9 157983 30441.5 165291 21634 171209 C 29906.2 162146 40796.4 155862 48909.4 146621 C 44987.1 150520 25605.8 165025 38627.3 154171 C 42342.4 151329 55509.6 138031 45336.6 147166 C 42007.9 150187 30455.5 159404 40382.4 150751 C 46295.8 147000 54333.1 137255 41774 140097 C 35066.9 152002 26267.9 162558 18914.8 174049 C 20273.5 173080 21605.1 172074 22943.5 171078 Z "
        "M 44816.2 145331 C 47755.6 142345 47134.6 143998 44651.4 145611 Z "
        "M 246914 173263 C 239274 162063 230788 151303 223502 139950 C 213526 137618 215804 144132 221910 147590 C 225125 150309 238728 161922 227616 153074 C 223339 149701 210228 138571 221013 148610 C 225044 152200 239594 164658 227417 155141 C 223832 152293 210715 141364 220807 150639 C 226660 156388 242715 167720 242591 170092 C 236033 165534 223141 153916 221122 153220 C 228568 159898 240401 169921 246914 173263 Z "
        "M 221816 146447 C 215662 141346 216584 141002 222096 146266 L 223406 147560 Z "
        "M 150788 165430 C 156950 162502 167087 148589 167094 149293 C 163516 154885 159126 159259 157887 161296 C 149905 170384 170678 148055 160367 160725 C 154953 166990 159652 162878 162305 159486 C 159556 163474 154184 168913 161261 162476 C 167309 158318 172073 142675 169093 140224 C 168339 145968 159109 154402 159033 155801 C 163585 153661 173119 134605 166214 148641 C 164889 153474 147667 167531 150788 165430 Z "
        "M 163901 155945 C 167500 150539 167596 152311 163901 155945 Z "
        "M 117229 166053 C 113350 162555 101552 153332 111882 162082 C 113364 163374 116042 165477 117229 166053 Z "
        "M 156738 164464 C 155319 164884 155148 166321 156738 164464 Z "
        "M 106611 163044 C 103303 160098 100671 155237 105503 161324 C 102675 157489 93859.8 145672 101744 155628 C 105326 160853 114960 168659 105745 159419 C 102401 155870 93894.3 142702 101358 152981 C 104343 157931 117359 169201 107044 158690 C 101848 155515 93122.9 133656 96515.5 149295 C 97275.4 155407 105654 163724 108246 164606 Z "
        "M 107365 162878 C 105824 161175 104758 160684 107365 162878 Z "
        "M 107217 156243 C 103363 151785 95973.1 143778 103582 152973 C 103403 152769 108936 158536 107217 156243 Z "
        "M 36502 143600 C 34896.1 140114 35265.9 144581 36502 143600 Z "
        "M 230010 143283 C 232838 137865 222730 135776 228747 142436 C 232122 141131 227140 144615 230010 143283 Z "
        "M 37319.1 142045 C 42954 133105 30418.5 142142 36782.5 142706 L 37319.1 142045 Z "
        "M 39149.2 142045 C 41281.1 137459 36916.6 145177 39149.2 142045 Z "
        "M 97715.9 142301 C 94285.6 135705 96651.4 142004 97715.9 142301 Z "
        "M 226613 141416 C 224765 139056 228199 144654 226613 141416 Z "
        "M 231015 140563 C 230195 139556 231294 141831 231015 140563 Z "
        "M 169061 138925 C 171638 134193 164771 144215 169061 138925 Z "
        "M 34127.9 137159 C 33847.5 127036 31418.4 147936 34127.9 137159 Z "
        "M 32920.5 138670 C 33368.9 137325 33318.2 139610 32920.5 138670 Z "
        "M 232793 140029 C 234172 137820 228553 128776 231528 138047 C 231183 137644 231901 140932 232793 140029 Z "
        "M 99434.1 139730 C 98084.4 137012 98563.9 140722 99434.1 139730 Z "
        "M 54025.8 139178 C 52631.3 137836 40312.1 136643 50425.6 139106 L 51843.4 139353 L 54025.8 139178 Z "
        "M 217383 138402 C 225410 135533 203696 140306 214905 139155 Z "
        "M 59160.2 138478 C 63183.3 132809 61625.5 130288 63874.9 132549 C 64067.2 130867 65403.7 133125 65241.5 130725 C 66992.8 133143 65622.1 129499 67443.8 131973 C 65710.8 126422 69616.7 135114 68075.5 129173 C 70950.4 136165 67891 124484 70588.5 131403 C 72474.2 131574 68981.6 123779 72246.1 130149 C 67783 118537 76707.7 135510 77950.3 132483 C 72573.4 130904 70472.8 117813 74706.4 128258 C 81146.6 138555 68926.3 114781 75828.4 126907 C 77106.9 128482 71568.8 115674 76704.6 125197 C 80748.9 130789 71881.5 114661 77065.7 122266 C 74024.5 114616 83806.2 133832 78371.2 122238 C 74252 111487 84236 131560 79006.7 120141 C 77156.9 114901 85341.3 130445 80201.1 119589 C 79610.3 117607 87368.5 129797 82939.7 121694 C 77164.9 109794 88676.8 129921 84140.9 120770 C 79744.7 112138 91798.8 132230 85483 120108 C 80253.2 109115 93723.2 132184 87303.3 119679 C 82363.6 109399 97371 134483 90476.6 121354 C 87178.8 115150 87122.1 113766 90797.4 120236 C 96538.6 127134 102750 143418 109944 128886 C 112848 123268 118116 124375 123398 125046 C 132577 125484 141783 125222 150921 124258 C 154758 128106 158595 131954 162432 135802 C 167422 130408 175926 118018 177407 116379 C 174812 121641 170853 129372 177331 119980 C 184074 108343 170795 133784 179748 119815 C 186287 107553 174058 132091 181623 120747 C 188096 110609 176784 130349 183457 121771 C 189124 110831 179328 130873 185965 120049 C 189035 114957 181790 129738 187030 120594 C 191080 114193 181306 133325 187892 122328 C 192398 114928 182427 133439 188924 122986 C 192783 115549 185390 131994 191404 122538 C 188200 129174 187428 132871 191530 124378 C 192759 127572 181299 138383 190812 129096 C 194233 122599 192577 125632 191852 130119 C 193243 125384 192536 135109 193502 128820 C 194015 132112 194271 128150 194848 130968 C 196011 127923 196339 134610 198320 129957 C 197731 133030 199061 130615 199147 131634 C 199906 129542 199393 134158 200418 131263 C 200927 133340 201341 129007 201774 132564 C 201563 128023 206016 141568 202294 135053 C 206708 143557 202290 128373 205166 137069 C 211777 142923 199754 129674 207862 127180 C 215235 121099 196177 119581 192175 116069 C 185961 111894 178565 101182 170316 106674 C 159215 112521 147824 118189 135663 121349 C 147763 119743 116361 118739 128982 121491 C 115053 117384 102743 109359 89266.8 104231 C 79605.7 108515 72837.2 118044 62086.2 120654 C 55023.8 123049 53907.1 125141 59445 130341 C 66203 134312 52475.5 140794 59160.2 138478 Z "
        "M 101408 132196 C 97351.5 129726 88219.8 111008 95137.6 122521 C 95669.7 124351 107740 138232 101408 132196 Z "
        "M 162917 132492 C 166280 129116 177241 111365 170426 123679 C 169685 125579 160305 136688 162917 132492 Z "
        "M 101216 128651 C 97464.1 124897 92240.8 114111 98254.5 123920 C 99289.6 125657 105959 133834 101216 128651 Z "
        "M 163290 129446 C 166637 124632 173476 115296 166428 125736 C 165372 126955 164577 128434 163290 129446 Z "
        "M 193087 128039 C 193879 124756 193218 129669 193087 128039 Z "
        "M 57811.9 126559 C 53919 123249 59524.2 127114 57811.9 126559 Z "
        "M 208357 125263 C 206949 124473 212670 124250 208357 125263 Z "
        "M 206602 125004 C 209139 122795 207521 124936 206602 125004 Z "
        "M 55177 124579 C 57511.2 123205 58959.5 125618 55177 124579 Z "
        "M 58454.7 123643 C 59576.2 123277 58565.5 124135 58454.7 123643 Z "
        "M 129045 123649 C 130454 123233 129301 124096 129045 123649 Z "
        "M 135574 123641 C 137260 123262 135901 124065 135574 123641 Z "
        "M 136976 123393 C 138385 122978 137232 123841 136976 123393 Z "
        "M 129829 121597 C 130950 121230 129940 122089 129829 121597 Z "
        "M 147758 120981 C 151917 119410 144230 122713 147758 120981 Z "
        "M 119573 119993 C 114461 118639 101995 110706 113656 116859 C 115070 117538 127856 122742 119573 119993 Z "
        "M 141645 120921 C 146958 118922 165420 110746 151496 117664 C 148337 119057 145062 120360 141645 120921 Z "
        "M 149865 120117 C 154160 117898 150922 120260 149865 120117 Z "
        "M 70462.3 117509 C 71871.1 117094 70718 117957 70462.3 117509 Z "
        "M 193768 117509 C 195177 117094 194024 117957 193768 117509 Z "
        "M 66305.2 137853 C 72248.2 136690 74375.4 133072 69941.8 135478 C 69368.9 134881 67493.3 134586 66033.5 136240 C 65240.4 134393 63112.2 137675 62826.2 136045 C 55882 141214 61811.6 138165 66305.2 137853 Z "
        "M 100969 138701 C 98242 134533 97817.3 137648 100969 138701 Z "
        "M 167310 136545 C 173167 128721 165875 135597 165439 138911 L 166082 138216 Z "
        "M 204983 138508 C 198344 133512 200988 137332 196441 134562 C 197336 136857 193474 132177 195075 135771 C 182470 130482 207882 142608 204983 138508 Z "
        "M 57522.4 136147 C 61221.5 129025 51973.2 133732 55569.7 137632 C 54844.8 134985 52971.4 135523 55500.4 137838 L 56377.6 137449 L 57522.4 136147 Z "
        "M 61579.4 136801 C 63240.1 130699 59356.5 140779 61579.4 136801 Z "
        "M 210770 137440 C 213920 134051 203772 138582 210770 137440 Z "
        "M 100548 134878 C 95049.1 128645 95612.4 130874 100316 136105 C 101952 139396 103819 135506 100548 134878 Z "
        "M 165423 135346 C 172876 125377 158649 140928 165423 135346 Z "
        "M 209693 136775 C 214198 131418 203076 130729 207772 136353 C 206035 132575 209484 138334 209693 136775 Z "
        "M 37299.3 136380 C 40523.3 130516 37981.6 126944 35909.1 134917 C 38080.1 133937 34431.3 137921 37299.3 136380 Z "
        "M 229199 135948 C 229782 136347 228291 128363 226701 130661 C 225621 132718 230501 139075 229199 135948 Z "
        "M 42003.9 135440 C 44004.5 132052 50394.5 119670 42846 126962 C 47856.6 125180 34131.3 135364 42130.1 134385 C 41212.6 134756 39925 136601 42003.9 135440 Z "
        "M 224957 135401 C 225274 134175 224420 128420 221717 126504 C 223034 124445 213792 123152 220498 128510 C 222177 130308 221464 135979 224957 135401 Z "
        "M 48200.5 134125 C 49494.1 126891 50874.5 131824 51862.4 131010 C 52340.7 130594 52069.1 131762 55069.1 130569 C 61277 127657 45251 122124 47944 127177 C 42173.1 132782 48394.4 133144 46730.9 134983 L 48200.5 134125 Z "
        "M 71500.2 134172 C 70776.2 134666 71196.2 135284 71500.2 134172 Z "
        "M 218997 134449 C 218508 132937 221791 130995 218037 127011 C 213070 119827 205914 132041 212134 131109 C 213022 131646 214211 130974 215176 130452 C 214853 127192 219805 137620 218997 134449 Z "
        "M 213295 131066 C 212549 129408 213700 130265 213295 131066 Z "
        "M 57434.1 131422 C 61214.3 130447 51788.5 131233 57434.1 131422 Z "
        "M 208776 131188 C 211451 127578 203850 133048 208776 131188 Z "
        "M 40634.3 129957 C 41295.7 127489 38793 132595 40634.3 129957 Z "
        "M 89712.9 130469 C 83696.4 128990 82152.9 130571 89712.9 130469 Z "
        "M 180233 130113 C 181014 128809 169927 131675 179014 130452 L 180233 130113 Z "
        "M 225074 129889 C 224288 129266 225836 131263 225074 129889 Z "
        "M 40680.7 127926 C 39087.3 128810 40663.3 130169 40680.7 127926 Z "
        "M 225810 128729 C 224740 126740 223900 128769 225810 128729 Z "
        "M 137424 116644 C 152657 115177 165493 105512 179429 100500 C 175576 99783.9 171690 101293 177587 99003 C 165525 100353 156748 111253 144788 113719 C 130938 118093 115167 115247 104670 104903 C 101308 101885 92046 94930 101065 100854 C 104199 103164 119799 114743 109808 105910 C 119822 114606 134158 117644 146384 111726 C 155185 108787 162310 102663 170066 98082.6 C 164461 102881 180232 95544.2 169711 95329.2 C 160713 99619.4 153762 108598 143789 111883 C 130338 118149 116563 110503 106446 101803 C 104374 96375.6 86638.1 94323.6 96965.7 99284.4 C 101383 102644 110782 111318 99839.8 104327 C 96175.7 101912 89007.1 99643.3 91144.5 99404.9 C 79423.6 100121 102267 104424 105479 108393 C 93242.9 103859 113577 112758 117454 114110 C 123866 116115 130696 117299 137424 116644 Z "
        "M 158397 108219 C 162982 105038 173878 102277 163235 107019 C 162010 107273 159200 108868 158397 108219 Z "
        "M 139022 112035 C 144359 109704 142233 108722 145482 107050 C 138030 108979 152207 103749 143819 105649 C 152965 102576 139179 106067 146635 103118 C 149220 101468 144500 102369 150320 99384.5 C 144348 101418 147376 100374 150350 97692.5 C 146297 99113.1 157554 91936.8 148782 96733.2 C 145545 97632.9 154740 93206.2 147214 96189 C 150264 93878.5 151882 91872.3 147017 95063 C 152130 91508.8 153602 90498.5 147145 93229.4 C 155011 88849.1 141359 95131.1 149792 89788.9 C 141152 94489 146573 91527.9 151092 87392.6 C 143988 91671 147285 89217.5 148860 87464.5 C 146270 88592.1 140381 92747.3 145408 87935.5 C 141621 89984.1 142085 89841.3 140877 89793.5 C 140915 88588.1 138735 90702.8 138025 91087.6 C 139413 86909.8 135185 95790.5 137034 89456.5 C 135327 93421.7 135592 87877.4 134006 93247 C 133740 89374.7 132394 94161.3 131156 91486.4 C 130709 93040.8 129815 91269 128688 90878.2 C 127294 89021.8 129395 94604.4 126398 89286.9 C 129166 96092 122894 84990.2 125749 91496.3 C 123241 88072.5 122134 87247.5 124655 91413.3 C 119573 85641 124669 92847.3 119681 88176.3 C 125446 94392.2 111584 83296.2 118548 89793.4 C 112843 86284.2 115730 88618.5 117005 90050.7 C 115720 90304 123717 94453.7 115679 90504.1 C 124113 96518.6 107775 87371 116829 93591.7 C 111987 91609.5 123535 98833.6 115039 95039 C 123812 100392 106664 90674 116510 97523.4 C 121050 100268 110499 95390.7 117198 99205.4 C 124075 102845 109529 96917.2 118211 101292 C 122095 103261 112959 100707 120283 103351 C 114344 102690 127927 106009 118446 104464 C 125305 107265 115273 103976 121818 107431 C 120133 107282 119899 107523 124450 109747 C 119011 108417 126230 111473 126978 112052 C 130929 112776 135054 112485 139022 112035 Z "
        "M 132500 111154 C 132743 109484 132658 113143 132500 111154 Z "
        "M 132504 107189 C 132700 105136 132700 109242 132504 107189 Z "
        "M 145418 102415 C 146826 102000 145673 102863 145418 102415 Z "
        "M 132494 100282 C 132700 98681.1 132700 101883 132494 100282 Z "
        "M 132494 96700.6 C 132700 95099.6 132700 98301.6 132494 96700.6 Z "
        "M 76858.1 109153 C 82081.9 106146 88054.7 100699 78856.6 106560 C 78418.1 106497 73916.5 111688 76858.1 109153 Z "
        "M 152645 106058 C 157640 102647 162905 95413.1 162656 97945 C 169758 93437.3 160898 88215.1 160349 96826.3 C 160002 99503.7 143439 112826 152645 106058 Z "
        "M 187089 107227 C 176120 99933.9 184905 108002 187089 107227 Z "
        "M 180018 102058 C 178852 101593 175119 102984 180018 102058 Z "
        "M 94317.7 100666 C 91462.2 99232 95925 102033 94317.7 100666 Z "
        "M 158381 98120.7 C 162403 91972.6 156712 87745.3 157352 96584.4 C 160655 91750.1 153991 104834 158381 98120.7 Z "
        "M 107276 98056.1 C 103715 89688.7 109151 99562 107824 95494 C 106172 83221.8 103379 98836.5 107276 98056.1 Z "
        "M 101488 95568.2 C 103971 91179.3 99674.5 89973.6 100744 95460.4 L 101597 96326.4 L 101488 95568.2 Z "
        "M 115423 89793.4 C 114505 88819.4 115105 90801.9 115423 89793.4 Z "
        "M 132286 83360 C 132032 80118.3 133606 85867.3 133709 82758.3 C 133956 88740.5 135280 77590.4 134572 84084.8 C 137466 79282 134311 87520.2 137698 81351.3 C 136410 85954.4 139151 80963 139667 81706.9 C 141780 77740.2 138008 88372.5 141421 80851.9 C 142007 80062.7 141117 84775.7 143277 79934.4 C 142255 84618.9 147577 74261 143691 82504 C 148781 75645.7 141799 87727 147415 80230 C 143135 86894.6 152620 75869.7 148029 83014.1 C 151242 79375.9 154100 75345.8 149903 82531.4 C 154855 75827.8 151201 82975.4 153671 80613.2 C 158562 71090.3 151020 88844.6 156725 78607.5 C 153524 86483.2 156803 79409.5 158170 80268.5 C 160185 73209.9 160417 74465 160308 79187.7 C 161380 73152 162281 74831.8 161186 80024.2 C 163327 75219.2 162818 71689.3 163180 79148.8 C 164069 72647.2 164368 69957 164516 78268.3 C 165320 77268.3 164945 65620.9 165962 76362.7 C 166557 79880.9 166065 65817.8 167534 75193.7 C 166429 66661.5 168056 75418.2 168343 73166.9 C 166174 66876.6 171465 75658.6 167884 68861.7 C 172677 76599.7 165722 62466 170985 70515.1 C 165611 61843.2 171849 70276 168728 65109.4 C 173370 68679.9 165897 61083.2 171312 66088.6 C 167776 62552.7 170686 64490.8 169502 62292.6 C 174528 67820.1 166824 58670.6 170483 61484 C 169203 59398.7 169027 58878.2 168643 57931.1 C 172088 58659.3 167555 55644.3 170169 56303.6 C 163413 52348.4 165389 56419.8 163453 56865 C 160982 57210.4 162645 58891.8 163773 59198.9 C 157987 57589.2 166075 61249 159040 58717.2 C 167406 62718.9 149130 56969.5 157627 60546.4 C 154505 59785.7 149835 57698.5 152840 60446.5 C 143904 57904.7 142389 46345.7 133595 43021.5 C 125120 42992.3 121319 54524.8 117275 57879.2 C 112673 60895.4 112169 60086.5 113527 58583.9 C 109078 59876.2 106187 60231.9 107896 59187 C 96651.6 61499.5 108366 58396.7 104295 58687 C 101667 58986 103590 57473.7 102230 57413.9 C 101511 56313.6 101079 56295.3 100608 55381.6 C 100912 52677.5 91667.9 57208.5 97229.7 56842.8 C 92858.9 59396.4 100636 56473.8 94981.9 59694.6 C 97083.5 59308.9 94963.3 61049.3 95307.6 61513.7 C 91423.5 65673.4 99163.2 58824.1 93860.4 64586.3 C 99482.3 58732.9 95613.5 65191.3 94797.2 64467.3 C 93196.8 68453.3 99934.6 59845 94833.1 66766.7 C 100433 61302.7 92251.9 72205.5 96832.6 67089 C 92976.2 72494.8 95407.8 70159.3 97950 66897.5 C 95624.6 70037.2 94477.2 75005.3 97817.4 68393.5 C 96398.5 71374.8 97248.5 78724 98096 71246.5 C 98816.1 79084.8 98695.4 74730.2 99833.4 70990.7 C 98943.1 74376.9 100082 80524.1 100188 73046.1 C 101042 79506.8 100857 76750.9 101875 72497 C 101887 84021.1 102753 71524.5 103284 76954.6 C 104561 84743.4 103247 68474 104839 78743.5 C 106022 82527.7 104347 68507.9 105764 77380.9 C 108452 84976.8 105030 71941.6 107808 80148.3 C 109665 83487.4 106480 73136.2 109379 81394.7 C 110420 82357 107635 72109.5 110110 80155.5 C 112002 83044.7 109371 75253.8 112074 80697.6 C 112838 79604 116414 85598.5 112643 78153.9 C 114283 80485.9 117690 85518 114315 78920 C 119583 85719.8 116171 79933.9 115979 79064.2 C 118419 82628.8 120498 84260.4 117808 79688.8 C 122768 85530.4 116012 74990.6 122786 82847.4 C 120267 76165.5 126313 87679.7 123668 80832.8 C 127446 87952.4 123037 76259.7 126979 83753.9 C 127617 83913.7 125837 79677.1 128849 84037.7 C 126177 77137 132961 90215.6 129915 81759.1 C 131687 85803.3 130866 81559.7 132370 85188.9 L 132285 83360.3 Z "
        "M 121019 80392 C 118433 76514.4 123274 83110.3 121019 80392 Z "
        "M 158073 79048.9 C 158773 73537.7 158295 80912.8 158073 79048.9 Z "
        "M 130084 77897.7 C 129347 77512.6 127688 76854.6 126791 77619.8 C 125313 75642.5 124993 75223.6 122737 73557 C 120580 71497.9 126906 72673.4 127575 72931.8 C 129031 73613.1 130756 73590.7 132350 73790.2 C 134133 73323.7 136264 74598.8 136757 72815 C 137939 73017.8 140292 72205.1 141925 72252.1 C 145119 73421.6 139435 74563.1 140217 75598.3 C 138985 74770.8 138932 77321.2 138084 76554.9 C 136233 77954.8 135874 77200.8 135102 77770 C 134477 78614.1 133161 76567.3 132436 78906.8 C 131666 77358.1 131148 78200.3 130649 78025.9 C 130629 79568.5 130386 79013 130084 77897.7 Z "
        "M 157044 77641.9 C 157323 76427 157194 79182.9 157044 77641.9 Z "
        "M 119572 70378.7 C 115960 68012.7 111803 67394.1 110868 66844.6 C 106469 68403.6 109686 64076.9 111623 64341.7 C 114206 63157.9 115949 65193.2 116627 65637.7 C 115671 66484.3 121066 66548.9 118365 67025.5 C 122040 71277.6 137624 63813.6 126388 67459.1 C 134311 63945.6 128287 66068.5 127118 66002.6 C 133238 63679.3 130920 63960.5 126367 65136.6 C 134083 62887.9 125648 64532.9 129005 63270.6 C 121611 62771.1 130094 63055.3 125208 61502.7 C 125940 61129.7 122185 56989.5 126758 61479 C 128467 64927.6 118963 49923.2 129188 49734.6 C 140432 44127.4 143097 61670.5 138654 62556.3 C 137692 60959.4 143183 58148.2 136402 62540.3 C 143810 64497.1 131946 61768.1 139127 64412.6 C 129923 61827.6 140435 65518.8 137255 64844.2 C 130367 62936.9 144183 67845.1 134850 65088 C 142744 68258.5 127166 62058.4 136475 67458.1 C 143128 70603.5 147203 65770.2 152028 64611.3 C 150332 62536.7 157874 64028.8 156739 67025.7 C 155998 67328.9 153657 67309.1 151566 67712.5 C 151434 68537.6 146678 70585.4 143666 70491.6 C 135256 68830.6 127978 70043.5 119572 70378.7 Z "
        "M 129458 59043.2 C 127809 57241 123405 59558.2 129458 59043.2 Z "
        "M 138299 58944.2 C 140594 56876.8 131024 60485.8 138299 58944.2 Z "
        "M 127188 52607.8 C 132189 53155.7 145970 54546.4 134851 50620 C 131941 47098.1 121974 56573.2 127188 52607.8 Z "
        "M 166819 68240.5 C 165067 66377.3 168985 70037.1 166819 68240.5 Z "
        "M 113504 68203.9 C 114503 67369.8 114530 68658.1 113504 68203.9 Z "
        "M 141261 67603.4 C 144355 65991.5 141725 68432 141261 67603.4 Z "
        "M 122714 67245.7 C 124406 66492.4 124403 67678.5 122714 67245.7 Z "
        "M 137551 67031.1 C 127297 63855.8 146524 68409.2 137551 67031.1 Z "
        "M 145354 66769.5 C 145663 65834.2 145985 67680.8 145354 66769.5 Z "
        "M 157217 65042.7 C 156329 63952.4 158889 66361.9 157217 65042.7 Z "
        "M 125736 64292.4 C 126857 63926 125846 64784.6 125736 64292.4 Z "
        "M 96620 60629.8 C 98494.8 59557.2 95985.7 61637.3 96620 60629.8 Z "
        "M 97153 55421.4 C 98156.2 54845.4 99547.5 55269.3 97153 55421.4 Z "
        "M 88689.6 71533.5 C 87825 70495.7 87480 70827 88689.6 71533.5 Z "
        "M 171192 62676.4 C 168837 60794.8 172570 64434.9 171192 62676.4 Z "
        "M 158705 55368.2 C 168660 55510.4 167172 35740.9 163879 36684.3 C 167958 43809.1 163460 53752.3 158705 55368.2 Z "
        "M 169913 55098.7 C 164127 51386.6 170766 56873.6 169913 55098.7 Z "
        "M 98577.1 53910.5 C 96480.9 53572.6 98009.8 51301.5 96875.9 50087.9 C 96614.9 49681.6 97354.4 47688.7 94917.5 45397.3 C 90004.1 44450.4 88403.6 46723.6 87871.2 48423.9 C 83892.6 49850.5 96217.6 48434.7 86515.1 50127.5 C 90979.5 48117.6 93981.2 52396.3 94686.4 54362.2 C 94222.2 55427.8 96965.2 55045.7 98577.1 53909.9 Z "
        "M 108254 54911.7 C 98332.7 53043.2 99688.1 40599 102220 35140.6 C 94098.3 41920.9 102335 57439.9 109660 55297.8 C 109191 55169.1 108723 55040.4 108254 54911.7 Z "
        "M 170716 54618 C 170517 48752.9 182628 50647.6 174433 49155.9 C 180324 49029.1 174901 46785.4 176692 45958.7 C 172698 43069.1 167833 47740.4 168825 49553.2 C 169144 50768.9 167294 51342.3 169000 52513.2 C 164699 51589.4 171181 55746.5 170716 54618 Z "
        "M 155646 53170.6 C 165289 52837 158110 31674.5 160489 45155.1 C 156624 62074.3 133309 43124.9 149415 36349.2 C 153526 35613.8 160912 37203.3 151929 35016.5 C 135075 36040 146716 61567.6 158370 50284.9 C 163476 44428.7 153362 57960.4 148582 52669 C 139933 47630.9 152324 56957.3 155646 53170.6 Z "
        "M 117342 52396.5 C 121240 51052.9 104751 55461.1 104932 46963.4 C 103547 42046.3 106198 32083.4 103164 43106 C 103036 49960.6 110965 55483 117342 52396.5 Z "
        "M 117154 51608.8 C 132533 45756.6 111882 29251.3 110804 35676.8 C 127907 31818.9 120896 60055.6 107597 49323.9 C 103139 46622.1 107686 33008.2 104549 43529.6 C 104948 49537.3 111294 54611.5 117154 51608.8 Z "
        "M 162390 51119.3 C 162522 49587.1 160934 53565.5 162390 51119.3 Z "
        "M 121789 49372.9 C 125237 44959.3 117802 53133.7 121789 49372.9 Z "
        "M 162421 45709.5 C 163100 39635.9 158723 35399.6 161685 44206.6 C 161863 47564.9 160848 51142.1 162421 45709.5 Z "
        "M 142361 47263.1 C 138877 37840 151876 31974.2 157359 34934.4 C 147735 28855.7 138874 41287 142361 47263.1 Z "
        "M 96544.8 44193.3 C 96152.9 44692.5 96929.5 46745.5 96544.8 44193.3 Z "
        "M 97662.2 45129.8 C 98355.9 38970.1 96081.2 43028.9 97662.3 45129.8 Z "
        "M 97663.2 43084.7 C 98032.4 42403.4 97777.4 44187.8 97663.2 43084.7 Z "
        "M 164324 42830.3 C 162879 34548 164762 49642.8 164324 42830.3 Z "
        "M 168757 43650.3 C 167972 40323.4 167658 43200 168758 43650.3 Z "
        "M 131156 41421.3 C 138952 42928.3 137961 41181.4 130744 40883.5 C 125685 42449.6 127895 42536.5 131156 41421 Z "
        "M 122694 39937 C 123491 30426.9 99859.8 34364.2 113621 33648.5 C 117719 29941.5 125848 47355.1 122694 39937 Z "
        "M 140826 40867.6 C 142490 33294 116229 36626.6 126336 41649.4 C 124960 32832.9 126761 45819.5 132736 40327.2 C 134607 38736.6 139420 35849.9 139544 42431.7 L 139999 42362.5 L 140826 40867.7 Z "
        "M 137039 40931.6 C 132514 39016.9 139568 42674.8 137039 40931.6 Z "
        "M 164924 41187.4 C 164293 40276.1 164615 42122.8 164924 41187.4 Z "
        "M 138181 39364.6 C 137870 37164.1 137274 40271.4 138181 39364.6 Z "
        "M 129864 34280.3 C 131293 35545.7 132984 33944.4 133779 35251.4 C 135647 33895.6 135856 34715 137136 34852.2 C 139817 32846.2 138655 34492.2 140784 32856.3 C 141232 33486 143845 29943.5 143568 31608.8 C 143789 31672.6 146258 30500.2 146313 30742.9 C 145875 31992.2 149923 29862.9 149945 30937.8 C 153925 30426.3 149371 30940.9 154756 31760.2 C 155028 30055 160023 35959 159871 31483.2 C 154995 28085.2 154336 27655.9 150151 26527.8 C 148707 25437.9 144130 26695.8 143781 25849 C 141826 24634.6 142698 25500.8 139904 25347.7 C 137907 24407.8 136154 26652.1 135581 24687.8 C 134570 28922.8 131903 22378.8 132145 26123 C 132241 26412.3 129887 25426.6 129234 25322.6 C 128683 26057.6 124508 24574.8 124249 25307.6 C 123016 25887.7 120316 25880.1 118310 25904.7 C 118124 25892.3 110658 26732.2 111841 27867.5 C 104554 29241.2 113499 28086.3 105238 31294.1 C 108374 33195.4 118308 30151.1 116840 30413.1 C 120101 32481.5 117055 27381.6 122615 32594.5 C 120724 29574 124868 33216.8 124377 32340 C 125496 32843.5 126990 35512 129864 34280.3 Z "
        "M 131591 31114.5 C 129898 29460 135544 29728.2 132447 31346 L 132137 31432.7 L 131591 31114.5 Z "
        "M 128306 30506.9 C 125613 27072.1 130202 32286.7 128306 30506.9 Z "
        "M 129621 30187.1 C 128806 27934.1 130983 31851 129621 30187.1 Z "
        "M 134243 30442.9 C 134660 28533.4 135447 29788.9 134243 30442.9 Z "
        "M 137295 30451.7 C 138965 28537.5 142712 28219.1 137295 30451.7 Z "
        "M 135249 30278.7 C 135800 28827.8 136258 29322.1 135249 30278.7 Z "
        "M 126679 29831.4 C 121930 26915.5 129694 30769.1 126679 29831.4 Z "
        "M 136508 29582.7 C 138716 27119 135295 31661.2 136508 29582.7 Z "
        "M 120510 31330.4 C 118900 29362.2 121280 33546.1 120510 31330.4 Z "
        "M 119644 30954.6 C 119013 30043.3 119334 31889.9 119644 30954.6 Z "
        "M 142555 21291.9 C 141054 21926.8 141703 22401.7 142555 21291.9 Z",
    ),
    stroke=(),
)

icon_meerk40t_transparent = VectorIcon(
    stroke=(
        "[width=2,0x808080]M 3.6469929,87.296135 C 1.4593631,82.123996 0.24965244,76.437523 0.24965286,70.468506 C 0.24965328,64.49949 1.4692349,58.822837 3.6618002,53.655609 C 5.8543654,48.488382 9.0199143,43.830578 12.911849,39.899261 C 14.835249,37.956398 16.942335,36.201205 19.212349,34.65937 C 20.347356,33.888452 20.914956,33.441158 22.128833,32.78013 "
        + "M 25.88228,30.969908 C 31.032508,28.791042 37.359559,27.298072 43.481094,27.237064 C 49.449814,27.177584 55.136584,28.446775 60.308722,30.634405 C 61.601756,31.181312 61.612581,31.282557 62.837702,31.948083 "
        + "M 65.29003,33.157969 C 65.884253,33.519029 67.077222,34.231865 67.652204,34.620315 C 69.952131,36.174115 72.094501,37.943422 74.050339,39.89926 C 81.873691,47.722612 86.712535,58.530473 86.712536,70.468506 C 86.712537,76.437523 85.980625,81.263957 83.792995,86.436096 "
        + "M 79.329286,94.639617 C 77.775485,96.939544 76.006179,99.081914 74.050341,101.03775 C 66.226981,108.8611 55.419128,113.69995 43.481094,113.69995 C 31.543061,113.69995 20.7352,108.86111 12.911848,101.03775 C 10.95601,99.081915 9.1867035,96.939545 7.632903,94.639617",
    ),
    fill=(
        "[red]M 20.326051,28.370775 L 23.19782,30.127621 L 36.137667,43.101256 L 36.070097,42.357975 L 37.286374,42.357975 L 39.245933,43.743181 L 39.446257,44.819716 L 39.398477,45.190011 L 39.135687,45.85893 L 38.526492,46.850363 L 37.690343,47.244548 L 36.50779,47.065373 L 34.620483,45.35724 L 34.871329,44.401642 L 35.659697,44.616652 L 28.492709,36.756855 L 20.326051,28.370775",
        "[red]M 68.571755,28.607274 L 65.970271,31.445256 L 54.719696,42.797186 L 53.435848,44.621604 L 53.131778,47.020375 L 51.104646,47.696085 L 49.516728,46.885233 L 48.933928,46.201076 L 48.604519,45.432456 L 48.950822,44.123267 L 50.716114,42.771847 L 52.329374,42.518456 L 52.47296,43.168827 L 57.287395,38.675355 L 62.203187,33.76801 L 64.68642,31.335453 L 65.032723,31.014491 L 68.571755,28.607274",
        "M 37.20854,46.397556 C 39.89356,46.128618 37.0092,41.275614 38.777491,44.807376 C 39.73453,46.098147 35.715005,46.857576 37.20854,46.397556 L 37.20854,46.397556",
        "M 50.247035,46.548987 C 47.867535,45.375054 51.44748,41.730663 49.534851,45.16599 C 49.279839,46.389785 52.536754,46.985181 50.247035,46.548987 L 50.247035,46.548987",
        "M 60.310473,56.469843 C 62.106234,55.249112 59.527575,57.262886 60.310473,56.469843 L 60.310473,56.469843",
        "M 50.220818,110.85977 C 44.835028,109.20671 51.797902,98.480295 44.662726,102.36465 C 42.135185,102.83457 38.396961,99.675188 40.070954,104.15434 C 42.002724,108.55121 36.277301,114.04691 34.028931,108.03191 C 33.815443,104.88071 34.455851,102.4209 30.912611,101.25864 C 27.133819,101.02138 26.296224,96.70493 23.58394,95.244059 C 21.074675,97.073383 17.730553,101.25082 16.024733,95.949041 C 11.080792,91.642671 3.5697484,94.089561 -1.0865607,97.656713 C -2.7236997,99.112832 -4.183106,101.02902 -2.5372538,97.838668 C 0.11765216,93.144064 3.7335932,89.075115 6.6099773,84.521353 C 2.1572827,81.718357 7.2126602,77.050746 10.381997,75.704808 C 12.552997,76.048894 14.40568,75.151967 16.234445,74.09848 C 19.733736,73.434938 21.377671,71.047415 23.215651,68.249789 C 26.049605,65.50694 29.769122,65.335621 32.293129,62.790498 C 35.076971,63.486664 32.529236,59.98596 32.549824,60.982481 C 31.508912,59.798212 30.911942,59.898384 29.874469,57.872471 C 29.695512,58.184127 29.538847,57.474416 29.271638,57.009423 C 29.415296,57.392103 26.384405,55.629235 28.359438,56.484978 C 26.18019,55.745014 25.348668,53.64162 25.65757,53.743777 C 24.893629,53.058895 24.498734,51.548412 24.565394,49.348519 C 24.841172,47.66764 25.190983,45.777318 27.439233,45.075 C 30.816726,44.97838 29.927322,43.492832 31.180081,41.716603 C 31.362019,38.304738 25.348893,35.293768 23.358938,31.919985 C 22.190862,30.66732 18.177143,26.139675 21.514877,29.518687 C 26.489798,34.620292 31.649209,39.585031 36.217169,45.05431 C 32.606647,43.066814 37.462455,49.673557 38.971151,45.842448 C 41.231291,43.371783 33.964576,41.184761 36.792039,43.835191 C 31.889721,39.580518 27.422255,34.734109 23.003896,29.959239 C 26.46888,33.003753 29.66331,36.339604 32.925498,39.597658 C 34.092963,38.725838 32.105025,39.367066 34.48203,38.390215 C 32.833979,38.491903 35.61764,37.809059 34.977786,37.679264 C 36.368997,37.171357 38.458711,36.710901 39.016901,36.401941 C 40.353311,36.408141 40.00471,35.945442 41.417535,36.087815 C 42.109817,35.865469 43.060483,36.45444 43.704691,36.028185 C 44.24621,36.111255 44.979737,36.334902 46.23438,36.087595 C 47.622687,35.960348 47.013165,36.136425 48.116856,36.190525 C 48.510753,36.672682 49.68052,36.680893 51.43693,37.001672 C 52.161127,37.521338 53.390287,37.621333 53.871063,38.424728 C 54.53572,39.100383 55.831909,40.710432 57.502463,37.971243 C 59.804265,35.681525 63.119245,32.36849 65.079757,30.971221 C 60.658858,35.52635 56.297771,40.185275 51.488976,44.328678 C 55.033892,40.42427 45.311554,44.796772 50.147972,47.012892 C 52.418174,48.384105 54.238135,43.475163 52.198101,45.242637 C 57.390079,39.346709 63.072845,33.885941 68.741217,28.450617 C 64.857655,32.920572 60.67553,37.124991 56.512034,41.334202 C 57.380701,42.338156 58.947427,44.550341 57.751926,43.804972 C 59.240451,45.068163 63.598745,46.007122 62.938442,47.289612 C 63.382255,48.090271 63.800464,50.785927 63.171539,52.671044 C 61.79977,54.034562 63.067909,54.618027 59.820117,56.515258 C 58.883764,57.37095 58.665545,57.024777 58.51164,58.155676 C 57.940875,58.410709 56.492936,60.351093 55.917122,60.759385 C 55.229579,61.548916 54.330434,61.177612 54.345025,62.435878 C 57.384399,63.700566 60.788672,64.884575 63.424004,67.331495 C 66.948541,70.062368 68.80859,74.004004 73.669069,74.972108 C 77.827815,75.332157 81.900617,77.147136 83.527372,81.450563 C 82.313308,83.548116 80.708414,85.008742 83.564772,87.224988 C 86.457525,91.41409 90.107292,95.212103 91.91647,100.04601 C 87.746094,95.161364 80.252182,91.926196 74.069953,94.74144 C 71.512454,96.011618 69.509856,102.68646 67.058606,97.370289 C 63.4919,93.37622 61.434605,102.02601 57.349775,101.2681 C 51.230266,102.49556 57.239176,110.48152 50.220814,110.85977 L 50.220818,110.85977 "
        + "M 35.512597,108.62467 C 35.547887,106.90365 34.985487,100.11564 34.36143,105.441 C 34.230783,108.30899 34.9346,108.1816 34.936073,105.70107 C 34.840493,104.71642 35.701694,111.68719 35.512597,108.62467 L 35.512597,108.62467 "
        + "M 52.622756,108.98344 C 53.023763,106.57859 53.277031,104.44205 53.284049,108.31921 C 54.528411,106.83635 53.009009,100.48481 52.759314,105.26833 C 53.243916,105.4687 51.693377,111.39306 52.622756,108.98344 L 52.622756,108.98344 "
        + "M 52.606226,104.60905 C 52.401853,102.11504 52.416386,108.76023 52.606226,104.60905 L 52.606226,104.60905 "
        + "M 35.626586,103.76244 C 35.433928,105.69763 35.873182,106.75247 35.626586,103.76244 L 35.626586,103.76244 "
        + "M 36.087569,105.32978 C 35.923149,105.4567 36.234338,105.98329 36.087569,105.32978 L 36.087569,105.32978 "
        + "M 54.775213,102.23845 C 60.952189,99.366326 61.763619,91.076865 58.997821,85.522496 C 57.193868,89.541617 57.259933,94.10859 55.075804,97.983244 C 56.588582,96.970575 57.590638,90.480198 57.681333,91.929132 C 57.971258,93.924625 55.479266,98.531947 55.552675,98.561996 C 57.252396,97.396433 58.194962,91.484351 58.280104,91.692306 C 58.467792,94.065758 56.103917,99.087185 55.544246,99.502779 C 57.17725,97.69071 59.152086,95.5266 56.793086,98.849656 C 54.071852,102.76754 60.997296,93.683852 57.66767,98.603484 C 55.74215,101.27735 57.253453,99.718218 58.416123,98.065495 C 58.202449,100.17049 52.215579,103.10673 56.394379,100.93177 C 55.182588,103.03101 48.680543,101.96137 53.913915,102.51448 L 54.775217,102.23853 L 54.775213,102.23845 "
        + "M 57.059051,98.664506 C 57.489308,98.040547 56.847469,99.327317 57.059051,98.664506 L 57.059051,98.664506 "
        + "M 56.940647,97.617139 C 58.09353,95.62172 59.299489,89.722673 58.070877,95.275249 C 57.818804,96.102771 57.544312,96.969458 56.940647,97.617139 L 56.940647,97.617139 "
        + "M 57.755917,90.628769 C 57.835647,90.008247 57.835647,91.249291 57.755917,90.628769 L 57.755917,90.628769 "
        + "M 35.82514,102.4281 C 37.694131,102.56683 30.122491,101.24349 32.64931,101.35252 C 34.112353,102.28661 28.332407,98.148519 29.276599,96.272082 C 29.57711,98.578904 33.821063,102.36023 30.477134,98.30515 C 28.871042,93.979023 30.355935,98.447244 32.028448,99.6121 C 30.005641,98.511999 28.827107,89.196476 30.052719,94.896242 C 30.031069,97.04666 34.091063,101.58597 31.18027,97.22824 C 30.233965,94.883787 29.232194,89.182869 30.598801,94.591626 C 30.788816,96.624362 34.467908,101.06428 31.808886,96.954379 C 30.702324,95.489295 29.81286,88.046233 30.942043,93.231429 C 31.232722,95.253323 34.436106,100.44316 32.033983,95.755529 C 30.874864,93.031114 30.443889,86.72434 28.895891,85.949313 C 26.432059,91.394272 27.463568,98.987803 33.069911,102.04649 C 33.892415,102.53834 34.903511,102.60111 35.82514,102.4281 L 35.82514,102.4281 "
        + "M 29.696222,91.025375 C 29.775952,90.404853 29.775952,91.645897 29.696222,91.025375 L 29.696222,91.025375 "
        + "M 53.839189,102.07038 C 53.446327,101.86193 53.746939,102.29361 53.839189,102.07038 L 53.839189,102.07038 "
        + "M 34.184584,101.93198 C 33.173743,101.49453 34.455696,102.33957 34.184584,101.93198 L 34.184584,101.93198 "
        + "M 54.235796,101.97118 C 53.842925,101.76272 54.143546,102.19441 54.235796,101.97118 L 54.235796,101.97118 "
        + "M 47.56996,99.010886 C 51.752073,97.634167 55.805628,94.242208 56.439681,89.686835 C 54.475451,93.464235 50.762089,96.019434 46.839914,97.504083 C 49.516945,97.114023 52.261368,94.822559 53.774883,93.487262 C 52.454452,95.541457 48.026939,97.504294 47.332761,98.013052 C 49.26085,97.483679 53.932147,94.76243 49.80796,97.299981 C 47.765026,98.296109 45.397098,99.295913 48.99723,98.012618 C 51.33937,97.189448 44.756903,99.97633 47.56996,99.010886 L 47.56996,99.010886 "
        + "M 40.672334,98.923966 C 38.404838,97.822343 37.385319,96.885211 40.239648,98.376731 C 42.398232,99.44049 32.628747,93.899559 38.07311,96.834414 C 39.55865,97.70981 43.525167,98.845825 39.813443,97.410153 C 37.953992,97.161632 32.006283,91.49789 36.083026,94.945482 C 37.603706,96.501769 43.61333,98.383569 38.613549,96.257955 C 35.887251,95.668777 32.350741,90.071217 31.751304,90.513769 C 33.118853,94.720527 36.941637,97.851338 41.075569,99.146769 L 40.67233,98.923969 L 40.672334,98.923966 "
        + "M 45.289491,94.737206 C 49.695345,91.324236 53.916249,87.526063 57.068805,82.892206 C 55.0299,80.804954 53.004151,78.704916 50.960884,76.621912 C 46.387264,77.111386 41.755873,77.138162 37.182087,76.635372 C 35.421174,79.434675 28.687472,82.282931 32.970835,85.49027 C 36.286759,89.219469 39.963721,92.711107 44.049393,95.585388 L 44.475314,95.335901 L 45.289491,94.737201 L 45.289491,94.737206 "
        + "M 42.617699,93.970735 C 40.466441,92.9259 39.654806,91.153824 40.084065,88.907064 C 40.174955,86.470376 39.491377,80.442893 41.246275,85.997224 C 41.82331,87.625035 43.278601,92.520966 45.224209,89.812123 C 46.251132,88.013594 48.469941,80.248529 48.044085,85.888562 C 47.868926,87.92223 48.308854,90.246628 47.815629,92.137217 C 46.158878,92.984727 44.309036,96.308799 42.617699,93.970735 L 42.617699,93.970735 "
        + "M 35.309133,87.334774 C 32.554669,85.141222 30.586347,82.377238 34.397638,80.194969 C 35.995409,78.198355 37.619393,76.332786 40.373023,77.416586 C 43.830253,77.541761 47.301882,77.525309 50.742791,77.134535 C 52.574224,79.144369 54.839967,80.906913 56.332127,83.121691 C 55.258568,84.191493 51.660813,89.951311 51.393224,87.755085 C 51.391224,84.837673 51.389124,81.920261 51.387124,79.002849 C 47.977344,78.590469 45.539063,79.671565 44.881192,83.356767 C 43.303836,87.878789 42.876802,79.753142 40.788081,79.170785 C 39.549384,79.537441 36.711295,78.277386 36.710506,79.903095 C 36.694726,82.852202 36.678956,85.80131 36.663186,88.750417 C 36.211828,88.278536 35.760469,87.806655 35.309111,87.334774 L 35.309133,87.334774 "
        + "M 1.5143535,94.271424 C 4.7058671,91.903206 7.8524727,89.452437 10.685815,86.657808 C 7.4483278,89.196269 4.4204054,92.028601 1.006801,94.322269 C 4.212933,90.80972 8.4337436,88.374334 11.578174,84.792417 C 10.057968,86.303627 2.5462186,91.92545 7.5930411,87.718826 C 9.0329408,86.617117 14.136287,81.463209 10.193439,85.003693 C 8.9033041,86.174448 4.4258352,89.746911 8.2732918,86.393421 C 10.565198,84.939513 13.68031,81.1626 8.8126582,82.263922 C 6.2131223,86.878011 2.8028146,90.969239 -0.04710341,95.423138 C 0.47951921,95.047606 0.99561231,94.65767 1.5143535,94.271424 L 1.5143535,94.271424 "
        + "M 9.991758,84.292726 C 11.131007,83.135081 10.8903,83.775926 9.927881,84.401192 L 9.991758,84.292726 "
        + "M 88.320499,95.118445 C 85.359587,90.777359 82.070668,86.607107 79.246663,82.20704 C 75.380277,81.303233 76.26304,83.827975 78.629372,85.168098 C 79.875714,86.22199 85.147848,90.72288 80.841103,87.293756 C 79.183317,85.986276 74.101987,81.672423 78.281748,85.56335 C 79.84431,86.954675 85.483442,91.783262 80.764059,88.094784 C 79.374364,86.990784 74.290425,82.755 78.201976,86.34967 C 80.470576,88.57819 86.69311,92.970087 86.64515,93.889345 C 84.103513,92.122786 79.106704,87.619839 78.324162,87.350018 C 81.210083,89.938372 85.796143,93.823301 88.3205,95.118444 L 88.320499,95.118445 "
        + "M 78.593266,84.724993 C 76.207907,82.747893 76.565455,82.614722 78.701672,84.654923 L 79.20951,85.156382 L 78.593266,84.724993 "
        + "M 51.064018,92.082385 C 53.452628,90.94766 57.381179,85.55529 57.384183,85.828235 C 55.997322,87.995301 54.295991,89.690779 53.815448,90.480397 C 50.721817,94.002754 58.773188,85.348241 54.776641,90.258837 C 52.678554,92.687052 54.499824,91.09323 55.527849,89.77873 C 54.462497,91.324356 52.380428,93.43249 55.123461,90.937498 C 57.467334,89.325931 59.313701,83.26316 58.158695,82.31306 C 57.866551,84.539358 54.289308,87.808265 54.259929,88.350454 C 56.02395,87.520935 59.719263,80.13526 57.042989,85.575599 C 56.529249,87.448484 49.854369,92.896843 51.064018,92.082385 L 51.064018,92.082385 "
        + "M 56.146516,88.406385 C 57.541395,86.310878 57.578632,86.997781 56.146516,88.406385 L 56.146516,88.406385 "
        + "M 38.057406,92.323941 C 36.553832,90.968356 31.981469,87.393387 35.985098,90.784829 C 36.559278,91.285649 37.5975,92.100547 38.057406,92.323941 L 38.057406,92.323941 "
        + "M 53.370291,91.708027 C 52.820115,91.870883 52.754135,92.427729 53.370291,91.708027 L 53.370291,91.708027 "
        + "M 33.942233,91.157914 C 32.66001,90.01589 31.639817,88.131901 33.512698,90.490923 C 32.416757,89.004757 28.999998,84.424868 32.055803,88.2833 C 33.444005,90.308559 37.177926,93.333963 33.606471,89.752703 C 32.310416,88.377329 29.013364,83.273678 31.906126,87.257638 C 33.063201,89.175932 38.107694,93.543993 34.109758,89.470398 C 32.096182,88.239705 28.714413,79.767486 30.029319,85.828898 C 30.32382,88.197835 33.57121,91.421191 34.575625,91.763023 L 33.942233,91.157914 "
        + "M 34.234162,91.093504 C 33.63703,90.433233 33.223845,90.242951 34.234162,91.093504 L 34.234162,91.093504 "
        + "M 34.177062,88.521818 C 32.683273,86.793885 29.819093,83.690617 32.768166,87.254376 C 32.698836,87.175236 34.843217,89.410511 34.177062,88.521818 L 34.177062,88.521818 "
        + "M 6.7693528,83.62165 C 6.1469322,82.270421 6.2902494,84.001732 6.7693528,83.62165 L 6.7693528,83.62165 "
        + "M 81.768889,83.498903 C 82.86505,81.399039 78.947493,80.589374 81.279594,83.170436 C 82.587639,82.664883 80.656629,84.015236 81.768885,83.498903 L 81.768889,83.498903 "
        + "M 7.0860292,83.01883 C 9.2699931,79.554073 4.4115082,83.0565 6.8780416,83.275058 L 7.0860292,83.018807 L 7.0860292,83.01883 "
        + "M 7.7953305,83.018935 C 8.621604,81.241583 6.9300347,84.23278 7.7953305,83.018935 L 7.7953305,83.018935 "
        + "M 30.494564,83.118085 C 29.165037,80.561539 30.08197,83.003034 30.494564,83.118085 L 30.494564,83.118085 "
        + "M 80.452534,82.775214 C 79.736166,81.860353 81.06687,84.030234 80.452534,82.775214 L 80.452534,82.775214 "
        + "M 82.158274,82.44454 C 81.840584,82.054097 82.266761,82.936134 82.158274,82.44454 L 82.158274,82.44454 "
        + "M 58.146467,81.809712 C 59.14501,79.975838 56.483817,83.860095 58.146467,81.809712 L 58.146467,81.809712 "
        + "M 5.8491947,81.125078 C 5.7405155,77.20179 4.7990529,85.302279 5.8491947,81.125078 L 5.8491947,81.125078 "
        + "M 5.3812399,81.711038 C 5.5550012,81.189547 5.5353668,82.075396 5.3812399,81.711038 L 5.3812399,81.711038 "
        + "M 82.847667,82.237493 C 83.382184,81.381422 81.204395,77.876222 82.357214,81.469392 C 82.223422,81.313056 82.501703,82.587501 82.847667,82.237493 L 82.847667,82.237493 "
        + "M 31.16048,82.121619 C 30.637383,81.068312 30.823234,82.506165 31.16048,82.121619 L 31.16048,82.121619 "
        + "M 13.56119,81.90788 C 13.020698,81.387508 8.2460456,80.925315 12.165826,81.87972 L 12.715355,81.97551 L 13.561195,81.90788 L 13.56119,81.90788 "
        + "M 76.875047,81.607088 C 79.986062,80.495215 71.57004,82.344952 75.914405,81.899023 L 76.875047,81.607088 "
        + "M 15.551161,81.636318 C 17.110443,79.439152 16.506661,78.462039 17.378508,79.338645 C 17.453008,78.686421 17.971012,79.561856 17.90814,78.631488 C 18.586914,79.568616 18.055664,78.156222 18.76171,79.115339 C 18.09005,76.964011 19.603901,80.33285 19.006541,78.029968 C 20.120801,80.740064 18.935031,76.212523 19.980555,78.894274 C 20.711409,78.960574 19.357745,75.939393 20.623002,78.408361 C 18.893196,73.907753 22.352224,80.486251 22.833824,79.312942 C 20.749868,78.70099 19.935718,73.62707 21.576556,77.675559 C 24.072647,81.666302 19.336318,72.45218 22.011428,77.151666 C 22.506929,77.762304 20.360493,72.798172 22.351024,76.489081 C 23.918508,78.656414 20.481668,72.405604 22.490952,75.353192 C 21.312258,72.388187 25.103455,79.835667 22.996967,75.342052 C 21.400455,71.175374 25.270043,78.95529 23.243249,74.529352 C 22.526316,72.498574 25.698409,78.523148 23.706175,74.315341 C 23.477205,73.547169 26.484106,78.271993 24.767614,75.131261 C 22.529408,70.519144 26.991186,78.319901 25.233162,74.773413 C 23.529281,71.427723 28.201209,79.214699 25.753323,74.516743 C 23.72637,70.255922 28.947064,79.197244 26.458832,74.350357 C 24.544322,70.366124 30.36086,80.088253 27.688762,74.999553 C 26.410575,72.59485 26.388619,72.058502 27.813098,74.566301 C 30.038237,77.239586 32.445786,83.551057 35.233725,77.918659 C 36.359364,75.741324 38.401351,76.170302 40.44839,76.430346 C 44.00581,76.600416 47.573991,76.498546 51.115609,76.125231 C 52.602769,77.616565 54.089928,79.1079 55.577086,80.599236 C 57.511057,78.508815 60.807039,73.706517 61.381288,73.071535 C 60.375529,75.110921 58.841001,78.107222 61.351678,74.466964 C 63.965155,69.956675 58.818594,79.817355 62.288623,74.403134 C 64.822868,69.650529 60.083171,79.161071 63.015302,74.764419 C 65.523777,70.834909 61.139603,78.485844 63.726077,75.161026 C 65.92233,70.92117 62.125647,78.688989 64.698088,74.493793 C 65.887813,72.520394 63.079711,78.249026 65.110883,74.705021 C 66.680476,72.22402 62.892236,79.63914 65.444796,75.376987 C 67.191411,72.509162 63.326602,79.683355 65.845071,75.632155 C 67.340394,72.749674 64.475215,79.123285 66.805917,75.458477 C 65.564332,78.030573 65.265037,79.463215 66.854857,76.171613 C 67.331305,77.409373 62.8896,81.599656 66.576662,78.000327 C 67.902583,75.482212 67.260634,76.657575 66.979838,78.396571 C 67.518681,76.561663 67.244677,80.330871 67.619334,77.893403 C 67.818224,79.168959 67.917407,77.633595 68.140899,78.725687 C 68.591656,77.545452 68.718692,80.137353 69.486391,78.333846 C 69.25823,79.524952 69.773781,78.589008 69.806915,78.983969 C 70.101109,78.172939 69.902415,79.962006 70.29977,78.840196 C 70.496814,79.64519 70.657462,77.965679 70.825361,79.344293 C 70.743421,77.584223 72.469276,82.834237 71.026982,80.309099 C 72.73762,83.604941 71.025382,77.720158 72.139883,81.090366 C 74.702156,83.359135 70.042275,78.224329 73.18503,77.257452 C 76.042447,74.900627 68.656001,74.312286 67.104981,72.951375 C 64.69632,71.333029 61.829969,67.181208 58.632872,69.309844 C 54.330344,71.575957 49.915552,73.772869 45.202196,74.997621 C 49.891594,74.374991 37.720972,73.986077 42.612442,75.052501 C 37.214007,73.461015 32.442895,70.35068 27.219874,68.363203 C 23.475433,70.023358 20.852076,73.716705 16.685221,74.72822 C 13.948001,75.656613 13.515175,76.467406 15.661552,78.482674 C 18.280832,80.021795 12.96033,82.534025 15.551157,81.63632 L 15.551161,81.636318 "
        + "M 31.925624,79.201608 C 30.353335,78.244575 26.814064,70.989713 29.495258,75.452068 C 29.701483,76.161136 34.379488,81.540997 31.925624,79.201608 L 31.925624,79.201608 "
        + "M 55.764997,79.31661 C 57.06871,78.008017 61.316716,71.128066 58.67526,75.900739 C 58.388328,76.637083 54.752803,80.942647 55.764997,79.31661 L 55.764997,79.31661 "
        + "M 31.851211,77.827678 C 30.396971,76.37285 28.372535,72.192185 30.703285,75.994223 C 31.104487,76.667143 33.68959,79.836414 31.851222,77.827678 L 31.851211,77.827678 "
        + "M 55.90969,78.135736 C 57.206833,76.270078 59.8576,72.651699 57.126081,76.698047 C 56.716541,77.1704 56.408367,77.743528 55.90969,78.135736 L 55.90969,78.135736 "
        + "M 67.458211,77.590405 C 67.765526,76.318231 67.509261,78.222351 67.458211,77.590405 L 67.458211,77.590405 "
        + "M 15.028596,77.016736 C 13.519804,75.734059 15.692239,77.232056 15.028596,77.016736 L 15.028596,77.016736 "
        + "M 73.376834,76.514786 C 72.8308,76.208256 75.048213,76.121961 73.376834,76.514786 L 73.376834,76.514786 "
        + "M 72.696565,76.414152 C 73.679607,75.558086 73.052844,76.387802 72.696565,76.414152 L 72.696565,76.414152 "
        + "M 14.007371,76.249621 C 14.912069,75.716849 15.473393,76.652269 14.007371,76.249621 L 14.007371,76.249621 "
        + "M 15.277741,75.886701 C 15.712399,75.744713 15.320671,76.077462 15.277741,75.886701 L 15.277741,75.886701 "
        + "M 42.637201,75.888901 C 43.18321,75.727973 42.736291,76.062436 42.637201,75.888901 L 42.637201,75.888901 "
        + "M 45.167437,75.885901 C 45.82098,75.739183 45.294259,76.050381 45.167437,75.885901 L 45.167437,75.885901 "
        + "M 45.710879,75.789791 C 46.256888,75.628863 45.809969,75.963326 45.710879,75.789791 L 45.710879,75.789791 "
        + "M 42.940852,75.093671 C 43.375486,74.95164 42.983812,75.284474 42.940852,75.093671 L 42.940852,75.093671 "
        + "M 49.889672,74.854873 C 51.501666,74.246074 48.522554,75.526123 49.889672,74.854873 L 49.889672,74.854873 "
        + "M 38.965807,74.471949 C 36.984677,73.947403 32.153085,70.872815 36.672545,73.257328 C 37.220556,73.520476 42.176327,75.537605 38.965807,74.471949 L 38.965807,74.471949 "
        + "M 47.520385,74.831711 C 49.579846,74.057003 56.735058,70.88825 51.338561,73.569546 C 50.114177,74.109287 48.8449,74.614481 47.520385,74.831711 L 47.520385,74.831711 "
        + "M 50.706572,74.520141 C 52.371236,73.660002 51.115992,74.575561 50.706572,74.520141 L 50.706572,74.520141 "
        + "M 19.931638,73.509372 C 20.477647,73.348444 20.030728,73.682907 19.931638,73.509372 L 19.931638,73.509372 "
        + "M 67.722386,73.509372 C 68.268395,73.348444 67.821476,73.682907 67.722386,73.509372 L 67.722386,73.509372 "
        + "M 18.320435,81.39426 C 20.623812,80.943336 21.44825,79.541203 19.729915,80.47365 C 19.507856,80.242345 18.780898,80.128002 18.215117,80.769106 C 17.907748,80.053035 17.082878,81.325377 16.972021,80.693576 C 14.280631,82.696842 16.578789,81.515262 18.320435,81.394257 L 18.320435,81.39426 "
        + "M 31.755386,81.722771 C 30.69847,80.107446 30.533863,81.314671 31.755386,81.722771 L 31.755386,81.722771 "
        + "M 57.467739,80.88719 C 59.737927,77.854712 56.91162,80.519754 56.742426,81.804338 L 56.991974,81.534926 L 57.467739,80.88719 "
        + "M 72.068881,81.648224 C 69.496032,79.711829 70.520627,81.192421 68.758219,80.118771 C 69.105285,81.00813 67.608369,79.19415 68.229006,80.58749 C 63.343382,78.537435 73.192455,83.237094 72.068881,81.648224 L 72.068881,81.648224 "
        + "M 14.916383,80.73286 C 16.350102,77.972849 12.765659,79.797092 14.159585,81.308582 C 13.878611,80.282497 13.152513,80.491137 14.132705,81.388522 L 14.472683,81.237497 L 14.916388,80.732863 L 14.916383,80.73286 "
        + "M 16.488815,80.986344 C 17.132478,78.62138 15.627244,82.528256 16.488815,80.986344 L 16.488815,80.986344 "
        + "M 74.312029,81.234218 C 75.532917,79.920815 71.599634,81.676743 74.312059,81.234216 L 74.312029,81.234218 "
        + "M 31.592312,80.241301 C 29.460953,77.825461 29.679281,78.689312 31.502182,80.716562 C 32.136382,81.99242 32.860012,80.484419 31.592312,80.241301 L 31.592312,80.241301 "
        + "M 56.736479,80.422718 C 59.625165,76.558899 54.110841,82.58612 56.736479,80.422718 L 56.736479,80.422718 "
        + "M 73.894531,80.976323 C 75.640523,78.900057 71.32989,78.633092 73.149803,80.812826 C 72.476696,79.348772 73.813403,81.580478 73.894531,80.976323 L 73.894531,80.976323 "
        + "M 7.0783623,80.823409 C 8.3279044,78.550622 7.342806,77.166053 6.5395247,80.256216 C 7.380985,79.876327 5.9667749,81.420569 7.0783623,80.823409 L 7.0783623,80.823409 "
        + "M 81.45479,80.655816 C 81.680401,80.810731 81.102855,77.716038 80.486509,78.606716 C 80.067904,79.404068 81.959157,81.868013 81.45479,80.655816 L 81.45479,80.655816 "
        + "M 8.9017534,80.458843 C 9.6771279,79.146024 12.153784,74.347019 9.2281492,77.173023 C 11.170127,76.482448 5.8505027,80.429625 8.9506732,80.050194 C 8.5950815,80.193845 8.0960032,80.909056 8.9017532,80.458843 L 8.9017534,80.458843 "
        + "M 79.810692,80.443743 C 79.93346,79.968631 79.602462,77.738362 78.554581,76.995528 C 79.065169,76.19761 75.483146,75.696529 78.082232,77.773229 C 78.733124,78.469797 78.456584,80.667845 79.810692,80.443743 L 79.810692,80.443743 "
        + "M 11.303419,79.949394 C 11.804797,77.145565 12.339815,79.057408 12.722706,78.742069 C 12.908085,78.58061 12.802826,79.03349 13.965547,78.571185 C 16.371602,77.442564 10.16028,75.297864 11.204013,77.256391 C 8.9673222,79.42884 11.378576,79.569089 10.733841,80.281722 L 11.303432,79.949386 L 11.303419,79.949394 "
        + "M 20.33388,79.967424 C 20.053289,80.159073 20.216088,80.398724 20.33388,79.967424 L 20.33388,79.967424 "
        + "M 77.500656,80.075107 C 77.310867,79.488743 78.583315,78.736251 77.128508,77.191937 C 75.203534,74.407877 72.429827,79.141771 74.840687,78.780213 C 75.184897,78.988542 75.645722,78.727893 76.019624,78.525806 C 75.894316,77.262306 77.813743,81.303993 77.500656,80.075107 L 77.500656,80.075107 "
        + "M 75.290474,78.763557 C 75.001468,78.121156 75.447349,78.453403 75.290474,78.763557 L 75.290474,78.763557 "
        + "M 14.882195,78.901908 C 16.347311,78.523905 12.69408,78.828588 14.882195,78.901908 L 14.882195,78.901908 "
        + "M 73.539278,78.811038 C 74.575882,77.411956 71.629707,79.531806 73.539278,78.811038 L 73.539278,78.811038 "
        + "M 8.3709192,78.334054 C 8.6272685,77.377337 7.6572607,79.356246 8.3709192,78.334054 L 8.3709192,78.334054 "
        + "M 27.392747,78.532357 C 25.06088,77.959154 24.462669,78.571957 27.392747,78.532357 L 27.392747,78.532357 "
        + "M 62.4766,78.394399 C 62.779315,77.888846 58.481945,78.999628 62.003972,78.525743 L 62.476596,78.394399 L 62.4766,78.394399 "
        + "M 79.85589,78.307619 C 79.551172,78.06601 80.151311,78.839945 79.85589,78.307619 L 79.85589,78.307619 "
        + "M 8.388917,77.546748 C 7.7713506,77.889272 8.382177,78.415891 8.388917,77.546748 L 8.388917,77.546748 "
        + "M 80.14104,77.85813 C 79.726417,77.086905 79.400892,77.87351 80.14104,77.85813 L 80.14104,77.85813 "
        + "M 45.884396,73.173912 C 51.788667,72.605661 56.763374,68.8596 62.164832,66.91694 C 60.671394,66.639441 59.16527,67.224233 61.451092,66.336791 C 56.776104,66.859919 53.374081,71.084509 48.738769,72.040498 C 43.370627,73.735648 37.258074,72.632808 33.189888,68.623433 C 31.886607,67.453745 28.297031,64.758204 31.792723,67.05429 C 33.007378,67.949464 39.053357,72.437394 35.181297,69.013868 C 39.062402,72.384231 44.618647,73.561794 49.357378,71.268047 C 52.768505,70.128722 55.529729,67.755351 58.535826,65.980069 C 56.363431,67.839798 62.475984,64.996236 58.39823,64.912927 C 54.910722,66.575713 52.216797,70.055613 48.351363,71.328798 C 43.138263,73.757294 37.799378,70.793976 33.878222,67.422211 C 33.075028,65.318461 26.201048,64.523146 30.20379,66.445862 C 31.915655,67.747976 35.558758,71.109804 31.317734,68.400195 C 29.8976,67.464255 27.119207,66.584981 27.947604,66.492553 C 23.404847,66.770062 32.258546,68.437706 33.503228,69.976148 C 28.760909,68.218875 36.641977,71.667946 38.144711,72.191937 C 40.629919,72.969139 43.276991,73.427933 45.884396,73.173912 L 45.884396,73.173912 "
        + "M 54.013235,69.908714 C 55.79019,68.675894 60.013239,67.605762 55.888367,69.443504 C 55.413735,69.542254 54.324354,70.160391 54.013235,69.908714 L 54.013235,69.908714 "
        + "M 46.504088,71.387648 C 48.572509,70.484092 47.748441,70.103661 49.007644,69.455584 C 46.119292,70.20319 51.614225,68.1763 48.363164,68.912505 C 51.907771,67.721683 46.564919,69.074606 49.454445,67.931848 C 50.456366,67.292276 48.62721,67.641335 50.882675,66.484675 C 48.568068,67.272952 49.741894,66.868092 50.894285,65.828874 C 49.323597,66.379489 53.686628,63.598099 50.286814,65.457078 C 49.031908,65.805776 52.595852,64.090064 49.678988,65.246144 C 50.860923,64.350663 51.48826,63.573104 49.602548,64.809751 C 51.584262,63.43222 52.154942,63.040631 49.652118,64.099091 C 52.700846,62.401366 47.409758,64.836132 50.678215,62.765594 C 47.329554,64.587286 49.430416,63.439601 51.18186,61.836862 C 48.428828,63.495052 49.706429,62.544139 50.316949,61.864702 C 49.312996,62.301743 47.030603,63.912204 48.978919,62.047279 C 47.511285,62.841279 47.691174,62.785923 47.22293,62.767372 C 47.23747,62.300212 46.392527,63.119799 46.117517,63.268938 C 46.655547,61.649742 45.016905,65.091696 45.733594,62.636766 C 45.071634,64.173594 45.174386,62.024752 44.560008,64.105888 C 44.456677,62.605055 43.935083,64.460242 43.455173,63.423525 C 43.281987,64.025985 42.935427,63.339275 42.498786,63.187794 C 41.958256,62.468301 42.772563,64.632 41.611164,62.571056 C 42.684029,65.208546 40.253052,60.905714 41.359543,63.427348 C 40.387374,62.100367 39.958399,61.780631 40.93562,63.395188 C 38.965907,61.157951 40.94092,63.950981 39.007654,62.140608 C 41.242143,64.549733 35.869357,60.249192 38.568757,62.767336 C 36.357661,61.407259 37.47643,62.311995 37.970626,62.867066 C 37.472473,62.965256 40.571903,64.573583 37.456538,63.042809 C 40.725558,65.373916 34.3931,61.828499 37.902383,64.239489 C 36.025869,63.471251 40.50138,66.271151 37.208668,64.800435 C 40.60878,66.875068 33.962734,63.108665 37.778784,65.763332 C 39.53853,66.827075 35.44896,64.93675 38.045291,66.415263 C 40.710865,67.826033 35.072958,65.528384 38.43808,67.224075 C 39.943248,67.987124 36.402343,66.997067 39.241268,68.021945 C 36.939396,67.765763 42.203852,69.052347 38.529157,68.453542 C 41.187623,69.539157 37.299235,68.264265 39.83617,69.603348 C 39.183077,69.545378 39.092376,69.639058 40.856197,70.50113 C 38.747939,69.985517 41.546153,71.169719 41.835968,71.394283 C 43.367403,71.674775 44.966167,71.562147 46.504082,71.387683 L 46.504088,71.387648 "
        + "M 43.975954,71.046462 C 44.070424,70.399108 44.037324,71.817013 43.975954,71.046462 L 43.975954,71.046462 "
        + "M 43.977854,69.509623 C 44.053784,68.713928 44.053784,70.305311 43.977854,69.509623 L 43.977854,69.509623 "
        + "M 48.982758,67.65924 C 49.528767,67.498312 49.081848,67.832775 48.982758,67.65924 L 48.982758,67.65924 "
        + "M 43.973852,66.832548 C 44.053582,66.212026 44.053582,67.45307 43.973852,66.832548 L 43.973852,66.832548 "
        + "M 43.973852,65.444434 C 44.053582,64.823912 44.053582,66.064956 43.973852,65.444434 L 43.973852,65.444434 "
        + "M 22.410499,70.270739 C 24.435136,69.105243 26.750068,66.993975 23.185081,69.2658 C 23.015126,69.24129 21.270423,71.253232 22.410499,70.270739 L 22.410499,70.270739 "
        + "M 51.7839,69.071038 C 53.719795,67.749027 55.760421,64.94542 55.664094,65.926729 C 58.416492,64.179646 54.982628,62.155621 54.769714,65.493157 C 54.635403,66.530845 48.215991,71.694415 51.7839,69.071038 L 51.7839,69.071038 "
        + "M 65.133698,69.524231 C 60.882272,66.697594 64.287221,69.824644 65.133698,69.524231 L 65.133698,69.524231 "
        + "M 62.393051,67.520994 C 61.941278,67.340672 60.494493,67.879667 62.393051,67.520994 L 62.393051,67.520994 "
        + "M 29.177464,66.981273 C 28.070756,66.425542 29.800442,67.511152 29.177464,66.981273 L 29.177464,66.981273 "
        + "M 54.007052,65.994854 C 55.565872,63.611945 53.360177,61.973561 53.608367,65.399384 C 54.888495,63.525727 52.305432,68.596601 54.007052,65.994854 L 54.007052,65.994854 "
        + "M 34.199896,65.969784 C 32.819662,62.726773 34.926517,66.553441 34.412234,64.976784 C 33.771886,60.220356 32.689432,66.272268 34.199896,65.969784 L 34.199896,65.969784 "
        + "M 31.956462,65.005543 C 32.918838,63.304502 31.253667,62.837211 31.668182,64.963763 L 31.998906,65.299393 L 31.956456,65.005543 L 31.956462,65.005543 "
        + "M 37.357415,62.767348 C 37.001624,62.389869 37.234305,63.158234 37.357415,62.767348 L 37.357415,62.767348 "
        + "M 43.893125,60.273913 C 43.794895,59.017478 44.404796,61.245685 44.444815,60.040698 C 44.540595,62.359275 45.053738,58.037734 44.779059,60.554833 C 45.900909,58.693355 44.678187,61.886326 45.990733,59.495373 C 45.491438,61.279423 46.55377,59.344874 46.753722,59.633197 C 47.57289,58.09577 46.110739,62.216624 47.433785,59.301826 C 47.660822,58.995941 47.315718,60.822582 48.152943,58.946194 C 47.756857,60.76182 49.819581,56.747315 48.313601,59.942148 C 50.286467,57.284004 47.580047,61.966443 49.756812,59.060792 C 48.098221,61.643826 51.77404,57.370801 49.994693,60.13983 C 51.240016,58.729749 52.347949,57.167782 50.720984,59.952769 C 52.640446,57.354591 51.224127,60.124856 52.181413,59.20931 C 54.077246,55.518413 51.153918,62.399631 53.365408,58.43195 C 52.124521,61.484376 53.395648,58.742788 53.925207,59.075716 C 54.706091,56.339954 54.796047,56.826396 54.75408,58.656818 C 55.169288,56.317501 55.518752,56.96856 55.094375,58.981014 C 55.923906,57.118712 55.726671,55.750579 55.867103,58.64174 C 56.211579,56.121857 56.327624,55.079168 56.384713,58.300468 C 56.6963,57.912907 56.551085,53.398592 56.945178,57.561912 C 57.176086,58.925461 56.985398,53.474935 57.554754,57.10881 C 57.126434,53.801934 57.756968,57.19581 57.868266,56.323261 C 57.027404,53.885266 59.078108,57.289004 57.690072,54.654678 C 59.547764,57.653771 56.852335,52.17584 58.892122,55.295504 C 56.809351,51.934437 59.226875,55.202824 58.01751,53.200362 C 59.81662,54.5842 56.920246,51.639894 59.018845,53.579872 C 57.648491,52.209436 58.776352,52.96058 58.317315,52.108614 C 60.265349,54.250969 57.279407,50.704809 58.697681,51.795231 C 58.201603,50.987 58.133143,50.785267 57.984435,50.418197 C 59.319571,50.70044 57.562744,49.531882 58.575668,49.78742 C 55.957494,48.254478 56.72326,49.83245 55.972945,50.004986 C 55.015223,50.138883 55.6598,50.790547 56.096884,50.909571 C 53.854455,50.285688 56.988962,51.704162 54.262597,50.722877 C 57.50489,52.273852 50.421577,50.045511 53.71493,51.43184 C 52.504828,51.13699 50.694882,50.328065 51.859479,51.39313 C 48.396099,50.40795 47.808936,45.927922 44.400394,44.639566 C 41.115767,44.628236 39.642661,49.098001 38.075123,50.398084 C 36.291434,51.567104 36.096113,51.253572 36.622737,50.67121 C 34.898098,51.172096 33.777703,51.309941 34.439994,50.904956 C 30.082046,51.801225 34.622416,50.598652 33.044287,50.711155 C 32.02607,50.827066 32.771124,50.240903 32.243999,50.21773 C 31.965404,49.791294 31.797949,49.784214 31.615505,49.430071 C 31.733327,48.381994 28.15048,50.138128 30.306123,49.996409 C 28.612069,50.986133 31.626186,49.853398 29.434918,51.101688 C 30.249442,50.952188 29.427718,51.626729 29.561141,51.80672 C 28.055753,53.418931 31.055484,50.764292 29.000256,52.997613 C 31.17917,50.728967 29.67972,53.232112 29.363322,52.951473 C 28.743036,54.496389 31.354462,51.159974 29.377252,53.842688 C 31.547544,51.724966 28.376814,55.950645 30.152189,53.967594 C 28.657547,56.062796 29.599962,55.157574 30.585299,53.893404 C 29.684017,55.110256 29.239309,57.035796 30.533899,54.473214 C 29.983946,55.62868 30.313383,58.477087 30.641863,55.578972 C 30.920979,58.616919 30.87417,56.929159 31.31523,55.479822 C 30.970192,56.792233 31.41173,59.174781 31.452562,56.27647 C 31.783527,58.780495 31.711878,57.712336 32.106528,56.063647 C 32.111128,60.530118 32.446909,55.686724 32.652648,57.791298 C 33.147729,60.810087 32.638448,54.504404 33.255371,58.484634 C 33.71369,59.951337 33.064497,54.517558 33.613666,57.956548 C 34.655499,60.900524 33.329436,55.848371 34.406189,59.029112 C 35.125817,60.323285 33.891448,56.311392 35.015105,59.512204 C 35.418428,59.885168 34.338873,55.913462 35.298138,59.031903 C 36.031464,60.151717 35.011749,57.132129 36.059619,59.242001 C 36.355522,58.818138 37.741582,61.1415 36.280139,58.25611 C 36.915481,59.159949 38.236278,61.110316 36.928138,58.553042 C 38.969911,61.188497 37.647395,58.946017 37.57283,58.608942 C 38.518684,59.990514 39.324507,60.62289 38.281752,58.851019 C 40.2041,61.115104 37.585737,57.030099 40.211038,60.07521 C 39.234916,57.485468 41.578035,61.948138 40.553139,59.294397 C 42.017425,62.053801 40.308518,57.521968 41.836222,60.426555 C 42.083531,60.488515 41.39359,58.846486 42.561139,60.536576 C 41.525528,57.861993 44.154723,62.93097 42.974227,59.653444 C 43.660981,61.220889 43.342984,59.576134 43.925585,60.982754 L 43.892985,60.274034 L 43.893125,60.273913 "
        + "M 39.526233,59.12355 C 38.524231,57.620682 40.40047,60.177117 39.526233,59.12355 L 39.526233,59.12355 "
        + "M 53.887659,58.603019 C 54.158877,56.466994 53.973759,59.325402 53.887659,58.603019 L 53.887659,58.603019 "
        + "M 43.039923,58.156842 C 42.754178,58.007558 42.111247,57.752562 41.763408,58.049111 C 41.190745,57.282752 41.066742,57.120413 40.192264,56.474465 C 39.356025,55.676394 41.808068,56.131993 42.067246,56.23216 C 42.631448,56.496202 43.300109,56.487515 43.918112,56.564832 C 44.609142,56.384047 45.435147,56.878229 45.626188,56.18689 C 46.084295,56.2655 46.996203,55.950502 47.62897,55.968712 C 48.867007,56.421974 46.663983,56.864416 46.967012,57.265643 C 46.489532,56.944923 46.468911,57.933372 46.140426,57.636389 C 45.422804,58.17896 45.28393,57.886745 44.984764,58.107352 C 44.742378,58.434495 44.232291,57.641198 43.951419,58.547954 C 43.653011,57.947684 43.452103,58.274102 43.258845,58.206516 C 43.250845,58.804412 43.15688,58.589089 43.039923,58.156846 L 43.039923,58.156842 "
        + "M 53.48877,58.057692 C 53.596857,57.586813 53.54685,58.654951 53.48877,58.057692 L 53.48877,58.057692 "
        + "M 38.965335,55.242607 C 37.56572,54.325618 35.954362,54.085849 35.591892,53.872882 C 33.88711,54.477119 35.134017,52.800188 35.884563,52.902795 C 36.885922,52.444004 37.561209,53.232851 37.824123,53.405127 C 37.453425,53.733227 39.54448,53.75828 38.497653,53.942985 C 39.922118,55.59102 45.961955,52.69813 41.60719,54.111053 C 44.678047,52.749298 42.343414,53.572098 41.890272,53.546559 C 44.26222,52.646091 43.363644,52.755082 41.599265,53.210905 C 44.589544,52.339357 41.320609,52.976903 42.621536,52.48769 C 39.755639,52.294089 43.043801,52.40422 41.149819,51.802481 C 41.433591,51.6579 39.978333,50.053256 41.750758,51.793281 C 42.413,53.129874 38.729355,47.314518 42.692636,47.241404 C 47.050513,45.068192 48.083232,51.867491 46.36117,52.210839 C 45.988411,51.591888 48.116739,50.502358 45.488445,52.204639 C 48.359463,52.963044 43.761245,51.905356 46.544681,52.930283 C 42.977211,51.928407 47.051388,53.359047 45.8191,53.097574 C 43.149286,52.358336 48.504168,54.260646 44.886971,53.192044 C 47.946507,54.420867 41.908669,52.01786 45.516829,54.110647 C 48.095332,55.329743 49.674858,53.456468 51.544935,53.00731 C 50.887305,52.203235 53.810607,52.781528 53.370659,53.943064 C 53.083343,54.060568 52.17618,54.052912 51.365904,54.20925 C 51.314744,54.529034 49.471307,55.322748 48.303878,55.286393 C 45.044446,54.642632 42.223316,55.112716 38.965335,55.242613 L 38.965335,55.242607 "
        + "M 42.797209,50.849215 C 42.158002,50.150732 40.450985,51.048808 42.797209,50.849215 L 42.797209,50.849215 "
        + "M 46.223817,50.810855 C 47.113085,50.009592 43.404222,51.408344 46.223817,50.810855 L 46.223817,50.810855 "
        + "M 41.917363,48.355 C 43.855577,48.567357 49.197008,49.106355 44.887254,47.584569 C 43.759479,46.219571 39.896356,49.891902 41.917363,48.355 L 41.917363,48.355 "
        + "M 57.277332,54.413893 C 56.59824,53.691766 58.116907,55.11024 57.277332,54.413893 L 57.277332,54.413893 "
        + "M 36.613785,54.399733 C 37.00088,54.076437 37.011182,54.575748 36.613785,54.399733 L 36.613785,54.399733 "
        + "M 47.37166,54.166979 C 48.570738,53.542247 47.551371,54.488132 47.37166,54.166979 L 47.37166,54.166979 "
        + "M 40.183215,54.028342 C 40.839093,53.736378 40.83775,54.196099 40.183215,54.028342 L 40.183215,54.028342 "
        + "M 45.933971,53.945182 C 41.959605,52.714492 49.411662,54.479273 45.933971,53.945182 L 45.933971,53.945182 "
        + "M 48.958074,53.843776 C 49.077982,53.481267 49.202591,54.196982 48.958074,53.843776 L 48.958074,53.843776 "
        + "M 53.555943,53.174507 C 53.211856,52.751923 54.20387,53.6858 53.555943,53.174507 L 53.555943,53.174507 "
        + "M 41.354438,52.883687 C 41.789084,52.741694 41.397368,53.074451 41.354438,52.883687 L 41.354438,52.883687 "
        + "M 30.069822,51.464151 C 30.796445,51.048443 29.823971,51.854643 30.069822,51.464151 L 30.069822,51.464151 "
        + "M 30.276385,49.445508 C 30.665216,49.222243 31.204444,49.386548 30.276385,49.445508 L 30.276385,49.445508 "
        + "M 26.996141,55.690208 C 26.661065,55.28796 26.527323,55.416388 26.996141,55.690208 L 26.996141,55.690208 "
        + "M 58.972316,52.25736 C 58.059576,51.528126 59.506478,52.938936 58.972316,52.25736 L 58.972316,52.25736 "
        + "M 54.132557,49.424878 C 57.991066,49.479968 57.414196,41.817758 56.138082,42.183376 C 57.718794,44.944825 55.975593,48.798592 54.132557,49.424878 L 54.132557,49.424878 "
        + "M 58.476564,49.320411 C 56.234086,47.881697 58.80714,50.008314 58.476564,49.320411 L 58.476564,49.320411 "
        + "M 30.828318,48.8599 C 30.015878,48.728921 30.608466,47.848697 30.168977,47.378323 C 30.067825,47.220859 30.354423,46.448449 29.409966,45.560353 C 27.505617,45.193368 26.885295,46.074413 26.67895,46.733391 C 25.136932,47.286326 29.913844,46.737591 26.153361,47.393677 C 27.883669,46.614694 29.047056,48.273019 29.320371,49.034964 C 29.140452,49.447969 30.203595,49.29986 30.828346,48.859656 L 30.828318,48.8599 "
        + "M 34.578851,49.247954 C 30.733608,48.523743 31.258928,43.700638 32.240183,41.58508 C 29.092434,44.213001 32.284813,50.227815 35.123828,49.397589 C 34.942169,49.347709 34.76051,49.297829 34.578851,49.247954 L 34.578851,49.247954 "
        + "M 58.787736,49.134107 C 58.710736,46.860918 63.40483,47.595276 60.228539,47.017112 C 62.51164,46.967982 60.409969,46.098371 61.103876,45.777964 C 59.556171,44.657987 57.670303,46.468512 58.055122,47.171119 C 58.178554,47.642292 57.461463,47.864526 58.122622,48.318327 C 56.455757,47.960271 58.968156,49.571489 58.787738,49.134107 L 58.787736,49.134107 "
        + "M 52.94685,48.573138 C 56.684569,48.443829 53.902218,40.241693 54.824125,45.466485 C 53.326201,52.023997 44.289553,44.679643 50.532192,42.0535 C 52.125215,41.768478 54.987853,42.384558 51.506394,41.536988 C 44.974147,41.93366 49.485861,51.827642 54.00286,47.454692 C 55.981795,45.184943 52.06164,50.429548 50.209258,48.37872 C 46.857173,46.426041 51.659312,50.040757 52.94685,48.573138 L 52.94685,48.573138 "
        + "M 38.101049,48.273122 C 39.611834,47.75234 33.221368,49.460885 33.291548,46.16734 C 32.754524,44.261572 33.781987,40.400188 32.606125,44.672315 C 32.556665,47.328994 35.629626,49.469362 38.101049,48.273122 L 38.101049,48.273122 "
        + "M 38.028499,47.967819 C 43.988795,45.699624 35.984951,39.302498 35.567088,41.792895 C 42.195884,40.29767 39.478817,51.241604 34.324071,47.082226 C 32.596258,46.035076 34.358661,40.75861 33.142867,44.836493 C 33.297581,47.164932 35.757187,49.131608 38.028499,47.967819 L 38.028499,47.967819 "
        + "M 55.560972,47.778082 C 55.612012,47.184225 54.996612,48.726183 55.560972,47.778082 L 55.560972,47.778082 "
        + "M 39.824652,47.101228 C 41.161121,45.390594 38.279554,48.558831 39.824652,47.101228 L 39.824652,47.101228 "
        + "M 55.572799,45.681376 C 55.835879,43.327372 54.139489,41.685483 55.287616,45.098872 C 55.356706,46.400464 54.963333,47.786907 55.572799,45.681376 L 55.572799,45.681376 "
        + "M 47.798003,46.283518 C 46.447786,42.631327 51.48587,40.357858 53.610929,41.50518 C 49.880807,39.149181 46.446544,43.967285 47.798003,46.283518 L 47.798003,46.283518 "
        + "M 30.040645,45.093707 C 29.88878,45.287193 30.189768,46.082879 30.040645,45.093707 L 30.040645,45.093707 "
        + "M 30.473747,45.456699 C 30.742615,43.0693 29.860989,44.642438 30.47377,45.456699 L 30.473747,45.456699 "
        + "M 30.474122,44.664052 C 30.617219,44.399994 30.518382,45.091568 30.474122,44.664052 L 30.474122,44.664052 "
        + "M 56.310272,44.565462 C 55.750457,41.355393 56.480166,47.205826 56.310272,44.565462 L 56.310272,44.565462 "
        + "M 58.028734,44.883271 C 57.724285,43.59384 57.602444,44.708727 58.028847,44.883257 L 58.028734,44.883271 "
        + "M 43.455064,44.019359 C 46.476604,44.603416 46.092635,43.926349 43.295508,43.810894 C 41.334671,44.417891 42.191185,44.451585 43.455067,44.019239 L 43.455064,44.019359 "
        + "M 40.175454,43.444064 C 40.484272,39.758145 31.325478,41.284161 36.6591,41.006774 C 38.24746,39.570027 41.398104,46.319147 40.175454,43.444064 L 40.175454,43.444064 "
        + "M 47.203123,43.804751 C 47.847879,40.869371 37.669924,42.161007 41.587158,44.107754 C 41.053746,40.690657 41.751714,45.723984 44.067481,43.595284 C 44.792831,42.978805 46.658368,41.859983 46.706077,44.410942 L 46.882731,44.384132 L 47.203146,43.804772 L 47.203123,43.804751 "
        + "M 45.735537,43.829561 C 43.981366,43.087472 46.715621,44.505184 45.735537,43.829561 L 45.735537,43.829561 "
        + "M 56.542988,43.928711 C 56.298452,43.575509 56.423086,44.291219 56.542988,43.928711 L 56.542988,43.928711 "
        + "M 46.177776,43.222229 C 46.057468,42.369343 45.826313,43.573681 46.177776,43.222229 L 46.177776,43.222229 "
        + "M 42.954643,41.251628 C 43.508253,41.74208 44.163841,41.121446 44.471814,41.628017 C 45.195936,41.102554 45.276763,41.420128 45.773063,41.473297 C 46.812104,40.695819 46.361741,41.333783 47.186803,40.699737 C 47.360366,40.943807 48.373164,39.570814 48.265877,40.216231 C 48.351617,40.240951 49.30829,39.78657 49.329903,39.880614 C 49.159959,40.364838 50.728804,39.539573 50.737509,39.956174 C 52.280039,39.757903 50.514904,39.957374 52.60223,40.274901 C 52.707384,39.614003 54.643423,41.902267 54.584735,40.167544 C 52.694864,38.850571 52.439274,38.684174 50.817175,38.246939 C 50.257703,37.824517 48.483657,38.312039 48.348459,37.983852 C 47.590635,37.513179 47.928722,37.848897 46.845584,37.789558 C 46.071881,37.425259 45.392248,38.295126 45.170299,37.533799 C 44.77825,39.175184 43.744822,36.638883 43.838581,38.090048 C 43.875711,38.202167 42.963332,37.820135 42.710416,37.77982 C 42.496622,38.064702 40.878668,37.489998 40.778133,37.77402 C 40.30035,37.998836 39.254024,37.995909 38.476539,38.005429 C 38.404469,38.000629 35.510525,38.326168 35.969313,38.766198 C 33.144845,39.298605 36.611874,38.850978 33.409769,40.094267 C 34.62535,40.831152 38.475729,39.651256 37.906573,39.752811 C 39.17053,40.554463 37.989833,38.57787 40.145105,40.598256 C 39.41217,39.427577 41.018192,40.839465 40.828006,40.499616 C 41.261521,40.694757 41.840557,41.729035 42.954643,41.251638 L 42.954643,41.251628 "
        + "M 43.623781,40.024631 C 42.967478,39.383413 45.15593,39.487353 43.955668,40.114391 L 43.835345,40.147971 L 43.623776,40.02465 L 43.623781,40.024631 "
        + "M 42.350563,39.78915 C 41.306722,38.457911 43.085306,40.478972 42.350563,39.78915 L 42.350563,39.78915 "
        + "M 42.860159,39.665215 C 42.544362,38.79201 43.388221,40.310121 42.860159,39.665215 L 42.860159,39.665215 "
        + "M 44.651542,39.764365 C 44.813145,39.024281 45.118395,39.510881 44.651542,39.764365 L 44.651542,39.764365 "
        + "M 45.834687,39.767765 C 46.482018,39.025841 47.93403,38.902473 45.834679,39.767764 L 45.834687,39.767765 "
        + "M 45.041482,39.700705 C 45.255284,39.138364 45.432553,39.329962 45.041482,39.700705 L 45.041482,39.700705 "
        + "M 41.719926,39.527352 C 39.879405,38.397194 42.888458,39.890784 41.719926,39.527352 L 41.719926,39.527352 "
        + "M 45.529732,39.430952 C 46.385362,38.476086 45.059496,40.236529 45.529732,39.430952 L 45.529732,39.430952 "
        + "M 39.329159,40.108312 C 38.705212,39.345511 39.627477,40.967097 39.329159,40.108312 L 39.329159,40.108312 "
        + "M 38.993276,39.96268 C 38.748714,39.609493 38.873406,40.325178 38.993276,39.96268 L 38.993276,39.96268 "
        + "M 47.873412,36.2176 C 47.291293,36.463692 47.54288,36.647768 47.873412,36.2176 L 47.873412,36.2176",
    ),
    strokewidth=1,
)

icon_distort = VectorIcon(
    fill=(
        "M464.149,343.637l-52.693-158.08C432.981,175.253,448,153.429,448,128c0-35.307-28.715-64-64-64"
        "c-18.219,0-34.603,7.744-46.272,20.011l-169.877-37.76C160.107,19.627,135.765,0,106.667,0c-35.285,0-64,28.693-64,64"
        "c0,26.816,16.619,49.749,40.085,59.264L45.056,387.179C19.051,395.328,0,419.349,0,448c0,35.285,28.715,64,64,64"
        "c28.651,0,52.672-19.051,60.821-45.056l263.915-37.696c9.493,23.445,32.448,40.085,59.264,40.085c35.285,0,64-28.715,64-64"
        "C512,375.637,491.605,350.848,464.149,343.637z M387.2,386.368l-263.936,37.717c-6.507-16.064-19.285-28.864-35.349-35.349"
        "L125.632,124.8c17.792-5.568,32.363-18.453,39.723-35.392l155.072,34.453C320.32,125.248,320,126.571,320,128"
        "c0,29.675,20.395,54.464,47.851,61.675l52.693,158.08C404.629,355.392,392.533,369.323,387.2,386.368z",
    ),
    stroke=(),
)

icon_copies = VectorIcon(
    fill=(
        "M425.95,1.911H193.555c-18.609,0-33.749,15.139-33.749,33.748V51.19h30.806V35.658c0-1.622,1.32-2.941,2.942-2.941"
        "H425.95c1.623,0,2.942,1.32,2.942,2.941v232.396c0,1.622-1.32,2.941-2.942,2.941h-18.309v30.806h18.309"
        "c18.609,0,33.749-15.139,33.749-33.748V35.658C459.699,17.05,444.559,1.911,425.95,1.911z",
        "M346.34,81.997H110.407c-16.815,0-30.494,13.68-30.494,30.495v17.568h29.322v-15.8c0-1.622,1.32-2.941,2.941-2.941"
        "h232.396c1.622,0,2.941,1.32,2.941,2.941v232.396c0,1.622-1.32,2.941-2.941,2.941h-16.844v29.322h18.612"
        "c16.815,0,30.495-13.68,30.495-30.494V112.492C376.835,95.676,363.155,81.997,346.34,81.997z",
        "M266.427,160.866H30.494C13.68,160.866,0,174.546,0,191.361v235.933c0,16.814,13.68,30.494,30.494,30.494h235.933"
        "c16.815,0,30.495-13.68,30.495-30.494V191.361C296.922,174.546,283.242,160.866,266.427,160.866z",
        "M264.659,428.467H32.263c-1.623,0-2.942-1.32-2.942-2.942V193.13c0-1.623,1.32-2.942,2.942-2.942h232.395c1.623,0,2.942,1.32,2.942,2.942v232.395h0.001"
        "C267.601,427.148,266.281,428.467,264.659,428.467z",
    ),
    stroke=(),
)

icon_z_up = VectorIcon(
    fill=(),
    stroke=("M 45,60 h 10 v-40 h15 l-20,-20 l-20,20 h15 v40",),
    strokewidth=2,
)

icon_z_up_double = VectorIcon(
    fill=(),
    stroke=(
        "M 45,60 h 10 v-40 h15 l-20,-20 l-20,20 h15 v40",
        "M 30,12.5 l 20,-20 l 20,20",
    ),
    strokewidth=2,
)

icon_z_up_triple = VectorIcon(
    fill=(),
    stroke=(
        "M 45,60 h 10 v-40 h15 l-20,-20 l-20,20 h15 v40",
        "M 30,12.5 l 20,-20 l 20,20",
        "M 30,5 l 20,-20 l 20,20",
    ),
    strokewidth=2,
)

icon_z_down = VectorIcon(
    fill=(),
    stroke=("M 45,0 h 10 v40 h15 l-20,20 l-20,-20 h15 v-40",),
    strokewidth=2,
)

icon_z_down_double = VectorIcon(
    fill=(),
    stroke=(
        "M 45,0 h 10 v40 h15 l-20,20 l-20,-20 h15 v-40",
        "M 30,47.5 l 20,20 l 20,-20",
    ),
    strokewidth=2,
)

icon_z_down_triple = VectorIcon(
    fill=(),
    stroke=(
        "M 45,0 h 10 v40 h15 l-20,20 l-20,-20 h15 v-40",
        "M 30,47.5 l 20,20 l 20,-20",
        "M 30,55 l 20,20 l 20,-20",
    ),
    strokewidth=2,
)

icon_z_home = VectorIcon(
    fill=(),
    stroke=(
        "M 50,0 l 25,25 h -5 v 35 h -40 v -35 h -5 l 25,-25",
        "M 37.5,25 h 25 l -25, 25 h 25",
    ),
)
