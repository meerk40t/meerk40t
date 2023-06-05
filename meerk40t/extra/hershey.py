from glob import glob
from os.path import basename, exists, join, realpath, splitext

from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.units import UNITS_PER_PIXEL, Length
from meerk40t.kernel import get_safe_path
from meerk40t.svgelements import Arc, Color, Path
from meerk40t.tools.jhfparser import JhfFont
from meerk40t.tools.shxparser import ShxFont, ShxFontParseError
from meerk40t.tools.ttfparser import TrueTypeFont


class FontPath:
    def __init__(self):
        self.path = Path()

    def new_path(self):
        pass

    def move(self, x, y):
        self.path.move((x, -y))

    def line(self, x0, y0, x1, y1):
        self.path.line((x1, -y1))

    def quad(self, x0, y0, x1, y1, x2, y2):
        self.path.quad((x1, -y1), (x2, -y2))

    def cubic(self, x0, y0, x1, y1, x2, y2, x3, y3):
        self.path.cubic((x1, -y1), (x2, -y2), (x3, -y3))

    def close(self):
        self.path.closed()

    def arc(self, x0, y0, cx, cy, x1, y1):
        arc = Arc(start=(x0, -y0), control=(cx, -cy), end=(x1, -y1))
        self.path += arc


def fonts_registered():
    registered_fonts = {
        "shx": ("Autocad", ShxFont),
        "jhf": ("Hershey", JhfFont),
        "ttf": ("TrueType", TrueTypeFont),
    }
    return registered_fonts


def have_hershey_fonts(context):
    safe_dir = realpath(get_safe_path(context.kernel.name))
    context.setting(str, "font_directory", safe_dir)
    font_dir = context.font_directory
    registered_fonts = fonts_registered()
    for extension in registered_fonts:
        for p in glob(join(font_dir, "*." + extension.lower())):
            return True
        for p in glob(join(font_dir, "*." + extension.upper())):
            return True
    return False


def validate_node(node):
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


def update(context, node):
    # We need to check for the validity ourselves...
    if (
        hasattr(node, "mktext")
        and hasattr(node, "mkfont")
        and hasattr(node, "mkfontsize")
    ):
        update_linetext(context, node, node.mktext)


def update_linetext(context, node, newtext):
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
    oldtext = getattr(node, "_translated_text", "")
    registered_fonts = fonts_registered()
    fontname = node.mkfont
    fontsize = node.mkfontsize
    # old_color = node.stroke
    # old_strokewidth = node.stroke_width
    # old_strokescaled = node._stroke_scaled
    font_dir = getattr(context, "font_directory", "")
    font_path = join(font_dir, fontname)
    if not exists(font_path):
        # Fallback to meerk40t directory...
        safe_dir = realpath(get_safe_path(context.kernel.name))
        font_path = join(safe_dir, fontname)
        if not exists(font_path):
            return
    try:
        filename, file_extension = splitext(font_path)
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
    cfont = fontclass(font_path)
    path = FontPath()
    # print (f"Path={path}, text={remainder}, font-size={font_size}")
    horizontal = True
    mytext = context.elements.wordlist_translate(newtext)
    cfont.render(path, mytext, horizontal, float(fontsize))
    olda = node.path.transform.a
    oldb = node.path.transform.b
    oldc = node.path.transform.c
    oldd = node.path.transform.d
    olde = node.path.transform.e
    oldf = node.path.transform.f
    node.path = path.path
    node.path.transform.a = olda
    node.path.transform.b = oldb
    node.path.transform.c = oldc
    node.path.transform.d = oldd
    node.path.transform.e = olde
    node.path.transform.f = oldf
    # print (f"x={node.mkcoordx}, y={node.mkcoordy}")
    # node.path.transform = Matrix.translate(node.mkcoordx, node.mkcoordy)
    # print (f"Updated: from {oldtext} -> {mytext}")
    node.mktext = newtext
    node._translated_text = mytext
    node.altered()


