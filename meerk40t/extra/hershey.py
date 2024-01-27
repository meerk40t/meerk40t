from functools import lru_cache
from glob import glob
from os import environ, walk
from os.path import basename, exists, join, realpath, splitext

import numpy as np

from meerk40t.core.node.node import Fillrule
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_PIXEL, Length
from meerk40t.kernel import get_safe_path
from meerk40t.svgelements import Color
from meerk40t.tools.geomstr import BeamTable, Geomstr
from meerk40t.tools.jhfparser import JhfFont
from meerk40t.tools.shxparser import ShxFont, ShxFontParseError
from meerk40t.tools.ttfparser import TrueTypeFont


class FontPath:
    def __init__(self, weld):
        self.total_list = list()
        self.total_geometry = Geomstr()
        self.geom = Geomstr()
        self._index = 0
        self.start = None
        self.weld = weld

    def character_end(self):
        if self.weld:
            self.geom.as_interpolated_points()
            c = Geomstr()
            for sp in self.geom.as_subpaths():
                for segs in sp.as_interpolated_segments(interpolate=10):
                    c.polyline(segs)
                    c.end()
            c.flag_settings(flag=self._index)
            self._index += 1
            self.total_geometry.append(c)
        else:
            self.total_geometry.append(self.geom)
        self.geom.clear()

    @property
    def geometry(self):
        if not self.weld:
            return self.total_geometry
        bt = BeamTable(self.total_geometry.simplify())
        union = bt.union(*list(range(self._index)))
        union.greedy_distance()
        return union.simplify()

    def new_path(self):
        self.geom.end()

    def move(self, x, y):
        # self.geom.move((x, -y))
        if self.start is not None:
            self.geom.end()
        self.start = x - 1j * y

    def line(self, x0, y0, x1, y1):
        # self.path.line((x1, -y1))
        end = x1 - 1j * y1
        self.geom.line(self.start, end)
        self.start = end

    def quad(self, x0, y0, x1, y1, x2, y2):
        # self.path.quad((x1, -y1), (x2, -y2))
        control = x1 - 1j * y1
        end = x2 - 1j * y2
        self.geom.quad(self.start, control, end)
        self.start = end

    def cubic(self, x0, y0, x1, y1, x2, y2, x3, y3):
        # self.path.cubic((x1, -y1), (x2, -y2), (x3, -y3))
        control0 = x1 - 1j * y1
        control1 = x2 - 1j * y2
        end = x3 - 1j * y3
        self.geom.cubic(self.start, control0, control1, end)
        self.start = end

    def close(self):
        self.geom.close()

    def arc(self, x0, y0, cx, cy, x1, y1):
        # arc = Arc(start=(x0, -y0), control=(cx, -cy), end=(x1, -y1))
        # self.path += arc
        control = cx - 1j * cy
        end = x1 - 1j * y1
        self.geom.arc(self.start, control, end)
        self.start = end


