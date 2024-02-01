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


def get_default_icon_size():
    return int(_GLOBAL_FACTOR * STD_ICON_SIZE)


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
                            e = int(e[2:], 16)
                        except ValueError:
                            pass
                    color = e
            pathstr = pathstr[idx + 1 :]
            # print(f"{pattern}: {color}, {bright} -> {pathstr}")
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

    def prepare_bitmap(self, final_icon_width, final_icon_height, buffer):
        wincol = self._background.GetColour()
        bmp = wx.Bitmap.FromRGBA(
            final_icon_width,
            final_icon_height,
            wincol.red,
            wincol.blue,
            wincol.green,
            0,
        )
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        # dc.SetBackground(self._background)
        # dc.SetBackground(wx.RED_BRUSH)
        # dc.Clear()
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
            fill_paths.append((gp, color, attrib))
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

        def_col = self._pen.GetColour()
        for s_entry in self.list_stroke:
            e = s_entry[2]
            attrib = s_entry[3]
            geom = Geomstr.svg(e)
            color = get_color(s_entry[0], s_entry[1], def_col)
            gp = self.make_geomstr(gc, geom)
            stroke_paths.append((gp, color, attrib))
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
        matrix.post_translate(
            -min_x
            + self.edge
            + stroke_buffer
            + (final_icon_width - width_scaled) / 2 / scale_x,
            -min_y
            + self.edge
            + stroke_buffer
            + (final_icon_height - height_scaled) / 2 / scale_x,
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

            spen.SetCap(wx.CAP_ROUND)
            if "cap_butt" in attrib:
                spen.SetCap(wx.CAP_BUTT)
            if "cap_round" in attrib:
                spen.SetCap(wx.CAP_BUTT)
            if "cap_square" in attrib:
                spen.SetCap(wx.CAP_PROJECTING)

            spen.SetJoin(wx.JOIN_ROUND)
            if "join_arcs" in attrib:
                spen.SetJoin(wx.JOIN_ROUND)
            if "join_bevel" in attrib:
                spen.SetJoin(wx.JOIN_BEVEL)
            if "join_miter" in attrib:
                spen.SetJoin(wx.JOIN_MITER)
            if "join_miterclip" in attrib:
                spen.SetJoin(wx.JOIN_MITER)
            gc.SetPen(spen)
            gc.StrokePath(gp)
        dc.SelectObject(wx.NullBitmap)
        gc.Destroy()
        del gc.dc
        del dc
        return bmp

    @lru_cache(maxsize=1024)
    def retrieve_bitmap(self, color_dark, final_icon_width, final_icon_height, buffer):
        # Even if we don't use color_dark in this routine, it is needed
        # to create the proper function hash?!
        with self._lock:
            bmp = self.prepare_bitmap(final_icon_width, final_icon_height, buffer)
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
        buffer=None,
        resolution=1,
        **kwargs,
    ):
        if color is not None and hasattr(color, "red"):
            if color.red == color.green == color.blue == 255:
                # Color is white...
                force_darkmode = True

        if force_darkmode or DARKMODE:
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
        bmp = self.retrieve_bitmap(
            color_dark, final_icon_width, final_icon_height, buffer
        )

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
    "M 24.90625 -0.03125 C 24.863281 -0.0234375 24.820313 -0.0117188 24.78125 0 C 24.316406 0.105469 23.988281 0.523438 24 1 L 24 27.9375 C 24 28.023438 24.011719 28.105469 24.03125 28.1875 C 22.859375 28.59375 22 29.6875 22 31 C 22 32.65625 23.34375 34 25 34 C 26.65625 34 28 32.65625 28 31 C 28 29.6875 27.140625 28.59375 25.96875 28.1875 C 25.988281 28.105469 26 28.023438 26 27.9375 L 26 1 C 26.011719 0.710938 25.894531 0.433594 25.6875 0.238281 C 25.476563 0.0390625 25.191406 -0.0585938 24.90625 -0.03125 Z M 35.125 12.15625 C 34.832031 12.210938 34.582031 12.394531 34.4375 12.65625 L 27.125 25.3125 C 26.898438 25.621094 26.867188 26.03125 27.042969 26.371094 C 27.222656 26.710938 27.578125 26.917969 27.960938 26.90625 C 28.347656 26.894531 28.6875 26.664063 28.84375 26.3125 L 36.15625 13.65625 C 36.34375 13.335938 36.335938 12.9375 36.140625 12.625 C 35.941406 12.308594 35.589844 12.128906 35.21875 12.15625 C 35.1875 12.15625 35.15625 12.15625 35.125 12.15625 Z M 17.78125 17.71875 C 17.75 17.726563 17.71875 17.738281 17.6875 17.75 C 17.375 17.824219 17.113281 18.042969 16.988281 18.339844 C 16.867188 18.636719 16.894531 18.976563 17.0625 19.25 L 21.125 26.3125 C 21.402344 26.796875 22.015625 26.964844 22.5 26.6875 C 22.984375 26.410156 23.152344 25.796875 22.875 25.3125 L 18.78125 18.25 C 18.605469 17.914063 18.253906 17.710938 17.875 17.71875 C 17.84375 17.71875 17.8125 17.71875 17.78125 17.71875 Z M 7 19.6875 C 6.566406 19.742188 6.222656 20.070313 6.140625 20.5 C 6.0625 20.929688 6.273438 21.359375 6.65625 21.5625 L 19.3125 28.875 C 19.796875 29.152344 20.410156 28.984375 20.6875 28.5 C 20.964844 28.015625 20.796875 27.402344 20.3125 27.125 L 7.65625 19.84375 C 7.488281 19.738281 7.292969 19.683594 7.09375 19.6875 C 7.0625 19.6875 7.03125 19.6875 7 19.6875 Z M 37.1875 22.90625 C 37.03125 22.921875 36.882813 22.976563 36.75 23.0625 L 29.6875 27.125 C 29.203125 27.402344 29.035156 28.015625 29.3125 28.5 C 29.589844 28.984375 30.203125 29.152344 30.6875 28.875 L 37.75 24.78125 C 38.164063 24.554688 38.367188 24.070313 38.230469 23.617188 C 38.09375 23.164063 37.660156 22.867188 37.1875 22.90625 Z M 0.71875 30 C 0.167969 30.078125 -0.21875 30.589844 -0.140625 31.140625 C -0.0625 31.691406 0.449219 32.078125 1 32 L 19 32 C 19.359375 32.003906 19.695313 31.816406 19.878906 31.503906 C 20.058594 31.191406 20.058594 30.808594 19.878906 30.496094 C 19.695313 30.183594 19.359375 29.996094 19 30 L 1 30 C 0.96875 30 0.9375 30 0.90625 30 C 0.875 30 0.84375 30 0.8125 30 C 0.78125 30 0.75 30 0.71875 30 Z M 30.71875 30 C 30.167969 30.078125 29.78125 30.589844 29.859375 31.140625 C 29.9375 31.691406 30.449219 32.078125 31 32 L 49 32 C 49.359375 32.003906 49.695313 31.816406 49.878906 31.503906 C 50.058594 31.191406 50.058594 30.808594 49.878906 30.496094 C 49.695313 30.183594 49.359375 29.996094 49 30 L 31 30 C 30.96875 30 30.9375 30 30.90625 30 C 30.875 30 30.84375 30 30.8125 30 C 30.78125 30 30.75 30 30.71875 30 Z M 19.75 32.96875 C 19.71875 32.976563 19.6875 32.988281 19.65625 33 C 19.535156 33.019531 19.417969 33.0625 19.3125 33.125 L 12.25 37.21875 C 11.898438 37.375 11.667969 37.714844 11.65625 38.101563 C 11.644531 38.484375 11.851563 38.839844 12.191406 39.019531 C 12.53125 39.195313 12.941406 39.164063 13.25 38.9375 L 20.3125 34.875 C 20.78125 34.675781 21.027344 34.160156 20.882813 33.671875 C 20.738281 33.183594 20.25 32.878906 19.75 32.96875 Z M 30.03125 33 C 29.597656 33.054688 29.253906 33.382813 29.171875 33.8125 C 29.09375 34.242188 29.304688 34.671875 29.6875 34.875 L 42.34375 42.15625 C 42.652344 42.382813 43.0625 42.414063 43.402344 42.238281 C 43.742188 42.058594 43.949219 41.703125 43.9375 41.320313 C 43.925781 40.933594 43.695313 40.59375 43.34375 40.4375 L 30.6875 33.125 C 30.488281 33.007813 30.257813 32.964844 30.03125 33 Z M 21.9375 35.15625 C 21.894531 35.164063 21.851563 35.175781 21.8125 35.1875 C 21.519531 35.242188 21.269531 35.425781 21.125 35.6875 L 13.84375 48.34375 C 13.617188 48.652344 13.585938 49.0625 13.761719 49.402344 C 13.941406 49.742188 14.296875 49.949219 14.679688 49.9375 C 15.066406 49.925781 15.40625 49.695313 15.5625 49.34375 L 22.875 36.6875 C 23.078125 36.367188 23.082031 35.957031 22.882813 35.628906 C 22.683594 35.304688 22.316406 35.121094 21.9375 35.15625 Z M 27.84375 35.1875 C 27.511719 35.234375 27.226563 35.445313 27.082031 35.746094 C 26.9375 36.046875 26.953125 36.398438 27.125 36.6875 L 31.21875 43.75 C 31.375 44.101563 31.714844 44.332031 32.101563 44.34375 C 32.484375 44.355469 32.839844 44.148438 33.019531 43.808594 C 33.195313 43.46875 33.164063 43.058594 32.9375 42.75 L 28.875 35.6875 C 28.671875 35.320313 28.257813 35.121094 27.84375 35.1875 Z M 24.90625 35.96875 C 24.863281 35.976563 24.820313 35.988281 24.78125 36 C 24.316406 36.105469 23.988281 36.523438 24 37 L 24 45.9375 C 23.996094 46.296875 24.183594 46.632813 24.496094 46.816406 C 24.808594 46.996094 25.191406 46.996094 25.503906 46.816406 C 25.816406 46.632813 26.003906 46.296875 26 45.9375 L 26 37 C 26.011719 36.710938 25.894531 36.433594 25.6875 36.238281 C 25.476563 36.039063 25.191406 35.941406 24.90625 35.96875 Z"
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
                print(s[: idx + 1])
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
