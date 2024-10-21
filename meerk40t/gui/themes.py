"""
Basic Module to provide infmoration about the GUI
"""
import wx

from meerk40t.kernel import Service


class Themes(Service):
    def __init__(self, kernel, index=None, *args, **kwargs):
        Service.__init__(self, kernel, "themes" if index is None else f"themes{index}")
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
        self._dark = wx.SystemSettings().GetColour(wx.SYS_COLOUR_WINDOW)[0] < 127
        from platform import system

        buggy_darwin = bool(system() == "Darwin" and not self._dark)

        self._theme_properties = dict()
        tp = self._theme_properties
        # Just a scaffold, will be extended later
        # tp["button"] = wx.Button
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