class Meerk40tFonts:
    """
    Main Interface to access vector fonts.
    Supported formats:
    ttf - TrueType fonts
    shx - AutoCad fonts
    jhf - Hershey fonts
    """

    def __init__(self, context, **kwds):
        self.context = context
        self._available_fonts = None

    def fonts_registered(self):
        registered_fonts = {
            "shx": ("Autocad", ShxFont),
            "jhf": ("Hershey", JhfFont),
            "ttf": ("TrueType", TrueTypeFont),
        }
        return registered_fonts

    @property
    def font_directory(self):
        fontdir = ""
        safe_dir = realpath(get_safe_path(self.context.kernel.name))
        self.context.setting(str, "font_directory", safe_dir)
        fontdir = self.context.font_directory
        return fontdir

    @font_directory.setter
    def font_directory(self, value):
        self.context.setting(str, "font_directory", value)
        self.context.font_directory = value
        self._available_fonts = None

    def have_hershey_fonts(self):
        p = self.available_fonts()
        return len(p) > 0

    @lru_cache(maxsize=512)
    def get_font_information(self, full_file_name):
        if full_file_name.lower().endswith(".ttf"):
            info = TrueTypeFont.query_name(full_file_name)
            return info
        else:
            return None

    def _get_full_info(self, short):
        s_lower = short.lower()
        p = self.available_fonts()
        for info in p:
            # We don't care about capitalisation
            f_lower = info[0].lower()
            if f_lower.endswith(s_lower):
                return info
        return None

    def is_system_font(self, short):
        info = self._get_full_info(short)
        if info:
            return info[2]
        return True

    def full_name(self, short):
        info = self._get_full_info(short)
        if info:
            return info[0]
        return None

    def short_name(self, fullname):
        return basename(fullname)

    @lru_cache(maxsize=128)
    def cached_fontclass(self, fontname):
        registered_fonts = self.fonts_registered()
        if not exists(fontname):
            return
        try:
            filename, file_extension = splitext(fontname)
            if len(file_extension) > 0:
                # Remove dot...
                file_extension = file_extension[1:].lower()
            item = registered_fonts[file_extension]
            fontclass = item[1]
        except (KeyError, IndexError):
            # channel(_("Unknown fonttype {ext}").format(ext=file_extension))
            # print ("unknown fonttype, exit")
            return
        # print("Nearly there, all fonts checked...")
        cfont = fontclass(fontname)

        return cfont

    def validate_node(self, node):
        # After a svg load the attributes are still a string...
        if not hasattr(node, "mkfontsize"):
            return
        if isinstance(node.mkfontsize, str):
            try:
                value = float(node.mkfontsize)
            except ValueError:
                value = Length("20px")
            node.mkfontsize = value
        # if not hasattr(node, "mkcoordx"):
        #     node.mkcoordx = 0
        # if not hasattr(node, "mkcoordy"):
        #     node.mkcoordy = 0
        # if isinstance(node.mkcoordx, str):
        #     try:
        #         value = float(node.mkcoordx)
        #     except ValueError:
        #         value = 0
        #     node.mkcoordx = value
        # if isinstance(node.mkcoordy, str):
        #     try:
        #         value = float(node.mkcoordy)
        #     except ValueError:
        #         value = 0
        #     node.mkcoordy = value

    def update(self, node):
        # We need to check for the validity ourselves...
        if (
            hasattr(node, "mktext")
            and hasattr(node, "mkfont")
            and hasattr(node, "mkfontsize")
        ):
            self.update_linetext(node, node.mktext)

    def update_linetext(self, node, newtext):
        # print ("Update Linetext")
        if node is None:
            # print ("node is none, exit")
            return
        if not hasattr(node, "mkfont"):
            # print ("no font attr, exit")
            return
        if not hasattr(node, "mkfontsize"):
            # print ("no fontsize attr, exit")
            return
        spacing = None
        if hasattr(node, "mkfontspacing"):
            try:
                spacing = float(node.mkfontspacing)
            except AttributeError:
                pass
        if spacing is None:
            spacing = 1
        weld = None
        if hasattr(node, "mkfontweld"):
            try:
                weld = bool(node.mkfontweld)
            except ValueError:
                pass
        if weld is None:
            weld = False
        # from time import perf_counter
        # _t0 = perf_counter()
        oldtext = getattr(node, "_translated_text", "")
        fontname = node.mkfont
        fontsize = node.mkfontsize
        # old_color = node.stroke
        # old_strokewidth = node.stroke_width
        # old_strokescaled = node._stroke_scaled
        fullfont = self.full_name(fontname)
        if fullfont is None:
            # This font does not exist in our environment
            return
        # Make sure any paths are removed
        fontname = self.short_name(fontname)

        cfont = self.cached_fontclass(fullfont)
        if cfont is None:
            # This font does not exist in our environment
            return

        # _t1 = perf_counter()

        path = FontPath(weld)
        # print (f"Path={path}, text={remainder}, font-size={font_size}")
        horizontal = True
        mytext = self.context.elements.wordlist_translate(newtext)
        cfont.render(path, mytext, horizontal, float(fontsize), spacing)
        # _t2 = perf_counter()
        olda = node.matrix.a
        oldb = node.matrix.b
        oldc = node.matrix.c
        oldd = node.matrix.d
        olde = node.matrix.e
        oldf = node.matrix.f
        node.geometry = path.geometry
        node.matrix.a = olda
        node.matrix.b = oldb
        node.matrix.c = oldc
        node.matrix.d = oldd
        node.matrix.e = olde
        node.matrix.f = oldf
        # print (f"x={node.mkcoordx}, y={node.mkcoordy}")
        # node.path.transform = Matrix.translate(node.mkcoordx, node.mkcoordy)
        # print (f"Updated: from {oldtext} -> {mytext}")
        node.mktext = newtext
        node.mkfont = fontname
        node._translated_text = mytext
        # _t3 = perf_counter()
        node.altered()
        # _t4 = perf_counter()
        # print (f"Readfont: {_t1 -_t0:.2f}s, render: {_t2 -_t1:.2f}s, path: {_t3 -_t2:.2f}s, alter: {_t4 -_t3:.2f}s, total={_t4 -_t0:.2f}s")

    def create_linetext_node(
        self, x, y, text, font=None, font_size=None, font_spacing=1.0
    ):

        if font_size is None:
            font_size = Length("20px")
        if font_spacing is None:
            font_spacing = 1
        self.context.setting(str, "last_font", "")
        # Check whether the default is still valid
        if self.context.last_font:
            dummy = self.full_name(self.context.last_font)
            if dummy is None:
                self.context.last_font = None
        # Valid font?
        if font:
            dummy = self.full_name(font)
            if dummy is None:
                font = None
        if font is not None:
            self.context.last_font = font
        else:
            if self.context.last_font is not None:
                #  print (f"Fallback to {context.last_font}")
                font = self.context.last_font
        # Still not valid?
        if font is None or font == "":
            font = ""
            # No preferred font set, let's try a couple of candidates...
            candidates = (
                "timesr.jhf",
                "romant.shx",
                "rowmans.jhf",
                "FUTURA.SHX",
                "arial.ttf",
            )
            for fname in candidates:
                dummy = self.full_name(fname)
                if dummy is not None:
                    # print (f"Taking font {fname} instead")
                    font = dummy
                    self.context.last_font = font
                    break
            if font == "":
                # You know, I take anything at this point...
                if self.available_fonts():
                    font = self._available_fonts[0]
                    # print (f"Fallback to first file found: {font}")
                    self.context.last_font = font

        if font is None or font == "":
            # print ("Font was empty")
            return None
        font_path = self.full_name(font)
        font = self.short_name(font)
        horizontal = True
        cfont = self.cached_fontclass(font_path)
        if cfont is None:
            # This font does not exist in our environment
            return
        weld = False
        try:
            path = FontPath(weld)
            # print (f"Path={path}, text={remainder}, font-size={font_size}")
            mytext = self.context.elements.wordlist_translate(text)
            cfont.render(path, mytext, horizontal, float(font_size), font_spacing)
        except ShxFontParseError as e:
            # print(f"FontParseError {e.args}")
            return
        #  print (f"Pathlen={len(path.path)}")
        # if len(path.path) == 0:
        #     print("Empty path...")
        #     return None

        path_node = PathNode(
            geometry=path.geometry,
            stroke=Color("black"),
            fillrule = Fillrule.FILLRULE_NONZERO,
        )
        path_node.matrix.post_translate(x, y)
        path_node.mkfont = font
        path_node.mkfontsize = float(font_size)
        path_node.mkfontspacing = float(font_spacing)
        path_node.mkfontweld = weld
        path_node.mktext = text
        path_node._translated_text = mytext
        path_node.mkcoordx = x
        path_node.mkcoordy = y
        path_node.stroke_width = UNITS_PER_PIXEL

        return path_node

    def preview_file(self, fontfile):
        def create_preview_image(fontfile, bmpfile, bitmap_format):
            from math import isinf

            simplefont = basename(fontfile)
            pattern = "The quick brown fox..."
            try:
                node = self.create_linetext_node(
                    0, 0, pattern, font=simplefont, font_size=Length("12pt")
                )
            except Exception as e:
                # We may encounter an IndexError, a ValueError or an error thrown by struct
                # The latter cannot be named? So a global except...
                # print (f"Node creation failed: {e}")
                return False
            if node is None:
                return False
            if node.bounds is None:
                return False
            make_raster = self.context.elements.lookup("render-op/make_raster")
            if make_raster is None:
                return False
            xmin, ymin, xmax, ymax = node.bounds
            if isinf(xmin):
                # No bounds for selected elements
                return False
            width = xmax - xmin
            height = ymax - ymin
            dpi = 150
            dots_per_units = dpi / UNITS_PER_INCH
            new_width = width * dots_per_units
            new_height = height * dots_per_units
            new_height = max(new_height, 1)
            new_width = max(new_width, 1)
            try:
                bitmap = make_raster(
                    [node],
                    bounds=node.bounds,
                    width=new_width,
                    height=new_height,
                    bitmap=True,
                )
            except Exception as e:
                # print (f"Raster failed: {e}")
                # Invalid path or whatever...
                return False
            try:
                bitmap.SaveFile(bmpfile, bitmap_format)
            except (OSError, RuntimeError, PermissionError, FileNotFoundError) as e:
                # print (f"Save failed: {e}")
                return False
            return True

        bitmap = None
        try:
            import wx
        except ImportError:
            return None
        base, ext = splitext(basename(fontfile))
        bmpfile = join(self.font_directory, base + ".png")
        if not exists(bmpfile):
            __ = create_preview_image(fontfile, bmpfile, wx.BITMAP_TYPE_PNG)
        if exists(bmpfile):
            bitmap = wx.Bitmap()
            bitmap.LoadFile(bmpfile, wx.BITMAP_TYPE_PNG)
        return bitmap

    def available_fonts(self):
        if self._available_fonts is not None:
            return self._available_fonts

        # Return a tuple of two values
        import platform
        from time import perf_counter
        t0 = perf_counter()
        systype = platform.system()
        directories = []
        directories.append(self.font_directory)
        if systype == "Windows":
            if "WINDIR" in environ:
                windir = environ["WINDIR"]
                directories.append(join(windir, "Fonts"))
            if "LOCALAPPDATA" in environ:
                appdir = environ["LOCALAPPDATA"]
                directories.append(join(appdir, "Microsoft\\Windows\\Fonts"))
        elif systype == "Linux":
            directories.append("/usr/share/fonts")
            directories.append("/usr/local/share/fonts")
            directories.append("~/.local/share/fonts")
        elif systype == "Darwin":
            directories.append("/Library/Fonts")
            directories.append("~/Library/Fonts")
        # Walk through all folders recursively
        found = dict()
        font_types = list(self.context.fonts.fonts_registered())
        self._available_fonts = []
        filelist = []
        for idx, fontpath in enumerate(directories):
            systemfont = idx != 0
            for p in font_types:
                found[p] = 0
            try:
                for root, dirs, files in walk(fontpath):
                    for filename in files:
                        short = basename(filename)
                        full_name = join(root, filename)
                        test = filename.lower()
                        for p in font_types:
                            if test.endswith(p):
                                if filename not in filelist:
                                    extended = short
                                    info = self.context.fonts.get_font_information(full_name)
                                    if info:
                                        # Tuple with font_family, font_subfamily, font_name
                                        extended = info[2]
                                    self._available_fonts.append((full_name, extended, systemfont))
                                    filelist.append(filename)
                                    found[p] += 1
                                break
            except (OSError, FileNotFoundError, PermissionError):
                continue
            # for key, value in found.items():
            #     print(f"{key}: {value} - {fontpath}")

        t1 = perf_counter()
        # print (f"Ready, took {t1 - t0:.2f}sec")
        return self._available_fonts