def create_linetext_node(context, x, y, text, font=None, font_size=None):
    registered_fonts = fonts_registered()

    if font_size is None:
        font_size = Length("20px")

    context.setting(str, "shx_preferred", None)
    safe_dir = realpath(get_safe_path(context.kernel.name))
    context.setting(str, "font_directory", safe_dir)
    font_dir = context.font_directory
    # Check whether the default is still valid
    if context.shx_preferred is not None and context.shx_preferred != "":
        font_path = join(font_dir, context.shx_preferred)
        if not exists(font_path):
            context.shx_preferred = None
    # Valid font?
    if font is not None and font != "":
        font_path = join(font_dir, font)
        if not exists(font_path):
            font = None
    if font is not None:
        context.shx_preferred = font
    else:
        if context.shx_preferred is not None:
            #  print (f"Fallback to {context.shx_preferred}")
            font = context.shx_preferred
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
            fullfname = join(font_dir, fname)
            if exists(fullfname):
                # print (f"Taking font {fname} instead")
                font = fname
                context.shx_preferred = font
                break
        if font == "":
            # You know, I take anything at this point...
            for extension in registered_fonts:
                ext = "*." + extension
                if font == "":
                    for p in glob(join(font_dir, ext.lower())):
                        font = basename(p)
                        # print (f"Fallback to first file found: {font}")
                        context.shx_preferred = font
                        break
                if font == "":
                    for p in glob(join(font_dir, ext.upper())):
                        font = basename(p)
                        # print (f"Fallback to first file found: {font}")
                        context.shx_preferred = font
                        break

    if font is None or font == "":
        # print ("Font was empty")
        return None
    font_path = join(font_dir, font)
    try:
        filename, file_extension = splitext(font_path)
        if len(file_extension) > 0:
            # Remove dot...
            file_extension = file_extension[1:].lower()
        item = registered_fonts[file_extension]
        fontclass = item[1]
    except (KeyError, IndexError):
        # print(f"Unknown fonttype {file_extension}")
        return None
    horizontal = True
    try:
        cfont = fontclass(font_path)
        path = FontPath()
        # print (f"Path={path}, text={remainder}, font-size={font_size}")
        mytext = context.elements.wordlist_translate(text)
        cfont.render(path, mytext, horizontal, float(font_size))
    except ShxFontParseError as e:
        # print(f"FontParseError {e.args}")
        return
    #  print (f"Pathlen={len(path.path)}")
    # if len(path.path) == 0:
    #     print("Empty path...")
    #     return None

    path_node = PathNode(
        path=path.path,
        stroke=Color("black"),
    )
    path_node.matrix.post_translate(x, y)
    path_node.mkfont = font
    path_node.mkfontsize = float(font_size)
    path_node.mktext = text
    path_node._translated_text = mytext
    path_node.mkcoordx = x
    path_node.mkcoordy = y
    path_node.stroke_width = UNITS_PER_PIXEL

    return path_node


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root

        # Register update routine for linetext
        kernel.register("path_updater/linetext", update)

        @context.console_option("font", "f", type=str, help=_("SHX font file."))
        @context.console_option(
            "font_size", "s", type=Length, default="20px", help=_("SHX font file.")
        )
        @context.console_command(
            "linetext", help=_("linetext <font> <font_size> <text>")
        )
        def linetext(
            command, channel, _, font=None, font_size=None, remainder=None, **kwargs
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

            registered_fonts = fonts_registered()

            context.setting(str, "shx_preferred", None)
            if font is not None:
                context.shx_preferred = font
            font = context.shx_preferred

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
                return
            x = 0
            y = float(font_size)

            try:
                font = ShxFont(font_path)
                path = FontPath()
                font.render(path, remainder, True, float(font_size))
            except ShxFontParseError as e:
                channel(f"{e.args}")
                return
            path_node = create_linetext_node(context, x, y, remainder, font, font_size)
            # path_node = PathNode(
            #     path=path.path,
            #     matrix=Matrix.translate(0, float(font_size)),
            #     stroke=Color("black"),
            # )
            context.elements.elem_branch.add_node(path_node)
            context.signal("element_added", path_node)
