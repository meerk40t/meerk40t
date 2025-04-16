"""
Basic Module to provide infmoration about the GUI
"""
from math import sqrt
from platform import system
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

def inverted_color(c1:wx.Colour) -> wx.Colour:
    return wx.Colour(255-c1.red, 255-c1.green, 255-c1.blue, c1.alpha)

def is_a_bright_color(c1):
    return color_distance(c1, wx.BLACK) > color_distance(c1, wx.WHITE)

def is_a_dark_color(c1):
    return color_distance(c1, wx.BLACK) < color_distance(c1, wx.WHITE)

class Themes(Service):
    def __init__(self, kernel, index=None, *args, **kwargs):
        Service.__init__(self, kernel, "themes" if index is None else f"themes{index}")
        _ = wx.GetTranslation
        os_ver = system()
        if os_ver == "Darwin":
            kernel.root.setting(str, "forced_theme", "default")
            kernel.root.forced_theme = "default"
        else:
            if os_ver == "Windows":
                default_value = "light"
            elif os_ver == "Linux":
                default_value = "default"
            else:
                default_value = "default"
            choices = [
                {
                    "attr": "forced_theme",
                    "object": kernel.root,
                    "default": default_value,
                    "type": str,
                    "label": _("UI-Colours"),
                    "style": "option",
                    "choices": ("default", "dark", "light"),
                    "display": (_("System"), _("Dark"), _("Light")),
                    "tip": _("Will force MeerK40t to start in dark/lightmode despite the system settings"),
                    "page": "Start",
                    "signals": "restart",
                },
            ]
            kernel.register_choices("preferences", choices)

        self.forced_theme = kernel.root.forced_theme

        self.registered_themes = {
            "system": self.load_system_default,
        }
        self._theme = None
        self._dark = False
        self._theme_properties = {}
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
        if self.forced_theme == "dark":
            self._dark = True
        elif self.forced_theme == "light":
            self._dark = False
        else:
            try:
                res1 = wx.SystemSettings().GetAppearance().IsDark()
            except AttributeError:
                # Old wxpython version
                res1 = False
            res2 = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
            self._dark = res1 or res2

        self._theme_properties = {}
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
        tp["inactive_bg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INACTIVECAPTION)
        tp["inactive_fg"] = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INACTIVECAPTIONTEXT)
        # for key, col in tp.items():
        #     print (f'tp["{key}"] = wx.Colour({col.red}, {col.green}, {col.blue}, {col.alpha})')
        for p1, p2 in (("label_bg", "label_fg"), ("button_bg", "button_fg"), ("text_bg", "text_fg"), ("list_bg", "list_fg")):
            inv_col = inverted_color(tp[p2])
            if color_distance(tp[p2], tp[p1]) < color_distance(inv_col, tp[p1]):
                tp[p2] = inv_col
        if system() != "Darwin":
            # Alas, Darwin does not properly support overloading of colors...
            if not self.dark and is_a_dark_color(tp["win_bg"]):
                base_bg = wx.Colour(255, 255, 255)
                base_fg = wx.Colour(0, 0, 0)
                tp["win_bg"] = base_bg
                tp["win_fg"] = base_fg
                tp["button_bg"] = wx.Colour(240, 240, 240, 255)
                tp["button_fg"] = base_fg
                tp["text_bg"] = base_bg
                tp["text_fg"] = base_fg
                tp["list_bg"] = base_bg
                tp["list_fg"] = base_fg
                tp["label_bg"] = base_bg
                tp["label_fg"] = base_fg
                tp["highlight"] = wx.Colour(0, 120, 215, 255)
                tp["inactive_bg"] = wx.Colour(191, 205, 219, 255)
                tp["inactive_fg"] = base_fg        
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
                tp["highlight"] = wx.Colour(0, 0, 255)
                tp["inactive_bg"] = wx.Colour(46, 46, 46)
                tp["inactive_fg"] = base_fg
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


    def set_window_colors(self, win:wx.Window):
        tp = self._theme_properties
        win.SetBackgroundColour(tp["win_bg"])
        win.SetForegroundColour(tp["win_fg"])
