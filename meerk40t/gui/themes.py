"""
Basic Module to provide infmoration about the GUI
"""
from math import sqrt
import wx

from meerk40t.kernel import Service


def color_distance(c1:wx.Colour, c2:wx.Colour) -> bool:
    """
    Rather than naive Euclidean distance we use Compuphase's Redmean color distance.
    https://www.compuphase.com/cmetric.htm

    It's computationally simple, and empirical tests finds it to be on par with LabDE2000.

    :param c1: first color
    :param c2: second color
    :return: square of color distance
    """
    red_mean = int((c1.red + c2.red) / 2.0)
    r = c1.red - c2.red
    g = c1.green - c2.green
    b = c1.blue - c2.blue
    sq_dist =  (
        (((512 + red_mean) * r * r) >> 8)
        + (4 * g * g)
        + (((767 - red_mean) * b * b) >> 8)
    )
    # print (f"Distance from {c1.GetAsString()} to {c2.GetAsString()} = {sqrt(sq_dist)}")
    return sqrt(sq_dist)

def is_a_bright_color(c1):
    return color_distance(c1, wx.BLACK) > color_distance(c1, wx.WHITE)

def is_a_dark_color(c1):
    return color_distance(c1, wx.BLACK) < color_distance(c1, wx.WHITE)

class Themes(Service):
    def __init__(self, kernel, index=None, force_dark=False, *args, **kwargs):
        Service.__init__(self, kernel, "themes" if index is None else f"themes{index}")
        self.force_dark = force_dark
        self.registered_themes = {
            "system": self.load_system_default,
        }
        self._theme = None
        self._dark = False
        self._theme_properties = dict()
        self.theme = "system"

    @property
    def dark(self):
        return self._dark

    @property
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, new_theme):
        if new_theme in self.registered_themes:
            self._theme = new_theme
            self.registered_themes[new_theme]()

    def get(self, property_value):
        if property_value in self._theme_properties:
            return self._theme_properties[property_value]
        # property not found
        return None

    def load_system_default(self):
        self._theme = "system"
        res1 = wx.SystemSettings().GetAppearance().IsDark()
        res2 = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        # print (f"wx claims: {res1}, we think: {res2}, overload: {self.force_dark}")
        self._dark = res1 or res2 or self.force_dark
        from platform import system

        buggy_darwin = bool(system() == "Darwin" and not self._dark)

        self._theme_properties = dict()
        tp = self._theme_properties
        # Just a scaffold, will be extended later
        tp["win_bg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        tp["win_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        tp["button_bg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        tp["button_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT)
        tp["text_bg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        tp["text_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        tp["list_bg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)
        tp["list_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT)
        tp["label_bg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        tp["label_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_CAPTIONTEXT)
        tp["highlight"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)

        if self.dark and is_a_bright_color(tp["win_bg"]):
            base_bg = wx.Colour(23, 23, 23)
            base_fg = wx.Colour(255, 255, 255, 216)
            tp["win_bg"] = base_bg
            tp["win_fg"] = base_fg
            tp["button_bg"] = wx.Colour(46, 46, 46)
            tp["button_fg"] = base_fg
            tp["text_bg"] = base_bg
            tp["text_fg"] = base_fg
            tp["list_bg"] = base_bg
            tp["list_fg"] = base_fg
            tp["label_bg"] = base_bg
            tp["label_fg"] = base_fg
            tp["highlight"] = wx.BLUE

        tp["pause_bg"] = (
            wx.Colour(87, 87, 0) if self._dark else wx.Colour(200, 200, 0)
        )
        # wx.Colour("ORANGE") if self._dark else wx.Colour("YELLOW")
        tp["pause_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        # Start Button
        tp["start_bg"] = wx.Colour(150, 210, 148) # Mute green
        tp["start_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        tp["start_bg_inactive"] = wx.Colour(86, 146, 84)
        tp["start_fg_focus"] = wx.BLACK

        # Stop button
        tp["stop_bg_inactive"] = wx.Colour(145, 2, 0)
        tp["stop_bg"] = wx.Colour(172, 29, 27)  # Casual red
        tp["stop_fg"] = (
            wx.WHITE if self._dark else wx.BLACK
        )
        tp["stop_fg_focus"] = (
            wx.BLACK if self._dark else wx.WHITE
        )

        tp["arm_bg"] = wx.Colour(172, 29, 27)  # Casual red
        tp["arm_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        tp["arm_bg_inactive"] = wx.Colour(145, 2, 0)
        tp["arm_fg_focus"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)

        if buggy_darwin:
            for key, item in tp.items():
                if isinstance(item, wx.Colour):
                    # System default
                    tp[key] = None
            tp["pause_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)

    def set_window_colors(self, win:wx.Window):
        tp = self._theme_properties
        win.SetBackgroundColour(tp["win_bg"])
        win.SetForegroundColour(tp["win_fg"])
