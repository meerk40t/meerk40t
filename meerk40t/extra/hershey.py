import os.path
from glob import glob
from os.path import join, realpath

from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.units import Length
from meerk40t.kernel import get_safe_path
from meerk40t.svgelements import Arc, Color, Matrix, Path
from meerk40t.tools.shxparser import ShxFont
from meerk40t.tools.jhfparser import JhfFont

class FontPath:
    def __init__(self):
        self.path = Path()

    def new_path(self):
        pass

    def move(self, x, y):
        self.path.move((x, -y))

    def line(self, x0, y0, x1, y1):
        self.path.line((x1, -y1))

    def arc(self, x0, y0, cx, cy, x1, y1):
        arc = Arc(start=(x0, -y0), control=(cx, -cy), end=(x1, -y1))
        self.path += arc

def fonts_registered():
    registered_fonts = {
        "shx": ("Autocad", ShxFont),
        "jhf": ("Hershey", JhfFont),
    }
    return registered_fonts


def update_linetext(context, node, newtext):
    if node is None:
        return
    if not hasattr(node, "font"):
        return
    if not hasattr(node, "fontsize"):
        return
    registered_fonts = fonts_registered()
    fontname = node.font
    fontsize = node.fontsize
    # old_color = node.stroke
    # old_strokewidth = node.stroke_width
    # old_strokescaled = node._stroke_scaled
    font_dir = getattr(context, "font_directory", "")
    font_path = join(font_dir, fontname)
    if not os.path.exists(font_path):
        return
    try:
        filename, file_extension = os.path.splitext(font_path)
        if len(file_extension)>0:
            # Remove dot...
            file_extension = file_extension[1:].lower()
        item = registered_fonts[file_extension]
        fontclass = item[1]
    except (KeyError, IndexError):
        # channel(_("Unknown fonttype {ext}").format(ext=file_extension))
        return
    cfont = fontclass(font_path)
    path = FontPath()
    # print (f"Path={path}, text={remainder}, font-size={font_size}")
    horizontal = True
    cfont.render(path, newtext, horizontal, float(fontsize))
    node.path = path.path
    # node.stroke = old_color
    # node.stroke_width = old_strokewidth
    # node._stroke_scaled = old_strokescaled
    node.altered()

def create_linetext_node(context, x, y, text, font=None, font_size=None):
    registered_fonts = fonts_registered()
    context.setting(str, "shx_preferred", None)
    if font is not None:
        context.shx_preferred = font
    font = context.shx_preferred
    if font_size is None:
        font_size = Length("20px")
    safe_dir = realpath(get_safe_path(context.kernel.name))
    context.setting(str, "font_directory", safe_dir)
    font_dir = context.font_directory
    font_path = join(font_dir, font)
    try:
        filename, file_extension = os.path.splitext(font_path)
        if len(file_extension)>0:
            # Remove dot...
            file_extension = file_extension[1:].lower()
        item = registered_fonts[file_extension]
        fontclass = item[1]
    except (KeyError, IndexError):
        # channel(_("Unknown fonttype {ext}").format(ext=file_extension))
        return None
    cfont = fontclass(font_path)
    path = FontPath()
    # print (f"Path={path}, text={remainder}, font-size={font_size}")
    horizontal = True
    cfont.render(path, text, horizontal, float(font_size))

    path_node = PathNode(
        path=path.path,
        matrix=Matrix.translate(x, y),
        stroke=Color("black"),
    )
    path_node.font = font
    path_node.fontsize = float(font_size)
    path_node.text = text

    return path_node

def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root

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
                    channel(_("{ftype} fonts in {path}:").format(ftype=desc, path=font_dir))
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
            if not os.path.exists(font_path):
                channel(_("Font was not found at {path}").format(path=font_path))
                display_fonts()
                return
            if remainder is None:
                channel(_("No text to make a path with."))
                return
            x = 0
            y = float(font_size)
            path_node = create_linetext_node(context, x, y, remainder, font, font_size)
            context.elements.elem_branch.add_node(path_node)
            context.signal("element_added", path_node)