def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        context.fonts = Meerk40tFonts(context=context)

        # Register update routine for linetext
        kernel.register("path_updater/linetext", context.fonts.update)
        for idx, attrib in enumerate(("mkfontsize", "mkfontweld", "mkfontspacing")):
            kernel.register(f"registered_mk_svg_parameters/font{idx}", attrib)

        @context.console_option("font", "f", type=str, help=_("SHX font file."))
        @context.console_option(
            "font_size", "s", type=Length, default="20px", help=_("Font size")
        )
        @context.console_option(
            "font_spacing",
            "g",
            type=float,
            default=1,
            help=_("Character spacing factor"),
        )
        @context.console_command(
            "linetext", help=_("linetext <font> <font_size> <text>")
        )
        def linetext(
            command,
            channel,
            _,
            font=None,
            font_size=None,
            font_spacing=None,
            remainder=None,
            **kwargs,
        ):
            def display_fonts():
                for extension, item in registered_fonts:
                    desc = item[0]
                    channel(
                        _("{ftype} fonts in {path}:").format(ftype=desc, path=font_dir)
                    )
                    for p in glob(join(font_dir, "*." + extension.lower())):
                        channel(p)
                    for p in glob(join(font_dir, "*." + extension.upper())):
                        channel(p)
                    return

            registered_fonts = context.fonts.fonts_registered()
            if font_spacing is None:
                font_spacing = 1

            context.setting(str, "last_font", None)
            if font is not None:
                context.last_font = font
            font = context.last_font

            safe_dir = realpath(get_safe_path(context.kernel.name))
            context.setting(str, "font_directory", safe_dir)
            font_dir = context.font_directory

            if font is None:
                display_fonts()
                return
            font_path = join(font_dir, font)
            if not exists(font_path):
                channel(_("Font was not found at {path}").format(path=font_path))
                display_fonts()
                return
            if remainder is None:
                channel(_("No text to make a path with."))
                info = str(context.fonts.cached_fontclass.cache_info())
                channel(info)
                return
            x = 0
            y = float(font_size)

            # try:
            #     font = ShxFont(font_path)
            #     path = FontPath()
            #     font.render(path, remainder, True, float(font_size))
            # except ShxFontParseError as e:
            #     channel(f"{e.args}")
            #     return
            path_node = context.fonts.create_linetext_node(
                context, x, y, remainder, font, font_size, font_spacing
            )
            # path_node = PathNode(
            #     path=path.path,
            #     matrix=Matrix.translate(0, float(font_size)),
            #     stroke=Color("black"),
            # )
            context.elements.elem_branch.add_node(path_node)
            context.signal("element_added", path_node)
