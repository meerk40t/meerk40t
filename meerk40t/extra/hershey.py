import os.path
from glob import glob
from os.path import join, realpath

from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.units import Length
from meerk40t.kernel import get_safe_path
from meerk40t.svgelements import Arc, Color, Matrix, Path
from meerk40t.tools.shxparser import ShxFont, ShxFontParseError


class ShxPath:
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
            context.setting(str, "shx_preferred", None)
            if font is not None:
                context.shx_preferred = font
            font = context.shx_preferred

            safe_dir = realpath(get_safe_path(context.kernel.name))
            if font is None:
                channel(_("SHX fonts in {path}:").format(path=safe_dir))
                for p in glob(join(safe_dir, "*.shx")):
                    channel(p)
                for p in glob(join(safe_dir, "*.SHX")):
                    channel(p)
                return
            font_path = join(safe_dir, font)
            if not os.path.exists(font_path):
                channel(_("Font was not found at {path}").format(path=font_path))
                for p in glob(join(safe_dir, "*.shx")):
                    channel(p)
                for p in glob(join(safe_dir, "*.SHX")):
                    channel(p)
                return
            if remainder is None:
                channel(_("No text to make a path with."))
                return
            try:
                font = ShxFont(font_path)
                path = ShxPath()
                font.render(path, remainder, True, float(font_size))
            except ShxFontParseError as e:
                channel(f"{e.args}")
                return
            path_node = PathNode(
                path=path.path,
                matrix=Matrix.translate(0, float(font_size)),
                stroke=Color("black"),
            )
            context.elements.elem_branch.add_node(path_node)
            context.signal("element_added", path_node)
