"""
Provides and stores all relevant colors for gui.

This is a service, such that it's available at `.colors` for all contexts. However, this, because it requires wx a
purely gui service. Calling .colors.get("<aspect>") will provide the relevant wxColour() object.

All color aspects exist, if they don't actually exist a base color will be provided.
"""

import random

import wx

from meerk40t.kernel import Service
from meerk40t.svgelements import Color


def random_color():
    """
    Creates a random color.

    @return:
    """
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


def base_color(item):
    """
    Provides a base color, either default if the color is provided by default, or a random color.
    @param item:
    @return:
    """
    if item in default_color:
        return default_color[item]
    else:
        return random_color()


class GuiColors(Service):
    """
    Color service class, for wxGui.
    Service is registered by the gui.plugin
    """

    def __init__(self, kernel, *args, **kwargs):
        Service.__init__(self, kernel, "colors")
        _ = kernel.translation
        for key in default_color:
            self.setting(str, key, default_color[key])
        self.sanity_check()

    def __getattr__(self, item):
        """
        Getattr replaces the .color_* values with the declared colors.
        @param item:
        @return:
        """
        if not item.startswith("color_"):
            raise AttributeError
        return self.get_color(item[6:])

    def __setattr__(self, key, value):
        """
        Setattr applying to the .color_* values.

        @param key:
        @param value:
        @return:
        """
        if key.startswith("color_"):
            key = key[6:]
        super().__setattr__(key, value)

    def __getitem__(self, item):
        """
        Permit .colors["bed"], this will return a wx.Colour() object.
        @param item:
        @return:
        """
        return self.get(item)

    def get_color(self, item, default=None):
        """
        Returns a string color value corresponding to the key used.

        @param item:
        @param default:
        @return:
        """
        if default is None:
            default = base_color(item)
        d = self.__dict__
        if item in d:
            color = d[item]
        else:
            color = default
            d[item] = color

        if color == "default":
            color = base_color(item)
            d[item] = color
        return color

    def get(self, item, default=None):
        """
        Get wxColor at the item key value.

        @param item:
        @param default:
        @return:
        """
        color = self.get_color(item, default)
        c = Color(color)
        return wx.Colour(red=c.red, green=c.green, blue=c.blue, alpha=c.alpha)

    def sanity_check(self):
        """
        Look at some color-combinations to see if there are identical colors, if that's the case
        then this is degenerate and will lead to default colors
        @return:
        """

        def identical(color1, color2):
            return color1.GetRGB() == color2.GetRGB()

        bed_color = self.get("bed")
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
            item_color = self.get(key)
            if identical(bed_color, item_color):
                setattr(self, key, base_color(key))

    def set_random_colors(self):
        """
        Reset all colors to random values...
        """
        for key in default_color:
            setattr(self, key, random_color())

    def set_default_colors(self):
        """
        Reset all colors to default values...
        """
        for key in default_color:
            setattr(self, key, default_color[key])
