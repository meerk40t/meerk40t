import random

import wx

from meerk40t.svgelements import Color


def random_color():
    return (
        f"#"
        f"{random.randint(0, 255):02X}"
        f"{random.randint(0, 255):02X}"
        f"{random.randint(0, 255):02X}"
    )


default_color = {
    "manipulation": "#A07FA0",
    "manipulation_handle": "#A07FA0",
    "laserpath": "#FF000040",
    "grid": "#A0A0A080",
    "guide": "#000000",
    "background": "#7F7F7F",
    "magnetline": "#A0A0FF60",
    "snap_visible": "#A0A0A040",
    "snap_closeup": "#00FF00A0",
    "selection1": "#0000FF",
    "selection2": "#00FF00",
    "selection3": "#FF0000",
    "measure_line": "#0000FF80",
    "measure_text": "#FF000060",
    "bed": "#FFFFFF",
    "grid2": "#A0A0A080",
    "guide2": "#000000",
    "grid3": "#A0A0A080",
    "guide3": "#A0A0A080",
}


class GuiColors:
    """
    Provides and stores all relevant colors for a scene
    """

    def __init__(self, context):
        self.context = context
        for key in default_color:
            self.context.setting(str, f"color_{key}", default_color[key])
        self.sanity_check()

    def get(self, item, default=None):
        if default is None:
            if item in default_color:
                default = default_color[item]
            else:
                default = random_color()
        return self.context.setting(str, f"color_{item}", default)

    def sanity_check(self):
        """
        Look at some color-combinations to see if there are identical colors, if that's the case
        then this is degenerate and will lead to default colors
        @return:
        """

        def identical(color1, color2):
            return color1.GetRGB() == color2.GetRGB()

        bed_color = self.color_bed
        fixed = 0
        for key in (
            "grid",
            "guide",
            "grid2",
            "guide2",
            "grid3",
            "guide3",
            "selection1",
            "selection2",
            "selection3",
        ):
            item_color = self._get_color(key)
            if identical(bed_color, item_color):
                fixed += 1
                color_key = f"color_{key}"
                setattr(self.context, color_key, default_color[key])
        # if fixed>0:
        # self.context("Reset %d colors to their defaults, as thye wre indistinguishable from the bed" % fixed)

    def set_random_colors(self):
        """
        Reset all colors to random values...
        """
        for key in default_color:
            color_key = f"color_{key}"
            setattr(self.context, color_key, random_color())

    def set_default_colors(self):
        """
        Reset all colors to default values...
        """
        for key in default_color:
            color_key = f"color_{key}"
            setattr(self.context, color_key, default_color[key])

    def _get_color(self, key):
        color_key = f"color_{key}"
        if hasattr(self.context, color_key):
            s = getattr(self.context, color_key)
            if len(s) == 0 or s == "default":
                # print ("Reset requested for color: %s" % color_key)
                s = default_color[key]
                setattr(self.context, color_key, s)
        else:
            s = default_color[key]
        c = Color(s)
        return wx.Colour(red=c.red, green=c.green, blue=c.blue, alpha=c.alpha)

    @property
    def color_manipulation(self):
        return self._get_color("manipulation")

    @property
    def color_manipulation_handle(self):
        return self._get_color("manipulation_handle")

    @property
    def color_laserpath(self):
        return self._get_color("laserpath")

    @property
    def color_grid(self):
        return self._get_color("grid")

    @property
    def color_grid2(self):
        return self._get_color("grid2")

    @property
    def color_grid3(self):
        return self._get_color("grid3")

    @property
    def color_guide(self):
        return self._get_color("guide")

    @property
    def color_guide2(self):
        return self._get_color("guide2")

    @property
    def color_guide3(self):
        return self._get_color("guide3")

    @property
    def color_background(self):
        return self._get_color("background")

    @property
    def color_magnetline(self):
        return self._get_color("magnetline")

    @property
    def color_snap_visible(self):
        return self._get_color("snap_visible")

    @property
    def color_snap_closeup(self):
        return self._get_color("snap_closeup")

    @property
    def color_selection1(self):
        return self._get_color("selection1")

    @property
    def color_selection2(self):
        return self._get_color("selection2")

    @property
    def color_selection3(self):
        return self._get_color("selection3")

    @property
    def color_measure_line(self):
        return self._get_color("measure_line")

    @property
    def color_measure_text(self):
        return self._get_color("measure_text")

    @property
    def color_bed(self):
        return self._get_color("bed")
