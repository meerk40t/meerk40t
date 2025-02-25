import os
import platform
from functools import lru_cache
from glob import glob
from os.path import basename, exists, join, realpath, splitext

from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.node import Fillrule, Linejoin
from meerk40t.core.units import UNITS_PER_INCH, Length
from meerk40t.tools.geomstr import BeamTable, Geomstr
from meerk40t.tools.jhfparser import JhfFont
from meerk40t.tools.shxparser import ShxFont, ShxFontParseError
from meerk40t.tools.ttfparser import TrueTypeFont, TTFParsingError

# import numpy as np


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
        # union.remove_0_length()
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

    @property
    def fonts_registered(self):
        fonts = {
            "shx": ("Autocad", ShxFont, None),
            "jhf": ("Hershey", JhfFont, None),
            "ttf": ("TrueType", TrueTypeFont, TrueTypeFont.query_name),
        }
        return fonts

    @property
    def font_directory(self):
        safe_dir = self.context.kernel.os_information["WORKDIR"]
        self.context.setting(str, "font_directory", safe_dir)
        fontdir = self.context.font_directory
        if not exists(fontdir):
            # Fallback, something strange happened...
            fontdir = safe_dir
            self.context.font_directory = fontdir
        return fontdir

    @font_directory.setter
    def font_directory(self, value):
        if not exists(value):
            # We cant allow a non-valid directory
            value = self.context.kernel.os_information["WORKDIR"]
        self.context.setting(str, "font_directory", value)
        self.context.font_directory = value
        self._available_fonts = None

    @property
    def cache_file(self):
        return join(self.font_directory, "fonts.cache")

    def reset_cache(self):
        fn = self.cache_file
        try:
            os.remove(fn)
        except (OSError, FileNotFoundError, PermissionError):
            pass
        self._available_fonts = None
        p = self.available_fonts()

    def have_hershey_fonts(self):
        p = self.available_fonts()
        return len(p) > 0

    @lru_cache(maxsize=512)
    def get_font_information(self, full_file_name):
        filename, file_extension = splitext(full_file_name)
        if len(file_extension) == 0:
            return None
        # Remove dot...
        file_extension = file_extension[1:].lower()
        try:
            item = self.fonts_registered[file_extension]
        except KeyError:
            return None
        if item[2]:
            return item[2](full_file_name)
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
            return info[4]
        return True

    def face_to_full_name(self, short):
        s_lower = short.lower()
        p = self.available_fonts()
        options = ("regular", "bold", "italic")
        candidates = []
        for info in p:
            # We don't care about capitalisation
            f_lower = info[1].lower()
            # print (f"Comparing {s_lower} to {f_lower} ({info[1]}, {info[2]}, {info[3]})")
            if f_lower == s_lower:
                return info[0]
            for idx, opt in enumerate(options):
                if f"{s_lower} {opt}" == f_lower:
                    # print (f"Appending {idx} {f_lower}")
                    candidates.append((idx, info[0]))
        if len(candidates):
            candidates.sort(key=lambda e: e[0])
            return candidates[0][1]
        return None

    def full_name(self, short):
        info = self._get_full_info(short)
        if info:
            return info[0]
        return None

    def short_name(self, fullname):
        return basename(fullname)

    @lru_cache(maxsize=128)
    def cached_fontclass(self, fontname):
        registered_fonts = self.fonts_registered
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
        try:
            cfont = fontclass(fontname)
        except (TTFParsingError, ShxFontParseError):
            return None
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

    def update(self, context=None, node=None):
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
        h_spacing = None
        if hasattr(node, "mkfontspacing"):
            try:
                h_spacing = float(node.mkfontspacing)
            except AttributeError:
                pass
        if h_spacing is None:
            h_spacing = 1
        v_spacing = None
        if hasattr(node, "mklinegap"):
            try:
                v_spacing = float(node.mklinegap)
            except AttributeError:
                pass
        if v_spacing is None:
            v_spacing = 1.1

        align = None
        if hasattr(node, "mkalign"):
            align = node.mkalign
        if align is None or align not in ("start", "middle", "end"):
            align = "start"

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
        # oldtext = getattr(node, "_translated_text", "")
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
        cfont.render(
            path, mytext, horizontal, float(fontsize), h_spacing, v_spacing, align
        )
        if hasattr(cfont, "line_information"):
            # Store the relative start / end positions of the text lines
            # for any interested party...
            node._line_information = cfont.line_information()
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
        tlines = mytext.split("\n")
        tlabel = f"Text: {tlines[0]}"
        if node.label is None or node.label.startswith("Text: "):
            node.label = tlabel

        node.altered()
        # _t4 = perf_counter()
        # print (f"Readfont: {_t1 -_t0:.2f}s, render: {_t2 -_t1:.2f}s, path: {_t3 -_t2:.2f}s, alter: {_t4 -_t3:.2f}s, total={_t4 -_t0:.2f}s")

    def _validate_font(self, font):
        """
        Check if the given font value is valid.

        @param font:
        @return:
        """
        if not font:
            return False
        # Let's check whether it's valid...
        font_path = self.full_name(font)
        if not font_path:
            # Font isn't found as processed.
            return False
        try:
            self.cached_fontclass(font_path)
        except TTFParsingError:
            # Font could not parse.
            return False
        return True

    def _try_candidates(self):
        # No preferred font set, let's try a couple of candidates...
        candidates = (
            "arial.ttf",
            "opensans_regular.ttf",
            "timesr.jhf",
            "romant.shx",
            "rowmans.jhf",
            "FUTURA.SHX",
        )
        for fname in candidates:
            if self._validate_font(fname):
                return self.full_name(fname)
        return None

    def _try_available(self):
        if not self.available_fonts():
            return None
        for i, font in enumerate(self._available_fonts):
            candidate = font[0]
            if self._validate_font(candidate):
                return candidate
        return None

    def retrieve_font(self, font):
        if not self._validate_font(font) and font is not None:
            # Is the given font valid?
            # It could still translate to a valid name
            font_path = self.face_to_full_name(font)
            if font_path:
                font = self.short_name(font_path)
                return font, font_path
            font = None
        if not font:
            # No valid font, try last font.
            font = self.context.last_font
            if not self._validate_font(font):
                font = None
        if not font:
            # Still not valid? Try preselected candidates.
            font = self._try_candidates()
        if not font:
            # You know, I take anything at this point...
            font = self._try_available()

        if not font:
            # No font could be located.
            return None, None

        # We have our valid font.
        font_path = self.full_name(font)
        font = self.short_name(font)
        return font, font_path

    def create_linetext_node(
        self, x, y, text, font=None, font_size=None, font_spacing=1.0, align="start",
    ):
        if font_size is None:
            font_size = Length("20px")
        if font_spacing is None:
            font_spacing = 1
        self.context.setting(str, "last_font", "")
        font, font_path = self.retrieve_font(font)

        if not font:
            # No font could be located.
            return None

        # We tried everything if there is a font, set it to last_font.
        self.context.last_font = font

        # We have our valid font.

        horizontal = True
        cfont = self.cached_fontclass(font_path)
        weld = False

        # Render the font.
        try:
            path = FontPath(weld)
            # print (f"Path={path}, text={remainder}, font-size={font_size}")
            mytext = self.context.elements.wordlist_translate(text)
            cfont.render(path, mytext, horizontal=horizontal, font_size=float(font_size), h_spacing=font_spacing, align=align)
        except (AttributeError, ShxFontParseError):
            # Could not parse path.
            pass

        tlines = mytext.split("\n")
        tlabel = "Text: {mktext}"
        # Create the node.
        path_node = PathNode(
            geometry=path.geometry,
            stroke=self.context.elements.default_stroke,
            stroke_width=self.context.elements.default_strokewidth,
            fill=self.context.elements.default_fill,
            fillrule=Fillrule.FILLRULE_NONZERO,
            linejoin=Linejoin.JOIN_BEVEL,
            label=tlabel,
        )
        path_node.matrix.post_translate(x, y)
        path_node.mkfont = font
        path_node.mkfontsize = float(font_size)
        path_node.mkfontspacing = float(font_spacing)
        path_node.mkfontweld = weld
        path_node.mkalign = align
        path_node.mklinegap = 1.1
        path_node.mktext = text
        path_node._translated_text = mytext
        path_node.mkcoordx = x
        path_node.mkcoordy = y
        if hasattr(cfont, "line_information"):
            # Store the relative start / end positions of the text lines
            # for any interested party...
            path_node._line_information = cfont.line_information()

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
            except Exception:
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
            except Exception:
                # print (f"Raster failed: {e}")
                # Invalid path or whatever...
                return False
            try:
                bitmap.SaveFile(bmpfile, bitmap_format)
            except (OSError, RuntimeError, PermissionError, FileNotFoundError):
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
        # from time import perf_counter

        _ = self.context.kernel.translation
        # t0 = perf_counter()
        self._available_fonts = []

        cache = self.cache_file
        if exists(cache):
            try:
                with open(cache, "r", encoding="utf-8") as f:
                    while True:
                        line = f.readline()
                        if not line:
                            break
                        line = line.strip()
                        parts = line.split("|")
                        if len(parts) > 4:
                            flag = False
                            if parts[4].lower in ("true", "1"):
                                flag = True
                            self._available_fonts.append(
                                (
                                    parts[0],
                                    parts[1],
                                    parts[2],
                                    parts[3],
                                    flag,
                                )
                            )
            except (OSError, FileNotFoundError, PermissionError):
                self._available_fonts = []
            if len(self._available_fonts):
                # t1 = perf_counter()
                # print (f"Cached, took {t1 - t0:.2f}sec")
                return self._available_fonts

        busy = self.context.kernel.busyinfo
        busy.start(msg=_("Reading system fonts..."))
        directories = []
        directories.append(self.font_directory)
        for d in self.context.system_font_directories:
            directories.append(d)
        # Walk through all folders recursively
        found = dict()
        font_types = self.fonts_registered
        filelist = []
        for idx, fontpath in enumerate(directories):
            busy.change(msg=fontpath, keep=1)
            busy.show()

            systemfont = idx != 0
            for p in font_types:
                found[p] = 0
            try:
                for root, dirs, files in os.walk(fontpath):
                    for filename in files:
                        if not filename:
                            continue
                        short = basename(filename)
                        if not short:
                            continue
                        full_name = join(root, filename)
                        test = filename.lower()
                        for p in font_types:
                            if test.endswith(p):
                                if filename not in filelist:
                                    font_family = ""
                                    font_subfamily = ""
                                    face_name = short
                                    info = self.get_font_information(full_name)
                                    if info:
                                        # Tuple with font_family, font_subfamily, face_name
                                        font_family, font_subfamily, face_name = info
                                    else:
                                        entry = font_types[p]
                                        font_family = entry[0]
                                    if face_name is None:
                                        face_name = short
                                    self._available_fonts.append(
                                        (
                                            str(full_name),
                                            str(face_name),
                                            font_family,
                                            font_subfamily,
                                            systemfont,
                                        )
                                    )
                                    # print (face_name, font_family, font_subfamily, full_name)
                                    filelist.append(filename)
                                    found[p] += 1
                                break
            except (OSError, FileNotFoundError, PermissionError):
                continue
            # for key, value in found.items():
            #     print(f"{key}: {value} - {fontpath}")
        self._available_fonts.sort(key=lambda e: e[1])
        try:
            with open(cache, "w", encoding="utf-8") as f:
                for p in self._available_fonts:
                    f.write(f"{p[0]}|{p[1]}|{p[2]}|{p[3]}|{p[4]}\n")
        except (OSError, FileNotFoundError, PermissionError):
            pass

        busy.end()
        # t1 = perf_counter()
        # print (f"Ready, took {t1 - t0:.2f}sec")
        return self._available_fonts


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root
        # Generate setting for system-directories
        directories = []
        systype = platform.system()
        if systype == "Windows":
            if "WINDIR" in os.environ:
                windir = os.environ["WINDIR"]
            else:
                windir = "c:\\windows"
            directories.append(join(windir, "Fonts"))
            if "LOCALAPPDATA" in os.environ:
                appdir = os.environ["LOCALAPPDATA"]
                directories.append(join(appdir, "Microsoft\\Windows\\Fonts"))
        elif systype == "Linux":
            directories.append("/usr/share/fonts")
            directories.append("/usr/local/share/fonts")
            directories.append("~/.local/share/fonts")
        elif systype == "Darwin":
            directories.append("/System/Library/Fonts")
            directories.append("/Library/Fonts")
            directories.append("~/Library/Fonts")
        choices = [
            {
                "attr": "system_font_directories",
                "object": context,
                "page": "_95_Fonts",
                "section": "_95_System font locations",
                "default": directories,
                "type": list,
                "columns": [
                    {
                        "attr": "directory",
                        "type": str,
                        "label": _("Directory"),
                        "width": -1,
                        "editable": True,
                    },
                ],
                "label": "_00_",
                "style": "chart",
                "primary": "directory",
                "allow_deletion": True,
                "allow_duplication": True,
                "tip": _("Places where MeerK40t will look for fonts."),
            },
        ]
        kernel.register_choices("preferences", choices)
        context.fonts = Meerk40tFonts(context=context)

        # Register update routine for linetext
        kernel.register("path_updater/linetext", context.fonts.update)
        for idx, attrib in enumerate(
            ("mkfontsize", "mkfontweld", "mkfontspacing", "mklinegap", "mkalign")
        ):
            kernel.register(f"registered_mk_svg_parameters/font{idx}", attrib)


        @context.console_argument("x", type=Length, help=_("X-Coordinate"))
        @context.console_argument("y", type=Length, help=_("Y-Coordinate"))
        @context.console_argument("text", type=str, help=_("Text to render"))
        @context.console_option("font", "f", type=str, help=_("Font file."))
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
            x=None,
            y=None,
            text=None,
            font=None,
            font_size=None,
            font_spacing=None,
            remainder=None,
            **kwargs,
        ):
            if x is None or y is None or text is None:
                channel(_("linetext <x> <y> <text> - please provide all required arguments"))
                registered_fonts = context.fonts.available_fonts()
                for item in registered_fonts:
                    channel(f"{item[1]} ({item[0]})")
                return
            try:
                x = float(Length(x))
                y = float(Length(y))
            except ValueError:
                channel(_("Invalid coordinates"))
                return
            if text is None or text == "":
                channel(_("No text given."))
                return


            if font_spacing is None:
                font_spacing = 1

            context.setting(str, "last_font", None)
            if font is None:
                font = context.last_font

            font_name, font_path = context.fonts.retrieve_font(font)
            if font_name is None:
                channel(f"Could not find a valid font file for '{font}'")
                registered_fonts = context.fonts.available_fonts()
                for item in registered_fonts:
                    channel(f"{item[1]} ({item[0]})")
                return

            channel(f"Will use font '{font_name}' ({font_path})")

            path_node = context.fonts.create_linetext_node(
                x, y, text, font_path, font_size, font_spacing
            )
            # path_node = PathNode(
            #     path=path.path,
            #     matrix=Matrix.translate(0, float(font_size)),
            #     stroke=Color("black"),
            # )
            context.elements.elem_branch.add_node(path_node)
            if context.elements.classify_new:
                context.elements.classify([path_node])
            context.elements.set_emphasis([path_node])

            context.signal("element_added", path_node)
            context.signal("refresh_scene", "Scene")
